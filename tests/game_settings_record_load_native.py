"""Native32 bounded fixtures; numeric checksum header adapts byte order."""
from tools.experiments import game_settings_record_load_candidates as candidate
from tools.tests import game_settings_record_load_oracle as model
from functools import lru_cache
def digest(values):
    v=2166136261
    for b in values:v=((v^b)*16777619)&0xFFFFFFFF
    return v
@lru_cache(maxsize=1)
def rendered_rows(cases):
    # The three positive profiles and sixteen controls share these immutable
    # reference inputs. Cache only their rows, never a candidate C body.
    rows=[];s=model.symbols()
    for c in cases:
        expected=model.reference(model.fixture(c),c);m=expected['memory'];values=[m[s['D_800BE358']+i]for i in range(2,128)]+[m[s['D_800E0BE0']-16+i]for i in range(96)]+[m[s['D_8008FE30']]]
        obs=[digest(v)for target,v in expected['observations']];rows.append('{%d,%d,%d,%d,%d,0x%Xu,%d,{0x%Xu,0x%Xu}}'%(c.pattern,c.saved,c.valid,c.readmode,c.effects,digest(values),model.read(m,s['D_800BE358'],2),*obs))
    return ',\n'.join(rows)
def source(body,cases):
    return '#include <ultra64.h>\n'+r'''
static union{u16 align;u8 bytes[128];}scratch;
static s8 native_settings[96];
#define D_800BE358 (scratch.bytes)
#define D_800BE35A (scratch.bytes+2)
#define D_800E0BE0 (native_settings+16)
#define D_800E0BFC (native_settings+44)
extern OSMesgQueue D_800BE900;
s32 func_151DD3A0(OSMesgQueue*,u8,u8*,s32) __attribute__((noinline));
'''+candidate.DECLARATIONS+body+r'''
u8 D_8008FE30;OSMesgQueue D_800BE900;
typedef struct{u32 pattern,saved,valid,readmode,effects,result,header,observations[2];}Row;
static const Row rows[]={
'''+rendered_rows(tuple(cases))+r'''
};
static const Row *row;static u32 ordinal;static int error;static u32 marks[3];
static u32 observe(void){u32 v=2166136261u;for(u32 i=0;i<28;i++)v=(v^(u8)D_800E0BE0[i])*16777619u;return(v^D_8008FE30)*16777619u;}
s32 func_151DD3A0(OSMesgQueue*q,u8 channel,u8*p,s32 length){
 if(ordinal++!=0||q!=&D_800BE900||channel!=0||p!=D_800BE358||length!=32)error=1;
 for(u32 i=0;i<32;i++)p[i]=(u8)(i*31+row->pattern*71+17);
 u32 sum=0xCC;for(u32 i=2;i<30;i++)sum+=p[i]<<(i&3);
 scratch.align=(u16)((sum&65535u)^(row->valid?0:1));
 if(row->readmode&1)D_800E0BE0[16]=(s8)(row->saved^0x55);
 if(row->readmode&2)D_800BE358[23]^=0x55;
 if(row->readmode&4)D_8008FE30=0x64;
 marks[0]=0xA5000000u;__asm__ volatile("":::"eax","ecx","edx","memory");return(s32)0x87654321u;
}
__attribute__((noinline)) s32 func_151DD9E4(void){
 if(ordinal++!=1||observe()!=row->observations[0])error=1;
 if(row->effects&1){D_800E0BE0[16]^=(s8)0xA5;D_8008FE30=0x71;}
 marks[1]=0xA5000001u;__asm__ volatile("":::"eax","ecx","edx","memory");return(s32)0x87654321u;
}
__attribute__((noinline)) void func_151E7EF8(void){
 if(ordinal++!=2||observe()!=row->observations[1])error=1;
 if(row->effects&2){D_800E0BE0[0]^=0x5A;D_8008FE30=0x72;}
 marks[2]=0xA5000002u;__asm__ volatile("":::"eax","ecx","edx","memory");
}
static void(*volatile probe)(void)=func_15007440;
static int run(void){
 for(u32 n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  row=&rows[n];ordinal=0;error=0;for(u32 i=0;i<3;i++)marks[i]=0;
  for(u32 i=0;i<128;i++)scratch.bytes[i]=(u8)((i+16)*29+row->pattern*71+123);
  for(u32 i=0;i<96;i++)native_settings[i]=(s8)(i*29+row->pattern*71+123);
  D_800E0BE0[16]=(s8)row->saved;D_8008FE30=0xE2;probe();
  u32 v=2166136261u;for(u32 i=2;i<128;i++)v=(v^scratch.bytes[i])*16777619u;
  for(u32 i=0;i<96;i++)v=(v^(u8)native_settings[i])*16777619u;v=(v^D_8008FE30)*16777619u;
  if(error||ordinal!=3||v!=row->result||scratch.align!=row->header)return 1;
  for(u32 i=0;i<3;i++)if(marks[i]!=0xA5000000u+i)return 1;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
