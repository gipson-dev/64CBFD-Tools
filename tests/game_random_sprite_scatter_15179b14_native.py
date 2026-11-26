"""Actual sprite C, defined-byte provider contract and finite IEEE comparisons."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_random_sprite_scatter_15179b14_match as target_packet
o=target_packet.OUT
def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;a=source.index('/* Scatter bounded random sprite requests');body=source[a:source.index('\n}\n',a)+3];a=source.index('typedef struct {\n    Vtx vertices[8];');types=source[a:source.index('/* Scatter bounded random sprite requests',a)];(o/'candidate-body.c').write_text(body);(o/'candidate-types.h').write_text(types)
 known=set()
 for i in range(8):known.update(range(i*16+6,i*16+16))
 for off,n in((0x80,4),(0x88,2),(0x8A,2),(0x8C,6),(0x92,8),(0x9C,4),(0xA0,3)):known.update(range(off,off+n))
 assert len(known)==109;mask=','.join('1'if i in known else'0'for i in range(168))
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
typedef union{struct{s16 ob[3];u16 flag;s16 tc[2];u8 cn[4];}v;unsigned long long alignment;}Vtx;
'''+types+'''
void func_15179B14(s32);
typedef char Layout[sizeof(void*)==4&&sizeof(Vtx)==16&&sizeof(SelectedVertexSprite)==168&&__builtin_offsetof(SelectedVertexSprite,flags)==152&&__builtin_offsetof(SelectedVertexSprite,textureIndex)==160?1:-1];
typedef struct{u32 pre[4];u8 output[4][184];u32 post[4];}Data;
typedef struct{u32 count,args[32][6],packets,bad_pointer;u8 bytes[4][168];}Observation;
extern Data data;extern Observation observation;extern u32 row,mutation,outcome,width,tall,random_count,height_count,packet_pointer;
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static const u8 known_mask[168]={MASK};
static u32 known(u32 i){return known_mask[i]||((mutation&2)&&i>=0x84&&i<0x88);}
static void effect(u32 stage,u32 n,SelectedVertexSprite*p){if(mutation&1){D_800DD438[0]=(s16)(123+n);D_800DD438[2]=(s16)(-456-(s32)n);D_800A7208=(f32)(37+n);}if((mutation&2)&&stage==2){p->retained84=0xABCDEF00u+n;p->tag=(s8)(0x80+n);}}
__attribute__((noipa))s32 func_150ADA20(void){static const u32 values[]={0,499,500,0xffffffffu,0x80000000u,0x7fffffffu,999,0xfffffc19u};u32 n=++random_count,k=observation.count++;observation.args[k][0]=0x150ADA20;effect(0,n,(void*)0);return(s32)values[(row+n)&7];}
__attribute__((noipa))s32 func_1510F8D8(s32 x,s32 y,s32 z,s32 mode){static const s32 heights[]={-10000,10,16777217,2147483647,(-2147483647-1),0,-9999,500};u32 n=++height_count,k=observation.count++;observation.args[k][0]=0x1510F8D8;observation.args[k][1]=(u32)x;observation.args[k][2]=(u32)y;observation.args[k][3]=(u32)z;observation.args[k][4]=(u32)mode;effect(1,n,(void*)0);return heights[(row+n)&7];}
__attribute__((noipa))void func_1516865C(void*input,u8 red,u8 green,u8 blue,u8 alpha){SelectedVertexSprite*p=input;u32 i,k=observation.count++;s16 lowU=8192,lowV=8192,highU=(s16)((width+256)*32),highV=(s16)((tall+256)*32);static const u8 corner[8][2]={{1,1},{0,1},{0,0},{1,0},{1,1},{0,1},{0,0},{1,0}};if(!packet_pointer)packet_pointer=(u32)p;else if(packet_pointer!=(u32)p)observation.bad_pointer=1;observation.args[k][0]=0x1516865C;observation.args[k][1]=168;observation.args[k][2]=red;observation.args[k][3]=green;observation.args[k][4]=blue;observation.args[k][5]=alpha;if(p->flags&128){s16 t=lowV;lowV=highV;highV=t;}if(p->flags&256){s16 t=lowU;lowU=highU;highU=t;}for(i=0;i<8;i++){p->vertices[i].v.flag=0;p->vertices[i].v.cn[0]=red;p->vertices[i].v.cn[1]=green;p->vertices[i].v.cn[2]=blue;p->vertices[i].v.cn[3]=alpha;p->vertices[i].v.tc[0]=corner[i][0]?highU:lowU;p->vertices[i].v.tc[1]=corner[i][1]?highV:lowV;}p->cleared88=p->cleared9C=p->cleared9E=0;effect(2,observation.packets+1,p);}
__attribute__((noipa))void *func_15168800(void*input,u8 channel,s32 context){SelectedVertexSprite*p=input;u32 i,n=observation.packets++,k=observation.count++;if(packet_pointer!=(u32)p)observation.bad_pointer=1;observation.args[k][0]=0x15168800;observation.args[k][1]=168;observation.args[k][2]=channel;observation.args[k][3]=(u32)context;for(i=0;i<168;i++)if(known(i)){u8 v=((u8*)p)[i];observation.bytes[n][i]=v;if(outcome)data.output[n][16+i]=v;}effect(3,n+1,p);return outcome?data.output[n]:(void*)0;}
'''.replace('MASK',mask);(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Data data;Observation observation;u32 row,mutation,outcome,width,tall,random_count,height_count,packet_pointer;s16 D_800DD438[3];f32 D_800A7208;
typedef struct{Data data;Observation observation;u32 csr,sentinel;s16 origins[3];u16 reserved;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static void reference(s32 count){SelectedVertexSprite sprite;s32 ox=D_800DD438[0],oz=D_800DD438[2],i,x,z,h;volatile f32 sentinel,converted;if(count<=0)return;sentinel=D_800A7208;for(i=0;i<count;i++){x=func_150ADA20()%500+ox;z=func_150ADA20()%500+oz;h=func_1510F8D8(x,10000,z,0);converted=(f32)h;if(converted!=sentinel){sprite.value80=0;sprite.value8A=128;sprite.x=(s16)x;sprite.y=(s16)h;sprite.z=(s16)z;sprite.lifetime=sprite.remaining=25;sprite.initialHeight=0;sprite.tag=14;sprite.textureIndex=18;sprite.flags=0x9804;sprite.mode=0;func_1516865C(&sprite,255,255,255,255);func_15168800(&sprite,255,0);}}}
static s32 count(void){static const s32 n[]={-1,0,1,2,3,0,-2,1};return n[row&7];}
static void fixture(void){u32 i;static const s16 origins[]={-32768,32767,0,-1};static const u32 sentinels[]={0xC61C4000,0,0x4B800000,0x80000000},modes[]={0,3,2,1};for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;D_800DD438[0]=origins[(row>>3)&3];D_800DD438[1]=1234;D_800DD438[2]=origins[(row>>5)&3];D_800A7208=floating(sentinels[(row>>9)&3]);mutation=(row>>7)&3;outcome=(row>>11)&1;width=(row&16)?65535:47;tall=(row&32)?0:31;random_count=height_count=packet_pointer=0;setCSR(0x1f80u|(modes[(row>>2)&3]<<13)|((row&64)?4u:0u));}
static void capture(void){u32 i;current.csr=csr();current.data=data;current.observation=observation;current.sentinel=bits(D_800A7208);for(i=0;i<3;i++)current.origins[i]=D_800DD438[i];}
static s32 fail(void){u32 msg[4]={row,current.observation.count,current.observation.packets,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){fixture();func_15179B14(count());capture();actual=current;fixture();reference(count());capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('signed-modulus','% 500','% 501'),('origin-z','D_800DD438[2]','D_800DD438[1]'),('height-query','x, 10000, z, 0','x, 10001, z, 0'),('sentinel-test','(f32)height != noGround','(f32)height == noGround'),('scale','sprite.value8A = 128','sprite.value8A = 129'),('lifetime','sprite.lifetime = 25','sprite.lifetime = 24'),('alpha','&sprite, 255, 255, 255, 255','&sprite, 255, 255, 255, 254'),('channel','&sprite, 255, 0','&sprite, 254, 0'),('flags','sprite.flags = 0x9804','sprite.flags = 0x9805')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 changed=body.replace('        noGround = D_800A7208;','').replace('            height = func_1510F8D8','            noGround = D_800A7208;\n            height = func_1510F8D8');assert changed!=body;controls.append(dict(name='late-sentinel',**run('control-late-sentinel',changed,'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_C_void_s32_count_and_typed168byte_sprite=True,initialized_bytes_observed=109,initially_unknown59_source_bytes_not_read_before_definition=True,mutated_retained84_is_observed_when_defined=True,guest_compares_all168_bytes_and_native_does_not_claim_unknown_byte_copy=True,captured_origin_and_sentinel_signed_modulo500_and_height_conversion=True,finite_all_four_rounding_modes_existing_flags_and_MXCSR=True,typed_output_arenas_canaries_metadata_calls_and_globals_equal=True,opaque_noipa_defined_byte_provider_contract_not_original_backend=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
