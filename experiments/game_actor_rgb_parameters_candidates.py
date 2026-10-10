"""Recover the complete frame-free actor RGB parameter callback."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502D54C, 0x5A9FC, 57
FUNCTION = 'func_1502D54C'
SOURCE = 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502D54C() {\n    return 0;\n}'
DECLARATIONS = 'extern u8 D_800CC2D0[];\n'
SYMBOLS = dict(D_800CC2D0=0x800CC2D0)
SELECTED = '''void func_1502D54C(s32 slot, s32 *parameters) {
    u8 *actor = D_800CC2D0 + (u32)slot * 0x32C;

    if ((actor[0x66] & 0xC) == 4) {
        parameters[0] = (actor[0x1E0] + actor[0x1DD]) / 2;
        parameters[1] = (actor[0x1E1] + actor[0x1DE]) / 2;
        parameters[2] = (actor[0x1E2] + actor[0x1DF]) / 2;
        parameters[0] = 255 - parameters[0];
        parameters[1] = 255 - parameters[1];
        parameters[2] = 255 - parameters[2];
        return;
    }
    parameters[0] = parameters[1] = parameters[2] = 255;
}'''


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS,
            SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_1502D54C();') != 1:
        raise ValueError('stale RGB owner or declaration')
    body = SELECTED.replace('D_800CC2D0 +', '(u8 *)D_800CC2D0 +')
    return before.replace('s32 func_1502D54C();',
        'void func_1502D54C(s32, s32 *);').replace(ORIGINAL, body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-rgb-parameters'
    records = []
    for name, body in (
            ('selected', SELECTED),
            ('signed-slot', SELECTED.replace('(u32)slot', 'slot')),
            ('reverse-condition', SELECTED.replace('== 4', '!= 4'))):
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
