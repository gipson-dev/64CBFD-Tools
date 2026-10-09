"""Recover the complete endpoint-pair callback and retail repeated-read order."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B2F04, 0x1E03B4, 39
FUNCTION = 'func_151B2F04'
SOURCE = 'conker/src/game/generated_1DF510.c'
ORIGINAL = 's32 func_151B2F04() {\n    return 0;\n}'
BASE = '''void func_151B2F04(u8 *owner, u8 *packet, u8 kind) {
    u8 *pair = owner + 0x28;

    if (kind == 0x2D) {
        if (*(s32 *)packet == *(s32 *)pair) {
            *(s32 *)pair = *(s32 *)(packet + 4);
            pair[4] = packet[9];
        } else if (*(s32 *)(packet + 4) == *(s32 *)pair) {
            *(s32 *)pair = *(s32 *)packet;
            pair[4] = packet[8];
        }
        if (*(s32 *)packet == *(s32 *)(pair + 8)) {
            *(s32 *)(pair + 8) = *(s32 *)(packet + 4);
            pair[12] = packet[9];
        } else if (*(s32 *)(packet + 4) == *(s32 *)(pair + 8)) {
            *(s32 *)(pair + 8) = *(s32 *)packet;
            pair[12] = packet[8];
        }
    }
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'pair-after-gate', BASE.replace('    u8 *pair = owner + 0x28;', '    u8 *pair;').replace(
        '    if (kind == 0x2D) {', '    if (kind == 0x2D) {\n        pair = owner + 0x28;')
    yield 'early-return', BASE.replace('    if (kind == 0x2D) {',
        '    if (kind != 0x2D) {\n        return;\n    }\n    {')
    yield 'unsigned-words', BASE.replace('s32 *', 'u32 *')
    yield 'word-kind', BASE.replace('u8 kind', 's32 kind').replace('kind ==', '(u8)kind ==')
    yield 'owner-relative', BASE.replace('    u8 *pair = owner + 0x28;\n', '').replace(
        '*(s32 *)pair', '*(s32 *)(owner + 0x28)').replace(
        '(pair + 8)', '(owner + 0x30)').replace('pair[4]', 'owner[0x2C]').replace(
        'pair[12]', 'owner[0x34]')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS='', SYMBOLS={}):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    frames = [(-word) & 65535 for word in words if word & 0xFFFF0000 == 0x27BD0000
        and word & 0x8000]
    meta['frame'] = frames[0] if frames else 0
    return meta, words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-endpoint-pair'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
