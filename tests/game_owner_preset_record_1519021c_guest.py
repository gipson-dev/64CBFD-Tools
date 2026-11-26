"""Preset bounds, captured owner/position and three ordered attachment copies."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle,data
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_pointer_quad_vertices_150db714_guest import trunc
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_owner_preset_record_1519021c_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x1519021C;ACTOR=0x30000;PARENT=0x40000;OUTPUT=0x60000;MARK=0x70000;FACTORY=0x151602C0;COPY=0x10022EC0;TABLES=(0x800A6760,0x800A67C0,0x800A6820);SCALAR=0x800A8004;bits=fp.bits;u32=lambda x:x&0xFFFFFFFF;half=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 preset:int=0
 lifetime:int=0xABCDFfff
 channel:int=0xABCD0080
 context:int=0x87654321
 parent:int=PARENT
 actor:int=ACTOR
 coordinates:tuple=tuple(map(bits,(10.5,-12.25,3.75)))
 success:int=1
 mutation:int=0
 alias:int=0
 copy:int=0
 rm:int=0
 phase:int=0
 seed:int=0

def symbols():return dict(func_151602C0=FACTORY,memcpy=COPY,D_800A6760=TABLES[0],D_800A67C0=TABLES[1],D_800A6820=TABLES[2],D_800A8004=SCALAR)
@lru_cache(maxsize=1)
def rom():return(r/'conker/conker.us.bin').read_bytes()
def result(c):return ACTOR if c.alias else OUTPUT
def args(c):return tuple(map(u32,(c.parent,c.actor,c.preset,c.lifetime,c.channel,c.context)))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,4096)}
 for base,n in((ACTOR,512),(PARENT,128),(OUTPUT-32,192),(MARK,16)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for a,at in zip(TABLES,(0x24B220,0x24B280,0x24B2E0)):m.update({a+i:b for i,b in enumerate(rom()[at:at+96])})
 put(m,SCALAR,struct.unpack_from('>I',rom(),0x24CAC4)[0])
 for i,v in enumerate(c.coordinates):put(m,ACTOR+0x14+4*i,v)
 m[ACTOR+0x3B]=(c.seed*37+0x80)&255;return m
def effect(m,c,t,n):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation:
  m[ACTOR+0x3B]^=0x55
  for i,v in enumerate((bits(-7.5),bits(19.25),bits(-3.5))):put(m,ACTOR+0x14+4*i,v)
  for a in(*TABLES,SCALAR):put(m,a,bits(float(n+2)))
def reference(initial,c,home=None,arguments=None,initial_fcsr=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;parent,actor,preset,lifetime,channel,context=args(c)if arguments is None else arguments;preset&=255;lifetime=half(lifetime);channel&=255;csr=c.rm if initial_fcsr is None else initial_fcsr;calls=[];obs=[];ops=[];counts={};frame=home-144
 put(m,home+8,u32(preset if arguments is None else arguments[2]));put(m,home+12,u32(c.lifetime if arguments is None else arguments[3]))
 if preset>=24:return public(m,c),calls,obs,ops,csr,0
 header,owner,values,position=frame+0x84,frame+0x7C,frame+0x5C,frame+0x4C
 put(m,frame+0x58,parent)
 for i,v in enumerate((read(m,TABLES[1]+4*preset),read(m,TABLES[0]+4*preset),read(m,TABLES[2]+4*preset),bits(1.),0,bits(5.),read(m,SCALAR),0)):put(m,values+4*i,v)
 m[header]=2 if lifetime==-1 else 3;m[header+1]=18;put(m,header+2,300 if lifetime==-1 else lifetime,2);m[header+4]=37;put(m,owner,actor);m[owner+4]=m[actor+0x3B]
 for i in range(3):
  a=read(m,actor+0x14+4*i);ops.append((13,a,0,csr));v,flags=trunc(a);csr=(csr&~0x3F000)|flags;put(m,position+4*i,v)
 a=(header,position,0,255,209,0,255,0,48,channel,u32(context));calls.append((FACTORY,a));obs.append((FACTORY,a,data(m,header,6),data(m,position,12)));counts[FACTORY]=1;effect(m,c,FACTORY,1);answer=result(c)if c.success else 0
 if answer:
  for i,b in enumerate(data(m,header,6)):m[answer+14+i]=b
  put(m,answer+20,0x12340000);m[answer+14]|=2
  for offset,src,n in((24,owner,8),(32,values,32),(64,frame+0x58,4)):
   a=(answer+offset,src,n);calls.append((COPY,a));obs.append((COPY,a,data(m,src,n),b''));counts[COPY]=counts.get(COPY,0)+1
   for i,b in enumerate(data(m,src,n)):m[a[0]+i]=b
   effect(m,c,COPY,counts[COPY])
 return public(m,c),calls,obs,ops,csr,answer
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.home=STACK+c.phase;self.observations=[];self.fp_operations=[];self.counts={};code=dict(connected or{})
  if c.copy:code.update(zip(range(COPY,COPY+44,4),struct.unpack_from('>11I',rom(),0x22EC0)))
  super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=args(c)if arguments is None else arguments,s=symbols(),connected=code);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   fs,fd=w>>11&31,w>>6&31;a=self.f[fs];self.fp_operations.append((13,a,0,self.fcsr));v,flags=trunc(a);self.f[fd]=v;self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  assert t in(FACTORY,COPY),hex(t);a=tuple(map(u32,self.arguments(11 if t==FACTORY else 3)));self.calls.append((t,a));self.events.append(('CALL',t,a));self.counts[t]=self.counts.get(t,0)+1;self.observations.append((t,a,data(self.memory,a[0],6)if t==FACTORY else data(self.memory,a[1],a[2]),data(self.memory,a[1],12)if t==FACTORY else b''))
  if t==COPY and self.c.copy:assert not self.c.mutation;effect(self.memory,self.c,t,self.counts[t])
 def hook(self,t):
  a=self.calls[-1][1]
  if t==FACTORY:
   effect(self.memory,self.c,t,1);value=result(self.c)if self.c.success else 0
   if value:
    for i,b in enumerate(data(self.memory,a[0],6)):self.memory[value+14+i]=b
    put(self.memory,value+20,0x12340000);self.memory[value+14]|=2
  else:
   for i,b in enumerate(data(self.memory,a[1],a[2])):self.memory[a[0]+i]=b
   effect(self.memory,self.c,t,self.counts[t]);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def observable(m):return public(m.memory,m.c),m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);assert observable(m)==want,dict(case=str(c),components=[a==b for a,b in zip(observable(m),want)]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def pin():
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes()
 for entry,at,n in(*[(a,at,96)for a,at in zip(TABLES,(0x24B220,0x24B280,0x24B2E0))],(SCALAR,0x24CAC4,4),(FACTORY,0x18D770,188),(0x1516037C,0x18D82C,128),(COPY,0x22EC0,44)):
  start=elf_slot_offset(elf,entry,n);assert elf[start:start+n]==rom()[at:at+n],(hex(entry),hex(at))
def cases():
 rows=[Case(preset=p,lifetime=l,channel=0xABCD00FF,success=s,mutation=m,alias=a,rm=rm,seed=p+rm,phase=8*(rm&1))for p,l,s,m,a,rm in itertools.product((0,1,12,23,24,255,0x12340018,0xABCDEF00),(0xFFFFFFFF,0xFFFF8000,0,0x1234012C),(0,1),(0,1),(0,1),(0,3))]
 rows.extend(Case(preset=p,actor=0)for p in range(24,256));rows.extend(Case(preset=p,rm=rm)for p,rm in itertools.product(range(24),range(4)));rows.extend(Case(preset=p,copy=1,rm=rm,success=s)for p,rm,s in itertools.product((0,23),range(4),(0,1)));return rows
def main():
 pin();files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];streams=[bound_blob(*payload(o/f,'func_1519021C'),symbols())for f in files];assert all(w==streams[0]for w in streams);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+436)
 prefixes=0
 for c in(Case(),Case(success=0,lifetime=3),Case(preset=24,actor=0),Case(mutation=1,alias=1),Case(copy=1)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 assert len(seen)==109,(len(seen),sorted(set(range(ENTRY,ENTRY+436,4))-seen))
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=109,fault_prefix_quintuples=prefixes,all_raw_and_literal_full_private_completion_and_fault_states_equal=True,independent_reference_public_memory_calls_payload_return_FP_and_FCSR_equal=True,invalid_presets24_through255_null_actor_no_reads=True,unwritten_header5_and_pair_padding3_preserved_in_guest=True,captured_before_mutating_factory_and_copy_providers=True,actual11word_memcpy_connected_on_nonmutating_paths=True,existing47word_factory32word_wrapper11word_copy_tables24_and_scalar_ROM_ELF_pinned=True,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
