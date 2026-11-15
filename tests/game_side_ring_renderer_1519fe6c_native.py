"""Native32 renderer body, typed objects, complete output windows and controls."""
from pathlib import Path
import json,subprocess,struct
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.experiments import game_side_ring_renderer_1519fe6c_recovery as recover
from tools.experiments import game_side_effect_constructor_1519f1c8_match as ctor
from tools.experiments import game_side_effect_update_1519f4f0_match as updater
from tools.experiments import game_side_ring_emitter_1519f7f0_match as emitter
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
O=recover.OUT
SENTINELS={'cursor':0xCCCCCCCC,'sync':0xDDDDDDDD}

def make_source(body=recover.PIN['source']):
 rows=[];corpus=list(g.cases());array=lambda values:'{'+','.join(str(v) for v in values)+'}'
 for c in corpus:
  m=g.fixture(c);expected,result,calls,segments=g.reference(m,c);spans=[]
  for memory in (m,expected):
   for at,n in ((g.E,160),(g.P,80),(g.PALT,80),(g.A,36*c.cap),(g.ALT,36*c.cap),(g.V,512),(g.OUT,512)):
    spans.append(array(memory[at+i] for i in range(n)))
  callrows=[]
  for t,args in calls:
   args=tuple(SENTINELS.get(x,x) for x in args);values=(t,len(args),*args,*([0]*(11-len(args))))
   callrows.append('{'+','.join('0x%Xu'%g.u32(x) for x in values)+'}')
  callrows+=['{0}']*(7-len(callrows));assert len(callrows)==7
  scalars=(c.cap,c.mutation,c.success,c.view,result-g.OUT,len(calls),g.read(expected,g.S['D_800D2C9C']))
  rows.append('{'+','.join('0x%Xu'%g.u32(x) for x in scalars)+','+','.join(spans)+',{'+','.join(callrows)+'}}')
 prefix='#include <ultra64.h>\n#include "structs.h"\n'+ctor.PIN['declarations']+updater.PIN['declarations']+emitter.PIN['declarations']+recover.PIN['declarations']+'''
f32 fabsf(f32 v){union{f32 f;u32 u;}a;a.f=v;a.u&=0x7FFFFFFF;return a.f;}
f32 sqrtf(f32 v){f32 x;__asm__("sqrtss %1,%0":"=x"(x):"x"(v));return x;}
u8 D_80090E0C[16];u32 D_800D2C9C;
typedef struct {
 u32 cap,mutation,success,view,result,ncall,finalMode;
 u8 ie[160],ip[80],iq[80],ia[180],ib[180],iv[512],io[512];
 u8 fe[160],fp[80],fq[80],fa[180],fb[180],fv[512],fo[512];
 u32 calls[7][13];
} NativeCase;
static SideEmitter1519F7F0 effect;
static SidePayload1519F1C8 packet,otherPacket;
static SideEmitEntry1519F7F0 entries[5],otherEntries[5];
static Vtx vertices[32];static Gfx commands[64];
static const NativeCase *current;static u32 ordinal,failure;
static u32 get32(const u8 *p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static s32 get16(const u8 *p){u32 x=(u32)p[0]<<8|p[1];return(s32)x-(x&32768?65536:0);}
static void put32(u8 *p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static void put16(u8 *p,u32 v){p[0]=v>>8;p[1]=v;}
static f32 number(u32 x){union{u32 u;f32 f;}a;a.u=x;return a.f;}
static u32 word(f32 x){union{u32 u;f32 f;}a;a.f=x;return a.u;}
static void copy(u8 *d,const u8 *s,u32 n){for(u32 i=0;i<n;i++)d[i]=s[i];}
static int same(const u8 *a,const u8 *b,u32 n){for(u32 i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static const u32 *call(u32 target,u32 n,const u32 *args){
 u32 which=ordinal++;if(which>=current->ncall){failure=1;return current->calls[0];}
 const u32 *expected=current->calls[which];if(expected[0]!=target||expected[1]!=n)failure=2;
 for(u32 i=0;i<n;i++)if(expected[i+2]!=args[i])failure=3;
 return expected;
}
static u32 address(Gfx *p){return 0x90000+(u32)((u8 *)p-(u8 *)commands);}
static void mutate(u32 target){
 u32 m=current->mutation;
 if(target==0x151D5D60&&(m&1)){effect.entries=otherEntries;effect.payload=&otherPacket;}
 if(target==0x15142E24){
  if(m&2){effect.entries=otherEntries;effect.payload=&otherPacket;}
  if(m&4){packet.red=90;packet.green=80;packet.blue=70;effect.flags=2;effect.mode=7;}
 }
 if(target==0x1513F4E4&&(m&8))D_800D2C9C=0x789ABCD;
 if(target==0x15142FBC&&(m&16)){effect.head=1;effect.tail=2;packet.zero46=-1025;packet.command=-32768;}
}
static Gfx *emit(Gfx *out,u32 target,u8 *sync){
 out->words.w0=0xBA000000|(ordinal-1);out->words.w1=target;
 if(sync)*sync=0;mutate(target);return out+1;
}
void func_151D5D60(void *slots,s16 view,s32 size,Vtx **cursor,u8 *fresh){
 u32 a[]={slots==effect.reserved84?0x30084:0,(u32)(s32)view,(u32)size,0xCCCCCCCC,(u32)fresh};call(0x151D5D60,5,a);
 *cursor=current->success?vertices:0;mutate(0x151D5D60);
}
Gfx *func_15142E24(Gfx *out,void *source,s32 packed,s32 width,s32 height,s32 value,s32 index,u8 kind,u8 *attachment,u8 *sync,s32 flags){
 u32 a[]={address(out),source==D_80090E0C?0x80090E0C:0,packed,width,height,value,index,kind,(u32)attachment,0xDDDDDDDD,flags};
 call(0x15142E24,11,a);if(*sync!=1)failure=4;return emit(out,0x15142E24,sync);
}
Gfx *func_15142B7C(Gfx *out,u32 first,u32 second){u32 a[]={address(out),first,second};call(0x15142B7C,3,a);return emit(out,0x15142B7C,0);}
Gfx *func_15142C10(Gfx *out,s32 r,s32 g,s32 b,s32 alpha,u8 *sync){u32 a[]={address(out),r,g,b,alpha,0xDDDDDDDD};call(0x15142C10,6,a);if(*sync)failure=4;return emit(out,0x15142C10,sync);}
Gfx *func_15142CF0(Gfx *out,s32 min,s32 frac,s32 r,s32 g,s32 b,s32 alpha,u8 *sync){u32 a[]={address(out),min,frac,r,g,b,alpha,0xDDDDDDDD};call(0x15142CF0,8,a);if(*sync)failure=4;return emit(out,0x15142CF0,sync);}
Gfx *func_1513F4E4(Gfx *out,u8 index,u8 *sync){u32 a[]={address(out),index,0xDDDDDDDD};call(0x1513F4E4,3,a);if(*sync)failure=4;return emit(out,0x1513F4E4,sync);}
Gfx *func_15142FBC(Gfx *out,u32 first,u32 second,u8 *sync){u32 a[]={address(out),first,second,0xDDDDDDDD};call(0x15142FBC,4,a);if(*sync)failure=4;return emit(out,0x15142FBC,sync);}
static void load_packet(SidePayload1519F1C8 *p,const u8 *bytes){copy((u8 *)p,bytes,80);p->speed=number(get32(bytes+56));p->zero46=get16(bytes+70);p->command=get16(bytes+74);}
static void save_packet(u8 *bytes,SidePayload1519F1C8 *p){copy(bytes,(u8 *)p,80);put32(bytes+56,word(p->speed));put16(bytes+70,p->zero46);put16(bytes+74,p->command);}
static void load_entries(SideEmitEntry1519F7F0 *a,const u8 *bytes,u32 n){
 for(u32 i=0;i<n;i++){const u8 *b=bytes+36*i;copy((u8 *)&a[i],b,36);
 a[i].x=number(get32(b));a[i].z=number(get32(b+4));a[i].height=number(get32(b+8));a[i].phase=number(get32(b+12));
 a[i].alpha=get16(b+16);a[i].light=get16(b+20);a[i].tag=get16(b+22);}
}
static void save_entries(u8 *bytes,SideEmitEntry1519F7F0 *a,u32 n){
 for(u32 i=0;i<n;i++){u8 *b=bytes+36*i;copy(b,(u8 *)&a[i],36);
 put32(b,word(a[i].x));put32(b+4,word(a[i].z));put32(b+8,word(a[i].height));put32(b+12,word(a[i].phase));
 put16(b+16,a[i].alpha);put16(b+20,a[i].light);put16(b+22,a[i].tag);}
}
typedef char effect_shape[sizeof(effect)==160?1:-1];
typedef char entry_shape[sizeof(entries[0])==36?1:-1];
typedef char vertex_shape[sizeof(vertices[0])==16?1:-1];
'''
 harness='\nstatic const NativeCase cases[]={\n'+',\n'.join(rows)+'\n};\n'+'''
static int run(void){
 for(u32 which=0;which<sizeof(cases)/sizeof(cases[0]);which++){
  const NativeCase *c=&cases[which];current=c;ordinal=failure=0;D_800D2C9C=0x10001;
  copy((u8 *)&effect,c->ie,160);effect.entries=entries;effect.payload=&packet;
  effect.flags=get16(c->ie+30);effect.mode=get32(c->ie+32);
  for(u32 i=0;i<3;i++)((f32 *)&effect.point)[i]=number(get32(c->ie+16+4*i));
  load_packet(&packet,c->ip);load_packet(&otherPacket,c->iq);load_entries(entries,c->ia,c->cap);load_entries(otherEntries,c->ib,c->cap);
  for(u32 i=0;i<32;i++){
   for(u32 j=0;j<3;j++)vertices[i].v.ob[j]=get16(c->iv+16*i+2*j);
   vertices[i].v.flag=get16(c->iv+16*i+6);vertices[i].v.tc[0]=get16(c->iv+16*i+8);vertices[i].v.tc[1]=get16(c->iv+16*i+10);
   for(u32 j=0;j<4;j++)vertices[i].v.cn[j]=c->iv[16*i+12+j];
  }
  for(u32 i=0;i<64;i++){commands[i].words.w0=get32(c->io+8*i);commands[i].words.w1=get32(c->io+8*i+4);}
  Gfx *result=func_1519FE6C(&effect,commands,(s16)c->view);
  if(result!=(Gfx *)((u8 *)commands+c->result)||ordinal!=c->ncall||failure)return 151;
  if(D_800D2C9C!=c->finalMode)return 152;
  u8 e[160],p[80],q[80],a[180],b[180],v[512],out[512];copy(e,(u8 *)&effect,160);
  put32(e+148,effect.entries==entries?0x60000:0x70000);put32(e+152,effect.payload==&packet?0x50000:0x71000);
  put16(e+30,effect.flags);put32(e+32,effect.mode);for(u32 i=0;i<3;i++)put32(e+16+4*i,word(((f32 *)&effect.point)[i]));
  save_packet(p,&packet);save_packet(q,&otherPacket);save_entries(a,entries,c->cap);save_entries(b,otherEntries,c->cap);
  for(u32 i=0;i<32;i++){
   for(u32 j=0;j<3;j++)put16(v+16*i+2*j,vertices[i].v.ob[j]);
   put16(v+16*i+6,vertices[i].v.flag);put16(v+16*i+8,vertices[i].v.tc[0]);put16(v+16*i+10,vertices[i].v.tc[1]);
   for(u32 j=0;j<4;j++)v[16*i+12+j]=vertices[i].v.cn[j];
  }
  for(u32 i=0;i<64;i++){
   u32 first=commands[i].words.w0,second=commands[i].words.w1;
   if(first==0x0100600C){if(second<(u32)vertices||second>(u32)vertices+512)return 154;second=0x80000+(second-(u32)vertices);}
   put32(out+8*i,first);put32(out+8*i+4,second);
  }
  if(!same(e,c->fe,160)||!same(p,c->fp,80)||!same(q,c->fq,80)||!same(a,c->fa,36*c->cap)||!same(b,c->fb,36*c->cap)||!same(v,c->fv,512)||!same(out,c->fo,512))return 153;
 }
 return 0;
}
'''
 return prefix+body+harness+START,len(corpus)

def main():
 text,count=make_source();profiles=[];controls=[]
 def run(text,name,opt,alias):
  path=O/(name+'.c');exe=path.with_suffix('');path.write_text(text)
  p=subprocess.run(native_command(opt)+['-mstackrealign',alias,'-o',str(exe),str(path)],capture_output=True,text=True);assert p.returncode==0 and not p.stderr,p.stderr
  return subprocess.run([str(exe)],capture_output=True).returncode
 for opt in ('-O0','-O2','-O3'):
  for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
   result=run(text,'native'+opt+alias,opt,alias);assert result==0,(opt,alias,result);profiles.append(opt+alias)
  for label,old,new in (
   ('allocation-size','effect->capacity * 48 + 0x120','effect->capacity * 47 + 0x120'),
   ('zero-fade-entry','if (packet->kind & 2) {','if ((packet->kind & 2) && packet->style != 0) {'),
   ('negative-remainder','packet->zero46 % 1024','(u32)packet->zero46 % 1024'),
   ('last-triangle','gSP1Triangle(output++, 1, 5, 2, 0);','gSP1Triangle(output++, 1, 4, 2, 0);')):
   assert recover.PIN['source'].count(old)==1
   wrong=text.replace(recover.PIN['source'],recover.PIN['source'].replace(old,new));result=run(wrong,'native-control-'+label+opt,opt,'-fstrict-aliasing')
   assert result in (151,152,153,154),(label,opt,result);controls.append(label+opt)
 report=dict(cases_per_profile=count,profiles=profiles,UBSan=True,provider_arguments=True,complete_typed_objects=True,vertex_window=512,command_window=512,effective_source_controls=controls,hardware_FCSR_emulated=False,c_match_credit=0)
 (O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
