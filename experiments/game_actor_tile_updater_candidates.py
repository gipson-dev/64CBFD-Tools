"""Complete actor texture-tile updater and measured retail compiler candidates."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502F9FC, 0x5CEAC, 123
FUNCTION, SOURCE = 'func_1502F9FC', 'conker/src/game/generated_58F80.c'
ORIGINAL = 'Gfx *func_1502F9FC() {\n    return 0;\n}'
DECLARATIONS = '''typedef struct { u32 address; u32 reserved[2]; } ActorSegmentRow58F80;
typedef struct ActorDisplay58F80 {
    s32 active; u8 id; u8 state; u8 pad6[0x17E];
    u32 flags; u8 pad188[0x1A4];
} ActorDisplay58F80;
extern ActorDisplay58F80 D_800CC2D0[26];
extern ActorSegmentRow58F80 *D_800C5338[];
Gfx *func_150C3160(Gfx *, u8 *);
'''
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800C5338=0x800C5338, func_150C3160=0x150C3160)
SELECTED = '''Gfx *func_1502F9FC(Gfx *commands, s32 slot) {
    u8 *actor;
    u8 *record;
    s32 kind, selected, part;
    u16 left, top, right, bottom;

    actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
    kind = actor[4];
    if (kind == 0x89 || kind == 0xBA) {
        return func_150C3160(commands, actor);
    }
    if (kind == 0) {
        selected = 14;
    } else if (kind == 0x96) {
        selected = 7;
    } else if (kind == 0x28) {
        selected = 4;
    } else if (kind == 1 || kind == 2 || kind == 3 || kind == 4) {
        selected = 5;
    } else {
        selected = 0;
    }
    if (D_800C5338[kind] != NULL) {
        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
        for (part = 0; part != 2; part++, actor += 2) {
            record = (u8 *)D_800C5338[kind] + selected * 12;
            left = *(s16 *)(actor + 0x27A);
            top = *(s16 *)(actor + 0x27E);
            right = *(u16 *)(record + 8);
            bottom = *(u16 *)(record + 10);
            left += 2;
            top += 2;
            right = right * 4 - 2;
            bottom = bottom * 4 - 2;
            gDPSetTileSize(commands++, 5 - part, left, top, right, bottom);
        }
    }
    return commands;
}'''


def candidates():
    yield 'selected', SELECTED
    first, second = SELECTED.split('        actor = (u8 *)D_800CC2D0 + ', 1)
    signed_second = first + '        actor = (u8 *)D_800CC2D0 + ' + second.replace('(u32)slot', 'slot', 1)
    yield 'signed-second', signed_second
    combined = signed_second.replace('left = *(s16 *)(actor + 0x27A);', 'left = *(s16 *)(actor + 0x27A) + 2;').replace(
        'top = *(s16 *)(actor + 0x27E);', 'top = *(s16 *)(actor + 0x27E) + 2;').replace(
        '            left += 2;\n            top += 2;\n', '')
    yield 'signed-second-combined', combined
    yield 'signed-both-combined', combined.replace('(u32)slot', 'slot')
    yield 'combined-widths', combined.replace('right = *(u16 *)(record + 8);',
        'right = *(u16 *)(record + 8) * 4 - 2;').replace('bottom = *(u16 *)(record + 10);',
        'bottom = *(u16 *)(record + 10) * 4 - 2;').replace(
        '            right = right * 4 - 2;\n            bottom = bottom * 4 - 2;\n', '')
    indexed = SELECTED.replace('actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;',
        'actor = (u8 *)&D_800CC2D0[slot];').replace('kind = actor[4];', 'kind = D_800CC2D0[slot].id;')
    yield 'structured-actor', indexed
    yield 'structured-coordinates', indexed.replace('left = *(s16 *)(actor + 0x27A);',
        'left = *(s16 *)(actor + 0x27A) + 2;').replace('top = *(s16 *)(actor + 0x27E);',
        'top = *(s16 *)(actor + 0x27E) + 2;').replace('            left += 2;\n            top += 2;\n', '')
    yield 's16-coordinates', indexed.replace('u16 left, top, right, bottom;',
        's16 left, top;\n    u16 right, bottom;')
    coordinate_base = SELECTED.replace('        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;',
        '        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C + 0x27A;').replace(
        'actor + 0x27A', 'actor').replace('actor + 0x27E', 'actor + 4')
    yield 'coordinate-base', coordinate_base
    yield 'coordinate-base-combined', coordinate_base.replace('left = *(s16 *)(actor);',
        'left = *(s16 *)(actor) + 2;').replace('top = *(s16 *)(actor + 4);',
        'top = *(s16 *)(actor + 4) + 2;').replace('            left += 2;\n            top += 2;\n', '')
    yield 'count-variable', SELECTED.replace('kind, selected, part;', 'kind, selected, part, count;').replace(
        '    if (kind == 0) {', '    count = 2;\n    if (kind == 0) {').replace('part != 2', 'part != count')
    yield 'less-than', SELECTED.replace('part != 2', 'part < 2')
    yield 'indexed-actor', SELECTED.replace('part++, actor += 2', 'part++').replace(
        'actor + 0x27A', 'actor + 0x27A + part * 2').replace('actor + 0x27E', 'actor + 0x27E + part * 2')
    yield 'byte-kind', SELECTED.replace('s32 kind, selected, part;', 'u8 kind;\n    s32 selected, part;')
    yield 'volatile-kind', SELECTED.replace('s32 kind, selected, part;', 'volatile s32 kind;\n    s32 selected, part;')
    yield 'decrement-count', SELECTED.replace('for (part = 0; part != 2; part++, actor += 2)', 
        'for (part = 2; part != 0; part--, actor += 2)').replace('5 - part', 'part + 3')
    for typ in ('u32', 's32', 's16'):
        yield 'coordinates-' + typ, SELECTED.replace('u16 left, top, right, bottom;', typ + ' left, top, right, bottom;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def copied_owner(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count('Gfx *func_1502F9FC();') != 1:
        raise ValueError('stale actor tile owner')
    return before.replace('Gfx *func_1502F9FC();', 'Gfx *func_1502F9FC(Gfx *, s32);').replace(
        ORIGINAL, 'Gfx *func_150C3160(Gfx *, u8 *);\n\n' + body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-tile-updater'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()

