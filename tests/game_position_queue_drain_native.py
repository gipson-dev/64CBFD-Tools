"""SDK native32 queue layout, ten-argument calls and live bounded queue updates."""
from tools.experiments import game_position_queue_drain_candidates as source
from tools.tests import game_position_queue_drain_oracle as g

def controls():
    b=source.SELECTED
    return dict(wrong_cycle=b.replace('+= 5','+= 4'),wrong_wrap=b.replace('>= 200','> 200'),wrong_order=b.replace('&D_800DDD28[D_8008CEB0[0]]','&D_800DDD28[0]'),skip_null_drain=b.replace('    savedIndex =','    if (pixels == NULL) return displayList;\n    savedIndex ='),unsigned_coordinate=b.replace('displayList, entry->unk0','displayList, (u16)entry->unk0'),signed_width=b.replace('(u16)entry->unk8','entry->unk8'),wrong_stride=b.replace('* 640','* 320'),lost_restore=b.replace('    D_800DDD58 = savedIndex;','    D_800DDD58 = savedIndex + 1;'),lost_chain=b.replace('displayList = func_1517D074','func_1517D074'),stub='Gfx *func_1517D690(Gfx *displayList, u16 *pixels) { return NULL; }')

def queue(m,s=None):
    s=g.symbols()if s is None else s;values=[]
    for i in range(3):
        p=s['D_800DDD28']+16*i;values.append([g.read(m,p,2),g.read(m,p+2,2),g.read(m,p+4,2),m[p+6],m[p+7],g.read(m,p+8,2),g.read(m,p+10,2),g.read(m,p+12)])
    return values

def program():
    cases=[c for c in g.cases()if c.phase==0 and c.count<=3 and c.display==g.DISPLAY];rows=[]
    arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(tuple,list))else'0x%Xu'%g.u32(x)for x in xs)+'}'
    for c in cases:
        initial=g.fixture(c);final,calls,obs,result=g.reference(initial,c);observations=[]
        for cycle,count,index,data in obs:
            m={g.QUEUE+i:v for i,v in enumerate(data)};observations.append([cycle,count,index,queue(m)])
        rows.append(arr([c.count,c.cycle,c.index,c.mutation,c.returns,int(bool(c.pixels)),queue(initial),final[g.COUNT],final[g.PHASE],g.read(final,g.INDEX),queue(final),result,len(calls),[list(a)for t,a in calls]+[[0]*10]*(4-len(calls)),observations+[[0,0,0,[[0]*8]*3]]*(4-len(obs))]))
    owner=(source.ROOT/source.SOURCE).read_text();at=owner.index('typedef struct {');end=owner.index('} PositionQueueEntry;',at)+len('} PositionQueueEntry;');record=owner[at:end]
    prototype=source.TYPED_HELPER.split(' {',1)[0]+';\n'
    text='#include <ultra64.h>\n'+record+'\nextern u8 D_8008CEB0[];\nextern u8 D_800DDD1C;\nextern PositionQueueEntry D_800DDD28[];\n'+source.SUPPORT+prototype+source.SELECTED+'\n'
    variants=controls()
    for n,b in variants.items():assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=source.TYPED_HELPER.replace('func_1517D074','preserved_unfinished_helper')+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(Gfx)==8&&sizeof(PositionQueueEntry)==16&&__builtin_offsetof(PositionQueueEntry,unk6)==6&&__builtin_offsetof(PositionQueueEntry,unk8)==8&&__builtin_offsetof(PositionQueueEntry,unkA)==10&&__builtin_offsetof(PositionQueueEntry,unkC)==12)?1:-1];\n'
    text+='typedef struct{u32 cycle,count,index,queue[3][8];}Observation;\ntypedef struct{u32 count,cycle,index,mutation,returns,pixels,initial[3][8],finalCount,finalCycle,finalIndex,finalQueue[3][8],result,calls,args[4][10];Observation obs[4];}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\n'
    text+=r'''
u8 D_8008CEB0[1],D_800DDD1C;u32 D_800DDD58;PositionQueueEntry D_800DDD28[3];
static Gfx arena[64];static u16 pixels[256*1280];static const Row*c;static u32 calls,bad;
static u32 raw(Gfx*p){return p?(u32)(unsigned long)p-(u32)(unsigned long)arena+0x230000u:0;}
static void fill(const u32 v[3][8]){u32 i;PositionQueueEntry*p;for(i=0;i<3;i++){p=&D_800DDD28[i];p->unk0=(s16)v[i][0];p->unk2=(s16)v[i][1];p->unk4=(s16)v[i][2];p->unk6=(u8)v[i][3];p->pad7=(u8)v[i][4];p->unk8=(s16)v[i][5];p->unkA=(s16)v[i][6];*(u32*)&p->unkC=v[i][7];}}
static u32 check(const u32 v[3][8]){u32 i,j,actual[8];PositionQueueEntry*p;for(i=0;i<3;i++){p=&D_800DDD28[i];actual[0]=(u16)p->unk0;actual[1]=(u16)p->unk2;actual[2]=(u16)p->unk4;actual[3]=p->unk6;actual[4]=p->pad7;actual[5]=(u16)p->unk8;actual[6]=(u16)p->unkA;actual[7]=*(u32*)&p->unkC;for(j=0;j<8;j++)if(actual[j]!=v[i][j])return 1;}return 0;}
Gfx *func_1517D074(Gfx*dl,s32 x,s32 y,s32 z,f32 angle,s32 halfWidth,s32 halfHeight,s32 textureWidth,s32 textureHeight,u16*row){u32 n=calls++,i,ordinal=n+1;PositionQueueEntry*p;u32 args[10]={raw(dl),(u32)x,(u32)y,(u32)z,*(u32*)&angle,(u32)halfWidth,(u32)halfHeight,(u32)textureWidth,(u32)textureHeight,(u32)(unsigned long)row-(u32)(unsigned long)pixels+0x240000u};
 if(n>=c->calls||n>=4){bad=1;return NULL;}
 for(i=0;i<10;i++)if(args[i]!=c->args[n][i])bad=1;
 if(D_8008CEB0[0]!=c->obs[n].count||D_800DDD1C!=c->obs[n].cycle||D_800DDD58!=c->obs[n].index||check(c->obs[n].queue))bad=1;
 D_800DDD58=0xABC00000u+ordinal;
 if(ordinal==1){if(c->mutation&1)D_8008CEB0[0]=1;if(c->mutation&2)D_8008CEB0[0]=3;}
 if(c->mutation&4){p=&D_800DDD28[ordinal%3];D_800DDD1C^=128;p->unk6=(u8)(255-ordinal);p->unk0=(s16)(0x8000+ordinal);p->unk8=(s16)(0xFFF0+ordinal);*(u32*)&p->unkC=0x3F000000u+ordinal;}
 if(c->returns==1)return NULL;if(c->returns==2)return ordinal&1?NULL:arena;
 return dl?dl+(1+ordinal%3):arena+(1+ordinal%3);
}
typedef Gfx*(*Callback)(Gfx*,u16*);
static u32 run(Callback fn){u32 n,fail=0;Gfx*answer;for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];bad=calls=0;D_8008CEB0[0]=(u8)c->count;D_800DDD1C=(u8)c->cycle;D_800DDD58=c->index;fill(c->initial);answer=fn(arena,c->pixels?pixels:NULL);
 if(bad||calls!=c->calls||raw(answer)!=c->result||D_8008CEB0[0]!=c->finalCount||D_800DDD1C!=c->finalCycle||D_800DDD58!=c->finalIndex||check(c->finalQueue))fail++;
 }return fail;
}
void _start(void){u32 mask=0;int result;if(run(func_1517D690))goto failure;
 if(preserved_unfinished_helper(arena,-32768,32767,-1,1.f,65535,32768,16,32,pixels))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!=1023)goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
