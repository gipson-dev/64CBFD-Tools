from pathlib import Path
import subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-pointer-list-validation-15114f44-screen';source=body(Path(__import__('os').environ.get('POINTER_LIST_SOURCE',out/'selected.c')).read_text(),'func_15114F44')
prefix=r'''#include <ultra64.h>
s32 D_800BE9F0; u32 *D_800DBDD8[2]; s32 D_800DBE18[2]; extern s32 D_800DBE20[];
__asm__(".globl D_800DBE20\n.set D_800DBE20,D_800DBE18+8");
s32 D_8003C8E0,D_800DBF9C,D_800DBFA0,D_800DBFA4;
static u32 called,mutate;
void func_150AD770(void) {called++;if(mutate){D_800DBE18[0]=1;D_800DBE18[1]=1;}}
'''
harness=r'''
static u32 entries[2][3][3];
static int run(void) {
 const s32 modes[]={0,0x12,0x13,0x36,0x37},counts[]={-1,0,1,3};int checked=0;
 for(int m=0;m<5;m++)for(int n=0;n<4;n++)for(int k=0;k<4;k++)for(int pattern=0;pattern<11;pattern++)for(int change=0;change<2;change++){
  int expectedCalls=0; s32 expectCount[2]={counts[n],counts[k]};u32 expectError=0x5a5a5a5a;
  for(int g=0;g<2;g++){D_800DBDD8[g]=&entries[g][0][0];D_800DBE18[g]=expectCount[g];for(int r=0;r<3;r++)for(int c=0;c<3;c++)entries[g][r][c]=0x80001000+g*0x100+r*12+c*4;}
  if(pattern==10){entries[0][0][0]=entries[0][1][0]=0x90000000U;}
  else if(pattern){int slot=(pattern-1)%3;int bad=(pattern-1)/3;entries[0][0][slot]=bad==0?0x90000000U:bad==1?0x80001001U:0x7ffffffcU;}
  D_800BE9F0=modes[m];D_8003C8E0=0x5a5a5a5a;D_800DBF9C=D_800DBFA0=D_800DBFA4=0x5a5a5a5a;called=0;mutate=change;
  if(modes[m]==0x12||modes[m]==0x13||modes[m]==0x36){
   for(int g=0;g<2;g++)for(int i=0;i<expectCount[g];i++){
    u32 x=entries[g][i][0],y=entries[g][i][1],z=entries[g][i][2];
    if((x&0xf0000000U)!=0x80000000U||(y&0xf0000000U)!=0x80000000U||(z&0xf0000000U)!=0x80000000U||((x|y|z)&3)){
     expectError=0x0c00005a;expectedCalls++;if(change)expectCount[0]=expectCount[1]=1;
    }
   }
  }
  func_15114F44(0x12345678,0x23456789,0x3456789a);
  if(called!=(u32)expectedCalls||(u32)D_8003C8E0!=expectError)return 42;
  if(modes[m]==0x12||modes[m]==0x13||modes[m]==0x36){if(D_800DBF9C!=0x12345678||D_800DBFA0!=0x23456789||D_800DBFA4!=0x3456789a)return 42;}
  else if(D_800DBF9C!=0x5a5a5a5a||D_800DBFA0!=0x5a5a5a5a||D_800DBFA4!=0x5a5a5a5a)return 42;
  if(D_800DBE18[0]!=expectCount[0]||D_800DBE18[1]!=expectCount[1])return 42;checked++;
 }
 return checked==1760?0:20;
}
'''
(out/'native.c').write_text(prefix+source+harness+START)
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  dest=out/('native'+opt+alias);cmd=native_command(opt)+['-mstackrealign',alias,'-o',str(dest),str(out/'native.c')];c=subprocess.run(cmd,capture_output=True,text=True);assert c.returncode==0,c.stderr
  r=subprocess.run([str(dest)],capture_output=True,text=True);print(opt,alias,'exit',r.returncode,flush=True);assert r.returncode==0
