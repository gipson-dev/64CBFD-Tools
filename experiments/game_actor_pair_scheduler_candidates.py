"""Screen complete semantic bodies for the retail actor-pair scheduler."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_pair_visibility_candidates as previous
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-actor-pair-scheduler'
SOURCE, OWNER = previous.SOURCE, previous.OWNER
FUNCTION, ENTRY, ROM, WORDS = 'func_1508C5B8', 0x1508C5B8, 0xB9A68, 261
ORIGINAL = 's32 func_1508C5B8() {\n    return 0;\n}'
INPUTS = dict(previous.INPUTS)
INPUTS.update({
    SOURCE: '48ed16dc763cd0986c53a00631daa1a4ec3d613515956d5b4879b7b25bdef00d',
    'conker/retail_word_patches.us.csv': 'c963921a32c3ba48666d7be2cac4d99e115c6bed56e79c1afc2c8f37b9c33cc4',
    'conker/build/conker.us.elf': 'bdbf803a28dcf347719ce65c670e299aba0fe870ac8936653b5d10e2691ddef7',
})
DECLARATIONS = '''extern s32 D_800D23B0;
extern s8 D_8008FD90;
extern s8 D_8008FD8C;
extern u16 D_800D18A0;
extern u8 D_800CC2D0[];
extern f32 D_8009DA68;
void func_1508C1A4(s32 first, s32 second);
'''
INITIAL = '''/* Refresh three ranked pairs per primary actor, then advance the pair cursor. */
s32 func_1508C5B8(s32 rowIndex, s32 pairBudget) {
    f32 costs[4];
    s8 choices[4];
    s32 *groups;
    u8 *actor;
    u8 *cursorActor;
    u32 *row;
    s32 primary;
    s32 candidate;
    s32 primaryCount;
    s32 count;
    s32 rank;
    s32 i;
    s32 attempts;
    s8 displaced;
    u8 first;
    u8 second;
    u8 kind;
    f32 x;
    f32 dx;
    f32 dz;
    f32 cost;
    f32 displacedCost;

    first = ((u8 *)D_800D23B0)[0x1700];
    second = ((u8 *)D_800D23B0)[0x1701];
    groups = (s32 *)((u8 *)D_800D23B0 + 0xE64);
    if (pairBudget != 0) {
        primaryCount = D_8008FD90;
        primary = 0;
        actor = D_800CC2D0;
        if (primaryCount > 0) {
            do {
                x = *(f32 *)(actor + 0x14);
                count = D_8008FD8C;
                for (i = 0; i < 3; i++) {
                    choices[i] = -1;
                    costs[i] = D_8009DA68;
                }
                for (candidate = primaryCount; candidate < count; candidate++) {
                    if ((groups[primary] != groups[candidate]) &&
                            !(*(u32 *)((u8 *)D_800D23B0 + primary * 4 + 0x16C0) &
                                (0x10001u << ((u32)candidate & 31)))) {
                        /* Retail uses this primary actor's X in both deltas. */
                        dx = x - x;
                        dz = x - *(f32 *)(actor + 0x1C);
                        if (primary == *(s32 *)((u8 *)D_800D23B0 + candidate * 4 + 0x11C)) {
                            dx *= 0.5f;
                            dz *= 0.5f;
                        }
                        cost = dx * dx + dz * dz;
                        if (cost < costs[2]) {
                            rank = 2;
                            displacedCost = costs[rank];
                            do {
                                displaced = choices[rank];
                                costs[rank + 1] = displacedCost;
                                choices[rank] = candidate;
                                costs[rank] = cost;
                                choices[rank + 1] = displaced;
                                rank--;
                                if (rank < 0) {
                                    break;
                                }
                                displacedCost = costs[rank];
                            } while (cost < displacedCost);
                        }
                    }
                }
                for (i = 0; i < 3; i++) {
                    candidate = choices[i];
                    if (candidate != -1) {
                        row = (u32 *)((u8 *)D_800D23B0 + primary * 4 + 0x16C0);
                        *row &= ~(0x10001u << ((u32)candidate & 31));
                        row = (u32 *)((u8 *)D_800D23B0 + candidate * 4 + 0x16C0);
                        *row &= ~(0x10001u << ((u32)primary & 31));
                        func_1508C1A4(primary, candidate);
                    }
                }
                primary++;
                actor += 0x32C;
                primaryCount = D_8008FD90;
            } while (primary < primaryCount);
        }
    }
    if (pairBudget != 0) {
        cursorActor = D_800CC2D0 + first * 0x32C;
        do {
            kind = cursorActor[0x128];
            attempts = 0;
            do {
                second++;
                count = D_8008FD8C;
                if (second >= count) {
                    first++;
                    if (first >= count - 1) {
                        first = 0;
                    }
                    second = first + 1;
                    cursorActor = D_800CC2D0 + first * 0x32C;
                    kind = cursorActor[0x128];
                }
                row = (u32 *)((u8 *)D_800D23B0 + first * 4 + 0x16C0);
                *row &= ~(0x10001u << ((u32)second & 31));
                row = (u32 *)((u8 *)D_800D23B0 + second * 4 + 0x16C0);
                *row &= ~(0x10001u << ((u32)first & 31));
                attempts++;
                if (attempts >= 64) {
                    break;
                }
            } while ((D_800D18A0 & ((1u << ((u32)first & 31)) |
                    (1u << ((u32)second & 31)))) ||
                (kind == D_800CC2D0[second * 0x32C + 0x128]));
            func_1508C1A4(first, second);
            pairBudget = (s32)((u32)pairBudget - 1u);
        } while (pairBudget != 0);
    }
    ((u8 *)D_800D23B0)[0x1700] = first;
    ((u8 *)D_800D23B0)[0x1701] = second;
    return *(s32 *)((u8 *)D_800D23B0 + (u32)rowIndex * 4 + 0x16C0);
}
'''
SELECTED = INITIAL
compile_profile, link_owner = previous.compile_profile, previous.link_owner


def freeze(root, out):
    with patch.object(previous, 'INPUTS', INPUTS):
        return previous.freeze(root, out)


def recovered_owner(before, body=None):
    if before.count(ORIGINAL) != 1:
        raise ValueError('Unknown actor-pair scheduler predecessor')
    return before.replace(ORIGINAL, DECLARATIONS + '\n' + (SELECTED if body is None else body).rstrip()).replace(
        's32 func_1508C5B8();', 's32 func_1508C5B8(s32 rowIndex, s32 pairBudget);')


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero actor-pair scheduler alignment tail')
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
    yield 'implicit-shifts', INITIAL.replace('((u32)candidate & 31)', 'candidate').replace(
        '((u32)primary & 31)', 'primary').replace('((u32)first & 31)', 'first').replace(
        '((u32)second & 31)', 'second')
    cached = INITIAL.replace('    f32 x;\n', '    f32 sentinel;\n    f32 x;\n    f32 sameX;\n    f32 sameZ;\n').replace(
        '        if (primaryCount > 0) {', '        if (primaryCount > 0) {\n            sentinel = D_8009DA68;').replace(
        '                count = D_8008FD8C;', '                sameX = x;\n                sameZ = x;\n                count = D_8008FD8C;', 1).replace(
        'costs[i] = D_8009DA68;', 'costs[i] = sentinel;').replace('dx = x - x;', 'dx = sameX - x;').replace(
        'dz = x - *(f32 *)', 'dz = sameZ - *(f32 *)')
    yield 'cached-distinct-coordinates', cached
    shared = cached.replace('    u8 *cursorActor;\n', '').replace('cursorActor', 'actor')
    yield 'shared-actor', shared
    indexed = shared.replace(' + primary * 4 + 0x16C0);', ' + primary * 4);').replace(
        ' + candidate * 4 + 0x16C0);', ' + candidate * 4);').replace(
        ' + first * 4 + 0x16C0);', ' + first * 4);').replace(
        ' + second * 4 + 0x16C0);', ' + second * 4);').replace('*row &=', 'row[0x16C0 / 4] &=')
    yield 'indexed-row-fields', indexed


SELECTED = dict(candidates())['indexed-row-fields']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--normal', action='store_true')
    p.add_argument('--whole', action='store_true')
    p.add_argument('--screens', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    for name, body in candidates() if args.screens else [('selected', SELECTED)]:
        out = root / BUILD
        obj, words, row = compile_candidate(root, out, name + ('-normal' if args.normal else ''), body,
            normal=args.normal, whole=args.whole)
        print(json.dumps(dict(candidate=name, **{k: v for k, v in row.items() if k != 'bindings'})), flush=True)
