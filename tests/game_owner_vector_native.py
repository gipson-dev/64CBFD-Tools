"""Native32 typed constructor; padding has guest-only literal proof."""
from tools.experiments import game_owner_vector_candidates as source
from tools.tests import game_owner_vector_oracle as g
array=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
def image(m,p,n):return array([m[p+i]for i in range(n)])
def program():
    controls=g.controls();assert len(controls)==10 and len(set(controls.values()))==10 and all(x!=source.SELECTED for x in controls.values())
    text='#include <ultra64.h>\n#include <string.h>\n#include "structs.h"\n'+source.TYPES
    text+='struct225 *func_151602C0(Header *,Header2 *,s32,s32,s32,s32,u8,u8,s32,u8,s32);\n'+source.SELECTED+'\n'
    for name,body in controls.items():text+=body.replace(source.FUNCTION,'negative_'+name)+'\n'
    rows=[]
    cases=[g.Case(i,outcome=o,mode=m)for i in range(256)for o in(0,1,2)for m in(0,3)]
    cases += [g.Case(i,owner=0,vector=0,outcome=2)for i in(0,127,128,255)]
    for c in cases:
        a=g.args(c);before=g.fixture(c);after,calls,value,copies,snapshots=g.reference(before,c)
        # Store word fields as native words; owner identity remains a byte.
        input_owner=bytearray(before[g.OWNER+i]for i in range(128));expected_owner=bytearray(after[g.OWNER+i]for i in range(128))
        for image_bytes in(input_owner,expected_owner):
            for at in(0,4,8):image_bytes[at:at+4]=image_bytes[at:at+4][::-1]
        expected_record=bytearray(after[g.RESULT+i]for i in range(96))
        initial_record=bytearray(before[g.RESULT+i]for i in range(96))
        if value:
            # Defined multi-byte fields written by the factory and constructor.
            for at,n in((16,2),(20,4),(24,4),(32,4),(36,4),(40,4)):expected_record[at:at+n]=expected_record[at:at+n][::-1]
        rows.append('{'+','.join((array(a),array(input_owner),array(expected_owner),array(initial_record),array(expected_record),
            array([g.read(before,a[2]+4*i)if a[2]else 0 for i in range(3)]),
            array([g.read(after,a[2]+4*i)if a[2]else 0 for i in range(3)]),
            str(c.outcome)+'u',str(c.mode)+'u'))+'}')
    text+=r'''
typedef struct{u32 args[16];u8 owner[128],expectedOwner[128],record[96],expectedRecord[96];u32 vector[3],expectedVector[3],outcome,mode;}Vector;
static const Vector vectors[]={
'''+',\n'.join(rows)+r'''
};
typedef struct{struct17 prefix;u8 pad0C[0x2F];u8 identity;u8 tail[0x44];}Owner;
typedef char OwnerSize[sizeof(Owner)==128&&__builtin_offsetof(Owner,identity)==0x3B?1:-1];
typedef char PayloadSize[sizeof(OwnerVectorPayload15160A58)==24&&__builtin_offsetof(OwnerVectorPayload15160A58,tag)==20?1:-1];
typedef char HeaderSize[sizeof(Header)==6&&sizeof(Header2)==12?1:-1];
typedef union{struct225 record;u32 align[128];u8 bytes[512];}Record;
static Owner owner;static struct17 inputVector;static Record output;
static const Vector*v;static u32 error,factoryCalls,copyCalls;
static void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 word(const void*p){u32 n;bytes(&n,p,4);return n;}
static void set(void*p,u32 n){bytes(p,&n,4);}
static void mutate(void){
    u32 i;
    if(v->mode&1){owner.identity^=0x55;for(i=0;i<3;i++)set((u8*)&inputVector+4*i,word((u8*)&inputVector+4*i)^0xA5A5A5A5u);}
    if(v->mode&2){output.bytes[8]^=0xA5;owner.identity^=0xAA;}
}
__attribute__((noinline,noclone)) struct225 *func_151602C0(Header*h,Header2*z,s32 a,s32 b,s32 c,s32 d,u8 e,u8 f,s32 size,u8 priority,s32 user){
    if(factoryCalls++||copyCalls||h->unk0!=(s8)v->args[3]||h->unk1!=5||h->unk2!=(s16)v->args[4]||h->unk4!=16||
       z->unk0||z->unk4||z->unk8||(u32)a!=v->args[5]||(u32)b!=v->args[6]||(u32)c!=v->args[7]||(u32)d!=v->args[8]||
       e!=255||f||(u32)size!=v->args[12]+24u||priority!=(u8)v->args[14]||(u32)user!=v->args[15])error=1;
    mutate();
    if(v->outcome!=2)return 0;
    bytes(output.bytes+14,h,6);set(output.bytes+20,0x70000u);output.bytes[14]|=2;
    return &output.record;
}
__attribute__((noinline,noclone)) void *memcpy(void*dst,const void*src,size_t n){
    u32 i;const u8*p=src;
    if(copyCalls++||!factoryCalls||v->outcome!=2||dst!=output.bytes+24||n!=24){error=1;return dst;}
    if(word(p)!=(u32)&owner||p[4]!=v->owner[0x3B]||p[5]!=(u8)v->args[1]||
       p[20]!=(u8)v->args[11]||p[21]!=(u8)v->args[13])error=1;
    for(i=0;i<3;i++)if(word(p+8+4*i)!=v->vector[i])error=1;
    bytes(dst,src,(u32)n);return dst;
}
typedef struct225 *(*Callback)(u8*,u8,void*,u8,s16,s32,s32,s32,s32,s32,s32,s8,s32,u8,u8,s32);
static Callback callbacks[]={'''+','.join([source.FUNCTION,*['negative_'+n for n in controls]])+r'''};
static int run(void){
    u32 i,j,k,killed=0,same;struct225*result;
    for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)for(j=0;j<11;j++){
        v=&vectors[i];factoryCalls=copyCalls=error=0;bytes(&owner,v->owner,128);bytes(output.bytes,v->record,96);
        for(k=96;k<512;k++)output.bytes[k]=(u8)(k*13+89);
        for(k=0;k<3;k++)set((u8*)&inputVector+4*k,v->vector[k]);
        result=callbacks[j](v->args[0]?(u8*)&owner:0,(u8)v->args[1],v->args[2]?&inputVector:0,(u8)v->args[3],(s16)v->args[4],
            (s32)v->args[5],(s32)v->args[6],(s32)v->args[7],(s32)v->args[8],(s32)v->args[9],(s32)v->args[10],
            (s8)v->args[11],(s32)v->args[12],(u8)v->args[13],(u8)v->args[14],(s32)v->args[15]);
        same=!error&&result==(v->args[0]&&v->outcome==2?&output.record:0)&&factoryCalls==(v->args[0]?1u:0u)&&copyCalls==(v->args[0]&&v->outcome==2?1u:0u);
        for(k=0;k<128;k++)if(((u8*)&owner)[k]!=v->expectedOwner[k])same=0;
        for(k=0;k<3;k++)if(word((u8*)&inputVector+4*k)!=v->expectedVector[k])same=0;
        for(k=0;k<96;k++){
            if(v->args[0]&&v->outcome==2){
                if(k==19||k==30||k==31||k==46||k==47)continue;
                if(k>=24&&k<28)continue;
            }
            if(output.bytes[k]!=v->expectedRecord[k])same=0;
        }
        for(k=96;k<512;k++)if(output.bytes[k]!=(u8)(k*13+89))same=0;
        if(!same){if(!j)return 42;killed|=1u<<(j-1);}
    }
    return killed==1023?0:43;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,list(controls),len(rows)
