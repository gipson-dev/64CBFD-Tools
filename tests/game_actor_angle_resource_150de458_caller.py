"""Original callback installer and both bounded parent windows; ignored return."""
import itertools,json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_actor_angle_resource_150de458_match import ROOT,BUILD,NEW_SOURCE,HEADERS
root=ROOT;out=root/BUILD
from tools.tests import game_actor_angle_resource_150de458_oracle as guest
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
class Window(WindowCode):
 def __getitem__(self,pc):
  if pc==getattr(self.owner,'poison_pc',None):self.owner.r[2]=self.owner.poison
  return super().__getitem__(pc)
def run(m,stop,registers,poison_pc=None,poison=0):
 m.poison_pc,m.poison=poison_pc,poison;m.code=Window(m.code,m);m.code.ends=(stop,)
 for reg,value in registers.items():m.r[reg]=guest.u32(value)
 m.before=m.r[:]
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing declared window boundary')
 return m
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();delta=0x15000000-0x2D4B0;table=0x80088C90;producer=0x1509EBBC;end=0x1509ED5C
 assert struct.unpack_from('>3I',rom,0x22D870)==(guest.ENTRY,0,0)
 original=list(struct.unpack_from('>22I',rom,producer-delta));c=guest.Case();initial=guest.fixture(c);script=0x260000;guest.put(initial,script+8,24)
 for i in range(12):initial[table+24*12+i]=rom[0x22D870+i]
 expected=dict(initial);guest.put(expected,guest.ACTOR+0x38,guest.ENTRY);guest.put(expected,guest.ACTOR+0x78,0);expected[guest.ACTOR+0x92]=0
 m=run(guest.Oracle(original,initial,c,producer),end,{16:script,2:guest.ACTOR});assert guest.public(m.memory)==guest.public(expected)and m.r[2]==guest.ACTOR
 assert all(producer+4*j in m.visits for j in range(22))
 ps=[guest.words(out/n)for n in('retail-reference.o','qualified-padded.o','qualified-owner.o')];count=0
 for lane in(0,1):
  start,stop,after=(0x15113ED4,0x15113F08,0x15113EF0)if lane==0 else(0x15113F94,0x1511400C,0x15113FC8)
  window=list(struct.unpack_from('>%dI'%((stop-start)//4),rom,start-delta))
  for gate,iteration,flags,kind,phase in itertools.product((0,1),(0,)if lane==0 else(0,1),(0,3),(0,12),(0,8)):
   c=guest.Case(flags=flags,kind=kind,phase=phase,seed=3,ticks=1,lifetime=255);initial=guest.fixture(c);initial[guest.ACTOR+0x6E]=gate;guest.put(initial,guest.ACTOR+0x38,guest.ENTRY);guest.put(initial,0x80087380,0x87654321);guest.put(initial,0x800D23C0,0x270000);guest.put(initial,0x270002,iteration+1,2)
   prepared=dict(initial)
   if lane and iteration and not gate:
    for off,val in((0x5A,111),(0x5C,222),(0x5E,333)):guest.put(prepared,guest.ACTOR+off,val,2)
    guest.put(prepared,guest.ACTOR+0x80,0x11223344)
   want,calls=(prepared,[])if gate else guest.reference(prepared,c)
   if not gate:calls=[(guest.ENTRY,(guest.ACTOR,)),*calls]
   pairs={}
   for index,ws in enumerate(ps):
    models=[]
    for poison in(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678):
     code=dict(zip(range(guest.ENTRY,guest.ENTRY+640,4),ws));m=guest.Oracle(window,initial,c,start,connected=code)
     registers={4:iteration+1,16:guest.ACTOR,17:iteration,18:1 if not lane else 0,19:111,20:222,21:333,22:0x11223344,23:0,30:0}
     m=run(m,stop,registers,after,poison);assert(guest.public(m.memory),m.calls)==(guest.public(want),calls),(lane,gate,iteration,flags,kind)
     assert m.r[2]==0x87654321 and m.r[29]==guest.STACK+phase;models.append(m)
    for other in models[1:]:assert guest.state(models[0])==guest.state(other)
    pairs[index]=models
   for a,b in zip(pairs[0],pairs[1]):assert guest.state(a)==guest.state(b)
   count+=1
 report=dict(table='D_80088C90',row=24,row_ROM='0x22D870',row_bytes=12,callback_field='0x38',original_installer_words=22,all_installer_words_visited=True,parent_windows={'0x15113ED4':13,'0x15113F94':30},window_cases=count,root_bodies=3,return_poison_values=4,return_ignored_proven=True,gate_and_second_iteration_paths=True,whole_large_parent_claimed=False)
 (out/'caller-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
