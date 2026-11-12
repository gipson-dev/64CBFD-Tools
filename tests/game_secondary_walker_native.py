import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_secondary_walker_match as match
from tools.tests import game_type64_walker_oracle as g
out=match.OUT;root=match.ROOT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 selected=match.MANIFEST['body']
 controls={
  'row_count':('row < 2','row < 1'),
  'column_count':('column < 101','column < 100'),
  'row_stride':('row * 0x1A0','0 * 0x1A0'),
  'saved_next':('D_800DD198[D_800DD190] = *(void **)((u8 *)node + 8)','D_800DD198[D_800DD190] = NULL'),
  'next_reload':('node = D_800DD198[D_800DD190]','node = NULL'),
 }
 def ident(v):
  if v==0:return 0
  return g.NODES.index(v)+1
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct struct102 {u32 a,b;struct struct102 *next;u32 d;} struct102;
 typedef struct {void (*unk0)(struct102 *);void (*unk4)(u8 *);u8 pad[44];} struct115;
 _Static_assert(sizeof(struct115)==52 && __builtin_offsetof(struct102,next)==8,"record layout");
 struct115 D_8008B4A8[101];u8 D_800DCE50[0x340] __attribute__((aligned(4)));s8 D_800DD190;void *D_800DD198[6];
 static struct102 nodes[6];
 struct Event {u32 target,node,next;};
 struct Case {u32 pattern,mutation,depth,count;struct Event events[6];u32 slots[6],next[6],table[3];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,calls=g.reference(c);ev=[(1+g.CALLBACKS.index(target),g.NODES.index(node)+1,ident(nxt)) for target,node,nxt in calls]
  ev=ev+[(0,0,0)]*(6-len(ev))
  slots=[ident(g.read(m,g.SLOTS+i*4)) for i in range(6)]
  nexts=[ident(g.read(m,n+8)) for n in g.NODES]
  table=[0 if not g.read(m,g.TABLE+i*52+4) else 1+g.CALLBACKS.index(g.read(m,g.TABLE+i*52+4)) for i in (0,50,100)]
  code+='{%d,%d,%d,%d,{'%(c.pattern,c.mutation,c.depth,len(calls))+','.join('{%d,%d,%d}'%e for e in ev)+'},{'+','.join(map(str,slots))+'},{'+','.join(map(str,nexts))+'},{'+','.join(map(str,table))+'}},\n'
 code+=r'''};
 static const struct Case *current;static u32 count,bad;
 static u32 id(void *p){u32 i;if(!p)return 0;for(i=0;i<6;i++)if(p==&nodes[i])return i+1;bad=1;return 0;}
 static void callback2(u8 *p);
 static void act(struct102 *p,u32 target){u32 n=id(p),column;if(!n){bad=1;return;}column=n<=2?0:n<=4?50:100;
  if(count>=6){bad=1;return;}if(current->events[count].target!=target||current->events[count].node!=n||current->events[count].next!=id(D_800DD198[(u8)D_800DD190]))bad=1;count++;
  if(current->mutation&1)p->next=0;
  if((current->mutation&2)&&(n&1))D_800DD198[(u8)D_800DD190]=0;
  if(current->mutation==3)D_8008B4A8[column].unk4=callback2;
 }
 static void callback1(u8 *p){act((struct102 *)p,1);}static void callback2(u8 *p){act((struct102 *)p,2);}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace('func_151671E8','test_'+name,1)+'\n'
 code+=r'''
 typedef void(*T)(void);
 static int check(T test){u32 i,j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  const struct Case *c=&cases[i];current=c;count=bad=0;
  for(j=0;j<101;j++)D_8008B4A8[j].unk4=0;
  for(j=0;j<sizeof(D_800DCE50);j++)D_800DCE50[j]=0;
  for(j=0;j<6;j++){nodes[j].next=0;D_800DD198[j]=0;}
  D_800DD190=(s8)c->depth;
  if(c->pattern==1)D_8008B4A8[50].unk4=callback1;
  if(c->pattern>=2){D_8008B4A8[0].unk4=callback1;D_8008B4A8[50].unk4=callback1;D_8008B4A8[100].unk4=callback1;
  *(struct102 **)(D_800DCE50)=&nodes[0];*(struct102 **)(D_800DCE50+50*4)=&nodes[2];*(struct102 **)(D_800DCE50+0x1a0+100*4)=&nodes[4];
  if(c->pattern==3){nodes[0].next=&nodes[1];nodes[2].next=&nodes[3];nodes[4].next=&nodes[5];}}
  test();if(bad||count!=c->count||(u8)D_800DD190!=c->depth)return 1;
  for(j=0;j<6;j++)if(id(D_800DD198[j])!=c->slots[j]||id(nodes[j].next)!=c->next[j])return 2;
  for(j=0;j<3;j++){u32 ix=j==0?0:j==1?50:100;void(*f)(u8 *)=D_8008B4A8[ix].unk4;u32 v=!f?0:f==callback1?1:f==callback2?2:3;if(v!=c->table[j])return 3;}
  }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_u8_151671E8_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_u8_151671E8_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-4000:],r.stderr[-4000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,callbacks='modeled',valid_iterator_depth_only=True,source_installed=False)
 (out/'native_u8_151671E8_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report


if __name__ == "__main__": main()
