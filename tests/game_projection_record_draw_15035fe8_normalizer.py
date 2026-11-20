"""Closed register/schedule relation and bounded redundant entry-test removal."""
from pathlib import Path
import sys
from tools.experiments import game_projection_record_draw_15035fe8_recovery as source
ROOT=source.ROOT
import hashlib,json,struct,subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields,branch
OUT=source.OUT;SPEC=source.SPEC

def derive(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=SPEC['raw_sha256']:raise ValueError('Changed record draw payload')
    if json.loads(json.dumps(refs))!=SPEC['raw_refs']:raise ValueError('Changed record draw bindings')
    words=struct.unpack('>90I',raw)
    omitted=set(range(38,46))|{49}
    order=[(i,False)for i in range(38)]+[(46,False),(47,False),(51,False),(56,False),(48,False),(52,False)]
    order += [(i,True)for i in(73,74,71,72,75,15,76)]
    order += [(i,False)for i in(50,54,58,61,59,55,63,62,66,65,64,53,57,60,67,68)]
    order += [(i,False)for i in range(69,90)]
    assert len(order)==88 and{origin for origin,clone in order if not clone}==set(range(90))-omitted
    primary={origin:at for at,(origin,clone)in enumerate(order)if not clone}
    def color(origin,clone,word):
        roles={}
        if clone:
            if origin in(71,72):roles[9]=11
            if origin in(73,74):roles.update({25:4,8:10})
            if origin==75:roles[8]=10
            if origin==76:roles.update({8:10,9:11})
        else:
            if origin in(3,4,10):roles[6]=7
            if origin in(28,31,32):roles[4]=5
            if origin==34:roles.update({5:4,6:7})
            if origin==37:roles[5]=4
            if origin in(35,36):roles[2]=16
            if origin in(47,48,81):roles[11]=9
            if origin in(51,59):roles[14]=15
            if origin in(52,64):roles[24]=25
            if origin in(50,53):roles[2]=12
            if origin in(54,57):roles[12]=13
            if origin in(58,60):roles[13]=14
            if origin in(61,68):roles[15]=24
            if origin in(69,70,73,74):roles[25]=4
        result=word
        for shift in gpr_fields(word):
            reg=word>>shift&31
            if reg in roles:result=(result&~(31<<shift))|(roles[reg]<<shift)
        return result
    output=[];bindings={}
    for at,(origin,clone)in enumerate(order):
        word=color(origin,clone,words[origin])
        if clone and origin==15:target=76
        elif origin==48:
            assert words[origin]>>26==21
            word=(word&0x03FF0000)|(4<<26);target=51
        elif origin==80:target=40
        elif branch(word):
            old=origin+1+(((words[origin]&65535)^32768)-32768);target=primary[old]
        else:target=None
        if target is not None:word=(word&0xFFFF0000)|((target-at-1)&65535)
        output.append(word)
        if origin*4 in refs:bindings[at*4]=refs[origin*4]
    return struct.pack('>88I',*output),bindings,dict(raw_words=90,retail_words=88,retained_unique_origins=81,
        omitted_origins=sorted(omitted),cloned_origins=[i for i,c in order if c],frame=104,parameters_offset=84,
        redundant_bound_test_requires_positive_byte_count_and_nonwrapping_array=True,ROM_used_to_generate_output=False)

def original():
    full=(ROOT/'conker/asm/61D10.s').read_text();a=full.index('glabel func_15035FE8\n');b=full.index('endlabel func_15035FE8',a)+len('endlabel func_15035FE8')
    p=OUT/'original.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+full[a:b]+'\n.size func_15035FE8,.-func_15035FE8\n')
    q=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(q),str(p)],check=True,capture_output=True)
    return payload(q,'func_15035FE8')


from copy import deepcopy
from tools.experiments.game_actor_classifier_candidates import sections

def independent_links():
    raw,refs=payload(OUT/'qualified-screen/candidate.o','func_15035FE8');derived,bindings,report=derive(raw,refs)
    expected,oldrefs=original();assert(derived,bindings)==(expected,oldrefs)
    bad=bytearray(raw);bad[3]^=1;altered=deepcopy(refs);altered[12]=[('R_MIPS_HI16','D_800C3F08')]
    for blob,relocs in((bytes(bad),refs),(raw,altered)):
        try:derive(blob,relocs)
        except ValueError:pass
        else:raise AssertionError('Changed raw payload/binding accepted')
    folder=OUT/'links';folder.mkdir(exist_ok=True);reports=[]
    for index,(entry_shift,code_shift,data_shift)in enumerate(((0,0,0),(0x1000,0x2000,0x4348))):
        output=[]
        for name,blob,relocs in(('derived',derived,bindings),('original',expected,oldrefs)):
            text=['.set noat','.set noreorder','.text','.globl func_15035FE8','func_15035FE8:']
            for i,w in enumerate(struct.unpack('>88I',blob)):
                for kind,symbol in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+symbol)
                text.append('.word 0x%08X'%w)
            p=folder/(name+'-'+str(index)+'.s');p.write_text('\n'.join(text)+'\n');obj=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],check=True,capture_output=True)
            script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15035FE8+entry_shift))
            anchors={n:int(n.split('_')[1],16)+(code_shift if n.startswith('func_')else data_shift)for rs in relocs.values()for _,n in rs}
            elf=p.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15035FE8',
                *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            output.append(sections(elf)['.text'][1])
        assert output[0]==output[1];reports.append(dict(entry_shift=entry_shift,code_shift=code_shift,data_shift=data_shift))
    report.update(independent_links=reports,HI16_LO16_carry_context=True,payload_binding_controls_rejected=True,matching_credit=0)
    (OUT/'independent-links.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
