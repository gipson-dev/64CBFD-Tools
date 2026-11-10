"""SDK32 water/stun contract, float lanes and all modeled actor/child/global bytes."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_water_stun_150585f0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_water_stun_150585f0_oracle as guest
from tools.experiments import game_water_stun_150585f0_match as qualify
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def mutations(p):
 rows={
 'wrong-motion-first-float':p.replace('func_1505A3A8(0.0f,','func_1505A3A8(motion_scale,'),
 'wrong-motion-scale':p.replace('motion_scale, 0);','motion_scale + 1.0f, 0);'),
 'wrong-motion-fifth-argument':p.replace('motion_scale, 0);','motion_scale, 1);'),
 'strict-velocity-edge':p.replace('y_velocity < 60.0f','y_velocity <= 60.0f'),
 'wrong-water-range':p.replace('in_water < 0xA','in_water <= 0xA'),
 'wrong-water-escape-edge':p.replace('+ 40.0f) < arg0->y_position','+ 40.0f) <= arg0->y_position'),
 'omit-health-exclusion':p.replace('(arg0->health != 0) || (1 != arg0->interaction_state)','(1)'),
 'decrement-FE-sentinel':p.replace('arg0->stunned != 0xFE','arg0->stunned != 0xFD'),
 'advance-FF-sentinel':p.replace('arg0->stunned != 0xFF','arg0->stunned != 0xFD'),
 'unsigned-timer-test':p.replace('(s32) arg0->unk10C <= 0','(u16)arg0->unk10C == 0'),
 'wrong-timer-direction':p.replace('unk10C -= D_800CC264','unk10C += D_800CC264'),
 'wrong-timer-flag':p.replace('unkF4 & 0x100','unkF4 & 0x200'),
 'omit-child-clear':p.replace('arg0->unk31C->matrix_physics = (u8)0','arg0->unk31C->matrix_physics = (u8)1'),
 'wrong-resource':p.replace('func_1505E874(D_800C3E78,','func_1505E874(0,'),
 'wrong-recovered-heading':p.replace('arg0->unk78 = arg0->unk7A','arg0->unk78 = arg0->unk7A + 1'),
 'wrong-recovery-mask':p.replace('0xFFFF7FFF','0xFFFFBFFF'),
 'wrong-carried-byte':p.replace('unk23A = arg0->unk238','unk23A = arg0->unk238 + 1'),
 'wrong-render-heading':p.replace('recovery_heading ^= 0x8000','recovery_heading ^= 0x4000'),
 'wrong-render-command':p.replace('func_150599C8(arg0, 12,','func_150599C8(arg0, 13,'),
 }
 assert all(v!=p for v in rows.values());return rows
def cases():return[c for c in guest.cases()if not c.alias]
def vals(values):return'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in values)+'}'
def program(selected):
 rows=[]
 for c in cases():
  initial=guest.fixture(c);want,calls,obs=guest.reference(initial,c);inputs=[c.state,c.water,c.stun,c.health,c.timer,c.delta,c.scale_byte,c.y,c.level,c.yvel,c.speed,c.xzvel,c.history,c.flags,c.recovery_flags,c.heading,c.saved,c.carry,c.child,c.gate,c.resource,c.effects,c.unused_argument];assert len(inputs)==23;cs=[]
  for(t,args),snapshot in zip(calls,obs):
   kind=[guest.SYMS[n]for n in guest.CALL_NAMES].index(t);cs.append(vals([kind,*args,*([0]*(5-len(args))),snapshot]))
  rows.append('{'+vals(inputs)+',0x%Xu,%d,{'%(guest.digest(want),len(calls))+','.join(cs)+'}}')
 source='#include <ultra64.h>\n#include "structs.h"\n#include "functions.h"\n#include "variables.h"\nf32 func_1505A3A8(f32,void*,f32,f32,u8);u8 func_150599C8(struct127*,u8,u16);\nf32 D_80099478,D_8009947C,D_80099480,D_80099484;s16 D_800CC264;u8 D_800BE616,D_800C3E78;\n'
 for name,p in {'candidate':selected,**mutations(selected)}.items():source+=p.replace('func_150585F0(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(struct127)==812,"actor");_Static_assert(sizeof(struct126)<=512,"child");_Static_assert(__builtin_offsetof(struct126,matrix_physics)==125,"child byte");_Static_assert(__builtin_offsetof(struct127,unk10C)==268,"signed timer");_Static_assert(__builtin_offsetof(struct127,unk31C)==796,"child pointer");
struct Case{u32 w[23],expected,callcount,call[4][7];};static const struct Case cases[]={ROWS};static const struct Case*c;
static struct127 actor;static union Child{struct126 typed;u8 bytes[512];}children[2];static int calls,error;static u32 hash;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void be(u8*p,u32 v,int n){int i;for(i=0;i<n;i++)p[i]=(u8)(v>>((n-i-1)*8));}
static void feed(u8*p,int n){int i;for(i=0;i<n;i++)hash=(hash^p[i])*16777619u;}
static u32 childId(struct126*p){if(!p)return 0;if(p==&children[0].typed)return 0x50000;if(p==&children[1].typed)return 0x51000;error=1;return 0;}
static u32 digest(void){u8 b[812],v[4];int i;for(i=0;i<812;i++)b[i]=((u8*)&actor)[i];be(b,(u32)actor.interaction_state,4);be(b+24,bits(actor.y_position),4);be(b+32,bits(actor.y_velocity),4);be(b+36,bits(actor.gravity),4);be(b+40,bits(actor.unk28),4);be(b+60,bits(actor.xz_velocity),4);be(b+184,bits(actor.unkB8),4);be(b+280,bits(actor.unk118),4);be(b+460,bits(actor.unk1CC),4);be(b+244,actor.unkF4,4);be(b+248,actor.unkF8,4);be(b+118,actor.unk76,2);be(b+120,actor.unk78,2);be(b+122,actor.unk7A,2);be(b+268,(u16)actor.unk10C,2);be(b+540,actor.unk21C,2);be(b+796,childId(actor.unk31C),4);
 hash=2166136261u;feed(b,812);for(i=0;i<2;i++)feed(children[i].bytes,512);be(v,bits(D_80099478),4);feed(v,4);be(v,bits(D_8009947C),4);feed(v,4);be(v,bits(D_80099480),4);feed(v,4);be(v,bits(D_80099484),4);feed(v,4);be(v,(u16)D_800CC264,2);feed(v,2);v[0]=D_800BE616;feed(v,1);v[0]=D_800C3E78;feed(v,1);return hash;}
static void effect(int kind){u32 e=c->w[21];if(e&1){actor.in_water=1;actor.stunned=kind?0:1;actor.health=1;actor.interaction_state=1;}
 if(e&2){D_80099478=-2.;D_8009947C=500.;D_80099480=.5;D_80099484=100.;D_800CC264=-1;D_800BE616=0;D_800C3E78=0x31;}
 if(e&4){actor.unk10C=-3;actor.unk31C=&children[1].typed;actor.stunned=kind?0:0xFE;}
 if(e&8){actor.y_position=70.;actor.y_velocity=-5.;actor.unk7A=0xCDEF;actor.unk10B=4;actor.unk238=kind==2?9:7;}}
static void mock(int kind,u32 a,u32 b,u32 d,u32 e,u32 f){const u32*r;if(calls>=4){error=2;return;}r=c->call[calls++];if(r[0]!=(u32)kind||!same(a,r[1])||!same(b,r[2])||!same(d,r[3])||!same(e,r[4])||!same(f,r[5]))error=3;if(digest()!=r[6])error=4;effect(kind);}
f32 func_1505A3A8(f32 a,void*b,f32 d,f32 e,u8 f){if(b!=&actor)error=5;mock(0,bits(a),0x20000,bits(d),bits(e),f);return real(0x7FC12345u);}
void func_1505E874(u8 a,struct127*b){if(b!=&actor)error=5;mock(1,a,0x20000,0,0,0);}void func_1506B078(void){mock(2,0,0,0,0,0);}
u8 func_150599C8(struct127*a,u8 b,u16 d){if(a!=&actor)error=5;mock(3,0x20000,b,d,0,0);return 0xA5;}
typedef void(*Subject)(struct127*,f32);
static int check(Subject fn){u32 k;int i,j;u8*p;for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=&cases[k];p=(u8*)&actor;for(i=0;i<812;i++)p[i]=(u8)(i*29+0x59);for(i=0;i<2;i++)for(j=0;j<512;j++)children[i].bytes[j]=(u8)(j*29+0x59);
 actor.interaction_state=(s32)c->w[0];actor.in_water=(u8)c->w[1];actor.stunned=(u8)c->w[2];actor.health=(u8)c->w[3];actor.unk10C=(s16)c->w[4];D_800CC264=(s16)c->w[5];actor.unk109=(u8)c->w[6];actor.y_position=real(c->w[7]);actor.unk118=real(c->w[8]);actor.y_velocity=real(c->w[9]);actor.unk28=real(c->w[10]);actor.xz_velocity=real(c->w[11]);actor.unk1CC=real(c->w[12]);actor.unkF4=c->w[13];actor.unk10B=(u8)c->w[14];actor.unk76=(u16)c->w[15];actor.unk78=0x1324;actor.unk7A=(u16)c->w[16];actor.unk238=(u8)c->w[17];actor.unk23A=0xA7;actor.unk31C=c->w[18]?&children[c->w[18]-1].typed:0;D_800BE616=(u8)c->w[19];D_800C3E78=(u8)c->w[20];actor.gravity=3.;actor.unkB8=7.;actor.unk21C=0x8142;actor.unk80=0x71;actor.unk81=0x83;actor.unk83=0x95;
 actor.unkF8=0xA5A5FFFFu;GLOBALS
 calls=error=0;fn(&actor,real(c->w[22]));if(error||calls!=(int)c->callcount||digest()!=c->expected)return 1;}return 0;}
static int run(void){if(check(candidate))return 1;
'''.replace('ROWS',',\n'.join(rows)).replace('GLOBALS',''.join(n+'=real(0x%Xu);'%v for n,v in guest.DEFAULTS.items()))
 for i,name in enumerate(mutations(selected)):source+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 return source+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def main():
 selected=body((out/'final-owner.c').read_text(),qualify.FUNCTION);p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=len(mutations(selected)))
 report=dict(profiles=profiles,SDK32_layout=True,all_retained_actor_child_and_global_bytes=True,mixed_float_and_stack_contract=True,helper_boundary_snapshots=True,physical_aliases_guest_only=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
