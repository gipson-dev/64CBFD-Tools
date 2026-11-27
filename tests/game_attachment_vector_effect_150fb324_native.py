"""Canonical actor prefix, full matrix allocation and actual typed three-argument C."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_attachment_vector_effect_150fb324_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT
def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;body=source[source.index('extern struct17 D_800A1D30,'):];(o/'candidate-body.c').write_text(body)
 canonical=(o/'baseline/conker/include/structs.h').read_text();actor=canonical.split('struct struct127 {',1)[1].split('    struct255 *unk1D4;',1)[0]
 types='typedef struct struct255{u8 data[0x3C0];}struct255;\ntypedef struct struct129 struct129;\ntypedef struct struct127{'+actor+'    struct255 *unk1D4;\n}struct127;\ntypedef struct{f32 unk0,unk4,unk8;}struct17;\n';(o/'candidate-types.h').write_text(types)
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
'''+types+'''
typedef struct{u32 n,args[3][8],vectors[3][9],csr[3];u8 matrices[3][64];}Observation;
extern struct127 actor,alt;extern struct255 bank,other;extern Observation observation;extern struct17 D_800A1D30,D_800A1D3C,D_800A1D48,D_800A1D54;extern u32 row,mutation,pointBits[9];
void func_15145EA4(struct17**,struct17**,u8*,s32);void func_150FEC28(u8*,u8,struct17*,struct17*,struct17*,u8,s32);void func_151D4408(struct17*,struct17*,void*,u8*,f32,u8,s32);void func_150FB324(struct127*,u8,s32);
typedef char Layout[sizeof(void*)==4&&__builtin_offsetof(struct127,unk1D4)==0x1D4&&sizeof(struct17)==12&&__alignof__(struct17)==4&&sizeof(bank)==0x3C0?1:-1];
static inline u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static inline f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static inline u32 csr(void){u32 x;__asm__ volatile("stmxcsr %0":"=m"(x)::"memory");return x;}
static inline void setCSR(u32 x){__asm__ volatile("ldmxcsr %0"::"m"(x):"memory");}
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static u32 ownerID(u8*p){return p==(u8*)&actor?1:p==(u8*)&alt?2:0;}
static void vector(u32 n,u32 i,struct17*p){observation.vectors[n][i]=bits(p->unk0);observation.vectors[n][i+1]=bits(p->unk4);observation.vectors[n][i+2]=bits(p->unk8);}
static void matrix(u32 n,void*p){u32 i;observation.args[n][7]=p==bank.data+0x380?1:p==other.data+0x380?2:0;for(i=0;i<64;i++)observation.matrices[n][i]=((u8*)p)[i];}
static u32 observe(u32 t){u32 n=observation.n++;observation.args[n][0]=t;observation.csr[n]=csr();return n;}
static void change(void){if(mutation&1){actor.unk1D4=&other;alt.unk1D4=&other;D_800A1D30.unk0=19.f;bank.data[0x380]=0x12;bank.data[0x381]=0x34;bank.data[0x382]=0x56;bank.data[0x383]=0x78;}setCSR((csr()&~63u)|4u);}
__attribute__((noipa))void func_15145EA4(struct17**input,struct17**output,u8*m,s32 count){u32 n=observe(0x15145EA4),i;observation.args[n][1]=(u32)count;matrix(n,m);for(i=0;i<3;i++)vector(n,i*3,input[i]);for(i=0;i<3;i++){output[i]->unk0=floating(pointBits[i*3]);output[i]->unk4=floating(pointBits[i*3+1]);output[i]->unk8=floating(pointBits[i*3+2]);}if(mutation&4)input[0]->unk0=-17.25f;change();}
__attribute__((noipa))void func_150FEC28(u8*owner,u8 kind,struct17*first,struct17*second,struct17*point,u8 selector,s32 context){u32 n=observe(0x150FEC28);observation.args[n][1]=ownerID(owner);observation.args[n][2]=kind;observation.args[n][3]=selector;observation.args[n][4]=(u32)context;vector(n,0,first);vector(n,3,second);vector(n,6,point);if(mutation&4){first->unk4=7.f;second->unk8=8.f;point->unk0=9.f;}change();}
__attribute__((noipa))void func_151D4408(struct17*origin,struct17*direction,void*m,u8*owner,f32 scale,u8 selector,s32 context){u32 n=observe(0x151D4408);observation.args[n][1]=ownerID(owner);observation.args[n][2]=bits(scale);observation.args[n][3]=selector;observation.args[n][4]=(u32)context;vector(n,0,origin);vector(n,3,direction);matrix(n,m);change();}
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
struct127 actor,alt;struct255 bank,other;Observation observation;struct17 D_800A1D30,D_800A1D3C,D_800A1D48,D_800A1D54;u32 row,mutation,pointBits[9];
typedef struct{struct127 actor,alt;struct255 bank,other;Observation observation;struct17 presets[4];u32 csr;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static f32 subtract(f32 a,f32 b){return a-b;}
__attribute__((noinline,noclone))static void reference(u8 selector,s32 context){struct17 presets[4]={D_800A1D30,D_800A1D3C,D_800A1D48,D_800A1D54},out[3];struct17*input[3]={presets,presets+2,presets+3};struct17*output[3]={out,out+1,out+2};if(actor.unk1D4){u8*m=(u8*)actor.unk1D4+0x380;func_15145EA4(input,output,m,3);out[2].unk0=subtract(out[2].unk0,out[1].unk0);out[2].unk4=subtract(out[2].unk4,out[1].unk4);out[2].unk8=subtract(out[2].unk8,out[1].unk8);func_150FEC28((u8*)&actor,14,presets,presets+1,out,selector,context);func_151D4408(out+1,out+2,m,(u8*)&actor,1.f,selector,context);}}
static void fixture(void){u32 i;static const u32 points[4][9]={{0x3f800000u,0xc0000000u,0x40400000u,0x3e800000u,0x3fc00000u,0xbf000000u,0x40e00000u,0xc0800000u,0x3e000000u},{0,0x80000000u,1,0x80000001u,1,0x80000000u,0x80000000u,0,1},{0x60ad78ecu,0x40400000u,0xe0ad78ecu,0x3f800000u,0xe0ad78ecu,0x40400000u,0x60ad78ecu,0x3f800000u,0xe0ad78ecu},{0x7f7fffffu,0,1,0xff7fffffu,0x80000000u,0x80000001u,0x7f7fffffu,0x80000000u,1}};
 for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*19+row);for(i=0;i<sizeof(alt);i++)((u8*)&alt)[i]=(u8)(i*29+row);for(i=0;i<sizeof(bank);i++){bank.data[i]=(u8)(i*17+row);other.data[i]=(u8)(i*13+row);}actor.unk1D4=(row&1)?&bank:NULL;alt.unk1D4=actor.unk1D4;for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;D_800A1D30=(struct17){-108.f,-9.f,85.f};D_800A1D3C=(struct17){-150.f,-9.f,111.f};D_800A1D48=(struct17){-32.f,4.f,40.f};D_800A1D54=(struct17){-21.f,15.f,40.f};for(i=0;i<9;i++)pointBits[i]=points[(row>>3)&3][i];mutation=((row>>1)&1)|(((row>>2)&1)<<2);setCSR(0x1f80u|(((row>>5)&3)<<13)|4u);}
static void capture(void){current.actor=actor;current.alt=alt;current.bank=bank;current.other=other;current.observation=observation;current.presets[0]=D_800A1D30;current.presets[1]=D_800A1D3C;current.presets[2]=D_800A1D48;current.presets[3]=D_800A1D54;current.csr=csr();}
static s32 fail(void){u32 msg[4]={row,current.observation.n,actual.observation.n,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){static const u32 selectors[4]={0,1,255,0x87654380u},contexts[4]={0,1,0xffffffffu,0x80000000u};for(row=0;row<2048;row++){u8 s=(u8)selectors[(row>>7)&3];s32 c=(s32)contexts[(row>>9)&3];fixture();func_150FB324(&actor,s,c);capture();actual=current;fixture();reference(s,c);capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  p=o/(name+'.c');p.write_text('#include "native-shared.h"\n'+text);exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(p),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);v=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,v);return v
 profiles=[run('native-'+p,body,'-'+p,0)for p in('O0','O2','O3')];controls=[]
 for name,old,new in [('gate','owner->unk1D4 != NULL','owner->unk1D4 != NULL && selector != 255'),('matrix-bias','+ 0x380','+ 0x340'),('first-input','input[0] = &first','input[0] = &second'),('second-input','input[1] = &third','input[1] = &first'),('third-input','input[2] = &fourth','input[2] = &second'),('point-output','output[0] = &point;\n        output[1] = &origin','output[0] = &origin;\n        output[1] = &point'),('subtract-X','direction.unk0 -= origin.unk0','direction.unk0 += origin.unk0'),('subtract-Y','direction.unk4 -= origin.unk4','direction.unk4 -= origin.unk8'),('effect-id',', 14, &first',', 15, &first'),('selector',', selector, context',', selector ^ 1, context'),('context',', selector, context',', selector, context ^ 1'),('scale','1.0f, selector','2.0f, selector')]:
  assert old in body,name;changed=body.replace(old,new)
  if name=='second-input':changed=changed.replace('    struct17 third = D_800A1D48;\n','')
  if name=='third-input':changed=changed.replace('    struct17 fourth = D_800A1D54;\n','')
  controls.append(dict(name=name,**run('control-'+name,changed,'-O2',42)))
 q=dict(cases_per_profile=2048,profiles=profiles,translation_units=3,canonical_actor_prefix_copied_from_frozen_header=True,actor_attachment_offset=0x1D4,matrix_fixture_allocation_bytes=0x3C0,matrix_offset=0x380,matrix_access_bytes=64,actual_C_void_three_argument_ABI=True,full_initialized_actors_banks_presets_calls_vector_packets_and_MXCSR_compared=True,all_four_rounding_modes_including_subnormals_overflow_and_signed_zero=True,private_home_mutations_only_guest=True,backends_opaque=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='effective_controls'}),flush=True);return q
if __name__=='__main__':main()
