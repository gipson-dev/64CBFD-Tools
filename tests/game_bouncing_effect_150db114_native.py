"""Actual recovered C in typed native32 arenas under strict floating point."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_bouncing_effect_150db114_match as target_packet
o=target_packet.OUT
def main():
 s=(o/'selected-owner.c').read_text();a,z=function_span(s,'func_150DB114');body=s[a:z];start=s.index('typedef struct {');end=s.index('/* Integrate damped motion',start)
 header='typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;\n'+s[start:end]+'s32 func_150DB114(BouncingEffectOwner150DB114*);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(BouncingEffectOwner150DB114)==316&&sizeof(BouncingEffectMotion150DB114)==44&&__builtin_offsetof(BouncingEffectOwner150DB114,motion)==272&&__builtin_offsetof(BouncingEffectOwner150DB114,alpha)==92?1:-1];\n';(o/'native-shared.h').write_text(header)
 harness=r'''
typedef struct{u32 before[4];BouncingEffectOwner150DB114 owner;u32 after[4];}Data;static Data data;f32 D_800BE9A4;static u32 row;
typedef struct{Data data;u32 CSR;s32 result;f32 dt;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static f32 mul(f32 a,f32 b){return a*b;}
__attribute__((noinline,noclone))static f32 add(f32 a,f32 b){return a+b;}
__attribute__((noinline,noclone))static s32 reference(BouncingEffectOwner150DB114*p){
 BouncingEffectMotion150DB114*m=&p->motion;f32 d=m->damping;s32 alpha=(s32)p->alpha;f32 v[3];
 v[0]=mul(m->velocityX,d);v[1]=mul(m->velocityY,d);v[2]=mul(m->velocityZ,d);m->velocityX=v[0];m->velocityY=v[1];m->velocityZ=v[2];
 p->x=add(p->x,mul(m->velocityX,D_800BE9A4));p->y=add(p->y,mul(m->velocityY,D_800BE9A4));p->z=add(p->z,mul(m->velocityZ,D_800BE9A4));
 m->stretchY=add(m->stretchY,mul(m->stretchVelocityY,D_800BE9A4));
 if(m->stretchY>1.2f){m->stretchY=1.2f;m->stretchVelocityY=-m->stretchVelocityY;}else if(m->stretchY<.8f){m->stretchY=.8f;m->stretchVelocityY=-m->stretchVelocityY;}
 m->stretchZ=add(m->stretchZ,mul(m->stretchVelocityZ,D_800BE9A4));
 if(m->stretchZ>1.2f){m->stretchZ=1.2f;m->stretchVelocityZ=-m->stretchVelocityZ;}else if(m->stretchZ<.8f){m->stretchZ=.8f;m->stretchVelocityZ=-m->stretchVelocityZ;}
 m->scale=add(m->scale,mul(m->scaleRate,D_800BE9A4));p->sizeY=mul(m->scale,m->stretchY);p->sizeZ=mul(m->scale,m->stretchZ);
 alpha-=(s32)m->fadeStep;p->alpha=(u8)(alpha<0?0:alpha);return alpha>=0;
}
static void fixture(void){u32 i;static const u32 rms[]={0,3,2,1};static const f32 bounds[]={.5f,.8f,1.f,1.2f,2.f,-.5f,0.f,-0.f};static const f32 deltas[]={0.f,.25f,-.5f,1.f};BouncingEffectOwner150DB114*p=&data.owner;BouncingEffectMotion150DB114*m=&p->motion;
 for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;
 p->x=12.f;p->y=-34.f;p->z=56.f;m->velocityX=1.125f;m->velocityY=-2.5f;m->velocityZ=3.75f;m->stretchY=bounds[row&7];m->stretchZ=bounds[(row>>3)&7];m->stretchVelocityY=deltas[(row>>6)&3];m->stretchVelocityZ=-deltas[(row>>8)&3];m->scale=2.f;m->scaleRate=.125f;m->damping=(row&256)?0.f:.875f;p->alpha=(u8)(row>>3);m->fadeStep=(u8)(row>>5);D_800BE9A4=deltas[(row>>5)&3];setCSR(0x1f80u|(rms[(row>>10)&3]<<13));
}
static void capture(void){current.CSR=csr();current.data=data;current.dt=D_800BE9A4;}
static s32 fail(void){u32 msg[4]={row,(u32)current.result,(u32)actual.result,current.CSR^actual.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<8192;row++){fixture();current.result=func_150DB114(&data.owner);capture();actual=current;fixture();current.result=reference(&data.owner);capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('upper','upper = 1.2f','upper = 1.3f'),('lower','lower = 0.8f','lower = 0.7f'),('damping','motion->velocityY *= damping;','motion->velocityY += damping;'),('bounce','motion->stretchVelocityZ = -motion->stretchVelocityZ;','motion->stretchVelocityZ = motion->stretchVelocityZ;'),('scale','motion->scaleRate * D_800BE9A4','motion->scaleRate + D_800BE9A4'),('alpha-equality','if (alpha < 0)','if (alpha <= 0)'),('fade-sign','alpha -= motion->fadeStep;','alpha -= (signed char)motion->fadeStep;')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=8192,profiles=profiles,translation_units=2,actual_recovered_C_in_typed_owner316_and_motion44=True,all_four_rounding_modes=True,full_owner_canaries_DT_return_and_MXCSR_equal=True,strict_aliasing_UBSan_traps_LTO_types=True,no_trap_or_signal_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
