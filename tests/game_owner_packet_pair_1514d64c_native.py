"""Actual private callback C against an independent byte-offset packet contract.

This is source/ABI qualification only. No production source is installed and
no function is credited by this script.
"""
from pathlib import Path
from tools.experiments import game_owner_packet_pair_1514d64c_packet as target_packet
import hashlib,json,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import function_span
R=target_packet.ROOT;O=target_packet.OUT
HEADER=r'''
typedef unsigned char u8;typedef signed char s8;
typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct Opaque225 struct225;
TYPES
u8 *func_15189FF0(u8*,u8*,const void*,u8,u8,u8,u8) __attribute__((noipa));
s32 func_1514EC1C(s32,s32,s16) __attribute__((noipa));
struct225 *func_15160A58(u8*,u8,void*,u8,s16,s32,s32,s32,s32,s32,s32,s8,s32,u8,u8,s32) __attribute__((noipa));
void func_1514D64C(u8*) __attribute__((noipa));
typedef char Check[sizeof(void*)==4 && sizeof(PacketRuntime1514)==32 &&
 sizeof(PacketDescriptor1514)==88 && sizeof(PacketSource1514)==92 &&
 __builtin_offsetof(PacketSource1514,tail)==84 &&
 __builtin_offsetof(PacketRuntime1514,owner)==24 ? 1:-1];
'''
HARNESS=r'''
f32 D_800A5DF4,D_800A5DF8,D_800A5DFC,D_800A5E00;
u8 owner[1024];u32 bad,ordinal,identity,outcomes,mutations,seed,cases;
u8 *savedD,*savedS,*savedR;u8 previousD[88],previousS[92],previousR[32];
static const u32 patterns[14]={0,0x80000000,1,0x7fffff,0x800000,0x3f800000,
 0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc01234,0x7f801234,0xffffffff};
static u32 get(const void*p,u32 n){const u8*b=p;u32 i,v=0;for(i=0;i<n;i++)v|=(u32)b[i]<<(8*i);return v;}
static void put(void*p,u32 v,u32 n){u8*b=p;u32 i;for(i=0;i<n;i++)b[i]=(u8)(v>>(8*i));}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
static void report(u32 a,u32 b,u32 c,u32 d){u32 msg[4]={a,b,c,d};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");}
static void expect(const u8*p,u32 off,u32 v,u32 n,u8*mask){u32 i;
 if(get(p+off,n)!=v)bad|=1;
 for(i=0;i<n;i++)mask[off+i]=1;
}
static void descriptor(const u8*d,u8*mask){u32 i;
 expect(d,0,3,1,mask);expect(d,2,0x401,2,mask);expect(d,4,0,2,mask);
 expect(d,8,0,4,mask);expect(d,12,0,4,mask);expect(d,0x10,0xff0000ff,4,mask);
 expect(d,0x40,0x12012,4,mask);expect(d,0x45,255,1,mask);
 for(i=0;i<6;i++)expect(d,0x1c+4*i,0,4,mask);
}
static void source(const u8*s,u32 phase,u8*mask){u32 i;
 static const u32 dims[2][4]={{0x41e00000,0x41e00000,0x40800000,0x41880000},
 {0x41f00000,0x41f00000,0x41200000,0x41800000}};
 for(i=0;i<4;i++)expect(s,4*i,dims[phase][i],4,mask);
 expect(s,0x10,phase?get(&D_800A5DF8,4):0x3f000000,4,mask);
 expect(s,0x14,phase?get(&D_800A5DF8,4):0x3f000000,4,mask);
 expect(s,0x18,phase?get(&D_800A5DFC,4):0x3f400000,4,mask);
 expect(s,0x1c,phase?get(&D_800A5DFC,4):0x3e800000,4,mask);
 expect(s,0x20,get(phase?&D_800A5E00:&D_800A5DF4,4),4,mask);
 expect(s,0x48,0x3f800000,4,mask);expect(s,0x54,0,4,mask);
}
static void runtime(const u8*r,u32 phase,u8*mask){u32 i;
 static const u32 vectors[2][6]={{0,0,0x41c80000,0,0,0x42960000},
 {0,0x41200000,0xc28c0000,0,0x41a00000,0xc30c0000}};
 for(i=0;i<6;i++)expect(r,i*4,vectors[phase][i],4,mask);
 expect(r,24,(u32)owner,4,mask);expect(r,28,phase?5:43,1,mask);
 expect(r,29,owner[0x3b],1,mask);expect(r,30,phase?0:1,1,mask);
}
static void mutation(u32 stage){u32 i;
 if(!(mutations&(1u<<stage)))return;
 owner[0x3b]^=(u8)(0x31+stage*17);
 put(&D_800A5DF8,get(&D_800A5DF8,4)^0x01234567,4);
 put(&D_800A5DFC,get(&D_800A5DFC,4)^0x089abcde,4);
 put(&D_800A5E00,get(&D_800A5E00,4)^0x06543210,4);
 for(i=0;i<88;i++)savedD[i]=(u8)(i*17+stage*37+seed+1);
 for(i=0;i<92;i++)savedS[i]=(u8)(i*29+stage*41+seed+3);
 for(i=0;i<32;i++)savedR[i]=(u8)(i*31+stage*43+seed+5);
}
static void remember(void){copy(previousD,savedD,88);copy(previousS,savedS,92);copy(previousR,savedR,32);}
u8 *func_15189FF0(u8*d,u8*s,const void*v,u8 kind,u8 mode,u8 first,u8 variant){
 u8 dm[88]={0},sm[92]={0},rm[32]={0};u8*r=(u8*)v;u32 i,phase=ordinal==2;
 if((ordinal!=0&&ordinal!=2)||kind!=2||mode||first||variant)bad|=2;
 if(phase&&(d!=savedD||s!=savedS||r!=savedR))bad|=4;
 descriptor(d,dm);source(s,phase,sm);runtime(r,phase,rm);
 if(phase){
  for(i=0;i<88;i++)if(!dm[i]&&d[i]!=previousD[i])bad|=8;
  for(i=0;i<92;i++)if(!sm[i]&&s[i]!=previousS[i])bad|=16;
  for(i=0;i<32;i++)if(!rm[i]&&r[i]!=previousR[i])bad|=32;
 }
 savedD=d;savedS=s;savedR=r;
 /* The qualified actual 41-word helper writes this byte before the factory. */
 s[0x58]=0x0b;mutation(ordinal);remember();ordinal++;
 return (u8*)((outcomes&(phase?2:1))?(phase?0x60000:0x50000):0);
}
s32 func_1514EC1C(s32 object,s32 address,s16 key){u32 phase=ordinal==3;
 u32 answer=(outcomes&(phase?2:1))?(phase?0x60000:0x50000):0;
 if((ordinal!=1&&ordinal!=3)||(u32)object!=answer||(u32)address!=(u32)owner||key!=(phase?10:9))bad|=64;
 mutation(ordinal);remember();ordinal++;return (s32)(0x80000000u|ordinal);
}
struct225 *func_15160A58(u8*a,u8 b,void*c,u8 d,s16 e,s32 f,s32 g,s32 h,s32 i,s32 j,s32 k,s8 l,s32 m,u8 n,u8 p,s32 q){
 const u8*v=c;
 if(ordinal!=4||a!=owner||b!=5||c!=savedR||d!=2||e!=300||f!=40||g!=255||h||i||j!=255||k||l!=1||m||n||p!=255||q!=1)bad|=128;
 if(get(v,4)!=get(previousR,4)||get(v+4,4)!=get(previousR+4,4)||get(v+8,4)!=get(previousR+8,4))bad|=256;
 ordinal++;return (struct225*)0x76543210;
}
static s32 run(void){u32 id,answers,mut,pat,before,i;
 for(id=0;id<256;id++)for(answers=0;answers<4;answers++)for(mut=0;mut<16;mut++)for(pat=0;pat<14;pat++){
  identity=id;outcomes=answers;mutations=mut;seed=pat;bad=ordinal=0;
  savedD=savedS=savedR=0;
  for(i=0;i<sizeof(owner);i++)owner[i]=(u8)(i*13+id);
  owner[0x3b]=(u8)id;
  put(&D_800A5DF4,patterns[pat],4);put(&D_800A5DF8,patterns[(pat+3)%14],4);
  put(&D_800A5DFC,patterns[(pat+7)%14],4);put(&D_800A5E00,patterns[(pat+11)%14],4);
  before=0x1f80u|((cases&3)<<13)|(cases&0x20?1u:0u);setCSR(before);
  func_1514D64C(owner);
  if(bad||ordinal!=5||csr()!=before){report(cases,bad,ordinal,csr()^before);return 42;}
  cases++;
 }
 report(cases,0,0,0);return 0;
}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
def main():
 target_packet.prepare()
 s=target_packet.MANIFEST['selected_source'];a,z=function_span(s,'func_1514D64C');body=s[a:z]
 types=s[s.index('typedef struct { f32 v[6]'):s.index('/* Create two owner packets')]
 header=HEADER.replace('TYPES',types);(O/'packet-native.h').write_text(header)
 # Helpers and target are separate translation units; noipa survives LTO.
 (O/'packet-native-fixture.c').write_text('#include "packet-native.h"\n'+HARNESS)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,want):
  src=O/('packet-native-'+name+'.c');src.write_text('#include "packet-native.h"\n'+text+'\n');exe=src.with_suffix('.exe')
  p=subprocess.run([*flags,opt,str(src),str(O/'packet-native-fixture.c'),'-o',str(exe)],capture_output=True,text=True)
  (O/(name+'-native-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr[-1500:])
  p=subprocess.run([str(exe)],capture_output=True,timeout=60)
  values=list(struct.unpack('<4I',p.stdout)) if len(p.stdout)==16 else p.stdout.hex()
  row=dict(name=name,opt=opt,exit=p.returncode,diagnostic=values,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
  assert p.returncode==want and len(p.stdout)==16,(row,p.stderr)
  if want==0:assert values==[229376,0,0,0],row
  print(json.dumps(row),flush=True);return row
 rows=[]
 for opt in ['-O0','-O2','-O3']:rows.append(run('actual'+opt,body,opt,0))
 controls={
  'wrong-width':body.replace('value = 28.0f','value = 29.0f',1),
  'wrong-flags':body.replace('desc.flags40 = 0x12012','desc.flags40 = 0x12013',1),
  'stale-identity':body.replace('    u8 *effect;','    u8 *effect;\n    u8 who = owner[0x3B];').replace('runtime.identity = owner[0x3B]','runtime.identity = who'),
  'stale-coefficient':body.replace('    u8 *effect;','    u8 *effect;\n    f32 coefficient = D_800A5DF8;').replace('source.zero10 = D_800A5DF8','source.zero10 = coefficient').replace('source.zero14 = D_800A5DF8','source.zero14 = coefficient'),
  'wrong-key':body.replace('(s32)owner, 10)','(s32)owner, 9)',1),
  'skip-null':body.replace('    func_1514EC1C((s32)effect, (s32)owner, 10);','    if (effect) func_1514EC1C((s32)effect, (s32)owner, 10);'),
  'clear-unwritten':body.replace('    func_1514EC1C((s32)effect, (s32)owner, 9);','    func_1514EC1C((s32)effect, (s32)owner, 9);\n    source.pad24[0] = 0;'),
  'wrong-final-vector':body.replace('func_15160A58(owner, 5, runtime.v,','func_15160A58(owner, 5, runtime.v + 1,'),
 }
 for name,text in controls.items():
  assert text!=body,name;rows.append(run(name,text,'-O2',42))
 report=dict(actual_source_sha256=hashlib.sha256(s.encode()).hexdigest(),cases_per_profile=229376,profiles=rows[:3],effective_controls=rows[3:],native32_pointer_and_field_sizes_match_O32=True,strict_aliasing_UBSan_traps_LTO_types=True,all_256_identities=True,both_null_success_results=True,all_16_helper_mutation_masks=True,all_14_FP_bit_patterns=True,CSR_unchanged=True,unwritten_bytes_checked_only_after_defined_provider_poison=True,source_extent=92,helper_subtype_byte=88,helpers='opaque contract; actual 41-word helper not executed here',source_installed=target_packet.installed(),matching_credit=0)
 (O/'native-packet.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('profiles','effective_controls')}),flush=True)
 return report
if __name__=='__main__':main()
