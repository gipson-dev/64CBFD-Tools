from pathlib import Path
import sys,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();out=r/'conker/build/game-ranged-effect-151a9634-screen'
from tools.tests import game_ranged_effect_151a9634_behavior as b
s=(out/'selected.c').read_text();a=s.index('typedef struct {\n    f32 base0, base1, range0, range1;');z=s.index('s32 func_151A9834',a);piece=s[a:z];head,body=piece.split('/* Create an effect',1);body='/* Create an effect'+body
bad={
 'wrong_base':body.replace('parameters->base0','parameters->base1'),
 'wrong_lifetime':body.replace('parameters->lifetimeBase','parameters->countBase'),
 'wrong_tag':body.replace('tag = 0x71','tag = 0x72'),
 'wrong_mode':body.replace('? 0 : 2','? 1 : 2'),
 'wrong_variant':body.replace('parameters->variantBase','parameters->countBase'),
 'wrong_destination':body.replace('result + 0x160','result + 0x164'),
 'wrong_copy_size':body.replace('&extra, 8','&extra, 6')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid *memcpy(void *, const void *, u32);\n'+head+'\n'.join(v.replace('func_151A9634','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 floats[3],draws[4];s32 span;u32 flags,seed,outcome,ranges[2],scale,lifetime,count,variant,tag,mode,ownerC,owner1;} Case;
static const Case cases[]={
'''
rows=[]
for c in b.cases():
 if c.phase or c.mutation:continue
 m,calls,obs=b.reference(b.fixture(c),c);args=next(a for t,a in calls if t==b.EMIT);pair=obs[0][1];packet=obs[1][1] if c.outcome else bytes(8)
 values=[','.join('0x%Xu'%x for x in c.floats),','.join('0x%Xu'%x for x in c.draws),str(c.span),str(c.flags),str(c.seed),str(c.outcome),','.join('0x%Xu'%int.from_bytes(pair[i:i+4],'big') for i in (0,4)),str(int.from_bytes(packet[:4],'big')),str(int.from_bytes(packet[4:6],'big')),*('0x%Xu'%args[i] for i in (2,3,11,12,16,17))]
 rows.append('{{%s},{%s},%s,%s,%s,%s,{%s},%s,%s,%s,%s,%s,%s,%s,%s}'%tuple(values))
code+=',\n'.join(rows)+'\n};\n'
code+=r'''
typedef char ParameterLayout[sizeof(RangedEffect151A9634)==44 && __builtin_offsetof(RangedEffect151A9634,flags)==40?1:-1];
typedef char ExtraLayout[sizeof(EffectExtra151A9634)==8?1:-1];
typedef struct {u8 padding[128];RangedEffect151A9634 parameters;} Owner;
static Owner owner;static f32 position[3];static u8 output[1024];
static const Case*current;static u32 fstep,istep,emitted,copied,error;static volatile u32 seedState;
static f32 real(u32 x){Bits b;b.u=x;return b.f;}static u32 word(f32 x){Bits b;b.f=x;return b.u;}
f32 func_150ADA68(void){u32 n=fstep++;if(n>=3||istep) {error=1;return 0;}seedState=seedState*1664525u+1013904223u;return real(current->floats[n]);}
s32 func_150ADA20(void){u32 n=istep++;if(fstep!=3||n>=4){error=1;return 0;}seedState=seedState*1664525u+1013904223u;return (s32)current->draws[n];}
u8 *func_1514B8E4(f32*p,f32*r,s16 count,u8 variant,void*unused,f32 zero,f32 one0,f32 one1,u8 v8,u8 v9,u8 v10,u8 tag,u8 mode,s16 parameter0,s16 parameter1,s32 v15,u8 ownerC,s32 owner1){
 if(p!=position||word(r[0])!=current->ranges[0]||word(r[1])!=current->ranges[1]||
 (u32)(s32)count!=current->count||variant!=current->variant||unused||word(zero)||word(one0)!=0x3f800000||word(one1)!=0x3f800000||
 v8!=0x21||v9!=0x23||v10!=2||tag!=current->tag||mode!=current->mode||parameter0!=-32768||parameter1!=32767||v15!=8||ownerC!=current->ownerC||owner1!=(s32)current->owner1||
 fstep!=3||istep!=((current->flags&1)?3:4)||emitted)error=1;
 emitted++;return current->outcome?output:0;
}
void *memcpy(void*dest,const void*src,u32 n){const EffectExtra151A9634*p=(const EffectExtra151A9634*)src;
 if(dest!=output+0x160||n!=8||!emitted||copied||word(p->scale)!=current->scale||(u16)p->lifetime!=current->lifetime)error=1;
 copied++;return dest;
}
typedef void(*Candidate)(u8*,f32*,s32,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(8))+'};\n'
code+=r'''
static int run(void){u32 i,j,k,killed=0;RangedEffect151A9634*p=&owner.parameters;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<8;j++){
   for(k=0;k<128;k++)owner.padding[k]=(k*19+current->seed*7)&255;
   p->base0=10.;p->base1=-2.;p->range0=5.;p->range1=3.;p->extraBase=1.5;p->extraRange=.25;
   p->countBase=-32760;p->countRange=current->span;p->lifetimeBase=32760;p->lifetimeRange=current->span;
   p->variantBase=250;p->variantRange=current->span;p->parameter0=-32768;p->parameter1=32767;p->flags=current->flags;
   fstep=istep=emitted=copied=error=0;seedState=current->seed;
   candidates[j]((u8*)&owner,position,0x87654321,0x12345678);
   if(!emitted||copied!=current->outcome)error=1;
   if(error){if(j==0)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=out/'native-ranged-effect.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('native-ranged-effect'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
  profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,retained_bytes_excluded=2,typed_disjoint_inputs=True,helpers_scripted=True,helper_mutation_limited_to_disjoint_seed=True)
(out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
