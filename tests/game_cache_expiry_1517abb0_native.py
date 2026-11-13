from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_cache_expiry_1517abb0_match as screen
root,out=screen.ROOT,screen.OUT;src=(out/'variant-split.c').read_text();a=src.index('void func_1517ABB0(void) {');b=src.index('\n}\n',a)+2;fn=src[a:b]
header=r'''
typedef int s32;typedef unsigned int u32;typedef unsigned short u16;typedef unsigned char u8;
#define NULL ((void*)0)
typedef struct {void *allocation;u8 age;u8 unused[3];} CacheEntry1517;
typedef struct {u8 countIndex,slots,unused[6];} CacheDescriptor1517;
typedef char abi[(sizeof(void*)==4&&sizeof(CacheEntry1517)==8&&sizeof(CacheDescriptor1517)==8)?1:-1];
static s32 D_800DD460[2];static CacheDescriptor1517 D_800A7230[2];static u16 D_800C4310[2];
static CacheEntry1517 actual[2][2][3][3],wanted[2][2][3][3];
static CacheEntry1517 *rows[2][2][3];
static int mode,frees;static u32 calls[30];
static void func_10004074(void *p){
 calls[frees++]=(u32)p;
 if(frees==1){if(mode==1)D_800A7230[0].slots=1;else if(mode==2)D_800C4310[0]=1;else if(mode==3)D_800DD460[0]=(s32)rows[0][1];else if(mode==4)D_800A7230[0].countIndex=1;}
}
'''
tail=r'''
static int run(void){
 static const int patterns[]={0,1,2,3};int total=0;
 for(int c0=0;c0<3;c0++)for(int c1=0;c1<3;c1+=2)for(int s0=0;s0<3;s0++)for(int s1=0;s1<3;s1+=2)for(int pat=0;pat<4;pat++)for(mode=0;mode<5;mode++)for(int enabled=0;enabled<4;enabled++){
  int ec[2]={c0==2?3:c0,c1},es[2]={s0==2?3:s0,s1},ed[2]={0,1},rootIndex[2]={0,0},expectedFrees=0;u32 expectedCalls[30];
  D_800C4310[0]=ec[0];D_800C4310[1]=ec[1];
  for(int g=0;g<2;g++){
   D_800A7230[g].countIndex=g;D_800A7230[g].slots=es[g];
   for(int a=0;a<2;a++)for(int r=0;r<3;r++){
    rows[g][a][r]=actual[g][a][r];
    for(int c=0;c<3;c++){int index=g*9+r*3+c+a;CacheEntry1517 *p=&actual[g][a][r][c];p->allocation=(void*)((index+pat)%5?0x350000+index*16:0);p->age=(u8[]){0,1,2,255}[(index+patterns[pat])%4];for(int x=0;x<3;x++)p->unused[x]=(u8)(g*13+r*7+c*3+x+0x45);wanted[g][a][r][c]=*p;}
   }
   D_800DD460[g]=(enabled&(1<<g))?(s32)rows[g][0]:0;
  }
  for(int g=0;g<2;g++)if(enabled&(1<<g)){
   int r=0,count=ec[ed[g]];
   while(r<count){int slots=es[g];if(slots){int col=0;do{CacheEntry1517 *p=&wanted[g][rootIndex[g]][r][col];if(p->allocation){if(p->age)p->age--;else{expectedCalls[expectedFrees++]=(u32)p->allocation;if(expectedFrees==1){if(mode==1)es[0]=1;else if(mode==2)ec[0]=1;else if(mode==3)rootIndex[0]=1;else if(mode==4)ed[0]=1;}wanted[g][rootIndex[g]][r][col].allocation=0;}slots=es[g];}col++;}while(col<slots);count=ec[ed[g]];}r++;}
  }
  frees=0;func_1517ABB0();if(frees!=expectedFrees)return 1;for(int i=0;i<frees;i++)if(calls[i]!=expectedCalls[i])return 2;
  for(int g=0;g<2;g++){if(D_800A7230[g].countIndex!=ed[g]||D_800A7230[g].slots!=es[g]||D_800C4310[g]!=ec[g])return 3;for(int a=0;a<2;a++)for(int r=0;r<3;r++)for(int c=0;c<3;c++){CacheEntry1517*p=&actual[g][a][r][c],*q=&wanted[g][a][r][c];if(p->allocation!=q->allocation||p->age!=q->age)return 4;for(int x=0;x<3;x++)if(p->unused[x]!=q->unused[x])return 5;}}
  total++;
 }
 return total==2880?0:6;
}
'''
controls={'group_bound':('group < 2','group < 1'),'age_update':('entry->age--;','entry->age = 0;'),'clear':('))->allocation = NULL;', '))->allocation = (void *)0x1234;'),'byte_stride':('byteOffset += 8;','byteOffset += 16;'),'row_reload':('count = D_800C4310[descriptor->countIndex];\n                }','count = 0;\n                }'),'slot_reload':('slots = descriptor->slots;\n                                goto next_slot;', 'slots = 0;\n                                goto next_slot;')}
def check(name,body,opt):
 path=out/('native-'+name+'.c');exe=out/('native-'+name+'-'+opt[1:]);path.write_text(header+body+tail+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
 p=subprocess.run([*native_command(opt,True),'-fno-builtin',str(path),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True)
for opt in ('-O0','-O2','-O3'):
 p=check('selected',fn,opt);assert p.returncode==0,(opt,p.returncode,p.stderr);print(opt,'2880 cases',flush=True)
for name,(a,b) in controls.items():
 assert fn.count(a)==1,(name,fn.count(a));p=check('control-'+name,fn.replace(a,b),'-O2');assert p.returncode!=0,(name,p.returncode)
print('six incorrect implementations rejected',flush=True)
