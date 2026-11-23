"""SDK32 semantic C under strict aliasing and UBSan, with effective result controls."""
import hashlib,json,subprocess
from tools.experiments import game_ground_burst_callback_150df334_match as p
from tools.tests import game_ground_burst_callback_150df334_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def expected(c):
 initial=g.fixture(c);m,service=g.reference(initial,c);h=2166136261;home=g.STACK+c.phase
 for name,args,snap,supplied in service.observed:
  tag={'func_1504697C':1,'func_150ADA20':2,'func_150E83AC':3,'func_151A9834':4}[name];h=mix(h,tag);h=mix(h,len(args));pointers={0,3}if tag in(1,4)else{0}if tag==3 else set();tokens={home-68:1,home-40:2,home-56:3,home-80:4}
  for i,x in enumerate(args):h=mix(h,tokens.get(x,x)if i in pointers else x)
  if supplied:
   values=supplied[0][2]
   for i in range(3):h=mix(h,int.from_bytes(bytes(values[4*i:4*i+4]),'big'))
   if tag==4:
    for v in supplied[1][2]:h=mix(h,v)
 public=2166136261
 for i in range(-16,144):public=mix(public,m[g.OWNER+i])
 for i in range(-16,48):public=mix(public,m[g.MARK+i])
 return public,h
def vectors():
 rows=[];excluded=0
 for c in g.cases():
  if c.ground_mode!=2:excluded+=1;c=g.replace(c,ground_mode=2)
  rows.append('{{'+','.join(str(x&0xffffffff)+'u'for x in([getattr(c,n)for n in c.__dataclass_fields__]+list(expected(c))))+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded
def program():
 text='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\ntypedef struct {u8 prefix[40];struct17 position;u8 tail[76];} struct260;\n'+p.MANIFEST['declarations']+r'''
typedef struct {u32 f[11];} Vector;
#include "native-vectors.h"
typedef struct {u8 before[16];struct260 owner;u8 after[16];} OwnerBox;
typedef struct {u8 before[16];u32 mark;u8 tail[28],after[16];} MarkBox;
static OwnerBox box;static MarkBox marker;static const Vector *v;static u32 callHash,calls,randoms,invalid;static f32 *probe,*contact;static HeightResult71820 *ground;
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(f32)==4&&__CHAR_BIT__==8,"SDK32");
_Static_assert(sizeof(struct260)==128&&OFF(struct260,position)==40&&sizeof(struct17)==12,"typed owner coordinates");
_Static_assert(sizeof(HeightResult71820)==36&&OFF(HeightResult71820,vertices)==4&&OFF(HeightResult71820,pad16)==22&&OFF(HeightResult71820,metadata)==24&&OFF(HeightResult71820,flags)==28&&OFF(HeightResult71820,state)==29&&OFF(HeightResult71820,pad1E)==30&&OFF(HeightResult71820,value)==32,"complete ground layout");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"canonical endian codec");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static void putword(void *p,u32 x){__builtin_memcpy(p,&x,4);}
static u32 pattern(u32 i,u32 call){return(i*5+call+v->f[0])&255;}
static u32 patternWord(u32 i,u32 call){return(pattern(i,call)<<24)|(pattern(i+1,call)<<16)|(pattern(i+2,call)<<8)|pattern(i+3,call);}
static u32 initByte(u32 i){return(i*7+v->f[0]*3)&255;}
static u32 initWord(u32 i){return(initByte(i)<<24)|(initByte(i+1)<<16)|(initByte(i+2)<<8)|initByte(i+3);}
static void groundFill(HeightResult71820 *g,u32 call){u32 i,x;u8 bytes[36];for(i=0;i<36;i++)bytes[i]=(u8)(call?pattern(i,call):initByte(i));if(!call){f32 f=(f32)v->f[0]-20.5f;x=word(&f);for(i=0;i<4;i++)bytes[i]=(u8)(x>>(24-8*i));}x=((u32)bytes[0]<<24)|((u32)bytes[1]<<16)|((u32)bytes[2]<<8)|bytes[3];putword(&g->height,x);for(i=0;i<9;i++)g->vertices[i]=(s16)(((u32)bytes[4+2*i]<<8)|bytes[5+2*i]);g->pad16=(s16)(((u32)bytes[22]<<8)|bytes[23]);g->metadata=((u32)bytes[24]<<24)|((u32)bytes[25]<<16)|((u32)bytes[26]<<8)|bytes[27];g->flags=bytes[28];g->state=bytes[29];g->pad1E=(u16)(((u32)bytes[30]<<8)|bytes[31]);g->value=(s32)(((u32)bytes[32]<<24)|((u32)bytes[33]<<16)|((u32)bytes[34]<<8)|bytes[35]);}
static u32 groundByte(u32 i){u32 x,n,at;if(i<4){x=word(&ground->height);n=4;at=0;}else if(i<22){at=4+(i-4)/2*2;x=(u16)ground->vertices[(i-4)/2];n=2;}else if(i<24){at=22;x=(u16)ground->pad16;n=2;}else if(i<28){at=24;x=ground->metadata;n=4;}else if(i==28)return ground->flags;else if(i==29)return ground->state;else if(i<32){at=30;x=ground->pad1E;n=2;}else{at=32;x=(u32)ground->value;n=4;}return(x>>(8*(n-1-(i-at))))&255;}
static void vectorSet(void *a,f32 x,f32 y,f32 z){f32 values[3]={x,y,z};__builtin_memcpy(a,values,12);}
static void logStart(u32 tag,u32 n){calls++;callHash=mix(callHash,tag);callHash=mix(callHash,n);}
static void arg(u32 a){callHash=mix(callHash,a);}
static void vectorLog(const void *a){u32 i;for(i=0;i<3;i++)arg(word((const u8*)a+4*i));}
s32 func_1504697C(f32 *position,u16 selector,f32 threshold,HeightResult71820 *result){probe=position;ground=result;logStart(1,4);arg(1);arg(selector);arg(word(&threshold));arg(2);vectorLog(position);groundFill(result,0);if(v->f[2]&1)vectorSet((f32*)&box.owner.position,71.0f,-19.0f,23.0f);return(s32)v->f[1];}
s32 func_150ADA20(void){logStart(2,0);randoms++;if(v->f[2]&2){vectorSet((f32*)&box.owner.position,(f32)(31+randoms),-7.0f,13.0f);box.owner.prefix[12]^=0x55;box.owner.prefix[1]^=0xaa;}if(v->f[2]&4){vectorSet(probe,(f32)(100+calls),(f32)(-30-(s32)calls),(f32)(50+calls));if(contact)vectorSet(contact,(f32)(100+calls),(f32)(-30-(s32)calls),(f32)(50+calls));}if(v->f[2]&32)groundFill(ground,calls);return(s32)v->f[randoms==1?4:5];}
void func_150E83AC(struct17 *position,s16 lifetime,u8 channel,s32 context){u32 address;if(position==&box.owner.position)address=0x30028;else{address=3;contact=(f32*)position;}logStart(3,4);arg(address);arg((u32)(s32)lifetime);arg(channel);arg((u32)context);vectorLog((f32*)position);if(v->f[2]&8)vectorSet((f32*)position,202.0f,-88.0f,3.0f);if(v->f[2]&16){vectorSet((f32*)&box.owner.position,65.0f,34.0f,-17.0f);box.owner.prefix[12]^=0x33;box.owner.prefix[1]^=0xcc;}}
void func_151A9834(f32 *position,f32 minimum,f32 radius,HeightResult71820 *result,s32 count,u8 selector,u8 *tag,u8 channel,s32 context){u32 i;logStart(4,9);arg(4);arg(word(&minimum));arg(word(&radius));arg(2);arg((u32)count);arg(selector);arg((u32)tag);arg(channel);arg((u32)context);vectorLog(position);if(result!=ground||tag)invalid=1;for(i=0;i<36;i++)arg(groundByte(i));marker.mark=calls;}
'''
 text+=p.MANIFEST['body'].replace('func_150DF334(','subject(')+r'''
static void (*const death[9])(struct260 *)={[8]=subject};
static u32 publicHash(void){u32 h=2166136261u,x;const u8 *b=(const u8*)&box;s32 i;for(i=-16;i<144;i++){if(i>=40&&i<52){x=word((const u8*)&box.owner+40+(i-40)/4*4);x=(x>>(24-8*((i-40)%4)))&255;}else x=b[i+16];h=mix(h,x);}b=(const u8*)&marker;for(i=-16;i<48;i++){if(i>=0&&i<4)x=(marker.mark>>(24-8*i))&255;else x=b[i+16];h=mix(h,x);}return h;}
static void initialize(void){u32 i;u8 *b=(u8*)&box;for(i=0;i<sizeof(box);i++)b[i]=(u8)(((s32)i-16)*29+(s32)v->f[0]*11+0x51);b=(u8*)&marker;for(i=0;i<sizeof(marker);i++)b[i]=(u8)(((s32)i-16)*29+(s32)v->f[0]*11+0x51);box.owner.prefix[12]=(u8)v->f[7];box.owner.prefix[1]=(u8)v->f[8];for(i=0;i<3;i++){f32 f=(f32)((s32)((v->f[0]+i*7)%31)-15)*0.25f;putword((u8*)&box.owner.position+4*i,word(&f));}marker.mark=(word(&marker.mark)&255u)<<24|(word(&marker.mark)&0xff00u)<<8|(word(&marker.mark)&0xff0000u)>>8|(word(&marker.mark)>>24);callHash=2166136261u;calls=randoms=invalid=0;probe=contact=0;ground=0;}
static int run(void){u32 i;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];initialize();death[8](&box.owner);if(invalid)return 10;if(publicHash()!=v->f[9])return 11;if(callHash!=v->f[10])return 12;if(calls!=5||randoms!=2)return 13;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
def main():
 count,excluded=vectors();source=program();profiles={};outcomes=[]
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-Wno-unused-function',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_owner_and_vectors=True,complete_public_and_guard_bytes_compared=True,canonical_endian_and_private_pointer_roles=True)
 controls={'wrong-probe-height':('+ 500.0f;','+ 499.0f;'),'signed-lifetime-remainder':('random % 62U','(s32)random % 62'),'wrong-lifetime-range':('% 62U + 120U','% 61U + 120U'),'wrong-burst-count':('% 3U + 3U','% 3U + 2U'),'wrong-radius':('1000.0f, 250.0f','1000.0f, 251.0f'),'wrong-timed-channel':('((u8 *)owner)[0x0C], ((u8 *)owner)[1]','((u8 *)owner)[0x0B], ((u8 *)owner)[1]'),'wrong-contact-height':('contact.vector.unk4 = ground.height;','contact.vector.unk4 = ground.height + 1.0f;')}
 # Only change the subject, never its providers or the result oracle.
 body=p.MANIFEST['body'].replace('func_150DF334(','subject(')
 for label,(old,new)in controls.items():
  assert old in body,label;q=run('control-'+label,source.replace(body,body.replace(old,new)),'-O2');assert q.returncode in(10,11,12,13),(label,q.returncode,'Control must reach a result comparison');exe=o/('control-'+label);outcomes.append(dict(control=label,comparison_exit=q.returncode,binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(exe.with_suffix('.c').read_bytes()).hexdigest()))
 q=dict(profiles=profiles,effective_source_controls=outcomes,excluded_uninitialized_ground_cases=excluded,initialized_ground_supplement_cases=excluded,native_initial_or_padding_bit_identity_claim=False,providers_initialize_complete_ground_before_native_reads=True,full_original_C_dispatcher_execution_claim=False,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
