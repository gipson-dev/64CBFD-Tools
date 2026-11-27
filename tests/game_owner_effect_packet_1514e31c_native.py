"""Actual callback C against an independent native32 byte-offset contract."""
from pathlib import Path
from tools.experiments import game_owner_effect_packet_1514e31c_packet as target_packet
import hashlib,json,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import function_span
R=target_packet.ROOT;O=target_packet.OUT
HEADER='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct Opaque225 struct225;
typedef struct { f32 x,y,z; } GameEffectVector;
TYPES
extern f32 D_800A5E18,D_800A5E1C;
u8 *func_15189FF0(u8*,u8*,const void*,u8,u8,u8,u8) __attribute__((noipa));
s32 func_1514EC1C(s32,s32,s16) __attribute__((noipa));
struct225 *func_15160A58(u8*,u8,void*,u8,s16,s32,s32,s32,s32,s32,s32,s8,s32,u8,u8,s32) __attribute__((noipa));
void func_1514E31C(u8*) __attribute__((noipa));
typedef char Layout[sizeof(void*)==4&&sizeof(GameEffectVector)==12&&sizeof(PacketRuntime1514)==32&&sizeof(PacketDescriptor1514)==88&&sizeof(PacketSource1514)==92&&__builtin_offsetof(PacketSource1514,tail)==84&&__builtin_offsetof(PacketRuntime1514,owner)==24?1:-1];
'''
HARNESS=r'''
f32 D_800A5E18,D_800A5E1C;u8 owner[1024];
static u32 bad,ordinal,success,mutationMask,seed,cases;
static u8 *savedD,*savedS,*savedR;static u8 dcopy[88],scopy[92],rcopy[32];
static const u32 patterns[14]={0,0x80000000,1,0x7fffff,0x800000,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc01234,0x7f801234,0xffffffff};
static u32 get(const void*p,u32 n){const u8*b=p;u32 i,v=0;for(i=0;i<n;i++)v|=(u32)b[i]<<(8*i);return v;}
static void put(void*p,u32 v,u32 n){u8*b=p;u32 i;for(i=0;i<n;i++)b[i]=(u8)(v>>(8*i));}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
static void report(u32 a,u32 b,u32 c,u32 d){u32 m[4]={a,b,c,d};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(m),"d"(sizeof(m)):"memory");}
static void check(const u8*p,u32 off,u32 v,u32 n){if(get(p+off,n)!=v)bad|=1;}
static void poison(void){u32 i;
 for(i=0;i<88;i++)savedD[i]=(u8)(i*17+seed*13+ordinal*29+1);
 for(i=0;i<92;i++)savedS[i]=(u8)(i*23+seed*19+ordinal*31+3);
 for(i=0;i<32;i++)savedR[i]=(u8)(i*29+seed*23+ordinal*37+5);
 copy(dcopy,savedD,88);copy(scopy,savedS,92);copy(rcopy,savedR,32);
}
static void mutation(void){if(!(mutationMask&(1u<<ordinal)))return;
 owner[0x3b]^=(u8)(0x55+ordinal);put(&D_800A5E18,get(&D_800A5E18,4)^0x01234567,4);put(&D_800A5E1C,get(&D_800A5E1C,4)^0x089abcde,4);
}
u8 *func_15189FF0(u8*d,u8*s,const void*v,u8 kind,u8 mode,u8 first,u8 variant){u32 i;const u8*r=v;
 if(ordinal||kind!=2||mode!=3||first||variant)bad|=2;
 check(d,0,3,1);check(d,2,0x401,2);check(d,4,0,2);check(d,8,0,4);check(d,12,0,4);check(d,16,0xff00e6ff,4);check(d,64,0x2012,4);check(d,69,255,1);
 for(i=0;i<6;i++)check(d,28+4*i,0,4);
 check(s,0,0x42340000,4);check(s,4,0x425c0000,4);check(s,8,0x41c80000,4);check(s,12,0x42340000,4);
 check(s,16,0x3f000000,4);check(s,20,0x3f000000,4);check(s,24,get(&D_800A5E18,4),4);check(s,28,0,4);check(s,32,get(&D_800A5E1C,4),4);check(s,72,0x3f800000,4);check(s,84,0,4);
 for(i=0;i<6;i++)check(r,4*i,i==2?0x42c80000:i==5?0x44160000:0,4);
 check(r,24,(u32)owner,4);check(r,28,12,1);check(r,29,owner[0x3b],1);check(r,30,2,1);
 savedD=d;savedS=s;savedR=(u8*)v;s[88]=11;
 /* The opaque provider initializes every byte before full representation
    comparisons. No first-call uninitialized padding is inspected. */
 poison();mutation();ordinal++;return success?(u8*)0x50000:0;
}
s32 func_1514EC1C(s32 a,s32 b,s16 key){if(ordinal!=1||(u32)a!=(success?0x50000u:0u)||(u32)b!=(u32)owner||key!=7)bad|=4;
 if(!equal(savedD,dcopy,88)||!equal(savedS,scopy,92)||!equal(savedR,rcopy,32))bad|=8;
 poison();mutation();ordinal++;return (s32)0x81234567;
}
struct225 *func_15160A58(u8*a,u8 b,void*c,u8 d,s16 e,s32 f,s32 g,s32 h,s32 i,s32 j,s32 k,s8 l,s32 m,u8 n,u8 p,s32 q){
 if(ordinal!=2||a!=owner||b!=12||d!=2||e!=300||f!=40||g!=255||h!=181||i||j!=255||k||l!=2||m||n||p!=255||q!=1)bad|=16;
 if(c==savedR||c==savedD||c==savedS||get(c,4)||get((u8*)c+4,4)||get((u8*)c+8,4)!=0x43160000)bad|=32;
 if(!equal(savedD,dcopy,88)||!equal(savedS,scopy,92)||!equal(savedR,rcopy,32))bad|=64;
 ordinal++;return (struct225*)0x76543210;
}
static s32 run(void){u32 id,ok,mut,pat,i,before;
 for(id=0;id<256;id++)for(ok=0;ok<2;ok++)for(mut=0;mut<4;mut++)for(pat=0;pat<14;pat++){
  success=ok;mutationMask=mut;seed=pat;bad=ordinal=0;for(i=0;i<1024;i++)owner[i]=(u8)(i*13+id);owner[0x3b]=(u8)id;
  put(&D_800A5E18,patterns[pat],4);put(&D_800A5E1C,patterns[(pat+7)%14],4);
  before=0x1f80u|((cases&3)<<13)|(cases&32?1u:0u);setCSR(before);func_1514E31C(owner);
  if(bad||ordinal!=3||csr()!=before){report(cases,bad,ordinal,csr()^before);return 42;}cases++;
 }
 report(cases,0,0,0);return 0;
}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
def main():
 target_packet.prepare()
 source=(O/'selected-source.c').read_text();a,z=function_span(source,'func_1514E31C');body=source[a:z];types=source[source.index('typedef struct { f32 v[6]'):source.index('/* Create two owner packets')]
 (O/'native-shared.h').write_text(HEADER.replace('TYPES',types));(O/'native-fixture.c').write_text('#include "native-shared.h"\n'+HARNESS)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,want):
  p=O/(name+'.c');p.write_text('#include "native-shared.h"\n'+text+'\n');exe=p.with_suffix('.exe');c=subprocess.run([*flags,opt,str(p),str(O/'native-fixture.c'),'-o',str(exe)],capture_output=True,text=True);(O/(name+'-compile.txt')).write_text(c.stdout+c.stderr);assert c.returncode==0,(name,c.stderr[-1500:])
  c=subprocess.run([str(exe)],capture_output=True,timeout=60);values=list(struct.unpack('<4I',c.stdout))if len(c.stdout)==16 else c.stdout.hex();row=dict(name=name,opt=opt,exit=c.returncode,diagnostic=values,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert c.returncode==want and len(c.stdout)==16,(row,c.stderr)
  if want==0:assert values==[28672,0,0,0]
  print(json.dumps(row),flush=True);return row
 profiles=[run('native'+opt,body,opt,0)for opt in ('-O0','-O2','-O3')]
 controls={
 'flags':('desc.flags40 = 0x2012','desc.flags40 = 0x2013'),
 'color':('desc.color[1] = 230','desc.color[1] = 229'),
 'size':('source.size[0] = 45.0f','source.size[0] = 44.0f'),
 'coefficient':('source.half18 = D_800A5E18','source.half18 = D_800A5E1C'),
 'factory-mode':('&runtime, 2, 3, 0, 0','&runtime, 2, 0, 0, 0'),
 'runtime-kind':('runtime.kind = 12','runtime.kind = 11'),
 'attach-key':('(s32)owner, 7)','(s32)owner, 6)'),
 'skip-null':('    func_1514EC1C((s32)effect, (s32)owner, 7);','    if (effect) func_1514EC1C((s32)effect, (s32)owner, 7);'),
 'aliased-final-vector':('func_15160A58(owner, 12, &finalVector,','func_15160A58(owner, 12, runtime.v,'),
 'final-z':('finalVector.z = 150.0f','finalVector.z = 149.0f'),
 }
 negatives=[]
 for name,(old,new)in controls.items():
  assert body.count(old)==1,name;text=body.replace(old,new,1)
  if name=='aliased-final-vector':text=text.replace('    GameEffectVector finalVector;\n','').replace('    finalVector.x = 0.0f; finalVector.y = 0.0f; finalVector.z = 150.0f;\n','')
  negatives.append(run('control-'+name,text,'-O2',42))
 q=dict(cases_per_profile=28672,profiles=profiles,effective_controls=negatives,actual_source_sha256=hashlib.sha256(source.encode()).hexdigest(),native32_sizes_match_O32=True,all_256_identities=True,both_NULL_success_results=True,all_14_coefficient_bit_patterns=True,separate_vector_and_live_packet_storage=True,strict_aliasing_UBSan_traps_LTO_types=True,CSR_unchanged=True,no_signal_or_trap_counted_as_control=True,native_incoming_home_mutation_claimed=False,helpers='opaque contract; actual helper execution belongs to guest',source_installed=target_packet.installed(),matching_credit=0)
 (O/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_controls')}),flush=True);return q
if __name__=='__main__':main()
