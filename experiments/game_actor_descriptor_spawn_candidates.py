"""Recover the actor coordinate/descriptor factory and conditional float copy."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1506A864, 0x97D14, 65
FUNCTION = 'func_1506A864'
SOURCE = 'conker/src/game/generated_97AA0.c'
ORIGINAL = 's32 func_1506A864() {\n    return 0;\n}'
MARKER = 'extern u8 D_800D1560[];'
RECORD = '#include "structs.h"\n'
PROTOTYPE = '''struct225 *func_151602C0(Header *, Header2 *, s32, s32, s32, s32, u8, u8, s32, u8, s32);
extern f32 D_80099A28;
'''
DECLARATIONS = PROTOTYPE + 'void *memcpy(void *, const void *, unsigned int);\n'
SYMBOLS = dict(func_151602C0=0x151602C0, memcpy=0x10022EC0, D_80099A28=0x80099A28)
LOCALS = {'created': '    struct225 *created;', 'header': '    Header header;',
    'payload': '    f32 payload[4];', 'position': '    Header2 position;'}
BASE = '''void func_1506A864(u8 *actor, s32 arg1) {
    struct225 *created;
    Header header;
    f32 payload[4];
    Header2 position;

    position.unk0 = (s32)*(f32 *)(actor + 0x14);
    position.unk4 = (s32)(*(f32 *)(actor + 0x18) + 50.0f);
    position.unk8 = (s32)*(f32 *)(actor + 0x1C);
    header.unk0 = 2;
    header.unk1 = 15;
    header.unk2 = 300;
    header.unk4 = 5;
    payload[0] = 0.0f;
    payload[1] = 80.0f;
    payload[2] = 0.0f;
    payload[3] = D_80099A28;
    created = func_151602C0(&header, &position, 0, 0xFF, 0xFF, 90, 0xFF, 0, sizeof(payload), 0xFF, 1);
    if (created != NULL) {
        memcpy((u8 *)created + 0x18, payload, sizeof(payload));
    }
}'''
HEADER = '\n'.join('    header.' + statement for statement in
    ('unk0 = 2;', 'unk1 = 15;', 'unk2 = 300;', 'unk4 = 5;'))
SELECTED = BASE.replace(HEADER + '\n    payload[0] = 0.0f;\n    payload[1] = 80.0f;\n    payload[2] = 0.0f;',
    '    payload[0] = 0.0f;\n    payload[2] = 0.0f;\n' + HEADER + '\n    payload[1] = 80.0f;')


def candidates():
    original = '\n'.join(LOCALS.values())
    for order in itertools.permutations(LOCALS):
        yield '-'.join(order), SELECTED.replace(original, '\n'.join(LOCALS[name] for name in order), 1)


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(root, out, name, body, profile)
    adjustments = [(index, (-(word & 65535)) & 65535) for index, word in enumerate(words)
        if word >> 16 == 0x27BD and word & 32768]
    if len(adjustments) != 1:
        raise ValueError('Expected one actual negative SP adjustment: %r' % adjustments)
    record['frame'], record['prologue_word'] = adjustments[0][1], adjustments[0][0]
    return record, words


def recovered_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count(MARKER) != 1 or before.count('#include <ultra64.h>\n') != 1:
        raise ValueError('Expected the original spawn placeholder and owner includes')
    return before.replace('#include <ultra64.h>\n', '#include <ultra64.h>\n' + RECORD, 1).replace(
        MARKER, PROTOTYPE + '\n' + MARKER, 1).replace(ORIGINAL, body, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-descriptor-spawn'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
