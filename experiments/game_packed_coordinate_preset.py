"""Recover the packed-coordinate record preset with its complete o32 call packet."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_packed_record_scale as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import packed_record_scale_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-packed-coordinate-preset'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516E778', 0x1516E778, 0x19BC28, 85
CALLEE = 0x1516D99C
PATHS = dict(previous.PATHS, caller_original='conker/asm/50D80.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    caller_original='58dec15b45859c1dface2fc227f074871296eb4884e6499e4cfee37b8389111c')
SELECTED = '''/* Split packed signed coordinates; forward arg1/arg4 as words and two low bytes. */
void func_1516E778(u32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4) {
    func_1516D99C(
        (s16)(arg0 >> 16), (s16)arg0, 0, (u8)arg2, 0, 0, 0, 0,
        0, 0, 0, 0, 4, 0, 0, 0,
        0xFF, 0xFF, 0xFF, 0, 8, 8, 1, 0,
        0, 0, 0, 0x155, 0x155, 0x155, 0x155, arg1,
        0x1E, 0, 0xFF, 0x28, 0x168, 0x18, 0x21, 4,
        0, 1, 0, 0, 0, 0, 0, (u8)arg3, arg4);
}
'''
INITIAL = SELECTED
SELECTED = INITIAL.replace('(s16)(arg0 >> 16), (s16)arg0',
    '(s16)(arg0 >> 16), (s32)(arg0 << 16) >> 16')


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed coordinate-preset predecessor')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed coordinate-preset baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed coordinate-preset fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516E778() {\n    return 0;\n}':
        raise ValueError('Unknown coordinate-preset placeholder')
    return before[:lo] + selected.rstrip() + before[hi:]


def measure(root, out, label, selected):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, fs = build.link_owner(root, out, obj, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>85I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified', SELECTED)
    if (row['words'], row['differences'], row['diagnostics']) != (85, 0, ''):
        raise ValueError('Coordinate preset is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, fs = build.link_owner(root, out, padded, OWNER)
    f = fs[FUNCTION]
    if f['size'] != 340 or list(struct.unpack_from('>85I', data, f['value'])) != words:
        raise ValueError('Coordinate-preset production padder differs')
    row.update(guards_added=0, frame=208, direct_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def candidates():
    call = '    func_1516D99C('
    coords = '(s16)(arg0 >> 16), (s16)arg0'
    variants = {
        'shift-low': SELECTED,
        'packed-word': INITIAL.replace(call, '    u32 packed = arg0;\n' + call).replace(coords, '(s16)(packed >> 16), (s16)packed'),
        'signed-packed': INITIAL.replace(call, '    s32 packed = arg0;\n' + call).replace(coords, '(s16)((u32)packed >> 16), (s16)packed'),
        'word-locals': INITIAL.replace(call, '    s32 x = (s16)(arg0 >> 16);\n    s32 y = (s16)arg0;\n' + call).replace(coords, 'x, y'),
        'short-locals': INITIAL.replace(call, '    s16 x = arg0 >> 16;\n    s16 y = arg0;\n' + call).replace(coords, 'x, y'),
        'mutated-packed': INITIAL.replace(call, '    s32 x = (s16)(arg0 >> 16);\n    arg0 <<= 16;\n' + call).replace(coords, 'x, (s32)arg0 >> 16'),
        'high-word-local': INITIAL.replace(call, '    s32 x = arg0 >> 16;\n' + call).replace(coords, '(s16)x, (s32)(arg0 << 16) >> 16'),
        'signed-formal': INITIAL.replace('u32 arg0', 's32 arg0').replace(coords, '(s16)((u32)arg0 >> 16), (s16)arg0'),
    }
    shifted = SELECTED
    variants.update({
        'signed-shift-local': shifted.replace(call, '    s32 packed = arg0;\n' + call).replace(
            '(s16)(arg0 >> 16), (s32)(arg0 << 16) >> 16', '(s16)((u32)packed >> 16), (s32)((u32)packed << 16) >> 16'),
        'reused-second-formal': shifted.replace(call, '    s32 saved = arg1;\n    arg1 = arg0;\n' + call).replace(
            '(s16)(arg0 >> 16), (s32)(arg0 << 16) >> 16', '(s16)((u32)arg1 >> 16), (s32)((u32)arg1 << 16) >> 16').replace('0x155, arg1,', '0x155, saved,'),
        'reused-second-local': shifted.replace(call, '    u32 packed = arg0;\n    s32 saved = arg1;\n' + call).replace(
            '(s16)(arg0 >> 16), (s32)(arg0 << 16) >> 16', '(s16)(packed >> 16), (s32)(packed << 16) >> 16').replace('0x155, arg1,', '0x155, saved,'),
        'unsigned-formals': shifted.replace('s32 arg1, s32 arg2, s32 arg3, s32 arg4', 'u32 arg1, u32 arg2, u32 arg3, u32 arg4'),
        'signed-formal-shift': shifted.replace('u32 arg0', 's32 arg0').replace('arg0 >> 16', '(u32)arg0 >> 16').replace('arg0 << 16', '(u32)arg0 << 16'),
        'no-first-cast': shifted.replace('(s16)(arg0 >> 16)', 'arg0 >> 16'),
    })
    return variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path.cwd()
    out = root / BUILD
    freeze(root, out)
    if args.screen:
        for label, body in candidates().items():
            row = measure(root, out, label, body)[-1]
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'diagnostics')}), flush=True)
        return
    donor = build.body((out / 'before-archive_preset').read_text(), FUNCTION)
    archived = measure(root, out, 'archived', donor)[-1]
    selected = qualify(root, out)[-1] if args.qualify else measure(root, out, 'selected', SELECTED)[-1]
    selected['installable'] = selected['words'] == WORDS and selected['differences'] == 0 and not selected['diagnostics']
    print(json.dumps(dict(archived=archived, selected=selected), indent=2))


if __name__ == '__main__':
    main()
