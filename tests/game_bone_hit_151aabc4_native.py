"""SDK32 execution of the complete selected C with disjoint typed outputs."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,sys,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_bone_hit_151aabc4_recovery as source
from tools.tests import game_bone_hit_151aabc4_oracle as g
R,P=source.ROOT,source.OUT
TOKENS={name:0xffffffe0+i for i,name in enumerate(('matrix1','matrix2','bone-output','surface','actor','query','vertices','position','angles','trail'))}
def make_source():
 out=P/'native-v13';out.mkdir(exist_ok=False);blob=bytearray();count=0
 for c in g.cases():
  if not c.native:continue
  initial=g.fixture(c);final,calls=g.reference(initial,c);assert len(calls)<=6
  blob+=struct.pack('<10I',*g.asdict(c).values(),*g.bone_values(c))
  for memory in(initial,final):
   blob+=g.data(memory,g.A,512)+g.data(memory,g.TABLE,4)+struct.pack('<6I',*(g.read(memory,g.COEF+4*i)for i in range(5)),g.read(memory,g.MARK))
   if memory is final:blob+=struct.pack('<I',len(calls))
  for target,args,observed in calls:
   a=tuple(TOKENS.get(v,v)if isinstance(v,str)else v for v in args)
   blob+=struct.pack('<9I',target,len(a),*a,*([0]*(7-len(a))))+observed+bytes(112-len(observed))
  blob+=bytes((6-len(calls))*148);count+=1
 data=out/'fixtures.bin';data.write_bytes(blob);asm='.pushsection .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin "'+str(data)+'"\n.popsection\n'
 prefix='#include <ultra64.h>\n'+source.PIN['declarations']+'\n'
 prefix+='''
struct Event {u32 target,count,args[7];u8 observed[112];};
struct Row {u32 seed,bone,route,hit,mutation,phase,native,point[3];u8 initialActor[512],initialTable[4];u32 initialCoef[5],initialMark;u8 finalActor[512],finalTable[4];u32 finalCoef[5],finalMark,n;struct Event calls[6];};
extern const struct Row fixture_rows[];
typedef struct {u8 before[0x1d4];u8 *matrix;u8 after[0x28];} NativeActor;
typedef char ActorSize[(sizeof(NativeActor)==512)?1:-1];
typedef char SurfaceSize[(sizeof(HeightResult71820)==36)?1:-1];
typedef char TrailSize[(sizeof(BoneHitTrail151AABC4)==68)?1:-1];
typedef char AngleSize[(sizeof(BoneHitAngles151AABC4)==8)?1:-1];
static NativeActor actor;static u8 matrix1[64],matrix2[64];
u8 D_800A8F70[4];
f32 D_800A8FCC,D_800A8FD0,D_800A8FD4,D_800A8FD8,D_800A8FDC;
static f32 *coefficients[]={&D_800A8FCC,&D_800A8FD0,&D_800A8FD4,&D_800A8FD8,&D_800A8FDC};
static const struct Row *row;static u32 marker,callno;static s32 bad;
static f32 *boneOutput;static HeightResult71820 *surfaceOutput;static BoneHitPosition151AABC4 *hitOutput;
static void cp(void *d,const void *s,u32 n){u8 *a=d;const u8 *b=s;for(u32 i=0;i<n;i++)a[i]=b[i];}
static u32 word(f32 value){u32 v;cp(&v,&value,4);return v;}
static f32 real(u32 value){f32 v;cp(&v,&value,4);return v;}
static u32 be(const u8 *p){return((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void setBE(u8 *p,u32 value){for(u32 i=0;i<4;i++)p[i]=(u8)(value>>(24-8*i));}
static void reverseField(u8 *d,const u8 *s,u32 off,u32 n){for(u32 i=0;i<n;i++)d[off+i]=s[off+n-1-i];}
static void surfaceBytes(u8 *dst,HeightResult71820 *p){
 const u8 *s=(const u8*)p;cp(dst,s,36);reverseField(dst,s,0,4);for(u32 i=4;i<=22;i+=2)reverseField(dst,s,i,2);reverseField(dst,s,24,4);reverseField(dst,s,30,2);reverseField(dst,s,32,4);
}
static void fillSurface(HeightResult71820 *p,u32 ordinal){
 u8 b[36],n[36];for(u32 i=0;i<36;i++)b[i]=(u8)(i*11+row->seed+ordinal*7);setBE(b,word(((s32)row->seed-128)*.25f+ordinal*2.0f));
 cp(n,b,36);reverseField(n,b,0,4);for(u32 i=4;i<=22;i+=2)reverseField(n,b,i,2);reverseField(n,b,24,4);reverseField(n,b,30,2);reverseField(n,b,32,4);cp(p,n,36);
}
static void positionBytes(u8 *dst,const void *p){const u8 *s=p;for(u32 i=0;i<12;i++)dst[i]=s[(i&~3u)+3-(i&3)];}
static void angleBytes(u8 *dst,void *p){const u8 *s=p;for(u32 i=0;i<8;i++)dst[i]=s[(i&~1u)+1-(i&1)];}
static void trailBytes(u8 *dst,void *p){
 const u8 *s=p;for(u32 i=0;i<68;i++)dst[i]=(53<=i&&i<56)?0:s[i];
 for(u32 i=0;i<=32;i+=4)reverseField(dst,s,i,4);for(u32 i=36;i<=50;i+=2)reverseField(dst,s,i,2);
 reverseField(dst,s,56,4);reverseField(dst,s,60,2);reverseField(dst,s,62,2);reverseField(dst,s,64,4);
}
static void effect(u32 t,u32 ordinal){
 marker=0x13579bdfu+ordinal*0x10203u+t;
 if((row->mutation&1)&&t==0x151d8e20){actor.matrix=matrix2;for(u32 i=0;i<4;i++)D_800A8F70[i]=(u8)(row->seed+i*17+33);}
 if((row->mutation&2)&&boneOutput){for(u32 i=0;i<3;i++)boneOutput[i]=(f32)(ordinal+1)*((s32)i-1)*.375f;}
 if((row->mutation&4)&&surfaceOutput)fillSurface(surfaceOutput,ordinal+11);
 if((row->mutation&8)&&hitOutput){for(u32 i=0;i<3;i++)hitOutput->xyz[i]=(f32)(ordinal+1)*(i+1)*-.5f;}
 if((row->mutation&16)&&t==0x151dbcbc){for(u32 i=0;i<5;i++)*coefficients[i]=((s32)ordinal+(s32)i-5)*.125f;}
}
static void check(u32 t,const u32 *args,u32 n,const u8 *observed,u32 bytes){
 if(callno>=6){bad=1;return;}const struct Event *ev=&row->calls[callno];if(ev->target!=t||ev->count!=n)bad=1;
 for(u32 i=0;i<n;i++)if(args[i]!=ev->args[i])bad=1;for(u32 i=0;i<bytes;i++)if(observed[i]!=ev->observed[i])bad=1;effect(t,callno++);
}
u8 func_151D8E20(void){check(0x151d8e20,0,0,0,0);return(u8)row->seed;}
void func_15142314(u8 *m,s32 bone,f32 *out){u32 matrix=m==matrix1?0xffffffe0u:m==matrix2?0xffffffe1u:0;if(!matrix)bad=1;boneOutput=out;for(u32 i=0;i<3;i++)out[i]=real(row->point[i]);u32 args[]={matrix,(u32)bone,0xffffffe2};check(0x15142314,args,3,0,0);}
void func_1504715C(HeightResult71820 *p,HeightActor71820 *a){if((void*)a!=(void*)&actor)bad=1;surfaceOutput=p;fillSurface(p,callno);u32 args[]={0xffffffe3,0xffffffe4};check(0x1504715c,args,2,0,0);}
s32 func_1504697C(f32 *q,u16 selector,f32 lower,HeightResult71820 *p){u8 observed[48];positionBytes(observed,q);surfaceBytes(observed+12,p);if(p!=surfaceOutput)bad=1;fillSurface(p,callno);u32 args[]={0xffffffe5,selector,word(lower),0xffffffe3};check(0x1504697c,args,4,observed,48);return(s32)row->hit;}
void func_151DBCBC(u8 selector,f32 size,s16 life,s32 vertices,void *point,u8 slot,s32 context){u8 observed[36],surface[36];if((void*)(u32)vertices!=(void*)surfaceOutput->vertices)bad=1;surfaceBytes(surface,surfaceOutput);cp(observed,surface+4,18);positionBytes(observed+18,point);hitOutput=point;u32 args[]={selector,word(size),(u32)(s32)life,0xffffffe6,0xffffffe7,slot,(u32)context};check(0x151dbcbc,args,7,observed,30);}
void func_15153F18(void *angles,void *trail,s32 surface,s32 slot,s32 context){u8 observed[112];if((void*)(u32)surface!=(void*)surfaceOutput)bad=1;angleBytes(observed,angles);trailBytes(observed+8,trail);surfaceBytes(observed+76,surfaceOutput);u32 args[]={0xffffffe8,0xffffffe9,0xffffffe3,(u32)slot,(u32)context};check(0x15153f18,args,5,observed,112);}
static void actorBytes(u8 *out){cp(out,&actor,512);setBE(out+0x1d4,actor.matrix==matrix1?0x50000:actor.matrix==matrix2?0x60000:0);}
'''
 prefix+='\n__asm__('+json.dumps(asm)+');\n'
 body=source.PIN['body'].replace('func_151AABC4','invoke',1)
 suffix='''
static int run(void){
 for(u32 i=0;i<@COUNT@;i++){
  row=&fixture_rows[i];cp(&actor,row->initialActor,512);actor.matrix=be(row->initialActor+0x1d4)==0x50000?matrix1:0;cp(D_800A8F70,row->initialTable,4);
  for(u32 j=0;j<5;j++)*coefficients[j]=real(row->initialCoef[j]);marker=row->initialMark;callno=0;bad=0;boneOutput=0;surfaceOutput=0;hitOutput=0;
  invoke(row->route==1?0:(u8*)&actor,(u8)row->bone);
  if(bad||callno!=row->n||marker!=row->finalMark)return 3;
  for(u32 j=0;j<5;j++)if(word(*coefficients[j])!=row->finalCoef[j])return 3;
  for(u32 j=0;j<4;j++)if(D_800A8F70[j]!=row->finalTable[j])return 3;
  u8 bytes[512];actorBytes(bytes);for(u32 j=0;j<512;j++)if(bytes[j]!=row->finalActor[j])return 3;
 }return 0;
}
'''.replace('@COUNT@',str(count))+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return out,prefix,body,suffix,count
def main():
 out,prefix,body,suffix,count=make_source();runs=[]
 controls={'upper-bound':('+ 50.0f','+ 51.0f'),'matrix-offset':('actor + 0x1D4','actor + 0x1D0'),'hit-position':('trail.position = position','trail.position = bonePosition'),'count-value':('trail.countBase = 3','trail.countBase = 4'),'selector-field':('trail.selector = selector','trail.selector = 0'),'query-zero':('if (func_1504697C','if (!func_1504697C')}
 for label,variant in [('selected',body)]+[(n,body.replace(a,b,1))for n,(a,b)in controls.items()]:
  assert label=='selected'or variant!=body,label
  for opt in(('-O0','-O2','-O3')if label=='selected'else('-O2',)):
   path=out/(label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+variant+suffix);started=time.monotonic()
   q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-mstackrealign',str(path),'-o',str(exe)],cwd=R,capture_output=True,text=True)
   (out/(path.stem+'-diagnostics.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stdout and not q.stderr,(label,opt,q.stdout,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if label=='selected'else 3),(label,opt,q.returncode,q.stderr)
   row=dict(label=label,opt=opt,exit_code=q.returncode,seconds=round(time.monotonic()-started,3),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());runs.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_profile=count,runs=runs,native32=True,SDK_types=True,strict_aliasing=True,UB_traps=True,public_actor_bytes=512,trail_defined_bytes=65,angle_defined_bytes=8,padding_uncredited_bytes=3,source_installed=source.installed(),c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(runs),passes=True)),flush=True)
if __name__=='__main__':main()
