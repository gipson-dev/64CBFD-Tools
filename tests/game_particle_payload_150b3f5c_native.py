"""SDK32 packet ABI, live providers and defined finite coordinate conversion."""
import json,subprocess
from tools.experiments import game_particle_payload_150b3f5c_match as p
from tools.tests import game_particle_payload_150b3f5c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT

def main():
 vectors=[c for c in g.cases()if not c.alias and c.mode!=5];rows=[];literal=lambda n:'0x%08Xu'%(n&0xffffffff)
 for c in vectors:
  initial=g.fixture(c);expected,calls,result,requests,copies=g.reference(initial,c);sound=next((a for t,a in calls if t==g.S['func_1000FA64']),[0]*12)
  values=[c.count,c.success,c.mode,c.seed,c.shape,g.random(c),g.read(initial,g.SOURCE+20),g.read(initial,g.SOURCE+24),*[g.read(initial,g.POSITION+4*i)for i in range(3)],*[int.from_bytes(requests[0][i:i+4],'big')for i in(0,4,8)],int.from_bytes(copies[0][64:68],'big')if copies else 0,*sound[1:4],sound[11]]
  rows.append('{'+','.join(map(literal,values))+'}')
 (o/'native-vectors.h').write_bytes(('static const u32 vectors[][19]={'+','.join(rows)+'};\n').encode())
 prefix='''#include <ultra64.h>
'''+p.MANIFEST['declarations']+'''
#define off(t,m) __builtin_offsetof(t,m)
__attribute__((noreturn)) static void exit(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
_Static_assert(sizeof(void*)==4 && sizeof(size_t)==4,"SDK32");
_Static_assert(sizeof(ParticlePosition150B3F5C)==12 && sizeof(ParticlePayload150B3F5C)==88 && sizeof(ParticleRequest150B3F5C)==28,"packet sizes");
_Static_assert(off(ParticlePayload150B3F5C,first)==64 && off(ParticlePayload150B3F5C,second)==76 && off(ParticlePayload150B3F5C,zero1)==84 && off(ParticleRequest150B3F5C,count)==21,"packet fields");
static struct {u8 prefix[0x98];u8 *payload;u8 tail[0x104];} object;
static struct {u8 before[16];u8 bytes[88];u8 after[16];} normal,alternate;
static f32 input[16];static ParticlePosition150B3F5C position;
static u8 expected_source[64];static const u32 *v;static u32 calls,copy_calls,sound_calls,rng_calls;
static void fill(void *p,u8 b,u32 n){u8 *d=p;while(n--)*d++=b;}
static u32 bits(f32 f){union{f32 f;u32 u;}x;x.f=f;return x.u;}
static f32 value(u32 u){union{f32 f;u32 u;}x;x.u=u;return x.f;}
static void position_change(f32 x){position.x=x;position.y=x+(x<0?-1:1);position.z=x+(x<0?-2:2);}
s32 func_1000EF40(struct57 *a,struct57 *b,s32 *c,s32 d,s32 e,s32 f,u16 *g){exit(10);}
u8 *func_15147A80(void *request,s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 h,void *i,u8 j,s32 k){
 ParticleRequest150B3F5C *q=request;
 if(calls++!=1 || a!=88 || b!=36 || c!=7 || d!=7 || e!=7 || f || h || i || j!=255 || k!=1)exit(11);
 if(bits(q->position.x)!=v[11] || bits(q->position.y)!=v[12] || bits(q->position.z)!=v[13] || q->lifetime!=500 || q->flags!=2 || q->kind!=9 || q->count!=(u8)(s16)v[0])exit(12);
 if(v[2]==2)position_change(30.25f);
 return v[1]?(u8*)&object:NULL;
}
u32 func_150ADA20(void){if(calls++!=2)exit(13);rng_calls++;if(v[2]==3)position_change(-40.5f);return v[5];}
u16 func_1000FA64(u16 id,s16 x,s16 y,s16 z,s32 a,u16 b,s16 c,s32 callback,void *d,s32 e,s32 f,s32 random){
 if(calls++!=3 || id!=0x221 || x!=(s16)v[15] || y!=(s16)v[16] || z!=(s16)v[17] || a!=25000 || b!=4000 || c!=600 || callback!=(s32)func_1000EF40 || d || e || f!=8 || random!=(s32)v[18])exit(14);
 sound_calls++;if(v[2]==4)object.payload=alternate.bytes;return 0x8001;
}
void *memcpy(void *to,const void *from,size_t n){u8 *d=to;const u8 *s=from;u32 i;
 if(copy_calls==0){if(calls++!=0 || from!=input || n!=64)exit(15);}
 else{
  const ParticlePayload150B3F5C *q=from;
  if(calls++!=4 || to!=object.payload || n!=88)exit(16);
  for(i=0;i<64;i++)if(q->source[i]!=expected_source[i])exit(17);
  if(bits(q->first)!=v[14] || bits(q->second)!=v[14] || bits(q->zero0) || bits(q->zero1) || q->flag0 || q->flag1)exit(18);
 }
 for(i=0;i<n;i++)d[i]=s[i];copy_calls++;
 if(copy_calls==1 && v[2]==1){input[5]=8.f;input[6]=-1.f;position_change(20.5f);}
 return to;
}
#include "native-vectors.h"
'''
 suffix='''
static int run(void){u32 row,i;for(row=0;row<sizeof(vectors)/sizeof(*vectors);row++){
 u8 *result;v=vectors[row];fill(input,0x59+(u8)(11*v[3]),sizeof(input));input[5]=value(v[6]);input[6]=value(v[7]);
 position.x=value(v[8]);position.y=value(v[9]);position.z=value(v[10]);
 for(i=0;i<64;i++)expected_source[i]=((u8*)input)[i];
 fill(&object,0x6b,sizeof(object));fill(&normal,0x79,sizeof(normal));fill(&alternate,0x83,sizeof(alternate));object.payload=normal.bytes;
 calls=copy_calls=sound_calls=rng_calls=0;result=func_150B3F5C(input,&position,(s16)v[0]);
 if(result!=(v[1]?(u8*)&object:NULL) || calls!=(v[1]?5u:2u) || copy_calls!=(v[1]?2u:1u) || sound_calls!=v[1] || rng_calls!=v[1])return 19;
 for(i=0;i<sizeof(normal);i++){
  if(v[1] && v[2]!=4 && i>=16 && i<104)continue;
  if(((u8*)&normal)[i]!=0x79)return 20;
 }
 for(i=0;i<sizeof(alternate);i++){
  if(v[1] && v[2]==4 && i>=16 && i<104)continue;
  if(((u8*)&alternate)[i]!=0x83)return 21;
 }
 for(i=0;i<sizeof(object);i++){if(i>=0x98 && i<0x9c)continue;if(((u8*)&object)[i]!=0x6b)return 22;}
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 def run(body,label,opt):
  f=o/label;src=f.with_suffix('.c');src.write_bytes((prefix+body+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(f)],capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(f)],capture_output=True,text=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode
 body=p.MANIFEST['body'];profiles={}
 for opt in('-O0','-O2','-O3'):
  code=run(body,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=len(vectors),SDK32=True,UBSan=True,strict_aliasing=True,finite_signed32_coordinate_domain=True)
 controls=[('copy64','source, 0x40','source, 0x3C'),('count','count = count','count = count + 1'),('flag','flag0 = 0','flag0 = 1'),('lifetime','lifetime = 500','lifetime = 501'),('flags','flags = 2','flags = 3'),('kind','kind = 9','kind = 8'),('sum','source[6] + source[5]','source[6] + source[6]'),('zero','zero1 = 0.0f','zero1 = 1.0f'),('factory','0x58, 0x24','0x58, 0x20'),('sound-id','(0x221,','(0x220,'),('sound-coordinate','(s16)(s32)position->y','(s16)(s32)position->x'),('volume','25000, 4000','25001, 4000'),('pitch','4000, 600','4001, 600'),('range','600, (s32)','601, (s32)'),('random-mask','random & 0x40','random & 0x20'),('copy88','&local.payload, 0x58','&local.payload, 0x54')]
 outcomes=[]
 for name,old,new in controls:
  assert old in body,name;code=run(body.replace(old,new),'control-'+name,'-O2');assert code in range(10,23),(name,code);outcomes.append(dict(control=name,comparison_exit=code,source_sha256=p.sha(o/('control-'+name+'.c')),binary_sha256=p.sha(o/('control-'+name))))
 q=dict(profiles=profiles,effective_source_controls=outcomes,no_signal_or_UBSan_trap_counted=True,unwritten_padding_not_compared=True,guest_only_alias_and_incoming_home_cases=True,callback_address_codec_verified_not_called=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(native_cases=len(vectors),profiles=list(profiles),controls=len(outcomes))),flush=True);return q
if __name__=='__main__':main()
