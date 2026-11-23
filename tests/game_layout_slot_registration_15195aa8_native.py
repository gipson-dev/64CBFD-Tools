"""Typed SDK32 five-slot record arrays and independent guest vectors."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_layout_slot_registration_15195aa8_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_layout_slot_registration_15195aa8_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def vectors():
 rows=[]
 def value(v):
  if v==g.DISPLAY:return 0xABC00001
  if g.NODES<=v<g.NODES+768 and(v-g.NODES)%256==0:return 0xABC00100+(v-g.NODES)//256
  if g.NEW<=v<g.NEW+1024 and(v-g.NEW)%256==0:return 0xABC00200+(v-g.NEW)//256
  return v&0xffffffff
 for c in g.cases():
  initial=g.fixture(c);expected,calls,answer,_=g.reference(initial,c);params=[c.seed,c.null,c.gate,c.asset,c.mode,c.state,c.secondary,c.double,c.field12,c.field13,c.hits,c.failure,c.head,c.token,c.tiles,c.delta,c.index,c.mutation,c.fullness];fields=[]
  for base in[g.NODES+i*256 for i in range(3)]+[g.NEW+i*256 for i in range(4)]:
   fields.extend([g.read(expected,base+8,2),*[expected[base+i]for i in(0x12,0x13,0x14)],*[g.read(expected,base+offset+2*i,2)for offset in(0x1C,0x26)for i in range(5)],*[expected[base+offset+i]for offset in(0x30,0x35)for i in range(5)]])
  assert len(fields)==168;events=['{'+str(g.ROLES.index(next(n for n in g.ROLES if g.S[n]==t)))+'u,{'+','.join(str(value(v))+'u'for v in a)+'}}'for t,a in calls]
  rows.append('{'+','.join(str(v&0xffffffff)+'u'for v in params+[value(answer),g.read(expected,g.S['D_800E08F0'])])+',{'+','.join(str(v)+'u'for v in fields)+'},'+str(len(events))+'u,{'+','.join(events or['{0u,{0u,0u,0u,0u}}'])+'}}')
 (o/'native-vectors.h').write_text('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n');return len(rows)
def program():
 body=p.MANIFEST['body'].replace('func_15195AA8(','subject(')
 src='#include <ultra64.h>\n'+r'''
typedef struct {s32 previous;u8 *next;s16 key;u8 reserved[8],field12,field13,maxTile,gap[7];s16 primary[5],secondary[5];u8 primaryTiles[5],secondaryTiles[5],tail[198];} Node;
typedef Node PackedLayoutRecord15195984;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Node)==256&&__builtin_offsetof(Node,primary)==0x1c&&__builtin_offsetof(Node,secondary)==0x26&&__builtin_offsetof(Node,primaryTiles)==0x30&&__builtin_offsetof(Node,secondaryTiles)==0x35,"SDK32 typed five-slot records");
typedef struct {u32 role,arg[4];} Event;
typedef struct {u32 seed,null,gate,asset,mode,state,secondary,doubleSize,field12,field13,hits,failure,head,token,tiles,delta,index,mutation,fullness,result,wantToken,fields[168],calls;Event events[8];} Vector;
#include "native-vectors.h"
static Node nodes[3],created[4],wantNodes[3],wantCreated[4];static s32 display[65550],wantDisplay[65550];
static const Vector *current;static u32 step,count,overflow;static Event events[8];
s32 D_800E08E8,D_800E08F0;u8 D_800BEAC0;
static void copy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void *a,const void *b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 normalized(u32 v){u32 i;if(v==(u32)display)return 0xabc00001;for(i=0;i<3;i++)if(v==(u32)&nodes[i])return 0xabc00100+i;for(i=0;i<4;i++)if(v==(u32)&created[i])return 0xabc00200+i;return v;}
static void event(u32 role,u32 a,u32 b,u32 c,u32 d){Event *e;if(count==8){overflow=1;return;}e=&events[count++];e->role=role;e->arg[0]=normalized(a);e->arg[1]=normalized(b);e->arg[2]=normalized(c);e->arg[3]=normalized(d);}
__attribute__((noinline,noclone)) s32 func_15195868(u8 *dl,s32 asset,s32 occurrence,s32 *tile){u32 i,k=step++;event(0,(u32)dl,asset,occurrence,0xabc00010);*tile=(s32)(current->tiles+k*current->delta);if(current->mutation&1)D_800E08F0=(s32)(current->token+k+1);if(current->mutation&2)for(i=0;i<3;i++)nodes[i].maxTile=(u8)(current->seed+k*61+i);return k<current->hits?(s32)(current->index+k):-1;}
__attribute__((noinline,noclone)) PackedLayoutRecord15195984 *func_15195984(s32 key,s32 size,s32 scale,s32 doubleSize){u32 k=step-1;event(1,key,size,scale,doubleSize);if(k==current->failure)return 0;created[k].key=(s16)key;created[k].maxTile=1;return &created[k];}
__attribute__((noinline,noclone)) s32 func_15195A84(s16 index,s32 record,s32 size,s32 doubleSize){event(2,index,record,size,doubleSize);if(current->mutation&1)D_800E08F0=(s32)((u32)D_800E08F0+7);return index;}
'''+body+r'''
static int run(void){u32 i,j,k,x,n;Node *node;const Vector *v;
 for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
  current=v=&vectors[k];step=count=overflow=0;D_800E08F0=(s32)v->token;D_800BEAC0=(u8)v->gate;
  for(i=0;i<sizeof(nodes);i++)((u8*)nodes)[i]=(u8)((32+i)*29+v->seed*11+0x51);
  for(i=0;i<sizeof(created);i++)((u8*)created)[i]=(u8)((32+i)*29+v->seed*11+0x51);
  for(i=0;i<4;i++)display[(v->index+i)*2]=(s32)(0xf2000000u+i*0x101+v->seed),display[(v->index+i)*2+1]=(s32)(0x12345678u+i*0x102+v->seed);
  for(i=0;i<3;i++){nodes[i].next=i<2?(u8*)&nodes[i+1]:0;nodes[i].key=(s16)(v->head==4?7+i:i==1?0:i==0?7:9);nodes[i].maxTile=(u8)(v->seed*7+i*31);}
  for(i=0;i<4;i++){u32 a=(32+i*256+8)*29+v->seed*11+0x51;created[i].key=(s16)(((a&255)<<8)|((a+29)&255));}
  for(i=0;i<7;i++){node=i<3?&nodes[i]:&created[i-3];for(j=0;j<5;j++)node->primary[j]=node->secondary[j]=(s16)(j<v->fullness?7+j:0xffffffffu);}
  D_800E08E8=(s32)(v->head==0?0:v->head==2?&nodes[1]:v->head==3?&nodes[2]:&nodes[0]);
  copy(wantNodes,nodes,sizeof(nodes));copy(wantCreated,created,sizeof(created));copy(wantDisplay,display,sizeof(display));
  for(i=0;i<7;i++){node=i<3?&wantNodes[i]:&wantCreated[i-3];x=24*i;node->key=(s16)v->fields[x++];node->field12=(u8)v->fields[x++];node->field13=(u8)v->fields[x++];node->maxTile=(u8)v->fields[x++];for(j=0;j<5;j++)node->primary[j]=(s16)v->fields[x++];for(j=0;j<5;j++)node->secondary[j]=(s16)v->fields[x++];for(j=0;j<5;j++)node->primaryTiles[j]=(u8)v->fields[x++];for(j=0;j<5;j++)node->secondaryTiles[j]=(u8)v->fields[x++];}
  n=(u32)subject(v->null?0:(s32)display,(s32)v->asset,(s32)v->doubleSize,(s32)v->mode,(s32)v->state,(s32)v->secondary,(s32)v->field12,(s32)v->field13);
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
 count=vectors();src,body=program();profiles={}
 def run(text,label,opt):
  f=o/(label+'.c');f.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-4000:];return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True)
 changes={'wrong-list-key':body.replace('*(s16 *)(record + 8) != 0','*(s16 *)(record + 8) != assetId'),'wrong-array':body.replace('record + 0x1C','record + 0x26'),'wrong-slot-limit':body.replace('slot < 5','slot < 4'),'wrong-state-reset':body.replace('state = 0;','state = 1;'),'wrong-field13':body.replace('record[0x13] = field13;','record[0x13] = field13 ^ 1;'),'wrong-tile-comparison':body.replace('record[0x14] < tileCount','record[0x14] > tileCount'),'wrong-token-direction':body.replace('D_800E08F0--;','D_800E08F0++;'),'unsigned-command-index':body.replace('func_15195A84(index,','func_15195A84((u8)index,')};effective=[]
 for label,changed in changes.items():
  assert changed!=body;q=run(src.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 q=dict(profiles=profiles,effective_comparison_controls=effective,source_installed=p.installed(),matching_credit=0,limits='Valid native typed nodes and five-slot arrays. MIPS incoming argument-home writeback is an ABI effect, qualified separately in the guest; no private-frame alias or gameplay claim.');(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
