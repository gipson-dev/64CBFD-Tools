"""Height gates, signed remainder, separate binary32 operations and original RNG."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess,math
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.experiments import game_height_gated_velocity_match as source
r=o=None
ENTRY,RNG,SEED=0x1506BCC8,0x151EF610,0x80091970
ACTORS=(0x90000,0xA0000,0x3F800000)
SPEEDS=(0,0x80000000,0x42200000,0xC2200000,0x40400000,0x3DCCCCCD,0x7F800000,0x7FC12345,1)
PAIRS=((0,0),(0x80000000,0),(0x3FA00000,0x3FA00000),(0x3F800000,0x3F800001),(0x409FFFFF,0),(0x40A00000,0),(0x40A00001,0),(0xC09FFFFF,0),(0xC0A00000,0),(0xC0A00001,0),(0x7FC12345,0),(0x7F800000,0),(0x7F800000,0x7F800000),(0x4B800000,0x4B800002))
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def norm(v):return 0x7FC00000 if v&0x7F800000==0x7F800000 and v&0x7FFFFF else v
def next_seed(v):
 x=(v*4)&0xFFFFFFFF
 return(((x+2)&0xFFFFFFFF)*((x+3)&0xFFFFFFFF)&0xFFFFFFFF)>>2
@dataclass(frozen=True)
class Case:
 state:int=22
 y:int=0
 height:int=0
 speed:int=0x42200000
 step:int=17
 random:int=0
 mutation:int=0
 seed:int=1
 connected:bool=False
 alias:bool=False
 phase:int=0

def symbols(index=0):
 b=(0x800D154C,0x02337FFC,0x0343FFFC)[index]
 return dict(D_800D154C=b,D_800D1580=0x800D1580 if not index else b+0x8004,func_151EF610=RNG,D_80091970=SEED)
def fixture(c,s):
 s=dict(s)
 if c.alias:s['D_800D154C']=ACTORS[0]+0x20
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)}
 for j,a in enumerate(ACTORS):
  m.update({a+i:0xA5 for i in range(812)})
  for at,value in((0,c.state if j==0 else 0),(0x18,c.y if j==0 else 0x42140000),(0x180,c.height if j==0 else 0xC2200000),(0x3C,c.speed if j<2 else 0x42A00000),(0x20,0xC0E00000 if j<2 else 0x40000000)):put(m,a+at,value&0xFFFFFFFF)
 put(m,s['D_800D154C'],ACTORS[0]);put(m,s['D_800D1580'],c.step&0xFFFFFFFF);put(m,SEED,c.seed&0xFFFFFFFF)
 return m,s
def observation(m,s):
 a=read(m,s['D_800D154C'])
 return(ACTORS.index(a),read(m,s['D_800D1580']),read(m,SEED),*(norm(read(m,a+i))for i in(0x18,0x180,0x20,0x3C)))
def service(m,c,s):
 if c.connected:
  answer=next_seed(read(m,SEED));put(m,SEED,answer);return answer
 if c.mutation&1:put(m,s['D_800D154C'],ACTORS[1]);put(m,s['D_800D1580'],0x7FFFFFFF)
 if c.mutation&2:put(m,ACTORS[1]+0x3C,0x40400000)
 return c.random&0xFFFFFFFF
def reference(initial,c,s):
 m=dict(initial);calls=[];observations=[];a=read(m,s['D_800D154C']);y=floating(read(m,a+0x18));height=floating(read(m,a+0x180))
 if read(m,a)==22:
  if y==height:
   calls.append((RNG,()));observations.append(observation(m,s));random=signed(service(m,c,s));jitter=(abs(random)%8)*(-1 if random<0 else 1)
   value=signed((read(m,s['D_800D1580'])+jitter)&0xFFFFFFFF);a=read(m,s['D_800D154C']);put(m,a+0x20,bits(float(value)))
   a=read(m,s['D_800D154C']);speed=floating(read(m,a+0x3C))
   if speed!=0.0:
    ratio=floating(bits(speed/40.0));put(m,a+0x20,bits(floating(read(m,a+0x20))*ratio))
   else:put(m,a+0x20,0)
 else:
  difference=floating(bits(y-height))
  if -5.0<difference<5.0:put(m,a+0x20,bits(float(signed(read(m,s['D_800D1580'])))))
 return m,calls,observations
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None):
  self.c,self.s,self.observations=c,s,[]
  super().__init__(words,memory,c,entry=entry,s={},arguments=(2,0xA5A50001,0x87654321),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(ENTRY,RNG),hex(t);self.calls.append((t,()))
  if t==RNG:self.observations.append(observation(self.memory,self.s))
 def hook(self,t):
  assert t==RNG;answer=service(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=answer;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def corpus():
 for speed,random,step,mutation in itertools.product(SPEEDS,(0,1,7,-1,-7,-8,-9,-0x80000000,0x7FFFFFFF),(-0x80000000,-17,0,17,0x7FFFFFFF),(0,3)):
  yield Case(speed=speed,random=random,step=step,mutation=mutation,phase=8 if random<0 else 0)
 for state,pair,step in itertools.product((0,23,0xFFFFFFFF),PAIRS,(-0x80000000,-17,0,17,0x7FFFFFFF)):
  yield Case(state,*pair,step=step)
 for pair,speed,random in itertools.product(PAIRS,SPEEDS,(0,-9)):
  yield Case(22,*pair,speed,17,random,1)
 for seed,speed,step in itertools.product((0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678,0x80000001),(0,0x40400000,0x7FC12345),(-17,0x7FFFFFFF)):
  yield Case(speed=speed,step=step,seed=seed,connected=True)
 yield Case(step=1,random=0,alias=True)
def helper_code():
 rom=(r/'conker/conker.us.bin').read_bytes()
 return dict(zip(range(RNG,RNG+44,4),struct.unpack_from('>11I',rom,0x21CAC0)))
def public(m):
 result={a:v for a,v in m.items()if not STACK-128<=a<STACK+256}
 for a in ACTORS:put(result,a+0x20,norm(read(result,a+0x20)))
 return result
def compare(programs,c,s,entry=ENTRY):
 initial,s=fixture(c,s);expected,calls,observations=reference(initial,c,s);models=[]
 for program in programs:
  m=Oracle(program,initial,c,s,entry,helper_code()if c.connected else None).run()
  assert public(m.memory)==public(expected)and m.calls==calls and m.observations==observations,(c,'public state/calls')
  assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 for m in models[1:]:assert(m.memory,m.r,m.f,m.trace,m.visits)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].visits)
 return models[0]
def guest():
 paths=('original-func_1506BCC8.o','selected-final.o','qualified-padded.o','make-shadow/src/game_981E0.c.o');count=connected=0;seen=set();helper_seen=set();retail=None
 for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
  s=symbols(index);programs=[link(o/n,'velocity-program-%d-%d'%(index,i),entry,s)for i,n in enumerate(paths)];assert all(p==programs[0]for p in programs)
  for c in corpus():
   if c.alias:
    _,adjusted=fixture(c,s);alt=[link(o/n,'velocity-alias-%d-%d'%(index,i),entry,adjusted)for i,n in enumerate(paths)]
   else:alt=programs
   m=compare(alt,c,s,entry);seen.update(pc-entry for pc in m.visits);count+=1
   if c.connected:connected+=1;helper_seen.update(pc-RNG for pc in m.visits if RNG<=pc<RNG+44)
  if not index:retail=programs
 assert set(range(0,288,4))-seen=={0xBC},set(range(0,288,4))-seen
 assert helper_seen==set(range(0,44,4))
 return dict(cases=count,executions=count*4,body_words=72,frame=24,rebases=3,all_71_reachable_words_executed=True,unreachable_duplicate_height_load=0xBC,original_rng_words=11,connected_cases=connected,connected_executions=connected*4,all_original_rng_words_executed=True,NaNs_compared_by_class=True,hardware_FCSR_claimed=False,all_machine_states_and_traces_equal=True),retail
class ReturnPoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1506AEC8:self.owner.r[2]=self.owner.poison;self.owner.return_poisons+=1
  return super().__getitem__(pc)
def callers(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();s=symbols();body=struct.unpack_from('>19I',rom,0x98360);end=0x1506AEFC;count=0
 for state,pair,speed,random,mutation,changed in itertools.product((0,22),(PAIRS[0],PAIRS[5],PAIRS[7]),(0,0x40400000),(0,-9),(0,3),(0,1)):
  c=Case(state,*pair,speed,17,random,mutation);initial,s=fixture(c,s);record=0xE0000;put(initial,ACTORS[0]+0x2D0,record);put(initial,record+0x28,0xE1000);put(initial,ACTORS[0]+0x1C4,0xE2000);put(initial,record+8,0x3F800000);initial[ACTORS[0]+0x138]=7;put(initial,0x80086404,ENTRY)
  expected,calls,observations=reference(initial,c,s)
  if not changed:expected[ACTORS[0]+0x138]=8
  for program,poison in itertools.product(programs,(0,1,0x80000000,0xFFFFFFFF)):
   code=dict(zip(range(ENTRY,ENTRY+288,4),program));code[end]=0;m=Oracle(body,initial,c,s,0x1506AEB0,code);m.r[4]=2;m.r[30]=0x800863FC;m.r[17]=ACTORS[0];m.r[18]=0xE1000+changed;m.poison=poison;m.return_poisons=0
   m.code=ReturnPoisonCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original dispatch boundary not reached')
   assert public(m.memory)==public(expected)and m.calls==[(ENTRY,())]+calls and m.observations==observations
   assert m.return_poisons==1 and m.r[2]==0xE2000
  count+=1
 census=json.loads((o/'caller-census.json').read_text());assert census['slot']==2 and census['aligned_ROM_pointer_literals']==[0x22AEC4]and not census['aligned_ROM_JALs']
 return dict(cases=count,executions=count*16,original_window_words=19,callback_slot=2,return_poisons=4,return_ignored=True,full_dispatcher_reachability_claimed=False)
def cached_body():
 return source.SELECTED.replace('void func_1506BCC8(void) {','void func_1506BCC8(void) {\n    struct127 *actor = D_800D154C;').replace('D_800D154C->','actor->')
def controls():
 return (
 ('wrong-state',source.SELECTED.replace('interaction_state == 0x16','interaction_state == 0x17')),
 ('wrong-height-gate',source.SELECTED.replace('y_position == D_800D154C->unk180','y_position != D_800D154C->unk180')),
 ('unsigned-remainder',source.SELECTED.replace('func_151EF610() % 8','(u32)func_151EF610() % 8')),
 ('inclusive-near-boundary',source.SELECTED.replace('-5.0f < heightDifference','-5.0f <= heightDifference')),
 ('wrong-zero-speed',source.SELECTED.replace('xz_velocity != 0.0f','xz_velocity == 0.0f')),
 ('cached-actor',cached_body()),
 ('reassociated-float',source.SELECTED.replace('D_800D154C->y_velocity *= D_800D154C->xz_velocity / 40.0f;','D_800D154C->y_velocity = (D_800D154C->y_velocity * D_800D154C->xz_velocity) / 40.0f;')))
def digest(m,calls,observations,s):
 h=2166136261
 def mix(v):
  nonlocal h
  h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 mix(ACTORS.index(read(m,s['D_800D154C'])));mix(read(m,s['D_800D1580']));mix(read(m,SEED))
 for a in ACTORS:
  mix(read(m,a))
  for at in(0x18,0x180,0x20,0x3C):mix(norm(read(m,a+at)))
  for i in range(4,812):
   if not any(at<=i<at+4 for at in(0x18,0x180,0x20,0x3C)):mix(m[a+i])
 mix(len(calls))
 for row in observations:
  for v in row:mix(v)
 return h
def native():
 bodies=[source.SELECTED]+[b for _,b in controls()];assert all(b!=source.SELECTED for b in bodies[1:])
 code=source.HEADERS+'\n'.join(b.replace('func_1506BCC8','candidate_'+str(i))for i,b in enumerate(bodies))
 code+='''
struct127 *D_800D154C; s32 D_800D1580;
static struct127 actors[3];static u32 random_value,mutation,seed,connected,calls,observations[7];
static f32 single(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;if((v.u&0x7F800000u)==0x7F800000u&&(v.u&0x7FFFFFu))return 0x7FC00000u;return v.u;}
s32 func_151EF610(void){struct127*a=D_800D154C;u32 x;calls++;observations[0]=a-actors;observations[1]=D_800D1580;observations[2]=seed;observations[3]=word(a->y_position);observations[4]=word(a->unk180);observations[5]=word(a->y_velocity);observations[6]=word(a->xz_velocity);
 if(connected){x=seed*4u;seed=((x+2u)*(x+3u))>>2;return(s32)seed;}
 if(mutation&1){D_800D154C=&actors[1];D_800D1580=(s32)0x7FFFFFFFu;}if(mutation&2)actors[1].xz_velocity=3.0f;return(s32)random_value;}
typedef char ActorSize[sizeof(struct127)==812?1:-1];
typedef char HeightOffset[__builtin_offsetof(struct127,unk180)==0x180?1:-1];
typedef char YOffset[__builtin_offsetof(struct127,y_position)==0x18?1:-1];
typedef char VelocityOffset[__builtin_offsetof(struct127,y_velocity)==0x20?1:-1];
typedef struct{u32 state,y,height,speed,step,random,mutation,seed,connected,expected;}Test;
static const Test tests[]={
'''
 rows=[]
 for c in corpus():
  if c.alias:continue
  s=symbols();initial,s=fixture(c,s);expected,calls,observations=reference(initial,c,s)
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in(c.state,c.y,c.height,c.speed,c.step,c.random,c.mutation,c.seed,c.connected,digest(expected,calls,observations,s)))+'}')
 code+=',\n'.join(rows)+'''};
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 result(void){u32 h=2166136261u,i,j;u8*p;h=mix(h,D_800D154C-actors);h=mix(h,D_800D1580);h=mix(h,seed);
 for(j=0;j<3;j++){h=mix(h,actors[j].interaction_state);h=mix(h,word(actors[j].y_position));h=mix(h,word(actors[j].unk180));h=mix(h,word(actors[j].y_velocity));h=mix(h,word(actors[j].xz_velocity));p=(u8*)&actors[j];for(i=4;i<812;i++)if((i<0x18||i>=0x1C)&&(i<0x180||i>=0x184)&&(i<0x20||i>=0x24)&&(i<0x3C||i>=0x40))h=mix(h,p[i]);}
 h=mix(h,calls);if(calls)for(i=0;i<7;i++)h=mix(h,observations[i]);return h;}
static void reset(const Test*t){u32 i,j;u8*p;for(j=0;j<3;j++){p=(u8*)&actors[j];for(i=0;i<812;i++)p[i]=0xA5;actors[j].interaction_state=j?0:t->state;actors[j].y_position=single(j?0x42140000u:t->y);actors[j].unk180=single(j?0xC2200000u:t->height);actors[j].xz_velocity=single(j<2?t->speed:0x42A00000u);actors[j].y_velocity=single(j<2?0xC0E00000u:0x40000000u);}
 D_800D154C=&actors[0];D_800D1580=t->step;random_value=t->random;mutation=t->mutation;seed=t->seed;connected=t->connected;calls=0;}
static int run(void){u32 i,j,killed=0,h;for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<8;j++){reset(&tests[i]);switch(j){case 0:candidate_0();break;case 1:candidate_1();break;case 2:candidate_2();break;case 3:candidate_3();break;case 4:candidate_4();break;case 5:candidate_5();break;case 6:candidate_6();break;default:candidate_7();break;}h=result();if(h!=tests[i].expected){if(!j)return 10;killed|=1u<<(j-1);}}return killed==127?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-height-velocity.c';path.write_text(code);reports=[]
 for profile in('-O0','-O2','-O3'):
  exe=o/('native-height-velocity'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-height-velocity'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,wrapping_addition_defined=True,NaNs_by_class=True,controls=[n for n,_ in controls()],all_controls_effective=True))
 return reports
def guest_control():
 obj,diag=compile_owner(r,o,source.HEADERS+cached_body(),'public-cached-actor-control');assert not diag
 if(o/'cached-actor-negative.o').exists():assert source.payload(obj)==source.payload(o/'cached-actor-negative.o')
 raw,_=source.payload(obj);c=Case(step=1,alias=True);initial,s=fixture(c,symbols());program=link(obj,'cached-actor-control-linked',ENTRY,s,len(raw)//4);expected,calls,observations=reference(initial,c,s);m=Oracle(program,initial,c,s).run()
 assert public(m.memory)!=public(expected)or m.calls!=calls
 return dict(compiled_cached_actor_control_effective=True,alias_guest_only=True)
def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,programs=guest();print('guest qualified',g['cases'],flush=True)
 report=dict(guest=g,callers=callers(programs),guest_control=guest_control(),native=native(),adversarial_helper_provider_and_complete_original_rng_separate=True)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def link(obj,label,entry,s,words=72):
 text,functions,bindings=parse_object(obj);asm,unknown=emit_function(text,functions['func_1506BCC8'],bindings,'func_1506BCC8',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(name,value)for name,value in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_1506BCC8','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:words*4];return list(struct.unpack('>%dI'%words,data))
