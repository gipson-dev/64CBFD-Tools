"""SDK-typed native32 lanes, actor bytes, snapshots and diagnostic helper mutations."""
from tools.tests import game_sequence_state_reset_oracle as model

FLOATS = {0x800C3648, 0x800C364C, 0x800C3650, 0x800C35A4, 0x800C3674, 0x800C3678, model.LIMIT}
SPECS = [(base, width, indexed) for base, width, _, indexed in model.STORES]
SPECS += [(0x8008FD84, 1, False), (0x800C3670, 1, False), (model.LIMIT, 4, False)]


def name(base): return 'D_%08X' % base


def ctype(base, width):
    return 'f32' if base in FLOATS else 'void *' if base == 0x800C3D50 else (
        's8' if base == 0x800C3C8A else 's16' if width == 2 else 's32' if width == 4 else 'u8')


LANES = [(base + i * width, width, name(base) + ('[%d]' % i if indexed else ''), base)
    for base, width, indexed in SPECS for i in range(2 if indexed else 1)]
HEADER = '#include <ultra64.h>\n#include "structs.h"\nstruct Inputs {u32 pre;\n'
HEADER += '\n'.join('%s %s%s;' % (ctype(base, width), name(base), '[8]' if indexed else '') for base, width, indexed in SPECS)
HEADER += '\nstruct163 actors[3];u32 post;};\nextern struct Inputs inputs,expectedBefore;\nextern u32 mode,slot,calls,error,fired;\n'
HEADER += '\n'.join('#define %s inputs.%s' % (name(base), name(base)) for base, _, _ in SPECS)
HEADER += '\nvoid func_1501D044(s32);void func_150233BC(void);\n'


def assignment(target, field, base, value):
    cast = 'real(%s)' % value if base in FLOATS else '(void *)(u32)(%s)' % value if base == 0x800C3D50 else '(%s)(%s)' % (ctype(base, next(w for b,w,_ in SPECS if b == base)), value)
    # Field macros are for the actual body only; harness accesses use prefixed members.
    return '%s.field_%s=%s;' % (target, field, cast)


def harness_header():
    text = HEADER
    for base, _, _ in SPECS: text = text.replace(name(base), 'field_' + name(base))
    # The harness/provider use explicit fields, never the body macros.
    return '\n'.join(line for line in text.splitlines() if not line.startswith('#define')) + '\n'


def program():
    rows = []
    for slot, limit, pattern, mode in model.cases(native=True):
        memory = model.fixture(slot, limit, pattern); after, before, _ = model.reference(memory, slot, mode)
        values = lambda m:','.join('0x%Xu' % model.read(m, at, width) for at, width, _, _ in LANES)
        rows.append('{%d,%d,%d,0x%Xu,{%s},{%s},%d}' % (slot, pattern, mode, limit, values(before), values(after), after[model.TABLE + 167]))
    text = harness_header() + '''
struct Inputs inputs,expectedBefore;static struct Inputs expectedAfter;u32 mode,slot,calls,error,fired;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static void copy(void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)((u8*)a)[i]=((const u8*)b)[i];}
static u32 initial(u32 at,u32 width,u32 pattern){u32 i,v=0,base=at>=0x800C3500u?0x800C3500u:at>=0x800969B8u?0x800969B8u:0x8008FD80u;
 for(i=0;i<width;i++)v=(v<<8)|((pattern==1?(at+i-base)*13u+0xA5u:pattern==0?0u:255u)&255u);return v;}
'''
    text += 'struct Case{u32 slot,pattern,mode,limit,before[%d],after[%d],last;};\n' % (len(LANES), len(LANES))
    text += 'static const struct Case cases[]={' + ',\n'.join(rows) + '};\n'
    text += 'static void reset(const struct Case*c){u32 i;\nfor(i=0;i<sizeof(inputs);i++)((u8*)&inputs)[i]=0xA5;\n'
    for at, width, field, base in LANES:
        value = 'c->limit' if base == model.LIMIT else 'initial(0x%Xu,%d,c->pattern)' % (at, width)
        text += assignment('inputs', field, base, value) + '\n'
    text += 'for(i=0;i<168;i++)((u8*)inputs.actors)[i]=(u8)initial(0x800C3CA0u+i,1,c->pattern);\n'
    text += 'copy(&expectedBefore,&inputs,sizeof(inputs));copy(&expectedAfter,&inputs,sizeof(inputs));\n'
    for i, (_, _, field, base) in enumerate(LANES):
        text += assignment('expectedBefore', field, base, 'c->before[%d]' % i) + '\n'
        text += assignment('expectedAfter', field, base, 'c->after[%d]' % i) + '\n'
    text += '''
 for(i=0;i<168;i++)((u8*)expectedAfter.actors)[i]=0;((u8*)expectedAfter.actors)[167]=(u8)c->last;
 slot=c->slot;mode=c->mode;calls=error=fired=0;
}
void _start(void){u32 n;
 if(sizeof(void*)!=4||sizeof(f32)!=4||sizeof(struct163)!=56||__builtin_offsetof(struct163,unkC)!=12)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){reset(&cases[n]);func_1501D044((s32)slot);
  if(error||calls!=1||fired!=mode)die(22);if(!same(&inputs,&expectedAfter,sizeof(inputs)))die(21);}
 die(0);
}
'''
    return text


PROVIDER = harness_header() + '''
static int same(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
void func_150233BC(void){u32 i;calls++;
 if(!same(&inputs,&expectedBefore,sizeof(inputs)))error=1;
 for(i=0;i<168;i++)((u8*)inputs.actors)[i]=0;
 if(mode&1u){inputs.field_D_800C35B8[slot]=1234;inputs.field_D_800C3674=real(0xBF800000u);fired|=1;}
 if(mode&2u){inputs.field_D_8008FD84=127;inputs.field_D_800C3670=128;inputs.field_D_800C3C9E=0x1234;fired|=2;}
 if(mode&4u){inputs.field_D_800969C0=real(0x3FC00000u);inputs.field_D_800C3D50=(void*)0x80405678u;fired|=4;}
 if(mode&8u){inputs.field_D_800C363A[slot]=254;((u8*)inputs.actors)[167]=0x77;fired|=8;}
}
'''


def body_header():
    result = harness_header()
    result += '\n'.join('#define %s inputs.field_%s' % (name(base), name(base)) for base, _, _ in SPECS) + '\n'
    return result


def controls(body):
    early = body.replace('    D_800C3670 = 0;\n', '').replace('    func_150233BC();', '    D_800C3670 = 0;\n    func_150233BC();')
    return dict(wrong_word_stride=body.replace('D_800C35B8[slot]', 'D_800C35B8[slot * 4]'),
        wrong_sentinel=body.replace('= -100;', '= -99;'), missing_active=body.replace('D_800C3658[slot] = 1', 'D_800C3658[slot] = 0'),
        early_post_flag=early, late_sentinel=body.replace('    func_150233BC();', '    func_150233BC();\n    D_800C3C9E = -1;'),
        missing_limit=body.replace('D_800C3678 = limit', 'D_800C3678 = 0.0f'),
        missing_helper=body.replace('    func_150233BC();', ''), byte_sentinel=body.replace('D_800C3C9E = -1', 'D_800C3C9E = 255'))
