"""SDK32 C, typed public backing, endian/pointer codecs and known comparison controls."""
import hashlib,json,subprocess
from tools.experiments import game_actor_state_motion_150b12fc_match as p
from tools.tests import game_actor_state_motion_150b12fc_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def public_hash(m):
 h=2166136261
 for base,n in g.banks():
  for i in range(-16,n+16):h=mix(h,m[base+i])
 return h
def calls_hash(calls):
 h=2166136261
 for t,a in calls:
  for v in(t,len(a),*a):h=mix(h,v)
 return h
def observations_hash(rows):
 h=2166136261
 for row in rows:
  for v in row:h=mix(h,v)
 return h
FIELDS=[(0,0,4,0),(0,0x40,4,0),(0,0x76,2,0),(0,0x7a,2,0),(0,0xc4,4,0),(0,0x148,4,0),*((1,4*i,4,1)for i in range(256)),*((2,2*i,2,0)for i in range(512)),(3,0,4,0),(4,0,4,0),(4,4,4,0),(5,0,4,1)]
def vectors():
 rows=[];excluded=dict(public_alias_cases=0,nonfinite_float_cases=0)
 for c in g.cases():
  if c.alias:excluded['public_alias_cases']+=1;continue
  if any(x&0x7f800000==0x7f800000 for x in(c.velocity,c.smooth,c.factor)):excluded['nonfinite_float_cases']+=1;continue
  m,service=g.reference(g.fixture(c),c);values=[getattr(c,n)for n in c.__dataclass_fields__]+[public_hash(m),calls_hash(service.calls),observations_hash(service.observed)];assert len(values)==16;rows.append('{{'+','.join(str(v&0xffffffff)+'u'for v in values)+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded
def program():
 declarations=p.MANIFEST['declarations'].replace('#include "structs.h"\n','').replace('extern s32 *D_800D2104;\n','').replace('extern f32 D_8009F8BC, D_8009F8C0;\n','')
 text='#include <ultra64.h>\n'+r'''
typedef struct {s32 kind;u8 pad04[60];f32 unk40;u8 pad44[50];u16 unk76;u8 pad78[2];u16 unk7A;u8 pad7c[4],unk80,pad81[67];f32 unkC4;u8 padc8[119],unk13F,pad140[8];f32 unk148;u8 tail[372];} struct127;
'''+declarations+r'''
typedef struct {u32 f[16];} Vector;
#include "native-vectors.h"
typedef struct {u8 before[16];struct127 actor;u8 after[16];} OwnerBox;
typedef struct {u8 before[16];s32 values[256];u8 after[16];} TableBox;
typedef struct {u8 before[16];s16 values[256][2];u8 after[16];} RowBox;
typedef struct {u8 before[16];u32 value;u8 tail[28],after[16];} MarkBox;
typedef struct {u8 before[16];f32 value[2];u8 after[16];} FloatBox;
typedef struct {u8 before[16];s32 *value;u8 after[16];} PointerBox;
typedef struct {u32 bank,offset,size,pointer;} Field;
static OwnerBox ownerBox;static TableBox tableBox;static RowBox rowBox;static MarkBox markBox;static FloatBox floatBox;static PointerBox pointerBox;
#define D_800D2104 pointerBox.value
#define D_8009F8BC floatBox.value[0]
#define D_8009F8C0 floatBox.value[1]
static u8 *const bases[6]={(u8*)&ownerBox,(u8*)&tableBox,(u8*)&rowBox,(u8*)&markBox,(u8*)&floatBox,(u8*)&pointerBox};
static const u32 sizes[6]={704,1024,1024,32,8,4},addresses[6]={ADDRESS_VALUES};
static const Field fields[]={FIELD_VALUES};
static const Vector *v;static u32 callHash,observationHash,invalid,calls;
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(long)==4&&sizeof(f32)==4&&__CHAR_BIT__==8&&(s32)0xffffffffu==-1,"SDK32");
_Static_assert(sizeof(struct127)==704&&OFF(struct127,unk40)==0x40&&OFF(struct127,unk76)==0x76&&OFF(struct127,unk7A)==0x7a&&OFF(struct127,unk80)==0x80&&OFF(struct127,unkC4)==0xc4&&OFF(struct127,unk13F)==0x13f&&OFF(struct127,unk148)==0x148,"typed actor fields");
_Static_assert(OFF(OwnerBox,actor)==16&&OFF(TableBox,values)==16&&OFF(RowBox,values)==16&&OFF(MarkBox,value)==16&&OFF(FloatBox,value)==16&&OFF(PointerBox,value)==16,"guard boxes");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"word codec");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static u32 half(const void *p){u16 x;__builtin_memcpy(&x,p,2);return x;}
static void putword(void *p,u32 x){__builtin_memcpy(p,&x,4);}
static u32 be(const void *p,u32 n){const u8 *b=p;u32 i,x=0;for(i=0;i<n;i++)x=(x<<8)|b[i];return x;}
static void putbe(void *p,u32 x,u32 n){u8 *b=p;u32 i;for(i=0;i<n;i++)b[i]=(u8)(x>>(8*(n-1-i)));}
static u32 logical(u32 x){u32 b,start;if(!x)return 0;for(b=0;b<6;b++){start=(u32)(bases[b]+16);if(x>=start&&x<start+sizes[b])return addresses[b]+x-start;}invalid=1;return 0xffffffffu;}
static u32 native(u32 x){u32 b;if(!x)return 0;for(b=0;b<6;b++)if(x>=addresses[b]&&x<addresses[b]+sizes[b])return(u32)(bases[b]+16+x-addresses[b]);invalid=1;return 0;}
static u32 canonical(u32 bank,s32 at){u32 i,x;const Field *f;const u8 *b=bases[bank]+16;for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];if(f->bank!=bank||at<(s32)f->offset||at>=(s32)(f->offset+f->size))continue;x=f->size==4?word(b+f->offset):half(b+f->offset);if(f->pointer)x=logical(x);return(x>>(8*(f->size-1-(at-(s32)f->offset))))&255;}return bases[bank][at+16];}
static u32 publicHash(void){u32 h=2166136261u,b;s32 i;for(b=0;b<6;b++)for(i=-16;i<(s32)sizes[b]+16;i++)h=mix(h,canonical(b,i));return h;}
static void observe(void){u32 data[10]={word(&ownerBox.actor.unk40),word(&ownerBox.actor.unkC4),word(&ownerBox.actor.unk148),ownerBox.actor.unk76,ownerBox.actor.unk7A,ownerBox.actor.unk80,ownerBox.actor.unk13F,word(&D_8009F8BC),word(&D_8009F8C0),logical((u32)D_800D2104)},i;for(i=0;i<10;i++)observationHash=mix(observationHash,data[i]);}
static void logCall(u32 target,u32 count,const u32 *a){u32 i;calls++;callHash=mix(callHash,target);callHash=mix(callHash,count);for(i=0;i<count;i++)callHash=mix(callHash,a[i]);observe();markBox.value=calls;}
void func_15058EA4(struct127 *actor,f32 height,f32 scale,f32 second,f32 gravity,f32 maximum,f32 minimum){u32 a[7]={logical((u32)actor),word(&height),word(&scale),word(&second),word(&gravity),word(&maximum),word(&minimum)};logCall(@FIRST@,7,a);if(actor!=&ownerBox.actor)invalid=1;if(v->f[10]&1){actor->unk76=(u16)(v->f[2]^0x8000);actor->unkC4=-4.0f;actor->unk148=2.0f;D_8009F8C0=0.5f;}if(v->f[10]&4){D_800D2104=0;actor->unk13F^=0x55;rowBox.values[v->f[8]][1]=(s16)0x8000;}}
s32 func_15056B08(s32 actorWord){struct127 *actor=(struct127*)actorWord;u32 a[1]={logical((u32)actor)};logCall(@SECOND@,1,a);if(actor!=&ownerBox.actor)invalid=1;if(v->f[10]&2){actor->unk76=(u16)v->f[2];putword(&actor->unkC4,v->f[4]);putword(&actor->unk148,v->f[5]);actor->unk7A=(u16)v->f[7];}if(v->f[10]&8){D_800D2104=tableBox.values;putword(&D_8009F8C0,v->f[6]);}return(s32)0xdeadbeef;}
void func_15059140(struct127 *actor){u32 a[1]={logical((u32)actor)};logCall(@THIRD@,1,a);if(actor!=&ownerBox.actor)invalid=1;if(v->f[10]&16){actor->kind=0;actor->unkC4=-2.0f;actor->unk148=3.0f;actor->unk40=4.0f;}}
s32 func_150535F4(struct127 *actor){u32 a[1]={logical((u32)actor)};logCall(@PRED@,1,a);if(actor!=&ownerBox.actor)invalid=1;if(v->f[10]&32){actor->unk80^=0x80;actor->unkC4=7.0f;D_8009F8C0=0.25f;}return(s32)v->f[9];}
s32 func_1502178C(struct127 *actor,s32 mode,s32 selector){u32 a[3]={logical((u32)actor),(u32)mode,(u32)selector};logCall(@FINAL@,3,a);if(actor!=&ownerBox.actor)invalid=1;actor->unk80++;return(s32)0xdeadbeef;}
'''
 text=text.replace('ADDRESS_VALUES',','.join(hex(a)+'u'for a,n in g.banks())).replace('FIELD_VALUES',','.join('{'+','.join(map(str,f))+'}'for f in FIELDS))
 for token,name in(('FIRST','func_15058EA4'),('SECOND','func_15056B08'),('THIRD','func_15059140'),('PRED','func_150535F4'),('FINAL','func_1502178C')):text=text.replace('@'+token+'@',hex(g.S[name])+'u')
 text+=p.MANIFEST['body'].replace('func_150B12FC(','subject(')+r'''
static void (*const dispatch[8])(struct127 *)={[7]=subject};
static void initialize(void){u32 b,j,i,x;u8 *owner=bases[0]+16;const Field *f;invalid=calls=0;callHash=observationHash=2166136261u;for(b=0;b<6;b++)for(j=0;j<sizes[b]+32;j++)bases[b][j]=(u8)(((s32)j-16)*29+(s32)v->f[0]*11+0x51);for(i=0;i<256;i++)putbe(bases[1]+16+4*i,0x80000+4*i,4);putbe(bases[5]+16,0x50000,4);putbe(bases[4]+16,0xbf333333,4);putbe(bases[4]+20,v->f[6],4);putbe(owner,7,4);putbe(owner+0x76,v->f[1],2);putbe(owner+0x7a,v->f[7],2);owner[0x13f]=(u8)v->f[8];putbe(owner+0xc4,v->f[4],4);putbe(owner+0x148,v->f[5],4);putbe(owner+0x40,0x419c0000,4);putbe(bases[2]+16+4*v->f[8]+2,v->f[3],2);for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];x=be(bases[f->bank]+16+f->offset,f->size);if(f->pointer)x=native(x);if(f->size==4)putword(bases[f->bank]+16+f->offset,x);else{u16 h=(u16)x;__builtin_memcpy(bases[f->bank]+16+f->offset,&h,2);}}}
static int run(void){u32 i;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];initialize();dispatch[7](&ownerBox.actor);if(invalid)return 10;if(publicHash()!=v->f[13])return 11;if(callHash!=v->f[14])return 12;if(observationHash!=v->f[15])return 13;if(calls!=(v->f[9]?4u:5u))return 14;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
def main():
 count,excluded=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_actor_table_rows_and_globals=True,all_public_and_guard_bytes_compared=True,pointer_and_endian_normalized=True)
 body=p.MANIFEST['body'].replace('func_150B12FC(','subject(');controls={'wrong-counter':('actor->unk80 = 10;','actor->unk80 = 9;'),'unsigned-row-height':('((s16 *)D_800D2104','((u16 *)D_800D2104'),'wrong-wrap-width':('s16 angleChange;','s32 angleChange;'),'wrong-angle-scale':('(oldAngle - actor->unk76) * 6','(oldAngle - actor->unk76) * 5'),'wrong-correction-sign':(' - previous;',' + previous;'),'wrong-upper-bound':('6.0f) correction = 6.0f','5.0f) correction = 5.0f'),'stale-global-coefficient':('* D_8009F8C0;','* 0.05f;'),'wrong-facing-offset':('actor->unk7A + 0x4000','actor->unk7A + 0x2000'),'wrong-final-predicate':('if (!func_150535F4(actor))','if (func_150535F4(actor))')};outcomes=[]
 for label,(old,new)in controls.items():
  assert old in body,label;q=run('control-'+label,source.replace(body,body.replace(old,new)),'-O2');assert q.returncode in(10,11,12,13,14),(label,q.returncode,'Control must reach a known result comparison');f=o/('control-'+label);outcomes.append(dict(control=label,comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 stale=body.replace('    oldAngle = (s16)actor->unk76;\n','').replace('    func_15056B08((s32)actor);','    func_15056B08((s32)actor);\n    oldAngle = (s16)actor->unk76;');q=run('control-late-angle-capture',source.replace(body,stale),'-O2');assert q.returncode in(10,11,12,13,14);f=o/'control-late-angle-capture';outcomes.append(dict(control='late-angle-capture',comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 q=dict(profiles=profiles,effective_source_controls=outcomes,excluded_guest_only_cases=excluded,native_NaN_payload_or_public_alias_identity_claim=False,actual_complete_C_caller_execution_claim=False,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
