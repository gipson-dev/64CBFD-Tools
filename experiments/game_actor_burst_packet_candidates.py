"""Recover the mixed-layout mode-1 actor burst descriptor without filling holes."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1506A5F0, 0x97AA0, 67
FUNCTION = 'func_1506A5F0'
SOURCE = 'conker/src/game/generated_97AA0.c'
ORIGINAL = 's32 func_1506A5F0() {\n    return 0;\n}'
MARKER = 'extern s32 D_800CC260;'
COEFFICIENTS = tuple('D_80099A%02X' % offset for offset in range(0x10, 0x28, 4))
SYMBOLS = dict(func_151A6F00=0x151A6F00, **dict(zip(COEFFICIENTS, range(0x80099A10, 0x80099A28, 4))))
RECORD = '''typedef struct {
    s16 count;
    u8 pad2[2];
    f32 position[3];
    s16 duration;
    u8 pad12[2];
    f32 radius;
    s16 angle0, range0, angle1, range1;
    f32 speed, speedRange;
    f32 unk28, unk2C;
    f32 direction[3];
    f32 scale, scaleRange;
    f32 unk44, unk48, unk4C, unk50;
    u8 unk54, unk55;
    s16 unk56, unk58;
    u8 pad5A[2];
} ActorBurstPacket97AA0;
typedef char ActorBurstPacketSize97AA0[(sizeof(ActorBurstPacket97AA0) == 0x5C) ? 1 : -1];
'''
DECLARATIONS = 'void func_151A6F00(ActorBurstPacket97AA0 *, u8, u8, s32);\n' + ''.join(
    'extern f32 %s;\n' % name for name in COEFFICIENTS)
BASE = '''void func_1506A5F0(u8 *actor, s32 arg1) {
    ActorBurstPacket97AA0 packet;

    packet.count = 3;
    packet.position[0] = *(f32 *)(actor + 0x14);
    packet.position[1] = *(f32 *)(actor + 0x18);
    packet.position[2] = *(f32 *)(actor + 0x1C);
    packet.duration = 90;
    packet.radius = D_80099A10;
    packet.angle0 = 0;
    packet.range0 = 255;
    packet.angle1 = -64;
    packet.range1 = 40;
    packet.speed = D_80099A14;
    packet.speedRange = D_80099A18;
    packet.direction[0] = 0.0f;
    packet.direction[1] = 0.0f;
    packet.direction[2] = 0.0f;
    packet.scale = D_80099A1C;
    packet.scaleRange = D_80099A20;
    packet.unk44 = D_80099A24;
    packet.unk48 = 0.0f;
    packet.unk4C = -4.0f;
    packet.unk50 = 8.0f;
    packet.unk54 = 0;
    packet.unk55 = 0;
    packet.unk56 = 50;
    packet.unk58 = 25;
    func_151A6F00(&packet, 1, 0xFF, 1);
}'''
SELECTED = BASE.replace('packet.unk48 = 0.0f;', 'packet.unk48 = 0;')


def candidates():
    yield 'selected-integer-zero', SELECTED
    yield 'field-order', BASE
    for literal in ('0', '0.0', '(f32)0'):
        yield 'last-zero-' + literal.replace('(', '').replace(')', ''), BASE.replace(
            'packet.unk48 = 0.0f;', 'packet.unk48 = %s;' % literal)
    coordinates = '\n'.join('    packet.position[%d] = *(f32 *)(actor + 0x%X);' %
        (i, 0x14 + i * 4) for i in range(3))
    zeros = '\n'.join('    packet.direction[%d] = 0.0f;' % i for i in range(3))
    for literal in ('0', '0.0f'):
        body = BASE.replace(zeros,
            '    packet.direction[0] = packet.direction[1] = packet.direction[2] = %s;' % literal)
        yield 'chained-' + literal, body
    yield 'coordinates-first', BASE.replace('    packet.count = 3;\n' + coordinates,
        coordinates + '\n    packet.count = 3;')
    yield 'zeros-first', BASE.replace(zeros + '\n', '').replace(
        '    packet.count = 3;', zeros + '\n    packet.count = 3;')
    yield 'unused-argument-volatile', BASE.replace('s32 arg1', 's32 volatile arg1')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, words = compiler.compile_candidate(root, out, name, body, profile)
    adjustments = [(index, (-(word & 65535)) & 65535) for index, word in enumerate(words)
        if word >> 16 == 0x27BD and word & 32768]
    if len(adjustments) != 1:
        raise ValueError('Expected one actual negative SP adjustment: %r' % adjustments)
    record['prologue_word'], record['frame'] = adjustments[0]
    return record, words


def recovered_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count(MARKER) != 1:
        raise ValueError('Expected one burst placeholder and owner marker')
    return before.replace(MARKER, RECORD + '\n' + DECLARATIONS + '\n' + MARKER, 1).replace(ORIGINAL, body, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-burst-packet'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
