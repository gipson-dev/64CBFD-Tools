from pathlib import Path
import subprocess,sys
root=Path.cwd();sys.path.insert(0,str(root));out=root/'conker/build/game-camera-condition-150be850-screen'
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
fn=body((out/'camera-abi-shape1.c').read_text(),'func_150BE850')
controls={'condition':('value != -1','value == -1'),'mode':('!= 8','== 8'),'flag':('~4','~8'),'height':('= height;','= height + width;'),'event':('0x400E, 1','0x400E, 0')}
code='''#include <ultra64.h>\n#include <stdarg.h>\ntypedef struct struct108 struct108; f32 D_800A00B0,D_800A00B4; u8 D_800CC335;\ns32 func_1509BE40(s32,...); void func_1509BFB0(s32,s32,s32,...); void func_1512868C(struct108*); s32 func_15123934(struct108*,s32,s32,s32,s32); void func_151254F4(struct108*,s32);void func_15123070(struct108*);s32 func_151239CC(struct108*,s32);\n'''+fn.replace('func_150BE850(', 'selected(',1)+'\n'
for name,(old,new) in controls.items():
 assert old in fn;code+=fn.replace('func_150BE850(', 'bad_'+name+'(',1).replace(old,new,1)+'\n'
code+=r'''
static union {u64 align;u8 bytes[0x800];} camera;
static int first,second,third,mode,activate,leave,mutation,query,command,init,request,notify,update,release,bad;
static s32 get(s32 off){return *(s32*)(camera.bytes+off);}static void set(s32 off,s32 val){*(s32*)(camera.bytes+off)=val;}
s32 func_1509BE40(s32 count,...){va_list ap;s32 flags,key;va_start(ap,count);flags=va_arg(ap,s32);key=va_arg(ap,s32);va_end(ap);if(count||query>2||flags!=(query==0?0x2006:query==1?(first|0x2000):0x2000)||key!=(query==0?0xb7:query==1?0xbc:0xbb))bad=1;return query++==0?first:query==2?second:third;}
void func_1509BFB0(s32 n,s32 op,s32 value,...){if(n||op!=0x400e||value!=((second&&third!=-1)?1:0))bad=1;command++;}
void func_1512868C(struct108 *p){if((void*)p!=(void*)camera.bytes)bad=1;init++;if(mutation)set(0x134,77);}
s32 func_15123934(struct108*p,s32 a,s32 b,s32 c,s32 d){if((void*)p!=(void*)camera.bytes||a!=8||b||c!=(mutation&&mode!=8?77:42)||d!=3)bad=1;request++;return activate;}
void func_151254F4(struct108*p,s32 value){if((void*)p!=(void*)camera.bytes||value!=((second&&third!=-1)?-1:0))bad=1;notify++;if(mutation)set(0x84,0x1004);}
void func_15123070(struct108*p){if((void*)p!=(void*)camera.bytes)bad=1;update++;}
s32 func_151239CC(struct108*p,s32 type){if((void*)p!=(void*)camera.bytes||type!=3)bad=1;release++;return leave;}
typedef void(*F)(s32);
static int check(F f){
 for(first=0;first<=3;first+=3)for(second=0;second<2;second++)for(int t=0;t<2;t++)for(mode=0;mode<=8;mode+=8)for(activate=0;activate<2;activate++)for(leave=0;leave<2;leave++)for(mutation=0;mutation<2;mutation++){
  third=t?0:-1;query=command=init=request=notify=update=release=bad=0;
  for(int i=0;i<0x800;i++)camera.bytes[i]=0x5a;set(0x2c,mode);set(0x134,42);set(0x84,0x12345674);set(0x674,0x40000000);set(0x348,0x40400000);set(0x34c,0x40800000);set(0x374,0x40a00000);set(0x190,0x40c00000);*(s16*)(camera.bytes+0x73c)=42;D_800A00B0=1.25f;D_800A00B4=2.5f;D_800CC335=0;
  f((s32)camera.bytes);int active=second&&third!=-1;int want_notify=active?activate:leave;
  if(bad||query!=3||command!=(active||leave)||init!=(active&&mode!=8)||request!=active||notify!=want_notify||update!=active||release!=!active)return 1;
  int wantflag=0x12345674;if(want_notify&&mutation)wantflag=0x1004;if(active&&activate)wantflag=(wantflag|0x1000200)&~4;
  if(get(0x84)!=wantflag||get(0x134)!=(active&&mode!=8&&mutation?77:42)||get(0x674)!=((active&&activate)||(!active&&leave)?0:0x40000000)||*(s16*)(camera.bytes+0x73c)!=(active&&activate?0:42))return 1;
  if(get(0x348)!=(active?0x3fa00000:0x40400000)||get(0x34c)!=(active?0x3fa00000:0x40800000)||get(0x374)!=(active?0x40200000:0x40a00000)||get(0x190)!=(active?0:0x40c00000))return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
path=out/'camera-native.c';path.write_text(code);runtime=Path('/lib/i386-linux-gnu/libgcc_s.so.1');assert runtime.is_file()
for opt in ('-O0','-O2','-O3'):
 exe=out/('camera-native'+opt);r=subprocess.run([x for x in native_command(opt) if x!='-static']+['-fno-strict-aliasing','-mstackrealign',str(path),str(runtime),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
 r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
 print(opt,'128 native cases, five negative controls passed',flush=True)
