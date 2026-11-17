"""SDK32 execution of complete typed C against independent BE fixtures."""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_region_emitter_151a5660_oracle as g
O=source.OUT;R=source.ROOT
COUNT=128;BLOCKS=((g.E,512),(g.A,24),(g.B,24),(g.MASK,4),(g.MARK,4))
def make_source(label):
 out=O/('native-qualification-'+label+'-rev2');out.mkdir(exist_ok=True);blob=bytearray();n=0
 for c in g.cases():
  if not c.native:continue
  initial=g.fixture(c);final,calls=g.reference(initial,c);assert len(calls)<=COUNT
  blob+=struct.pack('<12I',*g.asdict(c).values(),len(calls))
  for m in(initial,final):
   for at,size in BLOCKS:blob+=g.data(m,at,size)
  for m in(initial,final):blob+=struct.pack('<7I',g.read(m,g.DT),*(g.read(m,g.COEF+4*i)for i in range(6)))
  for target,args,observed in calls:
   values=[0xfffffff0 if v=='query'else 0xfffffff1 if v=='packet'else v for v in args];values+=[0]*(6-len(values))
   blob+=struct.pack('<7I',target,*map(g.u32,values))+observed+bytes(72-len(observed))
  blob+=bytes((COUNT-len(calls))*100);n+=1
 assert len(blob)==n*14040
 fixtures=out/'fixtures.bin';assert not fixtures.exists();fixtures.write_bytes(blob)
 incbin='.pushsection .rodata\n.balign 4\nfixture_rows:\n.incbin "'+str(fixtures.resolve())+'"\n.popsection\n'
 types=source.PIN['declarations'].replace('extern f32','f32')
 prefix='#include <ultra64.h>\n'+types+'''
_Static_assert(sizeof(void*)==4 && sizeof(RegionSource151A5660)==24 && sizeof(RegionState151A5660)==112 && sizeof(RegionPacket151A5660)==72 && sizeof(RegionHeight151A5660)==36,"SDK32 layouts");
struct NativeOwner{u8 head[40];RegionState151A5660 state;u8 tail[360];};
_Static_assert(sizeof(struct NativeOwner)==512 && __builtin_offsetof(struct NativeOwner,state)==40,"typed owner");
typedef struct{u32 target,args[6];u8 observed[72];} Call;
typedef struct{u32 flags[11],ncalls;u8 initial[568],final[568];u32 ig[7],fg[7];Call calls[128];} Row;
_Static_assert(sizeof(Row)==14040,"fixture rows");
extern const Row fixture_rows[];
'''+ '__asm__('+json.dumps(incbin)+');\n'+'''
static const Row*row;static struct NativeOwner owner;static RegionSource151A5660 sources[2];static s16 mask[2];static u32 mark;
static u32 callno,counts[6];static u8*retainedPacket;static RegionPosition151A5660*retainedQuery;
static const u32 quarter[65]={'''+','.join('0x%Xu'%v for v in g.trig_source.quarter())+'''};
__attribute__((noreturn))static void quit(int c){__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(c):"memory");__builtin_unreachable();}
static void check(int ok){if(!ok)quit(3);}
static u32 be32(const u8*p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static u32 le32(const u8*p){return(u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void set32(u8*p,u32 v){for(u32 i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
static void be(u8*p,u32 v,u32 n){for(u32 i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
static void set16(u8*p,u32 v){p[0]=(u8)v;p[1]=(u8)(v>>8);}
static f32 number(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static void copy(u8*to,const u8*from,u32 n){for(u32 i=0;i<n;i++)to[i]=from[i];}
static const u8 ownerWords[]={44,48,52,56,60,64,68,72,80,84,88,92,96,100,112,136,144};
static const u8 ownerShorts[]={14,76,78,116,118,120,122,124,126,128,130,132,134,142};
static void decode(u8*to,const u8*from,u32 n,const u8*ws,u32 nw,const u8*hs,u32 nh){
 copy(to,from,n);for(u32 i=0;i<nw;i++)set32(to+ws[i],be32(from+ws[i]));
 for(u32 i=0;i<nh;i++)set16(to+hs[i],(u32)from[hs[i]]<<8|from[hs[i]+1]);
}
static void encode(u8*to,const u8*from,u32 n,const u8*ws,u32 nw,const u8*hs,u32 nh){
 copy(to,from,n);for(u32 i=0;i<nw;i++)be(to+ws[i],le32(from+ws[i]),4);
 for(u32 i=0;i<nh;i++)be(to+hs[i],(u32)from[hs[i]]|((u32)from[hs[i]+1]<<8),2);
}
static void sourceDecode(RegionSource151A5660*p,const u8*from){static const u8 ws[]={16},hs[]={0,2,4,6,8,10};decode((u8*)p,from,24,ws,1,hs,6);}
static u32 sourceAddress(RegionSource151A5660*p){if(!p)return 0;check(p==&sources[0]||p==&sources[1]);return p==&sources[0]?0x50000:0x60000;}
static RegionSource151A5660*sourcePointer(u32 p){if(!p)return 0;check(p==0x50000||p==0x60000);return &sources[p==0x60000];}
static void globalsSet(const u32*v){D_800BE9A4=number(v[0]);D_800A8D80=number(v[1]);D_800A8D84=number(v[2]);D_800A8D88=number(v[3]);D_800A8D8C=number(v[4]);D_800A8D90=number(v[5]);D_800A8D94=number(v[6]);}
static void initialize(void){const u8*p=row->initial;
 decode((u8*)&owner,p,512,ownerWords,sizeof(ownerWords),ownerShorts,sizeof(ownerShorts));owner.state.source=sourcePointer(be32(p+40));
 check(be32(p+148)==0||be32(p+148)==0x70000);owner.state.viewMask=be32(p+148)?mask:0;
 sourceDecode(&sources[0],p+512);sourceDecode(&sources[1],p+536);
 for(u32 i=0;i<2;i++)mask[i]=(s16)((u32)p[560+2*i]<<8|p[561+2*i]);mark=be32(p+564);globalsSet(row->ig);
 callno=0;for(u32 i=0;i<6;i++)counts[i]=0;retainedPacket=0;retainedQuery=0;
}
static void objectsCheck(void){u8 actual[568];const u8*p=row->final;static const u8 ws[]={16},hs[]={0,2,4,6,8,10};
 encode(actual,(const u8*)&owner,512,ownerWords,sizeof(ownerWords),ownerShorts,sizeof(ownerShorts));be(actual+40,sourceAddress(owner.state.source),4);
 check(!owner.state.viewMask||owner.state.viewMask==mask);be(actual+148,owner.state.viewMask?0x70000:0,4);
 encode(actual+512,(const u8*)&sources[0],24,ws,1,hs,6);encode(actual+536,(const u8*)&sources[1],24,ws,1,hs,6);
 for(u32 i=0;i<2;i++)be(actual+560+2*i,(u16)mask[i],2);be(actual+564,mark,4);
 for(u32 i=0;i<568;i++)check(actual[i]==p[i]);
 u32 v[]={word(D_800BE9A4),word(D_800A8D80),word(D_800A8D84),word(D_800A8D88),word(D_800A8D8C),word(D_800A8D90),word(D_800A8D94)};
 for(u32 i=0;i<7;i++)check(v[i]==row->fg[i]);check(callno==row->ncalls);
}
static u32 indexOf(u32 t){switch(t){case 0x150ada20:return 0;case 0x150ada68:return 1;case 0x151423d8:return 2;case 0x15046c80:return 3;case 0x15149550:return 4;case 0x151464b8:return 5;}quit(3);}
static u32 match(u32 target,const u32*args,u32 n,const u8*observed,u32 length){
 check(callno<row->ncalls&&callno<128);const Call*c=&row->calls[callno++];check(c->target==target);
 for(u32 i=0;i<n;i++)check(c->args[i]==args[i]);for(u32 i=0;i<length;i++)check(c->observed[i]==observed[i]);
 return counts[indexOf(target)]++;
}
static void effect(u32 target,u32 n,u32 local){u32 flags=row->flags[6],seed=row->flags[0];RegionState151A5660*s=&owner.state;
 mark=0x13579bdfu+n*0x10203u+target;
 if((flags&1)&&target==0x15149550&&local==0)s->accumulator=4.5f;
 if((flags&2)&&(target==0x150ada20||target==0x150ada68)){s->source=&sources[(n+seed)&1];s->queryHeight^=1;}
 if(flags&4){owner.head[12]^=(u8)(0x37+n);owner.head[1]^=(u8)(0x65+n);
  s->horizontalBase=(f32)((int)(n%7)-2);s->horizontalRange=(n%5)*.25f;s->verticalBase=(n%3)*.5f;s->verticalRange=(n%5)*.125f;
  s->value28=(f32)((int)(n%3)-1);s->value30=(n%7)*.25f;s->value38=(n%3)*.5f;s->byteBase^=0x55;s->byteRange=(u8)(n*17);}
 if(flags&8){RegionSource151A5660*p=s->source;if(p){u32 v=seed*37+n*11;p->x=(s16)v;p->y=(s16)(v+38);p->z=(s16)(v+76);p->radius=(s16)(v+114);p->height=(s16)(v+152);p->secondRadius=(s16)(v+190);}D_800BE9A4=(n%3)*.5f;}
 if(flags&16){if(retainedPacket)for(u32 i=0;i<72;i++)if(i<0x35||i>=0x38)retainedPacket[i]^=0x3c;if(retainedQuery)for(u32 i=0;i<12;i++)((u8*)retainedQuery)[i]^=0xa5;}
}
__attribute__((noinline,noclone))s32 func_150ADA20(void){u32 n=callno,k=match(0x150ada20,0,0,0,0);static const u32 values[]={0,1,0x7fffffff,0x80000000,0xffffffff};u32 answer=(row->flags[0]<<24)^(k*0x9e3779b9u)^values[(k+row->flags[5])%5];effect(0x150ada20,n,k);return(s32)answer;}
__attribute__((noinline,noclone))f32 func_150ADA68(void){u32 n=callno,k=match(0x150ada68,0,0,0,0);static const f32 values[]={0,.25f,.5f,.75f,1,-.5f};f32 answer=values[(k+row->flags[5]+row->flags[0])%6];effect(0x150ada68,n,k);return answer;}
__attribute__((noinline,noclone))f32 func_151423D8(u8 angle){u32 a=angle;match(0x151423d8,&a,1,0,0);u32 v=quarter[angle&64?64-(angle&63):angle&63];if((angle&192)!=0&&(angle&192)!=192)v^=0x80000000;return number(v);}
__attribute__((noinline,noclone))u8 func_151464B8(s16*p){check(p==mask);u32 args[]={0x70000},n=callno,k=match(0x151464b8,args,1,0,0);u8 answer=row->flags[2]==3;effect(0x151464b8,n,k);return answer;}
__attribute__((noinline,noclone))s32 func_15046C80(RegionPosition151A5660*p,u16 selector,f32 lower,RegionHeight151A5660*out){
 check(out==&owner.state.heightResult&&selector==0);u8 point[12];for(u32 i=0;i<3;i++)be(point+4*i,le32((const u8*)p+4*i),4);retainedQuery=p;
 u32 args[]={0xfffffff0,selector,word(lower),0x30070},n=callno,k=match(0x15046c80,args,4,point,12);u8 raw[36];
 for(u32 i=0;i<36;i++)raw[i]=(u8)(i*13+n*7+row->flags[0]);static const u8 ws[]={0,24,32},hs[]={4,6,8,10,12,14,16,18,20,22,30};
 decode((u8*)out,raw,36,ws,3,hs,11);out->height=((int)row->flags[0]-100)*.125f+k*.5f;
 u32 answer=row->flags[4]^((row->flags[6]&8)?k&1:0);effect(0x15046c80,n,k);return(s32)answer;
}
__attribute__((noinline,noclone))void*func_15149550(RegionPacket151A5660*p,u8 kind,u8 arg2,s32 arg3,u8 slot,s32 selector){
 check(kind==10&&arg2==0&&arg3==0);u8 observed[72];const u8*raw=(const u8*)p;
 for(u32 i=0;i<72;i++)observed[i]=(i>=0x35&&i<0x38)?0:raw[i];
 static const u8 ws[]={0,4,8,12,16,20,24,28,48,56,60,64,68},hs[]={32,34,36,42};
 for(u32 i=0;i<sizeof(ws);i++)be(observed+ws[i],le32(raw+ws[i]),4);
 for(u32 i=0;i<sizeof(hs);i++)be(observed+hs[i],(u32)raw[hs[i]]|((u32)raw[hs[i]+1]<<8),2);
 retainedPacket=(u8*)p;u32 args[]={0xfffffff1,kind,arg2,(u32)arg3,slot,(u32)selector},n=callno,k=match(0x15149550,args,6,observed,72);effect(0x15149550,n,k);return(void*)0xe5000002;
}
'''
 suffix='\nstatic int run(void){for(u32 i=0;i<'+str(n)+'u;i++){row=&fixture_rows[i];initialize();invoke((u8*)&owner);objectsCheck();}return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return out,prefix,source.PIN['body'].replace('func_151A5660','invoke',1),suffix,n
def main():
 label='selected'
 out,prefix,body,suffix,count=make_source(label);dest=out/'native-report.json';assert not dest.exists()
 controls={'expiry-value':('*(s16 *)(owner + 0xE) = -1','*(s16 *)(owner + 0xE) = -2'),'disabled-byte':('source->disabled == 1','source->mode == 1'),'threshold':('1.0f < state->accumulator','0.0f < state->accumulator'),'angle-bias':('angle - 64','angle - 63'),'packet-code':('0x6231','0x6230'),'height-result':('heightAccepted = func_15046C80','heightAccepted = !func_15046C80'),'loop-subtract':('state->accumulator -= 1.0f','state->accumulator += 1.0f'),'late-owner-byte':('owner[0xC]','owner[0xD]')}
 variants={'selected':body,**{name:body.replace(old,new,1)for name,(old,new)in controls.items()}};results=[]
 for name,variant in variants.items():
  assert name=='selected'or variant!=body,name
  for opt in(('-O0','-O2','-O3')if name=='selected'else('-O2',)):
   path=out/('native-'+name+opt+'.c');exe=path.with_suffix('');assert not path.exists();path.write_text(prefix+variant+suffix)
   started=time.monotonic();q=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing',str(path),'-o',str(exe)],cwd=R,capture_output=True,text=True)
   (out/(path.stem+'-diagnostics.txt')).write_text(q.stdout+q.stderr)
   assert q.returncode==0 and not q.stdout and not q.stderr,(name,opt,q.stdout,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode,q.stderr)
   row=dict(label=name,opt=opt,exit_code=q.returncode,seconds=round(time.monotonic()-started,3),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_profile=count,runs=results,native32=True,SDK_types=True,strict_aliasing=True,UB_traps=True,public_object_bytes=568,global_words=7,packet_defined_bytes=69,packet_padding_bytes_uncredited=3,source_installed=source.installed(),c_match_credit=0)
 dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(results),passed=True)),flush=True)
if __name__=='__main__':main()
