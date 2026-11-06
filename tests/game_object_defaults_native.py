"""Native32 object bytes, call-boundary snapshots and pointer relocation."""
from functools import lru_cache
from tools.tests import game_object_defaults_oracle as model

def digest(data):
    v=2166136261
    for i,b in enumerate(data):
        if not 0x2C4<=i<0x2C8:v=((v^b)*16777619)&0xFFFFFFFF
    return v

def little(data):
    b=bytearray(data)
    for p,n in[(p,4)for p in(0x24,0x48,0x118,0x14C,0x150,0x180)]+[(p,2)for p in(0x38,0x84,0x18C,0x18E,0x190,0x192,0x194,0x196,0x198,0x19A,0x19C)]:b[p:p+n]=b[p:p+n][::-1]
    return b

@lru_cache(maxsize=1)
def rows(cases):
    result=[]
    for c in cases:
        expected=model.reference(model.fixture(c),c);m=expected['memory'];s=model.symbols();obs=[digest(little(v))for t,p,v in expected['observations']]
        result.append('{0x%Xu,0x%Xu,0x%Xu,%d,%d,%d,0x%016Xull,0x%Xu,{0x%Xu,0x%Xu},0x%Xu,0x%Xu,0x%016Xull}'%(c.random,c.base,c.gravity,c.mutation,c.connected,c.component,c.seed,digest(little(model.block(m,c.owner,0x32C))),*obs,model.read(m,s['D_8009962C']),model.read(m,s['D_80099630']),model.read(m,s['D_800885B0'],8)))
    return ',\n'.join(result)

def source(body,cases):
    return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
f32 D_8009962C,D_80099630;
s32 func_150ADA20(void) __attribute__((noinline));
void func_150615DC(struct127*) __attribute__((noinline));
typedef char object_size[sizeof(struct127)==0x32C?1:-1];
typedef char id_offset[__builtin_offsetof(struct127,unk84)==0x84?1:-1];
typedef char scale_offset[__builtin_offsetof(struct127,xz_scale)==0x14C?1:-1];
'''+body.replace('void func_1505F188(', '__attribute__((noinline)) void func_1505F188(',1)+r'''
typedef struct{u32 random,base,gravity,mutation,connected,component;u64 seed;u32 result,observations[2],base_after,gravity_after;u64 seed_after;}Row;
static const Row rows[]={
'''+rows(tuple(cases))+r'''
};
static struct{u32 before;struct127 object;u32 after;}storage;
static const Row*row;static u64 seed;static u32 ordinal,error,marks[2];
static void word(u8*p,u32 v){*(u32*)p=v;}
static u32 observe(void){u8*p=(u8*)&storage.object;u32 v=2166136261u;if(*(u32*)(p+0x2C4)!=(u32)p+4u)error=1;for(u32 i=0;i<0x32C;i++)if(i<0x2C4||i>=0x2C8)v=(v^p[i])*16777619u;return v;}
static void effect(u32 phase,struct127*object){u8*p=(u8*)object;
 if(phase==0&&(row->mutation&1)){word(p+0x48,0xFFC12345u);word((u8*)&D_8009962C,0x80000000u);word((u8*)&D_80099630,0x7FC54321u);}
 if(phase==1&&(row->mutation&2)){word(p+0x14C,0x80000000u);word(p+0x18C,0xFFFFFFFFu);*(u16*)(p+0x19C)=0xBEEF;p[0x1DD]=0x31;}
 marks[phase]=0xA5000000u+phase;
}
s32 func_150ADA20(void){if(ordinal++!=0||observe()!=row->observations[0])error=1;effect(0,&storage.object);u32 value=row->random;
 if(row->connected){u64 mixed=((seed<<63)>>31)|((seed<<31)>>32);mixed^=(seed<<44)>>32;seed=((mixed>>20)&0xFFFu)^mixed;value=(u32)seed;}
 __asm__ volatile("":::"eax","ecx","edx","memory");return(s32)value;
}
void func_150615DC(struct127*p){if(ordinal++!=1||p!=&storage.object||observe()!=row->observations[1])error=1;effect(1,p);
 if(row->component){p->unk7=255;p->unk8=255;p->unk9=0;p->unkA=0;p->unkE.ub[1]=0;p->unkB=p->unkC=p->unkD=p->unkE.ub[0]=255;}
 __asm__ volatile("":::"eax","ecx","edx","memory");
}
static void(*volatile probe)(struct127*)=func_1505F188;
static int run(void){
 for(u32 n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  row=&rows[n];u8*p=(u8*)&storage;for(u32 i=0;i<sizeof(storage);i++)p[i]=(u8)(i*29+123);storage.before=0x12345678u;storage.after=0x87654321u;
  word((u8*)&D_8009962C,row->base);word((u8*)&D_80099630,row->gravity);seed=row->seed;ordinal=error=0;marks[0]=marks[1]=0;probe(&storage.object);
  if(error||ordinal!=2||observe()!=row->result||storage.before!=0x12345678u||storage.after!=0x87654321u||*(u32*)&D_8009962C!=row->base_after||*(u32*)&D_80099630!=row->gravity_after||seed!=row->seed_after||marks[0]!=0xA5000000u||marks[1]!=0xA5000001u)return 1;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
