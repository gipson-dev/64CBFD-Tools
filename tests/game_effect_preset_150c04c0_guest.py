"""Original preset packet, private machine state and real complete caller."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct
from tools.experiments import game_effect_preset_150c04c0_match as checkpoint
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=checkpoint.ROOT,checkpoint.OUT
ENTRY=0x150C04C0;FACTORY=0x15150400;CALLER=0x15074C00;PREPARE=0x1504715C;POSITION=0x30000;MARK=0x51000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
CONSTANTS={0x800A0108:0x3F800000,0x800A0170:0x3F266667,0x800A0174:0xBFA3D70B,0x800A0178:0x3EAC0832,0x800A017C:0x3F19999A,0x800A0180:0x3EE66667,0x800A0184:0x41889DB3,0x800A0188:0x3F408313,0x800A018C:0x3E50E561,0x800A0190:0x3E27EF9E}
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 enabled:int=0
 channel:int=255
 variant:int=22
 state:int=0x40000
 context:int=0xABCDEF01
 phase:int=0
 seed:int=0
 position:int=POSITION
 mutation:int=0
def fixture(c=Case(),s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2304)}
 for base,n in ((POSITION-32,128),(0x40000,0x300),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 for i,v in enumerate((0x3F800001,0x80000000,0x7FC01234)):put(m,c.position+4*i,v^(c.seed<<8))
 for address,value in CONSTANTS.items():put(m,s[f'D_{address:08X}'],value)
 return m
def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def expected(initial,c=Case(),s=None,home=None):
 s=S if s is None else s;home=STACK+c.phase if home is None else home;sp=home-152;base=sp+52
 fields={0:9,4:4,**{8+4*i:read(initial,c.position+4*i)for i in range(3)},20:0x40800000,24:0x40E00000,28:read(initial,s['D_800A0174']),32:read(initial,s['D_800A0178']),40:read(initial,s['D_800A017C']),44:read(initial,s['D_800A0180']),48:read(initial,s['D_800A0184']),52:u32(c.state),56:read(initial,s['D_800A0188']),60:read(initial,s['D_800A018C']),64:read(initial,s['D_800A0190']),68:0x41200000,72:sp+40,76:sp+36,80:1,84:0x429C0000,92:4,96:sp+32}
 values={(at,4):v for at,v in fields.items()};values.update({(36,2):80,(38,2):60,(88,1):int(bool(c.enabled&255)),(89,1):14})
 return base,sp+44,values,(u32(c.variant),read(initial,s['D_800A0108']),read(initial,s['D_800A0170']))
class Oracle(Base):
 def __init__(self,words,initial,c=Case(),entry=ENTRY,extra=None,s=None):
  self.c=c;self.s=S if s is None else s;self.observations=[];self.caller=False
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=extra,arguments=tuple(map(u32,(c.position,c.state,c.variant,c.enabled,c.channel,c.context))))
 def record_call(self,target):
  counts={ENTRY:6,self.s.get('func_15150400',FACTORY):4,PREPARE:2};assert target in counts,hex(target)
  args=tuple(map(u32,self.arguments(counts[target])));self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.s.get('func_15150400',FACTORY):
   p,a,ch,context=args
   packet=bytes(self.memory[p+i]for i in range(100));angles=bytes(self.memory[a+i]for i in range(8));locals_=tuple(read(self.memory,read(self.memory,p+at))for at in (72,76,96))
   self.observations.append((packet,angles,locals_,args))
 def hook(self,target):
  if target==PREPARE:
   p,_=self.calls[-1][1]
   for i in range(36):self.memory[p+i]=(i*9+self.c.seed)&255
  else:
   assert target==self.s.get('func_15150400',FACTORY),hex(target)
   put(self.memory,MARK,self.calls[-1][1][2]);put(self.memory,MARK+4,self.calls[-1][1][3])
  if self.c.mutation:
   for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
   for i in range(4):put(self.memory,self.target_home+4*i,0xCAFE0010+i)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5B61234
def streams():return {label:bound_blob(*payload(o/path,'func_150C04C0'),S)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/generated_EC420.c.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.trace,m.events,m.calls,m.observations,m.r,m.f,m.hi,m.lo)
def values():return [0,1,2,127,128,255,256,257,65535,0x80000000,0xFFFFFFFF]+[u32(i*0x01010101^0xCAFE0000)for i in range(21)]
def cases():
 for i,enabled in enumerate(values()):
  for phase,mutation in itertools.product((0,8),(0,1)):
   yield Case(enabled=enabled,channel=values()[-i-1],variant=u32(enabled^0xABCD8001),state=(0,0x40000,0x80001234,0xFFFFFFFF)[i%4],context=u32(~enabled),phase=phase,seed=i,mutation=mutation)
def check(m,initial,c,s=None,home=None):
 s=S if s is None else s;p,a,fields,locals_=expected(initial,c,s,home);assert len(m.observations)==1
 packet,angles,gotlocals,args=m.observations[0]
 for (at,n),v in fields.items():assert int.from_bytes(packet[at:at+n],'big')==u32(v)&((1<<(8*n))-1),(at,n,v,packet[at:at+n])
 assert packet[90:92]==bytes(initial[p+i]for i in (90,91)),'Uninitialized padding must remain untouched'
 assert angles==struct.pack('>4h',0,255,-50,35)and gotlocals==locals_
 assert args==(p,a,c.channel&255,u32(c.context));assert read(m.memory,MARK)==c.channel&255 and read(m.memory,MARK+4)==u32(c.context)
def main():
 programs=streams();visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[Oracle(ws,initial,c).run()for ws in programs.values()]
  assert state(models[0])==state(models[1])==state(models[2]);check(models[0],initial,c);visits.update(models[0].visits);count+=1
 aliases=0
 for at in (-152+52,-152+36,24,64):
  c=Case(position=STACK+at,enabled=0x100,phase=0);initial=fixture(c)
  models=[Oracle(ws,initial,c).run()for ws in programs.values()];assert state(models[0])==state(models[1])==state(models[2]);aliases+=1
 q=dict(cases_per_stream=count,guest_alias_cases_per_stream=aliases,streams=list(programs),all_named_fields_and_local_pointer_lifetimes_checked=True,padding_preserved=True,full_private_machine_state_three_way_equal=True,unexecuted_target_words=[i for i in range(98)if ENTRY+4*i not in visits],source_installed=checkpoint.installed(),matching_credit=0,limits='Complete target through the original typed consumer boundary. Consumer internals, hardware and gameplay are not executed.')
 assert not q['unexecuted_target_words'];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 count=0;programs=streams()
 for c in (Case(),Case(enabled=1,phase=8,mutation=1),Case(enabled=0x100,position=STACK-100)):
  initial=fixture(c);complete=Oracle(programs['retail'],initial,c).run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs.values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Memory cut did not fire')
    states.append(state(m))
   assert states[0]==states[1]==states[2],cut;count+=1
 q=dict(full_memory_GPR_FPR_HI_LO_trace_calls_prefix_triples=count,actual_dispatched_access_cuts=True,source_installed=checkpoint.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>32I',rom,0x15074C00-0x15000000+0x2D4B0);count=0
 for selector,phase in itertools.product((0,4,5,0x85,0xFF),(0,8)):
  c=Case(phase=phase,seed=selector);initial=fixture(c);initial[0x40239]=selector
  for at,v in zip((0x800CC2C0,0x800CC2C4,0x800CC2C8),(0x3F800000,0xBF800000,0x42A00000)):put(initial,at,v)
  states=[]
  for ws in streams().values():
   m=Oracle(words,initial,c,entry=CALLER,extra=dict(zip(range(ENTRY,ENTRY+392,4),ws)));m.r[5]=0x40000;m.before=m.r[:];m.run()
   if selector&127==5:
    assert [t for t,_ in m.calls]==[PREPARE,ENTRY,FACTORY]
    a=m.calls[1][1];assert a==(STACK+phase-12,STACK+phase-48,22,1,255,0),a
    assert m.observations[0][3][2:]==(255,0)and m.observations[0][2][0]==22
   else:assert not m.calls and not m.observations
   states.append(state(m))
  assert states[0]==states[1]==states[2];count+=1
 q=dict(original_complete_caller_words=32,cases_per_stream=count,selector_gate_and_six_word_interface=True,source_installed=checkpoint.installed(),matching_credit=0,limits='Original complete func_15074C00 plus new target. State preparation and packet consumer are bounded providers; no complete gameplay claim.')
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()))
