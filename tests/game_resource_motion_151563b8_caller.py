import itertools,json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_resource_motion_151563b8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_resource_motion_151563b8_oracle as guest
PARENT,TABLE,LISTS,DEPTH,SLOTS=0x151670C0,0x8008B4A8,0x800DCE50,0x800DD190,0x800DD198
RECORDS=(guest.OBJECT,guest.OBJECT+0x300,guest.OBJECT+0x600)

def fixture(c,mode,rom):
 m=guest.fixture(c)
 for j,p in enumerate(RECORDS):
  m.update(guest.public(guest.fixture(replace(c,object=p,remaining=(c.remaining+j)&65535))))
  m[p]=44 if j<2 else 83;guest.put(m,p+8,RECORDS[1]if j==0 and mode!=1 else 0)
 table=rom[0x22FF68:0x22FF68+0x1484];m.update({TABLE+i:b for i,b in enumerate(table)})
 m.update({LISTS+i:0 for i in range(0x340)})
 m.update({SLOTS+i:0x5A for i in range(64)});m[DEPTH]=0
 if mode!=0:
  guest.put(m,LISTS+44*4,RECORDS[0]);guest.put(m,LISTS+0x1A0+83*4,RECORDS[2])
 if mode==3:guest.put(m,TABLE+44*52,0)
 return m

def remove_effect(m,c,mode):
 guest.effect(m,c,guest.SYMS)
 if mode==4:guest.put(m,SLOTS+m[DEPTH]*4,0)

def reference(initial,c,mode):
 m=dict(initial);calls=[];snaps=[]
 for row in range(2):
  for kind in range(101):
   callback=guest.read(m,TABLE+kind*52)
   if not callback:continue
   p=guest.read(m,LISTS+row*0x1A0+kind*4);m[DEPTH]+=1
   while p:
    assert callback==guest.ENTRY
    guest.put(m,SLOTS+m[DEPTH]*4,guest.read(m,p+8));calls.append((callback,(p,)))
    active=replace(c,object=p,mutation=0)
    updated,child,observations=guest.reference(m,active)
    # A removal provider may invalidate record contents and the pending link.
    if child:
     snapshots=observations;child_case=replace(c,object=p)
     # reference already applied the mutation-free marker; provider effects
     # use the same call-time record/global snapshot before further mutation.
     remove_effect(updated,child_case,mode)
    else:snapshots=[]
    m=updated;calls.extend(child);snaps.extend(snapshots)
    p=guest.read(m,SLOTS+m[DEPTH]*4)
   m[DEPTH]-=1
 return m,calls,snaps

class Dispatcher(guest.Oracle):
 def __init__(self,words,initial,c,mode,target):
  self.link_mode=mode;self.active=c
  super().__init__(words,initial,c,entry=PARENT,connected=dict(zip(range(guest.ENTRY,guest.ENTRY+320,4),target)),arguments=())
 def record_call(self,t):
  if t==guest.ENTRY:
   a=(self.r[4],);self.calls.append((t,a));self.events.append(('CALL',t,a));return
  self.active=replace(self.case,object=self.r[4]);return super().record_call(t)
 def hook(self,t):
  assert t==guest.REMOVE;remove_effect(self.memory,self.active,self.link_mode)
  for j in range(4):self.put(self.r[29]+j*4,0xB5000000+j,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def main():
 rom=(root/'conker/conker.us.bin').read_bytes();words=list(struct.unpack_from('>74I',rom,0x194570));raw=guest.raw_words();truth=guest.retail_words()
 visits=set();n=callbacks=removals=0
 for flags,timer,mode,mutation,phase in itertools.product((0,1,8,9),(0,1,0x8000,0x7FFF),range(5),(0,1),(0,8)):
  c=guest.Case(flags=flags,remaining=timer,mutation=mutation,phase=phase,rate=0x7FFF,seed=timer%4)
  initial=fixture(c,mode,rom);expected,calls,snaps=reference(initial,c,mode);pair=[]
  for target in(truth,raw):
   m=Dispatcher(words,initial,c,mode,target)
   try:m.run()
   except AssertionError:
    print('dispatcher failure',c,mode,'r30',hex(m.r[30]),hex(m.before[30]),'sp',hex(m.r[29]),'saved',hex(guest.read(m.memory,guest.STACK+c.phase-8)),flush=True);raise
   pair.append(m);visits.update(m.visits)
   if(guest.public(m.memory),m.calls,m.snapshots)!=(guest.public(expected),calls,snaps):
    print('semantic mismatch',c,mode,'calls',m.calls,calls,'snap_equal',m.snapshots==snaps,'bytes',[(hex(a),v,expected.get(a))for a,v in guest.public(m.memory).items()if expected.get(a)!=v][:16],flush=True)
    raise AssertionError((c,mode))
   assert m.r[29]==guest.STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[31]==m.before[31]
  assert guest.state(pair[0])==guest.state(pair[1]);n+=1
  callbacks+=sum(t==guest.ENTRY for t,a in calls);removals+=sum(t==guest.REMOVE for t,a in calls)
  if n%128==0:print('dispatcher cases',n,flush=True)
 report=dict(cases_per_body=n,callback_entries=[44,83],caller_words=74,caller_words_visited=sum(PARENT<=p<PARENT+296 for p in visits),
             target_words_visited=sum(guest.ENTRY<=p<guest.ENTRY+320 for p in visits),callbacks=callbacks,removals=removals,
             complete_original_dispatcher=True,actual_retail_registry=True,two_rows_and_101_types=True,
             ignored_return_and_single_pointer_ABI=True,pending_link_mutation=True,removal_provider_opaque=True)
 (out/'caller-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
