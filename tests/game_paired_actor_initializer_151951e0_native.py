"""SDK32 source execution against independently guest-checked boundary vectors."""
from pathlib import Path
from dataclasses import replace
import itertools,json,subprocess,sys
from tools.experiments import game_paired_actor_initializer_151951e0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments import game_paired_actor_initializer_151951e0_match as screen
from tools.tests import game_paired_actor_initializer_151951e0_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
FIELDS=[(0,4),(0x14,4),(0x18,4),(0x1C,4),(0x20,4),(0x24,4),(0x3C,4),(0x40,4),(0x4C,4),(0x76,2),(0x7A,2),(0x84,2),(0x9C,4),(0xB8,4),(0xBC,4),(0xF8,4),(0x148,4),(0x14C,4),(0x150,4)]
def host_image(blob):
 b=bytearray(blob)
 for off,n in FIELDS:b[off:off+n]=blob[off:off+n][::-1]
 return bytes(b)
def digest(b):
 h=2166136261
 for v in b:h=((h^v)*16777619)&0xFFFFFFFF
 return h
PRE=r'''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;
typedef signed char s8;typedef short s16;typedef int s32;typedef float f32;
#define NULL ((void *)0)
#define offsetof __builtin_offsetof
void *memcpy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];return d;}
void *memset(void *d,int c,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=(u8)c;return d;}
typedef struct {
 s32 state;u8 id,p5[15];f32 x,y,z,vx,vz;u8 p28[0x14];f32 lift,rotation;
 u8 p44[8];s32 command;u8 p50[0x18],color[6],p6E[8];u16 heading,unk78,facing;
 u8 p7C[8];u16 resource;u8 p86[0x16];u32 flags;u8 pA0[0x18];f32 scalar,velocity;
 u8 pC0[0x38];u32 link;u8 pFC[8],stunned,p105[0x20],immune,p126[0x22];
 f32 spin,xzScale,yScale;u8 p154[0x76],health,p1CB[0x161];
} NativeActor;
typedef NativeActor struct127;
typedef char size_actor[sizeof(NativeActor)==812?1:-1];
typedef char size_pointer[sizeof(void*)==4?1:-1];
typedef char offsets_actor[offsetof(NativeActor,x)==0x14&&offsetof(NativeActor,command)==0x4C&&offsetof(NativeActor,heading)==0x76&&offsetof(NativeActor,resource)==0x84&&offsetof(NativeActor,flags)==0x9C&&offsetof(NativeActor,scalar)==0xB8&&offsetof(NativeActor,velocity)==0xBC&&offsetof(NativeActor,link)==0xF8&&offsetof(NativeActor,stunned)==0x104&&offsetof(NativeActor,immune)==0x125&&offsetof(NativeActor,spin)==0x148&&offsetof(NativeActor,yScale)==0x150&&offsetof(NativeActor,health)==0x1CA?1:-1];
s32 func_1507CD64(struct127*,s32);void func_15194AB4(u8*);s32 func_150ADA20(void);
u8 *func_1505ED34(void);void func_150838EC(u8*,u16,s32,s32);void func_150D10E4(u8*,s32);
'''
HARNESS=r'''
typedef struct {u8 before[16];NativeActor actor;u8 after[16];} GuardedActor;
static GuardedActor first,second;f32 D_800A8704;
static u32 rowIndex,stepIndex,bad;
static void check(int x){if(!x)bad=1;}
static u8 *actor(void){return (u8*)&first.actor;}
static u8 *paired(void){return rows[rowIndex].alias?actor():(u8*)&second.actor;}
static u32 hash(const u8 *p){u32 i,h=2166136261u;for(i=0;i<812;i++)h=(h^p[i])*16777619u;return h;}
static u32 pointer(const void *p){return p==(void*)actor()?1:p==(void*)paired()?2:0xBAD0u;}
static u32 call(u32 target,u32 a0,u32 a1,u32 a2,u32 a3){
 const Step *s=&steps[rows[rowIndex].stepStart+stepIndex++];u32 i,bits;
 memcpy(&bits,&D_800A8704,4);
 check(s->target==target&&s->a[0]==a0&&s->a[1]==a1&&s->a[2]==a2&&s->a[3]==a3);
 check(hash(actor())==s->sourceHash&&hash(paired())==s->pairedHash&&bits==s->coefficient);
 for(i=0;i<s->writeCount;i++){
  const Write *w=&writes[s->writeStart+i];u8 *p=w->which==0?actor():w->which==1?paired():(u8*)&D_800A8704;
  p[w->offset]=w->value;
 }
 return s->answer;
}
s32 func_1507CD64(struct127 *p,s32 k){return (s32)call(0x1507CD64,pointer(p),(u32)k,0,0);}
void func_15194AB4(u8 *p){call(0x15194AB4,pointer(p),0,0,0);}
s32 func_150ADA20(void){return (s32)call(0x150ADA20,0,0,0,0);}
u8 *func_1505ED34(void){call(0x1505ED34,0,0,0,0);return paired();}
void func_150838EC(u8 *p,u16 k,s32 z,s32 v){call(0x150838EC,pointer(p),k,(u32)z,(u32)v);}
void func_150D10E4(u8 *p,s32 mode){call(0x150D10E4,pointer(p),(u32)mode,0,0);}
static int run(void){
 u32 i,b;
 for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
  const Row *r=&rows[rowIndex];stepIndex=bad=0;
  memset(&first,0xA5,sizeof(first));memset(&second,0x5A,sizeof(second));
  memcpy(actor(),images+r->initialStart,812);memcpy(paired(),images+r->initialStart+812,812);
  b=r->coefficient;memcpy(&D_800A8704,&b,4);
  func_151951E0(actor());
  check(stepIndex==11&&hash(actor())==r->finalSource&&hash(paired())==r->finalPaired);
  memcpy(&b,&D_800A8704,4);check(b==r->finalCoefficient);
  for(i=0;i<16;i++)check(first.before[i]==0xA5&&first.after[i]==0xA5&&second.before[i]==0x5A&&second.after[i]==0x5A);
  if(bad)return 1;
 }
 return 0;
}
'''
CONTROLS={
 'missing-health-clear':screen.BODY.replace('actor[0x1CA] = 0','actor[0x1CA] = 1'),
 'missing-active-state':screen.BODY.replace('*(s32 *)(actor + 0) = 40','*(s32 *)(actor + 0) = 0'),
 'signed-first-remainder':screen.BODY.replace('func_150ADA20() % 5U','(s32)func_150ADA20() % 5',1),
 'wrong-actor-spin':screen.BODY.replace('(func_150ADA20() % 10U) - 5.0f','(func_150ADA20() % 10U) - 4.0f',1),
 'wrong-paired-lift':screen.BODY.replace('*(f32 *)(paired + 0x3C) = 10.0f','*(f32 *)(paired + 0x3C) = 11.0f'),
 'wrong-identity':screen.BODY.replace('paired[4] = actor[4]','paired[4] = actor[5]'),
 'wrong-scale':screen.BODY.replace('*(f32 *)(paired + 0x14C) = *(f32 *)(actor + 0x14C)','*(f32 *)(paired + 0x14C) = *(f32 *)(actor + 0x150)'),
 'wrong-flags-mask':screen.BODY.replace('0x0FFF0000','0x00FF0000'),
 'wrong-link':screen.BODY.replace('= link;','= link ^ 1U;'),
 'wrong-resource':screen.BODY.replace('*(u16 *)(actor + 0x84)','*(u16 *)(actor + 0x7A)'),
 'wrong-final-transition':screen.BODY.replace('func_150D10E4(paired, 1)','func_150D10E4(paired, 0)')}
def vectors():
 cases=[g.Case(kind=k,angle=20000+k*137,values=tuple((k*0x01010101+0x1020304*j)&0xFFFFFFFF for j in range(5)))for k in range(256)]
 cases += [g.Case(angle=a,mode=mode,alias=alias,values=v)for a,mode,alias,v in itertools.product((12000,32768,65535),(0,1,2,4,8,15),(0,1),((0,1,4,9,10921),(0xFFFFFFFF,0x80000000,7,0x7FFFFFFF,0)))]
 images=bytearray();writes=[];steps=[];rows=[]
 for c in cases:
  initial=g.fixture(c);final,calls,observations=g.reference(initial,c,True);start=len(images);a,p=g.pointers(c)
  images.extend(host_image(bytes(initial[a+i]for i in range(812))));images.extend(host_image(bytes(initial[p+i]for i in range(812))))
  step_start=len(steps)
  for step in observations:
   before=[host_image(v)for v in step['before'][:2]]+[step['before'][2].to_bytes(4,'little')]
   after=[host_image(v)for v in step['after'][:2]]+[step['after'][2].to_bytes(4,'little')]
   write_start=len(writes)
   for which,(b,d)in enumerate(zip(before,after)):
    if c.alias and which==1:continue
    writes.extend((which,i,y)for i,(x,y)in enumerate(zip(b,d))if x!=y)
   args=list(step['args'])+[0]*(4-len(step['args']))
   if step['target']in(g.TYPE,g.MODE,g.REGISTER,g.TRANSITION):args[0]=1 if args[0]==a else 2 if args[0]==p else 0xBAD0
   steps.append((step['target'],args,digest(before[0]),digest(before[1]),step['before'][2],step['answer'],write_start,len(writes)-write_start))
  rows.append((int(bool(c.alias)),start,step_start,c.coefficient,digest(host_image(bytes(final[a+i]for i in range(812)))),digest(host_image(bytes(final[p+i]for i in range(812)))),g.read(final,g.COEFF)))
 h='typedef struct {u32 which,offset;u8 value;} Write;\ntypedef struct {u32 target,a[4],sourceHash,pairedHash,coefficient,answer,writeStart,writeCount;} Step;\ntypedef struct {u32 alias,initialStart,stepStart,coefficient,finalSource,finalPaired,finalCoefficient;} Row;\n'
 h+='static const u8 images[]={'+','.join(map(str,images))+'};\nstatic const Write writes[]={'+','.join('{%d,%d,%d}'%r for r in writes)+'};\n'
 h+='static const Step steps[]={'+','.join('{0x%Xu,{%s},%s}'%(r[0],','.join('0x%Xu'%v for v in r[1]),','.join('0x%Xu'%v for v in r[2:]))for r in steps)+'};\n'
 h+='static const Row rows[]={'+','.join('{'+','.join('0x%Xu'%v for v in r)+'}'for r in rows)+'};\n'
 path=out/'native-vectors.h';path.write_text(h);return path,len(cases)
def main():
 header,count=vectors();profiles={};controls=[]
 for name,body,opt in [('O0',screen.BODY,'-O0'),('O2',screen.BODY,'-O2'),('O3',screen.BODY,'-O3')]+[(n,b,'-O2')for n,b in CONTROLS.items()]:
  if not name.startswith('O'):assert body!=screen.BODY
  p=out/('native-'+name+'.c');exe=p.with_suffix('.exe')
  p.write_text(PRE+'\n'+screen.TYPES+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name.startswith('O'):
   assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,typed_layout_asserted=True,strict_aliasing=True,UBSan=True)
  else:assert q.returncode!=0,name;controls.append(name)
 r=dict(profiles=profiles,effective_source_controls=controls,all_actor_bytes_and_call_boundary_hashes_checked=True,helper_effects_from_independent_guest_reference=True,undefined_negative_float_conversion_guest_only=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
