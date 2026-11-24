"""SDK32 C on typed records/vectors, with guards, aliases and effective controls."""
import hashlib,json,subprocess
from tools.experiments import game_effect_contact_1515a78c_match as p
from tools.tests import game_effect_contact_1515a78c_guest as g
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
 rows=[]
 for c in g.cases():
  m,service,result=g.reference(g.fixture(c),c);values=[getattr(c,n)for n in c.__dataclass_fields__]+[public_hash(m,c),calls_hash(service.calls),observations_hash(service.observed),result];assert len(values)==18;rows.append('{{'+','.join(str(v&0xffffffff)+'u'for v in values)+'}}')
 (o/'native-vectors.h').write_bytes(('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n').encode());return len(rows)
def program():
 text='''#include <ultra64.h>
typedef struct {f32 unk0,unk4,unk8;} struct17;
typedef struct {f32 center;u8 firstPhase,secondPhase;s8 firstVelocity,secondVelocity;f32 firstRadius,secondRadius;f32 scale[3];f32 phase,rate;} MotionPayload1515A11C;
typedef struct HeightResult71820 {f32 height;s16 vertices[9];s16 pad16;u32 metadata;u8 flags,state;u16 pad1E;s32 value;} HeightResult71820;
typedef struct {u8 header[0x40];f32 values[8];u8 pad60[0x20];HeightResult71820 query;u8 padA4[4];MotionPayload1515A11C motion;} ContactRecord;
typedef struct {u8 before[16];ContactRecord value;u8 after[16];} RecordBox;
typedef struct {u8 before[16];f32 value[3];u8 after[16];} PointBox;
typedef struct {u8 before[16];u32 value[8];u8 after[16];} MarkBox;
typedef struct {u32 f[18];} Vector;
#include "native-vectors.h"
static RecordBox recordBox;static PointBox positionBox,globalBox;static MarkBox markBox;
#define D_800A6408 globalBox.value[0]
#define D_800A640C globalBox.value[1]
#define D_800A6410 globalBox.value[2]
static const Vector *v;static u32 callHash,observationHash,calls,invalid;static f32 *exposed;
static u8 *bases[4];static const u32 sizes[4]={0xcc,12,32,12};static const u32 addresses[4]={0x30000,0x50000,0x70000,@GLOBAL@};
#define OFF(t,m) __builtin_offsetof(t,m)
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(long)==4&&sizeof(f32)==4&&__CHAR_BIT__==8,"SDK32");
_Static_assert(sizeof(ContactRecord)==0xcc&&OFF(ContactRecord,values)==0x40&&OFF(ContactRecord,query)==0x80&&OFF(ContactRecord,motion)==0xa8,"record layout");
_Static_assert(sizeof(HeightResult71820)==0x24&&OFF(HeightResult71820,state)==0x1d&&sizeof(MotionPayload1515A11C)==0x24&&OFF(MotionPayload1515A11C,rate)==0x20,"provider layouts");
_Static_assert(OFF(RecordBox,value)==16&&OFF(PointBox,value)==16&&OFF(MarkBox,value)==16,"guard boxes");
static u32 mix(u32 h,u32 x){return(h^x)*16777619u;}
static u32 word(const void *p){u32 x;__builtin_memcpy(&x,p,4);return x;}
static void putword(void *p,u32 x){__builtin_memcpy(p,&x,4);}
static u32 be(const void *p){const u8 *b=p;return((u32)b[0]<<24)|((u32)b[1]<<16)|((u32)b[2]<<8)|b[3];}
static f32 real(u32 x){f32 f;__builtin_memcpy(&f,&x,4);return f;}
static f32 *position(void){return v->f[11]==1?recordBox.value.values:v->f[11]==2?recordBox.value.values+1:v->f[11]==3?recordBox.value.motion.scale:positionBox.value;}
static u32 logical(const void *p){u32 x=(u32)p,b,start;if(exposed&&p==exposed)return 0x88000;for(b=0;b<4;b++){start=(u32)(bases[b]+16);if(x>=start&&x<start+sizes[b])return addresses[b]+x-start;}invalid=1;return 0xffffffff;}
static u32 typed(u32 bank,s32 at){return bank==0?((at>=0x40&&at<0x60)||at==0x80||at==0xa8||(at>=0xb0&&at<=0xc8)):at>=0&&at<(s32)sizes[bank];}
static u32 canonical(u32 bank,s32 at){u8 *start=bases[bank]+16;s32 offset=at&~3;u32 x;if(!typed(bank,offset))return start[at];x=word(start+offset);return(x>>(8*(3-(at-offset))))&255;}
static u32 publicHash(void){u32 h=2166136261,b;s32 i;for(b=0;b<4;b++)for(i=-16;i<(s32)sizes[b]+16;i++)h=mix(h,canonical(b,i));return h;}
static void observe(void){static const u32 offsets[9]={0x40,0x44,0x48,0x4c,0x54,0x5c,0x80,0xa8,0xc8};static const u32 bytes[4]={1,0xc,0x2b,0x9d};u32 i;for(i=0;i<9;i++)observationHash=mix(observationHash,word((u8*)&recordBox.value+offsets[i]));for(i=0;i<4;i++)observationHash=mix(observationHash,((u8*)&recordBox.value)[bytes[i]]);for(i=0;i<3;i++)observationHash=mix(observationHash,word(globalBox.value+i));observationHash=mix(observationHash,markBox.value[0]);for(i=0;i<3;i++)observationHash=mix(observationHash,exposed?word(exposed+i):0);}
static void logCall(u32 target,u32 n,const u32 *args){u32 i;calls++;callHash=mix(callHash,target);callHash=mix(callHash,n);for(i=0;i<n;i++)callHash=mix(callHash,args[i]);observe();markBox.value[0]=calls;}
static void retainedEffect(void){u32 i;if(v->f[10]&32&&exposed)for(i=0;i<3;i++)exposed[i]=(calls+i)*0.5f;}
void func_1515A60C(u8 *record,f32 *pos){u32 a[2]={logical(record),logical(pos)};logCall(@INITIAL@,2,a);if(record!=(u8*)&recordBox.value||pos!=position())invalid=1;if(v->f[10]&1){recordBox.value.values[7]=real(v->f[0]&1?0xbf800000:0x7fc00001);recordBox.value.motion.rate=-2.0f;position()[1]=-3.0f;recordBox.value.values[0]=-4.0f;recordBox.value.header[1]^=0x80;}retainedEffect();}
s32 func_1514672C(struct17 *point){u32 a[1];exposed=(f32*)point;a[0]=logical(point);logCall(@INSIDE@,1,a);if(v->f[10]&2){recordBox.value.values[1]=4.0f;recordBox.value.motion.rate=9.0f;D_800A6408=0.0f;exposed[0]=17.0f;exposed[1]=18.0f;exposed[2]=19.0f;}retainedEffect();return(s32)v->f[4];}
s32 func_15046C00(f32 *point,u16 selector,f32 threshold,HeightResult71820 *result){u32 a[4];if(exposed&&exposed!=point)invalid=1;exposed=point;a[0]=logical(point);a[1]=selector;a[2]=word(&threshold);a[3]=logical(result);logCall(@QUERY@,4,a);if(selector||word(&threshold)!=word(recordBox.value.values+1)||result!=&recordBox.value.query)invalid=1;recordBox.value.query.height=real(v->f[6]);recordBox.value.query.state=(u8)v->f[8];if(v->f[10]&4){recordBox.value.values[1]=-1.0f;recordBox.value.values[7]=-1.0f;recordBox.value.motion.rate=-1.0f;D_800A6410=2.0f;exposed[0]=23.0f;}retainedEffect();return(s32)v->f[5];}
f32 func_150ADA68(void){logCall(@RANDOM@,0,0);if(v->f[10]&8){recordBox.value.query.state=v->f[8]==3?0:3;recordBox.value.motion.center=6.0f;D_800A640C=0.75f;D_800A6410=0.25f;if(exposed)exposed[1]=99.0f;}retainedEffect();return real(v->f[7]);}
u8 func_151D8E20(void){logCall(@SELECTOR@,0,0);if(v->f[10]&16){recordBox.value.motion.center=-7.0f;D_800A6410=0.5f;recordBox.value.header[0x2b]=255;recordBox.value.header[0xc]=128;recordBox.value.header[1]=254;if(exposed)exposed[2]=11.0f;}retainedEffect();return(u8)v->f[9];}
void func_151DBCBC(u8 selector,f32 scale,s16 kind,s32 state,void *point,u8 category,s32 owner){u32 a[7];if(exposed&&exposed!=point)invalid=1;exposed=point;a[0]=selector;a[1]=word(&scale);a[2]=(u32)(s32)kind;a[3]=logical((void*)state);a[4]=logical(point);a[5]=category;a[6]=(u32)owner;logCall(@SUBMIT@,7,a);retainedEffect();}
'''
 for token,name in [('GLOBAL',g.GLOBALS[0]),('INITIAL',g.PROVIDERS[0]),('INSIDE',g.PROVIDERS[1]),('QUERY',g.PROVIDERS[2]),('RANDOM',g.PROVIDERS[3]),('SELECTOR',g.PROVIDERS[4]),('SUBMIT',g.PROVIDERS[5])]:text=text.replace('@'+token+'@',hex(g.S[name])+'u')
 text+=p.MANIFEST['body'].replace('func_1515A78C(','subject(')+r'''
static void initialize(void){u32 b,j;exposed=0;invalid=calls=0;callHash=observationHash=2166136261u;bases[0]=(u8*)&recordBox;bases[1]=(u8*)&positionBox;bases[2]=(u8*)&markBox;bases[3]=(u8*)&globalBox;for(b=0;b<4;b++){for(j=0;j<sizes[b]+32;j++)bases[b][j]=(u8)(((s32)j-16)*29+(s32)v->f[0]*11+0x51);for(j=0;j<sizes[b];j+=4)if(typed(b,(s32)j))putword(bases[b]+16+j,be(bases[b]+16+j));}recordBox.value.values[0]=1;recordBox.value.values[1]=real(v->f[3]);recordBox.value.values[2]=3;recordBox.value.values[3]=0.25f;recordBox.value.values[5]=-0.5f;recordBox.value.values[7]=real(v->f[1]);recordBox.value.query.height=real(v->f[6]);recordBox.value.motion.center=8;recordBox.value.motion.rate=real(v->f[2]);recordBox.value.query.state=(u8)v->f[8];for(j=0;j<3;j++)position()[j]=(f32)(9+j);D_800A6408=real(0xc7c34ff3);D_800A640C=D_800A6410=real(0x3e4ccccd);}
static int run(void){u32 i,result;for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];initialize();result=(u32)subject((u8*)&recordBox.value,position());if(invalid)return 10;if(publicHash()!=v->f[14])return 11;if(callHash!=v->f[15])return 12;if(observationHash!=v->f[16])return 13;if(result!=v->f[17])return 14;}return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
def main():
 count=vectors();source=program();profiles={}
 def run(label,text,opt):
  f=o/(label+'.c');exe=o/label;f.write_bytes(text.encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,(q.stdout+q.stderr)[-4000:];q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr;return q
 for opt in('-O0','-O2','-O3'):
  q=run('native'+opt,source,opt);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,UBSan=True,strict_aliasing=True,typed_records_and_initialized_vectors=True,public_position_record_aliases=True,retained_private_point_effects=True,all_public_and_guard_bytes_compared=True,pointer_and_endian_normalized=True)
 body=p.MANIFEST['body'].replace('func_1515A78C(','subject(');controls={'nonnegative-early-gate':('< 0.0f','<= 0.0f'),'wrong-x-field':('(record + 0x40)','(record + 0x44)'),'wrong-position-axis':('position[1]','position[2]'),'wrong-rate':('rate = motion->rate','rate = motion->phase'),'reverse-inside-gate':('if (!func_1514672C','if (func_1514672C'),'reverse-query-hit':('if (func_15046C00','if (!func_15046C00'),'wrong-query-output':('(HeightResult71820 *)(record + 0x80)','(HeightResult71820 *)(record + 0x84)'),'inclusive-random':('func_150ADA68() <','func_150ADA68() <='),'wrong-state':('record[0x9D] == 3','record[0x9D] == 2'),'narrow-selector':('func_151DBCBC(selector,','func_151DBCBC(selector & 0x7F,'),'wrong-scale':('motion->center * D_800A6410','motion->center + D_800A6410'),'wrong-kind':('record[0x2B]','record[0x2C]'),'wrong-owner':('point, record[0xC], record[1]','point, record[0xC], record[2]'),'wrong-return':('return result;','return result ^ 1;')};outcomes=[]
 for label,(old,new)in controls.items():
  assert old in body,label;q=run('control-'+label,source.replace(body,body.replace(old,new)),'-O2');assert q.returncode in(10,11,12,13,14),(label,q.returncode,'Control must reach a known result comparison');f=o/('control-'+label);outcomes.append(dict(control=label,comparison_exit=q.returncode,binary_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(f.with_suffix('.c').read_bytes()).hexdigest()))
 q=dict(profiles=profiles,effective_source_controls=outcomes,source_installed=p.installed(),matching_credit=0,whole_caller_or_transitive_provider_execution_claim=False);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
