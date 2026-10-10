"""Recover selector frame/storage shapes without changing the semantic baseline."""
import itertools
import json
from pathlib import Path

from tools.experiments import game_actor_segment_selector_candidates as recovery

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE = recovery.FUNCTION, recovery.SOURCE
BASE = recovery.SELECTED


def addressing(body, first, second):
    return body.replace('D_800D1C90[identity][index * 3 + cursor[0x6C] + 8]',first).replace(
        'D_800D1C90[identity][index * 3 + 10]',second)


def candidates():
    shapes=(
        ('addition', 'D_800D1C90[identity][index + index * 2 + cursor[0x6C] + 8]',
            'D_800D1C90[identity][index * 2 + index + 10]'),
        ('pointer-sum', '(D_800D1C90[identity] + index * 2)[index + cursor[0x6C] + 8]',
            '(D_800D1C90[identity] + index)[index * 2 + 10]'),
        ('pointer-sub', '(D_800D1C90[identity] + ((u32)index << 2))[cursor[0x6C] + 8 - index]',
            '(D_800D1C90[identity] - index)[index * 4 + 10]'),
        ('address-first', '(D_800D1C90[identity] + index * 4 - index)[cursor[0x6C] + 8]',
            '(D_800D1C90[identity] + index * 4 - index)[10]'),
        ('address-second', 'D_800D1C90[identity][index * 3 + cursor[0x6C] + 8]',
            '(D_800D1C90[identity] + index * 4 - index)[10]'),
        ('shift-sub', 'D_800D1C90[identity][((u32)index << 2) - index + cursor[0x6C] + 8]',
            '(D_800D1C90[identity] + (u32)index * 4 - index)[10]'),
        ('negative-index', '(D_800D1C90[identity] - index)[index * 4 + cursor[0x6C] + 8]',
            '(D_800D1C90[identity] - index)[index * 4 + 10]'))
    for name,first,second in shapes:
        body=addressing(BASE,first,second)
        for order in ('original','reverse'):
            if order=='reverse':
                body=body.replace('    s32 pairValues[2];\n    u8 selected[2];',
                    '    u8 selected[2];\n    s32 pairValues[2];')
            yield name+'-'+order,body
    for name,pairs,selection,order in itertools.product(('plain','address-first'),(2,4,6),
            (2,4,8),('original','reverse')):
        body=BASE if name=='plain' else addressing(BASE,shapes[3][1],shapes[3][2])
        declarations='    s32 pairValues[%d];\n    u8 selected[%d];'%(pairs,selection)
        if order=='reverse': declarations='    u8 selected[%d];\n    s32 pairValues[%d];'%(selection,pairs)
        body=body.replace('    s32 pairValues[2];\n    u8 selected[2];',declarations)
        yield '%s-pair%d-selection%d-%s'%(name,pairs,selection,order),body
    for gap in (0,4,8,12,16):
        declaration='    struct { s32 pairValues[2]; '+('u8 gap[%d]; '%gap if gap else '')+'u8 selected[2]; } work;'
        body=addressing(BASE,shapes[3][1],shapes[3][2]).replace(
            '    s32 pairValues[2];\n    u8 selected[2];',declaration)
        body=body.replace('pairValues[','work.pairValues[').replace('selected[','work.selected[').replace(
            's32 work.pairValues[','s32 pairValues[').replace('u8 work.selected[','u8 selected[')
        yield 'structured-gap%d'%gap,body
    for name in ('address-first-original','address-second-original','shift-sub-original'):
        body=dict(candidates_without_registers())[name]
        yield name+'-register-commands',body.replace('Gfx *commands,','register Gfx *commands,')
        yield name+'-s32-id',body.replace('u8 identity;','s32 identity;')
    for name,body in (('plain',BASE),*tuple(candidates_without_registers())):
        scoped=body.replace('    s32 pairValues[2];\n','').replace(
            '            if (pair != NULL) {\n                pairValues[0]',
            '            if (pair != NULL) {\n                s32 pairValues[2];\n                pairValues[0]')
        yield name+'-scoped-pair',scoped
        value=scoped.replace('                s32 pairValues[2];',
            '                volatile s32 pairValues[2];\n                s32 value;').replace(
            '                if (pair != NULL) {\n                    if (pairValues[index]',
            '                value = pairValues[index];\n                if (pair != NULL) {\n                    if (value').replace(
            'selected[index] = pairValues[index];','selected[index] = value;')
        yield name+'-scoped-volatile-pair',value
        pair=scoped.replace('                s32 pairValues[2];',
            '                s32 pairValues[2];\n                s32 value;').replace(
            '                if (pair != NULL) {\n                    if (pairValues[index]',
            '                value = pairValues[index];\n                if (pair != NULL) {\n                    if (value').replace(
            'selected[index] = pairValues[index];','selected[index] = value;')
        yield name+'-scoped-cached-pair',pair
    for name,body in scoped_shapes():
        combined=body.replace(
            ''') {
                        selected[index] = pairValues[index];
                    } else if (cursor[0x6C] == 0) {''',
            ''' || cursor[0x6C] == 0) {''')
        yield name+'-combined',combined
        for gap in (4,8,12,16):
            for source in (body,combined):
                form=source.replace('    u8 selected[2];',
                    '    struct { u8 reserved[%d]; u8 selected[2]; } selection;'%gap).replace(
                    'selected[','selection.selected[').replace('u8 selection.selected[','u8 selected[')
                yield '%s-%s-selection-gap%d'%(name,'combined' if source==combined else 'separate',gap),form
        old='''                    if (pairValues[index] == D_800D1C90[identity][index * 3 + 10]) {
                        selected[index] = pairValues[index];
                    } else if (cursor[0x6C] == 0) {
                        selected[index] = pairValues[index];
                    }'''
        condition=body.split('                    if (pairValues[index] == ',1)[1].split(') {',1)[0]
        old=old.replace('pairValues[index] == D_800D1C90[identity][index * 3 + 10]',
            'pairValues[index] == '+condition)
        for variant,replacement in (
                ('early-continue','''                    if (pairValues[index] != %s && cursor[0x6C] != 0) {
                        continue;
                    }
                    selected[index] = pairValues[index];'''%condition),
                ('nested-continue','''                    if (pairValues[index] == %s) {
                        selected[index] = pairValues[index];
                    } else {
                        if (cursor[0x6C] != 0) { continue; }
                        selected[index] = pairValues[index];
                    }'''%condition)):
            yield name+'-'+variant,body.replace(old,replacement)
        for count in (3,4,5,6):
            yield '%s-scoped-pair%d'%(name,count),body.replace('s32 pairValues[2];','s32 pairValues[%d];'%count)
        for count in (4,8,12,16):
            yield '%s-scoped-selection%d'%(name,count),body.replace('u8 selected[2];','u8 selected[%d];'%count)


def scoped_shapes():
    for name,body in (('plain',BASE),*tuple(candidates_without_registers())):
        yield name,body.replace('    s32 pairValues[2];\n','').replace(
            '            if (pair != NULL) {\n                pairValues[0]',
            '            if (pair != NULL) {\n                s32 pairValues[2];\n                pairValues[0]')


def candidates_without_registers():
    # Materialize the first address forms without recursively expanding the extra qualifiers.
    for name,first,second in (
            ('address-first-original','(D_800D1C90[identity] + index * 4 - index)[cursor[0x6C] + 8]',
                '(D_800D1C90[identity] + index * 4 - index)[10]'),
            ('address-second-original','D_800D1C90[identity][index * 3 + cursor[0x6C] + 8]',
                '(D_800D1C90[identity] + index * 4 - index)[10]'),
            ('shift-sub-original','D_800D1C90[identity][((u32)index << 2) - index + cursor[0x6C] + 8]',
                '(D_800D1C90[identity] + (u32)index * 4 - index)[10]')):
        yield name,addressing(BASE,first,second)


def compile_candidate(root,out,name,body=BASE,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-segment-selector-layout'
    records=[]
    for name,body in candidates():
        meta,_=compile_candidate(root,out,name,body)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
