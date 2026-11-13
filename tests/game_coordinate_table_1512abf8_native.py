from pathlib import Path
import subprocess,sys
from tools.experiments import game_coordinate_table_1512abf8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
 fn=body((out/'after.c').read_text(),'func_1512ABF8')
 controls={'half':('* 0.5f','* 0.25f'),'mode':('mode == 27','mode == 28'),'othermode':('mode == 30','mode == 31'),'source':('= D_80089590[index]','= D_80089590[group]'),'clear':('0x130','0x12F'),'loop':('index < 4','index < 3')}
 head='''#include <ultra64.h>
 typedef struct { s16 x,y,width,height; } CoordinatePreset1512ABF8;
 CoordinatePreset1512ABF8 D_80089590[4],D_800DC200[4][4];
 u8 D_800DC0C0[304];s32 D_80082FA0,D_800BE9F0;
 '''
 code=head+fn.replace('func_1512ABF8(', 'selected(',1)+'\n'
 for name,(old,new) in controls.items():assert old in fn,name;code+=fn.replace('func_1512ABF8(', 'bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+=r'''
 static u32 calls,bad;
 void bzero(void *p,int n){calls++;if(p!=D_800DC0C0||n!=304){bad=1;return;}for(int i=0;i<n;i++)((u8*)p)[i]=0;}
 typedef void (*Fn)(void);
 static int check(Fn fn){
  static const s32 players[]={-1,0,1,2,3,4,2147483647},modes[]={0,27,30,31};
  for(u32 p=0;p<7;p++)for(u32 m=0;m<4;m++)for(u32 pattern=0;pattern<2;pattern++){
   D_80082FA0=players[p];D_800BE9F0=modes[m];calls=bad=0;
   for(u32 i=0;i<304;i++)D_800DC0C0[i]=0xA5;
   for(u32 i=0;i<4;i++){D_80089590[i].x=pattern?(s16)(i==0?-32768:i==1?32767:i==2?-3:1):35;D_80089590[i].y=pattern?(s16)(i==0?32767:i==1?-32768:i==2?-1:1):45;D_80089590[i].width=(s16)(400-i*10);D_80089590[i].height=300;}
   for(u32 i=0;i<4;i++)for(u32 j=0;j<4;j++){D_800DC200[i][j].x=-1;D_800DC200[i][j].y=-1;D_800DC200[i][j].width=-1;D_800DC200[i][j].height=-1;}
   fn();if(bad||calls!=1)return 1;
   for(u32 i=0;i<304;i++)if(D_800DC0C0[i])return 1;
   for(u32 i=0;i<4;i++)for(u32 j=0;j<4;j++){
    s16 x=D_80089590[j].x,y=D_80089590[j].y;
    if(players[p]>0&&players[p]<4){x=(s16)(x*0.5f);y=(s16)(y*0.5f);}
    if(modes[m]==27||modes[m]==30){x=(s16)(x*0.75f);y=(s16)(y*0.75f);}
    if(D_800DC200[i][j].x!=x||D_800DC200[i][j].y!=y||D_800DC200[i][j].width!=D_80089590[j].width||D_800DC200[i][j].height!=D_80089590[j].height)return 1;
   }
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'56 native cases and',len(controls),'negative controls passed',flush=True)
