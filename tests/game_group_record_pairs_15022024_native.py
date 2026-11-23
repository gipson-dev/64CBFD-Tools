"""SDK32 typed backing and effective native C comparison controls."""
import json,subprocess
from tools.experiments import game_group_record_pairs_15022024_match as p
from tools.tests import game_group_record_pairs_15022024_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
r,o=p.ROOT,p.OUT
def vectors():
 rows=[];excluded=0
 for c in g.cases():
  if c.alias in(6,7,9):excluded+=1;continue
  initial=g.fixture(c);expected,answer=g.reference(initial,c);first,second=g.outputs(c)
  values=[c.seed,c.group,c.actor,c.gate,c.count,c.match,c.alias,c.primary,c.secondary,answer]
  values.extend(g.read(expected,g.OUT+i*4)for i in range(-4,12))
  values.extend(g.read(expected,g.RECORDS+i*68+offset)for i in range(4)for offset in(60,64))
  if c.alias==8:values.extend(g.read(expected,g.STACK+c.phase+0xC8+4*i)for i in range(4))
  else:values.extend([0]*4)
  rows.append('{'+','.join(str(v&0xffffffff)+'u'for v in values[:10])+',{'+','.join(str(v&0xffffffff)+'u'for v in values[10:])+'}}')
 (o/'native-vectors.h').write_text('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n');return len(rows),excluded
def program():
 body=p.MANIFEST['body'].replace('func_15022024(','subject(')
 src='#include <ultra64.h>\n'+r'''
typedef struct {u16 type;u8 id,rest[5];} Tag;
typedef struct {u8 prefix[60];f32 value[2];} Record;
typedef struct {u32 seed,group,actor,gate,count,match,alias,primary,secondary,result,want[28];} Vector;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Tag)==8&&sizeof(Record)==68,"SDK32 records");
#include "native-vectors.h"
static u16 active[255];static Tag tags[255];static Record records[255],wantedRecords[255];
static f32 output[16],caller[4];static u8 actors[26*812];
u16 *D_800C35C8[2];u8 *D_800C35F0[2],D_800C363A[2],D_800C35EA[2],*D_800C3958[2];
f32 D_80096A14;
#define PAIR_ACTIVE_49D30 D_800C35C8
#define PAIR_TAGS_49D30 D_800C35F0
#define PAIR_COUNT_49D30 D_800C363A
#define PAIR_GATE_49D30 D_800C35EA
#define PAIR_RECORDS_49D30 D_800C3958
#define PAIR_RECORD_RELOAD_49D30(group) (((u8 *volatile *)D_800C3958)[group])
#define PAIR_ACTORS_49D30 actors
static void word(void *p,u32 n){__builtin_memcpy(p,&n,4);}
static u32 bits(const void *p){u32 n;__builtin_memcpy(&n,p,4);return n;}
static void copy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void *a,const void *b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
'''+body+r'''
static int run(void){u32 k,i,j,n;const Vector *v;f32 *first,*second;
 for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
  v=&vectors[k];n=v->count>4?v->count:4;word(&D_80096A14,0xc61c3c00u);
  for(i=0;i<sizeof(records);i++)((u8*)records)[i]=(u8)(i*29+v->seed*11+0x51);
  for(i=0;i<16;i++){u32 base=i*4;u32 x=0;for(j=0;j<4;j++)x=(x<<8)|((base+j)*29+v->seed*11+0x51)%256;word(&output[i],x);}
  for(i=0;i<2;i++){D_800C35EA[i]=(u8)v->gate;D_800C363A[i]=(u8)v->count;D_800C35C8[i]=active;D_800C35F0[i]=(u8*)tags;D_800C3958[i]=(u8*)records;}
  actors[v->actor*812+59]=(u8)(0x48+v->actor);
  for(i=0;i<n;i++){
   active[i]=(u16)(i==v->match?1:(v->seed+i)%3);tags[i].type=(u16)(i==v->match?2:(v->seed+i)%3);
   tags[i].id=(u8)(i==v->match?0x48+v->actor:0x49+v->actor+i%255);if(i!=v->match&&tags[i].id==actors[v->actor*812+59])tags[i].id^=1;
   word(&records[i].value[0],i==v->match?v->primary:v->primary+i);word(&records[i].value[1],i==v->match?v->secondary:v->secondary+i);
  }
  copy(wantedRecords,records,sizeof(records));for(i=0;i<4;i++)for(j=0;j<2;j++)word(&wantedRecords[i].value[j],v->want[16+2*i+j]);
  first=&output[4];second=&output[8];
  if(v->alias==1)second=first;
  if(v->alias==2)second=first+1;
  if(v->alias==3)first++,second=&output[4];
  if(v->alias==4)first=records[v->match==0xffffffffu?0:v->match].value;
  if(v->alias==5)second=records[v->match==0xffffffffu?0:v->match].value;
  if(v->alias==8){u32 phase=(v->seed&1)*8;for(i=0;i<4;i++){u32 x=0;for(j=0;j<4;j++)x=(x<<8)|((phase+0xc8+i*4+j)*17+v->seed*13+0xa5)%256;word(&caller[i],x);}first=&caller[2];second=&caller[0];}
  if((u32)subject(first,second,(s32)v->actor,(s32)v->group)!=v->result)return 1;
  for(i=0;i<16;i++)if(bits(&output[i])!=v->want[i])return 1;
  if(!equal(records,wantedRecords,sizeof(records)))return 1;
  if(v->alias==8)for(i=0;i<4;i++)if(bits(&caller[i])!=v->want[24+i])return 1;
 }
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 count,excluded=vectors();src,body=program();profiles={}
 def run(text,label,opt):
  f=o/(label+'.c');f.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-4000:];return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True)
 effective=[]
 for label,changed in {'wrong-gate':body.replace('PAIR_GATE_49D30[group] != 1','PAIR_GATE_49D30[group] == 0'),'wrong-tag-type':body.replace('*(u16 *)tag == 2','*(u16 *)tag == 1'),'wrong-record-field':body.replace('record + 0x3C','record + 0x40'),'discarded-true-result':body.replace('return 1;','return 0;')}.items():
  assert changed!=body;q=run(src.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 q=dict(profiles=profiles,effective_comparison_controls=effective,excluded_guest_only_aliases=excluded,source_installed=p.installed(),matching_credit=0,limits='Typed native arrays and float-pair backing. Sentinel-region/cross-record aliases are guest-only. No FCSR, arbitrary-pointer or gameplay claim.');(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
