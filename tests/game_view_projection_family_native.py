"""Generate freestanding i386 vectors for the actual family C and SDK contracts."""
import itertools
import json
import struct
import subprocess

from tools.tests import game_view_projection_family_oracle as model
from tools.experiments import game_view_projection_family as family
from tools.experiments import game_view_projection_command_candidates as source
from tools.experiments import game_view_projection_command_matching as matching
from tools.experiments import game_remaining_donor_candidates as build


def vectors():
    rows = []
    for kind, index, seed, trig_mode, sdk_mode, page in itertools.product(range(3), (0, 1, 3),
            range(2), (0, 1, 4), (0, 1), (0, 1)):
        near = model.parent.CLIPS[(index + seed) % 5]
        far = model.parent.CLIPS[(index + seed + 2) % 5]
        memory = model.fixture(index, near, far, page)
        if kind == 1:
            args = (index, model.VIEWS + index * 0x180 + 0xB8, model.bits(45.0), model.bits(60.0), near, far, model.bits(1.0))
        else:
            args = (index, model.bits(1.25), model.bits(-2.5), model.bits(1.0))
            if kind == 0:
                args += (model.parent.CLIPS[(index + seed + 1) % 5],)
        root = (model.PARENT, model.CHILD, model.WRAPPER)[kind]
        result, calls = model.reference(memory, args, trig_mode, sdk_mode, seed, root)
        calls = [(target, args) for target, args in calls if target != model.CHILD]
        views = []
        for base in (model.VIEWS, model.ALTERNATE, model.THIRD):
            for offset in range(0, 0x900, 4):
                address = base + offset
                if offset % 0x180 in model.NUMERIC:
                    value = model.read(result, address)
                elif offset % 0x180 == 0xB8:
                    value = int.from_bytes(bytes(result[address + i] for i in range(2)), 'big')
                    value |= result[address + 2] << 16 | result[address + 3] << 24
                else:
                    value = int.from_bytes(bytes(result[address + i] for i in range(4)), 'little')
                views.append(value)
        globals_ = [(model.read(result, model.BASE) - model.VIEWS) // 0x4000, result[model.PAGE],
            *[model.read(result, address) for address in model.GLOBALS]]
        rows.append(dict(kind=kind, index=index, seed=seed, trig_mode=trig_mode, sdk_mode=sdk_mode,
            page=page, near=near, far=far, args=list(args) + [0] * (7 - len(args)), calls=calls,
            views=views, globals=globals_, rows=[model.read(result, 0x800D9AC0 + i * 4) for i in range(12)],
            dirty=result[0x800D9AF0]))
    return rows


def program(records, parent_body=family.PARENT_BODY, child_body=family.SELECTED_CHILD):
    literal = lambda values: '{' + ','.join('0x%Xu' % (v & 0xFFFFFFFF) for v in values) + '}'
    entries = []
    for row in records:
        calls = [[target, *args, *([0] * (7 - len(args)))] for target, args in row['calls']]
        calls += [[0] * 8 for _ in range(6 - len(calls))]
        entries.append('{%s,%s,%d,{%s},%s,%s,%s,%du}' % (
            ','.join(str(row[key]) + 'u' for key in ('kind', 'index', 'seed', 'trig_mode', 'sdk_mode', 'page', 'near', 'far')),
            literal(row['args']), len(row['calls']), ','.join(literal(c) for c in calls),
            literal(row['views']), literal(row['globals']), literal(row['rows']), row['dirty']))
    wrapper = build.body(family.recover('extern u8 *D_800BE628;\n' +
        's32 func_1510B128(){return 0;}\n' +
        's32 func_1510B32C(s32 arg0,f32 arg1,f32 arg2,f32 arg3){func_1510B128(arg0, *(s32 *)&arg1, *(s32 *)&arg2, *(s32 *)&arg3, 0);\n'
        'D_800D9AC0[arg0][0]=arg3;D_800D9AC0[arg0][1]=arg1;D_800D9AC0[arg0][2]=arg2;D_800D9AF0=1;}\n'
        's32 func_1510B5F8(){return 0;}\n'), 'func_1510B32C')
    preamble = source.PREAMBLE.replace('s32 func_1510B5F8(', 'void func_1510B5F8(')
    return '''typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef int s32; typedef float f32;
typedef struct {u32 words[16];} Mtx;
extern u8 *D_800BE628;
''' + preamble + '''
ViewProjection138520 storage[3][6];
u8 *D_800BE628; u8 D_800BE9C0;
f32 D_800A2C24,D_800A2C28,D_800C3648,D_800C364C,D_800C3650,D_800D9B1C,D_800D9B20;
f32 D_800D9AC0[4][3]; u8 D_800D9AF0;
typedef struct {u32 kind,index,seed,trig_mode,sdk_mode,page,nearWord,farWord,args[7],count,calls[6][8],views[1728],globals[9],rows[12],dirty;} Case;
static Case cases[]={''' + ',\n'.join(entries) + '''};
static const u32 answers[]={''' + ','.join('0x%Xu' % x for x in model.parent.RESULTS) + '''};
static Case *current;static u32 calls[6][8];static int count,error,trigCount;
static int mismatch(u32 stage,u32 region,u32 offset,u32 expected,u32 actual){u32 data[6]={(u32)(current-cases),stage,region,offset,expected,actual};u32 call=4;__asm__ volatile("int $0x80":"+a"(call):"b"(1),"c"(data),"d"(24):"memory");return 2;}
static u32 word(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
static f32 number(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static void putword(void *p,u32 value){u8*b=p;int i;for(i=0;i<4;i++){b[i]=value&255;value>>=8;}}
static u32 getword(const void *p){const u8*b=p;return (u32)b[0]|(u32)b[1]<<8|(u32)b[2]<<16|(u32)b[3]<<24;}
static u32 wire(const void *p){int r;u32 a=(u32)p;if(!p)return 0;for(r=0;r<3;r++){u32 b=(u32)storage[r];if(a>=b&&a<b+0x900)return 0x24000+r*0x4000+(a-b);}error=1;return 0xDEADBEEF;}
static void *pointer(u32 p){u32 r=(p-0x24000)/0x4000,o=(p-0x24000)%0x4000;if(!p)return (void*)0;if(r>=3||o>=0x900){error=1;return (void*)0;}return (u8*)storage[r]+o;}
static void submit(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g){u32*v;if(count>=6){error=1;return;}v=calls[count++];v[0]=target;v[1]=a;v[2]=b;v[3]=c;v[4]=d;v[5]=e;v[6]=f;v[7]=g;}
static void trig_effect(void){int i=current->index,m=current->trig_mode;
if(m==1&&trigCount==1){D_800BE628=(u8*)storage[1];D_800A2C24=2.0f;storage[1][i].fovX=179.0f;}
if(m==4&&trigCount==4){D_800C364C=7.0f;D_800C3650=777.0f;D_800BE628=(u8*)storage[2];}}
__attribute__((noinline)) f32 cosf(f32 x){trigCount++;submit(0x15047C00,word(x),0,0,0,0,0,0);trig_effect();return number(answers[(current->seed+trigCount*3)%6]);}
__attribute__((noinline)) f32 sinf(f32 x){trigCount++;submit(0x15047D60,word(x),0,0,0,0,0,0);trig_effect();return number(answers[(current->seed+trigCount*3)%6]);}
__attribute__((noinline)) void guPerspectiveF(f32 mf[4][4],u16*n,f32 y,f32 x,f32 near,f32 far,f32 scale){int j;u32 a=word(y),b=word(x),c=word(near),d=word(far),e=word(scale);
submit(0x15047F00,wire(mf),wire(n),a,b,c,d,e);for(j=0;j<16;j++)putword((u8*)mf+j*4,0x3F000000|((a^b^c^d^e^(j*0x10203))&0x7FFFFF));
if(n){*n=(u16)(0x8000|((a^c^e)&0x7FFF));}
if(current->sdk_mode==1){D_800BE628=(u8*)storage[2];D_800BE9C0=1;}}
__attribute__((noinline)) void guMtxF2L(f32 mf[4][4],Mtx*m){int j;u32 values[16];submit(0x150A7790,wire(mf),wire(m),0,0,0,0,0);for(j=0;j<16;j++)values[j]=getword((u8*)mf+j*4)^(0x01010101u*(j+1));for(j=0;j<16;j++)putword((u8*)m+j*4,values[j]);}
''' + parent_body + '\n' + child_body + '\n' + wrapper + '''
static int run(void){unsigned n;int r,i,j,k;u8*b;
if(sizeof(ViewProjection138520)!=0x180||__builtin_offsetof(ViewProjection138520,fovX)!=0x74)return 90;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
current=&cases[n];count=error=trigCount=0;
for(r=0;r<3;r++){b=(u8*)storage[r];for(i=0;i<0x900;i++)b[i]=(i*13+0xA5)&255;
for(i=0;i<6;i++){ViewProjection138520*v=&storage[r][i];v->extentX=160.0f+i+r;v->extentY=120.0f+i+r;v->axisScaleX=1.25f+i+r;v->axisScaleY=0.75f+i+r;
v->projectionX=-123.0f+i+r;v->projectionY=-456.0f+i+r;v->baseFovX=60.0f+i+r;v->baseFovY=45.0f+i+r;v->fovX=75.0f+i+r;v->fovY=50.0f+i+r;v->projectionScaleX=1.5f+i+r;v->projectionScaleY=0.5f+i+r;
*(u16*)((u8*)v+0xB8)=0xA55A;for(j=0;j<16;j++)putword((u8*)v+0xBC+j*4,word((j+1)*0.125f+i+r));for(j=0;j<32;j++)putword((u8*)v+0x100+j*4,0x11223300+r*0x1000+i*0x100+j);}}
D_800BE628=(u8*)storage[0];D_800BE9C0=current->page;D_800A2C24=D_800A2C28=number(0x3C0EFA35);D_800C3648=3.0f;D_800C364C=number(current->nearWord);D_800C3650=number(current->farWord);D_800D9B20=0.125f;D_800D9B1C=1000.0f;
for(i=0;i<12;i++){putword((u8*)D_800D9AC0+i*4,0xA5A5A5A5);}
D_800D9AF0=0xA5;
if(current->kind==0)func_1510B128(current->args[0],number(current->args[1]),number(current->args[2]),number(current->args[3]),number(current->args[4]));
else if(current->kind==1)func_1510B5F8(current->args[0],pointer(current->args[1]),number(current->args[2]),number(current->args[3]),number(current->args[4]),number(current->args[5]),number(current->args[6]));
else func_1510B32C(current->args[0],number(current->args[1]),number(current->args[2]),number(current->args[3]));
if(error||count!=(int)current->count){return 1;}
for(i=0;i<count;i++)for(j=0;j<8;j++)if(calls[i][j]!=current->calls[i][j])return 1;
for(r=0;r<3;r++)for(i=0;i<0x900;i+=4){k=r*576+i/4;if(getword((u8*)storage[r]+i)!=current->views[k])return mismatch(1,r,i,current->views[k],getword((u8*)storage[r]+i));}
if(D_800BE628!=(u8*)storage[current->globals[0]]||D_800BE9C0!=current->globals[1])return mismatch(2,0,0,current->globals[1],D_800BE9C0);
{f32 g[]={D_800A2C24,D_800A2C28,D_800C3648,D_800C364C,D_800C3650,D_800D9B20,D_800D9B1C};for(i=0;i<7;i++)if(word(g[i])!=current->globals[i+2])return mismatch(3,0,i,current->globals[i+2],word(g[i]));}
for(i=0;i<12;i++){if(getword((u8*)D_800D9AC0+i*4)!=current->rows[i])return mismatch(4,0,i,current->rows[i],getword((u8*)D_800D9AC0+i*4));}
if(D_800D9AF0!=current->dirty)return mismatch(5,0,0,current->dirty,D_800D9AF0);
}return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


def run(out, label, records, parent_body=family.PARENT_BODY, child_body=family.SELECTED_CHILD):
    path = out / ('native-' + label + '.c')
    path.write_text(program(records, parent_body, child_body))
    results = []
    for profile in ('-O2', '-O0'):
        binary = path.with_suffix('.' + profile[1:])
        compiled = subprocess.run(['cc', '-m32', profile, '-std=c11', '-msse2', '-mfpmath=sse', '-mstackrealign',
            '-fno-strict-aliasing', '-fwrapv', '-fno-builtin', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
            '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)], capture_output=True, text=True)
        if compiled.returncode:
            raise ValueError(compiled.stderr)
        executed = subprocess.run([str(binary)], capture_output=True)
        results.append(executed.returncode)
        if executed.stdout:
            fields = struct.unpack('<6I', executed.stdout)
            binary.with_suffix(binary.suffix + '.json').write_text(json.dumps(dict(zip(
                ('case', 'stage', 'region', 'offset', 'expected', 'actual'), fields)), indent=2) + '\n')
    return results
