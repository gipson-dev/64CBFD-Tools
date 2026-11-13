from pathlib import Path
import subprocess,sys
from tools.experiments import game_two_vector_provider_15160cdc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
 fn=body((out/'after.c').read_text(),'func_15160CDC')
 controls={'kind':('payload.kind = kind','payload.kind = 0'),'flag0':('(flag0 ? 1 : 0)','(flag0 ? 0 : 1)'),'flag1':('(flag1 ? 2 : 0)','(flag1 ? 0 : 2)'),'header':('header.unk1 = 6','header.unk1 = 5'),'vector':('payload.second = *secondVector','payload.second = *firstVector'),'tag':('payload.tag = tag','payload.tag = 0')}
 head='''#include <ultra64.h>
 typedef struct { f32 x,y,z; } GameEffectVector15160CDC;
 typedef struct {u8 *owner;u8 identity,kind;u8 pad06[2];GameEffectVector15160CDC first,second;f32 scale;u8 flags,tag,pad26[2];} TwoVectorPayload15160CDC;
 typedef struct {s8 unk0,unk1;s16 unk2;s8 unk4;u8 pad5;} Header;
 typedef struct {s32 unk0,unk4,unk8;} Header2;
 typedef struct { u32 data[128]; } struct225;
 struct225 *func_151602C0(Header*,Header2*,s32,s32,s32,s32,u8,u8,s32,u8,s32);
 void *memcpy(void*,const void*,unsigned int);
 '''
 code=head+fn.replace('func_15160CDC(', 'selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert old in fn,name;code+=fn.replace('func_15160CDC(', 'bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+=r'''
 static u32 owner_storage[128],output_storage[128];static u8 *owner;static u32 active,aliasout,mutate,bad,calls,copies;
 static u8 expkind,expflag0,expflag1,exptag,expheader,exppriority;static s16 explifetime;static s32 expuser;static GameEffectVector15160CDC one,two;static f32 expscale;
 struct225 *func_151602C0(Header *h,Header2 *z,s32 a,s32 b,s32 c,s32 d,u8 e,u8 f,s32 size,u8 priority,s32 user){
  calls++;if((u8)h->unk0!=expheader||h->unk1!=6||h->unk2!=explifetime||h->unk4!=17||z->unk0||z->unk4||z->unk8||a!=1||b!=2||c!=3||d!=4||e!=255||f!=0||size!=40||priority!=exppriority||user!=expuser)bad=1;
  if(mutate)owner[0x3b]^=0x5a;
  return active?(struct225*)(aliasout?owner:(u8*)output_storage):(struct225*)0;
 }
 void *memcpy(void *to,const void *from,unsigned int n){
  u8 *d=(u8*)to;const u8 *s=(const u8*)from;
  if(n==40){const TwoVectorPayload15160CDC *p=(const TwoVectorPayload15160CDC*)from;copies++;
   if(p->owner!=owner||p->identity!=0x73||p->kind!=expkind||p->first.x!=one.x||p->first.y!=one.y||p->first.z!=one.z||p->second.x!=two.x||p->second.y!=two.y||p->second.z!=two.z||p->scale!=expscale||p->flags!=((expflag0?1:0)|(expflag1?2:0))||p->tag!=exptag)bad=1;
  }
  for(unsigned int i=0;i<n;i++)d[i]=s[i];return to;
 }
 typedef void *(*Fn)(u8*,u8,GameEffectVector15160CDC*,GameEffectVector15160CDC*,f32,u8,s16,s32,s32,s32,s32,u8,u8,u8,u8,s32);
 static int check(Fn fn){
  static const s16 durations[]={-32768,-1,0,32767};
  static const u8 vals[]={0,1,255};
  for(u32 oi=0;oi<2;oi++)for(u32 al=0;al<2;al++)for(u32 mu=0;mu<2;mu++)for(u32 alias=0;alias<2;alias++)for(u32 f0=0;f0<3;f0++)for(u32 f1=0;f1<3;f1++)for(u32 di=0;di<4;di++){
   for(u32 i=0;i<128;i++)owner_storage[i]=output_storage[i]=0;owner=(u8*)owner_storage;owner[0x3b]=0x73;
   one.x=1.f;one.y=-2.f;one.z=3.f;two.x=4.f;two.y=5.f;two.z=-6.f;expscale=0.5f;
   active=al;mutate=mu;aliasout=alias;expkind=7;expflag0=vals[f0];expflag1=vals[f1];exptag=0xa5;expheader=2;explifetime=durations[di];exppriority=0xff;expuser=-3;bad=calls=copies=0;
   void *r=fn(oi?owner:(u8*)0,expkind,&one,&two,expscale,expheader,explifetime,1,2,3,4,expflag0,exptag,expflag1,exppriority,expuser);
   if(!oi){if(r||calls||copies||bad)return 1;continue;}
   if(bad||calls!=1||copies!=(active?1u:0u)||r!=(active?(void*)(aliasout?owner:(u8*)output_storage):(void*)0))return 1;
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
  print(opt,'576 native cases and',len(controls),'negative controls passed',flush=True)
