"""Typed SDK32 backing, canonical endian/pointer comparison and opaque providers."""
import json,subprocess
from tools.experiments import game_linked_effect_update_151d1138_match as p
from tools.tests import game_linked_effect_update_151d1138_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
BANKS=((g.OWNER,512),(g.ACTOR,512),(g.OTHER,512),(g.CHILD,160),(g.MARK,32))
FIELDS=[(0,0,4,0),(0,14,2,0),(0,40,4,1),(0,48,4,1),*((0,at,4,0)for at in range(0x34,0x5c,4)),*((bank,at,4,0)for bank in(1,2)for at in(0,0x28,0x184)),(4,0,4,0)]
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def public_hash(m):
 h=2166136261
 for base,n in BANKS:
  for i in range(-16,n+16):h=mix(h,m[base+i])
 return h
def calls_hash(calls):
 h=2166136261
 for t,a in calls:
  for x in(t,len(a),*a):h=mix(h,x)
 return h
def observations_hash(observed):
 h=2166136261
 for v in observed:
  tag={'callback':0,'length':1,'classify':2,'final':3}[v[0]];h=mix(h,tag)
  values=(*v[2],*v[3])if tag==0 else v[2]if tag==1 else(v[2],)if tag==2 else v[3:5]
  for x in values:h=mix(h,x)
 return h
def vectors():
 rows=[];excluded={'owner_actor_alias':0,'signaling_NaN_float_return':0}
 for c in g.cases():
  if c.alias:excluded['owner_actor_alias']+=1;continue
  if c.length==0x7f800001:excluded['signaling_NaN_float_return']+=1;continue
  m,calls,obs=g.reference(g.fixture(c),c);fields=[getattr(c,n)for n in c.__dataclass_fields__]+[public_hash(m),calls_hash(calls),observations_hash(obs)];assert len(fields)==17;rows.append('{'+','.join(str(v&0xffffffff)+'u'for v in fields)+'}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded

def program():
 text='#include <ultra64.h>\ntypedef struct {f32 x,y,z;} PositionVector151D0F60;\n'+p.MANIFEST['declarations']+r'''
typedef struct {s32 head;u8 prefix04[9],flags;s16 lifetime;s8 death,update;u8 prefix12[0x16];LinkedEffectState151D1138 link;u8 tail[0x1a0];} NativeOwner;
typedef NativeOwner struct260;
typedef struct {s32 live;u8 prefix04[0x24];f32 vertical;u8 pad2c[0xf],identity,pad3c[0x71],busy,padae[0xd6];u32 classword;u8 tail[0x78];} Actor;
typedef struct {u8 pre[16];NativeOwner value;u8 post[16];} OwnerBox;
typedef struct {u8 pre[16];Actor value;u8 post[16];} ActorBox;
typedef struct {u8 pre[16],value[160],post[16];} ChildBox;
typedef struct {u8 pre[16];u32 value;u8 tail[28],post[16];} MarkBox;
typedef struct {u32 field[17];} Vector;
typedef struct {u32 bank,offset,size,pointer;} Field;
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(f32)==4&&__CHAR_BIT__==8&&(s32)0xffffffffu==-1,"SDK32 words");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"native word codec");
_Static_assert(sizeof(NativeOwner)==512&&OFF(NativeOwner,lifetime)==14&&OFF(NativeOwner,link)==40&&OFF(NativeOwner,link.created)==48&&OFF(NativeOwner,link.position)==64&&OFF(NativeOwner,link.delta)==76&&OFF(NativeOwner,link.distance)==88&&OFF(NativeOwner,link.selector)==92,"owner/link fields");
_Static_assert(sizeof(Actor)==512&&OFF(Actor,vertical)==0x28&&OFF(Actor,identity)==0x3b&&OFF(Actor,busy)==0xad&&OFF(Actor,classword)==0x184,"typed actor fields");
_Static_assert(sizeof(LinkedEffectState151D1138)==56&&sizeof(PositionVector151D0F60)==12&&sizeof(((LinkedEffectState151D1138*)0)->delta)==12,"vectors and real float array");
#include "native-vectors.h"
static OwnerBox ownerBox;static ActorBox actorBox,otherBox;static ChildBox childBox;static MarkBox markBox;
static u8 *const bases[5]={(u8*)&ownerBox,(u8*)&actorBox,(u8*)&otherBox,(u8*)&childBox,(u8*)&markBox};
static const u32 sizes[5]={512,512,512,160,32};
static const u32 addresses[5]={0x30000,0x80000,0x88000,0x50000,0x90000};
static const Field fields[]={FIELD_ROWS};
static const Vector *v;static u32 callHash,observationHash;static int invalid;
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){const u8 *b=p;return(u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
static void putword(void *p,u32 x){u8 *b=p;b[0]=(u8)x;b[1]=(u8)(x>>8);b[2]=(u8)(x>>16);b[3]=(u8)(x>>24);}
static u32 be(const void *p,u32 n){const u8 *b=p;u32 x=0,i;for(i=0;i<n;i++)x=(x<<8)|b[i];return x;}
static void putbe(void *p,u32 x,u32 n){u8 *b=p;u32 i;for(i=0;i<n;i++)b[i]=(u8)(x>>(8*(n-1-i)));}
static u32 logical(u32 x){u32 b,start;if(!x)return 0;for(b=0;b<5;b++){start=(u32)(bases[b]+16);if(x>=start&&x<start+sizes[b])return addresses[b]+x-start;}invalid=1;return 0xffffffffu;}
static u32 native(u32 x){u32 b;if(!x)return 0;for(b=0;b<5;b++)if(x>=addresses[b]&&x<addresses[b]+sizes[b])return(u32)(bases[b]+16+x-addresses[b]);invalid=1;return 0;}
static u32 canonical(u32 bank,s32 at){u32 f,x;const Field *p;const u8 *b=bases[bank]+16;for(f=0;f<sizeof(fields)/sizeof(fields[0]);f++){p=&fields[f];if(p->bank!=bank||at<(s32)p->offset||at>=(s32)(p->offset+p->size))continue;x=p->size==4?word(b+p->offset):(u32)b[p->offset]|((u32)b[p->offset+1]<<8);if(p->pointer)x=logical(x);return(x>>(8*(p->size-1-(at-(s32)p->offset))))&255;}return bases[bank][at+16];}
static u32 public_hash(void){u32 h=2166136261u,b;s32 i;for(b=0;b<5;b++)for(i=-16;i<(s32)sizes[b]+16;i++)h=mix(h,canonical(b,i));return h;}
static void logcall(u32 target,u32 count,u32 a,u32 b){callHash=mix(callHash,target);callHash=mix(callHash,count);callHash=mix(callHash,a);if(count==2)callHash=mix(callHash,b);}
static void observe(u32 tag){u32 i;observationHash=mix(observationHash,tag);if(tag==0){for(i=0;i<3;i++)observationHash=mix(observationHash,word((u8*)&ownerBox.value.link.previous+4*i));for(i=0;i<3;i++)observationHash=mix(observationHash,word((u8*)&ownerBox.value.link.position+4*i));}else if(tag==1){for(i=0;i<3;i++)observationHash=mix(observationHash,word(ownerBox.value.link.delta+i));}else if(tag==2)observationHash=mix(observationHash,word(&ownerBox.value.link.distance));else{observationHash=mix(observationHash,logical(word(&ownerBox.value.link.created)));observationHash=mix(observationHash,word(&ownerBox.value.link.distance));}}
NATIVE_RUNTIME
'''
 text=text.replace('FIELD_ROWS',','.join('{'+','.join(map(str,f))+'}'for f in FIELDS))
 runtime=r'''
static s32 cb_common(u32 index,u8 *actor,PositionVector151D0F60 *out){u32 i;logcall(@CB@+64*index,2,logical((u32)actor),logical((u32)out));observe(0);if(index!=v->field[5]||actor!=(u8*)&actorBox.value||out!=&ownerBox.value.link.position)invalid=1;for(i=0;i<3;i++){f32 value=(f32)((s32)((v->field[0]+i*7)%31)-15)*0.5f;putword((u8*)out+4*i,word(&value));}if(v->field[11]&1){ownerBox.value.link.actor=(u8*)&otherBox.value;ownerBox.value.link.selector^=7;actorBox.value.classword=v->field[9]^0x1000000f;}if(v->field[11]&2){ownerBox.value.link.previous.x=1.0f;ownerBox.value.link.previous.y=-2.0f;ownerBox.value.link.previous.z=3.0f;}return(s32)v->field[4];}
CALLBACK_WRAPPERS
f32 func_15143E64(f32 *delta){f32 result;logcall(@LEN@,1,logical((u32)delta),0);observe(1);if(delta!=ownerBox.value.link.delta)invalid=1;if(v->field[11]&4){actorBox.value.vertical=1.0f;actorBox.value.busy=1;actorBox.value.classword=v->field[9]^0x10000006;}if(v->field[11]&8){ownerBox.value.link.actor=(u8*)&otherBox.value;ownerBox.value.link.distance=-10.0f;ownerBox.value.link.created=v->field[10]?0:childBox.value;}putword(&result,v->field[6]);return result;}
u32 func_1510F8CC(u32 value){logcall(@CLASS@,1,value,0);observe(2);if(v->field[11]&16){putword(&ownerBox.value.link.distance,(v->field[0]&1)?0x7fc12345u:0);actorBox.value.vertical=0.0f;actorBox.value.busy=0;ownerBox.value.link.created=(v->field[0]&1)?childBox.value:0;}return value&31;}
void func_151D13E0(u8 *owner){logcall(@DETACH@,1,logical((u32)owner),0);observe(3);if(owner!=(u8*)&ownerBox.value)invalid=1;markBox.value=0x11111111;ownerBox.value.link.created=0;}
void func_151D1448(u8 *owner){logcall(@ATTACH@,1,logical((u32)owner),0);observe(3);if(owner!=(u8*)&ownerBox.value)invalid=1;markBox.value=0x22222222;ownerBox.value.link.created=childBox.value;}
'''
 wrappers='\n'.join(f'static s32 callback_{i}(u8 *actor,PositionVector151D0F60 *out){{return cb_common({i},actor,out);}}'for i in range(256))+'\ns32 (*D_8008FC30[256])(u8 *,PositionVector151D0F60 *)={'+','.join(f'callback_{i}'for i in range(256))+'};\n'
 runtime=runtime.replace('CALLBACK_WRAPPERS',wrappers)
 for key,name in(('CB','_callbacks'),('LEN','func_15143E64'),('CLASS','func_1510F8CC'),('DETACH','func_151D13E0'),('ATTACH','func_151D1448')):runtime=runtime.replace('@'+key+'@',hex(g.S[name])+'u')
 text=text.replace('NATIVE_RUNTIME',runtime)+p.MANIFEST['body'].replace('func_151D1138(','subject(')+r'''
static void (*const dispatch[96])(struct260 *)={[95]=subject};
static void caller(struct260 *owner){dispatch[95](owner);}
static void initialize(void){u32 b,j,i,value;u8 *owner=bases[0]+16,*actor=bases[1]+16;const Field *f;invalid=0;callHash=observationHash=2166136261u;for(b=0;b<5;b++)for(j=0;j<sizes[b]+32;j++)bases[b][j]=(u8)(((s32)j-16)*29+(s32)v->field[0]*11+0x51);
putbe(owner+0x28,0x80000,4);owner[0x2c]=(u8)v->field[2];putbe(owner+0x30,v->field[10]?0x50000:0,4);owner[0x5c]=(u8)v->field[5];putbe(owner+14,123,2);
for(b=0;b<3;b++){u8 *a=bases[b]+16;putbe(a,0x13579bdf,4);a[0x3b]=17;a[0xad]=0;putbe(a+0x184,0xdeadbeef,4);if(b)putbe(a+0x28,0,4);}
putbe(owner+0x28,0x80000,4);putbe(actor,v->field[1],4);actor[0x3b]=(u8)v->field[3];putbe(actor+0x28,v->field[7],4);actor[0xad]=(u8)v->field[8];putbe(actor+0x184,v->field[9],4);for(i=0;i<3;i++){f32 x=(f32)((s32)((v->field[0]+3*i)%29)-14)*0.25f;putbe(owner+0x40+4*i,word(&x),4);}putbe(owner+0x58,0x42480000,4);
for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];value=be(bases[f->bank]+16+f->offset,f->size);if(f->pointer)value=native(value);if(f->size==4)putword(bases[f->bank]+16+f->offset,value);else{u8 *a=bases[f->bank]+16+f->offset;a[0]=(u8)value;a[1]=(u8)(value>>8);}}
}
static int run(void){u32 n;for(n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){v=&vectors[n];initialize();caller(&ownerBox.value);if(invalid)return 10;if(public_hash()!=v->field[14])return 11;if(callHash!=v->field[15])return 12;if(observationHash!=v->field[16])return 13;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text

def main():
 count,excluded=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-Wno-missing-braces',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,all_backing_and_guard_bytes_compared=True,pointer_and_endian_normalized=True,real_delta_float_array=True,opaque_owner_table_parameter_checked=True,explicit_static_assertions=source.count('_Static_assert('))
 controls={'wrong-callback-index':('[link->selector]','[link->selector ^ 1]'),'wrong-previous-capture':('link->previous = link->position;','link->position = link->previous;'),'missing-failure-restore':('link->position = link->previous;','link->position = link->position;'),'wrong-delta-y':('link->position.y - link->previous.y','link->position.y + link->previous.y'),'wrong-300-boundary':('link->distance > 300.0f','link->distance >= 300.0f'),'wrong-zero-boundary':('link->distance <= 0.0f','link->distance < 0.0f'),'wrong-classifier-gate':('kind == 14','kind == 12'),'late-actor-recapture':('        kind = func_1510F8CC(','        actor = link->actor;\n        kind = func_1510F8CC(')}
 rejected=[]
 for label,(old,new)in controls.items():
  assert old in source,label;q=run('control-'+label,source.replace(old,new),'-O2');assert q.returncode!=0,(label,'Ineffective result comparison');rejected.append(label)
 cached=source.replace('    u32 kind;','    u32 kind;\n    f32 cachedDistance;').replace('        kind = func_1510F8CC(','        cachedDistance = link->distance;\n        kind = func_1510F8CC(').replace('if (link->distance > 300.0f || link->distance <= 0.0f ||','if (cachedDistance > 300.0f || cachedDistance <= 0.0f ||');q=run('control-stale-distance',cached,'-O2');assert q.returncode!=0;rejected.append('stale-distance')
 q=dict(profiles=profiles,effective_source_controls=rejected,excluded_guest_only_cases=excluded,signaling_NaN_return_bit_identity_claim=False,full_original_C_dispatcher_execution_claim=False,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
