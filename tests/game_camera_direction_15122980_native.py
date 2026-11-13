def run():
 from pathlib import Path
 import subprocess,sys
 from tools.experiments import game_camera_direction_15122980_match as packet
 root=packet.ROOT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 out=packet.OUT
 fn=body(packet.MANIFEST['selected_source'],'func_15122980')
 controls={
  'mode':('!= 4','== 4'),
  'vector':('camera + 0x2C8','camera + 0x2BC'),
  'gate':('== 0) {','!= 0) {'),
  'mask':('& 0x100000','& 0x200000'),
  'boundary':('> 180.0f','>= 180.0f'),
  'late':('* *(f32 *)(camera + 0x8DC)','* 1.0f'),
  'final':('    func_1512E140(camera);','    (void)camera;'),
 }
 pre='''#include <ultra64.h>
 typedef struct { f32 x,y,z; } struct17;
 extern f32 D_800A34A0;
 void func_15048F90(struct17 *,struct17 *,struct17 *);f32 func_15048FC8(struct17 *);
 f32 func_15048A70(f32,f32);void func_150495B0(f32 *,f32,f32 *,f32,f32,f32);
 void func_15123A54(void *);void func_1512E140(void *);void func_1512A390(void *);
 '''
 code=pre+fn.replace('func_15122980(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert fn.count(old)==1,(name,old)
  code+=fn.replace('func_15122980(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+='''
 f32 D_800A34A0;
 typedef union {u32 u;f32 f;} Word;
 static f32 number(u32 v){Word w;w.u=v;return w.f;}
 static u32 word(f32 v){Word w;w.f=v;return w.u;}
 static u8 camera[0x900] __attribute__((aligned(16)));
 static int logv[16],nlog,heads,mutation,error;
 static void event(int id){logv[nlog++]=id;}
 void func_15048F90(struct17 *a,struct17 *b,struct17 *c){event(1);c->x=b->x-a->x;c->y=b->y-a->y;c->z=b->z-a->z;}
 f32 func_15048FC8(struct17 *v){
  event(2);heads++;
  if(v->x!=(heads==1?3.0f:6.0f)||v->y!=(heads==1?4.0f:7.0f)||v->z!=(heads==1?5.0f:8.0f))error=1;
  return heads==1?30.0f:90.0f;
 }
 void func_150495B0(f32 *p,f32 target,f32 *v,f32 a,f32 b,f32 dt){
  event(3);if(p!=(f32 *)(camera+0x8dc)||v!=(f32 *)(camera+0x8d8)||a!=1.0f||b!=2.0f||dt!=0.25f)error=1;
  *(f32 *)(camera+0x850)=target;*p=2.0f;*v=-2.0f;
 }
 f32 func_15048A70(f32 a,f32 b){
  event(4);if(a!=30.0f||b!=90.0f)error=1;
  if(mutation&1){*(f32 *)(camera+0x37c)=50.0f;*(f32 *)(camera+0x8dc)=3.0f;}
  if(mutation&2)D_800A34A0=0.25f;
  return 8.0f;
 }
 void func_15123A54(void *p){event(5);if(p!=camera)error=1;camera[0x100]=0x71;}
 void func_1512E140(void *p){event(6);if(p!=camera)error=1;camera[0x101]=0x72;}
 void func_1512A390(void *p){event(7);if(p!=camera)error=1;camera[0x102]=0x73;}
 typedef void (*Fn)(u8 *);
 static int check(Fn fn){
  static const u32 angles[]={0x43330000,0x43340000,0x43350000,0x43868000,0x43870000,0x43878000,0x7fc00000};
  for(int mode=0;mode<2;mode++)for(int gate=0;gate<2;gate++)for(int flag=0;flag<2;flag++)for(int angle=0;angle<7;angle++)for(int mut=0;mut<4;mut++){
   for(int i=0;i<0x900;i++)camera[i]=(i*29+0x51)&255;
   *(s32 *)(camera+0xdc)=mode?4:0;*(s16 *)(camera+0x298)=gate;*(u32 *)(camera+0x84)=flag?0x100000:0;
   *(f32 *)(camera+0x390)=number(angles[angle]);*(f32 *)(camera+0x37c)=10.0f;*(f32 *)(camera+0x39c)=-3.0f;
   *(f32 *)(camera+0x8d4)=9.0f;*(f32 *)(camera+0x8d8)=7.0f;*(f32 *)(camera+0x8dc)=4.0f;*(f32 *)(camera+0x7b4)=0.25f;
   for(int i=0;i<3;i++){*(f32 *)(camera+0x2f8+4*i)=1.0f+i;*(f32 *)(camera+0x2c8+4*i)=4.0f+2*i;*(f32 *)(camera+0x2bc+4*i)=7.0f+2*i;}
   D_800A34A0=0.5f;mutation=mut;nlog=heads=error=0;
   fn(camera);
   if(error||camera[0x100]!=0x71||camera[0x101]!=0x72||camera[0x102]!=0x73)return 1;
   if(mode){if(nlog!=3||logv[0]!=5||logv[1]!=6||logv[2]!=7||*(f32 *)(camera+0x37c)!=10.0f||*(f32 *)(camera+0x39c)!=-3.0f)return 2;}
   else {
    int order[]={1,1,2,2,3,4,5,6,7};f32 av=number(angles[angle]);
    f32 val=!gate?0.0f:flag||(av>180.0f&&av<270.0f)?0.75f:0.5f;
    f32 degrees=(mut&1?50.0f:10.0f)+8.0f*(mut&1?3.0f:2.0f);
    f32 radians=degrees*(mut&2?0.25f:0.5f);
    if(nlog!=9||heads!=2)return 3;for(int i=0;i<9;i++)if(logv[i]!=order[i])return 4;
    if(word(*(f32 *)(camera+0x850))!=word(val)||word(*(f32 *)(camera+0x8d4))!=word(val)||word(*(f32 *)(camera+0x37c))!=word(degrees)||word(*(f32 *)(camera+0x39c))!=word(radians))return 5;
   }
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
  print(opt,'224 camera cases,',len(controls),'effective negative controls, UBSan',flush=True)
