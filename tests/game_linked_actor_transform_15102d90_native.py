import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_linked_actor_transform_15102d90_match as p
out=p.out;root=p.root
from tools.tests import game_linked_actor_transform_15102d90_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_15102D90')
 controls={
  'identity':('owner->identity != actor->unique_id','owner->identity == actor->unique_id'),
  'active':('actor->interaction_state == 0','actor->interaction_state != 0'),
  'mode':('(actor->unk74 & 0xF) == 0xF','(actor->unk74 & 0xF) == 0xE'),
  'clear_flag':('owner->flags &= ~1','owner->flags &= ~2'),
  'set_flag':('owner->flags |= 1','owner->flags |= 2'),
  'descriptor_branch':('owner->descriptorId != -1','owner->descriptorId == -1'),
  'find_failure':('descriptor == 0','descriptor != 0'),
  'transform_failure':('!func_1514654C','func_1514654C'),
  'matrix_offset':('actor->unk1D4 + owner->matrixOffset','actor->unk1D4 + owner->matrixOffset + 4'),
 }
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad00[0x34];struct17 input[2];u8 pad4C[0xC4];struct127 *actor;u8 identity;u8 pad115[3];s32 matrixOffset;s16 descriptorId;u8 pad11E[2];s32 descriptorIndex;u8 flags;u8 pad125[3];struct17 output[2];} LinkOwner15102D90;
 _Static_assert(__builtin_offsetof(struct127,unk1D4)==0x1d4 && __builtin_offsetof(LinkOwner15102D90,actor)==0x110 && __builtin_offsetof(LinkOwner15102D90,output)==0x128,"layout");
 struct Case {s32 identity,actor_identity,active,matrix,mode,descriptor,found,ok,mutate,initflags,answer,flags;u32 index;s32 calls;u32 output[6];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,calls,answer=g.reference(c);index=g.read(m,g.OWNER+0x120);values=[c.identity,c.actor_identity,c.active,c.matrix,c.mode,c.descriptor,c.found,c.ok,c.mutate,c.flags,answer,m[g.OWNER+0x124],index,len(calls)];output=[g.read(m,g.OWNER+0x128+4*i)for i in range(6)]
  code+='{'+','.join(str(v) if i!=12 else '0x%Xu'%v for i,v in enumerate(values))+',{'+','.join('0x%Xu'%v for v in output)+'}},\n'
 initial=g.fixture(g.cases()[0]);ins=[g.read(initial,g.OWNER+0x34+4*i)for i in range(6)];outs=[g.read(initial,g.OWNER+0x128+4*i)for i in range(6)]
 code+='};\nstatic const u32 initial_input[6]={'+','.join('0x%Xu'%v for v in ins)+'};\nstatic const u32 initial_output[6]={'+','.join('0x%Xu'%v for v in outs)+'};\n'
 code+=r'''
 static LinkOwner15102D90 *current_owner;static struct127 *current_actor;static const struct Case *current_case;static u8 matrix[256];static struct126 descriptor;static int calls,bad;
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(f32*src){u32 x=0,i;u8*d=(u8*)&x,*s=(u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 static void put_word(s32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static int arrays(struct17 **in,struct17 **out){return in[0]==&current_owner->input[0]&&in[1]==&current_owner->input[1]&&out[0]==&current_owner->output[0]&&out[1]==&current_owner->output[1];}
 static void transform(void){u32 i,j;for(i=0;i<2;i++){u8*in=(u8*)&current_owner->input[i],*out=(u8*)&current_owner->output[i];for(j=0;j<12;j++)out[j]=in[j]^0x5a;}}
 struct126 *func_1503195C(struct127 *a,s32 id,s32 z){calls++;if(a!=current_actor||id!=current_case->descriptor||z)bad=1;if(current_case->mutate){current_owner->flags^=0x40;put_word(&current_owner->descriptorIndex,0x87654321u);}return current_case->found?&descriptor:0;}
 s32 func_1514654C(struct127 *a,u8*d,s32 index,struct17 **in,struct17 **out,s32 count){calls++;if(a!=current_actor||d!=(u8*)&descriptor||index!=current_owner->descriptorIndex||count!=2||!arrays(in,out))bad=1;if(current_case->mutate)current_owner->flags^=0x20;if(current_case->ok)transform();return current_case->ok;}
 void func_15145EA4(struct17 **in,struct17 **out,u8*m,s32 count){calls++;if(m!=matrix+0x20||count!=2||!arrays(in,out))bad=1;if(current_case->mutate)current_owner->flags^=0x20;transform();}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_15102D90','test_'+key,1)+'\n'
 code+=r'''
 typedef s32(*T)(LinkOwner15102D90*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];LinkOwner15102D90 owner;struct127 actor;u8 owner_before[sizeof owner],actor_before[sizeof actor];u8*o=(u8*)&owner,*a=(u8*)&actor;u32 answer;
  for(i=0;i<sizeof owner;i++)o[i]=(i*13+11)&255;for(i=0;i<sizeof actor;i++)a[i]=(i*13+11)&255;
  owner.actor=&actor;owner.identity=c->identity;owner.matrixOffset=0x20;owner.descriptorId=c->descriptor;owner.descriptorIndex=0x12345678;owner.flags=c->initflags;actor.interaction_state=c->active;actor.unique_id=c->actor_identity;actor.unk74=c->mode;actor.unk1D4=c->matrix?(struct255*)matrix:0;
  put_bits(&owner.input[0].unk0,initial_input[0]);put_bits(&owner.input[0].unk4,initial_input[1]);put_bits(&owner.input[0].unk8,initial_input[2]);put_bits(&owner.input[1].unk0,initial_input[3]);put_bits(&owner.input[1].unk4,initial_input[4]);put_bits(&owner.input[1].unk8,initial_input[5]);
  put_bits(&owner.output[0].unk0,initial_output[0]);put_bits(&owner.output[0].unk4,initial_output[1]);put_bits(&owner.output[0].unk8,initial_output[2]);put_bits(&owner.output[1].unk0,initial_output[3]);put_bits(&owner.output[1].unk4,initial_output[4]);put_bits(&owner.output[1].unk8,initial_output[5]);
  for(i=0;i<sizeof owner;i++)owner_before[i]=o[i];for(i=0;i<sizeof actor;i++)actor_before[i]=a[i];current_owner=&owner;current_actor=&actor;current_case=c;calls=bad=0;answer=test(&owner);
  if(answer!=(u32)c->answer||owner.flags!=c->flags||(u32)owner.descriptorIndex!=(u32)c->index||calls!=c->calls||bad)return 1;
  if(get_bits(&owner.output[0].unk0)!=c->output[0]||get_bits(&owner.output[0].unk4)!=c->output[1]||get_bits(&owner.output[0].unk8)!=c->output[2]||get_bits(&owner.output[1].unk0)!=c->output[3]||get_bits(&owner.output[1].unk4)!=c->output[4]||get_bits(&owner.output[1].unk8)!=c->output[5])return 2;
  for(i=0;i<sizeof owner;i++)if(i!=0x124&&(i<0x120||i>=0x124)&&(i<0x128||i>=0x140)&&o[i]!=owner_before[i])return 3;
  for(i=0;i<sizeof actor;i++)if(a[i]!=actor_before[i])return 4;
  }return 0;}
 static int run(void){int selected_result=check(test_selected);if(selected_result)return selected_result;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_15102D90_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_15102D90_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers='modeled',valid_disjoint_owner_actor_and_matrix=True,source_installed=False);(out/'native_15102D90_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
