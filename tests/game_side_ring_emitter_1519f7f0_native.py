"""Native defined-domain emitter checks; no transition-padding/native fault claim."""
from pathlib import Path
import json,subprocess,struct
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g
from tools.experiments import game_side_effect_constructor_1519f1c8_match as ctor
from tools.experiments import game_side_effect_update_1519f4f0_match as updater
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_side_ring_emitter_1519f7f0_recovery as source
O,PIN=source.OUT,source.PIN
PF=dict(scale=8,phase=12,**{'position.x':16,'position.y':20,'position.z':24},elapsed=28,referenceX=32,referenceZ=36,speed=56,limit=60,rate=76)
PS=dict(zero28=40,duration=46,alpha=48,width=50,height=52,zero46=70,count=72,command=74)
EF=dict(x=0,z=4,height=8,phase=12,**{'velocity.x':28,'velocity.z':32})
ES=dict(alpha=16,delay=18,light=20,tag=22,lifetime=24,reserved1A=26)
def make_source():
 corpus=[]
 for c in g.cases():
  if c.side_effects or c.hit!=1 or c.rule!='left' or c.seed or c.phase:continue
  m=g.fixture(c);expected,result,calls,ops=g.reference(m,c)
  if any(v&0x7F800000==0x7F800000 for op in ops for v in op[1:]):continue
  corpus.append((c,m,expected,result,calls))
 rows=[];array=lambda vals:'{'+','.join(str(v) for v in vals)+'}'
 for c,m,expected,result,calls in corpus:
  spans=[]
  for memory in (m,expected):
   for at,n in ((g.E,160),(g.P,80),(g.A,36*c.cap),(g.S,128),(g.T,512)):spans.append(array(memory[at+i] for i in range(n)))
  callrows=[]
  for call in calls:
   target,args=call[:2]
   if target==g.SIDE:values=(target,args[1],0,0,0)
   elif target==g.RNG:values=(target,0,0,0,0)
   else:assert target==g.FLOOR;values=(target,args[1],*struct.unpack('>3I',call[2]))
   callrows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
  assert len(callrows)<=12
  callrows+=['{0,0,0,0,0}']*(12-len(callrows))
  values=(c.bound,c.cap,c.motion,c.rng_effects,c.floor_effects,c.floor_hit,c.random,result,len(calls),g.read(expected,g.symbols()['D_800BE9A4']),g.read(expected,g.symbols()['D_800A8CF8']))
  rows.append('{'+','.join('0x%Xu'%v for v in values)+','+','.join(spans)+',{'+','.join(callrows)+'}}')
 prefix='#include <ultra64.h>\n#include "structs.h"\n'+ctor.PIN['declarations']+updater.PIN['declarations']+'''
typedef struct {u8 *first,*second,*third,*fourth;} FourWord1CC440;
'''+PIN['declarations']+'''
s32 func_1519EF90(u8 *,u8,f32 *);
void func_1519F48C(u8 *);
f32 sqrtf(f32);
f32 fabsf(f32);
f32 D_800A8CF4,D_800A8CF8,D_800A8CFC,D_800BE9A4;
typedef struct {
 u32 initialBound,cap,motion,rngEffects,floorEffects,floorHit,random,want,ncall,finalTime,finalBound;
 u8 ie[160],ip[80],ia[180],is[128],it[512],fe[160],fp[80],fa[180],fs[128],ft[512];
 u32 calls[12][5];
} NativeCase;
typedef struct {u8 retained00[24];struct127 *actor;u8 retained1C[100];} NativeState;
static SideEmitter1519F7F0 effect;
static SidePayload1519F1C8 packet;
static SideEmitEntry1519F7F0 entries[5];
static NativeState state;
static struct127 actor;
static u32 bank;
static const NativeCase *current;
static u32 ordinal,rngOrdinal,floorOrdinal,failure;
static f32 number(u32 v){union {u32 u;f32 f;} x;x.u=v;return x.f;}
static u32 word(f32 v){union {u32 u;f32 f;} x;x.f=v;return x.u;}
f32 fabsf(f32 v){return number(word(v)&0x7FFFFFFFu);}
f32 sqrtf(f32 v){f32 x;__asm__("sqrtss %1,%0":"=x"(x):"x"(v));return x;}
static void copy(u8 *d,const u8 *p,u32 n){for(u32 i=0;i<n;i++)d[i]=p[i];}
void *memcpy(void *d,const void *p,u32 n){copy(d,p,n);return d;}
static u32 get32(const u8 *p){return (u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static s32 get16(const u8 *p){u32 v=(u32)p[0]<<8|p[1];return (s32)v-(v&0x8000?65536:0);}
static void put32(u8 *p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static void put16(u8 *p,u32 v){p[0]=v>>8;p[1]=v;}
static int same(const u8 *a,const u8 *b,u32 n){for(u32 i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
typedef char shape_effect[sizeof(effect)==160?1:-1];
typedef char shape_packet[sizeof(packet)==80?1:-1];
typedef char shape_entry[sizeof(entries[0])==36?1:-1];
typedef char shape_state[sizeof(state)==128?1:-1];
typedef char shape_floor[sizeof(effect.floor)==36?1:-1];
typedef char shape_point[__builtin_offsetof(SideEmitter1519F7F0,point)==0x10?1:-1];
typedef char shape_entries[__builtin_offsetof(SideEmitter1519F7F0,entries)==0x94?1:-1];
typedef char shape_payload[__builtin_offsetof(SideEmitter1519F7F0,payload)==0x98?1:-1];
typedef char shape_height[__builtin_offsetof(struct127,unk118)==0x118?1:-1];
typedef char shape_actor_bank[__builtin_offsetof(struct127,unk1D4)==0x1D4?1:-1];
static const u32 *call(u32 target){u32 n=ordinal++;if(n>=current->ncall){failure=1;return current->calls[0];}if(current->calls[n][0]!=target)failure=2;return current->calls[n];}
s32 func_1519EF90(u8 *p,u8 mode,f32 *out){
 const u32 *a=call(0x1519EF90);if(p!=(u8 *)&packet||mode!=a[1]||out!=(f32 *)&effect.point)failure=3;
 static const f32 points[5][3]={{3,4,0},{0,0,0},{20001,0,0},{-3,0,-4},{.00001f,0,0}};
 for(u32 i=0;i<3;i++)out[i]=points[current->motion][i];return 1;
}
void func_1519F48C(u8 *p){failure=4;}
struct260 *func_151491F4(s16 a,s8 b,s8 c,u8 d,u8 e,s32 f,u8 h,s32 i){failure=5;return 0;}
s32 func_150ADA20(void){
 call(0x150ADA20);rngOrdinal++;
 if(current->rngEffects&1){packet.zero28=(s16)0x8001;packet.fourth=packet.fifth=255;}
 if(current->rngEffects&2){entries[effect.tail].velocity.x=-.25f;entries[effect.tail].velocity.z=.75f;}
 if(current->rngEffects&4){actor.unk118=-9600.f;actor.y_position=50.f;}
 return (s32)current->random;
}
s32 func_15045800(f32 *point,u16 selector,f32 bottom,void *out){
 const u32 *a=call(0x15045800);u32 n=floorOrdinal++;
 if(selector||out!=&effect.floor||word(bottom)!=a[1])failure=6;
 for(u32 i=0;i<3;i++)if(word(point[i])!=a[i+2])failure=7;
 for(u32 i=0;i<36;i++)((u8 *)out)[i]=(n*31+i*7+0xA5)&255;
 effect.floor.height=20.25f+n;
 if(current->floorEffects&1)packet.phase=n==0?1.25f:0.f;
 if(current->floorEffects&2){D_800A8CF8=0.f;D_800BE9A4=10.f;}
 if(current->floorEffects&4){effect.head=(effect.head+1)%current->cap;effect.count=1;}
 for(u32 i=0;i<12;i++)((u8 *)point)[i]^=0x5A;
 return current->floorHit<2?current->floorHit:n&1;
}
'''
 harness='\nstatic const NativeCase cases[]={\n'+',\n'.join(rows)+'\n};\n'+'''
static int run(void){
 for(u32 which=0;which<sizeof(cases)/sizeof(cases[0]);which++){
  const NativeCase *c=&cases[which];current=c;ordinal=rngOrdinal=floorOrdinal=failure=0;
  copy((u8 *)&effect,c->ie,160);copy((u8 *)&packet,c->ip,80);copy((u8 *)&state,c->is,128);copy((u8 *)&actor,c->it,512);
  effect.entries=entries;effect.payload=&packet;packet.state=(u8 *)&state;state.actor=&actor;
  actor.interaction_state=get32(c->it);actor.x_position=number(get32(c->it+20));actor.y_position=number(get32(c->it+24));actor.z_position=number(get32(c->it+28));actor.unk118=number(get32(c->it+0x118));actor.unk1D4=get32(c->it+0x1D4)?(struct255 *)&bank:0;
  effect.flags=get16(c->ie+30);effect.lifetime=get16(c->ie+28);effect.mode=get32(c->ie+32);
  for(u32 i=0;i<3;i++){((f32 *)&effect.point)[i]=number(get32(c->ie+16+4*i));((f32 *)&effect.published)[i]=number(get32(c->ie+0x54+4*i));}
  effect.floor.height=number(get32(c->ie+0x60));
'''
 for member,at in PF.items():harness+=f'  packet.{member}=number(get32(c->ip+{at}));\n'
 for member,at in PS.items():harness+=f'  packet.{member}=get16(c->ip+{at});\n'
 harness+='  for(u32 i=0;i<c->cap;i++){const u8 *p=c->ia+36*i;copy((u8 *)&entries[i],p,36);\n'
 for member,at in EF.items():harness+=f'   entries[i].{member}=number(get32(p+{at}));\n'
 for member,at in ES.items():harness+=f'   entries[i].{member}=get16(p+{at});\n'
 harness+='''  }
  D_800A8CF4=number(0x38D1B717);D_800A8CFC=-9500.f;D_800BE9A4=.5f;
  /* Initial bounds vary independently of a callback's final cached-bound mutation. */
  D_800A8CF8=number(c->initialBound);
  if((u32)func_1519F7F0(&effect)!=c->want||ordinal!=c->ncall||failure)return 151;
  if(word(D_800BE9A4)!=c->finalTime||word(D_800A8CF8)!=c->finalBound)return 152;
  u8 e[160],p[80],records[180],st[128],ac[512];copy(e,(u8 *)&effect,160);copy(p,(u8 *)&packet,80);copy(st,(u8 *)&state,128);copy(ac,(u8 *)&actor,512);
  put32(e+0x94,0x60000);put32(e+0x98,0x50000);put32(p,0x70000);put32(st+24,0x71000);
  put32(ac,actor.interaction_state);put32(ac+20,word(actor.x_position));put32(ac+24,word(actor.y_position));put32(ac+28,word(actor.z_position));put32(ac+0x118,word(actor.unk118));put32(ac+0x1D4,actor.unk1D4?0x12345678:0);
  put16(e+28,effect.lifetime);put16(e+30,effect.flags);put32(e+32,effect.mode);
  for(u32 i=0;i<3;i++){put32(e+16+4*i,word(((f32 *)&effect.point)[i]));put32(e+0x54+4*i,word(((f32 *)&effect.published)[i]));}put32(e+0x60,word(effect.floor.height));
'''
 for member,at in PF.items():harness+=f'  put32(p+{at},word(packet.{member}));\n'
 for member,at in PS.items():harness+=f'  put16(p+{at},packet.{member});\n'
 harness+='  for(u32 i=0;i<c->cap;i++){u8 *dst=records+36*i;copy(dst,(u8 *)&entries[i],36);\n'
 for member,at in EF.items():harness+=f'   put32(dst+{at},word(entries[i].{member}));\n'
 for member,at in ES.items():harness+=f'   put16(dst+{at},entries[i].{member});\n'
 harness+='''  }
  if(!same(e,c->fe,160)||!same(p,c->fp,80)||!same(records,c->fa,36*c->cap)||!same(st,c->fs,128)||!same(ac,c->ft,512))return 153;
 }
 return 0;
}
'''
 return prefix+PIN['source']+harness+START,len(corpus)
def main():
 text,count=make_source();path=O/'refined-native.c';path.write_text(text);profiles=[];warnings=[];controls=0
 def compile_run(code,label,opt,alias):
  path=O/(label+'.c');exe=path.with_suffix('');path.write_text(code)
  # Retail intentionally leaves inverseLength untouched on a path excluded
  # by the tested retained-progress contract. Preserve the exact source and
  # retain this diagnostic; do not initialize the local just to silence it.
  p=subprocess.run(native_command(opt)+['-Wno-error=maybe-uninitialized','-mstackrealign',alias,'-o',str(exe),str(path)],capture_output=True,text=True)
  assert p.returncode==0,p.stderr
  if p.stderr:
   assert p.stderr.count('warning:')==1 and 'inverseLength' in p.stderr and ' may be used uninitialized [-Wmaybe-uninitialized]' in p.stderr,p.stderr
   warnings.append(label);(O/(label+'-diagnostics.txt')).write_text(p.stderr)
  return subprocess.run([str(exe)],capture_output=True).returncode
 for opt in ('-O0','-O2','-O3'):
  for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
   result=compile_run(text,'refined-native'+opt+alias,opt,alias);assert result==0,(opt,alias,result);profiles.append(opt+alias)
  changes={'smoothing':('earlier = previous - 1;','earlier = previous;'),
           'duration':('entry->lifetime = packet->duration;','entry->lifetime = packet->alpha;'),
           'query-span':('point[1] - 200.0f','point[1] - 201.0f'),
           'signed-random':('random % ((u32)packet->fifth + 1)','((s32)random % ((s32)packet->fifth + 1))')}
  for label,(old,new) in changes.items():
   assert PIN['source'].count(old)==1
   wrong=text.replace(PIN['source'],PIN['source'].replace(old,new))
   result=compile_run(wrong,'refined-native-control-'+label+opt,opt,'-fstrict-aliasing')
   assert result in (151,152,153),(label,opt,result);controls+=1
 report=dict(cases_per_profile=count,profiles=profiles,UBSan=True,complete_public_snapshots=True,opaque_transition_and_nonfinite_inputs_excluded=True,
             expected_out_of_domain_uninitialized_inverse_warning=warnings,effective_source_controls=controls,hardware_FCSR_emulated=False,c_match_credit=0)
 (O/'refined-native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
