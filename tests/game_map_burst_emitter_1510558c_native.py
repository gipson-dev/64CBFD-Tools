"""Compile the actual SDK32 C and check independent guest-backed vectors."""
from pathlib import Path
import json,struct,subprocess
from tools.experiments import game_map_burst_emitter_1510558c_match as source
from tools.tests import game_map_burst_emitter_1510558c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    corpus=[c for c in g.cases()if c.profile<4 and c.phase==0];values=[len(corpus)]
    globals=(g.FIRST,g.SECOND,g.C0,g.C4,g.C8,*g.PARAMETERS,g.MARK)
    for c in corpus:
        initial=g.fixture(c);final,calls,_=g.reference(initial,c)
        values.extend((c.integer,c.profile,c.mutation));values.extend(initial[g.RECORD+i]for i in range(432));values.extend(g.read(initial,a)for a in globals);values.append(len(calls))
        for target,args in calls:
            flat=[]
            for a in args:flat.extend(a if isinstance(a,tuple)else(a,))
            values.extend((target,len(flat),*flat))
        values.extend(final[g.RECORD+i]for i in range(432));values.extend(g.read(final,a)for a in globals)
    binary=out/'native-expected.bin';binary.write_bytes(struct.pack('>%dI'%len(values),*(v&0xffffffff for v in values)))
    entry=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    template=Path(__file__).with_suffix('.c.in').read_text().replace('@BINARY@',binary.relative_to(source.ROOT).as_posix()).replace('@START@',entry)
    fragment=source.SPEC['fragment'];controls={
        'unsigned-modulo':fragment.replace('firstRandom % 56','firstRandom % 55'),
        'tag-mask':fragment.replace('emitter->tag & 31','emitter->tag & 63'),
        'strict-first-probability':fragment.replace('func_150ADA68() < D_800A23C0','func_150ADA68() <= D_800A23C0'),
        'strict-second-probability':fragment.replace('func_150ADA68() < D_800A23C8','func_150ADA68() <= D_800A23C8'),
        'negated-direction':fragment.replace('packet.direction.x = -emitter->direction.x','packet.direction.x = emitter->direction.x'),
        'packet-kind':fragment.replace('packet.kind = 1','packet.kind = 2'),
        'surface-tail':fragment.replace('packet.surface = emitter->surface;','packet.surface = emitter->surface;\n            packet.surface.values[8] ^= 1;'),
        'callback-channel':fragment.replace('1,\n                ((u8 *)record)[0xC], ((u8 *)record)[1]','1,\n                ((u8 *)record)[1], ((u8 *)record)[0xC]')}
    assert all(v!=fragment for v in controls.values())
    results=[]
    for label,body,opt in[('valid',fragment,opt)for opt in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
        path=out/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(template.replace('@FRAGMENT@',body))
        result=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
        assert result.returncode==0 and not result.stdout and not result.stderr,(label,result.stdout,result.stderr)
        result=subprocess.run([str(exe)],capture_output=True,timeout=30);assert(result.returncode==0)==(label=='valid'),(label,opt,result.returncode)
        results.append(dict(label=label,profile=opt,exit_code=result.returncode))
    report=dict(cases_each_positive_profile=len(corpus),actual_SDK32=True,strict_aliasing=True,UBSan=True,controls=len(controls),checks=results,
        defined_packet_bytes=86,uninitialized_packet_padding_not_compared=True,nonfinite_guest_and_symbolic_scope_separate=True,native_parent_not_claimed=True)
    (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');return report
