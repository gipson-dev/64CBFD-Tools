"""Both full original127-word parents execute the candidate child under bounded providers."""
from pathlib import Path
from dataclasses import replace
from functools import lru_cache
import hashlib,importlib.util,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests import game_random_particle_150b5e34_guest as g
from tools.experiments import game_random_particle_150b5e34_match as p
r,o=g.r,g.o;SUBMIT,TAIL=0x15152b38,0x150b6000;PARENTS=(0x150b5a3c,0x150b5c38)
def original(a,n,rom):return list(struct.unpack_from('>'+str(n)+'I',rom,a-0x15000000+0x2d4b0))
def pin(a,n,rom,elf):
 blob=struct.pack('>'+str(n)+'I',*original(a,n,rom));at=elf_slot_offset(elf,a,len(blob));live=elf[at:at+len(blob)];matched=live==blob
 if a==PARENTS[0]:assert matched
 else:
  assert a==PARENTS[1]and not matched
  stub,refs=payload(o/'baseline/conker/build/src/game/generated_E2DA0.c.o','func_150B5C38');assert len(stub)==12 and not refs and live[:12]==stub and not any(live[12:])
 return dict(address=hex(a),words=n,sha256=hashlib.sha256(blob).hexdigest(),matches_frozen_ELF=matched,original_ROM_execution_only=not matched,frozen_slot_sha256=hashlib.sha256(live).hexdigest())
@lru_cache(maxsize=1)
def constants():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes()
 from tools.patch_generated_slice_ld import load_game_data_layout
 start,base,end,_=load_game_data_layout(r/'conker');at=elf_slot_offset(elf,0x8009fca0,28);blob=elf[at:at+28];assert blob==rom[start+0x8009fca0-base:start+0x8009fca0-base+28];return blob
def fixture(c):
 m=g.fixture(c)
 for i,v in enumerate(constants()):m[0x8009fca0+i]=v
 return m
def parent_effect(m,c,t,args):
 g.put(m,g.MARK,g.read(m,g.MARK)+1)
 if c.mutation&1:
  for p in(g.POINT,g.ALT):
   for i in range(3):g.put(m,p+4*i,g.bits(float(80+i)))
 if t==SUBMIT:
  if c.mutation&2:
   for i in range(116):m[args[0]+i]=(i*5+c.seed*11+0x73)&255
  if c.ghost_homes:g.put(m,g.home(c),g.ALT);g.put(m,g.home(c)+4,0xabcd0072);g.put(m,g.home(c)+8,0x12345678)
 return 0x87654321
class Connected(g.Machine):
 def __init__(self,words,c,parent,rom,raw=False):
  self.parent_case=c;self.parent_home=g.home(c);self.parent=parent;self.pending=False;self.children=[];self.parent_observations=[];self.child_raw=raw
  body=original(parent,127,rom);sites=[parent+4*i+8 for i,w in enumerate(body)if w>>26==3 and ((w&0x3ffffff)<<2)==(g.ENTRY&0xfffffff)];assert len(sites)==1;self.child_return=sites[0]
  code=dict(zip(range(g.ENTRY,g.ENTRY+460,4),words));super().__init__(body,c,entry=parent,memory=fixture(c),args=g.arguments(c),connected=code);self.raw=False
 def close_child(self):
  self.children.append(dict(case=self.c,initial=self.child_initial,final=dict(self.memory),calls=self.calls[self.child_call_start:],observations=self.observations[self.child_observation_start:],mapped_frames=self.mapped_frames[self.child_frame_start:],final_frame=self.frame(),fcsr=self.fcsr,result=self.r[2]));self.pending=False;self.c=self.parent_case;self.raw=False;self.provider_count=0
 def execute(self,w):
  if self.pending and self.current_pc==self.child_return:self.close_child()
  super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(3)));self.calls.append((t,args));self.events.append(('CALL',t,args));assert not self.pending
   self.c=replace(self.parent_case,point=args[0],mode=args[1],extra=args[2],phase=self.r[29]-g.STACK,fcsr=self.fcsr)
   if self.child_raw:
    a=g.home(self.c)-152+0x20;b=a+4;x=g.data(self.memory,a,4);y=g.data(self.memory,b,4)
    for i in range(4):self.memory[a+i]=y[i];self.memory[b+i]=x[i]
   self.raw=self.child_raw;self.child_initial=dict(self.memory);self.child_call_start=len(self.calls);self.child_observation_start=len(self.observations);self.child_frame_start=len(self.mapped_frames);self.provider_count=0;self.pending=True;return
  if t in(SUBMIT,TAIL):
   args=tuple(map(g.u32,self.arguments(3)));self.calls.append((t,args));self.events.append(('CALL',t,args));self.parent_observations.append((t,args,g.public(self.memory,self.parent_case),g.data(self.memory,self.parent_home-116,116),self.fcsr));return
  assert self.pending;super().record_call(t)
 def hook(self,t):
  if t not in(SUBMIT,TAIL):return super().hook(t)
  value=parent_effect(self.memory,self.parent_case,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value;self.fcsr=g.provider_csr(self.parent_case,6 if t==SUBMIT else 7)
def verify(m,c):
 assert not m.pending and len(m.children)==1 and len(m.parent_observations)==2
 first,last=m.parent_observations;cc=m.children[0]['case'];child=m.children[0];memory=dict(m.initial)
 for i,v in enumerate(g.arguments(c)):g.put(memory,m.parent_home+4*i,v)
 expected_first=(m.parent_home-116,c.mode&255,g.u32(c.extra));assert first[0]==SUBMIT and first[1]==expected_first
 assert tuple(int.from_bytes(first[3][8+4*i:12+4*i],'big')for i in range(3))==c.coords
 parent_effect(memory,c,SUBMIT,expected_first);expected_args=(g.read(memory,m.parent_home),memory[m.parent_home+7],g.read(memory,m.parent_home+8));assert g.arguments(cc)==expected_args
 assert g.public(child['initial'],cc)==g.public(memory,cc)
 expected,calls,obs,fcsr,value=g.reference(child['initial'],cc);assert child['calls']==calls and child['observations']==obs and child['fcsr']==fcsr and child['result']==value
 assert g.public(child['final'],cc)==g.public(expected,cc)and g.data(child['final'],g.packet(cc),112)==g.data(expected,g.packet(cc),112)
 assert last[0]==TAIL and last[1]==expected_args,'Parent must ignore child result and reload its own homes'
 assert last[3]==first[3]if not c.mutation&2 else last[3]==bytes((i*5+c.seed*11+0x73)&255 for i in range(116))
 parent_effect(expected,c,TAIL,expected_args);assert g.public(m.memory,c)==g.public(expected,c)
 assert m.r[29]==m.parent_home and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 return child
def observable(m,c):
 child=m.children[0]
 return(g.public(m.memory,c),m.parent_observations,child['calls'],child['observations'],child['mapped_frames'],child['final_frame'],m.r,m.f,m.fcsr,m.hi,m.lo)
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();pins=[pin(a,127,rom,elf)for a in PARENTS];programs=[*g.streams(),g.raw_program()];visited={a:set()for a in PARENTS};count=children=0
 rows=[g.Case(mode=mode,extra=extra,fcsr=rm,mutation=mutation,outcome=outcome,phase=8*(mode&1),seed=mode&7,rng=(mode,mode&1,(mode>>1)&1))for mode,extra,rm,mutation,outcome in itertools.product((0,127,128,255),(0,0x80000000,0xffffffff),range(4),(0,3),(0,1))]
 rows +=[g.Case(ghost_homes=True,mode=255,mutation=mutation,phase=phase)for mutation,phase in itertools.product((0,3),(0,8))]
 for parent,c in itertools.product(PARENTS,rows):
  models=[]
  for i,ws in enumerate(programs):
   m=Connected(ws,c,parent,rom,raw=i==4).run();verify(m,c);models.append(m);visited[parent]|={pc for pc in m.visits if parent<=pc<parent+508}
  assert all(observable(m,c)==observable(models[0],c)for m in models[1:]);count+=1;children+=len(models[0].children)
 assert all(v==set(range(a,a+508,4))for a,v in visited.items())
 controls=[];c=g.Case(mutation=3,ghost_homes=True)
 for name,find,change in [('child-mode-home',lambda w:w>>26==36 and w&65535==0x9f,lambda w:w-1),('child-position-word',lambda w:w>>26==35 and w>>21&31==10 and w&65535==0,lambda w:w+4)]:
  bad=list(programs[0]);at=next(i for i,w in enumerate(bad)if find(w));bad[at]=change(bad[at]);m=Connected(bad,c,PARENTS[0],rom).run();assert len(m.children)==1 and len(m.parent_observations)==2
  try:verify(m,c)
  except AssertionError:controls.append(dict(name=name,supported_complete_parent_execution=True,rejected=True))
  else:raise AssertionError('Ineffective caller control')
 q=dict(parents=pins,cases_per_stream=count,streams=5,connected_children_per_stream=children,both_direct_child_sites=True,each_parent_words_visited=127,post_child_parent_home_reload_and_result_ignored=True,complete_child112_bytes_observed=True,full_child_mapped_frames_and_return_registers_equal=True,parent_first_packet116_bytes_retained=True,original_parent_provider_internals_contracted=True,second_parent_still_unmatched_C=True,effective_controls=controls,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
