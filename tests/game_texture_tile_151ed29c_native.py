"""Native32 defined-index and overlapping-output texture tile checks."""
from pathlib import Path
import json,os,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable';source=(out/os.environ.get('TILE_SOURCE','formatted.c')).read_text()
start=source.index('#ifdef __GNUC__\n#define TILE_151ED29C_ALIAS');begin=source.index('Gfx *func_151ED29C(',start);end=source.index('\n}',begin)+2
header='#include <ultra64.h>\n'+source[start:begin];fn=source[begin:end]
controls={
 'late-format':fn.replace('    format = image->format;\n    gDPPipeSync(syncCommand);','    gDPPipeSync(syncCommand);\n    format = image->format;'),
 'wrong-rounding':fn.replace(' * image->width + 7)', ' * image->width + 6)'),
 'wrong-size-table':fn.replace('D_8009DEBC[image->size]','D_8009DEB8[image->size]'),
 'wrong-width-mask':fn.replace('widthMask = 1','widthMask = 2'),
 'wrong-height-mask':fn.replace('heightMask = 1','heightMask = 2'),
 'wrong-return':fn.replace('return commands;','return commands + 1;'),
}
assert all(code!=fn for code in controls.values())
harness='''
u8 D_8009DEB0[]={3,1,0,0},D_8009DEB4[]={2,1,0,0},D_8009DEB8[]={1,1,2,2},D_8009DEBC[]={2,2,2,3};
typedef union { u32 align; u8 data[128]; } Block;
static Block actual,expected;
static u32 get16(u8 *p){return p[0]|((u32)p[1]<<8);}
static void set16(u8 *p,u32 v){p[0]=v;p[1]=v>>8;}
static void set32(u8 *p,u32 v){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static int mask(int x){int n=1,p=2;if(x>=3){do{p*=2;n++;}while(p<x);}return n;}
static void reference(u8 *a,int cursor,int image,int dest){
 u32 w=get16(a+image+6),h=get16(a+image+8),s=a[image+11],fmt;int wm,hm;
 set32(a+dest,(s32)(w*h+D_8009DEB0[s])>>(D_8009DEB4[s]&31));
 w=get16(a+image+6);h=get16(a+image+8);wm=mask(w);hm=mask(h);
 fmt=a[image+10];set32(a+cursor,0xe7000000u);set32(a+cursor+4,0);
 s=a[image+11];set32(a+cursor+8,0xf5000000u|((fmt&7)<<21)|((D_8009DEBC[s]&3)<<19));set32(a+cursor+12,0x07000000u);
 s=a[image+11];w=get16(a+image+6);
 set32(a+cursor+16,0xf5000000u|((fmt&7)<<21)|((s&3)<<19)|((((D_8009DEB8[s]*w+7)>>3)&511)<<9));
 set32(a+cursor+20,0x80200u|((hm&15)<<14)|((wm&15)<<4));set32(a+cursor+24,0xf2000000u);
 w=get16(a+image+6);h=get16(a+image+8);set32(a+cursor+28,((((w-1)*4)&4095)<<12)|(((h-1)*4)&4095));
}
static int run(void){
 static const int dims[]={0,1,2,3,4,16,255,65535};
 for(int a=0;a<2;a++)for(int i=0;i<8;i++)for(int j=0;j<8;j++)for(int f=0;f<8;f++)for(int s=0;s<4;s++){
  int image=16,cursor=a?20:64,dest=104;
  for(int k=0;k<128;k++)actual.data[k]=expected.data[k]=(u8)(k*13+11);
  set16(actual.data+image+6,dims[i]);set16(actual.data+image+8,dims[j]);actual.data[image+10]=f;actual.data[image+11]=s;
  for(int k=0;k<128;k++)expected.data[k]=actual.data[k];
  reference(expected.data,cursor,image,dest);
  Gfx *returned=func_151ED29C((Gfx *)(actual.data+cursor),(TextureTile151ED29C *)(actual.data+image),(s32 *)(actual.data+dest));
  if(returned!=(Gfx *)(actual.data+cursor+32))return 1;
  for(int k=0;k<128;k++)if(actual.data[k]!=expected.data[k])return 2;
 }
 return 0;
}
'''
def run(name,code,opt):
    src=out/(name+'.c');exe=out/(name+'-'+opt[1:]);src.write_text(header+code+harness+START)
    alias_flags=[] if os.environ.get('TILE_STRICT_ALIASING')=='1' else ['-fno-strict-aliasing']
    p=subprocess.run(native_command(opt)+alias_flags+[str(src),'-o',str(exe)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    return subprocess.run([str(exe)],capture_output=True,text=True)
for opt in ('-O0','-O2','-O3'):
    p=run('native-candidate',fn,opt);assert p.returncode==0,(opt,p.returncode,p.stderr)
    for name,code in controls.items():
        p=run('control-'+name,code,opt);assert p.returncode!=0,(opt,name)
report={'cases_per_optimization':4096,'optimizations':['O0','O2','O3'],'effective_controls':list(controls),
        'defined_size_indices':True,'overlap_and_ubsan':True,'strict_aliasing':os.environ.get('TILE_STRICT_ALIASING')=='1','uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
