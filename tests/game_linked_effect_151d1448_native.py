"""Typed SDK32 packet fields and full backing guards; padding bits are excluded."""
import json,subprocess
from tools.experiments import game_linked_effect_151d1448_match as p
from tools.tests import game_linked_effect_151d1448_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT;REQUEST_TOKEN=0xabcdef40
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def guard_hash(m):
 h=2166136261
 for base,n,skip in((g.OWNER,512,set(range(0x28,0x2c))|set(range(0x30,0x34))|set(range(0x40,0x4c))|set(range(0x14c,0x150))),(g.ACTOR,512,set(range(0x14c,0x150))),(g.OTHER,512,set(range(0x14c,0x150))),(g.ROOT,160,set(range(0x98,0x9c))),(g.CHILD,160,set()),(g.OUTA,32,set(range(32))),(g.OUTB,32,set(range(32)))):
  for i in range(-16,n+16):
   if i not in skip:h=mix(h,m[base+i])
 return h
def vectors():
 rows=[];excluded=0
 for c in g.cases():
  if c.root!=g.ROOT or c.dest_alias:excluded+=1;continue
  initial=g.fixture(c);m,calls,obs=g.reference(initial,c);packet=obs[0][1];request=(int.from_bytes(packet[i:i+4],'big')for i in(0,4,8));req=[*request,int.from_bytes(packet[12:14],'big'),int.from_bytes(packet[14:16],'big'),int.from_bytes(packet[16:20],'big'),packet[20],packet[21],int.from_bytes(packet[24:28],'big')]
  public=[g.read(m,g.S['D_80082FA0']),m[g.OWNER+1],m[g.OWNER+0xc],m[g.OWNER+4],g.read(m,g.OWNER+0x28),g.read(m,g.OWNER+0x30),g.read(m,g.OWNER+0x14c),m[g.ACTOR+4],g.read(m,g.ACTOR+0x14c),m[g.OTHER+4],g.read(m,g.OTHER+0x14c),*(g.read(m,g.OWNER+0x40+4*i)for i in range(3)),g.read(m,g.ROOT+0x98)]
  copy=[0]*11
  if c.outcome:
   _,dest,blob,child=obs[1];tmp={i:b for i,b in enumerate(blob)};copy=[dest,32,child,*g.config_words(tmp,0)]
  fields=[c.seed,c.kind,c.views,c.channel,c.context,c.outcome,c.mutation,c.alias,g.value(c),*g.positions(c),*public,REQUEST_TOKEN,*calls[0][1][1:],*req,*copy,*g.config_words(m,g.OUTA),*g.config_words(m,g.OUTB),guard_hash(m)]
  assert len(fields)==75,len(fields);rows.append('{'+','.join(str(v&0xffffffff)+'u'for v in fields)+'}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded
def program():
 body=p.MANIFEST['body'].replace('func_151D1448(','subject(')
 return '#include <ultra64.h>\n'+'''typedef struct {f32 x,y,z;} PositionVector151D0F60;\n'''+p.MANIFEST['declarations']+r'''
typedef struct {u8 *actor;u8 identity,pad05[3];u8 *created;PositionVector151D0F60 previous,position,delta;f32 distance;u8 callback,pad35[3];} Link;
typedef struct {u8 prefix[0x28];Link link;u8 pad60[0xec];f32 value;u8 tail[0xb0];} Owner;
typedef struct {u8 prefix[0x14c];f32 value;u8 tail[0xb0];} Actor;
typedef struct {u8 prefix[0x98];u8 *payload;u8 tail[4];} Core;
typedef struct {u8 pre[16];Owner value;u8 post[16];} OwnerBox;
typedef struct {u8 pre[16];Actor value;u8 post[16];} ActorBox;
typedef struct {u8 pre[16];Core value;u8 post[16];} CoreBox;
typedef struct {u8 pre[16];u8 value[160];u8 post[16];} ChildBox;
typedef struct {u8 pre[16];LinkedEffectConfig151D1448 value;u8 post[16];} OutputBox;
typedef struct {u32 field[75];} Vector;
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(f32)==4&&__CHAR_BIT__==8,"SDK32 words");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__&&(s32)0xffffffffu==-1,"native word codec");
_Static_assert(sizeof(LinkedEffectRequest151D1448)==28&&OFF(LinkedEffectRequest151D1448,lifetime)==12&&OFF(LinkedEffectRequest151D1448,mode)==14&&OFF(LinkedEffectRequest151D1448,active)==16&&OFF(LinkedEffectRequest151D1448,kind)==20&&OFF(LinkedEffectRequest151D1448,count)==21&&OFF(LinkedEffectRequest151D1448,zero)==24,"request fields");
_Static_assert(sizeof(LinkedEffectConfig151D1448)==32&&OFF(LinkedEffectConfig151D1448,value04)==4&&OFF(LinkedEffectConfig151D1448,level)==8&&OFF(LinkedEffectConfig151D1448,parameters)==12,"config fields");
_Static_assert(sizeof(Link)==0x38&&sizeof(Owner)==512&&OFF(Owner,link)==0x28&&OFF(Owner,link.created)==0x30&&OFF(Owner,link.position)==0x40&&OFF(Owner,value)==0x14c&&sizeof(Actor)==512&&OFF(Actor,value)==0x14c,"typed owner/actor");
_Static_assert(sizeof(Core)==0xa0&&OFF(Core,payload)==0x98,"actual factory payload slot");
#include "native-vectors.h"
s32 D_80082FA0;
static OwnerBox ownerBox;static ActorBox actorBox,otherBox;static CoreBox coreBox;static ChildBox childBox;static OutputBox output[2];
static const Vector *v;static u8 *initialActor;static u32 factoryCalls,copyCalls,copyData[11];static int invalid;
static u32 word(const void *p){const u8 *b=p;return(u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
static void putword(void *p,u32 x){u8 *b=p;b[0]=(u8)x;b[1]=(u8)(x>>8);b[2]=(u8)(x>>16);b[3]=(u8)(x>>24);}
static u32 pointer(const void *p){if(!p)return 0;if(p==&ownerBox.value)return 0x30000;if(p==&actorBox.value)return 0x80000;if(p==&otherBox.value)return 0x88000;if(p==childBox.value)return 0x50000;if(p==&coreBox.value)return 0x60000;if(p==&output[0].value)return 0x70000;if(p==&output[1].value)return 0x71000;invalid=1;return 0xffffffffu;}
static int same(const u32 *a,const u32 *b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void config(const LinkedEffectConfig151D1448 *p,u32 *a){u32 i;a[0]=pointer(p->owner);a[1]=word(&p->value04);a[2]=p->level;for(i=0;i<5;i++)a[3+i]=word(&p->parameters[i]);}
u8 *func_15147A80(void *packet,s32 bytes,s32 entry,s32 active,s32 first,s32 second,s32 resource,s32 value,void *optional,u8 channel,s32 context){
 LinkedEffectRequest151D1448 *request=packet;u32 a[11]={0xabcdef40u,(u32)bytes,(u32)entry,(u32)active,(u32)first,(u32)second,(u32)resource,(u32)value,pointer(optional),channel,(u32)context};u32 fields[9],i;
 factoryCalls++;for(i=0;i<3;i++)fields[i]=word((const u8*)&request->position+4*i);fields[3]=(u16)request->lifetime;fields[4]=(u16)request->mode;fields[5]=(u32)request->active;fields[6]=request->kind;fields[7]=request->count;fields[8]=(u32)request->zero;
 if(!same(a,&v->field[27],11)||!same(fields,&v->field[38],9))invalid=1;
 if(v->field[6]&1){ownerBox.value.prefix[1]^=0x55;ownerBox.value.prefix[0xc]^=0x5a;initialActor[4]^=37;ownerBox.value.link.actor=(u8*)&otherBox.value;putword(initialActor+0x14c,0xc1200000);putword(&otherBox.value.value,0x42c80000);D_80082FA0=1;for(i=0;i<3;i++)putword((u8*)&ownerBox.value.link.position+4*i,0x41200000+i*0x200000);}
 if(v->field[6]&2)ownerBox.value.link.created=0;
 if(v->field[6]&4){request->mode^=1;request->active^=0x10;putword(&request->position.y,word(&request->position.y)^0x80000000u);}
 if(!v->field[5])return 0;coreBox.value.payload=(u8*)&output[(v->field[6]&2)?1:0].value;return(u8*)&coreBox.value;
}
void *memcpy(void *dest,const void *source,u32 n){u32 i;u8 *d=dest;const u8 *s=source;copyCalls++;copyData[0]=pointer(dest);copyData[1]=n;copyData[2]=pointer(ownerBox.value.link.created);config(source,copyData+3);for(i=0;i<n;i++)d[i]=s[i];return dest;}
'''+body+r'''
static void caller(u8 *owner){subject(owner);}
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static int skip(u32 bank,s32 i){if(bank==0)return(i>=0x28&&i<0x2c)||(i>=0x30&&i<0x34)||(i>=0x40&&i<0x4c)||(i>=0x14c&&i<0x150);if(bank==1||bank==2)return i>=0x14c&&i<0x150;if(bank==3)return i>=0x98&&i<0x9c;if(bank>=5)return i>=0&&i<32;return 0;}
static u32 guards(void){u32 h=2166136261u,b; s32 i;const u8 *base[7]={(u8*)&ownerBox,(u8*)&actorBox,(u8*)&otherBox,(u8*)&coreBox,(u8*)&childBox,(u8*)&output[0],(u8*)&output[1]};const s32 size[7]={512,512,512,160,160,32,32};for(b=0;b<7;b++)for(i=-16;i<size[b]+16;i++)if(!skip(b,i))h=mix(h,base[b][i+16]);return h;}
static void fill(void *p,u32 size,u32 seed){u32 j;u8 *b=p;for(j=0;j<size;j++)b[j]=(u8)(((s32)j-16)*29+(s32)seed*11+0x51);}
static int run(void){u32 n,i,b,public[15],a[16];for(n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){
 v=&vectors[n];invalid=0;factoryCalls=copyCalls=0;for(i=0;i<11;i++)copyData[i]=0;
 fill(&ownerBox,sizeof(ownerBox),v->field[0]);fill(&actorBox,sizeof(actorBox),v->field[0]);fill(&otherBox,sizeof(otherBox),v->field[0]);fill(&coreBox,sizeof(coreBox),v->field[0]);fill(&childBox,sizeof(childBox),v->field[0]);fill(&output[0],sizeof(output[0]),v->field[0]);fill(&output[1],sizeof(output[1]),v->field[0]);
 initialActor=v->field[7]?(u8*)&ownerBox.value:(u8*)&actorBox.value;ownerBox.value.link.actor=initialActor;ownerBox.value.link.created=childBox.value;ownerBox.value.prefix[1]=(u8)v->field[4];ownerBox.value.prefix[0xc]=(u8)v->field[3];initialActor[4]=(u8)v->field[1];
 putword(&ownerBox.value.value,v->field[7]?v->field[8]:0x3f400000);putword(&actorBox.value.value,v->field[7]?0x3f400000:v->field[8]);putword(&otherBox.value.value,0x3f400000);for(i=0;i<3;i++)putword((u8*)&ownerBox.value.link.position+4*i,v->field[9+i]);
 coreBox.value.payload=(u8*)&output[0].value;D_80082FA0=(s32)v->field[2];for(b=0;b<2;b++){output[b].value.owner=0;putword(&output[b].value.value04,0x3f000000+(v->field[0]&255));output[b].value.level=0x5a;for(i=0;i<5;i++)putword(&output[b].value.parameters[i],0x41000000+i*0x100+(v->field[0]&255));}
 caller((u8*)&ownerBox.value);
 public[0]=(u32)D_80082FA0;public[1]=ownerBox.value.prefix[1];public[2]=ownerBox.value.prefix[0xc];public[3]=ownerBox.value.prefix[4];public[4]=pointer(ownerBox.value.link.actor);public[5]=pointer(ownerBox.value.link.created);public[6]=word(&ownerBox.value.value);public[7]=actorBox.value.prefix[4];public[8]=word(&actorBox.value.value);public[9]=otherBox.value.prefix[4];public[10]=word(&otherBox.value.value);for(i=0;i<3;i++)public[11+i]=word((u8*)&ownerBox.value.link.position+4*i);public[14]=pointer(coreBox.value.payload);
 config(&output[0].value,a);config(&output[1].value,a+8);
 if(factoryCalls!=1||copyCalls!=v->field[5]||invalid||!same(public,&v->field[12],15)||!same(copyData,&v->field[47],11)||!same(a,&v->field[58],16)||guards()!=v->field[74])return 1;
 }return 0;}
'''+START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
 # Linux enters _start directly, without the return-address push assumed by
 # the i386 C calling convention. Realign before optimized SSE stack stores.
def main():
 count,excluded=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1','-Wno-missing-braces',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-5000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_actor_owner_request_config_and_core=True,explicit_layout_assertions=source.count('_Static_assert('),padding_bits_compared=False,backing_guard_bytes_checked=True)
 controls={'wrong-actor-type':('actor[4] == 0x25','actor[4] == 0x24'),'wrong-view-boundary':('D_80082FA0 > 0','D_80082FA0 >= 0'),'wrong-special-parameter':('800.0f','700.0f'),'wrong-request-count':('request.count = 25','request.count = 24'),'wrong-request-mode':('request.mode = 0x36','request.mode = 0x35'),'wrong-payload-size':('&config, 32','&config, 28'),'signed-context':('owner[0x0C], owner[1]','owner[0x0C], (s8)owner[1]'),'missing-attachment':('*(u8 **)(link + 8) = created;','*(u8 **)(link + 8) = NULL;')}
 rejected=[]
 for label,(old,new)in controls.items():
  assert old in source,label;q=run('control-'+label,source.replace(old,new),'-O2');assert q.returncode!=0,(label,'ineffective native comparison control');rejected.append(label)
 q=dict(profiles=profiles,effective_source_controls=rejected,excluded_synthetic_guest_return_addresses=excluded,request_padding_bytes_excluded=2,config_padding_bytes_excluded=3,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
