"""Observe the qualified spline payload's owned, fingerprint-locked compiler frame."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from tools.experiments import game_route_spline_payload_recovery as source
from tools.experiments import game_actor_callback_frame_trace as frame
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-route-spline-payload-frame'
PREFIX='''#include <ultra64.h>
extern s16 D_80087290;
extern u8 *D_800D2350;
u8 func_1508907C(u8, u8, u8, u8);
s32 func_15086CBC(s32, f32 *, f32 *, f32 *);
'''


def qualify(root,out):
    source.freeze(root,out)
    body=PREFIX+source.front_floats(source.SELECTED)
    obj,diag=source.prior.prior.compile_profile(root,out,body,'isolated-front')
    if diag:raise ValueError('Isolated spline diagnostic compile: '+diag)
    source.checked(obj,True)
    row=dict(qualified_source_SHA256=hashlib.sha256(body.encode()).hexdigest(),
        words=302,frame=288,complete_raw_and_bindings_equal=True,installed=False)
    (out/'isolated.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,row


def trace(root,out):
    root,out=root.resolve(),out.resolve()
    if not out.is_relative_to(root/'conker/build'):raise ValueError('Compiler diagnostic must remain inside build')
    if frame.fingerprints(root)!=frame.COMPILERS:raise ValueError('Prepared compiler fingerprints changed')
    debugger=shutil.which('gdb')
    if debugger is None:raise FileNotFoundError('Existing GDB required; no installation')
    baseline,qualified=qualify(root,out);work=out/'trace-front';work.mkdir(exist_ok=True)
    script=work/'ugen-frame.gdb';script.write_text(frame.debugger_script(root,work))
    argv=json.loads((out/'isolated-front-command.json').read_text())
    output=work/'trace.o';argv[argv.index('-o')+1]=output.relative_to(root/'conker').as_posix()
    command=[debugger,'--nx','--batch','--iex','set auto-load off','-x',str(script),'--args',*argv]
    (work/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    result=subprocess.run(command,cwd=root/'conker',capture_output=True,text=True)
    log=result.stdout+result.stderr;(work/'debugger.txt').write_text(log)
    receipt=dict(exit_code=result.returncode,complete=False,installable=False,qualified=qualified)
    (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if result.returncode or 'TRACE_EXIT inferior=1 code=0' not in log.splitlines():
        raise ValueError('Owned frame trace did not finish; inspect the same handle/log before any retry')
    if frame.fingerprints(root)!=frame.COMPILERS or parse_object(baseline)!=parse_object(output) or \
            normalized_pools(baseline)!=normalized_pools(output):
        raise ValueError('Frame observation changed compiler/code/definitions/bindings/pools')
    observations=frame.validate_observations(work,log)
    (work/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    source.freeze(root,out)
    events=observations['events']
    receipt.update(complete=True,code_unchanged=True,compiler_SHA256=frame.fingerprints(root),
        events=len(events),input_stages=[row['stage'] for row in observations['inputs']],
        frames=sorted({e['frame'] for e in events}),last_event=events[-1])
    (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trace',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    print(json.dumps(trace(root,out) if args.trace else qualify(root,out)[1],indent=2))
