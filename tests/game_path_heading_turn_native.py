"""Native32 heading grid with typed providers and an independent circular reference."""
def source(body):
    return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
typedef struct {s16 x,pad2,z,pad6;} PathNode8;
typedef char actor_size_check[(sizeof(struct127)==0x32C)?1:-1];
static struct127 actors[2];struct127*D_800D154C;
static PathNode8 nodes[257];static PathNode8*paths[256];s32*D_800D2104;
static u8 table[5120];
#define D_80099A3C ((s16*)table)
u8 D_800D1890,D_800D1891;
static u32 angle_word,current_word,initial_mode,threshold,mutate,fail,seen_query,seen_turn;
static u32 want_x,want_z,expected_distance,expected_row,expected_actor;
static u32 bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
__attribute__((noinline)) u16 func_1505A630(f32 x,f32 z,s32 zero){
 seen_query++;if(bits(x)!=want_x||bits(z)!=want_z||zero)fail=1;
 if(mutate){D_800D154C=&actors[1];D_800D1890^=167;D_800D1891=37;table[expected_row*10]=threshold^129u;D_800D154C->unk76=current_word^0x8000u;}
 return (u16)angle_word;
}
__attribute__((noinline)) void func_15056A00(void*input,u8 magnitude,u8 row){
 seen_turn++;if(input!=&actors[expected_actor]||magnitude!=expected_distance||row!=expected_row||((struct127*)input)->unk250!=D_800D1891)fail=2;
}
'''+body.replace('void func_15077F64(', '__attribute__((noinline)) void func_15077F64(',1)+r'''
static void(*volatile probe)(void)=func_15077F64;
static u8 before[2][0x32C] __attribute__((aligned(4)));
static int one(u32 current,u32 angle,u32 mode,u32 limit,u32 seed){
 static const s16 xs[]={-32768,-1,0,32767};static const s16 zs[]={32767,0,-1,-32768};
 static const f32 px[]={0.f,1.25f,-17.5f,32768.f},pz[]={0.f,-1.5f,19.25f,-32768.f};
 u32 i,j,group=seed&255u,entry=(seed*7u)&255u,pattern=seed&3u;
 angle_word=angle;current_word=current;initial_mode=mode;threshold=limit;mutate=seed&1u;fail=seen_query=seen_turn=0;
 expected_actor=mutate;expected_row=(mode+255u)&255u;
 for(i=0;i<2;i++){
  u8*p=(u8*)&actors[i];for(j=0;j<0x32C;j++)p[j]=(u8)(j*13u+89u);
  actors[i].unk13F=group;actors[i].unk21E=entry;actors[i].x_position=px[pattern];actors[i].z_position=pz[pattern];actors[i].unk76=current;actors[i].unk78=0xA55A;
 }
 nodes[entry+1].x=xs[pattern];nodes[entry+1].z=zs[pattern];
 D_800D154C=&actors[0];D_800D1890=mode;D_800D1891=173;table[expected_row*10]=limit;
 want_x=bits((f32)((f64)xs[pattern]-(f64)px[pattern]));want_z=bits((f32)((f64)pz[pattern]-(f64)zs[pattern]));
 for(i=0;i<2;i++)for(j=0;j<0x32C;j++)before[i][j]=((u8*)&actors[i])[j];
 u32 active_current=mutate?(current^0x8000u):current;
 u32 high=(((angle+65536u-active_current)&65535u)/256u);expected_distance=high<=128u?high:256u-high;
 u32 active_threshold=mutate?(limit^129u):limit;u32 want_turn=active_threshold<expected_distance;
 if(mutate){((struct127*)before[1])->unk76=active_current;}
 ((struct127*)before[expected_actor])->unk78=angle;
 if(want_turn)((struct127*)before[expected_actor])->unk250=mutate?37:173;
 probe();
 if(fail||seen_query!=1||seen_turn!=want_turn||D_800D154C!=&actors[expected_actor]||D_800D1890!=(mutate?(mode^167u):mode)||D_800D1891!=(mutate?37u:173u)||table[expected_row*10]!=active_threshold)return 10;
 for(i=0;i<2;i++)for(j=0;j<0x32C;j++)if(((u8*)&actors[i])[j]!=before[i][j])return 11;
 return 0;
}
static int run(void){
 static const u32 modes[]={0,1,128,255},limits[]={0,1,127,128,255};u32 c,a,m,l;
 for(c=0;c<256;c++)paths[c]=nodes;D_800D2104=(s32*)paths;
 for(c=0;c<5120;c++)table[c]=(u8)(c*29u+55u);
 for(c=0;c<256;c++)for(a=0;a<256;a++)for(m=0;m<4;m++)for(l=0;l<5;l++){
  int r=one((c<<8)|((a*31u+c)&255u),(a<<8)|((c*17u+a)&255u),modes[m],limits[l],c+a);if(r)return r;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
