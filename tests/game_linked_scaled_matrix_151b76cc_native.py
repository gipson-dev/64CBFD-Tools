import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_linked_scaled_matrix_151b76cc_match as p
out=p.out;root=p.root
from tools.tests import game_linked_scaled_matrix_151b76cc_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_151B76CC')
 controls={
  'first_row_scale':('matrix[0][0] *= source->scaleX','matrix[0][0] *= source->scaleY'),
  'second_row_scale':('matrix[1][0] *= source->scaleY','matrix[1][0] *= source->scaleX'),
  'second_row_last':('matrix[1][2] *= source->scaleY','matrix[1][2] *= source->scaleX'),
  'third_row_scale':('matrix[2][1] *= source->scaleX','matrix[2][1] *= source->scaleY'),
  'translation':('matrix[3][2] = source->translation[2]','matrix[3][2] = source->translation[1]'),
  'rotation':('source->rotation[2]','source->rotation[1]'),
  'offset':('-250.0f','-249.0f'),
  'output_pointer':('&output->y','&output->x'),
  'return_value':('return 1','return 0'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct { f32 x,y,z; } ActorPosition151B6320;
 typedef struct {u8 reserved00[0x18];f32 scaleX,scaleY;f32 rotation[3];u8 reserved2C[0xC];f32 translation[3];} MatrixSource151B76CC;
 typedef struct {MatrixSource151B76CC *source;} MatrixLink151B76CC;
 typedef struct {u8 reserved00[4];MatrixLink151B76CC *link;} MatrixData151B76CC;
 typedef struct {u8 reserved00[0x10];ActorPosition151B6320 position;u8 reserved1C[0x7C];MatrixData151B76CC *data;} MatrixOwner151B76CC;
 _Static_assert(__builtin_offsetof(MatrixSource151B76CC,rotation)==0x20 && __builtin_offsetof(MatrixSource151B76CC,translation)==0x38 && __builtin_offsetof(MatrixOwner151B76CC,data)==0x98 && __builtin_offsetof(MatrixOwner151B76CC,position)==0x10,"layout");
 struct Case {u32 sx,sy,translation,seed,mutate,alias;u32 initial_matrix[16],expected_matrix[16],output[3],rotation[3];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,calls,answer=g.reference(c);assert answer==1
  vals=[g.bits(c.sx),g.bits(c.sy),g.bits(c.translation),c.seed,c.mutate,c.alias]
  arrays=[g.matrix_words(c),calls[1][1][0],g.output_words(calls[1][1][0]),calls[0][1]]
  code+='{'+','.join('0x%Xu'%v for v in vals)+','+','.join('{'+','.join('0x%Xu'%v for v in a)+'}' for a in arrays)+'},\n'
 code+=r'''};
 static MatrixSource151B76CC *current_source;static ActorPosition151B6320 *current_output;static const struct Case *current_case;static int calls,bad;
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(const f32*src){u32 x=0,i;u8*d=(u8*)&x;const u8*s=(const u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 i;calls++;if(calls!=1||get_bits(&x)!=current_case->rotation[0]||get_bits(&y)!=current_case->rotation[1]||get_bits(&z)!=current_case->rotation[2])bad=1;for(i=0;i<16;i++)put_bits(&m[i/4][i%4],current_case->initial_matrix[i]);if(current_case->mutate){current_source->scaleX=-.75f;current_source->scaleY=1.25f;current_source->translation[0]=7.f;current_source->translation[1]=8.f;current_source->translation[2]=9.f;}}
 void func_150A7960(f32 m[4][4],f32 x,f32 y,f32 z,f32 *a,f32 *b,f32 *c){u32 i;calls++;if(calls!=2||get_bits(&x)!=0||get_bits(&y)!=0||get_bits(&z)!=0xC37A0000u||a!=&current_output->x||b!=&current_output->y||c!=&current_output->z)bad=1;for(i=0;i<16;i++)if(get_bits(&m[i/4][i%4])!=current_case->expected_matrix[i])bad=1;put_bits(a,get_bits(&m[0][0])^1);put_bits(b,get_bits(&m[1][1])^1);put_bits(c,get_bits(&m[2][2])^1);}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_151B76CC','test_'+key,1)+'\n'
 code+=r'''
 typedef s32(*T)(MatrixOwner151B76CC*,ActorPosition151B6320*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];MatrixOwner151B76CC owner;MatrixData151B76CC data;MatrixLink151B76CC link;MatrixSource151B76CC source;ActorPosition151B6320 output,*dest;u8 before[sizeof source],owner_before[sizeof owner];u8*p=(u8*)&source,*o=(u8*)&owner;u32 answer;
  for(i=0;i<sizeof source;i++)p[i]=(i*13+11)&255;for(i=0;i<sizeof owner;i++)o[i]=(i*13+11)&255;owner.data=&data;data.link=&link;link.source=&source;put_bits(&source.scaleX,c->sx);put_bits(&source.scaleY,c->sy);put_bits(&source.rotation[0],c->rotation[0]);put_bits(&source.rotation[1],c->rotation[1]);put_bits(&source.rotation[2],c->rotation[2]);put_bits(&source.translation[0],c->translation);source.translation[1]=source.translation[0]+1.f;source.translation[2]=source.translation[0]+2.f;for(i=0;i<sizeof source;i++)before[i]=p[i];for(i=0;i<sizeof owner;i++)owner_before[i]=o[i];dest=c->alias?&owner.position:&output;current_source=&source;current_output=dest;current_case=c;calls=bad=0;answer=test(&owner,dest);
  if(answer!=1||calls!=2||bad)return 1;if(get_bits(&dest->x)!=c->output[0]||get_bits(&dest->y)!=c->output[1]||get_bits(&dest->z)!=c->output[2])return 2;
  for(i=0;i<sizeof source;i++)if((!c->mutate||((i<0x18||i>=0x20)&&(i<0x38||i>=0x44)))&&p[i]!=before[i])return 3;
  if(c->mutate&&(get_bits(&source.scaleX)!=0xBF400000u||get_bits(&source.scaleY)!=0x3FA00000u||get_bits(&source.translation[0])!=0x40E00000u||get_bits(&source.translation[1])!=0x41000000u||get_bits(&source.translation[2])!=0x41100000u))return 4;
  for(i=0;i<sizeof owner;i++)if((!c->alias||i<0x10||i>=0x1c)&&o[i]!=owner_before[i])return 5;
  }return 0;}
 static int run(void){int selected_result=check(test_selected);if(selected_result)return selected_result;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_151B76CC_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_151B76CC_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers='modeled',valid_finite_storage_with_owner_output_alias=True,source_installed=False);(out/'native_151B76CC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
