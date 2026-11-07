"""SDK native32 cached vectors, typed helpers, live flags and partial failures."""
from tools.experiments import game_cached_vector_basis_candidates as source
from tools.tests import game_cached_vector_basis_oracle as g

def controls():
    b=source.SELECTED
    return dict(wrong_gate=b.replace('flags & 1','flags & 2'),ignored_failure=b.replace(')) return 0;', ')) {}',1),wrong_scale=b.replace('1000.0f','100.0f'),wrong_basis_output=b.replace('&state->tangent, &state->bitangent','&state->bitangent, &state->tangent'),wrong_cache_bits=b.replace('flags |= 6','flags |= 2'),missing_second_normalize=b.replace('        if (!func_15145128(&state->bitangent, &state->bitangent, NULL, NULL)) return 0;',''),stale_flags=b.replace('    if (!(state->flags & 1))','    u8 flags = state->flags;\n    if (!(flags & 1))').replace('if (!(state->flags & 2))','if (!(flags & 2))').replace('if (!(state->flags & 4))','if (!(flags & 4))'),wrong_success=b.replace('    return 1;','    return 0;'),stub='s32 func_1514F6E8(void *input) { return 0; }')

def program():
    cases=[c for c in g.cases()if c.phase==0];rows=[]
    arr=lambda v:'{'+','.join(arr(x)if isinstance(x,(tuple,list))else '0x%Xu'%g.u32(x)for x in v)+'}'
    for c in cases:
        initial=g.fixture(c);final,calls,obs,result=g.reference(initial,c);p=g.address(c)
        words=lambda m:[g.read(m,p+4+4*i)for i in range(10)]
        obswords=lambda b:[b[0],*[int.from_bytes(b[4+4*i:8+4*i],'big')for i in range(10)]]
        tags=[1 if t==g.NORM else 2 for t,a in calls];args=[[v-p if v else 0 for v in a]+[0]*(4-len(a))for t,a in calls]
        rows.append(arr([c.mutation,c.replacement,len(c.outcomes),list(c.outcomes)+[0]*(3-len(c.outcomes)),list(g.data(initial,p,4)),words(initial),list(g.data(final,p,4)),words(final),result,len(calls),tags+[0]*(4-len(tags)),args+[[0]*4]*(4-len(args)),[obswords(b)for t,v,b in obs]+[[0]*11]*(4-len(obs))]))
    variants=controls();text='#include <ultra64.h>\n'+source.SUPPORT+'\n'+source.SELECTED+'\n'
    for n,b in variants.items():assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(struct17)==12&&sizeof(CachedVectorBasis17CAF0)==44&&__builtin_offsetof(CachedVectorBasis17CAF0,direction)==4&&__builtin_offsetof(CachedVectorBasis17CAF0,tangent)==16&&__builtin_offsetof(CachedVectorBasis17CAF0,bitangent)==28&&__builtin_offsetof(CachedVectorBasis17CAF0,radius)==40)?1:-1];\n'
    text+='typedef struct{u32 mutation,replacement,nseq,outcomes[3],first[4],initial[10],last[4],wanted[10],result,count,tags[4],args[4][4],obs[4][11];}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\n'
    text+=r'''
static CachedVectorBasis17CAF0 object;static const Row*c;static u32 calls,bad;
static u32 word(f32*p){return *(u32*)p;}
static void output(struct17*p,u32 n){p->unk0=(f32)(n+1)*.125f;p->unk4=-(f32)(n+2)*.25f;p->unk8=(f32)(n+3)*.5f;}
static s32 helper(u32 tag,struct17*a,struct17*b,void*d,void*e){u32 i,n=calls++;void*args[4]={a,b,d,e};u32*p=(u32*)((u8*)&object+4);
 if(n>=c->count||n>=4){bad=1;return 0;}
 if(tag!=c->tags[n]||object.flags!=c->obs[n][0])bad=1;
 for(i=0;i<10;i++)if(p[i]!=c->obs[n][i+1])bad=1;
 for(i=0;i<4;i++)if((args[i]?(u32)((u8*)args[i]-(u8*)&object):0)!=c->args[n][i])bad=1;
 output(b,n+1);if(tag==2)output(d,n+2);
 if(c->mutation&1)object.flags=(u8)c->replacement;
 if(c->mutation&2)output(&object.direction,n+3);
 if(c->mutation&4)object.radius=(f32)(n+1)+.5f;
 return(s32)c->outcomes[n%c->nseq];
}
s32 func_15145128(struct17*a,struct17*b,f32*d,f32*e){return helper(1,a,b,d,e);}
s32 func_15146078(struct17*a,struct17*b,struct17*d){return helper(2,a,b,d,0);}
typedef s32(*Callback)(void*);
static u32 run(Callback fn){u32 n,i,fail=0;u8*bytes=(u8*)&object;u32*p=(u32*)(bytes+4);s32 result;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){c=&rows[n];bad=calls=0;
  for(i=0;i<4;i++)bytes[i]=(u8)c->first[i];for(i=0;i<10;i++)p[i]=c->initial[i];
  result=fn(&object);
  if(bad||calls!=c->count||result!=(s32)c->result)fail++;
  for(i=0;i<4;i++)if(bytes[i]!=c->last[i])fail++;for(i=0;i<10;i++)if(p[i]!=c->wanted[i])fail++;
 }return fail;
}
void _start(void){u32 mask=0;int result;if(run(func_1514F6E8))goto failure;
'''
    text=text.replace('static u32 word(f32*p){return *(u32*)p;}\n','')
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!=511)goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
