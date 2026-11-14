from pathlib import Path
import json,subprocess
from tools.tests import game_radial_ground_emitter_151a9834_behavior as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-radial-ground-emitter-151a9834-screen';s=(o/'selected.c').read_text();a=s.index('extern f32 D_800A8F68,');z=s.index('/* Scatter ground-tested',a);head=s[a:z];body=s[z:]
snapshot=body.replace('    f32 first, factor;','    f32 first, factor, ox, oz;').replace('            first = func_150ADA68();','            ox = origin[0]; oz = origin[2];\n            first = func_150ADA68();').replace('point[0] += origin[0]','point[0] += ox').replace('point[2] += origin[2]','point[2] += oz')
callback=body.replace('    f32 first, factor;','    f32 first, factor;\n    void (*cached)(struct17 *,s32,u8 *,u8,s32);').replace('            if (func_15046C80','            cached = D_8008FA60[selector];\n            if (func_15046C80').replace('D_8008FA60[selector](&submitted','cached(&submitted')
bad={'reset_working_height':body.replace('            first = func_150ADA68();','            point[1] = origin[1];\n            first = func_150ADA68();'),
 'omit_angle_doubling':body.replace('(first + first) * factor','first * factor'),
 'wrong_radius_sample':body.replace('second * radius','first * radius').replace('            func_1514373C','            (void)second;\n            func_1514373C'),
 'snapshot_origin_before_helpers':snapshot,
 'truncate_ground_result':body.replace('if (func_15046C80','if ((u8)func_15046C80'),
 'wrong_submitted_height':body.replace('submitted.unk4 = ground->height','submitted.unk4 = point[1]'),
 'snapshot_callback_before_query':callback}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
height=s[s.index('typedef struct HeightResult71820'):s.index('\n',s.index('typedef struct HeightResult71820'))]
code='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\n'+height+'\nf32 func_150ADA68(void);\ns32 func_15046C80(f32*,u16,f32,HeightResult71820*);\n'+head+'\n'.join(v.replace('func_151A9834','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 ground,count,selector,channel,context,minimum,radius,hits,answer,mutation,seed,tag;u32 planes[6],queries[24],callbackValues[12],callbackKinds[3],queryCount,callbackCount,origin[3],height,factor,finalTag,table[2],groundFields[5];} Case;
static const Case cases[]={
'''
rows=[];arr=lambda xs:'{'+','.join(hex(b.u32(x))+'u' for x in xs)+'}';kind={b.CB0:0,b.CB1:1,b.ALT:2}
for c in b.cases():
 if c.phase:continue
 m,calls,obs=b.reference(b.fixture(c),c);planes=[v for t,a in calls if t==b.PLANE for v in a[:2]];queries=[];callbackValues=[];callbackKinds=[]
 for t,a in obs:
  if t==b.GROUND:
   vector,raw=a;queries.extend(vector);queries.extend((int.from_bytes(raw[0:4],'big'),int.from_bytes(raw[24:28],'big'),raw[28],raw[29],int.from_bytes(raw[32:36],'big')))
  else:callbackValues.extend((*a[0],a[1] if a[1] is not None else 0));callbackKinds.append(kind[t])
 assert len(queries)<=24 and len(callbackValues)<=12
 scalars=(int(bool(c.ground)),c.count,c.selector,c.channel,c.context,c.minimum,c.radius,c.hits,c.answer,c.mutation,c.seed,int(bool(c.tag)))
 origin=b.vector(m,c.origin);g=b.homes(c)[2];gf=(b.read(m,g),b.read(m,g+24),m[g+28],m[g+29],b.read(m,g+32));tables=[kind[b.read(m,b.TABLE+4*i)] for i in range(2)]
 rows.append('{'+','.join(hex(b.u32(v))+'u' for v in scalars)+','+','.join(arr(v or [0]) for v in (planes,queries,callbackValues,callbackKinds))+','+str(len(queries)//8)+','+str(len(callbackKinds))+','+arr(origin)+','+hex(b.read(m,b.HEIGHT))+'u,'+hex(b.read(m,b.FACTOR))+'u,'+hex(m[c.tag] if c.tag else 0)+'u,'+arr(tables)+','+arr(gf)+'}')
code+=',\n'.join(rows)+'\n};\n'+r'''
typedef char Layout[sizeof(void*)==4&&sizeof(HeightResult71820)==36&&__builtin_offsetof(HeightResult71820,metadata)==24&&__builtin_offsetof(HeightResult71820,value)==32?1:-1];
static const Case*current;static f32 origin[3],*lastPoint;static HeightResult71820 supplied,*currentGround;static u8 tag[4];static u32 draws,planes,queries,callbacks,error;
f32 D_800A8F68,D_800A8F6C;
static f32 real(u32 v){Bits b;b.u=v;return b.f;}static u32 word(f32 v){Bits b;b.f=v;return b.u;}
static void callback0(struct17*,s32,u8*,u8,s32);static void callback1(struct17*,s32,u8*,u8,s32);static void alternate(struct17*,s32,u8*,u8,s32);
void(*D_8008FA60[])(struct17*,s32,u8*,u8,s32)={callback0,callback1};
static void effect(u32 stage,u32 ordinal){if(current->mutation&1){
 if(stage==0){D_800A8F6C=9.f;D_800A8F68=17.f;origin[1]+=10.f;}
 if(stage==1){origin[0]+=7.f;origin[2]-=3.f;}
 if(stage==2)D_8008FA60[current->selector&255]=ordinal&1?alternate:callback1;
 }if((current->mutation&2)&&stage==3){origin[0]+=1.f;origin[2]-=2.f;lastPoint[1]+=1.f;currentGround->height+=4.f;D_8008FA60[current->selector&255]=callback0;if(current->tag)tag[0]^=0x33;}}
f32 func_150ADA68(void){static const f32 values[]={.125f,.75f,.5f,-.25f,0.f,1.f};f32 value=values[(draws+current->seed)%6];effect(0,draws);draws++;return value;}
void func_1514373C(f32 angle,f32 radius,f32*x,f32*z){if(planes>=current->queryCount||word(angle)!=current->planes[2*planes]||word(radius)!=current->planes[2*planes+1]||z!=x+2)error=1;*x=radius*(angle*.25f-.25f);*z=radius*(angle*.125f+.5f);lastPoint=x;effect(1,planes);planes++;}
s32 func_15046C80(f32*point,u16 mode,f32 minimum,HeightResult71820*ground){u32 values[8],i,index=queries;values[0]=word(point[0]);values[1]=word(point[1]);values[2]=word(point[2]);values[3]=word(ground->height);values[4]=ground->metadata;values[5]=ground->flags;values[6]=ground->state;values[7]=(u32)ground->value;
 if(index>=current->queryCount||point!=lastPoint||mode||word(minimum)!=current->minimum||(current->ground&&ground!=&supplied)||(currentGround&&ground!=currentGround))error=1;
 for(i=0;i<8;i++)if(values[i]!=current->queries[index*8+i])error=1;currentGround=ground;point[0]+=.25f;point[1]+=.5f;point[2]-=.75f;ground->height=point[1]-2.f;ground->metadata^=0x10203;ground->flags^=0x80;ground->state++;ground->value=(s32)(0xabc00000u+index);effect(2,index);queries++;return current->hits>>index&1?(s32)current->answer:0;}
static void callback(u32 kind,struct17*p,s32 ground,u8*data,u8 channel,s32 context){u32 index=callbacks;u32 values[4];values[0]=word(p->unk0);values[1]=word(p->unk4);values[2]=word(p->unk8);values[3]=data?*data:0;
 if(index>=current->callbackCount||current->callbackKinds[index]!=kind||(u32)ground!=(u32)currentGround||data!=(current->tag?tag:0)||channel!=(current->channel&255)||(u32)context!=current->context||&p->unk0==lastPoint)error=1;
 if(values[0]!=current->callbackValues[index*4]||values[1]!=current->callbackValues[index*4+1]||values[2]!=current->callbackValues[index*4+2]||values[3]!=current->callbackValues[index*4+3])error=1;effect(3,queries-1);callbacks++;}
static void callback0(struct17*p,s32 g,u8*t,u8 c,s32 x){callback(0,p,g,t,c,x);}static void callback1(struct17*p,s32 g,u8*t,u8 c,s32 x){callback(1,p,g,t,c,x);}static void alternate(struct17*p,s32 g,u8*t,u8 c,s32 x){callback(2,p,g,t,c,x);}
static void(*candidates[])(f32*,f32,f32,HeightResult71820*,s32,u8,u8*,u8,s32)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7};
static u32 tableKind(u32 index){return D_8008FA60[index]==callback0?0:D_8008FA60[index]==callback1?1:2;}
static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
 for(j=0;j<8;j++){origin[0]=1.25f;origin[1]=4.f;origin[2]=-2.5f;supplied.height=2.25f;supplied.metadata=0x12345678;supplied.flags=0xa5;supplied.state=0x3c;supplied.value=(s32)0x87654321u;for(k=0;k<9;k++)supplied.vertices[k]=(s16)(100+k);supplied.pad16=0x1122;supplied.pad1E=0x3344;tag[0]=(u8)(current->seed*11+0x5a);D_800A8F68=real(0x47c34ff3);D_800A8F6C=real(0x40490fdb);D_8008FA60[0]=callback0;D_8008FA60[1]=callback1;lastPoint=0;currentGround=0;draws=planes=queries=callbacks=error=0;
  candidates[j](origin,real(current->minimum),real(current->radius),current->ground?&supplied:0,(s32)current->count,(u8)current->selector,current->tag?tag:0,(u8)current->channel,(s32)current->context);
  if(queries!=current->queryCount||planes!=queries||draws!=queries*2||callbacks!=current->callbackCount||word(origin[0])!=current->origin[0]||word(origin[1])!=current->origin[1]||word(origin[2])!=current->origin[2]||word(D_800A8F68)!=current->height||word(D_800A8F6C)!=current->factor||(current->tag&&tag[0]!=current->finalTag)||tableKind(0)!=current->table[0]||tableKind(1)!=current->table[1])error=1;
  if(current->ground){if(word(supplied.height)!=current->groundFields[0]||supplied.metadata!=current->groundFields[1]||supplied.flags!=current->groundFields[2]||supplied.state!=current->groundFields[3]||(u32)supplied.value!=current->groundFields[4]||supplied.pad16!=0x1122||supplied.pad1E!=0x3344)error=1;for(k=0;k<9;k++)if(supplied.vertices[k]!=(s16)(100+k))error=1;}
  if(error){if(!j)return 10;killed|=1u<<(j-1);}
 }
}return killed==127u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-radial-ground-emitter.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-radial-ground-emitter'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,typed_disjoint_inputs=True,uninitialized_padding_not_compared=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
