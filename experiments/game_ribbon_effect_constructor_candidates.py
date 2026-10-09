"""Recover the complete angle-based ribbon effect constructor and mixed O32 ABI."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler


ENTRY, ROM, WORDS = 0x15148F1C, 0x1763CC, 107
FUNCTION = 'func_15148F1C'
ORIGINAL = 's32 func_15148F1C() {\n    return 0;\n}'
TYPES = '''typedef struct { s32 words[8]; } RenderRecord15147DA0;
typedef struct {
    f32 x, y, z;
    s16 duration, mode;
    s32 active;
    u8 reserved14, count, reserved16[2];
    s32 value;
} RibbonRequest15148F1C;
typedef struct {
    f32 gravity, velocityX, velocityY, velocityZ, threshold;
    u8 reserved14[4], flags, kind, channel, alpha, reserved1C[4];
} RibbonPayload15148F1C;
'''
DECLARATIONS = '''f32 func_151423D8(u8);
u8 *func_15147DA0(void *, void *, s32, s32, s32, s32, s32, s32, s32,
    s32, s32, void *, s32, u8, s32);
'''
SYMBOLS = dict(func_151423D8=0x151423D8, func_15147DA0=0x15147DA0)
BASE = '''u8 *func_15148F1C(u8 kind, f32 x, f32 y, f32 z, s32 count,
    u8 yaw, u8 pitch, f32 speed, s16 duration, f32 gravity, f32 threshold, u8 channel) {
    RibbonRequest15148F1C request;
    RibbonPayload15148F1C payload;
    f32 pitchValue;
    f32 pitchQuarter;
    f32 yawValue;
    f32 yawQuarter;
    RenderRecord15147DA0 render;

    pitchValue = func_151423D8(pitch);
    pitchQuarter = func_151423D8((u8)((u32)pitch - 0x40));
    yawValue = func_151423D8(yaw);
    yawQuarter = func_151423D8((u8)((u32)yaw - 0x40));
    request.active = 1;
    request.mode = 1;
    payload.channel = 255;
    payload.flags = 8;
    payload.kind = kind;
    if (kind == 10) {
        payload.flags = 0x28;
    }
    request.x = x;
    request.y = y;
    request.z = z;
    payload.velocityX = (speed * pitchValue) * yawQuarter;
    payload.velocityY = -speed * pitchQuarter;
    payload.velocityZ = (speed * pitchValue) * yawValue;
    payload.gravity = gravity;
    payload.threshold = threshold;
    payload.alpha = 255;
    request.count = (u32)count + 3;
    request.duration = duration;
    render.words[0] = 0;
    render.words[1] = 1;
    render.words[2] = 0x160600;
    render.words[3] = 3;
    render.words[4] = 0x10;
    render.words[5] = 0x80;
    render.words[6] = 0x20;
    ((u8 *)&render)[0x1C] = 0;
    ((u8 *)&render)[0x1D] = 9;
    return func_15147DA0(&request, &payload, 0, 1, 0, 0, 0, 0, 0, 0, 0,
        &render, 0, channel, 1);
}'''
SELECTED = BASE.replace('u8 yaw, u8 pitch', 's32 yaw, s32 pitch').replace(
    '    payload.gravity = gravity;\n    payload.threshold = threshold;\n', '').replace(
    '    payload.velocityX =',
    '    payload.gravity = gravity;\n    payload.threshold = threshold;\n    payload.velocityX =', 1)


def candidates():
    yield 'selected', SELECTED
    yield 'base-order', BASE
    grouped = SELECTED.replace('    f32 pitchValue;\n    f32 pitchQuarter;\n    f32 yawValue;\n    f32 yawQuarter;',
        '    f32 pitchValue, pitchQuarter, yawValue, yawQuarter;')
    yield 'grouped-floats', grouped
    yield 'render-first', SELECTED.replace('    RenderRecord15147DA0 render;\n', '').replace(
        '    RibbonRequest15148F1C request;', '    RenderRecord15147DA0 render;\n    RibbonRequest15148F1C request;')
    yield 'signed-count', SELECTED.replace('(u32)count + 3', 'count + 3')
    word = BASE.replace('u8 yaw, u8 pitch', 's32 yaw, s32 pitch')
    yield 'word-angles', word
    yield 'word-angles-register-quarter', word.replace('    f32 yawQuarter;', '    register f32 yawQuarter;')
    early = word.replace('    payload.gravity = gravity;\n    payload.threshold = threshold;\n', '')
    early = early.replace('    payload.velocityX =',
        '    payload.gravity = gravity;\n    payload.threshold = threshold;\n    payload.velocityX =', 1)
    yield 'word-angles-early-payload', early
    yield 'word-angles-early-payload-register-quarter', early.replace('    f32 yawQuarter;', '    register f32 yawQuarter;')
    yield 'word-angles-early-payload-inner-quarter', early.replace('    f32 yawQuarter;\n', '').replace(
        '    yawQuarter =', '    {\n    f32 yawQuarter;\n    yawQuarter =', 1).replace('\n}', '\n    }\n}')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-ribbon-effect-constructor'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, output, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
