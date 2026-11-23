"""Actual SDK32 C over typed native records and independent guest vectors."""
import hashlib,json,subprocess
from tools.experiments import game_texture_registration_15195dd4_match as p
from tools.tests import game_texture_registration_15195dd4_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
r,o=p.ROOT,p.OUT
def vectors():
 def value(v):
  if v==g.DISPLAY:return 0xABC00001
  if g.NODES<=v<g.NODES+0x300 and(v-g.NODES)%256==0:return 0xABC00100+(v-g.NODES)//256
  if g.NEW<=v<g.NEW+0x400 and(v-g.NEW)%256==0:return 0xABC00200+(v-g.NEW)//256
  return v&0xFFFFFFFF
 rows=[];excluded=0
 for c in g.cases():
  initial=g.fixture(c);expected,calls,answer,defined=g.reference(initial,c)
  if not(c.null or c.gate)and not defined:excluded+=1;continue
  params=[c.seed,c.null,c.gate,c.asset,c.mode,c.separate,c.double,c.field12,c.field13,c.hits,c.failure,c.head,c.token,c.tiles,c.delta,c.index,c.mutation]
  wanted=[value(answer),g.read(expected,g.S['D_800E08F0'])]
  for at in[g.NODES+k*256 for k in range(3)]+[g.NEW+k*256 for k in range(4)]:wanted.extend([g.read(expected,at+8,2),*[expected[at+i]for i in(0x12,0x13,0x14,0x15)]])
  events=[]
  for target,a in calls:events.append('{'+str(g.ROLES.index(next(n for n in g.ROLES if g.S[n]==target)))+'u,{'+','.join(str(value(v))+'u'for v in a)+'}}')
  assert len(events)<=13
  rows.append('{'+','.join(str(v&0xFFFFFFFF)+'u'for v in params+wanted[:2])+',{'+','.join(str(v&0xFFFFFFFF)+'u'for v in wanted[2:])+'},'+str(len(events))+'u,{'+','.join(events or['{0u,{0u,0u,0u,0u}}'])+'}}')
 (o/'native-vectors.h').write_text('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n');return len(rows),excluded
def program():
 body=(o/'selected-final/body.c').read_text().replace('func_15195DD4(','subject(')
 typedef=p.MANIFEST['selected_source'];typedef=typedef[typedef.index('typedef struct {'):typedef.index('} PackedLayoutRecord15195984;')+len('} PackedLayoutRecord15195984;')]
 src='#include <ultra64.h>\n'+typedef+r'''
typedef struct {s32 previous;u8 *next;s16 key;u8 rest[246];} Node;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Node)==256&&__builtin_offsetof(Node,key)==8,"SDK32 typed links and keys");
typedef struct {u32 role,arg[4];} Event;
typedef struct {u32 seed,null,gate,asset,mode,separate,doubleSize,field12,field13,hits,failure,head,token,tiles,delta,index,mutation;u32 result,wantToken,fields[35],calls;Event events[13];} Vector;
#include "native-vectors.h"
static Node nodes[3],created[4],wantNodes[3],wantCreated[4];
static s32 display[65550],wantDisplay[65550];
static const Vector *current;static u32 step,count,overflow;static Event events[16];
u8 D_800BEAC0;s32 D_800E08E8,D_800E08F0;
static void copy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void *a,const void *b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 normalized(u32 v){u32 i;if(v==(u32)display)return 0xabc00001;for(i=0;i<3;i++)if(v==(u32)&nodes[i])return 0xabc00100+i;for(i=0;i<4;i++)if(v==(u32)&created[i])return 0xabc00200+i;return v;}
static void event(u32 role,u32 a,u32 b,u32 c,u32 d){Event *e;if(count==16){overflow=1;return;}e=&events[count++];e->role=role;e->arg[0]=normalized(a);e->arg[1]=normalized(b);e->arg[2]=normalized(c);e->arg[3]=normalized(d);}
__attribute__((noinline,noclone)) s32 func_15195868(u8 *dl,s32 asset,s32 occurrence,s32 *tile){u32 i,k=step++;event(0,(u32)dl,asset,occurrence,0xabc00010);*tile=(s32)(current->tiles+k*current->delta);if(current->mutation&1)D_800E08F0=(s32)(current->token+k+1);if(current->mutation&2)for(i=0;i<3;i++)((u8*)&nodes[i])[0x14]=(u8)(current->seed+k*61+i);return k<current->hits?(s32)(current->index+k):-1;}
__attribute__((noinline,noclone)) PackedLayoutRecord15195984 *func_15195984(s32 key,s32 size,s32 scale,s32 doubleSize){u32 k=step-1;event(1,key,size,scale,doubleSize);if(k==current->failure)return 0;created[k].key=(s16)key;((u8*)&created[k])[0x14]=1;return(PackedLayoutRecord15195984*)&created[k];}
__attribute__((noinline,noclone)) s32 func_15195A84(s16 index,s32 record,s32 size,s32 doubleSize){event(2,index,record,size,doubleSize);return index;}
__attribute__((noinline,noclone)) void func_15195D00(u8 *record,s32 dl,s32 index,s32 tiles){event(3,(u32)record,dl,index,tiles);if(current->mutation&1)D_800E08F0=(s32)((u32)D_800E08F0+7);record[0x15]=(u8)(step-1+0x5a);}
'''+body+r'''
static int run(void){u32 i,j,k,n;Node *node;const Vector *v;
 for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
  current=v=&vectors[k];step=count=overflow=0;D_800BEAC0=v->gate;D_800E08F0=(s32)v->token;
  for(i=0;i<sizeof(nodes);i++)((u8*)nodes)[i]=(u8)((32+i)*29+v->seed*11+0x51);
  for(i=0;i<sizeof(created);i++)((u8*)created)[i]=(u8)((32+i)*29+v->seed*11+0x51);
  for(i=0;i<4;i++)display[(v->index+i)*2]=(s32)(0xf2000000u+i*0x101+v->seed),display[(v->index+i)*2+1]=(s32)(0x12345678u+i*0x102+v->seed);
  for(i=0;i<3;i++){nodes[i].next=i<2?(u8*)&nodes[i+1]:0;nodes[i].key=(s16)(i==0?-1:i==1?4:9);((u8*)&nodes[i])[0x14]=(u8)(v->seed*7+i*31);}
  if(v->head==4){nodes[0].key=123;nodes[1].key=-7;}
  for(i=0;i<4;i++){u32 a=(32+i*256+8)*29+v->seed*11+0x51;created[i].key=(s16)(((a&255)<<8)|((a+29)&255));}
  D_800E08E8=(s32)(v->head==0?0:v->head==2?&nodes[1]:v->head==3?&nodes[2]:&nodes[0]);
  copy(wantNodes,nodes,sizeof(nodes));copy(wantCreated,created,sizeof(created));copy(wantDisplay,display,sizeof(display));
  for(i=0;i<7;i++){node=i<3?&wantNodes[i]:&wantCreated[i-3];node->key=(s16)v->fields[i*5];for(j=0;j<4;j++)((u8*)node)[0x12+j]=(u8)v->fields[i*5+j+1];}
  n=(u32)subject(v->null?0:(s32)display,(s32)v->asset,(s32)v->doubleSize,(s32)v->mode,(s32)v->separate,(s32)v->field12,(s32)v->field13);
  if(normalized(n)!=v->result||D_800E08F0!=(s32)v->wantToken||overflow||count!=v->calls)return 1;
  if(!equal(nodes,wantNodes,sizeof(nodes))||!equal(created,wantCreated,sizeof(created))||!equal(display,wantDisplay,sizeof(display)))return 1;
  for(i=0;i<count;i++){if(events[i].role!=v->events[i].role)return 1;for(j=0;j<4;j++)if(events[i].arg[j]!=v->events[i].arg[j])return 1;}
 }
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 cases,excluded=vectors();src,body=program();profiles={}
 def run(text,label,opt):
  f=o/(label+'.c');f.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1','-Wno-error=uninitialized','-Wno-error=maybe-uninitialized',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-5000:];return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=cases,SDK32=True,UBSan=True,strict_aliasing=True,typed_link_and_key_objects=True)
 changes={
 'wrong-gate':body.replace('D_800BEAC0 != 0','D_800BEAC0 == 1'),
 'single-occurrence-only':body.replace('while (occurrence == -1)','while (0)'),
 'unsigned-record-key':body.replace('*(s16 *)(record + 8)','*(u16 *)(record + 8)'),
 'wrong-separate-key':body.replace('key = separate ? -1 : assetId;','key = separate ? 0 : assetId;'),
 'narrowed-command-index':body.replace('func_15195A84(index,','func_15195A84((u8)index,'),
 'wrong-field13':body.replace('record[0x13] = field13;','record[0x13] = field13 ^ 1;'),
 'wrong-tile-comparison':body.replace('record[0x14] < tileCount','record[0x14] > tileCount'),
 'wrong-token-direction':body.replace('D_800E08F0--;','D_800E08F0++;')}
 effective=[]
 for label,changed in changes.items():
  assert changed!=body;q=run(src.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 report=dict(profiles=profiles,effective_output_comparison_controls=effective,excluded_first_miss_uninitialized_C_cases=excluded,vectors_sha256=hashlib.sha256((o/'native-vectors.h').read_bytes()).hexdigest(),source_installed=p.installed(),matching_credit=0,limits='Actual C on typed ordinary native objects. First-search misses returning an uninitialized C value are excluded; emitted guest behavior is separately measured. Helpers are ABI providers, not full helper or gameplay qualification.');(o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
