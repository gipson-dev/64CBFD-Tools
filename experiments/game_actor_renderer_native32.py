"""Build full native32 renderer vectors from an endian-explicit independent reference."""
import re
from unittest.mock import patch

from tools.experiments import game_actor_renderer_matching as matching
from tools.tests import test_game_actor_renderer_recovery as proof
from tools.tests.test_game_dual_matrix_emitter import sdk_macro

IDS = {name: index + 1 for index, name in enumerate(proof.COUNTS)}
KINDS = (0, 7, 10, 255)
POINTER_ARGS = dict(func_150849CC=(0, 1), func_1503DA9C=(0,), func_1502F01C=(0,),
    func_1502F9FC=(0,), func_1502CC34=(0, 3, *range(4, 14)),
    func_1515D914=(0, 8, 9, 11, 13), func_151EFE88=(0,), func_1502FD70=(0,), func_15030F94=(0, 1))


def little_read(memory, address, size):
    return sum(memory[address + i] << (i * 8) for i in range(size))


def little_put(memory, address, value, size=4):
    for i in range(size):
        memory[address + i] = value >> (i * 8) & 255


def vectors():
    records = []
    class Collector:
        def receipt(self, *args, **kwargs):
            pass

        def compare(self, memory, slot=0, view=0, mode=0, extra=0, alpha=255, phase=0, plan=None):
            records.append((memory, (proof.OUTPUT, slot, view, 0x27000, alpha,
                proof.PARAMETERS, mode, extra), plan or proof.Plan(), False))

    with patch.multiple(proof.guest, read=little_read, put=little_put):
        for name in ('test_01_complete_graphics_modes_colors_and_lighting',
                'test_02_early_returns_live_masks_and_shift_boundaries',
                'test_03_callback_mutations_and_captured_lifetimes',
                'test_03b_lighting_force_flag_and_identity_boundaries'):
            getattr(proof.GameActorRendererRecoveryTests, name)(Collector())
        assert len(records) == 273
        for count in (31, 32, 33, 63, 64):
            for mode in (0, 3, 4):
                for skip in (0, 0xAAAAAAAA, 0xFFFFFFFF):
                    memory = proof.fixture(count=count, skip=skip, override=0xCCCCCCCC, enabled=-1)
                    records.append((memory, (proof.OUTPUT, 0, 0, 0x27000, -1,
                        proof.PARAMETERS, mode, 1), proof.Plan(), False))
        for alpha in (-1, 0, 254, 255, 256, 32767, 65535, -2147483648, 2147483647):
            records.append((proof.fixture(flags=8), (proof.OUTPUT, 0, 0, 0x27000,
                alpha, proof.PARAMETERS, 1, 1), proof.Plan(colors=tuple(alpha + i for i in range(10))), False))
        for mode in (0, 3, 5):
            memory = proof.fixture(count=65535, skip=0xFFFFFFFF)
            for kind in KINDS:
                little_put(memory, proof.S['D_800C4778'] + kind * 2, 65535, 2)
            records.append((memory, (proof.OUTPUT, 0, 0, 0x27000, 255,
                proof.PARAMETERS, mode, 1), proof.Plan(), True))
    return records


def expression(value, pointer=False):
    if isinstance(value, str):
        return '0'
    value &= 0xFFFFFFFF
    if not pointer:
        return '0x%08XU' % value
    for name, address in proof.S.items():
        if value == address:
            prefix = '&' if name in ('D_800C3E98', 'D_C3E98', 'D_800BE9C0', 'D_800D9900',
                'D_800DCD7C', 'D_800B0DF0') else ''
            return '(u32)(%s%s)' % (prefix, name)
    for address, size, name in ((proof.S['D_800CC2D0'], 26 * 0x32C, 'D_800CC2D0'),
            (proof.OUTPUT, 0x2000, 'output + 1'), (proof.CONFIG, 0x80, 'config'),
            (proof.PARAMETERS, 16, 'parameters'), (proof.PARTS, 256, 'partLists'),
            (proof.SPECIAL, 256, 'specialLists'), (proof.LIGHTS, 64, 'lights'),
            (0x26FC8, 256, 'matrixInput'), (0x277C8, 256, 'matrixExtra'),
            (proof.S['D_800C4778'], 512, 'D_800C4778'),
            (proof.S['D_800C4488'], 1024, 'D_800C4488'),
            (proof.S['D_800C48F0'], 1024, 'D_800C48F0')):
        if address <= value < address + size:
            return '(u32)((u8 *)(%s) + 0x%X)' % (name, value - address)
    return '0x%08XU' % value


def numbers(values):
    return '{' + ','.join('0x%X' % (value & 0xFFFFFFFF) for value in values) + '}'


def image(memory, address, size):
    return numbers(memory[address + i] for i in range(size))


def pointer_fixups(memory, actor):
    result = []
    for offset in range(0, 0x32C, 4):
        value = little_read(memory, actor + offset, 4)
        if value in (proof.LIGHTS, 0x27000, 0x27800):
            result.append('{0x%X,%s}' % (offset, expression(value, pointer=True)))
    assert len(result) <= 4
    return '{' + ','.join(result or ['{0,0}']) + '}', len(result)


def sdk(root):
    gbi = (root / 'conker/include/2.0L/PR/gbi.h').read_text()
    mbi = (root / 'conker/include/2.0L/PR/mbi.h').read_text()
    names = ('G_DL', 'G_DL_PUSH', 'gDma1p', 'gSPDisplayList',
        'G_RDPPIPESYNC', 'gDPNoParam', 'gDPPipeSync', 'G_MOVEWORD', 'G_MW_SEGMENT', 'gMoveWd', 'gSPSegment',
        'G_GEOMETRYMODE', 'gSPGeometryMode', 'gSPClearGeometryMode', 'gSPSetGeometryMode',
        'G_CULL_FRONT', 'G_CULL_BACK', 'G_CULL_BOTH', 'G_LIGHTING', 'G_FOG',
        'G_SETFOGCOLOR', 'G_SETPRIMCOLOR', 'G_SETENVCOLOR', 'gDPSetColor', 'DPRGBColor',
        'gDPSetFogColor', 'gDPSetPrimColor', 'gDPSetEnvColor',
        'G_MTX', 'G_MTX_MODELVIEW', 'G_MTX_LOAD', 'G_MTX_NOPUSH', 'G_MTX_PUSH', 'gDma2p', 'gSPMatrix')
    return sdk_macro(mbi, '_SHIFTL') + ''.join(sdk_macro(gbi, name) for name in names)


def source(root, body=matching.SELECTED, records=None):
    records = vectors() if records is None else records
    data = []
    cases = []
    with patch.multiple(proof.guest, read=little_read, put=little_put):
        for index, (memory, args, plan, all_skip) in enumerate(records):
            actor = proof.S['D_800CC2D0'] + args[1] * 0x32C
            input_memory = memory
            if all_skip:
                # Every wrapped bit is skipped: count changes reads, not commands/calls.
                input_memory = memory.copy()
                for kind in KINDS:
                    little_put(input_memory, proof.S['D_800C4778'] + kind * 2, 0, 2)
            returned, result, calls = proof.reference(input_memory, args, plan)
            if all_skip:
                for kind in KINDS:
                    little_put(result, proof.S['D_800C4778'] + kind * 2, 65535, 2)
            commands = [little_read(result, proof.OUTPUT + i * 4, 4)
                for i in range((returned - proof.OUTPUT) // 4)]
            def command_expression(i, value):
                first = commands[i - 1] if i & 1 else 0
                pointer = bool(i & 1 and (first >> 24 in (0xDE, 0xDA, 0xA0)
                    or first & 0xFFFFFF00 == 0xDB060000))
                return expression(value, pointer=pointer)
            data.append('static const u32 commands_%d[] = {%s};' % (index,
                ','.join(command_expression(i, value) for i, value in enumerate(commands)) or '0'))
            expected_calls = []
            for _, name, values in calls:
                parameters = values[3] if name == 'func_1502CC34' else (0, 0, 0, 0)
                values = list(values)
                if name == 'func_1502CC34': values[3] = proof.PARAMETERS
                expected_calls.append('{%d,%d,{%s},%s}' % (IDS[name], len(values),
                    ','.join(expression(value, pointer=i in POINTER_ARGS[name])
                        for i, value in enumerate(values)), numbers(parameters)))
            data.append('static const Call calls_%d[] = {%s};' % (index,
                ','.join(expected_calls) or '{0,0,{0},{0}}'))
            def action_value(address, value, size):
                pointer = size == 4 and (actor + 0x28C <= address < actor + 0x29C
                    or proof.S['D_800C4488'] <= address < proof.S['D_800C4488'] + 1024
                    or proof.S['D_800C48F0'] <= address < proof.S['D_800C48F0'] + 1024)
                return expression(value, pointer=pointer)
            actions = ['{%d,%d,%s,%s,%d}' % (IDS[name], ordinal, expression(address, pointer=True), action_value(address, value, size), size)
                for (name, ordinal), entries in plan.actions.items() for address, value, size in entries]
            data.append('static const Action actions_%d[] = {%s};' % (index,
                ','.join(actions) or '{0,0,0,0,0}'))
            initial_fixes, ninitial = pointer_fixups(memory, actor)
            final_fixes, nfinal = pointer_fixups(result, actor)
            optional = lambda state, address, size: little_read(state, address, size) if address in state else 0
            counts = lambda state: numbers(optional(state, proof.S['D_800C4778'] + kind * 2, 2)
                for kind in KINDS)
            pointers = lambda state, name: '{' + ','.join(expression(optional(state,
                proof.S[name] + kind * 4, 4), pointer=True) for kind in KINDS) + '}'
            scalar = lambda state, name, size=1: little_read(state, proof.S[name], size)
            cases.append('{' + ','.join((numbers(args[1:3]), numbers((args[4], args[6], args[7])),
                numbers((plan.identity, plan.tier, plan.skip)), numbers(plan.colors),
                image(memory, actor, 0x32C), image(result, actor, 0x32C), initial_fixes,
                final_fixes, str(ninitial), str(nfinal), image(memory, proof.CONFIG, 0x80),
                image(result, proof.CONFIG, 0x80), counts(memory), counts(result),
                pointers(memory, 'D_800C4488'), pointers(result, 'D_800C4488'),
                pointers(memory, 'D_800C48F0'), pointers(result, 'D_800C48F0'),
                numbers((scalar(memory, 'D_800BE9C0'), scalar(memory, 'D_800D9900'),
                    scalar(memory, 'D_800DCD7C', 4))),
                numbers((scalar(result, 'D_800BE9C0'), scalar(result, 'D_800D9900'),
                    scalar(result, 'D_800DCD7C', 4))),
                numbers(little_read(result, proof.S['D_800C3E98'] + i * 4, 4) for i in range(16)),
                'commands_%d' % index, str(len(commands)), 'calls_%d' % index, str(len(calls)),
                'actions_%d' % index, str(len(actions)))) + '}')
    return PRELUDE + matching.recovery.DECLARATIONS + sdk(root) + FIXTURE + body + '\n' + '\n'.join(data) + (
        '\nstatic const Case cases[] = {\n' + ',\n'.join(cases) + '\n};\n') + RUNNER


PRELUDE = '''#define NULL ((void *)0)
typedef unsigned char u8; typedef short s16; typedef unsigned short u16;
typedef int s32; typedef unsigned int u32; typedef float f32;
typedef struct { struct { u32 w0,w1; } words; } Gfx;
typedef struct { u8 bytes[64]; } Mtx;
typedef char widths[(sizeof(void *)==4 && sizeof(Gfx)==8 && sizeof(Mtx)==64)?1:-1];
'''

FIXTURE = r'''
u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16))), D_800BE9C0, D_800D9900, D_800DD2E4[3];
u8 config[0x80], parameters[16], lights[64], matrixInput[256], matrixExtra[256];
u8 *D_800B0DF0; s32 D_800DCD7C; u16 D_800C4778[256];
Gfx **D_800C48F0[256], **D_800C4488[256], *partLists[64], *specialLists[64];
Gfx D_80084160[1], D_80084190[1], D_800832C0[1], D_80082FC0[1], D_80083140[1], output[1026];
Mtx D_800C3E98, D_C3E98; u8 D_800D9E28[1];
typedef struct { u32 id,n,args[14],parameters[4]; } Call;
typedef struct { u32 id,ordinal,address,value,size; } Action;
typedef struct { u32 offset,value; } Fixup;
typedef struct {
    u32 slotView[2], alphaModeExtra[3], plan[3], colors[10];
    u8 before[0x32C],after[0x32C]; Fixup beforeFix[4],afterFix[4]; u32 nBeforeFix,nAfterFix;
    u8 beforeConfig[0x80],afterConfig[0x80]; u32 beforeCounts[4],afterCounts[4];
    u32 beforeParts[4],afterParts[4],beforeSpecial[4],afterSpecial[4],beforeGlobals[3],afterGlobals[3];
    u32 matrix[16]; const u32 *commands; u32 nCommands; const Call *calls; u32 nCalls;
    const Action *actions; u32 nActions;
} Case;
static const Case *current;
static u32 error,callIndex,ordinals[10],debug[3];
static void copy(u8 *to,const u8 *from,u32 n) { u32 i;for(i=0;i<n;i++)to[i]=from[i]; }
static void store(u32 address,u32 value,u32 size) {
    if(size==1) *(u8 *)address=(u8)value;
    else if(size==2) *(u16 *)address=(u16)value;
    else *(u32 *)address=value;
}
static u32 verify(u32 id,u32 *args,u32 n) {
    u32 i,j,ordinal=ordinals[id]++; const Call *expected;
    if(callIndex>=current->nCalls) { error=1;return ordinal; }
    expected=current->calls+callIndex++;
    if(expected->id!=id || expected->n!=n) error=2;
    for(i=0;i<n;i++) {
        if((id==1 && i==1) || (id==5 && i>=4)) {
            if(!args[i] || (args[i]&3)) error=3;
            if(id==5) for(j=4;j<i;j++) if(args[j]==args[i]) error=4;
        } else if(args[i]!=expected->args[i]) {
            error=5;debug[0]=i;debug[1]=args[i];debug[2]=expected->args[i];
        }
    }
    if(id==5) for(i=0;i<4;i++) if(((u32 *)args[3])[i]!=expected->parameters[i]) error=6;
    return ordinal;
}
static void actions(u32 id,u32 ordinal) {
    u32 i;for(i=0;i<current->nActions;i++) {
        const Action *a=current->actions+i;
        if(a->id==id && a->ordinal==ordinal) store(a->address,a->value,a->size);
    }
}
s32 func_150849CC(u8 *actor,s32 *tier) {
    u32 args[2]={(u32)actor,(u32)tier},o=verify(1,args,2);
    *tier=(s32)current->plan[1];actions(1,o);return (s32)current->plan[0];
}
s32 func_1503DA9C(u8 *actor,s32 identity,s32 tier,s32 flag) {
    u32 args[4]={(u32)actor,(u32)identity,(u32)tier,(u32)flag},o=verify(2,args,4);
    actions(2,o);return (s32)current->plan[2];
}
Gfx *func_1502F01C(Gfx *p,s32 slot) {
    u32 args[2]={(u32)p,(u32)slot},o=verify(3,args,2);
    p->words.w0=0xA0000002;p->words.w1=(u32)func_1502F01C;actions(3,o);return p+1;
}
Gfx *func_1502F9FC(Gfx *p,s32 slot) {
    u32 args[2]={(u32)p,(u32)slot},o=verify(4,args,2);
    p->words.w0=0xA0000002;p->words.w1=(u32)func_1502F9FC;actions(4,o);return p+1;
}
void func_1502CC34(u8 *actor,s32 view,s32 alpha,s32 *params,s32 *pr,s32 *pg,s32 *pb,
    s32 *er,s32 *eg,s32 *eb,s32 *fr,s32 *fg,s32 *fb,s32 *fa) {
    s32 *out[10]={pr,pg,pb,er,eg,eb,fr,fg,fb,fa};u32 i;
    u32 args[14]={(u32)actor,(u32)view,(u32)alpha,(u32)params,(u32)pr,(u32)pg,(u32)pb,
        (u32)er,(u32)eg,(u32)eb,(u32)fr,(u32)fg,(u32)fb,(u32)fa},o=verify(5,args,14);
    for(i=0;i<10;i++) { *out[i]=(s32)current->colors[i]; } actions(5,o);
}
Gfx *func_1515D914(Gfx *p,s32 view,s32 x,s32 y,s32 z,s32 flags,s32 scalar,s32 state,
    u8 *light,u8 *out,s32 count,u8 *other,s32 mode,u8 *data) {
    u32 args[14]={(u32)p,(u32)view,(u32)x,(u32)y,(u32)z,(u32)flags,(u32)scalar,(u32)state,
        (u32)light,(u32)out,(u32)count,(u32)other,(u32)mode,(u32)data},o=verify(6,args,14);
    p->words.w0=0xA000000E;p->words.w1=(u32)func_1515D914;actions(6,o);return p+1;
}
void func_151EFE88(Mtx *matrix) {
    u32 i,args[1]={(u32)matrix},o=verify(7,args,1);
    for(i=0;i<16;i++) { ((u32 *)matrix->bytes)[i]=0xB0000000+i; } actions(7,o);
}
void func_1502FD70(u8 *actor) { u32 args[1]={(u32)actor},o=verify(8,args,1);actions(8,o); }
Gfx *func_15030F94(Gfx *p,u8 *actor,s32 view,s32 flag) {
    u32 args[4]={(u32)p,(u32)actor,(u32)view,(u32)flag},o=verify(9,args,4);
    p->words.w0=0xA0000004;p->words.w1=(u32)func_15030F94;actions(9,o);return p+1;
}
static s32 map(u32 address) {
    s32 result;
    __asm__ volatile("pushl %%ebp; xorl %%ebp,%%ebp; int $0x80; popl %%ebp"
        :"=a"(result):"a"(192),"b"(address),"c"(8192),"d"(3),"S"(0x32),"D"(-1):"memory");
    return result;
}
static void unmap(u32 address) {
    s32 result;__asm__ volatile("int $0x80":"=a"(result):"a"(91),"b"(address),"c"(8192):"memory");
}
static s32 report(u32 code,u32 index) {
    u32 data[7]={index,code,error,callIndex,debug[0],debug[1],debug[2]};s32 result;
    __asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");
    return (s32)code;
}
'''

RUNNER = r'''
int run(void) {
    u32 c,i,j,k,viewAddress,mapped,kinds[4]={0,7,10,255};u8 expectedActor[0x32C];Gfx *end;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        const Case *test=cases+c;u8 *actor=D_800CC2D0+test->slotView[0]*0x32C;
        current=test;error=callIndex=0;for(i=0;i<10;i++)ordinals[i]=0;
        for(i=0;i<3;i++)debug[i]=0;
        for(i=0;i<1026;i++){output[i].words.w0=0x13579BDF;output[i].words.w1=0x2468ACE0;}
        copy(actor,test->before,0x32C);copy(expectedActor,test->after,0x32C);
        for(i=0;i<test->nBeforeFix;i++)store((u32)actor+test->beforeFix[i].offset,test->beforeFix[i].value,4);
        for(i=0;i<test->nAfterFix;i++)store((u32)expectedActor+test->afterFix[i].offset,test->afterFix[i].value,4);
        copy(config,test->beforeConfig,0x80);D_800B0DF0=config;
        D_800BE9C0=(u8)test->beforeGlobals[0];D_800D9900=(u8)test->beforeGlobals[1];
        D_800DCD7C=(s32)test->beforeGlobals[2];D_800DD2E4[0]=0x17;D_800DD2E4[1]=0x83;D_800DD2E4[2]=0xE1;
        for(i=0;i<256;i++){D_800C4778[i]=0;D_800C4488[i]=D_800C48F0[i]=NULL;}
        for(i=0;i<4;i++) {
            k=kinds[i];D_800C4778[k]=(u16)test->beforeCounts[i];
            D_800C4488[k]=(Gfx **)test->beforeParts[i];D_800C48F0[k]=(Gfx **)test->beforeSpecial[i];
        }
        for(i=0;i<64;i++){partLists[i]=(Gfx *)(0x02000000+i*0x100);specialLists[i]=(Gfx *)(0x03000000+i*0x100);}
        for(i=0;i<4;i++)((u32 *)parameters)[i]=i==3?144:(i+1)*11;
        for(i=0;i<64;i++)D_800C3E98.bytes[i]=(u8)(i*17+53);
        viewAddress=(u32)actor+0x304+test->slotView[1]*4;mapped=0;
        if(viewAddress<(u32)actor || viewAddress+4>(u32)actor+0x32C) {
            if(viewAddress<(u32)D_800CC2D0 || viewAddress+4>(u32)D_800CC2D0+sizeof(D_800CC2D0)) {
                mapped=viewAddress&~4095U;if((u32)map(mapped)!=mapped)return 90;
            }
            store(viewAddress,0xFEDCBA98,4);
        }
        end=func_1502CCFC(output+1,(s32)test->slotView[0],(s32)test->slotView[1],matrixInput+0x38,
            (s32)test->alphaModeExtra[0],(s32 *)parameters,(s32)test->alphaModeExtra[1],(s32)test->alphaModeExtra[2]);
        if(mapped)unmap(mapped);
        if(error || callIndex!=test->nCalls)return 10;
        if(end!=output+1+test->nCommands/2)return 11;
        for(i=0;i<test->nCommands;i++)if(((u32 *)(output+1))[i]!=test->commands[i]) {
            debug[0]=i;debug[1]=((u32 *)(output+1))[i];debug[2]=test->commands[i];return 12;
        }
        if(output[0].words.w0!=0x13579BDF || output[0].words.w1!=0x2468ACE0)return 13;
        for(i=test->nCommands/2+1;i<1026;i++)if(output[i].words.w0!=0x13579BDF || output[i].words.w1!=0x2468ACE0)return 14;
        for(i=0;i<0x32C;i++)if(actor[i]!=expectedActor[i])return 15;
        for(i=0;i<0x80;i++)if(config[i]!=test->afterConfig[i])return 16;
        for(i=0;i<4;i++) {
            j=kinds[i];if(D_800C4778[j]!=test->afterCounts[i] || (u32)D_800C4488[j]!=test->afterParts[i]
                || (u32)D_800C48F0[j]!=test->afterSpecial[i])return 17;
        }
        if(D_800BE9C0!=test->afterGlobals[0] || D_800D9900!=test->afterGlobals[1]
            || (u32)D_800DCD7C!=test->afterGlobals[2])return 18;
        for(i=0;i<16;i++)if(((u32 *)D_800C3E98.bytes)[i]!=test->matrix[i])return 19;
    }
    return 0;
}
'''
RUNNER = re.sub(r'return ([1-9]\d*);', r'return report(\1,c);', RUNNER)
