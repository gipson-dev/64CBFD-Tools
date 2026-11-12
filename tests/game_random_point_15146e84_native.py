"""Native SDK32 checks for both randomized effect paths and negative controls."""
import itertools,subprocess
from tools.experiments import game_random_point_15146e84_match as match
from tools.tests import test_game_point_interval_effect_match as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state):
 root,p=match.ROOT,match.OUT;fn=match.MANIFEST['body']
 controls={'gate':('== 0) return','!= 0) return'),'selector':('if (!func_15146890','if (func_15146890'),'threshold':('amount >= 71','amount > 71'),'branch':('func_150ADA20() & 1','!(func_150ADA20() & 1)'),'height':('effectPosition[1] = result.height','effectPosition[1] = position[1]'),'slot':('slot = func_151D8E20();','slot = func_151D8E20() + 1;'),'mode':('&result, (u8)mode)','&result, (u8)(mode + 1))'),'scale_wide':('randomFloat * 10.0f + 10.0f','randomFloat * 8.0f + 10.0f'),'scale_simple':('randomFloat * 8.0f + 5.0f','randomFloat * 8.0f + 4.0f'),'metadata':('result.metadata, 1.0f','0, 1.0f'),'wide_random':('randomB % 41U + 80','randomA % 41U + 80')}
 for n,(a,b) in controls.items():assert fn.count(a)==1,n
 rows=[]
 for mode,active,answer,amount,branch in itertools.product(range(256),(0,1),(0,1),(70,71),(0,1)):
  slot=(0,1,10,255)[mode%4];a=(mode*0x1234567)&0xffffffff;b=(mode*0x7654321)&0xffffffff;sample=g.bits((mode%11)/10.);factor,add=(10.,10.) if branch else (8.,5.);scale=g.single(g.floating(g.product(sample,g.bits(factor)))+add);rows.append((mode,active,answer,amount,branch,slot,a,b,sample,scale))
 code='#include <ultra64.h>\ntypedef struct HeightResult71820 { f32 height; s16 vertices[9]; s16 pad16; u32 metadata; u8 flags; u8 state; u16 pad1e; s32 value; } HeightResult71820;\ns32 func_15146890(f32 *,u8 *,HeightResult71820 *,u8);\nu8 func_151D8E20(void);\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15142180(u8,f32 *,s32,f32,f32);\nvoid func_151D9B8C(u8,f32,u8,s16 *,f32 *,s16,u8,u8,u8,u8,s32);\nvoid func_151DAB58(u8,f32,u8,f32 *,u8,u8,u8);\n'
 code+=r'''
 _Static_assert(sizeof(void*)==4 && sizeof(HeightResult71820)==36 && __builtin_offsetof(HeightResult71820,metadata)==24,"SDK32 layout");
 typedef struct {u32 mode,active,answer,amount,branch,slot,a,b,sample,scale;} Row;
 static const Row rows[]={
 '''
 for row in rows:code+='{'+','.join('0x%08Xu'%x for x in row)+'},\n'
 code+=r'''};
 static union {u32 align;u8 bytes[0x340];} actor;static const Row *row;static u32 calls,errors,randomIndex;static f32 *point;static HeightResult71820 *result;
 static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
 static f32 val(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
 s32 func_15146890(f32*p,u8*a,HeightResult71820*r,u8 mode){
  if(calls++!=0||a!=actor.bytes||mode!=(u8)row->mode)errors++;point=p;result=r;p[0]=1.25f;p[1]=-2.5f;p[2]=3.75f;r->height=99.f;r->vertices[0]=0x1234;r->metadata=0x12345678;return row->answer;}
 u8 func_151D8E20(void){if(calls++!=1)errors++;return row->slot;}
 void func_15142180(u8 slot,f32*p,s32 metadata,f32 w,f32 h){if(calls++!=2||slot!=row->slot||p!=point||metadata!=0x12345678||word(w)!=0x3f800000||word(h)!=0x3f800000)errors++;p[0]=-17.5f;p[2]=12.5f;result->height=55.f;}
 s32 func_150ADA20(void){u32 expected=2+(row->amount>=71)+(randomIndex?1+randomIndex:0);u32 v=randomIndex==0?row->branch:randomIndex==1?row->a:row->b;if(calls++!=expected)errors++;randomIndex++;return (s32)v;}
 f32 func_150ADA68(void){if(calls++!=3+(row->amount>=71)||randomIndex!=1)errors++;return val(row->sample);}
 static void packet(u8 slot,f32 scale,u8 alpha,f32*p){if(slot!=row->slot||word(scale)!=row->scale||alpha!=(u8)(row->a%101U+100)||word(p[0])!=word(row->amount>=71?-17.5f:1.25f)||word(p[1])!=word(row->amount>=71?55.f:99.f)||word(p[2])!=word(row->amount>=71?12.5f:3.75f))errors++;}
 void func_151D9B8C(u8 slot,f32 scale,u8 alpha,s16*v,f32*p,s16 len,u8 a,u8 b,u8 c,u8 d,s32 e){if(calls++!=6+(row->amount>=71)||!row->branch||randomIndex!=3||v!=result->vertices||v[0]!=0x1234||len!=(s16)(row->b%41U+80)||a!=1||b!=1||c!=0||d!=255||e!=1)errors++;packet(slot,scale,alpha,p);}
 void func_151DAB58(u8 slot,f32 scale,u8 alpha,f32*p,u8 a,u8 b,u8 c){if(calls++!=5+(row->amount>=71)||row->branch||randomIndex!=2||a!=1||b!=255||c!=1)errors++;packet(slot,scale,alpha,p);}
 '''
 for n,text in [('selected',fn)]+[(n,fn.replace(a,b,1)) for n,(a,b) in controls.items()]:code+='\n'+text.replace(match.NAME,'test_'+n,1)+'\n'
 code+=r'''
 typedef void(*Fn)(u8*,s32,s32);
 static int check(Fn fn){u32 i,j;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){row=&rows[i];for(j=0;j<sizeof(actor.bytes);j++)actor.bytes[j]=0;
  *(u32*)(actor.bytes+0x1d4)=row->active;calls=errors=randomIndex=0;fn(actor.bytes,(s32)(0xabcd0000|row->mode),(s32)row->amount);
  if(errors||calls!=(row->active?(row->answer?(6+(row->amount>=71)+row->branch):1):0))return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=p/'random-point-native.c';path.write_text(code);results={}
 for opt in ('-O0','-O2','-O3'):
  output=p/('random-point-native'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin','-Wno-unused-but-set-variable',str(path),'-o',str(output)],cwd=root,capture_output=True,text=True);assert z.returncode==0,(opt,z.stdout,z.stderr)
  z=subprocess.run([str(output)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr);results[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 return results
