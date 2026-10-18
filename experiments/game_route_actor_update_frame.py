"""Observe the complete route caller's owned, fingerprint-locked IDO frame."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from tools.experiments import game_route_actor_update as source
from tools.experiments import game_actor_callback_frame_trace as frame
from tools.experiments.game_actor_record_gate_compiler_trace import lifecycle
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-route-actor-update-frame'


def isolated_content(root, out):
    values = source.freeze(root, out)
    owner = values['conker/src/game/generated_B3020.c'].decode()
    first = source.function_span(owner, 'func_15085B70')[0]
    return owner[:first] + source.SELECTED


def qualify(root, out):
    content = isolated_content(root, out)
    obj, diagnostics = source.prior.compile_profile(root, out, content, 'isolated')
    raw, bindings = source.checked(obj)
    if diagnostics or set(parse_object(obj)[1]) != {source.FUNCTION}:
        raise ValueError('Changed isolated route-update scope or diagnostics')
    result = dict(words=len(raw) // 4, frame=480, bindings=len(bindings),
        raw_SHA256=source.RAW_SHA, source_SHA256=hashlib.sha256(content.encode()).hexdigest(),
        full_owner_target_bytes_and_bindings_equal=True, diagnostics=diagnostics, installed=False)
    (out / 'isolated.json').write_text(json.dumps(result, indent=2) + '\n')
    return obj, result


def capture(root, out):
    root, out = root.resolve(), out.resolve()
    if not out.is_relative_to(root / 'conker/build'):
        raise ValueError('Compiler diagnostics must remain inside the consumer build directory')
    if frame.fingerprints(root) != frame.COMPILERS:
        raise ValueError('Prepared compiler fingerprints changed')
    debugger = shutil.which('gdb')
    if debugger is None:
        raise FileNotFoundError('Existing GDB required; no installation')
    baseline, qualified = qualify(root, out)
    work = out / 'selected'
    if (work / 'debugger.txt').exists():
        raise ValueError('Capture already exists: audit the same completed/live evidence, do not restart')
    work.mkdir(exist_ok=True)
    script = work / 'ugen-frame.gdb'
    script.write_text(frame.debugger_script(root, work))
    argv = json.loads((out / 'isolated-command.json').read_text())
    output = work / 'trace.o'
    argv[argv.index('-o') + 1] = output.relative_to(root / 'conker').as_posix()
    command = [debugger, '--nx', '--batch', '--iex', 'set auto-load off', '-x', str(script), '--args', *argv]
    (work / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    log = result.stdout + result.stderr
    (work / 'debugger.txt').write_text(log)
    (work / 'launch.json').write_text(json.dumps(dict(exit_code=result.returncode,
        qualified=qualified, installed=False), indent=2) + '\n')
    if result.returncode:
        raise ValueError('Owned compiler capture failed: inspect its same log/handle before any retry')
    if parse_object(baseline) != parse_object(output) or normalized_pools(baseline) != normalized_pools(output):
        raise ValueError('Compiler observation changed code/definitions/bindings/pools')
    return audit(root, out)


def audit(root, out):
    work = out / 'selected'
    qualified = json.loads((out / 'isolated.json').read_text())
    content = isolated_content(root, out)
    if (out / 'isolated.c').read_text() != content or hashlib.sha256(content.encode()).hexdigest() != qualified['source_SHA256']:
        raise ValueError('Changed complete isolated route-update source')
    if frame.fingerprints(root) != frame.COMPILERS:
        raise ValueError('Changed prepared compiler fingerprints')
    log = (work / 'debugger.txt').read_text()
    launch = json.loads((work / 'launch.json').read_text())
    ended = lifecycle(root.resolve(), log)
    observations = frame.validate_observations(work, log)
    if launch['exit_code'] or launch['qualified'] != qualified:
        raise ValueError('Changed compiler launch/qualification receipt')
    if parse_object(out / 'isolated.o') != parse_object(work / 'trace.o') or \
            normalized_pools(out / 'isolated.o') != normalized_pools(work / 'trace.o'):
        raise ValueError('Changed normal/traced object or pools')
    source.checked(out / 'isolated.o')
    source.checked(work / 'trace.o')
    events = observations['events']
    facts = frame_facts(observations)
    result = dict(qualified=qualified, compiler_SHA256=frame.COMPILERS, lifecycle=ended,
        code_unchanged=True, installed=False, matching_credit=0,
        observations=observations, facts=facts, final_event=events[-1], frame_values=sorted({e['frame'] for e in events}))
    (work / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def frame_facts(observations):
    events = observations['events']
    expected = [('frame-watch-installed', 0, 0, 0, 0), ('frame-write', 48, 0, 48, 0),
                ('frame-write', 64, 0, 48, 16), ('frame-write', 480, 416, 48, 16)]
    if [(e['event'], e['frame'], e['locals'], e['saved'], e['outgoing']) for e in events] != expected:
        raise ValueError('Changed fired route-update frame decomposition')
    if any(e['temporary'] or e['temp_base'] or e['pool'] for e in events):
        raise ValueError('Changed observed UGEN temporary pool')
    records = observations['records']
    local_bytes = {}
    floors = {}
    for stage, n in (('frontend', 396), ('optimizer', 416)):
        rows = records[stage]
        if [r['block'] for r in rows if r['name'] == 'ent'] != [769]:
            raise ValueError('Changed isolated route-update procedure')
        definitions = [r for r in rows if r['name'] == 'def']
        if [(r['storage'], r['length']) for r in definitions] != [('M', n), ('P', 12)]:
            raise ValueError('Changed upstream route-update locals or argument span')
        local_bytes[stage] = n
        floors[stage] = min(r['offset'] for r in rows if r['storage'] == 'M' and r['offset'] is not None)
    if floors != dict(frontend=-396, optimizer=-404):
        raise ValueError('Changed upstream route-update private homes')
    homes = {(r['offset'], r['length']) for r in records['frontend'] if r['storage'] == 'M' and r['name'] == 'lda'}
    arrays = {(-56, 16), (-72, 16), (-88, 16), (-228, 132), (-260, 32), (-328, 68)}
    if not arrays <= homes:
        raise ValueError('Changed frontend route workspace extents')
    new_home = [r for r in records['optimizer'] if r['storage'] == 'M' and r['offset'] == -404]
    if sorted(r['name'] for r in new_home) != ['lod', 'lod', 'str', 'vreg', 'vreg', 'vreg'] or \
            any((r['dtype'], r['length'], r['block']) != ('J', 4, 769) for r in new_home):
        raise ValueError('Changed optimizer-created lower local home')
    return dict(procedure=769, frontend_local_bytes=396, optimized_local_bytes=416,
        saved_bytes=48, outgoing_bytes=16, frame_bytes=480, observed_UGEN_temporary_bytes=0,
        frontend_floor=-396, optimized_floor=-404, frontend_arrays=sorted(arrays),
        optimized_lower_home_dtype='J', optimized_lower_home_length=4,
        extra_local_bytes_exist_before_UGEN=True, original_retail_source_layout_not_observed=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    value = capture(root, out) if args.capture else audit(root, out) if args.audit else qualify(root, out)[1]
    print(json.dumps({k: v for k, v in value.items() if k != 'observations'}, indent=2))
