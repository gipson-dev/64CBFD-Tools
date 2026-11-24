"""Independent actor update, provider mutations, aliases and actual caller window."""
from dataclasses import dataclass,replace
import json,struct
from tools.experiments import game_actor_state_motion_150b12fc_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x150b12fc;OWNER=0x30000;TABLE=0x50000;ROWS=0x80000;MARK=0x90000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n};u32=lambda v:v&0xffffffff
def signed16(v):return((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 seed:int=0
 old_angle:int=0xffff
 current_angle:int=0x8000
 height:int=0xffff
 velocity:int=0x3f800000
 smooth:int=0
 factor:int=0x3d4ccccd
 facing:int=0xc000
 index:int=255
 result:int=0
 mutation:int=0
 alias:int=0
 phase:int=0
def cases():
 angles=(0,1,0x7fff,0x8000,0xffff,0x4000,0xc000,65534)
 for seed in range(8):
  for mutation in(0,1,2,4,8,16,32,63):
   for result in(0,1,-1):
    for alias in range(5):yield Case(seed,angles[seed],angles[-1-seed],angles[-1-seed],(0,0x80000000,0x40c00000,0xc0c00000,0x41200000,0xc1200000,0x3f800000,0xbf800000)[seed],bits((seed-4)*0.125),(0x3d4ccccd,0,0x3f800000,0xbf000000)[seed%4],angles[-1-seed],(0,1,127,255)[seed%4],result,mutation,alias,8*(seed&1))
 for old,current in((0,0),(0x8000,0x7fff),(0x7fff,0x8000),(0xffff,0)):
  for velocity in(0,0x80000000,0x40bfffff,0x40c00000,0x40c00001,0xc0bfffff,0xc0c00000,0xc0c00001,0x7f800000,0xff800000,0x7fc12345,0x7f800001):
   for result in(0,1):yield Case(old_angle=old,current_angle=current,velocity=velocity,result=result,mutation=2)
def table(c):return OWNER+0x180 if c.alias==3 else TABLE
def row(c,s=None):
 s=S if s is None else s
 return OWNER+0x74 if c.alias==1 else OWNER+0x7e if c.alias==2 else s['D_8009F8BC']-2 if c.alias==4 else ROWS+4*c.index
def banks(s=None):
 s=S if s is None else s;return((OWNER,704),(TABLE,1024),(ROWS,1024),(MARK,32),(s['D_8009F8BC'],8),(s['D_800D2104'],4))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 for base,n in banks(s):m.update({base+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,n+16)})
 if c.alias==3:m.update({table(c)+i:(i*29+c.seed*11+0x51)&255 for i in range(-16,1040)})
 for i in range(256):put(m,table(c)+4*i,ROWS+4*i)
 put(m,table(c)+4*c.index,row(c,s));put(m,s['D_800D2104'],table(c));put(m,s['D_8009F8BC'],0xbf333333);put(m,s['D_8009F8C0'],c.factor)
 put(m,OWNER,7);put(m,OWNER+0x76,c.old_angle,2);put(m,OWNER+0x7a,c.facing,2);m[OWNER+0x13f]=c.index;put(m,OWNER+0xc4,c.velocity);put(m,OWNER+0x148,c.smooth);put(m,OWNER+0x40,bits(19.5))
 if c.alias in(0,3):put(m,row(c,s)+2,c.height,2)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
def observation(m,s):return(tuple(read(m,OWNER+at)for at in(0x40,0xc4,0x148))+(read(m,OWNER+0x76,2),read(m,OWNER+0x7a,2),m[OWNER+0x80],m[OWNER+0x13f],read(m,s['D_8009F8BC']),read(m,s['D_8009F8C0']),read(m,s['D_800D2104'])))
class Providers:
 def __init__(self,m,c,s=None):self.m=m;self.c=c;self.s=S if s is None else s;self.calls=[];self.observed=[]
 def invoke(self,name,a):
  m,c,s=self.m,self.c,self.s;a=tuple(map(u32,a));self.calls.append((s[name],a));self.observed.append(observation(m,s));number=len(self.calls);put(m,MARK,number)
  if name=='func_15058EA4':
   if c.mutation&1:put(m,OWNER+0x76,c.current_angle^0x8000,2);put(m,OWNER+0xc4,bits(-4.0));put(m,OWNER+0x148,bits(2.0));put(m,s['D_8009F8C0'],bits(0.5))
   if c.mutation&4:put(m,s['D_800D2104'],0);m[OWNER+0x13f]^=0x55;put(m,row(c,s)+2,0x8000,2)
   answer=0xdeadbeef
  elif name=='func_15056B08':
   if c.mutation&2:put(m,OWNER+0x76,c.current_angle,2);put(m,OWNER+0xc4,c.velocity);put(m,OWNER+0x148,c.smooth);put(m,OWNER+0x7a,c.facing,2)
   if c.mutation&8:put(m,s['D_800D2104'],table(c));put(m,s['D_8009F8C0'],c.factor)
   answer=0xdeadbeef
  elif name=='func_15059140':
   if c.mutation&16:put(m,OWNER,0);put(m,OWNER+0xc4,bits(-2.0));put(m,OWNER+0x148,bits(3.0));put(m,OWNER+0x40,bits(4.0))
   answer=0xdeadbeef
  elif name=='func_150535F4':
   if c.mutation&32:m[OWNER+0x80]^=0x80;put(m,OWNER+0xc4,bits(7.0));put(m,s['D_8009F8C0'],bits(0.25))
   answer=c.result
  else:assert name=='func_1502178C';m[OWNER+0x80]=(m[OWNER+0x80]+1)&255;answer=0xdeadbeef
  return u32(answer)
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();service=Providers(m,c,s);old=signed16(read(m,OWNER+0x76,2));m[OWNER+0x80]=10;entry=read(m,read(m,s['D_800D2104'])+4*m[OWNER+0x13f]);height=bits(float(signed16(read(m,entry+2,2))))
 service.invoke('func_15058EA4',(OWNER,height,0x3f800000,height,read(m,s['D_8009F8BC']),bits(12.0),bits(-16.0)));service.invoke('func_15056B08',(OWNER,))
 change=signed16((old-read(m,OWNER+0x76,2))*6);previous=read(m,OWNER+0xc4);correction=bits(floating(bits(float(change)))*floating(0x3b800000));correction=bits(floating(correction)-floating(previous))
 if floating(correction)>6.0:correction=bits(6.0)
 elif floating(correction)<-6.0:correction=bits(-6.0)
 smooth=read(m,OWNER+0x148);difference=bits(floating(correction)-floating(smooth));scaled=bits(floating(difference)*floating(read(m,s['D_8009F8C0'])));put(m,OWNER+0x148,bits(floating(smooth)+floating(scaled)));put(m,OWNER+0xc4,bits(floating(previous)+floating(read(m,OWNER+0x148))));facing=signed16(read(m,OWNER+0x7a,2)+0x4000);put(m,OWNER+0x40,bits(floating(bits(float(facing)))*floating(0x3bb40000)))
 service.invoke('func_15059140',(OWNER,));answer=service.invoke('func_150535F4',(OWNER,))
 if answer==0:service.invoke('func_1502178C',(OWNER,0,0xffffffff))
 return m,service
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(OWNER,));self.fp_before=self.f[:];self.entry_sp=self.r[29];self.providers=Providers(self.memory,c,self.s)
 def record_call(self,t):
  counts={self.s['func_15058EA4']:7,self.s['func_15056B08']:1,self.s['func_15059140']:1,self.s['func_150535F4']:1,self.s['func_1502178C']:3,ENTRY:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  name=next(n for n in('func_15058EA4','func_15056B08','func_15059140','func_150535F4','func_1502178C')if self.s[n]==t);a=self.calls[-1][1];result=self.providers.invoke(name,a)
  for i in range(max(4,len(a))):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=result
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.providers.observed,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,service=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.providers.calls==service.calls,(c,'calls');assert m.providers.observed==service.observed,(c,'observed',m.providers.observed,service.observed);assert saved(m),(c,'saved')
def main():
 programs=streams();assert len({tuple(v)for k,v in programs.items()if k!='raw'})==1;assert struct.pack('>98I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0xde7ac:0xde934];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[1])for m in models[2:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,padded_retail_complete_identity=True,independent_public_effects_arguments_and_observations_equal=True,padded_retail_all_private_bytes_and_registers_equal=True,raw_private_or_fault_identity_claim=False,unexecuted_original_words=[i for i in range(98)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=[v for k,v in streams().items()if k!='raw'];count=0
 for c in(Case(velocity=0),Case(velocity=0x41200000),Case(velocity=0xc1200000),Case(velocity=0x7fc12345,mutation=63,alias=2),Case(result=-1,alias=3,phase=8)):
  initial=fixture(c);full=Oracle(programs[-1],initial,c);full.run()
  for cut in range(full.all_accesses):
   values=[]
   for ws in programs:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    values.append(state(m))
   assert all(v==values[0]for v in values[1:]);count+=1
 q=dict(padded_retail_full_state_and_dispatched_access_prefix_triples=count,raw_private_or_portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 caller=list(struct.unpack('>14I',(o/'original-caller-window.bin').read_bytes()));begin=0x1504ab00;end=0x1504ab38;count=called=bypassed=nulls=0;programs=streams()
 for c in list(cases())[::71]:
  for mode in('call','disabled','null'):
   initial=fixture(c);put(initial,OWNER+0x25c,0x200 if mode=='disabled'else 0);put(initial,S['D_80086014']+28,0 if mode=='null'else ENTRY);models=[]
   if mode=='call':expected,service=reference(initial,c);called+=1
   else:expected=initial;service=Providers(expected,c);bypassed+=int(mode=='disabled');nulls+=int(mode=='null')
   for ws in programs.values():
    code=dict(zip(range(ENTRY,ENTRY+392,4),ws));code[end]=0;m=Oracle(caller,initial,c,entry=begin,connected=code);m.r[16]=m.before[16]=OWNER;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Actual caller boundary did not fire')
    assert public(m.memory)==public(expected)and m.providers.calls==service.calls and m.providers.observed==service.observed,(c,mode,'caller');assert m.r[16:24]==m.before[16:24]and m.r[29]==m.entry_sp and m.f[20:]==m.fp_before[20:]and m.r[15]==read(expected,OWNER),(c,mode,'caller saved/reload');assert [a for t,a in m.calls if t==ENTRY]==([(OWNER,)]if mode=='call'else[]);models.append(m)
   assert all(state(m)==state(models[1])for m in models[2:]);count+=1
 q=dict(actual_complete_dispatch_window_words=14,callback_table_index=7,cases_per_stream=count,called_cases=called,disabled_cases=bypassed,null_entry_cases=nulls,all_four_streams_arguments_state_and_boundary_equal=True,post_callback_actor_kind_reload_verified=True,whole_1504A730_execution_claim=False,additional_caller_matching_credit=0);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()),flush=True);print(json.dumps(callers()),flush=True)
