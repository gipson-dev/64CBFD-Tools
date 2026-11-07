"""Native32 SDK descriptor fields, promoted call ABI and initialized positions."""
from tools.experiments import game_selected_point_effect_candidates as source
from tools.tests import game_selected_point_effect_oracle as g
FIELDS=tuple(sorted({**{a:n for a,(n,v)in g.FIXED.items()},**{a:4 for a in g.GLOBAL_FIELDS},8:4,12:4,16:4}.items()))
def controls():
    b=source.SELECTED
    return dict(wrong_gate=b.replace('== 0) return','!= 0) return'),wrong_point_mode=b.replace('(u8)context);','(u8)(context + 1));'),checked_helper_result=b.replace('    func_15146890(&position.x, actor, (HeightResult71820 *)0, (u8)context);','    if (func_15146890(&position.x, actor, (HeightResult71820 *)0, (u8)context) == 0) return;'),wrong_count=b.replace('countBase = 5','countBase = 4'),wrong_position=b.replace('descriptor.position = position;','descriptor.position = position;\n    descriptor.position.x = position.z;'),wrong_signed_range=b.replace('minimum20 = -20','minimum20 = 20'),wrong_constant=b.replace('field18 = D_800A570C','field18 = D_800A5708'),wrong_consumer_tag=b.replace('&descriptor, 0, 255, 1','&descriptor, 0, 254, 1'),stub='void '+source.FUNCTION+'(u8 *actor,s32 context,s32 unused) {}')
def program():
    cases=[c for c in g.cases()if c.phase==0 and not c.mutation&4 and c.fill];rows=[];arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(v)for v in xs)+'}'
    for c in cases:
        initial=g.fixture(c);m,calls,obs,emits=g.reference(initial,c);wanted=[int.from_bytes(obs[0][a:a+n],'big')for a,n in FIELDS]if obs else[0]*len(FIELDS)
        rows.append('{'+','.join(('0x%Xu'%g.u32(v)for v in(c.active,c.context,c.unused,c.mutation,c.answer)))+','+arr(c.point)+','+arr(c.constants)+','+arr(wanted)+','+str(g.read(m,g.ACTOR+0x1D4))+'}')
    text='#include <ultra64.h>\ntypedef struct HeightResult71820 HeightResult71820;\ns32 func_15146890();\n'+source.SUPPORT+'\n'+source.SELECTED+'\n';variants=controls()
    for n,b in variants.items():assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(EffectPoint173D40)==12&&sizeof(PointEffectDescriptor173D40)==68&&__builtin_offsetof(PointEffectDescriptor173D40,position)==8&&__builtin_offsetof(PointEffectDescriptor173D40,mode)==60&&__builtin_offsetof(PointEffectDescriptor173D40,value40)==64)?1:-1];\n'
    text+='typedef struct{u32 active,context,unused,mutation,answer,point[3],constants[6],wanted['+str(len(FIELDS))+'],finalActive;}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\n'
    text+='static const u32 fields[][2]={'+','.join('{%d,%d}'%(a,n)for a,n in FIELDS)+'};\n'
    text+=r'''
f32 D_800A5708,D_800A570C,D_800A5710,D_800A5714,D_800A5718,D_800A571C;
static f32*globals[]={&D_800A5708,&D_800A570C,&D_800A5710,&D_800A5714,&D_800A5718,&D_800A571C};
static u32 actorWords[0x340/4];static u8*actor=(u8*)actorWords;static const Row*c;static u32 pointCalls,consumerCalls,bad;static f32*escaped;
static u32 get(u8*p,u32 n){return n==1?*p:n==2?*(u16*)p:*(u32*)p;}
s32 func_15146890(f32*p,u8*owner,HeightResult71820*result,s32 context){u32 i;pointCalls++;escaped=p;
 if(owner!=actor||result||context!=(s32)(c->context&255)||*(u32*)(owner+0x1D4)!=c->active)bad=1;
 if(c->mutation&1)for(i=0;i<6;i++)*globals[i]=(f32)(i+1)*.125f;
 if(c->mutation&2)*(u32*)(owner+0x1D4)=0;
 for(i=0;i<3;i++)*(u32*)&p[i]=c->point[i];return(s32)c->answer;
}
void func_15150F90(PointEffectDescriptor173D40*d,u8 first,u8 tag,s32 enabled){u32 i;u8*p=(u8*)d;consumerCalls++;
 if(first||tag!=255||enabled!=1||!escaped||(u8*)&d->position==(u8*)escaped)bad=1;
 for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)if(get(p+fields[i][0],fields[i][1])!=c->wanted[i])bad=1;
 escaped[0]=40.0f;
 if(get((u8*)&d->position.x,4)!=c->point[0]||get((u8*)&d->position.y,4)!=c->point[1]||get((u8*)&d->position.z,4)!=c->point[2])bad=1;
}
typedef void(*Callback)(u8*,s32,s32);
static u32 run(Callback fn){u32 n,i,fail=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];bad=pointCalls=consumerCalls=0;escaped=0;
  for(i=0;i<sizeof(actorWords)/sizeof(actorWords[0]);i++)actorWords[i]=0;
  *(u32*)(actor+0x1D4)=c->active;for(i=0;i<6;i++)*(u32*)globals[i]=c->constants[i];
  fn(actor,(s32)c->context,(s32)c->unused);
  if(bad||pointCalls!=(c->active!=0)||consumerCalls!=(c->active!=0)||*(u32*)(actor+0x1D4)!=c->finalActive)fail++;
  for(i=0;i<sizeof(actorWords)/sizeof(actorWords[0]);i++)if(i!=0x1D4/4&&actorWords[i])fail++;
 }return fail;
}
void _start(void){u32 mask=0;int result;if(run(func_15146A98))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!=511)goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
