"""Actual recovered queue C in endian-normalized native32 backing storage."""
import json
import subprocess

from tools.experiments import game_view_pending_queue as source
from tools.tests import game_view_pending_queue_oracle as model


def vectors():
    rows = []
    for case in model.cases():
        expected, calls = model.reference(case['memory'], case['mode'])
        rows.append(dict(case, expected=expected, calls=calls))
    return rows


def negatives(rows):
    ordinary = next(r for r in rows if model.read(r['memory'], model.COUNT) == 1 and r['mode'] == 0 and r['calls'])
    shrink = next(r for r in rows if model.read(r['memory'], model.COUNT) == 3 and r['mode'] == 1 and r['calls'])
    rewrite = next(r for r in rows if model.read(r['memory'], model.COUNT) == 3 and r['mode'] == 3 and r['calls'])
    empty = next(r for r in rows if model.read(r['memory'], model.COUNT) == 0xFFFFFFFF)
    return (
        ('exclusive-bound', source.BODY.replace('index <= D_80082FA0', 'index < D_80082FA0'), ordinary, 1),
        ('cached-count', source.BODY.replace('    s32 index;', '    s32 index;\n    s32 count = D_80082FA0;').replace('<= D_80082FA0', '<= count'), shrink, 1),
        ('missing-consume', source.BODY.replace('pending[0] = -1.0f;', 'pending[0] = 0.0f;'), rewrite, 2),
        ('wrong-near-packet', source.BODY.replace('pending[0], 0.0f)', 'pending[0], 1.0f)'), ordinary, 1),
        ('swapped-offsets', source.BODY.replace('pending[1], pending[2]', 'pending[2], pending[1]'), ordinary, 1),
        ('missing-empty-clear', source.BODY.replace('    D_800D9AF0 = 0;', '    if (D_80082FA0 >= 0) D_800D9AF0 = 0;'), empty, 2),
    )


def program(rows, body=source.BODY):
    literal = lambda values: '{' + ','.join('0x%Xu' % (value & 0xFFFFFFFF) for value in values) + '}'
    words = lambda memory: [model.read(memory, base + i) for base, size in model.BANKS for i in range(0, size, 4)]
    entries = []
    for row in rows:
        packets = [packet for _, packet in row['calls']] + [(0,) * 5] * (6 - len(row['calls']))
        entries.append('{%du,%s,%s,%du,{%s}}' % (row['mode'], literal(words(row['memory'])),
            literal(words(row['expected'])), len(row['calls']), ','.join(literal(packet) for packet in packets)))
    return '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
static u32 storage[48];
#define banks (storage+4)
#define D_80082FA0 (*(s32*)&banks[2])
#define D_800D9AC0 ((f32 (*)[3])&banks[12])
#define D_800D9AF0 (((u8*)&banks[8])[0x40^3])
typedef struct{u32 mode,input[40],expected[40],count,packet[6][5];} Case;
static Case cases[]={''' + ',\n'.join(entries) + '''};
static Case *current;static u32 count;static int error;
static u32 word(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
void func_1510B128(s32 index,f32 x,f32 y,f32 scale,f32 nearFallback){
 u32 packet[5]={(u32)index,word(x),word(y),word(scale),word(nearFallback)};u32 i;
 if(count>=current->count||count>=6){error=1;return;}
 for(i=0;i<5;i++)if(packet[i]!=current->packet[count][i])error=1;
 count++;if(error)return;
 if(current->mode==1)D_80082FA0=-1;
 else if(current->mode==2&&count==1)D_80082FA0=5;
 else if(current->mode==3){
  ((u32*)D_800D9AC0)[index*3]=0x41100000u;
  if(index<5){u32 *p=(u32*)D_800D9AC0+(index+1)*3;p[0]=0x3F000000u;p[1]=0x7FCAB123u;p[2]=0x80000000u;}
 }else if(current->mode==4){D_80082FA0=0;D_800D9AF0=0xFE;((u32*)D_800D9AC0)[index*3+1]=0x12345678u;}
 else if(current->mode==5&&index<5)((u32*)D_800D9AC0)[(index+1)*3]=0xBF800000u;
 else if(current->mode==6)D_80082FA0=index<5?index+1:5;
}
''' + body + '''
static int run(void){u32 n,i;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(f32)!=4)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];count=0;error=0;
  for(i=0;i<48;i++)storage[i]=0xA55A1234u;
  for(i=0;i<40;i++)banks[i]=current->input[i];
  func_1510B3B0();
  if(error||count!=current->count)return 1;
  for(i=0;i<40;i++)if(banks[i]!=current->expected[i])return 2;
  for(i=0;i<4;i++)if(storage[i]!=0xA55A1234u||storage[44+i]!=0xA55A1234u)return 3;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


def run(out, label, rows, body=source.BODY):
    path = out / ('native-' + label + '.c')
    path.write_text(program(rows, body))
    statuses = []
    for profile in ('-O2', '-O0'):
        binary = path.with_suffix('.' + profile[1:])
        result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-msse2', '-mfpmath=sse',
            '-mstackrealign', '-fno-strict-aliasing', '-fwrapv', '-fno-builtin', '-ffp-contract=off',
            '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
            '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr)
        statuses.append(subprocess.run([str(binary)], capture_output=True).returncode)
    (out / ('native-' + label + '.json')).write_text(json.dumps(dict(cases=len(rows), statuses=statuses), indent=2) + '\n')
    return statuses
