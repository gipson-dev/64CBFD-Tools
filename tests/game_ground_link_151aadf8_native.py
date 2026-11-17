"""SDK32 C execution against the independent reference, with explicit padding limits."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,sys,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_ground_link_151aadf8_recovery as source
from tools.tests import game_ground_link_151aadf8_oracle as g
P,R=source.OUT,source.ROOT
TOKENS={name:0xffffffe0+i for i,name in enumerate(('query','ground','descriptor','ground-tail','payload-destination','payload-source'))}
def main():
 out=P/'native-v42';out.mkdir(exist_ok=False);blob=bytearray();count=0
 for c in g.cases():
  if c.route>=2 and c.seed>12:continue
  initial=g.fixture(c);final,calls=g.reference(initial,c)
  blob+=struct.pack('<4I',*g.asdict(c).values())
  for mem in(initial,final):
   for p,n in((g.OWNER,512),(g.ACTOR,512),(g.OUTPUT,512),(g.TABLE,768)):blob+=g.data(mem,p,n)
   blob+=struct.pack('<4I',*(g.read(mem,g.COEF+4*i)for i in range(3)),g.read(mem,g.MARK))
  blob+=struct.pack('<I',len(calls))
  for t,args,observed in calls:
   a=[TOKENS.get(v,v)if isinstance(v,str)else v for v in args]
   blob+=struct.pack('<16I',t,len(a),*a,*([0]*(14-len(a))))+observed+bytes(32-len(observed))
  blob+=bytes((8-len(calls))*96);count+=1
 data=out/'fixtures.bin';data.write_bytes(blob)
 asm='.pushsection .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin "'+str(data)+'"\n.popsection\n'
 prefix='#include <ultra64.h>\n'+(P/'declarations-v42.txt').read_text()+'''\n
u8 func_151D8E20(void);
s32 func_15045800(f32 *,u16,f32,void *);
struct Event {u32 target,count,args[14];u8 observed[32];};
struct Memory {u8 owner[512],actor[512],output[512],table[768];u32 coefficients[3],marker;};
struct Row {u32 seed,route,mutation,phase;struct Memory initial,final;u32 n;struct Event calls[8];};
extern const struct Row fixture_rows[];
typedef struct {u8 before[0x18];u8 *actor;u8 middle[0x18];f32 height;u8 middle38[0x38];u8 *effect;u8 tail[0x18c];} NativeOwner;
typedef struct {u8 before[0x14];f32 x,y,z;u8 middle[0xf8];f32 height;u8 tail[0xe4];} NativeActor;
typedef char OwnerSize[sizeof(NativeOwner)==512?1:-1];
typedef char ActorSize[sizeof(NativeActor)==512?1:-1];
typedef char PayloadSize[sizeof(GroundLinkPayload151AADF8)==32?1:-1];
typedef char DescriptorSize[sizeof(GroundLinkDescriptor151AADF8)==40?1:-1];
static NativeOwner owner;static NativeActor actor;static u8 output[512];
u8 D_800AB414[768];f32 D_800A8FE0,D_800A8FE4,D_800A8FE8;
static f32 *coefficients[]={&D_800A8FE0,&D_800A8FE4,&D_800A8FE8};
static const struct Row *row;static u32 marker,callno,drawno;static s32 bad;static f32 *query;
static void cp(void *d,const void *s,u32 n){u8 *a=d;const u8 *b=s;for(u32 i=0;i<n;i++)a[i]=b[i];}
static u32 word(f32 f){u32 w;cp(&w,&f,4);return w;}
static f32 real(u32 w){f32 f;cp(&f,&w,4);return f;}
static u32 be(const u8 *p){return((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void setBE(u8 *p,u32 w){for(u32 i=0;i<4;i++)p[i]=(u8)(w>>(24-8*i));}
static void reverseField(u8 *d,const u8 *s,u32 off,u32 n){for(u32 i=0;i<n;i++)d[off+i]=s[off+n-1-i];}
static void payloadBytes(u8 *d,const void *p){
 const u8 *s=p;for(u32 i=0;i<32;i++)d[i]=(i==5||i==6||i==7||i==26||i==27)?0:s[i];
 reverseField(d,s,0,4);for(u32 i=8;i<=16;i+=4)reverseField(d,s,i,4);for(u32 i=20;i<=24;i+=2)reverseField(d,s,i,2);reverseField(d,s,28,4);
 if(be(d)!=(u32)&owner)bad=1;setBE(d,0x30000);
}
static void descriptorBytes(u8 *d,const void *p){
 const u8 *s=p;for(u32 i=0;i<28;i++)d[i]=i==7?0:s[i];reverseField(d,s,0,4);reverseField(d,s,4,2);reverseField(d,s,8,4);reverseField(d,s,12,4);reverseField(d,s,24,4);
}
static void effect(u32 t,u32 n){
 if((row->mutation&1)&&query){for(u32 i=0;i<3;i++)query[i]=((s32)row->seed-128)*((s32)i-1)*.125f+(n+1)*.375f;}
 if((row->mutation&2)&&(t==0x151d8e20||t==0x150ada68))owner.height=(f32)(n+1)*((s32)row->seed-100)*.25f;
 if((row->mutation&4)&&t==0x150ada68){D_800A8FE4=((s32)row->seed-120)*127.5f;D_800A8FE8=(row->seed+1)/512.f;for(u32 i=0;i<768;i++)D_800AB414[i]=(u8)(row->seed+i*17+n);}
 if((row->mutation&8)&&t==0x150ada20){D_800A8FE4=1.25f;D_800A8FE8=.5f;owner.effect=(u8*)0x88888888;}
 if((row->mutation&16)&&t==0x1513c73c)owner.effect=(u8*)0x77777777;
 marker=0x13579bdfu+n*0x10203u+t;
}
static void check(u32 t,const u32 *a,u32 n,const u8 *o,u32 bytes){
 if(callno>=8){bad=1;return;}const struct Event *e=&row->calls[callno];if(e->target!=t||e->count!=n)bad=1;
 for(u32 i=0;i<n;i++)if(a[i]!=e->args[i])bad=1;for(u32 i=0;i<bytes;i++)if(o[i]!=e->observed[i])bad=1;effect(t,callno++);
}
s32 func_15045800(f32 *p,u16 mode,f32 lower,void *ground){
 u8 observed[12];query=p;for(u32 i=0;i<3;i++)setBE(observed+4*i,word(p[i]));if(ground!=&owner.height)bad=1;
 owner.height=((s32)row->seed-128)*.5f;u32 a[]={0xffffffe0,mode,word(lower),0xffffffe1};check(0x15045800,a,4,observed,12);return row->route==1?0:1;
}
u8 func_151D8E20(void){check(0x151d8e20,0,0,0,0);return(u8)row->seed;}
f32 func_150ADA68(void){check(0x150ada68,0,0,0,0);return(row->seed%257)/256.f;}
s32 func_150ADA20(void){u32 w=0x93ac4d71u+row->seed*0x12345u+drawno++*0xabcdef01u;check(0x150ada20,0,0,0,0);return(s32)w;}
u8 *func_1513C73C(s32 desc,u8 kind,u8 variant,s32 ground,f32 x,f32 y,f32 z,f32 scale0,f32 scale1,u8 first,u8 pair,s32 size,u8 slot,s32 context){
 u8 observed[28];descriptorBytes(observed,(void*)(u32)desc);if((void*)(u32)ground!=(u8*)&owner+0x38)bad=1;
 u32 a[]={0xffffffe2,kind,variant,0xffffffe3,word(x),word(y),word(z),word(scale0),word(scale1),first,pair,(u32)size,slot,(u32)context};check(0x1513c73c,a,14,observed,28);return row->route==3?output:0;
}
void *memcpy(void *d,const void *s,u32 n){u8 observed[32];payloadBytes(observed,s);if(d!=output+0xb0||n!=32)bad=1;u32 a[]={0xffffffe4,0xffffffe5,n};check(@COPY@,a,3,observed,32);cp(d,s,n);return d;}
static void ownerBytes(u8 *d){cp(d,&owner,512);setBE(d+0x18,owner.actor==(u8*)&actor?0x40000:(u32)owner.actor);reverseField(d,(const u8*)&owner,0x34,4);setBE(d+0x70,owner.effect==output?0x50000:(u32)owner.effect);}
static void actorBytes(u8 *d){cp(d,&actor,512);setBE(d+0x14,word(actor.x));setBE(d+0x18,word(actor.y));setBE(d+0x1c,word(actor.z));setBE(d+0x118,word(actor.height));}
static int failure(u32 stage,u32 index){u32 v[]={(u32)(row-fixture_rows),stage,index,callno};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(v),"d"(16):"memory");return 3;}
'''.replace('@COPY@',hex(g.COPY))
 prefix+='\n__asm__('+json.dumps(asm)+');\n'
 body=(P/'body-v42.txt').read_text().replace('func_151AADF8','invoke',1)
 suffix='''
static int run(void){
 for(u32 k=0;k<@COUNT@;k++){
  row=&fixture_rows[k];cp(&owner,row->initial.owner,512);cp(&actor,row->initial.actor,512);cp(output,row->initial.output,512);cp(D_800AB414,row->initial.table,768);
  owner.actor=(u8*)&actor;u32 heightBits=be(row->initial.owner+0x34);cp(&owner.height,&heightBits,4);owner.effect=be(row->initial.owner+0x70)?output:0;
  actor.x=real(be(row->initial.actor+0x14));actor.y=real(be(row->initial.actor+0x18));actor.z=real(be(row->initial.actor+0x1c));actor.height=real(be(row->initial.actor+0x118));
  for(u32 i=0;i<3;i++)*coefficients[i]=real(row->initial.coefficients[i]);marker=row->initial.marker;callno=drawno=bad=0;query=0;
  invoke((u8*)&owner);if(bad||callno!=row->n||marker!=row->final.marker)return failure(1,bad);
  u8 b[512];ownerBytes(b);for(u32 i=0;i<512;i++)if(b[i]!=row->final.owner[i])return failure(2,i);
  actorBytes(b);for(u32 i=0;i<512;i++)if(b[i]!=row->final.actor[i])return failure(3,i);
  cp(b,output,512);if(row->route==3){u8 p[32];payloadBytes(p,output+0xb0);cp(b+0xb0,p,32);}
  for(u32 i=0;i<512;i++)if(i!=0xb5&&i!=0xb6&&i!=0xb7&&i!=0xca&&i!=0xcb&&b[i]!=row->final.output[i])return failure(4,i);
  for(u32 i=0;i<768;i++)if(D_800AB414[i]!=row->final.table[i])return failure(5,i);
  for(u32 i=0;i<3;i++)if(word(*coefficients[i])!=row->final.coefficients[i])return failure(6,i);
 }return 0;
}
'''.replace('@COUNT@',str(count))+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 controls={'notification-byte':('oscillator[4] = 1','oscillator[5] = 1'),'raised-height':('+ 100.0f','+ 101.0f'),'factory-kind':(')&descriptor, 7, 1',')&descriptor, 8, 1'),'descriptor-flags':('descriptor.flags = 0x60300','descriptor.flags = 0x60301'),'saved-height':('position[1] = *(f32 *)(owner + 0x34)','position[1] = 0.0f')}
 runs=[]
 positives={'v42'}
 variants=[('v42',body)]
 variants += [(n,body.replace(a,b,1))for n,(a,b)in controls.items()]
 variants += [('unsequenced-draws',source.PIN['variants']['v48']['body'].replace('func_151AADF8','invoke',1))]
 for label,variant in variants:
  assert label=='v42'or variant!=body,label
  for opt in(('-O0','-O2','-O3')if label in positives else('-O2',)):
   name=label+opt;src=out/(name+'.c');exe=src.with_suffix('');src.write_text(prefix+variant+suffix);start=time.monotonic()
   cmd=native_command(opt)+['-fstrict-aliasing','-fno-builtin','-Wno-unused-function',str(src),'-o',str(exe)]
   q=subprocess.run(cmd,cwd=R,capture_output=True,text=True);assert q.returncode==0,q.stderr
   result=subprocess.run([str(exe)],cwd=R,capture_output=True,timeout=20);expected=0 if label in positives else 3;assert result.returncode==expected,(name,result.returncode,expected,result.stderr.hex())
   record=dict(label=label,opt=opt,exit_code=result.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),seconds=round(time.monotonic()-start,3));runs.append(record);print(json.dumps(record),flush=True)
 report=dict(cases=count,runs=runs,passes=True,source_installed=source.installed(),c_match_credit=0,padding_uncredited=True)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(runs),passes=True)),flush=True)
if __name__=='__main__':main()
