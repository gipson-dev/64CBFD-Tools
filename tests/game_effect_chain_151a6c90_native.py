"""Complete SDK32 C execution against independent effect-chain fixtures."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_effect_chain_151a6c90_recovery as source
from tools.tests import game_effect_chain_151a6c90_oracle as g
R,P=source.ROOT,source.OUT
def actor_bytes(m):
 b=bytearray(g.data(m,g.A,64))
 for off in(20,24,28):b[off:off+4]=b[off:off+4][::-1]
 return bytes(b)
def make_source():
 out=P/'native-v2';out.mkdir(exist_ok=False);blob=bytearray();count=0
 for c in g.cases():
  initial=g.fixture(c);final,calls=g.reference(initial,c);assert len(calls)==9
  blob+=struct.pack('<5I',*g.asdict(c).values())+actor_bytes(initial)+struct.pack('<I',g.read(initial,g.COEF))+actor_bytes(final)+struct.pack('<3I',g.read(final,g.COEF),g.read(final,g.MARK),len(calls))
  for target,args,observed in calls:
   args=tuple(0xfffffff0 if v=='packet'else 0xfffffff1 if v=='position'else v for v in args)
   blob+=struct.pack('<10I',target,len(args),*args,*([0]*(8-len(args))))+observed+bytes(92-len(observed))
  count+=1
 data=out/'fixtures.bin';data.write_bytes(blob)
 asm='.pushsection .rodata\n.balign 4\n.global fixture_rows\nfixture_rows:\n.incbin "'+str(data)+'"\n.popsection\n'
 prefix='#include <ultra64.h>\n'+source.PIN['declarations']+'\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\n'
 prefix+='''
struct Event {u32 target,count,args[8];u8 observed[92];};
struct Row {u32 seed,slot,context,mutation,phase;u8 initial[64];u32 coef;u8 final[64];u32 finalCoef,finalMark,n;struct Event calls[9];};
extern const struct Row fixture_rows[];
typedef struct {u8 pad0[20];BurstPosition1A6C90 position;u8 pad20[32];} NativeActor;
typedef char PacketSize[(sizeof(ActorBurstPacket1A6C90)==92)?1:-1];
typedef char PositionSize[(sizeof(BurstPosition1A6C90)==12)?1:-1];
typedef char ActorSize[(sizeof(NativeActor)==64)?1:-1];
static NativeActor actor;
f32 D_800A8DB0;
static const struct Row *row;
static u32 marker,callno,rngno;
static s32 bad;
static ActorBurstPacket1A6C90 *retainedPacket;
static BurstPosition1A6C90 *retainedPosition;
static void cp(void *d,const void *s,u32 n){u8 *a=d;const u8 *b=s;for(u32 i=0;i<n;i++)a[i]=b[i];}
static u32 word(f32 value){u32 v;cp(&v,&value,4);return v;}
static f32 real(u32 value){f32 v;cp(&v,&value,4);return v;}
static s32 hole(u32 i){return i==2||i==3||i==0x12||i==0x13||i==0x5a||i==0x5b;}
static void positionBytes(u8 *dst,BurstPosition1A6C90 *p){
 const u8 *s=(const u8*)p;for(u32 i=0;i<12;i++)dst[i]=s[(i&~3u)+(3-(i&3))];
}
static void packetBytes(u8 *dst,ActorBurstPacket1A6C90 *p){
 static const u8 w[]={4,8,12,20,32,36,40,44,48,52,56,60,64,68,72,76,80};
 static const u8 h[]={0,16,24,26,28,30,86,88};const u8 *s=(const u8*)p;
 for(u32 i=0;i<92;i++)dst[i]=hole(i)?0:s[i];
 for(u32 j=0;j<sizeof(w);j++)for(u32 i=0;i<4;i++)dst[w[j]+i]=s[w[j]+3-i];
 for(u32 j=0;j<sizeof(h);j++)for(u32 i=0;i<2;i++)dst[h[j]+i]=s[h[j]+1-i];
}
static void effect(u32 t,u32 ordinal){
 marker=0x13579bdfu+ordinal*0x10203u+t;
 if(row->mutation&1){actor.position.x=(ordinal+1)*.375f;actor.position.y=(ordinal+1)*2*.375f;actor.position.z=(ordinal+1)*3*.375f;}
 if(row->mutation&2)D_800A8DB0=((s32)ordinal-5)*.125f;
 if((row->mutation&4)&&retainedPosition){retainedPosition->x=-(f32)(ordinal+1)*.5f;retainedPosition->y=0.0f;retainedPosition->z=(ordinal+1)*.5f;}
 if((row->mutation&8)&&retainedPacket){u8 *p=(u8*)retainedPacket;for(u32 i=0;i<92;i++)if(!hole(i))p[i]=(u8)(i*7+ordinal*13+row->seed);}
}
static void check(u32 t,const u32 *args,u32 n,const u8 *observed,u32 bytes){
 if(callno>=9){bad=1;return;}const struct Event *event=&row->calls[callno];
 if(event->target!=t||event->count!=n)bad=1;
 for(u32 i=0;i<n;i++)if(args[i]!=event->args[i])bad=1;
 for(u32 i=0;i<bytes;i++)if(observed[i]!=event->observed[i])bad=1;
 effect(t,callno++);
}
s32 func_150ADA20(void){static const u32 values[]={0,1,3,4,0x7fffffff,0x80000000,0xfffffffe,0xffffffff};u32 v=values[(row->seed+3*rngno++)%8];check(0x150ada20,0,0,0,0);return(s32)v;}
f32 func_150ADA68(void){static const u32 values[]={0,0x3e800000,0x3f000000,0x3f7fffff,0xbf000000,0x40000000};u32 v=values[row->seed%6];check(0x150ada68,0,0,0,0);return real(v);}
void func_151A6F00(ActorBurstPacket1A6C90 *p,u8 kind,u8 slot,s32 ctx){u8 b[92];packetBytes(b,p);retainedPacket=p;u32 a[]={0xfffffff0,kind,slot,(u32)ctx};check(0x151a6f00,a,4,b,92);}
void func_151D5334(BurstPosition1A6C90 *p,f32 a,f32 b,f32 c,s32 n,s32 slot,s32 ctx){u8 out[12];positionBytes(out,p);retainedPosition=p;u32 args[]={0xfffffff1,word(a),word(b),word(c),(u32)n,(u32)slot,(u32)ctx};check(0x151d5334,args,7,out,12);}
void func_151D3FF4(BurstPosition1A6C90 *p,u8 slot,s32 ctx){u8 out[12];positionBytes(out,p);retainedPosition=p;u32 args[]={0xfffffff1,slot,(u32)ctx};check(0x151d3ff4,args,3,out,12);}
void func_151D5514(BurstPosition1A6C90 *p,u8 slot,s32 ctx){u8 out[12];positionBytes(out,p);retainedPosition=p;u32 args[]={0xfffffff1,slot,(u32)ctx};check(0x151d5514,args,3,out,12);}
void *func_151541B8(BurstPosition1A6C90 *p,f32 a,f32 b,f32 c,f32 d,u8 slot,s32 ctx){u8 out[12];positionBytes(out,p);retainedPosition=p;u32 args[]={0xfffffff1,word(a),word(b),word(c),word(d),slot,(u32)ctx};check(0x151541b8,args,7,out,12);return(void*)0xe5000007;}
void func_151D5404(BurstPosition1A6C90 *p,f32 a,f32 b,f32 c,s32 d,s32 e,s32 f,s32 h){u8 out[12];positionBytes(out,p);retainedPosition=p;u32 args[]={0xfffffff1,word(a),word(b),word(c),(u32)d,(u32)e,(u32)f,(u32)h};check(0x151d5404,args,8,out,12);}
'''
 prefix+='\n__asm__('+json.dumps(asm)+');\n'
 body=source.PIN['body'].replace('func_151A6C90','invoke',1)
 suffix='''
static int run(void){
 for(u32 i=0;i<@COUNT@;i++){
  row=&fixture_rows[i];cp(&actor,row->initial,64);D_800A8DB0=real(row->coef);marker=callno=rngno=0;bad=0;retainedPacket=0;retainedPosition=0;
  invoke((u8*)&actor,(u8)row->slot,(s32)row->context);
  if(bad||callno!=row->n||word(D_800A8DB0)!=row->finalCoef||marker!=row->finalMark)return 3;
  for(u32 j=0;j<64;j++)if(((u8*)&actor)[j]!=row->final[j])return 3;
 }return 0;
}
'''.replace('@COUNT@',str(count))
 suffix+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return out,prefix,body,suffix,count
def main():
 out,prefix,body,suffix,count=make_source();results=[]
 controls={'count':(' & 3) + 6',' & 3) + 7'),'duration':('duration = 80','duration = 81'),'snapshot':('actor + 0x14','actor + 0x10'),'kind':('&packet, 0,','&packet, 1,'),'rate':('0.000987166888f','0.000987166772f'),'random-range':('random % 56','random % 55')}
 for name,variant in [('selected',body)]+[(n,body.replace(a,b,1))for n,(a,b)in controls.items()]:
  assert name=='selected'or variant!=body,name
  for opt in(('-O0','-O2','-O3')if name=='selected'else('-O2',)):
   p=out/(name+opt+'.c');exe=p.with_suffix('');p.write_text(prefix+variant+suffix)
   start=time.monotonic();q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-mstackrealign',str(p),'-o',str(exe)],cwd=R,capture_output=True,text=True)
   (out/(p.stem+'-diagnostics.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stdout and not q.stderr,(name,opt,q.stdout,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
   item=dict(label=name,opt=opt,exit_code=q.returncode,seconds=round(time.monotonic()-start,3),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());results.append(item);print(json.dumps(item),flush=True)
 report=dict(cases_per_profile=count,runs=results,native32=True,SDK_types=True,strict_aliasing=True,UB_traps=True,public_actor_bytes=64,packet_defined_bytes=86,padding_uncredited_bytes=6,source_installed=source.installed(),c_match_credit=0)
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(results),passes=True)),flush=True)
if __name__=='__main__':main()
