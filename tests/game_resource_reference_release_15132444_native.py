import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_resource_reference_release_15132444_match as p
out=p.out;root=p.root
from tools.tests import game_resource_reference_release_15132444_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_15132444')
 controls={
  'global_count':('((u32)D_800DC63C - 1)','((u32)D_800DC63C - 2)'),
  'ref_decrement':('D_800DC468[owner->resourceId]--','D_800DC468[owner->resourceId]++'),
  'ref_gate':('D_800DC468[owner->resourceId] == 0','D_800DC468[owner->resourceId] == 1'),
  'retained_gate':('node->retained != 0','node->retained == 0'),
  'retained_reset':('D_800DC468[owner->resourceId] = 1','D_800DC468[owner->resourceId] = 2'),
  'head':('D_800DC460 = next','D_800DC460 = node'),
  'tail':('D_800DC464 = node->previous','D_800DC464 = NULL'),
  'previous_link':('node->previous->next = node->next','node->previous->next = node'),
  'next_link':('node->next->previous = node->previous','node->next->previous = NULL'),
  'free_resource':('(s32 *)owner->resourceNode->resource','(s32 *)owner->resourceNode'),
  'cleanup':('func_151325C8(owner);','(void)owner;'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct ExtendedResource15F680 {void *data;} ExtendedResource15F680;
 typedef struct ExtendedResourceNode15F680 {ExtendedResource15F680 *resource;struct ExtendedResourceNode15F680 *next,*previous;u16 id;u8 retained,reserved0F;} ExtendedResourceNode15F680;
 typedef struct {u8 pad0[0x66];u16 resourceId;u8 pad68[0x24];ExtendedResourceNode15F680 *resourceNode;u8 pad90[0xC4];s32 entries[4];s32 trailing;} ResourceOwner15F680;
 _Static_assert(__builtin_offsetof(ResourceOwner15F680,resourceId)==0x66 && __builtin_offsetof(ResourceOwner15F680,resourceNode)==0x8c && __builtin_offsetof(ResourceOwner15F680,entries)==0x154 && __builtin_offsetof(ExtendedResourceNode15F680,retained)==0xe,"layout");
 struct Call {s32 kind,target,extra;};
 struct Case {s32 index,refs,retained,previous,following,mutate,expected_ref,head,tail,prev_next,next_prev,owner_node,ncalls;struct Call calls[4];};
 static const struct Case cases[]={
 '''
 tags={0:0,g.NODE:1,g.PREV:2,g.NEXT:3,g.RESOURCE:4,g.AUX:5,g.NODE2:6,g.OWNER:7};kinds={g.RELEASE_AUX:1,g.FREE:2,g.CLEANUP:3}
 for c in g.cases():
  m,calls=g.reference(c);ref=g.read(m,g.REFS+2*c.index,2);ref=(ref^0x8000)-0x8000
  vals=[c.index,c.refs,c.retained,c.previous,c.following,c.mutate,ref,tags[g.read(m,g.HEAD)],tags[g.read(m,g.TAIL)],tags[g.read(m,g.PREV+4)],tags[g.read(m,g.NEXT+8)],tags[g.read(m,g.OWNER+0x8c)],len(calls)]
  cv=[(kinds[k],tags[a[0]],a[1] if len(a)>1 else 0)for k,a in calls]+[(0,0,0)]*(4-len(calls))
  code+='{'+','.join(map(str,vals))+',{'+','.join('{'+','.join(map(str,v))+'}' for v in cv)+'}},\n'
 code+=r'''};
 s32 D_800DC63C,D_800DC640[234];s16 D_800DC468[234];ExtendedResourceNode15F680 *D_800DC460,*D_800DC464;
 static ResourceOwner15F680 *current_owner;static ExtendedResourceNode15F680 *current_node,*current_prev,*current_next,*current_node2;static ExtendedResource15F680 *current_resource;static s16 *current_aux;static const struct Case *current_case;static struct Call observed[4];static int calls,bad,free_count;
 static int tag(void*p){if(!p)return 0;if(p==current_node)return 1;if(p==current_prev)return 2;if(p==current_next)return 3;if(p==current_resource)return 4;if(p==current_aux)return 5;if(p==current_node2)return 6;if(p==current_owner)return 7;return -1;}
 static void event(int kind,void*p,int extra){if(calls>=4){bad=1;return;}observed[calls].kind=kind;observed[calls].target=tag(p);observed[calls].extra=extra;calls++;}
 void func_1510D630(s16*p){event(1,p,0);if(current_case->mutate)current_node->next=current_case->following?NULL:current_next;}
 void func_100043B4(s32*p,u32 mode){event(2,p,(int)mode);free_count++;if(free_count==1&&current_case->mutate)current_owner->resourceNode=current_node2;}
 void func_151325C8(ResourceOwner15F680*p){event(3,p,0);p->entries[0]=0x13579bdf;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_15132444','test_'+key,1)+'\n'
 code+=r'''
 typedef void(*T)(ResourceOwner15F680*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];ResourceOwner15F680 owner;ExtendedResourceNode15F680 node,previous,following,node2;ExtendedResource15F680 resource;s16 aux;u8 before[sizeof owner];u8*o=(u8*)&owner;
  for(i=0;i<sizeof owner;i++)o[i]=(i*13+11)&255;for(i=0;i<234;i++){D_800DC468[i]=20;D_800DC640[i]=0;}
  owner.resourceId=c->index;owner.resourceNode=&node;node.resource=&resource;node.next=c->following?&following:NULL;node.previous=c->previous?&previous:NULL;node.retained=c->retained;previous.next=&node;following.previous=&node;node2.resource=&resource;D_800DC460=c->previous?&previous:&node;D_800DC464=c->following?&following:&node;D_800DC63C=10;D_800DC468[c->index]=c->refs;D_800DC640[c->index]=(s32)&aux;
  for(i=0;i<sizeof owner;i++)before[i]=o[i];current_owner=&owner;current_node=&node;current_prev=&previous;current_next=&following;current_node2=&node2;current_resource=&resource;current_aux=&aux;current_case=c;calls=bad=free_count=0;test(&owner);
  if(bad||calls!=c->ncalls||D_800DC63C!=9||D_800DC468[c->index]!=c->expected_ref||tag(D_800DC460)!=c->head||tag(D_800DC464)!=c->tail||tag(previous.next)!=c->prev_next||tag(following.previous)!=c->next_prev||tag(owner.resourceNode)!=c->owner_node||owner.entries[0]!=0x13579bdf)return 1;
  for(i=0;i<(u32)calls;i++)if(observed[i].kind!=c->calls[i].kind||observed[i].target!=c->calls[i].target||observed[i].extra!=c->calls[i].extra)return 2;
  for(i=0;i<234;i++)if((i!=(u32)c->index&&D_800DC468[i]!=20)||(i!=(u32)c->index&&D_800DC640[i]!=0))return 3;
  if(D_800DC640[c->index]!=(s32)&aux)return 4;
  for(i=0;i<sizeof owner;i++)if((i<0x8c||i>=0x90)&&(i<0x154||i>=0x158)&&o[i]!=before[i])return 5;
  }return 0;}
 static int run(void){int selected_result=check(test_selected);if(selected_result)return selected_result;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_15132444_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_15132444_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers='modeled',valid_disjoint_resource_storage=True,source_installed=False);(out/'native_15132444_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
