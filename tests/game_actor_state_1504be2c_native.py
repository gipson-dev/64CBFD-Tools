"""Native SDK32 typed body, retained storage and effective semantic mutations."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_actor_state_1504be2c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_actor_state_1504be2c_oracle as guest
from tools.experiments import game_actor_state_1504be2c_match as qualify
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def mutations(p):
 rows={
 'wrong-phase-step':p.replace('padA[1] += 2','padA[1] += 1'),
 'wrong-default-state':p.replace('state->unkE = 0xA6','state->unkE = 0xA5'),
 'threshold-equality':p.replace('*magnitude > 4.0f','*magnitude >= 4.0f'),
 'wrong-input-width':p.replace('(s16) *inputValue','(u8) *inputValue'),
 'missing-sine-boundary':p.replace('func_150AD78C(phaseAngle);','(void)phaseAngle;'),
 'wrong-damping':p.replace('pad54 *= 0.5f','pad54 *= 0.25f'),
 'unsigned-control':p.replace('((s8 *) D_800CC284)[3]','((u8 *) D_800CC284)[3]'),
 'wrong-control-index':p.replace('D_800CC284)[3]','D_800CC284)[2]'),
 'wrong-RNG-gate':p.replace('& 0x3F','& 0x1F'),
 'signed-RNG-modulo':p.replace('func_150ADA20() % 25000U','func_150ADA20() % 25000'),
 'unsigned-heading-divide':p.replace('D_800CC2B2 / 3','(u16)D_800CC2B2 / 3'),
 'reached-dead-helper':p.replace('(modeFlags != 0) && (modeFlags == 0)','(modeFlags != 0) || (modeFlags == 0)'),
 'cached-child-after-sine':p.replace('phaseState = actor->unk31C;','phaseState = state;'),
 'wrong-reset-timer':p.replace('unk282 = 0x1E','unk282 = 0x1D'),
 }
 assert all(p!=v for v in rows.values());return rows

def cases():
 return[c for c in guest.cases()if not c.effects&16 and c.outputptr!=guest.INPUT]+[guest.replace(guest.Case(),first=32)]

def digest(m):
 data=bytearray()
 for base,n in((guest.ACTOR,812),(guest.OTHER,812),(guest.CHILD,512),(guest.ALT,512),(guest.INPUT,16),(guest.MAG,16),(guest.OUTPUT,16),(guest.CONTROL,8),(guest.CONTROL2,8)):
  b=bytearray(m[base+i]for i in range(n))
  if base in(guest.ACTOR,guest.OTHER):
   value=guest.read(m,base+84)
   if value&0x7FFFFFFF>0x7F800000:b[84:88]=(0x7FC00000).to_bytes(4,'big')
  data.extend(b)
 for name,n in(('D_800991D8',4),('D_800CC2B4',4),('D_800CC284',4),('D_800CC2B2',2),('D_800C35EA',1)):data.extend(m[guest.SYMS[name]+i]for i in range(n))
 h=2166136261
 for b in data:h=((h^b)*16777619)&0xFFFFFFFF
 return h

def program(selected):
 rows=[]
 for c in cases():
  m=guest.fixture(c);want,calls,obs=guest.reference(m,c);ih={guest.INPUT:0,guest.CHILD+20:1,guest.CHILD+16:2,guest.ACTOR+132:3}[c.inputptr];mh=int(c.magptr==guest.ACTOR+84);oh={guest.OUTPUT:0,guest.CHILD+11:1,guest.CHILD+22:2,guest.ACTOR+630:3}[c.outputptr]
  flat=[c.type,c.flags,c.phasebyte,c.state,c.heading,c.input,c.magnitude,c.damping,c.control,c.gate,c.first,c.second,c.effects,ih,mh,oh,len(calls),calls[0][1][0],digest(want),*[digest(dict(v))for v in obs]];flat+=[0]*(22-len(flat));assert len(flat)==22;rows.append('{{'+','.join('0x%Xu'%v for v in flat)+'}}')
 source='#include <ultra64.h>\n#include "structs.h"\n#include "functions.h"\n#include "variables.h"\nf32 D_800991D8,D_800CC2B4;s32 D_800CC284;s16 D_800CC2B2;u8 D_800C35EA;\n'
 for name,p in {'candidate':selected,**mutations(selected)}.items():source+=p.replace('func_1504BE2C(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(sizeof(struct127)==812,"actor");
_Static_assert(__builtin_offsetof(struct127,unk31C)==796,"child pointer");
_Static_assert(__builtin_offsetof(struct126,pad3C)==60,"child mode");
_Static_assert(__builtin_offsetof(struct126,unk16)==22,"child flags");
struct Case{u32 w[22];};static const struct Case cases[]={ROWS};static const struct Case*c;
static struct127 actor,other;static union{u64 align;u8 b[1024];struct126 s;}child,alt;
static union{u64 align;u8 b[16];u16 h[8];f32 f[4];}input,mag,output;
static u8 control[8],control2[8];static int calls,error;static u32 hash;
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static void fill(u8*p,int n){int i;for(i=0;i<n;i++)p[i]=(u8)(i*29+0x59);}
static void be(u8*p,u32 v,int n){int i;for(i=0;i<n;i++)p[i]=(u8)(v>>((n-i-1)*8));}
static void feed(u8*p,int n){int i;for(i=0;i<n;i++)hash=(hash^p[i])*16777619u;}
static void actorHash(struct127*a){u8 b[812];int i;u32 f=bits(a->pad54);for(i=0;i<812;i++)b[i]=((u8*)a)[i];if((f&0x7FFFFFFFu)>0x7F800000u)f=0x7FC00000u;
 be(b+84,f,4);be(b+132,a->unk84.uh,2);be(b+642,(u16)a->unk282,2);be(b+796,a->unk31C==&child.s?0x30000u:0x31000u,4);feed(b,812);}
static void childHash(struct126*s){u8 b[512];int i;for(i=0;i<512;i++)b[i]=((u8*)s)[i];be(b+8,(u16)s->unk8,2);be(b+14,s->unkE,2);be(b+16,(u16)s->unk10,2);be(b+20,(u16)s->unk14,2);feed(b,512);}
static u32 digest(void){u8 b[16];int i;hash=2166136261u;actorHash(&actor);actorHash(&other);childHash(&child.s);childHash(&alt.s);
 for(i=0;i<16;i++)b[i]=input.b[i];be(b,input.h[0],2);feed(b,16);for(i=0;i<16;i++)b[i]=mag.b[i];be(b,bits(mag.f[0]),4);feed(b,16);feed(output.b,16);feed(control,8);feed(control2,8);
 be(b,bits(D_800991D8),4);feed(b,4);be(b,bits(D_800CC2B4),4);feed(b,4);be(b,D_800CC284==(s32)control?0x50000u:0x50100u,4);feed(b,4);be(b,(u16)D_800CC2B2,2);feed(b,2);feed(&D_800C35EA,1);return hash;}
static void effects(int stage){u32 e=c->w[12];if(stage==1){if(e&1)actor.unk31C=&alt.s;if(e&2){actor.unk84.uh=0x2C;actor.pad54=-17.5f;}if(e&4){D_800CC284=(s32)control2;D_800C35EA=1;}if(e&8)actor.unk31C->unk16^=255;}
 if(stage>=2&&(e&32))actor.unk31C=stage==2?&child.s:&alt.s;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static void observe(void){if(calls>=3){error=1;return;}if(digest()!=c->w[19+calls])error=2;calls++;effects(calls);}
void func_1507EB2C(f32 x){error=3;}
f32 func_150AD78C(f32 x){if(calls||!same(bits(x),c->w[17]))error=4;observe();return -99.5f;}
s32 func_150ADA20(void){if(calls<1)error=5;observe();return(s32)c->w[calls==2?10:11];}
typedef void(*Subject)(struct127*,u16*,f32*,s8*);
static int check(Subject fn){u32 j;u16*ip;f32*mp;s8*op;
 for(j=0;j<sizeof(cases)/sizeof(cases[0]);j++){c=&cases[j];fill((u8*)&actor,812);fill((u8*)&other,812);fill(child.b,512);fill(alt.b,512);fill(input.b,16);fill(mag.b,16);fill(output.b,16);fill(control,8);fill(control2,8);
  actor.unk31C=&child.s;other.unk31C=&alt.s;actor.unk84.uh=other.unk84.uh=(u16)c->w[0];actor.pad54=other.pad54=real(c->w[7]);
  actor.unk282=other.unk282=(s16)0x1330;child.s.unk8=alt.s.unk8=(s16)0x415E;
  child.s.padA[1]=alt.s.padA[1]=(u8)c->w[2];child.s.unk16=alt.s.unk16=(u8)c->w[1];child.s.unkE=alt.s.unkE=(u16)c->w[3];child.s.unk14=alt.s.unk14=(s16)c->w[4];child.s.unk10=alt.s.unk10=(s16)0x2946;
  input.h[0]=(u16)c->w[5];mag.f[0]=real(c->w[6]);control[3]=(u8)c->w[8];control2[3]=(u8)(c->w[8]^255u);D_800991D8=real(0x3CC90FDBu);D_800CC2B4=real(0xDEADBEEFu);D_800CC284=(s32)control;D_800CC2B2=(s16)0xA5A5;D_800C35EA=(u8)c->w[9];calls=error=0;
  ip=c->w[13]==1?(u16*)&child.s.unk14:c->w[13]==2?(u16*)&child.s.unk10:c->w[13]==3?&actor.unk84.uh:input.h;mp=c->w[14]?&actor.pad54:mag.f;op=c->w[15]==1?(s8*)&child.s.padA[1]:c->w[15]==2?(s8*)&child.s.unk16:c->w[15]==3?&actor.unk276:(s8*)output.b;
  fn(&actor,ip,mp,op);if(error||calls!=(int)c->w[16]||digest()!=c->w[18])return 1;
 }return 0;}
static int run(void){if(check(candidate))return 1;
'''.replace('ROWS',',\n'.join(rows))
 for i,name in enumerate(mutations(selected)):source+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 return source+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

def main():
 selected=body((out/'final-owner.c').read_text(),qualify.FUNCTION);p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-but-set-variable',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=len(mutations(selected)))
 report=dict(profiles=profiles,SDK32_layout=True,void_typed_ABI=True,all_retained_bytes=True,helper_boundary_snapshots=True,guest_home_aliases_claimed=False)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
