"""Recover the live callback/removal and wrapping 24.8 record update."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_small_record_factory as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import small_record_factory_checkpoint as checkpoint
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-packed-record-updater'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516D678', 0x1516D678, 0x19AB28, 48
TABLE, DELTA, REMOVE = 0x8008CBA0, 0x800BE9E4, 0x1516972C
PATHS = dict(previous.PATHS, callback_original='conker/asm/data/231660.rodata.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    callback_original='aa2ca7a05a0854c2d80d3c05663316357ffbb6c03842e5e5113bb2774731afe0')
DECLARATIONS = '''extern s32 (*D_8008CBA0[])(u8 *record);
void func_1516972C(struct102 *record);
'''
SELECTED = '''/* Dispatch the packed record; remove only on 1, otherwise advance 24.8 Y. */
void func_1516D678(u8 *record) {
    s32 remaining;
    u8 counter = record[0x24];
    u8 *binding;
    u32 fixed;

    if (counter != 0) {
        remaining = (s32)((u32)counter - (u32)D_800BE9E4);
        if (remaining < 0) {
            remaining = 0;
        }
        record[0x24] = remaining;
    }
    if (D_8008CBA0[record[0x23]](record) == 1) {
        binding = *(u8 **)(record + 0x30);
        if (binding != NULL) {
            *(s16 *)(binding + 4) = 0;
        }
        func_1516972C((struct102 *)record);
        return;
    }
    fixed = ((u32)(s32)*(s16 *)(record + 0x10) << 8) + record[0x25] +
        (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;
    *(s16 *)(record + 0x10) = (s32)fixed >> 8;
    record[0x25] = fixed;
}
'''
INITIAL = SELECTED
SELECTED = INITIAL.replace('    s32 remaining;\n    u8 counter = record[0x24];',
    '    s32 value = record[0x24];').replace('    u32 fixed;', '    s32 fixed;').replace(
    'counter != 0', 'value != 0').replace('remaining = (s32)((u32)counter', 'value = (s32)((u32)value').replace(
    'if (remaining < 0)', 'if (value < 0)').replace('remaining = 0;', 'value = 0;').replace(
    'record[0x24] = remaining;', 'record[0x24] = value;').replace('''    fixed = ((u32)(s32)*(s16 *)(record + 0x10) << 8) + record[0x25] +
        (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;''', '''    value = *(s16 *)(record + 0x10);
    value = value * 256;
    value += record[0x25];
    fixed = (s32)((u32)value + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4);''').replace(
    '/* Dispatch the packed record; remove only on 1, otherwise advance 24.8 Y. */',
    '/* Dispatch the packed record; remove only on 1, otherwise advance 24.8 Y.\n'
    ' * Three expected-word guards preserve the final temporary and operand order. */')
GUARDS = ((0xA0, 0x01821821, 0x004C7021), (0xA4, 0x00036A03, 0x000E6A03), (0xAC, 0xA0830025, 0xA08E0025))
RAW_SHA256 = '0f1c3e44ac133b87a612e230c5f09a8ce971494c0dca8a8b05195cc6882a1f98'
RELOCATIONS = {12: [('R_MIPS_HI16', 'D_800BE9E4')], 24: [('R_MIPS_LO16', 'D_800BE9E4')],
    56: [('R_MIPS_HI16', 'D_8008CBA0')], 68: [('R_MIPS_LO16', 'D_8008CBA0')],
    108: [('R_MIPS_26', 'func_1516972C')], 124: [('R_MIPS_HI16', 'D_800BE9E4')], 128: [('R_MIPS_LO16', 'D_800BE9E4')]}


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown packed-updater words or relocations')
    words = list(struct.unpack('>48I', raw))
    for offset, expected, replacement in GUARDS:
        if words[offset // 4] != expected:
            raise ValueError('Changed packed-updater register site')
        words[offset // 4] = replacement
    return words


def guard_manifest(before):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown packed-updater guard predecessor')
    rows = ''.join('%s,%s,0x%X,0x%08X,0x%08X,-,-,Preserve closed final fixed-point temporary allocation and commutative addition order,,,false\n' %
        (OWNER, FUNCTION, offset, expected, replacement) for offset, expected, replacement in GUARDS)
    return before + rows.encode()


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed packed-updater predecessor')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed packed-updater manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed packed-updater fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516D678() {\n    return 0;\n}':
        raise ValueError('Unknown packed-updater placeholder')
    marker = '#include <ultra64.h>\n'
    if before.count(marker) != 1 or '#include "structs.h"' in before:
        raise ValueError('Unknown packed-updater preamble')
    return (before[:lo] + selected.rstrip() + before[hi:]).replace(marker,
        marker + '#include "structs.h"\n\n' + DECLARATIONS, 1)


def measure(root, out, label, selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, fs = build.link_owner(root, out, obj, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>48I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (48, 3, ''):
        raise ValueError('Changed packed-updater reconstruction: ' + repr(row))
    raw, fs, rel = parse_object(obj)
    f = fs[FUNCTION]
    relative = {p - f['value']: r for p, r in rel.items() if f['value'] <= p < f['value'] + f['size']}
    normalize(raw[f['value']:f['value'] + f['size']], relative)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guard_manifest((out / 'before-guards').read_bytes()))
    text = emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=manifest)
    path = out / 'qualified-padded.s'
    path.write_text(text)
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], capture_output=True, check=True)
    data, fs = build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    guarded = list(struct.unpack_from('>48I', data, f['value']))
    truth = list(struct.unpack_from('>48I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if f['size'] != 192 or guarded != truth:
        raise ValueError('Packed updater production padder differs')
    row.update(guards=3, guarded_differences=0, raw_differences=3, frame=24, not_direct_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, guarded, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='Compile only labels with this prefix')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    if not args.only or 'corrected'.startswith(args.only):
        _, _, row = measure(root, out, 'corrected', INITIAL)
        print(json.dumps(row), flush=True)
    base = INITIAL.replace('    s32 remaining;\n    u8 counter = record[0x24];',
        '    s32 remaining = record[0x24];').replace('counter != 0', 'remaining != 0').replace('(u32)counter', '(u32)remaining')
    math = '''    fixed = ((u32)(s32)*(s16 *)(record + 0x10) << 8) + record[0x25] +
        (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;'''
    forms = {'single-countdown': base, 'signed-fixed': base.replace('u32 fixed;', 's32 fixed;')}
    forms['split-fixed'] = base.replace(math, '''    fixed = ((u32)(s32)*(s16 *)(record + 0x10) << 8) + record[0x25];
    fixed += (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;''')
    forms['signed-stage'] = base.replace('u32 fixed;', 's32 fixed;').replace(math, '''    fixed = (s32)*(s16 *)(record + 0x10) * 256 + record[0x25];
    fixed = (s32)((u32)fixed + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4);''')
    forms['signed-group'] = base.replace('u32 fixed;', 's32 fixed;').replace(math, '''    fixed = (s32)((u32)((s32)*(s16 *)(record + 0x10) * 256 + record[0x25]) +
        (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4);''')
    forms['reuse-countdown-y'] = base.replace(math, '''    remaining = *(s16 *)(record + 0x10);
    fixed = ((u32)remaining << 8) + record[0x25] +
        (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;''')
    forms['reuse-countdown-sum'] = base.replace(math, '''    remaining = *(s16 *)(record + 0x10);
    remaining = remaining * 256 + record[0x25];
    fixed = (u32)remaining + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;''')
    forms['named-y'] = base.replace('    u32 fixed;', '    s32 y;\n    u32 fixed;').replace(math, '''    y = *(s16 *)(record + 0x10);
    fixed = ((u32)y << 8) + record[0x25] +
        (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;''')
    forms['named-base'] = base.replace('    u32 fixed;', '    s32 y;\n    u32 fixed;').replace(math, '''    y = *(s16 *)(record + 0x10);
    y = y * 256 + record[0x25];
    fixed = (u32)y + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;''')
    reuse = forms['reuse-countdown-sum']
    forms['reuse-signed-result'] = reuse.replace('u32 fixed;', 's32 fixed;').replace(
        'fixed = (u32)remaining + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4;',
        'fixed = (s32)((u32)remaining + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4);')
    forms['fraction-first'] = forms['reuse-signed-result'].replace('remaining * 256 + record[0x25]',
        'record[0x25] + remaining * 256')
    forms['split-shift'] = forms['reuse-signed-result'].replace('    remaining = remaining * 256 + record[0x25];',
        '    remaining = remaining * 256;\n    remaining += record[0x25];')
    tail = '''    fixed = (s32)((u32)remaining + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4);
    *(s16 *)(record + 0x10) = (s32)fixed >> 8;
    record[0x25] = fixed;'''
    expression = '(u32)remaining + (u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4'
    forms['inline-result'] = forms['split-shift'].replace('    s32 fixed;\n', '').replace(tail,
        '    *(s16 *)(record + 0x10) = (s32)(' + expression + ') >> 8;\n    record[0x25] = ' + expression + ';')
    forms['inline-result-reverse'] = forms['inline-result'].replace(expression,
        '(u32)(s32)*(s16 *)(record + 0x18) * (u32)D_800BE9E4 + (u32)remaining')
    for label, body in forms.items():
        if args.only and not label.startswith(args.only):
            continue
        _, _, row = measure(root, out, label, body)
        print(json.dumps(row), flush=True)
    original_decls = '    s32 remaining = record[0x24];\n    u8 *binding;\n    s32 fixed;'
    import itertools
    declarations = ('    s32 remaining = record[0x24];', '    u8 *binding;', '    s32 fixed;')
    for i, order in enumerate(itertools.permutations(declarations)):
        if args.only and not ('local-order-%d' % i).startswith(args.only):
            continue
        body = forms['split-shift'].replace(original_decls, '\n'.join(order))
        _, _, row = measure(root, out, 'local-order-%d' % i, body)
        print(json.dumps(row), flush=True)
    if not args.only or 'qualified'.startswith(args.only):
        _, _, _, _, row = qualify(root, out)
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
