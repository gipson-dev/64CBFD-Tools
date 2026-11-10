"""All five original Game call sites: four complete parents and one window."""
import csv,json,struct,sys
from dataclasses import replace
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();base=root/"conker/build/game-actor-audio-15060778-match";out=base/"adoption"
from tools.tests import game_actor_audio_handle_15060778_oracle as game, game_actor_audio_handle_15060778_boundaries as boundaries, game_sound_slot_10010be8_oracle as alloc
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_point_transform_match import put,read

FALLBACK1,FALLBACK2=0x10010344,0x10010630
POINTER,PARAMS=0x800D154C,0x800D1890
PARENTS=((0x15060A30,27,1,False),(0x15060A9C,26,0,False),(0x15060B04,27,0,True),(0x15076250,24,None,False))
u32=game.u32

def original(rom,entry,n):return list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0))

class ParentOracle(game.Oracle):
 def __init__(self,ws,memory,c,entry,child,camera=None,fallback=None):
  connected=dict(zip(range(game.ENTRY,game.ENTRY+len(child)*4,4),child))
  if entry==0x15054420:connected[0x1505445C]=0
  super().__init__(ws,memory,c,entry=entry,connected=connected)
  self.root_calls=[];self.fallback=fallback;self.camera=camera
 def record_call(self,t):
  if t==game.ENTRY:
   a=tuple(map(u32,self.arguments(7)));canonical=(a[0],a[1],a[2]&65535,*a[3:]);c=self.c;wanted=tuple(map(u32,(c.sound,c.actor,c.volume&65535,c.pitch,c.near,c.far,c.flags)));assert canonical==wanted,('original-parent ABI',hex(self.root_entry),canonical,wanted)
   self.root_calls.append((t,a));return
  if t in(FALLBACK1,FALLBACK2):
   a=tuple(map(u32,self.arguments(5)));canonical=(a[0]&65535,a[1],a[2]if t==FALLBACK1 else a[2]&65535,u32(game.s16(a[3])),a[4]&65535);assert canonical==self.fallback,('fallback ABI',hex(self.root_entry),canonical,self.fallback);self.calls.append((t,canonical));return
  super().record_call(t)
 def hook(self,t):
  if t not in(FALLBACK1,FALLBACK2):return super().hook(t)
  put(self.memory,game.MARK,read(self.memory,game.MARK)+1)
  for i in range(5):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xDEADBEEF

def state_check(m,c,fallback=False):
 if fallback:
  expected=dict(m.initial);put(expected,game.MARK,read(expected,game.MARK)+1);assert len(m.calls)==1 and not m.root_calls
 else:
  expected,calls,_=game.reference(m.initial,c);assert len(m.root_calls)==1 and m.calls==calls,('connected-child calls',c,m.calls,calls)
 assert game.public(m.memory)==game.public(expected),('parent public-memory',hex(m.root_entry),c)
 assert m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]

def caller_suite(rom,programs):
 runs=roots=0;coverage={}
 for entry,n,flags,variable_volume in PARENTS:
  ws=original(rom,entry,n);cases=[]
  if flags is None:
   for byte in range(256):cases.append((game.Case(sound=(byte<<8)|(255-byte),volume=32000,pitch=-100,near=500,far=2500,flags=byte,query=-1,mutation=1),None))
  else:
   for sound in(0,0x123,0x80000000,0xFFFFFFFF):
    for camera in(0,1):
     for volume in((0,65535,0x1234FFFF)if variable_volume else(24000,)):cases.append((game.Case(sound=sound,volume=volume,pitch=0,near=500,far=2500,flags=flags),camera))
  seen=set()
  for name,child in programs.items():
   for index,(c,camera)in enumerate(cases):
    c=replace(c,phase=(index&1)*8,seed=index%7);memory=game.fixture(c);fallback=None
    if camera is None:
     put(memory,POINTER,game.ACTOR)
     for i,value in enumerate((c.sound>>8,c.sound&255,c.flags)):memory[PARAMS+i]=value
    else:
     put(memory,game.ACTOR+0x318,camera)
     fallback=(u32(c.sound)&65535,game.ACTOR,0x6D60 if entry==0x15060A30 else c.volume&65535,500,2500)
    m=ParentOracle(ws,memory,c,entry,child,camera,fallback);m.run();state_check(m,c,fallback=camera==0);runs+=1;roots+=len(m.root_calls);seen.update(m.visits)
  coverage[hex(entry)]=len(seen&set(range(entry,entry+n*4,4)))
 # Remaining large parent is bounded at the original call-return boundary.
 entry,end=0x15054420,0x1505445C;ws=original(rom,entry,(end-entry)//4);seen=set();window_runs=0
 for name,child in programs.items():
  for remainder in(0,1,2):
   for material in(0,0x80,0x180,0xFFFFFFFF):
    c=game.Case(sound=remainder+(24 if remainder<2 else 41),volume=30000,pitch=0,near=500,far=1500,flags=5,material=material)
    m=ParentOracle(ws,game.fixture(c),c,entry,child);m.r[3]=remainder;m.r[16]=game.ACTOR;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not reach its observed return boundary')
    state_check(m,c);window_runs+=1;roots+=len(m.root_calls);seen.update(m.visits)
 coverage[hex(entry)]=len(seen&set(range(entry,end,4)))
 return dict(full_parent_runs=runs,window_runs=window_runs,connected_target_calls=roots,coverage=coverage,full_large_parent_qualified=False,opaque_fallback_helpers=True)

def rw(w):
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if op==0:
  if fn in(0,2,3):return{rt},{rd}
  if fn in(8,9):return{rs},{rd}if fn==9 else set()
  if fn in(16,18):return set(),{rd}
  if fn in(17,19):return{rs},set()
  if fn in(24,25,26,27):return{rs,rt},set()
  return{rs,rt},{rd}
 if op in(1,6,7,22,23):return{rs},set()
 if op in(4,5,20,21):return{rs,rt},set()
 if op in(2,3):return set(),{31}if op==3 else set()
 if 8<=op<=15:return{rs},{rt}
 if op==17:return({rt},set())if rs==4 else(set(),{rt})if rs==0 else(set(),set())
 if op in(32,33,34,35,36,37,38,39,55):return{rs},{rt}
 if op in(40,41,42,43,44,45,46,63):return{rs,rt},set()
 if op in(49,53,57,61):return{rs},set()
 raise AssertionError(('Unclassified V0 liveness opcode',hex(w)))

def v0_liveness(rom):
 with (root/'conker/retail_layout.us.txt').open()as f:layout=list(csv.DictReader(f))
 calls=(0x15054454,0x15060A84,0x15060AEC,0x15060B58,0x15076298);report=[]
 for call in calls:
  row=next(r for r in layout if r['section']=='game'and int(r['address'],16)<=call<int(r['end'],16));entry,end=int(row['address'],16),int(row['end'],16);ws=original(rom,entry,(end-entry)//4);code=dict(zip(range(entry,end,4),ws));pending=[call+8];seen=set();kills=[]
  def consume(pc):
   assert pc in code,('V0 escaped parent',hex(pc));reads,writes=rw(code[pc]);assert 2 not in reads,('Original caller reads void-result V0',row['function'],hex(pc));return 2 in writes
  while pending:
   pc=pending.pop()
   if pc in seen:continue
   seen.add(pc)
   if consume(pc):kills.append((hex(pc),'definition'));continue
   w=code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op in(2,3)or op==0 and fn in(8,9):
    if consume(pc+4):kills.append((hex(pc+4),'delay definition'));continue
    if op==3 or op==0 and fn==9:kills.append((hex(pc),'next call'));continue
    if op==0:
     path=root/('conker/src/'+row['filename']+'.c');signature=body(path.read_text(),row['function']).split('{',1)[0].strip();assert signature.startswith('void '),('Unknown parent return type',signature);kills.append((hex(pc),'known void parent return'));continue
    pending.append(((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));continue
   if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
    d=pc+4+((((w&65535)^32768)-32768)*4);likely=op in(20,21,22,23)or op==1 and rt&2 or op==17 and rt&2;kill=consume(pc+4)
    if not kill:pending.append(d)
    if not kill or likely:pending.append(pc+8)
    if kill:kills.append((hex(pc+4),'branch-delay definition'))
   else:pending.append(pc+4)
  assert kills;report.append(dict(call=hex(call),parent=row['function'],visited_words=len(seen),kills=kills,read_before_kill=False))
 return report

def main():
 s=alloc.symbols();rom=(root/'conker/conker.us.bin').read_bytes();name='func_15060778';programs={label:boundaries.bound(out/(name+suffix),name,s)for label,suffix in(('raw','-raw.o'),('normalized','-generic.o'),('retail','-reference.o'))};r=caller_suite(rom,programs);r['V0_liveness']=v0_liveness(rom);(base/'original-callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
