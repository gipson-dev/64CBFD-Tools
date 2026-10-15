"""Recover the two-random spherical direction writer without uninitialized locals."""
import hashlib
import argparse
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_fade_acceleration as previous
from tools.tests import record_fade_acceleration_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-random-unit-vector'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_15170034', 0x15170034, 0x19D4E4, 41
RANDOM, COSINE, SINE = 0x150ADA20, 0x150489B0, 0x15048A40
PATHS, BASELINE = previous.PATHS, dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
DECLARATIONS = '''s32 func_150ADA20(void);
f32 func_150489B0(u8 angle);
f32 func_15048A40(u8 angle);

'''
SELECTED = '''/* Write a random direction; flag 0x40 restricts the polar-angle range. */
void func_15170034(s32 flags, f32 *x, f32 *y, f32 *z) {
    s32 mask;
    s32 randomWord;
    f32 azimuthCosine;
    f32 radius;
    s32 angle;
    f32 azimuthSine;

    if (flags & 0x40) {
        mask = 0x3F;
    } else {
        mask = 0x7F;
    }
    randomWord = func_150ADA20() & mask;
    angle = randomWord;
    *y = func_150489B0((u8)randomWord);
    radius = func_15048A40((u8)(&angle)[0]);
    randomWord = func_150ADA20() & 0xFF;
    angle = randomWord;
    azimuthCosine = func_150489B0((u8)randomWord);
    azimuthSine = func_15048A40((u8)(&angle)[0]);
    *x = radius * azimuthSine;
    *z = radius * azimuthCosine;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed random-direction predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed random-direction baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed random-direction fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15170034() {\n    return 0;\n}':
        raise ValueError('Unknown random-direction placeholder')
    marker = '/* Non-matching placeholders for the text-only asm slice asm/19A8B0.s. */'
    result = before[:lo] + selected.rstrip() + before[hi:]
    return result.replace(marker, DECLARATIONS + marker, 1)


def measure(root, out, label='qualified', selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>41I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        frame=(0x10000 - (words[0] & 65535)) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (41, 0, 48, ''):
        raise ValueError('Random direction is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 164 or list(struct.unpack_from('>41I', data, f['value'])) != words:
        raise ValueError('Random-direction production padding differs')
    return obj, padded, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown random-direction predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown random-direction predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 164)
    result[offset:offset + 164] = rom[ROM:ROM + 164]
    struct.pack_into('>I', result, row[0] + 8, 164)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode())


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    args = parser.parse_args()
    if args.screen:
        variants = {'selected': SELECTED,
            'reverse-product': SELECTED.replace('*x = radius * azimuthSine;', '*x = azimuthSine * radius;'),
            'sine-first': SELECTED.replace('    f32 azimuthSine;\n', '').replace('    s32 mask;', '    f32 azimuthSine;\n    s32 mask;'),
            'inlined-product': SELECTED.replace('    f32 azimuthSine;\n', '').replace(
                '    azimuthSine = func_15048A40((u8)(&angle)[0]);\n    *x = radius * azimuthSine;',
                '    *x = radius * func_15048A40((u8)(&angle)[0]);')}
        for label, selected in variants.items():
            _, _, row = measure(root, root / BUILD, label, selected)
            print(json.dumps(row), flush=True)
    else:
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
