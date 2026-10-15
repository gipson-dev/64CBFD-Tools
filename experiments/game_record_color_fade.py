"""Recover the leaf fade/extent/color callback with exact packed-field widths."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_fade_record_preset as previous
from tools.tests import fade_record_preset_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-record-color-fade'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516FBCC', 0x1516FBCC, 0x19D07C, 97
STEP, TABLE, CALLER, REMOVE = 0x800BE9E4, 0x8008CBA0, 0x1516D678, 0x1516972C
PATHS, BASELINE = previous.PATHS, dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
SELECTED = '''/* Keep fade math full-width and preserve retail's repeated width test. */
s32 func_1516FBCC(u8 *record) {
    s16 width;
    s32 factor;
    u8 start;
    s32 value;

    value = record[0x1F];
    if (record[0x24] != 0) {
        if (value != 255) {
            value = (s32)((u32)value + ((u32)D_800BE9E4 << 4));
            if (value >= 256) {
                value = 255;
            }
            record[0x1F] = value;
        }
    } else if (value != 0) {
        value = (s32)((u32)value - ((u32)D_800BE9E4 << (record[0x2F] & 31)));
        if (value < 0) {
            value = 0;
        }
        record[0x1F] = value;
    }
    if (record[0x24] == 0 && value == 0) {
        return 1;
    }
    value = *(s8 *)(record + 0x2D);
    value = (s32)((u32)value * (u32)D_800BE9E4);
    *(s16 *)(record + 0x14) = (s16)((u32)(s32)*(s16 *)(record + 0x14) + (u32)value);
    width = *(s16 *)(record + 0x14);
    value = *(s8 *)(record + 0x2E);
    value = (s32)((u32)value * (u32)D_800BE9E4);
    *(s16 *)(record + 0x16) = (s16)((u32)(s32)*(s16 *)(record + 0x16) + (u32)value);
    if (width <= 0 || width <= 0) {
        *(s16 *)(record + 0x16) = 0;
        *(s16 *)(record + 0x14) = *(s16 *)(record + 0x16);
        return 1;
    }
    value = (s32)((u32)record[0x2C] + (u32)D_800BE9E4);
    if (value >= 128) {
        value = 127;
    }
    start = record[0x26];
    factor = (s32)((u32)value << 1);
    record[0x2C] = value;
    record[0x1C] = ((s32)((u32)((s32)record[0x29] - start) * (u32)factor) >> 8) + start;
    start = record[0x27];
    record[0x1D] = ((s32)((u32)((s32)record[0x2A] - start) * (u32)factor) >> 8) + start;
    start = record[0x28];
    record[0x1E] = ((s32)((u32)((s32)record[0x2B] - start) * (u32)factor) >> 8) + start;
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
            raise ValueError('Changed color-fade predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed color-fade baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed color-fade fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516FBCC() {\n    return 0;\n}':
        raise ValueError('Unknown color-fade placeholder')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label='qualified', selected=None):
    selected = SELECTED if selected is None else selected
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>97I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, candidate_sha256=hashlib.sha256(selected.encode()).hexdigest(), words=len(words),
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        frame=((0x10000 - (words[0] & 65535)) & 65535) if words[0] >> 16 == 0x27BD else 0,
        diagnostics=diagnostics,
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def archival_shape(out):
    """Shape diagnostic only; retains archival signed-overflow and shift UB."""
    body = build.body((out / 'before-archive_preset').read_text(), FUNCTION)
    body = body.replace('void *arg0', 'u8 *arg0').replace('u8 var_v0;', 's32 var_v0;')
    for offset, kind in ((0x1F, 'u8'), (0x24, 'u8'), (0x2F, 'u8'), (0x14, 's16'),
            (0x16, 's16'), (0x2C, 'u8'), (0x26, 'u8'), (0x27, 'u8'), (0x28, 'u8')):
        body = body.replace('(*(s32 *)((char *)(arg0) + 0x%X))' % offset,
            '(*(%s *)((char *)(arg0) + 0x%X))' % (kind, offset))
    for offset in (0x2D, 0x2E):
        body = body.replace('(*(s16 *)((char *)(arg0) + 0x%X))' % offset,
            '(*(s8 *)((char *)(arg0) + 0x%X))' % offset)
    for offset in (0x29, 0x2A, 0x2B):
        body = body.replace('(*(s8 *)((char *)(arg0) + 0x%X))' % offset,
            '(*(u8 *)((char *)(arg0) + 0x%X))' % offset)
    return body


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (97, 0, 0, ''):
        raise ValueError('Color fade is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 388 or list(struct.unpack_from('>97I', data, f['value'])) != words:
        raise ValueError('Color-fade production padding differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = measure(root, root / BUILD) if args.measure else qualify(root, root / BUILD)
    print(json.dumps(result[-1], indent=2))
