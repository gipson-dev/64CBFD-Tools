"""SDK32 native backing and effective semantic controls."""
from tools.experiments import game_group_record_actor_dispatch_candidates as source
from tools.tests.test_game_row_destination_fill import START

def controls():
    changes={
        'wrong_kind':('record->kind == 2','record->kind == 3'),
        'narrow_kind':('record->kind == 2','(u8)record->kind == 2'),
        'skip_mask2':('D_800C35C8[group][index]','1'),
        'narrow_mask1':('D_800C35D0[group][index]','(u8)D_800C35D0[group][index]'),
        'wrong_id':('func_15083E90(record->actorId)','func_15083E90((u8)(record->actorId + 1))'),
        'wrong_group':('func_1502178C(actor, group, index)','func_1502178C(actor, group + 1, index)'),
        'wrong_index':('func_1502178C(actor, group, index)','func_1502178C(actor, group, index + 1)'),
        'stale_count':('            count = D_800C363A[group];','            count = count;'),
    }
    result={n:source.SELECTED.replace(a,b) for n,(a,b) in changes.items()}
    assert all(v!=source.SELECTED for v in result.values())
    return result

TEST=r'''
typedef char ptr32[sizeof(void*)==4?1:-1];
typedef char record8[sizeof(GroupActorRecord15022528)==8?1:-1];
typedef char kind0[__builtin_offsetof(GroupActorRecord15022528,kind)==0?1:-1];
typedef char actor2[__builtin_offsetof(GroupActorRecord15022528,actorId)==2?1:-1];
void *memset(void*p,int c,unsigned int n) { unsigned int i;u8*b=p;for(i=0;i<n;i++)b[i]=c;return p; }
void *memcpy(void*p,const void*q,unsigned int n) { unsigned int i;u8*d=p;const u8*s=q;for(i=0;i<n;i++)d[i]=s[i];return p; }
int memcmp(const void*a,const void*b,unsigned int n) { unsigned int i;const u8*x=a,*y=b;for(i=0;i<n;i++)if(x[i]!=y[i])return 1;return 0; }
typedef struct {
    u16 a[256],b[256],aa[256],bb[256];
    GroupActorRecord15022528 r[256],rr[256];
    u32 actors[4],log[2048];
    u32 used,updates;
} State;
static State actual,expected;
static int mode,alias,initialCount,group,actualAlt,expectedAlt;
static u8 actualCounts[3],expectedCounts[3];
u16 *D_800C35D0[3],*D_800C35C8[3];
u8 *D_800C35F0[3];
u8 D_800C363A[3];
static void logCall(State*s,u32 type,u32 a,u32 b,u32 c) {
    s->log[s->used++]=type;s->log[s->used++]=a;s->log[s->used++]=b;s->log[s->used++]=c;
}
static void apply(State*s,u8*counts,int*alt,int lookup,int index) {
    if(lookup) {
        if(mode==1) counts[group]=0;
        if(mode==2) counts[group]=initialCount>253?255:initialCount+2;
        if(mode==3) { *alt=1;counts[group]=4; }
        if(mode==4) { s->r[0].kind=65535;s->r[0].actorId=255; }
    } else {
        if(mode==5) counts[group]=0;
        if(mode==6) { counts[group]=4;if(*alt)s->aa[1]=0;else s->a[1]=0; }
        s->updates++;s->actors[index%4]=0x87654321U^group^index;
    }
}
u8 *func_15083E90(u8 id) {
    logCall(&actual,1,id,0,0);apply(&actual,D_800C363A,&actualAlt,1,0);
    if(actualAlt) { D_800C35D0[group]=actual.aa;D_800C35C8[group]=actual.bb;D_800C35F0[group]=(u8*)actual.rr; }
    return id%3==1?0:(u8*)&actual.actors[id%4];
}
s32 func_1502178C(u8*actor,s32 g,s32 i) {
    unsigned int id=(unsigned int)(actor-(u8*)actual.actors)/4;
    logCall(&actual,2,id,g,i);apply(&actual,D_800C363A,&actualAlt,0,i);return 0x12345678;
}
static void reference(void) {
    int i=0,count=expectedCounts[group];
    while(i<count) {
        u16*a=expectedAlt?expected.aa:expected.a;
        u16*b=expectedAlt?expected.bb:alias?expected.a:expected.b;
        if(a[i]!=0 && b[i]!=0) {
            GroupActorRecord15022528*r=expectedAlt?expected.rr:expected.r;
            if(r[i].kind==2) {
                unsigned int id=r[i].actorId;
                logCall(&expected,1,id,0,0);apply(&expected,expectedCounts,&expectedAlt,1,0);
                if(id%3!=1) { logCall(&expected,2,id%4,group,i);apply(&expected,expectedCounts,&expectedAlt,0,i); }
            }
            count=expectedCounts[group];
        }
        i++;
    }
}
static int check(int field,int value) {
    int i;static const u16 edges[8]={0,1,2,256,258,32768,32770,65535};
    memset(&actual,0,sizeof(actual));actualAlt=expectedAlt=0;
    for(i=0;i<256;i++) {
        actual.a[i]=field==1?edges[value%8]:1;
        actual.b[i]=field==2?edges[value%8]:1;
        actual.r[i].kind=field==3?edges[value%8]:2;
        actual.r[i].actorId=(u8)(value+i);
        actual.aa[i]=actual.bb[i]=1;actual.rr[i].kind=2;actual.rr[i].actorId=255-i;
    }
    expected=actual;initialCount=field==0?value:3;
    for(i=0;i<3;i++) { D_800C363A[i]=expectedCounts[i]=i==group?initialCount:165;D_800C35D0[i]=actual.a;D_800C35C8[i]=alias?actual.a:actual.b;D_800C35F0[i]=(u8*)actual.r; }
    func_15022528(group);reference();
    for(i=0;i<3;i++)actualCounts[i]=D_800C363A[i];
    if(memcmp(&actual,&expected,sizeof(actual)) || memcmp(actualCounts,expectedCounts,3) || actualAlt!=expectedAlt)return 42;
    if(D_800C35D0[group]!=(actualAlt?actual.aa:actual.a) || D_800C35C8[group]!=(actualAlt?actual.bb:alias?actual.a:actual.b) || D_800C35F0[group]!=(u8*)(actualAlt?actual.rr:actual.r))return 42;
    return 0;
}
int run(void) {
    int field,value;
    for(field=0;field<5;field++)for(value=0;value<256;value++)for(mode=0;mode<7;mode++) {
        group=(value+field)%3;alias=(value>>3)&1;if(check(field,value))return 42;
    }
    return 0;
}
'''

def program(body=None):
    decl='extern u16 *D_800C35D0[], *D_800C35C8[];\nextern u8 *D_800C35F0[];\nextern u8 D_800C363A[];\nu8 *func_15083E90(u8);\ns32 func_1502178C();\n'
    return '#include <ultra64.h>\n'+source.HEADERS+decl+(body or source.SELECTED)+TEST+START
