"""Recover the complete three-vector effect emitter and its mixed O32 factory call."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151A7610, 0x1D4AC0, 108
FUNCTION = 'func_151A7610'
SOURCE = 'conker/src/game/generated_1D43B0.c'
ORIGINAL = 's32 func_151A7610() {\n    return 0;\n}'
MARKER = 'extern s32 D_800BE9E4;'
RECORD = 'typedef struct { f32 x, y, z; } BurstVector1D43B0;\n'
DECLARATIONS = '''extern f32 D_800BE9A8;
extern f32 D_800A8DC8, D_800A8DCC, D_800A8DD0;
void func_151A26EC(BurstVector1D43B0 *, BurstVector1D43B0 *, BurstVector1D43B0 *,
    f32, f32, f32, s32, s32, s32, s32, s32, s32, s32, s32, s32, u8, s32);
'''
SYMBOLS = dict(func_150ADA68=0x150ADA68, func_150ADA20=0x150ADA20, func_151A26EC=0x151A26EC,
    D_800BE9A8=0x800BE9A8, D_800A8DC8=0x800A8DC8, D_800A8DCC=0x800A8DCC, D_800A8DD0=0x800A8DD0)
BASE = '''void func_151A7610(f32 x, f32 y, f32 z, f32 dx, f32 dy, f32 dz, u8 *actor) {
    BurstVector1D43B0 position, zero, velocity;
    f32 retained = *(f32 *)(actor + 0x40);
    f32 first, second, speed, multiplier;
    u32 integer0, integer1;

    position.x = x;
    position.y = y;
    position.z = z;
    first = func_150ADA68();
    multiplier = D_800BE9A8;
    speed = (first * 166.0f + 160.0f) * D_800A8DC8;
    zero.x = 0.0f;
    zero.y = 0.0f;
    zero.z = 0.0f;
    velocity.x = -dx * multiplier * speed;
    velocity.y = -dy * multiplier * speed;
    velocity.z = -dz * multiplier * speed;
    first = func_150ADA68();
    second = func_150ADA68();
    integer0 = (u32)func_150ADA20();
    integer1 = (u32)func_150ADA20();
    func_151A26EC(&position, &zero, &velocity, 1.0f,
        (first * D_800A8DCC - 600.0f) * D_800A8DD0,
        (second * 500.0f + 400.0f) * retained,
        integer0 % 21 + 15, integer1 % 101 + 100,
        15, 20, 0, -1, 0x56, 0x27, 0, actor[0xC], actor[1]);
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'base', BASE
    for vectors in itertools.permutations(('position', 'zero', 'velocity')):
        body = BASE.replace('BurstVector1D43B0 position, zero, velocity;',
            'BurstVector1D43B0 ' + ', '.join(vectors) + ';')
        yield 'vectors-' + '-'.join(vectors), body
    yield 'no-multiplier-local', BASE.replace('speed, multiplier;', 'speed;').replace(
        '    multiplier = D_800BE9A8;\n', '').replace('* multiplier', '* D_800BE9A8')
    for retention_first, literal_add in itertools.product((False, True), repeat=2):
        if not (retention_first or literal_add):
            continue
        body = BASE
        if retention_first:
            body = body.replace('    f32 retained = *(f32 *)(actor + 0x40);\n', '').replace(
                '    BurstVector1D43B0 ', '    f32 retained = *(f32 *)(actor + 0x40);\n    BurstVector1D43B0 ', 1)
        if literal_add:
            body = body.replace('first * D_800A8DCC - 600.0f', 'first * D_800A8DCC + -600.0f')
        yield 'shape-retain%d-add%d' % (retention_first, literal_add), body
    yield from lifetime_forms()
    yield from home_forms()
    yield from product_forms()
SHAPED = BASE.replace('    f32 retained = *(f32 *)(actor + 0x40);\n', '').replace(
    '    BurstVector1D43B0 ', '    f32 retained = *(f32 *)(actor + 0x40);\n    BurstVector1D43B0 ', 1).replace(
    'first * D_800A8DCC - 600.0f', 'first * D_800A8DCC + -600.0f')


def lifetime_forms():
    for vectors in itertools.permutations(('position', 'zero', 'velocity')):
        body = SHAPED.replace('    BurstVector1D43B0 position, zero, velocity;',
            '\n'.join('    BurstVector1D43B0 %s;' % v for v in vectors))
        yield 'lifetime-separate-' + '-'.join(vectors), body
    for distinct, multiplier_first, integer_first in itertools.product((False, True), repeat=3):
        body = SHAPED
        if distinct:
            body = body.replace('    f32 first, second, speed, multiplier;',
                '    f32 initial, first, second, speed, multiplier;').replace(
                '    first = func_150ADA68();', '    initial = func_150ADA68();', 1).replace(
                'first * 166.0f', 'initial * 166.0f')
        if multiplier_first:
            body = body.replace('speed, multiplier;', 'multiplier, speed;')
        if integer_first:
            body = body.replace('    u32 integer0, integer1;\n', '').replace(
                '    f32 retained', '    u32 integer0, integer1;\n    f32 retained', 1)
        yield 'lifetime-initial%d-multiplier%d-integer%d' % (distinct, multiplier_first, integer_first), body
    yield 'lifetime-observed-homes', SHAPED.replace('position', 'sp8C').replace('zero', 'sp74').replace(
        'velocity', 'sp80').replace('retained', 'sp6C').replace('first', 'sp58').replace('second', 'sp5C').replace(
        'integer0', 'sp60').replace('integer1', 'random1')


def home_forms():
    distinct = dict(lifetime_forms())['lifetime-initial1-multiplier0-integer1']
    start = distinct.index('    u32 integer0, integer1;')
    end = distinct.index('\n\n    position.x')
    locals = '''    BurstVector1D43B0 position;
    BurstVector1D43B0 velocity;
    BurstVector1D43B0 zero;
    f32 multiplier;
    f32 retained = *(f32 *)(actor + 0x40);
    f32 speed;
    f32 initial;
    u32 integer0;
    f32 second;
    f32 first;
    u32 integer1;'''
    body = distinct[:start] + locals + distinct[end:]
    yield 'homes-source-order', body
    yield 'homes-world-before-speed', body.replace('    multiplier = D_800BE9A8;\n', '').replace(
        '    velocity.x =', '    multiplier = D_800BE9A8;\n    velocity.x =')
    yield 'homes-commuted-products', body.replace('-dx * multiplier * speed', 'speed * (-dx * multiplier)').replace(
        '-dy * multiplier * speed', 'speed * (-dy * multiplier)').replace(
        '-dz * multiplier * speed', 'speed * (-dz * multiplier)')


def product_forms():
    body = dict(home_forms())['homes-source-order']
    for sample, middle in itertools.product(('initial', 'speed', 'first'), ('initial', 'speed')):
        code = body.replace('    initial = func_150ADA68();', '    %s = func_150ADA68();' % sample, 1).replace(
            '    speed = (initial * 166.0f + 160.0f) * D_800A8DC8;',
            '    %s = %s * 166.0f + 160.0f;\n    speed = %s * D_800A8DC8;' % (middle, sample, middle))
        yield 'product-sample-%s-middle-%s' % (sample, middle), code
    yield 'product-initial-result', body.replace('    speed = (initial * 166.0f + 160.0f) * D_800A8DC8;',
        '    initial = (initial * 166.0f + 160.0f) * D_800A8DC8;\n    speed = initial;')
    yield 'product-initial-world', body.replace('    multiplier = D_800BE9A8;',
        '    speed = initial;\n    initial = D_800BE9A8;').replace(
        '    speed = (initial * 166.0f + 160.0f) * D_800A8DC8;',
        '    speed = (speed * 166.0f + 160.0f) * D_800A8DC8;\n    multiplier = initial;')


SELECTED = dict(home_forms())['homes-source-order']
GUARDS = (
    (0x34, 0xC4220000, 0xC42C0000),
    (0x70, 0x46049302, 0x46049082),
    (0x78, 0x46024282, 0x460C4282),
    (0x80, 0x460C5402, 0x46025402),
    (0x88, 0x46022182, 0x460C2182),
    (0x94, 0x460C3202, 0x46023202),
    (0x9C, 0x46028482, 0x460C8482),
    (0xA4, 0x460C9102, 0x46029102),
)


def guard_rows(words, relocations):
    if len(words) != WORDS or words[0] != 0x27BDFF68:
        raise ValueError('Unexpected complete effect frame or extent')
    rows = []
    for offset, expected, replacement in GUARDS:
        owned = [('R_MIPS_LO16', 'D_800BE9A8')] if offset == 0x34 else []
        if words[offset // 4] != expected or relocations.get(offset, []) != owned:
            raise ValueError('Unexpected closed F2/F12 allocation or relocation')
        spec = 'R_MIPS_LO16:D_800BE9A8' if owned else '-'
        rows.append(dict(filename='generated_1D43B0', function=FUNCTION,
            offset='0x%03X' % offset, expected='0x%08X' % expected,
            replacement='0x%08X' % replacement, expected_relocations=spec,
            replacement_relocations=spec,
            note='Normalize closed effect velocity F2/F12 register allocation',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    declarations = 'f32 func_150ADA68(void);\ns32 func_150ADA20(void);\n' + DECLARATIONS
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=declarations, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def recovered_owner(before):
    if before.count(ORIGINAL) != 1 or before.count(MARKER) != 1:
        raise ValueError('Expected one effect placeholder and declaration marker')
    return before.replace(MARKER, DECLARATIONS + '\n' + MARKER).replace(ORIGINAL, SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-effect-packet'
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
