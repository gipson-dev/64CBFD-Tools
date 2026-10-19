"""Recover the two actor-pair masks and their ordered position/query gates."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_mode_context_init_candidates as previous
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-actor-pair-visibility'
SOURCE, OWNER = previous.SOURCE, previous.OWNER
FUNCTION, ENTRY, ROM, WORDS = 'func_1508C1A4', 0x1508C1A4, 0xB9654, 261
ORIGINAL = 's32 func_1508C1A4() {\n    return 0;\n}'
INPUTS = dict(previous.INPUTS)
INPUTS.update({
    SOURCE: '630d6cbaa567addbb094dce43b81277ece9b1dfb2865196038af637a691b7845',
    'conker/Makefile': 'cf6de057267055cf5ad789e72426b7433c0bfe37d04ae56c241332cf2f2febf4',
    'conker/retail_word_patches.us.csv': '9aefde5eabf696da27221d6daa912245766d5e9781563b9abadf39d7560733a1',
    'conker/build/conker.us.elf': 'e8b1afc1b2bfd45d1bd516e86fd61c4480b673c8a6cde72bae792962ba3dacf4',
    'conker/asm/D86A0.s': '4918cc17bed865c1db2ac160a461024c74c6e591274d12c0bda57d13077e5038',
    'conker/asm/nonmatchings/game_83300/func_1505EEF4.s': '78e95b6c29401b59b846a23cccc5a5cbec318e3444e50d596b21213d43d7e958',
})
DECLARATIONS = '''extern s32 D_800D23B0;
extern s8 D_800E0BD0;
extern s16 D_800872C4[];
u8 *func_1505EEF4(s32 key);
s32 func_150AC9C0(f32, f32, f32, f32, f32, f32, s32, s32,
    void **, void **, void **, f32 *, s32, s32, f32);
f32 func_15086D94(f32, f32, f32, f32, f32);
'''
SELECTED = '''/* Set symmetric pair masks after the collision and barrier queries. */
void func_1508C1A4(s32 first, s32 second) {
    s32 clearShadow;
    s32 queryClear;
    u8 *actor;
    f32 distance;
    void *hitA;
    void *hitB;
    void *hitC;
    f32 hitDistance;
    f32 savedX;
    f32 otherX;
    f32 savedY;
    f32 startZ;
    f32 otherZ;
    f32 dx;
    f32 dz;
    f32 savedZ;
    f32 dy;
    f32 x;
    f32 y;
    f32 otherY;
    s32 clear;
    u8 active;
    u8 otherActive;
    u8 *nested;
    u8 *other;
    u32 *row;

    queryClear = 0;
    clearShadow = 0;
    actor = func_1505EEF4(first & 0xFFFF0FFF);
    other = func_1505EEF4(second & 0xFFFF0FFF);
    clear = clearShadow;
    if ((actor != NULL) && (other != NULL)) {
        x = *(f32 *)(actor + 0x14);
        startZ = *(f32 *)(actor + 0x1C);
        nested = *(u8 **)(actor + 0x31C);
        active = nested[0x84];
        if (active != 0) {
            y = *(f32 *)(actor + 0x18) + (f32)*(s16 *)(nested + 0x114) * 0.75f;
            if ((nested[0x75] & 0x7F) == 9) {
                y -= 50.0f;
            }
            nested = *(u8 **)(other + 0x31C);
            otherActive = nested[0x84];
        } else if (*(s32 *)actor == 0x1F) {
            nested = *(u8 **)(other + 0x31C);
            otherActive = nested[0x84];
            y = *(f32 *)(actor + 0x18) + 80.0f;
        } else {
            nested = *(u8 **)(other + 0x31C);
            otherActive = nested[0x84];
            if ((otherActive != 0) && (D_800872C4[D_800E0BD0] != -1)) {
                x = (f32)*(s16 *)(actor + 0x1A4);
                startZ = (f32)*(s16 *)(actor + 0x1A8);
                y = (f32)*(s16 *)(actor + 0x1A6);
            } else {
                y = *(f32 *)(actor + 0x18) + 40.0f;
            }
        }
        otherX = *(f32 *)(other + 0x14);
        otherZ = *(f32 *)(other + 0x1C);
        if (otherActive != 0) {
            otherY = *(f32 *)(other + 0x18) + (f32)*(s16 *)(nested + 0x114) * 0.75f;
            if ((nested[0x75] & 0x7F) == 9) {
                otherY -= 50.0f;
            }
        } else if (*(s32 *)other == 0x1F) {
            otherY = *(f32 *)(other + 0x18) + 80.0f;
        } else if ((active != 0) && (D_800872C4[D_800E0BD0] != -1)) {
            otherX = (f32)*(s16 *)(other + 0x1A4);
            otherY = (f32)*(s16 *)(other + 0x1A6);
            otherZ = (f32)*(s16 *)(other + 0x1A8);
        } else {
            otherY = *(f32 *)(other + 0x18) + 40.0f;
        }
        dy = otherY - y;
        savedZ = startZ;
        dz = otherZ - startZ;
        dx = otherX - x;
        distance = sqrtf((dx * dx) + (dy * dy) + (dz * dz));
        savedX = x;
        savedY = y;
        clear = clearShadow;
        if (func_150AC9C0(x, y, savedZ, dx, dy, dz, 0, 0,
                &hitA, &hitB, &hitC, &hitDistance, 0, 0, 0.0f) == 0) {
            goto clear_query;
        }
        if (distance < hitDistance) {
clear_query:
            clear = 1;
        }
        queryClear = clear;
        if (clear != 0) {
            clearShadow = clear;
            if (func_15086D94(savedX, savedY, startZ, dx, dz) > 0.0f) {
                clear = 0;
            }
        }
    }
    if (clear != 0) {
        row = (u32 *)((u8 *)D_800D23B0 + (u32)first * 4);
        row[0x16C0 / 4] |= 1u << ((u32)second & 31);
        row = (u32 *)((u8 *)D_800D23B0 + (u32)second * 4);
        row[0x16C0 / 4] |= 1u << ((u32)first & 31);
    }
    if (queryClear != 0) {
        row = (u32 *)((u8 *)D_800D23B0 + (u32)first * 4);
        row[0x16C0 / 4] |= 0x10000u << ((u32)second & 31);
        row = (u32 *)((u8 *)D_800D23B0 + (u32)second * 4);
        row[0x16C0 / 4] |= 0x10000u << ((u32)first & 31);
    }
}
'''
INITIAL = SELECTED
compile_profile, link_owner = previous.compile_profile, previous.link_owner


def freeze(root, out):
    with patch.object(previous, 'INPUTS', INPUTS):
        return previous.freeze(root, out)


def recovered_owner(before, body=None):
    if before.count(ORIGINAL) != 1:
        raise ValueError('Unknown actor-pair visibility predecessor')
    return before.replace(ORIGINAL, DECLARATIONS + '\n' + (SELECTED if body is None else body).rstrip())


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor-pair alignment tail')
    return raw[:end * 4], {at - f['value']: entries for at, entries in bindings.items()
        if f['value'] <= at < f['value'] + end * 4}


def compile_candidate(root, out, name='selected', body=None, normal=False, whole=False):
    values = freeze(root, out)
    unit = recovered_owner(values[SOURCE].decode(), body) if whole else (
        '#include <ultra64.h>\n' + DECLARATIONS + (SELECTED if body is None else body))
    obj, diagnostics = compile_profile(root, out, unit, name, normal)
    raw, bindings = payload(obj)
    image, functions = link_owner(root, out, obj, OWNER)
    at = functions[FUNCTION]['value']
    words = list(struct.unpack_from('>%dI' % (len(raw) // 4), image, at))
    truth = struct.unpack_from('>261I', values['conker/conker.us.bin'], ROM)
    row = dict(words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(), bindings=bindings)
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def candidates():
    yield 'initial', INITIAL
    yield 'implicit-shift-mask', INITIAL.replace('((u32)second & 31)', 'second').replace('((u32)first & 31)', 'first')
    yield 'signed-row-offsets', INITIAL.replace('(u32)first * 4', 'first * 4').replace('(u32)second * 4', 'second * 4')
    live = INITIAL.replace('    s32 clearShadow;\n', '').replace('    clearShadow = 0;', '    clear = 0;').replace(
        '        clear = clearShadow;\n', '').replace('    clear = clearShadow;\n', '').replace('            clearShadow = clear;\n', '')
    yield 'single-visible-flag', live
    old = '''        if (func_150AC9C0(x, y, savedZ, dx, dy, dz, 0, 0,
                &hitA, &hitB, &hitC, &hitDistance, 0, 0, 0.0f) == 0) {
            goto clear_query;
        }
        if (distance < hitDistance) {
clear_query:
            clear = 1;
        }'''
    new = '''        if (func_150AC9C0(x, y, savedZ, dx, dy, dz, 0, 0,
                &hitA, &hitB, &hitC, &hitDistance, 0, 0, 0.0f) == 0) {
            clear = 1;
        } else if (distance < hitDistance) {
            clear = 1;
        }'''
    yield 'split-clear-branches', INITIAL.replace(old, new)
    yield 'single-visible-split', live.replace(old, new)
    direct = live.replace('    f32 savedX;\n', '').replace('    f32 savedY;\n', '').replace('    f32 savedZ;\n', '').replace(
        '        savedZ = startZ;\n', '').replace('        savedX = x;\n', '').replace('        savedY = y;\n', '').replace(
        'savedZ, dx, dy', 'startZ, dx, dy').replace('savedX, savedY, startZ', 'x, y, startZ')
    yield 'single-visible-direct-coordinates', direct
    split = direct.replace(old.replace('savedZ', 'startZ'), new.replace('savedZ', 'startZ'))
    yield 'direct-split', split
    early = split.replace('    s32 clear;\n', '').replace(
        '    s32 queryClear;', '    s32 clear;\n    s32 queryClear;')
    yield 'early-flag-direct-split', early
    for label, names in (('point-temps', ('dy', 'x', 'y', 'otherY')), ('deltas', ('dx', 'dy', 'dz'))):
        declarations = ''.join('    f32 %s;\n' % name for name in names)
        moved = early
        for name in names:
            moved = moved.replace('    f32 %s;\n' % name, '')
        yield label + '-before-outputs', moved.replace('    f32 distance;\n', declarations + '    f32 distance;\n')


SELECTED = dict(candidates())['early-flag-direct-split']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--normal', action='store_true')
    p.add_argument('--whole', action='store_true')
    p.add_argument('--screens', action='store_true')
    p.add_argument('--filter')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    for name, body in candidates() if args.screens else [('selected', SELECTED)]:
        if args.filter and args.filter not in name:
            continue
        _, _, row = compile_candidate(root, root / BUILD, name + ('-normal' if args.normal else '') +
            ('-whole' if args.whole else ''), body, args.normal, args.whole)
        print(json.dumps(dict(name=name, **{key: value for key, value in row.items() if key != 'bindings'})), flush=True)
