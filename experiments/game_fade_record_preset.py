"""Recover the complete preset-0x1B packet, preserving six physical inputs."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_fade_callback as previous
from tools.tests import record_fade_callback_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-fade-record-preset'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516FA88', 0x1516FA88, 0x19CF38, 81
CALLEE = 0x1516D99C
PATHS, BASELINE = previous.PATHS, dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
SELECTED = '''/* Preset 0x1B: signed coordinates, full-word variant/context, byte flag. */
void func_1516FA88(s16 arg0, s16 arg1, s16 arg2, s32 arg3, s32 arg4, s32 arg5) {
    func_1516D99C(
        arg0, arg1, arg2, 0x1B, 0, 0xFF, 0xFF, 0xFF,
        0, 0xFF, 0xFF, 0xFF, 3, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0x400, 0x400, 0, 0, 2,
        0, 0, 0xFF, 0xF, 0, 0, 9, 0,
        0xFF, 0xA, 0x5A, 5, arg3, 0, 0, (u8)arg4, arg5);
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed fade-preset predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed fade-preset baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed fade-preset fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516FA88() {\n    return 0;\n}':
        raise ValueError('Unknown fade-preset placeholder')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label='qualified', selected=None):
    selected = SELECTED if selected is None else selected
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>81I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, candidate_sha256=hashlib.sha256(selected.encode()).hexdigest(), words=len(words),
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        frame=(0x10000 - (words[0] & 65535)) & 65535, diagnostics=diagnostics,
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (81, 0, 208, ''):
        raise ValueError('Fade preset is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 324 or list(struct.unpack_from('>81I', data, f['value'])) != words:
        raise ValueError('Fade-preset production padding differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown fade-preset predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown fade-preset predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 324)
    result[offset:offset + 324] = rom[ROM:ROM + 324]
    struct.pack_into('>I', result, row[0] + 8, 324)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode())


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
