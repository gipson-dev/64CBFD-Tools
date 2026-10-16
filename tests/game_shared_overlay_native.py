"""Native32 actual C with a valid backward framebuffer table and guest packets."""
import itertools

from tools.experiments import game_shared_overlay_pass as source
from tools.tests import game_shared_overlay_oracle as model

APIS={0x151D6778:('s32',('s32',)),0x1501A490:('s32',('s32','s16','s32','s32','s32','s32')),
    0x151D5E90:('s32',('s32','s32','s32','s32')),0x1501A680:('s32',('s32',)),
    0x151D61B0:('s32',('s32',)),0x1517EFAC:('s32',('s32',)),0x1517E28C:('s32',('s32','s32')),
    0x15172F70:('s32',('s32',)),0x15181EE0:('s32',('s32',)),0x1517F564:('s32',('s32',)),
    0x1508FD38:('s32',('s32',)),0x151674F8:('void *',('void *','s32','s16','s32')),
    0x15096934:('s32',('s32',))}
TYPES=('u8','s32','s32','s32','u8','u8','s8','s32','s32','s32','u8','s32')
HEADER='#include <ultra64.h>\n'+''.join('extern %s D_%08X;\n'%(ty,a) for (a,_),ty in zip(model.FIELDS,TYPES))+'''
extern s32 framebuffer_table[256];
#define D_8002AAEC framebuffer_table[255]
s32 func_150198FC(Gfx *);
'''+''.join('%s func_%08X(%s);\n'%(ret,a,','.join(args)) for a,(ret,args) in APIS.items())


def corpus():
    for count,phase,pattern,disabled,mode in itertools.product((0,1),(0,1,4,5,128,255),range(4),(0,255),(0,2,3,4,5,6,7,8,9)):
        yield model.fixture(count,phase,pattern,disabled,pattern&1),pattern,mode
    for phase in range(256):yield model.fixture(1,phase,phase%4,1),phase%4,4
    for page in range(256):
        memory=model.fixture(1,0,page%4,1);memory[model.PAGE]=page
        yield memory,page%4,3
    for dimensions in ((0,1),(1,0),(-1,-1),(4096,4095),(16777217,16777219),(-16777217,16777219)):
        yield model.fixture(-1,0,1,1,dimensions=dimensions),1,0
    for count in (-0x80000000,0x7FFFFFFF):yield model.fixture(count,0,1,1),1,0


def program():
    literal=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    rows=[]
    for initial,pattern,mode in corpus():
        final,calls,observations,returns,_,result=model.reference(initial,pattern,mode)
        packets=['{0x%Xu,%s,%s,0x%Xu}'%(target,literal((*args,*([0]*(6-len(args))))),literal(state),value)
            for (target,args),(_,state),value in zip(calls,observations,returns)]
        changes=[]
        for index in range(1024):
            address=0x50000+index*4
            old,new=model.read(initial,address),model.read(final,address)
            if old!=new:changes.append('{%d,0x%Xu}'%(index,new))
        assert len(changes)<=6 and len(calls)<=16
        rows.append('{%d,%d,%s,%s,0x%Xu,%d,{%s},%d,{%s}}'%(pattern,mode,
            literal(model.snapshot(initial)),literal(model.snapshot(final)),result,len(calls),
            ','.join(packets),len(changes),','.join(changes)))
    wrappers=[]
    for address,(result,types) in APIS.items():
        params=','.join(ty+' a%d'%i for i,ty in enumerate(types))
        args=['canon((u32)a%d)'%i for i in range(len(types))]+['0']*(6-len(types))
        wrappers.append('%s func_%08X(%s){return (%s)uncanon(notify(0x%Xu,%s));}'%(result,address,params,result,address,','.join(args)))
    definitions=''.join('%s D_%08X;\n'%(ty,a) for (a,_),ty in zip(model.FIELDS,TYPES))
    getters=[];setters=[]
    for i,((address,size),ty) in enumerate(zip(model.FIELDS,TYPES)):
        name='D_%08X'%address
        getters.append('case %d:return (u32)(%s)%s;'%(i,'u8' if size==1 else 'u32',name))
        setters.append('case %d:%s=(%s)value;break;'%(i,name,ty))
    return HEADER+'''
struct Packet{u32 target,args[6],state[13],result;};
struct Change{u32 index,value;};
struct Case{u32 pattern,mode,initial[13],final[13],result,count;
 struct Packet packets[16];u32 changes;struct Change patch[6];};
static const struct Case cases[]={'''+','.join(rows)+'''};
'''+definitions+'''
s32 framebuffer_table[256];static Gfx storage[512];
static const struct Case*c;static u32 cursor,names[16],counts[16];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 canon(u32 value){u32 base=(u32)storage;
 if(value>=base&&value<base+sizeof(storage))return 0x50000u+value-base;return value;}
static u32 uncanon(u32 value){if(value>=0x50000u&&value<0x51000u)return (u32)storage+value-0x50000u;return value;}
static u32 buffer_hash(void){u32 i,value=2166136261u;for(i=0;i<128;i++){
 u32 word=canon((i&1)?storage[i/2].words.w1:storage[i/2].words.w0);value=(value^word)*16777619u;}return value;}
static u32 get(u32 field){switch(field){'''+''.join(getters)+'''case 12:return buffer_hash();}die(29);return 0;}
static void set(u32 field,u32 value){switch(field){'''+''.join(setters)+'''}}
static void effect(u32 target,u32 ordinal){
 if(c->mode==1&&target==0x151D6778u)D_80082FA0=-1;
 if(c->mode==2&&target==0x1501A490u){D_800BEAC0=1;D_80082F90=0;}
 if(c->mode==3&&target==0x151D5E90u&&ordinal==1){D_80082F90=7;D_800BE9C0=255;D_800BE9C4=(s32)0x81718004u;}
 if(c->mode==3&&target==0x1501A680u)D_80082F90=(s8)128;
 if(c->mode==4&&target==0x151D61B0u){D_80082F90=(s8)128;D_800BE9C4=(s32)0x81718004u;}
 if(c->mode==5&&target==0x1517EFACu)D_800BE9F0=(s32)0x87654321u;
 if(c->mode==6&&target==0x1517F564u){D_800BEAC0=0;D_800BEAC1=1;}
 if(c->mode==7&&target==0x1517F564u){D_800BEAC0=1;D_800BEAC1=0;}
 if(c->mode==8&&target==0x1501A490u){D_800BEAC0=0;D_80082F90=-1;}
 if(c->mode==9&&target==0x151D5E90u&&ordinal==1){D_800BE620=4096;D_800BE624=1;D_800BE9C4=(s32)0x81718004u;}
}
static u32 notify(u32 target,u32 a,u32 b,u32 d,u32 e,u32 f,u32 g){const struct Packet*p;u32 i,slot;
 u32 args[6]={a,b,d,e,f,g};if(cursor>=c->count)die(21);p=&c->packets[cursor++];
 if(p->target!=target)die(21);for(i=0;i<6;i++)if(args[i]!=p->args[i])die(21);
 for(i=0;i<13;i++)if(get(i)!=p->state[i])die(22);
 for(slot=0;slot<16&&names[slot]&&names[slot]!=target;slot++);if(slot==16)die(29);
 names[slot]=target;effect(target,++counts[slot]);return p->result;
}
'''+ '\n'.join(wrappers)+'''
static void run(void){u32 n,i,j,k,value,word;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(D_80082F90)!=1)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];cursor=0;
  for(i=0;i<16;i++)names[i]=counts[i]=0;
  for(i=0;i<256;i++)framebuffer_table[255-i]=(s32)(0x81200000u+i*0x1000);
  for(i=0;i<512;i++)storage[i].words.w0=storage[i].words.w1=0xA5A5A5A5u;
  for(i=0;i<12;i++)set(i,c->initial[i]);
  if(canon((u32)func_150198FC(storage+4))!=c->result)die(23);
  if(cursor!=c->count)die(24);for(i=0;i<13;i++)if(get(i)!=c->final[i])die(25);
  for(i=0;i<512;i++)for(j=0;j<2;j++){word=i*2+j;value=0xA5A5A5A5u;
   for(k=0;k<c->changes;k++)if(c->patch[k].index==word)value=c->patch[k].value;
   if(canon(j?storage[i].words.w1:storage[i].words.w0)!=value)die(26);}
  for(i=0;i<256;i++)if((u32)framebuffer_table[255-i]!=0x81200000u+i*0x1000)die(27);
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(unsigned_phase=body.replace('D_80082F90 < 5','(u8)D_80082F90 < 5'),
        wrong_increment=body.replace('D_80082F90++;','D_80082F90--;'),
        wrong_viewport_gate=body.replace('D_80082FA0 != 0','D_80082FA0 > 0'),
        wrong_table_page=body.replace('[-(s32)D_800BE9C0]','[-(s32)(D_800BE9C0 ^ 1)]'),
        wrong_scissor=body.replace('D_800BE620, D_800BE624);','D_800BE624, D_800BE620);'),
        cached_flags=body.replace('s32 func_150198FC(Gfx *commands) {','s32 func_150198FC(Gfx *commands) {\n    u8 disabled = D_800BEAC0;').replace('if (D_800BEAC0','if (disabled'),
        preserve_callback_phase=body.replace('            D_80082F90 = 1;','            D_80082F90 = D_80082F90;'),
        dropped_result=body.replace('return func_15096934((s32)commands);','func_15096934((s32)commands);\n    return (s32)commands;'))
