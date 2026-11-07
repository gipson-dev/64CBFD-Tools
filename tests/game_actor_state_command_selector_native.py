"""SDK native32 with valid record-array differences and eight effective controls."""
from dataclasses import replace
from tools.experiments import game_actor_state_command_selector_candidates as source
from tools.tests import game_actor_state_command_selector_oracle as g
def controls():
    b=source.SELECTED
    cached=b.replace('        if ((command ==','        u8 *state = (u8 *)actor->unk31C;\n        if ((command ==',1).replace('((u8 *)actor->unk31C)','state')
    base=b.replace('        if ((command ==','        struct178 *base = D_800D3098;\n        if ((command ==',1).replace('record - D_800D3098','record - base')
    return dict(wrong_special=b.replace('command == 0x2C','command == 0x2D'),wrong_fallback=b.replace('command = 0x1A','command = 0x1B'),wrong_protection=b.replace('& 0x80','& 0x40'),wrong_mask=b.replace('command & 7','command & 3'),wrong_index=b.replace('record - D_800D3098','record - D_800D3098 + 1'),cached_state=cached,cached_base=base,narrow_command=b.replace('        if ((command ==','        command = (u8)command;\n        if ((command ==',1))
def program():
    cases=[c for c in g.cases()if c.command<256]+[g.Case(command=v,query=0)for v in(256,0x7FFFFFFF,0x80000000,0xFFFFFFFF)]
    arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(x)for x in xs)+'}'
    rows=[]
    for c in cases:
        initial=g.fixture(c);m,calls=g.reference(initial,c);pending=g.read(m,g.PENDING)
        values=(c.command,c.secondary,c.active,c.gate,c.query,c.mask,c.first,c.second,c.record,c.null,c.mutation,len(calls),m[g.GLOBAL],0 if not pending else(pending-g.TABLE)//52+1,(g.read(m,g.BASE)-g.TABLE)//52,int(g.read(m,g.ACTOR+0x31C)==g.OTHER),g.read(m,g.ACTOR),m[g.ACTOR+0x127])
        rows.append('{'+','.join([*('0x%Xu'%g.u32(v)for v in values),arr(m[g.STATE+i]for i in range(128)),arr(m[g.OTHER+i]for i in range(128))])+'}')
    text='#include <ultra64.h>\n'+source.INCLUDE+'\nextern u8 *D_800D199C;\n'+source.DECLARATION+source.SELECTED+'\n';variants=controls()
    for n,b in variants.items():assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=r'''
u8 D_800D1940,D_800D2E60[32];u8*D_800D199C;struct178*D_800D3098;
typedef struct{u32 command,secondary,active,gate,query,mask,first,second,record,nullActor,mutation,calls,global,pending,base,state,finalActive,finalGate;u8 a[128],b[128];}Row;
static const Row rows[]={'''+',\n'.join(rows)+r'''};
static struct127 actor;static struct178 records[73];static u8 states[2][sizeof(struct126)];static const Row*c;static u32 calls,bad;
s32 func_15080738(s32 command){calls++;if((u32)command!=c->command)bad=1;
 if(c->mutation&1){actor.unk31C=(struct126*)states[1];actor.interaction_state=0;actor.unk127=255;}
 if(c->mutation&2)D_800D2E60[c->command>>3]^=255;
 if(c->mutation&4)D_800D3098=records+10;
 return(s32)c->query;}
static u32 run(void(*fn)(struct127*,struct178*,s32,s32)){u32 n,i,j,fail=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];calls=bad=0;
  for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*13+89);
  for(j=0;j<2;j++)for(i=0;i<sizeof(states[j]);i++)states[j][i]=(u8)(i*13+89);
  for(i=0;i<32;i++)D_800D2E60[i]=0;
  if(c->command<256)D_800D2E60[c->command>>3]=(u8)c->mask;
  actor.interaction_state=(s32)c->active;actor.unk127=(u8)c->gate;actor.unk31C=(struct126*)states[0];states[0][0x74]=(u8)c->first;states[0][0x75]=(u8)c->second;
  D_800D1940=165;D_800D199C=0;D_800D3098=records+36;
  fn(c->nullActor?0:&actor,records+c->record,(s32)c->secondary,(s32)c->command);
  if(bad||calls!=c->calls||D_800D1940!=c->global||D_800D199C!=(c->pending?(u8*)(records+c->pending-1):0)||D_800D3098!=records+c->base||actor.unk31C!=(struct126*)states[c->state]||(u32)actor.interaction_state!=c->finalActive||actor.unk127!=c->finalGate)fail++;
  for(i=0;i<128;i++)if(states[0][i]!=c->a[i]||states[1][i]!=c->b[i])fail++;
 }return fail;}
void _start(void){u32 mask=0;int result;if(run(func_15080500))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!=255)goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(rows)
