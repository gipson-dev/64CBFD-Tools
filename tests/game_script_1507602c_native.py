"""Native SDK32 checks for a path-directed movement command."""
import subprocess
from tools.experiments import game_script_1507602c_match as match
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def run():
    fn=match.MANIFEST['body']
    controls={
        'path':('[D_800D154C->unk13F][D_800D1891]','[D_800D154C->unk13F ^ 1][D_800D1891]'),
        'node':('node[1].x','node[0].x'),
        'z':('node[1].z','node[0].z'),
        'duration':('2.0f * (sqrtf','1.0f * (sqrtf'),
        'clamp':('duration < 12.0f','duration < 10.0f'),
        'adjust':('duration * D_8009A140','duration * 1.0f'),
        'timer':('duration * 100.0f','duration * 50.0f'),
        'velocity':('duration * 0.5f','duration * 1.0f'),
        'state':('unk223 = 4','unk223 = 5'),
        'index':('unk21E = D_800D1891','unk21E = 0'),
    }
    for name,(old,new) in controls.items():
        assert fn.count(old)==1,name
    code=r'''
#include <ultra64.h>
#include "structs.h"
_Static_assert(sizeof(void*)==4 && __builtin_offsetof(struct127,unk13F)==0x13f && __builtin_offsetof(struct127,unk21C)==0x21c && __builtin_offsetof(struct127,unk44)==0x44,"SDK32 layout");
typedef struct {s16 x,pad2,z,pad6;} PathNode8;
static struct127 actors[2];struct127 *D_800D154C;u8 D_800D1891;f32 D_8009A140;s32 *D_800D2104;
static PathNode8 nodes[2][4];static PathNode8 *paths[2];static unsigned selected,callcount;static f32 speed;
void func_15075548(void) {callcount++; D_800D154C=&actors[selected]; D_800D154C->unk44=speed;}
f32 sqrtf(f32 x) {f32 r; __asm__("sqrtss %1,%0" : "=x"(r) : "x"(x));return r;}
'''
    for name,body in [('selected',fn)]+[(k,fn.replace(a,b,1)) for k,(a,b) in controls.items()]:
        code+='\n'+body.replace(match.NAME,'test_'+name,1)+'\n'
    code+=r'''
typedef void (*Fn)(void);
static int check(Fn fn){unsigned path,index,actor,si;static const f32 speeds[]={0.5f,1.f,2.f,5.f,10.f,100.f};
 for(path=0;path<2;path++)for(index=0;index<2;index++)for(actor=0;actor<2;actor++)for(si=0;si<6;si++){
  f32 distance,duration,expected_rate;struct127 *a;
  paths[0]=nodes[0];paths[1]=nodes[1];D_800D2104=(s32*)paths;
  nodes[0][0].x=17;nodes[0][0].z=23;nodes[0][1].x=3;nodes[0][1].z=4;nodes[0][2].x=30;nodes[0][2].z=40;
  nodes[1][0].x=31;nodes[1][0].z=47;nodes[1][1].x=-3;nodes[1][1].z=-4;nodes[1][2].x=-30;nodes[1][2].z=-40;
  nodes[1][1].x=-6;nodes[1][1].z=-8;nodes[1][2].x=-60;nodes[1][2].z=-80;
  actors[0].unk13F=actors[1].unk13F=path;actors[0].x_position=actors[1].x_position=0.f;actors[0].z_position=actors[1].z_position=0.f;
  actors[0].gravity=actors[1].gravity=2.f;actors[0].unk21E=actors[1].unk21E=0xf0;actors[0].unk223=actors[1].unk223=0xf1;
  actors[0].unk21C=actors[1].unk21C=0xbeef;actors[0].y_velocity=actors[1].y_velocity=-999.f;
  D_800D154C=&actors[actor^1];selected=actor;D_800D1891=index;D_8009A140=0.083333f;speed=speeds[si];callcount=0;
  distance=(path?2.f:1.f)*(index?50.f:5.f);duration=2.f*(distance/speed);expected_rate=speed;
  if(duration<12.f){expected_rate*=duration*D_8009A140;duration=12.f;}
  fn();a=&actors[actor];
  if(callcount!=1||D_800D154C!=a||a->unk21E!=index||a->unk44!=expected_rate||a->unk21C!=(u16)(duration*100.f)||a->y_velocity!=duration||a->unk223!=4)return 1;
  if(actors[actor^1].unk21E!=0xf0||actors[actor^1].unk21C!=0xbeef||actors[actor^1].unk223!=0xf1)return 2;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
    for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=match.OUT;p.mkdir(parents=True,exist_ok=True);path=p/'movement-native.c';path.write_text(code)
    for opt in ('-O0','-O2','-O3'):
        exe=p/('movement-native'+opt)
        compile_result=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True)
        assert compile_result.returncode==0,(opt,compile_result.stderr)
        result=subprocess.run([str(exe)],capture_output=True)
        assert result.returncode==0,(opt,result.returncode,result.stderr)
    return dict(cases_per_optimization=48,negative_controls=len(controls),optimizations=3,scope='defined finite SDK32 inputs with modeled helper')
