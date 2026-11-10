"""Compiled semantic mistakes require normal observable witnesses."""
import json
from tools.experiments import game_slot_sector_search_1505dda8_match as p
from tools.tests import game_slot_sector_search_1505dda8_oracle as g
def mutants(source):
 changes={'exclusive-upper-slot':('slot <= D_80082FA0','slot < D_80082FA0'),'skip-first-slot':('slot = 0','slot = 1'),'only-state-one':('interaction_state == 0','interaction_state != 1'),'ignore-inactive':('D_800CC2D0[slot].interaction_state == 0','0'),'wrong-radius-factor':('* scale * 0.5f','* scale * 1.0f'),'missing-radius-scale':('* scale * 0.5f','* 0.5f'),'inclusive-distance':('< radius * radius','<= radius * radius'),'signed-heading-wrap':('(u16)(actor->unk76 - heading','(s16)(actor->unk76 - heading'),'wrong-heading-field':('actor->unk76','actor->unk7A'),'missing-half-sector':(' + angle_range / 2',' + 0'),'inclusive-sector-edge':('< angle_range','<= angle_range'),'unsigned-result':('return (s8)slot;','return slot;'),'wide-index':('u8 slot;','u32 slot;')}
 result={}
 for label,(a,b)in changes.items():assert a in source;result[label]=source.replace(a,b)
 result['unsigned-result']=result['unsigned-result'].replace('s8 func_1505DDA8','s32 func_1505DDA8')
 result['wrongly-excluded-unused-slot']=source.replace('        radius =','        if (slot == unused) { continue; }\n        radius =')
 result['cached-actor-heading']=source.replace('    u8 slot;','    u16 initial_angle = actor->unk76;\n    u8 slot;').replace('(actor->unk76 - heading','(initial_angle - heading')
 result['cached-actor-speed']=source.replace('    u8 slot;','    f32 initial_speed = actor->xz_velocity;\n    u8 slot;').replace('radius = actor->xz_velocity','radius = initial_speed')
 result['cached-slot-limit']=source.replace('    u8 slot;','    s32 initial_limit = D_80082FA0;\n    u8 slot;').replace('slot <= D_80082FA0','slot <= initial_limit')
 return result
def main():
 source=p.BASE;old=(p.out/'frozen'/p.SOURCE).read_text();cs=g.cases();report={}
 # Put each control's discriminating boundary first; no execution failures count.
 hints={'exclusive-upper-slot':g.Case(limit=0,match=0),'skip-first-slot':g.Case(match=0),'only-state-one':g.Case(state=0x80000000),'ignore-inactive':g.Case(pattern=1,match=0),'wrong-radius-factor':g.Case(distance=g.bits(2.)),'missing-radius-scale':g.Case(scale=g.bits(4.),distance=g.bits(4.)),'inclusive-distance':g.Case(velocity=g.bits(1.),distance=g.bits(.25)),'signed-heading-wrap':g.Case(angle=0xFFFF),'missing-half-sector':g.Case(heading=1),'inclusive-sector-edge':g.Case(angle=256),'unsigned-result':g.Case(limit=128,match=128,pattern=3),'wide-index':g.Case(limit=255,match=-1,stop_after=260),'wrongly-excluded-unused-slot':g.Case(unused=0,match=0),'cached-actor-heading':g.Case(mutation=1),'cached-actor-speed':g.Case(mutation=2,distance=g.bits(4.)),'cached-slot-limit':g.Case(mutation=4,match=-1,new_limit=0)}
 for label,mutant in mutants(source).items():
  owner=p.proposal(old,mutant)
  if label=='unsigned-result':owner=owner.replace('s8 func_1505DDA8(struct127 *, u8, u16, f32);','s32 func_1505DDA8(struct127 *, u8, u16, f32);')
  obj,_=p.compile_owner(p.root,p.out,owner,'negative-'+label);ws=g.words(obj)
  for i,c in enumerate(([hints[label]]if label in hints else[])+cs):
   # Longer mutants must not overlap the immediately adjacent real helper VA.
   m=g.Oracle(ws,g.fixture(c),c,entry=g.ENTRY+0x20000);m.run();expected,calls,result=g.reference(m.initial,c)
   if m.r[2]!=result or[a[1]for _,a in m.calls]!=calls or g.public(m.memory)!=g.public(expected):report[label]=dict(case=i,normal_completion=True,execution_errors=0);break
  assert label in report,('No observable normal witness',label);print(label,json.dumps(report[label]),flush=True)
 result=dict(controls=len(report),effective_compiled_controls=report,mutant_entry_rebased_to_avoid_adjacent_helper_overlap=True);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':main()
