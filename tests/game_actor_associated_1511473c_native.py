from pathlib import Path
import subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-actor-associated-update-1511473c-screen';source=body(Path(__import__('os').environ.get('ACTOR_ASSOC_SOURCE',out/'selected.c')).read_text(),'func_1511473C')
preamble=r'''
#include <ultra64.h>
s32 D_800DBEF0; u8 *D_800DBEF4; f32 D_800A2F60; u8 D_800CC2D0[0x32c*3]; u16 D_800CBDA0[8];
static u32 calls,mode; static u8 *selected;
s32 func_15114348(s32 index, void *a, void *b, void *c) {
 if(a!=selected+0x14||b!=selected+0x18||c!=selected+0x1c||index < -1||index > 1) __builtin_trap();
 calls++; if(mode) *(u16 *)(selected+0x76)=1234; return 0;
}
'''
harness=r'''
static int run(void) {
 static union { u32 align; u8 bytes[0x400]; } storage;
 const s32 indexes[]={-1,0,1},counts[]={-1,0,2}; const u16 values[]={0,32767,65535};
 const f32 scales[]={0.0f,0.5f},incs[]={-1.5f,0.0f,1.5f}; unsigned long checked=0;
 for(int i=0;i<3;i++)for(int n=0;n<3;n++)for(int v=0;v<3;v++)for(int s=0;s<2;s++)for(int x=0;x<3;x++)for(int flag=0;flag<2;flag++)for(int eq=0;eq<2;eq++)for(int change=0;change<2;change++)for(int has=0;has<2;has++){
  s32 index=indexes[i]; u32 live=has && index<counts[n]; f32 result=(change?1234.0f:values[v])+scales[s]*incs[x];
  if(live && !(result>-1.0f && result<4294967296.0))continue;
  for (u32 z=0;z<sizeof(storage.bytes);z++) storage.bytes[z]=0x5a; for (u32 z=0;z<sizeof(D_800CC2D0);z++) D_800CC2D0[z]=0x53; for (u32 z=0;z<8;z++) D_800CBDA0[z]=0;
  selected=D_800CC2D0+0x32c*2; D_800DBEF4=storage.bytes+0xa0;D_800DBEF0=counts[n];D_800A2F60=scales[s];
  *(f32 *)(storage.bytes+0xa0+index*0xa0+0x64)=incs[x];*(u16 *)(selected+0x76)=values[v];*(u16 *)(selected+0x7a)=0x5a5a;selected[0x137]=flag;
  D_800CBDA0[2]=eq?index+1:index+2;mode=change;calls=0;
  func_1511473C(has?selected:0,index);
  u32 expect=live?(u32)result:values[v];
  if(calls!=live || *(u16 *)(selected+0x76)!=(u16)expect || *(u16 *)(selected+0x7a)!=(live&&flag&&eq?(u16)expect:0x5a5a))return 42;
  checked++;
 }
 return checked==2592?0:20;
}
'''
(out/'native.c').write_text(preamble+source+harness+START)
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  dest=out/('native'+opt+alias);cmd=native_command(opt)+['-mstackrealign',alias,'-o',str(dest),str(out/'native.c')];c=subprocess.run(cmd,capture_output=True,text=True);assert c.returncode==0,c.stderr
  r=subprocess.run([str(dest)],capture_output=True,text=True);print(opt,alias,'exit',r.returncode,'cases',2592, 'stderr',r.stderr.strip(),flush=True);assert r.returncode==0
