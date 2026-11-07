"""SDK native32 semantics and eight finite, effective wrong-source controls."""
from tools.experiments import game_texture_tile_scan_candidates as source

def controls():
    b=source.SELECTED
    return dict(no_wildcard=b.replace(' || assetId == 0',''),ignore_occurrence=b.replace('occurrence-- <= 0','1'),predecrement=b.replace('occurrence-- <= 0','--occurrence <= 0'),skip_zero=b.replace('occurrence-- <= 0','occurrence-- < 0'),wrong_initial_count=b.replace('*tileCount = 0','*tileCount = 1'),wrong_increment=b.replace('*tileCount += 1','*tileCount += 2'),wrong_pair=b.replace('assetId == (s8)G_SETTILE && second == (s8)G_SETTILESIZE','assetId == (s8)G_SETTILE || second == (s8)G_SETTILESIZE'),wrong_return=b.replace('return index;','return index + 1;'))

def program():
    variants=controls();text='#include <ultra64.h>\ns32 D_800B0E58[7762];\n'+source.SELECTED+'\n'
    for n,b in variants.items():
        assert b!=source.SELECTED,n
        text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=r'''
typedef s32(*Scanner)(u8*,s32,s32,s32*);
static Scanner scanners[]={'''+','.join([source.FUNCTION,*['negative_'+n for n in variants]])+r'''};
static u32 actual[512],expected[512];static s32 countA,countB;
static void command(u32 *p,u32 i,u8 op,s32 value){p[2*i]=0x12345600;((u8*)p)[8*i]=op;p[2*i+1]=value;}
static s32 reference(u8*list,s32 id,s32 occurrence,s32*count){
 s32 i,j,k;*count=0;
 for(i=0;i<128;i++){
  u8 op=list[8*i];if(op==0xDF)return -1;if(op!=0xFD)continue;
  if(((s32*)list)[2*i+1]!=D_800B0E58[id]&&id!=0)continue;
  if(occurrence>0){occurrence--;continue;}
  for(j=i;list[8*j]!=0xF2;j++){}
  for(k=j+1;;k+=2){*count+=1;if(list[8*k]!=0xF5||list[8*(k+1)]!=0xF2)return j;}
 }return -999;
}
static int run(void){
 s32 ids[]={0,1,511,7761},occ[]={-2,-1,0,1,2,3,4,100};u32 id,oi,mask,pairs,ending,alias,v,i,j,n,killed=0; s32 *pa,*pb,a,b;
 for(id=0;id<4;id++)for(oi=0;oi<8;oi++)for(mask=0;mask<16;mask++)for(pairs=1;pairs<=3;pairs+=2)for(ending=0;ending<4;ending++)for(alias=0;alias<3;alias++)for(v=0;v<9;v++){
  for(i=0;i<512;i++)actual[i]=expected[i]=0;
  n=0;command(actual,n++,0xE6,0x12345678);
  for(i=0;i<4;i++){
   command(actual,n++,0xFD,mask>>i&1?0x87654321u:0x12345678);command(actual,n++,0xE6,0x55667788);command(actual,n++,0xF2,0x00FC00FC);
   for(j=1;j<pairs;j++){command(actual,n++,0xF5,0x12345678);command(actual,n++,0xF2,0x00FC00FC);}
   command(actual,n++,ending&1?0xF5:0xE7,0);command(actual,n++,ending&2?0xE7:0xF2,0);
  }
  command(actual,n++,0xDF,0);for(i=0;i<512;i++)expected[i]=actual[i];
  pa=alias==0?&countA:alias==1?(s32*)actual+1:(s32*)actual+2;
  pb=alias==0?&countB:alias==1?(s32*)expected+1:(s32*)expected+2;
  countA=countB=0x12345678;D_800B0E58[ids[id]]=0x87654321u;b=reference((u8*)expected,ids[id],occ[oi],pb);
  D_800B0E58[ids[id]]=0x87654321u;a=scanners[v]((u8*)actual,ids[id],occ[oi],pa);
  if(a!=b||*pa!=*pb){if(!v)return 31;killed|=1u<<(v-1);continue;}
  for(i=0;i<512;i++)if(actual[i]!=expected[i]){if(!v)return 32;killed|=1u<<(v-1);break;}
 }return killed==255?0:33;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
    return text,list(variants),12288
