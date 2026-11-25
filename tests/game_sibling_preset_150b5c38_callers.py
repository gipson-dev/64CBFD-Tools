"""Execute both complete original parents on their target-reaching routes."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import hashlib,itertools,json,math,struct,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_sibling_preset_150b5c38_guest as g
from tools.tests.game_animation_timeline_oracle import floating,signed
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_sibling_preset_150b5c38_match as p
r,o=p.ROOT,p.OUT
SMALL,BIG,GEOMETRY,TRANSFORM=0x15071690,0x15081e78,0x150b60e0,0x15143134
ACTOR,RECORD,MATRIX,ATTACHED=0x37000,0x36000,0x60000,0x62000
SOURCE,TABLE,SCALE=0x8009fc30,0x80099ac4,0x8009cc28
PARENT_COUNTS={TRANSFORM:3,0x1506ac8c:3,0x15145974:3,0x150b6754:2,0x15137610:6,0x150d7120:3,0x1505d024:4}
def original(a,n,rom):return list(struct.unpack_from('>'+str(n)+'I',rom,a-0x15000000+0x2d4b0))
def pin(a,n,rom,elf,baseline_equal=True):
 blob=struct.pack('>'+str(n)+'I',*original(a,n,rom));at=elf_slot_offset(elf,a,len(blob));equal=elf[at:at+len(blob)]==blob
 assert equal or not baseline_equal
 return dict(address=hex(a),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=equal)
@lru_cache(maxsize=16)
def constant(a,n,rom,elf):
 from tools.patch_generated_slice_ld import load_game_data_layout
 start,base,end,_=load_game_data_layout(r/'conker');at=elf_slot_offset(elf,a,n);blob=elf[at:at+n];assert blob==rom[start+a-base:start+a-base+n];return blob
@dataclass(frozen=True)
class Case(g.Case):
 parent:int=SMALL
 flag:int=0
 matrix:int=1
 state:int=2
 kind:int=0x94
 event:int=0
 health:int=0
 attached:int=0
 gate:int=0
 angle:int=g.bits(120.)
 owner_index:int=2
def owner(c):return g.u32(0x800cc2d0+c.owner_index*0x32c)
def point(c):return g.STACK+c.phase-12 if c.parent==SMALL else RECORD+8
def fixture(c,rom,elf):
 m=g.fixture(c)
 for a,n in [(ACTOR,812),(RECORD,128),(MATRIX,512),(ATTACHED,512),(owner(c),812)]:m.update({a+i:(i*23+c.seed*7+0x31)&255 for i in range(n)})
 g.put(m,0x800d154c,ACTOR);g.put(m,ACTOR+0x1d4,MATRIX if c.matrix else 0);m[ACTOR+0x74]=c.flag
 g.put(m,owner(c)+0x31c,ATTACHED if c.attached else 0);g.put(m,ATTACHED+0x1aa,0x7fff,2)
 g.put(m,RECORD,ACTOR);m[RECORD+0x59]=c.state;m[ACTOR+4]=c.kind;m[ACTOR+0x1ca]=c.health;m[ACTOR+0x125]=c.gate;m[ACTOR+0x104]=0
 for i,v in enumerate(c.coords):g.put(m,RECORD+8+4*i,v)
 for a,n in [(SOURCE,12),(TABLE,24),(SCALE,4)]:
  for i,v in enumerate(constant(a,n,rom,elf)):m[a+i]=v
 g.put(m,0x800be9f0,0x2b if c.seed&1 else 0)
 return m
def clobber(m,c,value=0x12345678):
 for i in range(4):m.put(m.r[29]+4*i,0xb5000000+i,4)
 for reg in(1,2,3,*range(4,16),24,25):m.r[reg]=0xa5000000+reg
 m.f[:20]=[0xa5000000+i for i in range(20)];m.hi,m.lo=0xa5000010,0xa5000011;m.r[2]=value;m.fcsr^=0x10000
def parent_effect(memory,c,t,args):
 g.put(memory,g.MARK,g.read(memory,g.MARK)+1)
 if t==TRANSFORM:
  assert args==(SOURCE,point(c),MATRIX+0x140)
  for i,v in enumerate(c.coords):g.put(memory,args[1]+4*i,v)
 if t==0x15145974:
  assert args==(RECORD+0x38,g.STACK+c.phase-8,g.STACK+c.phase-12)
  g.put(memory,args[1],c.angle);g.put(memory,args[2],g.bits(.25))
class Connected(g.Machine):
 def __init__(self,body,c,rom,elf):
  self.parent_case=c;self.parent_home=g.STACK+c.phase;self.pending=False;self.children=[];self.parent_calls=[];self.wrapper_calls=[]
  code=dict(zip(range(g.ENTRY,g.ENTRY+508,4),body));code.update(zip(range(GEOMETRY,GEOMETRY+48,4),original(GEOMETRY,12,rom)))
  super().__init__(original(c.parent,23 if c.parent==SMALL else 466,rom),c,entry=c.parent,memory=fixture(c,rom,elf),args=(0x12345678,)if c.parent==SMALL else(owner(c),RECORD,c.event),connected=code)
 def close_child(self):
  self.children.append(dict(case=self.c,initial=self.child_initial,final=dict(self.memory),calls=self.calls[self.child_start:],observations=self.observations[self.obs_start:],fcsr=self.fcsr));self.pending=False;self.c=self.parent_case;self.provider_count=0
 def execute(self,w):
  if self.pending and self.current_pc in (0x150716dc,0x15082180):self.close_child()
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and(rs in (2,6)or rs==16 and fn==36):AreaOracle.execute(self,w)
  elif op==17 and rs==16 and fn in(1,2):
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;self.f[fd],flags=arithmetic(self.f[fs],self.f[ft],fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(3)));self.calls.append((t,args));self.events.append(('CALL',t,args));assert not self.pending and args==(point(self.parent_case),255,1)
   self.c=replace(self.parent_case,point=args[0],mode=args[1],extra=args[2],phase=self.r[29]-g.STACK,rm=self.fcsr,caller_actor=ACTOR);self.child_initial=dict(self.memory);self.child_start=len(self.calls);self.obs_start=len(self.observations);self.provider_count=0;self.pending=True;return
  if t==GEOMETRY:
   args=tuple(self.arguments(2));self.calls.append((t,args));self.events.append(('CALL',t,args));self.wrapper_calls.append((t,args));return
  if t in PARENT_COUNTS:
   args=tuple(map(g.u32,self.arguments(PARENT_COUNTS[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.parent_calls.append((t,args));return
  super().record_call(t)
 def hook(self,t):
  if t not in PARENT_COUNTS:return super().hook(t)
  parent_effect(self.memory,self.parent_case,t,self.calls[-1][1]);clobber(self,self.parent_case)
def verify(m,c):
 assert not m.pending
 if c.parent==SMALL:
  active=bool(c.matrix and(c.flag&15)!=15);expected_calls=[(GEOMETRY,(ACTOR,point(c))),(TRANSFORM,(SOURCE,point(c),MATRIX+0x140))]if active else[]
 else:
  active=c.state==2 and c.kind==0x94 and not(c.health and c.gate)
  expected_calls=[]
  if c.state!=0:
   if c.event in(5,9,10):expected_calls.append((0x1506ac8c,(owner(c),3,0)))
   if not(c.health and c.gate):expected_calls.append((0x15145974,(RECORD+0x38,g.STACK+c.phase-8,g.STACK+c.phase-12)))
 assert len(m.children)==int(active),(c,'child count')
 expected=dict(m.initial)
 if c.parent==BIG and c.attached:g.put(expected,ATTACHED+0x1aa,0x8000,2)
 allcalls=[];fcsr=c.rm
 for t,args in expected_calls:
  allcalls.append((t,args))
  if t!=GEOMETRY:parent_effect(expected,c,t,args);fcsr^=0x10000
 if active:
  child=m.children[0];cc=child['case'];assert cc.rm==fcsr
  assert tuple(g.read(child['initial'],point(c)+4*i)for i in range(3))==c.coords
  assert g.public(child['initial'],cc)==g.public(expected,cc),'Parent public child prestate'
  end,calls,obs,fcsr,value=g.reference(child['initial'],cc)
  assert child['calls']==calls and child['observations']==obs
  assert g.public(child['final'],cc)==g.public(end,cc)and g.data(child['final'],g.packet(cc),116)==g.data(end,g.packet(cc),116)and child['fcsr']==fcsr
  expected=end;allcalls.extend([(g.ENTRY,(point(c),255,1)),*calls])
 if c.parent==BIG and c.state and not(c.health and c.gate):
  cleanup=[]
  if active:cleanup.append((0x150b6754,(255,1)))
  else:cleanup.append((0x15137610,(ACTOR,RECORD+8,RECORD+0x20,RECORD+0x38,255,1)))
  if c.event==13:cleanup.append((0x150d7120,(RECORD+8,255,1)))
  for t,args in cleanup:parent_effect(expected,c,t,args);fcsr^=0x10000;allcalls.append((t,args))
  if c.health:
   diff,flags=arithmetic(c.angle,g.bits(90.),1,fcsr&3);fcsr=(fcsr&~0x3f000)|flags
   scaled,flags=arithmetic(diff,g.read(expected,SCALE),2,fcsr&3);fcsr=(fcsr&~0x3f000)|flags
   v=floating(scaled);converted=math.trunc(v)if math.isfinite(v)and 0<=v<2**32 else 0xffffffff
   flag=expected[TABLE+c.event]
   if c.event==7 and g.read(expected,0x800be9f0)==0x2b:flag=0x27
   args=(ACTOR,flag|0x80000,converted&65535,g.u32(c.owner_index));allcalls.append((0x1505d024,args));parent_effect(expected,c,0x1505d024,args);fcsr^=0x10000
 assert m.calls==allcalls,(c,'call sequence',m.calls,allcalls)
 assert g.public(m.memory,c)==g.public(expected,c),(c,'final public state')
 assert m.fcsr==fcsr,(c,'final FCSR',m.fcsr,fcsr)
 assert m.r[29]==m.parent_home and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 if c.parent==BIG:assert m.r[2]==(0 if c.state==0 else 2)
 return active
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();pins=[pin(SMALL,23,rom,elf),pin(BIG,466,rom,elf),pin(GEOMETRY,12,rom,elf)]
 corpus=[Case(flag=flag,matrix=matrix,mutation=(0,15)[flag&1],phase=(flag&1)*8,rm=flag&3,seed=flag&15)for flag,matrix in itertools.product(range(256),(0,1))]
 corpus +=[Case(parent=BIG,state=state,kind=kind,event=event,health=health,attached=attached,gate=gate,mutation=mutation,rm=rm,phase=8*(event&1),seed=event&3,angle=angle,owner_index=index)for state,kind,event,health,attached,gate,mutation,rm,angle,index in itertools.product((0,2),(0x93,0x94),(0,5,7,9,10,13),(0,1),(0,1),(0,1),(0,15),(0,3),(g.bits(90.),g.bits(120.),g.bits(-120.),g.bits(1e20)),(-1,2))]
 retail=g.programs();assert len(retail)==4 and all(w==retail[0]for w in retail)
 programs=[retail[0],g.raw_program()];counts={};seen={SMALL:set(),BIG:set(),GEOMETRY:set()};children=0
 for c in corpus:
  models=[]
  for words in programs:
   m=Connected(words,c,rom,elf).run();verify(m,c);models.append(m)
  a=models[0];assert all((a.memory,a.calls,a.observations,a.r,a.f,a.fcsr,a.hi,a.lo)==(b.memory,b.calls,b.observations,b.r,b.f,b.fcsr,b.hi,b.lo)for b in models[1:])
  counts[c.parent]=counts.get(c.parent,0)+1;children+=len(a.children)
  for address,n in [(SMALL,23),(BIG,466),(GEOMETRY,12)]:seen[address]|={pc for pc in a.visits if address<=pc<address+4*n}
 assert seen[SMALL]==set(range(SMALL,SMALL+92,4));assert seen[GEOMETRY]==set(range(GEOMETRY,GEOMETRY+48,4))
 controls=[];c=Case(parent=BIG,event=13,health=1,mutation=15,angle=g.bits(120.))
 for name,find,change in [('child-count',lambda w:w>>26==9 and w&65535==13,lambda w:w+1),('child-provider',lambda w:w>>26==3 and(w&0x3ffffff)==((g.OTHER>>2)&0x3ffffff),lambda w:0x0c000000|((g.TAIL>>2)&0x3ffffff))]:
  bad=list(programs[0]);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);m=Connected(bad,c,rom,elf).run();assert not m.pending and m.r[2]==2 and m.r[29]==m.parent_home
  try:verify(m,c)
  except AssertionError:controls.append(dict(name=name,supported_complete_parent_execution=True,rejected=True))
  else:raise AssertionError('Ineffective full-parent control')
 q=dict(original_pins=pins,streams=len(programs),cases_per_parent={hex(a):n for a,n in counts.items()},connected_children_per_stream=children,visited_parent_words={hex(a):len(v)for a,v in seen.items()},large_parent_scope='complete entry-to-return state0 and state2 paths; state1/state3 non-target dispatch excluded explicitly',all256_manual_caller_flags=True,manual_caller_12byte_stack_position=True,large_caller_12byte_record_position=True,large_parent_health_gate_cleanup_event13_and_unsigned_conversion_paths=True,parent_FP_subtract_multiply_rounding_and_conversion_FCSR_preservation=True,original_geometry_wrapper_executed=True,transform_internals_contracted=True,raw_child_fault_order_not_claimed=True,source_installed=p.installed(),matching_credit=0)
 q['effective_controls']=controls
 q['four_retail_programs_byte_identical_and_executed_once_per_case']=True
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
