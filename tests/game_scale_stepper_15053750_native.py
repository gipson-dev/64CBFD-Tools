"""Private finite SDK32 scale-stepper screen with independent negative controls."""
import json,subprocess
from tools.experiments import game_scale_stepper_15053750_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=p.body((p.out/'selected-source.c').read_text(),p.NAME)
 controls={'x_difference':('actor->unk154 - actor->xz_scale','actor->xz_scale - actor->unk154'),
           'y_difference':('actor->unk158 - actor->y_scale','actor->y_scale - actor->unk158'),
           'x_threshold':('fabsf(difference) < actor->unk15C','fabsf(difference) < 0.0f'),
           'x_snap':('actor->unk154, actor->y_scale','actor->unk158, actor->y_scale'),
           'y_snap':('actor->xz_scale, actor->unk158','actor->xz_scale, actor->unk154'),
           'x_step':('(f32)direction * actor->unk15C + actor->xz_scale','(f32)direction * actor->unk15C - actor->xz_scale'),
           'y_step':('(f32)direction * actor->unk15C + actor->y_scale','(f32)direction * actor->unk15C - actor->y_scale'),
           'x_gate':('if (difference != 0.0f)', 'if (difference == 0.0f)')}
 code='''#include <ultra64.h>\n'''+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad[0x14c];f32 xz_scale,y_scale,unk154,unk158,unk15C;} struct127;
 typedef struct {f32 x,y,tx,ty,step;} Sample;
 typedef union {f32 f;u32 u;} Bits;
 static struct127 actual,expected;static int mutation,calls,expected_calls,bad;static u32 events[2][2],expected_events[2][2];
 f32 fabsf(f32 x){Bits v;v.f=x;v.u&=0x7fffffffu;return v.f;}
 static u32 raw(f32 x){Bits v;v.f=x;return v.u;}
 void func_15062BDC(struct127 *actor,f32 x,f32 y){
  if(actor!=&actual || calls>=2){bad=1;return;}
  events[calls][0]=raw(x);events[calls][1]=raw(y);actor->xz_scale=x;actor->y_scale=y;
  if(mutation && calls==0){actor->unk158=-2.0f;actor->unk15C=0.5f;}calls++;
 }
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+=r'''
 static void reference(void){int axis;f32 current,target,delta,step,next,sign,x,y;
  for(axis=0;axis<2;axis++){
   current=axis?expected.y_scale:expected.xz_scale;target=axis?expected.unk158:expected.unk154;
   delta=target-current;if(delta==0.0f)continue;step=expected.unk15C;
   if(fabsf(delta)<step)next=target;else{sign=delta<0.0f?-1.0f:1.0f;next=sign*step+current;}
   x=axis?expected.xz_scale:next;y=axis?next:expected.y_scale;
   expected_events[expected_calls][0]=raw(x);expected_events[expected_calls][1]=raw(y);
   expected.xz_scale=x;expected.y_scale=y;
   if(mutation && expected_calls==0){expected.unk158=-2.0f;expected.unk15C=0.5f;}expected_calls++;
  }
 }
 typedef void(*Test)(struct127*);
 static const Sample samples[]={
  {0,0,0,0,1},{0,0,.5f,.5f,1},{0,0,2,-2,1},{1,1,-2,2,.5f},
  {0,0,1,-1,1},{2,-1,2,1,.5f},{1,1,-1,1,2},{0,1,0,-1,0},
  {2,1,3,5,1},{2,1,-1,-2,.5f},{-2,-1,-2,1,.5f},{2,1,2,1.5f,1},{2,1,2.5f,1,1},{0,0,2,-2,-1}
 };
 static int check(Test fn){u32 i,j;for(i=0;i<sizeof(samples)/sizeof(samples[0]);i++)for(mutation=0;mutation<2;mutation++){
  const Sample *s=&samples[i];calls=expected_calls=bad=0;
  actual.xz_scale=expected.xz_scale=s->x;actual.y_scale=expected.y_scale=s->y;
  actual.unk154=expected.unk154=s->tx;actual.unk158=expected.unk158=s->ty;actual.unk15C=expected.unk15C=s->step;
  reference();fn(&actual);if(bad||calls!=expected_calls)return 1;
  for(j=0;j<(u32)calls;j++)if(events[j][0]!=expected_events[j][0]||events[j][1]!=expected_events[j][1])return 1;
  if(raw(actual.xz_scale)!=raw(expected.xz_scale)||raw(actual.y_scale)!=raw(expected.y_scale)||raw(actual.unk154)!=raw(expected.unk154)||raw(actual.unk158)!=raw(expected.unk158)||raw(actual.unk15C)!=raw(expected.unk15C))return 1;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=p.out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=p.out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True)
  assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr)
  reports[opt]=dict(cases=28,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,finite_values_only=True,helper_modeled=True,source_installed=False,byte_exact=False)
 (p.out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
