import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_scene_transition_dispatch_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'candidate_source.c').read_text(),'func_1501C730')
 controls={
  'reset':('    func_1501C53C();','    /* omitted reset */'),
  'clear':('    D_800D2132 = 0;','    D_800D2132 = 1;'),
  'command4':('        case 4:','        case 8:'),
  'arg4':('D_800BEA00[0] = arg4','D_800BEA00[0] = arg3'),
  'arg3':('D_800BEA04[0] = arg3','D_800BEA04[0] = arg4'),
  'channel':('D_800DD2C0 = channel','D_800DD2C0 = channel+1'),
  'prior':('D_800D2132 = D_800CC2D0[0].unkB2','D_800D2132 = 0'),
  'gate':('D_800BE616 == 0','D_800BE616 != 0'),
  'advance':('                func_15016680();','                /* omitted advance */'),
  'command5':('D_800BE9F4 = (u16 *)5','D_800BE9F4 = (u16 *)6'),
 }
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 _Static_assert(__builtin_offsetof(struct127,unkB2)==0xB2,"object field offset");
 struct127 D_800CC2D0[26];u16 D_800D2132;u8 D_800BE615,D_800BE616,D_800DD2C0;
 u16 *D_800BE9F4;s32 D_800BEA00[1],D_800BEA04[1];static u32 calls,mutation;
 void func_1501C53C(void){calls|=1;if(mutation){D_800BE616^=1;D_800CC2D0[0].unkB2=0x1234;D_800BE9F4=(u16 *)0xdeadbeefu;}}
 void func_15016680(void){calls|=2;if(mutation){D_800BE615=0x99;D_800D2132=0xbeef;}}
 '''
 code+='\n'+selected.replace('func_1501C730','test_selected',1)+'\n'
 for name,(a,b) in controls.items():
  assert a in selected,name;code+='\n'+selected.replace(a,b,1).replace('func_1501C730','control_'+name,1)+'\n'
 code+=r'''
 typedef void(*T)(s32,s32,s32,s32,s32);
 static int check(T f){static const u32 commands[]={0,1,2,3,4,5,6,7,8,255,0x7fffffffu,0x80000000u,0xffffffffu};u32 i,g,m;
 for(i=0;i<13;i++)for(g=0;g<3;g++)for(m=0;m<2;m++){
  u32 command=commands[i],mode=0x64,gate=g==2?255:g,channel=0xa5,prior=0x81f2,result=0xaaaa,scene=0x76543210u,a3=0x44556677u,a4=0x88776655u,want=1;
  calls=0;mutation=m;D_800BE615=mode;D_800BE616=gate;D_800DD2C0=channel;D_800CC2D0[0].unkB2=prior;D_800D2132=result;D_800BE9F4=(u16 *)scene;D_800BEA00[0]=a4;D_800BEA04[0]=a3;
  f((s32)command,(s32)0xfedcba98u,(s32)0xffffff80u,0x13579bdf,(s32)0x87654321u);
  if(m){gate^=1;prior=0x1234;scene=0xdeadbeefu;}result=0;
  if(command==4||command==6){a4=0x87654321u;a3=0x13579bdf;scene=0xfedcba98u;channel=0x80;mode=2;}
  else if(command==1||command==2){mode=3;scene=0xfedcba98u;result=prior;if(command==2)channel=0x80;}
  else if(command==3&&!gate){mode=m?0x99:4;result=m?0xbeef:0;want=3;}
  else if(command==5){scene=5;mode=1;}
  if(calls!=want||D_800BE615!=mode||D_800BE616!=gate||D_800DD2C0!=channel||D_800CC2D0[0].unkB2!=prior||D_800D2132!=result||(u32)D_800BE9F4!=scene||(u32)D_800BEA00[0]!=a4||(u32)D_800BEA04[0]!=a3)return 1;
 }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+=f'if(!check(control_{name}))return {20+i};\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True)
  assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-2000:],r.stderr[-2000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=78,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
