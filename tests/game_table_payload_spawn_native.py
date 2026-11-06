"""Native32 typed request, real split aggregate and independent byte snapshots."""
from tools.experiments import game_table_payload_spawn_candidates as c
from tools.tests import game_table_payload_spawn_oracle as g
from tools.tests.test_game_row_destination_fill import START

def program():
    h=c.HEADERS.replace('extern TableSpawnEntry1515A974 D_800A636C[];\n','')
    text='#include <ultra64.h>\n#include <string.h>\n'+h+'''
typedef char pointer_size[sizeof(void*)==4?1:-1];
typedef char request_size[sizeof(TableSpawnRequest1515A974)==40?1:-1];
typedef char payload_size[sizeof(TableSpawnPayload1515A974)==44?1:-1];
typedef char table_size[sizeof(TableSpawnEntry1515A974)==52?1:-1];
typedef char header_align[__alignof__(TableSpawnHeader1515A974)==1?1:-1];
typedef char values_align[__alignof__(TableSpawnValues1515A974)==4?1:-1];
typedef char request_owner[__builtin_offsetof(TableSpawnRequest1515A974,owner)==4?1:-1];
typedef char request_flags[__builtin_offsetof(TableSpawnRequest1515A974,flags)==38?1:-1];
static TableSpawnEntry1515A974 tables[512];
#define D_800A636C (tables+256)
static u8 ownerMemory[512],wantedOwner[512],object[256],wantedObject[256];
static u8 wantedTable[84],payload[44];
static TableSpawnRequest1515A974 expectedRequest;
static u32 calls,copies,bad,allocated,mode,alias;
static u8 *actor=ownerMemory+256;
static const u32 patterns[]={0,0x80000000u,1,0x7F800000u,0xFF800000u,0x7FC12345u,0x7F812345u,0xFFFFFFFFu};
static void wordbytes(u8*p,u32 v){u32 i;u8*q=(u8*)&v;for(i=0;i<4;i++)p[i]=q[i];}
static void actual_effect(TableSpawnRequest1515A974*p){
 u32 i;
 if(mode&1){actor[31]=255;wordbytes(actor+32,0xDEADBEEFu);}
 if(mode&2)for(i=0;i<52;i++)((u8*)D_800A636C)[i]=(u8)(i*31+0xA7);
 if(mode&4){wordbytes((u8*)p+8,0x12345678u);((u8*)p)[1]=0xED;}
}
u8 *func_151A8B20(TableSpawnRequest1515A974*p,s16 a,s32 b,u8 d,s32 e){
 u32 i;u8*x=(u8*)p,*y=(u8*)&expectedRequest;
 calls++;
 if(a!=-1||b!=44||d!=255||e!=0)bad=1;
 for(i=0;i<40;i++)if((i==0||(i>=4&&i<39))&&x[i]!=y[i])bad=1;
 actual_effect(p);
 if(!allocated)return(u8*)0;
 return alias==0?object:alias==1?actor-128:(u8*)tables+256*52-128;
}
void *memcpy(void*destination,const void*source,size_t n){
 u32 i;u8*d=destination;const u8*s=source;
 u8*expectedDestination=alias==0?object+128:alias==1?actor:(u8*)D_800A636C;
 copies++;
 if(d!=expectedDestination||n!=44)bad=1;
 for(i=0;i<n;i++){if(i>=44||s[i]!=payload[i])bad=1;d[i]=s[i];}
 return destination;
}
'''
    for name,b in dict(selected=c.SELECTED,**g.controls()).items():text+=b.replace(c.FUNCTION,name)+'\n'
    text+='''
typedef void(*Update)(u8*,s32);
__attribute__((noinline,noclone))static void invoke(Update fn,u8*p,s32 unused){fn(p,unused);}
static int variant(Update fn,u32 wrapped){
 u32 gate,pattern,outcome,effect,layout,i,j;u8*t=(u8*)D_800A636C;u8*tw=t-16;
 u8*er=(u8*)&expectedRequest;
 for(gate=0;gate<256;gate++)for(pattern=0;pattern<4;pattern++)for(outcome=0;outcome<2;outcome++)for(effect=0;effect<4;effect++)for(layout=0;layout<3;layout++){
  allocated=outcome;mode=effect==3?7:effect;alias=layout;
  for(i=0;i<512;i++)ownerMemory[i]=(u8)(i*13+pattern*17+89);
  for(i=0;i<256;i++)object[i]=(u8)(i*7+pattern*31+0x53);
  for(i=0;i<84;i++)tw[i]=(u8)(i*11+0xA3);
  for(i=0;i<13;i++)wordbytes(t+4*i,patterns[(i+pattern)&7]);
  actor[31]=(u8)gate;
  for(i=0;i<512;i++)wantedOwner[i]=ownerMemory[i];
  for(i=0;i<256;i++)wantedObject[i]=object[i];
  for(i=0;i<84;i++)wantedTable[i]=tw[i];
  for(i=0;i<44;i++)payload[i]=t[8+i];
  expectedRequest.kind=15;expectedRequest.owner=actor;
  for(i=0;i<8;i++)er[8+i]=t[i];
  for(i=16;i<36;i++)er[i]=0;
  expectedRequest.enabled=0;expectedRequest.mode=-1;expectedRequest.flags=2;
  if(gate==0){
   if(mode&1){wantedOwner[256+31]=255;wordbytes(wantedOwner+256+32,0xDEADBEEFu);}
   if(mode&2)for(i=0;i<52;i++)wantedTable[16+i]=(u8)(i*31+0xA7);
   if(allocated){u8*d=alias==0?wantedObject+128:alias==1?wantedOwner+256:wantedTable+16;for(i=0;i<44;i++)d[i]=payload[i];}
  }
  calls=copies=bad=0;
  if(wrapped)invoke(fn,actor,(s32)0xFEDCBA98u);else fn(actor,(s32)0xFEDCBA98u);
  if(bad||calls!=(gate==0)||copies!=((gate==0)&&allocated))return 1;
  for(j=0;j<512;j++)if(ownerMemory[j]!=wantedOwner[j])return 1;
  for(j=0;j<256;j++)if(object[j]!=wantedObject[j])return 1;
  for(j=0;j<84;j++)if(tw[j]!=wantedTable[j])return 1;
 }
 return 0;
}
static int run(void){
 if(variant(selected,0)||variant(selected,1))return 1;
'''
    for i,n in enumerate(g.controls()):text+=' if(variant(%s,0)!=1)return %d;\n'%(n,i+2)
    return text+'return 0;}\n'+START
