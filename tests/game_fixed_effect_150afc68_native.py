def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_fixed_effect_150afc68_match as packet_module
 root=packet_module.ROOT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet_module.OUT;source=packet_module.MANIFEST['selected_source'];function=body(source,'func_150AFC68');prototype='void func_1516D99C('+source.split('void func_1516D99C(',1)[1].split(');',1)[0]+')'
 controls={'kind':('0, 0, 13, 0','0, 0, 12, 0'),'scale':('170, 170, 170, 170','171, 170, 170, 170'),'input0':('0, arg0, 240','0, arg0 ^ 1, 240'),'input1':('0, 0, 0, arg1, 0','0, 0, 0, arg1 ^ 1, 0'),'input2':('arg2, arg3, 0','arg2 ^ 1, arg3, 0'),'input3':('arg2, arg3, 0','arg2, arg3 ^ 1, 0'),'input4':('0, arg4, arg5','0, arg4 ^ 1, arg5'),'input5':('0, arg4, arg5','0, arg4, arg5 ^ 1')}
 code='#include <ultra64.h>\nstatic u32 captured[49],count;\n'+prototype+'{u32 values[49]={'+','.join('arg%d'%i for i in range(49))+'};count++;for(int i=0;i<49;i++)captured[i]=values[i];}\n'+function.replace('func_150AFC68(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert function.count(old)==1,name
  code+=function.replace('func_150AFC68(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 typedef void (*Fn)(s32,s32,s32,s32,u8,s32);
 static int check(Fn fn){
  for(u32 i=0;i<2048;i++){
   u32 args[6],e[49]={0};for(int j=0;j<6;j++)args[j]=i*1664525u+(u32)j*0x372159abu+1013904223u;
   e[0]=1;e[3]=13;e[12]=4;e[16]=e[17]=e[18]=e[20]=255;e[22]=1;e[27]=e[28]=e[29]=e[30]=170;
   e[31]=args[2]&65535;e[32]=args[3]&255;e[34]=args[0]&255;e[35]=240;e[36]=e[37]=80;e[38]=1;e[39]=4;e[41]=1;e[45]=args[1]&255;e[47]=args[4]&255;e[48]=args[5];
   count=0;fn((s32)args[0],(s32)args[1],(s32)args[2],(s32)args[3],(u8)args[4],(s32)args[5]);
   if(count!=1)return 1;for(int j=0;j<49;j++)if(captured[j]!=e[j])return 2;
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'2048 complete-packet cases,',len(controls),'effective negative controls, UBSan',flush=True)
