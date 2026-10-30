"""Actor parameter clamp, pointer rereads and bounded nontrapping FP conversion."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import floating,bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-actor-byte-clamp-150DB630-match'
F='func_150DB630';ENTRY=0x150DB630;ROM=0x108AE0;BODY=228
ACTOR,DATA,OTHER,TABLE=0x200000,0x210000,0x220000,0x80089D60
VALUES=(0,0x80000000,1,0x80000001,0x3E800000,0x3F7FFFFF,0x3F800000,0x3F800001,0x437EFFFF,0x437F0000,0x437F0001,0x43800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,0xFFC12345,0x4EFFFFFF,0x4F000000,0x4F7FFFFF,0x4F800000)
@dataclass(frozen=True)
class Case:
 value:int=0x3F800000
 second:int=0x3F800000
 switch:bool=False
 alias:int=0
 phase:int=0
 fcsr:int=0
 seed:int=0

def address(c):return (DATA,ACTOR+0x5C,STACK+c.phase-16)[c.alias]
def fixture(c):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-256,256)}
 for base,n in ((ACTOR,0x180),(DATA,32),(OTHER,32),(TABLE,64)):m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(n)})
 put(m,ACTOR+0x120,address(c));put(m,address(c),c.value);put(m,OTHER,c.second);put(m,TABLE+40,ENTRY)
 return m
def converted(v):
 if not math.isfinite(v):return 255
 n=math.trunc(v)
 return n&255 if 0<=n<2**32 else 255
def reference(initial,c):
 m=dict(initial);trace=[]
 def load(a):
  v=read(m,a);trace.append(('R',a,4,v));return v
 p=load(ACTOR+0x120);v=floating(load(p))
 if v>255.0:result=255
 else:
  if c.switch:put(m,ACTOR+0x120,OTHER)
  p=load(ACTOR+0x120);v=floating(load(p));result=0 if v<0.0 else converted(v)
 put(m,ACTOR+0x5C,result,1);trace.append(('W',ACTOR+0x5C,1,result))
 return m,trace
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,connected=None):
  self.pointer_reads=0
  super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(ACTOR,))
  self.before=self.r[:];self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr
  self.code=faults.TrackedCode(dict(self.code),self)
 def get(self,p,n):
  if self.own_instruction and p==ACTOR+0x120 and n==4:
   self.pointer_reads+=1
   if self.pointer_reads==2 and self.case.switch:put(self.memory,ACTOR+0x120,OTHER)
  return super().get(p,n)
 def execute(self,w):
  op,rs,fn=w>>26,w>>21&31,w&63
  if op==17 and(rs in (2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,w)
  else:super().execute(w)
 def record_call(self,t):
  assert t==ENTRY;self.calls.append((t,(self.r[4],)));self.events.append(('CALL',t,(self.r[4],)))
 def hook(self,t):raise AssertionError(('Unexpected external call',t))
def program(obj):
 raw,rs=payload(obj,F);assert not rs
 return list(struct.unpack('>%dI'%(len(raw)//4),raw))
def state(m):return(m.r,m.f,m.hi,m.lo,m.memory,m.events,m.calls,m.trace,m.condition,m.fcsr)
def verify(m,initial,c,trace=True):
 want,tr=reference(initial,c);assert m.memory==want,c
 assert m.r[2]==1 and m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28] and m.r[31]==m.before[31] and m.f[20:]==m.before_f[20:] and m.fcsr==c.fcsr,c
 if trace:assert m.trace==tr,(c,m.trace,tr)
def cases():
 stable=[Case(v,v,False,a,p,f,s)for v,a,p,f,s in itertools.product(VALUES,range(3),(0,8),(0,0xA5A50003),(0,7))]
 switched=[Case(v,w,True,0,p,f,0)for v,w,p,f in itertools.product((0,0x437F0000,0x7FC12345),VALUES,(0,8),(0,0xA5A50003))]
 return tuple(stable+switched)
def guest_suite():
 objs=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[program(p)for p in objs];assert ps[0]==ps[1]==ps[2] and len(ps[0])==57
 visited=set();count=0
 for c in cases():
  initial=fixture(c);ms=[]
  for ws in ps:m=Oracle(ws,initial,c);m.run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visited.update(ms[0].visits);count+=1
 dead={12,22,48};assert visited==set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+4*i for i in dead},sorted(hex(v)for v in set(range(ENTRY,ENTRY+BODY,4))-visited)
 # These duplicate compiler words follow unconditional branches; retain them too.
 for i in dead:assert ps[0][i-2]>>26 in (2,4)
 prefixes=delay=0
 for c in (Case(value=bits(300.0)),Case(value=bits(-1.0)),Case(),Case(value=0x7FC12345),Case(switch=True,second=0x4F000000),Case(switch=True,second=0x4F800000)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   ms=[]
   for ws in ps:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]) and (ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of)==(ms[2].current_pc,ms[2].delay_of)
   prefixes+=1;delay+=ms[0].delay_of is not None
 rebases=0
 for entry in (0x10007FF0,0x15008000,0x1F00FFF0):
  for v in VALUES:
   c=Case(v,v);initial=fixture(c);ms=[]
   for ws in ps:m=Oracle(ws,initial,c,entry);m.run();verify(m,initial,c);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebases+=1
 return dict(cases=count,executions=count*3,covered_words=54,compiler_words=57,unreachable_indices=sorted(dead),frame=0,guards=0,bindings=0,prefix_cases=prefixes,delay_cuts=delay,rebase_cases=rebases,pointer_switch_cases=sum(c.switch for c in cases()),guest_alias_cases=sum(c.alias!=0 for c in cases()),all_RAM_and_access_order_checked=True,FCSR='bounded nontrapping model; no hardware exception claim',private_only=True,matching_credit=0)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22E848)[0]==ENTRY
 assert [i for i in range(0,len(rom)-3,4)if rom[i:i+4]==struct.pack('>I',ENTRY)]==[0x22E848]
 assert not any(rom[i:i+4]==struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF))for i in range(0,len(rom)-3,4))
 ws=struct.unpack_from('>13I',rom,0x16A524);assert ws[7:9]==(0x0320F809,0);count=0
 for v,selector,gate,phase in itertools.product(VALUES,(0,10),(0,1,255),(0,8)):
  c=Case(v,v,phase=phase);initial=fixture(c);sp=STACK+phase;want,_=reference(initial,c)
  if selector:put(want,sp+32,ACTOR);put(want,sp+27,gate,1)
  else:want=dict(initial)
  ms=[]
  for obj in (o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'):
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),program(obj)));code[0x1513D0A8]=0;m=Oracle(ws,initial,c,entry=0x1513D074,connected=code);m.r[2]=selector;m.r[7]=gate;m.code=WindowCode(m.code,m);m.code.ends=(0x1513D0A8,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller window boundary')
   assert m.memory==want and m.r[4]==ACTOR and m.r[7]==(((gate^128)-128)&0xFFFFFFFF if selector else gate) and m.fcsr==c.fcsr,(c,selector,gate,hex(m.r[7]),[(hex(a),m.memory.get(a),want.get(a))for a in set(m.memory)|set(want)if m.memory.get(a)!=want.get(a)][:20])
   assert m.calls==([(ENTRY,(ACTOR,))]if selector else [])
   assert m.r[29]==sp and m.r[16:24]==m.before[16:24];ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,table='D_80089D60',index=10,table_ROM='0x22E848',entry='0x1513D074',words=13,skipped_selector_and_success_return_checked=True,full_parent_claimed=False)
def controls(body):
 return dict(missing_pointer_reload=body.replace('f32 * volatile *','f32 **'),wrong_pointer=body.replace('actor + 0x120','actor + 0x124'),wrong_byte=body.replace('actor[0x5C]','actor[0x5D]'),wrong_high=body.replace('255.0f','254.0f'),wrong_high_result=body.replace('= 255;','= 254;'),wrong_low=body.replace('value < 0.0f','value < 128.0f'),wrong_low_result=body.replace('= 0;','= 1;'),wrong_cast=body.replace('(u32)value','((u32)value & 0x7F)'),wrong_return=body.replace('return 1;','return 0;'))
def compiled_controls():
 selected=(o/'selected-semantic-input.c').read_text();ws=program(o/('original-'+F+'.o'));rows=[]
 for label,text in controls(selected).items():
  assert text!=selected;obj,diag=compile_owner(r,o,text,'negative-'+label);assert not diag;bad=program(obj);failed=None
  for c in cases():
   initial=fixture(c);put(initial,ACTOR+0x124,OTHER)
   good=Oracle(ws,initial,c);good.run();verify(good,initial,c)
   m=Oracle(bad,initial,c);m.run()
   if m.memory!=good.memory or m.r[2]!=good.r[2]:failed=c;break
  assert failed is not None,('Ineffective semantic control',label);rows.append(label)
 return dict(count=len(rows),controls=rows,compiler_or_oracle_errors_accepted=False)
def native_suite():
 selected=(o/'selected-semantic-input.c').read_text();head,body=selected.split('/* Clamp',1);body='/* Clamp'+body
 rows=[]
 for v,alias,seed in itertools.product(VALUES,(0,1),(0,7)):
  value=floating(v)
  if not math.isfinite(value):continue
  rows.append((v,alias,seed,255 if value>255 else 0 if value<0 else math.trunc(value)))
 # Exercise every byte and both sides of every integer boundary.
 for n in range(256):
  base=bits(float(n))
  for v in (base,max(0,base-1),base+1):
   value=floating(v);rows.append((v,0,n&7,255 if value>255 else math.trunc(value)))
 text=head+'\n_Static_assert(sizeof(void*)==4,"native32");\nstatic u8 actor[0x180] __attribute__((aligned(16)));static f32 parameter;\n'
 bad=controls(body);text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items())
 text+='\nstatic const u32 fixtures[][4]={\n'+',\n'.join('{%su,%su,%su,%su}'%v for v in rows)+'\n};\n'
 text+='''
typedef s32(*Update)(u8*);
static s32 check(Update fn){u32 n,i;u8 expected[0x180];u32*out;for(n=0;n<sizeof(fixtures)/sizeof(fixtures[0]);n++){
for(i=0;i<sizeof(actor);i++)actor[i]=expected[i]=(u8)(i*29+fixtures[n][2]*11+0x59);
out=fixtures[n][1]?(u32*)(actor+0x5C):(u32*)&parameter;*out=fixtures[n][0];*(f32**)(actor+0x120)=(f32*)out;*(f32**)(actor+0x124)=&parameter;
for(i=0;i<sizeof(actor);i++)expected[i]=actor[i];expected[0x5C]=(u8)fixtures[n][3];
if(fn(actor)!=1)return 1;for(i=0;i<sizeof(actor);i++)if(actor[i]!=expected[i])return 2;
if(!fixtures[n][1]&&*(u32*)&parameter!=fixtures[n][0])return 3;
}return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 # A wrong pointer is a guest-only control: native intentionally separate backing may coincide.
 native_bad=[k for k in bad if k not in ('wrong_pointer','missing_pointer_reload')]
 for i,k in enumerate(native_bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native.c';p.write_text(text);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=o/('native'+opt);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);reports[opt]=dict(exit=0,cases=len(rows),UBSan=True,semantic_controls=len(native_bad))
 return dict(profiles=reports,cases=len(rows),semantic_controls=len(native_bad),all_actor_bytes_checked=True,nonfinite_and_pointer_switch_guest_only=True)
