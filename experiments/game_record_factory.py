"""Recover the 0x4C-byte factory's argument and field widths in its full owner."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from tools.experiments import game_factory_preset_wrapper as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import factory_preset_wrapper_checkpoint as checkpoint
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-record-factory'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516D99C', 0x1516D99C, 0x19AE4C, 125
CALLEE = 0x15167A68
PATHS = dict(previous.PATHS, allocator_owner='conker/src/game_1944C0.c',
    allocator_original='conker/asm/nonmatchings/game_1944C0/func_15167A68.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    allocator_owner='328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b',
    allocator_original='e10b48863a06a3abf7ab49384fc059fbb54f5005fd9d8c7bf716cd687a52a801')
DECLARATION = 'void *func_15167A68(s32, s32, s32, s32, u8, u8);\n'
PARAM_TYPES = ['s16'] * 3 + ['u8'] * 24 + ['s16'] * 4 + ['u16'] + ['u8'] * 4 + ['s16', 'u16', 'u16'] + ['u8'] * 5 + ['s32'] + ['u8'] * 3 + ['s32']
BODY = '''    s32 kind;
    u8 *record;

    if (arg44 != 0) {
        kind = 0x66;
    } else {
        kind = 0x11;
    }
    record = func_15167A68(kind, arg48, 0x4C, 0, arg47, 1);
    if (record != NULL) {
        *(s16 *)(record + 0xE) = arg0;
        *(s16 *)(record + 0x10) = arg1;
        *(s16 *)(record + 0x12) = arg2;
        *(s16 *)(record + 0x14) = arg27;
        *(s16 *)(record + 0x16) = arg28;
        *(s16 *)(record + 0x18) = arg29;
        *(s16 *)(record + 0x1A) = arg30;
        record[0x24] = arg3;
        record[0x25] = arg4;
        record[0x26] = arg5;
        record[0x27] = arg6;
        record[0x28] = arg7;
        record[0x2A] = arg9;
        record[0x2B] = arg10;
        record[0x2C] = arg11;
        record[0x29] = arg8;
        record[0x2D] = arg12;
        record[0x2E] = arg13;
        record[0x2F] = arg14;
        record[0x30] = arg15;
        record[0x31] = arg16;
        record[0x32] = arg17;
        record[0x33] = arg18;
        record[0x34] = arg19;
        record[0x35] = arg20;
        record[0x36] = arg21;
        record[0x37] = arg22;
        record[0x38] = arg23;
        record[0x39] = arg24;
        record[0x3A] = arg25;
        *(u16 *)(record + 0x20) = arg31;
        record[0x3C] = arg31;
        record[0x3B] = arg26;
        record[0x3D] = arg32;
        record[0x3E] = arg33;
        record[0x3F] = arg34;
        record[0x40] = arg35;
        *(s16 *)(record + 0x1C) = arg36;
        *(u16 *)(record + 0x1E) = arg37;
        *(u16 *)(record + 0x22) = arg38;
        record[0x42] = 0;
        record[0x41] = arg39;
        record[0x43] = arg40;
        if (arg44 != 0 && arg41 >= 4) {
            arg41 = 3;
        }
        record[0x44] = arg41;
        record[0x45] = arg42;
        record[0x46] = arg43;
        record[0x47] = arg45;
        record[0x48] = arg46;
    }
'''


def candidate(types, body=BODY):
    params = [t + ' arg%d' % i for i, t in enumerate(types)]
    lines = [', '.join(params[i:i + 6]) for i in range(0, len(params), 6)]
    return 'void ' + FUNCTION + '(\n    ' + ',\n    '.join(lines) + ') {\n' + body + '}\n'


SELECTED_TYPES = PARAM_TYPES.copy()
SELECTED_TYPES[47] = 's32'
SELECTED = ('/* Initialize a packed 0x4C-byte record; cap arg41 for the alternate kind.\n'
    ' * Six expected-word guards preserve two independent load/store schedules. */\n' +
    candidate(SELECTED_TYPES, BODY.replace('    record = func_15167A68(',
        '    /* The flag stays a word at the caller ABI; read its big-endian low byte. */\n    record = func_15167A68(').replace(
        'arg47, 1)', '((u8 *)&arg47)[3], 1)')))
GUARDS = ((0x144, 0xA4430020, 0x93B9008B), (0x148, 0xA043003C, 0xA4430020),
    (0x14C, 0x93B9008B, 0xA043003C), (0x188, 0xA0400042, 0xA44E0022),
    (0x18C, 0xA44E0022, 0x93AF00BF), (0x190, 0x93AF00BF, 0xA0400042))
RAW_SHA256 = 'd3401c6266bffc4ddc7687862a21a2e645e5ca254e38330072c5258e843cc847'
RELOCATIONS = {68: [('R_MIPS_26', 'func_15167A68')]}


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown factory words or relocations')
    words = list(struct.unpack('>125I', raw))
    for offset, expected, replacement in GUARDS:
        if words[offset // 4] != expected:
            raise ValueError('Changed factory scheduling site')
        words[offset // 4] = replacement
    return words


def guard_manifest(before):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown factory guard predecessor')
    rows = ''.join('%s,%s,0x%X,0x%08X,0x%08X,-,-,Preserve two closed independent factory load and store schedules,,,false\n' %
        (OWNER, FUNCTION, offset, expected, replacement) for offset, expected, replacement in GUARDS)
    return before + rows.encode()


def home_body():
    def access(match):
        i = int(match[1])
        t = PARAM_TYPES[i]
        return '((%s *)&arg%d)[%d]' % (t, i, 3 if t == 'u8' else 1) if t != 's32' else match[0]
    return re.sub(r'\barg(\d+)\b', access, BODY)


def scheduled_body():
    return BODY.replace('    u8 *record;\n', '    u8 *record;\n    u16 shared;\n    u8 byte26, byte39;\n').replace(
        'arg47, 1)', '((u8 *)&arg47)[3], 1)').replace(
        '        *(u16 *)(record + 0x20) = arg31;\n        record[0x3C] = arg31;\n        record[0x3B] = arg26;',
        '        shared = arg31;\n        byte26 = arg26;\n        *(u16 *)(record + 0x20) = shared;\n        record[0x3C] = shared;\n        record[0x3B] = byte26;').replace(
        '        record[0x42] = 0;\n        record[0x41] = arg39;',
        '        byte39 = arg39;\n        record[0x42] = 0;\n        record[0x41] = byte39;')


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed record-factory predecessor')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed record-factory manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed record-factory fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516D99C() {\n    return 0;\n}':
        raise ValueError('Unknown record-factory placeholder')
    return (before[:lo] + selected.rstrip() + before[hi:]).replace('extern s32 D_800BE9E4;\n',
        'extern s32 D_800BE9E4;\n\n' + DECLARATION, 1)


def measure(root, out, label, selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    result, bodies = dict(label=label, diagnostics=diagnostics), {}
    for name, entry, offset, count in ((FUNCTION, ENTRY, ROM, WORDS),
            (previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS)):
        row = functions[name]
        words = list(struct.unpack_from('>%dI' % (row['size'] // 4), data, row['value']))
        truth = list(struct.unpack_from('>%dI' % count, rom, offset))
        result[name] = dict(words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - count),
            different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
        bodies[name] = words
    (out / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    return obj, bodies, result


def pad(root, out, obj, label, guards):
    manifest = out / (label + '-guards.csv')
    manifest.write_bytes(guards)
    text = emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest)
    path = out / (label + '.s')
    path.write_text(text)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        capture_output=True, check=True)
    return path.with_suffix('.o')


def qualify(root, out):
    obj, bodies, row = measure(root, out, 'qualified')
    if row['diagnostics'] or (row[FUNCTION]['words'], row[FUNCTION]['differences'],
            row[previous.FUNCTION]['words'], row[previous.FUNCTION]['differences']) != (125, 6, 78, 0):
        raise ValueError('Changed factory/caller reconstruction: ' + repr(row))
    data, fs, rel = parse_object(obj)
    f = fs[FUNCTION]
    raw = data[f['value']:f['value'] + f['size']]
    relative = {p - f['value']: r for p, r in rel.items() if f['value'] <= p < f['value'] + f['size']}
    normalize(raw, relative)
    expected = bodies[FUNCTION].copy()
    for offset, old, new in GUARDS:
        if expected[offset // 4] != old:
            raise ValueError('Unknown linked scheduling site')
        expected[offset // 4] = new
    padded = pad(root, out, obj, 'qualified-padded', guard_manifest((out / 'before-guards').read_bytes()))
    linked, fs = build.link_owner(root, out, padded, OWNER)
    words = list(struct.unpack_from('>125I', linked, fs[FUNCTION]['value']))
    truth = list(struct.unpack_from('>125I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if fs[FUNCTION]['size'] != 500 or words != truth or words != expected:
        raise ValueError('Guarded factory slot differs')
    row.update(linked_differences=0, guards=6, raw_differences=6, frame=32,
        caller_words=78, caller_differences=0, not_direct_unguarded_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, bodies[FUNCTION], words, row


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    for label, types in (('words', ['s32'] * 49), ('narrow', PARAM_TYPES)):
        _, _, result = measure(root, out, label, candidate(types))
        print(json.dumps(result), flush=True)
    body = re.sub(r'= arg(\d+);', lambda m: '= (%s) arg%s;' % (PARAM_TYPES[int(m[1])], m[1]), BODY)
    types = ['s32'] * 49
    types[41] = 'u8'
    for label, selected in (('casts', candidate(types, body)), ('homes', candidate(['s32'] * 49, home_body()))):
        _, _, result = measure(root, out, label, selected)
        print(json.dumps(result), flush=True)
    types = PARAM_TYPES.copy()
    types[47] = 's32'
    for label, body in (('wire-byte', BODY.replace('arg47, 1)', '((u8 *)&arg47)[3], 1)')),
            ('scheduled', scheduled_body())):
        _, _, result = measure(root, out, label, candidate(types, body))
        print(json.dumps(result), flush=True)
    _, _, _, _, row = qualify(root, out)
    print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
