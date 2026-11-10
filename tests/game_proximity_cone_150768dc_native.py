"""Canonical SDK32 actor search with complete retained-byte/helper snapshots."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_proximity_cone_150768dc_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_proximity_cone_150768dc_oracle as guest
from tools.experiments import game_proximity_cone_150768dc_match as qualify
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def mutations(p):
 rows={
 'skip-final-slot':p.replace('index < 25','index < 24'),
 'scan-extra-slot':p.replace('index < 25','index < 26'),
 'omit-active-gate':p.replace('(candidate->interaction_state != 0)','(1)'),
 'omit-health-gate':p.replace('(candidate->health != 0)','(1)'),
 'omit-flag-gate':p.replace('((candidate->unkF8 & 0x20) != 0)','(1)'),
 'include-self':p.replace('(index != own_index)','(1)'),
 'ignore-ID-exclusion':p.replace('(D_800D1891 != 0)','(1)'),
 'strict-height-cutoff':p.replace('> 50.0f','>= 50.0f'),
 'reject-NaN-height':p.replace('!(fabsf(D_800D154C->y_position - candidate->y_position) > 50.0f)','(fabsf(D_800D154C->y_position - candidate->y_position) <= 50.0f)'),
 'wrong-range-scale':p.replace('D_800D1890 * 8','D_800D1890 * 4'),
 'accept-equal-distance':p.replace('distance < closest','distance <= closest'),
 'omit-nearest-update':p.replace('closest = distance;','closest = closest;'),
 'wrong-direction-X':p.replace('candidate->x_position - D_800D154C->x_position','D_800D154C->x_position - candidate->x_position'),
 'wrong-cone-edge':p.replace('< cone_width','<= cone_width'),
 'late-cone-width':p.replace('< cone_width','< definition->unk17'),
 'wrong-selected-mark':p.replace('index + 0x80','index + 0x81'),
 'wrong-script-decrement':p.replace('unk218 -= 1','unk218 -= 0'),
 'wrong-owner-index':p.replace('unk222 = own_index','unk222 = own_index + 1'),
 }
 assert all(v!=p for v in rows.values());return rows
def cases():return guest.cases()
def vals(values):return'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in values)+'}'
def program(selected):
 rows=[]
 for c in cases():
  initial=guest.fixture(c);want,calls,obs=guest.reference(initial,c);actors=[]
  for i in range(26):
   a=guest.ARRAY+i*812;actors.append(vals([guest.read(initial,a),initial[a+4],initial[a+458],guest.read(initial,a+248),*[guest.read(initial,a+f)for f in(20,24,28)],guest.read(initial,a+118,2),initial[a+714],guest.read(initial,a+536)]))
  cs=[]
  for(t,args),snapshot in zip(calls,obs):
   kind=[guest.SYMS[n]for n in guest.CALL_NAMES].index(t);args=(*args,0)if len(args)==2 else args;cs.append(vals([kind,*args,snapshot]))
  rows.append('{'+vals([c.command,c.cross,c.script,c.lookup,c.own,c.effects,c.distance,c.angle,c.width,c.candidates[0]if c.candidates else 0])+',{'+','.join(actors)+'},0x%Xu,%d,{'%(guest.digest(want),len(calls))+','.join(cs)+'}}')
 source='#include <ultra64.h>\n#include "structs.h"\n#include "functions.h"\n#include "variables.h"\nstruct216 *func_1507BB28(s32,u8);\nstruct127 D_800CC2D0[26];struct127*D_800D154C;struct124*D_800D1C90[187];u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;\n'
 for name,p in {'candidate':selected,**mutations(selected)}.items():source+=p.replace('func_150768DC(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(struct127)==812,"actor stride");_Static_assert(sizeof(struct216)==5,"script packet");
_Static_assert(__builtin_offsetof(struct127,unkA8)==168,"selection");_Static_assert(__builtin_offsetof(struct127,unk218)==536,"script");_Static_assert(__builtin_offsetof(struct127,unk2CA)==714,"signed angle offset");_Static_assert(__builtin_offsetof(struct124,unk17)==23,"cone width");
struct Case{u32 w[10],actor[26][10],expected,callcount,call[49][5];};static const struct Case cases[]={ROWS};static const struct Case*c;
static struct124 defs[187];static u8 scripts[1024];static int calls,error,last;static u32 hash;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
f32 fabsf(f32 f){return real(bits(f)&0x7FFFFFFFu);}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void be(u8*p,u32 v,int n){int i;for(i=0;i<n;i++)p[i]=(u8)(v>>((n-i-1)*8));}
static void feed(u8*p,int n){int i;for(i=0;i<n;i++)hash=(hash^p[i])*16777619u;}
static u32 actorId(struct127*a){return 0x800CC2D0u+(u32)(a-D_800CC2D0)*812u;}
static u32 scriptId(struct216*p){return p?0x90000u+(u32)((u8*)p-scripts):0;}
static void actorHash(struct127*a){u8 b[812];int i;for(i=0;i<812;i++)b[i]=((u8*)a)[i];be(b,(u32)a->interaction_state,4);be(b+20,bits(a->x_position),4);be(b+24,bits(a->y_position),4);be(b+28,bits(a->z_position),4);be(b+118,a->unk76,2);be(b+248,a->unkF8,4);be(b+536,scriptId(a->unk218),4);feed(b,812);}
static u32 digest(void){u8 b[4];int i;hash=2166136261u;for(i=0;i<26;i++)actorHash(&D_800CC2D0[i]);for(i=0;i<187;i++)feed((u8*)&defs[i],32);
 for(i=0;i<187;i++){if(D_800D1C90[i]!=&defs[i])error=1;be(b,0x60000u+(u32)i*32u,4);feed(b,4);}feed(scripts,1024);be(b,actorId(D_800D154C),4);feed(b,4);b[0]=D_800D1890;b[1]=D_800D1891;b[2]=D_800D1892;b[3]=D_800D1893;feed(b,4);return hash;}
static void effect(int kind,int index){u32 e=c->w[5];struct127*other=&D_800CC2D0[(c->w[4]+1)%26];struct127*a;
 if(e&1){other->unkA8=0x81;D_800D154C=other;}if(e&2){D_800D1891=1;D_800D1892=9;D_800D1893=0x31;}
 if(e&4){a=D_800D154C;a->unk76=0xFE00;a->unk2CA=(s8)0x81;a->id=2;defs[2].unk17=kind==1?251:3;}
 if(e&8){a=D_800D154C;a->unkA8=kind==2?0x99:0x81;if(index>=0){D_800CC2D0[index].x_position=999.;D_800CC2D0[index].z_position=-777.;}}}
static void mock(int kind,u32 a,u32 b,u32 d){const u32*r;if(calls>=49){error=2;return;}r=c->call[calls++];if(r[0]!=(u32)kind||!same(a,r[1])||!same(b,r[2])||(kind==1&&d!=r[3]))error=3;if(digest()!=r[4])error=4;effect(kind,kind==2?-1:last);}
f32 func_1505A72C(struct127*a,struct127*b){last=(int)(b-D_800CC2D0);mock(0,actorId(a),actorId(b),0);return last==(int)c->w[9]?real(c->w[6]):real(c->w[6])-(f32)(last&3);}
u16 func_1505A630(f32 a,f32 b,s32 d){mock(1,bits(a),bits(b),(u32)d);return(u16)c->w[7];}
struct216*func_1507BB28(s32 a,u8 b){mock(2,(u32)a,b,0);return(struct216*)(scripts+40);}
typedef void(*Subject)(void);
static int check(Subject fn){u32 k;int i,j;struct127*a;const u32*r;u8*p;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=&cases[k];for(i=0;i<26;i++){a=&D_800CC2D0[i];p=(u8*)a;r=c->actor[i];for(j=0;j<812;j++)p[j]=(u8)((j+i*812)*29+0x59);a->interaction_state=(s32)r[0];a->id=(u8)r[1];a->health=(u8)r[2];a->unkF8=r[3];a->x_position=real(r[4]);a->y_position=real(r[5]);a->z_position=real(r[6]);a->unk76=(u16)r[7];a->unk2CA=(s8)r[8];a->unk218=(struct216*)(scripts+r[9]-0x90000u);a->unkA8=0xE1;a->unk222=0xA9;a->unk232=0xC3;}
  for(i=0;i<187;i++){p=(u8*)&defs[i];for(j=0;j<32;j++)p[j]=(u8)((i*32+j)*29+0x59);defs[i].unk17=(u8)c->w[8];D_800D1C90[i]=&defs[i];}for(i=0;i<1024;i++)scripts[i]=(u8)(i*29+0x59);
  D_800D154C=&D_800CC2D0[c->w[4]];D_800D1890=(u8)c->w[0];D_800D1891=(u8)c->w[1];D_800D1892=(u8)c->w[2];D_800D1893=(u8)c->w[3];calls=error=0;last=-1;fn();if(error||calls!=(int)c->callcount||digest()!=c->expected)return 1;
 }return 0;}
static int run(void){if((u32)D_800CC2D0>0x7FFFFFFFu)return 99;if(check(candidate))return 1;
'''.replace('ROWS',',\n'.join(rows))
 for i,name in enumerate(mutations(selected)):source+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 return source+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def main():
 selected=body((out/'final-owner.c').read_text(),qualify.FUNCTION);p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=len(mutations(selected)))
 report=dict(profiles=profiles,SDK32_layout=True,script_packet_bytes=5,all_retained_actor_definition_and_script_bytes=True,helper_boundary_snapshots=True,void_no_arguments=True,physical_aliases_guest_only=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
