import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_randomized_effect_constructor_151ae984_match as p
out=p.out;root=p.root
from tools.tests import game_randomized_effect_constructor_151ae984_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_151AE984')
 controls={
  'x_sign':('velocity[0] = -x','velocity[0] = x'),
  'y_sign':('velocity[1] = -y','velocity[1] = y'),
  'z_sign':('velocity[2] = -z','velocity[2] = z'),
  'velocity_scale':('-x * D_800A9D8C','-x * D_800A9D90'),
  'first_scale':('first * D_800A9D90','first * D_800A9D8C'),
  'first_bias':('+ D_800A9D94','+ D_800A9D90'),
  'first_mod':('firstValue % 31U','firstValue % 30U'),
  'second_mod':('secondValue % 101U','secondValue % 100U'),
  'second_scale':('second * 219.0f','second * 218.0f'),
  'second_bias':('+ 77.0f','+ 76.0f'),
  'mode':('second * 219.0f + 77.0f, mode','second * 219.0f + 77.0f, mode ^ 1'),
  'selector':('0, 0, 1, 0, selector, 1','0, 0, 1, 0, selector ^ 1, 1'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 f32 D_800A9D8C,D_800A9D90,D_800A9D94;
 struct Case {u32 vector[3],randoms[4],mode,selector,answer,velocity[3],arguments[16];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  _,velocity,args,answer=g.reference(c)
  code+='{{'+','.join('0x%Xu'%v for v in c.vector)+'},{'+','.join('0x%Xu'%v for v in c.randoms)+'},'+','.join('0x%Xu'%v for v in (c.mode,c.selector,c.answer))+',{'+','.join('0x%Xu'%v for v in velocity)+'},{'+','.join('0x%Xu'%v for v in args)+'}},\n'
 code+=r'''};
 static const struct Case *current;static u32 calls,bad;static f32 position[3];
 static f32 value(u32 v){union {u32 u;f32 f;}x;x.u=v;return x.f;}
 static u32 word(f32 v){union {u32 u;f32 f;}x;x.f=v;return x.u;}
 f32 func_150ADA68(void){u32 i=calls++;if(i==0)return value(current->randoms[0]);if(i==3)return value(current->randoms[3]);bad=1;return 0;}
 s32 func_150ADA20(void){u32 i=calls++;if(i==1)return (s32)current->randoms[1];if(i==2)return (s32)current->randoms[2];bad=1;return 0;}
 void *func_151D9014(void *p,f32 *v,u8 a2,f32 a3,s16 a4,u8 a5,f32 a6,u8 a7,f32 a8,f32 a9,u8 a10,s32 a11,u8 a12,u8 a13,u8 a14,s32 a15){
  u32 i,actual[16]={0,0,a2,word(a3),(u32)(s32)a4,a5,word(a6),a7,word(a8),word(a9),a10,(u32)a11,a12,a13,a14,(u32)a15};
  calls++;if(calls!=5||p!=position)bad=1;for(i=0;i<3;i++)if(word(v[i])!=current->velocity[i])bad=1;
  for(i=2;i<16;i++)if(actual[i]!=current->arguments[i])bad=1;return (void*)current->answer;}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace('func_151AE984','test_'+name,1)+'\n'
 code+=r'''
 typedef void *(*T)(void *,f32,f32,f32,u8,u8);
 static int check(T test){u32 n;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){const struct Case *c=&cases[n];void *result;current=c;calls=bad=0;
  D_800A9D8C=value(0x3dd2f1ab);D_800A9D90=value(0x3f1a1cad);D_800A9D94=value(0xbf85c290);
  result=test(position,value(c->vector[0]),value(c->vector[1]),value(c->vector[2]),(u8)c->mode,(u8)c->selector);
  if(bad||calls!=5||(u32)result!=c->answer)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_151AE984_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_151AE984_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-4000:],r.stderr[-4000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False)
 (out/'native_151AE984_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
