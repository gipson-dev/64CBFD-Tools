"""Recover the actor-type-gated preset with its complete four-input o32 packet."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_packed_color_match as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import packed_color_match_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-actor-type-preset'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516ED68', 0x1516ED68, 0x19C218, 91
CALLEE, TABLE = 0x1516D99C, 0x800CC2D4
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
SELECTED = '''/* Create the type-0x3A actor preset; preserve word arguments and the low flag byte. */
void func_1516ED68(s32 arg0, s32 arg1, s32 arg2, s32 arg3) {
    if (D_800CC2D4[(u32)arg0 * 0x32C] == 0x3A) {
        func_1516D99C(
            5, 0, 0, 4, 0, 0xFF, 0xFF, 0xFF,
            0, 0, 0, 0, 2, 0, 0, 0,
            0, 0, 0, 8, 0, 0, 0, 0,
            0, 0, 0, 0x124, 0x124, 0, 0, arg1,
            0, 0, arg0, 0xC, 0, 0, 0x81, 2,
            0, 1, 0, 0, 0, 5, 0, (u8)arg2, arg3);
    }
}
'''
INITIAL = SELECTED
SELECTED = INITIAL.replace('    if (D_800CC2D4[(u32)arg0 * 0x32C] == 0x3A) {',
    '    u8 type = D_800CC2D4[(u32)arg0 * 0x32C];\n\n    if (type == 0x3A) {')


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed actor-preset predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed actor-preset baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed actor-preset fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516ED68() {\n    return 0;\n}':
        raise ValueError('Unknown actor-preset placeholder')
    return (before[:lo] + selected.rstrip() + before[hi:]).replace('extern s32 D_800BE9E4;',
        'extern s32 D_800BE9E4;\nextern u8 D_800CC2D4[];', 1)


def measure(root, out, label, selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>91I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(index * 4, '0x%08X' % actual, '0x%08X' % expected)
            for index, (actual, expected) in enumerate(zip(words, truth)) if actual != expected])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (91, 0, ''):
        raise ValueError('Actor preset is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 364 or list(struct.unpack_from('>91I', data, f['value'])) != words:
        raise ValueError('Actor-preset production padder differs')
    row.update(guards_added=0, frame=208, direct_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def candidates():
    return dict(expression=INITIAL, byte_type=SELECTED,
        signed_word_type=SELECTED.replace('u8 type =', 's32 type ='),
        unsigned_word_type=SELECTED.replace('u8 type =', 'u32 type ='))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    args = parser.parse_args()
    root = Path.cwd()
    if args.screen:
        for name, body in candidates().items():
            row = measure(root, root / BUILD, name, body)[-1]
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'diagnostics')}), flush=True)
        return
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
