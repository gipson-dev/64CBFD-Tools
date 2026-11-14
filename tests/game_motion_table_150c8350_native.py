from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-table-150c8350-screen';src=Path(__import__('os').environ.get('MOTION_TABLE_SOURCE',out/'selected.c')).read_text();begin=src.index('typedef struct { u8 group, pad1;');end=src.index('\n/* Advance the motion table',begin);body=src[begin:end]
prefix='#include <ultra64.h>\ns32 D_800BE4E0; s32 D_800BE9E4; u8 D_800BE9A0;\n'
harness='''
static MotionEntry150C8350 actual[10], expected[10];
static const s16 pos[]={0,-32768,32767,1280,-1,1279,10,300};
static const s16 cur[]={0,-1,32767,-16,16,-200,300,100};
static const s8 dir[]={0,-128,127,1,-1,2,-3,4};
static const s16 dst[]={0,-32768,32767,256,-256,200,100,300};
static const u32 ticks[]={0,1,3,0xffffffffU,0x08000000U};
static const u8 halves[]={0,1,127,255};
static void model(MotionEntry150C8350 *e,u32 tick,u8 half){
 s32 current=e->current, target=e->target, delta, magnitude, step=(s32)(tick<<4), next;
 if(current!=target){
  if(current<0)target=-target;
  delta=target-current;magnitude=delta<0?-delta:delta;
  if(magnitude<step)next=target;
  else next=(s32)((u32)current+(u32)step*(delta<0?0xffffffffU:1U));
  e->current=(s16)(u16)next;current=e->current;
 }
 e->position=(s16)(u16)((s32)e->position+current*e->direction*half);
 if(e->position>=0x500){
  e->position=(s16)(u16)(e->position-0x500);
  e->position=(s16)(u16)(0x500-e->position);
  e->direction=(s8)(u8)(-e->direction);
  if(e->position>=0x500)e->position=0x4ff;
 }else if(e->position<0){
  e->position=(s16)(u16)(-e->position);
  e->direction=(s8)(u8)(-e->direction);
  if(e->position<0)e->position=0;
 }
}
static int run(void){
 int cases=0;
 for(int pattern=0;pattern<8;pattern++)for(int ti=0;ti<5;ti++)for(int hi=0;hi<4;hi++)for(int seed=1;seed<=3;seed+=2){
  for(int i=0;i<10;i++){
   int k=(pattern+i*seed)%8;
   actual[i].group=(u8)(i+13);actual[i].pad1=0xa5;actual[i].pad3=0x5a;
   actual[i].position=pos[k];actual[i].current=cur[k];actual[i].target=dst[k];actual[i].direction=dir[k];
   expected[i]=actual[i];model(&expected[i],ticks[ti],halves[hi]);
  }
  D_800BE4E0=(s32)(u32)actual;D_800BE9E4=(s32)ticks[ti];D_800BE9A0=halves[hi];func_150C8350();
  for(int i=0;i<10;i++)if(actual[i].group!=expected[i].group||actual[i].pad1!=expected[i].pad1||actual[i].pad3!=expected[i].pad3||actual[i].position!=expected[i].position||actual[i].current!=expected[i].current||actual[i].target!=expected[i].target||actual[i].direction!=expected[i].direction)return 10;
  cases++;
 }
 return cases==320?0:20;
}
'''
controls={'wrong-target':('if (current < 0) desired = -target;','if (current < 0) desired = target;'),'wrong-step':('D_800BE9E4 << 4','D_800BE9E4 << 3'),'wrong-limit':('entry->position >= 0x500','entry->position > 0x500')}
def run(label,source,opt,alias):
 c=out/('native-'+label+'.c');exe=out/('native-'+label+opt+'-'+alias);c.write_text(prefix+source+harness+START);p=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(c),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True).returncode
for opt in ('-O0','-O2','-O3'):
 for alias in ('strict','no-strict'):assert run('candidate',body,opt,alias)==0,(opt,alias)
for name,(old,new) in controls.items():
 assert old in body;altered=body.replace(old,new)
 for alias in ('strict','no-strict'):assert run(name,altered,'-O2',alias)!=0,(name,alias)
report={'cases_per_configuration':320,'optimizations':3,'alias_modes':2,'ubsan_trapping':True,'negative_controls':list(controls),'uncredited':True};(out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
