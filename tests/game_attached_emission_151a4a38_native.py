"""Native32 checks typed public objects and only defined descriptor fields."""
from pathlib import Path
import importlib.util,json,struct,subprocess,sys,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_attached_emission_151a4a38_oracle as g
O=g.O;R=g.R
def make_source(label):
 dest=O/'native-qualification';dest.mkdir(exist_ok=True);blob=bytearray();count=0
 for c in g.cases():
  # Guest checks cover overlapping BE byte/word actor views. Native fixtures
  # serialize nonoverlapping typed objects only, without claiming endian aliases.
  if c.alias:continue
  initial=g.fixture(c);expected,calls,answer,ops=g.reference(initial,c);emitter=next((v for v in calls if v[0]==g.EMIT),None);transform=next((v for v in calls if v[0]==g.TRANSFORM),None)
  truncs=[g.floating(v[1])for v in ops if v[0]=='trunc'];assert all(-32768<=v<32768 for v in truncs)
  values=(c.seed,c.flips,c.route,c.mutation,c.pattern,int(emitter is not None),emitter[1][2]if emitter else 0,emitter[1][3]if emitter else 0,transform[1][2]if transform else 0,g.read(initial,g.DT),g.read(expected,g.DT),g.read(initial,g.MARK),g.read(expected,g.MARK))
  blob.extend(struct.pack('<13I',*map(g.u32,values)))
  for m in(initial,expected):
   for at in(g.E,g.A,g.ALT):blob.extend(g.data(m,at,512))
  blob.extend(emitter[2]if emitter else bytes(108));count+=1
 path=dest/'fixtures.bin';path.write_bytes(blob);assert len(blob)==count*3232
 incbin='.pushsection .rodata\n.balign 4\nfixture_rows:\n.incbin "'+str(path)+'"\n.popsection\n'
 types=g.source.PIN['declarations'];body=g.source.PIN['body']
 prefix='''#include <ultra64.h>
typedef struct {f32 x,y,z;} RingPosition151A361C;
s32 func_150ADA20(void);void func_15143134(void *,void *,s32);
__attribute__((noreturn))static void quit(int c){__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(c):"memory");__builtin_unreachable();}
static void check(int v){if(!v)quit(3);}
static f32 number(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static u32 be32(const u8*p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static u32 le32(const u8*p){return(u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void set32(u8*p,u32 v){for(u32 i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
static void set16(u8*p,u32 v){p[0]=(u8)v;p[1]=(u8)(v>>8);}
'''+types+'''
typedef struct {u32 seed,flips,route,mutation,pattern,emitted,slot,selector,matrix,initialDT,finalDT,initialMark,finalMark;u8 ie[512],ia[512],ialt[512],fe[512],fa[512],falt[512],packet[108];} Row;
extern const Row fixture_rows[];
'''+ '__asm__('+json.dumps(incbin)+');\n'+'''static const Row *row;
static u8 owner[512] __attribute__((aligned(4))),actor[512] __attribute__((aligned(4))),alternate[512] __attribute__((aligned(4)));
static u32 ri,transforms,emitters,mark;static u8 *output;
f32 D_800BE9A4;
static u8*pointer(u32 p){check(p==0x30000||p==0x50000||p==0x60000);return p==0x30000?owner:p==0x50000?actor:alternate;}
static int isword(u32 i,int kind){if(kind==0)return i==0x28||i==0x30||i==0x34||i==0x3c||i==0x40||i==0x44;return i==0||i==0x1d4;}
static int isshort(u32 i,int kind){return kind==0?i==0x0e:i==0x76;}
static void initialize(u8*b,const u8*be,int kind){
 for(u32 i=0;i<512;i++)b[i]=be[i];
 for(u32 i=0;i<512;i++){if(isword(i,kind))set32(b+i,be32(be+i));if(isshort(i,kind))set16(b+i,(u32)be[i]<<8|be[i+1]);}
 if(kind==0)set32(b+0x28,(u32)pointer(be32(be+0x28)));
}
static void compareObject(const u8*b,const u8*be,int kind){
 if(kind==0)check(le32(b+0x28)==(u32)pointer(be32(be+0x28)));
 for(u32 i=0;i<512;i++){
  if(kind==0&&i>=0x28&&i<0x2c)continue;
  u32 j=i;
  for(u32 k=0;k<4;k++)if(i>=k&&isword(i-k,kind)){j=(i-k)+(3-k);break;}
  for(u32 k=0;k<2;k++)if(i>=k&&isshort(i-k,kind)){j=(i-k)+(1-k);break;}
  check(b[j]==be[i]);
 }
}
static int defined(u32 i){return i!=5&&!(i>=0x65&&i<0x6c);}
static void comparePacket(const u8*b){
 static const u8 words[]={8,12,20,24,44,48,52,56,60,64,76,80,84,88,92};
 static const u8 shorts[]={0,2,6,16,18,38,40,42,68,70,72,74};
 for(u32 j=0;j<sizeof(words);j++){u32 at=words[j];check(le32(b+at)==be32(row->packet+at));}
 for(u32 j=0;j<sizeof(shorts);j++){u32 at=shorts[j];check(((u32)b[at]|(u32)b[at+1]<<8)==((u32)row->packet[at]<<8|row->packet[at+1]));}
 check(b[4]==row->packet[4]);for(u32 i=0x1c;i<=0x25;i++)check(b[i]==row->packet[i]);for(u32 i=0x60;i<=0x64;i++)check(b[i]==row->packet[i]);
}
__attribute__((noinline,noclone))void func_15143134(void*input,void*destination,s32 matrix){
 check(transforms++==0&&row->emitted&&input==owner+0x3c&&(u32)matrix==row->matrix);output=destination;
 for(u32 i=0;i<3;i++){check(le32((u8*)input+4*i)==be32(row->ie+0x3c+4*i));set32(output+4*i,be32(row->packet+0x38+4*i));}
 if(row->mutation&1){static const f32 values[]={-1.75f,2.75f,3.5f,.25f};set32(owner+0x34,bits(values[row->seed%4]));set32(owner+0x28,(u32)alternate);set16(actor+0x76,0xf4a5);}
 if(row->mutation&2){owner[12]^=0xa7;owner[1]^=0x56;D_800BE9A4=-4.0f;}
}
__attribute__((noinline,noclone))s32 func_150ADA20(void){
 u32 i=ri++;check(i<2&&row->emitted);
 if(row->mutation&(i==0?4:8)){owner[12]^=(u8)(0x37+i);owner[1]^=(u8)(0x65+i);for(u32 j=0;j<12;j++)output[j]^=(u8)(0x5a+i);}
 return(s32)(0xfffffffeu|((row->flips>>i)&1));
}
__attribute__((noinline,noclone))void func_15153634(void*p,u8 selector,u8 slot,u8 context){
 check(emitters++==0&&row->emitted&&selector==255&&slot==row->slot&&context==row->selector);comparePacket(p);mark=0x13579bdf;owner[0xd]^=0x40;
 if(row->mutation&16)for(u32 i=0;i<108;i++)if(defined(i))((u8*)p)[i]^=0x96;
}
'''
 suffix='''
_Static_assert(sizeof(Row)==3232,"fixture ABI");
_Static_assert(sizeof(AttachedEmissionDescriptor151A4A38)==108,"complete descriptor extent");
_Static_assert(sizeof(AttachedEmissionPayload151A4A38)==32,"source payload extent");
_Static_assert(__builtin_offsetof(AttachedEmissionDescriptor151A4A38,position)==0x38&&__builtin_offsetof(AttachedEmissionDescriptor151A4A38,flags)==0x5c,"descriptor fields");
static void(*volatile invoke)(u8*)=func_151A4A38;
static int run(void){for(u32 n=0;n<'''+str(count)+'''u;n++){
 row=&fixture_rows[n];initialize(owner,row->ie,0);initialize(actor,row->ia,1);initialize(alternate,row->ialt,1);
 ri=transforms=emitters=0;mark=row->initialMark;output=(void*)0;D_800BE9A4=number(row->initialDT);
 invoke(owner);check(ri==2*row->emitted&&transforms==row->emitted&&emitters==row->emitted&&mark==row->finalMark&&bits(D_800BE9A4)==row->finalDT);
 compareObject(owner,row->fe,0);compareObject(actor,row->fa,1);compareObject(alternate,row->falt,1);
 }return 0;}
'''
 return prefix,body,suffix,count
def main(label='v13'):
 prefix,body,suffix,count=make_source(label);variants={'selected':body,
 'excluded-type':body.replace('state->source == 8','state->source == 9'),
 'retirement-flag':body.replace('owner[0xD] |= 1','owner[0xD] |= 2'),
 'accumulator-scale':body.replace('state->rate * D_800BE9A4','(state->rate + 1.0f) * D_800BE9A4'),
 'threshold':body.replace('1.0f < state->accumulator','0.0f < state->accumulator'),
 'angle-bias':body.replace('>> 8) - 64','>> 8) - 63'),
 'counter-range':body.replace('packet.countRange = 0','packet.countRange = 1'),
 'random-flag':body.replace('flags |= 0x40','flags |= 0x20'),
 'late-channel':body.replace('owner[0xC]','owner[0xD]')}
 results=[];dest=O/'native-qualification'
 for name,fn in variants.items():
  assert name=='selected'or fn!=body,name
  for opt in(('-O0','-O2')if name=='selected'else('-O2',)):
   path=dest/('native-'+name+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START);start=time.monotonic()
   q=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing',str(path),'-o',str(exe)],cwd=R,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,(name,q.stdout,q.stderr)
   q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==(0 if name=='selected'else 3),(name,opt,q.returncode)
   row=dict(label=name,opt=opt,exit_code=q.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_profile=count,runs=results,defined_descriptor_bytes=100,unobserved_unmutated_indeterminate_bytes=8,native32=True,strict_aliasing=True,UB_traps=True,complete_three_public_objects=True,BE_byte_word_alias_cases_guest_only=32,source_installed=False,c_match_credit=0)
 (O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(results),passes=True)),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v13')
