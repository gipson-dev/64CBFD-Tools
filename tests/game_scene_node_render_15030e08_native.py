"""SDK32 execution on typed node/actor backing with pointer/endian normalization."""
import hashlib,json,subprocess
from tools.experiments import game_scene_node_render_15030e08_match as p
from tools.tests import game_scene_node_render_15030e08_guest as g
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
def flatten(v):
 if isinstance(v,(tuple,list)):
  for item in v:yield from flatten(item)
 else:yield v
def observations_hash(rows):
 h=2166136261
 for v in flatten(rows):h=mix(h,v)
 return h
FIELDS=[*((0,0x240*i+0x54,1)for i in range(4)),*((1,0x240*i+0x1d4,0)for i in range(4)),(3,0,0),(4,0,1)]
def vectors():
 rows=[];excluded=0
 for c in g.cases():
  if c.alias==2:excluded+=1;continue
  m,service,cursor=g.reference(g.fixture(c),c);values=[getattr(c,n)for n in c.__dataclass_fields__]+[public_hash(m),calls_hash(service.calls),observations_hash(service.observed),cursor];assert len(values)==13;rows.append('{{'+','.join(str(v&0xffffffff)+'u'for v in values)+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded
def program():
 text='#include <ultra64.h>\n'+r'''
typedef struct {u8 prefix[0x54];u8 *next;u8 tail[0x1e8];} Node;
typedef struct {u8 prefix[0x1d4];u32 active;u8 tail[0x68];} Actor;
typedef struct {u8 before[16];Node values[4];u8 after[16];} NodeBox;
typedef struct {u8 before[16];Actor values[4];u8 after[16];} ActorBox;
typedef struct {u8 before[16];Gfx values[64];u8 after[16];} CursorBox;
typedef struct {u8 before[16];u32 value;u8 tail[28],after[16];} MarkBox;
typedef struct {u8 before[16];u8 *value;u8 after[16];} PointerBox;
typedef struct {u32 f[13];} Vector;
#include "native-vectors.h"
typedef struct {u32 bank,offset,pointer;} Field;
static NodeBox nodeBox;static ActorBox actorBox;static CursorBox cursorBox;static MarkBox markBox;static PointerBox headBox;
#define D_800C3EE0 headBox.value
static u8 *const bases[5]={(u8*)&nodeBox,(u8*)&actorBox,(u8*)&cursorBox,(u8*)&markBox,(u8*)&headBox};
static const u32 sizes[5]={2304,2304,512,32,4},addresses[5]={ADDRESS_VALUES};
static const Field fields[]={FIELD_VALUES};
static const Vector *v;static u32 callHash,observationHash,invalid,calls,current;
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(long)==4&&sizeof(Gfx)==8&&__CHAR_BIT__==8&&(s32)0xffffffffu==-1,"SDK32");
_Static_assert(sizeof(Node)==0x240&&sizeof(Actor)==0x240&&OFF(Node,next)==0x54&&OFF(Actor,active)==0x1d4,"typed fields");
_Static_assert(OFF(NodeBox,values)==16&&OFF(ActorBox,values)==16&&OFF(CursorBox,values)==16&&OFF(MarkBox,value)==16&&OFF(PointerBox,value)==16,"guard boxes");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"word codec");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static void putword(void *p,u32 x){__builtin_memcpy(p,&x,4);}
static u32 be(const void *p){const u8 *b=p;return((u32)b[0]<<24)|((u32)b[1]<<16)|((u32)b[2]<<8)|b[3];}
static void putbe(void *p,u32 x){u8 *b=p;u32 i;for(i=0;i<4;i++)b[i]=(u8)(x>>(8*(3-i)));}
static u32 logical(u32 x){u32 b,start;if(!x)return 0;for(b=0;b<5;b++){start=(u32)(bases[b]+16);if(x>=start&&x<start+sizes[b])return addresses[b]+x-start;}invalid=1;return 0xffffffffu;}
static u32 native(u32 x){u32 b;if(!x)return 0;for(b=0;b<5;b++)if(x>=addresses[b]&&x<addresses[b]+sizes[b])return(u32)(bases[b]+16+x-addresses[b]);invalid=1;return 0;}
static u8 *node(u32 i){return(u8*)&nodeBox.values[i];}
static u8 *actor(u32 i){return(u8*)&actorBox.values[v->f[7]==1?0:i];}
static u32 canonical(u32 bank,s32 at){u32 i,x;const Field *f;for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];if(f->bank!=bank||at<(s32)f->offset||at>=(s32)(f->offset+4))continue;x=word(bases[bank]+16+f->offset);if(f->pointer)x=logical(x);return(x>>(8*(3-(at-(s32)f->offset))))&255;}return bases[bank][at+16];}
static u32 publicHash(void){u32 h=2166136261u,b;s32 i;for(b=0;b<5;b++)for(i=-16;i<(s32)sizes[b]+16;i++)h=mix(h,canonical(b,i));return h;}
static void observe(void){u32 i;observationHash=mix(observationHash,logical((u32)D_800C3EE0));for(i=0;i<4;i++){observationHash=mix(observationHash,node(i)[3]);observationHash=mix(observationHash,node(i)[4]);observationHash=mix(observationHash,logical((u32)nodeBox.values[i].next));}for(i=0;i<4;i++){observationHash=mix(observationHash,actorBox.values[i].active);observationHash=mix(observationHash,((u8*)&actorBox.values[i])[0x74]);observationHash=mix(observationHash,((u8*)&actorBox.values[i])[5]);}observationHash=mix(observationHash,markBox.value);}
static void logCall(u32 t,u32 n,const u32 *a){u32 i;calls++;callHash=mix(callHash,t);callHash=mix(callHash,n);for(i=0;i<n;i++)callHash=mix(callHash,a[i]);observe();markBox.value=calls;}
u8 *func_15083E90(s32 id){u32 a[1]={(u32)id},i;u8 *answer;logCall(@GETTER@,1,a);if(id<1||id>4){invalid=1;return 0;}current=i=(u32)id-1;answer=v->f[6]==2&&i==0?0:actor(i);if(v->f[5]&1){D_800C3EE0=0;nodeBox.values[i].next=0;}if(v->f[5]&2){((Actor*)actor(i))->active=(i+1)&1;actor(i)[0x74]=(u8)(1u<<(v->f[2]&7));actor(i)[5]=(u8[]){1,7,6,255}[i];}return answer;}
s32 func_1506196C(u8 *owner,s32 view){u32 a[2]={logical((u32)owner),(u32)view},i=current;logCall(@FILTER@,2,a);if(owner!=actor(i)||(u32)view!=v->f[2])invalid=1;if(v->f[5]&4){node(i)[4]^=2;actor(i)[5]=1;}if(v->f[5]&16){nodeBox.values[i].next=0;if(i+1<4){node(i+1)[3]=1;((Actor*)actor(i+1))->active=1;actor(i+1)[5]=7;}}return(s32)(v->f[6]==6?254:v->f[4]);}
s32 func_150311C4(Gfx *cursor,u8 *n,u8 *owner,s32 view,s32 zero){u32 a[5]={logical((u32)cursor),logical((u32)n),logical((u32)owner),(u32)view,(u32)zero},i=current,answer;logCall(@RENDER@,5,a);if(n!=node(i)||owner!=actor(i)||(u32)view!=v->f[2]||zero)invalid=1;answer=v->f[5]&32?0:(u32)cursor+8*(1+(calls+v->f[0])%3);if(v->f[5]&8){D_800C3EE0=node(3);nodeBox.values[i].next=0;if(i+1<4)node(i+1)[3]=0;}return(s32)answer;}
'''
 text=text.replace('ADDRESS_VALUES',','.join(hex(a)+'u'for a,n in g.banks())).replace('FIELD_VALUES',','.join('{'+','.join(map(str,f))+'}'for f in FIELDS))
 for token,name in(('GETTER','func_15083E90'),('FILTER','func_1506196C'),('RENDER','func_150311C4')):text=text.replace('@'+token+'@',hex(g.S[name])+'u')
 text+=p.MANIFEST['body'].replace('func_15030E08(','subject(')+r'''
static void initialize(void){u32 b,j,i,x;const Field *f;invalid=calls=current=0;callHash=observationHash=2166136261u;for(b=0;b<5;b++)for(j=0;j<sizes[b]+32;j++)bases[b][j]=(u8)(((s32)j-16)*29+(s32)v->f[0]*11+0x51);putbe(bases[4]+16,v->f[1]?0x30000:0);for(i=0;i<4;i++){putbe(bases[1]+16+(v->f[7]==1?0:i)*0x240+0x1d4,1);actor(i)[0x74]=0;actor(i)[5]=7;}for(i=0;i<4;i++){node(i)[0]=(u8)(i+1);node(i)[3]=1;node(i)[4]=0;putbe(node(i)+0x54,i+1<v->f[1]?0x30000+(i+1)*0x240:0);}if(v->f[6]==1)node(0)[3]=0;if(v->f[6]==3)putbe(actor(0)+0x1d4,0);if(v->f[6]==4)actor(0)[0x74]=(u8)(1u<<(v->f[2]&31));if(v->f[6]==5)node(0)[4]=2;if(v->f[6]==7)actor(0)[5]=1;if(v->f[6]==8)actor(0)[5]=6;if(v->f[6]==9)node(0)[4]=4;if(v->f[6]==10)actor(0)[0x74]=1;for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++){f=&fields[i];x=be(bases[f->bank]+16+f->offset);if(f->pointer)x=native(x);putword(bases[f->bank]+16+f->offset,x);}}
static int run(void){u32 i;Gfx *result;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];initialize();result=subject(cursorBox.values+4,(s32)v->f[2],(s32)v->f[3]);if(invalid)return 10;if(publicHash()!=v->f[9])return 11;if(callHash!=v->f[10])return 12;if(observationHash!=v->f[11])return 13;if(logical((u32)result)!=v->f[12])return 14;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
def main():
 count,excluded=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_node_actor_and_global_fields=True,shared_actor_aliases=True,all_public_and_guard_bytes_compared=True,pointer_and_endian_normalized=True)
 body=p.MANIFEST['body'].replace('func_15030E08(','subject(')
 controls={'wrong-view-mask':('view & 31','view & 15'),'wrong-active-field':('actor + 0x1D4','actor + 0x1D0'),'wrong-special-state':('actor[5] != 7','actor[5] != 6'),'wrong-node-flag':('node[4] & 2','node[4] & 4'),'wrong-status-equality':('status == 255','status == 254'),'unsigned-status':('status < 255','(u32)status < 255'),'wrong-status-threshold':('status < 255','status < 256'),'wrong-render-view':('node, actor, view, 0','node, actor, mode, 0'),'lost-rendered-cursor':('cursor = (Gfx *)func_150311C4','(void)func_150311C4')};outcomes=[]
 for label,(old,new)in controls.items():
  assert old in body,label;q=run('control-'+label,source.replace(body,body.replace(old,new)),'-O2');assert q.returncode in(10,11,12,13,14),(label,q.returncode,'Control must reach a known result comparison');f=o/('control-'+label);outcomes.append(dict(control=label,comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 changed=body.replace('            node = next;\n        } while','            node = *(u8 **)(node + 0x54);\n        } while');assert changed!=body;q=run('control-late-next-link',source.replace(body,changed),'-O2');assert q.returncode in(10,11,12,13,14);f=o/'control-late-next-link';outcomes.append(dict(control='late-next-link',comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 q=dict(profiles=profiles,effective_source_controls=outcomes,excluded_node_actor_overlap_guest_only_cases=excluded,actual_complete_C_caller_execution_claim=False,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
