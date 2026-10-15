"""Actual pass/decoder/frustum C with an independent ordered product oracle."""
import itertools
import json
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_matrix_pass as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import game_view_matrix_pass_oracle as model


def trig_returns(quiet=True):
    return tuple(word|0x00400000 if quiet and word&0x7F800000==0x7F800000 and word&0x007FFFFF else word
        for word in model.planes.RETURNS)


def vectors(quiet=True):
    rows=[]
    for count,page,pattern,mode in itertools.product((-1,0,1,3),(0,1),range(3),range(5)):
        memory=model.fixture(count,page,pattern)
        with patch.object(model.planes,'RETURNS',trig_returns(quiet)):
            expected,calls=model.reference(memory,mode,seed=pattern)
        rows.append(dict(memory=memory,mode=mode,seed=pattern,expected=expected,calls=model.canonical_calls(calls)))
    return rows


def negatives(rows):
    ordinary=next(r for r in rows if model.read(r['memory'],model.COUNT)==3 and r['mode']==0 and r['seed']==1)
    changed=next(r for r in rows if model.read(r['memory'],model.COUNT)==3 and r['mode']==1 and r['seed']==1)
    shrink=next(r for r in rows if model.read(r['memory'],model.COUNT)==3 and r['mode']==4 and r['seed']==1)
    cached_page=source.BODY.replace('    s16 index;','    s16 index;\n    u8 page;').replace('        guMtxL2F(projection,','        page = D_800BE9C0;\n        guMtxL2F(projection,').replace(
        'D_800DC2A0[D_800BE9C0]','D_800DC2A0[page]')
    cached_base=source.BODY.replace('    s16 index;','    s16 index;\n    u8 *base = D_800BE628;').replace('D_800BE628 +','base +')
    reversed_product=source.BODY.replace('func_150A7A48((f32 (*)[4])(D_800D9C10 + index * 0x40),\n            projection,',
        'func_150A7A48(projection,\n            (f32 (*)[4])(D_800D9C10 + index * 0x40),')
    return (
        ('cached-page',cached_page,changed),
        ('cached-view-base',cached_base,changed),
        ('reversed-product',reversed_product,ordinary),
        ('wrong-product-slot',source.BODY.replace('products[index]','products[0]'),ordinary),
        ('cached-count',source.BODY.replace('    s16 index;','    s16 index;\n    s32 count = D_80082FA0;').replace('<= D_80082FA0','<= count'),shrink),
        ('missing-frustum',source.BODY.replace('        func_1501B22C(index);',''),ordinary),
    )


def program(owner,sdk,frustum,rows,body=source.BODY,quiet=True):
    literal=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)+'}'
    words=lambda memory:[model.read(memory,base+i) for base,size in model.BANKS for i in range(0,size,4)]
    cases=[]
    for row in rows:
        memory,expected=row['memory'],row['expected']
        packets=[[target,*args,*([0]*(3-len(args)))] for target,args in row['calls']]
        packets += [[0]*4]*(16-len(packets))
        globals_=lambda m:[model.read(m,model.BASE),model.read(m,model.COUNT),m[model.PAGE],*[model.read(m,model.TABLE+p*4) for p in model.PAGES]]
        cases.append('{%du,%du,%s,%s,%s,%s,%du,{%s}}'%(row['mode'],row['seed'],literal(words(memory)),literal(words(expected)),
            literal(globals_(memory)),literal(globals_(expected)),len(row['calls']),','.join(literal(p) for p in packets)))
    regions=[]
    first=0
    for base,size in model.BANKS:
        regions.append('{0x%Xu,%d,%d}'%(base,first,size//4))
        first+=size//4
    assert first==1436
    converter=build.body(sdk,'guMtxL2F').replace('void guMtxL2F(', 'void actual_decoder(',1)
    finish=build.body(frustum,'func_1501B22C').replace('void func_1501B22C(', 'void actual_frustum(',1)
    return '''typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
typedef union __attribute__((aligned(8))){s32 m[4][4];long long alignment;} Mtx;
typedef struct{u8 padding0[0x74];f32 unk74,unk78;u8 padding7C[0xC];
 f32 unk88,unk8C,unk90,unk94,unk98,unk9C,unkA0,unkA4,unkA8,unkAC,unkB0,unkB4;u8 tail[0xC8];}struct259;
static u32 storage[1444] __attribute__((aligned(8)));
#define banks (storage+4)
static struct{u32 before[4];s32 count;u8 page,pad[3];u8 *base;u32 after[4];}globals;
static struct{u32 before[4];u8 *values[256];u32 after[4];}table;
#define D_800BE628 (globals.base)
#define D_800BE9C0 (globals.page)
#define D_80082FA0 (globals.count)
#define D_800DC2A0 (table.values)
#define D_800D9C10 ((u8*)&banks[1288])
#define D_800D9D10 ((f32 (*)[4][4])&banks[1352])
#define D_80096900 (*(f32*)&banks[1428])
#define D_80096904 (*(f32*)&banks[1429])
typedef struct{u32 mode,seed,input[1436],expected[1436],inGlobals[7],outGlobals[7],count,packet[16][4];}Case;
static Case cases[]={''' + ',\n'.join(cases) + '''};
static Case *current;static u32 calls,ordinal;static int error;static f32 *privateMatrix;
static const u32 pages[]={0,1,128,255};
static const struct{u32 guest,first,words;}regions[]={''' + ','.join(regions) + '''};
static const u32 returns[]={''' + ','.join('0x%Xu'%v for v in trig_returns(quiet)) + '''};
static u32 trigOrdinal,trigIndex;
static int mismatch(u32 stage,u32 offset,u32 expected,u32 actual){u32 data[6]={(u32)(current-cases),stage,offset,expected,actual,current->mode};u32 call=4;__asm__ volatile("int $0x80":"+a"(call):"b"(1),"c"(data),"d"(24):"memory");return 2;}
static f32 floating(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static u32 wire(const void *pointer){u32 p=(u32)pointer,i;
 for(i=0;i<6;i++){u32 start=(u32)(banks+regions[i].first);if(p>=start&&p<start+regions[i].words*4)return regions[i].guest+p-start;}
 if(privateMatrix&&p>=(u32)privateMatrix&&p<(u32)privateMatrix+64)return 0xF0000000u+p-(u32)privateMatrix;
 return pointer?0xFFFFFFFFu:0;
}
static u8* address(u32 p){u32 i;for(i=0;i<6;i++){
 if(p>=regions[i].guest&&p<regions[i].guest+regions[i].words*4){return (u8*)(banks+regions[i].first)+p-regions[i].guest;}}
 return (u8*)0;
}
static int record(u32 target,u32 a,u32 b,u32 c){u32 p[4]={target,a,b,c},i;
 if(error||calls>=current->count||calls>=16){error=1;return 0;}
 for(i=0;i<4;i++)if(p[i]!=current->packet[calls][i])error=1;
 calls++;return !error;
}
static void effect(u32 target,u32 index){
 if(current->mode==1&&target==0x151EFEB8u&&(ordinal&1)){
  D_800BE9C0=D_800BE9C0?0:1;D_800BE628=address(0x34000);D_800DC2A0[D_800BE9C0]=address(0x45000);
 }else if(current->mode==2&&target==0x151EFEB8u&&!(ordinal&1)){
  privateMatrix[0]=7;((f32*)D_800D9C10)[index*16+1]=9;D_80082FA0=-1;
 }else if(current->mode==3&&target==0x150A7A48u){
  D_800BE628=address(0x34000);D_80082FA0=3;D_800DC2A0[D_800BE9C0]=address(0x44000);
 }else if(current->mode==4&&target==0x1501B22Cu){D_80082FA0=-1;D_800BE9C0=255;}
}
f32 cosf(f32 x){(void)x;trigOrdinal++;return floating(returns[(current->seed+trigIndex+trigOrdinal*3)%8]);}
f32 sinf(f32 x){(void)x;trigOrdinal++;return floating(returns[(current->seed+trigIndex+trigOrdinal*3)%8]);}
''' + converter + '\n' + finish + '''
void guMtxL2F(f32 output[4][4],Mtx *input){
 if(!privateMatrix&&wire(output)==0xFFFFFFFFu)privateMatrix=&output[0][0];
 if(!record(0x151EFEB8u,wire(output),wire(input),0))return;
 ordinal++;actual_decoder(output,input);effect(0x151EFEB8u,(ordinal-1)/2);
}
void func_150A7A48(f32 left[4][4],f32 right[4][4],f32 product[4][4]){
 f32 cached[4][4],row[4],value;int i,j,k;
 if(!record(0x150A7A48u,wire(left),wire(right),wire(product)))return;
 for(i=0;i<4;i++)for(j=0;j<4;j++)cached[i][j]=right[i][j];
 for(i=0;i<4;i++){
  for(k=0;k<4;k++)row[k]=left[i][k];
  for(j=0;j<4;j++){value=row[0]*cached[0][j];for(k=1;k<4;k++)value+=row[k]*cached[k][j];product[i][j]=value;}
 }effect(0x150A7A48u,(ordinal-1)/2);
}
void func_1501B22C(s32 index){
 if(!record(0x1501B22Cu,(u32)index,0,0))return;
 trigOrdinal=0;trigIndex=(u32)index;actual_frustum(index);effect(0x1501B22Cu,(u32)index);
}
''' + body + '''
static int run(void){u32 n,i,j,expected;
 if(sizeof(void*)!=4||sizeof(Mtx)!=64||sizeof(struct259)!=0x180)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];calls=ordinal=0;error=0;privateMatrix=(f32*)0;
  for(i=0;i<1444;i++)storage[i]=0xA55A1234u;
  for(i=0;i<1436;i++)banks[i]=current->input[i];
  for(i=0;i<4;i++)globals.before[i]=globals.after[i]=table.before[i]=table.after[i]=0xA55A1234u;
  globals.pad[0]=globals.pad[1]=globals.pad[2]=0xA5;
  D_800BE628=address(current->inGlobals[0]);D_80082FA0=(s32)current->inGlobals[1];D_800BE9C0=(u8)current->inGlobals[2];
  for(i=0;i<256;i++)D_800DC2A0[i]=(u8*)0;
  for(i=0;i<4;i++)D_800DC2A0[pages[i]]=address(current->inGlobals[3+i]);
  func_1510B690();
  if(error||calls!=current->count)return 1;
  if(wire(D_800BE628)!=current->outGlobals[0]||(u32)D_80082FA0!=current->outGlobals[1]||D_800BE9C0!=current->outGlobals[2])return 2;
  for(i=0;i<1436;i++)if(banks[i]!=current->expected[i])return mismatch(1,i,current->expected[i],banks[i]);
  for(i=0;i<256;i++){expected=0;for(j=0;j<4;j++)if(i==pages[j])expected=current->outGlobals[3+j];if(wire(D_800DC2A0[i])!=expected)return 2;}
  for(i=0;i<4;i++)if(storage[i]!=0xA55A1234u||storage[1440+i]!=0xA55A1234u||globals.before[i]!=0xA55A1234u||globals.after[i]!=0xA55A1234u||table.before[i]!=0xA55A1234u||table.after[i]!=0xA55A1234u)return 3;
  for(i=0;i<3;i++)if(globals.pad[i]!=0xA5)return 3;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


def run(out,label,rows,body=source.BODY,quiet=True):
    path=out/('native-'+label+'.c')
    path.write_text(program((out/'before-owner').read_text(),(out/'before-sdk').read_text(),
        (out/'before-frustum_owner').read_text(),rows,body,quiet))
    statuses,details=[],[]
    for profile in ('-O2','-O0'):
        binary=path.with_suffix('.'+profile[1:])
        result=subprocess.run(['cc','-m32',profile,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign',
            '-fno-strict-aliasing','-fwrapv','-fno-builtin','-ffp-contract=off','-ffreestanding','-nostdlib',
            '-static','-fno-pie','-no-pie','-fno-stack-protector','-Wall','-Wextra','-Werror',str(path),'-o',str(binary)],
            capture_output=True,text=True)
        if result.returncode:
            raise ValueError(result.stderr)
        result=subprocess.run([str(binary)],capture_output=True)
        statuses.append(result.returncode)
        details.append(list(struct.unpack('<6I',result.stdout)) if len(result.stdout)==24 else result.stdout.hex())
    (out/('native-'+label+'.json')).write_text(json.dumps(dict(cases=len(rows),statuses=statuses,details=details),indent=2)+'\n')
    return statuses
