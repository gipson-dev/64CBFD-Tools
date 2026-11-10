"""SDK32 defined-domain selection and full actor/canary comparison against independent values."""
import json,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_actor_selection_15075650_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_actor_selection_15075650_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
def mutations(b):
 expr='((u32)func_150ADA20() % span) + D_800D154C->unk220'
 result={
 'old-span-exclusion':b.replace('excluded = selection - 1','excluded = span - 1'),
 'signed-random':b.replace('(u32)func_150ADA20()','func_150ADA20()'),
 'ignored-override':b.replace('if (D_800D154C->unk21F != 0) selection = D_800D154C->unk21F;',';'),
 'missing-lock':b.replace('!= 0xD','!= 0x100'),
 'cached-minimum':b.replace('    u8 excluded;','    u8 excluded;\n    u8 cachedMinimum = D_800D154C->unk220;').replace('+ D_800D154C->unk220','+ cachedMinimum'),
 'recomputed-span':b.replace('    u8 excluded;','    u8 excluded;\n    u32 value;').replace('((u32)func_150ADA20() % span)','(value = (u32)func_150ADA20(), value % (u8)(D_800D2108[D_800D154C->unk13F] - 1 - D_800D154C->unk220))'),
 'missing-state-reset':b.replace('->unk223 = 0','->unk223 = 1'),
 'wrong-timer':b.replace('* 0x64','* 0x63'),
 'signed-rate':b.replace('->unk44 = D_800D1892','->unk44 = (s8)D_800D1892'),
 'wrong-unit-rate':b.replace('= 0.5f','= 1.5f'),
 'missing-minimum-clamp':b.replace('    if (D_800D154C->unk21E < D_800D154C->unk220) D_800D154C->unk21E = D_800D154C->unk220;','    ;'),
 'missing-flags-call':b.replace('    func_15075498();','    ;')}
 assert len(result)==12 and all(v!=b for v in result.values());return result
def cases():return[c for c in guest.cases()if not c.alias and c.home_span<0 and c.home_excluded<0 and not guest.reference(guest.fixture(c),c)[3]]
def digest(vs):
 h=2166136261
 for v in vs:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def snapshot_values(o):return[guest.ACTORS.index(o[0]),*o[1:-1],o[-1]>>32,o[-1]&0xFFFFFFFF]
def values(m,c):
 s=guest.SYMS;vs=[guest.ACTORS.index(guest.read(m,s['D_800D154C'])),guest.TABLES.index(guest.read(m,s['D_800D2108']))]
 skip=set(range(0x44,0x48))|set(range(0xF4,0xF8))|set(range(0x21C,0x21E))|set(range(0x244,0x246))
 for a in guest.ACTORS:
  vs +=[guest.read(m,a+0x44),guest.read(m,a+0xF4),guest.read(m,a+0x21C,2),guest.read(m,a+0x244,2)]
  vs +=[m[a+i]for i in range(-16,828)if i not in skip]
 for t in guest.TABLES:vs +=[m[t+i]for i in range(256)]
 vs +=[m[s['D_800D1890']+i]for i in range(4)];seed=guest.read(m,guest.SEED,8);vs +=[seed>>32,seed&0xFFFFFFFF];return vs
def expected(c):
 m,calls,obs,trap=guest.reference(guest.fixture(c),c);assert not trap;trace=[]
 for (t,_),o in zip(calls,obs):trace +=[int(t==guest.FLAGS),*snapshot_values(o)]
 return digest(values(m,c)),digest(trace),len(calls)
def program(selected):
 rows=[]
 for c in cases():
  fields=[c.mode,c.table,c.override,c.minimum,c.current,c.state,c.timer,c.rate,c.flags,c.random,c.mutation,int(c.real),c.seed>>32,c.seed&0xFFFFFFFF,*expected(c)]
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in fields)+'}')
 functions='\n'.join(p.replace('func_15075650(',name.replace('-','_')+'(')for name,p in{'candidate':selected,**mutations(selected)}.items())
 flags=body((out/'final-owner.c').read_text(),'func_15075498').replace('void func_15075498(void) {','void func_15075498(void) {\n    record(1);').replace('\n}', '\n    if(c->mutation&8){D_800D154C=&actors[2].actor;D_800D154C->unk223=169;}\n}',1)
 text=r'''#include <ultra64.h>
#include "functions.h"
#include "variables.h"
_Static_assert(sizeof(void*)==4,"SDK pointers");
_Static_assert(sizeof(struct127)==812,"actor extent");
_Static_assert(__builtin_offsetof(struct127,unk44)==0x44,"rate");
_Static_assert(__builtin_offsetof(struct127,unk21C)==0x21C,"timer");
_Static_assert(__builtin_offsetof(struct127,unk21E)==0x21E,"selection");
_Static_assert(__builtin_offsetof(struct127,unk244)==0x244,"flags halfword");
struct Case{u32 mode,table,override,minimum,current,state,timer,rate,flags,random,mutation,real,seedHi,seedLo,stateHash,traceHash,calls;};
static const struct Case rows[]={ROWS};static const struct Case*c;
struct Actor{u8 before[16];struct127 actor;u8 after[16];};static struct Actor actors[3];
static u8 tables[2][256];struct127*D_800D154C;u8*D_800D2108;u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;u64 D_800885B0;
static u32 trace,calls,failure[2];
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static u32 actorId(struct127*p){u32 i;for(i=0;i<3;i++)if(p==&actors[i].actor)return i;return 99;}
static u32 floatBits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static void record(u32 code){struct127*a=D_800D154C;hash(&trace,code);hash(&trace,actorId(a));hash(&trace,a->unk21E);hash(&trace,a->unk220);hash(&trace,a->unk223);hash(&trace,a->unk21C);hash(&trace,floatBits(a->unk44));hash(&trace,(u32)a->unkF4);hash(&trace,(u16)a->unk244);hash(&trace,(u32)(D_800885B0>>32));hash(&trace,(u32)D_800885B0);calls++;}
s32 func_150ADA20(void){u64 mixed;record(0);
 if(c->mutation&1){D_800D154C=&actors[1].actor;D_800D154C->unk220=250;D_800D154C->unk21E=2;}
 if(c->mutation&2){D_800D1890=251;D_800D1892=1;D_800D1893=130;}
 if(c->mutation&4){D_800D2108=tables[1];D_800D154C->unk13F=9;D_800D154C->unk21F=1;tables[1][9]=3;}
 if(!c->real)return(s32)c->random;
 mixed=((D_800885B0&1)<<32)|((D_800885B0>>1)&0xFFFFFFFFu);mixed^=(D_800885B0&0xFFFFFu)<<12;D_800885B0=mixed^((mixed>>20)&0xFFFu);return(s32)D_800885B0;
}
FLAGS
FUNCTIONS
static void initialize(void){u32 k,j;u8*b;
 for(k=0;k<3;k++){b=(u8*)&actors[k];for(j=0;j<sizeof(actors[k]);j++)b[j]=(u8)(((s32)j-16)*29+k*17+91);actors[k].actor.unk13F=37;actors[k].actor.unk21F=(u8)c->override;actors[k].actor.unk220=(u8)c->minimum;actors[k].actor.unk21E=(u8)c->current;actors[k].actor.unk223=(u8)c->state;actors[k].actor.unk21C=(u16)((((0x21C*29+k*17+91)&255)<<8)|((0x21D*29+k*17+91)&255));actors[k].actor.unk244=(s16)((((0x244*29+k*17+91)&255)<<8)|((0x245*29+k*17+91)&255));actors[k].actor.unk44=1.0f;actors[k].actor.unkF4=(s32)0xA5A5143Eu;}
 for(k=0;k<2;k++)for(j=0;j<256;j++)tables[k][j]=(u8)(j*13+5);tables[0][37]=(u8)c->table;D_800D2108=tables[0];D_800D154C=&actors[0].actor;
 D_800D1890=(u8)c->timer;D_800D1891=(u8)c->mode;D_800D1892=(u8)c->rate;D_800D1893=(u8)c->flags;D_800885B0=((u64)c->seedHi<<32)|c->seedLo;trace=2166136261u;calls=0;
}
static u32 state(void){u32 h=2166136261u,k,j;u8*b;hash(&h,actorId(D_800D154C));hash(&h,D_800D2108==tables[0]?0:D_800D2108==tables[1]?1:99);
 for(k=0;k<3;k++){struct127*a=&actors[k].actor;hash(&h,floatBits(a->unk44));hash(&h,(u32)a->unkF4);hash(&h,a->unk21C);hash(&h,(u16)a->unk244);b=(u8*)a;for(j=0;j<844;j++){s32 off=(s32)j-16;if((off>=0x44&&off<0x48)||(off>=0xF4&&off<0xF8)||(off>=0x21C&&off<0x21E)||(off>=0x244&&off<0x246))continue;hash(&h,((u8*)&actors[k])[j]);}}
 for(k=0;k<2;k++)for(j=0;j<256;j++)hash(&h,tables[k][j]);hash(&h,D_800D1890);hash(&h,D_800D1891);hash(&h,D_800D1892);hash(&h,D_800D1893);hash(&h,(u32)(D_800885B0>>32));hash(&h,(u32)D_800885B0);return h;
}
static int check(void(*fn)(void)){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){c=&rows[i];initialize();fn();failure[0]=i;if(state()!=c->stateHash){failure[1]=1;return 1;}if(trace!=c->traceHash||calls!=c->calls){failure[1]=2;return 2;}}return 0;}
static int run(void){if(check(candidate))return 1;
CONTROLS
return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int r=run();if(r)__asm__ volatile(".byte 0xcd,0x80"::"a"(4),"b"(2),"c"(failure),"d"(8):"memory");__asm__ volatile(".byte 0xcd,0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
 controls='\n'.join('if(!check('+name.replace('-','_')+')){failure[0]='+str(i)+';failure[1]=99;return 2;}'for i,name in enumerate(mutations(selected)))
 return text.replace('ROWS',',\n'.join(rows)).replace('FLAGS',flags).replace('FUNCTIONS',functions).replace('CONTROLS',controls)
def main():
 selected=body((out/'final-owner.c').read_text(),'func_15075650');p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-variable','-Wno-type-limits','-Wno-unused-but-set-variable',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,struct.unpack('<II',r.stderr)if len(r.stderr)==8 else r.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=len(cases()),effective_controls=12)
 report=dict(profiles=profiles,SDK32_layout=True,full_actor_and_canary_bytes=True,independent_expected_state=True,zero_division_and_physical_guest_aliases_excluded=True,original_RNG_C_model=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
