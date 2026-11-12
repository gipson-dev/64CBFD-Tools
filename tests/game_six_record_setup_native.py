import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_six_record_setup_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'candidate_source.c').read_text(),'func_15010110')
 controls={
  'first_object':('D_800B0E00[0]','D_800B0E00[1]'),
  'second_object':('D_800B0E00[1]','D_800B0E00[0]'),
  'setup_argument':('0, 1, 0, -8','0, 2, 0, -8'),
  'loop_count':('i < 6','i < 5'),
  'record_index':('record.unk0 = i + 1','record.unk0 = i'),
  'first_source':('record.unk4 = D_800963A0[i]','record.unk4 = D_800963A0[0]'),
  'distance':('record.unk4.unk4 - record.unk4.unk10','record.unk4.unk4 + record.unk4.unk10'),
  'initial_flag':('record.unk20 = 0','record.unk20 = 1'),
 }
 code=r'''#include <ultra64.h>
 #include "functions.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 s32 D_800B0E00[2],D_80090298[32];struct180 D_800963A0[6];
 static u32 calls,bad,mutate,phase;
 static u32 word(f32 v){union {u32 u;f32 f;}x;x.f=v;return x.u;}
 f32 fabsf(f32 v){union {u32 u;f32 f;}x;x.f=v;x.u&=0x7fffffff;return x.f;}
 void *func_15195AA8(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h){
  u32 index=calls++;if(index>1||(u32)a!=(index?(mutate?0x87654321u:0x56780000u+phase):0x12340000u+phase)||(u32)b!=(index&&mutate?0xabcdef12u:0x13570000u+phase)||c||d!=-1||e||f!=(s32)index||g||h!=-8)bad=1;
  if(index==0&&mutate){D_800B0E00[1]=(s32)0x87654321u;D_80090298[20]=(s32)0xabcdef12u;}return 0;
 }
 s32 func_151ACBD4(struct179 *p,s32 mode){u32 i=calls-2;struct180 *v;calls++;if(i>=6||mode||p->unk0!=(s8)(i+1)||p->unk20!=(s8)((mutate&&(i&1))?0x5a:0)){bad=1;return 0;}
  v=&D_800963A0[i];if(p->unk4.unk0!=v->unk0||word(p->unk4.unk4)!=word(v->unk4)||p->unk4.unk8!=v->unk8||p->unk4.unkC!=v->unkC||word(p->unk4.unk10)!=word(v->unk10)||p->unk4.unk14!=v->unk14||word(p->unk1C)!=word(fabsf(v->unk4-v->unk10)))bad=1;
  if(mutate){p->unk20^=0x5a;if(i<5)D_800963A0[i+1].unk4=-18.25f-(f32)i;}return 0;
 }
 '''
 code+='\n'+selected.replace('func_15010110','test_selected',1)+'\n'
 for name,(a,b)in controls.items():
  assert selected.count(a)==1,name
  code+='\n'+selected.replace(a,b,1).replace('func_15010110','control_'+name,1)+'\n'
 code+=r'''
 typedef void (*T)(void);
 static int check(T test){u32 i,m,p;for(m=0;m<2;m++)for(p=0;p<64;p++){
  mutate=m;phase=p;calls=bad=0;D_800B0E00[0]=0x12340000+p;D_800B0E00[1]=0x56780000+p;D_80090298[20]=0x13570000+p;
  for(i=0;i<6;i++){D_800963A0[i].unk0=i+17;D_800963A0[i].unk4=(f32)((s32)i-(s32)p);D_800963A0[i].unk8=i*3;D_800963A0[i].unkC=i*4;D_800963A0[i].unk10=(f32)((s32)p-2*(s32)i);D_800963A0[i].unk14=i*5;}
  test();if(bad||calls!=8)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+=f'if(!check(control_{name}))return {20+i};\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-3000:],r.stderr[-3000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=128,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
