"""SDK32 finite-input semantic checks with negative controls."""
import itertools,subprocess
from tools.experiments import game_actor_point_flagged_15146bf8_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state):
 root,p=match.ROOT,match.OUT;function=match.MANIFEST['body']
 controls={'gate':('== 0) return','!= 0) return'),'selector':('&result, selected) != 0','&result, selected) == 0'),'flag':('if ((u8)flag)','if (!(u8)flag)'),'slot':('slot = 12','slot = 13'),'scale':('amount * D_800A5720','amount * D_800A5724'),'tag':('0x40) * D_800A5724','0x40) * D_800A5720'),'threshold':('amount >= 115','amount > 115'),'metadata':('result.metadata, 1.0f','(s32)0, 1.0f'),'mode':('position, selected);','position, selected + 1);')}
 for n,(a,b) in controls.items():assert function.count(a)==1,n
 rows=[]
 for mode,flag,active,answer,amount,mut in itertools.product(range(256),(0,1,0x100,0x101),(0,1),(0,1),(114,115),(0,1)):
  value=g.bits(27.5 if mut else 12.5);first=g.bits(.5) if mut else 0x3bfc0fc1;tagk=g.bits(2.) if mut else 0x3f360b61
  scale=g.product(g.single(float(amount)),first);tag=g.converted(g.product(value,tagk));rows.append((mode,flag,active,answer,amount,mut,scale,tag))
 code='#include <ultra64.h>\ntypedef struct HeightResult71820 { f32 height; s16 vertices[9]; s16 pad16; u32 metadata; u8 flags; u8 state; u16 pad1e; s32 value; } HeightResult71820;\nextern f32 D_800A5720,D_800A5724;\ns32 func_15146890(f32 *,u8 *,HeightResult71820 *,u8);\nvoid func_15141F78(u8,u8 *,f32,u8,f32 *,u8);\nvoid func_15142180(u8,f32 *,s32,f32,f32);\n'
 code+=r'''
 _Static_assert(sizeof(void*)==4 && sizeof(HeightResult71820)==36 && __builtin_offsetof(HeightResult71820,metadata)==24,"SDK32 layout");
 typedef struct {u32 mode,flag,active,answer,amount,mut,scale,tag;} Row;
 static const Row rows[]={
 '''
 for row in rows:code+='{'+','.join('0x%08Xu'%x for x in row)+'},\n'
 code+=r'''};
 f32 D_800A5720,D_800A5724;
 static union {u32 align;u8 bytes[0x340];} actor;static const Row *row;static u32 calls,errors;static f32 *lastPosition;static HeightResult71820 *lastResult;
 static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
 static f32 val(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
 s32 func_15146890(f32 *p,u8*a,HeightResult71820*r,u8 mode){
  if(calls++!=0||a!=actor.bytes||mode!=(u8)row->mode)errors++;lastPosition=p;lastResult=r;p[0]=1.25f;p[1]=-2.5f;p[2]=3.75f;r->metadata=0x12345678;
  if(row->mut){*(f32*)(actor.bytes+0x40)=27.5f;D_800A5720=.5f;D_800A5724=2.f;}return row->answer;}
 void func_15141F78(u8 slot,u8*src,f32 scale,u8 tag,f32*p,u8 mode){
  if(calls++!=1||slot!=((u8)row->flag?12:11)||src!=(u8*)lastResult||p!=lastPosition||mode!=(u8)row->mode||word(scale)!=row->scale||tag!=row->tag||lastResult->metadata!=0x12345678)errors++;lastResult->metadata=0x76543210;p[0]=-17.5f;}
 void func_15142180(u8 slot,f32*p,s32 metadata,f32 width,f32 height){
  if(calls++!=2||slot!=2||p!=lastPosition||metadata!=0x76543210||word(p[0])!=word(-17.5f)||word(width)!=0x3f800000||word(height)!=0x3f800000)errors++;}
 '''
 for n,text in [('selected',function)]+[(n,function.replace(a,b,1)) for n,(a,b) in controls.items()]:code+='\n'+text.replace(match.NAME,'test_'+n,1)+'\n'
 code+=r'''
 typedef void(*Fn)(u8*,s32,s32,s32);
 static int check(Fn fn){u32 i,j;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){row=&rows[i];for(j=0;j<sizeof(actor.bytes);j++)actor.bytes[j]=0;
  *(u32*)(actor.bytes+0x1d4)=row->active;*(f32*)(actor.bytes+0x40)=12.5f;D_800A5720=val(0x3bfc0fc1);D_800A5724=val(0x3f360b61);calls=errors=0;
  fn(actor.bytes,(s32)(0xabcd0000|row->mode),(s32)row->amount,(s32)row->flag);if(errors||calls!=(row->active?(row->answer?(row->amount>=115?3:2):1):0))return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=p/'flagged-native.c';path.write_text(code);results={}
 for opt in ('-O0','-O2','-O3'):
  output=p/('flagged-native'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(output)],cwd=root,capture_output=True,text=True);assert z.returncode==0,(opt,z.stdout,z.stderr)
  z=subprocess.run([str(output)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr);results[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 return results
