"""Qualify the archive actor-mode dispatch against its real retail jump table."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_texture_vertex_span as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools import pad_c_object

BUILD='conker/build/game-actor-mode-flags'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_A9D90','func_1507DF10',0x1507DF10,0xAB3C0,53
TABLE,TABLE_SYMBOL=0x8009B884,'jtbl_8009B884_game'
TABLE_OFFSETS=(0xAC,0xAC,0x78,0x78,0x48,0x24)
PATHS=dict(previous.PATHS,actor_owner='conker/src/game_A9D90.c',
    actor_original='conker/asm/nonmatchings/game_A9D90/func_1507DF10.s',
    symbols='conker/symbol_addrs.us.txt',undefined='conker/undefined_syms_auto.txt')
BASELINE=dict(previous.BASELINE,
    actor_owner='6372ec8438d2b7238507026c84b94df84689049bbf5c79869dcde52b528dbddd',
    actor_original='73c091c8092a04c77ae774e101eb15e072c76eee3913f50d0b788ba6ecf36cee',
    symbols='d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    undefined='a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd')
BODY='''/* Apply the selected actor mode's flag masks, preserving all other fields. */
void func_1507DF10(struct127 *actor, s32 mode) {
    switch (mode) {
        case 9:
            actor->unk94 |= 0x20;
            actor->unk9C |= 0x78;
            actor->unk2E4 = 1;
            break;
        case 8:
            actor->unk94 |= 0x40;
            actor->unk94 &= ~0x200;
            actor->unk9C |= 0xF00;
            actor->unk2E4 = 2;
            break;
        case 6:
        case 7:
            actor->unk94 |= 0xE;
            actor->unk94 &= ~0x410;
            actor->unk9C |= 0xEE0000;
            actor->unk2E4 = 4;
            break;
        case 4:
        case 5:
            actor->unk94 |= 0x80;
            actor->unk94 &= ~0x500;
            actor->unk2E4 = 8;
            break;
    }
}
'''


def freeze(root,out):
    out.mkdir(exist_ok=True)
    manifest=out/'baseline.json'
    if not manifest.exists():
        data={key:(root/path).read_bytes() for key,path in PATHS.items()}
        if {key:hashlib.sha256(value).hexdigest() for key,value in data.items()}!=BASELINE:
            raise ValueError('Changed actor mode baseline')
        for key,value in data.items():
            (out/('before-'+key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE,indent=2)+'\n')
    if json.loads(manifest.read_text())!=BASELINE:
        raise ValueError('Modified actor mode manifest')
    for key,digest in BASELINE.items():
        if hashlib.sha256((out/('before-'+key)).read_bytes()).hexdigest()!=digest:
            raise ValueError('Modified immutable actor mode input: '+key)


def recover(before,body=BODY):
    lo,hi=build.function_span(before,FUNCTION)
    text=before[:lo]+body.rstrip()+before[hi:]
    text=text.replace('s32 '+FUNCTION+'();\n','')
    return text.replace('/* Non-matching C placeholders for asm/nonmatchings/'+OWNER+'/'+FUNCTION+'.s. */\n','')


def recovered_makefile(before):
    marker='$(BUILD_DIR)/$(SRC_DIR)/game_433F0.c.o: RETAIL_RODATA_SYMBOL := jtbl_800966C0_game\n'
    assert before.count(marker)==1 and 'game_A9D90.c.o: RETAIL_RODATA_SYMBOL' not in before
    return before.replace(marker,marker+'$(BUILD_DIR)/$(SRC_DIR)/game_A9D90.c.o: RETAIL_RODATA_SYMBOL := '+TABLE_SYMBOL+'\n')


def pad_and_link(root,out,obj,name):
    assembly=pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,
        word_patches_path=root/PATHS['guards'],rodata_symbol=TABLE_SYMBOL)
    asm=out/(name+'.s')
    asm.write_text('.include "'+str(root/'conker/include/asm_processor_prelude.inc')+'"\n'+assembly)
    padded=out/(name+'.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(asm)],capture_output=True,check=True)
    linked,functions=build.link_owner(root,out,padded,OWNER)
    info=functions[FUNCTION]
    return list(struct.unpack_from('>%dI'%(info['size']//4),linked,info['value']))


def qualify(root,out):
    freeze(root,out)
    text=recover((out/'before-actor_owner').read_text())
    obj,diagnostics=build.compile_owner(root,out,text,'qualified')
    raw,functions,relocations=parse_object(obj)
    info=functions[FUNCTION]
    pool=sections(obj)['.rodata'][1]
    offsets=tuple(word-info['value'] for word in struct.unpack_from('>6I',pool))
    if offsets!=TABLE_OFFSETS or any(pool[24:]):
        raise ValueError('Unexpected compact actor mode jump table')
    expected_table=struct.pack('>6I',*(ENTRY+offset for offset in TABLE_OFFSETS))
    before=(out/'before-elf').read_bytes()
    at=elf_slot_offset(before,TABLE,len(expected_table))
    if before[at:at+24]!=expected_table:
        raise ValueError('Original actor mode jump table differs')
    if {at-info['value']:rows for at,rows in relocations.items()
            if info['value']<=at<info['value']+info['size']} != {
            0x10:[('R_MIPS_HI16','.rodata')],0x18:[('R_MIPS_LO16','.rodata')]}:
        raise ValueError('Unexpected actor mode code relocations')
    words=pad_and_link(root,out,obj,'padded')
    rom=(root/'conker/conker.us.bin').read_bytes()
    retail=list(struct.unpack_from('>53I',rom,ROM))
    record=dict(words=info['size']//4,differences=sum(a!=b for a,b in zip(words,retail)),
        diagnostics=diagnostics,table_address=TABLE,table_offsets=offsets,
        table_bytes_unchanged=True,guards_added=0,profile=['-O2','-g3'])
    if record['words']!=WORDS or words!=retail or diagnostics:
        raise ValueError('Actor mode donor is not byte exact: '+repr(record))
    (out/'qualification.json').write_text(json.dumps(record,indent=2)+'\n')
    return obj,words,record


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root=Path(__file__).resolve().parents[2]
    _,_,record=qualify(root,root/BUILD)
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    main()
