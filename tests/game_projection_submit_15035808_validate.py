"""Validate a closed C-origin schedule against independent assembly and links."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
from copy import deepcopy
import hashlib,json,struct,subprocess
from tools.tests import game_projection_submit_15035808_oracle as g
from tools.tests.game_projection_submit_15035808_normalizer import derive
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
OUT=recovery.OUT;WHERE=OUT/'closed-links';WHERE.mkdir(exist_ok=True)

def run():
    raw,refs=payload(recovery.WHERE/'candidate.o','func_15035808')
    plan=recovery.SPEC['schedule_plan'];blob,bindings=derive(raw,refs,plan)
    expected,original_refs=payload(OUT/'original-links/original.o','func_15035808')
    differences=[(i//4,hex(struct.unpack_from('>I',blob,i)[0]),hex(struct.unpack_from('>I',expected,i)[0]))for i in range(0,len(blob),4)if blob[i:i+4]!=expected[i:i+4]]
    (OUT/'closed-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('Closed schedule word differences',differences)
    assert bindings==original_refs
    truth=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    assert g.bind(blob,bindings)==truth
    negatives=[]
    bad=bytearray(raw);bad[3]^=1
    changed=deepcopy(refs);at=min(changed);changed[at]=[(changed[at][0][0],'D_800C3F08')]
    assert changed!=refs
    for label,source,rs in(('payload',bytes(bad),refs),('binding',raw,changed)):
        try:derive(source,rs,plan)
        except ValueError:negatives.append(label)
        else:raise AssertionError(('Changed derivation input accepted',label))
    changed_plan=deepcopy(plan);first=next(iter(changed_plan['branch_destinations']));changed_plan['branch_destinations'][first]+=1
    try:derive(raw,refs,changed_plan)
    except ValueError:negatives.append('plan')
    else:raise AssertionError('Changed derivation plan accepted')
    links=[]
    for context,(code_shift,data_shift)in enumerate(((0,0),(0x1000,0xc348))):
        objects=[]
        for label,source,relocs in(('derived',blob,bindings),('original',expected,original_refs)):
            rows=['.set noat','.set noreorder','.text','.globl func_15035808','func_15035808:']
            for i,w in enumerate(struct.unpack('>345I',source)):
                rows.extend('.reloc ., '+kind+', '+name for kind,name in relocs.get(i*4,[]));rows.append('.word 0x%08X'%w)
            p=WHERE/(label+'-'+str(context)+'.s');p.write_text('\n'.join(rows)+'\n');obj=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],check=True,capture_output=True)
            script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(g.ENTRY+code_shift))
            names={n for rs in relocs.values()for _,n in rs}
            anchors={n:(g.ALLOC+code_shift if n=='allocate_memory'else int(n.split('_')[1],16)+(data_shift if n.startswith('D_')else code_shift))for n in names}
            elf=p.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15035808',*['--defsym=%s=0x%X'%row for row in sorted(anchors.items())],'-o',str(elf),str(obj)],check=True,capture_output=True)
            actual=sections(elf)['.text'][1];wanted=struct.pack('>345I',*bound_blob(source,relocs,anchors))
            assert actual[:1380]==wanted;objects.append(actual)
        assert objects[0]==objects[1]
        links.append(dict(code_shift=code_shift,data_shift=data_shift,complete_linked_text_equal=True))
    report=dict(byte_exact_words=345,relocation_sites=32,independent_GNU_original_equal=True,independent_links=links,
        HI16_LO16_carry=True,effective_input_controls=negatives,source_origin_words=345,
        omitted_origins=plan['omitted_origins'],duplicated_origins=plan['duplicated_origins'],
        output_words_stored_in_plan=0,plan_sha256=hashlib.sha256((OUT/'schedule-plan.json').read_bytes()).hexdigest(),
        derived_unbound_sha256=hashlib.sha256(blob).hexdigest(),matching_credit=0)
    (OUT/'closed-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
