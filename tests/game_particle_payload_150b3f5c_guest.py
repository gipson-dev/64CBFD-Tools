"""Particle packet, seeded padding, live providers and original factory/copy."""
from dataclasses import dataclass
import json,math,struct
from tools.experiments import game_particle_payload_150b3f5c_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x150B3F5C;SOURCE=0x30000;POSITION=0x80000;ALT_SOURCE=0x31000;ALT_POSITION=0x81000;OUTPUT=0x50000;ALTOUT=0x60000;MARK=0x70000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda n:n&0xffffffff
signed16=lambda n:((n&65535)^32768)-32768
NAMES=('memcpy','func_15147A80','func_150ADA20','func_1000FA64','func_15167A68','bzero');ARITY=dict(zip(NAMES,(3,11,0,12,6,2)))
class ConversionBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
 count:int=20
 success:int=1
 mode:int=0
 seed:int=0
 phase:int=0
 shape:int=0
 alias:int=0
 src:int=SOURCE
 pos:int=POSITION
def cases():
 k=0
 for count in(-32768,-1,0,1,20,255,256,0x12340014):
  for success in(0,1):
   for shape in range(4):
    for seed in(0,1):yield Case(count,success,0,seed,8*seed,shape);k+=1
 for mode in range(1,6):
  for success in(0,1):
   for seed in(0,1):yield Case(-1,success,mode,seed,8*seed,1)
 for alias in(1,2):
  for shape in range(4):yield Case(20,1,0,1,8,shape,alias)
def args(c):return(c.src,c.src+16 if c.alias==1 else c.src if c.alias==2 else c.pos,u32(c.count))
def data(m,a,n):return bytes(m[a+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,512)}
 for base,n in((SOURCE,128),(POSITION,64),(ALT_SOURCE,128),(ALT_POSITION,64),(OUTPUT,0x2600),(ALTOUT,128),(MARK,32)):
  m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(-16,n+16)})
 pairs=((1.25,2.5),(-0.,0.),(1e20,-1e20),(16777216.,1.));a,b=pairs[c.shape]
 for base in(SOURCE,ALT_SOURCE):put(m,base+20,bits(a if base==SOURCE else 8.));put(m,base+24,bits(b if base==SOURCE else -1.))
 positions=((-32768.75,32767.75,0.),(-0.,.75,-.75),(65536.75,-65537.25,1000000.),(1e9,-1e9,2147483520.))
 for i,v in enumerate(positions[c.shape]):put(m,args(c)[1]+i*4,bits(v));put(m,ALT_POSITION+i*4,bits(10.25+i))
 return m
def random(c):return(0,64,0xffffffff,0x12345678)[(c.seed+c.shape)%4]
def copy(m,dst,src,n):
 for i in range(n):m[dst+i]=m[src+i]
def effect(m,c,name,home):
 if c.mode==1 and name=='first-copy':
  put(m,SOURCE+20,bits(8.));put(m,SOURCE+24,bits(-1.))
  for i in range(3):put(m,args(c)[1]+4*i,bits(20.5+i))
 if c.mode==2 and name in('func_15147A80','func_15167A68'):
  for i in range(3):put(m,args(c)[1]+4*i,bits(30.25+i))
 if c.mode==3 and name=='func_150ADA20':
  for i in range(3):put(m,args(c)[1]+4*i,bits(-40.5-i))
 if c.mode==4 and name=='func_1000FA64':put(m,OUTPUT+0x98,ALTOUT)
 if c.mode==5 and name=='first-copy':put(m,home,ALT_SOURCE);put(m,home+4,ALT_POSITION);put(m,home+8,0x1234ffff)
def initialize(m,request,connected=False):
 put(m,OUTPUT+0x98,OUTPUT+0xa0);put(m,OUTPUT+0x94,OUTPUT+0xf8);copy(m,OUTPUT+0x10,request,28)
 for i,v in enumerate((0,0,0,7,7,7)):m[OUTPUT+0x2c+i]=v
 put(m,OUTPUT+0x34,0);m[OUTPUT+0x38]=0
 for at in(0x3c,0x40,0x44,0x48,0x4c,0x50,0x54,0x58,0x5c):put(m,OUTPUT+at,0)
 m[OUTPUT+0x7c]=0
 if not connected:
  for i in range(16):m[OUTPUT+0x84+i]=0
def reference(initial,c,s=None,connected=False):
 s=S if s is None else s;m=initial.copy();home=STACK+c.phase;frame=home-184;request=frame+156;packet=frame+68;calls=[];snapshots=[];copies=[]
 for i,v in enumerate(args(c)):put(m,home+4*i,v)
 def call(name,*a):calls.append((s[name],tuple(map(u32,a))));put(m,MARK,len(calls))
 call('memcpy',packet,read(m,home),64);copy(m,packet,read(m,home),64);effect(m,c,'first-copy',home)
 m[request+0x15]=read(m,home+10,2)&255;m[packet+0x48]=0;put(m,request+14,2,2);put(m,request+12,500,2);put(m,packet+0x44,0)
 source=read(m,home);value=bits(floating(read(m,source+20))+floating(read(m,source+24)));put(m,packet+0x4c,value);m[packet+0x50]=0;put(m,packet+0x54,0);put(m,packet+0x40,value);copy(m,request,read(m,home+4),12);put(m,request+16,9)
 a=(request,88,36,7,7,7,0,0,0,255,1);call('func_15147A80',*a);snapshots.append(data(m,request,28))
 if connected:call('func_15167A68',34,1,248+m[request+21]*36,1,255,1);effect(m,c,'func_15167A68',home)
 else:effect(m,c,'func_15147A80',home)
 if not c.success:return m,calls,0,snapshots,copies
 initialize(m,request,connected)
 if connected:
  call('memcpy',OUTPUT+16,request,28);call('bzero',OUTPUT+0x84,16)
  for i in range(16):m[OUTPUT+0x84+i]=0
 call('func_150ADA20');effect(m,c,'func_150ADA20',home);pos=read(m,home+4);xyz=[]
 for i in range(3):
  value=floating(read(m,pos+4*i))
  if not math.isfinite(value)or not -2147483648<=value<2147483648:raise ConversionBoundary
  xyz.append(u32(signed16(math.trunc(value))))
 call('func_1000FA64',0x221,*xyz,25000,4000,600,s['func_1000EF40'],0,0,8,random(c)&64);effect(m,c,'func_1000FA64',home)
 dest=read(m,OUTPUT+0x98);call('memcpy',dest,packet,88);copies.append(data(m,packet,88));copy(m,dest,packet,88);return m,calls,OUTPUT,snapshots,copies
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=args(c));self.fp_before=self.f[:];self.entry_sp=self.r[29];self.snapshots=[];self.copies=[];self.copy_count=0;self.connected_factory=connected is not None
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   value=floating(self.f[w>>11&31])
   if not math.isfinite(value)or not -2147483648<=value<2147483648:raise ConversionBoundary
   self.f[w>>6&31]=u32(math.trunc(value))
  else:super().execute(w)
 def record_call(self,t):
  name=next((n for n in NAMES if self.s[n]==t),None);assert name is not None or t==ENTRY,hex(t);n=3 if name is None else ARITY[name];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a));put(self.memory,MARK,len([1 for target,_ in self.calls if target!=ENTRY]))
  if name=='func_15147A80':self.snapshots.append(data(self.memory,a[0],28))
  if name=='memcpy':
   self.copy_count+=1
   if a[2]==88:self.copies.append(data(self.memory,a[1],88))
 def hook(self,t):
  name=next(n for n in NAMES if self.s[n]==t);a=self.calls[-1][1];c=self.c;home=self.entry_sp;value=0xdeadbeef
  if name=='memcpy':copy(self.memory,*a);value=a[0];effect(self.memory,c,'first-copy'if self.copy_count==1 else name,home)
  elif name=='func_15147A80':
   effect(self.memory,c,name,home);value=OUTPUT if c.success else 0
   if value:initialize(self.memory,a[0])
  elif name=='func_15167A68':effect(self.memory,c,name,home);value=OUTPUT if c.success else 0
  elif name=='func_150ADA20':effect(self.memory,c,name,home);value=random(c)
  elif name=='func_1000FA64':effect(self.memory,c,name,home);value=0x8001
  else:
   assert name=='bzero'
   for i in range(a[1]):self.memory[a[0]+i]=0
  for i in range(max(4,ARITY[name])):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def canonical(trace,home):
 result=list(trace);count=0
 for i in range(len(result)-1):
  a,b=result[i:i+2]
  if len(a)==4 and len(b)==4 and a[:3]==('W',home-7,1)and b[:3]==('W',home-48,4):result[i],result[i+1]=b,a;count+=1
 assert count==1,count;return result
def state(m,raw=False):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,canonical(m.trace,m.entry_sp)if raw else m.trace,canonical(m.events,m.entry_sp)if raw else m.events,m.calls,m.snapshots,m.copies,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None,connected=False,caller=False):
 expected,calls,value,snapshots,copies=reference(initial,c,s,connected);assert public(m.memory)==public(expected),(c,'public');assert m.calls==([(ENTRY,args(c))]if caller else[])+calls,(c,'calls',m.calls,calls);assert m.r[2]==value and (saved(m)if not caller else m.r[29]==m.entry_sp and m.r[16:24]==m.before[16:24]and m.f[20:]==m.fp_before[20:]),(c,'return/saved');assert m.snapshots==snapshots and m.copies==copies,(c,'copied bytes')
def main():
 programs=streams();assert len({tuple(ws)for n,ws in programs.items()if n!='raw'})==1;assert struct.pack('>99I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0xe140c:0xe1598];visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for label,ws in programs.items():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append((label,m))
  base=state(models[-1][1]);assert all(state(m,label=='raw')==base for label,m in models);visits.update(models[-1][1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,all_public_private_bytes_registers_calls_and_copied_bytes_equal=True,raw_trace_equal_after_proved_store_commutation=True,normalized_stream_complete_trace_identity=True,unexecuted_original_words=[i for i in range(99)if ENTRY+4*i not in visits],unwritten_request_and_payload_bytes_preserved=True,raw_fault_prefix_identity_claim=False,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 count=0
 for c in(Case(success=0),Case(),Case(mode=4,seed=1,phase=8)):
  initial=fixture(c);programs={n:ws for n,ws in streams().items()if n!='raw'};full=Oracle(programs['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   states=[]
   for ws in programs.values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Fault boundary did not fire')
    states.append(state(m))
   assert all(v==states[0]for v in states[1:]);count+=1
 q=dict(padded_retail_full_state_prefix_triples=count,raw_prefix_excluded=True,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def connected():
 rom=(r/'conker/conker.us.bin').read_bytes();code={}
 for entry,offset,words in((S['func_15147A80'],0x174f30,115),(S['memcpy'],0x22ec0,11)):code.update(zip(range(entry,entry+words*4,4),struct.unpack_from('>'+str(words)+'I',rom,offset)))
 count=0
 for c in(Case(),Case(success=0),Case(count=0),Case(count=-1),Case(mode=2),Case(mode=4),Case(shape=3,phase=8,seed=1)):
  initial=fixture(c);models=[]
  for label,ws in streams().items():m=Oracle(ws,initial,c,connected=code);m.run();check(m,initial,c,connected=True);models.append((label,m))
  assert all(state(m,label=='raw')==state(models[-1][1])for label,m in models);count+=1
 q=dict(cases_per_stream=count,original_factory_words=115,original_memcpy_words=11,allocator_and_zero_providers_bounded=True,original_RNG_or_audio_implementation_claim=False,whole_seeded_request_and_payload_copy_verified=True);(o/'connected.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q

def callers():
 from dataclasses import replace
 rom=(r/'conker/conker.us.bin').read_bytes();reports=[]
 for begin,end,source_offset,position_offset in((0x150b2dc8,0x150b2dd8,0xa0,0xe0),(0x150b669c,0x150b66c8,0x30,0x24)):
  fragment=struct.unpack_from('>'+str((end-begin)//4)+'I',rom,begin-0x15000000+0x2d4b0);count=0
  for c in(Case(),Case(success=0),Case(count=-1,phase=8,seed=1),Case(mode=4,shape=3)):
   if begin==0x150b2dc8:c=replace(c,count=20)
   home=STACK+c.phase;original=fixture(c);c=replace(c,src=home+source_offset,pos=home+position_offset);initial=fixture(c)
   for i in range(64):initial[c.src+i]=original[SOURCE+i]
   for i in range(12):initial[c.pos+i]=original[POSITION+i]
   # The second window finishes writing its source block before the call.
   # F10/F4 are its source[5]/source[6]; the other FPR stores and SH are
   # seeded inputs. Fold those original stores into the independent input.
   fvalues={10:read(initial,c.src+20),4:read(initial,c.src+24),16:bits(1.5),18:bits(-2.),6:bits(4.),8:bits(8.)}
   if begin==0x150b669c:
    put(initial,S['D_8009FC8E'],c.count,2)
    for at,reg in((0x44,10),(0x48,4),(0x50,16),(0x58,18),(0x5c,6),(0x6c,8)):put(initial,home+at,fvalues[reg])
    put(initial,home+0x66,0x1234,2)
   expected_initial=initial.copy();models=[]
   for label,ws in streams().items():
    code=dict(zip(range(ENTRY,ENTRY+396,4),ws));code[end]=0;m=Oracle(fragment,initial,c,entry=begin,connected=code);m.connected_factory=False;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    if begin==0x150b669c:
     m.r[6]=(S['D_8009FC8E']+0x8000)&0xffff0000;m.r[14]=0x1234
     for reg,v in fvalues.items():m.f[reg]=v
     m.fp_before=m.f[:]
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller continuation not reached')
    check(m,expected_initial,c,caller=True);assert m.r[31]==end;models.append((label,m))
   assert all(state(m,label=='raw')==state(models[-1][1])for label,m in models);count+=1
  reports.append(dict(begin=hex(begin),continuation=hex(end),original_words=len(fragment),cases_per_stream=count))
 q=dict(windows=reports,target_arguments_and_copy_data_verified=True,target_frame_and_saved_registers_preserved=True,enclosing_full_function_claim=False,caller_epilogue_execution_claim=False);(o/'caller-windows.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(faults());print(connected())
