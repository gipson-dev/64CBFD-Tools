"""Actual native32 C with typed disjoint storage and complete byte snapshots."""
from pathlib import Path
import importlib.util,json,subprocess,sys,time
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_ribbon_renderer_151a3be4_oracle as g
O=g.O;R=g.R

def corpus():return [c for c in g.cases()if c.alias==0 and 0<=g.half(c.view)<4]

def make_source():
 rows=[];array=lambda values:'{'+','.join(str(v)for v in values)+'}'
 for c in corpus():
  initial=g.fixture(c);expected,result,calls,n=g.reference(initial,c);images=[]
  for memory in(initial,expected):
   for at,size in((g.E,160),(g.P,80),(g.PALT,80),(g.A,168),(g.ALT,168),(g.V,512),(g.OUT,512)):
    images.append(array(memory.get(at+i,0)for i in range(size)))
  callrows=[]
  for target,args in calls:
   args=[{'cursor':0xCCCCCCCC,'sync':0xDDDDDDDD}.get(v,v)for v in args]
   values=[target,len(args),*args,*([0]*(11-len(args)))];callrows.append('{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}')
  assert len(callrows)<=16;callrows+=['{0}']*(16-len(callrows))
  values=(c.cap,c.mutation,c.success,c.view,result-g.OUT,len(calls),g.read(expected,g.S['D_800D2C9C']),int(g.read(expected,g.S['D_800DBFF0'])==g.ALTWORLD))
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in values)+','+','.join(images)+',{'+','.join(callrows)+'}}')
 body=g.source.PIN['body'];decl=g.source.PIN['declarations']
 prefix='''#include <ultra64.h>
typedef struct {f32 x,y,z;} RingPosition151A361C;
typedef struct {RingPosition151A361C position;f32 value;s16 lifetime,delay;u8 mark,phase,reserved16[2];} RingSample151A37C0;
void *memcpy(void *,const void *,u32);f32 sqrtf(f32);
__attribute__((noreturn))static void quit(int code){__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void check(int v){if(!v)quit(3);}
static void copy(u8 *d,const u8 *s,u32 n){for(u32 i=0;i<n;i++)((volatile u8*)d)[i]=((const volatile u8*)s)[i];}
static int same(const u8 *a,const u8 *b,u32 n){for(u32 i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static u32 get32(const u8 *p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static u32 get16(const u8 *p){return(u32)p[0]<<8|p[1];}
static void put32(u8 *p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static void put16(u8 *p,u32 v){p[0]=v>>8;p[1]=v;}
static f32 number(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
f32 sqrtf(f32 x){f32 y;__asm__("sqrtss %1,%0":"=x"(y):"x"(x));return y;}
'''+decl+'''
typedef struct {u8 pre00[16];RingPosition151A361C position;u16 timer,flags;u8 pre20[5],capacity,pre26[6];s8 count,head,tail;u8 pre2F[0x65];RingSample151A37C0 *entries;RibbonProfile151A3BE4 *profile;u8 reserved9C[4];} NativeOwner;
typedef struct {u8 pre00[0x2F8];RingPosition151A361C eye;u8 tail[0x9A0-0x304];} NativeView;
typedef struct {u32 cap,mutation,success,view,result,ncall,finalMode,alternateWorld;
 u8 ie[160],ip[80],iq[80],ia[168],ib[168],iv[512],io[512];
 u8 fe[160],fp[80],fq[80],fa[168],fb[168],fv[512],fo[512];u32 calls[16][13];} NativeCase;
static NativeOwner owner;static RibbonProfile151A3BE4 profile,otherProfile,*cachedProfile;
static RingSample151A37C0 entries[7],otherEntries[7];static Vtx vertices[32];static Gfx commands[64];
static NativeView world[4],otherWorld[4],worldBefore[4],otherWorldBefore[4];
u8 *D_800DBFF0;u8 D_80090CD4[16];u32 D_800D2C9C;
static const NativeCase *current;static u32 ordinal;
_Static_assert(sizeof(NativeOwner)==160&&sizeof(RibbonProfile151A3BE4)==80&&sizeof(RingSample151A37C0)==24&&sizeof(NativeView)==0x9A0&&sizeof(Vtx)==16&&sizeof(Gfx)==8,"native sizes");
_Static_assert(__builtin_offsetof(NativeOwner,entries)==0x94&&__builtin_offsetof(NativeOwner,profile)==0x98&&__builtin_offsetof(RibbonProfile151A3BE4,flags)==0x30&&__builtin_offsetof(RibbonProfile151A3BE4,phaseOffset)==0x4C,"native offsets");
static u32 gfxAddress(Gfx *p){return 0x90000+(u32)((u8*)p-(u8*)commands);}
static u32 vertexAddress(const void *p){return 0x80000+((u32)p-(u32)vertices);}
static void call(u32 target,u32 n,const u32 *args){check(ordinal<current->ncall);const u32 *expected=current->calls[ordinal++];check(expected[0]==target&&expected[1]==n);for(u32 i=0;i<n;i++)check(expected[i+2]==args[i]);}
static void mutate(u32 target){u32 m=current->mutation;
 if(target==0x151D5D60&&(m&1)){owner.entries=otherEntries;owner.profile=&otherProfile;D_800DBFF0=(u8*)otherWorld;}
 if(target==0x15142E24){if(m&2){owner.entries=otherEntries;owner.profile=&otherProfile;D_800DBFF0=(u8*)otherWorld;}if(m&4){owner.flags=2;cachedProfile->phaseOffset=237;}}
 if(target==0x1513F4E4&&(m&8))D_800D2C9C=0x789ABCD;
 if(target==0x15142FBC&&(m&16)){owner.tail=0;owner.head=current->cap-2;cachedProfile->phaseOffset=73;}
}
static Gfx *emit(Gfx *out,u32 target,u8 *sync){out->words.w0=0xBA000000|(ordinal-1);out->words.w1=target;if(sync)*sync=0;mutate(target);return out+1;}
void func_151D5D60(void *slots,s16 view,s32 size,Vtx **cursor,u8 *fresh){u32 a[]={slots==(u8*)&owner+0x84?0x30084:0,(u32)(s32)view,(u32)size,0xCCCCCCCC,(u32)fresh};call(0x151D5D60,5,a);*cursor=current->success?vertices:0;mutate(0x151D5D60);cachedProfile=owner.profile;}
Gfx *func_15142E24(Gfx *out,void *source,s32 packed,s32 width,s32 height,s32 value,s32 index,u8 kind,u8 *attachment,u8 *sync,s32 flags){u32 a[]={gfxAddress(out),source==D_80090CD4?0x80090CD4:0,packed,width,height,value,index,kind,(u32)attachment,0xDDDDDDDD,flags};call(0x15142E24,11,a);check(*sync==1);return emit(out,0x15142E24,sync);}
Gfx *func_15142B7C(Gfx *out,u32 a,u32 b){u32 values[]={gfxAddress(out),a,b};call(0x15142B7C,3,values);return emit(out,0x15142B7C,0);}
Gfx *func_15142C10(Gfx *out,s32 r,s32 g,s32 b,s32 a,u8 *sync){u32 v[]={gfxAddress(out),r,g,b,a,0xDDDDDDDD};call(0x15142C10,6,v);check(*sync==0);return emit(out,0x15142C10,sync);}
Gfx *func_15142CF0(Gfx *out,s32 min,s32 frac,s32 r,s32 g,s32 b,s32 a,u8 *sync){u32 v[]={gfxAddress(out),min,frac,r,g,b,a,0xDDDDDDDD};call(0x15142CF0,8,v);check(*sync==0);return emit(out,0x15142CF0,sync);}
Gfx *func_1513F4E4(Gfx *out,u8 index,u8 *sync){u32 v[]={gfxAddress(out),index,0xDDDDDDDD};call(0x1513F4E4,3,v);check(*sync==0);return emit(out,0x1513F4E4,sync);}
Gfx *func_15142FBC(Gfx *out,u32 a,u32 b,u8 *sync){u32 v[]={gfxAddress(out),a,b,0xDDDDDDDD};call(0x15142FBC,4,v);check(*sync==0);return emit(out,0x15142FBC,sync);}
void *memcpy(void *d,const void *s,u32 n){u32 a[]={vertexAddress(d),vertexAddress(s),n};call(0x10022EC0,3,a);check(n==32);copy(d,s,n);return d;}
static void loadEntries(RingSample151A37C0 *a,const u8 *b){copy((u8*)a,b,168);for(u32 i=0;i<7;i++){u32 at=24*i;a[i].position.x=number(get32(b+at));a[i].position.y=number(get32(b+at+4));a[i].position.z=number(get32(b+at+8));a[i].value=number(get32(b+at+12));a[i].lifetime=get16(b+at+16);a[i].delay=get16(b+at+18);}}
static void saveEntries(u8 *b,const RingSample151A37C0 *a){copy(b,(const u8*)a,168);for(u32 i=0;i<7;i++){u32 at=24*i;put32(b+at,bits(a[i].position.x));put32(b+at+4,bits(a[i].position.y));put32(b+at+8,bits(a[i].position.z));put32(b+at+12,bits(a[i].value));put16(b+at+16,a[i].lifetime);put16(b+at+18,a[i].delay);}}
static void loadVertices(const u8 *b){copy((u8*)vertices,b,512);for(u32 i=0;i<32;i++){for(u32 k=0;k<3;k++)vertices[i].v.ob[k]=get16(b+16*i+2*k);vertices[i].v.flag=get16(b+16*i+6);vertices[i].v.tc[0]=get16(b+16*i+8);vertices[i].v.tc[1]=get16(b+16*i+10);}}
static void saveVertices(u8 *b){copy(b,(u8*)vertices,512);for(u32 i=0;i<32;i++){for(u32 k=0;k<3;k++)put16(b+16*i+2*k,vertices[i].v.ob[k]);put16(b+16*i+6,vertices[i].v.flag);put16(b+16*i+8,vertices[i].v.tc[0]);put16(b+16*i+10,vertices[i].v.tc[1]);}}
'''
 suffix='\nstatic const NativeCase cases[]={\n'+',\n'.join(rows)+'\n};\n'+'''
static Gfx *(*volatile invoke)(u8*,Gfx*,s16)=func_151A3BE4;
static int run(void){for(u32 which=0;which<sizeof(cases)/sizeof(cases[0]);which++){
 const NativeCase *c=&cases[which];current=c;ordinal=0;D_800D2C9C=0x10001;D_800DBFF0=(u8*)world;cachedProfile=&profile;
 copy((u8*)&owner,c->ie,160);owner.position.x=number(get32(c->ie+16));owner.position.y=number(get32(c->ie+20));owner.position.z=number(get32(c->ie+24));owner.timer=get16(c->ie+28);owner.flags=get16(c->ie+30);owner.entries=entries;owner.profile=&profile;
 copy((u8*)&profile,c->ip,80);copy((u8*)&otherProfile,c->iq,80);loadEntries(entries,c->ia);loadEntries(otherEntries,c->ib);loadVertices(c->iv);
 for(u32 i=0;i<64;i++){commands[i].words.w0=get32(c->io+8*i);commands[i].words.w1=get32(c->io+8*i+4);}
 s16 view=(s16)c->view;check(view>=0&&view<4);world[view].eye.x=8.25f;world[view].eye.y=-3.5f;world[view].eye.z=17.75f;otherWorld[view].eye.x=-7.5f;otherWorld[view].eye.y=3.25f;otherWorld[view].eye.z=19.f;
 copy((u8*)worldBefore,(u8*)world,sizeof(world));copy((u8*)otherWorldBefore,(u8*)otherWorld,sizeof(otherWorld));
 check(gfxAddress(invoke((u8*)&owner,commands,view))==0x90000+c->result);check(ordinal==c->ncall);
 u8 b[512];copy(b,(u8*)&owner,160);put32(b+16,bits(owner.position.x));put32(b+20,bits(owner.position.y));put32(b+24,bits(owner.position.z));put16(b+28,owner.timer);put16(b+30,owner.flags);
 check(owner.entries==entries||owner.entries==otherEntries);check(owner.profile==&profile||owner.profile==&otherProfile);put32(b+0x94,owner.entries==entries?0x60000:0x70000);put32(b+0x98,owner.profile==&profile?0x50000:0x71000);check(same(b,c->fe,160));
 check(same((u8*)&profile,c->fp,80)&&same((u8*)&otherProfile,c->fq,80));saveEntries(b,entries);check(same(b,c->fa,168));saveEntries(b,otherEntries);check(same(b,c->fb,168));saveVertices(b);check(same(b,c->fv,512));
 for(u32 i=0;i<64;i++){u32 w0=commands[i].words.w0,w1=commands[i].words.w1,expectedWord=get32(c->fo+8*i),expectedPointer=get32(c->fo+8*i+4);if(w0>>24==1&&expectedWord>>24==1&&expectedPointer>=0x80000&&expectedPointer<0x80200){check(w1>=(u32)vertices&&w1<(u32)vertices+512);w1=vertexAddress((void*)w1);}put32(b+8*i,w0);put32(b+8*i+4,w1);}check(same(b,c->fo,512));
 check(same((u8*)world,(u8*)worldBefore,sizeof(world))&&same((u8*)otherWorld,(u8*)otherWorldBefore,sizeof(otherWorld)));check(D_800D2C9C==c->finalMode&&D_800DBFF0==(c->alternateWorld?(u8*)otherWorld:(u8*)world));
 }return 0;}
'''
 return prefix,body,suffix,len(corpus())

def main():
 prefix,body,suffix,count=make_source();variants={'selected':body,
 'allocation-size':body.replace('owner[0x25] * 32 + 0xA0','owner[0x25] * 31 + 0xA0'),
 'count-gate':body.replace('owner + 0x2C) >= 2','owner + 0x2C) > 2'),
 'zero-fade-entry':body.replace('if (profile->flags & 2)','if ((profile->flags & 2) && profile->fadeInCount != 0)'),
 'fade-step':body.replace('factor += profile->fadeInStep','factor += profile->fadeOutStep'),
 'dirty-initial-value':body.replace('sync = 1','sync = 0'),
 'primitive-alpha':body.replace('output, 0, 0, 0, 0, 0, 0, &sync','output, 0, 0, 0, 0, 0, 255, &sync'),
 'combiner-index':body.replace('func_1513F4E4(output, 6,','func_1513F4E4(output, 7,'),
 'camera-z':body.replace('eye->z','eye->y'),
 'record-opacity':body.replace('entry->lifetime','entry->delay'),
 'vertex-flag':body.replace('cursor->v.flag = 0','cursor->v.flag = 1'),
 'first-triangle':body.replace('output++, 0, 1, 2, 0','output++, 0, 2, 1, 0'),
 'vertex-source-pointer':body.replace('cursor - 4, 4, 0','cursor - 3, 4, 0'),
 'seam-source-pair':body.replace('cursor[-2].v.tc[0]','cursor[-1].v.tc[0]')}
 results=[];destination=O/'native-qualification-v2';destination.mkdir(exist_ok=True)
 for label,fn in variants.items():
  assert label=='selected'or fn!=body,label
  for opt in(('-O0','-O2')if label=='selected'else('-O2',)):
   path=destination/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START);start=time.monotonic()
   q=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing',str(path),'-o',str(exe)],cwd=R,capture_output=True,text=True)
   assert q.returncode==0 and not q.stderr,(label,q.stdout,q.stderr)
   run=subprocess.run([str(exe)],capture_output=True,timeout=30);assert run.returncode==(0 if label=='selected'else 3),(label,opt,run.returncode)
   row=dict(label=label,opt=opt,exit_code=run.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_profile=count,runs=results,native32=True,UB_traps=True,strict_aliasing=True,complete_typed_disjoint_objects=True,vertex_bytes=512,command_bytes=512,complete_world_unchanged=True,hardware_FCSR_emulated=False,source_installed=False,c_match_credit=0)
 (O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=count,runs=len(results),passes=True)),flush=True);return report

if __name__=='__main__':main()
