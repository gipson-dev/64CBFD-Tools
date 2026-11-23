"""Raw C effects, normalized retail state, consumed packet and actual caller."""
from dataclasses import dataclass,replace
import itertools,json,struct
from tools.experiments import game_actor_emission_preset_150bffe0_match as checkpoint
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=checkpoint.ROOT,checkpoint.OUT
ENTRY=0x150BFFE0;PREPARE=0x15136C3C;FACTORY=0x15153634;ACTOR=0x30000;MARK=0x51000;WINDOW=0x1507D810;END=0x1507DB20
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
CONSTANTS={0x800A0134:0x3F828F5C,0x800A0138:0x43E18000,0x800A013C:0x43FA8000,0x800A0140:0x3EB53F7D,0x800A0144:0x3F20418A,0x800A0148:0x3F60A72F}
u32=lambda n:n&0xFFFFFFFF
def add32(bits,value):return int.from_bytes(struct.pack('>f',struct.unpack('>f',bits.to_bytes(4,'big'))[0]+value),'big')
@dataclass(frozen=True)
class Case:
 y:int=0
 actor:int=ACTOR
 phase:int=0
 mutation:int=0
 seed:int=0
def cases():
 ys=[0,0x80000000,0x3F800000,0xBF800000,0xC28C0000,0xC2D20000,0x4C000000,0xCC000000,1,0x80000001,0x00800000,0x7F7FFFFF,0x3EAAAAAB,0x42F60001,0x4BFFFFFF,0xCBFFFFFF]
 for i,y in enumerate(ys):
  for phase,mutation,actor in itertools.product((0,8),(0,1),(ACTOR,STACK+128)):
   yield Case(y,actor,phase,mutation,i)
def fixture(c=Case(),s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for p,n in ((ACTOR-32,0x240),(MARK,32)):m.update({p+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 for at,v in ((0x14,0x3F800001^(c.seed<<8)),(0x180,c.y),(0x1C,0x7FC01234^(c.seed<<8))):put(m,c.actor+at,v)
 for address,value in CONSTANTS.items():put(m,s[f'D_{address:08X}'],value)
 return m
def first_effect(m,c,s):
 put(m,MARK,0x13579BDF)
 if c.mutation:
  for at,v in ((0x14,0xC1200000),(0x180,0x4C800001),(0x1C,0x80000000)):put(m,c.actor+at,v)
  for address,value in CONSTANTS.items():put(m,s[f'D_{address:08X}'],value^((c.seed+1)<<4))
def expected(initial,c=Case(),s=None,home=None):
 s=S if s is None else s;home=STACK+c.phase if home is None else home;after=initial.copy();first_effect(after,c,s);p=home-120
 fields={(0,2):17,(2,2):7,(4,1):108,(6,2):0x5103,(8,4):0x200005,(12,4):0,(16,2):40,(18,2):20,(20,4):0,(24,4):0,(28,1):78,(29,1):84,(30,1):123,(31,1):255,(32,1):164,(33,1):161,(34,1):200,(35,1):155,(36,1):100,(37,1):255,(38,2):30,(40,2):8,(42,2):30,(44,4):read(after,s['D_800A0134']),(48,4):read(after,s['D_800A0138']),(52,4):read(after,s['D_800A013C']),(56,4):read(initial,c.actor+0x14),(60,4):add32(add32(c.y,70.0),35.0),(64,4):read(initial,c.actor+0x1C),(68,2):0,(70,2):u32(-20),(72,2):255,(74,2):30,(76,4):0x41700000,(80,4):0x421C0000,(84,4):read(after,s['D_800A0140']),(88,4):read(after,s['D_800A0144']),(92,4):0x40040E07,(96,1):16,(97,1):255,(98,1):8,(99,1):6,(100,1):1,(104,4):read(after,s['D_800A0148'])}
 put(after,MARK+4,0x2468ACE0);return p,fields,after
class Oracle(Base):
 def __init__(self,words,initial,c=Case(),entry=ENTRY,extra=None,s=None):
  self.c=c;self.s=S if s is None else s;self.observations=[]
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=extra,arguments=(c.actor,))
 def record_call(self,target):
  counts={ENTRY:1,self.s['func_15136C3C']:8,self.s['func_15153634']:4};assert target in counts,hex(target)
  args=tuple(map(u32,self.arguments(counts[target])));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.s['func_15153634']:
   p=args[0];self.observations.append((bytes(self.memory[p+i]for i in range(108)),args))
 def hook(self,target):
  if target==self.s['func_15136C3C']:first_effect(self.memory,self.c,self.s)
  else:assert target==self.s['func_15153634'];put(self.memory,MARK+4,0x2468ACE0)
  if self.c.mutation:
   for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5B61234
def streams():return {label:bound_blob(*payload(o/path,'func_150BFFE0'),S)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/generated_EC420.c.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.trace,m.events,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
def final_state(m):return(m.memory,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def check(m,initial,c,s=None,home=None):
 s=S if s is None else s;p,fields,after=expected(initial,c,s,home);assert len(m.observations)==1
 packet,args=m.observations[0]
 for (at,n),v in fields.items():assert int.from_bytes(packet[at:at+n],'big')==v&((1<<(8*n))-1),(at,n,v,packet[at:at+n])
 assert args==(p,255,255,1);assert m.calls[-2:]==[(s['func_15136C3C'],(c.actor,0,0,1,0,0,255,1)),(s['func_15153634'],args)]
 for at in (5,101,102,103):assert packet[at]==initial[p+at],('Padding overwritten',at)
 assert public(m.memory)==public(after)
def main():
 programs=streams();visits=set();count=0;different_traces=0
 for c in cases():
  initial=fixture(c);models=[Oracle(ws,initial,c).run()for ws in programs.values()]
  assert state(models[1])==state(models[2]);assert final_state(models[0])==final_state(models[1])==final_state(models[2])
  for m in models:check(m,initial,c)
  different_traces+=models[0].trace!=models[2].trace;visits.update(models[2].visits);count+=1
 q=dict(cases_per_stream=count,streams=list(programs),raw_C_packet_public_effects_and_final_private_state_equal=True,normalized_retail_full_state_and_trace_equal=True,raw_trace_differences_observed=different_traces,all_initialized_fields_and_padding_checked=True,unexecuted_target_words=[i for i in range(127)if ENTRY+4*i not in visits],source_installed=checkpoint.installed(),matching_credit=0,limits='Complete target; effect helper and descriptor consumer are bounded providers. Raw memory access order is deliberately not claimed retail-exact. No consumer-internal, hardware or gameplay acceptance.')
 assert not q['unexecuted_target_words'];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs=streams();count=0;raw_differences=0
 for c in (Case(),Case(y=0x4C000000,phase=8,mutation=1),Case(y=0xC28C0000,actor=STACK+128)):
  initial=fixture(c);complete=Oracle(programs['retail'],initial,c).run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs.values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    states.append(state(m))
   assert states[1]==states[2],cut;raw_differences+=states[0]!=states[2];count+=1
 q=dict(normalized_retail_full_memory_GPR_FPR_HI_LO_trace_calls_prefix_pairs=count,raw_private_prefix_differences=raw_differences,actual_dispatched_access_cuts=True,source_installed=checkpoint.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>4I',rom,WINDOW-0x15000000+0x2D4B0);count=0
 for c in list(cases())[::4]:
  initial=fixture(c);states=[]
  for ws in streams().values():
   m=Oracle(words,initial,c,entry=WINDOW,extra=dict(zip(range(ENTRY,ENTRY+508,4),ws)));m.r[16]=c.actor;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary missing')
   check(m,initial,c);assert m.r[2]==0 and m.calls[0]==(ENTRY,(c.actor,));states.append(final_state(m))
  assert states[0]==states[1]==states[2];count+=1
 q=dict(real_caller_window_words=4,cases_per_stream=count,actor_pointer_and_discarded_return_verified=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Actual JAL/delay actor move and branch/delay V0=0 window; complete dispatcher not executed.');(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
