from pathlib import Path
import json,struct,subprocess
from tools.tests import game_map_particle_emitter_15104c44_oracle as g
from tools.experiments import game_map_particle_emitter_15104c44_recovery as source
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=source.ROOT
def flatten(args):
    result=[]
    for a in args:result.extend(a if isinstance(a,tuple)else(a,))
    return result
def native_checks(p):
    encoded=[];count=0;parent_cases=0;nan_categories=0
    def append(values):encoded.extend(int(v)&0xffffffff for v in values)
    cases=list(g.cases());append([len(cases)])
    for i,c in enumerate(cases):
        initial=g.fixture(c);final,calls,packets=g.reference(initial,c);parent=i%2
        parent_cases+=parent;nan_categories+=int(c.timer>=0 and not c.blocked and g.floating(g.read(final,g.TAIL+4))!=g.floating(g.read(final,g.TAIL+4)))
        append([c.seed,c.hits,c.mutation,parent,int(c.timer>=0 and not c.blocked)])
        append([initial[g.RECORD+j]for j in range(144)]);append([c.blocked,*[g.read(initial,a)for a in(g.TICKS,g.TIME,g.RATE,g.RANGE,g.MARK)]])
        if parent:calls=[(g.ENTRY,(g.RECORD,)),*calls]
        append([len(calls)]);payloads=iter(packets)
        for target,args in calls:
            arguments=flatten(args);append([target,len(arguments),*arguments])
            if target==g.SPAWN:data=next(payloads);append([len(data),*data])
            else:append([0])
        append([final[g.RECORD+j]for j in range(144)]);append([g.read(final,a)for a in(g.TICKS,g.TIME,g.RATE,g.RANGE,g.MARK)])
        count+=1
    binary=p/'native-expected.bin';binary.write_bytes(struct.pack('>%dI'%len(encoded),*encoded))
    fragment=source.FRAGMENT;gate=(r/'conker/src/game_16EE20.c').read_text().split('u8 func_151464B8(',1)[1].split('\nvoid func_15146508',1)[0]
    gate='u8 actual_gate('+gate
    parent=(r/'conker/src/game/done/game_1765E0.c').read_text().split('void func_15149264(',1)[1].split('\nvoid func_15149318',1)[0]
    parent='void func_15149264('+parent
    template=Path(__file__).with_name('game_map_particle_emitter_15104c44_native.c.in').read_text();common=template.replace('@BINARY@',binary.relative_to(r).as_posix()).replace('@GATE@',gate).replace('@PARENT@',parent).replace('@START@',START)
    controls={
      'initial-timer-gate':('if (emitter->timer < 0) {\n        return;','if (emitter->timer >= 0) {\n        return;',1),
      'gate-result':('if (func_151464B8(emitter->gate) != 0)','if (func_151464B8(emitter->gate) == 0)',1),
      'strict-spawn-threshold':('emitter->accumulator > 1.0f','emitter->accumulator >= 1.0f',2),
      'start-height':('emitter->height - 180.0f','emitter->height + 180.0f',1),
      'surface-hit':('if (func_15046C80(&sample, 0, emitter->position.y, &emitter->surface) != 0)','if (func_15046C80(&sample, 0, emitter->position.y, &emitter->surface) == 0)',1),
      'unsigned-random-modulo':('(u32)func_150ADA20()','func_150ADA20()',3),
      'counter-decrement':('emitter->accumulator -= 1.0f','emitter->accumulator -= 0.5f',1),
      'end-height':('packet.sample.y + 180.0f','packet.sample.y - 180.0f',1),
      'channel-context-order':('((u8 *)record)[0xC], ((u8 *)record)[1]','((u8 *)record)[1], ((u8 *)record)[0xC]',1)}
    results=[]
    for opt in('-O0','-O2','-O3'):
        for name,body in[('valid',fragment),*[(n,fragment.replace(a,b))for n,(a,b,_)in controls.items()]]:
            if name!='valid':a,b,occurs=controls[name];assert fragment.count(a)==occurs and body!=fragment
            path=p/('native'+opt+'-'+name+'.c');exe=path.with_suffix('');path.write_text(common.replace('@FRAGMENT@',body))
            result=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=r,capture_output=True,text=True)
            assert not result.returncode and not result.stdout and not result.stderr,(name,opt,result.stdout,result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=15)
            assert result.returncode==(0 if name=='valid'else 1),(name,opt,result.returncode)
        results.append(dict(profile=opt,cases=count,actual_SDK32=True,actual_parent_cases=parent_cases,controls=9,strict_aliasing=True,UBSan=True,nonfinite_accumulator_category_cases=nan_categories))
    report=dict(profiles=results,finite_results_and_defined_packet_bytes_exact=True,nonfinite_result_NaN_payload_not_portable=True,hardware_FCSR_not_claimed=True)
    (p/'native.json').write_text(json.dumps(report,indent=2)+'\n');return report
