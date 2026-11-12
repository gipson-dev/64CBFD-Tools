import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_four_damping_callbacks_match as p
out=p.out;root=p.root
from tools.tests import game_four_damping_callbacks_guest as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
controls={
 'x_add':('state->x *= *factor;','state->x += *factor;'),
 'z_add':('state->z *= *factor;','state->z += *factor;'),
 'factor_alias':('f32 *factor = &state->damping;','f32 *factor = &state->x;'),
 'tick_even':('ticks = (u32)D_800BE9E4;','ticks = (u32)D_800BE9E4 & ~1U;'),
 'copy_z':('state->x *= *factor;','state->x = state->z * *factor;'),
 'return_zero':('    return 1;','    return 0;'),
}
def main():
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad00[0x58];f32 x,pad5C,z;u8 pad64[0x44];f32 damping;} State;
 '''
 for target,owner,index in g.TARGETS:code+='typedef State DampingState'+target+';\n'
 code+='s32 D_800BE9E4;\nstruct Case {u32 tick,x,z,factor,expected_x,expected_z;};\nstatic const struct Case cases[]={\n'
 for c in g.cases():
  m,_,_=g.reference(c,g.fixture(c));code+='{'+','.join('0x%Xu'%v for v in (c.tick,c.x,c.z,c.factor,g.read(m,g.RECORD+0x58),g.read(m,g.RECORD+0x60)))+'},\n'
 code+=r'''};
 static f32 value(u32 v){union {u32 u;f32 f;}x;x.u=v;return x.f;}
 static u32 word(f32 v){union {u32 u;f32 f;}x;x.f=v;return x.u;}
 '''
 for target,owner,index in g.TARGETS:
  selected=body((out/('ptr_'+target+'_source.c')).read_text(),'func_'+target)
  for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
   if name!='selected':assert text!=selected,(target,name)
   code+='\n'+text.replace('func_'+target,'test_'+target+'_'+name,1)+'\n'
 code+=r'''
 typedef s32 (*T)(State *,s32);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case *c=&cases[n];State state;u8 *bytes=(u8*)&state;for(i=0;i<sizeof(state);i++)bytes[i]=0xa5;
  D_800BE9E4=(s32)c->tick;state.x=value(c->x);state.z=value(c->z);state.damping=value(c->factor);
  if(test(&state,0x12345678)!=1||word(state.x)!=c->expected_x||word(state.z)!=c->expected_z||word(state.damping)!=c->factor||(u32)D_800BE9E4!=c->tick)return 1;
  for(i=0;i<sizeof(state);i++)if((i<0x58||(i>=0x5c&&i<0x60)||(i>=0x64&&i<0xa8))&&bytes[i]!=0xa5)return 1;
  }return 0;}
 static int run(void){
 '''
 for target,owner,index in g.TARGETS:
  code+='if(check(test_'+target+'_selected))return 1;\n'
  for i,name in enumerate(controls):code+='if(!check(test_'+target+'_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-4000:],r.stderr[-4000:]);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases_per_target=len(list(g.cases())),targets=4,negative_controls_per_target=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='none',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report

if __name__=='__main__':main()
