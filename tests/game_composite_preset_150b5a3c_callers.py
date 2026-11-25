"""Whole original parent, both child sites, and the original position wrapper."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import hashlib,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()));
from tools.tests import game_composite_preset_150b5a3c_guest as g
from tools.tests.game_animation_timeline_oracle import floating
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
PARENT,FRNG,GEOMETRY,TRANSFORM=0x150b5950,0x150ada68,0x150b60e0,0x15143134
ACTOR,RECORD,NEWACTOR,MATRIX,ALTMATRIX=0x37000,0x36000,0x38000,0x60000,0x61000
LIMITS,SOURCE=(0x8009fc98,0x8009fc9c),0x8009fc30
from tools.experiments import game_composite_preset_150b5a3c_match as p
o,r=p.OUT,p.ROOT
def original(a,n,rom):return list(struct.unpack_from('>'+str(n)+'I',rom,a-0x15000000+0x2d4b0))
def pin(a,n,rom,elf):
 words=original(a,n,rom);blob=struct.pack('>'+str(n)+'I',*words);at=elf_slot_offset(elf,a,len(blob));assert elf[at:at+len(blob)]==blob;return words,dict(address=hex(a),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=True)
@lru_cache(maxsize=16)
def constant(a,n,rom,elf):
 from tools.patch_generated_slice_ld import load_game_data_layout
 start,base,end,_=load_game_data_layout(r/'conker');at=elf_slot_offset(elf,a,n);blob=elf[at:at+n];assert blob==rom[start+a-base:start+a-base+n];return blob
@dataclass(frozen=True)
class Case(g.Case):
 valid:int=1
 identity:int=1
 matrix:int=1
 samples:tuple=(g.bits(0.),g.bits(0.))
def geometry_words(memory):return (g.bits(7.25),g.bits(-8.5),g.bits(9.75))if g.read(memory,ACTOR+0x1d4)==ALTMATRIX else(g.bits(-1.25),g.bits(2.5),g.bits(-3.75))
def fixture(c,rom,elf):
 m=g.fixture(c)
 for a,n in[(ACTOR,512),(NEWACTOR,512),(RECORD,64),(MATRIX,512),(ALTMATRIX,512)]:m.update({a+i:(i*23+c.seed*7+0x31)&255 for i in range(n)})
 g.put(m,ACTOR,c.valid);m[ACTOR+0x3b]=0xa1;m[RECORD+0x2c]=0xa1 if c.identity else 0xa2;g.put(m,RECORD+0x28,ACTOR);g.put(m,RECORD+0xe,123,2);m[RECORD+0xc]=c.mode;m[RECORD+1]=0x85
 g.put(m,ACTOR+0x1d4,MATRIX if c.matrix else 0)
 for i,v in enumerate(c.coords):g.put(m,ACTOR+0x14+4*i,v)
 for a in LIMITS:
  for i,v in enumerate(constant(a,4,rom,elf)):m[a+i]=v
 for i,v in enumerate(constant(SOURCE,12,rom,elf)):m[SOURCE+i]=v
 return m
class Connected(g.Machine):
 def __init__(self,body,c,rom,elf):
  self.parent_case=c;self.parent_home=g.STACK+c.phase;self.children=[];self.pending=False;self.rng_count=0;self.geometry_calls=[];self.helper_calls=[]
  code=dict(zip(range(g.ENTRY,g.ENTRY+508,4),body));code.update(zip(range(GEOMETRY,GEOMETRY+48,4),original(GEOMETRY,12,rom)))
  super().__init__(original(PARENT,59,rom),c,entry=PARENT,memory=fixture(c,rom,elf),args=(RECORD,),connected=code)
 def close_child(self):
  self.children.append(dict(case=self.c,initial=self.child_initial,final=dict(self.memory),calls=self.calls[self.child_call_start:],observations=self.observations[self.child_observation_start:],fcsr=self.fcsr));self.pending=False;self.c=self.parent_case;self.provider_count=0
 def execute(self,w):
  if self.pending and self.current_pc in(0x150b59e8,0x150b5a28):self.close_child()
  if w>>26==17 and w>>21&31==16 and w&63==60:
   fs,ft=w>>11&31,w>>16&31;self.condition=floating(self.f[fs])<floating(self.f[ft]);self.fcsr=(self.fcsr&~0x800000)|(0x800000 if self.condition else 0)
  else:super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(3)));self.calls.append((t,args));self.events.append(('CALL',t,args));assert not self.pending
   self.c=replace(self.parent_case,point=args[0],mode=args[1],extra=args[2],phase=self.r[29]-g.STACK,rm=self.fcsr,caller_record=RECORD,caller_actor=ACTOR);self.child_initial=dict(self.memory);self.child_call_start=len(self.calls);self.child_observation_start=len(self.observations);self.provider_count=0;self.pending=True;return
  if t in(FRNG,GEOMETRY,TRANSFORM):
   args=tuple(map(g.u32,self.arguments({FRNG:0,GEOMETRY:2,TRANSFORM:3}[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.helper_calls.append((t,args))
   if t==TRANSFORM:self.geometry_calls.append((args,g.data(self.memory,SOURCE,12)))
   return
  super().record_call(t)
 def hook(self,t):
  if t not in(FRNG,TRANSFORM):return super().hook(t)
  g.put(self.memory,g.MARK,g.read(self.memory,g.MARK)+1)
  if t==FRNG:value=self.parent_case.samples[self.rng_count];self.rng_count+=1
  else:
   a=self.calls[-1][1];assert a==(SOURCE,self.parent_home-16,g.u32(g.read(self.memory,ACTOR+0x1d4)+0x140)),a
   for i,v in enumerate(geometry_words(self.memory)):g.put(self.memory,a[1]+4*i,v)
   value=0x12345678
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value;self.fcsr=self.parent_case.rm
  if t==FRNG:self.f[0]=value
def verify(m,c):
 assert not m.pending;memory=dict(m.initial);calls=[];child_index=0;point=m.parent_home-16
 def child(expected_coords):
  nonlocal memory,child_index
  actual=m.children[child_index];child_index+=1;cc=actual['case'];args=(point,memory[RECORD+0xc],memory[RECORD+1]);assert g.arguments(cc)==args,(args,g.arguments(cc));assert tuple(g.read(actual['initial'],point+4*i)for i in range(3))==expected_coords
  assert g.public(actual['initial'],cc)==g.public(memory,cc),'Public child prestate differs'
  expected,inside,obs,fcsr,value=g.reference(actual['initial'],cc);assert actual['calls']==inside and actual['observations']==obs,'Child transfer differs';assert g.public(actual['final'],cc)==g.public(expected,cc)and g.data(actual['final'],g.packet(cc),116)==g.data(expected,g.packet(cc),116)and actual['fcsr']==fcsr
  calls.append((g.ENTRY,args));calls.extend(inside);memory=expected
 if not c.valid or not c.identity:g.put(memory,RECORD+0xe,0xffff,2)
 elif c.matrix:
  calls.append((FRNG,()));g.put(memory,g.MARK,g.read(memory,g.MARK)+1)
  if floating(c.samples[0])<floating(g.read(memory,LIMITS[0])):child(c.coords)
  calls.append((FRNG,()));g.put(memory,g.MARK,g.read(memory,g.MARK)+1)
  if floating(c.samples[1])<floating(g.read(memory,LIMITS[1])):
   calls.extend([(GEOMETRY,(ACTOR,point)),(TRANSFORM,(SOURCE,point,g.read(memory,ACTOR+0x1d4)+0x140))]);g.put(memory,g.MARK,g.read(memory,g.MARK)+1);child(geometry_words(memory))
 assert child_index==len(m.children);assert m.calls==calls,('Parent call sequence',m.calls,calls);assert g.public(m.memory,c)==g.public(memory,c),'Parent public state';assert m.r[29]==m.parent_home and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return child_index
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();_,parent_pin=pin(PARENT,59,rom,elf);_,geometry_pin=pin(GEOMETRY,12,rom,elf)
 limits=tuple(int.from_bytes(constant(a,4,rom,elf),'big')for a in LIMITS);assert all(0<floating(v)<.99 for v in limits);choices=[(g.bits(0.),v,g.bits(.999))for v in limits];programs=[*g.programs(),g.raw_program()];seen=set();geo=set();cases=children=0;routes=set();controls=[]
 for valid,identity,matrix,a,b,mutation,mode,rm in itertools.product((0,1),(0,1),(0,1),range(3),range(3),(0,15),(0,255),range(4)):
  c=Case(valid=valid,identity=identity,matrix=matrix,samples=(choices[0][a],choices[1][b]),mutation=mutation,mode=mode,rm=rm,phase=8*(mode&1));models=[]
  for words in programs:
   m=Connected(words,c,rom,elf).run();n=verify(m,c);models.append(m);seen|={pc for pc in m.visits if PARENT<=pc<PARENT+236};geo|={pc for pc in m.visits if GEOMETRY<=pc<GEOMETRY+48}
  left=models[0];assert all((left.memory,left.calls,left.observations,left.r,left.f,left.fcsr,left.hi,left.lo)==(right.memory,right.calls,right.observations,right.r,right.f,right.fcsr,right.hi,right.lo)for right in models[1:]);children+=len(left.children);cases+=1;routes.add(('stale'if not valid or not identity else'no-matrix'if not matrix else'active',len(left.children)))
 assert seen==set(range(PARENT,PARENT+236,4))-{0x150b598c};assert geo==set(range(GEOMETRY,GEOMETRY+48,4))
 c=Case(samples=(g.bits(0.),g.bits(0.)),mutation=15,mode=255)
 for name,alter in[('child-mode-byte',False),('child-provider-binding',True)]:
  bad=list(programs[0]);at=next(i for i,w in enumerate(bad)if w>>26==36 and w&65535==0x97)if not alter else next(i for i,w in enumerate(bad)if w>>26==3 and((w&0x3ffffff)<<2)==(g.OTHER&0xfffffff));bad[at]=bad[at]-1 if not alter else 0x0c000000|((g.TAIL>>2)&0x3ffffff)
  m=Connected(bad,c,rom,elf).run();assert len(m.children)==2
  try:verify(m,c)
  except AssertionError:controls.append(dict(name=name,supported_complete_parent_execution=True,rejected=True))
  else:raise AssertionError('Ineffective parent control')
 q=dict(parent=parent_pin,geometry_wrapper=geometry_pin,cases_per_stream=cases,streams=5,connected_children_per_stream=children,visited_parent_words=58,unreachable_original_parent_word='0x150B598C',visited_geometry_wrapper_words=12,both_child_sites_and_both_comparison_outcomes=True,stale_and_no_matrix_paths=True,post_child_mode_extra_threshold_matrix_reload=True,full_public_state_and_registers_equal=True,original_transform_internals_contracted=True,helpers_matching_credit=0,effective_controls=controls,routes=sorted(routes),source_installed=p.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
