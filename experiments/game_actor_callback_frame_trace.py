"""Observe UGEN frame temporaries in a fingerprint-locked owned compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from tools.experiments import game_actor_callback_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments.game_text_measurer_frontend_trace import CFE_SHA256, decode_ucode

COMPILERS = {'cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'cfe':CFE_SHA256,
    'uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d'}


def fingerprints(root):
    return {n:hashlib.sha256((root/'ido/ido5.3_recomp'/n).read_bytes()).hexdigest() for n in COMPILERS}


def candidates():
    yield 'selected',screen.SELECTED
    direct=screen.RETAIL_CASES.replace('switch (actor[4])','switch ((s32)actor[4])')
    yield 'signed-byte-switch',direct
    for name,body in (('inline-address-switch',direct),('inline-address-named-switch',screen.SELECTED)):
        body=body.replace('    u8 *actor = D_800CC2D0 + (u32)index * 0x32C;\n','')
        body=body.replace('actor','(D_800CC2D0 + (u32)index * 0x32C)')
        yield name,body


MATCHED=dict(candidates())['inline-address-switch']


def debugger_script(root,work):
    ugen=json.dumps(str((root/'ido/ido5.3_recomp/ugen').resolve()))
    compiler_dir=json.dumps(str((root/'ido/ido5.3_recomp').resolve()))
    output=json.dumps(str(work))
    return '''set pagination off
set confirm off
set startup-with-shell off
set auto-load off
set print thread-events off
set follow-fork-mode child
set detach-on-fork off
set schedule-multiple on
handle SIGCHLD nostop noprint pass
python
import json,struct,hashlib
from pathlib import Path
compiler_dir=Path('''+compiler_dir+''')
output=Path('''+output+''')
def capture():
    stage=Path(gdb.current_progspace().filename).name
    if stage not in ('uopt','ugen') or Path(gdb.current_progspace().filename).parent!=compiler_dir:
        return
    inferior=gdb.selected_inferior()
    arguments=[a.decode() for a in Path('/proc/%d/cmdline' % inferior.pid).read_bytes().rstrip(b'\\0').split(b'\\0')]
    prefix='/tmp/ctmf' if stage=='uopt' else '/tmp/ctmo'
    paths=[Path(a) for a in arguments if a.startswith(prefix)]
    if len(paths)!=1 or not paths[0].is_file() or paths[0].is_symlink():
        raise gdb.GdbError('No unique owned compiler input')
    data=paths[0].read_bytes()
    name='frontend' if stage=='uopt' else 'optimizer'
    (output/(name+'.ucode')).write_bytes(data)
    gdb.write('FRAME_INPUT '+json.dumps(dict(stage=stage,inferior=inferior.num,
        path=str(paths[0]),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))+'\\n')
def ended(event):
    gdb.write('TRACE_EXIT inferior=%d code=%s\\n' % (event.inferior.num,getattr(event,'exit_code','unknown')))
gdb.events.exited.connect(ended)
def u32(mem,offset):
    return struct.unpack('<I',gdb.selected_inferior().read_memory(mem+offset,4))[0]
def pool(mem):
    result=[]
    pointer=u32(mem,0x1001A440)
    seen=set()
    while pointer:
        if pointer in seen or len(result)>=16:
            raise gdb.GdbError('Unbounded/cyclic UGEN temporary list')
        seen.add(pointer)
        result.append(dict(pointer=pointer,size=u32(mem,pointer+8),offset=u32(mem,pointer+12)))
        pointer=u32(mem,pointer+16)
    return result
def record(name,mem,argument=None):
    gdb.write('FRAME_TRACE '+json.dumps(dict(event=name,argument=argument,
        frame=u32(mem,0x10019388),temp_base=u32(mem,0x1001A444),pool=pool(mem),
        locals=u32(mem,0x10019BA0),saved=u32(mem,0x10019D54),
        outgoing=u32(mem,0x10019D4C),temporary=u32(mem,0x10019BA4),
        host_pc=int(gdb.parse_and_eval('$pc'))),sort_keys=True)+'\\n')
class FrameChanged(gdb.Breakpoint):
    def __init__(self,mem):
        self.mem=mem
        super().__init__('*(unsigned int*)%d' % (mem+0x10019388),
                         type=gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
    def stop(self):
        record('frame-write',self.mem)
        return False
class Begin(gdb.Breakpoint):
    def stop(self):
        mem=int(gdb.parse_and_eval('$rdi'))
        byte=lambda address:bytes(gdb.selected_inferior().read_memory(mem+(address^3),1))[0]
        table=[dict(opcode=i,name=bytes(byte(0x10005B40+i*4+j) for j in range(4)).decode('ascii').strip(),
                    descriptor=[byte(0x1001A6C0+i*19+j) for j in range(19)]) for i in range(154)]
        types=dict(dtypes=bytes(byte(0x10005DB0+i) for i in range(20)).decode('ascii'),
                   mtypes=bytes(byte(0x10005DC4+i) for i in range(8)).decode('ascii'))
        (output/'ucode-table.json').write_text(json.dumps(table))
        (output/'ucode-types.json').write_text(json.dumps(types))
        record('frame-watch-installed',mem)
        FrameChanged(mem)
        self.enabled=False
        return False
class Returned(gdb.FinishBreakpoint):
    def __init__(self,name,mem):
        self.name,self.mem=name,mem
        super().__init__(gdb.newest_frame(),internal=True)
    def stop(self):
        record(self.name+'-return',self.mem)
        return False
class Observe(gdb.Breakpoint):
    def stop(self):
        mem=int(gdb.parse_and_eval('$rdi'))
        argument=int(gdb.parse_and_eval('$edx'))
        record(self.location,mem,argument)
        if self.location=='f_temp_offset':
            Returned(self.location,mem)
        return False
end
catch exec
commands
silent
python
capture()
if gdb.current_progspace().filename == '''+ugen+''':
    Begin('f_readuinstr.constprop.0')
    for name in ('f_spill_to_temp','f_temp_offset','f_free_temp'):
        Observe(name)
    gdb.execute('set follow-fork-mode parent')
end
continue
end
run
inferior 1
continue
python
for breakpoint in gdb.breakpoints() or ():
    if breakpoint.location in ('f_spill_to_temp','f_temp_offset','f_free_temp'):
        breakpoint.delete()
for attempt in range(6):
    if not any(i.num==1 and i.pid for i in gdb.inferiors()):
        break
    if gdb.selected_inferior().pid:
        raise gdb.GdbError('Unexpected live child: no automatic compiler restart')
    gdb.execute('inferior 1')
    gdb.execute('continue')
else:
    raise gdb.GdbError('Driver did not terminate')
end
info inferiors
'''


def trace(root,out,name,body=screen.SELECTED):
    root,out=Path(root).resolve(),Path(out).resolve()
    work=(out/name).resolve()
    if not work.is_relative_to(root/'conker/build') or Path(name).name!=name:
        raise ValueError('Owned diagnostic output must be inside conker/build')
    if fingerprints(root)!=COMPILERS:
        raise ValueError('Prepared compiler fingerprints changed')
    debugger=shutil.which('gdb')
    if not debugger:
        raise FileNotFoundError('Existing GDB required; no install')
    work.mkdir(parents=True,exist_ok=True)
    meta,_=screen.compile_candidate(root,work,'baseline',body)
    script=work/'ugen-frame.gdb'
    script.write_text(debugger_script(root,work))
    relative=lambda p:os.path.relpath(root/p,work)
    command=[debugger,'--nx','--batch','--iex','set auto-load off','-x',str(script),'--args',
        relative('ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm',
        '-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-mips2','-o32']
    for include in ('conker/include','conker/include/2.0L','conker/include/2.0L/PR','conker/include/libc'):
        command.extend(('-I',relative(include)))
    command.extend(('-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-O2','-g3',
        '-o','trace.o','baseline.c'))
    result=subprocess.run(command,cwd=work,capture_output=True,text=True)
    log=result.stdout+result.stderr
    (work/'debugger.txt').write_text(log)
    record=dict(exit_code=result.returncode,baseline=meta,compiler_sha256=fingerprints(root),
                code_unchanged=False,installable=False)
    (work/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    if result.returncode or 'TRACE_EXIT inferior=1 code=0' not in log.splitlines():
        raise ValueError('Owned compiler trace did not terminate successfully; inspect its handle/log')
    if fingerprints(root)!=COMPILERS or parse_object(work/'baseline.o')!=parse_object(work/'trace.o'):
        raise ValueError('Diagnostic changed compiler/object')
    a,b=sections(work/'baseline.o'),sections(work/'trace.o')
    for key in a.keys()|b.keys():
        if key.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and a.get(key)!=b.get(key):
            raise ValueError('Diagnostic changed pool')
    record.update(validate_observations(work,log))
    record.update(code_unchanged=True)
    (work/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def validate_observations(work,log):
    lines=log.splitlines()
    events=[json.loads(line.removeprefix('FRAME_TRACE ')) for line in lines if line.startswith('FRAME_TRACE ')]
    if (len([e for e in events if e.get('event')=='frame-watch-installed'])!=1
            or not any(e.get('event')=='frame-write' for e in events)):
        raise ValueError('No UGEN frame observation gate fired')
    fields={'event','argument','frame','temp_base','pool','locals','saved','outgoing','temporary','host_pc'}
    for event in events:
        if (set(event)!=fields or any(type(event[k]) is not int or not 0<=event[k]<=0xFFFFFFFF
                for k in fields-{'event','argument','pool'}) or not isinstance(event['pool'],list)):
            raise ValueError('Malformed frame observation')
    inputs=[json.loads(line.removeprefix('FRAME_INPUT ')) for line in lines if line.startswith('FRAME_INPUT ')]
    if [entry.get('stage') for entry in inputs]!=['uopt','ugen']:
        raise ValueError('Incomplete compiler inputs')
    table=json.loads((work/'ucode-table.json').read_text())
    types=json.loads((work/'ucode-types.json').read_text())
    decoded={}
    for name,entry in zip(('frontend','optimizer'),inputs):
        data=(work/(name+'.ucode')).read_bytes()
        marker='TRACE_EXIT inferior=%d code=0' % entry['inferior']
        capture_line=next(line for line in lines if line.startswith('FRAME_INPUT ') and json.loads(line[12:])==entry)
        if (marker not in lines or lines.index(marker)<=lines.index(capture_line)
                or len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']):
            raise ValueError('Compiler input integrity/completion mismatch')
        decoded[name]=decode_ucode(data,table,types)
    return dict(events=events,inputs=inputs,records=decoded)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',default='selected')
    parser.add_argument('--screens',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.screens:
        out=root/'conker/build/game-actor-callback-frame-screens'
        out.mkdir(exist_ok=True)
        for name,body in candidates():
            meta,_=screen.compile_candidate(root,out,name,body)
            print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
        return
    record=trace(root,root/'conker/build/game-actor-callback-frame-trace',args.name)
    print(json.dumps(dict(baseline=record['baseline'],events=record['events'],
        inputs=record['inputs'],record_counts={k:len(v) for k,v in record['records'].items()},
        code_unchanged=record['code_unchanged'],installable=record['installable']),indent=2))


if __name__=='__main__':
    main()
