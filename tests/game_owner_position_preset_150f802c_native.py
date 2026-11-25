"""Native32 actual-source ABI, all descriptor fields, tail lifetime and copy extent."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.experiments import game_owner_position_preset_150f802c_match as p
def main():
 r,o=p.ROOT,p.OUT;source=p.MANIFEST['selected_source'];a,z=function_span(source,'func_150F802C');body=source[a:z]
 start=source.index('typedef struct { f32 x, y, z; } OwnerEffectVector150F802C;');end=source.index('/* Capture a source record',start);types=source[start:end]
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;
 typedef unsigned int u32;typedef int s32;typedef float f32;typedef u32 size_t;
 void *memcpy(void *,const void *,size_t);
 '''+types+'''
 void func_150F802C(OwnerEffectRecord150F802C *,s16,u8,s32);
 typedef char size_input[sizeof(OwnerEffectRecord150F802C)==68?1:-1];
 typedef char size_descriptor[sizeof(OwnerEffectDescriptor150F802C)==124?1:-1];
 typedef char size_tail[sizeof(OwnerEffectTail150F802C)==20?1:-1];
 '''
 spans=[('scale',0,8),('extent',8,8),('direction',16,12),('unitScale',28,12),('position',40,12),('zeroVelocity',52,12),('reference',64,12),('zero4C',76,4),('flags',80,4),('parameter',84,2),('resourceId',86,2),('zero58',88,1),('padding59',89,3),('zero5C',92,4),*[(name,96+i,1)for i,name in enumerate(('value60','value61','zero62','zero63','zero64','zero65','zero66','zero67','zero68'))],('padding69',105,1),('zero6A',106,1),('padding6B',107,1),('zero6C',108,4),('zero70',112,1),('padding71',113,1),('value72',114,2),('value74',116,2),('padding76',118,2),('zero78',120,4)]
 assert sorted(at+i for _,at,n in spans for i in range(n))==list(range(124))
 for name,at,n in spans:header+=f'typedef char offset_{name}[__builtin_offsetof(OwnerEffectDescriptor150F802C,{name})=={at}?1:-1];\ntypedef char width_{name}[sizeof(((OwnerEffectDescriptor150F802C *)0)->{name})=={n}?1:-1];\n'
 for name,at in [('owner',0),('position',4),('zero10',16)]:header+=f'typedef char tail_{name}_offset[__builtin_offsetof(OwnerEffectTail150F802C,{name})=={at}?1:-1];\n'
 (o/'native-shared.h').write_text(header)
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();data_start,data_base,_,_=load_game_data_layout(r/'conker');constants=[]
 for address,n in [(0x800a1bdc,4),(0x800a5480,12)]:
  at=elf_slot_offset(elf,address,n);blob=elf[at:at+n];assert blob==rom[data_start+address-data_base:data_start+address-data_base+n];constants.extend(int.from_bytes(blob[i:i+4],'big')for i in range(0,n,4))
 actual=(o/'baseline/conker/src/libultra/libc/string.c').read_text();a,z=function_span(actual,'memcpy');copy=actual[a:z].replace('memcpy(', 'actual_copy(',1)
 harness=r'''
 static OwnerEffectRecord150F802C live;
 f32 D_800A1BDC;OwnerEffectVector150F802C D_800A5480;
 static union {u32 align;u8 bytes[612];} arena;
 static u32 bad,phase,activeOutcome,mutation,slotValue,contextValue,parameterValue,original[6],seed;
 static u32 get32(const void *p){const u8 *b=p;return (u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
 static void put32(void *p,u32 v){u8 *b=p;b[0]=(u8)v;b[1]=(u8)(v>>8);b[2]=(u8)(v>>16);b[3]=(u8)(v>>24);}
 static void big(u8 *p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
 static void half(u8 *p,u32 v){p[0]=(u8)(v>>8);p[1]=(u8)v;}
 static u32 mxcsr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}
 static u32 csr(u32 step){static const u32 map[4]={0,3,2,1};return 0x1f80u|(map[seed&3]<<13)|(step?1u<<(step-1):0);}
 static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
 static u32 hole(u32 i){return i==89||i==90||i==91||i==105||i==107||i==113||i==118||i==119;}
 static u8 packetByte(const u8 *p,u32 i){u32 base;
  if(i<84){base=i&~3u;return p[base+3-(i-base)];}
  if(i>=84&&i<88){base=i&~1u;return p[base+1-(i-base)];}
  if((i>=92&&i<96)||(i>=108&&i<112)||(i>=120&&i<124)){base=i&~3u;return p[base+3-(i-base)];}
  if(i>=114&&i<118){base=i&~1u;return p[base+1-(i-base)];}
  return p[i];
 }
 static void expectedPacket(u8 *p){u32 i;for(i=0;i<124;i++)p[i]=0;
  big(p,0x3f800000u);big(p+4,0x3f800000u);big(p+8,constantWords[0]);big(p+12,constantWords[0]);
  for(i=0;i<3;i++){big(p+16+4*i,original[3+i]);big(p+28+4*i,0x3f800000u);big(p+40+4*i,original[i]);big(p+64+4*i,constantWords[1+i]);}
  big(p+80,0x980);half(p+84,parameterValue);half(p+86,47);p[96]=255;p[97]=20;half(p+114,1);half(p+116,255);
 }
 void *func_1513264C(u8 *descriptor,s32 resource,s32 value,ExtendedState15F680 *state,s32 payloadBytes,u8 slot,s32 context){u32 i;u8 expected[124];
  if(phase!=0||mxcsr()!=csr(0)||resource!=3||value!=255||state!=0||payloadBytes!=180||slot!=slotValue||(u32)context!=contextValue)bad=1;
  expectedPacket(expected);for(i=0;i<124;i++)if(!hole(i)&&packetByte(descriptor,i)!=expected[i])bad=1;
  if(mutation&1)for(i=0;i<68;i++)((u8 *)&live)[i]=(u8)(i*13+seed);
  if(mutation&2){put32(&D_800A1BDC,0xc1200000u);for(i=0;i<3;i++)put32((u8 *)&D_800A5480+4*i,0x41000000u+0x10000*i);}
  if(mutation&4)for(i=0;i<124;i++)descriptor[i]=(u8)(i*7+seed*11+0x31);
  phase=1;setCSR(csr(1));return activeOutcome?arena.bytes+32:(void *)0;
 }
 void *memcpy(void *destination,const void *source,size_t n){const OwnerEffectTail150F802C *tail=source;u32 i;
  if(phase!=1||!activeOutcome||mxcsr()!=csr(1)||destination!=arena.bytes+32+0x170||n!=20)bad=1;
  if(tail->owner!=&live||get32(&tail->zero10)!=0)bad=1;
  for(i=0;i<3;i++)if(get32(&tail->position[i])!=original[i])bad=1;
  actual_copy(destination,source,n);phase=2;setCSR(csr(2));return destination;
 }
 static s32 main(void){static const u32 parameters[8]={0,1,0xffff,0x8000,0x7fff,0x1234,0x00ff,0xff00};
  static const u32 values[8]={0x3fa00000u,0xc0200000u,0x40700000u,0x80000000u,1,0x00800000u,0x7f7fffffu,0xff7fffffu};u32 row,outcome,i;u8 expectedTail[20];
  for(row=0;row<1024;row++)for(outcome=0;outcome<2;outcome++){
   seed=row;slotValue=row&255;contextValue=row&1?0x87654321u:(row&2?0xffffffffu:0);parameterValue=parameters[(row>>2)&7];mutation=(row>>4)&7;activeOutcome=outcome;phase=bad=0;
   for(i=0;i<6;i++){original[i]=values[(row+i)&7];put32((u8 *)&live+4*i,original[i]);}
   for(i=24;i<68;i++)((u8 *)&live)[i]=(u8)(i*17+row);
   put32(&D_800A1BDC,constantWords[0]);for(i=0;i<3;i++)put32((u8 *)&D_800A5480+4*i,constantWords[1+i]);
   for(i=0;i<612;i++)arena.bytes[i]=(u8)(i*29+row*11+0x5a);
   put32(expectedTail,(u32)&live);for(i=0;i<3;i++)put32(expectedTail+4+4*i,original[i]);put32(expectedTail+16,0);setCSR(csr(0));
   func_150F802C(&live,(s16)parameterValue,(u8)slotValue,(s32)contextValue);
   if(phase!=(outcome?2u:1u)||mxcsr()!=csr(outcome?2:1))bad=1;
   for(i=0;i<612;i++){u8 expected=(outcome&&i>=400&&i<420)?expectedTail[i-400]:(u8)(i*29+row*11+0x5a);if(arena.bytes[i]!=expected)bad=1;}
   if(bad)return 42;
  }
  return 0;
 }
 __attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
 '''
 (o/'native-harness.c').write_text('#include "native-shared.h"\nstatic const u32 constantWords[4]={' +','.join(hex(v)+'u'for v in constants)+'};\n'+copy+'\n'+harness)
 base=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation']
 def run(name,function,opt,expected):
  f=o/(name+'.c');f.write_text('#include "native-shared.h"\n'+function+'\n');exe=o/(name+'.exe');cmd=[*base,opt,str(f),str(o/'native-harness.c'),'-o',str(exe)];p=subprocess.run(cmd,capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr);p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==expected,(name,p.returncode,p.stdout,p.stderr)
  return dict(comparison_exit=p.returncode,command=cmd,source_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 profiles={opt:run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')};controls=[]
 mutations=[('source-position','tail.position[2]=source->position[2];','tail.position[2]=source->position[0];'),('direction','descriptor.direction[2]=source->direction[2];','descriptor.direction[2]=source->direction[0];'),('coefficient','descriptor.extent[1]=D_800A1BDC;','descriptor.extent[1]=1.0f;'),('resource','descriptor.resourceId=47;','descriptor.resourceId=46;'),('flags','descriptor.flags=0x980;','descriptor.flags=0x981;'),('parameter','descriptor.parameter=parameter;','descriptor.parameter=parameter^1;'),('payload','0,180,slot,context);','0,176,slot,context);'),('slot','0,180,slot,context);','0,180,slot^1,context);'),('context','0,180,slot,context);','0,180,slot,context^1);'),('copy-width','&tail,20);','&tail,16);'),('copy-destination','result+0x170','result+0x174'),('tail-zero','tail.zero10=0.0f;','tail.zero10=1.0f;')]
 for name,old,new in mutations:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=2048,profiles=profiles,effective_controls=controls,translation_units=2,descriptor_bytes=124,initialized_descriptor_bytes=116,unspecified_descriptor_bytes=8,trailing_record_bytes=20,source_record_bytes=68,allocation_bytes=548,allocation_and_null_outcomes=True,all256_slot_bytes=True,signed16_parameter_boundaries=True,context32_boundaries=True,source_global_and_passed_packet_mutations=True,full_allocation_and_canaries_checked=True,all_four_rounding_modes_and_provider_sticky_flags=True,descriptor_fields_pinned=len(spans),actual_SDK_memcpy_C_body_executed=True,tail_observed_only_during_target_lifetime=True,strict_aliasing_and_UBSan_trap=True,LTO_type_mismatch_errors=True,no_signal_or_trap_counted=True,profile_comparison_exits={k:v['comparison_exit']for k,v in profiles.items()},control_comparison_exits={v['name']:v['comparison_exit']for v in controls},constants=[hex(v)for v in constants],source_installed=p.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_controls')}),flush=True)
 return q
if __name__=='__main__':main()
