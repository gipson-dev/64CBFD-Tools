import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_effect_ground_motion_150eae24_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'selected-source.c').read_text(),'func_150EAE24')
 controls={'advance_x':('motion->x += motion->dx * D_800BE9A4','motion->x -= motion->dx * D_800BE9A4'),'advance_z':('motion->z += motion->dz * D_800BE9A4','motion->z -= motion->dz * D_800BE9A4'),'point_y':('position[1] = motion->height','position[1] = motion->queryHeight'),'output_x':('record->unk14->unkE = (s32)motion->x','record->unk14->unkE = (s32)motion->z'),'output_z':('record->unk14->unk12 = (s32)motion->z','record->unk14->unk12 = (s32)motion->x'),'query':('0, motion->queryHeight, &motion->result','0, motion->height, &motion->result'),'hit_height':('record->unk14->unk10 = (s32)motion->result.height','record->unk14->unk10 = (s32)motion->height'),'miss_height':('record->unk14->unk10 = (s32)motion->height','record->unk14->unk10 = (s32)motion->queryHeight'),'lifetime':('motion->remaining -= D_800BE9A4','motion->remaining += D_800BE9A4')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {f32 height;s16 vertices[9];s16 pad16;u32 metadata;u8 flags;u8 state;u16 pad1e;s32 value;} HeightResult71820;
 typedef struct {f32 x,z,dx,dz,height,queryHeight,remaining;HeightResult71820 result;} EffectMotion;
 typedef struct {u8 pad[14];s16 unkE,unk10,unk12;} struct226;
 typedef struct {u8 pad[20];struct226 *unk14;EffectMotion motion;} struct225;
 _Static_assert(__builtin_offsetof(struct225,unk14)==0x14 && __builtin_offsetof(struct225,motion)==0x18,"record layout");
 _Static_assert(__builtin_offsetof(EffectMotion,result)==0x1c,"result layout");
 static struct225 rec;static struct226 out1,out2;f32 D_800BE9A4;static int mutation,answer,bad,called;static f32 ex,ez,eh,eq;
 s32 func_15046C80(f32 *point,u16 kind,f32 query,HeightResult71820 *res){called++;if(point[0]!=ex||point[1]!=eh||point[2]!=ez||kind||query!=eq||res!=&rec.motion.result)bad=1;if(mutation){rec.unk14=&out2;rec.motion.height=-11.5f;D_800BE9A4=.25f;}res->height=19.75f;return answer;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,z,1) for n,(a,z) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_150EAE24','test_'+key,1)+'\n'
 code+=r'''
 typedef s32(*Fn)(struct225*);
 static int check(Fn test){int sample,i;for(sample=0;sample<4;sample++)for(answer=0;answer<2;answer++)for(mutation=0;mutation<2;mutation++){
  f32 x,z,dx,dz,height,query,remain,delta;int ret;struct226 *out;
  x=sample==0?1.25f:sample==1?-5.75f:sample==2?0.f:123.75f;
  z=sample==0?-2.75f:sample==1?6.5f:sample==2?0.f:-110.25f;
  dx=sample==0?.5f:sample==1?-2.f:sample==2?0.f:3.f;
  dz=sample==0?-1.5f:sample==1?.5f:sample==2?0.f:-2.f;
  height=sample==0?8.5f:sample==1?-8.5f:sample==2?-1.f:5.f;
  query=sample==0?-2.25f:sample==1?4.f:sample==2?1.f:-10.f;
  remain=sample==0?2.f:sample==1?.25f:sample==2?0.f:-.5f;
  delta=sample==0?.5f:sample==1?.5f:sample==2?1.f:.25f;
  rec.unk14=&out1;rec.motion.x=x;rec.motion.z=z;rec.motion.dx=dx;rec.motion.dz=dz;rec.motion.height=height;rec.motion.queryHeight=query;rec.motion.remaining=remain;rec.motion.result.height=0.f;D_800BE9A4=delta;
  out1.unkE=out1.unk10=out1.unk12=-30000;out2.unkE=out2.unk10=out2.unk12=-30000;
  ex=x+dx*delta;ez=z+dz*delta;eh=height;eq=query;bad=called=0;ret=test(&rec);
  if(bad||called!=1||rec.motion.x!=ex||rec.motion.z!=ez||out1.unkE!=(s16)(s32)ex||out1.unk12!=(s16)(s32)ez)return 1;
  out=mutation?&out2:&out1;if(out->unk10!=(s16)(s32)(answer?19.75f:mutation?-11.5f:height))return 2;
  if(mutation && out1.unk10!=-30000)return 3;
  if(rec.motion.remaining!=remain-(mutation?.25f:delta)||ret!=(remain-(mutation?.25f:delta)>0.f))return 4;
  for(i=0;i<3;i++)if(rec.pad[i]){} /* no additional access assumptions */
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=16,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,finite_float_only=True,modeled_layout=True,helper_modeled=True,source_installed=False);(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
