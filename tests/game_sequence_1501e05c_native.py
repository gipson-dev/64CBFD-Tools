"""SDK32 checks for sequence predicate input gating and helper mutation."""
import subprocess
from tools.experiments import game_sequence_1501e05c_match as match
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
 fn=match.MANIFEST['body'];controls={
 'scene29':('== 0x1D','== 0x1C'), 'trigger':('!= 0) {','== 0) {'),
 'event':('D_800C35E8[0] != 5','D_800C35E8[0] != 4'),
 'scene33':('== 0x21','== 0x22'), 'button1000':('& 0x1000','& 0x0800'),
 'hardware':('D_8000030C == 1','D_8000030C == 0'), 'threshold':('>= 301','>= 300'),
 'button20':('& 0x20','& 0x40'), 'lock':('D_800C3C9C == 0','D_800C3C9C != 0'),
 'override':('D_800D2E40 != 0','D_800D2E40 == 0'), 'force':('D_800C3C99 != 0','D_800C3C99 == 0'),
 'timing':('+ 30U','+ 31U'), 'slot':('D_800C35E8[slot]','D_800C35E8[slot ^ 1]')}
 for k,(a,b) in controls.items():assert fn.count(a)==1,k
 code=r'''
#include <ultra64.h>
s32 D_800BE9F0,D_8000030C,D_800C35B0[2],D_800C3640[2];u16 D_800BE710[1];
u8 D_8008FD84,D_800C35E8[2],D_800C3C9C,D_800D2E40,D_800C3C99;
static s32 answer,mutation,selected;static u32 calls,errors;
s32 func_1501D2C4(s32 scene,s32 event){calls++;if(scene!=D_800BE9F0||event!=D_800C35E8[selected])errors++;if(mutation){D_800C3C99=1;D_800C35B0[selected]=-1;D_800C3640[selected]=0;}return answer;}
'''
 for name,body in [('selected',fn)]+[(k,fn.replace(a,b,1)) for k,(a,b) in controls.items()]:code+='\n'+body.replace(match.NAME,'test_'+name,1)+'\n'
 code+=r'''
typedef s32 (*Fn)(s32);
static int check(Fn fn){static const s32 scenes[]={29,33,17};static const u16 buttons[]={0,0x20,0x1000,0x1020};
 s32 si,trig,event,bi,hw,lock,over,force,ans,mut,start,bound;u32 expected_calls;u8 expected_trigger;s32 expected;
 for(selected=0;selected<2;selected++)for(si=0;si<3;si++)for(trig=0;trig<2;trig++)for(event=4;event<=5;event++)for(bi=0;bi<4;bi++)for(hw=0;hw<2;hw++)for(lock=0;lock<2;lock++)for(over=0;over<2;over++)for(force=0;force<2;force++)for(ans=0;ans<2;ans++)for(mut=0;mut<2;mut++)for(start=300;start<=301;start++)for(bound=30;bound<=31;bound++){
  D_800BE9F0=scenes[si];D_8008FD84=trig?0x80:0;D_800C35E8[0]=event;D_800C35E8[1]=event+1;D_800BE710[0]=buttons[bi];D_8000030C=hw;D_800C3C9C=lock;D_800D2E40=over;D_800C3C99=force;
  D_800C35B0[0]=D_800C35B0[1]=start;D_800C3640[0]=D_800C3640[1]=start+bound;answer=ans;mutation=mut;calls=errors=0;
  expected=0;expected_calls=0;expected_trigger=D_8008FD84;
  if(si==0&&trig){expected=1;expected_trigger=0;}
  else if(si==0&&event!=5){}
  else if(si==1){expected=((buttons[bi]&0x1000)!=0&&hw==1&&start>=301);}
  else if((buttons[bi]&0x20)&&!lock){if(over)expected=1;else{expected_calls=1;if(ans&&(force||mut||start+30<start+bound))expected=1;}}
  if(fn(selected)!=expected||errors||calls!=expected_calls||D_8008FD84!=expected_trigger)return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(i+20)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 match.OUT.mkdir(parents=True,exist_ok=True);path=match.OUT/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=match.OUT/('native'+opt);z=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True);assert z.returncode==0,(opt,z.stderr)
  z=subprocess.run([str(exe)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr)
 return dict(cases_per_optimization=24576,negative_controls=len(controls),optimizations=3,scope='valid two-slot inputs; helper modeled')
