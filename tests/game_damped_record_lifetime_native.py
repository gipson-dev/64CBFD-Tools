"""SDK callbacks, signed truncation, finite float rounding and whole-storage fences."""
from tools.experiments import game_damped_record_lifetime_candidates as source
from tools.tests import game_damped_record_lifetime_oracle as g

def controls():
    b=source.SELECTED
    return dict(zero_expires=b.replace('effect->age < 0','effect->age <= 0'),eager_expiry=b.replace('effect->age = -10;','effect->age = -10;\n            func_10004074(effect->records);\n            func_1516972C(input);'),update_wrapped_age=b.replace('else if (effect->age >= 0)','else'),wrong_clamp=b.replace('record->elapsed = record->duration;','record->elapsed = record->duration - 1;'),eleven_records=b.replace('0x780','0x6E0'),wrong_stride=b.replace('offset += 0xA0','offset += 0x140'),wrong_damping=b.replace('3.0f','2.0f'),wrong_float_order=b.replace('(record->baseIncrement / 3.0f) * record->elapsed / record->duration','(record->baseIncrement * record->elapsed) / (3.0f * record->duration)'),reverse_cleanup=b.replace('        func_10004074(effect->records);\n        func_1516972C(input);','        func_1516972C(input);\n        func_10004074(effect->records);'),missing_buffer_free=b.replace('        func_10004074(effect->records);',''),stub='void func_15187978(struct102 *input) {}')

def values(m,p):return[[g.read(m,p+160*i+0x8C),g.read(m,p+160*i+0x90),g.read(m,p+160*i+0x94,2),g.read(m,p+160*i+0x96,2)]for i in range(12)]
def program():
    cases=[c for c in g.cases()if c.phase==0 and c.pattern<3 and not c.mutation&4];rows=[]
    arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(tuple,list))else'0x%Xu'%g.u32(x)for x in xs)+'}'
    for c in cases:
        a=g.fixture(c);m,calls,obs=g.reference(a,c);tags=[1 if t==g.FREE else 2 for t,aa in calls];rows.append(arr([c.age,c.lifetime,c.ticks,c.mutation,c.seed,c.payload,values(a,g.RECORDS),g.read(m,g.ACTOR+0xA8,2),g.read(m,g.ACTOR+0xAA,2),g.read(m,g.CLOCK),g.read(m,g.ACTOR+0xA4),m[g.ACTOR+31],values(m,g.RECORDS),len(calls),tags+[0]*(2-len(tags)),[aa[0]for t,aa in calls]+[0]*(2-len(calls)),obs+[[0]*4]*(2-len(obs))]))
    text='#include <ultra64.h>\n'+source.SUPPORT+'\n'+source.SELECTED+'\n';variants=controls()
    for n,b in variants.items():assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(struct115)==52&&__builtin_offsetof(struct115,unk0)==0&&sizeof(DampedEffectRecord1B1600)==160&&sizeof(TimedDampedEffect1B1600)==172&&__builtin_offsetof(TimedDampedEffect1B1600,records)==164&&__builtin_offsetof(TimedDampedEffect1B1600,age)==168&&__builtin_offsetof(DampedEffectRecord1B1600,baseIncrement)==140&&__builtin_offsetof(DampedEffectRecord1B1600,elapsed)==148)?1:-1];\n'
    text+='typedef struct{u32 age,lifetime,ticks,mutation,seed,payload,initial[12][4],finalAge,finalLimit,finalTicks,finalPayload,mark,wanted[12][4],calls,tags[2],args[2],obs[2][4];}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\n'
    text+=r'''
typedef union{struct102 actor;TimedDampedEffect1B1600 effect;u8 bytes[sizeof(struct102)];}Owner;
static Owner actual,expected;static DampedEffectRecord1B1600 records[12],other[12],wanted[12],otherWanted[12];static const Row*c;static u32 calls,bad;s32 D_800BE9E4;
static u32 pointer(void*p){return p==records?0x230000u:p==other?0x240000u:p==&actual?0x220000u:p?0xDEADBEEFu:0;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void fill(DampedEffectRecord1B1600*p,const u32 v[12][4]){u32 i;for(i=0;i<12;i++){*(u32*)&p[i].baseIncrement=v[i][0];*(u32*)&p[i].accumulated=v[i][1];p[i].elapsed=(s16)v[i][2];p[i].duration=(s16)v[i][3];}}
static void observe(u32 tag,void*p){u32 n=calls++,v[4]={pointer(actual.effect.records),(u32)(s32)actual.effect.age,(u32)(s32)actual.effect.lifetime,(u32)D_800BE9E4},i;if(n>=c->calls||n>=2){bad=1;return;}if(tag!=c->tags[n]||pointer(p)!=c->args[n])bad=1;for(i=0;i<4;i++)if(v[i]!=c->obs[n][i])bad=1;}
void func_10004074(void*p){observe(1,p);if(c->mutation&1)actual.effect.records=other;if(c->mutation&2){actual.effect.age=-123;D_800BE9E4=0x12345678;}}
void func_1516972C(struct102*p){observe(2,p);((u8*)p)[31]^=0xA5;}
static u32 run(void(*fn)(struct102*)){u32 n,i,fail=0;u8*p;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];calls=bad=0;p=actual.bytes;for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+c->seed+90);actual.bytes[0]=6;actual.effect.age=(s16)c->age;actual.effect.lifetime=(s16)c->lifetime;actual.effect.records=c->payload?records:NULL;D_800BE9E4=(s32)c->ticks;
  p=(u8*)records;for(i=0;i<sizeof(records);i++)p[i]=(u8)(i*7+c->seed+89);fill(records,c->initial);copy((u8*)other,(u8*)records,sizeof(records));copy((u8*)otherWanted,(u8*)other,sizeof(other));copy((u8*)wanted,(u8*)records,sizeof(records));fill(wanted,c->wanted);copy(expected.bytes,actual.bytes,sizeof(actual));expected.effect.age=(s16)c->finalAge;expected.effect.lifetime=(s16)c->finalLimit;expected.effect.records=c->finalPayload==0x230000u?records:c->finalPayload==0x240000u?other:NULL;expected.bytes[31]=(u8)c->mark;
  fn(&actual.actor);
  if(bad||calls!=c->calls||(u32)D_800BE9E4!=c->finalTicks||!equal(actual.bytes,expected.bytes,sizeof(actual))||!equal((u8*)records,(u8*)wanted,sizeof(records))||!equal((u8*)other,(u8*)otherWanted,sizeof(other)))fail++;
 }return fail;
}
void _start(void){u32 mask=0;int result;struct115 entry;entry.unk0=func_15187978;if(run(entry.unk0))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!='+str((1<<len(variants))-1)+')goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
