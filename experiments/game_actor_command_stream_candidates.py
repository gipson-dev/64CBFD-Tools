"""Recover the full attached/global actor command-stream writer."""
import argparse
import csv
import io
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_type_dispatch_candidates import compile_owner
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=0x150341BC,0x6166C,97
FUNCTION,SOURCE='func_150341BC','conker/src/game/generated_61490.c'
SYMBOLS=dict(D_800CC2D0=0x800CC2D0,D_800C3E78=0x800C3E78,D_80097D14=0x80097D14)
DECLARATIONS='extern u8 D_800CC2D0[];\nextern u8 D_800C3E78[];\nextern f32 D_80097D14;\n'
OWNER_DECLARATIONS='extern u8 D_800C3E78[];\nextern f32 D_80097D14;\n'
ORIGINAL='s32 func_150341BC() {\n    return 0;\n}'
SELECTED='''u8 *func_150341BC(u8 *cursor, s32 slot) {
    u8 *actor = D_800CC2D0 + (u32)slot * 0x32C;
    u8 *attached = *(u8 **)(actor + 0x31C);
    s16 amount;
    s32 extra;

    if (attached != NULL && (*(u16 *)(actor + 0x2F8) & 0x80) == 0) {
        amount = (s32)(*(f32 *)(actor + 0x54) * D_80097D14);
        if (*(u16 *)(actor + 0x84) == 0x42 || *(u16 *)(actor + 0x84) == 0x14 || *(u16 *)(actor + 0x84) == 0x76) {
            *(s16 *)cursor = 10;
            *(s16 *)(cursor + 2) = amount;
            cursor += 4;
            *(s16 *)cursor = 4;
            *(s16 *)(cursor + 2) = -amount;
            cursor += 4;
        } else {
            extra = 4;
            if (attached[0x78] == 10) {
                extra = 0;
            }
            *(s16 *)cursor = 6 + extra;
            *(s16 *)(cursor + 2) = amount;
            cursor += 4;
        }
    }
    if (*(s8 *)(actor + 0x1D1) != 0) {
        *(s16 *)cursor = 6;
        cursor += 4;
        *(s16 *)(cursor - 2) = *(s8 *)(actor + 0x1D1) * 200;
    }
    if (*(u8 **)(D_800CC2D0 + D_800C3E78[0] * 0x32C + 0x31C) != NULL &&
        *(s16 *)(*(u8 **)(D_800CC2D0 + D_800C3E78[0] * 0x32C + 0x31C) + 0x12) != 0) {
        *(s16 *)cursor = 8;
        cursor += 4;
        *(s16 *)(cursor - 2) = -*(s16 *)(*(u8 **)(D_800CC2D0 + D_800C3E78[0] * 0x32C + 0x31C) + 0x12);
    }
    return cursor;
}'''


BASE=SELECTED


def recovered_owner(source,body=None):
    body=SELECTED if body is None else body
    if source.count(ORIGINAL)==1:
        source=source.replace(ORIGINAL,body)
    elif source.count(body)!=1:
        raise ValueError('Expected the known stream placeholder or complete body')
    if OWNER_DECLARATIONS not in source:
        source=source.replace('extern u8 D_800CC2D0[];','extern u8 D_800CC2D0[];\n'+OWNER_DECLARATIONS.rstrip(),1)
    return source


def compile_candidate(root,out,name,body=None):
    body=SELECTED if body is None else body
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        record,words=compiler.compile_candidate(root,out,name,body)
    record['frame']=(-words[0])&65535 if words[0]>>16==0x27BD else 0
    return record,words


def source_screens(SELECTED):
    yield 'selected',SELECTED
    yield 'extra-if-else',SELECTED.replace('            extra = 4;\n            if (attached[0x78] == 10) {\n                extra = 0;\n            }',
        '            if (attached[0x78] == 10) {\n                extra = 0;\n            } else {\n                extra = 4;\n            }')
    yield 'extra-ternary',SELECTED.replace('            extra = 4;\n            if (attached[0x78] == 10) {\n                extra = 0;\n            }',
        '            extra = attached[0x78] == 10 ? 0 : 4;')
    yield 'type-local',SELECTED.replace('    s16 amount;','    u16 type;\n    s16 amount;').replace(
        '        if (*(u16 *)(actor + 0x84) == 0x42 || *(u16 *)(actor + 0x84) == 0x14 || *(u16 *)(actor + 0x84) == 0x76)',
        '        type = *(u16 *)(actor + 0x84);\n        if (type == 0x42 || type == 0x14 || type == 0x76)')
    view=SELECTED.replace('D_800CC2D0 + (u32)slot * 0x32C','((u8 (*)[0x32C])D_800CC2D0)[slot]')
    yield 'actor-array-view',view
    yield 'signed-first-product',SELECTED.replace('(u32)slot * 0x32C','slot * 0x32C')
    start=SELECTED.index('        if (*(u16 *)(actor + 0x84)')
    middle=SELECTED.index('        } else {',start)
    end=SELECTED.index('\n    }\n    if (*(s8 *)',middle)
    pair=SELECTED[SELECTED.index('\n',start)+1:middle]
    normal=SELECTED[middle+len('        } else {\n'):end-len('        }')]
    condition='        if (*(u16 *)(actor + 0x84) != 0x42 && *(u16 *)(actor + 0x84) != 0x14 && *(u16 *)(actor + 0x84) != 0x76) {\n'
    normal_first=SELECTED[:start]+condition+normal+'        } else {\n'+pair+'        }'+SELECTED[end:]
    yield 'normal-first',normal_first
    yield 'normal-first-array',normal_first.replace('D_800CC2D0 + (u32)slot * 0x32C','((u8 (*)[0x32C])D_800CC2D0)[slot]')
    yield 'normal-first-signed',normal_first.replace('(u32)slot * 0x32C','slot * 0x32C')
    normal_if_else=normal_first.replace('            extra = 4;\n            if (attached[0x78] == 10) {\n                extra = 0;\n            }',
        '            if (attached[0x78] == 10) {\n                extra = 0;\n            } else {\n                extra = 4;\n            }')
    yield 'normal-first-if-else',normal_if_else
    for name,expression in (('factored-stride','((u32)slot * 203U << 2)'),
            ('word-view-stride','((u32)slot * 203U)')):
        body=normal_if_else.replace('(u32)slot * 0x32C',expression)
        if name=='word-view-stride':
            body=normal_if_else.replace('D_800CC2D0 + (u32)slot * 0x32C',
                '(u8 *)((u32 *)D_800CC2D0 + (u32)slot * 203U)')
        yield name,body
    yield from remaining_screens(normal_first,normal_if_else)


def candidates():
    yield from source_screens(BASE)


def normalized_word(word,offset):
    # Split the combined cursor step, then relocate crossing branches and GPR roles.
    op,fn=word>>26,word&63
    if offset==0x2C:
        assert word==0x000E7880
        return 0x000E7080
    if offset<0x30:
        return word
    if op==0:
        if fn not in (0,3,8,18,25,33,35,37):
            raise ValueError('Unexpected register-cycle instruction')
        fields=(21,16,11)
    elif op in (4,5,9,12,13,15,32,33,35,36,37,41,20,21):
        fields=(21,16)
    elif op==49:
        fields=(21,)
    elif op==17:
        fields=(16,) if word>>21&31 in (0,4) else ()
    else:
        raise ValueError('Unexpected opcode in register cycle')
    cycle={8:25,**{r:r-1 for r in range(9,16)},24:15,25:24}
    for shift in fields:
        register=word>>shift&31
        word=(word&~(31<<shift))|(cycle.get(register,register)<<shift)
    if offset in (0x12C,0x160):
        assert op==0 and fn==33
        left,right=word>>21&31,word>>16&31
        word=(word&~0x03FF0000)|(right<<21)|(left<<16)
    if op in (4,5,20,21):
        immediate=word&65535
        target=offset+4+((immediate^0x8000)-0x8000)*4
        origin=offset+(4 if offset>=0xD8 else 0)
        target+=4 if target>=0xD8 else 0
        word=(word&~65535)|(((target-origin-4)//4)&65535)
    if offset in (0xD8,0xDC,0xE0):
        expected={0xD8:0xA4CD0004,0xDC:0xA4CE0006,0xE0:0x24C60008}
        assert word==expected[offset]
        word=(word&~65535)|{0xD8:0,0xDC:2,0xE0:4}[offset]
    return word


def normalize(words):
    assert len(words)==96 and words[0xD4//4]==0xA4C40002
    result=[]
    for i,word in enumerate(words):
        result.append(normalized_word(word,i*4))
        if i*4==0xD4:
            result.append(0x24C60004)
    assert len(result)==WORDS
    return result


def guard_rows(obj):
    text,functions,relocations=parse_object(obj)
    meta=functions[FUNCTION]
    assert meta['size']==384
    words=struct.unpack_from('>96I',text,meta['value'])
    rows=[]
    for i,word in enumerate(words):
        offset=i*4
        replacement=normalized_word(word,offset)
        insert=0x24C60004 if offset==0xD4 else None
        if replacement==word and insert is None:
            continue
        assert not relocations.get(meta['value']+offset)
        rows.append(dict(filename='generated_61490',function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%word,replacement='0x%08X'%replacement,
            expected_relocations='-',replacement_relocations='-',
            note='Restore command cursor split and closed scratch GPR cycle with branch relocation',
            insert_after='' if insert is None else '0x%08X'%insert,insert_after_relocations='',omit='false'))
    return rows


def guard_bytes(before,obj):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(row['function']==FUNCTION for row in reader):
        raise ValueError('Command stream guards already installed')
    tail=io.StringIO()
    writer=csv.DictWriter(tail,fieldnames=reader.fieldnames,lineterminator='\n')
    writer.writerows(guard_rows(obj))
    return before+tail.getvalue().encode()


def remaining_screens(normal_first,normal_if_else):
    factored=normal_if_else.replace('(u32)slot * 0x32C','((u32)slot * 203U << 2)')
    yield 'register-slot',factored.replace('s32 slot)','register s32 slot)')
    yield 'unsigned-register-slot',factored.replace('s32 slot)','register u32 slot)')
    halfword=factored.replace('u8 *func_150341BC(u8 *cursor','s16 *func_150341BC(s16 *cursor').replace(
        '*(s16 *)(cursor + 2)','cursor[1]').replace('*(s16 *)(cursor - 2)','cursor[-1]').replace(
        '*(s16 *)cursor','*cursor').replace('cursor += 4;','cursor += 2;')
    yield 'halfword-cursor',halfword
    yield 'halfword-postincrement',halfword.replace('            cursor[1] = amount;\n            cursor += 2;',
        '            *++cursor = amount;\n            cursor++;').replace(
        '            cursor[1] = -amount;\n            cursor += 2;',
        '            *++cursor = -amount;\n            cursor++;')
    command=factored.replace('u8 *func_150341BC(u8 *cursor','Command341BC *func_150341BC(Command341BC *cursor').replace(
        '*(s16 *)(cursor + 2)','cursor->value').replace('*(s16 *)(cursor - 2)','cursor[-1].value').replace(
        '*(s16 *)cursor','cursor->command').replace('cursor += 4;','cursor++;')
    command='typedef struct { s16 command, value; } Command341BC;\n'+command
    yield 'command-record-cursor',command
    yield 'command-record-postincrement',command.replace('            cursor->value = amount;\n            cursor++;',
        '            (cursor++)->value = amount;').replace(
        '            cursor->value = -amount;\n            cursor++;','            (cursor++)->value = -amount;')
    yield 'integer-actor',normal_if_else.replace('u8 *actor = D_800CC2D0 +','u32 actor = (u32)D_800CC2D0 +')
    yield 'integer-actor-factored',factored.replace('u8 *actor = D_800CC2D0 +','u32 actor = (u32)D_800CC2D0 +')
    yield 'integer-actor-u32-product',normal_if_else.replace('u8 *actor = D_800CC2D0 +','u32 actor = (u32)D_800CC2D0 +').replace('slot * 0x32C','slot * 0x32CU')
    offset=factored.replace('    u8 *actor = D_800CC2D0 + ((u32)slot * 203U << 2);',
        '    u32 offset = (u32)slot * 203U;\n    u8 *actor;').replace(
        '    u8 *attached = *(u8 **)(actor + 0x31C);','    u8 *attached;').replace(
        '    s32 extra;','    s32 extra;\n\n    offset <<= 2;\n    actor = D_800CC2D0 + offset;\n    attached = *(u8 **)(actor + 0x31C);')
    yield 'offset-assignment',offset
    yield 'offset-register',offset.replace('u32 offset =','register u32 offset =')
    for name,body in (('address-increments',factored),('offset-address-increments',offset)):
        yield name,body.replace('cursor += 4;','cursor = (u8 *)((u32)cursor + 4);')
    yield 'word-increments',factored.replace('cursor += 4;','cursor = (u8 *)((s16 *)cursor + 2);')
    for name,body in (('integer-cursor',normal_if_else),('integer-cursor-factored',normal_if_else.replace(
            '(u32)slot * 0x32C','((u32)slot * 203U << 2)'))):
        body=body.replace('u8 *cursor, s32 slot','u8 *output, s32 slot').replace(
            '    u8 *actor =','    u32 cursor = (u32)output;\n    u8 *actor =').replace(
            '    return cursor;','    return (u8 *)cursor;')
        yield name,body
    for name,body in (('pair-postincrement',normal_first),('pair-postincrement-array',normal_first.replace(
            'D_800CC2D0 + (u32)slot * 0x32C','((u8 (*)[0x32C])D_800CC2D0)[slot]'))):
        body=body.replace('            *(s16 *)(cursor + 2) = amount;\n            cursor += 4;',
            '            cursor += 4;\n            *(s16 *)(cursor - 2) = amount;').replace(
            '            *(s16 *)(cursor + 2) = -amount;\n            cursor += 4;',
            '            cursor += 4;\n            *(s16 *)(cursor - 2) = -amount;')
        yield name,body


SELECTED=dict(candidates())['factored-stride']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-stream'
    out.mkdir(exist_ok=True)
    measurements=[]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        if args.filter and args.filter not in name:
            continue
        record,_=compile_candidate(root,out,name,body)
        measurements.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],record['pool_bytes'],flush=True)
    (out/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')


if __name__=='__main__':
    main()
