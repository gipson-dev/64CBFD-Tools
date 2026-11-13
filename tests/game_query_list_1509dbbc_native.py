from pathlib import Path
import subprocess,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-query-list-1509dbbc-screen'
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
src=(out/'selected2.c').read_text();prefix=src[src.index('typedef struct QueryNodeC9EC0'):src.index('s32 func_1509DBBC(')];fn=body(src,'func_1509DBBC').replace('volatile s32 spare;','volatile s32 spare __attribute__((unused));')
controls={'mode':('arg1 == 4','arg1 == 3'),'kind':('node->kind == 2','node->kind == 3'),'row':('row < 2','row < 1'),'column':('column < 3','column < 2'),'success':('return 1;','return 0;'),'default':('return 4;','return 5;')}
code='#include <ultra64.h>\n'+prefix+'\n'+fn.replace('func_1509DBBC(','selected(',1)+'\n'
for name,(old,new) in controls.items():
 assert old in fn;code+=fn.replace('func_1509DBBC(','bad_'+name+'(',1).replace(old,new,1)+'\n'
code+=r'''
u8 D_800DCE50[0x340] __attribute__((aligned(8)));u8 D_800A6060[12] __attribute__((aligned(8)));
typedef char row_size[(sizeof(QueryRowC9EC0)==0x1a0)?1:-1];typedef char node_next[(__builtin_offsetof(QueryNodeC9EC0,next)==8)?1:-1];typedef char node_kind[(__builtin_offsetof(QueryNodeC9EC0,kind)==0x48)?1:-1];
static QueryNodeC9EC0 nodes[6][3];static int helper_calls;
void func_150E36BC(s32 a,s32*x,s32*y,s32*z){helper_calls++;*x=a;*y=a;*z=a;}
typedef s32(*F)(s32,s32,s32*);
static int check(F fn){static const s32 keys[]={0,4,5,6,25,26,-1,0x7fffffff};static const s32 modes[]={-1,0,1,4,5};static const s32 columns[]={54,76,91};
 for(int k=0;k<8;k++)for(int a=0;a<5;a++)for(int scenario=0;scenario<9;scenario++){
  QueryRowC9EC0*rows=(QueryRowC9EC0*)D_800DCE50;helper_calls=0;for(int i=0;i<0x340;i++)D_800DCE50[i]=0;for(int i=0;i<3;i++)((s32*)D_800A6060)[i]=columns[i];
  for(int slot=0;slot<6;slot++){
   if(scenario==0||(scenario>=1&&scenario<=6&&slot!=scenario-1))continue;
   int count=scenario>=7?3:1;rows[slot/3].cells[columns[slot%3]]=&nodes[slot][0];
   for(int j=0;j<count;j++){nodes[slot][j].next=j+1<count?&nodes[slot][j+1]:(QueryNodeC9EC0*)0;nodes[slot][j].kind=(scenario<=6||(scenario==7&&slot==5&&j==2))?2:1;}
  }
  s32 expected=keys[k]==25&&modes[a]==4?(scenario>=1&&scenario<=7?0:1):4;
  if(fn(keys[k],modes[a],(s32*)0)!=expected||helper_calls)return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
path=out/'native.c';path.write_text(code);runtime=Path('/lib/i386-linux-gnu/libgcc_s.so.1');assert runtime.is_file()
for opt in ('-O0','-O2','-O3'):
 exe=out/('native'+opt);r=subprocess.run([x for x in native_command(opt) if x!='-static']+['-fno-strict-aliasing','-mstackrealign',str(path),str(runtime),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
 r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
 print(opt,'360 native cases and six negative controls passed',flush=True)
