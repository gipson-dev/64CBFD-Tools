"""SDK native32 poller and typed Init return, against independent packet rows."""
from tools.experiments import game_channel_command_poller_candidates as source
from tools.tests import game_channel_command_poller_oracle as g


def controls():
    b=source.SELECTED
    return dict(wrong_opcode=b.replace('== 0x4C','== 0x4D'),
        unmasked_byte=b.replace('command[4] & 0x7F','command[4]'),
        wrong_divisor=b.replace('/= 367','/= 366'),
        missing_fallback=b.replace('duration = 20;','duration = 0;'),
        wrong_channel=b.replace('command[3] - 1','command[3]'),
        cached_index=b.replace('    s32 duration;','    s32 duration;\n    u8 savedIndex = D_800D18D0;').replace('D_800D18D0 * 0x32C','savedIndex * 0x32C'),
        positive_status=b.replace('!= 0)', '> 0)'))


def program():
    rows=[]
    array=lambda xs:'{'+','.join('0x%Xu'%g.u32(x)for x in xs)+'}'
    for c in g.cases():
        e=g.reference(g.fixture(c),c)
        messages='{'+','.join(array(m)for m in c.messages)+'}'
        actions='{'+','.join(array((a[0]-g.BASE,a[1],a[2]))for a in e['actions'])+'}'
        rows.append('{'+','.join((messages,array(map(len,c.messages)),array(c.statuses or tuple(map(len,c.messages))),str(len(c.messages)),str(c.index),str(c.mode),str(e['reads']),str(len(e['actions'])),actions,str(e['memory'][g.INDEX])))+'}')
    header=source.ROOT/source.BUILD/'qualified-functions.h'
    text='#include "'+str(header)+'"\n'+source.DECLARATION+source.QUEUE_DECL+'\n'+source.SELECTED+'\n'
    variants=controls()
    for n,b in variants.items():
        assert b!=source.SELECTED,n
        text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=r'''
u8 D_800D18D0,D_800CC2D0[256*0x32C];struct105 D_800427A0;
typedef struct{u8 message[4][256];u32 length[4],status[4],n,index,mode,reads,count,actions[4][3],finalIndex;}Row;
static const Row rows[]={'''+',\n'.join(rows)+r'''};
static const Row*c;static u32 reads,actions,bad,lost;static u8*escaped;
s32 func_15043CA4(struct105*q,u8*output,s32 capacity){u32 i,n=reads++;
 if(q!=&D_800427A0||capacity!=256||reads>8)bad=1;
 escaped=output;if(c->mode&1)D_800D18D0=(u8)(c->index+reads*37);
 if(n>=c->n)return 0;
 for(i=0;i<c->length[n];i++)output[i]=c->message[n][i];
 return(s32)c->status[n];}
'''+source.NEW_INIT.replace('return func_15043CA4(&D_800427A0, output, capacity);','s32 n = func_15043CA4(&D_800427A0, output, capacity);\n    return lost ? 0 : n;')+r'''
void func_15080430(u8*owner,s32 channel,s32 duration){u32 n=actions++,i;
 if(n>=c->count||owner!=D_800CC2D0+c->actions[n][0]||(u32)channel!=c->actions[n][1]||(u32)duration!=c->actions[n][2])bad=1;
 if(c->mode&2)D_800D18D0=(u8)(D_800D18D0+17);
 if(c->mode&4){static const u8 bytes[]={255,128,129,130};escaped[3]^=255;for(i=0;i<4;i++)escaped[4+i]=bytes[i];}}
static u32 run(void(*fn)(void),u32 lose){u32 i,fail=0;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){c=&rows[i];D_800D18D0=(u8)c->index;reads=actions=bad=0;lost=lose;fn();
 if(bad||reads!=c->reads||actions!=c->count||D_800D18D0!=c->finalIndex)fail++;}return fail;}
void _start(void){u32 mask=0;int result;if(run(func_15080228,0))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+',0))mask|='+str(1<<i)+';\n'
    text+='if(run(func_15080228,1))mask|=128;\nif(mask!=255)goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,[*variants,'lost_Init_return'],len(rows)
