"""Actual recovered C in separate typed caller, provider and comparison units."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_owner_preset_record_1519021c_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();body=target_packet.MANIFEST['native_body'];types=target_packet.MANIFEST['native_types'];assert source.count(body.rstrip())==1 and types in source
 header='''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
typedef struct{s8 unk0,unk1;s16 unk2;s8 unk4;u8 pad5;}Header;typedef struct{s32 unk0,unk4,unk8;}Header2;
typedef struct{u8 pad0[20];f32 x_position,y_position,z_position;u8 pad20[27];u8 unique_id;u8 tail[68];}struct127;typedef struct{u8 data[128];}struct225;
'''+types+'''void *memcpy(void*,const void*,u32);struct225 *func_1519021C(u8*,struct127*,u8,s16,u8,s32);
typedef char Layout[sizeof(void*)==4&&sizeof(Header)==6&&sizeof(Header2)==12&&sizeof(PresetOwnerPair1519021C)==8&&__builtin_offsetof(struct127,unique_id)==0x3B?1:-1];
typedef struct{u32 pre[4];struct127 actor;u32 gap[4];struct225 output;u8 parent[64];u32 post[4];}Data;
typedef struct{u32 count;u32 args[4][11];u8 header[5];Header2 position;u8 copied[3][32];}Observation;
extern Data data;extern Observation observation;extern u32 success,mutation,alias,copies;extern u32 row;
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static void effect(void){u32 i;if(mutation){data.actor.unique_id^=0x55;data.actor.x_position=-7.5f;data.actor.y_position=19.25f;data.actor.z_position=-3.5f;for(i=0;i<24;i++){D_800A6760[i]=3.f;D_800A67C0[i]=4.f;D_800A6820[i]=5.f;}D_800A8004=6.f;}}
struct225 *func_151602C0(Header*h,Header2*p,s32 a,s32 b,s32 c,s32 d,u8 e,u8 f,s32 size,u8 channel,s32 context){u32 i,k=observation.count++;u32 values[11]={0x100,0x101,(u32)a,(u32)b,(u32)c,(u32)d,e,f,(u32)size,channel,(u32)context};for(i=0;i<11;i++)observation.args[k][i]=values[i];for(i=0;i<5;i++)observation.header[i]=((u8*)h)[i];observation.position=*p;effect();return success?(alias?(struct225*)&data.actor:&data.output):NULL;}
void *memcpy(void*dest,const void*source,u32 n){u32 i,k=observation.count++,off=(u8*)dest-(alias?(u8*)&data.actor:(u8*)&data.output);observation.args[k][0]=off;observation.args[k][1]=n;for(i=0;i<n;i++)((u8*)dest)[i]=((const u8*)source)[i];if(k>=1&&k<=3){for(i=0;i<n&&i<32;i++){if(!(k==1&&i>=5))observation.copied[k-1][i]=((const u8*)source)[i];}}copies++;effect();return (void*)0xDEADBEEF;}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Data data;Observation observation;u32 row,success,mutation,alias,copies;f32 D_800A6760[24],D_800A67C0[24],D_800A6820[24],D_800A8004;
typedef struct{Data data;Observation observation;u32 csr,value,copies;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
static u8 preset(void){static const u8 values[]={0,1,12,23,24,127,128,255};return values[row&7];}
static s16 lifetime(void){static const s16 values[]={-1,0,1,300,-32768,32767,-2,127};return values[(row>>3)&7];}
__attribute__((noinline,noclone))static struct225 *reference(u8*parent,struct127*actor,u8 index,s16 life,u8 channel,s32 context){struct225*answer;Header h;Header2 p;PresetOwnerPair1519021C pair;f32 v[8];if(index>23)return NULL;pair.owner=actor;pair.identifier=actor->unique_id;v[0]=D_800A67C0[index];v[1]=D_800A6760[index];v[2]=D_800A6820[index];v[3]=1.f;v[4]=0.f;v[5]=5.f;v[6]=D_800A8004;v[7]=0.f;h.unk0=life==-1?2:3;h.unk1=18;h.unk2=life==-1?300:life;h.unk4=37;p.unk0=(s32)actor->x_position;p.unk4=(s32)actor->y_position;p.unk8=(s32)actor->z_position;answer=func_151602C0(&h,&p,0,255,209,0,255,0,48,channel,context);if(answer){memcpy((u8*)answer+24,&pair,8);memcpy((u8*)answer+32,v,32);memcpy((u8*)answer+64,&parent,4);}return answer;}
static void fixture(void){u32 i;static const u32 modes[]={0,3,2,1};static const f32 coords[]={0.f,-0.f,1.25f,-2.75f,32767.75f,65536.5f,-65536.5f,17.f};for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;data.actor.x_position=coords[(row>>6)&7];data.actor.y_position=-12.25f;data.actor.z_position=3.75f;data.actor.unique_id=(u8)row;for(i=0;i<24;i++){D_800A6760[i]=(f32)i;D_800A67C0[i]=(f32)i+.5f;D_800A6820[i]=-(f32)i-.25f;}D_800A8004=.2489f;success=(row>>9)&1;mutation=(row>>10)&1;alias=(row>>11)&1;copies=0;setCSR(0x1f80u|(modes[(row>>4)&3]<<13));}
static void capture(struct225*p){u8*out;if(p&&!(alias&&mutation)){out=(u8*)p;out[0x1D]=0;out[0x1E]=0;out[0x1F]=0;}current.csr=csr();current.data=data;current.observation=observation;current.value=(u32)p;current.copies=copies;}
static s32 fail(void){u32 msg[4]={row,current.observation.count,current.value^actual.value,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){u8 index=preset();fixture();capture(func_1519021C(data.parent,index<24?&data.actor:NULL,index,lifetime(),(u8)(row>>2),(s32)(row^0x87654321u)));actual=current;fixture();capture(reference(data.parent,index<24?&data.actor:NULL,index,lifetime(),(u8)(row>>2),(s32)(row^0x87654321u)));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('bounds','preset >= 24','preset >= 23'),('life','? 300 : lifetime','? 301 : lifetime'),('table','D_800A67C0[preset]','D_800A6760[preset]'),('owner-id','owner.identifier = actor->unique_id','owner.identifier = actor->unique_id ^ 1'),('factory-size','0x30, channel','0x2C, channel'),('channel','0x30, channel','0x30, (u8)(channel + 1)'),('third-copy','+ 0x40, &parent','+ 0x44, &parent'),('return','return created;','return NULL;')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_recovered_C_typed_actor128_header6_position12_pair8=True,native_only_defined_header5_pair5_and_all_values_parent_bytes_observed=True,pair_padding3_canonicalized_only_in_capture_not_source_or_runtime=True,invalid_preset_null_actor_and_valid_finite_s32_conversion_range=True,mutating_providers_and_output_alias_actor=True,all_four_rounding_modes=True,full_typed_arenas_canaries_metadata_return_and_MXCSR_equal=True,strict_aliasing_UBSan_traps_LTO_types=True,opaque_providers_not_original_backend_implementation=True,no_trap_or_signal_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
