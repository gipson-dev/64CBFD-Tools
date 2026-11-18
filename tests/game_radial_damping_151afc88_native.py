"""Private SDK32 semantic screen; no result is installed or counted."""
from pathlib import Path
import sys,subprocess,itertools,json
from tools.experiments import game_radial_damping_151afc88_match as match
root=match.ROOT;p=match.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
fn=match.PIN['body'];s=match.PIN['declarations'];typ=s[s.index('typedef struct RadialPacket151AFC88'):s.index('extern f32 D_800AA110')]
def run(state):
 controls={'kind':('packet.field08 = 0xE03','packet.field08 = 0xE04'),'type':('packet.field1D = 41','packet.field1D = 40'),'life':(' & 15) + 25',' & 7) + 25'),'alpha':('% 156U + 100','% 156U + 99'),'x':('packet.position[0] = x','packet.position[0] = y'),'base':('sample * 202.0f + 101.0f','sample * 202.0f + 100.0f'),'pitch':('random % 21U - 20','random % 21U - 19'),'speed':('sample * D_800AA110 + 500.0f','sample * D_800AA110 + 499.0f'),'flag1':('packet.flags |= 0x40','packet.flags |= 0x20'),'flag2':('packet.flags |= 0x80','packet.flags |= 0x20'),'height':('packet.field24 = D_800AA118','packet.field24 = D_800AA114'),'bonus':('bonus = D_800AA11C','bonus = D_800AA114'),'factory':('&packet, 1, 4, slot, 1','&packet, 1, 4, slot, 0'),'return':('    return 1;','    return 0;')}
 for k,(a,b) in controls.items():assert fn.count(a)==1,k
 code='#include <ultra64.h>\ntypedef struct { f32 x, y, z; } EffectPoint151AFC88;\n'+typ+'\nextern f32 D_800AA110,D_800AA114,D_800AA118,D_800AA11C;\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143794(s16,s16,f32,EffectPoint151AFC88 *);\nvoid *func_15130374(void *,u8,s32,u8,s32);\nvoid *memcpy(void *,const void *,size_t);\n'
 code+=r'''
 _Static_assert(sizeof(void*)==4 && sizeof(RadialPacket151AFC88)==116 && __builtin_offsetof(RadialPacket151AFC88,flags)==0x58,"SDK32 layout");
 f32 D_800AA110,D_800AA114,D_800AA118,D_800AA11C;
 static u32 mode,flags,success,mut,calls,errors,ri,fi;static union{u32 align;u8 bytes[256];} output;
 static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
 s32 func_150ADA20(void){u32 vals[]={mode,mode*0x1234567u,mode*0x7654321u,flags&1,flags>>1};u32 expected[]={0,1,3,6,7};if(ri>=5||calls++!=expected[ri])errors++;return vals[ri++];}
 f32 func_150ADA68(void){u32 expected[]={2,4};if(fi>=2||calls++!=expected[fi])errors++;fi++;return fi==1?0.5f:0.25f;}
 void func_15143794(s16 angle,s16 pitch,f32 radius,EffectPoint151AFC88*p){if(calls++!=5||angle!=(s16)mode||pitch!=(s16)(((mode*0x7654321u)%21u)-20)||word(radius)!=word(275.25f))errors++;p->x=7.25f;p->y=-8.5f;p->z=9.75f;if(mut){D_800AA118=3.5f;D_800AA11C=4.25f;}}
 void *func_15130374(void *v,u8 a,s32 n,u8 slot,s32 context){u32 i;RadialPacket151AFC88 *d=v;if(calls++!=8||a!=1||n!=4||slot!=(u8)mode||context!=1)errors++;
  if(d->field00!=0x200005||d->field04||d->field08!=0xe03||d->field0a!=(s16)((mode&15)+25)||d->field0C||d->field10||d->field14!=64||d->field15!=11||d->field16!=106||d->field17!=255||d->field18!=176||d->field19!=160||d->field1A!=42||d->field1B!=(u8)((mode*0x1234567u)%156u+100)||d->field1C!=255||d->field1D!=41||d->field1E!=15||d->field20!=17||d->field22!=25||word(d->field24)!=word(mut?3.5f:1.5f)||word(d->field28)!=word(202.0f)||word(d->field2C)!=word(202.0f)||word(d->position[0])!=word(1.25f)||word(d->position[1])!=word(-2.5f)||word(d->position[2])!=word(3.75f)||word(d->direction.x)!=word(7.25f)||word(d->direction.y)!=word(-8.5f)||word(d->direction.z)!=word(9.75f)||word(d->field54)!=0||d->flags!=(0xe05|((flags&1)?0x40:0)|((flags&2)?0x80:0))||d->field60!=3||d->field61!=3||d->field62!=6||d->field63!=-1)errors++;
  if(success){for(i=0;i<112;i++)output.bytes[0x10+i]=((u8 *)v)[i];output.bytes[0x9c]=0;}return success?output.bytes:0;}
 void *memcpy(void *a,const void *b,size_t n){u32 i;u8*dst=a;const u8*src=b;if(calls++!=9||dst!=output.bytes+0xa8||n!=4||word(*(const f32*)b)!=word(mut?4.25f:2.25f))errors++;for(i=0;i<n;i++)dst[i]=src[i];return a;}
 '''
 code=code.replace('d->field0a','d->field0A')
 for n,text in [('selected',fn)]+[(n,fn.replace(a,b,1)) for n,(a,b) in controls.items()]:code+='\n'+text.replace('func_151AFC88','test_'+n,1)+'\n'
 code+=r'''
 typedef s32(*Fn)(s32,s16,f32,f32,f32,f32,f32,f32,s16,u8,f32,s32,f32,s32,u8);
 static int check(Fn fn){for(mode=0;mode<256;mode++)for(flags=0;flags<4;flags++)for(success=0;success<2;success++)for(mut=0;mut<2;mut++){D_800AA110=202.0f;D_800AA114=.5f;D_800AA118=1.5f;D_800AA11C=2.25f;calls=errors=ri=fi=0;if(fn(3,2,1.25f,-2.5f,3.75f,0,0,0,(s16)mode,0,0,0,0,0,(u8)mode)!=1||errors||calls!=9+success||ri!=5||fi!=2)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=p/'native.c';path.write_text(code);results={}
 for opt in ('-O0','-O2','-O3'):
  out=p/('native'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(out)],cwd=root,capture_output=True,text=True);assert z.returncode==0,(opt,z.stderr);z=subprocess.run([str(out)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr);results[opt]=dict(cases=4096,negative_controls=len(controls),UBSan=True)
 return results
