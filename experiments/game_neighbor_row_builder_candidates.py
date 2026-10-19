"""Recover the signed-cursor sorted neighbor row and original-distance minimum."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_pair_scheduler_candidates as previous
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-neighbor-row-builder'
SOURCE, OWNER = previous.SOURCE, previous.OWNER
FUNCTION, ENTRY, ROM, WORDS = 'func_1508A1BC', 0x1508A1BC, 0xB766C, 336
ORIGINAL = 's32 func_1508A1BC() {\n    return 0;\n}'
INPUTS = dict(previous.INPUTS)
INPUTS.update({
    SOURCE: '6bd6a7aea0861135038d9709e42a2a72378c3d67b4d8a644807b007fc0fc3e6d',
    'conker/retail_word_patches.us.csv': '6da8e07397f8b4340de5d95b44ffc14cf881793fc23c0d1ac2e539ae7ea6648d',
    'conker/build/conker.us.elf': '067be2667e83c916756a9eb7f69d9cd29d8349886ff0e8c09bc7c6057a777b5c',
    'conker/asm/B21B0.s': 'b579807db904bbbbc9d68a556346f4aa38f7e5ba97d0c5cc6d5b58b09d2098b7',
})
DECLARATIONS = '''extern s32 D_800D23B0;
extern s8 D_8008FD90;
extern u8 D_800CC2D0[];
s32 func_150859AC(s16 slot, s32 field);
f32 sqrtf(f32 value);
'''
INITIAL = '''/* Rebuild one sorted neighbor row and publish its unweighted minimum distance. */
s32 func_1508A1BC(void) {
    u8 *state;
    s32 *groups;
    s32 *states;
    s32 *active;
    s32 *teams;
    s32 *neighbors;
    s32 *scores;
    s32 count;
    u32 enabled;
    s32 slot;
    s32 start;
    s32 group;
    u32 mask;
    s32 used;
    s32 nearest;
    s32 i;
    s32 position;
    s32 copy;
    s32 primaryCount;
    s16 mode;
    u8 *actor;
    u8 *selected;
    s32 distance;
    s32 score;
    f32 dx;
    f32 dz;

    state = (u8 *)D_800D23B0;
    groups = (s32 *)(state + 0xE64);
    count = *(s32 *)(state + 0x10);
    enabled = *(u32 *)(state + 0x14);
    states = (s32 *)(state + 0x15C);
    active = (s32 *)(state + 0x39C);
    teams = (s32 *)(state + 0x9C);
    neighbors = (s32 *)(state + 0x5DC);
    scores = (s32 *)(state + 0x9DC);
    *(s8 *)(state + 0x1704) = (s8)(*(s8 *)(state + 0x1704) + 1);
    state = (u8 *)D_800D23B0;
    slot = *(s8 *)(state + 0x1704);
    if (*(s32 *)(state + 0x10) == slot) {
        *(s8 *)(state + 0x1704) = 0;
        state = (u8 *)D_800D23B0;
        slot = *(s8 *)(state + 0x1704);
    }
    start = slot * 16;
    used = 0;
    nearest = 32000;
    if (!(enabled & (1u << ((u32)slot & 31)))) {
        for (i = 0; i < 16; i++) {
            neighbors[start + i] = -1;
        }
        return 0;
    }
    group = groups[slot];
    mask = *(u32 *)(state + slot * 4 + 0x16C0);
    for (i = 0; i < count; i++) {
        if ((active[i] > 0) && (group != groups[i])) {
            actor = D_800CC2D0 + (u32)i * 0x32C;
            primaryCount = D_8008FD90;
            mode = *(s16 *)((u8 *)D_800D23B0 + 0x16BC);
            if (actor != NULL) {
                selected = D_800CC2D0 + slot * 0x32C;
                dx = *(f32 *)(selected + 0x14) - *(f32 *)(actor + 0x14);
                dz = *(f32 *)(selected + 0x1C) - *(f32 *)(actor + 0x1C);
                distance = (s32)sqrtf(dx * dx + dz * dz);
            } else {
                distance = 32000;
            }
            score = distance;
            if (teams[slot] != teams[i]) {
                score = (s32)((u32)score + 500u);
            }
            if (mask & (0x10000u << ((u32)i & 31))) {
                if ((score >= 3001) && (actor[0x65] != 0)) {
                    score = -1;
                }
            } else {
                if (i >= primaryCount) {
                    score = (s32)((u32)score * 2u);
                }
                if ((mode != 0xB8) && ((states[i] == 2) || (states[i] == 3))) {
                    score = -1;
                }
            }
            if (mode == 0xB7) {
                if (score == -1) {
                    score = distance;
                }
                if (actor[0x13C] != 0) {
                    if (i >= primaryCount) {
                        score = (s32)((u32)score * 2u);
                    }
                    score = score / (s32)((u32)func_150859AC((s16)i, 6) + 2u);
                    primaryCount = D_8008FD90;
                }
            }
            if ((i < primaryCount) && (score != -1)) {
                score = (s32)((f32)score * *(f32 *)((u8 *)D_800D23B0 + 0x16B8));
            }
            if (score >= 0) {
                position = 0;
                while ((position < used) && (scores[start + position] < score)) {
                    position++;
                }
                for (copy = used; copy > position; copy--) {
                    neighbors[start + copy] = neighbors[start + copy - 1];
                    scores[start + copy] = scores[start + copy - 1];
                }
                neighbors[start + position] = i;
                used++;
                scores[start + position] = score;
            }
            if (distance < nearest) {
                nearest = distance;
            }
        }
    }
    for (i = used; i < 16; i++) {
        neighbors[start + i] = -1;
    }
    state = (u8 *)D_800D23B0;
    if ((u32)state + 0x51Cu != 0) {
        *(s32 *)(state + slot * 4 + 0x51C) = nearest;
    }
    return 0;
}
'''
SELECTED = INITIAL
compile_profile, link_owner = previous.compile_profile, previous.link_owner


def shapes():
    """Bounded source-only experiments; none silently replaces SELECTED."""
    yield 'pointer-null', INITIAL.replace('(u32)state + 0x51Cu != 0', '(s32 *)(state + 0x51C) != NULL')
    fill = INITIAL.replace('i < 16; i++', 'i != 64; i += 4').replace(
        'for (i = used;', 'for (i = used * 4;').replace(
        'neighbors[start + i] = -1;', '*(s32 *)((u8 *)neighbors + start * 4 + i) = -1;').replace(
        'for (i = used * 4; i != 64;', 'for (i = used * 4; i < 64;')
    yield 'byte-fill', fill
    yield 'byte-fill-narrow', fill.replace('s32 primaryCount;', 's8 primaryCount;')
    yield 'byte-fill-narrow-slot', fill.replace('s32 primaryCount;', 's8 primaryCount;').replace('s32 slot;', 's8 slot;')
    yield 'byte-copy', fill.replace('    s32 copy;', '    s32 copy;\n    s32 offset;').replace(
        '                    neighbors[start + copy] = neighbors[start + copy - 1];\n'
        '                    scores[start + copy] = scores[start + copy - 1];',
        '                    offset = (start + copy) * 4;\n'
        '                    *(s32 *)((u8 *)neighbors + offset) = *(s32 *)((u8 *)neighbors + offset - 4);\n'
        '                    *(s32 *)((u8 *)scores + offset) = *(s32 *)((u8 *)scores + offset - 4);')
    yield 'narrow-primary', INITIAL.replace('s32 primaryCount;', 's8 primaryCount;')
    yield 'early-minimum', INITIAL.replace('    used = 0;\n    nearest = 32000;\n', '').replace(
        '    state = (u8 *)D_800D23B0;\n    groups',
        '    used = 0;\n    nearest = 32000;\n    state = (u8 *)D_800D23B0;\n    groups',1)


def freeze(root, out):
    with patch.object(previous, 'INPUTS', INPUTS):
        return previous.freeze(root, out)


def recovered_owner(before, body=None):
    if before.count(ORIGINAL) != 1:
        raise ValueError('Unknown neighbor-row predecessor')
    return before.replace(ORIGINAL, DECLARATIONS + '\n' + (SELECTED if body is None else body).rstrip())


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]): raise ValueError('Nonzero neighbor-row alignment tail')
    return raw[:end * 4], {at - f['value']: entries for at, entries in bindings.items()
        if f['value'] <= at < f['value'] + end * 4}


def compile_candidate(root, out, name='selected', body=None, normal=False, whole=False):
    values = freeze(root, out)
    unit = recovered_owner(values[SOURCE].decode(), body) if whole else (
        '#include <ultra64.h>\n' + DECLARATIONS + (SELECTED if body is None else body))
    obj, diagnostics = compile_profile(root, out, unit, name, normal)
    raw, bindings = payload(obj)
    image, functions = link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (len(raw) // 4), image, functions[FUNCTION]['value']))
    truth = struct.unpack_from('>336I', values['conker/conker.us.bin'], ROM)
    row = dict(words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_SHA256=hashlib.sha256(raw).hexdigest(), bindings=bindings)
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--normal', action='store_true'); p.add_argument('--whole', action='store_true')
    p.add_argument('--shapes', action='store_true')
    args = p.parse_args(); root = Path(__file__).resolve().parents[2]
    if args.shapes:
        rows = {}
        for name,body in shapes():
            _,_,row = compile_candidate(root,root/BUILD/'shape-screen',name,body,normal=True)
            rows[name] = {k:v for k,v in row.items() if k!='bindings'}
        (root/BUILD/'shape-screen/screen.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(rows,indent=2)); raise SystemExit(0)
    _, _, row = compile_candidate(root, root / BUILD, 'selected' + ('-normal' if args.normal else ''),
        normal=args.normal, whole=args.whole)
    print(json.dumps({k: v for k, v in row.items() if k != 'bindings'}, indent=2))
