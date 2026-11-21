"""Independent GNU original assembly and separate raw/original relocation checks.

This validates both input streams and binders, not byte identity between the
unmatched C stream and retail. All generated files remain in this private scope.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
from collections import Counter
import hashlib,json,struct,subprocess
from tools.tests import game_projection_submit_15035808_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
OUT=recovery.OUT;WHERE=OUT/'original-links';WHERE.mkdir(exist_ok=True)
FUNCTION='func_15035808'

def assemble(name,text):
    source=WHERE/(name+'.s');source.write_text(text);obj=source.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)],check=True,capture_output=True)
    return obj

def run():
    original=assemble('original','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+recovery.original_assembly()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    ob,orr=payload(original,FUNCTION);cb,cr=payload(recovery.WHERE/'candidate.o',FUNCTION)
    truth=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    assert g.bind(ob,orr)==truth and len(ob)==1380 and len(cb)==1380
    symbols=lambda refs:Counter(item for rows in refs.values()for item in rows)
    assert symbols(cr)==symbols(orr),(symbols(cr)-symbols(orr),symbols(orr)-symbols(cr))
    receipts=[]
    for context,(code_shift,data_shift)in enumerate(((0,0),(0x1000,0xc348))):
        for label,blob,refs in(('raw-C',cb,cr),('original-GNU',ob,orr)):
            rows=['.set noat','.set noreorder','.text','.globl '+FUNCTION,FUNCTION+':']
            for i,w in enumerate(struct.unpack('>345I',blob)):
                rows.extend('.reloc ., '+kind+', '+name for kind,name in refs.get(i*4,[]));rows.append('.word 0x%08X'%w)
            obj=assemble(label+'-'+str(context),'\n'.join(rows)+'\n')
            script=obj.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(g.ENTRY+code_shift))
            names={n for rs in refs.values()for _,n in rs}
            anchors={n:(g.ALLOC+code_shift if n=='allocate_memory'else int(n.split('_')[1],16)+(data_shift if n.startswith('D_')else code_shift))for n in names}
            elf=obj.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,*['--defsym=%s=0x%X'%row for row in sorted(anchors.items())],'-o',str(elf),str(obj)],check=True,capture_output=True)
            actual=sections(elf)['.text'][1][:len(blob)]
            expected=struct.pack('>345I',*bound_blob(blob,refs,anchors));assert actual==expected,(label,context)
            receipts.append(dict(stream=label,code_shift=code_shift,data_shift=data_shift,words=345,binder_equals_GNU_linker=True,sha256=hashlib.sha256(actual).hexdigest()))
    report=dict(original_GNU_body_matches_retail_345_words=True,raw_and_original_symbol_kind_multisets_equal=True,
        original_relocation_sites=len(orr),raw_relocation_sites=len(cr),independent_links=receipts,
        data_HI16_LO16_carry_exercised=True,C_and_retail_byte_identity_claim=False,matching_credit=0)
    (OUT/'original-links.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
