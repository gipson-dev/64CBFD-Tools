"""Native32 screen and effective source controls for the private renderer."""
from pathlib import Path
import json,subprocess,os
from tools.tests import game_direction_strip_151a7d6c_oracle as b
from tools.experiments import game_direction_strip_151a7d6c_candidates as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();o=r/p.BUILD;body=p.SELECTED
bad={
 'wrong_active_gate':body.replace('state->flags & 2','state->flags & 1'),
 'wrong_endpoint':body.replace('last = state->count - 1','last = state->count - 2'),
 'reversed_cross_y':body.replace('delta.unk8 * ray.unk0 - ray.unk8 * delta.unk0','ray.unk8 * delta.unk0 - delta.unk8 * ray.unk0'),
 'wrong_width':body.replace('state->width / sqrtf(magnitude)','(state->width * 0.5f) / sqrtf(magnitude)'),
 'wrong_texture_span':body.replace('= 960;','= 1024;'),
 'wrong_triangle_winding':body.replace('gSP1Triangle(output++, 0, 2, 3, 0)','gSP1Triangle(output++, 0, 3, 2, 0)'),
 'cached_count':body.replace('    s16 first, next;','    s16 first, next;\n    s16 cachedCount;').replace('    loopOwner = state;','    cachedCount = state->count;\n    loopOwner = state;').replace('next < loopOwner->count','next < cachedCount'),
 'signed_color':body.replace('state->color[1]','(s8)state->color[1]')}
assert len(set(bad.values()))==8 and all(v!=body for v in bad.values())
source='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\ntypedef struct {f32 x,y,z,outX,outY,outZ;} DirectionVertex151A7A90;\n'+p.DECLARATIONS+'\n'.join(v.replace(p.FUNCTION,'candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
source+=r'''
typedef union{u32 u;f32 f;} Bits;
typedef struct{u32 flags,success,count,shape,mutation,seed,view,width;u32 calls[8][13],callCount,observation[9],owner[256],vertices[32][10],output[128],camera[3],global,table[8];} Case;
static const Case cases[]={
'''
def arr(xs):return '{'+','.join(arr(v) if isinstance(v,(list,tuple)) else hex(b.u32(v))+'u' for v in xs)+'}'
roles={'cursor':0xffff0001,'sync':0xffff0002,'delta':0xffff0003,'closest':0xffff0004,'parameter':0xffff0005}
rows=[]
for c in b.cases():
 if c.phase:continue
 initial=b.fixture(c);m,calls,obs,value=b.reference(initial,c)
 serialized=[[t,len(args),*[roles[x] if isinstance(x,str) else x for x in args]] for t,args in calls];serialized+=([[0]]*(8-len(serialized)))
 verts=[]
 for i in range(32):
  at=b.BUFFER+16*i;verts.append([*[b.read(m,at+2*j,2) for j in range(6)],*[m[at+12+j] for j in range(4)]])
 output=[b.read(m,b.OUTPUT+4*i) for i in range(128)]
 owner=[m[b.OWNER+i] for i in range(256)]
 observation=[v for vectors in obs for vector in vectors for v in vector] or [0]
 # Normalize expected native pointers/fields separately from raw padding bytes.
 fields=(c.flags,c.success,c.count,c.shape,c.mutation,c.seed,c.view,c.width)
 rows.append(arr([*fields,serialized,len(calls),observation,owner,verts,output,list(b.vec(m,b.CAM)),b.read(m,b.GLOBAL),[b.read(m,b.TABLE+4*i) for i in range(8)]]))
source+=',\n'.join(rows)+'\n};\n'+r'''
static struct{DirectionStripState151A7D6C state;u8 tail[128];} object;
static DirectionVertex151A7A90 primary[16],alternate[16];static Vtx vertices[32];static Gfx output[64];static struct17 camera;
u8 D_80090D70[32];u32 D_800D2C9C,D_800A4AC8[8];
static const Case*current;static u32 callIndex,error;static Gfx*expectedReturn;
static f32 real(u32 v){Bits a;a.u=v;return a.f;}static u32 word(f32 v){Bits a;a.f=v;return a.u;}
f32 sqrtf(f32 v){f32 answer;__asm__("sqrtss %1,%0":"=x"(answer):"x"(v));return answer;}
static u32 addr(const void*p){u32 a=(u32)p;
 if(a>=(u32)&object&&a<(u32)&object+sizeof(object))return 0x30000u+a-(u32)&object;
 if(a>=(u32)primary&&a<(u32)(primary+16))return 0x31040u+a-(u32)(primary+4);
 if(a>=(u32)alternate&&a<(u32)(alternate+16))return 0x32040u+a-(u32)(alternate+4);
 if(a>=(u32)vertices&&a<(u32)(vertices+32))return 0x70000u+a-(u32)vertices;
 if(a>=(u32)output&&a<(u32)(output+64))return 0x80000u+a-(u32)output;
 if(p==&camera)return 0x90000u;if(p==D_80090D70)return 0x80090d70u;return a;
}
static void record(u32 t,u32 n,const u32*a){u32 i;if(callIndex>=current->callCount){error=1;return;}
 if(current->calls[callIndex][0]!=t||current->calls[callIndex][1]!=n)error=error?error:5000+callIndex*20+19;
 for(i=0;i<n;i++)if(current->calls[callIndex][i+2]!=a[i])error=error?error:5000+callIndex*20+i;callIndex++;}
static void effect(u32 t){DirectionStripState151A7D6C*s=&object.state;
 if(current->mutation&1){if(t==0x151d5d60u){s->count=2;s->flags=0;}if(t==0x15144b34u)s->vertices=alternate+4;if(t==0x15142e24u)s->count=4;
  if(t==0x15142b7cu){u32 i;for(i=0;i<4;i++)s->color[i]^=0x55;}if(t==0x1513f4e4u)s->width=-1.5f;if(t==0x15142fbcu)s->vertices=primary+4;}
 if(current->mutation&2){if(t==0x15142e24u){D_800D2C9C=0x55443322u;D_800A4AC8[6]=0x80200480u;D_800A4AC8[7]=0x01020804u;}
  if(t==0x15145548u){camera.unk0=3.f;camera.unk4=-2.f;camera.unk8=7.f;s->count=3;s->width=.75f;s->vertices=alternate+4;}}
}
static Gfx*emit(u32 t,Gfx*out){out->words.w0=0xa0000000u|(t&0xffffffu);out->words.w1=0x12345678u;return out+1;}
void func_151D5D60(void*cache,s16 view,s32 bytes,Vtx**cursor,u8*fresh){u32 a[]={addr(cache),(u32)(s32)view,(u32)bytes,0xffff0001u,addr(fresh)};
 if(!cursor||fresh)error=1;record(0x151d5d60u,5,a);*cursor=current->success?vertices:0;effect(0x151d5d60u);}
struct17*func_15144B34(s32 view){u32 a[]={(u32)view};record(0x15144b34u,1,a);effect(0x15144b34u);return &camera;}
Gfx*func_15142E24(Gfx*out,void*texture,s32 packed,s32 width,s32 x,s32 y,s32 mode,u8 flags,u8*palette,u8*sync,s32 tail){u32 a[]={addr(out),addr(texture),(u32)packed,(u32)width,(u32)x,(u32)y,(u32)mode,flags,addr(palette),0xffff0002u,(u32)tail};if(!sync||*sync!=1)error=1;record(0x15142e24u,11,a);effect(0x15142e24u);(*sync)++;return emit(0x15142e24u,out);}
Gfx*func_15142B7C(Gfx*out,u32 a0,u32 a1){u32 a[]={addr(out),a0,a1};record(0x15142b7cu,3,a);effect(0x15142b7cu);return emit(0x15142b7cu,out);}
Gfx*func_15142C10(Gfx*out,s32 r,s32 g,s32 b,s32 alpha,u8*sync){u32 a[]={addr(out),(u32)r,(u32)g,(u32)b,(u32)alpha,0xffff0002u};if(!sync||*sync!=2)error=1;record(0x15142c10u,6,a);effect(0x15142c10u);(*sync)++;return emit(0x15142c10u,out);}
Gfx*func_1513F4E4(Gfx*out,u8 mode,u8*sync){u32 a[]={addr(out),mode,0xffff0002u};if(!sync||*sync!=3)error=1;record(0x1513f4e4u,3,a);effect(0x1513f4e4u);(*sync)++;return emit(0x1513f4e4u,out);}
Gfx*func_15142FBC(Gfx*out,u32 a0,u32 a1,u8*sync){u32 a[]={addr(out),a0,a1,0xffff0002u};if(!sync||*sync!=4)error=1;record(0x15142fbcu,4,a);effect(0x15142fbcu);(*sync)++;return emit(0x15142fbcu,out);}
void func_15145548(struct17*endpoint,struct17*delta,struct17*origin,struct17*closest,f32*parameter){u32 a[]={addr(endpoint),0xffff0003u,addr(origin),0xffff0004u,0xffff0005u};u32 v[]={word(endpoint->unk0),word(endpoint->unk4),word(endpoint->unk8),word(delta->unk0),word(delta->unk4),word(delta->unk8),word(origin->unk0),word(origin->unk4),word(origin->unk8)};u32 i;record(0x15145548u,5,a);for(i=0;i<9;i++)if(v[i]!=current->observation[i])error=1;
 closest->unk0=endpoint->unk0+delta->unk0*.25f;closest->unk4=endpoint->unk4+delta->unk4*.25f;closest->unk8=endpoint->unk8+delta->unk8*.25f;*parameter=.25f;
 if(current->mutation&2){delta->unk0=.25f;delta->unk4=-.5f;delta->unk8=1.f;}effect(0x15145548u);}
static void setup(void){u32 i,j;u8*bytes=(u8*)&object;for(i=0;i<sizeof(object);i++)bytes[i]=(u8)((i+32)*29+current->seed*11+0x5a);
 object.state.flags=(u8)current->flags;object.state.count=(s16)current->count;object.state.width=real(current->width);object.state.vertices=primary+4;object.state.bytes=(s32)0x87654321u;
 for(i=0;i<4;i++)object.state.color[i]=(u8)((u32[]){3,129,254,65})[i];
 for(i=0;i<16;i++){s32 index=(s32)i-4;f32 x=index*1.25f,y=1.f+index*.5f,z=-2.f+index*.75f;
  if(current->shape==0)y+=index*index*.125f;if(current->shape==2){x=2.f;y=3.f;z=4.f;}
  primary[i].x=alternate[i].x=11.f;primary[i].y=alternate[i].y=12.f;primary[i].z=alternate[i].z=13.f;
  primary[i].outX=x;primary[i].outY=y;primary[i].outZ=z;alternate[i].outX=x+.25f;alternate[i].outY=y+.5f;alternate[i].outZ=z+.75f;}
 for(i=0;i<32;i++){u8 raw[16];for(j=0;j<16;j++)raw[j]=(u8)((i*16+j+32)*29+current->seed*11+0x5a);
  for(j=0;j<3;j++)vertices[i].v.ob[j]=(s16)((u32)raw[j*2]*256+raw[j*2+1]);vertices[i].v.flag=(u16)((u32)raw[6]*256+raw[7]);
  for(j=0;j<2;j++)vertices[i].v.tc[j]=(s16)((u32)raw[8+j*2]*256+raw[9+j*2]);for(j=0;j<4;j++)vertices[i].v.cn[j]=raw[12+j];}
 for(i=0;i<128;i++){u32 value=0;for(j=0;j<4;j++)value=(value<<8)|(u8)((i*4+j+32)*29+current->seed*11+0x5a);if(i&1)output[i/2].words.w1=value;else output[i/2].words.w0=value;}
 camera.unk0=current->shape==1?0.f:4.f;camera.unk4=current->shape==1?1.f:5.f;camera.unk8=current->shape==1?-2.f:6.f;D_800D2C9C=0x01234567;
 for(i=0;i<8;i++)D_800A4AC8[i]=0x10000000u+i*0x01010101u;
 callIndex=error=0;expectedReturn=output+(current->callCount>2?5:0);if(current->callCount>2){s32 count=(s16)((current->owner[18]<<8)|current->owner[19]);expectedReturn+=count>=2?(count-1)*3:0;}
}
static u32 finish(Gfx*answer){u32 i,j;u8*bytes=(u8*)&object;u32 count=((current->owner[18]<<8)|current->owner[19]);u32 width=(current->owner[40]<<24)|(current->owner[41]<<16)|(current->owner[42]<<8)|current->owner[43];u32 pointer=(current->owner[100]<<24)|(current->owner[101]<<16)|(current->owner[102]<<8)|current->owner[103];
 if(callIndex!=current->callCount||answer!=expectedReturn||object.state.count!=(s16)count||word(object.state.width)!=width||addr(object.state.vertices)!=pointer||object.state.bytes!=(s32)0x87654321u)error=error?error:9000;
 for(i=0;i<sizeof(object);i++)if(!(i>=18&&i<20)&&!(i>=40&&i<44)&&!(i>=100&&i<104)&&!(i>=124&&i<128)&&bytes[i]!=current->owner[i])error=error?error:100+i;
 for(i=0;i<32;i++){u32 v[]={((u32)(u16)vertices[i].v.ob[0]),((u32)(u16)vertices[i].v.ob[1]),((u32)(u16)vertices[i].v.ob[2]),vertices[i].v.flag,((u32)(u16)vertices[i].v.tc[0]),((u32)(u16)vertices[i].v.tc[1]),vertices[i].v.cn[0],vertices[i].v.cn[1],vertices[i].v.cn[2],vertices[i].v.cn[3]};for(j=0;j<10;j++)if(v[j]!=current->vertices[i][j])error=error?error:1000+i*10+j;}
 for(i=0;i<128;i++){u32 value=i&1?output[i/2].words.w1:output[i/2].words.w0;if((i&1)&&output[i/2].words.w0==0x01004008u)value=addr((void*)value);if(value!=current->output[i])error=error?error:2000+i;}
 if(word(camera.unk0)!=current->camera[0]||word(camera.unk4)!=current->camera[1]||word(camera.unk8)!=current->camera[2]||D_800D2C9C!=current->global)error=error?error:3000;
 for(i=0;i<8;i++)if(D_800A4AC8[i]!=current->table[i])error=error?error:4000+i;return error;
}
static Gfx*(*candidates[])(Gfx*,DirectionStripState151A7D6C*,s16)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7,candidate_8};
typedef char Layout[sizeof(void*)==4&&sizeof(DirectionStripState151A7D6C)==128&&__builtin_offsetof(DirectionStripState151A7D6C,vertices)==100&&__builtin_offsetof(DirectionStripState151A7D6C,cache)==108&&__builtin_offsetof(DirectionStripState151A7D6C,bytes)==124&&sizeof(DirectionVertex151A7A90)==24?1:-1];
static int run(void){u32 i,j,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;for(j=0;j<9;j++){Gfx*answer;setup();answer=candidates[j](output,&object.state,(s16)current->view);if(finish(answer)){if(!j){u32 info[]={i,error,callIndex,addr(answer),addr(expectedReturn)};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(info),"d"(sizeof(info)):"memory");return 10;}killed|=1u<<(j-1);}}}return killed==255u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
source=source.replace('current->observation[i])error=1','current->observation[i])error=error?error:7000+i').replace('return killed==255u?0:11;','if(killed!=255u){__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(&killed),"d"(4):"memory");return 11;}return 0;')
path=o/'native-strip.c';path.write_text(source);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-strip'+opt+alias);command=native_command(opt)+[alias,'-Wno-unused-but-set-variable','-fsanitize=float-cast-overflow','-o',str(exe),str(path)];p1=subprocess.run(command,cwd=r,capture_output=True,text=True);assert p1.returncode==0,(p1.stdout,p1.stderr)
  p1=subprocess.run([str(exe)],cwd=r,capture_output=True);assert p1.returncode==0,(opt,alias,p1.returncode,p1.stdout.hex(),p1.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,helpers_modeled=True);(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
