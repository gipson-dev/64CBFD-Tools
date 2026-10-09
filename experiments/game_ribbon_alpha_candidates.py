"""Audit the full ribbon alpha callback without changing any retail instruction."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151490C8, 0x176578, 15
FUNCTION = 'func_151490C8'
SOURCE = 'conker/src/game/generated_175250.c'
ORIGINAL = '''s32 func_151490C8(u8 *arg0) {
    u8 *temp_v0 = *(u8 **) (arg0 + 0x98);
    s32 temp_v1 = *(s16 *) (arg0 + 0x1C) << 3;

    if (temp_v1 >= 0x100) {
        temp_v1 = 0xFF;
    }
    *(temp_v0 + 0x1B) = temp_v1;
    if ((temp_v1 & 0xFF) < 0) {
        return 0;
    }
    return 1;
}'''
SELECTED = ORIGINAL.replace('<< 3', '* 8')


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
    out = root / 'conker/build/game-ribbon-alpha'
    records = []
    for name, body in (('original', ORIGINAL), ('selected', SELECTED),
            ('unsigned-shift', ORIGINAL.replace('*(s16 *) (arg0 + 0x1C) << 3',
                '(s32)((u32)*(s16 *) (arg0 + 0x1C) << 3)'))):
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
