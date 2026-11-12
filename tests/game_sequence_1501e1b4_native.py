"""Native SDK32 checks for sequence transition states and call ordering."""
import subprocess
from tools.experiments import game_sequence_1501e1b4_match as match
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
 fn=match.MANIFEST['body'];controls={
 'active':('D_800C35EA[slot] == 1','D_800C35EA[slot] == 0'),
 'predicate':('func_1501E05C(slot) != 0','func_1501E05C(slot) == 0'),
 'threshold':('>= 91','>= 90'),
 'state_set':('D_800C3C88 = 1;','D_800C3C88 = 2;'),
 'timer_set':('D_800C3C89 = 30;','D_800C3C89 = 29;'),
 'query1':('func_151F2CDC() == 1','func_151F2CDC() == 2'),
 'query2':('func_151F2CDC() == 2','func_151F2CDC() == 3'),
 'countdown':('D_800BEA08 < D_800C3C89','D_800BEA08 <= D_800C3C89'),
 'timer_clear':('D_800C3C89 = 0;','D_800C3C89 = 1;'),
 'finish_state':('D_800C3C88 = 2;','D_800C3C88 = 3;'),
 'reset':('D_800C3C88 = 0;','D_800C3C88 = 3;'),
 'audio':('0x2B02','0x2B03'),
 }
 for k,(a,b) in controls.items():assert fn.count(a)==1,k
 code=r'''
#include <ultra64.h>
u8 D_800C3C88,D_800C3C89,D_8008FD84,D_800C35EA[2];s32 D_800C3640[2],D_800C35B0[2],D_800BEA08;
static s32 selected,predicate,query,mutate;static u32 trace,errors;
s32 func_1501E05C(s32 s){trace=trace*10+1;if(s!=selected)errors++;if(mutate){D_800C3640[s]=200;D_800C35B0[s]=101;}return predicate;}
void func_1517EE40(s32 a,s32 b,s32 c,s32 d,s8 e,s32 f){trace=trace*10+2;if(a||b||c||d!=30||e!=1||f||D_800C3C88!=1||D_800C3C89!=30)errors++;}
void func_1000E17C(void){trace=trace*10+3;}
s32 func_151F2CDC(void){trace=trace*10+4;return query;}
void func_151F2D6C(s32 a,s32 b){trace=trace*10+5;if(a||b!=0x2b02)errors++;}
s32 func_1501DF04(s32 s){trace=trace*10+6;if(s!=selected||D_800C3C88!=2)errors++;D_800C3C88=0x99;return 0;}
'''
 for name,body in [('selected',fn)]+[(k,fn.replace(a,b,1)) for k,(a,b) in controls.items()]:code+='\n'+body.replace(match.NAME,'test_'+name,1)+'\n'
 code+=r'''
typedef void (*Fn)(s32);
static int check(Fn fn){s32 state,active,pred,gap,q,delta,timer,mutation;u32 expected_trace;u8 expected_state,expected_timer,expected_trigger;
 static const s32 deltas[]={(-2147483647-1),-1,0,29,30,31,2147483647};
 for(selected=0;selected<2;selected++)for(state=0;state<4;state++)for(active=0;active<2;active++)for(pred=0;pred<2;pred++)for(gap=90;gap<=91;gap++)for(q=0;q<3;q++)for(delta=0;delta<7;delta++)for(timer=0;timer<2;timer++)for(mutation=0;mutation<2;mutation++){
  D_800C3C88=state;D_800C3C89=timer?30:0;D_8008FD84=0xab;D_800C35EA[selected]=active;D_800C35B0[selected]=100;D_800C3640[selected]=100+gap;D_800BEA08=deltas[delta];predicate=pred;query=q;mutate=mutation;trace=errors=0;
  expected_trace=0;expected_state=state;expected_timer=D_800C3C89;expected_trigger=0xab;
  if(state==0&&active==1){expected_trace=1;if(pred){expected_trigger=0;if((mutation?99:gap)>=91){expected_state=1;expected_timer=30;expected_trace=1234;if(q==1)expected_trace=12345;else{expected_trace=12344;if(q==2)expected_trace=123445;}}}}
  else if(state==1){if(deltas[delta]<(s32)expected_timer)expected_timer=(u8)((u32)expected_timer-(u32)deltas[delta]);else{expected_timer=0;expected_state=0;expected_trace=6;}}
  fn(selected);if(errors||trace!=expected_trace||D_800C3C88!=expected_state||D_800C3C89!=expected_timer||D_8008FD84!=expected_trigger)return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(i+20)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 match.OUT.mkdir(parents=True,exist_ok=True);path=match.OUT/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=match.OUT/('native'+opt);z=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True);assert z.returncode==0,(opt,z.stderr)
  z=subprocess.run([str(exe)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr)
 return dict(cases_per_optimization=5376,negative_controls=len(controls),optimizations=3,scope='valid two-slot state space; modeled helpers')
