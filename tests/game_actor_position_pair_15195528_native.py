"""Native SDK32 finite nearest-rounding cases and mutation controls."""
import itertools,json,subprocess
from tools.experiments import game_actor_position_pair_15195528_match as p
from tools.tests import game_actor_position_pair_15195528_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(p.out/'selected-source.c').read_text();selected=p.body(source,p.NAME)
 controls={'source_yaw':('*(f32 *)(source + 0x40) - 90.0f','*(f32 *)(source + 0x40) - 89.0f'),'actor_yaw':('*(f32 *)(actor + 0x40) - 90.0f','*(f32 *)(actor + 0x40) - 89.0f'),'scale':('angle * D_800A8708','angle + D_800A8708'),'xscale':('direction[0] * 20.0f','direction[0] * 21.0f'),'zscale':('direction[2] * 20.0f','direction[2] * 21.0f'),'yoffset':('*(f32 *)(actor + 0x18) + 50.0f','*(f32 *)(actor + 0x18) + 49.0f'),'end_x':('*(f32 *)(actor + 0x14) - x','*(f32 *)(actor + 0x14) + x'),'end_z':('*(f32 *)(actor + 0x1C) - z','*(f32 *)(actor + 0x1C) + z'),'direction_y':('direction[1] = 0.0f','direction[1] = 1.0f'),'submit_flag':('direction, 255, 1','direction, 254, 1')}
 rows=[]
 for i,(sourceflag,yaw,scale,trig,mutation)in enumerate(itertools.product((0,1,2),(g.bits(0.),g.bits(45.),g.bits(180.)),(g.bits(.5),g.bits(1.),g.bits(.017453292)),((g.bits(.25),g.bits(-.75)),(g.bits(-1.),g.bits(.5))),(0,1))):
  c=g.Case(sourceflag,1,yaw,g.bits(-30.),scale,*trig,g.bits(.25),mutation,0,i%3);m,angle,start,end,direction=g.reference(c,g.fixture(c));rows.append((c,angle,*start,*end,*direction))
 code='#include <ultra64.h>\n'+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef union {u32 u;f32 f;} Bits;
 typedef struct {u32 source,yaw,actor_yaw,scale,sine,cosine,mutation,angle,start[3],end[3],direction[3];} Fixture;
 static u32 actor_data[64],source_data[64];static u8 *actor=(u8*)actor_data,*source=(u8*)source_data;static const Fixture *cur;static u32 trig_calls,submit_calls,bad;
 f32 D_800A8708;
 static f32 val(u32 n){Bits v;v.u=n;return v.f;}static u32 bits(f32 x){Bits v;v.f=x;return v.u;}
 f32 func_150ADA68(void){bad=1;return .25f;}
 void func_1514373C(f32 angle,f32 magnitude,f32 *sine,f32 *cosine){trig_calls++;if(bits(angle)!=cur->angle||bits(magnitude)!=bits(1.0f))bad=1;*sine=val(cur->sine);*cosine=val(cur->cosine);if(cur->mutation){*(f32*)(actor+0x14)=-7.0f;*(f32*)(actor+0x18)=12.0f;*(f32*)(actor+0x1c)=.5f;}}
 void func_15137610(u8 *a,f32 *start,f32 *end,f32 *direction,s32 x,s32 y){u32 i;submit_calls++;if(a!=actor||x!=255||y!=1)bad=1;for(i=0;i<3;i++)if(bits(start[i])!=cur->start[i]||bits(end[i])!=cur->end[i]||bits(direction[i])!=cur->direction[i])bad=1;}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'
 for c,angle,*v in rows:
  vals=(c.source,c.yaw,c.actor_yaw,c.scale,c.sin,c.cos,c.mutation,angle);arr=lambda a:','.join(str(x)+'u' for x in a);code+='{'+arr(vals)+',{'+arr(v[:3])+'},{'+arr(v[3:6])+'},{'+arr(v[6:9])+'}},\n'
 code+='};\n'+r'''
 typedef void(*Update)(u8*,u8*,s32);
 static int check(Update fn){u32 n;for(n=0;n<CASE_COUNT;n++){cur=fixtures+n;*(f32*)(source+0x40)=val(cur->yaw);*(f32*)(actor+0x40)=val(cur->actor_yaw);*(f32*)(actor+0x14)=10.5f;*(f32*)(actor+0x18)=-2.25f;*(f32*)(actor+0x1c)=100.0f;D_800A8708=val(cur->scale);trig_calls=submit_calls=bad=0;fn(cur->source==2?actor:cur->source?source:0,actor,0x12345678);if(bad||trig_calls!=1||submit_calls!=1)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');src=p.out/'native.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);v=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 result=dict(profiles=reports,finite_nearest_rounding_only=True,actor_nonnull_only=True,helpers_modeled=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
