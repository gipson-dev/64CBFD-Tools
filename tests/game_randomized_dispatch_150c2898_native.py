"""Execute the actual semantic C and effective C controls in SDK32 builds."""
import hashlib,json,subprocess
from tools.experiments import game_randomized_dispatch_150c2898_recovery as s
from tools.tests import game_randomized_dispatch_150c2898_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
 controls=dict(direction_sign=('-dx * speed','dx * speed'),speed_bias=('+ 247.0f','+ 246.0f'),mask=('& 15U','& 7U'),modulus=('% 101U','% 100U'),scale=('first * D_800A028C','first * D_800A0288'),kind=('position, velocity, 6','position, velocity, 5'),owner=('owner[0xC]','owner[0xB]'))
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 f32 D_800A0288,D_800A028C,D_800A0290;
 struct Case {u32 pos[3],vector[3],randoms[5],mode,selector,mutation,seed,velocity[3],args[16];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  _,(_,velocity,args)=g.reference(g.fixture(c),c)
  arr=lambda vs:'{'+','.join('0x%Xu'%v for v in vs)+'}'
  code+='{'+','.join((arr(c.position),arr(c.vector),arr(c.randoms),str(c.mode),str(c.selector),str(c.mutation),str(c.seed),arr(velocity),arr(args)))+'},\n'
 code+=r'''};
 static const struct Case *current;static u32 calls,bad,mark;static u8 owner[128];
 static f32 value(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
 static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
 static void effect(u32 n){mark=0x13579bdf+n*0x10203;
  if(current->mutation){owner[44]^=0x55;owner[33]^=0xa3;
   D_800A0288=value(n%2?0x3e800000:0x3dcccccd);
   D_800A028C=value(n%2?0x3f400000:0x3f19999a);
   D_800A0290=value(n%2?0xbe800000:0xbf400000);}}
 f32 func_150ADA68(void){u32 n=calls++;effect(n);if(n==0)return value(current->randoms[0]);if(n==1)return value(current->randoms[1]);if(n==4)return value(current->randoms[4]);bad=1;return 0;}
 s32 func_150ADA20(void){u32 n=calls++;effect(n);if(n!=2&&n!=3){bad=1;return 0;}return (s32)current->randoms[n];}
 void *func_151D9014(void *p,f32 *v,u8 a2,f32 a3,s16 a4,u8 a5,f32 a6,u8 a7,f32 a8,f32 a9,u8 a10,s32 a11,u8 a12,u8 a13,u8 a14,s32 a15){
  u32 i,n=calls++,actual[16]={0,0,a2,word(a3),(u32)(s32)a4,a5,word(a6),a7,word(a8),word(a9),a10,(u32)a11,a12,a13,a14,(u32)a15};
  if(n!=5)bad=1;for(i=0;i<3;i++)if(word(((f32*)p)[i])!=current->pos[i]||word(v[i])!=current->velocity[i])bad=1;
  for(i=2;i<16;i++)if(actual[i]!=current->args[i])bad=1;effect(n);return (void*)0x34560;}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(s.NAME,'test_'+name,1)+'\n'
 code+=r'''
 typedef void (*T)(f32,f32,f32,f32,f32,f32,u8*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];current=c;calls=bad=0;mark=0;
  for(i=0;i<128;i++)owner[i]=((i-32)*13+c->seed*11+0x53)&255;
  owner[44]=(u8)c->mode;owner[33]=(u8)c->selector;
  D_800A0288=value(0x3dcccccd);D_800A028C=value(0x3f19999a);D_800A0290=value(0xbf400000);
  test(value(c->pos[0]),value(c->pos[1]),value(c->pos[2]),value(c->vector[0]),value(c->vector[1]),value(c->vector[2]),owner+32);
  if(bad||calls!=6||mark!=0x13579bdf+5*0x10203)return 1;
  for(i=0;i<128;i++){u32 want=((i-32)*13+c->seed*11+0x53)&255;if(i==44)want=c->mode;if(i==33)want=c->selector;if(owner[i]!=want)return 2;}
  if(word(D_800A0288)!=(c->mutation?0x3e800000:0x3dcccccd)||word(D_800A028C)!=(c->mutation?0x3f400000:0x3f19999a)||word(D_800A0290)!=(c->mutation?0xbe800000:0xbf400000))return 3;
 }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=s.OUT/'native.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=s.OUT/('native'+opt);q=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr)
  profiles[opt]=dict(cases=len(list(g.cases())),controls=len(controls),UBSan=True,sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 report=dict(profiles=profiles,public_owner_bytes=128,mutable_global_words=3,helpers_modeled=True,native_source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
 (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
