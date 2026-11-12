"""SDK32 semantic checks with globals, actor switches and negative controls."""
import subprocess
from tools.experiments import game_script_15079fbc_match as match
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state):
 root,p=match.ROOT,match.OUT;fn=match.MANIFEST['body']
 controls={'gate':('unk65 == 0','unk65 != 0'),'boundary':('unk44 < 5.0f','unk44 < 4.0f'),'lookup':('func_1507BB28(0, D_800D154C->unk232)','func_1507BB28(0, D_800D1890)'),'rewind':('unk218 -= 1','unk218 -= 2'),'target':('unk31C->unk4C','unk31C->unk4E'),'chased':('unk31C->chased)', 'unk31C->chased == 0)'),'scale':('unk44 * D_8009A1E4','unk44 * 1.0f'),'threshold':('speed < 17','speed < 16'),'increment':('D_800D1893 += 1','D_800D1893 += 2'),'mode':('D_800D1890 = 8','D_800D1890 = 9'),'byte':('D_800D1892 = speed','D_800D1892 = speed + 1'),'flag':('unkF4 |= 0x40','unkF4 |= 0x20')}
 for k,(a,b) in controls.items():assert fn.count(a)==1,k
 code=r'''
#include <ultra64.h>
#include "structs.h"
_Static_assert(sizeof(void*)==4 && sizeof(struct216)==5 && __builtin_offsetof(struct127,unk218)==0x218 && __builtin_offsetof(struct127,unk31C)==0x31c && __builtin_offsetof(struct126,chased)==0x4a,"SDK32 layout");
struct127 D_800CC2D0[26];struct127 *D_800D154C;u8 D_800D1890,D_800D1891,D_800D1892,D_800D1893;f32 D_8009A1E4;
static struct127 actor,other;static struct126 meta;static struct216 scripts[4];static u32 mutation,command,lookups,applies,errors;
s32 func_1507BB28(s32 zero,s32 id){if(lookups++||zero||id!=(s32)command)errors++;if(mutation&1)D_800D154C=&other;return (s32)&scripts[2];}
void func_15075F40(void){if(applies++)errors++;if(mutation&2){D_800D154C=&other;other.unkF4=0x34560001;}}
'''
 for n,text in [('selected',fn)]+[(n,fn.replace(a,b,1)) for n,(a,b) in controls.items()]:code+='\n'+text.replace(match.NAME,'test_'+n,1)+'\n'
 code+=r'''
typedef void(*Fn)(void);
static int check(Fn fn){u32 who,active,vi,scale,chased,cmdi;static const f32 values[]={4.f,5.f,16.f,16.75f,17.f,20.f,255.f,32767.f};static const u32 commands[]={0,1,127,255};
 for(who=0;who<2;who++)for(active=0;active<2;active++)for(vi=0;vi<8;vi++)for(scale=0;scale<3;scale++)for(chased=0;chased<2;chased++)for(mutation=0;mutation<4;mutation++)for(cmdi=0;cmdi<4;cmdi++){
  struct127 *selected=who?D_800CC2D0:&actor;struct127 *target;u32 expectedFlag;int fallback,speed;
  actor.unk218=other.unk218=D_800CC2D0->unk218=&scripts[0];actor.unk78=other.unk78=D_800CC2D0->unk78=0x4444;actor.unk232=other.unk232=D_800CC2D0->unk232=0x55;
  actor.unkF4=0x12340020;other.unkF4=0x12340030;D_800CC2D0->unkF4=0x12340010;D_800D154C=selected;D_800CC2D0->unk65=active;D_800CC2D0->unk44=values[vi];D_800CC2D0->unk31C=&meta;meta.unk4C=0x91ab;meta.unk4E=0x23;meta.chased=chased;D_8009A1E4=scale==0?.5f:scale==1?1.f:.7f;
  command=commands[cmdi];D_800D1890=13;D_800D1891=command;D_800D1892=0x19;D_800D1893=255;lookups=applies=errors=0;fallback=!active||values[vi]<5.f;speed=(s16)(chased?values[vi]:values[vi]*D_8009A1E4);
  fn();if(errors)return 1;
  if(fallback){target=(mutation&1)?&other:selected;if(lookups!=1||applies||selected->unk232!=command||target->unk218!=&scripts[1]||D_800D154C!=target||D_800D1890!=13||D_800D1892!=0x19||D_800D1893!=255)return 2;}
  else{target=(mutation&2)?&other:selected;expectedFlag=(mutation&2)?0x34560041:(who?0x12340050:0x12340060);if(lookups||applies!=1||selected->unk78!=0x91ab||D_800D154C!=target||(u32)target->unkF4!=expectedFlag||D_800D1892!=(u8)speed||D_800D1890!=(speed<17?8:13)||D_800D1893!=(speed<17?0:255))return 3;}
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=p/'script-native.c';path.write_text(code);result={}
 for opt in ('-O0','-O2','-O3'):
  out=p/('script-native'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(out)],cwd=root,capture_output=True,text=True);assert z.returncode==0,(opt,z.stderr);z=subprocess.run([str(out)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr);result[opt]=dict(cases=3072,negative_controls=len(controls),UBSan=True)
 return result
