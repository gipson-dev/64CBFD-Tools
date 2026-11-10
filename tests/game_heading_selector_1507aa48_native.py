"""SDK32 C execution on defined unsigned-conversion inputs with effective controls."""
import json,math,subprocess,sys
from pathlib import Path
from tools.experiments.game_heading_selector_1507aa48_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_heading_selector_1507aa48_oracle as guest
from tools.experiments import game_heading_selector_1507aa48_match as qualify
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def mutations(p):
 rows={
 'wrong-packed-byte':p.replace('D_800D1890 << 8','D_800D1890 << 7'),
 'wrong-add':p.replace('unk76 + value','unk76 - value'),
 'wrong-subtract':p.replace('unk76 - value','unk76 + value'),
 'wrong-saved-field':p.replace('unk7A = D_800D154C->unk78','unk7A = D_800D154C->unk76 + 1'),
 'wrong-X-direction':p.replace('second[1].x - first[1].x','first[1].x - second[1].x'),
 'wrong-node':p.replace('second[1].z','second[0].z'),
 'wrong-bias':p.replace('+ 0x4000','+ 0x2000'),
 'wrong-actor-stride':p.replace('* 0x196','* 0x195'),
 'wrong-mode6':p.replace('case 6:\n            D_800D154C->unk78 = D_800D154C->unk76','case 6:\n            D_800D154C->unk78 = D_800D154C->unk7A'),
 'stale-actor':p.replace('    u16 value;','    struct127 *cached = D_800D154C;\n    u16 value;').replace('D_800D154C->unk78 =','cached->unk78 ='),
 'stale-scale':p.replace('    u16 value;','    f32 scale = D_8009A20C;\n    u16 value;').replace('* D_8009A20C','* scale'),
 'stale-third-byte':p.replace('    u16 value;','    u8 third = D_800D1893;\n    u16 value;').replace('(D_800D1893 << 8)','(third << 8)'),
 }
 assert all(v!=p for v in rows.values());return rows
def cases():
 result=[]
 for c in guest.cases():
  if c.alias:continue
  if c.command==4:
   value=guest.floating(guest.bits(guest.floating(c.angle)*guest.floating(0x40000000 if c.effects&4 else c.scale)))
   if not math.isfinite(value)or not -1<value<2**32:continue
  result.append(c)
 return result
def digest(m):
 s=guest.SYMS;data=bytearray()
 for base,n in((guest.ACTOR,812),(guest.ALT_ACTOR,812),(s['D_800CC34A']-122,812*26),(guest.TABLE,1024),*((p,2080)for p in guest.ROWS)):data.extend(m[base+i]for i in range(n))
 for name,n in(('D_800D154C',4),('D_800D1890',4),('D_800D2104',4),('D_8009A20C',4)):data.extend(m[s[name]+i]for i in range(n))
 h=2166136261
 for b in data:h=((h^b)*16777619)&0xFFFFFFFF
 return h
def program(selected):
 rows=[]
 for c in cases():
  want,calls,obs,_=guest.reference(guest.fixture(c),c);args=calls[0][1]if calls and c.command==4 else(0,0)
  flat=[c.command,c.first,c.second,c.third,c.base,c.heading,c.saved,c.selected,c.group,*c.coordinates,c.angle,c.scale,c.random,c.effects,len(calls),digest(want),digest(dict(obs[0]))if obs else 0,*args];assert len(flat)==22;rows.append('{{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in flat)+'}}')
 source='#include <ultra64.h>\n#include "structs.h"\n#include "functions.h"\n#include "variables.h"\ntypedef struct{s16 x,pad2,z,pad6;}PathNode8;\nstruct127 D_800CC2D0[26];struct127*D_800D154C;u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;s32*D_800D2104;f32 D_8009A20C;\n__asm__(".globl D_800CC34A\\n.set D_800CC34A,D_800CC2D0+122");\n'
 for name,p in {'candidate':selected,**mutations(selected)}.items():source+=p.replace('func_1507AA48(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(struct127)==812,"actor");_Static_assert(sizeof(PathNode8)==8,"path");
_Static_assert(__builtin_offsetof(struct127,unk76)==118,"base");_Static_assert(__builtin_offsetof(struct127,unk78)==120,"heading");_Static_assert(__builtin_offsetof(struct127,unk7A)==122,"saved");
_Static_assert(__builtin_offsetof(struct127,unk13F)==319,"group");_Static_assert(__builtin_offsetof(struct127,unk222)==546,"selection");
struct Case{u32 w[22];};static const struct Case cases[]={ROWS};static const struct Case*c;
static struct127 actor,other;static PathNode8*tables[256],paths[2][260];static int calls,error;static u32 hash;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void be(u8*p,u32 v,int n){int i;for(i=0;i<n;i++)p[i]=(u8)(v>>((n-i-1)*8));}
static u32 readbe(u8*p,int n){int i;u32 v=0;for(i=0;i<n;i++)v=(v<<8)|p[i];return v;}
static void feed(u8*p,int n){int i;for(i=0;i<n;i++)hash=(hash^p[i])*16777619u;}
static void actorHash(struct127*a){u8 b[812];int i;for(i=0;i<812;i++)b[i]=((u8*)a)[i];be(b+118,a->unk76,2);be(b+120,a->unk78,2);be(b+122,a->unk7A,2);feed(b,812);}
static u32 digest(void){u8 b[4];int i,j;u16*p;hash=2166136261u;actorHash(&actor);actorHash(&other);for(i=0;i<26;i++)actorHash(&D_800CC2D0[i]);
 for(i=0;i<256;i++){if(tables[i]!=paths[0]&&tables[i]!=paths[1])error=1;be(b,tables[i]==paths[0]?0x70000u:0x72000u,4);feed(b,4);}
 for(i=0;i<2;i++){p=(u16*)paths[i];for(j=0;j<1040;j++){be(b,p[j],2);feed(b,2);}}
 be(b,D_800D154C==0?0:D_800D154C==&actor?0x20000u:0x21000u,4);feed(b,4);b[0]=D_800D1890;b[1]=D_800D1891;b[2]=D_800D1892;b[3]=D_800D1893;feed(b,4);be(b,0x60000u,4);feed(b,4);be(b,bits(D_8009A20C),4);feed(b,4);return hash;}
static void effect(void){u32 e=c->w[16];int i;if(e&1)D_800D154C=&other;if(e&2)D_800D1893=0x17;if(e&4)D_8009A20C=2.0f;
 if(e&8){for(i=0;i<2;i++){struct127*a=i?&other:&actor;a->unk78=0x5A81;a->unk13F^=1;}tables[c->w[8]]=paths[1-(c->w[8]&1)];}}
static void mock(int kind,u32 a,u32 b){if(calls++||kind!=(int)c->w[0]||(kind==4&&(a!=c->w[20]||b!=c->w[21])))error=2;if(digest()!=c->w[19])error=3;effect();}
f32 func_150484A0(f32 a,f32 b){mock(4,bits(a),bits(b));return real(c->w[13]);}s32 func_150ADA20(void){mock(5,0,0);return (s32)c->w[15];}
static void initialize(struct127*a,int phase){u8*p=(u8*)a;int i;for(i=0;i<812;i++)p[i]=(u8)((i+phase)*29+0x59);a->unk76=(u16)readbe(p+118,2);a->unk78=(u16)readbe(p+120,2);a->unk7A=(u16)readbe(p+122,2);}
typedef void(*Subject)(void);
static int check(Subject fn){u32 k;int i,j;u16*p;PathNode8*r;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=&cases[k];initialize(&actor,0);initialize(&other,0);for(i=0;i<26;i++)initialize(&D_800CC2D0[i],i*812);
  for(i=0;i<2;i++){struct127*a=i?&other:&actor;a->unk222=(u8)c->w[7];a->unk13F=(u8)(c->w[8]^(u32)i);a->unk76=(u16)(c->w[4]^(i?0x55AAu:0));a->unk78=(u16)(c->w[5]^(i?0x55AAu:0));a->unk7A=(u16)(c->w[6]^(i?0x55AAu:0));}
  D_800CC2D0[c->w[7]].unk7A=0xE137;
  for(i=0;i<2;i++){p=(u16*)paths[i];for(j=0;j<1040;j++)p[j]=(u16)((u16)(u8)(2*j*29+0x59)<<8)|(u8)((2*j+1)*29+0x59);}
  for(i=0;i<256;i++)tables[i]=paths[i&1];r=paths[c->w[8]&1];r[c->w[1]+1].x=(s16)c->w[9];r[c->w[1]+1].z=(s16)c->w[10];r[c->w[2]+1].x=(s16)c->w[11];r[c->w[2]+1].z=(s16)c->w[12];
  D_800D154C=c->w[0]>=9?0:&actor;D_800D2104=(s32*)tables;D_8009A20C=real(c->w[14]);D_800D1890=(u8)c->w[1];D_800D1891=(u8)c->w[2];D_800D1892=(u8)c->w[0];D_800D1893=(u8)c->w[3];calls=error=0;
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
 report=dict(profiles=profiles,SDK32_layout=True,void_no_arguments=True,retained_actor_path_table_bytes=True,helper_boundary_snapshots=True,invalid_float_conversions_claimed=False,physical_aliases_guest_only=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
