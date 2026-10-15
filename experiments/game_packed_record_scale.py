"""Recover the packed fade/scale callback without truncating its live accumulator."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_packed_record_updater as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import packed_record_updater_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly, parse_object

BUILD = 'conker/build/game-packed-record-scale'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516ECAC', 0x1516ECAC, 0x19C15C, 47
DELTA = 0x800BE9E4
PATHS = dict(previous.PATHS, texture_owner='conker/src/game_16EE20.c',
    packet_owner='conker/src/game/generated_C1D70.c', packet_original='conker/asm/C1D70.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    texture_owner='7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810',
    packet_owner='466484e6b845016ee44bb8635941cfff9f753516af836b27eb31ded35b7bd111',
    packet_original='dcf4dee9900592f8f40476367e93b455b7e5a3d1705e2c0bb658657b7780b139')
SELECTED = '''/* Fade the packed intensity and scale both extents; report a completed fade. */
s32 func_1516ECAC(u8 *record) {
    s32 value = record[0x1F];
    s32 scale;

    if (record[0x24] != 0) {
        if (value != 0xFF) {
            value = (s32)((u32)value + ((u32)D_800BE9E4 << 7));
            if (value >= 0x100) {
                value = 0xFF;
            }
            record[0x1F] = value;
        }
    } else if (value != 0) {
        value = (s32)((u32)value - (u32)D_800BE9E4 * record[0x26]);
        if (value < 0) {
            value = 0;
        }
        record[0x1F] = value;
    }
    if (record[0x24] == 0 && value == 0) {
        return 1;
    }
    scale = (s32)((u32)((record[0x2C] << 8) | record[0x2D]) * (u32)value) >> 7;
    *(s16 *)(record + 0x16) = scale;
    *(s16 *)(record + 0x14) = scale;
    return 0;
}
'''
INITIAL = SELECTED
SELECTED = SELECTED.replace('    s32 scale;', '    s32 scale;\n    s32 base;').replace(
    'scale = (s32)((u32)((record[0x2C] << 8) | record[0x2D]) * (u32)value) >> 7;',
    'base = record[0x2D] | (record[0x2C] << 8);\n'
    '    scale = (s32)((u32)base * (u32)value);\n    scale >>= 7;')
SELECTED = SELECTED.replace('/* Fade the packed intensity and scale both extents; report a completed fade. */',
    '/* Fade intensity and scale both extents; report completion.\n'
    ' * Three relocation-aware guards retain the retail operand-load schedule. */')
GUARDS = ((0x48, 0x3C190000, 0x3C180000, 'R_MIPS_HI16:D_800BE9E4', 'R_MIPS_HI16:D_800BE9E4'),
    (0x4C, 0x90980026, 0x8F180000, '-', 'R_MIPS_LO16:D_800BE9E4'),
    (0x50, 0x8F390000, 0x90990026, 'R_MIPS_LO16:D_800BE9E4', '-'))
RAW_SHA256 = '884e91589580a1850a9a8d67fd2aaecfb4add9f61d38ce2bcabde53c974c2464'
RELOCATIONS = {24: [('R_MIPS_HI16', 'D_800BE9E4')], 28: [('R_MIPS_LO16', 'D_800BE9E4')],
    72: [('R_MIPS_HI16', 'D_800BE9E4')], 80: [('R_MIPS_LO16', 'D_800BE9E4')]}


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown packed-scale words or relocations')
    data = bytearray(raw)
    for offset, expected, replacement, _, _ in GUARDS:
        if struct.unpack_from('>I', data, offset)[0] != expected:
            raise ValueError('Changed packed-scale scheduling site')
        struct.pack_into('>I', data, offset, replacement)
    moved = dict(relocations)
    moved[76] = moved.pop(80)
    return bytes(data), moved


def guard_manifest(before):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown packed-scale guard predecessor')
    rows = ''.join('%s,%s,0x%X,0x%08X,0x%08X,%s,%s,Preserve closed fade-product operand loads and commutative multiply,,,false\n' %
        (OWNER, FUNCTION, *row) for row in GUARDS)
    return before + rows.encode()


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed packed-scale predecessor')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed packed-scale baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed packed-scale fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516ECAC() {\n    return 0;\n}':
        raise ValueError('Unknown packed-scale placeholder')
    return before[:lo] + selected.rstrip() + before[hi:]


def measure(root, out, label='selected', selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, fs = build.link_owner(root, out, obj, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>47I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (WORDS, 3, ''):
        raise ValueError('Changed packed-scale reconstruction: ' + repr(row))
    raw, fs, rel = parse_object(obj)
    f = fs[FUNCTION]
    normalize(raw[f['value']:f['value'] + f['size']],
        {p - f['value']: r for p, r in rel.items() if f['value'] <= p < f['value'] + f['size']})
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guard_manifest((out / 'before-guards').read_bytes()))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=manifest))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, fs = build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    guarded = list(struct.unpack_from('>47I', data, f['value']))
    truth = list(struct.unpack_from('>47I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if f['size'] != WORDS * 4 or guarded != truth:
        raise ValueError('Packed-scale production padder differs')
    row.update(guards=3, frame=0, direct_C=False, guarded_differences=0)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, guarded, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--screen', action='store_true')
    args = parser.parse_args()
    root = Path.cwd()
    out = root / BUILD
    if args.screen:
        expression = 'scale = (s32)((u32)((record[0x2C] << 8) | record[0x2D]) * (u32)value) >> 7;'
        variants = {
            'split': INITIAL.replace(expression, 'scale = (record[0x2C] << 8) | record[0x2D];\n'
                '    scale = (s32)((u32)scale * (u32)value);\n    scale >>= 7;'),
            'split-base': INITIAL.replace('    s32 scale;', '    s32 scale;\n    s32 base;').replace(expression,
                'base = (record[0x2C] << 8) | record[0x2D];\n'
                '    scale = (s32)((u32)base * (u32)value);\n    scale >>= 7;'),
            'split-all': INITIAL.replace('    s32 scale;', '    s32 scale;\n    s32 base, product;').replace(expression,
                'base = record[0x2C];\n    base = (base << 8) | record[0x2D];\n'
                '    product = (u32)base * (u32)value;\n    scale = product >> 7;'),
            'delta-local': INITIAL.replace('    s32 scale;', '    s32 scale;\n    u32 delta;').replace(
                '        value = (s32)((u32)value - (u32)D_800BE9E4 * record[0x26]);',
                '        delta = D_800BE9E4;\n        value = (s32)((u32)value - delta * record[0x26]);'),
        }
        split = variants['split-base']
        for label, expression in {
            'or-reversed': '(record[0x2D]) | (record[0x2C] << 8)',
            'addition': '(record[0x2C] << 8) + record[0x2D]',
            'addition-reversed': 'record[0x2D] + (record[0x2C] << 8)',
        }.items():
            variants[label] = split.replace('(record[0x2C] << 8) | record[0x2D]', expression)
        variants['two-byte-locals'] = split.replace('    s32 base;', '    s32 base, high, low;').replace(
            '    base = (record[0x2C] << 8) | record[0x2D];',
            '    high = record[0x2C];\n    low = record[0x2D];\n    base = (high << 8) | low;')
        for label, selected in list(variants.items()):
            if label != 'delta-local':
                variants[label + '-delta-reversed'] = selected.replace(
                    '(u32)D_800BE9E4 * record[0x26]', 'record[0x26] * (u32)D_800BE9E4')
        old = '        value = (s32)((u32)value - (u32)D_800BE9E4 * record[0x26]);'
        for label, declaration, expression in (
                ('decrement', 'u32 decrement;', 'decrement = (u32)D_800BE9E4 * record[0x26];\n        value = (s32)((u32)value - decrement);'),
                ('signed-decrement', 's32 decrement;', 'decrement = (u32)D_800BE9E4 * record[0x26];\n        value = (s32)((u32)value - (u32)decrement);'),
                ('signed-delta', 's32 delta;', 'delta = D_800BE9E4;\n        value = (s32)((u32)value - (u32)delta * record[0x26]);'),
                ('unsigned-result', 'u32 remaining;', 'remaining = (u32)value - (u32)D_800BE9E4 * record[0x26];\n        value = remaining;'),
                ('speed-local', 's32 speed;', 'speed = record[0x26];\n        value = (s32)((u32)value - (u32)D_800BE9E4 * (u32)speed);')):
            variants[label] = SELECTED.replace('    s32 base;', '    s32 base;\n    ' + declaration).replace(old, '        ' + expression)
        for label, selected in variants.items():
            row = measure(root, out, label, selected)[-1]
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'diagnostics')}))
        return
    result = qualify(root, out) if args.qualify else measure(root, out)
    print(json.dumps(result[-1], indent=2))


if __name__ == '__main__':
    main()
