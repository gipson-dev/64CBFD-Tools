from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;src=(out/'variant-case1_default.c').read_text();a=src.index('void func_1500E738(void) {');b=src.index('\n}\n',a)+2;fn=src[a:b]
header=r'''
typedef int s32;typedef unsigned int u32;typedef unsigned char u8;typedef signed char s8;typedef float f32;
static s32 D_80082FA0;static s8 D_8008FD8C;static u8 D_800DCA20,D_800DCA28;static f32 D_800DCA24,D_800DCA2C;
static u32 bits(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
'''
tail=r'''
static int run(void){static const u32 states[]={0,1,2,3,4,0xffffffffu,0x80000000u,0x7fffffffu};int total=0;
 for(int i=0;i<8;i++)for(int mode=0;mode<256;mode++){
  u32 state=states[i],a=0xa5,b=0x3f200000,c,d;int sign=(s8)mode;
  if(state==0){a=0;b=0x3f800000;}else if(state==1){a=1;b=0x3f000000;}else if(state==2||state==3){a=2;b=0x3e800000;}
  if(sign==2){c=1;d=0x3f000000;}else if(sign==3||sign==4){c=2;d=0x3e800000;}else if(sign>=5&&sign<=8){c=3;d=0x3e000000;}else if(sign>=9&&sign<=16){c=4;d=0x3d800000;}else{c=0;d=0x3f800000;}
  D_80082FA0=(s32)state;D_8008FD8C=(s8)mode;D_800DCA20=0xa5;D_800DCA24=0.625f;D_800DCA28=0xa5;D_800DCA2C=0.625f;
  func_1500E738();if(D_800DCA20!=a||bits(D_800DCA24)!=b||D_800DCA28!=c||bits(D_800DCA2C)!=d)return 1;total++;
 }return total==2048?0:2;
}
'''
controls={'state0':('D_800DCA20 = 0; D_800DCA24 = 1.0f','D_800DCA20 = 1; D_800DCA24 = 1.0f'),'state2':('D_800DCA20 = 2; D_800DCA24 = 0.25f','D_800DCA20 = 2; D_800DCA24 = 0.5f'),'mode2':('D_800DCA28 = 1; D_800DCA2C = 0.5f','D_800DCA28 = 1; D_800DCA2C = 0.25f'),'mode9':('D_800DCA28 = 4; D_800DCA2C = 0.0625f','D_800DCA28 = 4; D_800DCA2C = 0.125f'),'default':('case 1: default: D_800DCA28 = 0;','case 1: default: D_800DCA28 = 1;')}
def check(name,body,opt):
 p=out/('native-'+name+'.c');exe=out/('native-'+name+'-'+opt[1:]);p.write_text(header+body+tail+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
 proc=subprocess.run([*native_command(opt,True),'-fno-builtin',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert proc.returncode==0,proc.stderr
 return subprocess.run([str(exe)],capture_output=True)
for opt in ('-O0','-O2','-O3'):
 p=check('selected',fn,opt);assert p.returncode==0,(opt,p.returncode,p.stderr);print(opt,'2048 cases',flush=True)
for name,(a,b) in controls.items():
 assert fn.count(a)==1,(name,fn.count(a));p=check('control-'+name,fn.replace(a,b),'-O2');assert p.returncode!=0,name
print('five incorrect implementations rejected',flush=True)
