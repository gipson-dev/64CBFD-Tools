"""Actual SDK32 source with an independent Python reference and live helper mutations."""
from pathlib import Path
import json,struct,subprocess
from tools.experiments import game_map_edge_emitter_151050b0_recovery as source
from tools.tests import game_map_edge_emitter_151050b0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def native_checks(out):
    root=source.ROOT;encoded=[];count=parent_count=0
    def append(values):encoded.extend(int(v)&0xffffffff for v in values)
    corpus=[c for c in g.cases()if not c.nan and c.accumulator!=0x7fc12345 and c.fcsr==0];append([len(corpus)])
    for i,c in enumerate(corpus):
        initial=g.fixture(c);final,calls,packets=g.reference(initial,c);parent=i%2;parent_count+=parent
        append([c.seed,c.blocked,c.mutation,parent]);append([initial[g.RECORD+j]for j in range(152)]);append([initial[g.SOURCE+j]for j in range(24)]);append([initial[g.ALT+j]for j in range(24)])
        append([g.read(initial,a)for a in(g.TICKS,g.TIME,g.RATE,g.RANGE,g.WIDTH,g.MARK)])
        if parent:calls=[(g.ENTRY,(g.RECORD,)),*calls]
        append([len(calls)]);iterator=iter(packets)
        for target,args in calls:
            flat=[]
            for a in args:flat.extend(a if isinstance(a,tuple)else(a,))
            append([target,len(flat),*flat]);data=next(iterator)if target==g.SPAWN else();append([len(data),*data])
        append([final[g.RECORD+j]for j in range(152)]);append([final[g.SOURCE+j]for j in range(24)]);append([final[g.ALT+j]for j in range(24)]);append([g.read(final,a)for a in(g.TICKS,g.TIME,g.RATE,g.RANGE,g.WIDTH,g.MARK)]);count+=1
    rom=(root/'conker/conker.us.bin').read_bytes();rng=list(struct.unpack_from('>25I',rom,0xDAF18));assert rng[17:]==[0x3042FFFF,0x44821000,0x3C01800A,0xC424F740,0x46801020,0x46040002,0x03E00008,0]
    assert struct.unpack_from('>I',rom,0x244200)[0]==0x37800080
    for i in range(65536):append([g.fp(g.bits(float(i)),0x37800080,'mul')])
    binary=out/'native-expected.bin';binary.write_bytes(struct.pack('>%dI'%len(encoded),*encoded));fragment=source.FRAGMENT
    parent=(root/'conker/src/game/done/game_1765E0.c').read_text().split('void func_15149264(',1)[1].split('\nvoid func_15149318',1)[0];parent='void func_15149264('+parent
    # A Linux ELF entry has no caller return-address word. Align the freestanding
    # C entry explicitly before GCC emits ABI-aligned vector stores in callees.
    entry=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    template=Path(__file__).with_name('game_map_edge_emitter_151050b0_native.c.in').read_text().replace('@BINARY@',binary.relative_to(root).as_posix()).replace('@PARENT@',parent).replace('@START@',entry)
    controls={
        'initial-timer':fragment.replace('if (emitter->timer < 0)','if (emitter->timer >= 0)',1),
        'source-state':fragment.replace('emitter->source->state = 1','emitter->source->state = 2'),
        'dispatch':fragment.replace('func_151494E0(0, 0x39)','func_151494E0(0, 0x38)'),
        'strict-threshold':fragment.replace('emitter->accumulator > 1.0f','emitter->accumulator >= 1.0f'),
        'first-index-scale':fragment.replace('func_150ADA68() * 3.0f','func_150ADA68() * 2.0f'),
        'opposite-index-wrap':fragment.replace('secondIndex -= 4','secondIndex -= 3'),
        'width-reload':fragment.replace('3, &packet, width, 2','3, &packet, D_800A23BC, 2').replace('    f32 width;\n','').replace('                width = D_800A23BC;\n',''),
        'channel-order':fragment.replace('((u8 *)record)[0xC], ((u8 *)record)[1]','((u8 *)record)[1], ((u8 *)record)[0xC]')}
    assert all(v!=fragment for v in controls.values());results=[]
    for label,body,opt in[('valid',fragment,o)for o in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
        path=out/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(template.replace('@FRAGMENT@',body))
        v=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not v.returncode and not v.stdout and not v.stderr,(label,opt,v.stdout,v.stderr)
        v=subprocess.run([str(exe)],capture_output=True,timeout=30);assert(v.returncode==0)==(label=='valid'),(label,opt,v.returncode);results.append(dict(label=label,profile=opt,exit_code=v.returncode))
    report=dict(cases_each_positive_profile=count,actual_parent_cases_each_profile=parent_count,actual_SDK32=True,strict_aliasing=True,UBSan=True,controls=len(controls),checks=results,finite_native_domain=True,nonfinite_guest_models_separate=True,defined_packet_bytes=43,uninitialized_packet_padding_not_compared=True,
        original_RNG_mask_and_suffix_pinned=True,exhaustive_16bit_random_domain_each_profile=65536,all_first_and_second_indices_valid_and_distinct=True,full_64bit_generator_execution_not_claimed=True)
    (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');return report
