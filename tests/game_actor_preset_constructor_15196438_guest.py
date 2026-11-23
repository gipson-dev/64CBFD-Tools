"""Independent preset packet reference and typed o32 helper providers."""
from dataclasses import dataclass,replace
from pathlib import Path
import json,random,struct,sys
from tools.experiments import game_actor_preset_constructor_15196438_match as p
r=p.ROOT;o=p.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};ENTRY=0x15196438;OWNER=0x30000;MATRIX=0x40000;CREATED=0x50000;PAYLOAD=0x60000;ALTERNATE=0x61000;MARK=0x70000
TRANSFORM=0x15143134;ALLOCATE=0x15147A80;COPY=0x10022EC0;AUDIO=0x10010F30;VOICE=0x10010BE8
SOUND=(0x15198C60,);SCALE=(0x151979F8,0x15197A0C,0x15197A68);SETUP=(0x151993E4,)
u32=lambda n:n&0xffffffff
s32=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
s8=lambda n:((n&255)^128)-128
def blob(m,p,n):return bytes(m[p+i]for i in range(n))
def store(m,p,data):m.update({p+i:b for i,b in enumerate(data)})
@dataclass(frozen=True)
class Case:
 seed:int=0
 null:int=0
 matrix:int=1
 preset:int=0
 channel:int=255
 context:int=0
 success:int=1
 sound:int=-1
 scale:int=0
 setup:int=-1
 matrix_index:int=3
 sound_return:int=0x12348001
 scale_bits:int=0x3FA8F5C3
 mutations:int=0
 real:int=0
 phase:int=0
def cases():
 rng=random.Random(0x15196438)
 for seed in range(512):
  yield Case(seed=seed,null=int(seed%47==0),matrix=int(seed%41!=0),preset=rng.randrange(7),channel=rng.choice((0,1,255,256,-1,0x123480FF,-0x80000000)),context=rng.choice((0,1,-1,0x12348001)),success=int(seed%5!=0),sound=rng.choice((-1,0)),scale=rng.choice((-1,0,1,2)),setup=rng.choice((-1,0)),matrix_index=rng.choice((0,1,3,255)),sound_return=rng.choice((0,-1,0x12348001,0x10000)),scale_bits=rng.choice((0,0x80000000,0x3FA8F5C3,0x412E6666,0x7F7FFFFF,1)),mutations=rng.randrange(16),phase=8*(seed&1))
 for i in range(7):
  for mutations in(0,1,2,4,8,15):yield Case(seed=600+i,preset=i,real=1,mutations=mutations,channel=0xABCD80FF,context=-1)
def args(c):return tuple(map(u32,(0 if c.null else OWNER,c.preset,c.channel,c.context)))
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,4096)}
 for base,n in((OWNER,512),(MATRIX,0x4100),(CREATED,0xA0),(PAYLOAD,0x90),(ALTERNATE,0x90),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(n)})
 table=(r/'conker/conker.us.bin').read_bytes()[0x24D260:0x24D500];assert len(table)==7*0x60;store(m,S['D_800A87A0'],table)
 for name,values in(('D_8008F890',SOUND),('D_8008F870',SCALE),('D_8008F87C',SETUP)):
  for i,v in enumerate(values):put(m,S[name]+4*i,v)
 put(m,OWNER+0x1D4,MATRIX if c.matrix else 0);m[OWNER+0x3B]=(0x80+c.seed*7)&255;put(m,CREATED+0x98,PAYLOAD);put(m,ALTERNATE,OWNER)
 m[S['D_80041FD9']]=c.seed&255
 if not c.real:
  at=S['D_800A87A0']+c.preset*96
  for i in range(96):m[at+i]=(i*31+c.seed*11+0x69)&255
  for i,v in((0x3F,c.sound),(0x30,c.scale),(0x3C,c.setup),(0x14,c.matrix_index)):m[at+i]=v&255
  for k,off in enumerate((4,8,0x18,0x1C,0x20,0x24,0x28,0x2C,0x34,0x38,0x48,0x50,0x58)):put(m,at+off,(0,0x3F800000,0x80000000,0x7F7FFFFF,1)[(c.seed+k)%5])
 return m
def output_bits(c,step):return tuple((0x3F000000+((c.seed*13+step*17+k*19)&0x7FFF))for k in range(3))
def service(m,c,target,a,step,home):
 if target in SOUND:
  if c.mutations&1:put(m,OWNER+0x1D4,MATRIX+64);m[OWNER+0x3B]^=0x55
  if c.mutations&16:put(m,home+8,0xABCDFE80)
  return u32(c.sound_return),None
 if target==TRANSFORM:
  assert len(a)==3
  for k,v in enumerate(output_bits(c,step)):put(m,a[1]+4*k,v)
  if c.mutations&2:put(m,OWNER+0x1D4,MATRIX+128)
  if c.mutations&32:put(m,home+8,0x12345681)
  return 0xA5A50001,None
 if target==ALLOCATE:
  assert len(a)==11 and a[1:9]==(0x90,0x24,2,2,2,0,0,0)and a[9]==read(m,home+8)&255 and a[10]==u32(c.context)
  destination=home-172 if c.mutations&64 else home+8 if c.mutations&128 else PAYLOAD
  put(m,MARK,0x13579BDF);put(m,CREATED+0x98,destination);return CREATED if c.success else 0,None
 if target==COPY:
  assert a[2]==0x90;store(m,a[0],blob(m,a[1],a[2]));return a[0],None
 if target in SCALE:
  if c.mutations&4:m[PAYLOAD+0x60]=255
  if c.mutations&8:put(m,CREATED+0x98,ALTERNATE)
  return 0xA5A50002,c.scale_bits
 assert target in SETUP,hex(target)
 put(m,MARK+4,CREATED);return 0xA5A50003,None
FIELD_COPIES=((0x3C,0x60,1),(0x3D,0x61,1),(0x3E,0x62,1),(4,0x40,4),(8,0x48,4),(0xC,0x51,1),(0x14,5,1),(0x18,8,12),(0x24,0x14,12),(0x54,0x80,1),(0x3F,0x63,1),(0x30,7,1),(0x31,0x52,1),(0x32,0x53,1),(0x33,0x54,1),(0x47,0x6A,1),(0x4C,0x74,1),(0x34,0x58,4),(0x38,0x5C,4),(0x48,0x6C,4),(0x50,0x78,4),(0x58,0x84,4),(0x40,0x64,1),(0x41,0x65,1),(0x42,0x68,1),(0x46,0x69,1),(0x5C,0x8C,4))
def reference(initial,c,home=None):
 m=initial.copy();home=STACK+c.phase if home is None else home;packet=home-172;request=home-28;calls=[];observations=[];step=0
 put(m,home+8,c.channel);put(m,home+12,c.context)
 if c.null or not read(m,OWNER+0x1D4):return m,calls,0,observations
 put(m,packet,OWNER);m[packet+4]=m[OWNER+0x3B];m[packet+6]=2;table=S['D_800A87A0']+c.preset*96
 for src,dst,n in FIELD_COPIES:store(m,packet+dst,blob(m,table+src,n))
 for off in(0x3C,0x4C,0x70,0x7C,0x88):put(m,packet+off,0)
 m[packet+0x50]=0;put(m,request+0xC,read(m,table,2),2);put(m,request+0xE,read(m,table+0x44,2),2);m[request+0x15]=m[table+0x13]
 def call(target,a):
  nonlocal step
  a=tuple(map(u32,a));calls.append((target,a))
  if target==TRANSFORM:observations.append(('point',blob(m,a[0],12)))
  if target==ALLOCATE:observations.append(('request',blob(m,a[0],28)))
  if target==COPY:observations.append(('packet',blob(m,a[1],0x90)))
  result=service(m,c,target,a,step,home)
  if target==TRANSFORM:step+=1
  return result
 selector=s8(m[packet+0x63]);value=call(read(m,S['D_8008F890']+selector*4),())[0]if selector!=-1 else 0;put(m,packet+0x66,value,2)
 matrix=u32(read(m,OWNER+0x1D4)+m[packet+5]*64)
 call(TRANSFORM,(packet+8,packet+0x20,matrix));call(TRANSFORM,(packet+0x14,packet+0x2C,matrix));store(m,request,blob(m,packet+0x20,12));put(m,request+0x10,3)
 created=call(ALLOCATE,(request,0x90,0x24,2,2,2,0,0,0,read(m,home+8)&255,c.context))[0]
 if created:
  destination=read(m,created+0x98);call(COPY,(destination,packet,0x90));selector=s8(m[destination+7])
  value=call(read(m,S['D_8008F870']+selector*4),(created,))[1]if selector!=-1 else 0;put(m,destination+0x38,value)
  selector=s8(m[packet+0x60])
  if selector!=-1:call(read(m,S['D_8008F87C']+selector*4),(created,))
 return m,calls,u32(created),observations
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,connected=None,arguments=None):
  self.c=c;self.step=0;self.full_calls=[];self.observations=[];self.guest_home=STACK+c.phase;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=args(c)if arguments is None else arguments)
 def record_call(self,target):
  n=4 if target==ENTRY else 7 if target==VOICE else 5 if target==AUDIO else 0 if target in SOUND else 3 if target in(TRANSFORM,COPY)else 11 if target==ALLOCATE else 1 if target in SCALE+SETUP else None;assert n is not None,hex(target);actual=tuple(map(u32,self.arguments(n)));self.full_calls.append((target,actual));a=list(actual)
  if target==ENTRY:self.guest_home=self.r[29]
  if target==AUDIO:assert actual==(0x1AA,0x7FFF,0x40,0,0)
  if target==VOICE:assert actual==(0,0x1AA,0x7FFF,0x40,0,0,self.memory[S['D_80041FD9']])
  if target==ALLOCATE:a[9]&=255
  a=tuple(a);self.calls.append((target,a));self.events.append(('CALL',target,actual))
  if target==TRANSFORM:self.observations.append(('point',blob(self.memory,a[0],12)))
  if target==ALLOCATE:self.observations.append(('request',blob(self.memory,a[0],28)))
  if target==COPY:self.observations.append(('packet',blob(self.memory,a[1],0x90)))
 def hook(self,target):
  a=self.calls[-1][1];value,fp=service(self.memory,self.c,SOUND[0]if target in(AUDIO,VOICE)else target,()if target in(AUDIO,VOICE)else a,self.step,self.guest_home)
  if target==VOICE:value&=65535
  if target==TRANSFORM:self.step+=1
  for k in range(4):put(self.memory,self.r[29]+4*k,0xB5000000+k)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+k for k in range(20)];self.r[2]=value
  if fp is not None:self.f[0]=fp
  self.hi,self.lo=0xA5000010,0xA5000011
def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-248<=a<STACK+c.phase}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.observations,m.full_calls,getattr(m,'dispatched_word',None))
def streams():
 from tools.tests.game_actor_preset_constructor_15196438_normalizer import normalize
 raw=payload(o/'selected-final/candidate.o','func_15196438');programs={k:bound_blob(*v,S)for k,v in dict(raw=raw,normalized=normalize(*raw),retail=payload(o/'original-target.o','func_15196438')).items()}
 padded=o/'qualified-owner/generated_1C2C60.c.o'
 if padded.exists():programs['padded']=bound_blob(*payload(padded,'func_15196438'),S)
 assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;return programs
def main():
 programs=streams();assert programs['normalized']==programs['retail'];assert struct.pack('>196I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x1C38E8:0x1C3BF8];count=0;extended=0;visits=set()
 for c in cases():
  initial=fixture(c);expected,calls,value,observations=reference(initial,c);models=[]
  for label,words in programs.items():
   m=Oracle(words,initial,c);m.run();assert public(m.memory,c)==public(expected,c),(label,c,'public');assert m.calls==calls,(label,c,'calls',m.calls,calls);assert m.r[2]==value,(label,c,'result');assert m.observations==observations,(label,c,'packet/request/vector bytes');models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);a,b=models[:2];different={p for p in a.memory.keys()|b.memory.keys()if a.memory.get(p)!=b.memory.get(p)};allowed={STACK+c.phase-248+0x24+k for k in range(3)};assert different<=allowed,(c,different);extended+=bool(different);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=list(programs),public_memory_return_typed_calls_and_full_packet_observations_equal=True,raw_private_difference_limited_to_outgoing_byte_argument_high_bytes=extended,normalized_complete_state_equal=True,unexecuted_retail_words=[i for i in range(196)if ENTRY+4*i not in visits],scope='Raw call9 is interpreted with the existing allocator unsigned-byte formal. Its complete outgoing o32 word is restored by the explicit low-byte load guard. Original private packet/request gaps and all 248 frame bytes are literal normalized guest evidence, not portable native initialized fields.',source_installed=p.installed(),matching_credit=0);assert q['unexecuted_retail_words']==[8];(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def alias_cases():
 for phase in(0,8):
  for mutation in(16,32,64,128):yield Case(seed=1100+mutation,sound=0,scale=1,setup=0,channel=0xABCD80FF,mutations=mutation,phase=phase)
def aliases():
 count=0
 for c in alias_cases():
  initial=fixture(c);expected,calls,value,observations=reference(initial,c);models=[]
  for label,words in streams().items():
   m=Oracle(words,initial,c);m.run();assert public(m.memory,c)==public(expected,c)and m.calls==calls and m.r[2]==value and m.observations==observations,(label,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);different={a for a in models[0].memory.keys()|models[1].memory.keys()if models[0].memory.get(a)!=models[1].memory.get(a)};assert different<={STACK+c.phase-248+0x24+k for k in range(3)}
  if c.mutations&48:assert next(a[9]for target,a in models[1].full_calls if target==ALLOCATE)==(0x80 if c.mutations&16 else 0x81)
  count+=1
 q=dict(guest_only_home_and_packet_alias_cases=count,post_provider_current_channel_byte_reload=True,packet_self_copy_and_incoming_home_output_aliases=True,raw_typed_public_semantics_equal=True,normalized_complete_state_equal=True,source_installed=p.installed(),matching_credit=0);(o/'aliases.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def faults():
 programs={k:v for k,v in streams().items()if k!='raw'};count=0
 examples=[Case(null=1),Case(matrix=0),Case(sound=0,scale=1,setup=0,mutations=15,channel=0xABCDFEFF),Case(sound=0,success=0),Case(scale=-1,setup=-1)]+list(alias_cases())
 for c in examples:
  initial=fixture(c);m=Oracle(programs['retail'],initial,c);m.run()
  for cut in range(m.all_accesses):
   states=[]
   for words in programs.values():
    n=Oracle(words,initial,c);n.cut=cut
    try:n.run()
    except AccessBoundary:pass
    else:raise AssertionError('Own-access boundary did not fire')
    states.append(state(n))
   assert all(s==states[0]for s in states[1:]);count+=1
 q=dict(full_state_own_access_prefix_sets=count,streams=list(programs),dispatched_word_included=True,private_gaps_and_byte_parameter_home_aliases=True,source_installed=p.installed(),matching_credit=0);(o/'faults.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();count=0;wrappers=[]
 for entry,preset in((0x1506FCC8,6),(0x1506FCFC,5)):
  offset=entry-0x15000000+0x2D4B0;words=list(struct.unpack_from('>13I',rom,offset));frame=(-words[0])&65535;assert frame==24 and words[2]==0xAFA40018;wrappers.append(dict(VA=hex(entry),ROM=hex(offset),words=13,preset=preset))
  for original in list(cases())[::16]:
   c=replace(original,preset=preset,channel=255,context=0);initial=fixture(c);put(initial,S['D_800D154C'],0 if c.null else OWNER);child_home=STACK+c.phase-frame;expected,calls,value,observations=reference(initial,c,child_home);put(expected,STACK+c.phase,0xABC00001);models=[]
   for label,child in streams().items():
    m=Oracle(words,initial,c,entry=entry,connected=dict(zip(range(ENTRY,ENTRY+784,4),child)),arguments=(0xABC00001,0xABC00002,0xABC00003,0xABC00004));m.run();assert{a:b for a,b in m.memory.items()if not child_home-248<=a<STACK+c.phase}=={a:b for a,b in expected.items()if not child_home-248<=a<STACK+c.phase};assert m.calls==[(ENTRY,args(c))]+calls and m.observations==observations;assert m.r[2]==value;models.append(m)
   assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 windows=[]
 for entry,preset in((0x150DBA18,1),(0x150DBC40,2)):
  offset=entry-0x15000000+0x2D4B0;words=list(struct.unpack_from('>3I',rom,offset));end=entry+12;windows.append(dict(VA=hex(entry),ROM=hex(offset),words=3,preset=preset))
  for original in list(cases())[::16]:
   c=replace(original,preset=preset,channel=original.channel&255,context=0);initial=fixture(c);expected,calls,value,observations=reference(initial,c);models=[]
   for label,child in streams().items():
    m=Oracle(words,initial,c,entry=entry,connected=dict(zip(range(ENTRY,ENTRY+784,4),child)),arguments=args(c));m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Original bounded parent window did not finish')
    assert public(m.memory,c)==public(expected,c)and m.calls==[(ENTRY,args(c))]+calls and m.observations==observations and m.r[2]==value;models.append(m)
   assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(original_full_wrappers=wrappers,original_parent_windows=windows,cases_per_stream=count,four_full_arguments_and_complete_child=True,source_installed=p.installed(),matching_credit=0,limits='Both complete 13-word callback wrappers and both 3-word call windows are original ROM. Full func_150DB9E0 is not executed.');(o/'caller-window.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def connected_sound():
 rom=(r/'conker/conker.us.bin').read_bytes();sound=list(struct.unpack_from('>12I',rom,0x1C6110));literal=bound_blob(*payload(o/'selected-final/candidate.o','func_15198C60'),S);assert literal==sound;count=0
 for original in list(cases())[::8]:
  c=replace(original,null=0,matrix=1,sound=0,real=0);initial=fixture(c);expected,calls,value,observations=reference(initial,c);expanded=[]
  for target,a in calls:
   expanded.append((target,a))
   if target in SOUND:expanded.append((AUDIO,(0x1AA,0x7FFF,0x40,0,0)))
  models=[]
  for label,words in streams().items():
   m=Oracle(words,initial,c,connected=dict(zip(range(SOUND[0],SOUND[0]+48,4),sound)));m.run();assert{a:b for a,b in m.memory.items()if not STACK+c.phase-280<=a<STACK+c.phase}=={a:b for a,b in expected.items()if not STACK+c.phase-280<=a<STACK+c.phase};assert m.calls==expanded and m.observations==observations and m.r[2]==value;models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(original_sound_wrapper_words=12,selected_C_sound_wrapper_words_and_bindings_fixed=True,real_five_argument_audio_submission=True,injected_guest_V0_words_then_low16_handle=True,cases_per_stream=count,source_installed=p.installed(),matching_credit=0,limits='Actual sound-wrapper instructions execute; the audio provider injects V0 to test low16 handling. High-word injections are guest probes; the corrected C audio API returns u16. No hardware claim.');(o/'connected-sound.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def connected_audio_chain():
 rom=(r/'conker/conker.us.bin').read_bytes();sound=list(struct.unpack_from('>12I',rom,0x1C6110));audio=list(struct.unpack_from('>22I',rom,0x10F30));audio_frame=(-audio[0])&65535;assert audio_frame==40;count=0
 code=dict(zip(range(SOUND[0],SOUND[0]+48,4),sound));code.update(zip(range(AUDIO,AUDIO+88,4),audio))
 for original in list(cases())[::8]:
  c=replace(original,null=0,matrix=1,sound=0,real=0);initial=fixture(c);expected,calls,value,observations=reference(initial,c);expanded=[]
  for target,a in calls:
   expanded.append((target,a))
   if target in SOUND:expanded.extend(((AUDIO,(0x1AA,0x7FFF,0x40,0,0)),(VOICE,(0,0x1AA,0x7FFF,0x40,0,0,initial[S['D_80041FD9']]))))
  models=[]
  for label,words in streams().items():
   m=Oracle(words,initial,c,connected=code);m.run();assert{a:b for a,b in m.memory.items()if not STACK+c.phase-320<=a<STACK+c.phase}=={a:b for a,b in expected.items()if not STACK+c.phase-320<=a<STACK+c.phase};assert m.calls==expanded and m.observations==observations and m.r[2]==value;models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(original_sound_words=12,original_Init_audio_wrapper_words=22,actual_three_level_chain=True,canonical_unsigned16_audio_handle=True,real_seven_argument_voice_request=True,cases_per_stream=count,source_installed=p.installed(),matching_credit=0,limits='Constructor, sound callback and Init forwarding wrapper execute original instructions. Voice allocator/hardware remains a bounded provider.');(o/'connected-audio-chain.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
