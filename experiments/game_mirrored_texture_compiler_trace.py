"""Observe mirrored-texture homes and spills in an owned, unchanged compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from tools.experiments import game_mirrored_texture_rectangles as source
from tools.experiments import game_actor_callback_frame_trace as frame
from tools.experiments import game_packet_rectangle_compiler_trace as qualified
from tools.experiments import game_text_measurer_ugen_nodes as nodes
from tools.pad_generated_object import parse_object

KNOWN = {
    'record': (626, 216, 604, source.RAW_SHA),
    'record-y-first': (622, 216, 599, '793004d757fc241ad54cfdc918b5d36a21c7a8a39abbfc5ea1f21d0f5db90361'),
    'step-promoted-short': (620, 208, 608, 'dbd71a0373814f701d2ed424b1c1959d773e4ca0dd026b84bbfb2f984382e9c9'),
    'step-register-short': (626, 216, 604, source.RAW_SHA),
}
CAPTURE_FILES = ('baseline.c', 'baseline-processed.c', 'trace.gdb', 'debugger.txt', 'baseline.o', 'trace.o',
    'frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json')


def forms():
    result = {n: dict(source.forms())[n] for n in ('record', 'record-y-first')}
    result['step-promoted-short'] = source.SELECTED.replace('u16 step;', 's32 step;').replace(
        'step = (u32)', 'step = (u16)(u32)')
    result['step-register-short'] = source.SELECTED.replace('u16 step;', 'register u16 step;')
    return result


def signature(obj):
    return (*source.parts(obj), {n: data for n, (_, data) in source.projection.sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and data})


def debugger_script(root, work):
    script = qualified.debugger_script(root, work)
    anchor = 'class FrameChanged(gdb.Breakpoint):'
    node_script = nodes.debugger_script(root)
    probe = node_script[node_script.index('class LoadNode('):node_script.index('end\ncatch exec')]
    probe = 'program=' + json.dumps(str((root / 'ido/ido5.3_recomp/ugen').resolve())) + '\nnode_probes=[]\n' + probe
    probe += '''def cleanup_nodes(event):
    if event.inferior.progspace.filename==program:
        for probe in node_probes:
            probe.delete()
        gdb.write('MIRROR_NODE_REMOVED\\n')
gdb.events.exited.connect(cleanup_nodes)
'''
    install = "        record('frame-watch-installed',mem)"
    if script.count(anchor) != 1 or script.count(install) != 1:
        raise ValueError('Changed qualified frame script anchors')
    script = script.replace(anchor, probe + anchor, 1)
    return script.replace(install, "        node_probes.append(LoadNode('*0x430480', internal=True))\n        gdb.write('MIRROR_NODE_INSTALLED\\n')\n" + install, 1)


def validate(work, root):
    receipt = json.loads((work / 'receipt.json').read_text())
    label = receipt.get('label')
    if (label not in KNOWN or receipt.get('exit_code') != 0 or receipt.get('installable') is not False or
            receipt.get('compiler_sha256') != frame.COMPILERS):
        raise ValueError('Incomplete mirrored-texture compiler receipt')
    meta = receipt['baseline']
    if (tuple(meta.get(k) for k in ('words', 'frame', 'differences', 'raw_sha256')) != KNOWN[label] or
            meta.get('diagnostics') != '' or meta.get('bindings') != json.loads(json.dumps(source.BINDINGS))):
        raise ValueError('Changed mirrored-texture diagnostic baseline')
    hashes = {n: hashlib.sha256((work / n).read_bytes()).hexdigest() for n in CAPTURE_FILES}
    if hashes != receipt.get('capture_sha256') or (work / 'trace.gdb').read_text() != debugger_script(root, work):
        raise ValueError('Changed mirrored-texture source/script/capture')
    log = (work / 'debugger.txt').read_text()
    lines = log.splitlines()
    if ('Python Exception' in log or 'Error in sourced' in log or
            lines.count('TRACE_EXIT inferior=1 code=0') != 1 or frame.fingerprints(root) != frame.COMPILERS):
        raise ValueError('Mirrored-texture trace did not complete unchanged')
    parsed = frame.validate_observations(work, log)
    exits = [json.loads(x[10:]) for x in lines if x.startswith('RECT_EXIT ')]
    for stage in ('cfe', 'uopt', 'ugen', 'as1', 'cc'):
        entries = [e for e in exits if e.get('stage') == stage]
        if len(entries) != 1 or entries[0].get('code') != 0 or set(entries[0]) != {'stage', 'inferior', 'code'}:
            raise ValueError('Incomplete mirrored-texture compiler stage: ' + stage)
    flow = [json.loads(x[10:]) for x in lines if x.startswith('RECT_FLOW ')]
    if (len(flow) != 2 or flow[0]['output'] != flow[1]['input'] or
            [e['stage'] for e in flow] != ['uopt', 'ugen']):
        raise ValueError('Disconnected mirrored-texture compiler flow')
    for stage, producer, entry, captured in zip(('uopt', 'ugen'), ('cfe', 'uopt'), flow, parsed['inputs']):
        if (set(entry) != {'stage', 'inferior', 'input', 'output', 'producer', 'producer_exits'} or
                entry['producer'] != producer or entry['producer_exits'] != [0] or
                entry['inferior'] != captured['inferior'] or entry['input'] != captured['path']):
            raise ValueError('Changed mirrored-texture producer/input')
        positions = lambda prefix, item: next(i for i, x in enumerate(lines)
            if x.startswith(prefix) and json.loads(x[len(prefix):]) == item)
        before = next(e for e in exits if e['stage'] == producer)
        after = next(e for e in exits if e['stage'] == stage)
        if not positions('RECT_EXIT ', before) < positions('RECT_FLOW ', entry) < positions('FRAME_INPUT ', captured) < positions('RECT_EXIT ', after):
            raise ValueError('Misordered mirrored-texture producer/consumer')
    tables = [json.loads(x[12:]) for x in lines if x.startswith('RECT_TABLES ')]
    actual = {k: hashlib.sha256((work / n).read_bytes()).hexdigest() for k, n in
        (('descriptors', 'ucode-table.json'), ('types', 'ucode-types.json'))}
    if tables != [qualified.TABLES] or actual != qualified.TABLES:
        raise ValueError('Changed mirrored-texture Ucode tables')
    node_events = nodes.node_events(log)
    positions = [i for i, x in enumerate(lines) if x.startswith('UGEN_NODE ')]
    child = next(e for e in exits if e['stage'] == 'ugen')
    if (not node_events or lines.count('MIRROR_NODE_INSTALLED') != 1 or lines.count('MIRROR_NODE_REMOVED') != 1 or
            not lines.index('MIRROR_NODE_INSTALLED') < min(positions) <= max(positions) <
            lines.index('TRACE_EXIT inferior=%d code=0' % child['inferior']) <
            lines.index('MIRROR_NODE_REMOVED') < lines.index('TRACE_EXIT inferior=1 code=0')):
        raise ValueError('Incomplete mirrored-texture load-node observation')
    if parse_object(work / 'baseline.o') != parse_object(work / 'trace.o') or signature(work / 'baseline.o') != signature(work / 'trace.o'):
        raise ValueError('Mirrored-texture trace changed code/bindings/pools')
    raw, bindings, pools = signature(work / 'baseline.o')
    if (len(raw) != KNOWN[label][0] * 4 or hashlib.sha256(raw).hexdigest() != KNOWN[label][3] or
            bindings != source.BINDINGS or pools or set(parse_object(work / 'baseline.o')[1]) != {source.FUNCTION}):
        raise ValueError('Unknown mirrored-texture isolated code/bindings/pools')
    if [(e['event'], e['frame'], e['locals'], e['temporary'], e['pool']) for e in parsed['events']] != [
            ('frame-watch-installed', 0, 0, 0, []), ('frame-write', KNOWN[label][1], KNOWN[label][1], 0, [])]:
        raise ValueError('Changed mirrored-texture frame observation')
    return dict(**parsed, node_events=node_events)


def trace(root, label='record', run=None):
    root = Path(root).resolve()
    if label not in forms() or not re.fullmatch('[A-Za-z0-9_-]+', label):
        raise ValueError('Unknown bounded mirrored-texture source')
    if run is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', run):
        raise ValueError('Invalid owned trace run name')
    out = root / source.BUILD
    work = out / ((run + '-' if run is not None else 'compiler-homes-v2-') + label)
    if work.exists():
        raise ValueError('Preserve existing trace; no automatic restart')
    if frame.fingerprints(root) != frame.COMPILERS or not shutil.which('gdb'):
        raise ValueError('Prepared compiler/GDB required; no installation')
    body = forms()[label]
    full, _, meta = source.measure(root, out, 'compiler-owner-' + label, body)
    if tuple(meta.get(k) for k in ('words', 'frame', 'differences', 'raw_sha256')) != KNOWN[label]:
        raise ValueError('Changed complete mirrored-texture candidate')
    owner = source.recovered_owner((out / 'before-color_owner').read_text(), body)
    pragmas = re.findall(r'^#pragma GLOBAL_ASM\("asm/nonmatchings/generated_1AC2F0/(func_[0-9A-F]+)\.s"\)$', owner, re.M)
    if pragmas != ['func_15182670']:
        raise ValueError('Changed isolated owner assembly declarations')
    owner = re.sub(r'^#pragma GLOBAL_ASM\([^\n]+\)\n', '', owner, flags=re.M)
    view = re.sub(r'^(?:u32|u8|Gfx)\s*\*', lambda m: 's32' + ' ' * (len(m.group()) - 3), owner, flags=re.M)
    for lo, hi in sorted((source.build.function_span(view, n) for n in parse_object(full)[1] if n not in [source.FUNCTION, *pragmas]), reverse=True):
        owner = owner[:lo] + owner[hi:]
    work.mkdir()
    normal, diagnostics = source.compile_owner(root, work, owner, 'baseline')
    full_sig, isolated_sig = signature(full), signature(normal)
    if (diagnostics or set(parse_object(normal)[1]) != {source.FUNCTION} or isolated_sig[:2] != full_sig[:2]
            or isolated_sig[2] or full_sig[2] != {'.rodata': source.projection.POOL}):
        raise ValueError('Isolated mirrored texture differs from complete owner')
    script = work / 'trace.gdb'
    script.write_text(debugger_script(root, work))
    command = [shutil.which('gdb'), '--nx', '--batch', '--iex', 'set auto-load off', '-x', str(script), '--args',
        str(root / 'ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-D_LANGUAGE_C', '-D_FINALROM',
        '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', '-woff', '649,838']
    for include in ('.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
            'src/libultra/os', 'src/libultra/audio', 'src/libultra/io'):
        command.extend(('-I', include))
    command.extend(('-O2', '-g3', '-mips2', '-o32', '-o', os.path.relpath(work / 'trace.o', root / 'conker'),
        os.path.relpath(work / 'baseline-processed.c', root / 'conker')))
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    (work / 'debugger.txt').write_text(result.stdout + result.stderr)
    receipt = dict(label=label, baseline=meta, exit_code=result.returncode, code_unchanged=False,
        compiler_sha256=frame.fingerprints(root), installable=False,
        capture_sha256={n: hashlib.sha256((work / n).read_bytes()).hexdigest() for n in CAPTURE_FILES})
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if result.returncode:
        raise ValueError('Mirrored compiler trace failed; inspect retained output')
    receipt.update(validate(work, root), code_unchanged=True, isolated_target_matches_complete_owner=True,
        isolated_pools={}, complete_owner_pool_sha256=hashlib.sha256(source.projection.POOL).hexdigest())
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    source.freeze(root, out)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='record', choices=forms())
    parser.add_argument('--run', help='New owned output prefix; existing runs are never replaced')
    args = parser.parse_args()
    record = trace(Path(__file__).resolve().parents[2], args.name, args.run)
    print(json.dumps({k: v for k, v in record.items() if k not in ('records', 'node_events')}, indent=2), flush=True)
