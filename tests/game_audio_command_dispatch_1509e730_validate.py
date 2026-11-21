from pathlib import Path
import hashlib,json,struct,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.tests.game_audio_command_dispatch_1509e730_normalizer import ORDER,emit
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
def run():
    entry=0x1509E730;obj=out/'qualified-source-screen/candidate.o';blob,refs=payload(obj,'func_1509E730')
    normalized,revised,branches=emit(blob,refs)
    anchors={n:int(n.split('_')[1],16)for entries in refs.values()for _,n in entries if n!='.rodata'};anchors['.rodata']=0x8009F3D0
    raw=bound_blob(blob,refs,anchors);words=bound_blob(normalized,revised,anchors)
    rom=(root/'conker/conker.us.bin').read_bytes()
    assert hashlib.sha256(rom).hexdigest()==json.loads((out/'baseline/fingerprints.json').read_text())['inputs']['conker/conker.us.bin']
    truth=struct.unpack_from('>92I',rom,0xCBBE0)
    assert tuple(words)==truth
    pool,relocations=normalized_pools(obj)['.rodata'];assert len(pool)==32 and len(relocations)==7 and pool==bytes(32)
    old_entries=[entry+row[2]for row in relocations]
    new_entries=[entry+4*ORDER.index((address-entry)//4)for address in old_entries]
    elf=out/'baseline/conker/build/conker.us.elf';candidates=[]
    for name,(address,data)in sections(elf).items():
        if address<=0x8009F3D0 and 0x8009F3D0+28<=address+len(data):
            candidates.append((name,tuple(struct.unpack_from('>7I',data,0x8009F3D0-address))))
    assert len(candidates)==1,candidates
    assert tuple(new_entries)==candidates[0][1],(tuple(map(hex,new_entries)),tuple(map(hex,candidates[0][1])),relocations)
    controls={}
    for label,offset in(('zero-return-word',32),('branch-target',28),('helper-opcode',68)):
        corrupt=bytearray(blob);corrupt[offset+3]^=1
        try:emit(bytes(corrupt),refs)
        except AssertionError:controls[label]=True
        else:raise AssertionError(label)
    plan=dict(order=ORDER,default_branch_input=7,default_destination_output=86,
              branches=branches,code_pointer_case_mapping=list(zip(old_entries,new_entries)),stores_output_words=False)
    report=dict(words=92,frame=32,raw_differences=sum(a!=b for a,b in zip(raw,truth)),
     normalized_differences=0,insertions=0,omissions=0,relocation_sites=len(refs),
     old_code_pointer_entries=old_entries,new_code_pointer_entries=new_entries,retail_table_section=candidates[0][0],
     checked_negative_controls=controls,plan_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),
     normalized_unbound_sha256=hashlib.sha256(normalized).hexdigest(),source_installed=recovery.installed(),matching_credit=0)
    (out/'normalizer-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (out/'normalizer-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'normalized-unbound.bin').write_bytes(normalized)
    print(json.dumps(report))
    return report
