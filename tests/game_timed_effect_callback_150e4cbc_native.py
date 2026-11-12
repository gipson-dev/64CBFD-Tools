"""SDK32 native comparison and discriminating controls for the private callback."""
import json,subprocess
from tools.tests import game_timed_effect_callback_150e4cbc_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((g.out/'independent-selected.c').read_text(),'func_150E4CBC')
 controls={
  'age_threshold':('age < 9','age < 8'),
  'ramp_multiplier':('* 90U','* 89U'),
  'fade_divisor':('/ 600','/ 601'),
  'fade_rate':('* 17U','* 16U'),
  'intensity_boundary':('step < effect->intensity','step <= effect->intensity'),
  'end_threshold':('age >= 609','age >= 608'),
  'base_factor':('* 14.0f','* 13.0f'),
  'timer_increment':('(u32)age + (u32)D_800BE9E4','(u32)age - (u32)D_800BE9E4'),
  'amount_scale':('(1.0f / 256.0f)','(1.0f / 128.0f)'),
  'fade_state':('effect->state = -1','effect->state = -2'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 retained00[0x90];s32 age;s16 base,strength,state;u8 retained9A[8];s16 amountA,amountB;u8 retainedA6[0xE];u8 intensity;} TimedEffect111670;
 _Static_assert(__builtin_offsetof(TimedEffect111670,age)==0x90 && __builtin_offsetof(TimedEffect111670,amountA)==0xA2 && __builtin_offsetof(TimedEffect111670,intensity)==0xB4,"offsets");
 s32 D_800BE9E4;
 struct Case {u32 age,strength,base,tick,intensity,seed,expectedAge,expectedState,expectedA,expectedB,expectedIntensity;};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m=g.reference(c,g.fixture(c))
  vals=(c.age,c.strength,c.base,c.tick,c.intensity,c.seed,g.read(m,g.RECORD+0x90),g.read(m,g.RECORD+0x98,2),g.read(m,g.RECORD+0xa2,2),g.read(m,g.RECORD+0xa4,2),g.read(m,g.RECORD+0xb4,1))
  code+='{'+','.join('0x%Xu'%(x&0xffffffff)for x in vals)+'},\n'
 code+='};\n'
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace('func_150E4CBC','test_'+name,1)+'\n'
 code+=r'''
 typedef void(*Test)(TimedEffect111670 *);
 static int check(Test test){u32 i,j;union {TimedEffect111670 effect;u8 bytes[0xc0];} record;u8 before[0xc0];
  for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){const struct Case *c=&cases[i];
   for(j=0;j<sizeof(record.bytes);j++)record.bytes[j]=(u8)(j*19+c->seed*11+37);
   record.effect.age=(s32)c->age;record.effect.base=(s16)c->base;record.effect.strength=(s16)c->strength;
   record.effect.state=12345;record.effect.amountA=-123;record.effect.amountB=456;record.effect.intensity=(u8)c->intensity;D_800BE9E4=(s32)c->tick;
   for(j=0;j<sizeof(record.bytes);j++)before[j]=record.bytes[j];
   test(&record.effect);
   if((u32)record.effect.age!=c->expectedAge||(u16)record.effect.state!=c->expectedState||(u16)record.effect.amountA!=c->expectedA||(u16)record.effect.amountB!=c->expectedB||record.effect.intensity!=c->expectedIntensity||(u32)D_800BE9E4!=c->tick)return 1;
   for(j=0;j<sizeof(record.bytes);j++)if(!(j>=0x90&&j<0x94)&&!(j>=0x98&&j<0x9a)&&!(j>=0xa2&&j<0xa6)&&j!=0xb4&&before[j]!=record.bytes[j])return 2;
  }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=g.out/'native_150E4CBC_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=g.out/('native_150E4CBC_screen'+opt);p=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=g.root,capture_output=True,text=True)
  assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout[-3000:],p.stderr[-3000:])
  p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
  profiles[opt]=dict(cases=len(list(g.cases())),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,valid_disjoint_record_only=True,source_installed=False)
 (g.out/'native_150E4CBC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
