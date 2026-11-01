"""Selected actor health command, live aliases and original script dispatch window."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_selected_actor_health_match as source
r=o=None
ENTRY,CHANGE,EFFECT=0x150746F0,0x1507CD64,0x1517F488
A,STATE,CAMERA,MARK=0x90000,0xB0000,0xC0000,0xD0000
@dataclass(frozen=True)
class Case:
 flag:int=1
 linked:int=0
 health:int=127
 amount:int=1
 state:int=1
 available:int=4
 mutation:int=0
 alias:int=0
 phase:int=0

AVAILABLE=((0,0,0),(1,0,1),(0,1,1),(1,1,0),(1,1,1))
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def symbols(index=0):
 if not index:return dict(D_800BE616=0x800BE616,D_800D154C=0x800D154C,D_800D1580=0x800D1580,D_800CC2D0=0x800CC2D0,func_1507CD64=CHANGE,func_1517F488=EFFECT)
 base=(0x02337FFC,0x0343FFFC)[index-1]
 return dict(D_800BE616=base,D_800D154C=base+0x8004,D_800D1580=base+0x10004,D_800CC2D0=base+0x18004,func_1507CD64=CHANGE,func_1517F488=EFFECT)

def fixture(c,s):
 s=dict(s);actor=0x91230 if c.alias==3 else A;pool=s['D_800CC2D0']
 if c.alias==2:s['D_800D1580']=actor+0x1C8
 if c.alias==3:s['D_800D154C']=actor+0x1C8
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)}
 for base,n in ((actor,0x330),(pool,0x330),(STATE,0x1C0),(CAMERA,0x300),(MARK,16),(0x90030,0x330)):
  m.update({base+i:0xA5 for i in range(n)})
 has_state,has_camera,enabled=AVAILABLE[c.available]
 for at in (actor,pool):
  put(m,at,c.state&0xFFFFFFFF);m[at+0x13C]=c.linked&255;m[at+0x1CA]=c.health&255;m[at+0x125]=0x34 if at==actor else 0x45
  put(m,at+0x31C,STATE if has_state else 0);put(m,at+0x318,CAMERA if has_camera else 0)
 m[STATE+0x197]=enabled;m[CAMERA+0x23D]=(c.health^0xA5)&255
 m[s['D_800BE616']]=c.flag&255;put(m,s['D_800D154C'],pool if c.alias==1 else actor);put(m,s['D_800D1580'],c.amount&0xFFFFFFFF);put(m,MARK,0)
 return m,s

def effect(m,c,s,selected):
 put(m,MARK,0x13579BDF)
 if c.mutation:
  current=read(m,s['D_800D154C']);put(m,s['D_800D154C'],s['D_800CC2D0'] if current==A else A)
  put(m,s['D_800D1580'],0x80000000)

def reference(initial,c,s):
 m=dict(initial);calls=[];selected=0
 if m[s['D_800BE616']]:selected=read(m,s['D_800D154C'])
 elif m[read(m,s['D_800D154C'])+0x13C]:selected=s['D_800CC2D0']
 if selected:
  amount=signed(read(m,s['D_800D1580']));health=m[selected+0x1CA]
  if amount>=health:
   m[selected+0x1CA]=0;m[read(m,s['D_800D154C'])+0x1CA]=0
   if read(m,selected)==1:
    m[selected+0x125]=255;calls.append((s['func_1507CD64'],(selected,6)));effect(m,c,s,selected)
  else:
   state=read(m,selected+0x31C);m[selected+0x1CA]=(health-amount)&255
   if state:
    camera=read(m,selected+0x318)
    if camera and m[state+0x197]:
     calls.append((s['func_1517F488'],(255,0,0,180,20,m[camera+0x23D])));effect(m,c,s,selected)
 return m,calls

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None,poison=0xDEADBEEF):
  self.c,self.s,self.poison=c,s,poison
  super().__init__(words,memory,c,entry=entry,s={},arguments=(0x156,0xABCD0001,0x87654321,0xA5A55A5A),connected=connected)
  self.before_f=self.f[:]
 def record_call(self,t):
  counts={ENTRY:0,self.s['func_1507CD64']:2,self.s['func_1517F488']:6};assert t in counts,hex(t)
  self.calls.append((t,tuple(self.arguments(counts[t]))))
 def hook(self,t):
  assert t in (self.s['func_1507CD64'],self.s['func_1517F488'])
  initial=self.entry_memory
  selected=read(initial,self.s['D_800D154C'])if initial[self.s['D_800BE616']]else self.s['D_800CC2D0']
  effect(self.memory,self.c,self.s,selected)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=self.poison;self.f[:20]=[0xA5000000+i for i in range(20)]
  self.hi,self.lo=0xA5000010,0xA5000011

def corpus():
 for flag,linked,health,amount,state,available in itertools.product((0,1,128),(0,1),(0,1,127,255),(-0x80000000,-1,0,1,127,255,256,0x7FFFFFFF),(0,1),range(5)):
  yield Case(flag,linked,health,amount,state,available,(health+available)&1,0,8 if flag==128 else 0)
 for flag in range(256):yield Case(flag,1,128,1,1,4,flag&1,flag&1)
 for alias,amount in itertools.product((2,3),(-0x80000000,0,18,255)):
  yield Case(1,0,18,amount,1,4,0,alias)

def public(m):return{a:v for a,v in m.items()if not STACK-128<=a<STACK+256}
def compare(programs,c,s,entry):
 initial,s=fixture(c,s);expected,calls=reference(initial,c,s);models=[]
 for program in programs:
  m=Oracle(program,initial,c,s,entry);m.entry_memory=initial;m.run()
  assert public(m.memory)==public(expected)and m.calls==calls,(c,'public state/calls')
  assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
  models.append(m)
 for m in models[1:]:assert (m.memory,m.r,m.f,m.trace,m.visits)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].visits)
 return models[0]

def guest():
 paths=('original-func_150746F0.o','selected-final.o','qualified-padded.o','make-shadow/src/game_981E0.c.o');count=0;seen=set();retail=None
 for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
  s=symbols(index);programs=[link(o/name,'health-program-%d-%d'%(index,i),entry,s)for i,name in enumerate(paths)];assert all(p==programs[0]for p in programs)
  for c in corpus():
   if c.alias in(2,3):
    _,adjusted=fixture(c,s);alt=[link(o/name,'health-alias-%d-%d-%d-%d'%(index,c.alias,c.amount&0xFFFFFFFF,i),entry,adjusted)for i,name in enumerate(paths)]
   else:alt=programs
   m=compare(alt,c,s,entry);seen.update(pc-entry for pc in m.visits);count+=1
  if index==0:retail=programs
 assert set(range(0,244,4))-seen=={0x98},set(range(0,244,4))-seen
 return dict(cases=count,executions=count*4,programs=4,body_words=61,frame=32,rebases=3,all_60_reachable_words_executed=True,unreachable_duplicate_state_load=0x98,all_256_selector_bytes=True,live_health_amount_and_current_pointer_aliases=True,all_machine_states_and_traces_equal=True),retail

class ReturnPoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1506AEC8:
   self.owner.r[2]=self.owner.poison;self.owner.return_poisons+=1
  return super().__getitem__(pc)

def callers(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();s=symbols();start,end=0x1506AEB0,0x1506AEFC
 body=list(struct.unpack_from('>19I',rom,0x98360));assert int.from_bytes(rom[0x22B12C:0x22B130],'big')==ENTRY
 count=0
 for flag,health,amount,available,mutation,changed in itertools.product((0,1),(0,127),(0,1,255),range(5),(0,1),(0,1)):
  c=Case(flag,1,health,amount,1,available,mutation)
  initial,s=fixture(c,s);record=0xE0000;put(initial,A+0x2D0,record);put(initial,record+0x28,0xE1000);put(initial,A+0x1C4,0xE2000);put(initial,record+8,0x3F800000);initial[A+0x138]=7
  put(initial,0x8008666C,ENTRY);expected,calls=reference(initial,c,s)
  if not changed:expected[A+0x138]=8
  for program,poison in itertools.product(programs,(0,1,0x80000000,0xFFFFFFFF)):
   code=dict(zip(range(ENTRY,ENTRY+244,4),program));code[end]=0
   m=Oracle(body,initial,c,s,start,code,poison);m.entry_memory=initial;m.r[4]=156;m.r[30]=0x800863FC;m.r[17]=A;m.r[18]=0xE1000+changed
   m.return_poisons=0;m.code=ReturnPoisonCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original dispatch boundary not reached')
   assert public(m.memory)==public(expected)and m.calls==[(ENTRY,())]+calls,(c,changed,m.calls,calls,[(hex(a),m.memory.get(a),v)for a,v in expected.items()if not STACK-128<=a<STACK+256 and m.memory.get(a)!=v][:12])
   assert m.return_poisons==1
   assert m.r[2]==0xE2000,'Dispatcher consumed callback return value'
  count+=1
 census=json.loads((o/'caller-census.json').read_text());assert not census['aligned_ROM_JALs']and census['slot']==156 and census['aligned_ROM_pointer_literals']==[0x22B12C]
 return dict(cases=count,executions=count*16,original_dispatch_window_words=19,callback_slot=156,return_poisons=4,callback_return_ignored=True,full_dispatcher_reachability_claimed=False,only_pointer_literal_qualified=True)

def controls():
 return (
 ('selector-inverted','D_800BE616 != 0','D_800BE616 == 0'),
 ('wrong-boundary','actor->health <= D_800D1580','actor->health < D_800D1580'),
 ('unsigned-amount','actor->health <= D_800D1580','actor->health <= (u32)D_800D1580'),
 ('missing-current-clear','D_800D154C->health = 0;','/* missing current clear */'),
 ('wrong-effect-flag','[0x197]','[0x196]'),
 ('wrong-effect-argument','0xB4, 0x14','0xB4, 0x15'))

def digest(m,calls,s):
 h=2166136261
 def mix(v):
  nonlocal h
  h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 mix(m[s['D_800BE616']]);mix(read(m,s['D_800D1580']));mix(read(m,s['D_800D154C'])==s['D_800CC2D0'])
 for actor in (A,s['D_800CC2D0']):
  mix(read(m,actor))
  for i in range(4,812):
   if not 0x318<=i<0x320:mix(m[actor+i])
 mix(m[STATE+0x197]);mix(m[CAMERA+0x23D]);mix(read(m,MARK));mix(len(calls))
 for target,args in calls:
  mix(target==s['func_1517F488'])
  for i,v in enumerate(args):mix(v==s['D_800CC2D0']if target==s['func_1507CD64']and i==0 else v)
 return h

def native():
 bodies=[source.SELECTED]
 for name,old,new in controls():assert old in source.SELECTED;bodies.append(source.SELECTED.replace(old,new))
 code=source.HEADERS+'\n'.join(body.replace('func_150746F0','candidate_'+str(i))for i,body in enumerate(bodies))
 code+='''
u8 D_800BE616;struct127 *D_800D154C;struct127 D_800CC2D0[26];s32 D_800D1580;
static struct127 actor;static struct126 state;static struct108 camera;
static u32 mutation,mark,count,call_log[6],tag;static struct127 *selected;
typedef char ActorSize[sizeof(struct127)==812?1:-1];
typedef char HealthOffset[__builtin_offsetof(struct127,health)==0x1CA?1:-1];
typedef char CameraOffset[__builtin_offsetof(struct127,camera)==0x318?1:-1];
typedef char CameraByteOffset[__builtin_offsetof(struct108,unk23D)==0x23D?1:-1];
static void effect(void){mark=0x13579BDFu;if(mutation){D_800D154C=D_800D154C==&actor?D_800CC2D0:&actor;D_800D1580=(s32)0x80000000u;}}
s32 func_1507CD64(struct127 *p,s32 n){tag=0;count++;call_log[0]=p==D_800CC2D0;call_log[1]=n;effect();return (s32)0xDEADBEEFu;}
void func_1517F488(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f){tag=1;count++;call_log[0]=a;call_log[1]=b;call_log[2]=c;call_log[3]=d;call_log[4]=e;call_log[5]=f;effect();}
typedef struct {u32 flag,linked,health,amount,state,available,mutation,alias,expected;} Test;
static const Test tests[]={
'''
 rows=[]
 for c in corpus():
  if c.alias>=2:continue
  initial,s=fixture(c,symbols());expected,calls=reference(initial,c,s)
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in (c.flag,c.linked,c.health,c.amount,c.state,c.available,c.mutation,c.alias,digest(expected,calls,s)))+'}')
 code+=',\n'.join(rows)+'''};
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 result(void){u32 h=2166136261u,i,j;u8 *p;h=mix(h,D_800BE616);h=mix(h,(u32)D_800D1580);h=mix(h,D_800D154C==D_800CC2D0);
 for(j=0;j<2;j++){p=(u8*)(j?D_800CC2D0:&actor);h=mix(h,(u32)(j?D_800CC2D0:&actor)->interaction_state);for(i=4;i<812;i++)if(i<0x318||i>=0x320)h=mix(h,p[i]);}
 h=mix(h,((u8*)&state)[0x197]);h=mix(h,camera.unk23D);h=mix(h,mark);h=mix(h,count);
 if(count){h=mix(h,tag);for(i=0;i<(tag?6u:2u);i++)h=mix(h,call_log[i]);}return h;}
static void reset(const Test *t){u32 i,j;u8 *p;struct127 *obj;
 for(j=0;j<2;j++){obj=j?D_800CC2D0:&actor;p=(u8*)obj;for(i=0;i<812;i++)p[i]=0xA5;obj->interaction_state=t->state;obj->unk13C=t->linked;obj->health=t->health;obj->immune=j?0x45:0x34;obj->unk31C=(t->available==1||t->available>=3)?&state:0;obj->camera=t->available>=2?&camera:0;}
 p=(u8*)&state;for(i=0;i<sizeof(state);i++)p[i]=0xA5;p[0x197]=t->available==3||t->available==0?0:1;
 p=(u8*)&camera;for(i=0;i<sizeof(camera);i++)p[i]=0xA5;camera.unk23D=t->health^0xA5;
 D_800BE616=t->flag;D_800D154C=t->alias?D_800CC2D0:&actor;D_800D1580=t->amount;mutation=t->mutation;mark=count=0;
 selected=D_800BE616?D_800D154C:(D_800D154C->unk13C?D_800CC2D0:0);}
static int run(void){u32 i,j,killed=0,h;
 for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<7;j++){reset(&tests[i]);switch(j){case 0:candidate_0();break;case 1:candidate_1();break;case 2:candidate_2();break;case 3:candidate_3();break;case 4:candidate_4();break;case 5:candidate_5();break;default:candidate_6();break;}h=result();if(h!=tests[i].expected){if(!j)return 10;killed|=1u<<(j-1);}}
 return killed==63?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-selected-health.c';path.write_text(code);reports=[]
 for profile in('-O0','-O2','-O3'):
  exe=o/('native-selected-health'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-selected-health'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,extreme_negative_amount_defined=True,controls=[n for n,_,_ in controls()],all_controls_effective=True))
 return reports

def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,programs=guest();report=dict(guest=g,callers=callers(programs),native=native(),helper_providers_explicit=True)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def link(obj,label,entry,s,words=61):
 text,functions,bindings=parse_object(obj);asm,unknown=emit_function(text,functions['func_150746F0'],bindings,'func_150746F0',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(name,value)for name,value in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_150746F0','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:words*4];return list(struct.unpack('>%dI'%words,data))
