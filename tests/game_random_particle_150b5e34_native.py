"""Private SDK32 native boundary checks with independent byte-offset/FP expectations."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_random_particle_150b5e34_match as p
def main():
 r,o=p.ROOT,p.OUT;source=p.MANIFEST['selected_source'];lo,hi=function_span(source,'func_150B5E34');body=source[lo:hi]
 first=source.index('typedef struct {\n    f32 x, y, z;\n} CompositeEffectPosition;');end=source.index('} CompositePositionStorage150B5A3C;',first)+len('} CompositePositionStorage150B5A3C;');types=source[first:end]
 end=source.index('} RandomParticleDefinition150B5E34;')+len('} RandomParticleDefinition150B5E34;');start=source.rfind('typedef struct {',0,end);types+='\n'+source[start:end]
 header=r'''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;
 typedef int s32;typedef unsigned int u32;typedef float f32;
 #define offsetof(t,m) __builtin_offsetof(t,m)
 static void *memcpy(void *d,const void *s,u32 n){u8 *a=d;const u8 *b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];return d;}
 static void *memset(void *d,int v,u32 n){u8 *a=d;u32 i;for(i=0;i<n;i++)a[i]=(u8)v;return d;}
 '''+types+r'''
 _Static_assert(sizeof(void*)==4,"SDK32 pointers");
 _Static_assert(sizeof(CompositePositionStorage150B5A3C)==12,"position12");
 _Static_assert(sizeof(RandomParticleDefinition150B5E34)==112,"descriptor112");
 _Static_assert(offsetof(RandomParticleDefinition150B5E34,extentX)==0x28,"extent28");
 _Static_assert(offsetof(RandomParticleDefinition150B5E34,position)==0x30,"position30");
 _Static_assert(offsetof(RandomParticleDefinition150B5E34,flags58)==0x58,"flags58");
 _Static_assert(offsetof(RandomParticleDefinition150B5E34,reserved6C)==0x6c,"complete tail");
 s32 func_150ADA20(void);f32 func_150ADA68(void);
 void *func_15130280(RandomParticleDefinition150B5E34 *,u8,void *,s32,u8,s32);
 '''
 harness=r'''
 static CompositePositionStorage150B5A3C point;
 static u8 expected[112],allocation[0xb0];
 static u32 numbers[3],sampleBits,expectedFP,expectedCSR,modeWord,extraWord;
 static unsigned caseNumber,calls,integerCalls,bad;
 static u32 csr(void){u32 x;__asm__ volatile("stmxcsr %0":"=m"(x));return x;}
 static void setcsr(u32 x){__asm__ volatile("ldmxcsr %0"::"m"(x):"memory");}
 static u32 bits(f32 x){u32 n;memcpy(&n,&x,4);return n;}
 static f32 real(u32 x){f32 v;memcpy(&v,&x,4);return v;}
 static u32 epochCSR(unsigned epoch){return 0x1f80U|(((caseNumber/256+epoch)%4)<<13)|((caseNumber+epoch*7)%64);}
 static void put32(unsigned at,u32 v){memcpy(expected+at,&v,4);}
 static void put16(unsigned at,u16 v){memcpy(expected+at,&v,2);}
 static void movePoint(unsigned epoch){
  unsigned i;for(i=0;i<3;i++){
   u32 v=(0x3f000000U+(caseNumber+i*3+epoch*5)*0x1021U)^((caseNumber+i+epoch)&1?0x80000000U:0);
   memcpy(&point.array[i],&v,4);
   if(epoch==2)memcpy(expected+0x30+4*i,&v,4);
  }
 }
 static void boundary(unsigned wanted){
  ++calls;if(calls!=wanted)bad=1;
  if(csr()!=(wanted==3?expectedCSR:epochCSR(wanted-1)))bad=1;
  movePoint(wanted);setcsr(epochCSR(wanted));
 }
 s32 func_150ADA20(void){
  u32 n;if(integerCalls>=3){bad=1;return 0;}
  boundary(integerCalls==0?1:integerCalls==1?3:4);n=numbers[integerCalls++];return(s32)n;
 }
 f32 func_150ADA68(void){boundary(2);return real(sampleBits);}
 void *func_15130280(RandomParticleDefinition150B5E34 *packet,u8 kind,void *extra,s32 size,u8 mode,s32 context){
  unsigned i;u8 *bytes=(u8*)packet;boundary(5);
  if(kind!=1||extra!=0||size!=0||mode!=(u8)modeWord||(u32)context!=extraWord)bad=1;
  for(i=0;i<112;i++)if(!(i>=0x5c&&i<0x60)&&i<0x66&&bytes[i]!=expected[i])bad=1;
  /* memcpy may carry the14 unspecified bytes; they are never asserted fixed. */
  memcpy(allocation+0x10,packet,112);
  for(i=0;i<112;i++)if(!(i>=0x5c&&i<0x60)&&i<0x66&&allocation[0x10+i]!=expected[i])bad=1;
  return caseNumber&1?allocation:0;
 }
 static void prepare(void){
  static const u32 rng[]={0,1,2,6,7,8,0x7fffffffU,0x80000000U,0xffffffffU};
  static const u32 samples[]={0,0x80000000U,0x3e800000U,0x3f000000U,0x3f800000U,0xbf800000U,1,0x7f7fffffU,0xff7fffffU};
  unsigned i;f32 x,c=500.0f;u32 save=csr();
  numbers[0]=rng[caseNumber%9];numbers[1]=rng[(caseNumber/3+1)%9];numbers[2]=rng[(caseNumber/7+2)%9];sampleBits=samples[(caseNumber/11)%9];
  x=real(sampleBits);setcsr(epochCSR(2));
  __asm__ volatile("mulss %1,%0; addss %1,%0":"+x"(x):"x"(c):"memory");
  expectedFP=bits(x);expectedCSR=csr();setcsr(save);
  memset(expected,0xa5,sizeof(expected));put32(0,0x200005);put32(4,0x20000);
  put16(8,0x4403);put16(0xa,(u16)(numbers[0]%7U+4));put32(0xc,0);put32(0x10,0);
  for(i=0x14;i<=0x1c;i++)expected[i]=255;expected[0x1d]=43;
  put16(0x1e,3);put16(0x20,85);put16(0x22,1);put32(0x24,0x3f800000);put32(0x28,expectedFP);put32(0x2c,expectedFP);
  for(i=0x3c;i<0x58;i++)expected[i]=0;
  put32(0x58,0xc201U|((numbers[1]&1)?0x40:0)|((numbers[2]&1)?0x80:0));
  expected[0x60]=6;expected[0x61]=6;expected[0x62]=255;expected[0x63]=255;expected[0x64]=255;expected[0x65]=4;
  modeWord=caseNumber&255;extraWord=(u32[]){0,0xffffffffU,0x80000000U,0x7fffffffU,0x12345678U}[caseNumber%5];
  calls=integerCalls=bad=0;movePoint(0);memset(allocation,0x59,sizeof(allocation));setcsr(epochCSR(0));
 }
 int main(void){
  u32 saved=csr();for(caseNumber=0;caseNumber<1024;caseNumber++){
   void *result;prepare();result=func_150B5E34(&point,(u8)modeWord,(s32)extraWord);
   if(calls!=5||integerCalls!=3||csr()!=epochCSR(5)||result!=(caseNumber&1?(void*)allocation:0))bad=1;
   if(bad){setcsr(saved);return 42;}
  }
  setcsr(saved);return 0;
 }
 __attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
 '''
 def build(label,code,opt):
  c=o/(label+'.c');exe=o/(label+'.exe');c.write_text(header+code+'\n'+harness)
  command=['cc','-m32',opt,'-std=gnu11','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-fno-omit-frame-pointer',str(c),'-o',str(exe)]
  q=subprocess.run(command,capture_output=True,text=True);assert q.returncode==0,q.stderr
  result=subprocess.run([str(exe)],capture_output=True,text=True)
  return dict(source_sha256=hashlib.sha256(c.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),comparison_exit=result.returncode,stdout=result.stdout,stderr=result.stderr)
 profiles={}
 for opt in ['-O0','-O2','-O3']:
  q=build('native'+opt,body,opt);assert q['comparison_exit']==0,q;profiles[opt]=q;print(json.dumps(dict(profile=opt,exit=q['comparison_exit'],cases=1024)),flush=True)
 controls=[]
 mutations=[('lifetime-base','%7U+4','%7U+5'),('packet-code','packet.code08=0x4403;','packet.code08=0x4402;'),('field04-zero','packet.field04=0x20000;','packet.field04=0;'),('extent-base','*500.0f+500.0f','*500.0f+501.0f'),('extent-multiply','*500.0f+500.0f','+500.0f+500.0f'),('first-flag','?0x40:0','?0x20:0'),('flags58','|0xC200;','|0xC300;'),('wrong-mode',',mode,extra);',',0,extra);'),('wrong-context',',mode,extra);',',mode,0);'),('wrong-return','return func_15130280(&packet,1,0,0,mode,extra);','func_15130280(&packet,1,0,0,mode,extra);return 0;')]
 for name,old,new in mutations:
  assert body.count(old)==1,(name,old);q=build('native-control-'+name,body.replace(old,new),'-O2');assert q['comparison_exit']==42,q;controls.append(dict(name=name,**q,completed_target_before_comparison=True));print(json.dumps(dict(control=name,exit=42)),flush=True)
 old='    packet.extentX=packet.extentY=func_150ADA68()*500.0f+500.0f;\n    packet.position=position->vector;';assert body.count(old)==1
 wrong=body.replace(old,'    packet.position=position->vector;\n    packet.extentX=packet.extentY=func_150ADA68()*500.0f+500.0f;');q=build('native-control-position-before-RNG',wrong,'-O2');assert q['comparison_exit']==42,q;controls.append(dict(name='position-before-RNG',**q,completed_target_before_comparison=True))
 q=dict(cases_per_profile=1024,profiles=profiles,effective_source_controls=controls,negative_controls=11,all_controls_comparison_exit42=True,no_signal_or_UBSan_trap_counted=True,complete_source_packet_bytes=112,defined_packet_bytes_observed=98,unspecified_bytes_excluded=14,all_256_mode_bytes=True,all_four_round_modes_and_status_flags=True,strict_aliasing_and_UBSan=True,provider_point_mutation_at_each_boundary=True,unpassed_private_storage_unobserved=True,allocation_pointer_and_null_return_contract=True,copy_extent_bytes=112,source_installed=p.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True)
 return q
if __name__=='__main__':main()
