"""Actual typed C against independent finite native32 reference and opaque draws."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_random_targets_1518f1a0_match as target_packet
o=target_packet.OUT
def main():
 body=target_packet.MANIFEST['native_body'];types=target_packet.MANIFEST['native_types'];assert body.rstrip()in(o/'selected-owner.c').read_text()and types in(o/'selected-owner.c').read_text()
 header='''typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
'''+types+'''
s32 func_150ADA20(void);f32 func_150ADA68(void);s32 func_1518F1A0(u8*);
typedef char Layout[sizeof(void*)==4&&sizeof(RandomTargetTracks1518F1A0)==48&&sizeof(RandomTargetState1518F1A0)==320&&__builtin_offsetof(RandomTargetState1518F1A0,targets)==0x110&&__builtin_offsetof(RandomTargetTracks1518F1A0,rateTimer)==44?1:-1];
typedef struct{u32 pre[4];RandomTargetState1518F1A0 state;u32 post[4];}Data;
typedef struct{u32 count,calls[8],integer,float_draw;}Observation;
extern Data data;extern Observation observation;extern u32 row,mode;
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static void effect(u32 t,u32 n){RandomTargetState1518F1A0*p=&data.state;RandomTargetTracks1518F1A0*q=&p->targets;if((mode&1)&&t){q->firstA=-6.5f+n;q->firstB=4.25f+n;q->splitPivot=-1.5f+n;q->splitA=-9.25f+n;q->splitB=7.75f+n;q->rateA=-13.5f+n;q->rateB=3.25f+n;p->animationRate=-32+(s32)n;p->firstValue=2.25f+n;p->splitValue=-3.5f-n;}if(mode&2){static const u32 deltas[]={0,2,0xffffffffu,0x80000001u};D_800BE9E4=(s32)deltas[(n+t)&3];D_800A7B68=.25f;D_800A7B6C=-.125f;D_800A7B70=.375f;}}
__attribute__((noipa))s32 func_150ADA20(void){static const u32 draws[]={0,1,6,17,15,0xffffffffu,0x80000000u,23};u32 n=observation.integer++;observation.calls[observation.count++]=0x150ADA20;effect(0,n+1);return(s32)draws[(row+n)&7];}
__attribute__((noipa))f32 func_150ADA68(void){static const f32 draws[]={0.f,.25f,.5f,1.f};u32 n=observation.float_draw++;observation.calls[observation.count++]=0x150ADA68;effect(1,n+1);return draws[(row+n)&3];}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Data data;Observation observation;u32 row,mode;s32 D_800BE9E4;f32 D_800A7B68,D_800A7B6C,D_800A7B70;
typedef struct{Data data;Observation observation;u32 csr,value,delta,coefficients[3];}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static s32 reference(u8*record){RandomTargetState1518F1A0*p=(void*)record;RandomTargetTracks1518F1A0*q=&p->targets;u32 choose;f32 sample,lower;volatile f32 a,b,d;
 q->splitTimer=(s16)((u32)(s32)q->splitTimer-(u32)D_800BE9E4);
 if(q->splitTimer<0){q->splitTimer=(u32)func_150ADA20()%6;choose=(u32)func_150ADA20()&3;sample=func_150ADA68();if(choose){lower=q->splitA;a=q->splitPivot-lower;}else{lower=q->splitPivot;a=q->splitB-lower;}b=sample*a;q->splitTarget=b+lower;}
 a=q->splitTarget-p->splitValue;b=a*D_800A7B68;p->splitValue=p->splitValue+b;
 q->firstTimer=(s16)((u32)(s32)q->firstTimer-(u32)D_800BE9E4);
 if(q->firstTimer<0){q->firstTimer=(u32)func_150ADA20()%17;sample=func_150ADA68();lower=q->firstB;a=q->firstA-lower;b=sample*a;q->firstTarget=b+lower;}
 a=q->firstTarget-p->firstValue;b=a*D_800A7B6C;p->firstValue=p->firstValue+b;
 q->rateTimer=(s16)((u32)(s32)q->rateTimer-(u32)D_800BE9E4);
 if(q->rateTimer<0){q->rateTimer=(u32)func_150ADA20()%15;sample=func_150ADA68();lower=q->rateB;a=q->rateA-lower;b=sample*a;q->rateTarget=b+lower;}
 a=(f32)p->animationRate;b=q->rateTarget-a;d=b*D_800A7B70;p->animationRate=(s32)((u32)p->animationRate+(u32)(s32)d);return 1;}
static void fixture(void){u32 i;RandomTargetState1518F1A0*p=&data.state;RandomTargetTracks1518F1A0*q=&p->targets;static const s16 timers[]={-32768,-1,0,32767};static const u32 ticks[]={0,1,0xffffffffu,0x80000000u};static const s32 rates[]={0,100,-100,16777217,2147483647,(-2147483647-1),-1,65535};for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;q->firstA=8.f;q->firstB=-4.f;q->firstTarget=3.f;q->splitPivot=2.f;q->splitA=-7.f;q->splitB=13.f;q->splitTarget=-3.f;q->rateA=11.f;q->rateB=-9.f;q->rateTarget=4.f;q->firstTimer=timers[(row>>2)&3];q->splitTimer=timers[(row>>4)&3];q->rateTimer=timers[(row>>6)&3];p->animationRate=rates[(row>>8)&7];p->firstValue=1.25f;p->splitValue=-2.5f;D_800BE9E4=(s32)ticks[(row>>10)&3];D_800A7B68=floating(0x3eb7ced9);D_800A7B6C=floating(0x3e3e76c9);D_800A7B70=floating(0x3e6c8b44);mode=(row>>5)&3;setCSR(0x1f80u|((row&3)<<13)|((row&16)?1u:0u));}
static void capture(s32 value){current.csr=csr();current.data=data;current.observation=observation;current.value=(u32)value;current.delta=(u32)D_800BE9E4;current.coefficients[0]=bits(D_800A7B68);current.coefficients[1]=bits(D_800A7B6C);current.coefficients[2]=bits(D_800A7B70);}
static s32 fail(void){u32 msg[4]={row,current.observation.count,current.value^actual.value,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){fixture();capture(func_1518F1A0((u8*)&data.state));actual=current;fixture();capture(reference((u8*)&data.state));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('split-timer-modulo','% 6;','% 7;'),('first-timer-modulo','% 17;','% 16;'),('rate-timer-modulo','% 15;','% 14;'),('split-interval','& 3) != 0','& 3) == 0'),('first-smoothing','* D_800A7B6C','* D_800A7B68'),('rate-smoothing','* D_800A7B70','* D_800A7B6C'),('clock-direction','splitTimer -=','splitTimer +='),('return','return 1;','return 0;')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_C_byte_pointer_ABI_and_typed_320byte_state_48byte_tracks=True,full_arenas_canaries_globals_calls_return_and_MXCSR_equal=True,all_four_rounding_modes_existing_flags_modular_clocks_and_rate=True,unsigned_RNG_moduli_6_17_15_and_live_provider_mutations=True,finite_s32_conversion_domain_only=True,strict_aliasing_UBSan_traps_LTO_types=True,opaque_noipa_providers_not_original_RNG_implementation=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
