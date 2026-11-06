"""SDK native32 vectors derived from the independent guest contract."""
from tools.experiments import game_phase_motion_candidates as source
from tools.tests import game_phase_motion_oracle as g

def native_image(memory):
    data=bytearray(memory[g.OWNER+i]for i in range(256))
    for off in g.FLOAT_FIELDS:data[off:off+4]=data[off:off+4][::-1]
    return data

def array(values):return'{'+','.join('0x%Xu'%v for v in values)+'}'

def program():
    controls=g.controls();assert len(controls)==8 and len(set(controls.values()))==8
    assert all(body!=source.SELECTED for body in controls.values())
    text='#include <ultra64.h>\nextern s32 D_800BE9E4;\n'+source.TYPES+source.SELECTED+'\n'
    for name,body in controls.items():text+=body.replace(source.FUNCTION,'negative_'+name)+'\n'
    rows=[]
    for index in range(256):
        for mode in(0,1,2,7):
            c=g.Case(index,g.TICKS[index%len(g.TICKS)],mode=mode);initial=g.fixture(c)
            expected,calls,result,snapshots=g.reference(initial,c)
            assert result==1 and len(calls)==4
            rows.append('{'+','.join((array(native_image(initial)),array(native_image(expected)),
                array([args[0]for target,args in calls]),array([g.provider(c,n)for n in range(4)]),
                '{'+','.join(array(row)for row in snapshots)+'}',str(mode)+'u',
                hex(g.read(initial,g.symbols()['D_800BE9E4']))+'u',
                hex(g.read(initial,g.symbols()['D_800BE9A4']))+'u',
                hex(g.read(expected,g.symbols()['D_800BE9E4']))+'u',
                hex(g.read(expected,g.symbols()['D_800BE9A4']))+'u'))+'}')
    text+=r'''
typedef struct {
    u8 prefix[0x38];f32 x,y;u8 gap40[12];f32 output[3];u8 gap58[0x50];
    MotionPayload1515A11C motion;u8 suffix[0x34];
} Owner;
typedef char OwnerLayout[sizeof(Owner)==256&&__builtin_offsetof(Owner,motion)==0xA8?1:-1];
typedef char PayloadLayout[sizeof(MotionPayload1515A11C)==36&&__builtin_offsetof(MotionPayload1515A11C,phase)==28?1:-1];
typedef struct {u8 input[256],expected[256];u32 arguments[4],answers[4],snapshots[4][16],mode,ticks,dt,finalTicks,finalDt;} Vector;
static const Vector vectors[]={
'''+',\n'.join(rows)+r'''
};
typedef s32(*Callback)(u8*,u8*);
static Callback callbacks[]={'''+','.join([source.FUNCTION,*['negative_'+n for n in controls]])+r'''};
typedef struct {u32 before[4];Owner owner;u32 after[4];} Guarded;
static Guarded world;static u8 workspace[64];static const Vector*v;static u32 used,error;
s32 D_800BE9E4;f32 D_800BE9A4;
static const u32 offsets[]={0x38,0x3C,0x4C,0x50,0x54,0xA8,0xAC,0xB0,0xB4,0xB8,0xBC,0xC0,0xC4,0xC8};
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 word(const void*p){u32 x;copy(&x,p,4);return x;}
static void set(void*p,u32 x){copy(p,&x,4);}
static void effect(u32 n){
    u8*p=(u8*)&world.owner;
    if(n==0&&(v->mode&1)){
        p[0xAD]^=0x55;p[0xAC]^=0xAA;
        world.owner.motion.center=-2.5f;world.owner.motion.firstRadius=.25f;world.owner.motion.secondRadius=-4.0f;
        world.owner.motion.rate=.5f;D_800BE9A4=.25f;
    }
    if(n==1&&(v->mode&2)){
        world.owner.motion.center=1.25f;world.owner.motion.firstRadius=-.5f;world.owner.motion.secondRadius=3.0f;
        world.owner.motion.phase=-1.25f;world.owner.motion.rate=-.25f;D_800BE9A4=.5f;D_800BE9E4=(s32)0x87654321u;
    }
    if(n==2&&(v->mode&4)){
        world.owner.motion.phase=-9.0f;world.owner.motion.rate=7.5f;
        world.owner.motion.scale[0]=2.0f;world.owner.motion.scale[1]=-3.0f;world.owner.motion.scale[2]=.125f;
    }
    if(n==3&&(v->mode&4)){
        world.owner.motion.phase=-3.0f;
        world.owner.motion.scale[0]=-1.5f;world.owner.motion.scale[1]=.25f;world.owner.motion.scale[2]=2.0f;
    }
}
static f32 provide(u32 argument){
    u32 n=used++,i,value;u8*p=(u8*)&world.owner;f32 result;
    if(n>=4){error=1;return 0.0f;}
    if(argument!=v->arguments[n])error=1;
    for(i=0;i<14;i++){
        value=offsets[i]==0xAC?((u32)p[0xAC]<<24|(u32)p[0xAD]<<16|(u32)p[0xAE]<<8|p[0xAF]):word(p+offsets[i]);
        if(value!=v->snapshots[n][i])error=1;
    }
    if((u32)D_800BE9E4!=v->snapshots[n][14]||word(&D_800BE9A4)!=v->snapshots[n][15])error=1;
    effect(n);set(&result,v->answers[n]);return result;
}
__attribute__((noinline,noclone)) f32 func_151423D8(u8 argument){return provide(argument);}
__attribute__((noinline,noclone)) f32 func_15144B68(f32 argument){return provide(word(&argument));}
__attribute__((noinline,noclone)) f32 sinf(f32 argument){return provide(word(&argument));}
static int run(void){
    u32 i,j,k,killed=0,same; s32 result;
    for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++)for(j=0;j<9;j++){
        v=&vectors[i];used=error=0;copy(&world.owner,v->input,256);
        for(k=0;k<4;k++){world.before[k]=0x12345678u+k;world.after[k]=0xABCDEF00u+k;}
        for(k=0;k<64;k++)workspace[k]=(u8)(k*13+89);
        D_800BE9E4=(s32)v->ticks;set(&D_800BE9A4,v->dt);
        result=callbacks[j]((u8*)&world.owner,workspace);
        same=result==1&&!error&&used==4&&(u32)D_800BE9E4==v->finalTicks&&word(&D_800BE9A4)==v->finalDt;
        for(k=0;k<256;k++)if(((u8*)&world.owner)[k]!=v->expected[k])same=0;
        for(k=0;k<4;k++)if(world.before[k]!=0x12345678u+k||world.after[k]!=0xABCDEF00u+k)same=0;
        for(k=0;k<64;k++)if(workspace[k]!=(u8)(k*13+89))same=0;
        if(!same){if(j==0)return 42;killed|=1u<<(j-1);}
    }
    return killed==255?0:43;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
    return text,list(controls),len(rows)
