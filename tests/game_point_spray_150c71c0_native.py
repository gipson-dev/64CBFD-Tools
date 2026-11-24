"""Actual SDK32 emitter C against independently guest-checked packet vectors."""
from pathlib import Path
import itertools,json,subprocess,sys
from tools.experiments import game_point_spray_150c71c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_point_spray_150c71c0_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
selected=packet.MANIFEST['selected_source'];a,b=function_span(selected,'func_150C71C0');BODY=selected[a:b]
def hash_bytes(values):
 h=2166136261
 for x in values:h=((h^x)*16777619)&0xFFFFFFFF
 return h
def snapshot(m,c):
 v,constants,emitter,other=g.snapshot(m,c)
 return list(v)+list(constants)+[hash_bytes(emitter)]
PRE=r'''#include <ultra64.h>
#include "structs.h"
#define OFF __builtin_offsetof
typedef char emitter_layout[sizeof(void*)==4&&sizeof(struct17)==12&&sizeof(struct102)==472&&OFF(struct102,unk74)==0x74?1:-1];
f32 D_800A0498,D_800A049C,D_800A04A0,D_800A04A4;
f32 func_150ADA68(void);u32 func_150ADA20(void);
void *func_151DB5D0(u8,const struct17*,const struct17*,f32,f32,f32,f32,s16,u8,s16,s16,u8,u8,s32);
'''
HARNESS=r'''
typedef union{u32 word;f32 number;} FloatBits;
static struct102 emitter;static f32 vectors[4][3];
static u32 rowIndex,stepIndex,floatIndex,integerIndex,bad,output;
static void check(int yes){if(!yes)bad=1;}
static u32 raw(f32 v){FloatBits x;x.number=v;return x.word;}
static u32 loadbits(const void *p,u32 at){const u8 *b=(const u8 *)p+at;return (u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
static f32 number(u32 v){FloatBits x;x.word=v;return x.number;}
static f32 *pointer(u32 i){return rows[rowIndex].alias==1?vectors[0]:rows[rowIndex].alias==2?vectors[i<2?0:2]:vectors[i];}
static u32 emitterhash(void){
 const u8 *p=(const u8*)&emitter;u32 i,j,h=2166136261u;
 for(i=0;i<sizeof(emitter);i++){j=i>=0x74&&i<0x78?0x77-(i-0x74):i;h=(h^p[j])*16777619u;}
 return h;
}
static void compare(const u32 wanted[17]){
 u32 i,j,n=0;for(i=0;i<4;i++)for(j=0;j<3;j++)check(raw(pointer(i)[j])==wanted[n++]);
 check(raw(D_800A0498)==wanted[12]&&raw(D_800A049C)==wanted[13]&&raw(D_800A04A0)==wanted[14]&&raw(D_800A04A4)==wanted[15]);
 check(emitterhash()==wanted[16]);
}
static const Step *call(u32 target){
 const Row *r=&rows[rowIndex];check(stepIndex<r->stepCount);if(bad)return &steps[0];
 const Step *s=&steps[r->stepStart+stepIndex++];check(s->target==target);compare(s->before);return s;
}
f32 func_150ADA68(void){
 const Row *r=&rows[rowIndex];u32 i,j;call(0x150ADA68);++floatIndex;
 if((r->mode&1)&&floatIndex==1){for(i=0;i<4;i++)for(j=0;j<3;j++)pointer(i)[j]=40.f+j;emitter.unk74=17.f;}
 if((r->mode&2)&&floatIndex==2){D_800A0498=2.f;D_800A049C=3.f;D_800A04A0=5.f;D_800A04A4=7.f;((u8*)&emitter)[0xC]^=0x55;((u8*)&emitter)[1]^=0xAA;}
 return number(r->floats[floatIndex-1]);
}
u32 func_150ADA20(void){
 const Row *r=&rows[rowIndex];call(0x150ADA20);++integerIndex;
 if(r->mode&4){D_800A04A0=8.f+integerIndex;((u8*)&emitter)[0xC]=(u8)(r->kind+integerIndex);}
 return r->integers[integerIndex-1];
}
void *func_151DB5D0(u8 k,const struct17 *p,const struct17 *v,f32 size,f32 first,f32 second,f32 spread,s16 a,u8 b,s16 c,s16 d,u8 e,u8 f,s32 context){
 const Step *s=call(0x151DB5D0);u32 i,args[14]={k,1,2,raw(size),raw(first),raw(second),raw(spread),(u32)(s32)a,b,(u32)(s32)c,(u32)(s32)d,e,f,(u32)context};
 for(i=0;i<14;i++)check(args[i]==s->args[i]);
 check((const void *)p==(const void *)pointer(0));
 check(loadbits(p,0)==s->position[0]&&loadbits(p,4)==s->position[1]&&loadbits(p,8)==s->position[2]);
 check(raw(v->unk0)==s->velocity[0]&&raw(v->unk4)==s->velocity[1]&&raw(v->unk8)==s->velocity[2]);
 output=0x13579BDF;return &output;
}
static int run(void){
 u32 i,j;
 for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
  const Row *r=&rows[rowIndex];stepIndex=floatIndex=integerIndex=bad=output=0;
  for(i=0;i<sizeof(emitter);i++)((u8*)&emitter)[i]=(u8)((i+16)*19+0xA5);
  emitter.unk74=number(r->coefficient);((u8*)&emitter)[0xC]=(u8)r->kind;((u8*)&emitter)[1]=(u8)r->context;
  for(i=0;i<4;i++)for(j=0;j<3;j++)pointer(i)[j]=number(r->vectors[3*i+j]);
  D_800A0498=number(r->constants[0]);D_800A049C=number(r->constants[1]);D_800A04A0=number(r->constants[2]);D_800A04A4=number(r->constants[3]);
  void (*callback)(f32*,f32*,f32*,f32*,f32,struct102*)=func_150C71C0;
  callback(pointer(0),pointer(1),pointer(2),pointer(3),number(r->fraction),&emitter);
  compare(r->final);check(stepIndex==6&&floatIndex==3&&integerIndex==2&&output==0x13579BDF);
  if(bad)return 42;
 }
 return 0;
}
'''
def vectors():
 cases=[g.Case(kind=i,context=255-i)for i in range(256)]
 cases += [g.Case(fraction=g.bits(f),coefficient=g.bits(k),alias=alias,mode=mode)
           for f,k,alias,mode in itertools.product((0.,1.,-.5,.1),(0.,1.25,-2.),range(3),(0,1,2,4,7))]
 cases += [g.Case(integers=(a,b))for a,b in itertools.product((0,1,15,16,155,156,0x7FFFFFFF,0x80000000,0xFFFFFFFF),repeat=2)]
 cases += [g.Case(integers=(a,0x80000000))for a in range(31)]
 cases += [g.Case(integers=(0xffffffff,b))for b in range(101)]
 cases += [g.Case(vectors=(v,)*12,fraction=f,coefficient=k)for v,f,k in itertools.product((0,0x80000000),(0,g.bits(1.)),(0,0x80000000,g.bits(-1.)))]
 rows=[];steps=[];program=g.streams()[0]
 for c in cases:
  assert c.alias!=3 and not(c.mode&8)and c.fcsr==0
  machine=g.check(program,c);initial=g.fixture(c);final,calls,observations,fcsr=g.reference(initial,c)
  assert g.public(machine.memory)==g.public(final)
  replay=dict(initial);start=len(steps);counts={}
  for (t,args),observation in zip(calls,observations):
   assert g.snapshot(replay,c)==observation[0]
   normalized=list(args)+[0]*(14-len(args))
   if t==g.EMIT:normalized[1:3]=[1,2]
   steps.append((t,normalized,observation[1],observation[2],snapshot(replay,c)))
   counts[t]=counts.get(t,0)+1;g.effect(replay,c,t,counts[t],g.STACK)
  assert g.public(replay)==g.public(final)
  rows.append((c,start,snapshot(final,c)))
 def arr(values):return'{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}'
 text='typedef struct{u32 target,args[14],position[3],velocity[3],before[17];}Step;\ntypedef struct{u32 vectors[12],fraction,coefficient,constants[4],floats[3],integers[2],kind,context,alias,mode,stepStart,stepCount,final[17];}Row;\n'
 text+='static const Step steps[]={'+','.join('{0x%Xu,%s,%s,%s,%s}'%(t,arr(a),arr(p),arr(v),arr(s))for t,a,p,v,s in steps)+'};\n'
 text+='static const Row rows[]={'+','.join('{%s,0x%Xu,0x%Xu,%s,%s,%s,%s,%s}'%(arr(c.vectors),c.fraction,c.coefficient,arr(c.constants),arr(c.floats),arr(c.integers),','.join('0x%Xu'%v for v in(c.kind,c.context,c.alias,c.mode,start,6)),arr(final))for c,start,final in rows)+'};\n'
 (out/'native-vectors.h').write_text(text);return len(cases)
def main():
 count=vectors();controls={
 'reversed-difference':BODY.replace('(second[0] - first[0])','(first[0] - second[0])'),
 'wrong-coefficient':BODY.replace('0.4070000052f','0.408f'),
 'missing-float-RNG-call':BODY.replace('thirdRandom = func_150ADA68();','thirdRandom = secondRandom;'),
 'signed-opacity-remainder':BODY.replace('opacityRandom % 101U','(s32)opacityRandom % 101'),
 'wrong-life-remainder':BODY.replace('% 31U','% 32U'),
 'wrong-size-factor':BODY.replace('firstRandom * 70.0f','firstRandom * 71.0f'),
 'wrong-late-global':BODY.replace('secondRandom * D_800A0498 + D_800A049C','secondRandom * D_800A0498 + D_800A04A4'),
 'wrong-identity-byte':BODY.replace('((u8 *)emitter)[0xC]','((u8 *)emitter)[0xD]'),
 'wrong-life-division':BODY.replace('255 / lifetime','254 / lifetime'),
 'wrong-context':BODY.replace('((u8 *)emitter)[1]','((u8 *)emitter)[2]')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe')
  path.write_text(PRE+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode==42,(name,q.returncode,q.stderr);effective.append(dict(name=name,comparison_exit=42,source_sha256=packet.sha(path),binary_sha256=packet.sha(exe)))
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_struct_layout=True,strict_aliasing=True,UBSan=True,source_sha256=packet.sha(path),binary_sha256=packet.sha(exe))
 r=dict(profiles=profiles,effective_source_controls=effective,independent_guest_checked_vectors=True,
        fourteen_argument_words_and_all_packet_values=True,no_signal_or_UBSan_trap_counted=True,all_call_boundary_states=True,signed_zero_cases=True,
        input_vector_aliases=True,incoming_home_and_emitter_overlap_excluded_from_native=True,
        source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
