"""SDK32 common-header entry, escaped scratch lifetime and bounded IEEE C behavior."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_particle_emission_accumulator_150ec520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_particle_emission_accumulator_150ec520_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
selected=packet.MANIFEST['selected_source'];a,b=function_span(selected,'func_150EC520');PRE=selected[:a];BODY=selected[a:b]
HARNESS=r'''
#define OFF __builtin_offsetof
typedef char layout[sizeof(void*)==4&&sizeof(struct260)==36&&OFF(ParticleEmitterRecord1199D0,emitter)==40&&sizeof(ParticleEmitterRecord1199D0)==56&&sizeof(ParticlePacket1199D0)==16&&OFF(ParticleScratch1199D0,packet)==4?1:-1];
typedef struct {s16 x,y,z,reserved6,height;u8 reservedA[11];u8 flags;u8 tail[2];}Source;
typedef struct {struct260 header;u8 reserved24[4];ParticlePacket1199D0 packet;u8 tail[8];}Output;
static ParticleEmitterRecord1199D0 record;static Source sources[2];static s16 gates[2][2];static Output outputs[8];
f32 D_800A1570,D_800A1574,D_800BE9A4;
typedef union{u32 word;f32 number;}FloatBits;
static u32 rowIndex,stepIndex,sampleCount,integerCount,factoryCount,copyCount,bad,valid;
static ParticlePacket1199D0*captured;static f32*capturedTop;
static u32 raw(f32 x){FloatBits v;v.number=x;return v.word;}
static f32 number(u32 x){FloatBits v;v.word=x;return v.number;}
static void check(int yes){if(!yes)bad=1;}
static u32 headerHash(const void*p){const u8*b=(const u8*)p;u32 i,j,h=2166136261u;for(i=0;i<40;i++){j=i==14?15:i==15?14:i;h=(h^b[j])*16777619u;}return h;}
static void compare(const u32 wanted[48]){
 u32 i,j,n=8;ParticleEmitter1199D0*e=&record.emitter;
 check(headerHash(&record)==wanted[0]);check((e->source==&sources[0]?0x50000u:0x51000u)==wanted[1]);check(raw(e->rate)==wanted[2]);
 check((e->gate==gates[0]?0x52000u:0x52100u)==wanted[3]);check(raw(e->accumulator)==wanted[4]);check(raw(D_800A1570)==wanted[5]&&raw(D_800A1574)==wanted[6]&&raw(D_800BE9A4)==wanted[7]);
 for(i=0;i<8;i++){check(headerHash(&outputs[i])==wanted[n++]);for(j=0;j<4;j++){u32 got=j==0?raw(outputs[i].packet.x):j==1?raw(outputs[i].packet.y):j==2?raw(outputs[i].packet.z):raw(outputs[i].packet.parameter);check(got==wanted[n++]);}}
}
static void call(u32 target,const u32*args,u32 count){
 const Row*r=&rows[rowIndex];u32 i;check(stepIndex<r->stepCount);if(bad)return;const Step*s=&steps[r->stepStart+stepIndex++];
 check(s->target==target);compare(s->before);for(i=0;i<count;i++)check(args[i]==s->args[i]);check(valid==s->valid);
 if(valid&1)check(raw(captured->x)==s->packet[0]);if(valid&2)check(raw(captured->y)==s->packet[1]);if(valid&4)check(raw(captured->z)==s->packet[2]);if(valid&8)check(raw(captured->parameter)==s->packet[3]);if(valid&16)check(raw(*capturedTop)==s->top);
}
u8 func_151464B8(s16*gate){
 const Row*r=&rows[rowIndex];u32 a[1]={gate==gates[0]?0x52000u:0x52100u};call(0x151464B8,a,1);
 if(r->mode&1){record.emitter.rate=.5f;record.emitter.gate=gates[1];D_800A1570=.25f;}return(u8)r->gate;
}
f32 func_150ADA68(void){
 const Row*r=&rows[rowIndex];call(0x150ADA68,0,0);
 if(r->mode&2){D_800A1570=2.f;D_800A1574=.5f;D_800BE9A4=.25f;record.emitter.rate=.75f;}return number(r->randomFloat);
}
void func_151432BC(void*source,f32*x,f32*z,f32*top,f32*y){
 const Row*r=&rows[rowIndex];Source*s=(Source*)source;u32 a[5]={source==&sources[0]?0x50000u:0x51000u,1,3,4,2};
 check((u8*)z==(u8*)x+8&&(u8*)top==(u8*)x-4&&(u8*)y==(u8*)x+4);captured=(ParticlePacket1199D0*)x;capturedTop=top;valid=sampleCount?31:8;
 call(0x151432BC,a,5);++sampleCount;*x=(f32)s->x;*z=(f32)s->z;*top=(f32)((s32)s->y+s->height);*y=(f32)((s32)s->y-s->height);valid=31;
 if(r->mode&4){record.emitter.source=&sources[1];((u8*)&record)[12]^=0x55;}
}
u32 func_150ADA20(void){
 const Row*r=&rows[rowIndex];call(0x150ADA20,0,0);++integerCount;
 if(r->mode&8){captured->parameter=(f32)integerCount;((u8*)&record)[1]=(u8)(r->context+integerCount);}return r->randoms[(integerCount-1)%8];
}
struct260*func_15149130(s16 lifetime,s8 first,s8 kind,s8 second,u8 flags,u8 code,u32 bytes,u8 identity,s32 context){
 const Row*r=&rows[rowIndex];u32 i,args[9]={(u32)(s32)lifetime,(u32)(s32)first,(u32)(s32)kind,(u32)(s32)second,flags,code,bytes,identity,(u32)context};
 call(0x15149130,args,9);++factoryCount;check(factoryCount<=8);if(bad)return 0;
 if(r->mode&16){captured->x=-(f32)factoryCount;((u8*)&record)[12]=(u8)(r->kind+factoryCount);}
 if(!(r->allocationMask&(1u<<(factoryCount-1))))return 0;
 struct260*p=&outputs[factoryCount-1].header;p->unkE=lifetime;p->unk10=first;p->unk11=kind;p->unk12=second;p->unkD=flags;p->unk13=code;
 for(i=0;i<16;i++)((u8*)p)[20+i]=0;return p;
}
void*memcpy(void*destination,const void*source,u32 bytes){
 const Row*r=&rows[rowIndex];u32 i,which=8;for(i=0;i<8;i++)if(destination==&outputs[i].packet)which=i;
 check(which<8&&source==captured);u32 a[3]={0x60000u+64*which+40,1,bytes};call(0x10022EC0,a,3);++copyCount;
 if(bad)return destination;for(i=0;i<bytes;i++)((u8*)destination)[i]=((const u8*)source)[i];
 if((r->mode&32)&&copyCount==1)record.emitter.accumulator=.5f;return destination;
}
static int run(void){
 u32 i,j;
 for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
  const Row*r=&rows[rowIndex];stepIndex=sampleCount=integerCount=factoryCount=copyCount=bad=valid=0;captured=0;capturedTop=0;
  for(i=0;i<sizeof(record);i++)((u8*)&record)[i]=0xA5;
  ((u8*)&record)[1]=(u8)r->context;((u8*)&record)[12]=(u8)r->kind;record.header.unkD=0;record.header.unkE=1000;record.header.unk10=-1;record.header.unk11=89;
  record.emitter.source=&sources[0];record.emitter.gate=gates[0];record.emitter.rate=number(r->rate);record.emitter.accumulator=number(r->accumulator);
  for(i=0;i<2;i++){for(j=0;j<sizeof(Source);j++)((u8*)&sources[i])[j]=0xA5;sources[i].x=(s16)(i?16:1);sources[i].y=(s16)(i?32:2);sources[i].z=(s16)(i?48:3);sources[i].height=(s16)(i?8:4);sources[i].flags=3;}
  gates[0][0]=gates[1][0]=0;gates[0][1]=1;gates[1][1]=0;
  for(i=0;i<sizeof(outputs);i++)((u8*)outputs)[i]=0xA5;
  D_800A1570=number(r->constants[0]);D_800A1574=number(r->constants[1]);D_800BE9A4=number(r->constants[2]);
  func_150EC520(&record.header);compare(r->final);check(stepIndex==r->stepCount);if(bad)return 1;
 }
 return 0;
}
'''
def vectors():
 cases=[c for c in g.cases()if c.fcsr==0 and c.phase==0];rows=[];steps=[]
 for c in cases:
  m=g.check(g.streams()[0],c);final,calls,observations,fcsr=g.reference(m.initial,c);start=len(steps)
  for(t,args),obs in zip(calls,observations):
   args=list(args)+[0]*(9-len(args))
   if t==g.SAMPLE:args[1:5]=[1,3,4,2]
   if t==g.COPY:args[1]=1
   steps.append((t,args,obs))
  rows.append((c,start,len(calls),g.snapshot(final)))
 def arr(values):return'{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}'
 text='typedef struct{u32 target,args[9],before[48],valid,packet[4],top;}Step;\ntypedef struct{u32 gate,accumulator,rate,constants[3],randomFloat,randoms[8],allocationMask,kind,context,mode,stepStart,stepCount,final[48];}Row;\n'
 text+='static const Step steps[]={'+','.join('{0x%Xu,%s,%s,%du,%s,0x%Xu}'%(t,arr(a),arr(o[0]),o[1],arr(o[2]),o[3])for t,a,o in steps)+'};\n'
 text+='static const Row rows[]={'+','.join('{%du,0x%Xu,0x%Xu,%s,0x%Xu,%s,%du,%du,%du,%du,%du,%du,%s}'%(c.gate_result,c.accumulator,c.rate,arr(c.constants),c.random_float,arr(c.randoms),c.allocation_mask,c.kind,c.context,c.mode,start,n,arr(final))for c,start,n,final in rows)+'};\n'
 (out/'native-vectors.h').write_text(text);return len(cases)
def main():
 count=vectors();controls={
 'reversed-gate':BODY.replace('->emitter.gate) == 0','->emitter.gate) != 0'),
 'inclusive-emission-threshold':BODY.replace('emitter->accumulator > 1.0f','emitter->accumulator >= 1.0f'),
 'missing-rate':BODY.replace('*emitter->rate','*1.0f'),
 'wrong-timestep':BODY.replace('*D_800BE9A4','*D_800A1574'),
 'signed-lifetime-remainder':BODY.replace('lifetime%131U','(s32)lifetime%131'),
 'wrong-sampler-output':BODY.replace('&scratch.packet.z','&scratch.packet.y'),
 'reset-parameter-each-iteration':BODY.replace('            scratch.packet.parameter=0.0f;\n','').replace('                func_151432BC','                scratch.packet.parameter=0.0f;\n                func_151432BC'),
 'wrong-payload-size':BODY.replace('sizeof(scratch.packet)','12'),
 'wrong-effect-kind':BODY.replace(',-1,90,-1',',-1,91,-1'),
 'cached-source':BODY.replace('            scratch.packet.parameter=0.0f;','            void *cached=emitter->source;\n            scratch.packet.parameter=0.0f;').replace('func_151432BC(emitter->source,','func_151432BC(cached,')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe');path.write_text(PRE+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode!=0,name;effective.append(name)
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_struct_layout=True,strict_aliasing=True,UBSan=True)
 r=dict(profiles=profiles,effective_source_controls=effective,independent_guest_checked_vectors=True,
  common_header_entry=True,uninitialized_scratch_not_read=True,escaped_packet_objects_valid=True,
  finite_nearest_rounding_domain=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r;return r
if __name__=='__main__':main()
