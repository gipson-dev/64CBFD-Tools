"""Recover actor position and a global-vector difference in two private arrays."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1506A79C, 0x97C4C, 40
FUNCTION = 'func_1506A79C'
SOURCE = 'conker/src/game/generated_97AA0.c'
ORIGINAL = 's32 func_1506A79C() {\n    return 0;\n}'
MARKER = 'extern u8 D_800D1560[];'
VECTORS = 'extern u8 D_800D1560[];\nextern u8 D_800D1570[];\n'
DECLARATIONS = 'void func_151D3480(f32 *, f32 *, void *, u8, u8, s32);\n'
SYMBOLS = dict(D_800D1560=0x800D1560, D_800D1570=0x800D1570, func_151D3480=0x151D3480)
POSITION = ['    position[%d] = *(f32 *)(actor + 0x%X);' % (i, 0x14 + i * 4) for i in range(3)]
DIFFERENCE = ['    difference[%d] = *(f32 *)(D_800D1570 + %d) - *(f32 *)(D_800D1560 + %d);' % (i, i * 4, i * 4) for i in range(3)]
SELECTED = '''void func_1506A79C(u8 *actor, s32 arg1) {
    f32 position[3];
    f32 difference[3];

''' + '\n'.join(POSITION + DIFFERENCE) + '''
    func_151D3480(position, difference, NULL, 0, 0xFF, 1);
}'''


def candidates():
    for order, assignments, qualifiers in itertools.product((0, 1), ('position', 'difference', 'interleaved'), range(4)):
        body = SELECTED
        if order:
            body = body.replace('    f32 position[3];\n    f32 difference[3];',
                '    f32 difference[3];\n    f32 position[3];')
        stores = DIFFERENCE + POSITION if assignments == 'difference' else [
            store for pair in zip(POSITION, DIFFERENCE) for store in pair] if assignments == 'interleaved' else POSITION + DIFFERENCE
        body = body.replace('\n'.join(POSITION + DIFFERENCE), '\n'.join(stores))
        if qualifiers & 1:
            body = body.replace('u8 *actor', 'u8 *volatile actor')
        if qualifiers & 2:
            body = body.replace('s32 arg1', 's32 volatile arg1')
        yield 'order%d-%s-qualifier%d' % (order, assignments, qualifiers), body


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD=VECTORS, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(root, out, name, body, profile)
    # Some profiles hoist an address load ahead of the actual stack adjustment.
    adjustments = [(index, (-(word & 65535)) & 65535) for index, word in enumerate(words)
        if word >> 16 == 0x27BD and word & 32768]
    if len(adjustments) != 1:
        raise ValueError('Expected one actual negative SP adjustment: %r' % adjustments)
    record['frame'] = adjustments[0][1]
    record['prologue_word'] = adjustments[0][0]
    return record, words


def recovered_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count(MARKER) != 1:
        raise ValueError('Expected the vector-snapshot placeholder and global declarations')
    return before.replace(MARKER, DECLARATIONS + '\n' + MARKER, 1).replace(ORIGINAL, body, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-vector-snapshot'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
