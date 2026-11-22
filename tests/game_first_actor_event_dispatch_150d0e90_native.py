"""Run the actual C body with SDK32 types against independent guest vectors."""
from pathlib import Path
import itertools,json,subprocess,sys
from tools.experiments import game_first_actor_event_dispatch_150d0e90_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_first_actor_event_dispatch_150d0e90_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
selected=packet.MANIFEST['selected_source'];a,b=function_span(selected,'func_150D0E90');BODY=selected[a:b]

def hash_bytes(values):
 h=2166136261
 for value in values:h=((h^value)*16777619)&0xFFFFFFFF
 return h

def snapshot(m):
 actor=[m[g.ACTOR+i]for i in range(812)]
 actor[0x31C:0x320]=[0,0,0,0]
 return [g.read(m,p)for p in g.COUNTERS]+[g.read(m,g.TICKS),(g.read(m,g.BASE)-g.RECORDS)//160,
    int(g.read(m,g.FLAGSP)==g.OTHER),hash_bytes(actor),hash_bytes(m[g.ATTACH+i]for i in range(0x130)),
    hash_bytes(m[g.FLAGS-128+i]for i in range(264)),hash_bytes(m[g.OTHER-128+i]for i in range(264))]

PRE=r'''#include <ultra64.h>
#include "structs.h"
#define OFF __builtin_offsetof
typedef char exact_sizes[sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(struct131)==160?1:-1];
typedef char exact_actor_link[OFF(struct127,unk31C)==0x31C?1:-1];
s32 D_80088890,D_80088894,D_80088898,D_8008889C,D_800BE9E4;
struct127 D_800CC2D0[1];
static struct131 records[64];
static u32 firstFlags[128],secondFlags[128];
static u8 attachment[0x140];
struct131 *D_800DBEF4;
u32 *D_800DBF94;
u8 *func_151149AC(u8);
void func_151951E0(u8 *);
s32 func_10010154(u16,void *,u16,s16,u16);
s32 func_15136C3C(void *,s32,s32,s32,s32,s32,s32,s32);
void func_15145A50(struct127 *);
s32 func_1507CD64(struct127 *,s32);
'''
HARNESS=r'''
static u32 rowIndex,stepIndex,bad,counts[6];
static void check(int value){if(!value)bad=1;}
static void setword(u8 *p,u32 v){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static u32 byteshash(const u8 *p,u32 n){u32 i,h=2166136261u;for(i=0;i<n;i++)h=(h^p[i])*16777619u;return h;}
static u32 wordhash(const u32 *p){u32 i,j,h=2166136261u;for(i=0;i<66;i++)for(j=0;j<4;j++)h=(h^((p[i]>>(24-8*j))&255))*16777619u;return h;}
static u32 actorhash(void){
 const u8 *p=(const u8*)D_800CC2D0;u32 i,j,k,h=2166136261u;
 for(i=0;i<812;i++){
  j=i;
  for(k=0;k<5;k++){u32 start=k==0?0:0x1Cu+4*k;if(i>=start&&i<start+4)j=start+3-(i-start);}
  h=(h^(i>=0x31C&&i<0x320?0:p[j]))*16777619u;
 }
 return h;
}
static void state(u32 result[11]){
 result[0]=(u32)D_80088890;result[1]=(u32)D_80088894;result[2]=(u32)D_80088898;result[3]=(u32)D_8008889C;
 result[4]=(u32)D_800BE9E4;result[5]=(u32)(D_800DBEF4-records);result[6]=D_800DBF94==secondFlags+32;
 result[7]=actorhash();result[8]=byteshash(attachment,0x130);result[9]=wordhash(firstFlags);result[10]=wordhash(secondFlags);
}
static void compare(const u32 wanted[11]){u32 i,actual[11];state(actual);for(i=0;i<11;i++)check(actual[i]==wanted[i]);}
static u32 call(u32 target,u32 a0,u32 a1,u32 a2,u32 a3,u32 a4,u32 a5,u32 a6,u32 a7){
 const Row *r=&rows[rowIndex];u32 index,ordinal;u8 *actor=(u8*)D_800CC2D0;
 check(stepIndex<r->stepCount);if(bad)return 0;
 const Step *s=&steps[r->stepStart+stepIndex++];u32 args[8]={a0,a1,a2,a3,a4,a5,a6,a7},i;
 check(s->target==target);for(i=0;i<8;i++)check(args[i]==s->args[i]);compare(s->before);
 if(target==0x151149AC){
  index=a0==250?0:a0==249?1:a0==248?2:a0==251?3:4;
  check(index<4);if(bad)return 0;
  struct131 *answer=D_800DBEF4+r->indices[index];ordinal=++counts[0];
  if(r->mode&1)D_800DBEF4+=ordinal%2?1:-1;
  if(r->mode&2)D_800DBF94=D_800DBF94==firstFlags+32?secondFlags+32:firstFlags+32;
  return (u32)answer;
 }
 if(target==0x151951E0){ordinal=++counts[1];setword(actor+0x20,0x13570000u+ordinal);if(r->mode&4){attachment[0x120]=255;D_800BE9E4=7;}}
 else if(target==0x10010154){
  ordinal=++counts[2];setword(actor+0x24,0x24680000u+ordinal);
  if(r->mode&8)for(i=0;i<4;i++){firstFlags[32+r->indices[i]]^=1;secondFlags[32+r->indices[i]]^=1;}
 }
 else if(target==0x15136C3C){ordinal=++counts[3];setword(actor+0x28,0x35790000u+ordinal);}
 else if(target==0x15145A50){ordinal=++counts[4];setword(actor+0x2C,0x468A0000u+ordinal);}
 else if(target==0x1507CD64){++counts[5];setword(actor,a1);}
 else check(0);
 return 0xDEADBEEFu;
}
u8 *func_151149AC(u8 k){return (u8*)call(0x151149AC,k,0,0,0,0,0,0,0);}
void func_151951E0(u8 *p){check(p==(u8*)D_800CC2D0);call(0x151951E0,1,0,0,0,0,0,0,0);}
s32 func_10010154(u16 s,void *p,u16 v,s16 a,u16 b){check(p==(void*)D_800CC2D0);return call(0x10010154,s,1,v,(u32)a,b,0,0,0);}
s32 func_15136C3C(void *p,s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 k){check(p==(void*)D_800CC2D0);return call(0x15136C3C,1,a,b,c,d,e,f,k);}
void func_15145A50(struct127 *p){check(p==D_800CC2D0);call(0x15145A50,1,0,0,0,0,0,0,0);}
s32 func_1507CD64(struct127 *p,s32 k){check(p==D_800CC2D0);return call(0x1507CD64,1,k,0,0,0,0,0,0);}
static int run(void){
 u32 i,j;u8 *actor=(u8*)D_800CC2D0;
 for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){
  const Row *r=&rows[rowIndex];stepIndex=bad=0;
  for(i=0;i<6;i++)counts[i]=0;
  for(i=0;i<812;i++)actor[i]=(u8)((i+16)*19+0xA5);
  for(i=0;i<5;i++){j=i==0?0:0x1C+4*i;u32 v=(u32)actor[j]<<24|(u32)actor[j+1]<<16|(u32)actor[j+2]<<8|actor[j+3];setword(actor+j,v);}
  for(i=0;i<sizeof(attachment);i++)attachment[i]=(u8)((i+16)*19+0xA5);
  for(i=0;i<128;i++)firstFlags[i]=secondFlags[i]=0;
  {u32 guard=0;for(i=0;i<4;i++)guard=(guard<<8)|(((260+i)*19+0xA5)&255);firstFlags[65]=secondFlags[65]=guard;}
  for(i=0;i<4;i++){u32 v=r->pattern|((r->mask>>i)&1);firstFlags[32+r->indices[i]]=v;secondFlags[32+r->indices[i]]=v^1;}
  D_800DBEF4=records+16;D_800DBF94=firstFlags+32;
  D_800CC2D0[0].unk31C=(void*)attachment;attachment[0x120]=r->gate;
  D_80088890=r->counters[0];D_80088894=r->counters[1];D_80088898=r->counters[2];D_8008889C=r->counters[3];D_800BE9E4=r->ticks;
  func_150D0E90((s32)r->unused);compare(r->final);check(stepIndex==r->stepCount);
  if(bad)return 1;
 }
 return 0;
}
'''

def vectors():
 cases=[g.Case(gate=i,unused=g.u32(i*0x01010101))for i in range(256)]
 cases += [g.Case(mask=mask,indices=indices,mode=mode,phase=phase,pattern=pattern,ticks=ticks)
           for mask,indices,mode,phase,pattern,ticks in itertools.product(range(16),
              ((0,1,2,3),(-5,3,-1,4),(0,0,0,0)),(0,1,2,4,8,15),(0,8),(0,3),(-1,1))]
 cases += [g.Case(ticks=1,counters=(2147483607,-2147483582,-2147483640,2147483555)),
           g.Case(ticks=-1,counters=(-2147483608,2147483581,2147483639,-2147483556)),
           g.Case(ticks=23342213,counters=(0,0,0,0)),g.Case(ticks=-23342213,counters=(0,0,0,0))]
 steps=[];rows=[];program=g.streams()[0]
 for c in cases:
  assert not c.residual and not c.missing
  for counter,k in zip(c.counters,(40,-66,-8,92)):
   assert -2**31<=c.ticks*k<2**31 and -2**31<=counter+c.ticks*k<2**31
  m=g.check(program,c);initial=g.fixture(c);final,calls,observations=g.reference(initial,c)
  assert g.public(m.memory)==g.public(final)
  # Replay the independent reference's helper effects to capture every boundary state.
  replay=dict(initial)
  for a,k in zip(g.COUNTERS,(40,-66,-8,92)):g.put(replay,a,g.read(replay,a)+c.ticks*k)
  start=len(steps);counts={}
  for (target,args),observation in zip(calls,observations):
   assert g.observe(replay)==observation
   adjusted=list(args)+[0]*(8-len(args))
   if target in(g.INIT,g.EFFECT,g.RESET,g.STATE):adjusted[0]=1
   elif target==g.SOUND:adjusted[1]=1
   steps.append((target,adjusted,snapshot(replay)))
   counts[target]=counts.get(target,0)+1;g.effect(replay,c,target,args,counts[target])
  assert g.public(replay)==g.public(final)
  rows.append((c, start,len(steps)-start,snapshot(final)))
 def array(values):return '{'+','.join('0x%Xu'%g.u32(v)for v in values)+'}'
 header='typedef struct {u32 target,args[8],before[11];} Step;\ntypedef struct {s32 ticks,counters[4],indices[4];u32 gate,mask,pattern,mode,unused,stepStart,stepCount,final[11];} Row;\n'
 header+='static const Step steps[]={'+','.join('{0x%Xu,%s,%s}'%(t,array(a),array(s))for t,a,s in steps)+'};\n'
 header+='static const Row rows[]={'+','.join('{%d,%s,%s,%s,%s}'%(c.ticks,array(c.counters),array(c.indices),
            ','.join('0x%Xu'%g.u32(v)for v in(c.gate,c.mask,(0,2,0x80000000,0xFFFFFFFE)[c.pattern%4],c.mode,c.unused,start,count)),array(final))for c,start,count,final in rows)+'};\n'
 (out/'native-vectors.h').write_text(header);return len(cases)

def main():
 count=vectors()
 controls={
  'wrong-counter-factor':BODY.replace('* 40;','* 41;'),
  'inverted-attachment-gate':BODY.replace('[0x120] == 0','[0x120] != 0'),
  'missing-selector':BODY.replace('i != 3','i != 2'),
  'wrong-flag-bit':BODY.replace('] & 1','] & 2'),
  'omitted-initializer':BODY.replace('func_151951E0((u8 *)actor);','(void)actor;'),
  'wrong-sound-volume':BODY.replace('0x7FFF,200,700','0x7FFE,200,700'),
  'wrong-final-selector':BODY.replace('func_151149AC(251)','func_151149AC(250)'),
  'wrong-effect-stack-argument':BODY.replace('actor,1,1,1,1,0,255,1','actor,1,1,1,1,1,255,1'),
  'omitted-state-reset':BODY.replace('func_15145A50(actor);','(void)actor;'),
  'wrong-final-state':BODY.replace('func_1507CD64(actor,6)','func_1507CD64(actor,7)')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe')
  path.write_text(PRE+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode!=0,name;effective.append(name)
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_struct_layout=True,strict_aliasing=True,UBSan=True)
 report=dict(profiles=profiles,effective_source_controls=effective,independent_guest_checked_vectors=True,
             all_call_arguments_and_boundary_states=True,negative_record_indices_same_allocated_array=True,
             NULL_nonmultiple_and_overflow_inputs_excluded_from_native=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
