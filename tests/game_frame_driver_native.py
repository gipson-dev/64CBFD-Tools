"""Separate native32 driver fixture; opaque providers use guest-qualified packets."""
import itertools
import re

from tools.experiments import game_frame_driver as source
from tools.tests import game_frame_driver_oracle as model

TYPES={model.COUNT:'s32',model.CURSOR:'Gfx *',model.INDEX:'s32',model.PAGE:'u8',model.OLD:'u8',
    model.NEXT:'u8',model.HOLD:'u8',model.STOP:'u8',model.RESET:'u8',0x800BE9B4:'u8',
    0x800BEAA8:'u16',model.PENDING:'s32',model.UCODE:'u8',0x800D9AF0:'u8',0x800D9B18:'u8',
    0x8002AC60:'u8',0x8002AC64:'u16',0x800BEB9C:'void *',model.LIMIT:'s32'}
PROTOTYPES=source.DECLARATIONS.replace('extern Gfx *D_800BE9C8, *D_800BE9CC;\n','')+'''
s32 func_1501A680(s32);
s32 func_15019130(void);
s32 func_1515D6D0(s32, s32);
s32 func_150195A0(s32, s32);
s32 func_150198FC(s32);
s32 func_15019CC8(s32, s32);
s32 func_151DCFD8(s32);
void func_10004074(void *);
void func_10004674(void);
void func_1000E2F4(s32);
void func_10011E94(s32);
s32 func_1501878C(void);
'''
HEADER='#include <ultra64.h>\n'+''.join('extern %s D_%08X;\n'%(ty,a) for a,ty in TYPES.items())+'''
extern OSMesgQueue D_800BEA10;
extern Gfx *frame_base_pointers[256];
#define D_800BE9C8 frame_base_pointers[0]
#define D_800BE9CC frame_base_pointers[1]
'''+PROTOTYPES


def corpus():
    yield from ((1,c,p,d,0,m,None) for c,p,d,m in itertools.product((-1,0,1,3),range(4),(0,1),range(8)))
    yield from ((2,0,p,0,stop,m,None) for p,stop,m in itertools.product(range(4),(0,1),(0,8,9)))
    yield from ((code,0,0,0,0,0,None) for code in (-32768,-1,0,3,32767))
    yield from ((1,-1,p,old,0,0,next_) for p,old,next_ in itertools.product(range(4),(0,1),(0,1)) if old!=next_)


def program():
    literal=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    rows=[]
    for code,count,pattern,disabled,stop,mode,next_ in corpus():
        initial=model.fixture(code,count,pattern,disabled,stop)
        if next_ is not None:initial[model.NEXT]=next_
        final,calls,observations,returns,_,value,halt=model.reference(initial,pattern,mode)
        assert not halt and len(calls)<=128
        packets=[]
        for (target,args),(_,state),returned in zip(calls,observations,returns):
            if target==model.RECV:args=(args[0],model.POINTER_OUT,args[2])
            packets.append('{0x%Xu,%s,%s,0x%Xu}'%(target,literal((*args,*([0]*(3-len(args))))),literal(state),returned))
        changes=[]
        for bank,base in enumerate(model.BUFFERS):
            for index in range(2056):
                address=base+(index-4)*4
                old,new=model.read(initial,address),model.read(final,address)
                if new!=old:changes.append('{%d,%d,0x%Xu}'%(bank,index,new))
        assert len(changes)<=20
        rows.append('{%d,%d,%d,%s,%s,%d,%d,{%s},%d,{%s}}'%(code,pattern,mode,
            literal(model.snapshot(initial)),literal(model.snapshot(final)),value,len(calls),','.join(packets),len(changes),','.join(changes)))
    wrappers=[]
    for result,name,args in re.findall(r'(void|s32|Gfx \*)\s*(func_[0-9A-F]+)\(([^;{}]*)\);',PROTOTYPES):
        target=int(name[5:],16)
        types=[] if args=='void' else [v.strip() for v in args.split(',')]
        params=', '.join(ty+' a%d'%i for i,ty in enumerate(types)) or 'void'
        values=['canon((u32)a%d)'%i for i in range(len(types))]+['0']*(3-len(types))
        invoke='notify(0x%Xu,%s)'%(target,','.join(values))
        tail=invoke+';' if result=='void' else 'return (%s)uncanon(%s);'%(result,invoke)
        if name!='func_1501878C':wrappers.append('%s %s(%s){%s}'%(result,name,params,tail))
    getters=[];setters=[]
    for i,(a,_) in enumerate(model.FIELDS):
        name='D_%08X'%a
        ty='Gfx *' if a in (model.BASES,model.BASES+4) else TYPES[a]
        getters.append('case %d:return canon((u32)%s);'%(i,name))
        setters.append('case %d:%s=(%s)%s;break;'%(i,name,ty,'uncanon(value)' if '*' in ty else 'value'))
    definitions=''.join('%s D_%08X;\n'%(ty,a) for a,ty in TYPES.items())
    return HEADER+'''
struct Packet{u32 target,args[3],state['''+str(len(model.FIELDS))+'''],result;};
struct Change{u32 bank,index,value;};
struct Case{s32 code;u32 pattern,mode,initial['''+str(len(model.FIELDS))+'''],final['''+str(len(model.FIELDS))+'''],result,count;
 struct Packet packets[128];u32 changes;struct Change patch[20];};
static const struct Case cases[]={'''+','.join(rows)+'''};
'''+definitions+'''
OSMesgQueue D_800BEA10;Gfx *frame_base_pointers[256];
u8 D_800C1060[8],D_800BE630[256];Mtx D_80089470;LookAt D_800D9B90[256];
static Gfx storage[5124];static const struct Case*c;static u32 cursor,callbacks[64],names[64];
static u16 delivered;
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 canon(u32 value){u32 base=(u32)storage;
 if(value>=base&&value<base+sizeof(storage))return 0x4FFF0u+value-base;
 if(value==(u32)&D_800BEA10)return 0x800BEA10u;
 if(value==(u32)D_800C1060)return 0x800C1060u;
 if(value==(u32)&D_80089470)return 0x80089470u;
 base=(u32)D_800D9B90;if(value>=base&&value<base+sizeof(D_800D9B90))return 0x800D9B90u+value-base;
 return value;}
static u32 uncanon(u32 value){
 if(value>=0x4FFF0u&&value<0x5A010u)return (u32)storage+value-0x4FFF0u;
 return value;}
static u32 get(u32 field){switch(field){'''+''.join(getters)+'''}die(29);return 0;}
static void set(u32 field,u32 value){switch(field){'''+''.join(setters)+'''}}
static void effect(u32 target,u32 ordinal){
 if(c->mode==1&&target==0x151E51ECu)D_800BE615=1;
 if(c->mode==2&&target==0x1501A39Cu)D_800BE614=7;
 if(c->mode==2&&target==0x1510B3B0u)D_800D9B18=1;
 if(c->mode==4&&target==0x15018F80u&&ordinal==1)D_80082FA4=(s32)0x12348001u;
 if(c->mode==4&&target==0x15019464u&&ordinal==1)D_80082FA0=-1;
 if(c->mode==4&&target==0x15019414u)D_80082FA0=1;
 if(c->mode==5&&target==0x1515D69Cu)D_800BE9D0=(Gfx*)uncanon(0x58020u);
 if(c->mode==5&&target==0x1515D6D0u)D_80082FA4=(s32)0x12348001u;
 if(c->mode==5&&target==0x150195A0u&&ordinal==1){D_800BE9C0=1;D_800BEBA4=0;}
 if(c->mode==6&&target==0x15019CC8u){D_800BEAC0=0;D_80082FA0=0;}
 if(c->mode==6&&target==0x15019E60u){D_800BEAC0=0;D_80082FA0=0;}
 if(c->mode==6&&target==0x15019BB8u)D_80082FA0=ordinal==1?2:-1;
 if(c->mode==7&&target==0x1000E2F4u){D_800BEAC0=128;D_800BEAC1=255;}
 if(c->mode==8&&target==0x1517E1ACu)D_800DC9F0=1;
 if(c->mode==8&&target==0x151412BCu){D_800BEAA8=1;D_800BE615=1;}
 if(c->mode==9&&target==0x10004074u&&ordinal==1){frame_base_pointers[1]=(Gfx*)uncanon(0x58090u);frame_base_pointers[0]=(Gfx*)uncanon(0x500A0u);}
}
static u32 notify(u32 target,u32 a,u32 b,u32 d){const struct Packet*p;u32 i,slot;
 if(cursor>=c->count)die(21);p=&c->packets[cursor++];
 if(p->target!=target||p->args[0]!=a||p->args[1]!=b||p->args[2]!=d)die(21);
 for(i=0;i<sizeof(c->initial)/sizeof(c->initial[0]);i++)if(get(i)!=p->state[i])die(22);
 for(slot=0;slot<64&&names[slot]&&names[slot]!=target;slot++);if(slot==64)die(29);
 names[slot]=target;callbacks[slot]++;effect(target,callbacks[slot]);return p->result;
}
s32 osRecvMesg(OSMesgQueue*q,OSMesg*out,s32 flag){u32 result;
 if(q!=&D_800BEA10||*out||flag!=1)die(22);
 result=notify(0x10023440u,0x800BEA10u,0xF0000001u,1);*out=&delivered;return (s32)result;}
'''+ '\n'.join(wrappers)+'''
static void run(void){u32 n,i,j,k,v,word;static const u32 offsets[4]={0,1,128,255};
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(LookAt)!=32)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];cursor=0;delivered=(u16)c->code;
  for(i=0;i<64;i++)callbacks[i]=names[i]=0;
  for(i=0;i<5124;i++)storage[i].words.w0=storage[i].words.w1=0xA5A5A5A5u;
  for(i=0;i<256;i++){D_800BE630[i]=(u8)(i+offsets[c->pattern]);frame_base_pointers[i]=(Gfx*)uncanon((i&1)?0x58000u:0x50000u);}
  for(i=0;i<sizeof(c->initial)/sizeof(c->initial[0]);i++)set(i,c->initial[i]);
  if((u32)func_1501878C()!=c->result)die(23);if(cursor!=c->count)die(24);
  for(i=0;i<sizeof(c->initial)/sizeof(c->initial[0]);i++)if(get(i)!=c->final[i])die(25);
  for(i=0;i<5124;i++)for(j=0;j<2;j++){v=0xA5A5A5A5u;word=i*2+j;
   for(k=0;k<c->changes;k++)if(c->patch[k].bank*8192+c->patch[k].index==word)v=c->patch[k].value;
   if(canon(j?storage[i].words.w1:storage[i].words.w0)!=v)die(26);}
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(cached_stop=body.replace('D_800BE615','cachedStop').replace('    OSMesg message',
            '    u8 cachedStop = D_800BE615;\n    OSMesg message',1),
        cached_count=body.replace('D_80082FA0','cachedCount').replace('    OSMesg message',
            '    s32 cachedCount = D_80082FA0;\n    OSMesg message',1),
        wrong_rollback=body.replace('D_800BE9D0 = savedCommands;', 'D_800BE9D0 = savedCommands + 1;'),
        wrong_light_slot=body.replace('(u8 *)(D_800D9B90 + D_800BE9C0) + 16, 1);',
            '(u8 *)(D_800D9B90 + D_800BE9C0) + 16, 2);'),
        wrong_halfword=body.replace('func_150195A0((s32)D_800BE9D0, (s16)D_80082FA4)',
            'func_150195A0((s32)D_800BE9D0, D_80082FA4)'),
        wrong_return=body.replace('return 1;', 'return 0;'),
        wrong_counter=body.replace('(*(s16 *)&D_800BEAA8)--;', '(*(s16 *)&D_800BEAA8)++;'))
