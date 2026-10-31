"""Slot refresh: live actor scan, helper effects, eligibility code and repeat caller."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_slot_actor_refresh_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY;STRIDE=0x32C
BASE,TICKS,DEST,POOL,INDEX=0x800C3640,0x800BEA08,0x800C35B0,0x800CC2D0,0x800C3E78
MODE,RESET,CLEAR,QUERY,APPLY,FINISH=0x150242F8,0x1501EC38,0x15020EC4,0x150229E4,0x1502178C,0x1501E81C
FLAGS,COUNTS,LINK_ID,DESCRIPTORS=0x800C35C8,0x800C363A,0x800CBFDF,0x800C35F0
FLAG,STOP,MARK,FLAG_DATA,DESC_DATA=0x800C3C99,0x800C35C4,0x70000,0x60000,0x61000
SYMS=dict(D_800C3640=BASE,D_800BEA08=TICKS,D_800C35B0=DEST,D_800CC2D0=POOL,D_800C3E78=INDEX,func_150242F8=MODE,func_1501EC38=RESET,func_15020EC4=CLEAR,func_150229E4=QUERY,func_1502178C=APPLY,func_1501E81C=FINISH,D_800C35C8=FLAGS,D_800C363A=COUNTS,D_800CBFDF=LINK_ID,D_800C35F0=DESCRIPTORS)
u32=lambda v:v&0xFFFFFFFF
def address(base,slot):return u32(base+u32(slot*4))
@dataclass(frozen=True)
class Case:
 slot:int=0
 pattern:int=1
 result:int=1
 effect:int=0
 phase:int=0
 seed:int=0
 onehot:int=24
 base:int=0x7FFFFFFF
 ticks:int=0x80000001
 flag:int=1
 stop:int=0
 exit_after:int=0
 drop_at:int=0
def active(c,i):return (0,4 if i&1 else 27,0xFFFFFFFF if i&1 else 0,4 if i==0 else 0,4 if i==24 else 0,4 if i==c.onehot else 0,4 if(i*13+c.seed)%3==0 else 0,0x80000000)[c.pattern]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,2048)}
 for base,n in ((s['D_800CC2D0']-32,25*STRIDE+64),(MARK,32),(FLAG_DATA,64),(DESC_DATA,64)):
  m.update({base+i:(i*29+c.seed+0x5A)&255 for i in range(n)})
 for name in ('D_800C3640','D_800C35B0'):
  for i in range(-4,8):put(m,u32(s[name]+i*4),0xA5000000+i)
 put(m,address(s['D_800C3640'],c.slot),c.base);put(m,s['D_800BEA08'],c.ticks)
 for i in range(25):
  p=s['D_800CC2D0']+i*STRIDE;put(m,p,active(c,i));put(m,p+5,4 if i&1 else 0,1);put(m,p+0x3B,i,1);put(m,p+0x65,i+1 if i%3==0 else 0,1)
 put(m,s['D_800C3E78'],0xA7,1);put(m,MARK,0);put(m,MARK+4,0);put(m,FLAG,c.flag,1);put(m,STOP,c.stop,1)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+2048}
def observation(m,c,s):return(m[s['D_800C3E78']],read(m,address(s['D_800C35B0'],c.slot)),read(m,address(s['D_800C3640'],c.slot)),read(m,s['D_800BEA08']),read(m,MARK),tuple(read(m,s['D_800CC2D0']+i*STRIDE)for i in range(25)))
def result(c,i):return(0,1,0x80000000,2 if i%3==0 else 0)[c.result]
def effect(m,c,s,t,a):
 pool=s['D_800CC2D0'];put(m,MARK,read(m,MARK)+1)
 def toggle(i):
  if i<25:put(m,pool+i*STRIDE,0 if read(m,pool+i*STRIDE)else 4)
 if c.effect&1:
  if t==s['func_150242F8']and a[0]==1:toggle(0);toggle(24);put(m,s['D_800BEA08'],0x89ABCDEF);put(m,address(s['D_800C3640'],c.slot),0x76543210)
  elif t==s['func_1501EC38']:put(m,pool+STRIDE,1)
  elif t==s['func_150242F8']and a[0]==0:put(m,pool+2*STRIDE,0)
  elif t==s['func_15020EC4']:put(m,pool+3*STRIDE,0x80000000)
 i=(a[0]-pool)//STRIDE if t in(s['func_150229E4'],s['func_1502178C'])else 0
 if t==s['func_150229E4']and c.effect&2:put(m,s['D_800C3E78'],0xE0+(i&31),1);put(m,a[0],0);toggle(i+1)
 if t==s['func_1502178C']and c.effect&4:put(m,a[0]+0x2FF,0x77,1);put(m,s['D_800C3E78'],0x80+(i&31),1);put(m,address(s['D_800C35B0'],c.slot),read(m,address(s['D_800C35B0'],c.slot))^0x13579BDF);toggle(i+2)
 if t==s['func_1501E81C']:
  finished=read(m,MARK+4)+1;put(m,MARK+4,finished)
  if c.effect&8:put(m,s['D_800C3E78'],0xFE,1);put(m,address(s['D_800C35B0'],c.slot),read(m,address(s['D_800C35B0'],c.slot))+17)
  if c.exit_after:put(m,STOP,int(c.stop or finished>=c.exit_after),1);put(m,FLAG,0 if finished==c.drop_at else 1,1)
 return result(c,i)if t==s['func_150229E4']else u32(0xA5000000|(t&65535))
def query(m,p,s=SYMS):
 if not p or not read(m,p)or not read(m,s['D_800C35C8']):return 0
 group=int(read(m,p+5,1)==4);link=read(m,p+0x65,1);identity=read(m,s['D_800CBFDF']+link*STRIDE,1)if link else read(m,p+0x3B,1);count=read(m,s['D_800C363A']+group,1)
 for i in range(count):
  flags=read(m,s['D_800C35C8']+4*group);desc=read(m,s['D_800C35F0']+4*group)+8*i
  if read(m,flags+2*i,2)and read(m,desc,2)==2 and read(m,desc+2,1)==identity:return 2 if link else 1
 return 0
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);calls=[];observations=[];put(m,address(s['D_800C35B0'],c.slot),read(m,address(s['D_800C3640'],c.slot))+read(m,s['D_800BEA08']))
 def call(t,*a):
  a=tuple(map(u32,a));calls.append((t,a));observations.append(observation(m,c,s))
  return query(m,a[0],s)if connected and t==s['func_150229E4']else effect(m,c,s,t,a)
 call(s['func_150242F8'],1,0);call(s['func_1501EC38'],0);call(s['func_150242F8'],0,0);call(s['func_15020EC4'],0)
 for i in range(25):
  p=s['D_800CC2D0']+i*STRIDE
  if not read(m,p):continue
  put(m,s['D_800C3E78'],i,1)
  if call(s['func_150229E4'],p):call(s['func_1502178C'],p,c.slot,0xFFFFFFFF)
 call(s['func_1501E81C'],1,c.slot)
 return m,calls,observations
def linked(obj,label,entry=ENTRY,s=SYMS,function=F):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,args=None):
  self.observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(u32(c.slot),)if args is None else args)
 def record_call(self,t):
  counts={self.syms['func_150242F8']:2,self.syms['func_1501EC38']:1,self.syms['func_15020EC4']:1,self.syms['func_150229E4']:1,self.syms['func_1502178C']:3,self.syms['func_1501E81C']:2,ENTRY:1};assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append(observation(self.memory,self.case,self.syms))
 def hook(self,t):
  value=effect(self.memory,self.case,self.syms,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=value
def state(m):return(complete(m),m.trace,m.observations,m.current_pc,m.delay_of,m.all_accesses)
def check(m,initial,c,s=SYMS,connected=False):
 want,calls,observations=reference(initial,c,s,connected);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),c
def programs(label='guest',entry=ENTRY,s=SYMS):return[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','qualified-padded.o','selected-final.o'))]
def cases():
 for slot,pattern,result_mode,effect,phase in itertools.product((0,1),range(8),range(4),(0,1,2,4,8,15),(0,8)):yield Case(slot,pattern,result_mode,effect,phase)
 for i,slot,result_mode in itertools.product(range(25),(0,1),(0,2)):yield Case(slot=slot,pattern=5,onehot=i,result=result_mode,effect=15,seed=i)
 for base,ticks,slot in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1)):yield Case(slot=slot,base=base,ticks=ticks,pattern=0)
def guest_suite():
 ws=programs();assert ws[0]==ws[1]and ws[0]!=ws[2];visited=set();corpus=list(cases())
 for c in corpus:
  initial=fixture(c);ms=[]
  for w in ws:m=Oracle(w,initial,c).run();check(m,initial,c);ms.append(m);visited.update(m.visits)
  assert state(ms[0])==state(ms[1])==state(ms[2]),c
 assert set(range(ENTRY,ENTRY+236,4))<=visited;cuts=delays=0
 for c in (Case(pattern=0),Case(pattern=5,onehot=24,effect=15),Case(pattern=1,result=0)):
  initial=fixture(c);normal=Oracle(ws[0],initial,c).run()
  for cut in range(normal.all_accesses):
   ms=[]
   for w in ws:
    m=Oracle(w,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebase=0
 for entry,pool,index,base,dest,ticks in ((0x17007FFC,0x802D7FFC,0x803D8000,0x80407FFC,0x80508000,0x8060FFFC),(0x2500FFFC,0x803D8000,0x802D7FFC,0x80508000,0x80407FFC,0x80618000)):
  s=dict(SYMS,D_800CC2D0=pool,D_800C3E78=index,D_800C3640=base,D_800C35B0=dest,D_800BEA08=ticks)
  for i,name in enumerate(('func_150242F8','func_1501EC38','func_15020EC4','func_150229E4','func_1502178C','func_1501E81C')):s[name]=(entry&0xF0000000)+0x01000000+i*0x1000
  ps=programs('rebase-'+str(entry),entry,s)
  for c in (Case(),Case(slot=1,pattern=0),Case(effect=15,result=2,phase=8)):
   initial=fixture(c,s);ms=[Oracle(w,initial,c,entry,s).run()for w in ps]
   for m in ms:check(m,initial,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebase+=1
 aliases=0
 for name,value in (('D_800C3E78',POOL+0x3B),('D_800C35B0',POOL)):
  s=dict(SYMS,**{name:value});ps=programs('alias-'+name,s=s)
  for c in (Case(),Case(pattern=0,effect=15),Case(slot=1,result=2,effect=6)):
   initial=fixture(c,s);ms=[Oracle(w,initial,c,s=s).run()for w in ps]
   for m in ms:check(m,initial,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);aliases+=1
 return dict(cases=len(corpus),executions=3*len(corpus),body_words=59,frame=48,guards=3,bindings=17,all_target_words_exercised=True,access_cuts=cuts,delay_cuts=delays,rebase_cases=rebase,alias_cases=aliases,all25_actor_positions_and_live_helper_mutations=True,wrapping_timestamp_and_call_observations=True,raw_complete_machine_state_equal=True,portable_alias_or_hardware_claimed=False)
def connected_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>73I',rom,0x4FE94);helper=dict(zip(range(QUERY,QUERY+292,4),words));ws=programs('connected');count=0;visited=set()
 for missing,match,linked,pattern,slot in itertools.product((False,True),(False,True),(False,True),(1,2,5),(0,1)):
  c=Case(slot=slot,pattern=pattern,onehot=24,effect=1);initial=fixture(c)
  for group in (0,1):
   put(initial,FLAGS+4*group,0 if missing and group==0 else FLAG_DATA+16*group);put(initial,DESCRIPTORS+4*group,DESC_DATA+16*group);put(initial,COUNTS+group,2,1)
   for i in (0,1):put(initial,FLAG_DATA+16*group+2*i,1,2);put(initial,DESC_DATA+16*group+8*i,2 if match else 3,2);put(initial,DESC_DATA+16*group+8*i+2,24 if i else 0,1)
  for i in range(25):put(initial,POOL+i*STRIDE+0x65,(i+1)if linked else 0,1)
  ms=[]
  for w in ws:m=Oracle(w,initial,c,connected=helper).run();check(m,initial,c,connected=True);ms.append(m);visited.update(m.visits)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,executions=3*count,original_query_words=73,query_words_visited=sum(p in visited for p in helper),original_direct_and_linked_identity_paths=True,results_zero_one_two=True,empty_pointer_and_type_identity_filters=True,remaining_helpers_are_ABI_hooks=True,full_gameplay_claimed=False)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>19I',rom,0x4B408);ws=programs('caller');count=0
 class WindowExit(Exception):pass
 class WindowCode(faults.TrackedCode):
  def __getitem__(self,pc):
   if pc==0x1501DFA4:self.owner.current_pc=pc;raise WindowExit
   return super().__getitem__(pc)
 for slot,flag,stop,limit,drop,pattern in itertools.product((0,1),(0,1),(0,1),(1,2,3),(0,1,2),(0,2)):
  c=Case(slot=slot,flag=flag,stop=stop,exit_after=limit,drop_at=drop,pattern=pattern,effect=15);initial=fixture(c);want=dict(initial);calls=[];observations=[];latch=flag;iterations=0
  while True:
   calls.append((ENTRY,(slot,)));observations.append(observation(want,c,SYMS));want,subcalls,subobs=reference(want,c);calls.extend(subcalls);observations.extend(subobs);iterations+=1
   if not latch:break
   if read(want,STOP,1):break
   latch=read(want,FLAG,1)
  assert iterations<=3;ms=[]
  for w in ws:
   code=dict(zip(range(ENTRY,ENTRY+236,4),w));code[0x1501DFA4]=0;m=Oracle(words,initial,c,entry=0x1501DF58,connected=code,args=(0,));m.r[19]=slot;m.code=WindowCode(m.code,m)
   try:m.run()
   except WindowExit:pass
   else:raise AssertionError('Caller window did not exit')
   assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),(c,iterations);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,original_window_words=19,parent='func_1501DF04',JAL_ROM=['0x4B414','0x4B438'],both_sites_and_branch_likely_loop_executed=True,latched_flag_and_live_stop_checked=True,up_to_three_complete_refresh_invocations=True,void_result_ignored=True,full_parent_or_gameplay_claimed=False)
def controls(body):
 return dict(wrong_timestamp=body.replace('(u32)D_800C3640[slot] + (u32)D_800BEA08','(u32)D_800C3640[slot]'),wrong_setup_order=body.replace('func_150242F8(1, 0);\n    func_1501EC38(0);','func_1501EC38(0);\n    func_150242F8(1, 0);'),wrong_mode=body.replace('func_150242F8(1, 0)','func_150242F8(0, 0)'),wrong_clear_argument=body.replace('func_15020EC4(0)','func_15020EC4(1)'),wrong_start=body.replace('index = 0','index = 1'),wrong_count=body.replace('limit = 25','limit = 24'),wrong_cursor=body.replace('actor++;','actor += 0;'),wrong_active_gate=body.replace('interaction_state != 0','interaction_state > 0'),wrong_query_gate=body.replace('func_150229E4(actor) != 0','func_150229E4(actor) == 1'),wrong_index_publication=body.replace('D_800C3E78 = index','D_800C3E78 = index + 1'),wrong_apply_slot=body.replace('actor, slot, -1','actor, slot + 1, -1'),wrong_apply_flag=body.replace('actor, slot, -1','actor, slot, 0'),wrong_finish=body.replace('func_1501E81C(1, slot)','func_1501E81C(0, slot)'))
def compiled_controls():
 receipt={};corpus=[Case(effect=15,result=2),Case(effect=0,result=1),Case(pattern=7,result=1)]
 for name,body in controls(source.SELECTED).items():
  assert body!=source.SELECTED;obj,diag=source.compile_owner(r,o,source.HEADERS+body,'control-'+name);assert not diag;words=linked(obj,'control-linked-'+name)
  for i,c in enumerate(corpus):
   initial=fixture(c);m=Oracle(words,initial,c).run()
   try:check(m,initial,c)
   except AssertionError:receipt[name]=i;break
  assert name in receipt,('Ineffective control',name)
 return dict(count=len(receipt),effective_IDO_controls=receipt,compiler_or_oracle_errors_accepted=False)
def native_harness(body):
 return source.HEADERS+body+r'''
typedef char actor_stride_is_32C[sizeof(struct127)==0x32C?1:-1];
s32 D_800C3640[2],D_800C35B0[2],D_800BEA08;struct127 D_800CC2D0[25];u8 D_800C3E78;
static struct127 wantedPool[25];static s32 wantedBase[2],wantedDest[2],wantedTicks;static u8 wantedIndex;
typedef struct {struct127 *pool;s32 *base,*dest,*ticks;u8 *index;u32 mark;} Context;
typedef struct {u32 target,a,b,c,hash;} Event;
static Event events[128];static u32 eventCount,eventCursor,error,slot,pattern,resultMode,effectMode,onehot,seed;
static Context actual,wanted;
static u32 state_value(u32 i){switch(pattern){case 0:return 0;case 1:return i&1?4:27;case 2:return i&1?0xFFFFFFFFu:0;case 3:return i==0?4:0;case 4:return i==24?4:0;case 5:return i==onehot?4:0;case 6:return(i*13+seed)%3==0?4:0;default:return 0x80000000u;}}
static u32 hash(Context *x){u32 i,h=0x811C9DC5u;h=(h^(u32)x->dest[slot])*16777619u;h=(h^(u32)x->base[slot])*16777619u;h=(h^(u32)*x->ticks)*16777619u;h=(h^*x->index)*16777619u;h=(h^x->mark)*16777619u;for(i=0;i<25;i++)h=(h^(u32)x->pool[i].interaction_state)*16777619u;return h;}
static void toggle(Context*x,u32 i){if(i<25)x->pool[i].interaction_state=x->pool[i].interaction_state?0:4;}
static u32 change(Context*x,u32 t,u32 a,u32 b,u32 c){u32 i=a;(void)b;(void)c;x->mark++;
 if(effectMode&1){if(t==0&&a==1){toggle(x,0);toggle(x,24);*x->ticks=(s32)0x89ABCDEFu;x->base[slot]=0x76543210;}else if(t==1)x->pool[1].interaction_state=1;else if(t==0&&a==0)x->pool[2].interaction_state=0;else if(t==2)x->pool[3].interaction_state=(s32)0x80000000u;}
 if(t==3&&(effectMode&2)){*x->index=(u8)(0xE0+(i&31));x->pool[i].interaction_state=0;toggle(x,i+1);}
 if(t==4&&(effectMode&4)){((u8 *)&x->pool[i])[0x2FF]=0x77;*x->index=(u8)(0x80+(i&31));x->dest[slot]=(s32)((u32)x->dest[slot]^0x13579BDFu);toggle(x,i+2);}
 if(t==5&&(effectMode&8)){*x->index=0xFE;x->dest[slot]=(s32)((u32)x->dest[slot]+17u);}
 if(t==3){if(resultMode==0)return 0;if(resultMode==1)return 1;if(resultMode==2)return 0x80000000u;return i%3==0?2:0;}return 0xA5000000u|t;
}
static u32 predict_call(u32 t,u32 a,u32 b,u32 c){Event *e=&events[eventCount++];e->target=t;e->a=a;e->b=b;e->c=c;e->hash=hash(&wanted);return change(&wanted,t,a,b,c);}
static u32 actual_call(u32 t,u32 a,u32 b,u32 c){Event *e;if(eventCursor>=eventCount){error=1;return 0;}e=&events[eventCursor++];if(e->target!=t||e->a!=a||e->b!=b||e->c!=c||e->hash!=hash(&actual))error=2;return change(&actual,t,a,b,c);}
s32 func_150242F8(s32 a,s32 b){return(s32)actual_call(0,(u32)a,(u32)b,0);}
s32 func_1501EC38(s32 a){return(s32)actual_call(1,(u32)a,0,0);}
s32 func_15020EC4(s32 a){return(s32)actual_call(2,(u32)a,0,0);}
s32 func_150229E4(struct127*p){return(s32)actual_call(3,(u32)(p-D_800CC2D0),0,0);}
s32 func_1502178C(struct127*p,s32 a,s32 b){return(s32)actual_call(4,(u32)(p-D_800CC2D0),(u32)a,(u32)b);}
s32 func_1501E81C(s32 a,s32 b){return(s32)actual_call(5,(u32)a,(u32)b,0);}
static int run(void){static const u32 values[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};static const u32 effects[]={0,1,2,4,8,15};u32 n,mode,fx,i,j;u8 *a,*b;
 for(n=0;n<256;n++)for(slot=0;slot<2;slot++)for(mode=0;mode<4;mode++)for(fx=0;fx<6;fx++){
  pattern=n%8;seed=n;onehot=n%25;resultMode=mode;effectMode=effects[fx];eventCount=eventCursor=error=0;
  actual.pool=D_800CC2D0;actual.base=D_800C3640;actual.dest=D_800C35B0;actual.ticks=&D_800BEA08;actual.index=&D_800C3E78;actual.mark=0;
  wanted.pool=wantedPool;wanted.base=wantedBase;wanted.dest=wantedDest;wanted.ticks=&wantedTicks;wanted.index=&wantedIndex;wanted.mark=0;
  a=(u8*)D_800CC2D0;b=(u8*)wantedPool;for(i=0;i<sizeof(D_800CC2D0);i++)a[i]=b[i]=(u8)(i*29+n);
  for(i=0;i<25;i++)D_800CC2D0[i].interaction_state=wantedPool[i].interaction_state=(s32)state_value(i);
  for(i=0;i<2;i++){D_800C3640[i]=wantedBase[i]=(s32)values[(n+i)%5];D_800C35B0[i]=wantedDest[i]=(s32)(0xA5A50000u+n+i);}D_800BEA08=wantedTicks=(s32)values[(n/5)%5];D_800C3E78=wantedIndex=(u8)(n*13);
  wanted.dest[slot]=(s32)((u32)wanted.base[slot]+(u32)*wanted.ticks);predict_call(0,1,0,0);predict_call(1,0,0,0);predict_call(0,0,0,0);predict_call(2,0,0,0);
  for(i=0;i<25;i++)if(wantedPool[i].interaction_state){wantedIndex=(u8)i;if(predict_call(3,i,0,0))predict_call(4,i,slot,0xFFFFFFFFu);}predict_call(5,1,slot,0);
  func_1501DE18((s32)slot);if(error||eventCursor!=eventCount||hash(&actual)!=hash(&wanted))return error?error:3;
  for(i=0;i<sizeof(D_800CC2D0);i++)if(a[i]!=b[i])return 4;for(j=0;j<2;j++)if(D_800C3640[j]!=wantedBase[j]||D_800C35B0[j]!=wantedDest[j])return 5;if(D_800BEA08!=wantedTicks||D_800C3E78!=wantedIndex)return 6;
 }
 return 0;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def native_suite():
 profiles={};negative={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stderr);profiles[opt]=dict(exit=0,cases=12288,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  p=o/('native-control-'+name+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,7)and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);negative[name]=q.returncode
 return dict(cases_per_profile=12288,profiles=profiles,negative_controls=len(negative),effective_native_controls=negative,SDK32_actor_stride=804,all25_actor_positions=True,all_pool_bytes_preserved_except_helper_effects=True,call_sequence_observations_and_wrapping_timestamp=True,live_future_record_and_index_mutations=True,void_return_not_interpreted=True,portable_guest_alias_or_hardware_claimed=False)
