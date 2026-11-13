def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_hud_state_15178eb0_match as packet
 root=packet.ROOT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet.OUT
 source=packet.MANIFEST['selected_source'];first=body(source,'func_15178EB0');second=body(source,'func_15178EFC')
 controls_first={'init_timer':('D_800DD444 = 600','D_800DD444 = 599'),'init_color':('D_800DD433 = 20','D_800DD433 = 21'),'init_list':('D_800DD440 = 0','D_800DD440 = (u8 **)1')}
 controls_second={'state':('state == 2','state != 2'),'limit':('i < 300','i < 299'),'flag':('D_800DD446 == 3','D_800DD446 == 4'),'sound':('func_100111C8(D_800DD430)','func_100111C8(D_800DD430 + 1)'),'finish':('D_800DD436 = 0','D_800DD436 = 1')}
 pre='''#include <ultra64.h>
 extern u8 D_800DD432,D_800DD433,D_800DD434;extern s8 D_800DD446;extern s16 D_800DD444,D_800DD436;extern u16 D_800DD430;extern u8 **D_800DD440;
 void func_1516972C(void *);void func_10004074(void *);void func_100111C8(u16);
 '''
 code=pre+first.replace('func_15178EB0(','selected_init(',1)+'\n'+second.replace('func_15178EFC(','selected_trans(',1)+'\n'
 for name,(old,new) in controls_first.items():
  assert first.count(old)==1,name
  code+=first.replace('func_15178EB0(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 for name,(old,new) in controls_second.items():
  assert second.count(old)==1,name
  code+=second.replace('func_15178EFC(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 u8 D_800DD432,D_800DD433,D_800DD434;s8 D_800DD446;s16 D_800DD444,D_800DD436;u16 D_800DD430;u8 **D_800DD440;
 static u8 *arrayA[300],*arrayB[300],*expectA[300],*expectB[300];
 static u32 logtype[16],logarg[16],count,disposeCount,plan;
 static void event(u32 kind,u32 value){logtype[count]=kind;logarg[count]=value;count++;}
 void func_1516972C(void *p){
  event(1,(u32)p);disposeCount++;
  if(disposeCount==1&&plan==1)D_800DD440=arrayB;
  if(disposeCount==1&&plan==2){D_800DD430=0x4567;D_800DD446=9;}
 }
 void func_10004074(void *p){event(2,(u32)p);if(plan==2)D_800DD440=arrayB;}
 void func_100111C8(u16 p){event(3,p);if(plan==2){D_800DD444=0x1111;D_800DD436=0x2222;}}
 typedef void (*Init)(void);typedef void (*Trans)(s32);
 static void reset(int status,int array,int pl){
  static const int ids[]={0,1,149,150,299};
  for(int i=0;i<300;i++)arrayA[i]=arrayB[i]=0;
  for(int k=0;k<5;k++){int i=ids[k];arrayA[i]=(u8 *)(0x70000+16*i);arrayB[i]=(u8 *)(0x74000+16*i);}
  D_800DD440=array?arrayA:0;D_800DD430=0x9876;D_800DD436=0x1234;D_800DD444=0x4321;
  D_800DD434=0x71;D_800DD432=0x72;D_800DD433=0x73;D_800DD446=(s8)status;plan=pl;count=disposeCount=0;
 }
 static int check_init(Init fn){
  for(int st=0;st<4;st++)for(int array=0;array<2;array++){
   reset(st,array,0);fn();
   if(D_800DD434||D_800DD446||D_800DD444!=600||D_800DD432!=240||D_800DD433!=20||D_800DD436||D_800DD440||count)return 1;
  }
  return 0;
 }
 static int check_trans(Trans fn){
  static const int states[]={0,1,2,3,-1};static const int statuses[]={0,1,3,255};
  for(int st=0;st<5;st++)for(int fl=0;fl<4;fl++)for(int array=0;array<2;array++)for(int pl=0;pl<3;pl++){
   u32 want_type[16],want_arg[16],n=0,ordinal=0;u8 mode=0x71;s8 status=(s8)statuses[fl];s16 timer=0x4321,counter=0x1234;u16 handle=0x9876;u8 **live;
   reset(statuses[fl],array,pl);
   for(int i=0;i<300;i++){expectA[i]=arrayA[i];expectB[i]=arrayB[i];}live=array?arrayA:0;
   if(states[st]==2){
    mode=status=0;
    if(live){
     for(int i=0;i<300;i++){
      u8 **model=live==arrayA?expectA:expectB;u8 *obj=model[i];
      if(obj){ordinal++;want_type[n]=1;want_arg[n++]=(u32)obj;if(ordinal==1&&pl==1)live=arrayB;if(ordinal==1&&pl==2){handle=0x4567;status=9;}model=live==arrayA?expectA:expectB;model[i]=0;}
     }
     want_type[n]=2;want_arg[n++]=(u32)live;if(pl==2)live=arrayB;live=0;
    }
    want_type[n]=3;want_arg[n++]=handle;timer=counter=0;
   } else if(states[st]==3){if(!status)timer=600;else if(status==3)status=1;mode=3;}
   else mode=(u8)states[st];
   fn(states[st]);
   if(D_800DD434!=mode||D_800DD446!=status||D_800DD444!=timer||D_800DD436!=counter||D_800DD430!=handle||D_800DD440!=live||count!=n)return 1;
   for(u32 i=0;i<n;i++)if(logtype[i]!=want_type[i]||logarg[i]!=want_arg[i])return 2;
   for(int i=0;i<300;i++)if(arrayA[i]!=expectA[i]||arrayB[i]!=expectB[i])return 3;
  }
  return 0;
 }
 static int run(void){if(check_init(selected_init)||check_trans(selected_trans))return 10;
 '''
 for i,name in enumerate(controls_first):code+='if(!check_init(bad_'+name+'))return '+str(20+i)+';\n'
 for i,name in enumerate(controls_second):code+='if(!check_trans(bad_'+name+'))return '+str(30+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'8 reset and 120 transition cases,',len(controls_first)+len(controls_second),'effective negative controls, UBSan',flush=True)
