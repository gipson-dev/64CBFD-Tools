"""Separate-unit native32 fixture with Python-generated protocol/data expectations."""
import itertools

from tools.experiments import game_frame_sequence as source
from tools.tests import game_frame_sequence_oracle as model

HEADER = '''#include <ultra64.h>
extern s32 D_80082FA0,D_800BE9F0;
extern u8 D_800BEAC0,D_800D23A9,D_800BE616,D_800CC2B0,D_800BE9C0;
extern u32 age_storage[1024];
#define D_80043B40 age_storage[4]
'''+model.PROTOTYPES+'\ns32 func_15019130(void);\n'


def program():
    rows=[]
    literal=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    corpus=list(itertools.product((-1,0,1,3),range(4),range(8)))+[(v,3,8) for v in (254,255,256)]
    globals_=(model.COUNT,model.CONTEXT,model.DISABLED,model.FLAG,model.EXTERNAL,model.CC,model.PAGE,model.RESET)
    for count,pattern,mode in corpus:
        initial=model.fixture(count,pattern,(0,1,128,255)[pattern])
        final,calls,_=model.reference(initial,mode)
        def values(memory):
            return [model.read(memory,a) if a in (model.COUNT,model.CONTEXT) else memory[a] for a in globals_]
        packets=['{0x%Xu,%s}'%(target,literal((*args,*([0]*(2-len(args)))))) for target,args in calls]
        ages=[model.read(final,model.TABLE+i*8+4) for i in range(508)]
        rows.append('{%d,%d,%s,%s,%d,{%s},%s}'%(pattern,mode,literal(values(initial)),literal(values(final)),
            len(calls),','.join(packets),literal(ages)))
    wrappers=[]
    for target,(name,result,arity) in sorted(model.SIGNATURES.items()):
        args=', '.join('s32 a%d'%i for i in range(arity)) or 'void'
        values=['(u32)a%d'%i for i in range(arity)]+['0']*(2-arity)
        wrappers.append('%s %s(%s){notify(0x%Xu,%s);%s}'%(result,name,args,target,','.join(values),
            'return (s32)0xAABB1234u;' if result=='s32' else ''))
    return HEADER+'''
struct Packet{u32 target,args[2];};
struct Case{u32 pattern,mode,initial[8],final[8],count;struct Packet packets[640];u32 ages[508];};
static const struct Case cases[]={'''+','.join(rows)+'''};
s32 D_80082FA0,D_800BE9F0;u8 D_800BEAC0,D_800D23A9,D_800BE616,D_800CC2B0,D_800BE9C0,D_800DCD27;
u32 age_storage[1024];static const struct Case*c;static u32 cursor,second,prepares;
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void notify(u32 target,u32 a,u32 b){const struct Packet*p;
 if(cursor>=c->count)die(21);p=&c->packets[cursor++];
 if(p->target!=target||p->args[0]!=a||p->args[1]!=b)die(21);
 if(target==0x10004250u&&D_800DCD27)die(22);
 if(target==0x1510B690u)second++;if(target==0x15094EA0u)prepares++;
 if(c->mode==1&&target==0x15113E54u)D_800BEAC0=1;
 if(c->mode==1&&target==0x15018DFCu)D_800BEAC0=0;
 if(c->mode==2&&target==0x15177A94u)D_800BEAC0=1;
 if(c->mode==3&&target==0x1510FC34u&&!a)D_80082FA0=D_80082FA0==0?3:-1;
 if(c->mode==3&&target==0x1510B690u&&second==2)D_80082FA0=1;
 if(c->mode==4&&target==0x151749F8u)D_800BE9F0=(s32)0x87654321u;
 if(c->mode==4&&target==0x1501C860u)D_800BE9C0=255;
 if(c->mode==5&&target==0x15034F20u)age_storage[4+507*2+1]=0x7FFFFFFFu;
 if(c->mode==5&&target==0x1515D6C8u){age_storage[5]=0xFFFFFFFFu;age_storage[4+253*2+1]=0x80000000u;}
 if(c->mode==6&&target==0x15113180u)D_800BEAC0=0;
 if(c->mode==6&&target==0x1501E2F8u)D_800D23A9=128;
 if(c->mode==6&&target==0x1502BEE4u)D_800BE616=0;
 if(c->mode==6&&target==0x15113C88u)D_800CC2B0=1;
 if(c->mode==7&&target==0x15094EA0u&&prepares==1)D_80082FA0=D_80082FA0==0?3:-1;
 if(c->mode==8&&target==0x15094EA0u&&a==255)D_80082FA0=0;
 if(c->mode==8&&target==0x15094EA0u&&!a&&prepares>=257)D_80082FA0=-1;
}
'''+ '\n'.join(wrappers)+'''
static void run(void){u32 n,i;u32 final[8];
 if(sizeof(void*)!=4)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];cursor=second=prepares=0;
  D_80082FA0=(s32)c->initial[0];D_800BE9F0=(s32)c->initial[1];
  D_800BEAC0=(u8)c->initial[2];D_800D23A9=(u8)c->initial[3];D_800BE616=(u8)c->initial[4];
  D_800CC2B0=(u8)c->initial[5];D_800BE9C0=(u8)c->initial[6];D_800DCD27=(u8)c->initial[7];
  for(i=0;i<1024;i++)age_storage[i]=0xA55A1234u;
  for(i=0;i<508;i++){static const u32 edges[5]={0,1,0x7FFFFFFFu,0xFFFFFFFFu,0x80000000u};
   age_storage[4+i*2]=0xD15A0000u+i;age_storage[5+i*2]=edges[(i+c->pattern)%5];}
  if(func_15019130()!=1)die(23);if(cursor!=c->count)die(24);
  for(i=0;i<508;i++)if(age_storage[4+i*2]!=0xD15A0000u+i||age_storage[5+i*2]!=c->ages[i])die(25);
  for(i=0;i<4;i++)if(age_storage[i]!=0xA55A1234u||age_storage[1020+i]!=0xA55A1234u)die(26);
  final[0]=(u32)D_80082FA0;final[1]=(u32)D_800BE9F0;final[2]=D_800BEAC0;final[3]=D_800D23A9;
  final[4]=D_800BE616;final[5]=D_800CC2B0;final[6]=D_800BE9C0;final[7]=D_800DCD27;
  for(i=0;i<8;i++)if(final[i]!=c->final[i])die(27);
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(cached_disabled=body.replace('    u8 slot;','    u8 slot;\n    u8 disabled = D_800BEAC0;').replace(
            'if (D_800BEAC0 == 0)','if (disabled == 0)'),
        cached_bound=body.replace('    u8 slot;','    u8 slot;\n    s32 bound = D_80082FA0;').replace('<= D_80082FA0','<= bound'),
        zero_return=body.replace('return 1;','return 0;'),
        too_many_ages=body.replace('view < 508','view < 509'),
        age_tag=body.replace('[view * 2 + 1]','[view * 2]'),
        widened_second_loop=body.replace('u8 slot;','s32 slot;'),
        narrowed_first_loop=body.replace('view <= D_80082FA0; view++','view <= D_80082FA0; view = (u8)(view + 1)'))
