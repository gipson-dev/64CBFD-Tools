"""SDK32 motion approach with full actor-byte preservation and effective controls."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_motion_approach_1505a3a8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_motion_approach_1505a3a8_oracle as guest
from tools.experiments import game_motion_approach_1505a3a8_match as qualify
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def mutations(p):
 rows={
 'omit-acceleration-time':p.replace('acceleration *= D_800D1550[0];','acceleration *= 1.0f;'),
 'omit-deceleration-time':p.replace('deceleration *= D_800D1550[0];','deceleration *= 1.0f;'),
 'omit-global-gate':p.replace('D_800CC27C != 0','D_800CC27C == 0'),
 'wrong-gate-edge':p.replace('actor->unk28 < 5.0f','actor->unk28 <= 5.0f'),
 'wrong-state-30-exception':p.replace('interaction_state != 30','interaction_state != 31'),
 'wrong-player-state':p.replace('interaction_state == 1','interaction_state == 2'),
 'wrong-water-acceleration':p.replace('acceleration = 2.0f','acceleration = 3.0f'),
 'omit-water-friction':p.replace('deceleration *= D_800994C0','deceleration *= 1.0f'),
 'wrong-slow-friction':p.replace('deceleration *= 0.25f','deceleration *= 0.5f'),
 'wrong-flag-40':p.replace('unk81 & 0x40','unk81 & 0x80'),
 'wrong-flag-20':p.replace('unk81 & 0x20','unk81 & 0x10'),
 'wrong-fixed-friction':p.replace('deceleration = D_800994C4','deceleration = D_800994C4 + 1.0f'),
 'omit-flag-friction':p.replace('deceleration *= D_800994C8','deceleration *= 1.0f'),
 'wrong-magnitude-46':p.replace('magnitude >= 46','magnitude > 46'),
 'wrong-magnitude-91':p.replace('magnitude >= 91','magnitude > 91'),
 'omit-extra-friction':p.replace('deceleration *= D_800994CC','deceleration *= 1.0f'),
 'wrong-target-sign-edge':p.replace('target_speed < 0.0f','target_speed <= 0.0f'),
 'wrong-positive-reversal':p.replace('deceleration += acceleration','deceleration -= acceleration'),
 'wrong-negative-reversal':p.replace('acceleration += deceleration','acceleration -= deceleration'),
 'wrong-braking-direction':p.replace('actor->xz_velocity - deceleration','actor->xz_velocity + deceleration'),
 'wrong-acceleration-direction':p.replace('actor->xz_velocity + acceleration','actor->xz_velocity - acceleration'),
 'wrong-near-target-width':p.replace('target_speed - 1.0f','target_speed - 0.5f'),
 'omit-near-target-scale':p.replace('acceleration *= D_800994D0','acceleration *= 1.0f'),
 'omit-target-clamps':p.replace('actor->xz_velocity = target_speed','actor->xz_velocity = target_speed + 1.0f'),
 }
 assert all(v!=p for v in rows.values());return rows
def cases():return[c for c in guest.cases()if not c.alias]
def array(xs):return'{'+','.join('0x%Xu'%(n&0xFFFFFFFF)for n in xs)+'}'
def program(selected):
 rows=[]
 for c in cases():
  expected=guest.reference(guest.fixture(c),c);xs=[c.state,c.gate,c.field28,c.water,c.slow,c.flags,c.extra,c.speed,c.target,c.acceleration,c.deceleration,c.magnitude,*c.globals,guest.read(expected,guest.ACTOR+60)]
  rows.append(array(xs))
 source='#include <ultra64.h>\n#include "structs.h"\n#include "variables.h"\nf32 D_800D1550[1],D_800994C0,D_800994C4,D_800994C8,D_800994CC,D_800994D0;u8 D_800CC27C;\n'
 for name,p in {'candidate':selected,**mutations(selected)}.items():source+=p.replace('func_1505A3A8(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(struct127)==812,"actor");_Static_assert(__builtin_offsetof(struct127,xz_velocity)==60,"speed");_Static_assert(__builtin_offsetof(struct127,in_water)==173,"water");
static const u32 cases[][19]={ROWS};
static struct127 actor;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
typedef void(*Subject)(f32,void*,f32,f32,u8);
static int check(Subject fn){u32 k;int i;u8 before[812],*p=(u8*)&actor;const u32*c;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=cases[k];for(i=0;i<812;i++)p[i]=(u8)(i*29+89);
  actor.interaction_state=(s32)c[0];D_800CC27C=(u8)c[1];actor.unk28=real(c[2]);actor.in_water=(u8)c[3];actor.unkA8=(u8)c[4];actor.unk81=(u8)c[5];actor.unkAE=(u8)c[6];actor.xz_velocity=real(c[7]);
  D_800D1550[0]=real(c[12]);D_800994C0=real(c[13]);D_800994C4=real(c[14]);D_800994C8=real(c[15]);D_800994CC=real(c[16]);D_800994D0=real(c[17]);
  for(i=0;i<812;i++)before[i]=p[i];
  fn(real(c[8]),&actor,real(c[9]),real(c[10]),(u8)c[11]);
  if(!same(bits(actor.xz_velocity),c[18]))return 1;
  for(i=0;i<812;i++)if((i<60||i>=64)&&p[i]!=before[i])return 2;
  if(D_800CC27C!=(u8)c[1]||bits(D_800D1550[0])!=c[12]||bits(D_800994C0)!=c[13]||bits(D_800994C4)!=c[14]||bits(D_800994C8)!=c[15]||bits(D_800994CC)!=c[16]||bits(D_800994D0)!=c[17])return 3;
 }return 0;}
static int run(void){if(check(candidate))return 1;
'''.replace('ROWS',',\n'.join(rows))
 for i,name in enumerate(mutations(selected)):source+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 return source+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def main():
 selected=body((out/'final-owner.c').read_text(),qualify.FUNCTION);p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=len(mutations(selected)))
 report=dict(profiles=profiles,SDK32_layout=True,all_actor_and_global_bytes=True,physical_aliases_guest_only=True,void_mixed_float_and_fifth_byte_ABI=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
