"""Actual C in Native32 with valid typed arenas, strict FP and two TUs."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_buffered_matrix_update_151d6e60_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();a,z=function_span(source,'func_151D6E60');body=source[a:z];start=source.index('typedef struct {\n    u8 retained00[0x14]');end=source.index('/* Rebuild the selected matrix',start);header='typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;\n'+source[start:end]+'\ns32 func_151D6E60(BufferedMatrixOwner151D6E60 *);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(BufferedMatrixPosition151D6E60)==32&&sizeof(BufferedMatrixOwner151D6E60)==252&&__builtin_offsetof(BufferedMatrixOwner151D6E60,position)==76&&__builtin_offsetof(BufferedMatrixOwner151D6E60,matrices)==124?1:-1];\n';(o/'native-shared.h').write_text(header)
 harness=r'''
typedef struct{u32 before[4];BufferedMatrixOwner151D6E60 owner;u32 after[4];}OwnerArena;
typedef struct{u32 before[4];BufferedMatrixPosition151D6E60 position;u32 after[4];}PositionArena;
static OwnerArena arena;static PositionArena first,second;
u8 D_800BE9C0;f32 D_800AB278;
static u32 row,mode,pattern,initialCSR,calls;static f32 angleValue;
typedef struct{u32 args[4],CSR;u8 owner[sizeof(OwnerArena)],first[sizeof(PositionArena)],second[sizeof(PositionArena)];u32 page,scale;}Observation;
typedef struct{Observation before[2];u8 owner[sizeof(OwnerArena)],first[sizeof(PositionArena)],second[sizeof(PositionArena)];u32 result,CSR,calls,page,scale;}Capture;
static Capture current,actual;
static u32 word(f32 f){union{f32 f;u32 w;}v;v.f=f;return v.w;}static f32 value(u32 w){union{f32 f;u32 w;}v;v.w=w;return v.f;}
static void copy(void*d,const void*s,u32 n){u8*a=d;const u8*b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];}
static u32 equal(const void*a,const void*b,u32 n){const u8*x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
static void observe(u32 a,u32 b,u32 c,u32 d){Observation*p=&current.before[calls++];p->args[0]=a;p->args[1]=b;p->args[2]=c;p->args[3]=d;p->CSR=csr();copy(p->owner,&arena,sizeof(arena));copy(p->first,&first,sizeof(first));copy(p->second,&second,sizeof(second));p->page=D_800BE9C0;p->scale=word(D_800AB278);}
static void effect(void){
 if(mode&1)D_800BE9C0^=1;
 if(mode&2){first.position.x=-4.25f;first.position.y=5.5f;first.position.z=-6.75f;second.position.x=7.25f;second.position.y=-8.5f;second.position.z=9.75f;}
 if(mode&4)arena.owner.position=&second.position;
 if(mode&8)D_800AB278=calls==1?-.75f:1.25f;
 setCSR(initialCSR|(calls==1?1u:2u));
}
__attribute__((noinline,noclone))f32 func_15144AA8(s32 selector){observe((u32)selector,0,0,0);effect();return angleValue;}
__attribute__((noinline,noclone))void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 i,j;observe((u32)m,word(x),word(y),word(z));for(i=0;i<4;i++)for(j=0;j<4;j++)m[i][j]=value(0x3e000000u+(i*4+j+pattern)*0x10000u);effect();}
__attribute__((noinline,noclone))static s32 reference(BufferedMatrixOwner151D6E60*p){
 f32 angle=func_15144AA8(0)+25.0f,scale;u32 i,j;
 func_150A8050(p->matrices[D_800BE9C0],0.f,angle,0.f);scale=D_800AB278;
 p->matrices[D_800BE9C0][3][0]=p->position->x;
 p->matrices[D_800BE9C0][3][1]=p->position->y+120.0f;
 p->matrices[D_800BE9C0][3][2]=p->position->z;
 for(i=0;i<3;i++)for(j=0;j<3;j++)p->matrices[D_800BE9C0][i][j]=p->matrices[D_800BE9C0][i][j]*scale;
 return 1;
}
static void fixture(void){u32 i,j,k;static const u32 modes[]={0,3,2,1};static const u32 angles[]={0,0x80000000u,0x3e000000u,0xbe800000u,0x42c88000u,1,0x00800000u,0xc2c88000u};
 for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;
 for(i=0;i<sizeof(arena);i++)((u8*)&arena)[i]=(u8)(i*17+row);
 for(i=0;i<sizeof(first);i++){((u8*)&first)[i]=(u8)(i*19+row);((u8*)&second)[i]=(u8)(i*23+row);}
 first.position.x=1.5f;first.position.y=-2.75f;first.position.z=3.125f;second.position.x=-11.5f;second.position.y=12.75f;second.position.z=-13.125f;arena.owner.position=&first.position;
 for(i=0;i<2;i++)for(j=0;j<4;j++)for(k=0;k<4;k++)arena.owner.matrices[i][j][k]=value(0x3f000000u+(i*16+j*4+k+pattern)*0x10000u);
 D_800BE9C0=(row>>4)&1;D_800AB278=value(0x3f0d0e56);angleValue=value(angles[(row>>7)&7]);calls=0;initialCSR=0x1f80u|(modes[(row>>5)&3]<<13)|(1u<<(row%6));setCSR(initialCSR);
}
static void capture(s32 result){current.result=(u32)result;current.CSR=csr();current.calls=calls;current.page=D_800BE9C0;current.scale=word(D_800AB278);copy(current.owner,&arena,sizeof(arena));copy(current.first,&first,sizeof(first));copy(current.second,&second,sizeof(second));}
static s32 fail(void){u32 msg[4]={row,current.result,current.calls,current.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<2048;row++){mode=row&15;pattern=(row>>7)&15;fixture();capture(func_151D6E60(&arena.owner));copy(&actual,&current,sizeof(actual));fixture();capture(reference(&arena.owner));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(f),str(o/'native-harness.c'),'-o',str(exe)],text=True,capture_output=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());(o/(name+'-execution.json')).write_text(json.dumps(report,indent=2)+'\n');assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('angle','25.0f','24.0f'),('height','120.0f','119.0f'),('position-x','[3][0] = owner->position->x;','[3][0] = owner->position->y;'),('return','return 1;','return 0;'),('basis','[0][0] *= scale;','[0][0] += scale;'),('skip-final','    owner->matrices[D_800BE9C0][2][2] *= scale;','')]:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 cached=body.replace('    f32 scale;','    f32 scale;\n    u8 page = D_800BE9C0;').replace('matrices[D_800BE9C0]','matrices[page]');controls.append(dict(name='cached-page',**run('control-cached-page',cached,'-O2',42)))
 early=body.replace('    scale = D_800AB278;\n','').replace('    f32 scale;','    f32 scale = D_800AB278;');controls.append(dict(name='early-scale',**run('control-early-scale',early,'-O2',42)))
 q=dict(cases_per_profile=2048,profiles=profiles,effective_controls=controls,translation_units=2,owner_prefix_and_two_pages_bytes=252,owner_arena_bytes=284,position_object_bytes=32,position_arena_bytes=64,complete_arenas_canaries_pointer_fields_provider_snapshots_and_integer_return=True,all_four_rounding_modes_and_provider_MXCSR=True,valid_two_page_typed_native_arenas_only=True,guest_only_arbitrary_aliases_and_all256_indices=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted=True,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
