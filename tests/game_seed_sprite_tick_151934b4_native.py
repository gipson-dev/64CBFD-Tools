"""Actual direct C, typed owner, separate seven-argument provider and controls."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_seed_sprite_tick_151934b4_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();a,z=function_span(source,'func_151934B4');body=source[a:z];start=source.index('typedef struct {\n    u8 retained00[0x94];');end=source.index('/* Grow the seed sprite',start)
 header='typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;\n'+source[start:end]+'void func_151934B4(SeedSpriteRuntime151934B4*);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(SeedSpriteRuntime151934B4)==180&&__builtin_offsetof(SeedSpriteRuntime151934B4,phase)==152&&__builtin_offsetof(SeedSpriteRuntime151934B4,verticalExtent)==164&&__builtin_offsetof(SeedSpriteRuntime151934B4,variant)==179?1:-1];\n'
 header+='typedef struct{u32 count,metadata[7],position[3];}Observation;extern Observation observation;extern SeedSpriteRuntime151934B4 *activeOwner;extern u32 mode;\n';(o/'native-shared.h').write_text(header)
 provider=r'''
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
void func_151DBCBC(u8 kind,f32 size,s16 alpha,s32 randomize,void *vector,u8 channel,s32 context){u32 i;f32*p=vector;observation.count++;observation.metadata[0]=kind;observation.metadata[1]=word(size);observation.metadata[2]=(u32)(s32)alpha;observation.metadata[3]=(u32)randomize;observation.metadata[4]=0x1234;observation.metadata[5]=channel;observation.metadata[6]=(u32)context;for(i=0;i<3;i++)observation.position[i]=word(p[i]);
if(mode&1){p[0]=99.f;activeOwner->phase=1234;((u8*)activeOwner)[12]^=0x55;}if(mode&2){activeOwner->growthTicks=32767;D_800BE9E4=(s32)0x80000000u;}
}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
typedef struct{u32 before[4];SeedSpriteRuntime151934B4 owner;u32 after[4];}Data;static Data data;SeedSpriteRuntime151934B4 *activeOwner;Observation observation;u32 mode;s32 D_800BE9E4;static u32 row,initialCSR;
typedef struct{Data data;Observation observation;u32 CSR;s32 delta;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static void reference(SeedSpriteRuntime151934B4*p){
 if(p->verticalExtent<p->targetExtent){s32 g=p->growthTicks,q=g>=0?g/4:-((3-g)/4);p->verticalExtent=(s16)(q*8);p->horizontalExtent=(s16)(q*2);p->growthTicks=(s16)((u32)g+(u32)D_800BE9E4);}
 else{s32 f=(s16)((s32)p->fallTicks+1);long long product,half;p->fallTicks=(s16)f;if(f>20){f=20;p->fallTicks=20;}product=(long long)((unsigned long long)(u32)f*(u32)D_800BE9E4&0xffffffffu);if(product>=2147483648LL)product-=4294967296LL;half=product>=0?product/2:-((1-product)/2);p->y=(s16)((long long)p->y-half);
 if(p->y<p->floorY){if(p->variant==1){f32 position[3];position[0]=(f32)p->x;position[1]=(f32)p->floorY;position[2]=(f32)p->z;func_151DBCBC(5,30.f,255,0,position,((u8*)p)[12],((u8*)p)[1]);}p->phase=-1;}}
}
static void fixture(void){u32 i;static const u32 modes[]={0,3,2,1};static const s16 signed16s[]={-32768,-32767,-4,-1,0,1,20,32767};static const u32 deltas[]={0,1,0xffffffffu,0x7fffffffu,0x80000000u,65536};
 for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;activeOwner=&data.owner;
 data.owner.verticalExtent=(row&1)?-1:10;data.owner.targetExtent=(row&1)?1:10;data.owner.growthTicks=signed16s[(row>>1)&7];data.owner.fallTicks=signed16s[(row>>4)&7];data.owner.y=signed16s[(row>>7)&7];data.owner.floorY=signed16s[(row>>10)&7];data.owner.x=signed16s[(row>>3)&7];data.owner.z=signed16s[(row>>6)&7];data.owner.phase=11;data.owner.variant=(row&64)?1:0;((u8*)&data.owner)[12]=(u8)(0x80u+(row&127));((u8*)&data.owner)[1]=(u8)(0x80u+((row>>4)&127));
 D_800BE9E4=(s32)deltas[(row>>5)%6];mode=(row>>8)&3;initialCSR=0x1f80u|(modes[(row>>9)&3]<<13);setCSR(initialCSR);
}
static void capture(void){current.CSR=csr();current.data=data;current.observation=observation;current.delta=D_800BE9E4;}
static s32 fail(void){u32 msg[4]={row,current.observation.count,current.CSR,actual.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<8192;row++){fixture();func_151934B4(&data.owner);capture();actual=current;fixture();reference(&data.owner);capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('phase','sprite->phase = -1;','sprite->phase = -2;'),('growth','((growth >> 2) * 24)','((growth >> 2) * 21)'),('fall-limit','sprite->fallTicks = 20;','sprite->fallTicks = 19;'),('floor','sprite->y < sprite->floorY','sprite->y > sprite->floorY'),('coordinate','position[0] = sprite->x;','position[0] = sprite->y;'),('channel','((u8 *)sprite)[0xC]','((u8 *)sprite)[1]'),('context-sign','((u8 *)sprite)[1]','((s8 *)sprite)[1]')]:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=8192,profiles=profiles,translation_units=3,actual_recovered_C_and_separate_typed_seven_argument_provider=True,valid_typed_partial_owner180_and_float_vector=True,signed16_narrowing_growth_and_full32_unsigned_product_boundaries=True,full_owner_canaries_globals_argument_metadata_positions_and_MXCSR=True,all_four_rounding_modes=True,strict_aliasing_UBSan_traps_LTO_types=True,no_trap_or_signal_counted_as_control=True,opaque_provider_not_original_implementation=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
