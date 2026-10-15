"""Observe actual table-callback frame reservations without altering the compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from tools.experiments import game_table_fade_callback as source
from tools.experiments import game_actor_callback_frame_trace as observer
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-table-fade-frame'


def candidates():
    yield 'selected', source.SELECTED
    yield 'initial', source.INITIAL
    named = source.SELECTED.replace('    s32 value;', '    s32 step;\n    s32 coefficient;\n    s32 value;', 1)
    named = named.replace('            value = (s32)((u32)value + ((u32)D_800BE9E4 << 4));',
        '            step = D_800BE9E4;\n            value = (s32)((u32)value + ((u32)step << 4));')
    named = named.replace('        value = (s32)((u32)value - (u32)D_800BE9E4 * fades.values[index]);',
        '        step = D_800BE9E4;\n        coefficient = fades.values[index];\n        value = (s32)((u32)value - (u32)step * coefficient);')
    named = named.replace('    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)D_800BE9E4 * growth.values[index]);',
        '    step = D_800BE9E4;\n    coefficient = growth.values[index];\n    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)step * coefficient);')
    yield 'named-live-operands', named
    yield 'named-live-operands-reverse', named.replace('    s32 step;\n    s32 coefficient;', '    s32 coefficient;\n    s32 step;')
    yield 'named-live-operands-word-coefficient', named.replace('s32 coefficient;', 'u32 coefficient;')
    tail = source.SELECTED.replace('    s32 value;', '    s32 step;\n    s32 coefficient;\n    s32 value;', 1).replace(
        '    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)D_800BE9E4 * growth.values[index]);',
        '    step = D_800BE9E4;\n    coefficient = growth.values[index];\n    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)step * coefficient);')
    yield 'tail-live-operands', tail
    yield 'tail-live-operands-unsigned', tail.replace('s32 step;', 'u32 step;').replace('s32 coefficient;', 'u32 coefficient;')
    yield 'tail-live-operands-product-first', tail.replace('(u32)*(s16 *)(record + 0x14) + (u32)step * coefficient', '(u32)step * coefficient + (u32)*(s16 *)(record + 0x14)')
    yield 'tail-extent-through-value', tail.replace(
        '    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)step * coefficient);',
        '    value = *(s16 *)(record + 0x14);\n    extent = (s32)((u32)value + (u32)step * coefficient);')
    yield 'tail-result-through-value', tail.replace(
        '    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)step * coefficient);\n    *(s16 *)(record + 0x16) = extent;\n    *(s16 *)(record + 0x14) = extent;',
        '    extent = *(s16 *)(record + 0x14);\n    value = (s32)((u32)extent + (u32)step * coefficient);\n    *(s16 *)(record + 0x16) = value;\n    *(s16 *)(record + 0x14) = value;')
    for label, body in (('tail-product-through-step', tail.replace(
            '    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)step * coefficient);',
            '    step = (s32)((u32)step * coefficient);\n    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)step);')),
            ('tail-step-and-old-extent', tail.replace('    coefficient = growth.values[index];',
                '    coefficient = *(s16 *)(record + 0x14);').replace(
                '(u32)*(s16 *)(record + 0x14) + (u32)step * coefficient', '(u32)coefficient + (u32)step * growth.values[index]'))):
        yield label, body
    fade = source.SELECTED.replace('    s32 value;', '    s32 step;\n    s32 coefficient;\n    s32 value;', 1).replace(
        '        value = (s32)((u32)value - (u32)D_800BE9E4 * fades.values[index]);',
        '        step = D_800BE9E4;\n        coefficient = fades.values[index];\n        value = (s32)((u32)value - (u32)step * coefficient);')
    yield 'fade-live-operands', fade


def target(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[source.FUNCTION]
    return (text[f['value']:f['value'] + f['size']],
        [(at - f['value'], entries) for at, entries in relocations.items()
            if f['value'] <= at < f['value'] + f['size']])


def trace(root, out, name, body):
    root, out = Path(root).resolve(), Path(out).resolve()
    if not out.is_relative_to(root / 'conker/build') or Path(name).name != name:
        raise ValueError('Owned frame output required')
    if observer.fingerprints(root) != observer.COMPILERS:
        raise ValueError('Prepared compiler fingerprints changed')
    debugger = shutil.which('gdb')
    if not debugger:
        raise FileNotFoundError('Existing GDB required; no installation')
    source.freeze(root, out)
    work = out / name
    work.mkdir(exist_ok=True)
    owner_obj, _, row = source.measure(root, out, name, body)
    isolated = '#include <ultra64.h>\n' + source.DECLARATIONS + 'extern s32 D_800BE9E4;\n' + body
    normal, diagnostics = source.build.compile_owner(root, work, isolated, 'normal')
    if diagnostics or target(normal) != target(owner_obj):
        raise ValueError('Isolated callback differs from its complete owner')
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
        different_object_sections=sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k)),
        raw_target_sha256=hashlib.sha256(target(normal)[0]).hexdigest(), completed_exits=exits)
    (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=dict(candidates()), default='selected')
    parser.add_argument('--screen', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    if args.screen:
        for name, body in candidates():
            row = source.measure(root, out, name, body)[-1]
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'frame', 'diagnostics')}), flush=True)
        return
    receipt = trace(root, out, args.name, dict(candidates())[args.name])
    print(json.dumps({k: v for k, v in receipt.items() if k != 'records'}, indent=2))


if __name__ == '__main__':
    main()
