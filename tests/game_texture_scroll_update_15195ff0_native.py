"""SDK32 typed record/list backing, independent phase and command vectors."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_texture_scroll_update_15195ff0_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_texture_scroll_update_15195ff0_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def vectors():
 rows=[];params=('seed','count','gate','delta','width','height','u','v','speed_u','speed_v','tiles','primary','secondary','links');largest=0
 for c in g.cases():
  initial=g.fixture(c);expected=g.reference(initial,c);changes=[]
  for base,n in((g.DL0,0),(g.DL1,1),(g.DL2,2)):
   for a in sorted(a for a in initial if base<=a<base+4096 and a%4==0):
    if g.read(initial,a)!=g.read(expected,a):changes.append((n,(a-base)//4,g.read(expected,a)))
  largest=max(largest,len(changes));fields=[g.read(expected,g.NODES+256*i+off,2)for i in range(3)for off in(0xE,0x10)]
  rows.append('{'+','.join(str(getattr(c,k)&0xFFFFFFFF)+'u'for k in params)+',{'+','.join(str(v)+'u'for v in fields)+'},'+str(len(changes))+'u,{'+','.join('{%du,%du,%du}'%x for x in changes)+'}}')
 assert largest<=312
 (o/'native-vectors.h').write_text('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n');return len(rows),largest
def program():
 body=p.MANIFEST['body'].replace('func_15195FF0(','subject(')
 src='#include <ultra64.h>\n'+r'''
typedef struct Association Association;
typedef struct Node {s32 previous;u8 *next;s16 key,width,height;u16 u,v;s8 speedU,speedV;u8 maxTile,gap[3],*links;s16 primary[5],secondary[5];u8 primaryTiles[5],secondaryTiles[5],tail[198];} Node;
struct Association {u8 reserved[8];s32 list;u16 index;u8 count,pad;u8 *next;u8 tail[12];};
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Node)==256&&sizeof(Association)==32&&__builtin_offsetof(Node,u)==0xe&&__builtin_offsetof(Node,links)==0x18&&__builtin_offsetof(Node,primary)==0x1c&&__builtin_offsetof(Node,secondary)==0x26&&__builtin_offsetof(Node,primaryTiles)==0x30&&__builtin_offsetof(Node,secondaryTiles)==0x35&&__builtin_offsetof(Association,next)==0x10,"SDK32 texture record/list layout");
typedef struct {u32 list,index,value;} Patch;
typedef struct {u32 seed,count,gate,delta,width,height,u,v,speedU,speedV,tiles,primary,secondary,links,want[6],patches;Patch patch[312];} Vector;
#include "native-vectors.h"
static Node nodes[3],wantNodes[3];static Association links[9],wantLinks[9];
static u32 lists[3][1024],wantLists[3][1024];
s32 D_800E08E8,D_800BE9E4;u8 D_800BEAC0;
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
'''+body+r'''
static int run(void){u32 k,i,j,b,a,index,byte,value;Node*n;Association*l;const Vector*v;
 for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
  v=&vectors[k];D_800E08E8=v->count?(s32)nodes:0;D_800BE9E4=(s32)v->delta;D_800BEAC0=(u8)v->gate;
  for(i=0;i<sizeof(nodes);i++)((u8*)nodes)[i]=(u8)(i*29+v->seed*11+0x51);
  for(i=0;i<sizeof(links);i++)((u8*)links)[i]=(u8)(i*29+v->seed*11+0x51);
  for(i=0;i<3;i++){
   n=&nodes[i];n->next=i+1<v->count?(u8*)&nodes[i+1]:0;n->width=(s16)v->width;n->height=(s16)v->height;n->u=(u16)v->u;n->v=(u16)v->v;n->speedU=(s8)v->speedU;n->speedV=(s8)v->speedV;n->maxTile=(u8)v->tiles;n->links=v->links?(u8*)&links[i*3]:0;
   for(j=0;j<5;j++){index=2+j*24+i*160;n->primary[j]=(s16)(j<v->primary?index:0xffffffffu);n->secondary[j]=(s16)(j<v->secondary?index:0xffffffffu);n->primaryTiles[j]=(u8)((j+v->seed)%3?(v->tiles<8?v->tiles:8):0);n->secondaryTiles[j]=(u8)((j+v->seed)%4?(v->tiles<8?v->tiles:8):0);}
   for(j=0;j<3;j++){l=&links[i*3+j];l->list=(s32)lists[2];l->index=(u16)(3+j*32+i*192);l->count=(u8)(j!=1?(v->tiles<8?v->tiles:8):0);l->next=j+1<v->links?(u8*)&links[i*3+j+1]:0;}
   for(a=0;a<1024;a++){value=0;for(b=0;b<4;b++){byte=a*4+b;value=(value<<8)|((byte*13+v->seed*19+0xa3)&255);}lists[i][a]=value;}
  }
  copy(wantNodes,nodes,sizeof(nodes));copy(wantLinks,links,sizeof(links));copy(wantLists,lists,sizeof(lists));
  for(i=0;i<3;i++){wantNodes[i].u=(u16)v->want[2*i];wantNodes[i].v=(u16)v->want[2*i+1];}
  for(i=0;i<v->patches;i++)wantLists[v->patch[i].list][v->patch[i].index]=v->patch[i].value;
  subject((s32)lists[0],(s32)lists[1]);
  if(D_800E08E8!=(v->count?(s32)nodes:0)||D_800BE9E4!=(s32)v->delta||D_800BEAC0!=(u8)v->gate||!equal(nodes,wantNodes,sizeof(nodes))||!equal(links,wantLinks,sizeof(links))||!equal(lists,wantLists,sizeof(lists)))return 1;
 }
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 count,largest=vectors();src,body=program();profiles={}
 def run(text,label,opt):
  f=o/(label+'.c');f.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-4000:];return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True)
 controls={'phase-source':body.replace('u = *(u16 *)(record + 0x0E);','u = *(u16 *)(record + 0x10);'),'wrong-gate':body.replace('D_800BEAC0 == 0','D_800BEAC0 != 0'),'unsigned-speed':body.replace('*(s8 *)(record + 0x12)','*(u8 *)(record + 0x12)'),'tile-limit':body.replace('level < 8','level < 7'),'tile-mask':body.replace('0xFFF','0x7FF'),'slot-limit':body.replace('slot < 10','slot < 8'),'command-stride':body.replace('output += 4;','output += 2;'),'wrong-list':body.replace('(u32 *)secondaryList','(u32 *)primaryList'),'single-wrap':body.replace('(u32)u - (u32)width','(u32)u - (u32)width * 2')};effective=[]
 for label,changed in controls.items():
  assert changed!=body;q=run(src.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1 and not q.stderr,(label,q.returncode,q.stderr);effective.append(label)
 q=dict(profiles=profiles,max_changed_commands=largest,effective_comparison_controls=effective,source_installed=p.installed(),matching_credit=0,limits='Separate valid SDK32 typed records, association chains and display-list arrays; counts never exceed generated scratch words. Guest-only aliases/private-stack behavior are separate gates.');(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
