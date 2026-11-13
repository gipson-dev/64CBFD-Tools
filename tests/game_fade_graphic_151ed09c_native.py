def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_fade_graphic_151ed09c_match as packet
 root=packet.ROOT
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet.OUT;source=packet.MANIFEST['selected_source'];anchor='Gfx *func_151ED09C('
 function=anchor+source.split(anchor,1)[1].split('\n}',1)[0]+'\n}'
 controls={'clamp':('alpha = 255','alpha = 254'),'timer':('<< 2','<< 1'),'image1':('D_8009181C, 146','D_8009181C, 145'),'combine':('0xFCFFD3FF','0xFCFFD3FE'),'image2':('D_80091828, 146','D_80091828, 145'),'bias':('((u32)alpha + 1u)','((u32)alpha + 2u)'),'color':('255, 128, 32','255, 129, 32')}
 code='''#include <ultra64.h>
 extern s32 D_800E0A90;extern u8 D_800E0B97;extern Gfx D_80090028;extern u8 D_8009181C[],D_80091828[];
 Gfx *func_151ED430(Gfx *,u8 *,s32,s32,s32,s32,f32,s32);u8 *func_15096934(u8 *);
 '''+function.replace('func_151ED09C(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert old in function,name
  code+=function.replace('func_151ED09C(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 s32 D_800E0A90;u8 D_800E0B97;Gfx D_80090028;u8 D_8009181C[4],D_80091828[4];
 static Gfx base[32],layer[32],endbuf[32];static int calls,broken,mut,alias;static u8 level;
 Gfx *func_151ED430(Gfx *p,u8 *img,s32 x,s32 y,s32 width,s32 height,f32 scale,s32 flags){
  calls++;if(x!=146||y!=108||width!=8||height!=3||scale!=1.0f||flags||img!=(calls==1?D_8009181C:D_80091828)||p!=(calls==1?base+2:(alias?base:layer)+3))broken=1;
  if(mut&&calls==1){D_800E0B97=255-level;D_800E0A90=0x12345678;}
  return alias?(calls==1?base:base+4):(calls==1?layer:endbuf);
 }
 u8 *func_15096934(u8 *p){Gfx *g=(Gfx *)p;calls++;if(g!=(alias?base+4:endbuf))broken=1;g->words.w0=0xde000000;g->words.w1=0x80087408;return p+8;}
 typedef Gfx *(*Fn)(Gfx *);
 static int check(Fn fn){static const u32 timers[]={0,1,63,64,255,0x1fffffff,0x20000000,0x7fffffff,0x80000000,0xffffffff};static const int levels[]={0,1,127,255};
  for(int t=0;t<10;t++)for(int l=0;l<4;l++)for(int m=0;m<2;m++)for(int a=0;a<2;a++){
   for(int i=0;i<32;i++){base[i].words.w0=base[i].words.w1=0x5a5a5a5a;layer[i]=endbuf[i]=base[i];}
   D_800E0A90=(s32)timers[t];D_800E0B97=level=levels[l];mut=m;alias=a;calls=broken=0;
   s32 alpha=(s32)(timers[t]<<2);if(alpha>=256)alpha=255;u32 scaled=((s32)((u32)(m?255-level:level)*((u32)alpha+1u))>>8)&255;Gfx *r=fn(base);Gfx *second=alias?base:layer;
   if(broken||calls!=3||r!=(alias?base+5:endbuf+1))return 1;
   if(!alias&&(base[0].words.w0!=0xde000000||base[0].words.w1!=(u32)&D_80090028||base[1].words.w0!=0xfb000000||base[1].words.w1!=(0xffffff00u|((u32)alpha&255))))return 2;
   if(second[0].words.w0!=0xe7000000||second[0].words.w1||second[1].words.w0!=0xfcffd3ff||second[1].words.w1!=0xffa6ff7f||second[2].words.w0!=0xfb000000||second[2].words.w1!=(0xff802000u|scaled))return 3;
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
  print(opt,'160 cases,',len(controls),'effective negative controls, UBSan',flush=True)
