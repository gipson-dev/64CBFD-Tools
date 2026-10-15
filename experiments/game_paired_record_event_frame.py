"""Observe real compiler home/spill reservations for the uninstalled paired event."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from tools.experiments import game_paired_record_event as source
from tools.experiments import game_actor_callback_frame_trace as observer
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

NAMES = ('initial_inputs', 'initial_plain_short_temps', 'initial')


def candidates():
    result = {name: source.candidates()[name] for name in NAMES}
    inline = dict(byte4='(u8)arg4', byte6='(u8)arg6',
        width='(s16)((s32)((u32)arg7 << 12) / 4096)',
        height='(s16)((s32)((u32)arg8 << 12) / 4096)',
        half3='(u16)arg3', byte9='(u8)arg9', half5='(s16)arg5',
        shiftedWidth='((s32)((u32)arg7 << 12) / 4096)',
        shiftedHeight='((s32)((u32)arg8 << 12) / 4096)')
    for label, replacements in (('expression_values', inline),
            ('expression_all', dict(inline, x='arg0', y='arg1', z='arg2'))):
        body = result['initial_inputs']
        for local, value in replacements.items():
            body = re.sub(r'^    (?:s32 ' + local + r';|' + local + r' = [^\n]+;)\n', '', body, flags=re.M)
            body = body.replace('(&%s)[0]' % local, local)
            body = re.sub(r'\b' + local + r'\b', value, body)
        result[label] = body
        result[label + '_live_context'] = body.replace('(void *)arg3', '(void *)(&arg3)[0]')
    return result


def target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[source.FUNCTION]
    return (text[f['value']:f['value'] + f['size']],
        [(at - f['value'], entries) for at, entries in rel.items()
            if f['value'] <= at < f['value'] + f['size']])


def trace(root, name, previous_input=None):
    if name not in candidates():
        raise ValueError('Unknown bounded paired-event frame candidate')
    root = Path(root).resolve()
    out = root / source.BUILD
    work = out / ('frame-' + name)
    if not work.resolve().is_relative_to(root / 'conker/build'):
        raise ValueError('Owned frame output required')
    source.freeze(root, out)
    for key, path in source.PATHS.items():
        payload = (root / path).read_bytes()
        if previous_input is not None:
            payload = previous_input(payload, path, root)
        if hashlib.sha256(payload).hexdigest() != source.BASELINE[key]:
            raise ValueError('Changed paired-event compiler input: ' + key)
    if observer.fingerprints(root) != observer.COMPILERS:
        raise ValueError('Prepared compiler fingerprints changed')
    debugger = shutil.which('gdb')
    if not debugger:
        raise FileNotFoundError('Existing GDB required; no installation')
    body = candidates()[name]
    work.mkdir(exist_ok=True)
    owner_obj, _, row = source.measure(root, out, 'frame-owner-' + name, body)
    before = (out / 'before-preset_owner').read_text()
    lo, _ = source.build.function_span(before, 'func_1516D99C')
    prototype = before[lo:before.index('{', lo)].rstrip() + ';\n'
    isolated = '#include <ultra64.h>\n#include "structs.h"\n' + prototype + body
    normal, diagnostics = source.build.compile_owner(root, work, isolated, 'normal')
    if diagnostics or target(normal) != target(owner_obj):
        raise ValueError('Isolated paired event differs from complete owner')
    script = work / 'frame.gdb'
    script.write_text(observer.debugger_script(root, work))
    command = [debugger, '--nx', '--batch', '--iex', 'set auto-load off', '-x', str(script), '--args',
        str(root / 'ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-D_LANGUAGE_C', '-D_FINALROM',
        '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', '-woff', '649,838']
    for include in ('.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
            'src/libultra/os', 'src/libultra/audio', 'src/libultra/io'):
        command.extend(('-I', include))
    command.extend(('-O2', '-g3', '-mips2', '-o32', '-o', os.path.relpath(work / 'traced.o', root / 'conker'),
        os.path.relpath(work / 'normal-processed.c', root / 'conker')))
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    log = result.stdout + result.stderr
    (work / 'debugger.txt').write_text(log)
    receipt = dict(compiler_sha256=observer.fingerprints(root), baseline=row, exit_code=result.returncode,
        source_context='exact predecessor adapter' if previous_input is not None else 'unchanged predecessor',
        code_unchanged=False, installable=False)
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if result.returncode or 'TRACE_EXIT inferior=1 code=0' not in log.splitlines():
        raise ValueError('Owned compiler did not finish; inspect its actual process/log')
    captures = observer.validate_observations(work, log)
    exits = [line for line in log.splitlines() if line.startswith('TRACE_EXIT ')]
    if len(exits) < 4 or any(not line.endswith(' code=0') for line in exits):
        raise ValueError('Compiler producer/consumer completion failed')
    if observer.fingerprints(root) != observer.COMPILERS or parse_object(normal) != parse_object(work / 'traced.o'):
        raise ValueError('Compiler or complete traced object changed')
    a, b = sections(normal), sections(work / 'traced.o')
    if a.keys() != b.keys() or any(a[k] != b[k] for k in a if k.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))):
        raise ValueError('Traced pools changed')
    receipt.update(captures, code_unchanged=True, standalone_equals_complete_owner=True,
        literal_object_files_equal=normal.read_bytes() == (work / 'traced.o').read_bytes(),
        different_object_sections=sorted(k for k in a if a[k] != b[k]),
        raw_target_sha256=hashlib.sha256(target(normal)[0]).hexdigest(), completed_exits=exits)
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=candidates(), default=NAMES[0])
    parser.add_argument('--screen', action='store_true')
    args = parser.parse_args()
    if args.screen:
        root = Path(__file__).resolve().parents[2]
        for name, body in candidates().items():
            if name in NAMES:
                continue
            row = source.measure(root, root / source.BUILD, 'fit-' + name, body)[-1]
            print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)
        raise SystemExit(0)
    result = trace(Path(__file__).resolve().parents[2], args.name)
    summary = {k: v for k, v in result.items() if k != 'records'}
    summary['baseline'] = {k: v for k, v in result['baseline'].items() if k != 'different_words'}
    print(json.dumps(summary, indent=2))
