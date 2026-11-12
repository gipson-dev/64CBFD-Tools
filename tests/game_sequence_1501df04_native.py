"""SDK32 sequence completion, helper mutations and actor-byte checks."""
import subprocess
from tools.experiments import game_sequence_1501df04_match as match
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
 fn=match.MANIFEST['body'];controls={
  'provider':('func_100127D0() != 0','func_100127D0() == 0'),
  'found':('found != NULL','found == NULL'),
  'slot':('func_1501DE18(slot);','func_1501DE18(slot + 1);'),
  'pending':('pending != 0 && D_800C35C4 == 0','pending == 0 && D_800C35C4 == 0'),
  'fade1':('D_800C35A9 == 0','D_800C35A9 != 0'),
  'fade2':('D_800C3C8A != 1','D_800C3C8A == 1'),
  'fade3':('D_800C3C8D == 0','D_800C3C8D != 0'),
  'actors':('interaction_state != 0','interaction_state == 0'),
  'byte':('*(u8 *)&actor->padA4 = 0','*((u8 *)&actor->padA4 + 1) = 0'),
  'flag':('D_800C3663 = 0','D_800C3663 = 1'),
  'mode':('D_800DBFF4 = 4','D_800DBFF4 = 5'),
  'finish':('D_800C3672 = 1','D_800C3672 = 0')}
 for k,(a,b) in controls.items():assert fn.count(a)==(2 if k in ('slot','pending') else 1),k
 code=r'''
#include <ultra64.h>
#include "structs.h"
_Static_assert(sizeof(void*)==4 && sizeof(struct127)==0x32c && __builtin_offsetof(struct127,padA4)==0xa4,"SDK32 layout");
struct127 D_800CC2D0[25];__asm__(".globl D_800D121C\n.set D_800D121C,D_800CC2D0+20300");extern s32 D_800D121C;
u8 D_800C3C99,D_800C35C4,D_800C35A9,D_800C3C8D,D_800C3663,D_800DBFF4,D_800C3672;s8 D_800C3C8A;
static s32 selected,provider,found,pattern;static u32 calls,events,errors;
s32 func_100127D0(void){events=events*10+1;return provider;}
void func_151F2BA8(void){events=events*10+2;}
struct127 *func_15072208(struct127 *a,s32 b){events=events*10+3;if(a!=D_800CC2D0||b)errors++;return found?&D_800CC2D0[1]:NULL;}
void func_15060F28(struct127 *a,s32 b){events=events*10+4;if(a!=&D_800CC2D0[1]||b)errors++;}
void func_1501DE18(s32 s){events=events*10+5;if(s!=selected)errors++;calls++;if(pattern==1)D_800C3C99=0;if(pattern==2&&calls>=2)D_800C3C99=0;if(pattern==3)D_800C35C4=1;}
void func_1517EE40(s32 a,s32 b,s32 c,s32 d,s8 e,s32 f){events=events*10+6;if(a||b||c||d!=30||e||f)errors++;}
void func_1000E17C(void){events=events*10+7;if(D_800C3663!=0)errors++;D_800DBFF4=9;D_800C3672=9;}
'''
 for name,body in [('selected',fn)]+[(k,fn.replace(a,b,1)) for k,(a,b) in controls.items()]:code+='\n'+body.replace(match.NAME,'test_'+name,1)+'\n'
 code+=r'''
typedef void (*Fn)(s32);
static int check(Fn fn){s32 p,f,pat,fa,fb,fc,i;u32 expected_events,expected_calls;u8 *bytes;
 for(selected=0;selected<2;selected++)for(p=0;p<2;p++)for(f=0;f<2;f++)for(pat=0;pat<4;pat++)for(fa=0;fa<2;fa++)for(fb=0;fb<2;fb++)for(fc=0;fc<2;fc++){
  provider=p;found=f;pattern=pat;calls=events=errors=0;D_800C3C99=pat?1:0;D_800C35C4=0;D_800C35A9=fa;D_800C3C8A=fb;D_800C3C8D=fc;D_800C3663=9;D_800DBFF4=8;D_800C3672=7;
  for(i=0;i<25;i++){D_800CC2D0[i].interaction_state=(i%2);bytes=(u8 *)&D_800CC2D0[i].padA4;bytes[0]=0x31;bytes[1]=0x42;bytes[2]=0x53;bytes[3]=0x64;}
  expected_events=1;if(p)expected_events=expected_events*10+2;expected_events=expected_events*10+3;if(f)expected_events=expected_events*10+4;
  expected_calls=(pat==1?2:pat==2?3:1);for(i=0;i<(s32)expected_calls;i++)expected_events=expected_events*10+5;
  if(!fa&&!fb&&!fc)expected_events=expected_events*10+6;expected_events=expected_events*10+7;
  fn(selected);if(errors||calls!=expected_calls||events!=expected_events||D_800C3663||D_800DBFF4!=4||D_800C3672!=1)return 1;
  for(i=0;i<25;i++){bytes=(u8 *)&D_800CC2D0[i].padA4;if(bytes[0]!=(i%2?0:0x31)||bytes[1]!=0x42||bytes[2]!=0x53||bytes[3]!=0x64)return 2;}
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(i+20)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 match.OUT.mkdir(parents=True,exist_ok=True);path=match.OUT/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=match.OUT/('native'+opt);z=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True);assert z.returncode==0,(opt,z.stderr)
  z=subprocess.run([str(exe)],capture_output=True,timeout=20);assert z.returncode==0,(opt,z.returncode,z.stderr)
 return dict(cases_per_optimization=256,negative_controls=len(controls),optimizations=3,scope='25 valid actor records; bounded modeled helper mutations')
