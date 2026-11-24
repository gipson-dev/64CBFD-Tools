"""Literal menu initializer streams, independent semantics and bounded callers."""
from dataclasses import dataclass,replace
import json,struct
from tools.experiments import game_menu_transition_init_151e53e8_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x151E53E8;MENU=0x30000;DATA=0x50000;MARK=0x70000;SCRIPT=0x71000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda x:x&0xffffffff
signed=lambda x,n=32:((x&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))
FIELDS=(('D_800E0A90',4),('D_800BE616',1),('D_8008FE2C',1),('D_80087270',1),('D_800E0B94',1),('D_8008FD74',1),('D_8008FDD4',4),('D_8008FD90',1),('D_800E0A88',4),('D_8008FDC0',2),('D_800E0A86',1))
@dataclass(frozen=True)
class Case:
 count:int=4
 tag:int=-2
 defer:int=0
 gate:int=1
 slot:int=0
 seed:int=0
 phase:int=0
 alias:int=0

def cases():
 k=0
 for count in(-128,-1,0,1,4,127):
  for tag in(-128,-2,-1,0,127):
   for defer in(0,1,256,-1,-2147483648,2147483647):
    yield Case(count,tag,defer,1,(-128,-1,0,1,127)[k%5],k%2,8*(k%2));k+=1
 for gate in(0,255):
  for tag in(-128,-2,-1,0,127):
   for defer in(0,1,256,-1,-2147483648,2147483647):yield Case(4,tag,defer,gate,0,1,8)
 for alias in(1,2):
  for defer in(0,1,256):yield Case(4,-2,defer,1,0,1,8,alias)

def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,512)}
 for n,z in FIELDS:
  m.update({s[n]+i:(i*29+c.seed*11+0x51)&255 for i in range(-8,z+8)})
 m.update({MARK+i:0x6b for i in range(16)});put(m,SCRIPT+8,c.defer)
 menu=MENU if not c.alias else s['D_8008FD90']-0x6c if c.alias==1 else s['D_8008FDD4']-0x6c
 for base in(MENU,menu,0x30000+(menu&65535)):
  m.update({base+i:0x6b for i in range(-8,0x680)})
 for base in(MENU,menu,0x30000+(menu&65535)):m[base+0x42]=c.slot&255
 put(m,s['D_8008FDD4'],menu);put(m,s['D_800E0A90'],0x89abcdef);put(m,s['D_800E0A88'],0x12345678);put(m,s['D_8008FDC0'],0xffff^(c.seed*0xa55a),2)
 m[s['D_800BE616']]=c.gate;m[s['D_8008FD90']]=c.count&255
 for slot in(-128,-1,0,1,127):m[s['D_800AB68C']+slot*10+7]=c.tag&255
 for i in range(128):
  at=s['D_800CC2D0']+i*0x32c+0x31c;put(m,at,DATA+i*0x1c0)
  value=(0,0x8000,0x7fff,0xffff,0x1234)[(i+c.seed)%5]
  if c.alias==1 and i==0:value=0
  if c.alias==2 and i==0:value=3
  put(m,DATA+i*0x1c0+0x1aa,value,2)
 return m

def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def call_effect(m):put(m,MARK,0x13579bdf)
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();calls=[]
 put(m,s['D_800E0A90'],0);gate=m[s['D_800BE616']];m[s['D_8008FE2C']]=0;m[s['D_80087270']]=0
 if not gate:m[s['D_800E0B94']]=4;return m,calls
 m[s['D_800E0B94']]=7;m[s['D_8008FD74']]=8
 menu=read(m,s['D_8008FDD4']);tag=signed(m[s['D_800AB68C']+signed(m[menu+0x42],8)*10+7],8)
 m[menu+0x3f]=3 if tag==-1 else 4;put(m,s['D_800E0A88'],s['func_151DDBA0'if tag==-1 else'func_151E4BD8'])
 index=0
 while index<signed(m[s['D_8008FD90']],8):
  actor=read(m,s['D_800CC2D0']+index*0x32c+0x31c);menu=read(m,s['D_8008FDD4']);put(m,menu+0x6c+index*12,read(m,actor+0x1aa,2),2);index+=1;assert index<=127
 put(m,s['D_8008FDC0'],read(m,s['D_8008FDC0'],2)&0xe35f,2);m[s['D_800E0A86']]=c.defer&255
 menu=read(m,s['D_8008FDD4']);tag=signed(m[s['D_800AB68C']+signed(m[menu+0x42],8)*10+7],8)
 if tag==-2:
  if not u32(c.defer):calls.append((s['func_151E4BD8'],()));call_effect(m)
  else:put(m,s['D_800E0A88'],s['func_151DDBA0']);m[menu+0x3f]=3
 return m,calls

class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(u32(c.defer),));self.fp_before=self.f[:];self.entry_sp=self.r[29]
 def record_call(self,t):
  n=1 if t==ENTRY else 0;assert t in(ENTRY,self.s['func_151E4BD8'],self.s['func_150AE280']),hex(t)
  a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t in(self.s['func_151E4BD8'],self.s['func_150AE280'])
  if t==self.s['func_151E4BD8']:call_effect(self.memory)
  else:put(self.memory,MARK+4,0x2468ace0)
  for i in range(4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0xdeadbeef

def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,calls=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.calls==calls,(c,'calls');assert saved(m),(c,'saved')
def main():
 programs=streams();assert len({tuple(ws)for ws in programs.values()})==1;rom=(r/'conker/conker.us.bin').read_bytes();assert struct.pack('>101I',*programs['retail'])==rom[0x212898:0x212a2c];visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,direct_complete_identity=True,all_private_and_public_bytes_registers_accesses_calls_equal=True,independent_public_semantics_equal=True,unexecuted_original_words=[i for i in range(101)if ENTRY+4*i not in visits],signed_rows_and_count=True,full_word_defer=True,live_count_and_menu_aliases=True,void_result_compared=False,opaque_helper_implementation_claim=False,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 count=0
 for c in(Case(gate=0),Case(count=0),Case(count=1),Case(count=4,defer=256),Case(alias=1),Case(alias=2)):
  initial=fixture(c);full=Oracle(streams()['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams().values():
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access boundary did not fire')
    states.append(state(m))
   assert all(x==states[0]for x in states[1:]);count+=1
 q=dict(four_stream_full_state_and_dispatched_access_prefixes=count,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();rows=[]
 for begin,end,n,result,flag in((0x150261ac,0x150265b4,4,1,False),(0x1509fb28,0x1509fdf8,4,0,False),(0x1509fba0,S['func_150AE280'],7,None,True)):
  cases_run=0
  for arg in(0,256,-1,-2147483648):
   c=Case(defer=arg if begin==0x1509fb28 else 0,seed=1);initial=fixture(c);put(initial,SCRIPT+8,arg);fragment=struct.unpack_from('>'+str(n)+'I',rom,begin-0x15000000+0x2d4b0)
   if flag:put(initial,S['D_8008FDC0'],read(initial,S['D_8008FDC0'],2)|0x8000,2)
   expected,calls=reference(initial,c)
   if flag:calls.append((S['func_150AE280'],()))
   models=[]
   for ws in streams().values():
    code=dict(zip(range(ENTRY,ENTRY+404,4),ws));code[end]=0;m=Oracle(fragment,fixture(c),c,entry=begin,connected=code);put(m.memory,SCRIPT+8,arg);m.r[16]=SCRIPT;m.r[5]=S['D_8008FDC0'];m.r[4]=0x12345678;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller continuation not reached')
    assert public(m.memory)==public(expected);assert m.calls==[(ENTRY,(u32(c.defer),)),*calls];assert (result is None or m.r[2]==result)and m.r[29]==m.entry_sp;assert m.r[31]==(0x1509fbbc if flag else begin+8);assert m.r[16:24]==m.before[16:24]and m.f[20:]==m.fp_before[20:];models.append(m)
   assert all(state(x)==state(models[0])for x in models[1:]);cases_run+=1
  rows.append(dict(start=hex(begin),original_words=n,cases_per_stream=cases_run,boundary='stack-switch helper entry'if flag else'caller branch continuation',callee_body_executed=False if flag else None))
 q=dict(windows=rows,complete_dispatcher_claim=False,void_target_result_ignored=True,full_script_argument=True,stack_switch_body_executed=False,stack_switch_return_assumed=False);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(faults());print(callers())
