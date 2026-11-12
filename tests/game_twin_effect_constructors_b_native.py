import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_twin_effect_constructors_match as p
out=p.out;root=p.root
from tools.tests import game_twin_effect_constructors_b_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'variant_151B50F4_source.c').read_text(),'func_151B50F4')
 controls={
  'x_sign':('velocity[0] = -x','velocity[0] = x'),
  'y_sign':('velocity[1] = -y','velocity[1] = y'),
  'z_sign':('velocity[2] = -z','velocity[2] = z'),
  'velocity_scale':('f32 scale = D_800AA3E8','f32 scale = D_800AA3EC'),
  'first_scale':('first * D_800AA3F0','first * D_800AA3E8'),
  'first_bias':('+ D_800AA3F4','+ D_800AA3F0'),
  'first_mask':('duration & 15U','duration & 7U'),
  'second_mod':('alpha % 45U','alpha % 44U'),
  'second_scale':('second * 202.0f','second * 201.0f'),
  'second_bias':('+ 142.0f','+ 141.0f'),
  'variant':('variant = 1','variant = 0'),
  'selector':('0, 0, 1, 0, selector, 1','0, 0, 1, 0, selector ^ 1, 1'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 f32 D_800AA3E8,D_800AA3EC,D_800AA3F0,D_800AA3F4;
 struct Case {u32 vector[3],randoms[5],selector,answer,phase,velocity[3],arguments[16];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  _,velocity,args,answer=g.reference(c)
  code+='{{'+','.join('0x%Xu'%v for v in c.vector)+'},{'+','.join('0x%Xu'%v for v in c.randoms)+'},'+','.join('0x%Xu'%v for v in (c.selector,c.answer,c.phase))+',{'+','.join('0x%Xu'%v for v in velocity)+'},{'+','.join('0x%Xu'%v for v in args)+'}},\n'
 code+=r'''};
 static const struct Case *current;static u32 calls,bad;static f32 position[3];
 static f32 value(u32 v){union {u32 u;f32 f;}x;x.u=v;return x.f;}
 static u32 word(f32 v){union {u32 u;f32 f;}x;x.f=v;return x.u;}
 f32 func_150ADA68(void){u32 i=calls++;if(i==1)return value(current->randoms[1]);if(i==4)return value(current->randoms[4]);bad=1;return 0;}
 s32 func_150ADA20(void){u32 i=calls++;if(i==0)return (s32)current->randoms[0];if(i==2)return (s32)current->randoms[2];if(i==3)return (s32)current->randoms[3];bad=1;return 0;}
 void *func_151D9014(void *p,f32 *v,u8 a2,f32 a3,s16 a4,u8 a5,f32 a6,u8 a7,f32 a8,f32 a9,u8 a10,s32 a11,u8 a12,u8 a13,u8 a14,s32 a15){
  u32 i,actual[16]={0,0,a2,word(a3),(u32)(s32)a4,a5,word(a6),a7,word(a8),word(a9),a10,(u32)a11,a12,a13,a14,(u32)a15};
  calls++;if(calls!=6||p!=position)bad=1;for(i=0;i<3;i++)if(word(v[i])!=current->velocity[i])bad=1;
  for(i=2;i<16;i++)if(actual[i]!=current->arguments[i])bad=1;return (void*)current->answer;}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace('func_151B50F4','test_'+name,1)+'\n'
 code+=r'''
 typedef void *(*T)(f32 *,f32,f32,f32,u8);
 static int check(T test){u32 n;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){const struct Case *c=&cases[n];void *result;current=c;calls=bad=0;
  D_800AA3E8=value(c->phase?0x3e051eb9:0x3dd2f1ab);D_800AA3EC=value(c->phase?0x3fd9999a:0x3f000000);D_800AA3F0=value(c->phase?0x3e010625:0x3f1a1cad);D_800AA3F4=value(c->phase?0xbf33b646:0xbf85c290);
  result=test(position,value(c->vector[0]),value(c->vector[1]),value(c->vector[2]),(u8)c->selector);
  if(bad||calls!=6||(u32)result!=c->answer)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_151B50F4_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_151B50F4_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-4000:],r.stderr[-4000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False)
 (out/'native_151B50F4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
