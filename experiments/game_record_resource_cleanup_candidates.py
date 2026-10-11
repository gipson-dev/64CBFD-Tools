"""Recover the complete conditional resource cleanup and callback-aware loop."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS, SLOT_WORDS = 0x1503DD1C, 0x6B1CC, 43, 45
FUNCTION, SOURCE = 'func_1503DD1C', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503DD1C() {\n    return 0;\n}'
DECLARATIONS = '''extern u16 D_800C5628[];
extern u32 *D_800C5338[];
void func_1510D7AC(s32);
'''
SYMBOLS = dict(D_800C5628=0x800C5628, D_800C5338=0x800C5338,func_1510D7AC=0x1510D7AC)
PROFILES = dict(compiler.PROFILES,owner=('-O2','-g3','-Wo,-loopunroll,0'),retail=('-O2','-g3'))
SELECTED = '''void func_1503DD1C(s32 identity) {
    s32 index;
    u32 *record;

    for (index = 0; index < D_800C5628[identity]; index++) {
        record = D_800C5338[identity] + index * 3;
        if (record[0] != 0x80000000U && record[0] != record[1]) {
            func_1510D7AC(record[1]);
        }
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'record-first', SELECTED.replace('    s32 index;\n    u32 *record;','    u32 *record;\n    s32 index;')
    yield 'byte-offset', SELECTED.replace('D_800C5338[identity] + index * 3',
        '(u32 *)((u8 *)D_800C5338[identity] + index * 12)')
    yield 'separate-current', SELECTED.replace('    u32 *record;', '    u32 *record;\n    u32 current;').replace(
        '        if (record[0] != 0x80000000U && record[0] != record[1])',
        '        current = record[0];\n        if (current != 0x80000000U && current != record[1])')
    yield 'split-skip', SELECTED.replace('        if (record[0] != 0x80000000U && record[0] != record[1]) {',
        '        if (record[0] == 0x80000000U) {\n            continue;\n        }\n        if (record[0] != record[1]) {')
    yield 'signed-word', SELECTED.replace('u32 *record;', 's32 *record;').replace(
        'record = D_800C5338[identity]', 'record = (s32 *)D_800C5338[identity]')


QUALIFIED = dict(candidates())['byte-offset']
PROPAGATION_SOURCE_SHA = '0621f5de4f8c8b3f9c931d07bcf6838566b204eafbbeae45869e54d572d82a3c'
PROTOTYPE = 's32 func_1503DD1C();'
TYPED_PROTOTYPE = 'void func_1503DD1C(s32);'
ANCHOR = 'u32 func_1510D0EC(u32, s32, s32, s32);'
RELEASE_DECLARATION = 'void func_1510D7AC(s32);'


def install(before):
    if (before.count(ORIGINAL),before.count(PROTOTYPE),before.count(ANCHOR)) != (1,1,1) or RELEASE_DECLARATION in before:
        raise ValueError('stale record cleanup body or declarations')
    return before.replace(ORIGINAL,QUALIFIED).replace(PROTOTYPE,TYPED_PROTOTYPE).replace(
        ANCHOR,ANCHOR+'\n'+RELEASE_DECLARATION)


def propagation_source(root):
    """Reverse only the complete qualified cleanup for immutable older audits."""
    from tools.experiments import game_third_resource_loader_lifetime_candidates as third
    source=third.historical_source(root)
    if ORIGINAL in source:
        return source
    assert source.count(QUALIFIED)==source.count(TYPED_PROTOTYPE)==source.count(RELEASE_DECLARATION)==1
    before=source.replace(QUALIFIED,ORIGINAL).replace(TYPED_PROTOTYPE,PROTOTYPE).replace(
        ANCHOR+'\n'+RELEASE_DECLARATION,ANCHOR)
    assert hashlib.sha256(before.encode('ascii')).hexdigest()==PROPAGATION_SOURCE_SHA
    assert install(before)==source
    return before


def metadata_pair(data):
    """Identify only the measured two absolute data symbols, using ELF tables."""
    from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL
    header=ELF_HEADER.unpack_from(data)
    sections=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
    tables=[section for section in sections if section[1]==2]
    assert len(tables)==1
    table=tables[0];strings=sections[table[6]]
    names=bytes(data[strings[4]:strings[4]+strings[5]])
    expected={b'D_800D35E0':0x800D35E0,b'D_8008F8C0':0x8008F8C0}
    found=[]
    for offset in range(table[4],table[4]+table[5],table[9]):
        symbol=SYMBOL.unpack_from(data,offset);name=names[symbol[0]:].split(b'\0',1)[0]
        if name in expected:
            assert symbol[1:]==(expected[name],0,16,0,65521)
            found.append((offset,strings[4]+symbol[0],name))
    assert len(found)==2 and {item[2] for item in found}==set(expected)
    assert found[1][0]-found[0][0]==16 and found[1][1]-found[0][1]==11
    return found


def swap_metadata_pair(data):
    pair=metadata_pair(data);result=bytearray(data)
    for index,(offset,string,name) in enumerate(pair):
        other_offset,other_string,other_name=pair[1-index]
        result[offset+4:offset+8]=data[other_offset+4:other_offset+8]
        result[string:string+11]=data[other_string:other_string+11]
    metadata_pair(result)
    return bytes(result)


def restore_metadata_pair(actual,before):
    current,original=metadata_pair(actual),metadata_pair(before)
    assert [(o,s) for o,s,n in current]==[(o,s) for o,s,n in original]
    expected=before if [n for o,s,n in current]==[n for o,s,n in original] else swap_metadata_pair(before)
    result=bytearray(actual)
    for offset,string,name in original:
        assert actual[offset:offset+16]==expected[offset:offset+16]
        assert actual[string:string+11]==expected[string:string+11]
        result[offset:offset+16]=before[offset:offset+16]
        result[string:string+11]=before[string:string+11]
    return bytes(result)


def propagation_elf(root,before):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_actor_renderer_install_match import symbol_size_offset

    source=propagation_source(root)
    actual=(root/'conker/build/conker.us.elf').read_bytes()
    if source==(root/SOURCE).read_text():
        return actual
    size=SLOT_WORDS*4
    start=elf_slot_offset(actual,ENTRY,size);extent=symbol_size_offset(actual,FUNCTION,ENTRY)
    retail=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+size]
    assert actual[start:start+size]==retail
    assert struct.unpack_from('>I',actual,extent)[0]==WORDS*4
    old_start=elf_slot_offset(before,ENTRY,size);old_extent=symbol_size_offset(before,FUNCTION,ENTRY)
    assert struct.unpack_from('>I',before,old_extent)[0]==12
    result=bytearray(restore_metadata_pair(actual,before));result[start:start+size]=before[old_start:old_start+size]
    struct.pack_into('>I',result,extent,12)
    return bytes(result)


def compile_candidate(root,out,name,body=QUALIFIED,profile='owner'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-word)&65535 for word in words if word&0xFFFF0000==0x27BD0000 and word&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--filter',default='byte-offset')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-record-resource-cleanup'
    records=[]
    for name,body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in ('owner','retail') if args.profiles else ('owner',):
            meta,words=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta);print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
