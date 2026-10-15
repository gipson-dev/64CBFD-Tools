"""Actual clip-command C in bounded endian-normalized native32 banks."""
import itertools
import json
import subprocess

from tools.experiments import game_view_clipping_commands as source
from tools.tests import game_view_clipping_oracle as model


def vectors():
    rows=[]
    for index,near,far,mode in itertools.product((0,1,3),(0,0x80000000,model.bits(2),0x7FC12345),
            (0,0x80000000,model.bits(5),0x7FCAB123),(0,1,3)):
        rows.append(dict(memory=model.fixture(pattern=2),args=(index,near,far),root=model.COMMAND,mode=mode))
    for count,pattern,skip,mode in itertools.product((-1,0,3),(2,3),(0,15),(0,1,3)):
        rows.append(dict(memory=model.fixture(count,pattern,skip),args=(),root=model.QUEUE,mode=mode))
    for row in rows:
        row['expected'],row['calls']=model.reference(row['memory'],row['args'],row['root'],row['mode'])
    return rows


def negatives(rows):
    command=next(r for r in rows if r['root']==model.COMMAND and r['mode']==0 and r['args']==(0,0,0))
    queue=next(r for r in rows if r['root']==model.QUEUE and r['mode']==1 and model.read(r['memory'],model.COUNT)==3 and r['calls'])
    ordinary=next(r for r in rows if r['root']==model.QUEUE and r['mode']==0 and model.read(r['memory'],model.COUNT)==3 and r['calls'])
    empty=next(r for r in rows if r['root']==model.QUEUE and model.read(r['memory'],model.COUNT)==0xFFFFFFFF)
    return (
        ('wrong-default',source.COMMAND_BODY.replace('nearPlane == 0.0f','nearPlane != 0.0f'),source.QUEUE_BODY,command,1),
        ('swapped-command-planes',source.COMMAND_BODY.replace('nearPlane, farPlane,','farPlane, nearPlane,'),source.QUEUE_BODY,command,1),
        ('missing-command-store',source.COMMAND_BODY.replace('[0] = nearPlane;','[0] = 0.0f;'),source.QUEUE_BODY,command,2),
        ('missing-command-dirty',source.COMMAND_BODY.replace('D_800D9B18 = 1;','D_800D9B18 = 0;'),source.QUEUE_BODY,command,2),
        ('cached-count',source.COMMAND_BODY,source.QUEUE_BODY.replace('    s32 index;','    s32 index;\n    s32 count = D_80082FA0;').replace('<= D_80082FA0','<= count'),queue,1),
        ('wrong-queue-scale',source.COMMAND_BODY,source.QUEUE_BODY.replace('PROJECTION_VIEWS_138520[index].matrixScale','1.0f'),ordinary,1),
        ('swapped-queue-planes',source.COMMAND_BODY,source.QUEUE_BODY.replace('pending[0], farPlane,','farPlane, pending[0],'),ordinary,1),
        ('missing-consume',source.COMMAND_BODY,source.QUEUE_BODY.replace('pending[0] = -1.0f;','pending[0] = 0.0f;'),ordinary,2),
        ('missing-empty-clear',source.COMMAND_BODY,source.QUEUE_BODY.replace('    D_800D9B18 = 0;','    if (D_80082FA0 >= 0) D_800D9B18 = 0;'),empty,2),
    )


def program(owner,rows,command=source.COMMAND_BODY,queue=source.QUEUE_BODY):
    literal=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)+'}'
    words=lambda memory:[model.read(memory,base+i) for base,size in model.BANKS for i in range(0,size,4)]
    entries=[]
    for row in rows:
        calls=[args for _,args in row['calls']]
        calls += [(0,)*7]*(6-len(calls))
        entries.append('{%du,%du,%s,%s,%s,0x%Xu,0x%Xu,%du,{%s}}' %
            (row['root']==model.QUEUE,row['mode'],literal(row['args'] or (0,0,0)),
            literal(words(row['memory'])),literal(words(row['expected'])),model.read(row['memory'],model.BASE),
            model.read(row['expected'],model.BASE),len(row['calls']),','.join(literal(c) for c in calls)))
    view=owner[owner.index('typedef struct {'):owner.index('extern f32 D_800A2C24')]
    regions=[]
    first=0
    for base,size in model.BANKS:
        regions.append('{0x%Xu,%d,%d}'%(base,first,size//4))
        first+=size//4
    assert first==1288
    return '''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 *D_800BE628;
''' + view + '''
static u32 storage[1296];
#define banks (storage+4)
#define D_80082FA0 (*(s32*)&banks[1282])
#define D_800D9AF8 ((f32 (*)[2])&banks[1198])
#define D_800D9B18 (((u8*)&banks[1152])[0xD8^3])
#define D_800D9B20 (*(f32*)&banks[1208])
#define D_800D9B1C (*(f32*)&banks[1207])
typedef struct{u32 kind,mode,args[3],input[1288],expected[1288],base,outBase,count,packet[6][7];} Case;
static Case cases[]={''' + ',\n'.join(entries) + '''};
static Case *current;static u32 count;static int error;
static const struct{u32 guest,first,words;}regions[]={''' + ','.join(regions) + '''};
static u32 word(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
static f32 floating(u32 value){union{u32 u;f32 f;}v;v.u=value;return v.f;}
static u32 wire(const void *p){u32 a=(u32)p,i;for(i=0;i<4;i++){
 u32 start=(u32)(banks+regions[i].first);if(a>=start&&a<start+regions[i].words*4)return regions[i].guest+a-start;}return 0xFFFFFFFFu;}
static u8* address(u32 p){u32 i;for(i=0;i<4;i++){
 if(p>=regions[i].guest&&p<regions[i].guest+regions[i].words*4){return (u8*)(banks+regions[i].first)+p-regions[i].guest;}}
 return (u8*)0;}
void func_1510B5F8(s32 index,u16 *normalization,f32 y,f32 x,f32 nearPlane,f32 farPlane,f32 scale){
 u32 packet[7]={(u32)index,wire(normalization),word(y),word(x),word(nearPlane),word(farPlane),word(scale)};u32 i;
 if(count>=current->count||count>=6){error=1;return;}
 for(i=0;i<7;i++)if(packet[i]!=current->packet[count][i])error=1;
 count++;if(error)return;
 if(current->mode==1){D_80082FA0=-1;D_800BE628=address(0x28000);D_800D9B20=7;D_800D9B1C=11;}
 else if(current->mode==2){D_800BE628=address(0x28000);if(index<5){((u32*)D_800D9AF8)[(index+1)*2]=0x3F000000u;((u32*)D_800D9AF8)[(index+1)*2+1]=0x7FCAB123u;}}
 else if(current->mode==3){((u32*)D_800D9AF8)[index*2]=0x41100000u;((u32*)D_800D9AF8)[index*2+1]=0xC1300000u;D_800D9B18=0xFE;}
 else if(current->mode==4&&current->kind&&count==1){D_80082FA0=5;D_800BE628=address(0x28000);}
}
''' + command + '\n' + queue + '''
static int run(void){u32 n,i;
 if(sizeof(void*)!=4||sizeof(ViewProjection138520)!=0x180||__builtin_offsetof(ViewProjection138520,matrixScale)!=0x84)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];count=0;error=0;
  for(i=0;i<1296;i++)storage[i]=0xA55A1234u;
  for(i=0;i<1288;i++)banks[i]=current->input[i];
  D_800BE628=address(current->base);if(!D_800BE628)return 91;
  if(current->kind)func_1510B51C();else func_1510B458((s32)current->args[0],floating(current->args[1]),floating(current->args[2]));
  if(error||count!=current->count)return 1;
  if(wire(D_800BE628)!=current->outBase)return 2;
  for(i=0;i<1288;i++)if(banks[i]!=current->expected[i])return 2;
  for(i=0;i<4;i++)if(storage[i]!=0xA55A1234u||storage[1292+i]!=0xA55A1234u)return 3;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


def run(out,label,rows,command=source.COMMAND_BODY,queue=source.QUEUE_BODY):
    path=out/('native-'+label+'.c')
    path.write_text(program(source.recover((out/'before-owner').read_text()),rows,command,queue))
    statuses=[]
    for profile in ('-O2','-O0'):
        binary=path.with_suffix('.'+profile[1:])
        result=subprocess.run(['cc','-m32',profile,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign',
            '-fno-strict-aliasing','-fwrapv','-fno-builtin','-ffp-contract=off','-ffreestanding','-nostdlib',
            '-static','-fno-pie','-no-pie','-fno-stack-protector','-Wall','-Wextra','-Werror',str(path),'-o',str(binary)],
            capture_output=True,text=True)
        if result.returncode:
            raise ValueError(result.stderr)
        statuses.append(subprocess.run([str(binary)],capture_output=True).returncode)
    (out/('native-'+label+'.json')).write_text(json.dumps(dict(cases=len(rows),statuses=statuses),indent=2)+'\n')
    return statuses
