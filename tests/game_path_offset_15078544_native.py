"""SDK32 signed packed offsets, float ABI, typed narrowing and retained path storage."""
import json,math,subprocess,sys
from pathlib import Path
from tools.experiments.game_path_offset_15078544_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_path_offset_15078544_oracle as guest
from tools.experiments import game_path_offset_15078544_match as qualify
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def mutations(p):
 rows={
 'unsigned-X':p.replace('(s32)(s8)D_800D1891','(s32)(u8)D_800D1891'),
 'unsigned-Z':p.replace('(s32)(s8)D_800D1892','(s32)(u8)D_800D1892'),
 'wrong-packed-Z':p.replace('(D_800D1893 & 0xF)','(D_800D1893 >> 4)'),
 'missing-command-mask':p.replace('original_cmd & 0x3F','original_cmd'),
 'wrong-target':p.replace('D_800CC2D0[D_800D154C->unk222]','D_800CC2D0[0]'),
 'wrong-angle-helper':p.replace('func_15048A40(angle_byte)','func_150489B0(angle_byte)'),
 'wrong-angle-offset':p.replace('>> 8) - 0x40','>> 8) - 0x20'),
 'wrong-mode1-sine':p.replace('sin_angle = 0.0f','sin_angle = 1.0f'),
 'reversed-facing-delta':p.replace('D_800D154C->x_position - target_x, D_800D154C->z_position - target_z','D_800D154C->z_position - target_z, D_800D154C->x_position - target_x'),
 'wrong-Z-sign':p.replace('(offset_z * cos_angle) - (offset_x * sin_angle)','(offset_z * cos_angle) + (offset_x * sin_angle)'),
 'missing-X-origin':p.replace('target_x +=','target_x ='),
 'wrong-node-slot':p.replace('D_800D1890 + 1','D_800D1890 + 0'),
 'wrong-Y-field':p.replace('].pad2 =','].pad6 ='),
 'stale-path-actor':p.replace('[D_800D154C->unk13F]','[target->unk13F]'),
 }
 assert all(v!=p for v in rows.values());return rows

def cases():return[c for c in guest.cases()if not c.alias and all(math.isfinite(guest.floating(v))and abs(guest.floating(v))<1e8 for v in c.target)]

def digest(m):
 data=bytearray()
 for base,n in((guest.ACTOR,812),(guest.ALT_ACTOR,812),(guest.SYMS['D_800CC2D0'],812*26),(guest.TABLE,1024),(guest.ALT_TABLE,1024),*((p,2080)for p in guest.ROWS)):
  data.extend(m[base+i]for i in range(n))
 for name,n in(('D_800D154C',4),('D_800D1890',4),('D_800D2104',4)):data.extend(m[guest.SYMS[name]+i]for i in range(n))
 h=2166136261
 for b in data:h=((h^b)*16777619)&0xFFFFFFFF
 return h

def program(selected):
 rows=[]
 for c in cases():
  want,calls,obs,writes=guest.reference(guest.fixture(c),c);args=[];kinds=[]
  for t,a in calls:args.extend((*a,0)if len(a)==1 else a);kinds.append([guest.SYMS[n]for n in guest.CALL_NAMES].index(t))
  args+=[0]*(6-len(args));kinds+=[0]*(3-len(kinds));observations=[digest(dict(v))for v in obs]+[0]*(3-len(obs));flat=[c.command,c.highx,c.highz,c.packed,c.selected,c.group,c.heading,*c.target,*c.current,*c.returns,c.effects,len(calls),digest(want),*observations,*args,*kinds];assert len(flat)==31;rows.append('{{'+','.join('0x%Xu'%v for v in flat)+'}}')
 source='#include <ultra64.h>\n#include "structs.h"\n#include "functions.h"\n#include "variables.h"\ntypedef struct{s16 x,pad2,z,pad6;}PathNode8;\nf32 func_150489B0(u8);\nstruct127 D_800CC2D0[26];struct127*D_800D154C;u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;s32*D_800D2104;\n'
 for name,p in {'candidate':selected,**mutations(selected)}.items():source+=p.replace('func_15078544(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(struct127)==812,"actor");_Static_assert(sizeof(PathNode8)==8,"path stride");
_Static_assert(__builtin_offsetof(struct127,unk13F)==319,"path group");_Static_assert(__builtin_offsetof(struct127,unk222)==546,"target index");
struct Case{u32 w[31];};static const struct Case cases[]={ROWS};static const struct Case*c;
static struct127 actor,other;static PathNode8*tables[2][256];static u16 rows[4][1040];static int calls,error;static u32 hash;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void fill(u8*p,int n,int phase){int i;for(i=0;i<n;i++)p[i]=(u8)((i+phase)*29+0x59);}
static void be(u8*p,u32 v,int n){int i;for(i=0;i<n;i++)p[i]=(u8)(v>>((n-i-1)*8));}
static void feed(u8*p,int n){int i;for(i=0;i<n;i++)hash=(hash^p[i])*16777619u;}
static void actorHash(struct127*a){u8 b[812];int i;for(i=0;i<812;i++)b[i]=((u8*)a)[i];be(b+20,bits(a->x_position),4);be(b+24,bits(a->y_position),4);be(b+28,bits(a->z_position),4);be(b+122,a->unk7A,2);feed(b,812);}
static u32 rowId(PathNode8*p){int i;for(i=0;i<4;i++)if(p==(PathNode8*)rows[i])return 0x70000u+(u32)i*0x2000u;error=1;return 0;}
static u32 digest(void){u8 b[4];int i,j;hash=2166136261u;actorHash(&actor);actorHash(&other);for(i=0;i<26;i++)actorHash(&D_800CC2D0[i]);
 for(i=0;i<2;i++)for(j=0;j<256;j++){be(b,rowId(tables[i][j]),4);feed(b,4);}for(i=0;i<4;i++)for(j=0;j<1040;j++){be(b,rows[i][j],2);feed(b,2);}
 be(b,D_800D154C==&actor?0x20000u:0x21000u,4);feed(b,4);b[0]=D_800D1890;b[1]=D_800D1891;b[2]=D_800D1892;b[3]=D_800D1893;feed(b,4);be(b,D_800D2104==(s32*)tables[0]?0x60000u:0x61000u,4);feed(b,4);return hash;}
static void effect(int stage){u32 e=c->w[16];int i;struct127*t=&D_800CC2D0[c->w[4]];
 if(e&1)D_800D154C=&other;if(e&2)D_800D1890=(u8)(65+stage*71);if(e&4)D_800D2104=(s32*)tables[1];
 if(e&8){t->x_position=9000.0f+(f32)stage;t->y_position=9001.0f+(f32)stage;t->z_position=9002.0f+(f32)stage;for(i=0;i<2;i++){struct127*a=i?&other:&actor;a->unk13F^=1;a->x_position=-3.0f*(f32)stage;}}}
static f32 mock(int kind,u32 a,u32 b){int stage=calls;if(stage>=3){error=2;return 0;}
 if(kind!=(int)c->w[28+stage]||!same(a,c->w[22+stage*2])||(kind==2&&!same(b,c->w[23+stage*2])))error=3;
 if(digest()!=c->w[19+stage])error=4;calls++;effect(calls);return real(c->w[13+stage]);}
f32 func_15048A40(u8 a){return mock(0,a,0);}f32 func_150489B0(u8 a){return mock(1,a,0);}
f32 func_150484A0(f32 a,f32 b){return mock(2,bits(a),bits(b));}f32 sinf(f32 a){return mock(3,bits(a),0);}f32 cosf(f32 a){return mock(4,bits(a),0);}
static u32 readbe(u8*p,int n){int i;u32 v=0;for(i=0;i<n;i++)v=(v<<8)|p[i];return v;}
static void initialize(struct127*a,int phase){u8*p=(u8*)a;u32 x,y,z,h;fill(p,812,phase);x=readbe(p+20,4);y=readbe(p+24,4);z=readbe(p+28,4);h=readbe(p+122,2);a->x_position=real(x);a->y_position=real(y);a->z_position=real(z);a->unk7A=(u16)h;}
typedef void(*Subject)(void);
static int check(Subject fn){u32 k;int i,j;struct127*t;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=&cases[k];initialize(&actor,0);initialize(&other,0);for(i=0;i<26;i++)initialize(&D_800CC2D0[i],i*812);
  for(i=0;i<2;i++){struct127*a=i?&other:&actor;a->unk222=(u8)c->w[4];a->unk13F=(u8)(c->w[5]^(u32)i);a->x_position=real(c->w[10]);a->y_position=real(c->w[11]);a->z_position=real(c->w[12]);}
  t=&D_800CC2D0[c->w[4]];t->x_position=real(c->w[7]);t->y_position=real(c->w[8]);t->z_position=real(c->w[9]);t->unk7A=(u16)c->w[6];
  for(i=0;i<4;i++)for(j=0;j<1040;j++)rows[i][j]=(u16)((u16)(u8)(2*j*29+0x59)<<8)|(u8)((2*j+1)*29+0x59);
  for(i=0;i<256;i++){tables[0][i]=(PathNode8*)rows[i&1];tables[1][i]=(PathNode8*)rows[2+(i&1)];}
  D_800D154C=&actor;D_800D2104=(s32*)tables[0];D_800D1890=(u8)c->w[0];D_800D1891=(u8)c->w[1];D_800D1892=(u8)c->w[2];D_800D1893=(u8)c->w[3];calls=error=0;
  fn();if(error||calls!=(int)c->w[17]||digest()!=c->w[18])return 1;
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
 report=dict(profiles=profiles,SDK32_layout=True,void_no_arguments=True,all_retained_actor_path_and_table_bytes=True,helper_boundary_snapshots=True,guest_physical_aliases_claimed=False,invalid_float_conversions_claimed=False)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
