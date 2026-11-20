"""Derive a duplicate private argument reload and retail register roles."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields,branch
from tools.experiments import game_actor_randomized_effect_150f97ec_recovery as source
OUT=source.OUT;ROOT=source.ROOT;SPEC=source.SPEC
def derive(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=SPEC['raw_sha256']:raise ValueError('Changed effect payload')
    if json.loads(json.dumps(refs))!=SPEC['raw_refs']:raise ValueError('Changed effect bindings')
    words=struct.unpack('>88I',raw)
    order=list(range(10))+[13,11,10,None,14,15,16,17,18,12,19,20,21]+list(range(22,88))
    assert len(order)==89 and sorted(x for x in order if x is not None)==list(range(88))
    destinations={old:new for new,old in enumerate(order)if old is not None}
    def color(origin,w):
        roles={}
        if origin in(13,14,18):roles[9]=10
        if origin==17:roles.update({14:8,8:9})
        if origin in(18,21):roles[10]=11
        if origin==21:roles[8]=9
        if origin in(44,47,59,83):roles[12]=13
        if origin in(49,62):roles[13]=14
        if origin in(50,51,58,81):roles[11]=12
        if origin in(61,78):roles[14]=8
        if origin in(67,72):roles[9]=10
        if origin in(68,71):roles[8]=9
        if origin in(69,70):roles[10]=11
        changed=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in roles:changed=(changed&~(31<<shift))|(roles[reg]<<shift)
        return changed
    output=[];bindings={}
    for at,origin in enumerate(order):
        if origin is None:
            assert words[5]==0x8FAE0070
            word=(words[5]&~(31<<16))|(8<<16) # independent incoming actor reload
        else:
            word=color(origin,words[origin])
            if branch(word):
                target=origin+1+(((words[origin]&65535)^32768)-32768)
                word=(word&0xFFFF0000)|((destinations[target]-at-1)&65535)
            if origin*4 in refs:bindings[at*4]=refs[origin*4]
        output.append(word)
    return struct.pack('>89I',*output),bindings,dict(raw_words=88,normalized_words=89,retained_source_origins=88,duplicated_private_actor_home_origin=5,
        duplicate_output_index=13,frame=112,FP_primitives_unchanged=True,ROM_used_to_generate_output=False)
def original():
    full=(ROOT/'conker/asm/124920.s').read_text();a=full.index('glabel func_150F97EC\n');b=full.index('endlabel func_150F97EC',a)+len('endlabel func_150F97EC')
    p=OUT/'original.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+full[a:b]+'\n.size func_150F97EC,.-func_150F97EC\n')
    q=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(q),str(p)],capture_output=True,check=True)
    return payload(q,'func_150F97EC')

from copy import deepcopy
from tools.experiments.game_actor_classifier_candidates import sections

def independent_links():
    raw,refs=payload(OUT/'qualified-screen/candidate.o','func_150F97EC');derived,bindings,report=derive(raw,refs)
    expected,oldrefs=original();assert(derived,bindings)==(expected,oldrefs)
    bad=bytearray(raw);bad[3]^=1;altered=deepcopy(refs);altered[80]=[('R_MIPS_26','func_150F97EC')]
    for blob,relocs in((bytes(bad),refs),(raw,altered)):
        try:derive(blob,relocs)
        except ValueError:pass
        else:raise AssertionError('Corrupt payload/binding accepted')
    folder=OUT/'links';folder.mkdir(exist_ok=True);reports=[]
    for index,(entry_shift,code_shift,data_shift)in enumerate(((0,0,0),(0x1000,0x2000,0x12348))):
        output=[]
        for name,blob,relocs in(('derived',derived,bindings),('original',expected,oldrefs)):
            text=['.set noat','.set noreorder','.text','.globl func_150F97EC','func_150F97EC:']
            for i,w in enumerate(struct.unpack('>89I',blob)):
                for kind,symbol in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+symbol)
                text.append('.word 0x%08X'%w)
            p=folder/(name+'-'+str(index)+'.s');p.write_text('\n'.join(text)+'\n');obj=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],check=True,capture_output=True)
            script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x150F97EC+entry_shift))
            anchors={n:int(n.split('_')[1],16)+(code_shift if n.startswith('func_')else data_shift)for rs in relocs.values()for _,n in rs};elf=p.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_150F97EC',*['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            output.append(sections(elf)['.text'][1])
        assert output[0]==output[1];reports.append(dict(entry_shift=entry_shift,code_shift=code_shift,data_shift=data_shift))
    report.update(independent_links=reports,payload_and_binding_controls_rejected=True,matching_credit=0)
    (OUT/'independent-links.json').write_text(json.dumps(report,indent=2)+'\n');return report
