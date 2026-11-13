"""Native 32-bit finite-domain checks and effective negative controls."""
import subprocess
from tools.experiments import game_exponential_1504a2b0_match as packet
from tools.experiments.game_remaining_donor_candidates import body as source_body
from tools.tests import game_exponential_1504a2b0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state):
    root=packet.ROOT;out=packet.OUT
    body=source_body(packet.MANIFEST['selected'], packet.NAME); controls={
        'epsilon':('1.1920929e-7f','2.3841858e-7f'),
        'limit':('scale >= 1025','scale >= 1024'),
        'divisor':('magnitude / D_800990A0','magnitude / 1.0f'),
        'remainder':('(f32)scale * D_800990A8','(f32)scale * 0.5f'),
        'initial_result':('result = 1.0f;','result = 0.0f;'),
        'initial_term':('term = 1.0f;','term = 0.0f;'),
        'reciprocal':('return 1.0f / result;','return -1.0f / result;'),
        'positive':('return result;','return 1.0f;')}
    text='#include <ultra64.h>\n#define fabsf(x) __builtin_fabsf(x)\nf32 D_800990A0=0.6931471824645996f, D_800990A4=3.4028234663852886e38f, D_800990A8=0.6931471824645996f;\n'
    text+=body.replace('func_1504A2B0(', 'selected(',1)+'\n'
    for key,(a,b) in controls.items():
        assert body.count(a)==1,(key,a)
        text+=body.replace('func_1504A2B0(', 'bad_'+key+'(',1).replace(a,b,1)+'\n'
    rows=',\n'.join('{0x%08Xu,0x%08Xu}'%(x,g.reference(x)) for x in g.cases())
    text+='''\ntypedef union {u32 u; f32 f;} Word;
    typedef f32 (*Routine)(f32);
    static const u32 cases[][2]={\n'''+rows+'''\n};
    static int check(Routine f) {u32 i; for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){Word in,out;in.u=cases[i][0];out.f=f(in.f);if(out.u!=cases[i][1]) return 1;}return 0;}
    static int run(void){if(check(selected))return 10;\n'''
    for i,key in enumerate(controls):text+='if(!check(bad_'+key+'))return '+str(20+i)+';\n'
    text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    file=out/'native.c';file.write_text(text);reports={}
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);r=subprocess.run(native_command(opt)+[str(file),'-o',str(exe)],cwd=root,capture_output=True,text=True)
        assert r.returncode==0,(r.stdout,r.stderr)
        r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(opt,r.returncode,r.stderr)
        reports[opt]={'cases':len(g.cases()),'effective_negative_controls':len(controls),'ubsan':True}
    result={'profiles':reports,'scope':'finite inputs with defined signed float-to-int conversions'}
    return result
