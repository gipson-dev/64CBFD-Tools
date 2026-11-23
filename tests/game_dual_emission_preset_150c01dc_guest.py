"""Both impact packets, raw C lifetimes and real indirect callback windows."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_dual_emission_preset_150c01dc_match as checkpoint
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
r,o=checkpoint.ROOT,checkpoint.OUT
ENTRY=0x150C01DC;BURST=0x15152190;FACTORY=0x15153634;ACTOR=0x30000;MARK=0x51000;TABLE=0x80089934
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
CONSTANTS=checkpoint.MANIFEST['constants']
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
  for phase,mutation,actor in itertools.product((0,8),(0,1),(ACTOR,STACK+128)):yield Case(y,actor,phase,mutation,i)
def arguments(c):return(c.actor,0x7FC01234^c.seed,0x80000000,0x7F800000,c.y,c.actor+0x114)
def fixture(c=Case(),s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for p,n in((ACTOR-32,0x240),(MARK,32)):m.update({p+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 for at,v in((0x38,0x3F800001^(c.seed<<8)),(0x3C,0x42C60000),(0x40,0x7FC01234^(c.seed<<8))):put(m,c.actor+at,v)
 m[c.actor+1]=(c.seed*17+129)&255;m[c.actor+12]=(c.seed*31+128)&255
 for name,value in CONSTANTS.items():put(m,s[name],value)
 return m
def first_effect(m,c,s):
 put(m,MARK,0x13579BDF)
 if c.mutation:
  put(m,c.actor+0x38,0xC1200000);put(m,c.actor+0x40,0x80000000);m[c.actor+1]^=0xFF;m[c.actor+12]^=0xFF
  for name,value in CONSTANTS.items():put(m,s[name],value^((c.seed+1)<<4))
def expected(initial,c=Case(),s=None,home=None):
 s=S if s is None else s;home=STACK+c.phase if home is None else home;after=initial.copy();first_effect(after,c,s);position=(read(initial,c.actor+0x38),add32(c.y,20.0),read(initial,c.actor+0x40))
 burst={(0,4):5,(4,4):4,(8,4):position[0],(12,4):position[1],(16,4):position[2],(20,2):0,(22,2):255,(24,2):u32(-64),(26,2):34,(28,4):0x41400000,(32,4):0x41000000,(36,4):read(initial,s['D_800A014C']),(40,4):read(initial,s['D_800A0150']),(44,2):30,(46,2):15,(48,4):read(initial,s['D_800A0154']),(52,4):read(initial,s['D_800A0158']),(56,4):read(initial,s['D_800A015C'])}
 emission={(0,2):5,(2,2):8,(4,1):108,(6,2):0x5103,(8,4):0x200005,(12,4):0,(16,2):30,(18,2):15,(20,4):0,(24,4):0,(28,1):78,(29,1):84,(30,1):123,(31,1):255,(32,1):164,(33,1):161,(34,1):200,(35,1):100,(36,1):155,(37,1):255,(38,2):14,(40,2):18,(42,2):14,(44,4):read(after,s['D_800A0164']),(48,4):0x435A0000,(52,4):read(after,s['D_800A0168']),(56,4):position[0],(60,4):position[1],(64,4):position[2],(68,2):0,(70,2):u32(-40),(72,2):255,(74,2):40,(76,4):0x41980000,(80,4):0x41000000,(84,4):read(after,s['D_800A0160']),(88,4):read(after,s['D_800A0160']),(92,4):0x840E07,(96,1):16,(97,1):255,(98,1):8,(99,1):6,(100,1):1,(104,4):read(after,s['D_800A016C'])}
 put(after,MARK+4,0x2468ACE0);a=(home-72,home-76,home-80,1,0,1,initial[c.actor+12],initial[c.actor+1]);b=(home-188,255,after[c.actor+12],after[c.actor+1]);return burst,emission,after,a,b
class Oracle(Base):
 def __init__(self,words,initial,c=Case(),entry=ENTRY,extra=None,s=None):
  self.c=c;self.s=S if s is None else s;self.observations=[]
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=extra,arguments=arguments(c))
 def record_call(self,target):
  counts={ENTRY:6,self.s['func_15152190']:8,self.s['func_15153634']:4};assert target in counts,hex(target)
  args=tuple(map(u32,self.arguments(counts[target])));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.s['func_15152190']:
   self.observations.append((bytes(self.memory[args[0]+i]for i in range(60)),args,read(self.memory,args[1]),read(self.memory,args[2])))
  elif target==self.s['func_15153634']:self.observations.append((bytes(self.memory[args[0]+i]for i in range(108)),args))
 def hook(self,target):
  if target==self.s['func_15152190']:first_effect(self.memory,self.c,self.s)
  else:assert target==self.s['func_15153634'];put(self.memory,MARK+4,0x2468ACE0)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5B61234
def streams():return{label:bound_blob(*payload(o/path,'func_150C01DC'),S)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/generated_EC420.c.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.trace,m.events,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
def final_state(m):return(m.memory,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def check(m,initial,c,s=None,home=None):
 s=S if s is None else s;home=STACK+c.phase if home is None else home;burst,emission,after,a,b=expected(initial,c,s,home);assert len(m.observations)==2
 for observed,fields in zip(m.observations,(burst,emission)):
  packet=observed[0]
  for(at,n),v in fields.items():assert int.from_bytes(packet[at:at+n],'big')==v&((1<<(8*n))-1),(at,n,v,packet[at:at+n])
 assert m.observations[0][1:]==(a,read(initial,s['D_800A0100']),read(initial,s['D_800A0104']));assert m.observations[1][1]==b
 assert m.calls[-2:]==[(s['func_15152190'],a),(s['func_15153634'],b)]
 for at in(5,101,102,103):assert m.observations[1][0][at]==initial[b[0]+at],('Padding overwritten',at)
 assert public(m.memory)==public(after)and m.r[2]==0
def main():
 programs=streams();visits=set();count=different_traces=0
 for c in cases():
  initial=fixture(c);models=[Oracle(ws,initial,c).run()for ws in programs.values()]
  assert state(models[1])==state(models[2]);assert final_state(models[0])==final_state(models[1])==final_state(models[2])
  for m in models:check(m,initial,c)
  different_traces+=models[0].trace!=models[2].trace;visits.update(models[2].visits);count+=1
 q=dict(cases_per_stream=count,streams=list(programs),raw_C_packet_public_effects_and_final_private_state_equal=True,normalized_retail_full_state_and_trace_equal=True,raw_trace_differences_observed=different_traces,all_initialized_fields_and_padding_checked=True,unexecuted_target_words=[i for i in range(185)if ENTRY+4*i not in visits],source_installed=checkpoint.installed(),matching_credit=0,limits='Complete target; both effect consumers are bounded providers. Raw access ordering is not retail exact. No consumer-internal, hardware or gameplay acceptance.');assert not q['unexecuted_target_words'];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs=streams();count=raw_differences=0
 for c in(Case(),Case(y=0x4C000000,phase=8,mutation=1),Case(y=0xC28C0000,actor=STACK+128)):
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
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();assert read(dict(enumerate(elf)),elf_slot_offset(elf,TABLE+52,4))==ENTRY
 rom=(r/'conker/conker.us.bin').read_bytes();count=0;reports=[]
 for entry,n,ends in((0x15132FDC,19,(0x15133024,0x15133028,0x151332C8)),(0x1513397C,17,(0x151339C0,))):
  words=struct.unpack_from('>'+str(n)+'I',rom,entry-0x15000000+0x2D4B0);visits=set()
  for c in list(cases())[::4]:
   initial=fixture(c);home=STACK+c.phase;put(initial,TABLE+52,ENTRY);initial[c.actor+0x73]=13;put(initial,c.actor+0x110,c.y)
   offset=0x374 if entry==0x15132FDC else 0x40
   for i,v in enumerate(arguments(c)[1:4]):put(initial,home+offset+4*i,v)
   models=[]
   for ws in streams().values():
    m=Oracle(words,initial,c,entry=entry,extra=dict(zip(range(ENTRY,ENTRY+740,4),ws)));m.r[16]=c.actor;m.r[4]=c.actor;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary missing')
    assert m.calls[0]==(ENTRY,arguments(c)),m.calls[0];check(m,initial,c);models.append(m);visits.update(p for p in m.visits if entry<=p<entry+4*n)
   assert final_state(models[0])==final_state(models[1])==final_state(models[2]);count+=1
  reports.append(dict(entry=hex(entry),words=n,visited_words=len(visits)))
 q=dict(real_indirect_caller_windows=reports,cases_per_stream=count,table_index=13,all_six_arguments_and_zero_result_verified=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Both actual JALR callback windows, including outgoing height/contact and callback return handling. Complete dispatch parents not executed.');(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
