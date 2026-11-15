"""SDK32 execution of private semantic C, without assigning byte-match credit."""
import hashlib,json,subprocess
from tools.experiments import game_radial_effect_150c29f0_recovery as s
from tools.tests import game_radial_effect_150c29f0_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
 controls=dict(angle=('angle - 64','angle - 63'),radius=('radius * directionX','radius + directionX'),duration=('% 201U','% 200U'),timer=('% 51U','% 50U'),kind=('&packet, 10','&packet, 9'),code=('0x6231','0x6230'),owner=('owner[0xC]','owner[0xB]'),scale=('D_800A02AC * firstScale','D_800A02AC * secondScale'))
 code='#include <ultra64.h>\n'+s.PREAMBLE.replace('extern f32','f32')
 code+=r'''
 _Static_assert(sizeof(void*)==4 && sizeof(RadialEffectPacket150C29F0)==72,"SDK32 packet");
 struct Owner {u8 head[14];s16 timer;u8 rest10[24];f32 values28[4];u8 tail38[40];};
 static struct {u8 before[32];struct Owner record;} storage;
 _Static_assert(sizeof(storage)==128 && __builtin_offsetof(struct Owner,values28)==40,"owner layout");
 static const u32 quarter[65]={
 '''+','.join('0x%Xu'%v for v in g.quarter())+'};\n'
 code+='struct Case {u32 randoms[6],position[4],mutation,mode,selector,seed;u8 initial[128],final[128],packet[72];u32 globals[8];};\nstatic const struct Case cases[]={\n'
 arr=lambda vs:'{'+','.join('0x%Xu'%v for v in vs)+'}'
 for c in g.cases():
  initial=g.fixture(c);final,_,(packet,_)=g.reference(initial,c)
  code+='{'+','.join((arr(c.randoms),arr(c.position),str(c.mutation),str(c.mode),str(c.selector),str(c.seed),arr(initial[g.OWNER-32+i] for i in range(128)),arr(final[g.OWNER-32+i] for i in range(128)),arr(packet),arr(g.read(final,g.CONST+4*i) for i in range(8))))+'},\n'
 code+=r'''};
 static const struct Case *current;static u32 calls,bad,mark;
 static f32 value(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
 static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
 static void be(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
 static void globals(u32 out[8]){out[0]=word(D_800A02A0);out[1]=word(D_800A02A4);out[2]=word(D_800A02A8);out[3]=word(D_800A02AC);out[4]=word(D_800A02B0);out[5]=word(D_800A02B4);out[6]=word(D_800A02B8);out[7]=word(D_800A02BC);}
 static void set_globals(int mutated,int odd){f32 k=mutated?(odd?.125f:-.25f):.1f;
  if(!mutated){D_800A02A0=.1f;D_800A02A4=.2f;D_800A02A8=.3f;D_800A02AC=.4f;D_800A02B0=.5f;D_800A02B4=.6f;D_800A02B8=.7f;D_800A02BC=.8f;return;}
  D_800A02A0=k;D_800A02A4=2*k;D_800A02A8=3*k;D_800A02AC=4*k;D_800A02B0=5*k;D_800A02B4=6*k;D_800A02B8=7*k;D_800A02BC=8*k;}
 static void effect(u32 n){u32 i;mark=0x13579bdf+n*0x10203;
  if(current->mutation){storage.record.head[12]^=0x55;storage.record.head[1]^=0xa3;
   for(i=0;i<4;i++)storage.record.values28[i]=(i+1)*(n&1?.5f:-1.f);set_globals(1,n&1);}}
 s32 func_150ADA20(void){u32 n=calls++;effect(n);if(n==0)return (s32)current->randoms[0];if(n==4)return (s32)current->randoms[2];if(n==8)return (s32)current->randoms[5];bad=1;return 0;}
 f32 func_150ADA68(void){u32 n=calls++;effect(n);if(n==3)return value(current->randoms[1]);if(n==5)return value(current->randoms[3]);if(n==6)return value(current->randoms[4]);bad=1;return 0;}
 f32 func_151423D8(u8 angle){u32 n=calls++,v,index=angle&64?64-(angle&63):angle&63;
  if((n==1&&angle!=(u8)(current->randoms[0]-64))||(n==2&&angle!=(u8)current->randoms[0])||(n!=1&&n!=2))bad=1;
  v=quarter[index];if((angle&192)!=0&&(angle&192)!=192)v^=0x80000000;return value(v);}
 void *func_15149550(RadialEffectPacket150C29F0*p,u8 kind,u8 arg2,s32 arg3,u8 mode,s32 selector){
  u32 i,n=calls++;u8 bytes[72];const u8*raw=(const u8*)p;
  if(n!=7||kind!=10||arg2!=1||arg3!=0||mode!=storage.record.head[12]||selector!=storage.record.head[1])bad=1;
  for(i=0;i<72;i++)bytes[i]=raw[i];
  for(i=0;i<32;i+=4)be(bytes+i,word(*(const f32*)(raw+i)),4);
  for(i=0x38;i<72;i+=4)be(bytes+i,word(*(const f32*)(raw+i)),4);
  for(i=0x20;i<=0x24;i+=2)be(bytes+i,*(const u16*)(raw+i),2);
  be(bytes+0x2a,*(const u16*)(raw+0x2a),2);
  for(i=0;i<72;i++)if((i<0x35||i>=0x38)&&bytes[i]!=current->packet[i])bad=1;
  effect(n);return (void*)0x34560;}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(s.NAME,'test_'+name,1)+'\n'
 code+=r'''
 typedef void (*T)(u8*);
 static int check(T test){u32 n,i,words[8];u8 canonical[128];
  for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){const struct Case*c=&cases[n];u8*raw=(u8*)&storage;
   current=c;calls=bad=mark=0;for(i=0;i<128;i++)raw[i]=c->initial[i];storage.record.timer=-127;
   for(i=0;i<4;i++)storage.record.values28[i]=value(c->position[i]);set_globals(0,0);
   test((u8*)&storage.record);if(bad||calls!=9||mark!=0x13579bdf+8*0x10203)return 1;
   for(i=0;i<128;i++)canonical[i]=raw[i];for(i=0;i<4;i++)be(canonical+32+40+i*4,word(storage.record.values28[i]),4);
   be(canonical+32+14,(u16)storage.record.timer,2);for(i=0;i<128;i++)if(canonical[i]!=c->final[i])return 2;
   globals(words);for(i=0;i<8;i++)if(words[i]!=c->globals[i])return 3;
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
 report=dict(profiles=profiles,owner_bytes=128,global_words=8,packet_defined_bytes=69,padding_not_claimed=3,original_trig_semantics=True,private_uninstalled=True,native_source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
 (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
