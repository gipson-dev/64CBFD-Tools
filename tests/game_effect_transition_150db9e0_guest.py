"""Complete descriptor transfers, opaque call mutations and identical access cuts."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_effect_transition_150db9e0_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x150DB9E0;ACTOR=0x30000;MARK=0x70000;RESULT=0x60000;PRESET=0x15196438;ORIENTED=0x15152F70;SPAWN=0x151491F4;SHORT=0x15153298;DATA=0x80090514;CONSTANTS=tuple(range(0x800A0C00,0x800A0C24,4));u32=lambda v:v&0xFFFFFFFF
CONSTANT_NAMES=tuple('D_%08X'%a for a in CONSTANTS)
LONG_KNOWN=tuple([*range(0x3A),*range(0x3C,0x56)]);SHORT_KNOWN=tuple(range(0x3E))
@dataclass(frozen=True)
class Case:
 actor:int=ACTOR
 transition:int=0
 channel:int=0xABCD00FE
 mutation:int=0
 private:int=0
 phase:int=0
 seed:int=0
 fcsr:int=0
def symbols():return dict(func_15196438=PRESET,func_15152F70=ORIENTED,func_151491F4=SPAWN,func_15153298=SHORT,D_80090514=DATA,**dict(zip(CONSTANT_NAMES,CONSTANTS)))
@lru_cache(maxsize=1)
def rom():return(r/'conker/conker.us.bin').read_bytes()
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+4096}
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,4096)}
 for base,n in((ACTOR,512),(RESULT,128),(MARK,16),(DATA,64)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for i,a in enumerate(CONSTANTS):put(m,a,struct.unpack_from('>I',rom(),0x2456C0+4*i)[0]^((c.seed&3)<<16))
 return m
def effect(m,c,t,home):
 put(m,MARK,read(m,MARK)+1)
 if c.mutation:
  first=0 if t==PRESET else 4
  for i in range(first,9):put(m,CONSTANTS[i],u32(0x3F000001+i*0x12345+c.seed*3+((t>>2)&0xFFFF)))
 if c.private:
  put(m,home+8,0x12340011)
  if t==ORIENTED:put(m,home-208+0x78,0x7FC12345)
 return RESULT if c.mutation&1 else 0
def observation(m,t,args):
 known=LONG_KNOWN if t==ORIENTED else SHORT_KNOWN if t==SHORT else()
 return t,args,tuple(m[args[0]+i]for i in known)
def write_fields(m,base,fields):
 for offset,value,n in fields:put(m,base+offset,value,n)
def long_fields(m):
 fs=[(i*4,read(m,a),4)for i,a in enumerate(CONSTANTS[:3])]
 fs.extend((offset,value,4)for offset,value in((0xC,0x40400000),(0x10,0x40400000),(0x14,read(m,CONSTANTS[3])),(0x18,0),(0x1C,0x41100000),(0x20,0x41000000)))
 fs.extend((offset,value,2)for offset,value in((0x24,8),(0x26,8),(0x28,-75),(0x2C,-38),(0x2A,22),(0x2E,35),(0x30,3),(0x32,2),(0x34,41),(0x36,0)))
 fs.extend([(0x38,10,1),(0x39,40,1),*( (offset,value,4)for offset,value in((0x3C,1),(0x40,0),(0x44,0),(0x48,0),(0x4C,0),(0x50,0))),(0x54,255,1),(0x55,255,1)]);return fs
def short_fields(m):
 fs=[(i*4,read(m,a),4)for i,a in enumerate(CONSTANTS[4:7])]
 fs.extend((offset,value,2)for offset,value in((0xC,6),(0xE,3),(0x10,-74),(0x14,-38),(0x12,21),(0x16,35),(0x20,14),(0x22,14),(0x24,-61),(0x26,28),(0x2A,6),(0x2C,6),(0x2E,0),(0x30,174),(0x32,115),(0x34,115),(0x36,135)))
 fs.extend([(0x28,255,1),(0x29,18,1),(0x38,DATA,4),(0x3C,255,1),(0x3D,255,1),(0x18,read(m,CONSTANTS[7]),4),(0x1C,read(m,CONSTANTS[8]),4)]);return fs
def reference(initial,c,home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial);calls=[];obs=[];channel=c.channel&255
 def call(t,args):
  args=tuple(map(u32,args));calls.append((t,args));obs.append(observation(m,t,args));effect(m,c,t,home)
 if c.actor:
  if u32(c.transition)==0:
   call(PRESET,(c.actor,1,channel,0));base=home-208+0x78;write_fields(m,base,long_fields(m));call(ORIENTED,(base,channel));call(SPAWN,(30,-1,0,1,0,0,channel,0));base=home-208+0x38;write_fields(m,base,short_fields(m));call(SHORT,(base,channel,1))
  elif u32(c.transition)==1:call(PRESET,(c.actor,2,channel,0))
 return public(m,c),calls,obs,c.fcsr
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.home=STACK+c.phase;self.observations=[];super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(u32(c.actor),u32(c.transition),u32(c.channel))if arguments is None else arguments,s=symbols(),connected=connected);self.initial=dict(self.memory);self.fcsr=c.fcsr;self.before_f=self.f[:]
 def record_call(self,t):
  counts={PRESET:4,ORIENTED:2,SPAWN:8,SHORT:3};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args));self.observations.append(observation(self.memory,t,args))
 def hook(self,t):
  value=effect(self.memory,self.c,t,self.home)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def observable(m):return public(m.memory,m.c),m.calls,m.observations,m.fcsr
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);assert observable(m)==want,dict(case=str(c),components=[a==b for a,b in zip(observable(m),want)],actual_calls=m.calls,want_calls=want[1],actual_observations=m.observations,want_observations=want[2]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 return [Case(actor=actor,transition=t,channel=channel,mutation=mutation,private=private,phase=phase,seed=channel&7,fcsr=csr)for actor,t,channel,mutation,private,phase,csr in itertools.product((0,ACTOR),(0,1,2,-1,0x80000000),(0,255,0xABCD0080,0x12340001),(0,1),(0,1),(0,8),(0,3))]
def pin_helpers():
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes()
 for a in CONSTANTS:
  at=elf_slot_offset(elf,a,4);romat=0x2456C0+a-CONSTANTS[0];assert elf[at:at+4]==rom()[romat:romat+4]
 q=[]
 for asmfile,fn in [('1C2C60.s','func_15196438'),('17CAF0.s','func_15152F70'),('17CAF0.s','func_15153298')]:
  text=(o/'baseline/conker/asm'/asmfile).read_text();body=text.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',body);blob=bytes.fromhex(''.join(x[2]for x in rows));at=int(rows[0][0],16);entry=int(rows[0][1],16);assert blob==rom()[at:at+len(blob)];start=elf_slot_offset(elf,entry,len(blob));assert elf[start:start+len(blob)]==blob,fn;q.append(dict(function=fn,words=len(rows),frozen_ELF_ROM_equal=True))
 return q
def main():
 helpers=pin_helpers();files=['original-target.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o','selected-owner.o'];streams=[bound_blob(*payload(o/f,'func_150DB9E0'),symbols())for f in files];assert all(w==streams[0]for w in streams[:4]);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+640)
 prefixes=0
 for c in(Case(actor=0),Case(),Case(transition=1),Case(transition=-1),Case(mutation=1,private=1,phase=8)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 missing=sorted(set(range(ENTRY,ENTRY+640,4))-seen);assert not missing,missing
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),unreachable_words=[],fault_prefix_quintuples=prefixes,raw_and_literal_full_private_completion_and_fault_identity=True,independent_reference_public_memory_calls_initialized_record_bytes_FCSR_equal=True,void_return_V0_not_consumed_or_independently_equated=True,all_descriptor_unwritten_bytes_preserved=True,all9_float_bindings_ROM_ELF_pinned=True,existing_helper_pins=helpers,helpers_opaque_with_live_global_record_and_incoming_home_mutations=True,private_home_probes_not_portable_C=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
