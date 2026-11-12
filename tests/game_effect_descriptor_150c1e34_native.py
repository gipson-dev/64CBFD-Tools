import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_effect_descriptor_150c1e34_match as p
out=p.out;root=p.root
from tools.tests import game_effect_descriptor_150c1e34_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_150C1E34')
 controls={
  'position_x':('position[0] = x','position[0] = z'),
  'position_y':('position[1] = y','position[1] = z'),
  'scale':('value16 = (s16)scale','value16 = (s16)scale + 1'),
  'scale_double':('scale * D_800A0228','scale * 0.5'),
  'velocity_x':('(x - previousX) * 10.0f','(x - previousX) * 9.0f'),
  'velocity_z':('(z - previousZ) * 10.0f','(z - previousZ) * 9.0f'),
  'value22':('value22 = 150','value22 = 151'),
  'value24':('value24 = 20','value24 = 21'),
  'value26':('value26 = 600','value26 = 601'),
  'alpha':('alpha = 255','alpha = 254'),
  'random':('(func_150ADA20() & 15) + 12','(func_150ADA20() & 7) + 12'),
  'flags':('flags = 1','flags = 2'),
  'submit':('func_1518CA80(&descriptor, 1)','func_1518CA80(&descriptor, 0)'),
  'return':('return 1;','return 0;'),
 }
 offsets=list(g.reference(g.cases()[0]))
 widths=[g.reference(g.cases()[0])[i][0] for i in offsets]
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {f32 position[3];u8 retained0C[10];s16 value16,value18,value1A,value1C,value1E,value20,value22,value24,value26;u8 firstRGB[3],secondRGB[3],alpha,value2F;s8 value30;u8 flags;} EffectDescriptor150C1E34;
 _Static_assert(sizeof(EffectDescriptor150C1E34)==52 && __builtin_offsetof(EffectDescriptor150C1E34,value16)==22 && __builtin_offsetof(EffectDescriptor150C1E34,flags)==49,"layout");
 f64 D_800A0228=0.1757;
 struct Case {u32 v[7],random;u32 expected[22];};
 static const struct Case cases[]={
 '''
 assert len(offsets)==22
 for c in g.cases():
  values=[g.bits(v) for v in (c.x,c.y,c.z,c.px,c.py,c.pz,c.scale)]
  expected=[g.reference(c)[i][1] for i in offsets]
  code+='{{'+','.join('0x%Xu'%v for v in values)+'},0x%Xu'%c.random+',{'+','.join('0x%Xu'%v for v in expected)+'}},\n'
 code+='};\nstatic const u8 offsets[22]={'+','.join(map(str,offsets))+'};\nstatic const u8 widths[22]={'+','.join(map(str,widths))+'};\n'
 code+=r'''
 static const struct Case *current;static int calls,bad;
 static f32 value(u32 u){union {u32 u;f32 f;} x;x.u=u;return x.f;}
 void func_151429E0(u8 mode,u8 *r,u8 *g,u8 *b){calls++;if(mode||g!=r+1||b!=r+2||calls>2)bad=1;if(calls==1){*r=0x31;*g=0x72;*b=0xb3;}else{*r=0x42;*g=0x83;*b=0xc4;}}
 s32 func_150ADA20(void){calls++;if(calls!=3)bad=1;return (s32)current->random;}
 void func_1518CA80(EffectDescriptor150C1E34 *p,u8 mode){u32 i,j,v;const u8 *bytes=(const u8*)p;calls++;if(calls!=4||mode!=1)bad=1;
 for(i=0;i<22;i++){v=0;for(j=0;j<widths[i];j++)v|=(u32)bytes[offsets[i]+j]<<(8*j);if(v!=current->expected[i])bad=1;}}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace('func_150C1E34','test_'+name,1)+'\n'
 code+=r'''
 typedef s32(*T)(s32,s32,f32,f32,f32,f32,f32,f32,s32,s32,f32,s32,f32,s32,s32);
 static int check(T test){u32 i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){const struct Case *c=&cases[i];s32 answer;current=c;calls=bad=0;
 answer=test(1,7,value(c->v[0]),value(c->v[1]),value(c->v[2]),value(c->v[3]),value(c->v[4]),value(c->v[5]),0x7fffffff,(s32)0x80000000u,14.0f,0x12345678,value(c->v[6]),(s32)0xabcdef01u,255);
 if(answer!=1||bad||calls!=4)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_150C1E34_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_150C1E34_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-4000:],r.stderr[-4000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers='modeled',initialized_packet_fields_only=True,source_installed=False)
 (out/'native_150C1E34_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
