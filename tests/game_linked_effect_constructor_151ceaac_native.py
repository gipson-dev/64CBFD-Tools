"""Native32 constructor screen with real helper behavior and mutations."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-linked-effect-constructor-151ceaac-durable'
source=(out/'formatted.c').read_text();start=source.index('typedef struct {\n    u8 *owner; u8 identity;');end=source.index('\ns32 func_151CEC10(f32 *arg0',start);body=source[start:end]
HARNESS='''
f32 D_800AB008;
static union { u32 align; u8 b[160]; } owner,attachment,effect,output;
static int randomCalls,success,mutation,errors,factoryCalls;
static u8 expectedIdentity;static u8 *givenOwner,*givenAttachment;static u8 expectedChannel;
static u32 bits(f32 f){union{f32 f;u32 u;} v;v.f=f;return v.u;}
static u32 word(const u8 *p){u32 v;memcpy(&v,p,4);return v;}
void *memcpy(void *dst,const void *src,u32 n){u8 *d=dst;const u8 *s=src;for(u32 i=0;i<n;i++)d[i]=s[i];return dst;}
f32 func_150ADA68(void){
 randomCalls++;
 if(mutation&&randomCalls==1){owner.b[0x3b]=0x22;*(f32 *)(owner.b+0x14)=8.5f;*(f32 *)(attachment.b+0x40)=9.25f;D_800AB008=3.f;}
 return randomCalls==1?.25f:.5f;
}
s32 func_151CEC10(f32 *out,u8 *own,u8 *attach){
 if(attach){memcpy(out,attach+0x40,12);}else{memcpy(out,own+0x14,12);}return 1;
}
u8 *func_15147A80(void *ptr,s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,void *h,u8 channel,s32 context){
 LinkedEffectRequest151CEAAC *r=ptr;factoryCalls++;
 if(a!=40||b!=40||c!=0||d!=15||e!=15||f!=0||g!=0||h!=0||channel!=expectedChannel||(u32)context!=0x87654321u)errors++;
 if(r->lifetime!=300||r->mode!=16||r->active!=17||r->kind!=3||r->count!=25)errors++;
 if(bits(r->position[0])!=bits(givenAttachment?(mutation?9.25f:-4.25f):(mutation?8.5f:1.25f)))errors++;
 if(bits(r->position[1])!=bits(givenAttachment?5.5f:-2.5f)||bits(r->position[2])!=bits(givenAttachment?-6.75f:3.75f))errors++;
 return success?effect.b:0;
}
static int run(void){
 int cases=0;static const u32 modes[]={0,1,0x100,0x1ff};
 for(int pointerCase=0;pointerCase<3;pointerCase++)for(int mode=0;mode<4;mode++)for(success=0;success<2;success++)for(mutation=0;mutation<2;mutation++)for(int seed=0;seed<2;seed++){
  for(int i=0;i<160;i++)owner.b[i]=attachment.b[i]=effect.b[i]=output.b[i]=(u8)(i*29+seed*13+49);
  owner.b[0x3b]=0x87;*(f32 *)(owner.b+0x14)=1.25f;*(f32 *)(owner.b+0x18)=-2.5f;*(f32 *)(owner.b+0x1c)=3.75f;
  *(f32 *)(attachment.b+0x40)=-4.25f;*(f32 *)(attachment.b+0x44)=5.5f;*(f32 *)(attachment.b+0x48)=-6.75f;
  *(u8 **)(effect.b+0x98)=output.b;givenOwner=pointerCase==1?0:owner.b;givenAttachment=pointerCase==0?0:attachment.b;
  expectedIdentity=givenOwner?0x87:0;expectedChannel=0xab;D_800AB008=2.;randomCalls=factoryCalls=errors=0;
  u8 *got=func_151CEAAC(givenOwner,givenAttachment,(u8)modes[mode],expectedChannel,(s32)0x87654321u);
  if(got!=(success?effect.b:0)||randomCalls!=2||factoryCalls!=1||errors)return 1;
  if(success){
   if(word(output.b)!=(u32)givenOwner||output.b[4]!=expectedIdentity||word(output.b+8)!=(u32)givenAttachment)return 2;
   if(word(output.b+12)!=bits(0.)||word(output.b+16)!=bits(1.)||word(output.b+20)!=bits(0.)||word(output.b+24)!=bits(1.))return 3;
   if(output.b[28]!=((modes[mode]&255)?2:0)||word(output.b+32)!=bits(500.)||word(output.b+36)!=bits(mutation?3.:2.))return 4;
  }
  cases++;
 }
 return cases==96?0:5;
}
'''
controls={
 'wrong-count':('request.count = 25;','request.count = 24;'),
 'wrong-flags':('effectFlags = 2;','effectFlags = 1;'),
 'wrong-random':('* 400.0f + 400.0f','* 400.0f + 401.0f'),
 'wrong-copy-length':('&payload, 0x28','&payload, 0x24'),
}
def run(name,code,opt,alias):
 src=out/(name+'.c');exe=out/(name+'-'+opt[1:]+'-'+alias)
 src.write_text('#include <ultra64.h>\n#include "structs.h"\nvoid *memcpy(void *, const void *, u32);\n'+code+'\n'+HARNESS+START)
 cmd=native_command(opt)+['-mstackrealign','-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(src),'-o',str(exe)]
 p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True,text=True).returncode
for opt in ('-O0','-O2','-O3'):
 for alias in ('strict','no-strict'):
  assert run('native-candidate',body,opt,alias)==0,(opt,alias)
  for name,(old,new) in controls.items():
   assert body.count(old)==1
   assert run('control-'+name,body.replace(old,new),opt,alias)!=0,(opt,alias,name)
report={'cases_per_configuration':96,'optimizations':3,'alias_modes':2,'controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
