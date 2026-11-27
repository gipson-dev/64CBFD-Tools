"""Typed actual C under the pinned target's signed-low-word wrapping contract."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_phase_height_update_1511f788_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT
def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;lo,hi=function_span(source,'func_1511F788');body=source[lo:hi];end=source.index('} HeightPhaseState1511F788;')+len('} HeightPhaseState1511F788;');start=source.rfind('typedef struct {',0,end);types=source[start:end];(o/'candidate-body.c').write_text(body);(o/'candidate-types.h').write_text(types+'\n')
 header='''typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
'''+types+'''
typedef struct{u32 pre[4];HeightPhaseState1511F788 state;u8 tail[24];u32 post[4];}Storage;
typedef struct{u32 n,target[2],argument[2],csr[2];u8 state[2][136];u32 gate[2],ticks[2];}Observation;
extern Storage storage;extern Observation observation;extern u8 D_800BE9B4;extern s32 D_800BE9E4;extern u32 row,mutation,initialMode,integerBits,cosineBits;
s32 func_150ADA20(void);f32 cosf(f32);void func_1511F788(HeightPhaseState1511F788*);
typedef char Layout[sizeof(void*)==4&&sizeof(s32)==4&&(s16)0x8000==-32768&&sizeof(HeightPhaseState1511F788)==136&&sizeof(Storage)==192&&__builtin_offsetof(HeightPhaseState1511F788,height)==0x12&&__builtin_offsetof(HeightPhaseState1511F788,phase)==0x7C&&__builtin_offsetof(HeightPhaseState1511F788,timer)==0x84?1:-1];
static inline u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static inline f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static inline u32 csr(void){u32 x;__asm__ volatile("stmxcsr %0":"=m"(x)::"memory");return x;}
static inline void setCSR(u32 x){__asm__ volatile("ldmxcsr %0"::"m"(x):"memory");}
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static u32 observe(u32 t,u32 a){u32 n=observation.n++,i;observation.target[n]=t;observation.argument[n]=a;observation.csr[n]=csr();for(i=0;i<sizeof(storage.state);i++)observation.state[n][i]=((u8*)&storage.state)[i];observation.gate[n]=D_800BE9B4;observation.ticks[n]=(u32)D_800BE9E4;return n;}
static void change(u32 t){HeightPhaseState1511F788*p=&storage.state;if(mutation&1){D_800BE9E4=(s32)(t?0x80000001u:0xffffffffu);D_800BE9B4^=0x80;p->duration=(s32)((u32)p->duration^0xffffffffu);p->phase=t?0x80000000u:0x7fffffffu;}if(mutation&2){p->height=(s16)(t?-9999:-10000);p->offset=-7.25f;p->mode=(s32)((initialMode+1)&3);p->timer=0x7fffffff;}setCSR((csr()&~63u)|4u);}
__attribute__((noipa))s32 func_150ADA20(void){observe(0x150ADA20,0);change(0);return(s32)integerBits;}
__attribute__((noipa))f32 cosf(f32 x){observe(0x15047C00,bits(x));change(1);return floating(cosineBits);}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Storage storage;Observation observation;u8 D_800BE9B4;s32 D_800BE9E4;u32 row,mutation,initialMode,integerBits,cosineBits;
typedef struct{Storage storage;Observation observation;u32 gate,ticks,csr;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static f32 convert(s32 x){return(f32)x;}
__attribute__((noinline,noclone))static f32 add(f32 a,f32 b){return a+b;}
__attribute__((noinline,noclone))static f32 subtract(f32 a,f32 b){return a-b;}
__attribute__((noinline,noclone))static f32 mul(f32 a,f32 b){return a*b;}
__attribute__((noinline,noclone))static s32 truncated(f32 x){return(s32)x;}
__attribute__((noinline,noclone))static void reference(void){HeightPhaseState1511F788*p=&storage.state;u8 gate=D_800BE9B4;s16 old=(s16)truncated(add(convert(p->height),p->offset));u32 product=(u32)p->duration*60u;s32 limit=(s32)product/60;if(gate)p->phase=(u32)func_150ADA20()&65535u;f32 angle=mul(convert((s32)p->phase),floating(0x3bb40000u));f32 c=cosf(angle);p->offset=mul(c,25.f);p->phase+=10u*(u32)D_800BE9E4;if(p->mode==1){p->timer=(s32)((u32)p->timer+(u32)D_800BE9E4);if(limit<p->timer)p->mode=2;}else if(p->mode==2){p->height=(s16)((u32)(s32)p->height-(u32)D_800BE9E4);if(p->height<-10000)p->finished=1;}p->delta=(s16)truncated(subtract(add(convert(p->height),p->offset),convert(old)));}
static void fixture(void){u32 i;static const u32 durations[]={0,1,35791394u,35791395u,0x7fffffffu,0x80000000u,0xffffffffu,0xfdddddddu},ticks[]={0,1,0xffffffffu,0x80000000u,0x7fffffffu,10001u,65535u,65536u},phases[]={0,1,0x7fffffffu,0x80000000u},integers[]={0,0xffffffffu,0x80000000u,0x8765f380u},cosines[]={0,0x80000000u,1,0x80000001u,0x3eaaaaabu,0xbf471c72u,0x3f800000u,0xbf800000u};static const s16 heights[]={-32768,-10001,-10000,-9999,0,1,32766,32767};HeightPhaseState1511F788*p=&storage.state;
 for(i=0;i<sizeof(storage);i++)((u8*)&storage)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;initialMode=(row>>1)&3;mutation=(row>>3)&3;D_800BE9B4=(row&1)?255:0;D_800BE9E4=(s32)ticks[(row>>5)&7];p->height=heights[(row>>3)&7];p->offset=(row&4)?3.25f:-.5f;p->duration=(s32)durations[(row>>8)&7];p->delta=(s16)0x8001;p->finished=0;p->phase=phases[(row>>5)&3];p->mode=(s32)initialMode;p->timer=(s32)ticks[(row>>7)&7];integerBits=integers[(row>>2)&3];cosineBits=cosines[(row>>4)&7];setCSR(0x1f80u|(((row>>6)&3)<<13)|4u);}
static void capture(void){current.storage=storage;current.observation=observation;current.gate=D_800BE9B4;current.ticks=(u32)D_800BE9E4;current.csr=csr();}
static s32 fail(void){u32 msg[4]={row,current.observation.n,actual.observation.n,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){fixture();func_1511F788(&storage.state);capture();actual=current;fixture();reference();capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fwrapv','-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text);exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+p,body,'-'+p,0)for p in('O0','O2','O3')];controls=[]
 for name,old,new in [('gate','if (resetPhase != 0)','if (resetPhase == 0)'),('duration-product','threshold = threshold * divisor','threshold = (s32)((u32)threshold * 59u)'),('unsigned-division','threshold /= divisor','threshold = (s32)((u32)threshold / (u32)divisor)'),('phase-mask','& 0xFFFF','& 0x7FFF'),('coefficient','0.0054931640625f','0.010986328125f'),('amplitude','* 25.0f','* 24.0f'),('phase-step','10u *','11u *'),('timer-comparison','threshold < record->timer','threshold <= record->timer'),('fall-step','(u32)(s32)record->height - (u32)D_800BE9E4','(u32)(s32)record->height + (u32)D_800BE9E4'),('fall-boundary','< -10000','< -9999'),('delta','- (f32)previousHeight','+ (f32)previousHeight')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 old='    threshold = threshold * divisor;\n    threshold /= divisor;';assert old in body;controls.append(dict(name='duration-identity',**run('control-duration-identity',body.replace(old,'    (void)divisor;'),'-O2',42)))
 assert '-fwrapv'in flags and '-fsanitize=undefined,float-cast-overflow'in flags
 q=dict(cases_per_profile=4096,profiles=profiles,compiler_command_prefix=flags,translation_units=3,actual_C_void_one_argument_ABI=True,canonical_source_record_type_and_all_offsets_asserted=True,full_initialized_storage_canaries_state_globals_calls_snapshots_and_MXCSR_compared=True,signed_duration_low_word_contract_explicit=True,native_fwrapv_required_for_pinned_N64_signed_integer_semantics=True,independent_reference_product_is_unsigned_32bit=True,all_32bit_duration_edge_domains_retained=True,no_claim_of_unflagged_generic_C_signed_overflow_semantics=True,strict_aliasing_UBSan_float_cast_traps_and_LTO_types=True,private_home_mutations_only_guest=True,finite_cosine_contract=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='effective_controls'}),flush=True);return q
if __name__=='__main__':main()
