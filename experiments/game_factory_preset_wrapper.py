"""Qualify the preset-0x2D wrapper without changing its opaque factory."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_rotation_matrix_leaf as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import rotation_matrix_leaf_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-factory-preset-wrapper'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516F1C0', 0x1516F1C0, 0x19C670, 78
CALLEE = 0x1516D99C
PATHS = dict(previous.PATHS,
    preset_owner='conker/src/game/generated_19A8B0.c',
    preset_original='conker/asm/19A8B0.s',
    archive_preset='../Another Source/CBFD-Recompiled/conker/conker/src/game/game_19A8B0.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    preset_owner='7d957be8f30ba049c616973d21c415cfce2e8afd3b5e9ba4ba6dccc387877c2a',
    preset_original='5c7a87eb09e62c9f0914c830d22351f539bdc4646c2b05ac37deb4266018f737',
    archive_preset='2455c2297c4ef88ee28886a0e7b47e60436570d75fd70128bc9b2ff9fed20df2')
SELECTED = '''/* Preset 0x2D: forward arg0/arg1/arg3 as words; only arg2 narrows. */
void func_1516F1C0(s32 arg0, s32 arg1, s32 arg2, s32 arg3) {
    func_1516D99C(
        2, 0, 0, 0x2D, 0, 0xFF, 0xFF, 0xFF,
        0, 0, 0, 0, 2, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0, 0,
        0, 0, 0, 0x50, 0x50, 0, 0, arg1,
        0xA, 0xA, arg0, 0x3C, 0, 0, 0x81, 4,
        0, 1, 0, 0, 0, 4, 2, (u8) arg2, arg3);
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed preset-wrapper predecessor')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed preset-wrapper manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed preset-wrapper fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516F1C0() {\n    return 0;\n}':
        raise ValueError('Unknown preset-wrapper placeholder')
    return before[:lo] + selected.rstrip() + before[hi:]


def measure(root, out, label, selected):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    row = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (row['size'] // 4), data, row['value']))
    truth = list(struct.unpack_from('>78I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    result = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth))
        + abs(len(words) - WORDS), diagnostics=diagnostics)
    return obj, words, result


def qualify(root, out):
    obj, words, result = measure(root, out, 'qualified', SELECTED)
    if (result['words'], result['differences'], result['diagnostics']) != (78, 0, ''):
        raise ValueError('Preset wrapper is not a direct match: ' + repr(result))
    padded = emit_padded_assembly(obj, root / PATHS['preset_original'],
        word_patches_path=root / PATHS['guards'], filename=OWNER)
    path = out / 'qualified-padded.s'
    path.write_text(padded)
    output = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(output), str(path)],
        capture_output=True, check=True)
    data, functions = build.link_owner(root, out, output, OWNER)
    row = functions[FUNCTION]
    if row['size'] != 312 or list(struct.unpack_from('>78I', data, row['value'])) != words:
        raise ValueError('Production padded preset wrapper differs')
    (out / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
    return obj, output, words, result


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    donor = build.body((out / 'before-archive_preset').read_text(), FUNCTION)
    _, _, original = measure(root, out, 'archived', donor)
    _, _, _, selected = qualify(root, out)
    print(json.dumps(dict(archived=original, selected=selected)), flush=True)


if __name__ == '__main__':
    main()
