"""Exercise source behavior on defined, non-overlapping 32-bit host inputs."""
import subprocess
from tools.experiments import game_effect_descriptor_150b9d8c_direct as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def run():
    source = packet.MANIFEST['selected_source']
    declarations = source[source.index('typedef struct EffectDescriptor150B9D8C'):source.index('/* Submit a randomized descriptor')]
    function = body(source, 'func_150B9D8C')
    controls = {
        'flags': ('descriptor.flags = 0x11', 'descriptor.flags = 0x12'),
        'selector': ('== -1', '== 0'),
        'height': ('+ 0xA6) + 2', '+ 0xA6) + 3'),
        'random': ('work.first & 255U', 'work.second & 255U'),
        'identity': ('actor[0x0C], actor[1]', 'actor[0x0D], actor[1]'),
        'mode': ('descriptor.mode = 0x30001', 'descriptor.mode = 0x30002'),
    }
    code = '#include <ultra64.h>\n' + declarations
    code += function.replace('func_150B9D8C(', 'selected(', 1) + '\n'
    for name, (old, new) in controls.items():
        assert old in function, name
        code += function.replace('func_150B9D8C(', 'bad_'+name+'(', 1).replace(old, new, 1) + '\n'
    code += r'''
static u32 storage[64];
static u8 *actor;
static int draws, calls, bad, mutate;
static u32 values[3];
u32 func_150ADA20(void) {
    u32 value = values[draws++];
    if (mutate) {
        *(s16 *)(actor+0x9C) = (s16)(100 + draws);
        *(s16 *)(actor+0xA0) = (s16)(-200 - draws);
        *(s16 *)(actor+0xA2) = (s16)(300 + draws);
        *(s16 *)(actor+0xA6) = (s16)(-400 - draws);
        actor[0x0C] = (u8)(0x50 + draws);
        actor[1] = (u8)(0x60 + draws);
    }
    return value;
}
void *func_1513C4EC(s32 address, s32 a1, u8 a2, u8 a3,
                    f32 x, f32 y, f32 z, f32 s, f32 t,
                    u8 r, u8 bits, s32 a11, s32 a12, s32 a13, u8 id, s32 who) {
    EffectDescriptor150B9D8C *d = (EffectDescriptor150B9D8C *)address;
    calls++;
    if (a1 || a2 != 2 || a3 || d->flags != 0x11 || d->count != 100 || d->category != 4 ||
        d->zero || d->phase || d->color[0] != 255 || d->color[1] != 0x78 ||
        d->color[2] || d->color[3] || d->color[4] || d->color[5] != 255 || d->mode != 0x30001 ||
        x != (mutate ? 103.0f : 100.0f) || y != (mutate ? -401.0f : -398.0f) ||
        z != (mutate ? -203.0f : -200.0f) || s != (mutate ? 303.0f : 300.0f) || s != t ||
        r != (values[0]&255u) || bits != (((values[2]&1u)<<1)+(values[1]&1u)) ||
        a11 != 3 || a12 != 255 || a13 || id != (mutate ? 0x53 : 0xd2) || who != (mutate ? 0x63 : 0xe3)) bad=1;
    return (void *)0;
}
typedef void (*Fn)(u8 *);
static int check(Fn fn) {
    for (int selected_case=0; selected_case<2; selected_case++)
    for (int m=0; m<2; m++)
    for (int pattern=0; pattern<4; pattern++) {
        for (int i=0; i<64; i++) storage[i]=0;
        actor=(u8 *)storage; mutate=m; draws=calls=bad=0;
        *(s16 *)(actor+0x98)=selected_case ? -1 : 0;
        *(s16 *)(actor+0x9C)=100; *(s16 *)(actor+0xA0)=-200;
        *(s16 *)(actor+0xA2)=300; *(s16 *)(actor+0xA6)=-400;
        *(u32 *)(actor+0x90)=0x12345678;
        actor[0x0C]=0xd2; actor[0x0D]=0xd3; actor[1]=0xe3;
        values[0]=0x76543210u+pattern; values[1]=0x12345678u+pattern; values[2]=0x80000001u+pattern;
        fn(actor);
        if (bad || draws != (selected_case ? 3 : 0) || calls != selected_case) return 1;
    }
    return 0;
}
static int run(void) {
    if (check(selected)) return 10;
'''
    for i, name in enumerate(controls):
        code += 'if (!check(bad_'+name+')) return '+str(20+i)+';\n'
    code += 'return 0; }\n' + START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
    path = packet.OUT/'native-direct.c'
    path.write_text(code)
    for opt in ('-O0', '-O2', '-O3'):
        exe = packet.OUT/('native-direct'+opt)
        result = subprocess.run(native_command(opt)+['-fno-strict-aliasing', str(path), '-o', str(exe)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        result = subprocess.run([str(exe)], capture_output=True)
        assert result.returncode == 0, (opt, result.returncode, result.stderr)
