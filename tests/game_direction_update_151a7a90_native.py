from pathlib import Path
import json,subprocess
from tools.tests import game_direction_update_151a7a90_behavior as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-direction-update-151a7a90-screen';s=(o/'selected.c').read_text();a=s.index('typedef struct {f32 x,y,z,outX,outY,outZ;}');z=s.index('\ns32 func_151A7D6C',a);head,body=s[a:z].split('/* Run lifecycle',1);body='/* Run lifecycle'+body
snapshot=body.replace('    u8 dead;','    u8 dead;\n    s8 selectedSecond;').replace('    dead = 0;','    selectedSecond = state->secondCallback;\n    dead = 0;').replace('if (state->secondCallback != -1 && !dead) dead = !D_8008F948[state->secondCallback]','if (selectedSecond != -1 && !dead) dead = !D_8008F948[selectedSecond]')
range_snapshot=body.replace('    u8 dead;','    u8 dead;\n    f32 oldRange;').replace('            state->timer = func_150ADA68();','            oldRange = state->range;\n            state->timer = func_150ADA68();').replace('state->timer * state->range','state->timer * oldRange')
bad={'wrong_lifetime_mask':body.replace('state->flags & 1','state->flags & 4'),
 'truncate_callback_return':body.replace('dead = !D_8008F940','dead = !(u8)D_8008F940'),
 'snapshot_second_selector':snapshot,
 'omit_count_narrowing':body.replace('(s16)(state->count - 1)','(state->count - 1)'),
 'snapshot_range_before_sample':range_snapshot,
 'wrong_vertex_basis':body.replace('vertex->y * side.unk4','vertex->y * side.unk0'),
 'wrong_release_gate':body.replace('if (dead) func_1516972C','if (!dead) func_1516972C')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\ntypedef struct struct102 struct102;\nvoid func_1516972C(struct102 *);\n'+head+'\n'.join(v.replace('func_151A7A90','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 flags,first,second,firstAnswer,secondAnswer,lifetime,ticks,count,timer,timestep,minimum,range,sample,mutation;
u32 finalLifetime,finalCount,finalFlags,finalSecond,alternate;u32 values[14],vertices[60],events[6],eventCount,eventCountArgument,randomTimer,crossInput[6];} Case;
static const Case cases[]={
'''
rows=[];kinds={b.GATE_A:1,b.GATE_A+4:1,b.GATE_B:2,b.GATE_B+4:2,b.EVENT:3,b.RANDOM:4,b.CROSS:5,b.FREE:6}
offsets=(20,24,104,*range(48,92,4))
assert len(offsets)==14
arr=lambda vs:'{'+','.join(hex(b.u32(v))+'u' for v in vs)+'}'
for c in b.cases():
 if c.phase:continue
 m,calls,obs=b.reference(b.fixture(c),c)
 scalar=(c.flags,c.first,c.second,c.first_answer,c.second_answer,c.lifetime,c.ticks,c.count,b.fb(c.timer),b.fb(c.timestep),b.fb(c.minimum),b.fb(c.range),b.fb(c.sample),c.mutation,b.read(m,c.record+16,2),b.read(m,c.record+18,2),m[c.record+28],m[c.record+45],int(b.read(m,c.record+100)==b.ALTERNATE))
 values=[b.read(m,c.record+at) for at in offsets];vertices=[b.read(m,p+4*i) for p in (b.VERTICES,b.ALTERNATE) for i in range(30)]
 events=[kinds[t] for t,a in calls];countArg=next((a[2] for t,a in calls if t==b.EVENT),0);randomTimer=next((a for t,a in obs if t==b.RANDOM),0);cross=next((a[0]+a[1] for t,a in obs if t==b.CROSS),(0,)*6)
 rows.append('{'+','.join(hex(b.u32(v))+'u' for v in scalar)+','+arr(values)+','+arr(vertices)+','+arr(events or [0])+','+str(len(events))+','+hex(countArg)+'u,'+hex(randomTimer)+'u,'+arr(cross)+'}')
code+=',\n'.join(rows)+'\n};\n'+r'''
typedef struct {DirectionState151A7A90 state;u8 tail[148];} Object;
typedef char Layout[sizeof(Object)==256&&sizeof(DirectionVertex151A7A90)==24&&__builtin_offsetof(DirectionState151A7A90,lifetime)==16&&__builtin_offsetof(DirectionState151A7A90,firstCallback)==44&&__builtin_offsetof(DirectionState151A7A90,vertices)==100&&sizeof(DirectionState151A7A90)==108?1:-1];
static Object object;static DirectionVertex151A7A90 vertices[5],alternate[5];static u8 before[256],cache[64];
static const Case*current;static u32 nextEvent,error;
s32 D_800BE9E4;f32 D_800BE9A4;
static f32 real(u32 v){Bits b;b.u=v;return b.f;}static u32 word(f32 v){Bits b;b.f=v;return b.u;}
static void event(u32 kind){if(nextEvent>=current->eventCount||current->events[nextEvent]!=kind)error=1;nextEvent++;}
static void effect(u32 stage){DirectionState151A7A90*p=&object.state;if(!(current->mutation&1))return;
 if(stage==1){p->secondCallback=0;p->timer=-.5f;D_800BE9A4=.5f;}
 if(stage==2){p->flags|=2;p->count=2;}
 if(stage==3){p->count=2;p->timer=31.f;p->minimum=3.f;p->range=6.f;}
 if(stage==4){p->minimum=5.f;p->range=7.f;p->timer=99.f;p->flags|=2;}
 if(stage==5){p->start.unk0=7.5f;p->start.unk4=-2.25f;p->start.unk8=.5f;p->reciprocal=.5f;p->count=2;p->vertices=alternate;}
 if(stage==6)((u8*)p)[1]=0xee;
}
static s32 gateA(u8*p){event(1);if(p!=(u8*)&object)error=1;effect(1);return current->firstAnswer;}
static s32 gateB(u8*p){event(2);if(p!=(u8*)&object)error=1;effect(2);return current->secondAnswer;}
s32(*D_8008F940[])(u8*)={gateA,gateA};s32(*D_8008F948[])(u8*)={gateB,gateB};
s32 func_151A8340(u8*p,s32 zero,s32 count,s32 context,s32 limit){event(3);if(p!=(u8*)&object||zero||(u32)count!=current->eventCountArgument||(u32)context!=0x87654321u||limit!=100)error=1;effect(3);return 0;}
f32 func_150ADA68(void){event(4);if(word(object.state.timer)!=current->randomTimer)error=1;effect(4);return real(current->sample);}
void func_151450B4(struct17*a,struct17*b,struct17*out){event(5);if(word(a->unk0)!=current->crossInput[0]||word(a->unk4)!=current->crossInput[1]||word(a->unk8)!=current->crossInput[2]||word(b->unk0)!=current->crossInput[3]||word(b->unk4)!=current->crossInput[4]||word(b->unk8)!=current->crossInput[5])error=1;
 out->unk0=a->unk4*b->unk8-a->unk8*b->unk4;out->unk4=a->unk8*b->unk0-a->unk0*b->unk8;out->unk8=a->unk0*b->unk4-a->unk4*b->unk0;effect(5);if(current->mutation&1){a->unk0+=.25f;b->unk8-=.5f;}}
void func_1516972C(struct102*p){event(6);if(p!=(struct102*)&object)error=1;effect(6);}
static void(*candidates[])(struct102*)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7};
static int run(void){u32 i,j,k,n,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
 for(j=0;j<8;j++){DirectionState151A7A90*p=&object.state;u32 values[14];
  for(k=0;k<256;k++)((u8*)&object)[k]=(u8)(k*19);
  p->lifetime=(s16)current->lifetime;p->count=(s16)current->count;p->minimum=real(current->minimum);p->range=real(current->range);p->flags=current->flags;p->context=(s32)0x87654321u;p->firstCallback=(s8)current->first;p->secondCallback=(s8)current->second;
  p->start.unk0=2.f;p->start.unk4=4.f;p->start.unk8=6.f;p->end.unk0=7.f;p->end.unk4=11.f;p->end.unk8=15.f;p->direction.unk0=20.f;p->direction.unk4=21.f;p->direction.unk8=22.f;p->length=13.f;p->reciprocal=17.f;p->cache=cache;p->vertices=vertices;p->timer=real(current->timer);
  D_800BE9E4=(s32)current->ticks;D_800BE9A4=real(current->timestep);
  for(n=0;n<2;n++)for(k=0;k<5;k++){DirectionVertex151A7A90*v=(n?alternate:vertices)+k;v->x=.5f+k+n;v->y=-1.f+.25f*k;v->z=.75f-.125f*k;v->outX=-10.f;v->outY=-20.f;v->outZ=-30.f;}
  for(k=0;k<256;k++)before[k]=((u8*)&object)[k];nextEvent=error=0;candidates[j]((struct102*)&object);
  if((u16)p->lifetime!=current->finalLifetime||(u16)p->count!=current->finalCount||p->flags!=current->finalFlags||(u8)p->secondCallback!=current->finalSecond||p->vertices!=(current->alternate?alternate:vertices)||nextEvent!=current->eventCount||p->cache!=cache)error=1;
  values[0]=word(p->minimum);values[1]=word(p->range);values[2]=word(p->timer);values[3]=word(p->start.unk0);values[4]=word(p->start.unk4);values[5]=word(p->start.unk8);values[6]=word(p->end.unk0);values[7]=word(p->end.unk4);values[8]=word(p->end.unk8);values[9]=word(p->direction.unk0);values[10]=word(p->direction.unk4);values[11]=word(p->direction.unk8);values[12]=word(p->length);values[13]=word(p->reciprocal);
  for(k=0;k<14;k++)if(values[k]!=current->values[k])error=1;
  for(n=0;n<2;n++)for(k=0;k<5;k++){DirectionVertex151A7A90*v=(n?alternate:vertices)+k;u32 base=n*30+k*6;if(word(v->x)!=current->vertices[base]||word(v->y)!=current->vertices[base+1]||word(v->z)!=current->vertices[base+2]||word(v->outX)!=current->vertices[base+3]||word(v->outY)!=current->vertices[base+4]||word(v->outZ)!=current->vertices[base+5])error=1;}
  for(k=0;k<256;k++)if(k!=1&&!(k>=16&&k<29)&&k!=45&&!(k>=48&&k<92)&&!(k>=100&&k<108)&&((u8*)&object)[k]!=before[k])error=1;
  if(((u8*)&object)[1]!=(current->mutation&1&&current->eventCount&&current->events[current->eventCount-1]==6?0xee:before[1]))error=1;
  if(error){if(!j)return 10;killed|=1u<<(j-1);}
 }
}return killed==127u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-direction-update.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-direction-update'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,typed_disjoint_inputs=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
