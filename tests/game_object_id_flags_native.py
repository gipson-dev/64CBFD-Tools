"""Exhaustive native32 ID classification with canonical object ABI."""
from tools.tests import game_object_id_flags_oracle as model

def source(body):
    tables=[];expected=[]
    for dataset in(0,1):
        values=model.table(dataset);tables.append('{'+','.join(map(str,values))+'}')
        lut={v:1 for v in values[:90]};lut.update({v:2 for v in values[90:93]})
        expected.append('{'+','.join('[%d]=%d'%(k,v)for k,v in sorted(lut.items()))+'}')
    return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
static u16 data[94];
#define D_8009877C (data[0])
#define D_8009877E (data[1])
#define D_80098780 (data+2)
#define D_80098830 (data+90)
#define D_80098836 (data+93)
typedef char state_at_zero[__builtin_offsetof(struct127,interaction_state)==0?1:-1];
typedef char id_at_84[__builtin_offsetof(struct127,unk84)==0x84?1:-1];
typedef char flag_at_2fb[__builtin_offsetof(struct127,unk2FB)==0x2FB?1:-1];
typedef char object_32c[sizeof(struct127)==0x32C?1:-1];
'''+body.replace('void func_1503B840(', '__attribute__((noinline)) void func_1503B840(',1)+r'''
static const u16 tables[2][94]={TABLES};
static const u8 expected[2][65536]={EXPECTED};
static struct{u32 before;struct127 object;u32 after;} storage;
static void(*volatile probe)(struct127*)=func_1503B840;
static void reset(void){u8*p=(u8*)&storage;for(u32 i=0;i<sizeof(storage);i++)p[i]=(u8)(i*29+123);storage.before=0x12345678u;storage.after=0x87654321u;}
static int check(u32 dataset,u32 identity,u32 flags,u32 state){
 struct127*p=&storage.object;p->interaction_state=(s32)state;p->unk84.uh=(u16)identity;p->unk2FB=(u8)flags;probe(p);
 if(p->unk2FB!=(u8)(flags|(state==1?expected[dataset][identity]:0))||p->unk84.uh!=identity||(u32)p->interaction_state!=state||storage.before!=0x12345678u||storage.after!=0x87654321u)return 1;
 return 0;
}
static void func_15039CC8(struct127*p){p->unk2FB|=4;p->unk84.uh=0xBEEF;}
static void wrapper(struct127*p){p->unk2FB=0;func_1503B840(p);func_15039CC8(p);}
static int run(void){
 static const u32 flags[]={0,1,2,3,127,128,252,255};
 static const u32 states[]={0,2,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
 static const u32 identities[]={0,233,0x7FFF,0x8000,0xFFFF};
 for(u32 d=0;d<2;d++){
  for(u32 i=0;i<94;i++)data[i]=tables[d][i];reset();
  for(u32 id=0;id<65536;id++)for(u32 f=0;f<8;f++)if(check(d,id,flags[f],1))return 1;
  for(u32 s=0;s<5;s++)for(u32 id=0;id<5;id++)for(u32 f=0;f<256;f++)if(check(d,identities[id],f,states[s]))return 1;
  /* Sample every byte outside the three input/output fields, including padding. */
  for(u32 id=0;id<256;id++){
   reset();if(check(d,id,128,1))return 1;u8*p=(u8*)&storage;
   for(u32 i=4;i<4+sizeof(struct127);i++){u32 at=i-4;if(at<4||(at>=0x84&&at<0x86)||at==0x2FB)continue;if(p[i]!=(u8)(i*29+123))return 1;}
  }
  for(u32 id=0;id<65536;id+=257){reset();storage.object.interaction_state=1;storage.object.unk84.uh=(u16)id;wrapper(&storage.object);if(storage.object.unk2FB!=(expected[d][id]|4)||storage.object.unk84.uh!=0xBEEF)return 1;}
  for(u32 i=0;i<94;i++)if(data[i]!=tables[d][i])return 1;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''.replace('TABLES',','.join(tables)).replace('EXPECTED',','.join(expected))
