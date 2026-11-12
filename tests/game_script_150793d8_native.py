"""SDK32 native checks for bounded randomized path-node selection."""
import subprocess
from tools.experiments import game_script_150793d8_match as match
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
 fn=match.MANIFEST['body']
 controls={
  'negative_limit':('x < -1180','x < -1179'), 'positive_limit':('x > 1180','x > 1179'),
  'z_limit':('z > 1180','z > 1179'), 'origin_reset':('x = 0;','x = 1;'),
  'delta_x':('x = x + dx','x = x - dx'), 'delta_z':('z = z + dz','z = z - dz'),
  'low_clamp':('x = -1200','x = -1199'), 'high_clamp':('x = 1200','x = 1199'),
  'z_clamp':('z = 1200','z = 1199'), 'node':('[D_800D1890 + 1].x','[D_800D1890].x'),
  'seed':('func_150ADA20(), 550.0f','func_150ADA20()+1, 550.0f'),
  'radius':('550.0f, 0.0f','549.0f, 0.0f'),
 }
 for k,(a,b) in controls.items():assert fn.count(a)==1,k
 code=r'''
#include <ultra64.h>
#include "structs.h"
_Static_assert(sizeof(void*)==4 && __builtin_offsetof(struct127,unk13F)==0x13f,"SDK32 layout");
typedef struct {s16 x,pad2,z,pad6;} PathNode8;
struct127 D_800CC2D0[1], actors[2], *D_800D154C;u8 D_800D1890;s32 *D_800D2104;
static PathNode8 nodes[2][5],*paths[2];static s32 offsetx,offsetz;static u32 actor,idx,errors,random_calls,vector_calls;
s32 func_150ADA20(void){random_calls++;return 0x1234abcd;}
void func_1505A184(u16 seed,f32 radius,f32 y,f32 *px,f32 *pz,f32 *py){
 vector_calls++;if(seed!=0xabcd||radius!=550.f||y!=0.f)errors++;
 *px=offsetx;*pz=offsetz;*py=123.f;D_800D154C=&actors[actor];D_800D1890=idx;
}
'''
 for name,body in [('selected',fn)]+[(k,fn.replace(a,b,1)) for k,(a,b) in controls.items()]:code+='\n'+body.replace(match.NAME,'test_'+name,1)+'\n'
 code+=r'''
typedef void (*Fn)(void);
static int check(Fn fn){static const s32 v[]={-1181,-1180,-1,0,1,1180,1181};static const s32 d[]={-300,-20,0,20,300};
 u32 xi,zi,di,dj,path,i,j; s32 x,z,ex,ez;
 for(xi=0;xi<7;xi++)for(zi=0;zi<7;zi++)for(di=0;di<5;di++)for(dj=0;dj<5;dj++)for(actor=0;actor<2;actor++)for(path=0;path<2;path++)for(idx=0;idx<2;idx++){
  x=v[xi];z=v[zi];offsetx=d[di];offsetz=d[dj];
  D_800CC2D0->x_position=(f32)x+(x<0?-.25f:.25f);D_800CC2D0->z_position=(f32)z+(z<0?-.25f:.25f);
  actors[actor].unk13F=path;actors[actor^1].unk13F=path^1;D_800D154C=&actors[actor^1];D_800D1890=idx^1;
  paths[0]=nodes[0];paths[1]=nodes[1];D_800D2104=(s32*)paths;
  for(i=0;i<2;i++)for(j=0;j<5;j++){nodes[i][j].x=0x3131;nodes[i][j].z=0x4141;nodes[i][j].pad2=0x5151;nodes[i][j].pad6=0x6161;}
  if(x< -1180||x>1180||z< -1180||z>1180){x=0;z=0;}ex=x+offsetx;ez=z+offsetz;
  if(ex< -1200)ex=-1200;if(ex>1200)ex=1200;if(ez< -1200)ez=-1200;if(ez>1200)ez=1200;
  errors=random_calls=vector_calls=0;fn();
  if(errors||random_calls!=1||vector_calls!=1||D_800D154C!=&actors[actor]||D_800D1890!=idx)return 1;
  for(i=0;i<2;i++)for(j=0;j<5;j++){
   if(nodes[i][j].x!=(i==path&&j==idx+1?ex:0x3131)||nodes[i][j].z!=(i==path&&j==idx+1?ez:0x4141)||nodes[i][j].pad2!=0x5151||nodes[i][j].pad6!=0x6161)return 2;
  }
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(i+20)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 match.OUT.mkdir(parents=True,exist_ok=True);path=match.OUT/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=match.OUT/('native'+opt);z=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True)
  assert z.returncode==0,(opt,z.stderr)
  z=subprocess.run([str(exe)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr)
 return dict(cases_per_optimization=9800,negative_controls=len(controls),optimizations=3,scope='defined finite integer offsets with modeled helpers')
