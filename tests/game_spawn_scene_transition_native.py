import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_spawn_scene_transition_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'candidate_source.c').read_text(),'func_1507DFE4')
 controls={
  'gate':('D_800C35EA == 1','D_800C35EA == 2'),
  'selection':('0, selection, 1','0, selection+1, 1'),
  'query_flag':('&flags, &signedTag, 1, &result','&flags, &signedTag, 0, &result'),
  'result_zero':('result == 0) sequence = 1','result == 0) sequence = 2'),
  'result_one':('result == 1) sequence = 3','result == 1) sequence = 2'),
  'coordinate':('position[0], position[1], position[2]','position[1], position[0], position[2]'),
  'scale':('1.40625f','1.4062f'),
  'angle_base':('+ 180.0f','+ 179.0f'),
  'scene':('D_800BE9F0 = 0x25','D_800BE9F0 = 0x24'),
  'dispatch_flag':('D_800C3671 = 1','D_800C3671 = 2'),
  'after_flag':('D_800C3670 = 1','D_800C3670 = 2'),
  'restore':('D_800BE9F0 = saved','D_800BE9F0 = saved+1'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 u8 D_800C35EA,D_800C3670,D_800C3671;s32 D_800BE9F0;
 static u32 calls,bad,byte,mutate;static s32 resultCode;
 static u32 word(f32 v){union {u32 u;f32 f;}x;x.f=v;return x.u;}
 s32 func_15084D70(s32 a,s32 b,s32 c,s16 *p,f32 *r,u8 *first,u8 *second,s32 *flags,s32 *tag,s32 one,s32 *result){
  calls++;if(calls!=1||a||b!=0x12345678||c!=1||one!=1)bad=1;p[0]=(s16)(0x8000+byte);p[1]=(s16)(0x7fff-byte);p[2]=(s16)(0xff00+byte);r[0]=1;r[1]=2;r[2]=3;*first=0xa5;*second=(u8)byte;*flags=0x11223344;*tag=0x55667788;*result=resultCode;if(mutate)D_800BE9F0=0x7aa12345;return 0;
 }
 void func_15022190(s16 x,s16 y,s16 z,f32 angle){calls++;if(calls!=2||x!=(s16)(0x8000+byte)||y!=(s16)(0x7fff-byte)||z!=(s16)(0xff00+byte)||word(angle)!=word(((s32)byte-64)*1.40625f+180.0f))bad=1;}
 void func_1501D348(s32 scene,s32 seq,s32 slot,s32 hook,s32 parameter){calls++;if(calls!=3||scene!=0x25||seq!=(resultCode?3:1)||slot||hook||parameter||D_800BE9F0!=0x25||D_800C3671!=1)bad=1;if(mutate){D_800BE9F0=(s32)0xdeadbeefu;D_800C3671=0x56;}}
 '''
 code+='\n'+selected.replace('func_1507DFE4','test_selected',1)+'\n'
 for name,(a,b)in controls.items():
  assert selected.count(a)==1,(name,selected.count(a));code+='\n'+selected.replace(a,b,1).replace('func_1507DFE4','control_'+name,1)+'\n'
 code+=r'''
 typedef void (*T)(s32,s32);
 static int check(T test){u32 gates[4]={0,1,2,255},results[4]={0,1,2,0xffffffffu},bytes[5]={0,63,64,127,255};u32 g,r,b,m;
  for(g=0;g<4;g++)for(r=0;r<4;r++)for(b=0;b<5;b++)for(m=0;m<2;m++){
   D_800C35EA=gates[g];resultCode=(s32)results[r];byte=bytes[b];mutate=m;calls=bad=0;D_800BE9F0=0x1234abcd;D_800C3670=0x83;D_800C3671=0x71;
   test(0x12345678,(s32)0xabcdef01u);
   if(D_800C35EA==1){if(calls||D_800BE9F0!=0x1234abcd||D_800C3670!=0x83||D_800C3671!=0x71)bad=1;}
   else if(resultCode!=0&&resultCode!=1){if(calls!=1||D_800BE9F0!=(mutate?0x7aa12345:0x1234abcd)||D_800C3670!=0x83||D_800C3671!=0x71)bad=1;}
   else if(calls!=3||D_800BE9F0!=(mutate?0x7aa12345:0x1234abcd)||D_800C3670!=1||D_800C3671!=(mutate?0x56:1))bad=1;
   if(bad)return 1;
  }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+=f'if(!check(control_{name}))return {20+i};\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-3000:],r.stderr[-3000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=160,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
