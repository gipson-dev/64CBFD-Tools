"""SDK32 integer decoder on typed backing with public aliases and guard checks."""
import hashlib,json,subprocess
from tools.experiments import game_actor_command_1506e46c_match as p
from tools.tests import game_actor_command_1506e46c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def mix(h,v):return((h^(v&0xffffffff))*16777619)&0xffffffff
def public_hash(m,c):
 h=2166136261
 for base,n in g.banks(c):
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
def vectors():
 rows=[];excluded=0
 for c in g.cases():
  if c.alias==2:excluded+=1;continue
  m,service,result=g.reference(g.fixture(c),c);values=[getattr(c,n)for n in c.__dataclass_fields__]+[public_hash(m,c),calls_hash(service.calls),observations_hash(service.observed),result];assert len(values)==16;rows.append('{{'+','.join(str(v&0xffffffff)+'u'for v in values)+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows),excluded
def program():
 text='#include <ultra64.h>\n'+r'''
typedef struct {u8 prefix[0x284];u32 command;u8 selector,tail[55];} struct127;
typedef struct {u8 before[16];struct127 value;u8 after[16];} ActorBox;
typedef struct {u8 before[16];u32 value[4];u8 after[16];} CommandBox;
typedef struct {u8 before[16];u32 value[8];u8 after[16];} MarkBox;
typedef struct {u8 before[16];u32 *value[256];u8 after[16];} TableBox;
typedef struct {u8 before[16];u32 value[32768];u8 after[16];} RowBox;
typedef struct {u32 f[16];} Vector;
#include "native-vectors.h"
static ActorBox actorBox;static CommandBox commandBox;static MarkBox markBox;static TableBox tableBox;static RowBox rowA,rowB;
#define D_800BE5A8 tableBox.value
static const Vector *v;static u32 callHash,observationHash,calls,invalid,index;
static const u32 sizes[6]={704,16,32,1024,4,4};
static u8 *bases[6];static u32 addresses[6];
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(long)==4&&__CHAR_BIT__==8&&(s32)0xffffffffu==-1,"SDK32");
_Static_assert(sizeof(struct127)==704&&OFF(struct127,command)==0x284&&OFF(struct127,selector)==0x288,"typed actor fields");
_Static_assert(OFF(ActorBox,value)==16&&OFF(CommandBox,value)==16&&OFF(MarkBox,value)==16&&OFF(TableBox,value)==16&&OFF(RowBox,value)==16,"guard boxes");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"word codec");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static void putword(void *p,u32 x){__builtin_memcpy(p,&x,4);}
static u32 be(const void *p){const u8 *b=p;return((u32)b[0]<<24)|((u32)b[1]<<16)|((u32)b[2]<<8)|b[3];}
static void putbe(void *p,u32 x){u8 *b=p;u32 i;for(i=0;i<4;i++)b[i]=(u8)(x>>(8*(3-i)));}
static u32 logical(u32 x){u32 b,start;if(!x)return 0;start=(u32)rowA.value;if(x>=start&&x<start+sizeof(rowA.value))return 0x100000u+x-start;start=(u32)rowB.value;if(x>=start&&x<start+sizeof(rowB.value))return 0x140000u+x-start;for(b=0;b<4;b++){start=(u32)(bases[b]+16);if(x>=start&&x<start+sizes[b])return addresses[b]+x-start;}invalid=1;return 0xffffffffu;}
static u32 commandPointer(void){if(v->f[8]==1)return(u32)&actorBox.value.command;if(v->f[8]==3)return(u32)&rowA.value[index];if(v->f[8]==4)return(u32)&markBox.value[0];return(u32)&commandBox.value[0];}
static u32 canonical(u32 bank,s32 at){s32 offset=0;u32 x,pointer=0,typed=0;u8 *start=bases[bank]+16;if(bank==0&&at>=0x284&&at<0x288){offset=0x284;typed=1;}if(bank>=1&&bank<=3&&at>=0&&at<(s32)sizes[bank]){offset=at&~3;typed=1;pointer=bank==3;}if(bank>=4){s32 physical=(s32)(index*4)+at;if(physical>=0&&physical<(s32)sizeof(rowA.value)){offset=at&~3;typed=1;}}if(!typed)return start[at];x=word(start+offset);if(pointer)x=logical(x);return(x>>(8*(3-(at-offset))))&255;}
static u32 publicHash(void){u32 h=2166136261u,b;s32 i;for(b=0;b<6;b++)for(i=-16;i<(s32)sizes[b]+16;i++)h=mix(h,canonical(b,i));return h;}
static void observe(void){u32 values[7]={word((void*)commandPointer()),actorBox.value.selector,logical((u32)D_800BE5A8[actorBox.value.selector]),rowA.value[index],rowB.value[index],markBox.value[0],actorBox.value.command},i;for(i=0;i<7;i++)observationHash=mix(observationHash,values[i]);}
static void logCall(u32 target,u32 count,const u32 *args){u32 i;calls++;callHash=mix(callHash,target);callHash=mix(callHash,count);for(i=0;i<count;i++)callHash=mix(callHash,args[i]);observe();markBox.value[0]=calls;}
static s32 gate(u32 target,struct127 *actor,u32 hasActor){u32 args[1]={hasActor?logical((u32)actor):0};logCall(target,hasActor,args);if(hasActor&&actor!=&actorBox.value)invalid=1;if(v->f[7]&1){putword((void*)commandPointer(),0x12345678);actorBox.value.selector=(u8)(v->f[9]+1);}if(v->f[7]&2)rowA.value[index]=rowB.value[index]=0;if(v->f[7]&16)D_800BE5A8[actorBox.value.selector]=rowB.value;return(s32)v->f[3];}
s32 func_100107F8(struct127 *actor){return gate(@FIRST@,actor,1);}
s32 func_10010894(struct127 *actor){return gate(@SECOND@,actor,1);}
s32 func_151F2CDC(void){return gate(@STATE@,0,0);}
s32 func_150ADA20(void){logCall(@RANDOM@,0,0);if(v->f[7]&4){putword((void*)commandPointer(),0x01234567);actorBox.value.selector^=0x80;}if(v->f[7]&32){rowA.value[index+1]=0x13579bdf;if(index)rowB.value[index-1]=0xfedcba98;else putbe(rowB.before+12,0xfedcba98);}return(s32)v->f[5];}
s32 func_1000F568(s32 value,u32 count){u32 args[2]={(u32)value,count};logCall(@CHOICE@,2,args);if(v->f[7]&8){putword((void*)commandPointer(),0x89abcdef);actorBox.value.selector^=0x80;D_800BE5A8[actorBox.value.selector]=rowA.value;}return(s32)v->f[6];}
'''
 for token,name in(('FIRST','func_100107F8'),('SECOND','func_10010894'),('STATE','func_151F2CDC'),('RANDOM','func_150ADA20'),('CHOICE','func_1000F568')):text=text.replace('@'+token+'@',hex(g.S[name])+'u')
 text+=p.MANIFEST['body'].replace('func_1506E46C(','subject(')+r'''
static void initialize(void){u32 b,j,i;u8 *bytes;index=(v->f[1]&0x7fff)>=2000?(v->f[1]&0x7fff)-2000:0;invalid=calls=0;callHash=observationHash=2166136261u;bases[0]=(u8*)&actorBox;bases[1]=(u8*)&commandBox;bases[2]=(u8*)&markBox;bases[3]=(u8*)&tableBox;bases[4]=(u8*)&rowA+4*index;bases[5]=(u8*)&rowB+4*index;addresses[0]=0x30000;addresses[1]=0x50000;addresses[2]=0x70000;addresses[3]=@TABLE@;addresses[4]=0x100000+4*index;addresses[5]=0x140000+4*index;for(b=0;b<4;b++)for(j=0;j<sizes[b]+32;j++)bases[b][j]=(u8)(((s32)j-16)*29+(s32)v->f[0]*11+0x51);for(b=0;b<2;b++){bytes=(u8*)(b?&rowB:&rowA);for(j=0;j<sizeof(RowBox);j++)bytes[j]=(u8)(((s32)j-16-(s32)(4*index))*29+(s32)v->f[0]*11+0x51);}for(i=0;i<256;i++)D_800BE5A8[i]=rowA.value;D_800BE5A8[(v->f[9]+1)&255]=rowB.value;actorBox.value.selector=(u8)v->f[9];putbe(&rowA.value[index],v->f[4]);putbe(&rowB.value[index],v->f[4]^0x10000001u);putbe((void*)commandPointer(),v->f[1]);actorBox.value.command=be(&actorBox.value.command);for(i=0;i<4;i++)commandBox.value[i]=be(&commandBox.value[i]);for(i=0;i<8;i++)markBox.value[i]=be(&markBox.value[i]);for(i=index>=4?index-4:0;i<=index+4;i++){rowA.value[i]=be(&rowA.value[i]);rowB.value[i]=be(&rowB.value[i]);}}
static u32 rowCanaries(void){u32 b,j;u8 *bytes;u8 expected;u32 begin=4*index,end=begin+36;for(b=0;b<2;b++){bytes=(u8*)(b?&rowB:&rowA);for(j=0;j<sizeof(RowBox);j++){if(j>=begin&&j<end)continue;expected=(u8)(((s32)j-16-(s32)(4*index))*29+(s32)v->f[0]*11+0x51);if(bytes[j]!=expected)return 0;}}return 1;}
static int run(void){u32 i,result;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];initialize();result=(u32)subject((s32)(u32)&actorBox.value,(s32)commandPointer(),(s32)v->f[2]);if(invalid)return 10;if(publicHash()!=v->f[12]||!rowCanaries())return 11;if(callHash!=v->f[13])return 12;if(observationHash!=v->f[14])return 13;if(result!=v->f[15])return 14;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text.replace('@TABLE@',hex(g.S['D_800BE5A8'])+'u')
def main():
 count,excluded=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_actor_command_table_and_rows=True,actor_row_marker_command_aliases=True,all_public_and_guard_bytes_compared=True,full_row_outside_window_canaries=True,pointer_and_endian_normalized=True)
 body=p.MANIFEST['body'].replace('func_1506E46C(','subject(');controls={'narrow-index':('& 0x7FFF;','& 0x3FFF;'),'wrong-gate-bit':('command & 0x200000','command & 0x400000'),'wrong-mode-one':('case 1:','case 3:'),'wrong-state-predicate':('func_151F2CDC() == 1','func_151F2CDC() != 0'),'wrong-table-bias':('index - 2000','index - 1999'),'wrong-selector':('[0x288]','[0x289]'),'wrong-flags':('command & 0xFF200000','command & 0xFF000000'),'wrong-replacement-width':('replacement & 0xFFFFFF','replacement & 0xFEFFFF'),'narrow-random':('func_150ADA20() & 0xFF','func_150ADA20() & 0x7F'),'wrong-choice-mask':('options & 0x1F','options & 0x0F'),'mask-choice-result':('command = func_1000F568(command, options & 0x1F);','command = func_1000F568(command, options & 0x1F) & 0x7FFF;'),'wrong-success':('return 1;','return 2;')};outcomes=[]
 for label,(old,new)in controls.items():
  assert old in body,label;q=run('control-'+label,source.replace(body,body.replace(old,new)),'-O2');assert q.returncode in(10,11,12,13,14),(label,q.returncode,'Control must reach a known result comparison');f=o/('control-'+label);outcomes.append(dict(control=label,comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 q=dict(profiles=profiles,effective_source_controls=outcomes,excluded_pointer_word_object_alias_guest_only_cases=excluded,whole_caller_or_transitive_provider_execution_claim=False,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
