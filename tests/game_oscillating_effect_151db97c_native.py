"""Native SDK32 checks for the private oscillating-effect candidate."""
import json,subprocess
from tools.tests import game_oscillating_effect_151db97c_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(g.out/'independent-selected.c').read_text();selected=body(source,'func_151DB97C')
 start=source.index('typedef struct {\n    u8 flags, retained01[3];');end=source.index('void func_15131918(f32 *, f32);',start);types=source[start:end]
 controls={
  'damping_flag':('params->flags & 2','params->flags & 4'),
  'oscillation_flag':('params->flags & 1','params->flags & 4'),
  'x_speed':('params->speedX *','params->speedY *'),
  'y_speed':('params->speedY *','params->speedZ *'),
  'z_speed':('params->speedZ *','params->speedX *'),
  'x_angle':('params->phaseX - 64','params->phaseX - 63'),
  'y_angle':('params->phaseY - 64','params->phaseY - 63'),
  'z_angle':('params->phaseZ - 64','params->phaseZ - 63'),
  'x_amplitude':('params->amplitudeX * x','params->amplitudeX * (x + y)'),
  'return_value':('return 1;','return 0;'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef union {f32 f;u32 u;} Float;
 static u32 raw(f32 f){Float x;x.f=f;return x.u;}
 '''+types+r'''
 _Static_assert(__builtin_offsetof(OscillatingEffect2062D0,oscillation)==0xA8 && __builtin_offsetof(OscillatingEffect2062D0,transform)==0x58 && __builtin_offsetof(OscillationParams2062D0,amplitudeX)==0x10,"offsets");
 s32 D_800BE9E4;
 struct Event {u32 kind,arg;};
 struct Case {u32 flags,mutation,tick,seed,expectedFlags,expectedTick,phase[3],amplitude[3],offset[3],count;struct Event events[4];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,calls,_=g.reference(c,g.fixture(c));events=[(1 if k==g.DAMP else 2,args[-1])for k,args in calls];events+= [(0,0)]*(4-len(events))
  values=(c.flags,c.mutation,c.tick,c.seed,m[g.RECORD+0xa8],g.read(m,g.TICK))
  phases=[m[g.RECORD+0xb0+i]for i in range(3)];amps=[g.read(m,g.RECORD+0xb8+4*i)for i in range(3)];offsets=[g.read(m,g.RECORD+0x4c+4*i)for i in range(3)]
  code+='{'+','.join('0x%Xu'%v for v in values)+',{'+','.join('0x%Xu'%v for v in phases)+'},{'+','.join('0x%Xu'%v for v in amps)+'},{'+','.join('0x%Xu'%v for v in offsets)+'},'+str(len(calls))+',{'+','.join('{%d,0x%Xu}'%v for v in events)+'}},\n'
 code+=r'''};
 static const struct Case *current;static OscillatingEffect2062D0 *active;static u32 count,bad,sines;
 void func_15131918(f32 *p,f32 damping){OscillationParams2062D0 *q=&active->oscillation;
  if(count>=current->count||current->events[count].kind!=1||current->events[count].arg!=raw(damping)||p!=active->transform)bad=1;count++;
  if(current->mutation&1)q->flags^=1;
  if(current->mutation&2){D_800BE9E4=(s32)((u32)D_800BE9E4^0x80000001u);q->phaseY^=0x80;q->amplitudeX=-2.5f;}
 }
 f32 func_151423D8(u8 arg){OscillationParams2062D0 *q=&active->oscillation;u32 index=sines++;
  if(count>=current->count||current->events[count].kind!=2||current->events[count].arg!=arg)bad=1;count++;
  if(current->mutation&4){if(index%2==0)q->phaseY^=0x40;else q->phaseZ^=0x40;if(index==2)q->amplitudeY=3.5f;}
  return (f32)((s32)(arg&3)-2)*.25f;
 }
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace('func_151DB97C','test_'+name,1)+'\n'
 code+=r'''
 typedef s32(*Test)(OscillatingEffect2062D0 *,s32);
 static int check(Test test){u32 i,j;union {OscillatingEffect2062D0 effect;u8 bytes[0xc8];} record;u8 before[0xc8];
  for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){const struct Case *c=&cases[i];OscillationParams2062D0 *q=&record.effect.oscillation;s32 answer;
   for(j=0;j<sizeof(record.bytes);j++)record.bytes[j]=(u8)(j*19+c->seed*11+37);
   q->flags=(u8)c->flags;q->damping=.75f;q->phaseX=(u8)c->seed;q->phaseY=(u8)(127+c->seed);q->phaseZ=(u8)(255+c->seed);
   q->speedX=(u8)(1+c->seed);q->speedY=(u8)(2+c->seed);q->speedZ=(u8)(255+c->seed);
   q->amplitudeX=1.5f;q->amplitudeY=-2.25f;q->amplitudeZ=.25f;record.effect.offsetX=7.;record.effect.offsetY=-9.;record.effect.offsetZ=12.;D_800BE9E4=(s32)c->tick;
   for(j=0;j<sizeof(record.bytes);j++)before[j]=record.bytes[j];
   current=c;active=&record.effect;count=bad=sines=0;answer=test(active,(s32)0x89abcdefu);
   if(bad||count!=c->count||answer!=1||q->flags!=c->expectedFlags||(u32)D_800BE9E4!=c->expectedTick||q->phaseX!=c->phase[0]||q->phaseY!=c->phase[1]||q->phaseZ!=c->phase[2]||raw(q->amplitudeX)!=c->amplitude[0]||raw(q->amplitudeY)!=c->amplitude[1]||raw(q->amplitudeZ)!=c->amplitude[2]||raw(record.effect.offsetX)!=c->offset[0]||raw(record.effect.offsetY)!=c->offset[1]||raw(record.effect.offsetZ)!=c->offset[2])return 1;
   for(j=0;j<sizeof(record.bytes);j++)if(!(j>=0x4c&&j<0x58)&&j!=0xa8&&!(j>=0xb0&&j<0xb3)&&!(j>=0xb8&&j<0xc0)&&before[j]!=record.bytes[j])return 2;
  }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=g.out/'native_151DB97C_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=g.out/('native_151DB97C_screen'+opt);p=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=g.root,capture_output=True,text=True)
  assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout[-3000:],p.stderr[-3000:])
  p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
  profiles[opt]=dict(cases=len(list(g.cases())),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled with mutations',valid_disjoint_record_only=True,source_installed=False)
 (g.out/'native_151DB97C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
