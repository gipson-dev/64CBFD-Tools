"""SDK native32 two-channel updater, defined packets and effective controls."""
from tools.experiments import game_owner_paired_effect_candidates as c
from tools.tests import game_owner_paired_effect_oracle as g

def controls():
    b=c.SELECTED
    return dict(one_channel=b.replace('index < 2','index < 1'),wrong_tick=b.replace('- (u32)D_800BE9E4','+ (u32)D_800BE9E4'),zero_expires=b.replace('timers[index] < 0','timers[index] <= 0'),ignore_tag=b.replace('record->tag == owner[0x3B]','1'),wrong_angle_limit=b.replace('angle % (u32)(record->secondChoiceLimit + 1)','angle % (u32)(record->firstChoiceLimit + 1)'),wrong_quarter=b.replace('angle - 0x40','angle - 0x3F'),wrong_reset=b.replace('% 23 + 5','% 22 + 5'),wrong_count=b.replace('request.count = angle % (u32)(record->firstChoiceLimit + 1)','request.count = angle % (u32)(record->secondChoiceLimit + 1)'),wrong_duration=b.replace('% 21 + 80','% 21 + 81'),late_kind=b.replace('                payload.kind = record->mode;\n','').replace('                payload.flags =','                payload.kind = record->mode;\n                payload.flags ='),wrong_y=b.replace('payload.velocityY = 0.0f','payload.velocityY = 1.0f'),wrong_threshold=b.replace('payload.threshold = threshold','payload.threshold = D_800A7440').replace('    f32 threshold = D_800A7440;',''),wrong_velocity=b.replace('speed * quarterValue','((void)quarterValue, speed * angleValue)'),wrong_active=b.replace('                    5, 1, 0, 2, 1','                    4, 1, 0, 2, 1'),wrong_context=b.replace('record->header[0xC], record->header[1]','record->header[0xC], record->header[0xC]'),no_backlink=b.replace('                    *(OwnerPairRecord **)owner = record;\n',''),wrong_backlink_index=b.replace('owner[4] = index','owner[4] = index + 1'),wrong_coordinate_stride=b.replace('index * 6 + 0x1AC','index * 4 + 0x1AC'),early_range=b.replace('                speed = func_150ADA68();','                f32 capturedBase = record->firstBase, capturedRange = record->firstRange;\n                speed = func_150ADA68();').replace('speed = speed * record->firstRange + record->firstBase','speed = speed * capturedRange + capturedBase'),stub='void func_1518BD60(OwnerPairRecord *record){}')

def program():
    cases=[g.Case(randoms=(i,0xFFFFFFFF,i,0xFFFFFFFE,i+64,23,i+1,21),limits=(32767,32767),outcome=i&3,kind=i,flags=i^0xA5,metric=g.u32(i*0x1020304),category=i,context=i^255)for i in range(256)]
    cases.extend(x for i,x in enumerate(g.cases())if i>=2048 and not x.connected and not x.alias)
    arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(tuple,list))else'0x%Xu'%g.u32(x)for x in xs)+'}'
    rows=[]
    for x in cases:
        initial=g.fixture(x);e=g.reference(initial,x);m=e['memory'];packets=[]
        for req,desc,render in e['packets']:
            packets.append([int.from_bytes(req[12:14],'big'),int.from_bytes(req[14:16],'big'),int.from_bytes(req[16:20],'big'),req[21],*[int.from_bytes(desc[i:i+4],'big')for i in range(0,20,4)],*desc[24:28]])
        packets+= [[0]*13]*(2-len(packets));events=[(1 if t==g.INTEGER else 2 if t==g.ANGLE else 3 if t==g.FLOAT else 4,a[0]if t==g.ANGLE else 0)for t,a in e['calls']];events+=[(0,0)]*(18-len(events))
        before=[g.read(initial,g.RECORD+i)for i in(52,56,60,64)];after=[g.read(m,g.RECORD+i)for i in(16,20,24,28)]+[g.read(m,g.RECORD+i,2)for i in(32,34)]+[g.read(m,g.RECORD+i)for i in(44,48,52,56,60,64)]+[m[g.RECORD+41],m[g.RECORD+42],m[g.RECORD+1],m[g.RECORD+12],int(g.read(m,g.RECORD+36)==g.OTHER),g.read(m,g.TICK),g.read(m,g.THRESHOLD)]
        links=[(int(i<e['factories']and x.outcome>>i&1),m[g.PAYLOAD+4096*i+76])for i in range(2)]
        rows.append(arr([x.timers,x.tick,x.gate,x.tag,x.limits,x.randoms,x.fractions,x.values,x.threshold,x.metric,x.kind,x.flags,x.category,x.context,x.outcome,x.mutation,before,after,packets,events,len(e['calls']),e['factories'],links]))
    text='#include <ultra64.h>\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\n'+c.SUPPORT+'\n'+c.SELECTED+'\n';variants=controls()
    for n,b in variants.items():assert b!=c.SELECTED,n;text+=b.replace('func_1518BD60','negative_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(OwnerPairRecord)==68&&sizeof(OwnerPairRequest)==28&&sizeof(OwnerPairPayload)==32&&sizeof(OwnerPairRender)==32&&__builtin_offsetof(OwnerPairRecord,timers)==44&&__builtin_offsetof(OwnerPairRecord,previousX)==52&&__builtin_offsetof(OwnerPairRecord,previousZ)==60&&__builtin_offsetof(OwnerPairPayload,flags)==24)?1:-1];\n'
    text+='typedef struct{u32 timers[2],tick,gate,tag,limits[2],randoms[8],fractions[4],values[4],threshold,metric,kind,flags,category,context,outcome,mutation,before[4],after[19],packets[2][13],events[18][2],calls,factories,links[2][2];}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\nstatic const u32 table[65]='+arr(g.LOOKUP)+';\n'
    text+=r'''
typedef union{u64 align;u8 bytes[768];}Storage;
static Storage storage,expected,owner,other,savedOwner,savedOther,created[2],savedCreated[2],payload[2],savedPayload[2];
static const Row*row;static u32 bad,step,ni,nf,nc;static OwnerPairRecord*record;
s32 D_800BE9E4;f32 D_800A7440;
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static u32 word(const void*p){u32 v;copy((u8*)&v,p,4);return v;}
static void setword(void*p,u32 v){copy(p,(u8*)&v,4);}
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static void event(u32 kind,u32 argument){if(step>=row->calls||row->events[step][0]!=kind||(kind==2&&row->events[step][1]!=argument))bad=1;step++;}
s32 func_150ADA20(void){u32 i=ni++;event(1,0);if(i==0&&(row->mutation&1))record->secondChoiceLimit=7;if(i>=8)bad=1;return(s32)row->randoms[i&7];}
f32 func_151423D8(u8 angle){u32 index=angle&64?64-(angle&63):angle&63;u32 value=table[index];event(2,angle);if((angle&192)!=0&&(angle&192)!=192)value^=0x80000000;return real(value);}
f32 func_150ADA68(void){u32 i=nf++;event(3,0);if(i==0&&(row->mutation&2)){record->firstBase=-3.0f;record->firstRange=2.0f;}if(i==1&&(row->mutation&4)){record->secondBase=17.0f;record->secondRange=-.5f;record->mode=211;record->subtype=255;record->header[1]=255;record->header[12]=129;}if(i>=4)bad=1;return real(row->fractions[i&3]);}
u8 *func_15147DA0(void*request,void*descriptor,s32 bytes,s32 active,s32 first,s32 second,s32 third,s32 fourth,s32 fifth,s32 fade,s32 alpha,void*render,s32 extra,u8 category,s32 context){
 OwnerPairRequest*q=request;OwnerPairPayload*p=descriptor;OwnerPairRender*r=render;u32 j,i=nc++;const u32*e=row->packets[i&1];event(4,0);
 if(i>=2||q->duration!=(s16)e[0]||q->mode!=(s16)e[1]||(u32)q->active!=e[2]||q->count!=e[3]||bytes!=(s32)(e[3]*12+8)||active!=5||first!=1||second||third!=2||fourth!=1||fifth||fade||alpha||extra||category!=record->header[12]||context!=record->header[1])bad=1;
 for(j=0;j<5;j++)if(word((u8*)p+4*j)!=e[4+j])bad=1;
 if(p->flags!=e[9]||p->kind!=e[10]||p->channel!=e[11]||p->alpha!=e[12])bad=1;
 if(r->words[0]||r->words[1]!=1||r->words[2]!=0x160600||r->words[3]!=3||r->words[4]!=16||r->words[5]!=128||r->words[6]!=32||((u8*)r)[28]||((u8*)r)[29]!=9)bad=1;
 /* Check defined inputs before filling only deliberately unwritten holes. */
 for(j=0;j<12;j++)((u8*)q)[j]=0xA5;((u8*)q)[20]=0xA5;for(j=22;j<28;j++)((u8*)q)[j]=0xA5;for(j=20;j<24;j++)((u8*)p)[j]=0xA5;for(j=28;j<32;j++)((u8*)p)[j]=0xA5;((u8*)r)[30]=((u8*)r)[31]=0xA5;
 if(row->mutation&8){record->owner=other.bytes;D_800BE9E4=7;setword(&D_800A7440,0x7FC12345);q->x=1.25f+i;}
 return row->outcome>>i&1?created[i&1].bytes:NULL;
}
static u32 run(void(*fn)(OwnerPairRecord*)){u32 n,i,j,fail=0;OwnerPairRecord*e;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){row=&rows[n];record=(OwnerPairRecord*)storage.bytes;fill(storage.bytes,768,0x5A);fill(owner.bytes,768,0x5A);fill(other.bytes,768,0x5A);
  for(i=0;i<2;i++){u8*p=i?other.bytes:owner.bytes;*(s32*)p=row->gate==2&&!i?0:1;*(s32*)(p+0x1D4)=row->gate==3&&!i?0:1;p[59]=(u8)row->tag;if(row->gate==4&&!i)p[59]^=1;*(u32*)(p+0x184)=row->metric+i;for(j=0;j<2;j++){*(s16*)(p+0x1AC+6*j)=-32768+71*i+19*j;*(s16*)(p+0x1B0+6*j)=32767-79*i-23*j;}fill(created[i].bytes,768,0x5A);fill(payload[i].bytes,768,0x5A);*(void**)(created[i].bytes+0x98)=payload[i].bytes;copy(savedCreated[i].bytes,created[i].bytes,768);copy(savedPayload[i].bytes,payload[i].bytes,768);if(row->links[i][0]){*(void**)(savedPayload[i].bytes+72)=record;savedPayload[i].bytes[76]=row->links[i][1];}}
  record->header[0]=31;record->header[1]=row->context;record->header[12]=row->category;for(i=0;i<4;i++)setword((u8*)record+16+4*i,row->values[i]);record->firstChoiceLimit=row->limits[0];record->secondChoiceLimit=row->limits[1];record->owner=row->gate==1?NULL:owner.bytes;record->tag=row->tag;record->mode=row->kind;record->subtype=row->flags;for(i=0;i<2;i++)record->timers[i]=row->timers[i];for(i=0;i<4;i++)setword((u8*)record+52+4*i,row->before[i]);D_800BE9E4=row->tick;setword(&D_800A7440,row->threshold);
  copy(expected.bytes,storage.bytes,768);copy(savedOwner.bytes,owner.bytes,768);copy(savedOther.bytes,other.bytes,768);e=(OwnerPairRecord*)expected.bytes;for(i=0;i<4;i++)setword((u8*)e+16+4*i,row->after[i]);e->firstChoiceLimit=row->after[4];e->secondChoiceLimit=row->after[5];for(i=0;i<6;i++)setword((u8*)e+44+4*i,row->after[6+i]);e->mode=row->after[12];e->subtype=row->after[13];e->header[1]=row->after[14];e->header[12]=row->after[15];e->owner=row->gate==1?NULL:row->after[16]?other.bytes:owner.bytes;
  step=ni=nf=nc=bad=0;fn(record);
  if(bad||step!=row->calls||nc!=row->factories||!equal(storage.bytes,expected.bytes,768)||!equal(owner.bytes,savedOwner.bytes,768)||!equal(other.bytes,savedOther.bytes,768)||(u32)D_800BE9E4!=row->after[17]||word(&D_800A7440)!=row->after[18])fail++;
  for(i=0;i<2;i++)if(!equal(created[i].bytes,savedCreated[i].bytes,768)||!equal(payload[i].bytes,savedPayload[i].bytes,768))fail++;
 }return fail;}
void _start(void){u32 mask=0;int result;if(run(func_1518BD60))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!='+str((1<<len(variants))-1)+')goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
