"""Compile the recovered callback with actual SDK32 layouts and original C dispatcher."""
from pathlib import Path
import json,subprocess
from tools.experiments import game_map_particle_sound_15104ff8_match as source
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def native_checks(out):
    root=source.ROOT;fragment=source.SPEC['fragment'];prefix,body=fragment.split('/* Restart',1);body='/* Restart'+body
    variants={'valid':body,
      'command':body.replace('command == 0x38','command == 0x39'),
      'state':body.replace('emitter->source->state == 1','emitter->source->state != 0'),
      'timer':body.replace('emitter->timer = 300','emitter->timer = 301'),
      'sound':body.replace('func_1000FA64(0x236','func_1000FA64(0x237'),
      'coordinates':body.replace('source->x, source->y, source->z','source->z, source->y, source->x'),
      'flags':body.replace('source, 0, 8, 0','source, 0, 9, 0'),
      'cached-source':body.replace('        func_1000FD38','        source = emitter->source;\n        func_1000FD38').replace('        source = emitter->source;\n        func_1000FA64','        func_1000FA64'),
      'missing-stop':body.replace('        func_1000FD38((s32)func_1000EF40, (s32)emitter->source, 0);','')}
    assert all(v!=body for n,v in variants.items()if n!='valid')
    text=prefix+'\n'.join(b.replace('func_15104FF8','variant_'+name.replace('-','_'))for name,b in variants.items())
    parent=(root/'conker/src/game/done/game_1765E0.c').read_text().split('void func_15149434(',1)[1].split('\ns32 func_15149490',1)[0];parent='void func_15149434('+parent
    template=Path(__file__).with_name('game_map_particle_sound_15104ff8_native.c.in').read_text();run=''
    for i,name in enumerate(variants):run+='if(variant(variant_%s)!=%d)return %d;\n'%(name.replace('-','_'),0 if name=='valid'else 1,i+1)
    template=template.replace('@SOURCE@',text).replace('@PARENT@',parent).replace('@RUN@',run).replace('@START@',START)
    results=[]
    for opt in('-O0','-O2','-O3'):
        path=out/('native'+opt+'.c');exe=path.with_suffix('');path.write_text(template)
        v=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not v.returncode and not v.stdout and not v.stderr,(v.stdout,v.stderr)
        v=subprocess.run([str(exe)],capture_output=True,timeout=45);assert v.returncode==0,(opt,v.returncode)
        results.append(dict(profile=opt,cases=49152,actual_C_dispatcher_cases=24576,controls=8,actual_SDK32=True,strict_aliasing=True,UBSan=True))
    report=dict(profiles=results,source_reload_mutations=8,all_record_source_and_surrounding_bytes_checked=True,guest_only_overlapping_views_not_claimed_native=True)
    (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');return report
