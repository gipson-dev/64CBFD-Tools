import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_effect_state_callback_150bf0f4_match as p
out=p.out;root=p.root
from tools.tests import game_effect_state_callback_150bf0f4_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'selected-source.c').read_text(),'func_150BF0F4')
 controls={'fadein':('record[0x27]','record[0x2F]'),'fadeout':('record[0x2F]','record[0x27]'),'target_clamp':('if (value > target)','if (value < target)'),'zero_gate':('record[0x24] == 0 && value == 0','record[0x24] == 0 || value == 0'),'x_sign':('(u32)(s32)*(s8 *)(record + 0x2D)','(u32)*(u8 *)(record + 0x2D)'),'y_sign':('(u32)(s32)*(s8 *)(record + 0x2E)','(u32)*(u8 *)(record + 0x2E)'),'stop_threshold':('*(s16 *)(record + 0x14) <= 0','*(s16 *)(record + 0x14) < 0'),'clear_y':('*(s16 *)(record + 0x16) = 0','*(s16 *)(record + 0x16) = 1'),'saturation':('phase = 127','phase = 126'),'return_early':('return 1','return 0'),'phase':('record[0x2C] + (u32)D_800BE9E4','record[0x2C] + 1')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 s32 D_800BE9E4;
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_150BF0F4','test_'+key,1)+'\n'
 code+='''\nstruct Case {int active,value,target,tick,x,y,dx,dy,fadein,fadeout,phase,outvalue,outx,outy,outphase,result,seed;};\nstatic const struct Case cases[]={\n'''
 for c in g.cases():
  e,result=g.reference(c,g.fixture(c));vals=[c.active,c.value,c.target,c.tick,c.x,c.y,c.dx,c.dy,c.fadein,c.fadeout,c.phase_byte,e[g.RECORD+0x1f],g.signed16(g.read(e,g.RECORD+0x14,2)),g.signed16(g.read(e,g.RECORD+0x16,2)),e[g.RECORD+0x2c],result,c.seed];code+='{'+','.join(map(str,vals))+'},\n'
 code+=r'''};
 typedef s32(*T)(u8*);
 static int check(T test){unsigned i,j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  const struct Case*c=&cases[i];union {u32 align;u8 bytes[80];} u;u8 before[80],*p=u.bytes;s32 result;
  for(j=0;j<80;j++)p[j]=(j*19+c->seed*11+37)&255;
  p[0x24]=c->active;p[0x1f]=c->value;p[0x26]=c->target;p[0x27]=c->fadein;p[0x2f]=c->fadeout;p[0x2d]=c->dx;p[0x2e]=c->dy;p[0x2c]=c->phase;*(s16*)(p+0x14)=c->x;*(s16*)(p+0x16)=c->y;
  for(j=0;j<80;j++)before[j]=p[j];D_800BE9E4=c->tick;result=test(p);
  if(result!=c->result||p[0x1f]!=c->outvalue||*(s16*)(p+0x14)!=c->outx||*(s16*)(p+0x16)!=c->outy||p[0x2c]!=c->outphase||D_800BE9E4!=c->tick)return 1;
  for(j=0;j<80;j++)if(j!=0x1f&&j!=0x14&&j!=0x15&&j!=0x16&&j!=0x17&&j!=0x2c&&p[j]!=before[j])return 2;
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
