from pathlib import Path
import subprocess,sys
from tools.experiments.game_point_descriptor_151382e0_match import ROOT as root, OUT as out
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
src=(out/'durable-point-after.c').read_text();end=src.index('} PointEffectDescriptor161520;')+len('} PointEffectDescriptor161520;');start=src.rfind('typedef struct {',0,src.index('} LocalizedTrailInput;'));layout=src[start:end];fn=body(src,'func_151382E0')
controls={'wrong_gate':fn.replace('category != 2','category != 1'),'wrong_flag':fn.replace('category == 1 ? 1 : 0','category == 0 ? 1 : 0'),'wrong_position':fn.replace('descriptor.localized.position = *position;','descriptor.localized.position = *position; descriptor.localized.position.x = 0;'),'wrong_group':fn.replace('channel, context);','channel ^ 1, context);'),'wrong_context':fn.replace('channel, context);','channel, 0);'),'wrong_constant':fn.replace('descriptor.localized.countBase = 18;','descriptor.localized.countBase = 19;')};assert all(v!=fn for v in controls.values())
unit='''typedef unsigned char u8; typedef short s16; typedef int s32; typedef unsigned int u32; typedef float f32;
typedef struct {f32 x,y,z;} Position161520; struct ActorEffectSurface {u32 value;};\n'''+layout+'''
u8 D_800A3FE6[320]; f32 D_800A4830,D_800A4834,D_800A4838,D_800A483C,D_800A4840;
static int calls,error,wgroup,wcontext,wcat;static Position161520 want;static struct ActorEffectSurface surf;
void func_15153F18(void *p,void *point,s32 surface,s32 group,s32 context) {
 PointEffectDescriptor161520*d=p;calls++;
 if(point!=&d->localized.position||surface!=(s32)&surf||group!=wgroup||context!=wcontext)error=1;
 if(d->localized.position.x!=want.x||d->localized.position.y!=want.y||d->localized.position.z!=want.z)error=2;
 if(d->localized.timeBase!=D_800A4830||d->localized.timeRange!=D_800A4834||d->localized.scaleBase!=D_800A4838||d->localized.scaleRange!=D_800A483C||d->localized.radiusBase!=4||d->localized.radiusRange!=9||d->localized.opaqueChance!=D_800A4840)error=3;
 if(d->angular.firstAngleBase!=0||d->angular.firstAngleRange!=255||d->angular.secondAngleBase!=-63||d->angular.secondAngleRange!=78||d->localized.countBase!=18||d->localized.countRange!=7||d->localized.requestSelectorBase!=3||d->localized.requestSelectorRange!=3||d->localized.durationBase!=20||d->localized.durationRange!=30||d->localized.modeBase!=155||d->localized.modeRange!=100||d->localized.firstValue!=16||d->localized.secondValue!=15||d->localized.requestValue!=0||d->localized.selector!=(wcat==1))error=4;
}
'''
for name,content in {'selected':fn,**controls}.items():unit+='\n'+content.replace('func_151382E0(',name+'(',1)+'\n'
unit+='''
typedef void(*Target)(Position161520*,s32,struct ActorEffectSurface*,u8,s32);
static int check(Target target) {int type,group,cat; const int cats[4]={0,1,2,255};
 D_800A4830=-2.5f;D_800A4834=3.5f;D_800A4838=-9;D_800A483C=11;D_800A4840=0.5f;
 for(type=0;type<20;type++)for(group=0;group<256;group++)for(cat=0;cat<4;cat++){
  D_800A3FE6[type*16]=cats[cat];wcat=cats[cat];wgroup=group;wcontext=type*1024+group+1;want.x=1+type;want.y=-3-group;want.z=9+cat;calls=error=0;
  target(&want,type,&surf,(u8)group,wcontext);if(error||calls!=(wcat!=2))return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;\n'''
for i,name in enumerate(controls):unit+='if(!check('+name+'))return '+str(20+i)+';\n'
unit+='return 0;}\n'+START
path=out/'interface-native.c';path.write_text(unit)
for opt in ('O0','O2','O3'):
 exe=out/('interface-native-'+opt);cmd=[*native_command('-'+opt,True),'-mstackrealign',str(path),'-o',str(exe)];p=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr;p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
print('native32: 20480 cases per optimization, O0/O2/O3 UBSan; six effective semantic controls')
