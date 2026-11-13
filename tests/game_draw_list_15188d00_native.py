def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_draw_list_15188d00_match as packet
 root=packet.ROOT
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet.OUT
 text=packet.MANIFEST['selected_source'];start=text.index('Gfx *func_15188D00(');end=text.index('\n}',start)+2
 fn=text[start:end]
 controls={
  'setmode':('0x00200004','0x00200005'),
  'clearmode':('0x00110000','0x00100000'),
  'convert':('0, 0, 0, 0, 0, 255','0, 0, 0, 0, 0, 254'),
  'type':('node->active','node->kind'),
  'view':('(commands, node, view)','(commands, node, 0)'),
  'next':('node = node->next;','node = NULL;'),
 }
 pre='''#include <ultra64.h>
 typedef struct ListNode15188A58 ListNode15188A58;
 struct ListNode15188A58 {u8 active,kind,cleared,recordSize;u8 mode,retained05;s16 timer;u8 *buffer;ListNode15188A58 *next;s32 key;};
 static u8 *heads[4];
 #define D_800DF7C8 heads[1]
 extern Mtx D_80089470;
 typedef Gfx *(*ListDraw15188D00)(Gfx *, ListNode15188A58 *, s16);
 extern ListDraw15188D00 D_8008D590[];
 '''
 code=pre+fn.replace('func_15188D00(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert fn.count(old)==1,name
  code+=fn.replace('func_15188D00(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 Mtx D_80089470;
 static ListNode15188A58 nodes[3];
 static u32 call_node[4],call_view[4],call_kind[4],call_count,mutation,node_length;
 static Gfx *draw0(Gfx *g,ListNode15188A58 *n,s16 v){
  u32 k=call_count++;call_node[k]=(u32)n;call_view[k]=(s32)v;call_kind[k]=0;
  if(k==0&&mutation==1)n->next=node_length>=3?&nodes[2]:0;
  if(k==0&&mutation==2)n->next=0;
  g->words.w0=0xA1000000|call_count;g->words.w1=(u32)n;return g+1;
 }
 static Gfx *draw1(Gfx *g,ListNode15188A58 *n,s16 v){
  u32 k=call_count++;call_node[k]=(u32)n;call_view[k]=(s32)v;call_kind[k]=1;
  if(k==0&&mutation==1)n->next=node_length>=3?&nodes[2]:0;
  if(k==0&&mutation==2)n->next=0;
  g->words.w0=0xA1000000|call_count;g->words.w1=(u32)n;return g+1;
 }
 ListDraw15188D00 D_8008D590[]={draw0,draw1};
 typedef Gfx *(*Fn)(Gfx *,s32,s16);
 static int check(Fn fn) {
  static const u16 views[]={0,1,0x7fff,0x8000,0xffff};
  for(int which=0;which<2;which++)for(int v=0;v<5;v++)for(int length=0;length<4;length++)for(int pattern=0;pattern<2;pattern++)for(int mut=0;mut<3;mut++){
   Gfx output[24];u32 expected_nodes[3],expected_kind[3],count=0;
   for(int i=0;i<24;i++){output[i].words.w0=0xdeadbeef;output[i].words.w1=0xcafebabe;}
   for(int i=0;i<3;i++){nodes[i].active=(i+pattern)&1;nodes[i].kind=nodes[i].active^1;nodes[i].next=i+1<length?&nodes[i+1]:0;}
   heads[1+which]=length?(u8 *)&nodes[0]:0;mutation=mut;node_length=length;call_count=0;
   int ix=0;while(ix<length){expected_nodes[count]=(u32)&nodes[ix];expected_kind[count]=(ix+pattern)&1;count++;if(count==1&&mut==1)ix=2;else if(count==1&&mut==2)break;else ix++;}
   Gfx *end=fn(output,which,(s16)views[v]);u32 position=length?6+count:0;
   if(end!=output+position || call_count!=count)return 1;
   for(u32 i=0;i<count;i++)if(call_node[i]!=expected_nodes[i]||call_view[i]!=(u32)(s32)(s16)views[v]||call_kind[i]!=expected_kind[i])return 2;
   if(length){
    static const u32 a[]={0xDA380003,0xD9FFFFFF,0xD9EEFFFF,0xE7000000,0xE2001E01,0xEC000000};
    u32 b[]={(u32)&D_80089470,0x00200004,0,0,0,255};
    for(int i=0;i<6;i++)if(output[i].words.w0!=a[i]||output[i].words.w1!=b[i])return 3;
    for(u32 i=0;i<count;i++)if(output[6+i].words.w0!=(0xA1000001+i)||output[6+i].words.w1!=expected_nodes[i])return 4;
   }
   if(output[position].words.w0!=0xdeadbeef || output[position].words.w1!=0xcafebabe)return 5;
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'240 draw-list cases,',len(controls),'effective negative controls, UBSan',flush=True)
