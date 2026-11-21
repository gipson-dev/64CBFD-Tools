"""Closed register-role, saved-store schedule and modulo-shift derivation."""
from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
import hashlib,json,struct
from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields,branch
OUT=source.OUT
SHA='c46837ea7e3435857bd1362a9c9418a22f7d68c3ee9c76c88d554a33830c254a'
REFS={12:[('R_MIPS_HI16','D_800C3F00')],16:[('R_MIPS_LO16','D_800C3F00')],
    96:[('R_MIPS_HI16','D_800C3F08')],100:[('R_MIPS_LO16','D_800C3F08')],
    108:[('R_MIPS_HI16','D_80083140')],136:[('R_MIPS_LO16','D_80083140')],
    112:[('R_MIPS_HI16','D_80082FC0')],132:[('R_MIPS_LO16','D_80082FC0')],
    180:[('R_MIPS_HI16','D_800C3F08')],184:[('R_MIPS_LO16','D_800C3F08')],
    220:[('R_MIPS_HI16','D_800C3F08')],224:[('R_MIPS_LO16','D_800C3F08')],
    260:[('R_MIPS_HI16','D_800C3F08')],264:[('R_MIPS_LO16','D_800C3F08')],
    528:[('R_MIPS_HI16','D_800C3F00')],532:[('R_MIPS_LO16','D_800C3F00')],
    536:[('R_MIPS_HI16','D_800C3F08')],540:[('R_MIPS_LO16','D_800C3F08')]}
def derive(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=SHA:raise ValueError('Changed filtered draw payload')
    if refs!=REFS:raise ValueError('Changed filtered draw bindings')
    words=struct.unpack('>160I',raw);masked=[i for i,w in enumerate(words)if w==0x304F001F];assert len(masked)==1;k=masked[0]
    origins=list(range(160));origins[:12]=[0,11,1,3,4,5,6,7,8,9,10,2];origins.remove(k)
    inverse={old:new for new,old in enumerate(origins)};result=[];bindings={}
    clear=next(i for i,w in enumerate(words)if w==0x3C18D9FF)
    for out,old in enumerate(origins):
        w=words[old];op,rs=w>>26,w>>21&31
        home=(op in(35,43)and rs==29 and 4<=w&65535<=28)
        roles={}if home else{16:17,17:18,18:16}
        if old==k+1:roles[14]=15
        if old==k+2:roles.update({15:2,14:15,24:14})
        if old==k+3:roles.update({24:14,14:24})
        if old==k+4:roles[14]=24
        if old==k+10:roles[24]=14
        if old in(k+11,k+12):roles.update({24:14,14:24})
        if clear<=old<=clear+2:roles[24]=14
        new=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in roles:new=(new&~(31<<shift))|(roles[reg]<<shift)
        if branch(w):
            dest=old+1+(((w&65535)^32768)-32768)
            if dest==k:dest=k+1
            assert dest in inverse,(old,dest)
            new=(new&0xFFFF0000)|((inverse[dest]-out-1)&65535)
        result.append(new)
        if old*4 in refs:bindings[out*4]=refs[old*4]
    return struct.pack('>159I',*result),bindings,dict(raw_words=160,retail_words=159,omitted_origin=k,
        mask_block=[k+1,k+12],clear_block=[clear,clear+2],origins=origins,frame=32,
        saved_homes_unchanged=True,saved_roles={16:17,17:18,18:16})

from copy import deepcopy
import subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob

def independent_links():
    folder=OUT/"links";folder.mkdir(exist_ok=True)
    raw,refs=payload(OUT/'qualified-screen/candidate.o','func_15035D6C');derived,bindings,report=derive(raw,refs)
    full=(ROOT/'conker/asm/61D10.s').read_text();start=full.index('glabel func_15035D6C\n');end=full.index('endlabel func_15035D6C',start)+len('endlabel func_15035D6C')
    p=folder/'original.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+full[start:end]+'\n.size func_15035D6C,.-func_15035D6C\n')
    original=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(original),str(p)],capture_output=True,check=True)
    expected,oldrefs=payload(original,'func_15035D6C');assert(derived,bindings)==(expected,oldrefs)
    anchors={n:int(n.split('_')[1],16)for rows in bindings.values()for _,n in rows}
    truth=struct.unpack_from('>159I',(ROOT/'conker/conker.us.bin').read_bytes(),0x6321C);assert tuple(bound_blob(derived,bindings,anchors))==truth
    negative=[];bad=bytearray(raw);bad[3]^=1;altered=deepcopy(refs);altered[12]=[('R_MIPS_HI16','D_800C3F08')]
    for label,blob,relocs in(('payload',bytes(bad),refs),('binding',raw,altered)):
        try:derive(blob,relocs)
        except ValueError:negative.append(label)
        else:raise AssertionError('Changed input accepted')
    contexts=[]
    for index,(entry_shift,data_shift)in enumerate(((0,0),(0x1000,0xC348))):
        output=[]
        for name,blob,relocs in(('derived',derived,bindings),('original',expected,oldrefs)):
            text=['.set noat','.set noreorder','.text','.globl func_15035D6C','func_15035D6C:']
            for i,w in enumerate(struct.unpack('>159I',blob)):
                for kind,symbol in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+symbol)
                text.append('.word 0x%08X'%w)
            p=folder/(name+'-'+str(index)+'.s');p.write_text('\n'.join(text)+'\n');obj=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],check=True,capture_output=True)
            script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15035D6C+entry_shift))
            values={n:int(n.split('_')[1],16)+data_shift for rows in relocs.values()for _,n in rows}
            elf=p.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15035D6C',
                *['--defsym=%s=0x%X'%v for v in values.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            output.append(sections(elf)['.text'][1])
        assert output[0]==output[1];contexts.append(dict(entry_shift=entry_shift,data_shift=data_shift))
    report.update(independent_links=contexts,HI16_LO16_carry=True,raw_binding_negative_controls=negative,
        original_GNU_payload_and_bindings_equal=True,retail_words=159,alignment_words=0)
    (OUT/'independent-links.json').write_text(json.dumps(report,indent=2)+'\n')

    return report
