"""Actual canonical actor prefix, 14-argument C ABI and defined typed inputs."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_attached_random_emitter_150e06d8_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT

def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;a=source.index('#define ATTACHED_RANDOM_RANGE');body=source[a:];(o/'candidate-body.c').write_text(body)
 canonical=(o/'baseline/conker/include/structs.h').read_text();actor=canonical.split('struct struct127 {',1)[1].split('    struct255 *unk1D4;',1)[0];types='typedef struct struct255 {u8 pad0[0x240];void *unk240;} struct255;\ntypedef struct struct129 struct129;\ntypedef struct struct127 {'+actor+'    struct255 *unk1D4;\n} struct127;\ntypedef struct {f32 x,y,z;} struct17;\n';(o/'candidate-types.h').write_text(types)
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
'''+types+'''
extern struct17 D_800A0F70[2],D_800A0F88[2];extern u8 D_80088988;
void func_15145EA4(struct17**,struct17**,u8*,s32);s32 func_150ADA20(void);f32 func_150ADA68(void);
void *func_15102B38(struct127*,u8,struct17*,struct17*,f32*,s16,u8,f32,struct17*,u8,s32,s16,u8,s32);
void func_150E06D8(struct127*,u8,u8,s32);
typedef struct {u32 n,args[7][14],csr[7],packet[13],ints[2],floats[3];} Observation;
extern Observation observation;extern struct127 actor;extern struct255 bank,otherBank;extern u32 row,mutation,drawI,drawF;
typedef char Layout[sizeof(void*)==4&&sizeof(struct17)==12&&__builtin_offsetof(struct127,unique_id)==0x3B&&__builtin_offsetof(struct127,unk1D4)==0x1D4&&sizeof(struct255)>=576?1:-1];
static inline u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static inline f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static inline u32 csr(void){u32 x;__asm__ volatile("stmxcsr %0":"=m"(x)::"memory");return x;}
static inline void setCSR(u32 x){__asm__ volatile("ldmxcsr %0"::"m"(x):"memory");}
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static u32 observe(u32 t){u32 n=observation.n++;observation.args[n][0]=t;observation.csr[n]=csr();return n;}
static void change(void){if(mutation&1){D_80088988=(D_80088988+1)&3;D_800A0F70[0].x=19.f;actor.unk1D4=&otherBank;}setCSR((csr()&~63u)|4u);}
__attribute__((noipa))void func_15145EA4(struct17**in,struct17**out,u8*matrix,s32 count){u32 n=observe(0x15145EA4);observation.args[n][1]=(u32)*in;observation.args[n][2]=(u32)matrix;observation.args[n][3]=(u32)count;(*out)->x=17.25f;(*out)->y=-2.5f;(*out)->z=31.f;if(mutation&2){*in=&D_800A0F88[0];*out=&D_800A0F88[1];}change();}
__attribute__((noipa))s32 func_150ADA20(void){observe(0x150ADA20);u32 value=observation.ints[drawI++];change();return(s32)value;}
__attribute__((noipa))f32 func_150ADA68(void){observe(0x150ADA68);u32 value=observation.floats[drawF++];change();return floating(value);}
__attribute__((noipa))void *func_15102B38(struct127*a,u8 b,struct17*c,struct17*d,f32*e,s16 f,u8 g,f32 h,struct17*i,u8 j,s32 k,s16 l,u8 m,s32 z){u32 n=observe(0x15102B38),q;u32 args[13]={(u32)a,b,(u32)c,(u32)d,0xEEEE0004u,(u32)(s32)f,g,bits(h),0xEEEE0008u,j,(u32)k,(u32)(s32)l,m};for(q=0;q<13;q++)observation.args[n][q+1]=args[q];observation.packet[0]=(u32)z;observation.packet[1]=bits(e[0]);observation.packet[2]=bits(e[1]);observation.packet[3]=bits(i->x);observation.packet[4]=bits(i->y);observation.packet[5]=bits(i->z);observation.packet[6]=bits(c->x);observation.packet[7]=bits(c->y);observation.packet[8]=bits(c->z);observation.packet[9]=bits(d->x);observation.packet[10]=bits(d->y);observation.packet[11]=bits(d->z);observation.packet[12]=a->unique_id;change();return(void*)0xDEADBEEFu;}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Observation observation;struct127 actor;struct255 bank,otherBank;u8 D_80088988;struct17 D_800A0F70[2],D_800A0F88[2];u32 row,mutation,drawI,drawF;
typedef struct{Observation observation;struct127 actor;struct255 bank,other;struct17 a[2],b[2];u32 player,csr;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static f32 mul(f32 a,f32 b){return a*b;}
__attribute__((noinline,noclone))static f32 add(f32 a,f32 b){return a+b;}
__attribute__((noinline,noclone))static void reference(u8 v,u8 selector,s32 context){if(actor.unk1D4){struct17 p,*in=&D_800A0F70[v],*out=&p;f32 parameters[2],x;u32 a,b;func_15145EA4(&in,&out,(u8*)actor.unk1D4+64*D_80088988,1);x=func_150ADA68();parameters[1]=add(mul(x,1.f),2.f);x=func_150ADA68();parameters[0]=add(mul(x,14.f),28.f);a=(u32)func_150ADA20();b=(u32)func_150ADA20();x=func_150ADA68();func_15102B38(&actor,D_80088988,&D_800A0F70[v],&D_800A0F88[v],parameters,a%3+4,b%156+100,add(mul(x,300.f),400.f),&p,255,0,-1,selector,context);}}
static void fixture(void){u32 i;static const u32 ints[]={0,0xffffffffu,0x80000000u,0x7fffffffu,155,156};static const u32 floats[]={0,0x80000000u,0x3eaaaaabu,0x3f7fffffu,0xbf000001u,1,0x00800000u,0x3f800001u};for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*19+row);for(i=0;i<sizeof(bank);i++)((u8*)&bank)[i]=(u8)(i*13+row);for(i=0;i<sizeof(otherBank);i++)((u8*)&otherBank)[i]=(u8)(i*11+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;actor.unk1D4=(row&1)?&bank:NULL;actor.unique_id=77;D_80088988=(row>>5)&3;for(i=0;i<2;i++){D_800A0F70[i].x=i?-17.f:17.f;D_800A0F70[i].y=0;D_800A0F70[i].z=90.f;D_800A0F88[i].x=D_800A0F70[i].x;D_800A0F88[i].y=0;D_800A0F88[i].z=150.f;observation.ints[i]=ints[(row+i)%6];}for(i=0;i<3;i++)observation.floats[i]=floats[((row>>2)+i)%8];mutation=(row>>3)&3;drawI=drawF=0;setCSR(0x1f80u|(((row>>7)&3)<<13)|4u);}
static void capture(void){u32 i;current.observation=observation;current.actor=actor;current.bank=bank;current.other=otherBank;for(i=0;i<2;i++){current.a[i]=D_800A0F70[i];current.b[i]=D_800A0F88[i];}current.player=D_80088988;current.csr=csr();}
static s32 fail(void){u32 msg[4]={row,current.observation.n,actual.observation.n,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){static const u32 selectors[]={0,1,255,0x87654380u},contexts[]={0,1,0xffffffffu,0x80000000u};for(row=0;row<4096;row++){u8 v=(row>>1)&1,s=(u8)selectors[(row>>9)&3];s32 c=(s32)contexts[(row>>10)&3];fixture();func_150E06D8(&actor,v,s,c);capture();actual=current;fixture();reference(v,s,c);capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text);exe=o/(name+'.exe');p=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr);p=subprocess.run([str(exe)],capture_output=True,timeout=30);q=dict(profile=opt,comparison_exit=p.returncode,diagnostic=list(struct.unpack('<4I',p.stdout))if len(p.stdout)==16 else p.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert p.returncode==expected,(name,q);return q
 profiles=[run('native-'+p,body,'-'+p,0)for p in('O0','O2','O3')];controls=[]
 for name,old,new in [('gate','owner->unk1D4 != NULL','owner->unk1D4 != NULL && selector != 255'),('first-range','2.0f, 3.0f','3.0f, 4.0f'),('second-range','28.0f, 42.0f','28.0f, 41.0f'),('signed-rem','u32 first, second','s32 first, second'),('first-mod','first % 3 + 4','first % 2 + 4'),('second-mod','second % 156 + 100','second % 155 + 100'),('size','400.0f, 700.0f','400.0f, 701.0f'),('selector','-1, selector, context','-1, selector ^ 1, context'),('context','-1, selector, context','-1, selector, context ^ 1'),('point','&point, 255','input, 255'),('pair-order','currentVariant = variant;','currentVariant = variant; { f32 t = parameters[0]; parameters[0] = parameters[1]; parameters[1] = t; }')]:
  assert old in body,name;changed=body.replace(old,new);controls.append(dict(name=name,**run('control-'+name,changed,'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,canonical_actor_prefix_copied_from_frozen_header=True,actor_attachment_offset=468,void_four_word_entry_and_inferred_14arg_provider_contract=True,variant_limited_to_pinned_two_entries=True,full_initialized_actor_banks_tables_calls_defined_packets_and_MXCSR_compared=True,private_home_mutations_only_guest=True,backends_opaque=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='effective_controls'}),flush=True);return q
if __name__=='__main__':main()
