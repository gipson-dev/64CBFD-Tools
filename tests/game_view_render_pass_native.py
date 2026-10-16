"""Native32 execution of the recovered C using guest-qualified opaque packets."""
import itertools

from tools.experiments import game_view_render_pass as source
from tools.tests import game_view_render_pass_oracle as model

APIS={
    0x1517EFAC:('s32',('s32',)),0x1510B7B4:('s32',('s32','s32')),
    0x1515D6D0:('s32',('s32','s32')),0x1510B958:('void',('s32',)),
    0x1501A490:('s32',('s32','s16','s32','s32','s32','s32')),
    0x151135C4:('s32',('s32','s32','s16')),0x151D6778:('s32',('s32',)),
    0x151674F8:('void *',('void *','s32','s16','s32')),
    0x15186794:('s32',('s32','s32')),0x1502BAD0:('Gfx *',('Gfx *','s32','s16')),
    0x15035FE8:('s32',('s32','s32')),0x15018E88:('s32',('void *','s16')),
    0x15018F08:('void *',('void *','s16')),0x15188D00:('s32',('s32','s32','s16'))}
HEADER='#include <ultra64.h>\n#include "structs.h"\n'+'''
extern struct108 *D_800DBFF0;
extern u8 D_800BEAC0,D_800BE9C0,D_800BE575;
extern s16 D_80084480;
extern u16 D_800D18A0;
extern s32 D_80082FA0,D_800BE628;
extern Mtx D_80089470;
s32 func_150195A0(Gfx *,s16);
'''+''.join('%s func_%08X(%s);\n'%(ret,a,','.join(args)) for a,(ret,args) in APIS.items())


def corpus():
    yield from itertools.product(range(4),(-1,0,1),range(4),(0,),range(7))
    yield from itertools.product(range(4),(1,),range(4),(1,2,3,4),(0,))


def program():
    literal=lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    rows=[]
    for view,count,pattern,gate,mode in corpus():
        initial=model.fixture(view,count,pattern,gate)
        final,calls,observations,returns,_,result=model.reference(initial,view,pattern,gate,mode)
        packets=['{0x%Xu,%s,%s,0x%Xu}'%(target,literal((*args,*([0]*(6-len(args))))),literal(state),value)
            for (target,args),(_,state),value in zip(calls,observations,returns)]
        changes=[]
        for index in range(1024):
            address=0x50000+index*4
            old,new=model.read(initial,address),model.read(final,address)
            if old!=new:changes.append('{%d,0x%Xu}'%(index,new))
        assert len(changes)<=4 and len(calls)<=24
        rows.append('{%d,%d,%d,%d,%s,%s,0x%Xu,%d,{%s},%d,{%s}}'%(view,pattern,gate,mode,
            literal(model.snapshot(initial,view)),literal(model.snapshot(final,view)),result,len(calls),
            ','.join(packets),len(changes),','.join(changes)))
    wrappers=[]
    for address,(result,types) in APIS.items():
        params=','.join(ty+' a%d'%i for i,ty in enumerate(types))
        args=['canon((u32)a%d)'%i for i in range(len(types))]+['0']*(6-len(types))
        invoke='notify(0x%Xu,%s)'%(address,','.join(args))
        tail=invoke+';' if result=='void' else 'return (%s)uncanon(%s);'%(result,invoke)
        wrappers.append('%s func_%08X(%s){%s}'%(result,address,params,tail))
    getters=[];setters=[]
    types=('struct108 *','u8','s16','u16','s32','s32','u8','u8')
    for i,((address,size),ty) in enumerate(zip(model.FIELDS,types)):
        name='D_%08X'%address
        getters.append('case %d:return canon((%s)%s);'%(i,'u16' if size==2 else 'u32',name))
        setters.append('case %d:%s=(%s)%s;break;'%(i,name,ty,'uncanon(value)' if '*' in ty else 'value'))
    return HEADER+'''
struct Packet{u32 target,args[6],state[10],result;};
struct Change{u32 index,value;};
struct Case{u32 view,pattern,gate,mode,initial[10],final[10],result,count;
 struct Packet packets[24];u32 changes;struct Change patch[4];};
static const struct Case cases[]={'''+','.join(rows)+'''};
struct108 *D_800DBFF0;u8 D_800BEAC0,D_800BE9C0,D_800BE575;
s16 D_80084480;u16 D_800D18A0;s32 D_80082FA0,D_800BE628;Mtx D_80089470;
static struct108 views[4],other[4];static Gfx storage[512];
static const struct Case*c;static u32 cursor,names[24],counts[24];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static u32 canon(u32 value){u32 base=(u32)storage;
 if(value>=base&&value<base+sizeof(storage))return 0x50000u+value-base;
 base=(u32)views;if(value>=base&&value<base+sizeof(views))return 0x30000u+value-base;
 base=(u32)other;if(value>=base&&value<base+sizeof(other))return 0x40000u+value-base;
 if(value==(u32)&D_80089470)return 0x80089470u;return value;}
static u32 uncanon(u32 value){if(value>=0x50000u&&value<0x51000u)return (u32)storage+value-0x50000u;
 if(value>=0x30000u&&value<0x32680u)return (u32)views+value-0x30000u;
 if(value>=0x40000u&&value<0x42680u)return (u32)other+value-0x40000u;return value;}
static u32 get(u32 field){switch(field){'''+''.join(getters)+'''
 case 8:return (u32)views[c->view].unk5F0;case 9:return (u32)other[c->view].unk5F0;}die(29);return 0;}
static void set(u32 field,u32 value){switch(field){'''+''.join(setters)+'''
 case 8:views[c->view].unk5F0=(s32)value;break;case 9:other[c->view].unk5F0=(s32)value;break;}}
static void effect(u32 target,u32 ordinal){
 if(c->mode==1&&target==0x1517EFACu)D_800D18A0=(u16)(1u<<c->view);
 if(c->mode==2&&target==0x1517EFACu)D_80082FA0=0x7FFFFFFF;
 if(c->mode==3&&target==0x1510B958u){D_800BE628=(s32)0x80507FFCu;D_800BE9C0=255;}
 if(c->mode==4&&target==0x151135C4u&&ordinal==1)D_800BE575=2;
 if(c->mode==5&&target==0x15035FE8u){D_800DBFF0=other;views[c->view].unk5F0^=1;}
 if(c->mode==6&&target==0x1517EFACu)D_800DBFF0=other;
}
static u32 notify(u32 target,u32 a,u32 b,u32 d,u32 e,u32 f,u32 g){const struct Packet*p;u32 i,slot;
 u32 args[6]={a,b,d,e,f,g};if(cursor>=c->count)die(21);p=&c->packets[cursor++];
 if(p->target!=target)die(21);for(i=0;i<6;i++)if(args[i]!=p->args[i])die(21);
 for(i=0;i<10;i++)if(get(i)!=p->state[i])die(22);
 for(slot=0;slot<24&&names[slot]&&names[slot]!=target;slot++);if(slot==24)die(29);
 names[slot]=target;effect(target,++counts[slot]);return p->result;
}
'''+ '\n'.join(wrappers)+'''
static void run(void){u32 n,i,j,k,value,word,at;u8*bytes;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(struct108)!=0x9A0||
    (u8*)&views[0].unk5F0-(u8*)views!=0x5F0)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];cursor=0;
  for(i=0;i<24;i++)names[i]=counts[i]=0;
  bytes=(u8*)views;for(i=0;i<sizeof(views);i++)bytes[i]=0xA5;
  bytes=(u8*)other;for(i=0;i<sizeof(other);i++)bytes[i]=0xA5;
  for(i=0;i<4;i++){views[i].unk5F0=(s32)(u32[]){0,1,0x80000000u,0xFFFFFFFFu}[c->pattern];other[i].unk5F0=(s32)~c->pattern;}
  for(i=0;i<512;i++)storage[i].words.w0=storage[i].words.w1=0xA5A5A5A5u;
  for(i=0;i<10;i++)set(i,c->initial[i]);
  if(canon((u32)func_150195A0(storage+4,(s16)c->view))!=c->result)die(23);
  if(cursor!=c->count)die(24);for(i=0;i<10;i++)if(get(i)!=c->final[i])die(25);
  for(i=0;i<512;i++)for(j=0;j<2;j++){word=i*2+j;value=0xA5A5A5A5u;
   for(k=0;k<c->changes;k++)if(c->patch[k].index==word)value=c->patch[k].value;
   if(canon(j?storage[i].words.w1:storage[i].words.w0)!=value)die(26);}
  for(k=0;k<2;k++){bytes=(u8*)(k?other:views);for(i=0;i<sizeof(views);i++){
   at=i%0x9A0;if(at>=0x5F0&&at<0x5F4)continue;if(bytes[i]!=0xA5)die(27);}}
 }}
void _start(void){run();die(0);}
'''


def controls():
    body=source.SELECTED
    return dict(wrong_flag=body.replace('state->unk5F0 & 1','state->unk5F0 & 2'),
        reversed_passes=body.replace('if (state->unk5F0 & 1)','if (!(state->unk5F0 & 1))'),
        wrong_stride=body.replace('view * 0x180','view * 0x100'),
        live_state_pointer=body.replace('state->unk5F0','D_800DBFF0[view].unk5F0').replace('    struct108 *state = &D_800DBFF0[view];\n',''),
        cached_mode=body.replace('    struct108 *state','    u8 cachedMode = D_800BE575;\n    struct108 *state').replace('if (D_800BE575 == 2)','if (cachedMode == 2)'),
        wrong_mode_gate=body.replace('D_800BE575 == 2','D_800BE575 >= 2'),
        dropped_result=body.replace('return (s32)func_151674F8(commands, 2, view, 1);',
            'func_151674F8(commands, 2, view, 1);\n    return (s32)commands;'))
