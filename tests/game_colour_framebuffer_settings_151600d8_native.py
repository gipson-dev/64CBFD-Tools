"""Actual settings, repaired C caller and retail default body across three TUs."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_colour_framebuffer_settings_151600d8_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();a,z=function_span(source,'func_151600D8');body=source[a:z];a,z=function_span(source,'func_1515FFEC');parent=source[a:z];assert 'D_8008B0D0[callbackIndex](arg0)'in parent
 start=source.index('typedef struct {\n    f32 positionS, positionT;');end=source.index('/* Read the retail colour',start)
 header='typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;\n#define NULL ((void*)0)\n'+source[start:end]+'\nextern s32 D_800BE9E4;extern s32 (*D_8008B0D0[])();\ns32 func_151600D8(u8*);void func_1515FFEC(u8*);void func_1516972C(u8*);s32 retail_default_provider(s32,s32,s32,s32,s32,s32,s32);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(ColourFrameBufferSettings151600D8)==20&&sizeof(ColourFrameBufferOwner151600D8)==44&&__builtin_offsetof(ColourFrameBufferOwner151600D8,settings)==24&&__builtin_offsetof(ColourFrameBufferOwner151600D8,remainingTicks)==18&&__builtin_offsetof(ColourFrameBufferOwner151600D8,callbackIndex)==15?1:-1];\n';(o/'native-shared.h').write_text(header)
 sdk=(o/'baseline/conker/src/game_16EE20.c').read_text();a,z=function_span(sdk,'func_151422DC');sdk=sdk[a:z].replace('func_151422DC','retail_default_provider');(o/'native-retail-provider.c').write_text('#include "native-shared.h"\n__attribute__((noinline,noclone))\n'+sdk+'\n')
 harness=r'''
u8 D_800A6540[]="pos s",D_800A657C[]="pos t",D_800A65B8[]="size s",D_800A65F4[]="size t",D_800A6630[]="pixelation";
u8 D_800A6548[]="../Effects/ColourFrameBuffer/colourframebuffer.c",D_800A6584[]="../Effects/ColourFrameBuffer/colourframebuffer.c",D_800A65C0[]="../Effects/ColourFrameBuffer/colourframebuffer.c",D_800A65FC[]="../Effects/ColourFrameBuffer/colourframebuffer.c",D_800A663C[]="../Effects/ColourFrameBuffer/colourframebuffer.c";
f32 D_800A6674,D_800A6678,D_800A667C,D_800A6680;s32 D_800BE9E4;s32 (*D_8008B0D0[])()={func_151600D8,NULL};
typedef struct{u32 before[4];ColourFrameBufferOwner151600D8 owner;u32 after[4];}Arena;static Arena arena;
typedef struct{u32 args[7],CSR;Arena arena;u32 coefficients[4];s32 ticks;}Observation;
typedef struct{Observation before[5];Arena arena;u32 coefficients[4],calls,freeCalls,freeArgument,result,CSR;s32 ticks;}Capture;
static Capture current,actual;static u32 row,calls,freeCalls,freeArgument,initialCSR,mode,actualProvider;
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 value(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
static void coefficients(u32*v){v[0]=word(D_800A6674);v[1]=word(D_800A6678);v[2]=word(D_800A667C);v[3]=word(D_800A6680);}
__attribute__((noinline,noclone))s32 func_151422DC(s32 index,s32 label,s32 minimum,s32 maximum,s32 defaultValue,s32 file,s32 line){
 static const u32 values[]={0,1,0xffffffffu,0x7fffffffu,0x80000000u,0x01000001u,0xfeffffffu,65536};Observation*p=&current.before[calls++];
 p->args[0]=(u32)index;p->args[1]=(u32)label;p->args[2]=(u32)minimum;p->args[3]=(u32)maximum;p->args[4]=(u32)defaultValue;p->args[5]=(u32)file;p->args[6]=(u32)line;p->CSR=csr();p->arena=arena;coefficients(p->coefficients);p->ticks=D_800BE9E4;
 if(actualProvider)return retail_default_provider(index,label,minimum,maximum,defaultValue,file,line);
 if(mode&1){D_800A6674=-(f32)calls*.125f;D_800A6678=-(f32)calls*.25f;D_800A667C=-(f32)calls*.375f;D_800A6680=-(f32)calls*.5f;}
 if(mode&2){arena.owner.settings.positionS=(f32)calls*.25f;arena.owner.settings.positionT=(f32)calls*.5f;arena.owner.settings.sizeS=(f32)calls*.75f;arena.owner.settings.sizeT=(f32)calls;}
 if(mode&4)arena.owner.settings.pixelation=(s32)(0xa6000000u+calls-1);
 setCSR(initialCSR|((mode&8)?((calls&1)?1u:2u):0));return(s32)values[((row>>5)+calls-1)&7];
}
__attribute__((noinline,noclone))void func_1516972C(u8*owner){if(owner!=(u8*)&arena.owner)__builtin_trap();freeCalls++;freeArgument=(u32)owner;}
__attribute__((noinline,noclone))static s32 reference(u8*raw){ColourFrameBufferSettings151600D8*p=&((ColourFrameBufferOwner151600D8*)raw)->settings;f32 f;
 f=(f32)func_151422DC(0,(s32)D_800A6540,-2000,2000,0,(s32)D_800A6548,452);p->positionS=f*D_800A6674;
 f=(f32)func_151422DC(1,(s32)D_800A657C,-2000,2000,0,(s32)D_800A6584,457);p->positionT=f*D_800A6678;
 f=(f32)func_151422DC(2,(s32)D_800A65B8,0,2000,500,(s32)D_800A65C0,462);p->sizeS=f*D_800A667C;
 f=(f32)func_151422DC(3,(s32)D_800A65F4,0,2000,500,(s32)D_800A65FC,467);p->sizeT=f*D_800A6680;
 p->pixelation=func_151422DC(4,(s32)D_800A6630,0,65536,65536,(s32)D_800A663C,473);return 1;
}
__attribute__((noinline,noclone))static void parentReference(u8*raw){ColourFrameBufferOwner151600D8*p=(ColourFrameBufferOwner151600D8*)raw;s32 remove=0;
 if(p->flags&1){p->remainingTicks=(s16)((s32)p->remainingTicks-D_800BE9E4);if(p->remainingTicks<0)remove=1;}
 if(!remove&&p->callbackIndex!=-1){if(!reference(raw))remove=1;}if(remove)func_1516972C(raw);
}
static void fixture(void){u32 i;static const u32 modes[]={0,3,2,1};static const s16 lives[]={-32768,-1,0,1,32767};static const s32 ticks[]={-65536,-1,0,1,65536};static const u32 scales[]={0x3a83126fu,0x3f000000u,0xbf400000u,0,0x80000000u,1,0x00800000u,0x3fa00000u};
 for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;for(i=0;i<sizeof(arena);i++)((u8*)&arena)[i]=(u8)(i*19+row);
 arena.owner.flags=(row>>3)&1;arena.owner.callbackIndex=(row&16)?-1:0;arena.owner.remainingTicks=lives[(row>>7)%5];D_800BE9E4=ticks[(row>>9)%5];
 D_800A6674=value(scales[(row>>5)&7]);D_800A6678=value(scales[((row>>5)+1)&7]);D_800A667C=value(scales[((row>>5)+2)&7]);D_800A6680=value(scales[((row>>5)+3)&7]);
 calls=freeCalls=freeArgument=0;initialCSR=0x1f80u|(modes[(row>>8)&3]<<13);setCSR(initialCSR);
}
static void capture(s32 result){current.result=(u32)result;current.CSR=csr();current.arena=arena;coefficients(current.coefficients);current.calls=calls;current.freeCalls=freeCalls;current.freeArgument=freeArgument;current.ticks=D_800BE9E4;}
static s32 fail(void){u32 msg[4]={row,current.calls,current.freeCalls,current.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){mode=(row>>1)&15;actualProvider=(row>>6)&1;fixture();if(row&1){func_1515FFEC((u8*)&arena.owner);capture(0x1234);}else capture(func_151600D8((u8*)&arena.owner));actual=current;
 fixture();if(row&1){parentReference((u8*)&arena.owner);capture(0x1234);}else capture(reference((u8*)&arena.owner));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-unused-parameter']
 def run(name,target,consumer,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+target+'\n'+consumer+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-retail-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,parent,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('return','    return 1;','    return 0;'),('line',', 452)',', 453)'),('index','    s32 index = 0;','    s32 index = 1;'),('position','settings->positionS =','settings->positionT ='),('size-coefficient',') * D_800A667C;',') * D_800A6678;'),('pixelation','func_151422DC(index++, (s32)D_800A6630, 0, 65536, 65536,\n                     (s32)D_800A663C, 473);','func_151422DC(index++, (s32)D_800A6630, 0, 65536, 65536,\n                     (s32)D_800A663C, 473) ^ 1;')]:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),parent,'-O2',42)))
 cached=body.replace('    s32 index = 0;','    s32 index = 0;\n    f32 cachedScale = D_800A6674;').replace(') * D_800A6674;',') * cachedScale;');controls.append(dict(name='early-coefficient',**run('control-early-coefficient',cached,parent,'-O2',42)))
 needle='D_8008B0D0[callbackIndex](arg0) == 0';assert parent.count(needle)==1;controls.append(dict(name='parent-zero-test',**run('control-parent-zero-test',body,parent.replace(needle,'D_8008B0D0[callbackIndex](arg0) != 0'),'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_selected_C_and_repaired_original_C_parent_executed=True,selected_native_table_index0_and_minus_one_skip_only=True,actual_original_seven_argument_default_C_body_executed=True,additional_opaque_provider_contract_with_INT32_boundaries_and_mutations=True,valid_typed_owner_header_lifetime_and_settings_subobject=True,full_arena_canaries_metadata_arguments_provider_snapshots_globals_return_and_MXCSR=True,all_four_rounding_modes_and_finite_subnormal_coefficients=True,strict_aliasing_UBSan_traps_LTO_types=True,no_trap_or_signal_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
