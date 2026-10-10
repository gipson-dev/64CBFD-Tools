"""Measure the complete six-mode leaf updater with explicit wrapping products."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502EAFC, 0x5BFAC, 78
FUNCTION = 'func_1502EAFC'
SOURCE = 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502EAFC() {\n    return 0;\n}'
DECLARATIONS = 'extern s32 D_800BE9E4;\n'
SYMBOLS = dict(D_800BE9E4=0x800BE9E4)
BASE = '''void func_1502EAFC(u8 *object) {
    s32 delta, phase;

    switch (object[0xA4]) {
    case 2:
    case 3:
        delta = (u32)object[0xA6] * (u32)D_800BE9E4;
        phase = object[0xA5];
        if (delta < phase) {
            object[0xA5] = (u32)phase - (u32)delta;
        } else {
            object[0xA5] = 0;
        }
        break;
    case 5:
        delta = (u32)D_800BE9E4 * 10;
        phase = object[0xA7];
        if (delta < phase) {
            object[0xA7] = (u32)phase - (u32)delta;
        } else {
            object[0xA4] = 0;
        }
        /* Fall through. */
    case 4:
        object[0xA5] += (u32)object[0xA6] * (u32)D_800BE9E4;
        break;
    case 6:
        delta = (u32)object[0xA6] * (u32)D_800BE9E4;
        phase = object[0xA5];
        if (phase < (s32)(255u - (u32)delta)) {
            object[0xA5] = (u32)phase + (u32)delta;
        } else {
            object[0xA5] = 255;
        }
        object[0xA4] = 7;
        break;
    case 7:
        delta = (u32)object[0xA6] * (u32)D_800BE9E4;
        phase = object[0xA5];
        if (delta < phase) {
            object[0xA5] = (u32)phase - (u32)delta;
        } else {
            object[0xA4] = 0;
        }
        break;
    }
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'register-phase', BASE.replace('s32 delta, phase;', 's32 delta; register s32 phase;')
    yield 'register-delta', BASE.replace('s32 delta, phase;', 'register s32 delta; s32 phase;')
    yield 'phase-first', BASE.replace('s32 delta, phase;', 's32 phase, delta;')
    yield 'void-pointer', BASE.replace('u8 *object)', 'void *record)').replace('    s32 delta, phase;',
        '    u8 *object = record;\n    s32 delta, phase;')
    yield 'mode4-explicit', BASE.replace('        object[0xA5] += (u32)object[0xA6] * (u32)D_800BE9E4;',
        '        delta = (u32)object[0xA6] * (u32)D_800BE9E4;\n'
        '        object[0xA5] = (u32)object[0xA5] + (u32)delta;')
    yield 'negative-cache-tick', BASE.replace('    s32 delta, phase;', '    s32 delta, phase;\n    u32 tick = D_800BE9E4;').replace(
        '(u32)D_800BE9E4', 'tick')
    yield 'negative-unsigned-compare', BASE.replace('if (delta < phase)', 'if ((u32)delta < (u32)phase)')
    yield 'negative-clear-phase', BASE.replace('            object[0xA4] = 0;', '            object[0xA5] = 0;')
    yield 'negative-no-fallthrough', BASE.replace('        /* Fall through', '        break;\n        /* Fall through')
    yield 'negative-mode6-gate', BASE.replace('phase < (s32)(255u - (u32)delta)', 'phase < (s32)(254u - (u32)delta)')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    meta['frame'] = 0
    return meta, words


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-object-phase-update'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if name == 'selected' else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], meta['differences'], meta['pool_bytes'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
