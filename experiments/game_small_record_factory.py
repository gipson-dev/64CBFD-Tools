"""Recover the packed 0x34-byte factory and its optional position/scale binding."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_factory as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import record_factory_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-small-record-factory'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516D4E8', 0x1516D4E8, 0x19A998, 100
ALLOCATOR, SECONDARY = 0x15167A68, 0x150448D0
PATHS = dict(previous.PATHS, secondary_owner='conker/src/game/generated_71820.c',
    secondary_original='conker/asm/71820.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    secondary_owner='1654f635094ebfe1cf465dd69945a4b747d422ec5e090881a8ba44e6da876fe4',
    secondary_original='dad3e6265a0b9d616da5b73bb78f2484995251e8ad6a5d8788fd5251fd078585')
DECLARATION = '''struct PositionScaleRecord71820;
struct PositionScaleRecord71820 *func_150448D0(s32, s32, s32, s32, s32, s32,
                                               s32, s16 *, s16 *);
'''
PARAM_TYPES = ['s16'] * 3 + ['u8'] * 20 + ['s16', 's16', 'u8', 's16', 's32', 's32', 'u8', 's32']
BODY = '''    s32 kind;
    u8 *record;

    if (arg27 != 0) {
        kind = 0x67;
    } else {
        kind = 0x12;
    }
    record = func_15167A68(kind, arg30, 0x34, 0, arg29, 1);
    if (record != NULL) {
        *(s16 *)(record + 0xE) = arg0;
        *(s16 *)(record + 0x10) = arg1;
        *(s16 *)(record + 0x12) = arg2;
        record[0x1A] = arg3;
        record[0x1B] = arg4;
        record[0x1C] = arg5;
        record[0x1D] = arg6;
        record[0x1E] = arg7;
        record[0x1F] = arg8;
        record[0x20] = arg9;
        record[0x21] = arg10;
        record[0x22] = arg11;
        record[0x23] = arg12;
        *(s16 *)(record + 0x14) = arg23;
        *(s16 *)(record + 0x16) = arg24;
        record[0x24] = arg25;
        record[0x25] = 0;
        *(s16 *)(record + 0x18) = arg26;
        record[0x26] = arg13;
        record[0x27] = arg14;
        record[0x28] = arg15;
        record[0x29] = arg16;
        record[0x2A] = arg17;
        record[0x2B] = arg18;
        record[0x2C] = arg19;
        record[0x2D] = arg20;
        record[0x2E] = arg21;
        record[0x2F] = arg22;
        if (arg28 != 0) {
            *(struct PositionScaleRecord71820 **)(record + 0x30) = func_150448D0(
                -1, 0, arg28, 0x14, 0x14, 0x14, 0,
                (s16 *)(record + 0xE), (s16 *)(record + 0x14));
            return;
        }
        *(struct PositionScaleRecord71820 **)(record + 0x30) = NULL;
    }
'''


def candidate(types=PARAM_TYPES, body=BODY):
    params = [t + ' arg%d' % i for i, t in enumerate(types)]
    lines = [', '.join(params[i:i + 6]) for i in range(0, len(params), 6)]
    return 'void ' + FUNCTION + '(\n    ' + ',\n    '.join(lines) + ') {\n' + body + '}\n'


ORDERED_BODY = BODY.replace('        record[0x25] = 0;\n        *(s16 *)(record + 0x18) = arg26;',
    '        *(s16 *)(record + 0x18) = arg26;\n        record[0x25] = 0;')
SELECTED = ('/* Initialize a packed record and optionally bind its position/scale fields. */\n' +
    candidate(body=ORDERED_BODY.replace('    s32 kind;\n    u8 *record;', '    u8 *record;\n    s32 kind;')))


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed small-factory predecessor')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed small-factory manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed small-factory fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516D4E8() {\n    return 0;\n}':
        raise ValueError('Unknown small-factory placeholder')
    return (before[:lo] + selected.rstrip() + before[hi:]).replace(previous.DECLARATION,
        previous.DECLARATION + DECLARATION, 1)


def measure(root, out, label, selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, fs = build.link_owner(root, out, obj, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>100I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (100, 0, ''):
        raise ValueError('Small factory is not a direct match: ' + repr(row))
    text = emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=root / PATHS['guards'])
    path = out / 'qualified-padded.s'
    path.write_text(text)
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], capture_output=True, check=True)
    data, fs = build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    if f['size'] != 400 or list(struct.unpack_from('>100I', data, f['value'])) != words:
        raise ValueError('Small factory production padder differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    _, _, row = measure(root, out, 'corrected')
    print(json.dumps(row), flush=True)
    _, _, row = measure(root, out, 'words', candidate(['s32'] * 31))
    print(json.dumps(row), flush=True)
    forms = {
        'saved-record': BODY.replace('    u8 *record;', '    u8 *record;\n    u8 *savedRecord;').replace(
            '        if (arg28 != 0) {', '        if (arg28 != 0) {\n            savedRecord = record;').replace(
            '*(struct PositionScaleRecord71820 **)(record + 0x30) = func_',
            '*(struct PositionScaleRecord71820 **)(savedRecord + 0x30) = func_'),
        'clear-after-half': BODY.replace('        record[0x25] = 0;\n        *(s16 *)(record + 0x18) = arg26;',
            '        *(s16 *)(record + 0x18) = arg26;\n        record[0x25] = 0;'),
        'named-binding': BODY.replace('    u8 *record;', '    u8 *record;\n    struct PositionScaleRecord71820 *binding;').replace(
            '*(struct PositionScaleRecord71820 **)(record + 0x30) = func_', 'binding = func_').replace(
            '(s16 *)(record + 0xE), (s16 *)(record + 0x14));\n            return;',
            '(s16 *)(record + 0xE), (s16 *)(record + 0x14));\n            *(struct PositionScaleRecord71820 **)(record + 0x30) = binding;\n            return;'),
    }
    for label, body in forms.items():
        _, _, row = measure(root, out, label, candidate(body=body))
        print(json.dumps(row), flush=True)
    forms = {'record-first': ORDERED_BODY.replace('    s32 kind;\n    u8 *record;', '    u8 *record;\n    s32 kind;')}
    forms.update({'kind-' + t: ORDERED_BODY.replace('s32 kind;', t + ' kind;') for t in ('u8', 'u16', 'u32')})
    forms['register-record'] = ORDERED_BODY.replace('    u8 *record;', '    register u8 *record;')
    for label, body in forms.items():
        _, _, row = measure(root, out, label, candidate(body=body))
        print(json.dumps(row), flush=True)
    _, _, _, row = qualify(root, out)
    print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
