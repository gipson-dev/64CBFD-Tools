"""Literal fade streams, wrap arithmetic, live aliases and explicit ABI stub."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_menu_fade_renderer_151e09dc_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x151E09DC;MENU=0x30000;OTHER=0x31000;MARK=0x70000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda x:x&0xffffffff
signed=lambda x,n=32:((x&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))
NAMES=('func_1504332C','func_15042D94','func_15042D78','func_151E2404','func_151E3344');ARITY=dict(zip(NAMES,(4,5,1,0,5)))
@dataclass(frozen=True)
class Case:
 alpha:int=255
 ticks:int=1
 direction:int=1
 save:int=1
 flags:int=0x1234
 slot:int=0
 index:int=0
 mode:int=0
 seed:int=0
 phase:int=0
 alias:int=0
def cases():
 k=0
 for alpha in(0,1,31,32,33,254,255):
  for ticks in(-2147483648,-1,0,1,7,8,2147483647,0x08000000,0x04000000,0x03ffffff,0x07ffffff,0x04000001):
   for direction in(0,1,-1):
    yield Case(alpha,ticks,direction,(0,1,-128)[k%3],(0,32,0x1234,0xffff)[k%4],(-128,-1,0,1,127)[k%5],(-128,-1,0,1,127)[(k//5)%5],0,k%2,8*(k%2));k+=1
 for mode in range(1,7):
  for alpha,ticks,direction in((1,1,0),(255,0,0),(255,0,1),(32,1,-1)):
   for seed in(0,1):yield Case(alpha,ticks,direction,1,0x1234,0,0,mode,seed,8*seed)
 for direction in(1,33,-1):yield Case(255,0,direction,1,0x120,0,0,0,1,8,1)
def menu_address(c,s):return s['D_800E0A96']-0x20 if c.alias else MENU
def mask_value(index):return u32(0x13579bdf^(u32(index)*0x100101))
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,512)}
 for base in(MENU,OTHER,menu_address(c,s)):m.update({base+i:0x6b for i in range(-8,136)})
 for n,z in(('D_8008FDD4',4),('D_800E0A95',1),('D_800E0A96',1),('D_8008FDE0',1),('D_800BE9E4',4)):
  for i in range(z):m.setdefault(s[n]+i,0x6b)
 m.update({MARK+i:0x6b for i in range(16)});m[s['D_800AB850']]=35;m[s['D_800AB850']+1]=0
 for base in(MENU,menu_address(c,s)):m[base+0x42]=c.slot&255;put(m,base+0x20,c.flags,2)
 m[OTHER+0x42]=7;put(m,OTHER+0x20,0xa55a,2)
 for index in(-128,-1,0,1,127):put(m,s['D_800AB754']+index*4,mask_value(index))
 m[s['D_800AB690']+c.slot*10]=c.index&255;m[s['D_800AB690']+70]=1
 put(m,s['D_8008FDD4'],menu_address(c,s));put(m,s['D_800BE9E4'],c.ticks);m[s['D_800E0A95']]=c.alpha;m[s['D_800E0A96']]=c.direction&255;m[s['D_8008FDE0']]=c.save&255
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def effect(m,c,name,s):
 if c.mode==1 and name==NAMES[0]:put(m,s['D_8008FDD4'],OTHER);m[s['D_800E0A95']]=96;m[s['D_800E0A96']]=1;put(m,s['D_800BE9E4'],2)
 if c.mode==2 and name==NAMES[1]:m[s['D_800E0A95']]=64;m[s['D_800E0A96']]=0;put(m,s['D_800BE9E4'],1)
 if c.mode==3 and name==NAMES[2]:put(m,s['D_8008FDD4'],OTHER);m[s['D_800AB690']+70]=127
 if c.mode==4 and name==NAMES[4]:put(m,s['D_8008FDD4'],OTHER);put(m,OTHER+0x20,0x1234,2);m[s['D_800E0A96']]=127
 if c.mode==5 and name==NAMES[4]:
  menu=read(m,s['D_8008FDD4']);put(m,menu+0x20,0xabdf,2);m[s['D_800E0A96']]=0x81;put(m,s['D_800AB754'],0xdeadbeef)
 if c.mode==6 and name==NAMES[3]:put(m,s['D_8008FDD4'],OTHER);m[s['D_800E0A96']]=12;m[s['D_8008FDE0']]=99
def reference(initial,c,s=None):
 s=S if s is None else s;m=initial.copy();calls=[]
 def call(name,*args):calls.append((s[name],tuple(map(u32,args))));effect(m,c,name,s)
 call(NAMES[0],255,255,255,255);call(NAMES[1],148,126,1,s['D_800AB850'],26);call(NAMES[2],129)
 menu=read(m,s['D_8008FDD4']);index=signed(m[s['D_800AB690']+signed(m[menu+0x42],8)*10],8);mask=read(m,s['D_800AB754']+index*4)
 if m[s['D_800E0A96']]==0:
  put(m,menu+0x20,read(m,menu+0x20,2)&0xffdf,2);value=signed(m[s['D_800E0A95']]-(read(m,s['D_800BE9E4'])<<5))
  if value<=0:
   menu=read(m,s['D_8008FDD4']);m[menu+0x3f]=0
   if m[s['D_8008FDE0']]:call(NAMES[3])
   m[s['D_8008FDE0']]=0;m[s['D_800E0A96']]=255;return m,calls
  m[s['D_800E0A95']]=value&255
 else:
  value=signed(m[s['D_800E0A95']]+(read(m,s['D_800BE9E4'])<<5))
  if value>=256:value=255
 m[s['D_800E0A95']]=value&255
 if value!=255:put(m,read(m,s['D_8008FDD4'])+0x20,0,2)
 call(NAMES[4],mask,1,0,value&255,0);menu=read(m,s['D_8008FDD4'])
 if read(m,menu+0x20,2)&32:m[s['D_800E0A96']]=0
 put(m,menu+0x20,read(m,menu+0x20,2)&0xffdf,2);return m,calls
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=());self.fp_before=self.f[:];self.entry_sp=self.r[29]
 def record_call(self,t):
  name=next((n for n in NAMES if self.s[n]==t),None);assert name is not None or t==ENTRY,hex(t);n=0 if name is None else ARITY[name];a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  name=next(n for n in NAMES if self.s[n]==t);effect(self.memory,self.c,name,self.s)
  for i in range(5 if ARITY[name]==5 else 4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=0xdeadbeef
def streams(s=None):return{label:bound_blob(*payload(o/path,p.FUNCTION),S if s is None else s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.dispatched_word)
def saved(m):return m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:]and m.r[29]==m.entry_sp
def check(m,initial,c,s=None):
 expected,calls=reference(initial,c,s);assert public(m.memory)==public(expected),(c,'public');assert m.calls==calls,(c,'calls',m.calls,calls);assert saved(m),(c,'saved')
def main():
 programs=streams();assert len({tuple(ws)for ws in programs.values()})==1;assert struct.pack('>101I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x20de8c:0x20e020];visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visits.update(models[-1].visits);count+=1
 c=Case(alpha=255,ticks=0,alias=1);initial=fixture(c);bad=programs['retail'][:];assert bad[94]==0x94430020;bad[94]=0;m=Oracle(bad,initial,c);m.run();expected,calls=reference(initial,c);assert public(m.memory)!=public(expected)and m.calls==calls and saved(m)
 q=dict(cases_per_stream=count,streams=4,direct_complete_identity=True,independent_public_semantics_equal=True,unexecuted_original_words=[i for i in range(101)if ENTRY+4*i not in visits],signed_wrap_and_full_value_vs_byte=True,live_provider_mutations=True,post_draw_alias_reread=True,effective_stale_halfword_instruction_control=True,void_result_compared=False,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 count=0
 for c in(Case(),Case(alpha=1,direction=0),Case(alpha=255,direction=0,ticks=0,save=0),Case(ticks=-1,mode=4),Case(alpha=255,ticks=0,alias=1)):
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
 rom=(r/'conker/conker.us.bin').read_bytes();begin=0x151df0c4;end=0x151df1b0;fragment=struct.unpack_from('>4I',rom,0x20c574);count=0
 for c in(Case(),Case(alpha=1,direction=0),Case(mode=4),Case(ticks=-1,direction=0)):
  initial=fixture(c);put(initial,STACK+c.phase+28,0x87654320);expected,calls=reference(initial,c);models=[]
  for ws in streams().values():
   code=dict(zip(range(ENTRY,ENTRY+404,4),ws));code[end]=0;m=Oracle(fragment,initial,c,entry=begin,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller continuation not reached')
   assert public(m.memory)==public(expected)and m.calls==[(ENTRY,()),*calls];assert m.r[31]==0x87654320 and m.r[29]==m.entry_sp and m.r[16:24]==m.before[16:24]and m.f[20:]==m.fp_before[20:];models.append(m)
  assert all(state(x)==state(models[0])for x in models[1:]);count+=1
 q=dict(original_bounded_caller_words=4,cases_per_stream=count,enclosing_RA_restored=True,complete_dispatcher_claim=False,void_target_result_ignored=True);(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def abi_stub():
 before=payload(o/'selected-final/before.o','func_151E3344');after=payload(o/'selected-final/candidate.o','func_151E3344');assert before==(bytes.fromhex('0000102503e0000800000000'),{})and after==(bytes.fromhex(p.MANIFEST['abi_helper_hex']),{});count=0
 for phase in(0,8):
  for args in((0,1,0,255,0),(0xffffffff,0x80000000,0x7fffffff,0xdeadbeef,0xffffffff)):
   c=Case(phase=phase);initial=fixture(c);models=[]
   for raw in(before,after):
    m=Oracle(bound_blob(*raw,S),initial,c,entry=S['func_151E3344']);m.r[4:8]=args[:4];put(m.memory,m.entry_sp+16,args[4]);m.run();assert saved(m)and m.r[2]==0;models.append(m)
   assert public(models[0].memory)==public(models[1].memory)
   homes=set(range(models[0].entry_sp,models[0].entry_sp+16));assert{a:b for a,b in models[0].memory.items()if a not in homes}=={a:b for a,b in models[1].memory.items()if a not in homes}
   for j,arg in enumerate(args[:4]):assert read(models[1].memory,models[1].entry_sp+4*j)==arg
   assert read(models[1].memory,models[1].entry_sp+16)==args[4];count+=1
 q=dict(cases=count,old_words=3,new_words=7,only_first_four_o32_homes_written=True,SP_RA_saved_registers_and_fifth_argument_preserved=True,zero_result_preserved=True,retail_helper_implementation_claim=False,helper_matching_credit=0);(o/'abi-stub.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(faults());print(callers());print(abi_stub())
