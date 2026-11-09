import itertools,json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_resource_matrix_15157dec_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_resource_matrix_15157dec_oracle as guest
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENTS=((0x15157DC8,0x185278,9),(0x150FB188,0x128638,24))
CONSTANT=0x800A1DC0
def payload(obj,name):
 t,fs,rs=parse_object(obj);f=fs[name];refs={a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']}
 symbols={n:int(n.split('_')[1],16)for rows in refs.values()for _,n in rows}
 return bound_blob(t[f['value']:f['value']+f['size']],refs,symbols)
class Caller(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   a=tuple(self.arguments(2));assert a==(self.case.object,self.case.parameters);self.calls.append((t,a));self.events.append(('CALL',t,a))
  else:super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();target=guest.raw_words();truth=guest.retail_words();visits=set();n=0
 for which,(entry,at,count)in enumerate(PARENTS):
  words=list(struct.unpack_from('>%dI'%count,rom,at));obj=out/('qualified-caller-padded.o'if which else'qualified-padded.o');assert payload(obj,'func_150FB188'if which else'func_15157DC8')==words
  for page,pattern,mutation,phase in itertools.product((0,1),range(3),range(32),(0,8)):
   param=guest.OBJECT+0x120 if not which else guest.STACK+phase-0x14
   c=guest.Case(page=page,pattern=pattern,mutation=mutation,phase=phase,parameters=param);initial=guest.fixture(c);guest.put(initial,CONSTANT,0x3E99999A)
   before=dict(initial)
   if which:
    for off,v in((0x54,-95.),(0x58,-80.),(0x5C,0.)):guest.put(before,c.object+off,guest.bits(v))
    for j,w in enumerate((0,0,0,0x3E99999A,0x3E99999A)):guest.put(before,param+j*4,w)
   expected,calls,snaps=guest.reference(before,c);calls=[(guest.ENTRY,(c.object,c.parameters)),*calls];pair=[]
   for body in(truth,target):
    code=dict(zip(range(guest.ENTRY,guest.ENTRY+404,4),body));m=Caller(words,initial,c,entry=entry,arguments=(c.object,),connected=code).run();pair.append(m);visits.update(m.visits)
    assert(guest.public(m.memory),m.calls,m.snapshots,m.r[2])==(guest.public(expected),calls,snaps,1),(c,which)
   assert guest.state(pair[0])==guest.state(pair[1]);n+=1
 report=dict(cases_per_body=n,wrapper_words_visited=sum(0x15157DC8<=p<0x15157DEC for p in visits),second_caller_words_visited=sum(0x150FB188<=p<0x150FB1E8 for p in visits),target_words_visited=sum(guest.ENTRY<=p<guest.ENTRY+404 for p in visits),two_complete_original_callers=True,both_current_caller_bodies_exact=True,embedded_and_five_field_stack_arguments=True,ignored_child_return_then_one=True)
 (out/'caller-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
def connection_checks():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'frozen/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,0x150A8050,336);assert elf[at:at+336]==rom[0xD5500:0xD5650]
 at=elf_slot_offset(elf,guest.FACTOR,4);assert struct.unpack_from('>I',elf,at)[0]==0x3C8EFA35
 kernel=list(struct.unpack_from('>83I',rom,0xD5500));code=dict(zip(range(guest.ROTATE,guest.ROTATE+332,4),kernel));visits=set();n=0
 for page,pattern,param,phase in itertools.product((0,1),range(4),(guest.INPUT,guest.OBJECT+0x120),(0,8)):
  c=guest.Case(page=page,pattern=pattern,parameters=param,phase=phase);initial=guest.fixture(c);pair=[]
  for body in(guest.retail_words(),guest.raw_words()):
   m=guest.Oracle(body,initial,c,connected=code).run();guest.check(m,initial,c,connected=True);pair.append(m);visits.update(m.visits)
  assert guest.state(pair[0])==guest.state(pair[1]);n+=1
 report=dict(cases_per_body=n,kernel_body_words=83,kernel_slot_words=84,kernel_words_visited=sum(guest.ROTATE<=p<guest.ROTATE+332 for p in visits),target_words_visited=sum(guest.ENTRY<=p<guest.ENTRY+404 for p in visits),kernel_and_factor_baseline_exact=True,independent_rounded_rotation_model=True,trig_services_opaque_rounded_math=True,hardware_claim=False)
 (out/'rotation-connections.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);return report
if __name__=='__main__':main();connection_checks()
