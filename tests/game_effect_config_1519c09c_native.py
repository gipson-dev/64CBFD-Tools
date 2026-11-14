"""Native32 candidate test with allocation failure, overlap and mutations."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-effect-config-1519c09c-durable'
source=(out/'formatted.c').read_text();start=source.index('extern f32 D_800A8AF8;');end=source.index('\ns32 func_1519C200',start)
body=source[start:end]
HARNESS='''
f32 D_800A8AF8;
static union { struct225 align; u8 bytes[128]; f32 values[32]; } block;
static u8 owner[8]; static f32 externalPosition[3];
static f32 *currentPosition; static int success, mutation, calls, errors;
static s32 expectedX,expectedY,expectedZ; static u32 expectedData;
void *memcpy(void *dst,const void *src,size_t n){ u8 *d=dst;const u8 *s=src;for(size_t i=0;i<n;i++)d[i]=s[i];return dst; }
struct225 *func_151602C0(Header *h, Header2 *p, s32 a,s32 b,s32 c,s32 d,u8 ff,u8 z,s32 sz,u8 pri,s32 user){
 calls++;
 if(h->unk0!=2||h->unk1!=2||h->unk2!=300||h->unk4!=34||p->unk0!=expectedX||p->unk4!=expectedY||p->unk8!=expectedZ)errors++;
 if(a!=17||b!=34||c!=51||d!=68||ff!=255||z!=0||sz!=36||pri!=85||(u32)user!=expectedData)errors++;
 if(mutation){currentPosition[0]=123.0f;D_800A8AF8=-.5f;p->unk0=0x12345678;h->unk0=9;}
 return success?(struct225 *)block.bytes:0;
}
static u32 bits(f32 f){union{f32 f;u32 u;} v;v.f=f;return v.u;}
static int run(void){
 static const f32 points[3][3]={{0.,-0.,1.75f},{-10.75f,42.9f,-1.25f},{123456.,-654321.,32767.75f}};
 int cases=0;
 for(int p=0;p<3;p++)for(int con=0;con<2;con++)for(success=0;success<2;success++)for(mutation=0;mutation<2;mutation++)for(int overlap=0;overlap<2;overlap++)for(int seed=0;seed<2;seed++){
  u32 expect[8]={bits(35.),bits(5.),bits(110.),bits(1.),bits(0.),bits(7.),bits(con?-.75f:0.),bits(127.)};
  for(int i=0;i<128;i++)block.bytes[i]=(u8)(i*29+seed*13+55);
  currentPosition=overlap?&block.values[6]:externalPosition;
  for(int i=0;i<3;i++)currentPosition[i]=points[p][i];
  expectedX=(s32)points[p][0];expectedY=(s32)points[p][1];expectedZ=(s32)points[p][2];
  expectedData=0x34567890u;D_800A8AF8=con?-.75f:0.;calls=errors=0;
  struct225 *got=func_1519C09C(owner,currentPosition,17,34,51,68,85,(s32)expectedData);
  if(got!=(success?(struct225 *)block.bytes:0)||calls!=1||errors)return 1;
  if(success){for(int i=0;i<8;i++)if(bits(block.values[6+i])!=expect[i])return 2;
   if(*(u32 *)(block.bytes+0x38)!=(u32)owner)return 3;}
  cases++;
 }
 return cases==96?0:4;
}
'''
controls={
 'wrong-header':('header.unk0 = 2;','header.unk0 = 3;'),
 'wrong-config':('config.sixth = 7.0f;','config.sixth = 8.0f;'),
 'wrong-coord':('coords.unk4 = (s32)position[1];','coords.unk4 = (s32)position[0];'),
 'wrong-owner-offset':('(u8 *)result + 0x38','(u8 *)result + 0x3c'),
}
def run(name,code,opt,alias):
 src=out/(name+'.c');exe=out/(name+'-'+opt[1:]+'-'+alias)
 src.write_text('#include <ultra64.h>\n#include "structs.h"\n#include <string.h>\n'+code+'\n'+HARNESS+START)
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
