from pathlib import Path
from importlib.machinery import SourceFileLoader
import subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_point_transform_match import read
from tools.experiments import game_angular_smoother_15049688_match as packet
from tools.tests import game_angular_smoother_15049688_reference as R
O=packet.OUT;G=R.G;source=packet.MANIFEST['selected_source'];f=body(source,'func_15049688')
def run():
 controls={
  'strength':('difference * strength','difference * 1.0f'),
  'damping':('* damping * deltaTime','* 1.0f * deltaTime'),
  'time_step':('* damping * deltaTime','* damping * 1.0f'),
  'initial_direction':('difference < 0.0f','difference > 0.0f'),
  'threshold':('magnitude < 10.0f','magnitude < 0.0f'),
  'next_direction':('nextDifference < 0.0f','nextDifference > 0.0f'),
  'velocity_zero':('*velocity = 0.0f','*velocity = 1.0f'),
  'snap_order':('*angle = target;\n            *velocity = 0.0f;','*velocity = 0.0f;\n            *angle = target;'),
  'integration':('*angle += *velocity * deltaTime','*angle += *velocity * 0.0f'),
  'normalization':('func_15048758(angle);','(void)angle;')}
 code='#include <ultra64.h>\nf32 func_15048A70(f32,f32);\nf32 fabsf(f32);\nvoid func_15048758(f32 *);\n'+f.replace('func_15049688(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert f.count(old)==1,(name,old);code+=f.replace('func_15049688(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 rows=[]
 for row in G.corpus():
  for alias in (False,True):
   initial,args=G.fixture(row,alias);expected,calls=R.reference(initial,args)
   data=lambda m:[read(m,0x20004-4+4*j) for j in range(4)]
   rows.append('{{%s},{%s},{%s},%d,%d}'%(','.join('0x%Xu'%v for v in data(initial)),','.join('0x%Xu'%v for v in(args[1],*args[3:])),','.join('0x%Xu'%v for v in data(expected)),alias,len(calls)-1))
 code+='\ntypedef union {u32 u[4];f32 f[4];} World;\ntypedef struct {u32 initial[4],args[4],expected[4],alias,calls;} Test;\nstatic const Test tests[]={\n'+',\n'.join(rows)+'\n};\n'
 code+=r"""
 static u32 delta_calls,normal_calls;
 f32 fabsf(f32 x){union {u32 u;f32 f;}v;v.f=x;v.u &= 0x7fffffff;return v.f;}
 f32 func_15048A70(f32 a,f32 b){f32 d=a-b;delta_calls++;if(d>180.0f)a-=360.0f;else if(d<=-180.0f)b-=360.0f;return b-a;}
 void func_15048758(f32 *p){normal_calls++;while(*p<0.0f)*p+=360.0f;while(*p>=360.0f)*p-=360.0f;}
 typedef void (*Routine)(f32*,f32,f32*,f32,f32,f32);
 static int check(Routine f){u32 i,j;World w,a;for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++){
  for(j=0;j<4;j++){w.u[j]=tests[i].initial[j];a.u[j]=tests[i].args[j];}delta_calls=normal_calls=0;
  f(w.f+1,a.f[0],w.f+(tests[i].alias?1:2),a.f[1],a.f[2],a.f[3]);
  for(j=0;j<4;j++)if(w.u[j]!=tests[i].expected[j])return 1;
  if(delta_calls!=tests[i].calls||normal_calls!=1)return 2;
  }return 0;}
 static int run(void){if(check(selected))return 10;
 """
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');(O/'native.c').write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=O/('native'+opt);result=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-fno-builtin-fabsf',str(O/'native.c'),'-o',str(exe)],capture_output=True,text=True);assert result.returncode==0,result.stderr
  result=subprocess.run([str(exe)],capture_output=True,timeout=30);assert result.returncode==0,(opt,result.returncode,result.stderr)
  print(opt,'native cases',len(rows),'effective controls',len(controls),'UBSan')
