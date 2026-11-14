"""Native32 finite/disjoint typed-object checks for the timed-motion C body."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-timed-motion-150f48d0-durable';source=(out/'formatted.c').read_text();start=source.index('typedef struct { f32 timer');end=source.index('\ns32 func_150F4A38',start);body=source[start:end]
HARNESS='''
f32 D_800BE9A4;static struct {f32 base[0x170/4];TimedMotion150F48D0 state;} actor;
static int mutation,calls,errors;static f32 observedPhase,observedScale;
void func_1514373C(f32 a,f32 b,f32 *x,f32 *z){calls++;observedPhase=a;observedScale=b;*x=2.0f;*z=-3.0f;
 if(mutation){D_800BE9A4=.75f;actor.state.rate=.5f;actor.base[0x44/4]=2.0f;}}
static int run(void){int cases=0;const f32 timers[]={0.,1.,12.},ticks[]={.5,2.};
 for(int t=0;t<3;t++)for(int d=0;d<2;d++)for(mutation=0;mutation<2;mutation++)for(int seed=0;seed<2;seed++){
  for(int i=0;i<0x170/4;i++)actor.base[i]=0.;
  actor.state.timer=timers[t];actor.state.x=3.;actor.state.y=-4.;actor.state.z=5.;actor.state.phase=1.;actor.state.rate=.25f;actor.state.width=4.;actor.state.depth=6.;actor.state.scale=2.;
  actor.base[0x20/4]=10.;actor.base[0x24/4]=11.;actor.base[0x28/4]=12.;actor.base[0x44/4]=.5f;actor.base[0x48/4]=1.;actor.base[0x4c/4]=1.5f;actor.base[0x50/4]=2.;actor.base[0x54/4]=2.5f;actor.base[0x58/4]=3.;
  D_800BE9A4=ticks[d];calls=errors=0;
  s32 got=func_150F48D0(actor.base);f32 left=timers[t]-ticks[d];
  if(actor.state.timer!=left)return 1;
  if(left<=0.){if(got||calls)return 2;}
  else{
   f32 step=mutation?.75f:ticks[d],vx=mutation?2.:.5f,rate=mutation?.5f:.25f;
   f32 x=3.+vx*step,y=-4.+step,z=5.+1.5f*step;
   if(got!=(s32)&actor.state||calls!=1||observedPhase!=1.||observedScale!=2.)return 3;
   if(actor.state.phase!=1.+rate*step||actor.state.x!=x||actor.state.y!=y||actor.state.z!=z)return 4;
   if(actor.base[0x38/4]!=x+8.||actor.base[0x3c/4]!=y-3.||actor.base[0x40/4]!=z-12.)return 5;
   if(actor.base[0x20/4]!=10.+2.*step||actor.base[0x24/4]!=11.+2.5f*step||actor.base[0x28/4]!=12.+3.*step)return 6;
  }
  cases++;
 }
 return cases==24?0:7;}
'''
controls={'wrong-timer':('state->timer -= D_800BE9A4;','state->timer += D_800BE9A4;'),'wrong-position':('state->x + a * state->width','state->x - a * state->width'),'wrong-velocity':('actor[0x50 / 4] * D_800BE9A4','actor[0x54 / 4] * D_800BE9A4')}
def run(label,code,opt,alias):
 src=out/(label+'.c');exe=out/(label+opt+'-'+alias);src.write_text('#include <ultra64.h>\n'+code+'\n'+HARNESS+START)
 p=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(src),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True,text=True).returncode
for opt in ('-O0','-O2','-O3'):
 for alias in ('strict','no-strict'):
  assert run('native-candidate',body,opt,alias)==0,(opt,alias)
  for label,(old,new) in controls.items():assert body.count(old)==1 and run('control-'+label,body.replace(old,new),opt,alias)!=0,(opt,alias,label)
report={'cases_per_configuration':24,'optimizations':3,'alias_modes':2,'controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
