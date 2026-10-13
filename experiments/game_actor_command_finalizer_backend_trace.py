"""Observe load nodes and raw immediate/memory emission in owned UGEN children."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_schedule as schedule
from tools.experiments import game_text_measurer_ugen_nodes as nodes

PROBES={'immediate':0x431550,'memory':0x435AB0}
PREFIX='FINALIZER_EMIT '
NODE_SCRIPT=nodes.debugger_script


def debugger_script(root,work):
    script=NODE_SCRIPT(root)
    declaration='''from pathlib import Path
import hashlib
as1 = %s
output = Path(%s)
def capture_as1():
    if gdb.current_progspace().filename != as1:
        return
    inferior = gdb.selected_inferior()
    arguments = [a.decode() for a in Path('/proc/%%d/cmdline' %% inferior.pid).read_bytes().rstrip(b'\\0').split(b'\\0')]
    files = []
    for ordinal, argument in enumerate(arguments):
        path = Path(argument)
        if not argument.startswith('/tmp/ctm') or not path.is_file():
            continue
        if path.is_symlink() or not 0 < path.stat().st_size <= 1048576:
            raise gdb.GdbError('Unexpected AS1 input file')
        data = path.read_bytes()
        name = 'as1-input-%%d.bin' %% ordinal
        destination = output / name
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            raise gdb.GdbError('AS1 capture destination is not an owned regular file')
        destination.write_bytes(data)
        files.append(dict(ordinal=ordinal,path=str(path),saved=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    if not files:
        raise gdb.GdbError('No actual AS1 input captured')
    gdb.write('FINALIZER_AS1 ' + json.dumps(dict(inferior=inferior.num,arguments=arguments,files=files)) + '\\n')
class EmitObserver(gdb.Breakpoint):
    def __init__(self, name, address):
        self.name = name
        super().__init__('*0x%%x' %% address, internal=True)
    def stop(self):
        if gdb.current_progspace().filename != program:
            raise gdb.GdbError('Emitter probe fired in a different compiler child')
        raw = {name:int(gdb.parse_and_eval('$' + name)) & 0xffffffff
               for name in ('rsi', 'rdx', 'rcx', 'r8', 'r9')}
        sp = int(gdb.parse_and_eval('$rsp'))
        caller = int.from_bytes(gdb.selected_inferior().read_memory(sp, 8).tobytes(), 'little')
        gdb.write('FINALIZER_EMIT ' + json.dumps(dict(probe=self.name, caller=caller, raw=raw)) + '\\n')
        return False
'''%(json.dumps(str((Path(root)/'ido/ido5.3_recomp/as1').resolve())),json.dumps(str(Path(work).resolve())))
    marker='end\ncatch exec'
    assert script.count(marker)==1
    script=script.replace(marker,declaration+marker,1)
    anchor='python\nif gdb.current_progspace().filename == program:'
    assert script.count(anchor)==1
    script=script.replace(anchor,'python\ncapture_as1()\nif gdb.current_progspace().filename == program:',1)
    anchor="    LoadNode('*0x430480', internal=True)"
    setup=anchor+''.join("\n    EmitObserver(%r, 0x%x)\n    gdb.write('FINALIZER_EMIT_INSTALLED %s\\n')"%
        (name,address,name) for name,address in PROBES.items())
    assert script.count(anchor)==1
    script=script.replace(anchor,setup,1)
    anchor="        if breakpoint.location == '*0x430480':"
    locations=tuple('*0x%x'%address for address in PROBES.values())
    replacement='''        if breakpoint.location in %r:
            name = breakpoint.name
            breakpoint.delete()
            gdb.write('FINALIZER_EMIT_REMOVED ' + name + '\\n')
        elif breakpoint.location == '*0x430480':'''%(locations,)
    assert script.count(anchor)==1
    return script.replace(anchor,replacement,1)


def emitter_events(log):
    records=[]
    for line in log.splitlines():
        if not line.startswith(PREFIX):continue
        event=json.loads(line.removeprefix(PREFIX))
        if (set(event)!={'probe','caller','raw'} or event['probe'] not in PROBES
                or type(event['caller']) is not int or not 0x400000<=event['caller']<0x500000
                or set(event['raw'])!={'rsi','rdx','rcx','r8','r9'}
                or any(type(v) is not int or not 0<=v<=0xFFFFFFFF for v in event['raw'].values())):
            raise ValueError('Malformed or unexpected raw emitter event')
        records.append(event)
    lines=log.splitlines()
    for name in PROBES:
        installed='FINALIZER_EMIT_INSTALLED '+name
        removed='FINALIZER_EMIT_REMOVED '+name
        positions=[i for i,line in enumerate(lines) if line.startswith(PREFIX)
            and json.loads(line.removeprefix(PREFIX))['probe']==name]
        if (lines.count(installed)!=1 or lines.count(removed)!=1 or not positions
                or not lines.index(installed)<min(positions)<=max(positions)<lines.index(nodes.CHILD_EXIT)
                or not lines.index(nodes.CHILD_EXIT)<lines.index(removed)<lines.index(nodes.qualified.EXIT_MARKER)):
            raise ValueError('Emitter probe did not fire or escaped its owned lifetime')
    return records


def validate_as1(work,log):
    lines=log.splitlines()
    positions=[i for i,line in enumerate(lines) if line.startswith('FINALIZER_AS1 ')]
    if len(positions)!=1:
        raise ValueError('No unique AS1 capture')
    at=positions[0]
    record=json.loads(lines[at].removeprefix('FINALIZER_AS1 '))
    if (not isinstance(record,dict) or set(record)!={'inferior','arguments','files'}
            or type(record['inferior']) is not int or record['inferior']!=5
            or not lines.index(nodes.CHILD_EXIT)<at<lines.index('TRACE_EXIT inferior=5 code=0')
            or not at<lines.index(nodes.qualified.EXIT_MARKER)
            or any(lines.index('FINALIZER_EMIT_REMOVED '+name)>=at for name in PROBES)
            or not isinstance(record['arguments'],list) or len(record['arguments'])!=16
            or not all(isinstance(a,str) for a in record['arguments'])
            or record['arguments'][:11]!=['as1','-elf','-G','0','-p0','-r4300_mul',
                '-r4300_mul','-mips2','-EB','-g3','-O2']
            or record['arguments'][12:15]!=['-o','trace.o','-t']
            or not isinstance(record['files'],list) or len(record['files'])!=2):
        raise ValueError('AS1 capture has invalid producer/consumer lifetime or profile')
    for item in record['files']:
        if (not isinstance(item,dict) or set(item)!={'ordinal','path','saved','bytes','sha256'}
                or type(item['ordinal']) is not int or item['ordinal'] not in (11,15)
                or not isinstance(item['path'],str) or not isinstance(item['sha256'],str)
                or item['saved']!='as1-input-%d.bin'%item['ordinal']
                or record['arguments'][item['ordinal']]!=item['path']
                or not item['path'].startswith('/tmp/ctm')
                or type(item['bytes']) is not int or not 0<item['bytes']<=1048576):
            raise ValueError('AS1 input provenance is invalid')
        path=Path(work)/item['saved']
        if path.is_symlink() or not path.is_file():
            raise ValueError('AS1 input is not an owned regular file')
        data=path.read_bytes()
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise ValueError('AS1 input digest/length changed')
    if {item['ordinal'] for item in record['files']}!={11,15}:
        raise ValueError('AS1 inputs are missing or duplicated')
    return record


def instruction_records(data):
    if not data or len(data)%16:
        raise ValueError('Incomplete binary-assembly record')
    records=[]
    for index,words in enumerate(struct.iter_unpack('>4I',data)):
        kind=words[1]>>16&63
        if kind!=23:continue
        records.append(dict(record=index,raw=list(words),opcode=(words[1]&65535)>>1,
            register0=words[2]>>25&127,register1=words[2]>>18&127,word3=words[3]))
    return records


def correlate(records,events):
    expected=Counter((e['raw']['rdx'],e['raw']['rcx'],
        72 if e['probe']=='immediate' else e['raw']['r9'],e['raw']['r8']) for e in events)
    observed=Counter((r['opcode'],r['register0'],r['register1'],r['word3']) for r in records)
    if expected-observed:
        raise ValueError('Emitter arguments disagree with captured AS1 instruction records')
    lower=[r for r in records if (r['opcode'],r['register0'],r['register1'],r['word3'])==(41,7,72,40)]
    if len(lower)!=1:
        raise ValueError('No unique observed lower-bound immediate record')
    return dict(correlated_events=sum(expected.values()),lower_record=lower[0],
        raw_unobserved_opcode_meanings_not_assigned=True)


def screen_adapter():
    fitting=schedule.previous.previous.previous.flow.roles.fitting
    return SimpleNamespace(compile_candidate=fitting.compile_candidate,
        compiler=fitting.recovery.compiler,FUNCTION=fitting.recovery.FUNCTION,SELECTED=schedule.SELECTED,
        PROFILES={'owner':fitting.recovery.compiler.PROFILES['o2g3']})


def trace(root,out,name,body):
    adapter=screen_adapter()
    # Reuse the qualified transport and identity gates; observe additional native entries only.
    work=Path(out)/name
    with patch.object(nodes,'screen',adapter),patch.object(nodes,'debugger_script',
            lambda directory:debugger_script(directory,work)):
        record=nodes.trace_nodes(root,out,name,body)
    log=(work/'debugger.txt').read_text()
    events=emitter_events(log)
    as1=validate_as1(work,log)
    binary=instruction_records((work/'as1-input-11.bin').read_bytes())
    record.update(emitter_events=events,emitter_event_count=len(events),
        raw_arguments_not_decoded=True,as1_input=as1,correlation=correlate(binary,events),installable=False)
    (work/'finalizer-trace.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',choices=('current','early'),default='current')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    body=schedule.SELECTED if args.candidate=='current' else schedule.early_lower(schedule.SELECTED)
    record=trace(root,root/'conker/build/game-actor-command-finalizer-backend',args.candidate,body)
    print(json.dumps(dict(candidate=args.candidate,code_unchanged=record['code_unchanged'],
        baseline={k:record['baseline'][k] for k in ('body_words','frame','differences')},
        load_events=record['event_count'],as1_input=record['as1_input'],
        emitter_events=record['emitter_event_count'],correlation=record['correlation'],
        installable=False),indent=2))


if __name__=='__main__':
    main()
