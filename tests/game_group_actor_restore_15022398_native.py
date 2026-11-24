"""SDK32 actor/record/descriptor backing, portable aliases and result controls."""
import hashlib,json,subprocess
from tools.experiments import game_group_actor_restore_15022398_match as p
from tools.tests import game_group_actor_restore_15022398_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def public_hash(m,c):
 h=2166136261
 for b,n in g.banks(c):
  for i in range(-16,n+16):h=mix(h,m[b+i])
 return h
def calls_hash(rows):
 h=2166136261
 for t,a in rows:
  for v in(t,len(a),*a):h=mix(h,v)
 return h
def observations_hash(rows):
 h=2166136261
 for row in rows:
  for v in row:h=mix(h,v)
 return h
def vectors():
 rows=[];excluded=0
 for c in g.cases():
  if c.alias in(1,3)or g.signed(c.key)<-1:excluded+=1;continue
  m,service=g.reference(g.fixture(c),c);values=[getattr(c,n)for n in c.__dataclass_fields__]+[public_hash(m,c),calls_hash(service.calls),observations_hash(service.observed)];assert len(values)==22;rows.append('{{'+','.join(str(v&0xffffffff)+'u'for v in values)+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded
def program():
 text='''#include <ultra64.h>
typedef struct {u8 prefix[5];u8 unk5;u8 pad06[0xee];s32 unkF4;u8 tail[0x234];} struct127;
typedef struct {u16 kind;u8 identity;u8 padding[5];} GroupRecord;
typedef struct {u8 bytes[0x30];} GroupSpawnDescriptor15022398;
typedef struct {u16 *active[2];u8 pad08[26];u8 enabled[2];u8 pad24[4];u8 *rows[2];} TableState;
typedef struct {GroupSpawnDescriptor15022398 *descriptors;u8 count[4];} DescriptorState;
typedef struct {u8 before[16];TableState value;u8 after[16];} TableBox;
typedef struct {u8 before[16];u8 value[4];u8 after[16];} CountBox;
typedef struct {u8 before[16];DescriptorState value;u8 after[16];} DescriptorStateBox;
typedef struct {u8 before[16];u16 value[8];u8 after[16];} ActiveBox;
typedef struct {u8 before[16];GroupRecord value[4];u8 after[16];} RowBox;
typedef struct {u8 before[16];GroupSpawnDescriptor15022398 value[256];u8 after[16];} DescriptorBox;
typedef struct {u8 before[16];struct127 value[26];u8 after[16];} ActorBox;
typedef struct {u8 before[16];u32 value[8];u8 after[16];} MarkBox;
typedef struct {u32 f[22];} Vector;
#include "native-vectors.h"
static TableBox tableBox;static CountBox countBox;static DescriptorStateBox descriptorStateBox;static ActiveBox activeBox;static RowBox rowA,rowB;static DescriptorBox descriptorA,descriptorB;static ActorBox actorBox;static MarkBox markBox;
#define D_800C35C8 tableBox.value.active
#define D_800C35F0 tableBox.value.rows
#define D_800D20FC descriptorStateBox.value.descriptors
#define D_800D2100 descriptorStateBox.value.count[0]
#define D_800CC2D0 actorBox.value
static const Vector *v;static u32 callHash,observationHash,calls,invalid,lookups;static struct127 *lastActor;
static u8 *bases[10];static const u32 sizes[10]={48,4,8,16,32,32,12288,12288,26*0x32c,32};
static const u32 addresses[10]={@TABLE@,@COUNTS@,@DESCRIPTOR@,0x30000,0x40000,0x50000,0x100000,0x110000,@ACTORS@,0x70000};
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(long)==4&&sizeof(f32)==4&&__CHAR_BIT__==8&&(s32)0xffffffffu==-1,"SDK32");
_Static_assert(sizeof(struct127)==0x32c&&OFF(struct127,unk5)==5&&OFF(struct127,unkF4)==0xf4,"actor layout");
_Static_assert(sizeof(GroupRecord)==8&&OFF(GroupRecord,identity)==2&&sizeof(GroupSpawnDescriptor15022398)==0x30,"record layouts");
_Static_assert(sizeof(TableState)==48&&OFF(TableState,enabled)==34&&OFF(TableState,rows)==40&&OFF(DescriptorState,count)==4&&sizeof(DescriptorState)==8,"global layouts");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static u32 be(const void *p){const u8 *b=p;return((u32)b[0]<<24)|((u32)b[1]<<16)|((u32)b[2]<<8)|b[3];}
static u16 half(const void *p){const u8 *b=p;return(u16)(((u32)b[0]<<8)|b[1]);}
static struct127 *actor(u32 result){return &actorBox.value[result==1?v->f[12]:(v->f[12]+1)%26];}
static GroupRecord *row(u32 group){return group==0||v->f[14]==2?rowA.value:rowB.value;}
static u32 logical(const void *p){u32 x=(u32)p,b,start;if(!p)return 0;for(b=0;b<10;b++){start=(u32)(bases[b]+16);if(x>=start&&x<start+sizes[b])return addresses[b]+x-start;}invalid=1;return 0xffffffffu;}
static u32 canonical(u32 bank,s32 at){u8 *start=bases[bank]+16;s32 off=at&~3;u32 x,pointer=0,wide=0;if(bank==0&&((at>=0&&at<8)||(at>=40&&at<48)))wide=pointer=1;if(bank==2&&at>=0&&at<4)wide=pointer=1;if(bank==9&&at>=0&&at<32)wide=1;if(bank==8&&at>=0&&at<(s32)sizes[bank]&&(at%0x32c)>=0xf4&&(at%0x32c)<0xf8)wide=1;if(wide){x=word(start+off);if(pointer)x=logical((void*)x);return(x>>(8*(3-(at-off))))&255;}if((bank==3&&at>=0&&at<16)||((bank==4||bank==5)&&at>=0&&at<32&&(at%8)<2)){u16 h;off=at&~1;__builtin_memcpy(&h,start+off,2);return(h>>(8*(1-(at-off))))&255;}return start[at];}
static u32 publicHash(void){u32 h=2166136261,b;s32 i;for(b=0;b<10;b++)for(i=-16;i<(s32)sizes[b]+16;i++)h=mix(h,canonical(b,i));return h;}
static void observe(void){u32 i;for(i=0;i<2;i++)observationHash=mix(observationHash,logical(D_800C35C8[i]));for(i=0;i<2;i++)observationHash=mix(observationHash,logical(D_800C35F0[i]));observationHash=mix(observationHash,logical(D_800D20FC));observationHash=mix(observationHash,D_800D2100);observationHash=mix(observationHash,countBox.value[0]);observationHash=mix(observationHash,countBox.value[2+v->f[2]]);observationHash=mix(observationHash,markBox.value[0]);for(i=1;i<=2;i++){observationHash=mix(observationHash,actor(i)->unk5);observationHash=mix(observationHash,(u32)actor(i)->unkF4);}}
static void logCall(u32 target,u32 n,const u32 *args){u32 i;calls++;callHash=mix(callHash,target);callHash=mix(callHash,n);for(i=0;i<n;i++)callHash=mix(callHash,args[i]);observe();markBox.value[0]=calls;}
s32 func_15083E0C(u8 identity){u32 a[1]={identity},g;logCall(@IDENTITY@,1,a);lookups=0;if(v->f[13]&1){for(g=0;g<2;g++){D_800C35F0[g]=(u8*)rowB.value;row(g)[v->f[1]].identity=255;}}return(s32)v->f[6];}
struct127 *func_1505EEF4(s32 key){u32 a[1]={(u32)key},result;logCall(@LOOKUP@,1,a);if((u32)key!=v->f[6])invalid=1;lookups++;result=lookups==1?v->f[7]:v->f[8];lastActor=result?actor(result):0;if(v->f[13]&2){D_800D2100=v->f[0]&1?255:0;D_800D20FC=descriptorB.value;if(lastActor){lastActor->unk5=3;lastActor->unkF4=(s32)0xaaaaaaaa;}}return lastActor;}
s32 func_15082A44(u8 *descriptor,s32 key,s32 zero,s32 group,s32 last){u32 a[5]={logical(descriptor),(u32)key,(u32)zero,(u32)group,(u32)last};u8 *expected=(u8*)&D_800D20FC[v->f[6]];logCall(@CONSTRUCT@,5,a);if(descriptor!=expected||(u32)key!=v->f[6]||zero||(u32)group!=v->f[2]||last)invalid=1;expected[2]^=1;if(v->f[13]&4){D_800D2100=0;D_800D20FC=descriptorA.value;D_800C35F0[v->f[2]]=(u8*)rowA.value;rowA.value[v->f[1]].identity=0;}return 0x12345678;}
void func_1505E650(struct127 *value,u16 mode,f32 a,f32 b,f32 c,f32 d,s32 flag){u32 args[7]={logical(value),mode,word(&a),word(&b),word(&c),word(&d),(u32)flag};logCall(@PHYSICS@,7,args);if(value!=lastActor)invalid=1;if(v->f[13]&8){lastActor->unk5=255;lastActor->unkF4=0x12345678;D_800C35F0[v->f[2]]=(u8*)rowB.value;}if(v->f[13]&32)lastActor=actor(2);}
void func_1502225C(s32 index,s32 group){u32 a[2]={(u32)index,(u32)group};logCall(@REGISTER@,2,a);markBox.value[1]=(u32)index;markBox.value[2]=(u32)group;if(v->f[13]&16){countBox.value[2+v->f[2]]=(u8)(v->f[16]<2?v->f[16]:2);D_800C35F0[v->f[2]]=(u8*)rowB.value;}}
'''
 for token,name in [('TABLE','D_800C35C8'),('COUNTS','D_800C3638'),('DESCRIPTOR','D_800D20FC'),('ACTORS','D_800CC2D0'),('IDENTITY',g.PROVIDERS[0]),('LOOKUP',g.PROVIDERS[1]),('CONSTRUCT',g.PROVIDERS[2]),('PHYSICS',g.PROVIDERS[3]),('REGISTER',g.PROVIDERS[4])]:text=text.replace('@'+token+'@',hex(g.S[name])+'u')
 text+=p.MANIFEST['body'].replace('func_15022398(','subject(')+r'''
static void initialize(void){u32 b,j,group;invalid=calls=lookups=0;lastActor=0;callHash=observationHash=2166136261u;bases[0]=(u8*)&tableBox;bases[1]=(u8*)&countBox;bases[2]=(u8*)&descriptorStateBox;bases[3]=(u8*)&activeBox;bases[4]=(u8*)&rowA;bases[5]=(u8*)&rowB;bases[6]=(u8*)&descriptorA;bases[7]=(u8*)&descriptorB;bases[8]=(u8*)&actorBox;bases[9]=(u8*)&markBox;for(b=0;b<10;b++)for(j=0;j<sizes[b]+32;j++)bases[b][j]=(u8)(((s32)j-16)*29+(s32)v->f[0]*11+0x51);for(j=0;j<26;j++)actorBox.value[j].unkF4=(s32)be(&actorBox.value[j].unkF4);for(j=0;j<8;j++)markBox.value[j]=be(markBox.value+j);for(j=0;j<4;j++){rowA.value[j].kind=half(&rowA.value[j].kind);rowB.value[j].kind=half(&rowB.value[j].kind);}for(j=1;j<=2;j++){actor(j)->unk5=(u8)v->f[9];actor(j)->unkF4=(s32)v->f[10];}for(group=0;group<2;group++){D_800C35C8[group]=activeBox.value+group*4;D_800C35F0[group]=(u8*)row(group);tableBox.value.enabled[group]=(u8)v->f[17];countBox.value[2+group]=(u8)v->f[16];for(j=0;j<4;j++){D_800C35C8[group][j]=(u16)v->f[3];row(group)[j].kind=(u16)v->f[4];row(group)[j].identity=(u8)v->f[5];}}D_800D20FC=descriptorA.value;D_800D2100=(u8)v->f[11];}
static int run(void){u32 i;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];initialize();subject((s32)v->f[1],(s32)v->f[2]);if(invalid)return 10;if(publicHash()!=v->f[19])return 11;if(callHash!=v->f[20])return 12;if(observationHash!=v->f[21])return 13;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
def main():
 count,excluded=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_actors_records_and_descriptor_arrays=True,shared_record_rows=True,all_public_and_guard_bytes_compared=True,pointer_and_endian_normalized=True)
 body=p.MANIFEST['body'].replace('func_15022398(','subject(');controls={'reversed-enabled':('D_800C35C8[group][index] == 0','D_800C35C8[group][index] != 0'),'wrong-kind':('!= 2) return;','!= 1) return;'),'wrong-identity':('index * 8 + 2','index * 8 + 3'),'wrong-key-rejection':('key == -1','key == 0'),'wrong-actor-state':('actor->unk5 == 3','actor->unk5 == 2'),'wrong-table-identity':('records != D_800C35F0','*records != *D_800C35F0'),'wrong-group-state':('actor->unk5 = 4','actor->unk5 = 5'),'wrong-flags':('~0x2A','~0x28'),'inclusive-count':('key < D_800D2100','key <= D_800D2100'),'wrong-constructor-group':('key, 0, group, 0','key, 0, group ^ 1, 0'),'wrong-physics-mode':('0.0f, 0.0f, 1','0.0f, 0.0f, 0'),'wrong-pool-stride':('(s32)sizeof(struct127)','((s32)sizeof(struct127) - 64)'),'wrong-list-group':('sizeof(struct127), group','sizeof(struct127), group ^ 1')};outcomes=[]
 for label,(old,new)in controls.items():
  assert old in body,label;q=run('control-'+label,source.replace(body,body.replace(old,new)),'-O2');assert q.returncode in(10,11,12,13),(label,q.returncode,'Control must reach a known comparison');f=o/('control-'+label);outcomes.append(dict(control=label,comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 # The captured identity must survive an aliased public row change by a helper.
 changed=body.replace('if (identity == 1)','if ((*records)[(u32)index * 8 + 2] == 1)');assert changed!=body;q=run('control-live-identity',source.replace(body,changed),'-O2');assert q.returncode in(10,11,12,13);f=o/'control-live-identity';outcomes.append(dict(control='live-identity',comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 q=dict(profiles=profiles,effective_source_controls=outcomes,excluded_mixed_type_row_actor_alias_or_modular_negative_descriptor_cases_guest_only=excluded,void_result_not_compared=True,source_installed=p.installed(),matching_credit=0,whole_caller_or_transitive_provider_execution_claim=False);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
