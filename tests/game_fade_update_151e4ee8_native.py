def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_fade_update_151e4ee8_match as packet
 root=packet.ROOT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet.OUT
 fn=body(packet.MANIFEST['selected_source'],'func_151E4EE8')
 controls={
  'rate':('D_8008FD74 == 255','D_8008FD74 != 255'),
  'gate':('D_800DDDC8 > D_800ABA2C','D_800DDDC8 < D_800ABA2C'),
  'split':('alpha < 0x55','alpha < 0x56'),
  'done':('alpha < 0x6E','alpha < 0x6F'),
  'clamp':('next >= 256','next > 256'),
  'completion':('D_8008FD74 = 8','D_8008FD74 = 9'),
 }
 pre='''#include <ultra64.h>
 extern u8 D_800E0B96,D_8008FD74;
 extern s32 D_800BE9E4,D_800E0A88;
 extern f32 D_8008FDD0,D_800DDDC8,D_800DDDD8,D_800ABA2C,D_800ABA30,D_800ABA34;
 '''
 code=pre+fn.replace('func_151E4EE8(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert fn.count(old)==1,name
  code+=fn.replace('func_151E4EE8(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 u8 D_800E0B96,D_8008FD74;s32 D_800BE9E4,D_800E0A88;
 f32 D_8008FDD0,D_800DDDC8,D_800DDDD8,D_800ABA2C,D_800ABA30,D_800ABA34;
 typedef union {u32 u;f32 f;} Word;
 static f32 number(u32 n){Word w;w.u=n;return w.f;}
 static u32 word(f32 f){Word w;w.f=f;return w.u;}
 static int called,callback_bad;
 static void callback(void){called++;if(D_800E0B96!=255 || D_8008FD74!=8 || D_8008FDD0!=1.0f)callback_bad=1;D_800E0B96=23;D_8008FD74=7;D_8008FDD0=0.5f;}
 typedef void (*Fn)(void);
 static int check(Fn fn) {
  static const u8 alphas[]={0,1,84,85,109,110,254,255};
  static const u8 rates[]={0,1,8,254,255};
  static const u32 ticks[]={0,1,0xff,0xffffffff,0x7fffffff,0x80000000};
  static const u32 levels[]={0,0x3f000000,0x3f800000,0x7fc00000};
  for(int a=0;a<8;a++)for(int r=0;r<5;r++)for(int t=0;t<6;t++)for(int l=0;l<4;l++)for(int k=0;k<4;k++){
   u32 alpha=alphas[a],rate=rates[r],tick=ticks[t],audio=0xc1234567,fade=word(1.0f-((f32)alpha/255.0f));int cb=0;f32 level=number(levels[l]),threshold=number(levels[k]);
   if(rate==255){if(level>threshold){alpha=(alpha+tick)&255;audio=alpha<85?0x3eaaaaab:0x3f000001;}if(!(level<1.0f)&&alpha>=110)cb=1;}
   else if(alpha==255)cb=1;
   else {s32 next=(s32)(alpha+tick*rate);alpha=(u8)(next>=256?255:next);}
   if(cb){alpha=23;rate=7;fade=word(0.5f);}
   D_800E0B96=alphas[a];D_8008FD74=rates[r];D_800BE9E4=(s32)tick;D_800E0A88=(s32)callback;
   D_8008FDD0=number(0xdeadbeef);D_800DDDC8=level;D_800DDDD8=number(0xc1234567);D_800ABA2C=threshold;D_800ABA30=number(0x3eaaaaab);D_800ABA34=number(0x3f000001);called=callback_bad=0;
   fn();
   if(D_800E0B96!=alpha || D_8008FD74!=rate || word(D_8008FDD0)!=fade || word(D_800DDDD8)!=audio || called!=cb || callback_bad)return 1;
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
  print(opt,'3840 fade cases,',len(controls),'effective negative controls, UBSan',flush=True)
