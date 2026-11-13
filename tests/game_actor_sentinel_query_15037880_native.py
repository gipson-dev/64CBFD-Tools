def run():
 from pathlib import Path
 import sys,subprocess
 from tools.experiments import game_actor_sentinel_query_15037880_match as packet
 root=packet.ROOT;out=packet.OUT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 fn=body(packet.MANIFEST['selected_source'],'func_15037880')
 controls={
  'mask':('& 7;','& 3;'),
  'first':(' + 0x2F8);',' + 0x2FC);'),
  'second':(' + 0x2FC);',' + 0x300);'),
  'type':('actor[5] == 4','actor[5] != 4'),
  'distance':(' > D_8009862C',' < D_8009862C'),
  'zref':('D_800C3FF4[2];','D_800C3FF4[0];'),
  'mode3':('if (mode == 3) return 1;','if (mode == 3) return 0;'),
  'default':('    return 0;\n}', '    return 1;\n}'),
  'far':('if (dx * dx + dz * dz > D_8009862C) return 1;','if (dx * dx + dz * dz > D_8009862C) return 0;'),
 }
 pre=r'''
 #include <ultra64.h>
 struct struct108 {u8 data[0x304];};
 extern struct struct108 *D_800DBFF0;extern s16 D_800C3FF4[];extern f32 D_8009862C;extern u8 D_800CC2D0[];
 '''
 code=pre+fn.replace('func_15037880(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert fn.count(old)>=1,(name,old);code+=fn.replace('func_15037880(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+=r'''
 u8 D_800CC2D0[3*0x32c] __attribute__((aligned(4)));s16 D_800C3FF4[3];f32 D_8009862C;
 static struct struct108 view;struct struct108 *D_800DBFF0=&view;
 typedef union {u32 u;f32 f;} Word;static u32 fbits(f32 v){Word w;w.f=v;return w.u;}static f32 number(u32 v){Word w;w.u=v;return w.f;}
 typedef s32 (*Fn)(s32,f32 *);
 static int check(Fn fn) {
  static const s16 refs[4][3]={{0,-7,0},{3,-32768,4},{-32768,1,32767},{32767,-1,-32768}};
  static const u32 thresholds[]={0,0x41c80000,0x7f800000,0x7fc12345,0xbf800000};static const int kinds[]={0,4,255};
  for(int index=0;index<3;index++)for(int mode=0;mode<8;mode++)for(int k=0;k<3;k++)for(int r=0;r<4;r++)for(int t=0;t<5;t++){
   u8 *a=D_800CC2D0+index*0x32c;u32 result[3]={0xdeadbeef,0xdeadbeef,0xdeadbeef},expected[3]={0xdeadbeef,0xdeadbeef,0xdeadbeef};
   *(u16 *)(a+0x2f8)=0xa5f8|mode;a[5]=kinds[k];*(f32 *)(a+0x14)=3.0f;*(f32 *)(a+0x1c)=4.0f;
   D_800C3FF4[0]=refs[r][0];D_800C3FF4[1]=refs[r][1];D_800C3FF4[2]=refs[r][2];D_8009862C=number(thresholds[t]);
   *(u32 *)(view.data+0x2f8)=0x3f800000;*(u32 *)(view.data+0x2fc)=0x80000000;*(u32 *)(view.data+0x300)=0x7fc12345;
   int answer=0;if(mode==1){answer=1;expected[0]=0x3f800000;expected[1]=0x80000000;expected[2]=0x7fc12345;}
   else if(mode==2){answer=1;f32 dx=3.0f-(f32)refs[r][0],dz=4.0f-(f32)refs[r][2];if(kinds[k]!=4 || !(dx*dx+dz*dz>D_8009862C)){for(int j=0;j<3;j++)expected[j]=fbits((f32)refs[r][j]);}}
   else if(mode==3)answer=1;
   if(fn(index,(f32 *)result)!=answer)return 1;for(int j=0;j<3;j++)if(result[j]!=expected[j])return 2;
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'1440 query cases,',len(controls),'negative controls, UBSan',flush=True)
