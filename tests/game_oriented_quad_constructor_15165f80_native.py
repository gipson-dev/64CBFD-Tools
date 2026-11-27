"""Actual nine-argument C with typed halfword storage and independent reference."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_oriented_quad_constructor_15165f80_match as target_packet
o=target_packet.OUT

def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;a=source.index('/* Initialize a flat or angle-oriented');body=source[a:source.index('\n}\n',a)+3];(o/'candidate-body.c').write_text(body)
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
void *func_15167A68(s32,s32,s32,s32,u8,u8);void func_1517E05C(s32,s32,s32);f32 sinf(f32);f32 cosf(f32);void func_15165F80(s32,s32,s32,s32,s32,s32,s32,u8,s32);
typedef struct{u32 pre[4];s16 words[84];u32 post[4];}Storage;
typedef struct{u32 n,args[4][7],csr[4];u8 packets[4][168];}Observation;
extern Storage storage;extern Observation observation;extern f32 D_800A6C94;extern u16 origin[3];extern u32 row,mutation,sineBits,cosineBits;
typedef char Layout[sizeof(void*)==4&&sizeof(Storage)==200&&sizeof(storage.words)==168&&__builtin_offsetof(Storage,words)==16&&__alignof__(s16)==2?1:-1];
static inline u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static inline f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static inline u32 csr(void){u32 x;__asm__ volatile("stmxcsr %0":"=m"(x)::"memory");return x;}
static inline void setCSR(u32 x){__asm__ volatile("ldmxcsr %0"::"m"(x):"memory");}
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static u32 observe(u32 t){u32 n=observation.n++,i;observation.args[n][0]=t;observation.csr[n]=csr();for(i=0;i<168;i++)observation.packets[n][i]=((u8*)storage.words)[i];return n;}
static void change(void){if(mutation&1){D_800A6C94=.5f;((u8*)storage.words)[0x94]=0xE1;}if(mutation&2){((u8*)storage.words)[0x91]=0xCC;((u8*)storage.words)[0x90]=0xDD;}setCSR((csr()&~63u)|4u);}
__attribute__((noipa))void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){u32 n=observe(0x15167A68);observation.args[n][1]=(u32)a;observation.args[n][2]=(u32)b;observation.args[n][3]=(u32)c;observation.args[n][4]=(u32)d;observation.args[n][5]=e;observation.args[n][6]=f;change();return(row&1)?storage.words:NULL;}
__attribute__((noipa))f32 sinf(f32 x){u32 n=observe(0x15047D60);observation.args[n][1]=bits(x);change();return floating(sineBits);}
__attribute__((noipa))f32 cosf(f32 x){u32 n=observe(0x15047C00);observation.args[n][1]=bits(x);change();return floating(cosineBits);}
__attribute__((noipa))void func_1517E05C(s32 x,s32 y,s32 z){u32 n=observe(0x1517E05C);observation.args[n][1]=(u32)x;observation.args[n][2]=(u32)y;observation.args[n][3]=(u32)z;origin[0]=(u16)x;origin[1]=(u16)y;origin[2]=(u16)z;}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Storage storage;Observation observation;f32 D_800A6C94;u16 origin[3];u32 row,mutation,sineBits,cosineBits;
typedef struct{Storage storage;Observation observation;u16 origin[3],pad;u32 coefficient,csr;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static f32 convert(s32 x){return(f32)x;}
__attribute__((noinline,noclone))static f32 mul(f32 a,f32 b){return a*b;}
__attribute__((noinline,noclone))static s32 truncated(f32 x){return(s32)x;}
__attribute__((noinline,noclone))static void reference(s32 angle,s32 x,s32 y,s32 z,s32 step,s32 lifetime,s32 mode,u8 selector,s32 category){u8*p=func_15167A68(4,category,168,1,selector,1);u32 block,i;if(p){if(angle==-1){for(block=0;block<2;block++){for(i=0;i<4;i++)*(s16*)(p+0x12+block*64+i*16)=(s16)y;for(i=0;i<4;i++)*(s16*)(p+0x16+block*64+i*16)=0;}p[0x95]=0;}else{f32 radians=mul(convert(angle),D_800A6C94),s=sinf(radians);p[0x91]=(u8)truncated(mul(s,127.f));f32 c=cosf(radians);p[0x95]=1;p[0x90]=(u8)truncated(mul(floating(bits(c)^0x80000000u),127.f));}for(block=0;block<2;block++){static const u32 offsets[8]={0x18,0x1A,0x28,0x2A,0x38,0x3A,0x48,0x4A},values[8]={0x2000,0x2000,0x2800,0x2000,0x2800,0x2800,0x2000,0x2800};for(i=0;i<8;i++)*(s16*)(p+block*64+offsets[i])=(s16)values[i];}*(s16*)(p+0x9A)=(s16)y;*(s16*)(p+0x9E)=1;p[0x92]=(u8)lifetime;p[0x93]=(u8)lifetime;*(s16*)(p+0x98)=(s16)x;*(s16*)(p+0x9C)=(s16)z;*(s16*)(p+0x96)=(s16)step;p[0x94]=(u8)mode;func_1517E05C(x,y,z);}}
static void fixture(void){u32 i;static const u32 finite[]={0,0x80000000u,1,0x80000001u,0x3eaaaaabu,0xbf471c72u,0x3f7fffffu,0xbf800000u};for(i=0;i<sizeof(storage);i++)((u8*)&storage)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;origin[0]=0x1234;origin[1]=0x5678;origin[2]=0x9abc;D_800A6C94=floating(0x3c8efa35u);mutation=(row>>3)&3;sineBits=finite[(row>>1)&7];cosineBits=finite[((row>>4)+3)&7];setCSR(0x1f80u|(((row>>5)&3)<<13)|4u);}
static void capture(void){u32 i;current.storage=storage;current.observation=observation;for(i=0;i<3;i++)current.origin[i]=origin[i];current.coefficient=bits(D_800A6C94);current.csr=csr();}
static s32 fail(void){u32 msg[4]={row,current.observation.n,actual.observation.n,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){static const u32 angles[]={0xffffffffu,0,1,0x1000001u,0x7fffffffu,0x80000000u},values[]={0,1,0xffffffffu,0x80000000u,0x7fffffffu,0x87654321u,0xfedcba98u,0x12340081u};for(row=0;row<4096;row++){s32 a=(s32)angles[(row>>1)%6],x=(s32)values[(row>>2)&7],y=(s32)values[(row>>4)&7],z=(s32)values[(row>>6)&7],step=(s32)values[(row>>7)&7],life=(s32)values[(row>>8)&7],mode=(s32)values[(row>>9)&7],category=(s32)values[(row>>5)&7];u8 selector=(u8)values[(row>>3)&7];fixture();func_15165F80(a,x,y,z,step,life,mode,selector,category);capture();actual=current;fixture();reference(a,x,y,z,step,life,mode,selector,category);capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text);exe=o/(name+'.exe');p=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=30);q=dict(profile=opt,comparison_exit=p.returncode,diagnostic=list(struct.unpack('<4I',p.stdout))if len(p.stdout)==16 else p.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert p.returncode==expected,(name,q);return q
 profiles=[run('native-'+p,body,'-'+p,0)for p in('O0','O2','O3')];controls=[]
 for name,old,new in [('gate','created != NULL','created != NULL && selector != 255'),('angle-gate','angle == -1','angle == -2'),('signed-angle','angle * D_800A6C94','(u32)angle * D_800A6C94'),('angle-scale','angle * D_800A6C94','angle * -D_800A6C94'),('sine-scale','sinf(radians) * 127.0f','sinf(radians) * 126.0f'),('cosine-sign','-cosf(radians)','cosf(radians)'),('flat-y','(vertices - 0x2E) = y','(vertices - 0x2E) = y ^ 1'),('UV','0x2000','0x2001'),('selector','0xA8, 1, selector, 1','0xA8, 1, selector ^ 1, 1'),('category','(4, category, 0xA8','(4, category ^ 1, 0xA8'),('lifetime','created[0x92] = lifetime','created[0x92] = lifetime ^ 1'),('origin','func_1517E05C(x, y, z)','func_1517E05C(x, y ^ 1, z)')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_nine_argument_C_void_entry=True,typed_84_halfword_allocation_with_character_access=True,full_initialized_storage_canaries_calls_packets_coefficient_origin_and_MXCSR_compared=True,all_four_rounding_modes_signed_conversion_finite_trig_and_truncation=True,private_home_mutations_only_guest=True,providers_are_opaque_counterparts=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='effective_controls'}),flush=True);return q
if __name__=='__main__':main()
