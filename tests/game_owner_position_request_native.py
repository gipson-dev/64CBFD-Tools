"""SDK/native32 checks score defined fields and keep reserved bytes unscored."""
from tools.experiments import game_owner_position_request_candidates as source
from tools.tests.test_game_row_destination_fill import START

def controls():
    b=source.SELECTED
    changes={
        'skip_owner_gate':('if (*(u8 **)input == NULL)', 'if (0)'),
        'short_snapshot':('memcpy(&payload, input, 0x30)', 'memcpy(&payload, input, 0x2C)'),
        'wrong_kind':('payload.kind = 6;', 'payload.kind = 7;'),
        'wrong_flags':('request.flags |= 4;', 'request.flags |= 8;'),
        'skip_position':('payload.position = request.position;', ''),
        'wrong_size':('&request, 0x50, 0x18', '&request, 0x4C, 0x18'),
        'wrong_channel':('NULL, channel, 0)', 'NULL, channel + 1, 0)'),
        'skip_final_copy':('if (created != NULL)', 'if (0)'),
        'return_copy_result':('memcpy(*(void **)(created + 0x98), &payload, 0x50);', 'return memcpy(*(void **)(created + 0x98), &payload, 0x50);'),
        'wrong_reject_result':('return NULL;', 'return input;'),
    }
    r={n:b.replace(a,z,1)for n,(a,z)in changes.items()}
    assert all(v!=b for v in r.values());return r

TEST=r'''
typedef char pointer32[sizeof(void*)==4?1:-1];
typedef char position12[sizeof(OwnerPosition151A3504)==12?1:-1];
typedef char snapshot48[sizeof(OwnerSnapshot151A3504)==48?1:-1];
typedef char payload80[sizeof(OwnerPayload151A3504)==80?1:-1];
typedef char request28[sizeof(OwnerRequest151A3504)==28?1:-1];
#define OFFSET(t,f,n) typedef char offset_##t##_##f[__builtin_offsetof(t,f)==n?1:-1]
OFFSET(OwnerSnapshot151A3504,owner,0);OFFSET(OwnerSnapshot151A3504,slot,5);
OFFSET(OwnerPayload151A3504,kind,0x30);OFFSET(OwnerPayload151A3504,position,0x34);
OFFSET(OwnerPayload151A3504,value40,0x40);OFFSET(OwnerPayload151A3504,flag44,0x44);
OFFSET(OwnerPayload151A3504,value48,0x48);OFFSET(OwnerPayload151A3504,flag4C,0x4c);
OFFSET(OwnerRequest151A3504,position,0);OFFSET(OwnerRequest151A3504,lifetime,12);
OFFSET(OwnerRequest151A3504,flags,14);OFFSET(OwnerRequest151A3504,step,16);
OFFSET(OwnerRequest151A3504,count,21);
typedef struct {u8 prefix[0x98];void *payload;u8 tail[4];} Record;
static struct {u32 left[4];Record record;u32 right[4];} output,expected_record;
static struct {u32 left[4];u8 payload[80];u32 right[4];} target;
static OwnerSnapshot151A3504 input;
static u8 owner[4],snapshot[48],expected[80],known[80],*live_payload;
static u32 current_query,current_outcome,current_channel,current_mutation,current_point;
static u32 copies,queries,factories,error,root_calls;
static const u32 points[4][3]={{0x3f800000,0x40000000,0xc0400000},{0x80000000,0,0x80000000},{0x7f800000,0x7fc12345,0x7f812345},{1,0x7f7fffff,0x80000001}};
static void bytes(void *dst,const void *src,u32 n){u8 *d=dst;const u8*s=src;u32 i;for(i=0;i<n;i++)d[i]=s[i];}
void *memcpy(void *dst,const void *src,u32 n){
    if(n!=48&&n!=80)error=42;
    if(n==48){live_payload=dst;bytes(snapshot,src,48);}
    bytes(dst,src,n);copies++;
    if(n==48&&(current_mutation&1))((u8*)&input)[12]^=0x33;
    return owner; /* Both copy results must be ignored. */
}
s32 func_151A4E34(u8 *p,void *out){
    OwnerRequest151A3504 *r=out;queries++;
    if(p!=live_payload)error=42;
    if(current_mutation&2){p[9]^=0x5a;r->flags^=0x40;r->count=current_channel;}
    if(current_query)bytes(out,points[current_point],12);
    return current_query?(-1):0;
}
u8 *func_15147A80(void *p,s32 size,s32 entry,s32 active,s32 first,s32 second,s32 resource,s32 value,void *optional,u8 channel,s32 context){
    OwnerRequest151A3504 *r=p;u32 i;factories++;
    if(size!=80||entry!=24||active!=6||first!=6||second!=6||resource||value||optional||context||channel!=current_channel)error=42;
    if(r->lifetime!=1000||r->step!=8||r->flags!=(2u|(current_query?4u:0u)|((current_mutation&2)?0x40u:0u))||r->count!=((current_mutation&2)?current_channel:50u))error=42;
    if(current_query)for(i=0;i<12;i++)if(((u8*)p)[i]!=((const u8*)points[current_point])[i])error=42;
    if(current_mutation&8){
        u32 v=0xbf800000;live_payload[11]^=0xa5;live_payload[0x30]=9;bytes(live_payload+0x40,&v,4);
        for(i=0;i<3;i++){v=points[current_point][i]^0x80000000;bytes((u8*)p+4*i,&v,4);}
    }
    output.record.payload=target.payload;
    return current_outcome?(u8*)&output.record:0;
}
typedef u8 *(*Constructor)(void*,u8);
static int check(Constructor fn,u32 route,u32 active,u32 query,u32 outcome,u32 mutation,u32 point,u32 channel){
    u32 i,v,mask=(mutation&1)|((mutation&2))|((mutation&4)<<1);u8 *a,*b,*result;
    a=(u8*)&input;for(i=0;i<sizeof(input);i++)a[i]=(u8)(i*29+channel);input.owner=active?owner:0;
    a=(u8*)&output;b=(u8*)&expected_record;for(i=0;i<sizeof(output);i++)a[i]=b[i]=(u8)(i*13+channel);
    a=(u8*)&target;for(i=0;i<sizeof(target);i++)a[i]=(u8)(i*17+channel);
    current_query=query;current_outcome=outcome;current_channel=channel;current_mutation=mask;current_point=point;copies=queries=factories=error=0;
    result=route?fn(&input,(u8)channel):func_151A3504(&input,(u8)channel);root_calls++;
    if(error||queries!=active||factories!=active||copies!=(active?(1+outcome):0)||result!=((active&&outcome)?(u8*)&output.record:0))return 42;
    if(active)expected_record.record.payload=target.payload;
    a=(u8*)&output;b=(u8*)&expected_record;for(i=0;i<sizeof(output);i++)if(a[i]!=b[i])return 42;
    for(i=0;i<80;i++){known[i]=0;expected[i]=0;}
    for(i=0;i<48;i++){known[i]=1;expected[i]=snapshot[i];}
    if(mask&2)expected[9]^=0x5a;
    known[0x30]=known[0x44]=known[0x4c]=1;expected[0x30]=6;
    for(i=0;i<4;i++)known[0x40+i]=known[0x48+i]=1;
    if(query)for(i=0;i<12;i++){known[0x34+i]=1;expected[0x34+i]=((const u8*)points[point])[i];}
    if(mask&8){expected[11]^=0xa5;expected[0x30]=9;v=0xbf800000;bytes(expected+0x40,&v,4);}
    if(active&&outcome)for(i=0;i<80;i++)if(known[i]&&target.payload[i]!=expected[i])return 42;
    a=(u8*)&target;for(i=0;i<sizeof(target);i++)if((!(active&&outcome)||i<16||i>=96)&&a[i]!=(u8)(i*17+channel))return 42;
    return 0;
}
int run(void){
    u32 route,active,query,outcome,mutation,point,channel;
    for(route=0;route<2;route++)for(active=0;active<2;active++)for(query=0;query<2;query++)for(outcome=0;outcome<2;outcome++)for(mutation=0;mutation<8;mutation++)for(point=0;point<4;point++)for(channel=0;channel<256;channel++)
        if(check(func_151A3504,route,active,query,outcome,mutation,point,channel))return 42;
    return root_calls==131072?0:43;
}
'''
def program(body=None):return '#include <ultra64.h>\n'+source.HEADERS+(source.SELECTED if body is None else body)+'\n'+TEST+'\n'+START
