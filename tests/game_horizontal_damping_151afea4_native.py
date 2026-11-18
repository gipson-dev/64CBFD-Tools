"""Fresh native32 C with the existing damping corpus and effective controls."""
import json
import subprocess
from tools.experiments import game_horizontal_damping_151afea4_match as s
from tools.tests import game_four_damping_callbacks_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def main():
    controls = {
        'x-add': ('state->x *= *factor;', 'state->x += *factor;'),
        'z-add': ('state->z *= *factor;', 'state->z += *factor;'),
        'wrong-factor': ('f32 *factor = &state->damping;', 'f32 *factor = &state->x;'),
        'skip-odd': ('ticks = (u32)D_800BE9E4;', 'ticks = (u32)D_800BE9E4 & ~1U;'),
        'copy-z': ('state->x *= *factor;', 'state->x = state->z * *factor;'),
        'return-zero': ('    return 1;', '    return 0;'),
    }
    code = '#include <ultra64.h>\n_Static_assert(sizeof(void *) == 4, "native32");\n' + s.PIN['declarations'] + '\ns32 D_800BE9E4;\n'
    code += 'struct Case { u32 tick,x,z,factor,expected_x,expected_z; };\nstatic const struct Case cases[]={\n'
    count = 0
    for c in g.cases():
        memory, _, _ = g.reference(c, g.fixture(c))
        values = (c.tick, c.x, c.z, c.factor, g.read(memory, g.RECORD + 0x58), g.read(memory, g.RECORD + 0x60))
        code += '{' + ','.join('0x%Xu' % v for v in values) + '},\n'
        count += 1
    code += '};\nstatic f32 value(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}\nstatic u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}\n'
    for name, text in {'selected': s.PIN['body'], **{name: s.PIN['body'].replace(a, b, 1) for name, (a, b) in controls.items()}}.items():
        if name != 'selected':
            assert text != s.PIN['body'], name
        code += text.replace(s.NAME, 'test_' + name.replace('-', '_'), 1) + '\n'
    code += '''
typedef s32 (*Test)(DampingState151AFEA4 *,void *);
static int check(Test test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 const struct Case *c=&cases[n];DampingState151AFEA4 state;u8 *bytes=(u8 *)&state;
 for(i=0;i<sizeof(state);i++)bytes[i]=0xa5;
 D_800BE9E4=(s32)c->tick;state.x=value(c->x);state.z=value(c->z);state.damping=value(c->factor);
 if(test(&state,(void *)0x12345678)!=1||word(state.x)!=c->expected_x||word(state.z)!=c->expected_z||word(state.damping)!=c->factor||(u32)D_800BE9E4!=c->tick)return 1;
 for(i=0;i<sizeof(state);i++)if((i<0x58||(i>=0x5c&&i<0x60)||(i>=0x64&&i<0xa8))&&bytes[i]!=0xa5)return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
    for i, name in enumerate(controls):
        code += 'if(!check(test_' + name.replace('-', '_') + '))return %d;\n' % (20 + i)
    code += 'return 0;}\n' + START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
    source = s.OUT / 'native.c'
    source.write_text(code)
    profiles = {}
    for opt in ('-O0', '-O2', '-O3'):
        exe = s.OUT / ('native' + opt)
        run = subprocess.run(native_command(opt) + ['-fno-builtin', str(source), '-o', str(exe)], cwd=s.ROOT, capture_output=True, text=True)
        assert run.returncode == 0 and not run.stdout and not run.stderr, (opt, run.stdout, run.stderr)
        run = subprocess.run([str(exe)], capture_output=True)
        assert run.returncode == 0, (opt, run.returncode, run.stderr)
        profiles[opt] = dict(cases=count, rejected_controls=len(controls), UBSan=True)
    report = dict(profiles=profiles, nonfinite_or_native_private_stack_claim=False)
    (s.OUT / 'native-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
