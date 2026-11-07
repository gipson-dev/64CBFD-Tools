"""SDK native32 callback, both packet phases, typed services and negative controls."""
from tools.experiments import game_selected_impact_sprite_candidates as c
from tools.experiments import game_selected_vertex_sprite_candidates as vertex
from tools.tests import game_selected_impact_sprite_oracle as g
def controls():
    b=c.SELECTED
    return dict(unsigned_index=b.replace('*(s8 *)(actor + 0x2D)','*(u8 *)(actor + 0x2D)'),wrong_stride=b.replace('* 20','* 16'),wrong_height=b.replace('heightInt = (s32)height','heightInt = (s32)(height + 1.0f)'),signed_random=b.replace('(u32)func_150ADA20()','func_150ADA20()'),wrong_lifetime=b.replace('% 21 + 35','% 20 + 35'),wrong_texture=b.replace('textureIndex = 18','textureIndex = 17'),wrong_color=b.replace('255, 255, 255, 255','254, 255, 255, 255'),live_positions=b.replace('    owner[0x20] = 4;','    owner[0x20] = 4;\n    positions = *(u8 **)(actor + 0x94);'),live_owner=b.replace('    u8 *owner = *(u8 **)(actor + 0x98);\n','').replace('owner[0x20] = 4','(*(u8 **)(actor + 0x98))[0x20] = 4'),late_mark=b.replace('    owner[0x20] = 4;\n','').replace('    return 1;','    owner[0x20] = 4;\n    return 1;'),previous_height=b.replace('position[1] = height','position[1] = previousY'),wrong_scale=b.replace('* 40.0f','* 41.0f'),zero_context=b.replace('(s32)context, position','0, position'),wrong_alpha=b.replace('selector, magnitude, 255,','selector, magnitude, 254,'),wrong_return=b.replace('return 1;','return 0;'),stub='s32 func_1518C69C(u8 *actor,f32 x,f32 y,f32 z,f32 height,void *context){return 0;}')
def program():
    cases=[x for x in g.cases()if not x.connected and not x.alias];arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(tuple,list))else'0x%Xu'%g.u32(x)for x in xs)+'}';rows=[]
    for x in cases:
        e=g.reference(g.fixture(x),x);p=e['packets'][0];fields=[g.half(int.from_bytes(p[k:k+2],'big'))for k in(0x8C,0x8E,0x90,0x92)];a=next(a for t,a in e['calls']if t==g.SUBMIT);rows.append(arr([g.byte(x.index),x.height,x.random,x.mutation,x.mode,x.outcome,x.float_random,x.selector,x.context,*fields,list(e['vectors'][0]),a[1],a[3],a[5],a[6],e['memory'][g.OWNER+32]]))
    text='#include <ultra64.h>\n'+vertex.LAYOUT+'\ns32 func_150ADA20(void);\nvoid func_1516865C(void *,u8,u8,u8,u8);\nvoid *func_15168800(void *,u8,s32);\n'+c.SUPPORT+'\nextern u8 *D_8008CA4C[];\n'+vertex.HELPER.replace('func_1516865C','initialize_vertices')+'\n'+c.SELECTED+'\n';variants=controls();variants['early_actor_bytes']=c.SELECTED.replace('    magnitude = func_150ADA68()', '    u8 category = actor[0xC], group = actor[1];\n    magnitude = func_150ADA68()').replace('(s32)context, position, actor[0xC], actor[1]','(s32)context, position, category, group')
    for n,b in variants.items():assert b!=c.SELECTED,n;text+=b.replace('func_1518C69C','negative_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(Vtx)==16&&sizeof(SelectedVertexSprite)==168&&__builtin_offsetof(SelectedVertexSprite,x)==140&&__builtin_offsetof(SelectedVertexSprite,textureIndex)==160)?1:-1];\n'
    text+='typedef struct{u32 index,height,random,mutation,mode,outcome,fraction,selector,context,x,y,z,lifetime,vector[3],scale,finalContext,category,group,mark;}Row;\nstatic const Row rows[]={'+',\n'.join(rows)+'};\n'
    text+=r'''
typedef union{u64 align;u8 bytes[256];}Storage;
static Storage actor,owner,other;static f32 positions[512][5];static u16 header[8];u8 *D_8008CA4C[256];static const Row*row;static u32 bad,step;static SelectedVertexSprite saved;
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static f32 real(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
s32 func_150ADA20(void){if(step++!=0)bad=1;if(row->mutation&1){*(void**)(actor.bytes+0x94)=positions+129;actor.bytes[0x2D]=127;}return(s32)row->random;}
void func_1516865C(void*input,u8 r,u8 g,u8 b,u8 a){SelectedVertexSprite*p=input;u8*bytes=input;u32 i;
 if(step++!=1||r!=255||g!=255||b!=255||a!=255||p->value80||p->value8A!=256||p->x!=(s16)row->x||p->y!=(s16)row->y||p->z!=(s16)row->z||p->initialHeight!=(s16)row->y||p->lifetime!=(s16)row->lifetime||p->remaining!=(s16)row->lifetime||p->flags!=12||p->textureIndex!=18||p->mode||p->tag!=-1)bad=1;
 /* Check defined inputs first, then initialize only the deliberately unwritten
    holes. Portable native C does not promise their production byte values. */
 for(i=0;i<128;i++)bytes[i]=0xA5;for(i=0x84;i<0x8A;i++)bytes[i]=0xA5;bytes[0x9A]=bytes[0x9B]=0xA5;for(i=0x9C;i<0xA0;i++)bytes[i]=0xA5;for(i=0xA3;i<168;i++)bytes[i]=0xA5;
 initialize_vertices(input,r,g,b,a);copy((u8*)&saved,bytes,168);
 if(row->mutation&2){actor.bytes[12]=17;actor.bytes[1]=255;*(void**)(actor.bytes+0x98)=other.bytes;}
}
void *func_15168800(void*input,u8 category,s32 group){s32 i;if(step++!=2||category!=((row->mutation&2)?17:201)||group!=((row->mutation&2)?255:135)||!equal(input,(u8*)&saved,168))bad=1;if(row->mutation&4)*(void**)(actor.bytes+0x98)=other.bytes;
 if(row->mode&1){*(void**)(actor.bytes+0x94)=positions+130;actor.bytes[0x2D]++;i=(s8)actor.bytes[0x2D];positions[128+i][0]=123.25f;positions[128+i][2]=-77.5f;}
 return row->outcome?&saved:NULL;}
u8 func_151D8E20(void){if(step++!=3||owner.bytes[32]!=4)bad=1;if(row->mode&2){actor.bytes[0x2D]++;*(void**)(actor.bytes+0x94)=positions+132;actor.bytes[12]=33;actor.bytes[1]=222;}return(u8)row->selector;}
f32 func_150ADA68(void){if(step++!=4||owner.bytes[32]!=4)bad=1;if(row->mode&4){actor.bytes[12]=255;actor.bytes[1]=129;*(void**)(actor.bytes+0x98)=other.bytes;}return real(row->fraction);}
void func_151DBCBC(u8 selector,f32 scale,s16 alpha,s32 context,void*input,u8 category,s32 group){f32*v=input;u32 i;if(step++!=5||owner.bytes[32]!=4||selector!=(u8)row->selector||word(scale)!=row->scale||alpha!=255||(u32)context!=row->finalContext||category!=row->category||(u32)group!=row->group)bad=1;for(i=0;i<3;i++)if(word(v[i])!=row->vector[i])bad=1;if(row->mode&8)owner.bytes[32]=0xAA;}
static u32 run(s32(*fn)(u8*,f32,f32,f32,f32,void*)){u32 n,i,j,fail=0;
 for(i=0;i<256;i++)D_8008CA4C[i]=(u8*)header;header[3]=47;header[4]=31;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){row=&rows[n];for(i=0;i<512;i++)for(j=0;j<5;j++)positions[i][j]=j==0?(i-128.0f)*257.0f+.75f:j==2?-(i-128.0f)*131.0f-.5f:0;fill(actor.bytes,256,0x5A);fill(owner.bytes,256,0x5A);fill(other.bytes,256,0x5A);actor.bytes[0x2D]=(u8)row->index;actor.bytes[12]=201;actor.bytes[1]=135;*(void**)(actor.bytes+0x94)=positions+128;*(void**)(actor.bytes+0x98)=owner.bytes;step=bad=0;
 if(fn(actor.bytes,3.25f,-4.5f,7.75f,real(row->height),(void*)row->context)!=1||bad||step!=6||owner.bytes[32]!=row->mark||other.bytes[32]!=0x5A)fail++;for(i=0;i<256;i++)if((i!=32&&owner.bytes[i]!=0x5A)||other.bytes[i]!=0x5A)fail++;
 }return fail;}
void _start(void){u32 mask=0;int result;if(run(func_1518C69C))goto failure;
'''
    for i,n in enumerate(variants):text+='if(run(negative_'+n+'))mask|='+str(1<<i)+';\n'
    text+='if(mask!='+str((1<<len(variants))-1)+')goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,list(variants),len(cases)
