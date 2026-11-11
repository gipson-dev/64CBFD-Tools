import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_effect_curve_callback_151a175c_match as p
out=p.out;root=p.root
from tools.tests import game_effect_curve_callback_151a175c_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'selected-source.c').read_text(),'func_151A175C')
 controls={'alpha_threshold':('curve[2] < age','curve[2] <= age'),'size_threshold':('curve[5] < age','curve[5] <= age'),'move_threshold':('curve[6] < age','curve[6] <= age'),'alpha_slope':('curve[0] * (curve[1] - age)','curve[3] * (curve[1] - age)'),'size_slope':('curve[3] * (curve[4] - age)','curve[0] * (curve[4] - age)'),'fraction_x':('effect->fractionX);','effect->fractionY);'),'fraction_y':('effect->fractionY);','effect->fractionZ);'),'fraction_z':('effect->fractionZ);','effect->fractionX);'),'velocity_x':('(u32)(s32)curve[10]','(u32)(s32)curve[11]'),'velocity_y':('(u32)(s32)curve[11]','(u32)(s32)curve[12]'),'velocity_z':('(u32)(s32)curve[12]','(u32)(s32)curve[10]'),'final_alpha':('age < curve[13]','age > curve[13]'),'final_size':('age < curve[15]','age > curve[15]')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad00[0x20];s16 x,y,z;u8 pad26[6];u8 fractionX,fractionZ,fractionY;u8 pad2F[5];s16 sizeX,sizeY,age;u8 pad3A[5];u8 intensity;u8 pad40[0x10];s16 curve[17];u8 tail[14];} EffectCurve1CC440;
 _Static_assert(__builtin_offsetof(EffectCurve1CC440,curve)==0x50 && __builtin_offsetof(EffectCurve1CC440,intensity)==0x3f && sizeof(EffectCurve1CC440)==128,"layout");
 s32 D_800BE9E4;
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_151A175C','test_'+key,1)+'\n'
 code+='''\nstruct Case {s32 age,t0,t1,t2,t3,t4,tick,seed,x,y,z,fx,fy,fz,sx,sy,intensity;};\nstatic const struct Case cases[]={\n'''
 for c in g.cases():
  e=g.reference(c,g.fixture(c));vals=[c.age,c.t0,c.t1,c.t2,c.t3,c.t4,c.tick,c.seed]+[g.signed16(g.read(e,g.RECORD+at,2))for at in (0x20,0x22,0x24)]+[e[g.RECORD+at]for at in (0x2c,0x2e,0x2d)]+[g.signed16(g.read(e,g.RECORD+at,2))for at in (0x34,0x36)]+[e[g.RECORD+0x3f]];code+='{'+','.join(map(str,vals))+'},\n'
 code+=r'''};
 typedef void(*T)(EffectCurve1CC440*);
 static int check(T test){unsigned i,j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  const struct Case*c=&cases[i];EffectCurve1CC440 e;u8 before[128],*p=(u8*)&e;s16 defaults[17]={-3,7,c->t0,4,-6,c->t1,c->t2,-2,3,-4,127,-1,128,c->t3,-6,c->t4,7};
  for(j=0;j<128;j++)p[j]=(j*19+c->seed*11+37)&255;e.x=-1234;e.y=2345;e.z=-32768;e.sizeX=23;e.sizeY=42;e.age=c->age;e.fractionX=0x21;e.fractionY=0xfe;e.fractionZ=0x80;e.intensity=55;
  for(j=0;j<17;j++)e.curve[j]=defaults[j];for(j=0;j<128;j++)before[j]=p[j];D_800BE9E4=c->tick;test(&e);
  if(e.x!=c->x||e.y!=c->y||e.z!=c->z||e.fractionX!=c->fx||e.fractionY!=c->fy||e.fractionZ!=c->fz||e.sizeX!=c->sx||e.sizeY!=c->sy||e.intensity!=c->intensity||D_800BE9E4!=c->tick)return 1;
  for(j=0;j<128;j++)if(j!=0x20&&j!=0x21&&j!=0x22&&j!=0x23&&j!=0x24&&j!=0x25&&j!=0x2c&&j!=0x2d&&j!=0x2e&&j!=0x34&&j!=0x35&&j!=0x36&&j!=0x37&&j!=0x3f&&p[j]!=before[j])return 2;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,valid_disjoint_record_only=True,source_installed=False);(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
