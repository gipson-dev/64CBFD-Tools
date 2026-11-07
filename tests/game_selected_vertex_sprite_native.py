"""SDK native32 interfaces; initialized helper fixtures and bounded packet holes."""
import itertools
from tools.experiments import game_selected_vertex_sprite_candidates as c
from tools.tests import game_selected_vertex_sprite_oracle as g
def controls():
    p,h=c.PRIMARY,c.HELPER
    return dict(unsigned_index=p.replace('*(s8 *)(actor + 0x2D)','*(u8 *)(actor + 0x2D)'),wrong_stride=p.replace('* 20','* 16'),wrong_height=p.replace('heightInt = (s32)height','heightInt = (s32)(height + 1.0f)'),signed_random=p.replace('(u32)func_150ADA20()','func_150ADA20()'),wrong_lifetime=p.replace('% 21 + 35','% 20 + 35'),wrong_texture=p.replace('textureIndex = 18','textureIndex = 17'),wrong_color=p.replace('255, 255, 255, 255','254, 255, 255, 255'),early_arguments=p.replace('    SelectedVertexSprite descriptor;','    u8 savedCategory = actor[0xC], savedRow = actor[1];\n    SelectedVertexSprite descriptor;').replace('actor[0xC], actor[1]','savedCategory, savedRow'),live_owner=p.replace('owner[0x20] = 4','(*(u8 **)(actor + 0x98))[0x20] = 4'),wrong_mark=p.replace('owner[0x20] = 4','owner[0x20] = 3'),stub='s32 func_1518C57C(u8 *actor, f32 x, f32 y, f32 z, f32 height, void *context) {return 0;}'),dict(seven_vertices=h.replace('i != 2','i != 1'),wrong_alpha=h.replace('.v.cn[3] = alpha','.v.cn[3] = blue'),wrong_width=h.replace(' + 6)', ' + 8)'),missing_v_flip=h.replace('flags & 0x80','flags & 0x40'),missing_u_flip=h.replace('flags & 0x100','flags & 0x200'),wrong_origin=h.replace('8192','4096'),wrong_clear=h.replace('sprite->cleared88 = 0','sprite->cleared88 = 1'),stub='void func_1516865C(void *input, u8 red, u8 green, u8 blue, u8 alpha) {}')
def native_bytes(raw):
    b=bytearray(raw)
    for off,n in [(16*i+j,2)for i in range(8)for j in(0,2,4,6,8,10)]+[(0x80,4),(0x84,4),(0xA4,4)]+[(i,2)for i in range(0x88,0xA0,2)]:b[off:off+n]=b[off:off+n][::-1]
    return bytes(b)
def program():
    roots=[x for x in g.cases()if x.connected==0];helpers=[]
    for flags,w,h,rgba in itertools.product((0,128,256,384,65535),(0,1,255,1792,65535),(0,31,255,65535),((0,1,128,255),(255,129,17,0))):
        x=g.Case(flags=flags,width=w,tall=h,rgba=rgba);a=g.fixture(x);e,*_=g.reference(a,x,helper=True);helpers.append((x,native_bytes(g.data(a,g.PACKET,168)),native_bytes(g.data(e,g.PACKET,168))))
    arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(tuple,list,bytes))else'0x%Xu'%g.u32(x)for x in xs)+'}'
    rootrows=[]
    for x in roots:
        a=g.fixture(x);e,calls,packets,v=g.reference(a,x);packet=packets[0];vals=[g.half(int.from_bytes(packet[k:k+2],'big'))for k in(0x8C,0x8E,0x90,0x92)]
        rootrows.append(arr([g.byte(x.index),x.height,x.random,x.mutation,x.outcome,*vals]))
    pcontrols,hcontrols=controls();pcontrols['live_owner']=pcontrols['live_owner'].replace('    u8 *owner = *(u8 **)(actor + 0x98);\n','');text='#include <ultra64.h>\n'+c.LAYOUT+'\nextern u8 *D_8008CA4C[];\ns32 func_150ADA20(void);\nvoid func_1516865C(void *,u8,u8,u8,u8);\nvoid *func_15168800(void *,u8,s32);\n'+c.PRIMARY+'\n'+c.HELPER.replace('func_1516865C','initialize_vertices')+'\n'
    for n,b in pcontrols.items():text+=b.replace('func_1518C57C','negative_'+n)+'\n'
    for n,b in hcontrols.items():text+=b.replace('func_1516865C','negative_helper_'+n)+'\n'
    text+='typedef char ABI[(sizeof(void*)==4&&sizeof(Vtx)==16&&sizeof(SelectedVertexSprite)==168&&__builtin_offsetof(SelectedVertexSprite,value80)==128&&__builtin_offsetof(SelectedVertexSprite,x)==140&&__builtin_offsetof(SelectedVertexSprite,flags)==152&&__builtin_offsetof(SelectedVertexSprite,textureIndex)==160)?1:-1];\n'
    text+='typedef struct{u32 index,height,random,mutation,outcome,x,y,z,lifetime;}Row;\nstatic const Row rows[]={'+',\n'.join(rootrows)+'};\n'
    text+='typedef struct{u32 width,height;u8 rgba[4],initial[168],wanted[168];}HelperRow;\nstatic const HelperRow helpers[]={'+',\n'.join(arr([x.width,x.tall,x.rgba,a,e])for x,a,e in helpers)+'};\n'
    text+=r'''
typedef union{u64 align;u8 bytes[256];}Actor;
static Actor actor,owner,other;static f32 positions[512][5];static u16 header[8];u8 *D_8008CA4C[256];
static const Row *row;static u32 bad,step;static SelectedVertexSprite saved;
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static u32 equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
s32 func_150ADA20(void){if(step++!=0)bad=1;if(row->mutation&1){*(f32(**)[5])(actor.bytes+0x94)=positions+129;actor.bytes[0x2D]=127;}return(s32)row->random;}
void func_1516865C(void*input,u8 r,u8 g,u8 b,u8 a){SelectedVertexSprite*p=input;u32 i,j;u8*bytes=input;
 if(step++!=1||r!=255||g!=255||b!=255||a!=255||p->value80||p->value8A!=256||p->x!=(s16)row->x||p->y!=(s16)row->y||p->z!=(s16)row->z||p->initialHeight!=(s16)row->y||p->lifetime!=(s16)row->lifetime||p->remaining!=(s16)row->lifetime||p->flags!=12||p->textureIndex!=18||p->mode||p->tag!=-1)bad=1;
 /* Initialize only holes that the callback deliberately leaves unwritten.
    Native fixtures do not assign a portable value to indeterminate bytes. */
 for(i=0;i<8;i++)for(j=0;j<16;j++)bytes[i*16+j]=0xA5;
 for(i=0x84;i<0x8A;i++)bytes[i]=0xA5;bytes[0x9A]=bytes[0x9B]=0xA5;for(i=0x9C;i<0xA0;i++)bytes[i]=0xA5;for(i=0xA3;i<168;i++)bytes[i]=0xA5;
 initialize_vertices(input,r,g,b,a);copy((u8*)&saved,bytes,168);
 if(row->mutation&2){actor.bytes[12]=17;actor.bytes[1]=255;*(void**)(actor.bytes+0x98)=other.bytes;}
}
void *func_15168800(void*input,u8 category,s32 group){if(step++!=2||category!=((row->mutation&2)?17:201)||group!=((row->mutation&2)?255:135)||!equal(input,(u8*)&saved,168))bad=1;if(row->mutation&4)*(void**)(actor.bytes+0x98)=other.bytes;return row->outcome?&saved:NULL;}
static u32 run(s32(*fn)(u8*,f32,f32,f32,f32,void*)){u32 n,i,j,fail=0;union{u32 u;f32 f;}height;
 for(i=0;i<512;i++)for(j=0;j<5;j++)positions[i][j]=j==0?(i-128.0f)*257.0f+.75f:j==2?-(i-128.0f)*131.0f-.5f:0;
 for(i=0;i<256;i++)D_8008CA4C[i]=(u8*)header;header[3]=47;header[4]=31;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){row=&rows[n];fill(actor.bytes,256,0x5A);fill(owner.bytes,256,0x5A);fill(other.bytes,256,0x5A);actor.bytes[0x2D]=(u8)row->index;actor.bytes[12]=201;actor.bytes[1]=135;*(void**)(actor.bytes+0x94)=positions+128;*(void**)(actor.bytes+0x98)=owner.bytes;height.u=row->height;step=bad=0;
 if(fn(actor.bytes,3.25f,-4.5f,7.75f,height.f,actor.bytes+100)!=1||bad||step!=3||owner.bytes[32]!=4||other.bytes[32]!=0x5A)fail++;
 for(i=0;i<256;i++)if((i!=32&&owner.bytes[i]!=0x5A)||other.bytes[i]!=0x5A)fail++;
 }return fail;}
static u32 run_helper(void(*fn)(void*,u8,u8,u8,u8)){u32 n,i,fail=0;union{u64 align;u8 bytes[200];}storage;
 for(i=0;i<256;i++)D_8008CA4C[i]=(u8*)header;
 for(n=0;n<sizeof(helpers)/sizeof(helpers[0]);n++){const HelperRow*r=&helpers[n];fill(storage.bytes,200,0x5A);copy(storage.bytes+16,r->initial,168);header[3]=(u16)r->width;header[4]=(u16)r->height;fn(storage.bytes+16,r->rgba[0],r->rgba[1],r->rgba[2],r->rgba[3]);if(!equal(storage.bytes+16,r->wanted,168))fail++;for(i=0;i<16;i++)if(storage.bytes[i]!=0x5A||storage.bytes[184+i]!=0x5A)fail++;
 }return fail;}
void _start(void){u32 pm=0,hm=0;int result;if(run(func_1518C57C)||run_helper(initialize_vertices))goto failure;
'''
    for i,n in enumerate(pcontrols):text+='if(run(negative_'+n+'))pm|='+str(1<<i)+';\n'
    for i,n in enumerate(hcontrols):text+='if(run_helper(negative_helper_'+n+'))hm|='+str(1<<i)+';\n'
    text+='if(pm!='+str((1<<len(pcontrols))-1)+'||hm!='+str((1<<len(hcontrols))-1)+')goto failure;result=0;goto finish;\nfailure:result=1;\nfinish:__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
    return text,dict(root=list(pcontrols),helper=list(hcontrols)),dict(root=len(roots),helper=len(helpers))
