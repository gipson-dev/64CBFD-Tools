import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_localized_trail_preset_151dbaa8_match as p
out=p.out;root=p.root
from tools.tests import game_localized_trail_preset_151dbaa8_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_151DBAA8')
 controls={
  'point':('position[0] = point->unk0','position[0] = point->unk4'),
  'angle':('firstAngleBase = 0','firstAngleBase = 1'),
  'angle_range':('secondAngleBase = -64','secondAngleBase = -63'),
  'time':('timeBase = 5.5f','timeBase = 5.0f'),
  'time_range':('timeRange = D_800AB4C0','timeRange = D_800AB4C4'),
  'scale':('scaleBase = D_800AB4C4','scaleBase = D_800AB4C0'),
  'radius':('radiusBase = 10.0f','radiusBase = 11.0f'),
  'count':('countBase = count','countBase = count + 1'),
  'duration':('durationBase = 30','durationBase = 31'),
  'selector':('selector = selector','selector = selector ^ 1'),
  'chance':('opaqueChance = 0.5f','opaqueChance = 1.0f'),
  'first':('firstValue = 16','firstValue = 17'),
  'request_value':('requestValue = 0','requestValue = 1'),
  'helper_arg':('&preset.localized, 0, mode, request','&preset.localized, 1, mode, request'),
  'mode':('&preset.localized, 0, mode, request','&preset.localized, 0, mode ^ 1, request'),
  'request':('&preset.localized, 0, mode, request','&preset.localized, 0, mode, request ^ 1'),
 }
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {s16 firstAngleBase,firstAngleRange,secondAngleBase,secondAngleRange;} AngularTrailInput151DBAA8;
 typedef struct {f32 position[3],timeBase,timeRange,scaleBase,scaleRange,radiusBase,radiusRange;s16 countBase,countRange,requestSelectorBase,requestSelectorRange,durationBase,durationRange,modeBase,modeRange;u8 selector,private35[3];f32 opaqueChance;s16 firstValue,secondValue;s32 requestValue;} LocalizedTrailInput151DBAA8;
 typedef struct {AngularTrailInput151DBAA8 angular;LocalizedTrailInput151DBAA8 localized;} TrailPreset151DBAA8;
 _Static_assert(sizeof(AngularTrailInput151DBAA8)==8 && sizeof(TrailPreset151DBAA8)==0x4c && __builtin_offsetof(TrailPreset151DBAA8,localized.selector)==0x3c && __builtin_offsetof(TrailPreset151DBAA8,localized.requestValue)==0x48,"preset layout");
 f32 D_800AB4C0,D_800AB4C4,D_800AB4C8,D_800AB4CC;
 struct Case {u32 point[3];s32 count;u32 selector,mode,request,mutate;};
 static const struct Case cases[]={
 '''
 for c in g.cases():code+='{{'+','.join('0x%Xu'%v for v in c.point)+'},'+str(c.count)+','+','.join('0x%Xu'%v for v in (c.selector,c.mode,c.request,c.mutate))+'},\n'
 code+=r'''};
 static const struct Case *current;static struct17 *current_point;static s32 calls,bad;
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(const f32*src){u32 x=0,i;u8*d=(u8*)&x;const u8*s=(const u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 void func_15153F18(AngularTrailInput151DBAA8*a,LocalizedTrailInput151DBAA8*b,s32 flags,s32 mode,s32 request){
  u32 i;calls++;if((u8*)b!=(u8*)a+8||flags!=0||(u32)mode!=(current->mode&255)||(u32)request!=current->request)bad=1;
  if(a->firstAngleBase!=0||a->firstAngleRange!=255||a->secondAngleBase!=-64||a->secondAngleRange!=46)bad=1;
  for(i=0;i<3;i++)if(get_bits(&b->position[i])!=current->point[i])bad=1;
  if(get_bits(&b->timeBase)!=0x40b00000||get_bits(&b->timeRange)!=0x403c28f5||get_bits(&b->scaleBase)!=0x3f1ced92||get_bits(&b->scaleRange)!=0x3f1a5e36||get_bits(&b->radiusBase)!=0x41200000||get_bits(&b->radiusRange)!=0x41233333)bad=1;
  if((u16)b->countBase!=((u32)current->count&0xffff)||b->countRange!=0||b->requestSelectorBase!=3||b->requestSelectorRange!=2||b->durationBase!=30||b->durationRange!=30||b->modeBase!=155||b->modeRange!=100||b->selector!=(current->selector&255)||get_bits(&b->opaqueChance)!=0x3f000000||b->firstValue!=16||b->secondValue!=15||b->requestValue!=0)bad=1;
  if(current->mutate){put_bits(&current_point->unk0,0xdeadbeef);put_bits(&D_800AB4C0,0x12345678);}
 }
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_151DBAA8','test_'+key,1)+'\n'
 code+=r'''
 typedef void(*T)(struct17*,s32,u8,u8,s32);
 static int check(T test){u32 n;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];struct17 point;put_bits(&point.unk0,c->point[0]);put_bits(&point.unk4,c->point[1]);put_bits(&point.unk8,c->point[2]);put_bits(&D_800AB4C0,0x403c28f5);put_bits(&D_800AB4C4,0x3f1ced92);put_bits(&D_800AB4C8,0x3f1a5e36);put_bits(&D_800AB4CC,0x41233333);
  current=c;current_point=&point;calls=bad=0;test(&point,c->count,(u8)c->selector,(u8)c->mode,(s32)c->request);
  if(bad||calls!=1||get_bits(&point.unk0)!=(c->mutate?0xdeadbeef:c->point[0])||get_bits(&point.unk4)!=c->point[1]||get_bits(&point.unk8)!=c->point[2]||get_bits(&D_800AB4C0)!=(c->mutate?0x12345678:0x403c28f5))return 1;
  }return 0;}
 static int run(void){int v=check(test_selected);if(v)return v;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_151DBAA8_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_151DBAA8_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helper='modeled',initialized_packet_fields_only=True,source_installed=False);(out/'native_151DBAA8_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
