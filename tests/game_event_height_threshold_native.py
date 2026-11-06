"""SDK32/UBSan tests use complete row backing, including negative indices."""
from tools.experiments import game_event_height_threshold_candidates as source
from tools.tests.test_game_row_destination_fill import START
def controls():
    b=source.SELECTED
    changes={
        'skip_valid_lookup':('if (owner != NULL)', 'if (0)'),
        'wrong_context':('event + 0x18','event + 0x14'),
        'wrong_command':('command = 0x60019','command = 0x60018'),
        'wrong_flag':('owner->flags & 8','owner->flags & 4'),
        'unsigned_count':('owner->count > 0','(u8)owner->count > 0'),
        'wrong_previous':('index = owner->previous - 1','index = owner->previous'),
        'signed_fallback':('index = owner->count25 - 1','index = (s8)owner->count25 - 1'),
        'wrong_extent':('extent = height','extent = radius'),
        'unordered_lower':('boundary <= limit','!(boundary > limit)'),
        'wrong_zero_argument':('actor, command, 0, -1','actor, command, 1, -1'),
    }
    result={n:b.replace(a,z)for n,(a,z)in changes.items()};assert all(v!=b for v in result.values());return result
TEST=r'''
typedef char pointer32[sizeof(void*)==4?1:-1];
typedef char position12[sizeof(struct17)==12?1:-1];
typedef char entry28[sizeof(HeightEntry151CE51C)==28?1:-1];
typedef char owner98[sizeof(HeightOwner151CE51C)==0x98?1:-1];
#define OFFSET(t,f,n) typedef char offset_##t##_##f[__builtin_offsetof(t,f)==n?1:-1]
OFFSET(HeightEntry151CE51C,height,4);OFFSET(HeightOwner151CE51C,flags,0x1e);
OFFSET(HeightOwner151CE51C,count25,0x25);OFFSET(HeightOwner151CE51C,count,0x2c);
OFFSET(HeightOwner151CE51C,current,0x2d);OFFSET(HeightOwner151CE51C,previous,0x2e);
OFFSET(HeightOwner151CE51C,entries,0x94);
typedef struct {u8 prefix[20];void *otherContext;void *context;} Event;
OFFSET(Event,otherContext,20);OFFSET(Event,context,24);
static struct {u32 left[4];HeightOwner151CE51C owner;u32 right[4];} actual,want;
static struct {u32 left[4];struct127 actor;u32 right[4];} actor,expected_actor;
static struct {u32 left[4];Event event;u32 right[4];} event,expected_event;
static HeightEntry151CE51C table[2][384],expected_table[2][384];
static u32 found,mutation,current_values,lookups,queries,dispatches,error,calls;
static const u32 values[12][3]={{0x40800000,0x3f800000,0x40400000},{0x40800000,0x3f800000,0x40a00000},{0,0x80000000,0},{0x80000000,0,0x80000000},{0x7f800000,0x3f800000,0x7f800000},{0xff800000,0xbf800000,0xff800000},{0x7f800000,0x7f800000,0},{0x3f800000,0x7fc12345,0},{0x7f812345,0,0},{0,0,0x7fc12345},{1,0x80000001,1},{0x7f7fffff,0xff7fffff,0x7f800000}};
static void bytes(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static f32 real(u32 v){union{u32 u;f32 f;}p;p.u=v;return p.f;}
static int equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static void effect(HeightOwner151CE51C *o,u32 m){
    if(m&2){o->flags^=8;o->current=(s8)((u8)o->current^128);o->previous=0;o->count25=0;o->entries=&table[1][128];}
    if(m&16)o->count=(s8)128;
}
void *func_151CE634(void *context){lookups++;if(context!=event.event.context)error=42;return found?&actual.owner:0;}
void func_1515C1A0(struct127 *a,struct17 *p,f32 *r,f32 *h){
    u32 x=0x3f800000,z=0xc0400000,radius=0x40000000;queries++;
    if(a!=&actor.actor||!p||!r||!h||r==h||(void*)p==(void*)r||(void*)p==(void*)h)error=42;
    bytes(&p->unk0,&x,4);bytes(&p->unk4,&values[current_values][0],4);bytes(&p->unk8,&z,4);bytes(r,&radius,4);bytes(h,&values[current_values][1],4);effect(&actual.owner,mutation);
}
s32 func_1505D024(struct127 *a,s32 command,u16 zero,s32 minus_one){
    u32 marker=0x13579bdf;dispatches++;
    if(a!=&actor.actor||command!=0x60019||zero||minus_one!=-1)error=42;
    bytes((u8*)a+0x20,&marker,4);return 0x2468;
}
typedef void (*Callback)(struct127*,u8*);
static int check(Callback fn,u32 route,u32 present,u32 flags,u32 field,u32 byte,u32 mode){
    u32 i,j,index,trigger=0,marker=0x13579bdf;u8 *p,*q;HeightOwner151CE51C projected;volatile f32 y,h,bound,limit;
    found=present;mutation=mode;current_values=(byte+field*3+mode)%12;lookups=queries=dispatches=error=0;
    p=(u8*)&actual;q=(u8*)&want;for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(i*29+byte);
    p=(u8*)&actor;q=(u8*)&expected_actor;for(i=0;i<sizeof(actor);i++)p[i]=q[i]=(u8)(i*13+byte);
    p=(u8*)&event;q=(u8*)&expected_event;for(i=0;i<sizeof(event);i++)p[i]=q[i]=(u8)(i*17+byte);
    event.event.otherContext=0;event.event.context=&actual;bytes(&expected_event,&event,sizeof(event));
    actual.owner.flags=flags;actual.owner.count=1;actual.owner.previous=1;actual.owner.current=0;actual.owner.count25=1;actual.owner.entries=&table[0][128];
    if(field==0)actual.owner.count=(s8)(u8)byte;else if(field==1)actual.owner.previous=(s8)(u8)byte;else if(field==2)actual.owner.current=(s8)(u8)byte;else actual.owner.count25=(u8)byte;
    if(field==3)actual.owner.previous=0;
    bytes(&want,&actual,sizeof(actual));if(found)effect(&want.owner,mode);projected=want.owner;
    p=(u8*)table;q=(u8*)expected_table;for(i=0;i<sizeof(table);i++)p[i]=q[i]=(u8)(i*7+byte);
    for(i=0;i<2;i++)for(j=0;j<384;j++){table[i][j].height=(f32)((s32)(j%23)-11);expected_table[i][j].height=table[i][j].height;}
    if(projected.count>0){
        s32 selected;
        if(projected.flags&8){selected=(s32)projected.previous-1;if(selected<0)selected=(u32)projected.count25-1;}else selected=projected.current;
        if(selected< -128||selected>254)return 44;
        index=(u32)(selected+128);i=projected.entries==&table[1][128];bytes(&table[i][index].height,&values[current_values][2],4);bytes(&expected_table[i][index].height,&values[current_values][2],4);
        y=real(values[current_values][0]);h=real(values[current_values][1]);limit=real(values[current_values][2]);
        if(projected.flags&8){bound=y-h;trigger=bound<=limit;}else{bound=y+h;trigger=limit<=bound;}
        trigger=trigger&&found;
    }
    if(trigger)bytes((u8*)&expected_actor.actor+0x20,&marker,4);
    if(route)fn(found?&actor.actor:0,(u8*)&event.event);else func_151CE51C(found?&actor.actor:0,(u8*)&event.event);calls++;
    if(error||lookups!=1||queries!=found||dispatches!=trigger)return 42;
    if(!equal(&actual,&want,sizeof(actual))||!equal(&actor,&expected_actor,sizeof(actor))||!equal(&event,&expected_event,sizeof(event))||!equal(table,expected_table,sizeof(table)))return 42;
    return 0;
}
int run(void){
    static const u32 modes[4]={0,2,16,18};u32 route,present,flags,field,byte,m;
    for(route=0;route<2;route++)for(present=0;present<2;present++)for(flags=0;flags<2;flags++)for(field=0;field<4;field++)for(byte=0;byte<256;byte++)for(m=0;m<4;m++)
        if(check(func_151CE51C,route,present,flags*8,field,byte,modes[m]))return 42;
    return calls==32768?0:43;
}
'''
def program(body=None):return '#include <ultra64.h>\n#include "structs.h"\n'+source.HEADERS+(source.SELECTED if body is None else body)+'\n'+TEST+'\n'+START
