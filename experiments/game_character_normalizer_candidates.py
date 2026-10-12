"""Recover byte normalization and the original 95-entry glyph lookup."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15042C40, 0x700F0, 68
TABLE, TABLE_ROM = 0x80085930, 0x22A3F0
FUNCTION, SOURCE = 'func_15042C40', 'conker/src/game/generated_6E770.c'
ORIGINAL = 's32 func_15042C40() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 D_80085930;
extern u8 D_80085931;
extern u8 D_80085932;
extern u8 D_80085933[];
'''
SYMBOLS = dict(D_80085930=TABLE,D_80085931=TABLE+1,D_80085932=TABLE+2,D_80085933=TABLE+3)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3','-Wo,-loopunroll,0'))
BASE = '''s32 func_15042C40(u8 character) {
    u8 normalized;
    s32 index;
    u8 *cursor;

    if (character >= 0x61 && character < 0x7B) {
        normalized = character - 0x20;
    } else {
        normalized = character;
    }
    if (character == 0x20) {
        return 0x60;
    }
    if (normalized == D_80085930) {
        return 0;
    }
    if (normalized == D_80085931) {
        return 1;
    }
    if (normalized == D_80085932) {
        return 2;
    }
    index = 3;
    cursor = D_80085933;
    do {
        if (normalized == cursor[0]) {
            return index;
        }
        if (normalized == cursor[1]) {
            return index + 1;
        }
        if (normalized == cursor[2]) {
            return index + 2;
        }
        if (normalized == cursor[3]) {
            return index + 3;
        }
        index += 4;
        cursor += 4;
    } while (index != 0x5F);
    return character;
}'''
SELECTED = BASE.replace('    u8 normalized;', '    u8 original = character;\n    u8 normalized;').replace(
    '    return character;', '    return original;').replace(
    '    index = 3;\n    cursor = D_80085933;', '    cursor = D_80085933;\n    index = 3;')
for _suffix in ('30','31','32'):
    SELECTED=SELECTED.replace('normalized == D_800859'+_suffix,'D_800859'+_suffix+' == normalized')
GUARD_ROWS = [('generated_6E770',FUNCTION,'0x%03X'%(index*4),'0x%08X'%expected,
    '0x%08X'%replacement,'-','-','Normalize glyph lookup cached byte and closed scratch allocation',
    '','','false') for index,expected,replacement in (
    (6,0x2861007B,0x2881007B),(8,0x2462FFE0,0x2482FFE0),(12,0x308200FF,0x306200FF),
    (35,0x24060003,0x24040003),(38,0x2407005F,0x2406005F),(43,0x00C01025,0x00801025),
    (48,0x24C20001,0x24820001),(53,0x24C20002,0x24820002),(56,0x24C60004,0x24840004),
    (58,0x24C20003,0x24820003),(59,0x24C60004,0x24840004),(60,0x14C7FFEA,0x1486FFEA),
)]


def guard_successor(data):
    rows=list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function']==FUNCTION for row in rows) and data.endswith(b'\n')
    stream=io.StringIO(newline='')
    csv.writer(stream,lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+stream.getvalue().encode('ascii')


def normalize(words,relocations):
    assert len(words)==65
    result=list(words)
    for row in GUARD_ROWS:
        offset=int(row[2],0);index=offset//4
        assert words[index]==int(row[3],0) and not relocations.get(offset)
        result[index]=int(row[4],0)
    return result


def candidates():
    yield 'selected', SELECTED
    reused=BASE.replace('    u8 normalized;', '    u8 original = character;').replace(
        'normalized', 'character').replace('        character = character;', '        character = original;').replace(
        'if (character == 0x20)', 'if (original == 0x20)').replace('    return character;', '    return original;')
    for suffix in ('30','31','32'):
        reused=reused.replace('character == D_800859'+suffix,'D_800859'+suffix+' == character')
    reused=reused.replace('    index = 3;\n    cursor = D_80085933;', '    cursor = D_80085933;\n    index = 3;')
    yield 'parameter-reuse',reused
    yield 'parameter-reuse-saved32',reused.replace('u8 original = character;', 's32 original = character;')
    captured=next(body for name,body in capture_candidates() if name=='capture-0')
    for name,old,new in (('original32','u8 original','s32 original'),
            ('register-index','s32 index;','register s32 index;'),
            ('register-search','u8 normalized;','register u8 normalized;')):
        yield 'declaration-'+name,captured.replace(old,new)
    yield 'integer-search', BASE.replace('u8 normalized;', 's32 normalized;')
    yield 'byte-return', BASE.replace('s32 func_', 'u8 func_')
    yield 'cursor-first', BASE.replace('    s32 index;\n    u8 *cursor;', '    u8 *cursor;\n    s32 index;')
    yield 'for-loop', BASE.replace('    do {', '    for (; index != 0x5F; index += 4, cursor += 4) {').replace(
        '        index += 4;\n        cursor += 4;\n    } while (index != 0x5F);', '    }')
    yield 'index-first', BASE.replace('    index = 3;\n    cursor = D_80085933;', '    cursor = D_80085933;\n    index = 3;')
    for name,body in (
            ('original-copy',BASE.replace('    u8 normalized;', '    u8 original = character;\n    u8 normalized;').replace(
                'normalized = character;', 'normalized = original;').replace('    return character;', '    return original;')),
            ('indexed',BASE.replace('    u8 *cursor;\n','').replace('    cursor = D_80085933;\n','').replace(
                'cursor[0]','D_80085933[index - 3]').replace('cursor[1]','D_80085933[index - 2]').replace(
                'cursor[2]','D_80085933[index - 1]').replace('cursor[3]','D_80085933[index]').replace('        cursor += 4;\n',''))):
        yield name,body
        flipped=body
        for suffix in ('30','31','32'):
            flipped=flipped.replace('normalized == D_800859'+suffix,'D_800859'+suffix+' == normalized')
        yield name+'-flipped-first',flipped
    yield 'loop95', '''s32 func_15042C40(u8 character) {
    u8 normalized;
    s32 index;
    if (character >= 0x61 && character < 0x7B) normalized = character - 0x20;
    else normalized = character;
    if (character == 0x20) return 0x60;
    for (index = 0; index != 0x5F; index++) {
        if (normalized == D_80085930[index]) return index;
    }
    return character;
}'''
    yield from capture_candidates()


def capture_candidates():
    for mask in range(16):
        body=BASE.replace('    u8 normalized;', '    u8 original = character;\n    u8 normalized;').replace(
            '    return character;', '    return original;')
        if mask&1:body=body.replace('character >= 0x61 && character < 0x7B','original >= 0x61 && original < 0x7B')
        if mask&2:body=body.replace('normalized = character - 0x20;', 'normalized = original - 0x20;')
        if mask&4:body=body.replace('normalized = character;', 'normalized = original;')
        if mask&8:body=body.replace('character == 0x20','original == 0x20')
        for suffix in ('30','31','32'):
            body=body.replace('normalized == D_800859'+suffix,'D_800859'+suffix+' == normalized')
        body=body.replace('    index = 3;\n    cursor = D_80085933;', '    cursor = D_80085933;\n    index = 3;')
        yield 'capture-'+str(mask),body


def compile_candidate(root,out,name,body=SELECTED,profile='owner',declarations=DECLARATIONS):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=declarations,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-w)&65535 for w in words if w&0xFFFF0000==0x27BD0000 and w&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def install(source):
    assert source.count(ORIGINAL)==1 and SELECTED not in source
    assert DECLARATIONS.rstrip() not in source
    return source.replace(ORIGINAL,SELECTED).replace('#include <ultra64.h>\n',
        '#include <ultra64.h>\n'+DECLARATIONS,1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='selected')
    parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-character-normalizer'
    records=[]
    for name,body in candidates():
        if args.filter and args.filter not in name:continue
        for profile in (('owner','o2g3','o1g3','o1') if args.profiles else ('owner',)):
            declarations=DECLARATIONS.replace('extern u8 D_80085930;', 'extern u8 D_80085930[95];') if name=='loop95' else DECLARATIONS
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile,declarations)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],meta['pool_bytes'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
