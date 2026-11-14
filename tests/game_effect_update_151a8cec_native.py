from pathlib import Path
import json,subprocess
from tools.tests import game_effect_update_151a8cec_behavior as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-effect-update-151a8cec-screen';s=(o/'selected.c').read_text();a=s.index('typedef struct {\n    u8 kind;');z=s.index('} ParitySpawnRequest;',a)+len('} ParitySpawnRequest;');request=s[a:z]
a=s.index('typedef struct HeightResult71820 {');z=s.index('\nvoid func_151A8F1C(u8 *arg0',a);piece=s[a:z];head,body=piece.split('/* Advance the effect',1);body='/* Advance the effect'+body
bad={'wrong_sentinel':body.replace('!= -1 &&','!= -2 &&'),
 'wrong_enable':body.replace('!(state->request.kind & 1)','!(state->request.kind & 16)'),
 'wrong_threshold':body.replace('> 1.0f','> 2.0f'),
 'wrong_increment':body.replace('state->request.primary + draw', 'state->request.primary - draw'),
 'wrong_position':body.replace('state->request.kind & 2','state->request.kind & 16'),
 'wrong_height':body.replace('vector[1] = state->ground.height','vector[1] = out1'),
 'wrong_decrement':body.replace('state->accumulator -= 1.0f','state->accumulator -= 2.0f')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct struct260 struct260;\n'+request+'\n'+head+r'''
static s32(*nativeGates[256])(u8*);
static void(*nativeEmitters[256])(u8*,f32*,f32,u8);
#define D_8008F980 (nativeGates+128)
#define D_8008F970 (nativeEmitters+128)
'''+ '\n'.join(v.replace('func_151A8CEC','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 flags,mode,selector,attached,spatial,gate,stop,ground,accumulator,mutation;u32 calls[32],count;u32 observations[8][5],observationsCount;u8 output[256];} Case;
static const Case cases[]={
'''
rows=[]
for c in b.cases():
 if c.phase or c.seed or c.selector not in (0,1,255):continue
 # No native read of the initially indeterminate accepted byte: the first
 # emitted tick must set it, or no emitter may observe it.
 expected,calls,obs=b.reference(b.fixture(c),c)
 if obs and not (c.flags&8 or c.ground==0):continue
 kinds=[]
 for t,args in calls:
  kinds.append(0 if b.GATE<=t<b.GATE+1024 else 1 if t==b.STOP else 2 if t==b.RANDOM else 3 if t==b.ATTACHED else 4 if t==b.FREE else 5 if t==b.GROUND else 6)
 assert len(kinds)<=32 and len(obs)<=8
 observed=['{'+','.join(hex(v)+'u' for v in (*vec,out0,flag))+'}' for vec,out0,flag in obs]
 scalar=(c.flags,c.mode,c.selector,c.attached,c.spatial,c.gate,c.stop,c.ground,b.fb(c.accumulator),c.mutation)
 row='{'+','.join(hex(v)+'u' for v in scalar)+',{'+','.join(map(str,kinds))+'},'+str(len(kinds))+',{'+','.join(observed or ['{0}'])+'},'+str(len(obs))+',{'+','.join(str(expected[b.OWNER+i]) for i in range(256))+'}}'
 rows.append(row)
code+=',\n'.join(rows)+'\n};\n'+r'''
typedef struct {u8 before[14];u16 lifetime;u8 after[24];} Header;
typedef struct {Header header;UpdatePayload151A8CEC payload;u8 tail[128];} Object;
typedef char SizeCheck[sizeof(Object)==256 && sizeof(UpdatePayload151A8CEC)==88?1:-1];
static Object object;static u8 other[256];static s16 spatial[3];
static const Case*current;static u32 nextCall,positions,grounds,emits,error;
f32 D_800BE9A4;
static f32 real(u32 v){Bits b;b.u=v;return b.f;}static u32 word(f32 v){Bits b;b.f=v;return b.u;}
static u32 expectedWord(u32 at){return((u32)current->output[at]<<24)|((u32)current->output[at+1]<<16)|((u32)current->output[at+2]<<8)|current->output[at+3];}
static void call(u32 kind){if(nextCall>=current->count||current->calls[nextCall]!=kind)error=1;nextCall++;}
static void effect(u32 stage,u32 index){UpdatePayload151A8CEC*p=&object.payload;if(!current->mutation)return;
 if(stage==0){p->request.kind^=2;p->request.owner=other;}
 if(stage==1)p->request.kind^=1;
 if(stage==2){p->request.primary=.75;p->request.secondary=.25;p->scale=.75;D_800BE9A4=.25;}
 if(stage==3){p->request.kind^=2;if(!index)p->request.flags=current->selector;}
 if(stage==5)p->ground.height=-7.-index;
 if(stage==6&&!index)p->accumulator=3.25;
}
static s32 gateFn(u8*owner){call(0);if(owner!=(u8*)&object)error=1;effect(0,0);return current->gate;}
u8 func_151464B8(s16*p){call(1);if(p!=spatial)error=1;effect(1,0);return current->stop;}
f32 func_150ADA68(void){call(2);effect(2,0);return .5;}
static void position(u8*owner,f32*vec,f32*out0,f32*out1,u32 kind){call(kind);if(owner!=(u8*)&object)error=1;vec[0]=10.+positions;vec[1]=20.+positions;vec[2]=30.+positions;*out0=40.+positions;*out1=50.+positions;effect(3,positions++);}
void func_151A8F1C(u8*o,f32*v,f32*a,f32*b){position(o,v,a,b,3);}
void func_151A8F6C(u8*o,f32*v,f32*a,f32*b){position(o,v,a,b,4);}
s32 func_15046C80(f32*v,u16 selector,f32 height,HeightResult71820*out){u32 n=grounds++;call(5);if(selector||word(height)!=word(50.+n)||out!=&object.payload.ground)error=1;effect(5,n);return(current->ground+n)&1;}
static void emitter(u8*owner,f32*v,f32 out0,u8 flag){u32 n=emits++,i;call(6);if(owner!=(u8*)&object||n>=current->observationsCount){error=1;return;}for(i=0;i<3;i++)if(word(v[i])!=current->observations[n][i])error=1;if(word(out0)!=current->observations[n][3]||flag!=current->observations[n][4])error=1;effect(6,n);}
static void(*candidates[])(struct260*)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7};
static int run(void){u32 i,j,k,killed=0;for(i=0;i<256;i++){nativeGates[i]=gateFn;nativeEmitters[i]=emitter;}
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<8;j++){UpdatePayload151A8CEC*p=&object.payload;for(k=0;k<sizeof(object);k++)((u8*)&object)[k]=(u8)(k*19);
   p->request.kind=current->flags;p->request.mode=current->mode;p->request.flags=current->selector;p->request.owner=current->attached?other:0;p->spatial=current->spatial?spatial:0;p->request.primary=.25;p->request.secondary=.5;p->accumulator=real(current->accumulator);p->ground.height=-2.;p->scale=.5;D_800BE9A4=.5;nextCall=positions=grounds=emits=error=0;
   candidates[j]((struct260*)&object);
   if(nextCall!=current->count||emits!=current->observationsCount)error=1;
   for(k=0;k<256;k++)if(!(k>=14&&k<16)&&!(k>=44&&k<56)&&!(k>=80&&k<88)&&!(k>=120&&k<128)&&((u8*)&object)[k]!=current->output[k])error=1;
   if(word(p->request.primary)!=expectedWord(48)||word(p->request.secondary)!=expectedWord(52)||word(p->accumulator)!=expectedWord(80)||word(p->ground.height)!=expectedWord(84)||word(p->scale)!=expectedWord(124))error=1;
   if(p->request.owner!=(expectedWord(44)?other:0)||p->spatial!=(current->spatial?spatial:0))error=1;
   {u16 lifetime=((u16)current->output[14]<<8)|current->output[15];if(object.header.lifetime!=lifetime)error=1;}
   if(error){if(!j)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
# Initialize the native lifetime as a numeric halfword, not host-order bytes.
code=code.replace('p->request.kind=current->flags;', 'object.header.lifetime=0x0a1d;p->request.kind=current->flags;')
p=o/'native-effect-update.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-effect-update'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,retained_flag_first_initialized=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
