"""Native32 actual typed workspace, initialized fields, SDK copy and ABI controls."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_owner_effect_factory_151c6ea0_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();a,z=function_span(source,'func_151C6EA0');body=source[a:z];start=source.index('/* Only the observed source prefix');end=source.index('/* Submit the owner-linked descriptor',start);types=source[start:end]
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;typedef unsigned int size_t;
 #define NULL ((void*)0)
 void *memcpy(void *,const void *,size_t);
 '''+types+'''
 void func_151C6EA0(OwnerEffectSource151C6EA0 *,u8,s32);
 typedef char ABI[sizeof(void*)==4&&sizeof(size_t)==4&&sizeof(OwnerEffectSource151C6EA0)==60&&sizeof(OwnerEffectDescriptor151C6EA0)==124&&sizeof(OwnerEffectWorkspace151C6EA0)==128&&__builtin_offsetof(OwnerEffectWorkspace151C6EA0,descriptor)==4?1:-1];
 '''
 spans=[('scale',0,8),('extent',8,8),('direction',16,12),('unitScale',28,12),('position',40,12),('velocity',52,12),('reference',64,12),('zero4C',76,4),('flags',80,4),('lifetime',84,2),('resourceId',86,2),('zero58',88,1),('padding59',89,3),('zero5C',92,4),*[(n,96+i,1)for i,n in enumerate(('value60','value61','zero62','zero63','zero64','zero65','zero66','zero67','value68'))],('sentinel69',105,1),('value6A',106,1),('padding6B',107,1),('owner',108,4),('sourceIdentity',112,1),('padding71',113,1),('value72',114,2),('value74',116,2),('padding76',118,2),('zero78',120,4)]
 assert sorted(at+i for _,at,n in spans for i in range(n))==list(range(124))
 for name,at,n in spans:header+=f'typedef char offset_{name}[__builtin_offsetof(OwnerEffectDescriptor151C6EA0,{name})=={at}&&sizeof(((OwnerEffectDescriptor151C6EA0*)0)->{name})=={n}?1:-1];\n'
 (o/'native-shared.h').write_text(header)
 actual=(o/'baseline/conker/src/libultra/libc/string.c').read_text();a,z=function_span(actual,'memcpy');copy=actual[a:z].replace('memcpy(','actual_copy(',1)
 harness=r'''
typedef struct{u32 prefix[4];OwnerEffectSource151C6EA0 owner;u32 suffix[4];}SourceArena;
static SourceArena live;static union{u32 align;u8 bytes[448];}arena;
OwnerEffectVector151C6EA0 D_800A5480;
static u32 row,mode,outcome,slotValue,contextValue,identityValue,phase,bad,defaults[3],initialCSR;
static u8 expectedArena[448],packetAfter[124];static u8 *passedPacket;
static u32 get32(const void*p){const u8*b=p;return (u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
static void put32(void*p,u32 v){u8*b=p;b[0]=(u8)v;b[1]=(u8)(v>>8);b[2]=(u8)(v>>16);b[3]=(u8)(v>>24);}
static void big(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
static void half(u8*p,u32 v){p[0]=(u8)(v>>8);p[1]=(u8)v;}
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
static u32 hole(u32 i){return i==89||i==90||i==91||i==107||i==113||i==118||i==119;}
static u8 packetByte(const u8*p,u32 i){u32 a;if(i<84||(i>=92&&i<96)||(i>=108&&i<112)||i>=120){a=i&~3u;return p[a+3-(i-a)];}if((i>=84&&i<88)||(i>=114&&i<118)){a=i&~1u;return p[a+1-(i-a)];}return p[i];}
static void expectedPacket(u8*p){u32 i,j;for(i=0;i<124;i++)p[i]=0;for(i=0;i<4;i++)big(p+4*i,0x3f800000u);for(i=0;i<3;i++)big(p+28+4*i,0x3f800000u);for(j=0;j<4;j++)for(i=0;i<3;i++)big(p+(j==0?16:j==1?40:j==2?52:64)+4*i,defaults[i]);big(p+80,0x11900);half(p+84,300);half(p+86,15);p[96]=100;p[97]=23;p[104]=5;p[105]=255;p[106]=1;big(p+108,(u32)&live.owner);p[112]=(u8)identityValue;half(p+114,1);half(p+116,255);}
void *func_1513264C(u8*descriptor,s32 resource,s32 value,ExtendedState15F680*state,s32 payloadBytes,u8 slot,s32 context){u32 i;u8 expected[124];
 if(phase||csr()!=initialCSR||resource!=3||value!=255||state||payloadBytes!=1||slot!=slotValue||(u32)context!=contextValue)bad=1;
 expectedPacket(expected);for(i=0;i<124;i++)if(!hole(i)&&packetByte(descriptor,i)!=expected[i])bad=1;
 if(mode&1)for(i=0;i<60;i++)((u8*)&live.owner)[i]=(u8)(i*13+row);
 if(mode&2)for(i=0;i<3;i++)put32((u8*)&D_800A5480+4*i,0x41000000u+i*0x10000u);
 if(mode&4)for(i=0;i<124;i++)descriptor[i]=(u8)(i*7+row*11+49);
 for(i=0;i<124;i++)packetAfter[i]=descriptor[i];passedPacket=descriptor;
 if(outcome)actual_copy(arena.bytes+48,descriptor,124);
 for(i=0;i<448;i++)expectedArena[i]=arena.bytes[i];phase=1;setCSR(initialCSR|1u);return outcome?arena.bytes+32:NULL;
}
void *memcpy(void*destination,const void*source,size_t n){u32 i;
 if(phase!=1||!outcome||csr()!=(initialCSR|1u)||destination!=arena.bytes+400||n!=1||(u32)source+4!=(u32)passedPacket)bad=1;
 if(*(const u8*)source!=0)bad=1;for(i=0;i<124;i++)if(!hole(i)&&passedPacket[i]!=packetAfter[i])bad=1;
 /* Wrong widths are comparison controls; do not execute invalid control reads. */
 if(n==1)actual_copy(destination,source,n);phase=2;setCSR(initialCSR|2u);return destination;
}
static s32 fail(u32 why){u32 msg[4]={row,why,phase,bad},nr=4;__asm__ volatile("int $0x80":"+a"(nr):"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){static const u32 patterns[8]={0,0x80000000u,1,0x00800000u,0x7f7fffffu,0x7f800000u,0x7fc12345u,0xff800000u};static const u32 modes[4]={0,3,2,1};u32 i;
 for(row=0;row<4096;row++){slotValue=row&255;mode=(row>>8)&7;outcome=(row>>11)&1;identityValue=(slotValue*73+31+mode)&255;contextValue=(row&3)==0?0:(row&3)==1?1:(row&3)==2?0x80000000u:0xffffffffu;phase=bad=0;
  for(i=0;i<sizeof(SourceArena);i++)((u8*)&live)[i]=(u8)(i*17+row);live.owner.identity=(u8)identityValue;
  for(i=0;i<448;i++)arena.bytes[i]=(u8)(i*29+row*11+90);
  for(i=0;i<3;i++){defaults[i]=patterns[(row+i)&7];put32((u8*)&D_800A5480+4*i,defaults[i]);}
  initialCSR=0x1f80u|(modes[row&3]<<13)|(1u<<(row%6));setCSR(initialCSR);func_151C6EA0(&live.owner,(u8)slotValue,(s32)contextValue);
  if(bad||phase!=(outcome?2u:1u)||csr()!=(initialCSR|(outcome?2u:1u)))return fail(1);
  for(i=0;i<448;i++){u8 expected=(outcome&&i==400)?0:expectedArena[i];if(arena.bytes[i]!=expected)return fail(2+i);}
  for(i=0;i<sizeof(SourceArena);i++){u8 expected=(mode&1)&&i>=16&&i<76?(u8)((i-16)*13+row):i==75?(u8)identityValue:(u8)(i*17+row);if(((u8*)&live)[i]!=expected)return fail(450+i);}
  for(i=0;i<3;i++)if(get32((u8*)&D_800A5480+4*i)!=((mode&2)?0x41000000u+i*0x10000u:defaults[i]))return fail(550+i);
 }return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+copy+'\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(f),str(o/'native-harness.c'),'-o',str(exe)],text=True,capture_output=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());(o/(name+'-execution.json')).write_text(json.dumps(report,indent=2)+'\n');assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in ('O0','O2','O3')];controls=[]
 for name,old,new in [('initial-byte','workspace.initialPayload = 0;','workspace.initialPayload = 1;'),('flags','flags = 0x11900;','flags = 0x11901;'),('lifetime','lifetime = 300;','lifetime = 301;'),('resource','resourceId = 15;','resourceId = 14;'),('owner','owner = source;','owner = NULL;'),('identity','sourceIdentity = source->identity;','sourceIdentity = slot;'),('sentinel','sentinel69 = -1;','sentinel69 = 0;'),('value6A','value6A = 1;','value6A = 2;'),('payload-size','NULL, 1, slot, context','NULL, 2, slot, context'),('slot','NULL, 1, slot, context','NULL, 1, slot ^ 1, context'),('context','NULL, 1, slot, context','NULL, 1, slot, context ^ 1'),('copy-width','&workspace.initialPayload, 1);','&workspace.initialPayload, 2);'),('copy-destination','result + 0x170','result + 0x171')]:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,effective_controls=controls,translation_units=2,source_prefix_bytes=60,source_identity_offset=59,descriptor_bytes=124,initialized_descriptor_bytes=117,unwritten_descriptor_bytes=7,workspace_bytes=128,descriptor_offset_in_workspace=4,full_output_arena_bytes=448,full_source_arena_bytes=92,all_defined_descriptor_fields_checked=True,unwritten_padding_native_value_not_assumed=True,full_after_factory_arena_and_source_canaries_and_globals_checked=True,actual_SDK_memcpy_C_executed_for_valid_calls=True,wrong_width_control_invalid_reads_not_executed=True,descriptor_observed_only_during_target_lifetime=True,void_return_no_incidental_V0_contract=True,all_four_rounding_modes_and_provider_sticky_flags=True,strict_aliasing_UBSan_traps_LTO_type_errors=True,no_signal_or_trap_counted=True,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
