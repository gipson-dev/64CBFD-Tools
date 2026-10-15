"""Native32 scanner with explicit big-endian opcode adaptation only."""
import json
import struct
import subprocess

from tools.experiments import game_texture_vertex_span as source
from tools.tests import game_texture_vertex_span_oracle as model

BANKS=((model.COMMANDS-32,128),(model.OUTPUT-16,12),(model.CACHE,8))


def program(rows,body):
    literal=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)+'}'
    words=lambda memory:[model.read(memory,base+i*4) for base,count in BANKS for i in range(count)]
    cases=[]
    for row in rows:
        expected,result,_=model.reference(row['memory'],row['args'],row['mode'])
        cases.append('{%s,%du,%s,%s,0x%Xu}'%(literal(row['args']),row['mode'],literal(words(row['memory'])),literal(words(expected)),result))
    assert body.count('*(s8 *)commands')==3
    body=body.replace('*(s8 *)commands','command_opcode(commands)')
    return '''typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
typedef union{struct{u32 w0,w1;}words;unsigned long long alignment;}Gfx;
typedef struct{u32 args[4],mode,input[148],expected[148],result;}Case;
static Case cases[]={''' + ',\n'.join(cases) + '''};
static u32 memory[156] __attribute__((aligned(8)));
#define bank (memory+4)
#define D_800B0E58 (bank+140)
static Case *current;static u32 calls;static int error;
static u32* address(u32 guest){if(guest>=0x21FE0u&&guest<0x221E0u)return bank+(guest-0x21FE0u)/4;
 if(guest>=0x23FF0u&&guest<0x24020u)return bank+128+(guest-0x23FF0u)/4;
 if(guest>=0x800B0E58u&&guest<0x800B0E78u)return bank+140+(guest-0x800B0E58u)/4;
 return (u32*)0;}
static s32 command_opcode(Gfx *commands){return (s32)commands->words.w0>>24;}
u32 func_1510D0EC(s32 id,s32 *extent,s32 priority,s32 retain){
 calls++;if((u32)id!=current->args[1]||priority!=3||retain||!extent)error=1;
 if(current->mode==1)D_800B0E58[id]=0x80050000u;
 else if(current->mode==2)*address(current->args[0]+4)=0x80050000u;
 else if(current->mode==3)*address(current->args[2])=0xDEADBEEFu;
 *extent=0x12345678;return 0xBAD01234u;
}
''' + body + '''
static int mismatch(u32 stage,u32 offset,u32 expected,u32 actual){u32 data[6]={(u32)(current-cases),stage,offset,expected,actual,current->mode};u32 call=4;
 __asm__ volatile("int $0x80":"+a"(call):"b"(1),"c"(data),"d"(24):"memory");return 2;}
static int run(void){u32 n,i,result;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];calls=0;error=0;
  for(i=0;i<156;i++)memory[i]=0xA55A1234u;
  for(i=0;i<148;i++)bank[i]=current->input[i];
  result=func_1510BF60((Gfx*)address(current->args[0]),(s32)current->args[1],address(current->args[2]),(s32)current->args[3]);
  if(error||calls!=1)return 1;
  if(result!=current->result)return mismatch(1,0,current->result,result);
  for(i=0;i<148;i++)if(bank[i]!=current->expected[i])return mismatch(2,i,current->expected[i],bank[i]);
  for(i=0;i<4;i++)if(memory[i]!=0xA55A1234u||memory[152+i]!=0xA55A1234u)return 3;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


def run(out,label,rows,body):
    path=out/('native-'+label+'.c')
    path.write_text(program(rows,body))
    statuses,details=[],[]
    diagnostics=[]
    for profile in ('-O2','-O0'):
        binary=path.with_suffix('.'+profile[1:])
        result=subprocess.run(['cc','-m32',profile,'-std=c11','-fno-strict-aliasing','-fwrapv','-fno-builtin',
            '-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector',
            '-Wall','-Wextra','-Werror','-Wno-error=maybe-uninitialized',str(path),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:
            raise ValueError(result.stderr)
        if result.stderr:
            assert result.stderr.count('warning:')==1 and 'vertexBase' in result.stderr and \
                'may be used uninitialized' in result.stderr,result.stderr
        diagnostics.append(result.stderr.replace(str(path),'CANDIDATE'))
        result=subprocess.run([str(binary)],capture_output=True)
        statuses.append(result.returncode)
        details.append(list(struct.unpack('<6I',result.stdout)) if len(result.stdout)==24 else result.stdout.hex())
    (out/('native-'+label+'.json')).write_text(json.dumps(dict(cases=len(rows),statuses=statuses,
        details=details,diagnostics=diagnostics),indent=2)+'\n')
    return statuses
