"""Actual setup C and SDK bodies in bounded endian-normalized native32 banks."""
import itertools
import json
import struct
import subprocess

from tools.experiments import game_view_orthographic_setup as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import game_view_orthographic_oracle as model


def vectors():
    rows = []
    for case in model.mock_cases():
        expected, packet = model.reference(case['memory'], case['mode'])
        rows.append(dict(case, expected=expected, packet=packet, sdk=0))
    for width, height, coefficient in itertools.product((0.5, 1, 2, 4), (0.5, 1, 2, 4), (3, 5, 9)):
        memory = model.finite_sdk_fixture(width, height, coefficient)
        expected, packet = model.sdk_reference(memory)
        rows.append(dict(memory=memory, expected=expected, packet=packet, mode=0, unused=0x87654321, view=0, sdk=1))
    return rows


def negative_cases(rows):
    unsigned = source.BODY.replace('= D_800DD2F2;', '= (u16) D_800DD2F2;').replace('= D_800DD2F4;', '= (u16) D_800DD2F4;')
    unsigned_case = next(row for row in rows if not row['sdk'] and row['mode'] == 0 and row['view'] == 0 and model.read(row['memory'], model.CONFIG_NEAR, 2) == 0x8000)
    ordinary = next(row for row in rows if not row['sdk'] and row['mode'] == 0 and row['view'] == 0)
    aliases = next(row for row in rows if not row['sdk'] and row['mode'] == 0 and row['view'] == 2)
    before, call = source.BODY.split('    func_151EF954(', 1)
    early = before.replace('    D_800D9B20 =',
        '    f32 width = PROJECTION_VIEWS_138520[0].extentX;\n    f32 height = PROJECTION_VIEWS_138520[0].extentY;\n    D_800D9B20 =', 1)
    early += '    func_151EF954(' + call.replace('PROJECTION_VIEWS_138520[0].extentX', 'width').replace('PROJECTION_VIEWS_138520[0].extentY', 'height')
    return (
        ('unsigned-defaults', unsigned, unsigned_case, 2),
        ('wrong-near-packet', source.BODY.replace('1.0f, D_800A2C20, 1.0f', '0.0f, D_800A2C20, 1.0f'), ordinary, 1),
        ('wrong-derived-sign', source.BODY.replace('100.0f - D_800D9B1C', 'D_800D9B1C - 100.0f'), ordinary, 2),
        ('early-extents', early, aliases, 1),
    )


def program(before_owner, sdk_owner, converter_owner, rows, body=source.BODY):
    literal = lambda values: '{' + ','.join('0x%Xu' % value for value in values) + '}'
    words = lambda memory: [model.read(memory, base + i, 4) for base, size in model.BANKS for i in range(0, size, 4)]
    shorts = lambda memory: [model.read(memory, model.CONFIG_BANK + i, 2) for i in range(0, model.CONFIG_SIZE, 2)]
    cases = []
    for row in rows:
        memory, expected = row['memory'], row['expected']
        cases.append('{%s,%s,%d,%d,%s,%s,%s,%s,%s,%s}' % (
            '0x%Xu' % model.read(memory, model.BASE), '0x%Xu' % row['unused'], row['mode'], row['sdk'],
            literal(words(memory)), literal(words(expected)), literal(shorts(memory)), literal(shorts(expected)),
            '0x%Xu' % model.read(expected, model.BASE), literal(row['packet'])))
    view = before_owner[before_owner.index('typedef struct {'):before_owner.index('extern f32 D_800A2C24')]
    sdk = '\n'.join(build.body(converter_owner, name) for name in ('guMtxF2L2', 'func_151EFE00')) + '\n'
    sdk += '\n'.join(build.body(sdk_owner, name) for name in ('func_151EF800', 'func_151EF954'))
    sdk = sdk.replace('void func_151EF954(', 'void actual_151EF954(', 1)
    regions, start = [], 0
    for base, size in model.BANKS:
        regions.append('{0x%Xu,%d,%d}' % (base, start, size // 4))
        start += size // 4
    assert start == 256
    return '''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
typedef union __attribute__((aligned(8))){s32 m[4][4];long long alignment;} Mtx;
#define FTOFIX32(x) (long)((x)*(float)0x00010000)
''' + view + '''
static u32 storage[360] __attribute__((aligned(8)));
#define banks (storage+4)
static struct{u32 before[4];u16 values[32];u32 after[4];} config;
static u8 *D_800BE628;
#define D_800DD2F2 (*(s16*)&config.values[9])
#define D_800DD2F4 (*(s16*)&config.values[10])
#define D_800D9B1C (*(f32*)&banks[195])
#define D_800D9B20 (*(f32*)&banks[196])
#define D_800D9B28 (*(Mtx*)&banks[198])
#define D_800D3670 (*(f32*)&banks[228])
#define D_800A2C20 (*(f32*)&banks[244])
''' + sdk + '''
typedef struct{u32 base,unused,mode,sdk,input[256],expected[256];u16 configIn[32],configOut[32];u32 expectedBase,packet[8];} Case;
static Case cases[]={''' + ',\n'.join(cases) + '''};
static Case *current;static int calls,error;
static const struct{u32 guest,first,words;}regions[]={''' + ','.join(regions) + '''};
static u32 word(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
static u32 wire(const void *pointer){u32 p=(u32)pointer;int i;
 for(i=0;i<5;i++){u32 start=(u32)(banks+regions[i].first);if(p>=start&&p<start+regions[i].words*4)return regions[i].guest+p-start;}return 0xFFFFFFFFu;}
static u8* address(u32 pointer){int i;for(i=0;i<5;i++)if(pointer>=regions[i].guest&&pointer<regions[i].guest+regions[i].words*4)return (u8*)(banks+regions[i].first)+pointer-regions[i].guest;return (u8*)0;}
void func_151EF954(Mtx*matrix,f32 left,f32 right,f32 bottom,f32 top,f32 nearPlane,f32 farPlane,f32 scale){
 u32 packet[8]={wire(matrix),word(left),word(right),word(bottom),word(top),word(nearPlane),word(farPlane),word(scale)};int i;
 calls++;for(i=0;i<8;i++)if(packet[i]!=current->packet[i])error=1;
 if(error)return;
 if(current->sdk){actual_151EF954(matrix,left,right,bottom,top,nearPlane,farPlane,scale);return;}
 if(current->mode){D_800BE628=(u8*)(banks+96);D_800D9B20=9;D_800D9B1C=-11;D_800D3670=13;D_800A2C20=-8;
  ((f32*)(banks+96))[3]=7;((f32*)(banks+96))[4]=-3;D_800DD2F2=-32767;D_800DD2F4=32766;}
 for(i=0;i<16;i++)((u32*)matrix)[i]=0x11223300u^packet[1+i%7]^((u32)i*0x01010101u);
}
''' + body + '''
static int run(void){int n,i;
 if(sizeof(void*)!=4||sizeof(long)!=4||sizeof(ViewProjection138520)!=0x180||sizeof(Mtx)!=64||__alignof__(Mtx)!=8)return 90;
 for(n=0;n<(int)(sizeof(cases)/sizeof(cases[0]));n++){
  current=&cases[n];calls=error=0;
  for(i=0;i<360;i++)storage[i]=0xA55A1234u;
  for(i=0;i<256;i++)banks[i]=current->input[i];
  for(i=0;i<4;i++)config.before[i]=config.after[i]=0xA55A1234u;
  for(i=0;i<32;i++)config.values[i]=current->configIn[i];
  D_800BE628=address(current->base);if(!D_800BE628)return 91;
  func_1510B070((s32)current->unused);
  if(calls!=1||error)return 1;
  if(wire(D_800BE628)!=current->expectedBase)return 2;
  for(i=0;i<256;i++)if(banks[i]!=current->expected[i])return 2;
  for(i=0;i<32;i++)if(config.values[i]!=current->configOut[i])return 2;
  for(i=0;i<4;i++)if(storage[i]!=0xA55A1234u||config.before[i]!=0xA55A1234u||config.after[i]!=0xA55A1234u)return 3;
  for(i=260;i<360;i++)if(storage[i]!=0xA55A1234u)return 3;
 }return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


def run(out, label, rows, body=source.BODY):
    path = out / ('native-' + label + '.c')
    path.write_text(program((out / 'before-owner').read_text(), (out / 'before-callee').read_text(),
        (out / 'before-converter').read_text(), rows, body))
    results = []
    for profile in ('-O2', '-O0'):
        binary = path.with_suffix('.' + profile[1:])
        result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-msse2', '-mfpmath=sse', '-mstackrealign',
            '-fno-strict-aliasing', '-fwrapv', '-fno-builtin', '-ffp-contract=off', '-ffreestanding', '-nostdlib',
            '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr)
        result = subprocess.run([str(binary)], capture_output=True)
        results.append(result.returncode)
    (out / ('native-' + label + '.json')).write_text(json.dumps(dict(cases=len(rows), statuses=results), indent=2) + '\n')
    return results
