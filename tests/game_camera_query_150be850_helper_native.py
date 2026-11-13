from pathlib import Path
import subprocess,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
fn=body((out/'query-shape08.c').read_text(),'func_1509BE40')
controls={'selector':('flags &= 0xfff','flags &= 0xffe'),'count':('D_800D3840 = count + 2','D_800D3840 = count + 3'),'restore':('D_800D3840 = previous','D_800D3840 = previous + 1'),'extra':('D_800D2F60[i + 2]','D_800D2F60[i + 3]')}
code='''#include <ultra64.h>\n#include <stdarg.h>\ns32 D_800D3840; s32 D_800D2F60[32]; s32 (*D_80088498[15])(s32,s32,s32*);\n'''+fn.replace('func_1509BE40(', 'selected(',1)+'\n'
for name,(old,new) in controls.items():
 assert old in fn
 code+=fn.replace('func_1509BE40(', 'bad_'+name+'(',1).replace(old,new,1)+'\n'
code+=r'''
static s32 chosen, mutation, observed_count, observed_selector, observed_key, observed_packet[16];
static s32 callback(s32 index,s32 selector,s32 key,s32 *packet){chosen=index;observed_count=D_800D3840;observed_selector=selector;observed_key=key;for(int i=0;i<16;i++)observed_packet[i]=packet[i];if(mutation){D_800D3840=0x12345678;packet[1]=0x76543210;}return (s32)0x89abcdefu;}
#define CB(N) static s32 c##N(s32 a,s32 b,s32 *p){return callback(N,a,b,p);}
CB(0) CB(1) CB(2) CB(3) CB(4) CB(5) CB(6) CB(7) CB(8) CB(9) CB(10) CB(11) CB(12) CB(13) CB(14)
typedef s32 (*Func)(s32,...);
static int check(Func f){
 static s32 (*funcs[15])(s32,s32,s32*)={c0,c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14};
 static const int counts[]={-2,-1,0,1,2,3,4,5,7};static const int flags[]={0x1001,0x2fff,0xfabc};static const int keys[]={0,0x7fffffff,-1};
 for(int n=0;n<15;n++)D_80088498[n]=funcs[n];
 for(int a=0;a<9;a++)for(int b=0;b<3;b++)for(int c=0;c<3;c++)for(int d=0;d<2;d++){
  int count=counts[a],flag=flags[b],key=keys[c];mutation=d;chosen=-1;D_800D3840=0x12345671;
  for(int i=0;i<32;i++)D_800D2F60[i]=(s32)0xa5a5a5a5u;
  s32 result=f(count,flag,key,0x12340000,0x12340001,0x12340002,0x12340003,0x12340004,0x12340005,0x12340006,0x12340007,0x12340008,0x12340009);
  if(result!=(s32)0x89abcdefu||chosen!=((flag>>12)-1)||observed_count!=count+2||observed_selector!=(flag&0xfff)||observed_key!=key||observed_packet[0]!=(flag&0xfff)||observed_packet[1]!=key||D_800D3840!=0x12345671||D_800D2F60[1]!=(d?0x76543210:key))return 1;
  for(int i=0;i<count;i++)if(observed_packet[i+2]!=0x12340000+i)return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
path=out/'query-native.c';path.write_text(code);runtime=Path('/lib/i386-linux-gnu/libgcc_s.so.1');assert runtime.is_file()
for opt in ('-O0','-O2','-O3'):
 exe=out/('query-native'+opt);r=subprocess.run([x for x in native_command(opt) if x!='-static']+['-fno-strict-aliasing','-mstackrealign',str(path),str(runtime),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
 r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
 print(opt,'162 native cases, four negative controls passed',flush=True)
