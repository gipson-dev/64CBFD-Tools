import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_resource_matrix_15157dec_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_resource_matrix_15157dec_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_resource_matrix_15157dec_match import NEW_SOURCE
owner=NEW_SOURCE;selected=body(owner,'func_15157DEC')
header='#include <ultra64.h>\n#include "structs.h"\nextern u8 D_800BE9C0;\n'+owner[owner.index('void func_150A8050('):owner.index('/* Rebuild the selected page')]
def controls():
 pairs={
 'rotation_page':('func_150A8050(state->matrices[D_800BE9C0]','func_150A8050(state->matrices[D_800BE9C0 ^ 1]'),
 'angles':('transform->angleX, transform->angleY','transform->angleY, transform->angleX'),
 'translation_x':('][3][0] = state->x','][3][0] = state->y'),
 'scale_horizontal':('transform->scaleXZ','transform->scaleY'),
 'scale_vertical':('transform->scaleY','transform->scaleXZ'),
 'skip_translation_z':('    state->matrices[D_800BE9C0][3][2] = state->z;',''),
 'skip_final_scale':('    state->matrices[D_800BE9C0][2][2] *= transform->scaleXZ;',''),
 'add_instead':('][0][0] *=','][0][0] +='),
 }
 rows={n:selected.replace(a,b)for n,(a,b)in pairs.items()}
 cached=selected.replace('    ResourceMatrix183640 *state','    u8 page;\n    ResourceMatrix183640 *state').replace('    func_150A8050(', '    page = D_800BE9C0;\n    func_150A8050(',1)
 rows['cached_page']=cached.replace('matrices[D_800BE9C0]','matrices[page]')
 cached=selected.replace('    ResourceMatrix183640 *state','    f32 scaleX, scaleY;\n    ResourceMatrix183640 *state').replace('    func_150A8050(', '    scaleX = transform->scaleXZ;\n    scaleY = transform->scaleY;\n    func_150A8050(',1)
 rows['cached_scales']=cached.replace('*= transform->scaleXZ','*= scaleX').replace('*= transform->scaleY','*= scaleY')
 assert all(v!=selected for v in rows.values());return rows
def main():
 cases=list(guest.native_cases())
 rows='\n'.join('{'+','.join('0x%Xu'%v for v in(c.page,c.pattern,c.mutation,0 if c.parameters==guest.INPUT else 1 if c.parameters==guest.OBJECT+0x120 else 2,c.scaleX,c.scaleY))+'},'for c in cases)
 program=header+r'''
typedef char Layout[(sizeof(void*)==4&&sizeof(struct102)==0x1D8&&sizeof(ResourceTransform183640)==20&&sizeof(ResourceMatrix183640)==0xFC&&
 __builtin_offsetof(ResourceTransform183640,scaleXZ)==12&&__builtin_offsetof(ResourceTransform183640,scaleY)==16&&
 __builtin_offsetof(ResourceMatrix183640,x)==0x54&&__builtin_offsetof(ResourceMatrix183640,matrices)==0x7C)?1:-1];
typedef struct{u32 page,pattern,mutation,paramKind,scaleX,scaleY;} Row;
static const Row rows[]={
'''+rows+r'''
};
u8 D_800BE9C0;
static struct102 object;
static struct{f32 x,y,z,horizontal,vertical;} separate;
static u8 expected[sizeof(object)],expectedSeparate[20],snapshot[sizeof(object)],paramSnapshot[20];
static u8 *parameters,*expectedParameters;static u32 calls,error,savedPage;static u32 angles[3];static u8*destination;
static const Row*row;
static u32 word(f32 f){union{f32 f;u32 w;}v;v.f=f;return v.w;}
static f32 value(u32 w){union{f32 f;u32 w;}v;v.w=w;return v.f;}
static u32 rd32(const u8*p){return(u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void wr32(u8*p,u32 w){u32 i;for(i=0;i<4;i++)p[i]=(u8)(w>>(i*8));}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static u32 seed(u32 i){return word(i==15?1.f:((s32)((i*3+row->pattern*5)%13)-6)*.125f);}
static void effect(u8*p,u8*q,u8*page){
 u32 i;if(row->mutation&1)*page^=1;
 if(row->mutation&2){wr32(p+0x54,word(-4.25f));wr32(p+0x58,word(5.5f));wr32(p+0x5C,word(-6.75f));}
 if(row->mutation&4){wr32(q+12,word(-.75f));wr32(q+16,word(1.25f));}
 if(row->mutation&8)for(i=0;i<16;i++)wr32(p+0x7C+(*page^1)*64+i*4,seed(15-i));
 if(row->mutation&16)for(i=0;i<3;i++)wr32(q+i*4,word(-11.f-i));
}
static void model(void){
 u32 i,j;const u32 dst[]={0x7C,0x80,0x84,0x8C,0x90,0x94,0x9C,0xA0,0xA4};u8 page=(u8)row->page;u8*d;
 savedPage=page;destination=(u8*)&object+0x7C+page*64;
 for(i=0;i<3;i++)angles[i]=rd32(expectedParameters+i*4);
 copy(snapshot,expected,sizeof(object));copy(paramSnapshot,expectedParameters,20);
 for(i=0;i<16;i++)wr32(expected+0x7C+page*64+i*4,seed(i));
 effect(expected,expectedParameters,&page);
 for(i=0;i<3;i++)wr32(expected+0xAC+i*4+page*64,rd32(expected+0x54+i*4));
 for(i=0;i<9;i++){j=i>=3&&i<6?16:12;d=expected+dst[i]+page*64;wr32(d,word(value(rd32(d))*value(rd32(expectedParameters+j))));}
 savedPage=page;
}
__attribute__((noinline,noclone)) void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){
 u32 i;if(++calls!=1||(u8*)m!=destination||D_800BE9C0!=row->page||word(x)!=angles[0]||word(y)!=angles[1]||word(z)!=angles[2]||!equal((u8*)&object,snapshot,sizeof(object))||!equal(parameters,paramSnapshot,20))error=1;
 for(i=0;i<16;i++)wr32((u8*)m+i*4,seed(i));effect((u8*)&object,parameters,&D_800BE9C0);
}
'''+selected+'\n'
 for name,b in controls().items():program+=b.replace('func_15157DEC(','negative_'+name+'(',1)+'\n'
 program+=r'''
typedef void(*Update)(u8*,void*);
static int test(Update fn){
 u32 n,i,page;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  row=&rows[n];for(i=0;i<sizeof(object);i++)((u8*)&object)[i]=(u8)(i*29+0x5A);
  parameters=row->paramKind==0?(u8*)&separate:(u8*)&object+(row->paramKind==1?0x120:0x70);
  for(page=0;page<2;page++)for(i=0;i<16;i++)wr32((u8*)&object+0x7C+page*64+i*4,seed(i));
  wr32((u8*)&object+0x54,word(1.5f));wr32((u8*)&object+0x58,word(-2.75f));wr32((u8*)&object+0x5C,word(3.125f));
  wr32(parameters,word(10.f+row->pattern));wr32(parameters+4,word(-20.f+row->pattern));wr32(parameters+8,word(30.f-row->pattern));wr32(parameters+12,row->scaleX);wr32(parameters+16,row->scaleY);
  D_800BE9C0=(u8)row->page;copy(expected,(u8*)&object,sizeof(object));copy(expectedSeparate,(u8*)&separate,20);
  expectedParameters=row->paramKind==0?expectedSeparate:expected+(row->paramKind==1?0x120:0x70);model();
  calls=error=0;fn((u8*)&object,parameters);
  if(error||calls!=1||D_800BE9C0!=savedPage||!equal((u8*)&object,expected,sizeof(object))||!equal((u8*)&separate,expectedSeparate,20))return 1;
 }
 return 0;
}
static __attribute__((noinline,noclone)) int matrixAlias(struct102*a,ResourceMatrix183640*b){a->unk54=1234;b->x=1.f;return a->unk54==0;}
static __attribute__((noinline,noclone)) int transformAlias(s32*a,ResourceTransform183640*b){*a=0;b->angleX=1.f;return*a==0x3F800000;}
static int run(void){
 if(!matrixAlias(&object,(ResourceMatrix183640*)&object))return 2;
 if(!transformAlias(&object.unk170,(ResourceTransform183640*)((u8*)&object+0x170)))return 3;
 if(test(func_15157DEC))return 4;
'''
 for i,n in enumerate(controls()):program+=' if(!test(negative_%s))return %d;\n'%(n,10+i)
 program+=' return 0;\n}\n'+START;(out/'native.c').write_text(program);profiles=[]
 for opt in('-O0','-O2','-O3'):
  binary=out/('native'+opt);p=subprocess.run(native_command(opt)+['-fstrict-aliasing','-Wstrict-aliasing=2','-fno-builtin','-mstackrealign',str(out/'native.c'),'-o',str(binary)],cwd=root,capture_output=True,text=True);(out/('native'+opt+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
  rc=subprocess.run([str(binary)],capture_output=True).returncode;assert rc==0,(opt,rc)
  profiles.append(dict(profile=opt,cases=len(cases),semantic_controls=len(controls()),strict_aliasing=True,UBSan_traps=True));print(json.dumps(profiles[-1]),flush=True)
 extras=[]
 for label,badheader in(('transform',header.replace('__attribute__((__may_alias__))','',1)),('matrix',''.join(header.rsplit('__attribute__((__may_alias__))',1)))):
  probes=program[program.index('static __attribute__((noinline,noclone)) int matrixAlias'):program.index('static int run(void)')]
  control=badheader+'\nstatic struct102 object;\n'+probes+'\nstatic int run(void){if(!matrixAlias(&object,(ResourceMatrix183640*)&object))return 2;if(!transformAlias(&object.unk170,(ResourceTransform183640*)((u8*)&object+0x170)))return 3;return 0;}\n'+START
  p=out/('native-noalias-'+label+'.c');p.write_text(control)
  for opt in('-O0','-O2','-O3'):
   binary=out/('native-noalias-'+label+opt);c=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=root,capture_output=True,text=True);assert c.returncode==0,c.stderr
   rc=subprocess.run([str(binary)],capture_output=True).returncode;assert rc==(0 if opt=='-O0'else 3 if label=='transform'else 2),(label,opt,rc)
   extras.append(dict(view=label,profile=opt,exit=rc))
 report=dict(cases_per_profile=len(cases),profiles=profiles,semantic_controls=len(controls()),native_only_controls=extras,typed_void_parameter_callback=True,two_pages_only_native=True,five_field_structure_and_embedded_views=True,all_record_parameter_and_page_bytes=True,generic_ISO_portability_claim=False)
 (out/'native-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
