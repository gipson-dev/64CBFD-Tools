"""Complete current/original effect dispatcher with its actual98-entry callback table."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_particle_emission_accumulator_150ec520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_particle_emission_accumulator_150ec520_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT=0x15149264;TABLE=0x8008A4E8;DEATH_TABLE=0x8008A4C0;DEATH=0x150AE790;RELEASE=0x1516972C;TICKS=0x800BE9E4
class Caller(g.Oracle):
 def record_call(self,t):
  if t not in(DEATH,RELEASE):return super().record_call(t)
  a=tuple(map(g.u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t not in(DEATH,RELEASE):return super().hook(t)
  if t==DEATH and self.revive:g.put(self.memory,g.RECORD+14,1,2)
  self.clobber(0xDEADBEEF)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 table=rom[0x22EFA8:0x22F130];at=elf_slot_offset(elf,TABLE,392);assert elf[at:at+392]==table and struct.unpack_from('>I',table,89*4)[0]==g.ENTRY
 death=rom[0x22EF80:0x22EFA8];at=elf_slot_offset(elf,DEATH_TABLE,40);assert elf[at:at+40]==death
 body=rom[0x176714:0x1767C8];at=elf_slot_offset(elf,PARENT,180);assert elf[at:at+180]==body;words=list(struct.unpack('>45I',body))
 def machine(ws,c,flags,life,ticks,callback,death_index,revive,broken=False):
  m=g.fixture(c);m[g.RECORD+13]=flags;g.put(m,g.RECORD+14,life,2);m[g.RECORD+17]=callback;m[g.RECORD+16]=death_index;g.put(m,TICKS,ticks)
  m.update({TABLE+i:b for i,b in enumerate(table)});m.update({DEATH_TABLE+i:b for i,b in enumerate(death)})
  caller=list(words)
  if broken:caller[18]=0x00002025
  code=dict(zip(range(g.ENTRY,g.ENTRY+400,4),ws));x=Caller(caller,c,entry=PARENT,connected=code,memory=m);x.revive=revive;return x
 count=0;visits=set()
 for flags,life,ticks,callback,death_index,revive,phase in itertools.product((0,1),(1000,0,-1),(0,1),(89,255),(0,255),(False,True),(0,8)):
  c=g.Case(phase=phase,mode=24);pair=[]
  for ws in g.streams():
   m=machine(ws,c,flags,life,ticks,callback,death_index,revive).run();expected=dict(m.initial);calls=[];observations=[]
   if flags&1:g.put(expected,g.RECORD+14,g.half(g.read(expected,g.RECORD+14,2))-ticks,2)
   if callback!=255:
    home=g.STACK+phase-24;observations=[g.observe(expected,home,0,c.fcsr)]
    expected,inner,obs,fcsr=g.reference(expected,c,home=home);calls=[(g.ENTRY,(g.RECORD,))]+inner;observations+=obs
   else:fcsr=c.fcsr
   if g.half(g.read(expected,g.RECORD+14,2))<0:
    if death_index!=255:
     calls.append((DEATH,(g.RECORD,)))
     if revive:g.put(expected,g.RECORD+14,1,2)
    if g.half(g.read(expected,g.RECORD+14,2))<0:calls.append((RELEASE,(g.RECORD,)))
   assert m.calls==calls,(c,'caller calls',m.calls,calls)
   assert m.observations==observations and g.public(m.memory)==g.public(expected)
   assert m.fcsr==fcsr;pair.append(g.state(m));visits.update(m.visits)
  assert pair[0]==pair[1];count+=1
 m=machine(g.streams()[0],g.Case(),0,1000,1,89,255,False,broken=True)
 try:m.run();raise AssertionError('missing record control ineffective')
 except AssertionError as e:assert 'unmapped read'in str(e),str(e)
 assert all(PARENT+4*i in visits for i in range(45))
 assert words[22]==0x8482000E # Callback V0 is overwritten by the lifetime reload.
 r=dict(cases_per_stream=count,streams=2,original_call_window_words=45,current_complete_caller_equal=True,
  table_entries=98,callback_index=89,target_pointer_address='0x8008A64C',common_header_record_argument=True,
  callback_return_ignored=True,lifetime_update_death_release_and_revival=True,effective_missing_record_control=True,
  death_release_internals_contracted=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
