"""Typed SDK32 backing, float-bit ABI observations and wrong-source controls."""
from tools.experiments import game_actor_type_query_candidates as source
from tools.tests.test_game_row_destination_fill import START
def controls():
    changes={
        'signed_kind':('actor[4] == actorType','(s8)actor[4] == actorType'),
        'narrow_type':('actor[4] == actorType','actor[4] == (u8)actorType'),
        'skip_model_gate':('*(void **)(actor + 0x1D4) != NULL','1'),
        'wrong_part_rejection':('part != -1','part > 0'),
        'wrong_metadata_byte':('part * 4 + 2','part * 4 + 3'),
        'swapped_floats':('forwardOffset, radius, queryMode','radius, forwardOffset, queryMode'),
        'wrong_mode':('forwardOffset, radius, queryMode','forwardOffset, radius, queryMode + 1'),
        'skip_first_actor':('actor = D_800CC2D0;','actor = D_800CC2D0 + 0x32C;'),
        'wrong_result':('return value;','return 1;'),
    }
    result={n:source.SELECTED.replace(a,b)for n,(a,b)in changes.items()};assert all(v!=source.SELECTED for v in result.values());return result
TEST=r'''
void *memset(void*p,int c,unsigned n){u8*d=p;unsigned i;for(i=0;i<n;i++)d[i]=c;return p;}
void *memcpy(void*p,const void*q,unsigned n){u8*d=p;const u8*s=q;unsigned i;for(i=0;i<n;i++)d[i]=s[i];return p;}
int memcmp(const void*p,const void*q,unsigned n){const u8*a=p,*b=q;unsigned i;for(i=0;i<n;i++)if(a[i]!=b[i])return 1;return 0;}
typedef struct {s32 busy;u8 kind;u8 opaque[0x1cf];void*model;u8 tail[0x154];} Actor;
typedef char actor_size[sizeof(Actor)==0x32c?1:-1];
typedef char model_offset[__builtin_offsetof(Actor,model)==0x1d4?1:-1];
typedef char kind_offset[__builtin_offsetof(Actor,kind)==4?1:-1];
typedef char pointer32[sizeof(void*)==4?1:-1];
typedef struct {Actor actors[25];u8 metadata[23*4];u32 log[1024];u32 used;} State;
State actual,expected;
__asm__(".global D_800CC2D0\n.set D_800CC2D0, actual\n.global D_800D121C\n.set D_800D121C, actual+20300\n.global D_8009BD30\n.set D_8009BD30, actual+20300\n");
static struct127 originActor;
static u8 *origin=(u8*)&originActor,other[16];
static struct {u32 before;s32 found;u32 after;} output;
static int mutation,partValue,returnValue,mode,expectedIndex;
static u32 forwardBits,radiusBits;
typedef s32 (*QueryCallback)(struct127*,f32,f32,s32*,s32,s32);
static QueryCallback callback=func_15081574;
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static void logWord(State*s,u32 v){s->log[s->used++]=v;}
static void change(State*s,int lookup,int i){
    if(lookup && mutation==1){s->actors[i].busy=0;s->actors[i].model=0;s->actors[i].kind^=255;}
    if(lookup && mutation==2 && partValue>=0)s->metadata[partValue*4+2]=255;
}
s32 func_1508108C(u8*actor){
    unsigned i=(unsigned)(actor-(u8*)actual.actors)/0x32c;
    logWord(&actual,1);logWord(&actual,i);change(&actual,1,i);return partValue;
}
s32 func_15080D20(u8*o,u8*actor,s32 tag,f32 forward,f32 radius,s32 queryMode){
    unsigned i=(unsigned)(actor-(u8*)actual.actors)/0x32c;
    logWord(&actual,2);logWord(&actual,o==origin);logWord(&actual,i);logWord(&actual,tag);logWord(&actual,bits(forward));logWord(&actual,bits(radius));logWord(&actual,queryMode);
    if(mutation==3)output.found=(s32)other;
    return returnValue;
}
static int reference(int actorType){
    int i,value=0;expectedIndex=-1;
    for(i=0;i<25;i++)if(expected.actors[i].busy && expected.actors[i].model && expected.actors[i].kind==actorType){
        logWord(&expected,1);logWord(&expected,i);change(&expected,1,i);
        if(partValue!=-1){
            logWord(&expected,2);logWord(&expected,1);logWord(&expected,i);logWord(&expected,expected.metadata[partValue*4+2]);logWord(&expected,forwardBits);logWord(&expected,radiusBits);logWord(&expected,mode);
            if(mutation==3)expectedIndex=-2;
            value=returnValue;if(value){expectedIndex=i;break;}
        }
    }
    return value;
}
static int check(int field,int value){
    static const u32 floats[10]={0,0x80000000U,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc12345,0x7f812345,1,0x7f7fffff};
    static const int parts[5]={-1,0,1,2,22};static const int returns[4]={0,1,-1,0x7fffffff};
    int i,at=field==0?value%26:0,type=value&255,want,got;
    union{u32 u;f32 f;}forwardArg,radiusArg;
    memset(&actual,0,sizeof(actual));partValue=parts[(value/3)%5];returnValue=returns[value%4];mode=value&1?-1:15;
    forwardBits=floats[value%10];radiusBits=floats[(value+3)%10];
    forwardArg.u=forwardBits;radiusArg.u=radiusBits;
    if(field==1 && value==0)type=256;
    for(i=0;i<25;i++){actual.actors[i].busy=i>=at?(value&1?0x80000000U:1):0;actual.actors[i].kind=value&255;actual.actors[i].model=field==2 && value%3==0?0:origin;}
    for(i=0;i<23*4;i++)actual.metadata[i]=(i*11+value)&255;
    expected=actual;output.before=0x12345678;output.after=0x87654321;output.found=(s32)other;
    got=(value&1?callback:func_15081574)(&originActor,forwardArg.f,radiusArg.f,&output.found,mode,type);want=reference(type);
    if(got!=want || memcmp(&actual,&expected,sizeof(actual)) || output.before!=0x12345678 || output.after!=0x87654321)return 42;
    if(output.found!=(s32)(expectedIndex==-1?0:expectedIndex==-2?other:(u8*)&actual.actors[expectedIndex]))return 42;
    return 0;
}
int run(void){int field,value;for(field=0;field<3;field++)for(value=0;value<256;value++)for(mutation=0;mutation<4;mutation++)if(check(field,value))return 42;return 0;}
'''
def program(body=None):
    decl='s32 func_15080D20(u8 *, u8 *, s32, f32, f32, s32);\n'
    return '#include <ultra64.h>\n'+source.HEADERS+decl+(body or source.SELECTED)+'\n'+TEST+START
