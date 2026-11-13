def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_impact_random_151ac408_match as packet_module
 root=packet_module.ROOT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet_module.OUT;source=packet_module.MANIFEST['selected_source'];function=body(source,'func_151AC408')
 controls={'large_scale':('payload * 6.0f','payload * 5.0f'),'small_scale':('payload * 1.5f','payload * 1.25f'),'range':('% 41u + 80','% 40u + 80'),'handled':('payload[0x20] = 4','payload[0x20] = 5'),'identity':('actor[0xC], actor[1]','actor[0xD], actor[1]'),'branch':('func_150ADA20() & 1','func_150ADA20() & 2'),'axis':(')].z;',')].y;')}
 code='''#include <ultra64.h>
 typedef struct {f32 x,y,z,velocityY,other;} ImpactMotionRecord;
 u8 func_151D8E20(void);s32 func_150ADA20(void);
 void func_151D9B8C(u8,f32,u8,s16 *,f32 *,s16,u8,u8,u8,u8,s32);
 void func_151DAB58(u8,f32,u8,f32 *,u8,u8,u8);
 '''+function.replace('func_151AC408(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert old in function,name
  code+=function.replace('func_151AC408(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 static u32 actor_words[72],payload_words[32],other_words[32];static ImpactMotionRecord records[5];static u8 *actor,*payload,*other;static int parity,mut,calls,broken;static u32 second;static f32 height=1.5f;static s16 result;
 u8 func_151D8E20(void){calls|=1;if(mut){*(f32 *)payload=3.25f;payload[0x1b]^=0x55;actor[0xc]^=0xaa;actor[1]^=0x55;*(u8 **)(actor+0x98)=other;actor[0x2d]=0;}return 0x93;}
 s32 func_150ADA20(void){if(!(calls&2)){calls|=2;return parity;}calls|=4;return (s32)second;}
 static void check(u8 select,f32 scale,u8 color,f32 *pos,u8 id,s32 who,f32 multiplier){s8 idx=(s8)(actor[0x2c]);
  if(select!=0x93||scale!=*(f32 *)payload*multiplier||color!=payload[0x1b]||pos[0]!=records[idx+2].x||pos[1]!=height||pos[2]!=records[idx+2].z||id!=actor[0xc]||who!=actor[1])broken=1;
  if(mut){*(u8 **)(actor+0x98)=other;payload[0x20]=0x77;}
 }
 void func_151D9B8C(u8 s,f32 scale,u8 color,s16 *out,f32 *pos,s16 time,u8 a,u8 b,u8 z,u8 id,s32 who){calls|=8;if(out!=&result||time!=(s16)(second%41u+80)||a!=1||b!=1||z)broken=1;check(s,scale,color,pos,id,who,6.0f);}
 void func_151DAB58(u8 s,f32 scale,u8 color,f32 *pos,u8 one,u8 id,u8 who){calls|=16;if(one!=1)broken=1;check(s,scale,color,pos,id,who,1.5f);}
 typedef s32 (*Fn)(u8 *,f32,f32,f32,f32,void *);
 static int checkfn(Fn fn){static const u32 seconds[]={0,40,41,0xffffffff};
  for(int idx=-2;idx<=2;idx+=2)for(int p=0;p<2;p++)for(int t=0;t<4;t++)for(int mode=0;mode<2;mode++){
   for(int i=0;i<72;i++)actor_words[i]=0;for(int i=0;i<32;i++)payload_words[i]=other_words[i]=0;actor=(u8 *)actor_words;payload=(u8 *)payload_words;other=(u8 *)other_words;
   for(int i=0;i<5;i++){records[i].x=(f32)i+0.25f;records[i].y=(f32)i+7.0f;records[i].z=(f32)i-0.5f;}
   *(ImpactMotionRecord **)(actor+0x94)=&records[2];*(u8 **)(actor+0x98)=payload;actor[0x2d]=(u8)idx;actor[0x2c]=(u8)idx;actor[0xc]=0x92;actor[1]=0x63;*(f32 *)payload=2.0f;payload[0x1b]=0x84;payload[0x20]=0x33;
   parity=p;second=seconds[t];mut=mode;calls=broken=0;
   s32 out=fn(actor,0.5f,2.0f,-1.0f,height,&result);
   if(out!=1||broken||calls!=(p?15:19)||payload[0x20]!=4)return 1;
  }
  return 0;
 }
 static int run(void){if(checkfn(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!checkfn(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'48 cases,',len(controls),'effective negative controls, UBSan',flush=True)
