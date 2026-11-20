"""Native SDK32 defined-byte recovery checks, separate from literal frame matching."""
from pathlib import Path
import json,struct,subprocess
from tools.experiments import game_map_trail_emitter_151058b4_recovery as source
from tools.tests import game_map_trail_emitter_151058b4_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    corpus=[c for c in g.cases()if c.phase==0 and c.count not in(0x7FC12345,0xFF800000)and not c.nan];values=[len(corpus)];parent_count=0
    globals=(g.RATE,g.BASE,g.RANGE_BASE,g.RANGE_SCALE,g.LIVE_SCALE,g.LIVE_BASE,g.MARK)
    for index,c in enumerate(corpus):
        mode=index%5;initial=g.fixture(c);expected=g.reference(initial,c)if mode in(0,1,3)else(g.public(initial),[],[])
        final,calls,_=expected;final=dict(final)
        if mode in(1,3):calls=[(g.ENTRY,(g.RECORD,)),*calls];final[g.RECORD+0x34]|=1
        elif mode==2:final[g.RECORD+0x34]&=254
        parent_count+=bool(mode)
        values.extend((c.blocked,c.integer,c.seed,c.mutation,mode));values.extend(initial[g.RECORD+i]for i in range(56))
        for base in(g.SOURCE,g.ALT):values.extend(initial[base+i]for i in range(22))
        values.extend(g.read(initial,a)for a in globals);values.append(len(calls))
        for target,args in calls:
            flat=[]
            for a in args:flat.extend(a if isinstance(a,tuple)else(a,))
            values.extend((target,len(flat),*flat))
        values.extend(final[g.RECORD+i]for i in range(56))
        for base in(g.SOURCE,g.ALT):values.extend(final[base+i]for i in range(22))
        values.extend(g.read(final,a)for a in globals)
    binary=out/'native-expected.bin';binary.write_bytes(struct.pack('>%dI'%len(values),*(v&0xffffffff for v in values)))
    entry=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    template=Path(__file__).with_suffix('.c.in').read_text().replace('@BINARY@',binary.relative_to(source.ROOT).as_posix()).replace('@START@',entry).replace('@TYPES@',source.TYPES)
    fragment=source.FRAGMENT;controls={
        'gate':fragment.replace('record->emitter.gate) == 0','record->emitter.gate) != 0'),
        'strict-count':fragment.replace('remaining > 1.0f','remaining >= 1.0f'),
        'byte-modulus':fragment.replace('% 101U','% 100U'),
        'duration-modulus':fragment.replace('% 31U','% 30U'),
        'signed-height':fragment.replace('(f32)emitter->source->y','(f32)(u16)emitter->source->y'),
        'loop-decrement':fragment.replace('remaining -= 1.0f','remaining -= 2.0f'),
        'channels':fragment.replace('((u8 *)record)[0xC], ((u8 *)record)[1]','((u8 *)record)[1], ((u8 *)record)[0xC]'),
        'range-reload':fragment.replace('    f32 rangeScale, rangeBase;\n','').replace('            rangeBase = D_800A23F4;\n','').replace('            rangeScale = D_800A23F8;\n','').replace('rangeScale','D_800A23F8').replace('rangeBase','D_800A23F4')}
    assert all(v!=fragment for v in controls.values());results=[]
    for label,body,opt in[('valid',fragment,opt)for opt in('-O0','-O2','-O3')]+[(name,body,'-O2')for name,body in controls.items()]:
        body=body.replace('void func_151058B4(','void func_151058B4_impl(',1)
        path=out/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(template.replace('@FRAGMENT@',body))
        result=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
        assert not result.returncode and not result.stdout and not result.stderr,(label,result.stdout,result.stderr)
        result=subprocess.run([str(exe)],capture_output=True,timeout=30);assert(result.returncode==0)==(label=='valid'),(label,opt,result.returncode)
        results.append(dict(label=label,profile=opt,exit_code=result.returncode))
    report=dict(cases_each_positive_profile=len(corpus),actual_C_wrapper_cases_each_profile=parent_count,actual_SDK32=True,strict_aliasing=True,UBSan=True,
        controls=len(controls),checks=results,defined_header_bytes=22,defined_packet_bytes=55,uninitialized_padding_not_compared=True,matching_credit=0)
    (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');return report
