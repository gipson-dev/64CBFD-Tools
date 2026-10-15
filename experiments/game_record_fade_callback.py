"""Recover the record fade/completion callback with full-word clamp lifetime."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_paired_record_event_match as previous
from tools.tests import paired_record_event_match_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-record-fade-callback'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516F9C4', 0x1516F9C4, 0x19CE74, 49
STEP, TABLE, CALLER, REMOVE = 0x800BE9E4, 0x8008CBA0, 0x1516D678, 0x1516972C
MOVE, SCALE = 0x1516F864, 0x1516F984
PATHS, BASELINE = previous.PATHS, dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
SELECTED = '''/* Keep the clamp value full-width; narrow only the stored record fields. */
s32 func_1516F9C4(u8 *record) {
    s32 extent;
    s32 value = record[0x1F];

    if (record[0x24] != 0) {
        if (value != 255) {
            value = (s32)((u32)value + ((u32)D_800BE9E4 << 4));
            if (value >= 256) {
                value = 255;
            }
            record[0x1F] = value;
        }
    } else {
        if (value != 0) {
            value = (s32)((u32)value - ((u32)D_800BE9E4 << 3));
            if (value < 0) {
                value = 0;
            }
            record[0x1F] = value;
        }
        extent = (s32)((u32)value << 9) >> 8;
        *(s16 *)(record + 0x16) = extent;
        *(s16 *)(record + 0x14) = extent;
    }
    if (record[0x24] == 0 && value == 0) {
        return 1;
    }
    func_1516F864(record);
    func_1516F984(record, 0xF0);
    return 0;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed fade-callback predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed fade-callback baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed fade-callback fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516F9C4() {\n    return 0;\n}':
        raise ValueError('Unknown fade-callback placeholder')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label='qualified', selected=None):
    selected = SELECTED if selected is None else selected
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>49I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, candidate_sha256=hashlib.sha256(selected.encode()).hexdigest(), words=len(words),
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        frame=(0x10000 - (words[0] & 65535)) & 65535, diagnostics=diagnostics,
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (49, 0, 24, ''):
        raise ValueError('Fade callback is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 196 or list(struct.unpack_from('>49I', data, f['value'])) != words:
        raise ValueError('Fade-callback production padding differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown fade-callback predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown fade-callback predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 196)
    result[offset:offset + 196] = rom[ROM:ROM + 196]
    struct.pack_into('>I', result, row[0] + 8, 196)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = measure(root, root / BUILD) if args.measure else qualify(root, root / BUILD)
    print(json.dumps(result[-1], indent=2))
