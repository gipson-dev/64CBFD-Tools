"""SDK native32 contract, mutable providers and checked wrong-body controls."""
from tools.experiments import game_descriptor_record_draw_candidates as source
from tools.tests import game_descriptor_record_draw_oracle as g
def program():
    controls=g.controls()
    controls['cached_actor']=source.SELECTED.replace('draw->descriptor','cachedActor').replace('    initialCount = draw->count;','    u8 *cachedActor = draw->descriptor;\n    initialCount = draw->count;',1)
    controls['cached_matrices']=source.SELECTED.replace('draw->records','cachedMatrices').replace('    initialCount = draw->count;','    Mtx *cachedMatrices = draw->records;\n    initialCount = draw->count;',1)
    assert len(controls)==12 and len(set(controls.values()))==12 and source.SELECTED not in controls.values()
    text=source.PREFIX+source.SELECTED+'\n'
    for name,body in controls.items():text+=body.replace(source.FUNCTION,'negative_'+name)+'\n'
    text+=r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(Mtx)==64&&sizeof(Gfx)==8&&sizeof(DescriptorDraw151897A4)==20&&__builtin_offsetof(DescriptorDraw151897A4,records)==8&&__builtin_offsetof(DescriptorDraw151897A4,descriptor)==16)?1:-1];
u8 D_800BE9C0;
static DescriptorDraw151897A4 draw;
static Mtx matrices0[65536],matrices1[65536];
static Gfx output[1024];static u32 expectedWords[2048];
static u8 actor0[256],actor1[256],expectedActor0[256],expectedActor1[256];
static u32 seed,mode,planned,calls,error,start,step,view,position;static u8*actor;static Mtx*matrices;
static void begin(u32 n,u32 m,u32 v){
    u32 i;seed=n;mode=m;view=v;planned=n;calls=error=position=0;
    draw.retained0=0x97;draw.stride=(u8)(n*37+7);draw.count=(u8)n;draw.step=(u8)(n*73+127);draw.retained4=0x12345678;draw.retainedC=0x87654321;
    draw.records=matrices=matrices0;draw.descriptor=actor=actor0;D_800BE9C0=(u8)(n*109+255);start=(u32)D_800BE9C0*draw.stride;step=draw.step;
    for(i=0;i<256;i++){expectedActor0[i]=actor0[i]=(u8)(i*13+7);expectedActor1[i]=actor1[i]=(u8)(i*17+9);}
    actor0[0x8A]=expectedActor0[0x8A]=0xD7;actor1[0x8A]=expectedActor1[0x8A]=0x2D;
    for(i=0;i<1024;i++){output[i].words.w0=expectedWords[2*i]=i*1664525u+1013904223u;output[i].words.w1=expectedWords[2*i+1]=~i;}
}
__attribute__((noinline,noclone)) Gfx *func_151137D4(Gfx*cursor,u8*a,Mtx*matrix,s32 which,s32 first,s32 second){
    u32 i=calls++,n=calls,alpha=(step*96u+i*(step<<5))>>8;u8*expectedActor=actor==actor0?expectedActor0:expectedActor1;
    if(i>=planned||cursor!=((mode&16)&&i?0:output+position)||a!=actor||matrix!=matrices+start+i||(u32)which!=(u32)(s32)(s16)view||first||second)error=1;
    if(a[0x8A]!=(u8)alpha)error=1;expectedActor[0x8A]=(u8)alpha;
    if(cursor&&position<1024){cursor->words.w0=0xC0010000u+i;cursor->words.w1=0xA5000000u|(u8)alpha;expectedWords[2*position]=0xC0010000u+i;expectedWords[2*position+1]=0xA5000000u|(u8)alpha;}
    if(mode&1)draw.descriptor=actor=(n&1)?actor1:actor0;
    if(mode&2)draw.records=matrices=(n&1)?matrices1:matrices0;
    if(mode&4){draw.stride^=255;draw.count^=0x55;draw.step^=0xAA;D_800BE9C0^=0x7F;}
    if(mode&8){a[0x8A]^=0xA5;expectedActor[0x8A]^=0xA5;}
    position+=1+n%3;return(mode&16)?0:output+position;
}
typedef Gfx*(*Callback)(Gfx*,DescriptorDraw151897A4*,s16);
static Callback functions[]={'''+','.join([source.FUNCTION,*['negative_'+n for n in controls]])+r'''};
static u32 check(Gfx*result){
    u32 i;u8*last=actor==actor0?expectedActor0:expectedActor1;
    if(planned)last[0x8A]=0xD7;
    if(error||calls!=planned||result!=((planned&&(mode&16))?0:output+position)||draw.records!=matrices||draw.descriptor!=actor||draw.retained0!=0x97||draw.retained4!=0x12345678u||draw.retainedC!=0x87654321u)return 0;
    if(draw.count!=(u8)(seed^(((mode&4)&&(planned&1))?0x55:0))||draw.stride!=(u8)((seed*37+7)^(((mode&4)&&(planned&1))?255:0))||draw.step!=(u8)((seed*73+127)^(((mode&4)&&(planned&1))?0xAA:0))||D_800BE9C0!=(u8)((seed*109+255)^(((mode&4)&&(planned&1))?0x7F:0)))return 0;
    for(i=0;i<256;i++)if(actor0[i]!=expectedActor0[i]||actor1[i]!=expectedActor1[i])return 0;
    for(i=0;i<1024;i++)if(output[i].words.w0!=expectedWords[2*i]||output[i].words.w1!=expectedWords[2*i+1])return 0;
    return 1;
}
static int run(void){
    u32 seedIndex,viewIndex,modeIndex,j,killed=0,n,m,v;Gfx*result;
    for(seedIndex=0;seedIndex<256;seedIndex++)for(viewIndex=0;viewIndex<4;viewIndex++)for(modeIndex=0;modeIndex<3;modeIndex++)for(j=0;j<13;j++){
        n=seedIndex;m=modeIndex==0?0:modeIndex==1?15:31;v=viewIndex==0?0:viewIndex==1?0x7FFF:viewIndex==2?0x8000:0xABCDFFFFu;
        begin(n,m,v);result=functions[j](output,&draw,(s16)v);if(!check(result)){if(!j)return 42;killed|=1u<<(j-1);}
    }
    for(modeIndex=0;modeIndex<32;modeIndex++)for(viewIndex=0;viewIndex<4;viewIndex++)for(j=0;j<13;j++){
        v=viewIndex==0?0:viewIndex==1?0x7FFF:viewIndex==2?0x8000:0xABCDFFFFu;begin(3,modeIndex,v);result=functions[j](output,&draw,(s16)v);if(!check(result)){if(!j)return 44;killed|=1u<<(j-1);}
    }
    return killed==4095?0:43;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,list(controls),3200
