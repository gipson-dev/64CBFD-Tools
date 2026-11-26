"""Actual C, typed camera/slot arenas and defined descriptor bytes only."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_display_sprite_slot_15179600_match as target_packet
o=target_packet.OUT
def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;a=source.index('/* Create a display sprite near the camera');body=source[a:source.index('\n}\n',a)+3];a=source.index('typedef struct {\n    Vtx vertices[8];');types=source[a:source.index('/* Create a display sprite near the camera',a)];(o/'candidate-body.c').write_text(body);(o/'candidate-types.h').write_text(types)
 known=set()
 for i in range(8):known.update(range(i*16+6,i*16+16))
 for off,n in((0x80,6),(0x88,4),(0x8C,6),(0x92,4),(0x98,2),(0x9C,4),(0xA0,3)):known.update(range(off,off+n))
 assert len(known)==109;mask=','.join('1'if i in known else'0'for i in range(168))
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
typedef union{struct{s16 ob[3];u16 flag;s16 tc[2];u8 cn[4];}v;unsigned long long alignment;}Vtx;
typedef struct{u8 retained[0x2F8];f32 unk2F8,unk2FC,unk300;}struct108;
extern u8 *D_800DBFF0;extern s16 D_800DD436;extern u8 **D_800DD440;
'''+types+'''
void func_15179600(s32,u32);
typedef char Layout[sizeof(void*)==4&&sizeof(Vtx)==16&&sizeof(DisplaySprite15179600)==168&&__builtin_offsetof(DisplaySprite15179600,slotIndex)==132&&__builtin_offsetof(DisplaySprite15179600,flags)==152&&__builtin_offsetof(struct108,unk2F8)==760&&__builtin_offsetof(struct108,unk2FC)==764&&__builtin_offsetof(struct108,unk300)==768?1:-1];
typedef struct{u32 pre[4];struct108 camera[2];u8 output[184];u32 post[4];}Data;
typedef struct{u32 pre[4];u8 *entry[2][304];u32 post[4];}SlotTables;
typedef struct{u32 count,args[8][6],packets,bad_pointer,input[4];u8 bytes[168];}Observation;
extern Data data;extern SlotTables tables;extern Observation observation;extern u32 row,mutation,outcome,width,tall,random_count,packet_pointer;
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static const u8 known_mask[168]={MASK};
static u32 known(u32 i){return known_mask[i]||((mutation&2)&&i>=0xA4);}
static void effect(u32 stage,u32 n,DisplaySprite15179600*p){if(mutation&1){if(stage==0)D_800DBFF0=(u8*)&data.camera[1];if(stage==1){D_800DBFF0=(u8*)&data.camera[0];data.camera[0].unk2F8=999.5f+n;data.camera[0].unk2FC=-33.25f-(s32)n;data.camera[0].unk300=777.75f+n;}D_800DD436=(s16)(stage==2?7:1+n);if(stage==2)D_800DD440=tables.entry[1];}if((mutation&2)&&stage==0){p->retainedA4=0xABCDEF01u;p->tag=(s8)0x80;}}
__attribute__((noipa))s32 func_150ADA20(void){static const u32 values[]={0,499,500,0xffffffffu,0x80000000u,0x7fffffffu,999,0xfffffc19u};u32 n=++random_count,k=observation.count++;observation.args[k][0]=0x150ADA20;effect(1,n,(void*)0);return(s32)values[(row+n)&7];}
__attribute__((noipa))void func_1516865C(void*input,u8 red,u8 green,u8 blue,u8 alpha){DisplaySprite15179600*p=input;u32 i,k=observation.count++;s16 lowU=8192,lowV=8192,highU=(s16)((width+256)*32),highV=(s16)((tall+256)*32);static const u8 corner[8][2]={{1,1},{0,1},{0,0},{1,0},{1,1},{0,1},{0,0},{1,0}};packet_pointer=(u32)p;observation.args[k][0]=0x1516865C;observation.args[k][1]=168;observation.args[k][2]=red;observation.args[k][3]=green;observation.args[k][4]=blue;observation.args[k][5]=alpha;observation.input[0]=p->flags;observation.input[1]=p->textureIndex;observation.input[2]=p->value8A;observation.input[3]=(u8)p->tag;if(p->flags&128){s16 t=lowV;lowV=highV;highV=t;}if(p->flags&256){s16 t=lowU;lowU=highU;highU=t;}for(i=0;i<8;i++){p->vertices[i].v.flag=0;p->vertices[i].v.cn[0]=red;p->vertices[i].v.cn[1]=green;p->vertices[i].v.cn[2]=blue;p->vertices[i].v.cn[3]=alpha;p->vertices[i].v.tc[0]=corner[i][0]?highU:lowU;p->vertices[i].v.tc[1]=corner[i][1]?highV:lowV;}p->cleared88=p->cleared9C=p->cleared9E=0;effect(0,1,p);}
__attribute__((noipa))void *func_15168800(void*input,u8 channel,s32 context){DisplaySprite15179600*p=input;u32 i,k=observation.count++;observation.packets++;if(packet_pointer!=(u32)p)observation.bad_pointer=1;observation.args[k][0]=0x15168800;observation.args[k][1]=168;observation.args[k][2]=channel;observation.args[k][3]=(u32)context;for(i=0;i<168;i++)if(known(i)){u8 v=((u8*)p)[i];observation.bytes[i]=v;if(outcome)data.output[16+i]=v;}effect(2,1,p);return outcome?data.output:(void*)0;}
'''.replace('MASK',mask);(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Data data;SlotTables tables;Observation observation;u32 row,mutation,outcome,width,tall,random_count,packet_pointer;u8 *D_800DBFF0;s16 D_800DD436;u8 **D_800DD440;
typedef struct{Data data;SlotTables tables;Observation observation;u32 csr,camera,table;s16 count;u16 reserved;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static void reference(s32 randomize,u32 value){DisplaySprite15179600 p;s32 x,y,z,ox,oy,oz;u32 v;void*object;p.textureIndex=17;p.value8A=51;p.tag=1;p.flags=0;func_1516865C(&p,255,255,255,80);ox=(s32)((struct108*)D_800DBFF0)->unk2F8;oy=(s32)((struct108*)D_800DBFF0)->unk2FC;oz=(s32)((struct108*)D_800DBFF0)->unk300;x=func_150ADA20()%500+ox;z=func_150ADA20()%500+oz;y=randomize?func_150ADA20()%500+oy:oy+500;v=(u32)func_150ADA20()%10;p.x=(s16)x;p.y=(s16)y;p.z=(s16)z;p.lifetime=4;p.remaining=(s16)(v+35);p.flags=0x8C00;p.mode=(u8)(v+10);p.cleared9C=p.cleared9E=0;p.value80=value;p.slotIndex=D_800DD436;object=func_15168800(&p,255,0);if(object){D_800DD440[D_800DD436]=object;D_800DD436++;}}
static s32 mode(void){static const s32 n[]={0,1,-1,(-2147483647-1)};return n[row&3];}
static u32 value(void){return row&8?0x89ABCDEFu:0;}
static void fixture(void){u32 i,j;static const f32 positions[]={-32768.75f,32767.75f,-0.0f,999.875f,-999.5f,1.f,16777216.f,-16777216.f};static const s16 counts[]={0,1,298,299};static const u32 modes[]={0,3,2,1};for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(tables);i++)((u8*)&tables)[i]=0;for(i=0;i<4;i++){tables.pre[i]=row+i;tables.post[i]=~row+i;}for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;for(j=0;j<2;j++){data.camera[j].unk2F8=positions[(row>>3)&7];data.camera[j].unk2FC=positions[(row>>6)&7];data.camera[j].unk300=positions[(row>>9)&7];}D_800DBFF0=(u8*)&data.camera[0];D_800DD436=counts[(row>>2)&3];D_800DD440=tables.entry[0];mutation=(row>>7)&3;outcome=(row>>11)&1;width=row&16?65535:47;tall=row&32?0:31;random_count=packet_pointer=0;setCSR(0x1f80u|(modes[(row>>4)&3]<<13)|((row&64)?4u:0u));}
static void capture(void){current.csr=csr();current.data=data;current.tables=tables;current.observation=observation;current.count=D_800DD436;current.camera=(u32)D_800DBFF0;current.table=(u32)D_800DD440;}
static s32 fail(void){u32 msg[4]={row,current.observation.count,current.observation.packets,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){fixture();func_15179600(mode(),value());capture();actual=current;fixture();reference(mode(),value());capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('signed-offset','% 500','% 501'),('height-mode','randomizeHeight == 0','randomizeHeight != 0'),('unsigned-variation','(u32)func_150ADA20() % 10','(u32)(func_150ADA20() % 10)'),('alpha','&sprite, 255, 255, 255, 80','&sprite, 255, 255, 255, 81'),('lifetime','sprite.lifetime = 4','sprite.lifetime = 5'),('flags','sprite.flags = 0x8C00','sprite.flags = 0x8C01'),('value','sprite.value80 = value','sprite.value80 = value + 1'),('slot-id','sprite.slotIndex = D_800DD436','sprite.slotIndex = D_800DD436 + 1'),('failure','if (object != NULL)','if (1)'),('late-camera','% 500 + originX','% 500 + (s32)((struct108 *)D_800DBFF0)->unk2F8')]:
  assert old in body,name;changed=body.replace(old,new)
  if name=='late-camera':changed=changed.replace('    randomValue = func_150ADA20();','    (void)originX;\n    randomValue = func_150ADA20();',1)
  controls.append(dict(name=name,**run('control-'+name,changed,'-O2',42)))
 changed=body.replace('    object = func_15168800','    s16 cachedCount = D_800DD436;\n    u8 **cachedTable = D_800DD440;\n    object = func_15168800').replace('D_800DD440[D_800DD436] = object;','cachedTable[cachedCount] = object;').replace('D_800DD436++;','D_800DD436 = cachedCount + 1;');assert changed!=body;controls.append(dict(name='cached-post-factory-slot',**run('control-cached-post-factory-slot',changed,'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_C_void_two_word_entry_and_typed168byte_sprite_camera_slots=True,initialized_bytes_observed=109,initially_unknown59_source_bytes_not_read_before_definition=True,mutated_retainedA4_is_observed_when_defined=True,guest_compares_all168_bytes_and_native_does_not_claim_unknown_byte_copy=True,captured_camera_signed_offsets_unsigned_variation_and_fresh_slot_reload=True,finite_valid_conversion_inputs_all_four_rounding_modes_and_MXCSR=True,typed_camera_slot_tables_output_arenas_canaries_metadata_calls_globals_equal=True,opaque_noipa_defined_byte_provider_contract_not_original_backend=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
