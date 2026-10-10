"""Measure complete tile updater coordinate/index shapes without touching production."""
import json
from pathlib import Path
from tools.experiments import game_actor_tile_updater_candidates as recovery

SELECTED = recovery.SELECTED


def candidates():
    yield 'baseline', SELECTED
    distinct = SELECTED.replace('    u8 *actor;', '    u8 *actor;\n    s16 *coordinates;').replace(
        '        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;',
        '        coordinates = (s16 *)D_800CC2D0 + (u32)slot * 0x196;').replace(
        'part++, actor += 2', 'part++, coordinates++').replace(
        '*(s16 *)(actor + 0x27A)', 'coordinates[0x13D]').replace(
        '*(s16 *)(actor + 0x27E)', 'coordinates[0x13F]')
    yield 'distinct-coordinates', distinct
    yield 'distinct-byte-kind', distinct.replace('s32 kind, selected, part;', 'u8 kind;\n    s32 selected, part;')
    yield 'distinct-unsigned-halfwords', distinct.replace('s16 *coordinates', 'u16 *coordinates').replace(
        'coordinates = (s16 *)', 'coordinates = (u16 *)')
    bare = SELECTED.replace('    actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;\n    kind = actor[4];',
        '    kind = D_800CC2D0[slot].id;').replace('return func_150C3160(commands, actor);',
        'return func_150C3160(commands, (u8 *)&D_800CC2D0[slot]);')
    yield 'kind-first', bare
    for name, expression in (
            ('halfword-index', '(s16 *)D_800CC2D0 + (u32)slot * 0x196'),
            ('actor-index', '(s16 *)&D_800CC2D0[slot]'),
            ('byte-index', '(s16 *)((u8 *)D_800CC2D0 + (u32)slot * 0x32C)'),
            ('shift-index', '(s16 *)D_800CC2D0 + (((u32)slot * 0x32C) >> 1)')):
        body = bare.replace('    u8 *actor;', '    s16 *coordinates;').replace(
            '        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;', '        coordinates = '+expression+';').replace(
            'part++, actor += 2', 'part++, coordinates++').replace(
            '*(s16 *)(actor + 0x27A)', 'coordinates[0x13D]').replace(
            '*(s16 *)(actor + 0x27E)', 'coordinates[0x13F]')
        yield name, body
        yield name+'-signed-inputs', body.replace('u16 left, top, right, bottom;',
            's32 x, y;\n    u16 left, top, right, bottom;').replace(
            'left = coordinates[0x13D];', 'x = coordinates[0x13D];').replace(
            'top = coordinates[0x13F];', 'y = coordinates[0x13F];').replace(
            'left += 2;', 'left = x + 2;').replace('top += 2;', 'top = y + 2;')
    yield 'pointer-distinct-multiply', bare.replace(
        '        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;',
        '        actor = (u8 *)D_800CC2D0 + ((u32)slot * 0x196) * 2;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-tile-updater-layout'
    records=[]
    for name,body in candidates():
        meta,words=compile_candidate(root,out,name,body)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
