"""SDK32 native tests for the private quad-placement candidate."""
import json, subprocess
from tools.tests import game_quad_ground_placement_15172b20_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 selected=body((g.out/'independent-selected.c').read_text(),'func_15172B20')
 controls={
     'missing_hit':('hit == 0 || ', ''),
     'missing_sentinel':(' || height == D_800A7158', ''),
     'wrong_sine':('radius * s', 'radius * (s + c)'),
     'wrong_cosine':('radius * c', 'radius * (c + s)'),
     'wrong_angle':('angle - 90.0f', 'angle + 90.0f'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef union { f32 f; u32 u; } Float;
 static u32 raw(f32 f){Float x;x.f=f;return x.u;}
 static f32 real(u32 u){Float x;x.u=u;return x.f;}
 f32 D_800A7154, D_800A7158;
 struct Case {u32 xyz[3], angle, radius, cosine, sine, mode, image, answer, radians, x, z;};
 static const struct Case cases[]={
 '''
 for c in g.cases():
     calls,_=g.reference(c)
     x,y,z=c.xyz
     code+='{{0x%Xu,0x%Xu,0x%Xu},0x%Xu,0x%Xu,0x%Xu,0x%Xu,%du,0x%Xu,0x%Xu,0x%Xu,0x%Xu,0x%Xu},\n'%(
         x,y,z,c.angle,c.radius,*c.trig,c.mode,c.image,c.answer,calls[0][1][0],calls[2][1][6],calls[2][1][8])
 code+=r'''};
 static const struct Case *current;static u32 bad,count;
 f32 cosf(f32 a){if(count++!=0||raw(a)!=current->radians)bad=1;return real(current->cosine);}
 f32 sinf(f32 a){if(count++!=1||raw(a)!=current->radians)bad=1;return real(current->sine);}
 void func_1510E82C(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,f32 x,f32 y,f32 z,f32 end,u16 mode,s32 extra){
  if(count++!=2||!a||!c||!e||b||d||f||raw(x)!=current->x||raw(y)!=current->xyz[1]||raw(z)!=current->z||raw(end)!=current->xyz[1]||mode||extra)bad=1;
  *(s32*)a=current->mode?0x50000:0;*(f32*)c=current->mode==1?D_800A7158:42.5f;*(s32*)e=0x42424242;
 }
 s32 func_151725FC(Vtx *v,void *p,f32 x,f32 y,f32 z,f32 angle,s32 scale,u8 image){
  if(count++!=3||v!=(Vtx*)0x30000||p!=(void*)0x50000||raw(x)!=current->x||raw(y)!=raw(42.5f)||raw(z)!=current->z||raw(angle)!=current->angle||scale!=0x12345678||image!=(u8)current->image)bad=1;
  return (s32)current->answer;
 }
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
     if name!='selected':assert text!=selected,name
     code+='\n'+text.replace('func_15172B20','test_'+name,1)+'\n'
 code+=r'''
 typedef s32(*Test)(Vtx*,f32,f32,f32,f32,s32,s32,u8);
 static int check(Test test){u32 i;D_800A7154=real(0x3c8efa35);D_800A7158=-1000.0f;
  for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){s32 result;current=&cases[i];bad=count=0;
  result=test((Vtx*)0x30000,real(current->xyz[0]),real(current->xyz[1]),real(current->xyz[2]),real(current->angle),(s32)current->radius,0x12345678,(u8)current->image);
  if(bad||count!=(current->mode==2?4u:3u)||(u32)result!=(current->mode==2?current->answer:0))return 1;
  }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=g.out/'native_15172B20_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
     exe=g.out/('native_15172B20_screen'+opt)
     p=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=g.root,capture_output=True,text=True)
     assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout[-3000:],p.stderr[-3000:])
     p=subprocess.run([str(exe)],capture_output=True)
     assert p.returncode==0,(opt,p.returncode,p.stderr)
     profiles[opt]=dict(cases=len(list(g.cases())),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False)
 (g.out/'native_15172B20_screen.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True);return report
