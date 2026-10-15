"""Recover both complete factory packets with the original input widths."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_table_fade_match as previous
from tools.tests import table_fade_match_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-dual-factory-preset-complete-callers'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516F2F8', 0x1516F2F8, 0x19C7A8, 148
CALLEE = 0x1516D99C
PATHS = dict(previous.PATHS, dual_caller_owner='conker/src/game/generated_50D80.c',
    secondary_caller_owner='conker/src/game_981E0.c',
    secondary_caller_original='conker/asm/nonmatchings/game_981E0/func_1506DE84.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    dual_caller_owner='b24a3bfada6d6003f33b080e1bea3c5f328d1c829e70dd1ab5b067cdaac6e318',
    secondary_caller_owner='e83baa9f46721ba0cdfae136976b6f4d36c1945b75a33998d212250dc7e2b9bb',
    secondary_caller_original='e2cfb7adb31422b51fcb0ea75175e260a158c37c8cde7bc07f86c629cccc0bd6')
build = previous.build
SELECTED = '''/* Preset 0x2B twice: snapshot the first input byte; retain word forwards. */
void func_1516F2F8(s32 arg0, s32 arg1, s32 arg2, s32 arg3, u8 arg4, s32 arg5) {
    s32 firstType;

    firstType = (u8)arg0;
    func_1516D99C(
        3, 0, 0, 0x2B, 0, 0xFF, 0xFF, 0xFF,
        0, 0, 0, 0, 2, 0, 0, 0,
        0, 0, 0, 2, 0, 0, 0, 0,
        0, 0, 0, 0x50, 0x50, 0, 0, arg1,
        4, 4, firstType, 0x10, 0, 0, 0x81, 4,
        0, 1, 0, 0, 0, 1, 0, (u8)arg4, arg5);
    func_1516D99C(
        3, 0, 0, 0x2B, 0, 0xFF, 0xFF, 0xFF,
        0, 0, 0, 0, 2, 0, 0, 0,
        0, 0, 0, 3, 0, 0, 0, 0,
        0, 0, 0, 0x50, 0x50, 0, 0, 7,
        4, 4, firstType, arg2, 0, 0, 0x81, 5,
        0, 1, 0, 0, 0, 1, arg3, (u8)arg4, arg5);
}
'''
INITIAL = SELECTED


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed dual-preset predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed dual-preset baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed dual-preset fixture: ' + key)


def recovered_owner(before, selected=None):
    selected = SELECTED if selected is None else selected
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516F2F8() {\n    return 0;\n}':
        raise ValueError('Unknown dual-preset placeholder')
    return before[:lo] + selected.rstrip() + before[hi:]


def measure(root, out, label, selected=None):
    selected = SELECTED if selected is None else selected
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>148I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        frame=(0x10000 - (words[0] & 65535)) & 65535, diagnostics=diagnostics,
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def candidates():
    wide = INITIAL.replace('u8 arg4,', 's32 arg4,')
    result = dict(initial=INITIAL,
        wide_fifth=wide,
        fifth_mask_second=wide.replace('arg3, (u8)arg4, arg5', 'arg3, arg4 & 0xFF, arg5'),
        fifth_mask_first=wide.replace('1, 0, (u8)arg4, arg5', '1, 0, arg4 & 0xFF, arg5'),
        fifth_mask_both=wide.replace('(u8)arg4', 'arg4 & 0xFF'),
        fifth_address_second=wide.replace('arg3, (u8)arg4', 'arg3, (u8)*(&arg4)'),
        fifth_address_first=wide.replace('1, 0, (u8)arg4', '1, 0, (u8)*(&arg4)'),
        fifth_address_both=wide.replace('(u8)arg4', '(u8)*(&arg4)'),
        fifth_signed_second=wide.replace('arg3, (u8)arg4', 'arg3, (s32)(u8)arg4'),
        fifth_signed_first=wide.replace('1, 0, (u8)arg4', '1, 0, (s32)(u8)arg4'),
        fifth_unsigned=wide.replace('s32 arg4,', 'u32 arg4,'),
        register_type=wide.replace('s32 firstType;', 'register s32 firstType;'),
        inline_snapshot=wide.replace('    firstType = (u8)arg0;\n', '').replace(
            '4, 4, firstType, 0x10', '4, 4, (firstType = (u8)arg0), 0x10'),
        word_snapshot=wide.replace('firstType = (u8)arg0;', 'firstType = arg0;').replace('4, 4, firstType,', '4, 4, (u8)firstType,'),
        fifth_shift_second=wide.replace('arg3, (u8)arg4', 'arg3, ((u32)arg4 << 24) >> 24'),
        fifth_index_second=wide.replace('arg3, (u8)arg4', 'arg3, (u8)(&arg4)[0]'),
        implicit_fifth=INITIAL.replace('(u8)arg4', 'arg4'),
        byte_first=INITIAL.replace('s32 arg0,', 'u8 arg0,').replace('firstType = (u8)arg0;', 'firstType = arg0;').replace('(u8)arg4', 'arg4'),
        assigned_first=INITIAL.replace('    s32 firstType;\n\n    firstType = (u8)arg0;', '    arg0 = (u8)arg0;').replace('firstType', 'arg0').replace('(u8)arg4', 'arg4'),
        initialized=INITIAL.replace('    s32 firstType;\n\n    firstType = (u8)arg0;', '    s32 firstType = (u8)arg0;'),
        unsigned_type=INITIAL.replace('s32 firstType;', 'u32 firstType;'),
        byte_type=INITIAL.replace('s32 firstType;', 'u8 firstType;'))
    indexed = result['fifth_index_second']
    result['indexed_snapshot_second'] = indexed.replace('4, 4, firstType, arg2', '4, 4, (&firstType)[0], arg2')
    result['indexed_snapshot_both'] = indexed.replace('4, 4, firstType,', '4, 4, (&firstType)[0],')
    result['indexed_snapshot_store'] = indexed.replace('firstType = (u8)arg0;', '(&firstType)[0] = (u8)arg0;')
    return result


SELECTED = candidates()['indexed_snapshot_second'].replace(
    '/* Preset 0x2B twice: snapshot the first input byte; retain word forwards. */',
    '/* Preset 0x2B twice: snapshot the first input byte; retain word forwards.\n'
    ' * Indexed reads preserve the live fifth input and saved snapshot home. */')


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (148, 0, 216, ''):
        raise ValueError('Dual preset is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 592 or list(struct.unpack_from('>148I', data, f['value'])) != words:
        raise ValueError('Dual-preset production padding differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--name', choices=candidates())
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    if args.screen:
        for name, body in candidates().items():
            if args.name is not None and name != args.name:
                continue
            row = measure(root, out, name, body)[-1]
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'frame', 'diagnostics')}), flush=True)
        return
    print(json.dumps(qualify(root, out)[-1], indent=2))


if __name__ == '__main__':
    main()
