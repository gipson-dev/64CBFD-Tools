def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_contact_effect_1516a3f4_match as packet
 root=packet.ROOT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet.OUT;source=packet.MANIFEST['selected_source'];function=body(source,'func_1516A3F4')
 controls={'limit':('height >= threshold','height > threshold'),'mode':('func_1510F800(0)','func_1510F800(1)'),'offset':('+ 10u','+ 11u'),'scale':('/ 5100 + 204','/ 5100 + 205'),'type':('effect.type = 3','effect.type = 4'),'zero':('*(s16 *)(record + 0x38) = 0','*(s16 *)(record + 0x38) = 1'),'damp':('record + 0x28) = threshold','record + 0x28) = height')}
 code='''#include <ultra64.h>
 typedef struct {u32 tag;s16 zero,extent,x,y,z,size1,size2;u8 flag,padding,type,alpha;} ContactEffect1516A3F4;
 extern u32 D_8008CADC;extern f32 D_800A6CC8;
 void func_1510F800(s32);s32 func_1510F8D8(s16,s16,s16,s32);void func_15167AD8(void *,u8,s32);
 '''+function.replace('func_1516A3F4(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert old in function,name
  code+=function.replace('func_1516A3F4(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 u32 D_8008CADC=0x1234fedc;f32 D_800A6CC8=0.5f;
 static s32 result,mutation,events,broken;static u8 *active;
 static s16 get16(int off){return *(s16 *)(active+off);}
 void func_1510F800(s32 n){events|=1;if(n)broken=1;if(mutation){*(s16 *)(active+0x20)=-50;*(s16 *)(active+0x22)=272;active[0x3b]=183;}}
 s32 func_1510F8D8(s16 x,s16 y,s16 z,s32 n){events|=2;if(x!=get16(0x20)||y!=get16(0x22)||z!=get16(0x24)||n)broken=1;if(mutation){*(s16 *)(active+0x24)=-64;active[0x0c]=68;}return result;}
 void func_15167AD8(void *ptr,u8 one,s32 two){ContactEffect1516A3F4 *e=ptr;s32 v=((s32)active[0x3b]*4096)/5100+204;events|=4;
  if(e->tag!=0x1234fedc||e->zero||e->extent!=256||e->x!=get16(0x20)||e->y!=(s16)((u32)*(s32 *)(active+0x14)+10u)||e->z!=get16(0x24)||e->size1!=v||e->size2!=v||e->flag||e->type!=3||e->alpha!=active[0x3b]||one!=active[0x0c]||two!=active[1])broken=1;
 }
 typedef void (*Fn)(u8 *);
 static int check(Fn fn){static const s32 hs[]={-2147483647,0,127,128,2147483647};static const s32 floors[]={-2147483647,127,128,2147483647};static const int alphas[]={0,1,127,255};u32 words[32];
  for(int h=0;h<5;h++)for(int f=0;f<4;f++)for(int a=0;a<4;a++)for(int mut=0;mut<2;mut++){
   for(int i=0;i<32;i++)words[i]=0;active=(u8 *)words;*(s32 *)(active+0x14)=hs[h];*(s16 *)(active+0x20)=128;*(s16 *)(active+0x22)=96;*(s16 *)(active+0x24)=32752;*(s16 *)(active+0x26)=-71;*(s16 *)(active+0x28)=177;*(s16 *)(active+0x2a)=32;*(s16 *)(active+0x38)=0x1234;active[0x3b]=alphas[a];active[0xc]=162;active[1]=195;result=floors[f];mutation=mut;events=broken=0;
   int called=hs[h]>=128;int height=called?floors[f]:hs[h];int effect=height>=128 && (s32)((u32)128-(u32)height)<50;int want=(called?3:0)|(effect?4:0);
   fn(active);if(broken||events!=want||*(s32 *)(active+0x14)!=height)return 1;
   if(height>=128){if(*(s16 *)(active+0x38)!=0)return 2;}else if(*(s16 *)(active+0x26)!=-35||*(s16 *)(active+0x28)!=88)return 3;
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
