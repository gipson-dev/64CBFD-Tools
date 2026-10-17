"""Native32 complete aggregate, compiled progress leaf and sequence gate."""
from tools.tests import game_color_channel_aggregate_oracle as model

HEADER='''#include <ultra64.h>
struct Bank{u32 pre;u8 bytes[0xB0];u32 post;};extern struct Bank bank;
struct Script{u32 pre;s32 timer;u8 stage;s16 fade;s8 left,right;u8 flag;s16 state;u8 command;u32 post;};extern struct Script script;
extern s32 *p_limit,*p_ticks,*p_limits;extern f32 *p_states;extern s8 *p_modes;extern u8 *p_busy;
s32 func_1517EFDC(void);s32 func_1517EF00(s32);s32 actual_progress(s32);void func_151E8214(void);
'''
MACROS='''#define D_80082FA0 (*p_limit)
#define D_800DDDC8 p_states
#define D_800DDDC0 p_busy
#define D_800DDDAC p_modes
#define D_800DDDB0 p_ticks
#define D_800DDE28 p_limits
#define D_800E0A90 script.timer
#define D_800E0B94 script.stage
#define D_8008FDCC script.fade
#define D_8008FD8C script.left
#define D_8008FD90 script.right
#define D_8008FDA4 script.flag
#define D_800E0A80 script.state
#define D_800D2E43 script.command
'''


def cases():
    for kind,fixtures in ((0,model.cases()),(1,model.script_cases())):
        for memory,config,g in fixtures:
            ref=(model.Reference if kind==0 else model.ScriptReference)(memory,config,g)
            try:result=ref.run()
            except model.progress.DivisionTrap:continue
            yield kind,memory,config,g,ref,0 if result is None else result


def script_values(memory):
    return [model.read(memory,at,width) if at in memory else 0xA5A5A5A5&((1<<(width*8))-1) for _,at,width in model.SCRIPT]


def program():
    initial=[];final=[];rows=[]
    for kind,memory,config,g,ref,result in cases():
        at=len(initial);initial.extend(memory[model.BASE+i] for i in range(model.LENGTH))
        final.extend(ref.memory[model.BASE+i] for i in range(model.LENGTH))
        limit_offset=g['limit']-model.BASE if model.BASE<=g['limit']<model.BASE+model.LENGTH else 0xFFFFFFFF
        count=sum(target==g['progress'] for target,_ in ref.calls)
        values=(kind,int(config['actual']),config['action'],g['states']-model.BASE,limit_offset,
            model.read(memory,g['limit']),model.read(ref.memory,g['limit']),result,count,at)
        fields=','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)
        arrays=[model.RETURNS[config['pattern']%len(model.RETURNS)],script_values(memory),script_values(ref.memory)]
        rows.append('{'+fields+','+','.join('{'+','.join('0x%Xu'%(x&0xFFFFFFFF) for x in array)+'}' for array in arrays)+'}')
    return HEADER+'''
struct Bank bank;static struct Bank wanted;
struct Script script;static struct Script wanted_script;
s32*p_limit,*p_ticks,*p_limits;f32*p_states;s8*p_modes;u8*p_busy;
static u32 limitbox[3],wanted_limits[3],calls,channels[8];
struct Case{u32 kind,actual,action,states,limit_offset,limit,final_limit,result,count,at,returns[4],script[8],final_script[8];};
static const struct Case*current;
'''+ 'static const u8 initial[]={'+','.join(map(str,initial))+'};\n'+ \
        'static const u8 final[]={'+','.join(map(str,final))+'};\n'+ \
        'static const struct Case cases[]={'+','.join(rows)+'};\n'+HARNESS


HARNESS=r'''
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 big(const u8*p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void lanes(struct Bank*b,const u8*p,u32 states){u32 i,k,at,offsets[3]={0x20,0x98,states};
 for(k=0;k<3;k++)for(i=0;i<4;i++){at=offsets[k]+i*4;*(u32*)(b->bytes+at)=big(p+at);}
}
static void script_values(struct Script*s,const u32*p){
 s->timer=(s32)p[0];s->stage=(u8)p[1];s->fade=(s16)p[2];s->left=(s8)p[3];
 s->right=(s8)p[4];s->flag=(u8)p[5];s->state=(s16)p[6];s->command=(u8)p[7];
}
s32 func_1517EF00(s32 channel){u32 n=(u32)channel;
 if(n>=4||calls>=8)die(22);channels[calls++]=n;
 if(current->actual)return actual_progress(channel);
 if(current->action==1&&n==0)*p_limit=-1;
 else if(current->action==2&&n==0)*p_limit=3;
 else if(current->action==3)*(u32*)(p_states+n)=(n&1)?0xBF800000:0x3F800000;
 else if(current->action==4&&n<2)*p_limit=n==0?1:-1;
 else if(current->action==5){*(u32*)(p_states+n)=0;*p_limit=n==0?3:0;}
 return (s32)current->returns[n];
}
void _start(void){u32 n,i,value;const struct Case*c;const u8*a,*b;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  c=&cases[n];current=c;fill(&bank,sizeof(bank));fill(&wanted,sizeof(wanted));
  copy(bank.bytes,initial+c->at,0xB0);lanes(&bank,initial+c->at,c->states);
  copy(wanted.bytes,final+c->at,0xB0);lanes(&wanted,final+c->at,c->states);
  fill(limitbox,sizeof(limitbox));fill(wanted_limits,sizeof(wanted_limits));
  p_limit=c->limit_offset==0xFFFFFFFF?(s32*)limitbox+1:(s32*)(bank.bytes+c->limit_offset);
  *p_limit=(s32)c->limit;if(c->limit_offset==0xFFFFFFFF)wanted_limits[1]=c->final_limit;
  p_states=(f32*)(bank.bytes+c->states);p_ticks=(s32*)(bank.bytes+0x20);p_limits=(s32*)(bank.bytes+0x98);
  p_busy=bank.bytes+0x30;p_modes=(s8*)(bank.bytes+0x1C);
  fill(&script,sizeof(script));fill(&wanted_script,sizeof(wanted_script));
  script_values(&script,c->script);script_values(&wanted_script,c->final_script);calls=0;fill(channels,sizeof(channels));
  if(c->kind==0){value=(u32)func_1517EFDC();if(value!=c->result)die(22);}else func_151E8214();
  if(calls!=c->count)die(22);for(i=0;i<calls;i++)if(channels[i]!=i)die(22);
  a=(const u8*)&bank;b=(const u8*)&wanted;for(i=0;i<sizeof(bank);i++)if(a[i]!=b[i])die(22);
  a=(const u8*)&script;b=(const u8*)&wanted_script;for(i=0;i<sizeof(script);i++)if(a[i]!=b[i])die(22);
  for(i=0;i<3;i++)if(limitbox[i]!=wanted_limits[i])die(22);
 }
 die(0);
}
'''
