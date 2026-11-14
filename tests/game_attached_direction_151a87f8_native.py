from pathlib import Path
import json,subprocess
from tools.tests import game_attached_direction_151a87f8_behavior as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-attached-direction-151a87f8-screen';s=(o/'selected.c').read_text();a=s.index('typedef struct {\n    u8 *target;');z=s.index('\nvoid func_151A8A20',a);head,body=s[a:z].split('/* Refresh an attached',1);body='/* Refresh an attached'+body
bad={'wrong_live_gate':body.replace('*(s32 *)target == 0','*(s32 *)target <= 0'),
 'wrong_identity':body.replace('cache->identity != target[0x3B]','cache->identity == target[0x3B]'),
 'wrong_matrix_stride':body.replace('<< 6','<< 5'),
 'wrong_delta':body.replace('dx = *(f32 *)(record + 0x30) -','dx = *(f32 *)(record + 0x30) +'),
 'wrong_latch':body.replace('!(cache->flags & 1)','!(cache->flags & 2)'),
 'wrong_reciprocal':body.replace('1.0f / *(f32 *)(record + 0x54)','2.0f / *(f32 *)(record + 0x54)'),
 'reload_cache':body.replace('        if (!(cache->flags & 1)) {','        cache = *(AttachedDirection151A87F8 **)(record + 0x60);\n        target = cache->target;\n        if (!(cache->flags & 1)) {')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\n'+head+'\n'.join(v.replace('func_151A87F8','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 active,identity,mismatch,kind,matrix,index,latched,flags,collision,accepted,length,mutation,answer,recordLink,cacheLink,finalFlags,finalLatch;u32 events[5],eventCount;u32 collisionValues[6],delta[3],values[20];} Case;
static const Case cases[]={
'''
rows=[]
for c in b.cases():
 if c.phase:continue
 if (not c.active or c.mismatch or c.kind==255) and not(c.matrix and c.latched==0 and c.collision and c.accepted and b.fb(c.length)==b.fb(2.5) and c.mutation==0):continue
 m,calls,obs,answer=b.reference(b.fixture(c),c);kinds={b.TRANSFORM:1,b.COLLISION:2,b.HIT:3,b.LENGTH:4,b.ORIENT:5}
 scalar=(c.active,c.identity,c.mismatch,c.kind,c.matrix,c.index,c.latched,c.flags,c.collision,c.accepted,b.fb(c.length),c.mutation,answer,int(b.read(m,b.RECORD+96)==b.CACHE2),int(b.read(m,b.CACHE)==b.TARGET2),m[b.RECORD+28],m[b.CACHE+37])
 events=[kinds[t] for t,a in calls];collision=next((a[:6] for t,a in calls if t==b.COLLISION),(0,)*6);delta=next((a for t,a in obs if t==b.LENGTH),(0,)*3)
 values=[b.read(m,b.RECORD+48+4*i) for i in range(11)]+[b.read(m,b.CACHE+at) for at in (8,12,16,24,28,32)]+[b.read(m,b.TARGET+20+4*i) for i in range(3)]
 arr=lambda vs:'{'+','.join(hex(v)+'u' for v in vs)+'}'
 rows.append('{'+','.join(hex(v)+'u' for v in scalar)+','+arr(events or [0])+','+str(len(events))+','+arr(collision)+','+arr(delta)+','+arr(values)+'}')
code+=',\n'.join(rows)+'\n};\n'+r'''
typedef struct {u8 before[28],flags,pad1D[19];f32 start[3],end[3];struct17 orientation;f32 length,reciprocal;u32 pad5C;AttachedDirection151A87F8*cache;u8 tail[156];} Object;
typedef struct {u32 active;u8 kind,pad05[15];f32 position[3];u8 pad20[27],identity,pad3C[408];u8*matrices;u8 tail[40];} Target;
typedef struct {AttachedDirection151A87F8 data;u8 tail[24];} Cache;
typedef char Layout[sizeof(Object)==256&&__builtin_offsetof(Object,cache)==96&&sizeof(Target)==512&&__builtin_offsetof(Target,matrices)==468&&sizeof(Cache)==64?1:-1];
static Object object;static Target target,other;static Cache cache,cache2;static u8 matrices[16384];
static const Case*current;static u32 nextEvent,error;
static f32 real(u32 v){Bits b;b.u=v;return b.f;}static u32 word(f32 v){Bits b;b.f=v;return b.u;}
static void event(u32 kind){if(nextEvent>=current->eventCount||current->events[nextEvent]!=kind)error=1;nextEvent++;}
static void effect(u32 stage){if(current->mutation&1){
 if(stage==1){object.cache=&cache2.data;cache.data.target=(u8*)&other;object.flags^=0x80;target.position[0]=8.;target.position[1]=9.;target.position[2]=10.;cache.data.offset[0]=-.25;cache.data.offset[1]=-1.25;cache.data.offset[2]=-2.25;}
 if(stage==2){cache.data.flags^=0x80;object.flags^=0x40;}
 if(stage==3){cache.data.flags^=0x40;object.flags^=0x20;}
 if(stage==4){object.length=99.;object.reciprocal=41.;object.flags^=0x10;}
 if(stage==5)object.flags^=8;
 }if((current->mutation&2)&&stage==1)cache.data.flags^=1;}
void func_15143134(f32*source,f32*out,u8*matrix){event(1);if(source!=cache.data.local||out!=object.start||matrix!=matrices+current->index*64)error=1;out[0]=source[0]+1.;out[1]=source[1]+2.;out[2]=source[2]+3.;effect(1);}
s32 func_150AC9C0(f32 x,f32 y,f32 z,f32 dx,f32 dy,f32 dz,s32 zero0,s32 zero1,f32*endX,f32*endY,f32*endZ,f32*unused,s32*hit,s32 zero2,f32 zero3){u32 i;f32 values[6];event(2);values[0]=x;values[1]=y;values[2]=z;values[3]=dx;values[4]=dy;values[5]=dz;for(i=0;i<6;i++)if(word(values[i])!=current->collisionValues[i])error=1;if(zero0||zero1||zero2||word(zero3)||unused||!hit||endX!=object.end||endY!=object.end+1||endZ!=object.end+2)error=1;*endX=x+4.;*endY=y+5.;*endZ=z+6.;*hit=0x12345678;effect(2);return current->collision;}
u8 func_15145C90(s32 hit){event(3);if(hit!=0x12345678)error=1;effect(3);return current->accepted;}
f32 func_15143E64(f32*value){struct17*v=(struct17*)value;event(4);if(word(v->unk0)!=current->delta[0]||word(v->unk4)!=current->delta[1]||word(v->unk8)!=current->delta[2])error=1;effect(4);return real(current->length);}
s32 func_15146078(struct17*v,struct17*temporary,struct17*out){event(5);if(word(v->unk0)!=current->delta[0]||word(v->unk4)!=current->delta[1]||word(v->unk8)!=current->delta[2]||out!=&object.orientation||word(object.reciprocal)!=word(1.f/real(current->length)))error=1;temporary->unk0=v->unk0+10.;temporary->unk4=v->unk4+10.;temporary->unk8=v->unk8+10.;out->unk0=v->unk0+20.;out->unk4=v->unk4+20.;out->unk8=v->unk8+20.;effect(5);return 0;}
static s32(*candidates[])(u8*)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7};
static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
 for(j=0;j<8;j++){s32 answer;u32 words[20];for(k=0;k<sizeof(object);k++)((u8*)&object)[k]=(u8)(k*19);for(k=0;k<sizeof(target);k++){((u8*)&target)[k]=(u8)(k*19);((u8*)&other)[k]=(u8)(k*19);}for(k=0;k<sizeof(cache);k++){((u8*)&cache)[k]=(u8)(k*19);((u8*)&cache2)[k]=(u8)(k*19);}
  object.flags=current->flags;object.cache=&cache.data;object.start[0]=2.;object.start[1]=4.;object.start[2]=6.;object.end[0]=7.;object.end[1]=11.;object.end[2]=15.;object.orientation.unk0=20.;object.orientation.unk4=21.;object.orientation.unk8=22.;object.length=13.;object.reciprocal=17.;
  cache.data.target=(u8*)&target;cache.data.identity=current->identity;cache.data.matrixIndex=current->index;cache.data.flags=current->latched;cache.data.local[0]=1.25;cache.data.local[1]=-2.5;cache.data.local[2]=3.75;cache.data.offset[0]=.5;cache.data.offset[1]=-.75;cache.data.offset[2]=1.25;
  target.active=current->active;target.kind=current->kind;target.identity=current->identity^current->mismatch;target.matrices=current->matrix?matrices:0;target.position[0]=-3.;target.position[1]=4.;target.position[2]=-5.;
  cache2.data.target=(u8*)&other;cache2.data.flags=0;cache2.data.offset[0]=9.;cache2.data.offset[1]=8.;cache2.data.offset[2]=7.;other.active=1;other.kind=1;other.matrices=matrices;other.position[0]=20.;other.position[1]=30.;other.position[2]=40.;nextEvent=error=0;
  answer=candidates[j]((u8*)&object);
  if(answer!=(s32)current->answer||nextEvent!=current->eventCount||object.flags!=current->finalFlags||cache.data.flags!=current->finalLatch||object.cache!=(current->recordLink?&cache2.data:&cache.data)||cache.data.target!=(current->cacheLink?(u8*)&other:(u8*)&target))error=1;
  for(k=0;k<3;k++){words[k]=word(object.start[k]);words[3+k]=word(object.end[k]);words[11+k]=word(cache.data.local[k]);words[14+k]=word(cache.data.offset[k]);words[17+k]=word(target.position[k]);}words[6]=word(object.orientation.unk0);words[7]=word(object.orientation.unk4);words[8]=word(object.orientation.unk8);words[9]=word(object.length);words[10]=word(object.reciprocal);for(k=0;k<20;k++)if(words[k]!=current->values[k])error=1;
  for(k=0;k<sizeof(object);k++)if(k!=28&&!(k>=48&&k<92)&&!(k>=96&&k<100)&&((u8*)&object)[k]!=(u8)(k*19))error=1;
  for(k=0;k<sizeof(cache);k++)if(!(k<5)&&!(k>=8&&k<21)&&!(k>=24&&k<36)&&k!=37&&((u8*)&cache)[k]!=(u8)(k*19))error=1;
  for(k=0;k<sizeof(target);k++)if(!(k<5)&&!(k>=20&&k<32)&&k!=59&&!(k>=468&&k<472)&&((u8*)&target)[k]!=(u8)(k*19))error=1;
  if(error){if(!j)return 10;killed|=1u<<(j-1);}
 }
}return killed==127u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-attached-direction.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-attached-direction'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,typed_disjoint_inputs=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
