"""Native SDK projection contract with float32 boundary cases and mutations."""
import json,sys,subprocess
from pathlib import Path
from tools.experiments.game_angle_limit_1505210c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_angle_limit_1505210c_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def mutations(selected):
 rows={
 'wrong-heading':selected.replace('actor->unk40','*(f32 *)((u8 *)actor + 0x44)'),
 'wrong-first-helper':selected.replace('func_150AD780(radians)','func_150AD78C(radians)'),
 'missing-input-negation':selected.replace('    z = -z;','    z = z;'),
 'wrong-primary-sign':selected.replace('(x * cosine) + (z * sine)','(x * cosine) - (z * sine)'),
 'wrong-secondary-sign':selected.replace('(-x * sine)','(x * sine)'),
 'upper-wrap-equality':selected.replace('x >= 180.0f','x > 180.0f'),
 'secondary-wrap-equality':selected.replace('second >= 180.0f','second > 180.0f'),
 'missing-primary-lower-clamp':selected.replace('if (x < negativeLimit) x = negativeLimit;','if (x < negativeLimit) x = x;'),
 'wrong-output':selected.replace('*secondary = z;','*secondary = x;'),
 'early-output':selected.replace('    second = func_150484A0','    *secondary = z;\n    second = func_150484A0'),
 'cached-first-scale':selected.replace('    f32 primary;','    f32 primary;\n    f32 cachedScale = D_80099334;').replace('* D_80099334','* cachedScale'),
 'overwritten-original-x':selected.replace('    primary = (x * cosine) + (z * sine);','    primary = (x * cosine) + (z * sine);\n    x = primary;'),
 }
 assert len(rows)==12 and all(v!=selected for v in rows.values()),[k for k,v in rows.items()if v==selected];return rows
def cases():return[c for c in guest.cases()if not c.effects&4 and c.output in(guest.OUTPUT,guest.ACTOR+64)]
def program(selected):
 rows=[]
 for c in cases():
  m=guest.fixture(c);guest.put(m,guest.STACK+c.phase+16,c.limit);want,calls,obs,value=guest.reference(m,c)
  flat=(c.heading,c.x,c.z,c.limit,*c.returns,value,guest.read(want,c.output),guest.read(want,guest.ACTOR+64),*[v for _,a in calls for v in(a if len(a)==2 else(*a,0))],*[v for observation in obs for v in observation[:2]],*[guest.read(want,guest.SYMS[n])for n in('D_80099330','D_80099334','D_80099338')])
  assert len(flat)==30;rows.append('{ {'+','.join('0x%Xu'%v for v in flat)+'},%d,%d }'%(c.effects,c.output==guest.ACTOR+64))
 source='#include <ultra64.h>\n#include "structs.h"\nf32 D_80099330,D_80099334,D_80099338;\nf32 func_150AD780(f32);\nf32 func_150AD78C(f32);\nf32 func_150484A0(f32,f32);\n'
 variants={'candidate':selected,**mutations(selected)}
 for name,part in variants.items():source+=part.replace('func_1505210C(',name.replace('-','_')+'(',1)+'\n'
 source+=r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(struct127)==812,"SDK actor");
_Static_assert(__builtin_offsetof(struct127,unk40)==64,"heading");
struct Case{u32 w[30];u8 effects,alias;};static const struct Case cases[]={ROWS};
static const struct Case*c;static struct127 actor;static f32 output;static int calls,error;
static f32 floating(u32 n){union{u32 u;f32 f;}v;v.u=n;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static f32 *destination(void){return c->alias?&actor.unk40:&output;}
static f32 mock(int kind,f32 x,f32 y){int stage=calls++;int wantKind=stage==0?0:stage==1?1:2;
 if(stage>3){error=1;return 0;}
 if(kind!=wantKind||!same(bits(x),c->w[11+stage*2])||(stage>1&&!same(bits(y),c->w[12+stage*2])))error=2;
 if(!same(bits(actor.unk40),c->w[19+stage*2])||!same(bits(*destination()),c->w[20+stage*2]))error=3;
 if(c->effects&1){actor.unk40=17.25f+(f32)(stage+1);D_80099330=.5f;D_80099334=2.0f+(f32)(stage+1);D_80099338=-3.0f-(f32)(stage+1);}
 if(c->effects&2)*destination()=floating(0xBAAD0001u+(u32)stage);
 return floating(c->w[4+stage]);
}
__attribute__((noinline)) f32 func_150AD780(f32 x){return mock(0,x,0);}
__attribute__((noinline)) f32 func_150AD78C(f32 x){return mock(1,x,0);}
__attribute__((noinline)) f32 func_150484A0(f32 x,f32 y){return mock(2,x,y);}
typedef f32(*Subject)(struct127*,f32,f32,f32*,f32);
static int check(Subject fn){u32 j;int i;f32 answer;u8*p=(u8*)&actor;
 for(j=0;j<sizeof(cases)/sizeof(cases[0]);j++){c=&cases[j];for(i=0;i<812;i++)p[i]=(u8)(i*29+0x59);actor.unk40=floating(c->w[0]);output=floating(0x597693B0u);
  D_80099330=floating(0x3C8EFA35u);D_80099334=D_80099338=floating(0x42652EE0u);calls=error=0;
  answer=fn(&actor,floating(c->w[1]),floating(c->w[2]),destination(),floating(c->w[3]));
  if(error||calls!=4||!same(bits(answer),c->w[8])||!same(bits(*destination()),c->w[9])||!same(bits(actor.unk40),c->w[10]))return 1;
  if(!same(bits(D_80099330),c->w[27])||!same(bits(D_80099334),c->w[28])||!same(bits(D_80099338),c->w[29]))return 2;
  for(i=0;i<812;i++)if(!(64<=i&&i<68)&&p[i]!=(u8)(i*29+0x59))return 3;
 }return 0;
}
static int run(void){if(check(candidate))return 1;
'''.replace('ROWS',',\n'.join(rows))
 for i,name in enumerate(mutations(selected)):source+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 return source+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def main():
 selected=body((out/'final-owner.c').read_text(),'func_1505210C');p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=12)
 report=dict(profiles=profiles,SDK32_actor_layout=True,ordered_NaN_and_signed_zero=True,NaN_payload_or_FCSR_claimed=False,actor_output_alias=True,callback_scale_reloads=True,untouched_actor_bytes=True,guest_home_mutations_claimed=False)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
