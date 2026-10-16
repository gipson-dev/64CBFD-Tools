"""Capture rectangle CFE/UOPT records and UGEN homes without changing code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_middle as source
from tools.experiments import game_actor_callback_frame_trace as frame
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

TABLES={'descriptors':'3f35ec97a5b8e73316a01473cdf7cee04bdbb4423ba9441fcee9339d78bcd715',
    'types':'f6b7523e54bd4b59cf759a9229552fedfb545920b1698b275fb426c312fb8aea'}
FRAME_SCRIPT=frame.debugger_script
ALLOCATION_SCRIPT=allocation.debugger_script
SIGNATURES={
    'ecb44344191b7e1034df986d516cad2e17810783fcddb537b0685a4e1b13288b':
        '6f15273cc09304bf1324a83acc427bd35436e66e7d8fe2ed8599a5f9db458c57',
    'd76a71559e7b4817334c60ad145706bcb12c2aaf497b5253de95b21859b13dfd':
        '6e8aa6920126987b5a85a24bf45c254714019fcf9b22be3a659f52112e53dcb3'}


def debugger_script(root,work):
    script=FRAME_SCRIPT(root,work)
    anchors=('def capture():','    name=\'frontend\' if stage==\'uopt\' else \'optimizer\'',
        'def ended(event):',"        record('frame-watch-installed',mem)")
    if any(script.count(a)!=1 for a in anchors):
        raise ValueError('Changed qualified frame script anchors')
    script=script.replace('def capture():',"flow_exits={}\noptimizer_output=None\n\ndef capture():\n    global optimizer_output",1)
    flow='''    producer='cfe' if stage=='uopt' else 'uopt'
    if flow_exits.get(producer)!=[0]:
        raise gdb.GdbError('Rectangle compiler producer incomplete')
    if stage=='uopt':
        optimizer_output=Path(arguments[arguments.index(str(paths[0]))+1])
        if not str(optimizer_output).startswith('/tmp/ctmo'):
            raise gdb.GdbError('Unexpected rectangle UOPT output')
    elif optimizer_output!=paths[0]:
        raise gdb.GdbError('Rectangle UGEN did not consume observed UOPT output')
    gdb.write('RECT_FLOW '+json.dumps(dict(stage=stage,inferior=inferior.num,input=str(paths[0]),
        output=str(optimizer_output),producer=producer,producer_exits=flow_exits[producer]))+'\\n')
'''
    script=script.replace(anchors[1],flow+anchors[1],1)
    script=script.replace('def ended(event):',
        "def ended(event):\n    name=Path(event.inferior.progspace.filename).name\n"
        "    code=getattr(event,'exit_code','unknown')\n"
        "    flow_exits.setdefault(name,[]).append(code)\n"
        "    gdb.write('RECT_EXIT '+json.dumps(dict(stage=name,inferior=event.inferior.num,code=code))+'\\n')",1)
    marker="        gdb.write('RECT_TABLES '+json.dumps(dict(descriptors=hashlib.sha256((output/'ucode-table.json').read_bytes()).hexdigest(), types=hashlib.sha256((output/'ucode-types.json').read_bytes()).hexdigest()))+'\\n')\n"
    return script.replace(anchors[3],marker+anchors[3],1)


def allocation_script(root):
    script=ALLOCATION_SCRIPT(root)
    script=script.replace('python\ndef trace_exit(event):','python\nimport json\ndef trace_exit(event):',1)
    first="    gdb.execute('set follow-fork-mode parent')"
    last='for attempt in range(6):'
    if script.count(first)!=1 or script.count(last)!=1:
        raise ValueError('Changed qualified allocation script anchors')
    script=script.replace(first,"    gdb.write('RECT_ALLOC_INSTALLED '+json.dumps(dict(inferior=gdb.selected_inferior().num,program=gdb.current_progspace().filename))+'\\n')\n"+first,1)
    return script.replace(last,"gdb.write('RECT_ALLOC_REMOVED\\n')\n"+last,1)


def signature(obj):
    text,funcs,rel=parse_object(obj)
    f=funcs[source.FUNCTION]
    return (text[f['value']:f['value']+f['size']],
        {a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        {n:d for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})


def checked_signature(obj):
    raw,rel,pools=signature(obj)
    key=hashlib.sha256(raw).hexdigest()
    if pools or SIGNATURES.get(key)!=hashlib.sha256(json.dumps(rel,sort_keys=True).encode()).hexdigest():
        raise ValueError('Unknown diagnostic object words, bindings or pools')
    return raw,rel,pools


def isolate(owner,names):
    # Broaden only the parser view, preserving all offsets and compiled spelling.
    view=re.sub(r'^(?:u32|u8|Gfx)\s*\*',lambda m:'s32'+' '*(len(m.group())-3),owner,flags=re.M)
    spans=sorted((source.build.function_span(view,n) for n in names if n!=source.FUNCTION),reverse=True)
    for lo,hi in spans:
        owner=owner[:lo]+owner[hi:]
    return owner


def prepared(root,out,label,body):
    root,out=Path(root).resolve(),Path(out).resolve()
    if not out.is_relative_to(root/'conker/build') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',label):
        raise ValueError('Owned compiler output/name must stay inside conker/build')
    source.freeze(root,out)
    full,_,meta=source.measure(root,out,'whole-'+label,body)
    names=parse_object(full)[1]
    isolated=isolate(source.recovered_owner((out/'before-packet_owner').read_text(),body),names)

    def compile_candidate(root,work,name,unused):
        obj,diagnostics=source.build.compile_owner(root,work,isolated,name)
        if diagnostics or set(parse_object(obj)[1])!={source.FUNCTION} or signature(obj)!=signature(full):
            raise ValueError('Isolated rectangle does not reproduce complete-owner output')
        return dict(words=meta['words'],frame=meta['frame'],differences=meta['differences'],
            raw_sha256=meta['raw_sha256'],source_sha256=hashlib.sha256(isolated.encode()).hexdigest(),
            isolated_matches_full_owner=True),obj

    adapter=SimpleNamespace(SELECTED=body,compile_candidate=compile_candidate,
        compiler=SimpleNamespace(parse_object=parse_object,sections=sections),PROFILES={'owner':('-O2','-g3')})
    return full,adapter


def validate(root,work):
    if frame.fingerprints(root)!=frame.COMPILERS:
        raise ValueError('Rectangle compiler fingerprints changed')
    log=(work/'debugger.txt').read_text()
    receipt=json.loads((work/'receipt.json').read_text())
    if (receipt.get('exit_code')!=0 or receipt.get('code_unchanged') is not True or
            receipt.get('installable') is not False or receipt.get('compiler_sha256')!=frame.COMPILERS):
        raise ValueError('Incomplete rectangle trace receipt')
    if hashlib.sha256((work/'baseline.c').read_bytes()).hexdigest()!=receipt.get('baseline',{}).get('source_sha256'):
        raise ValueError('Changed rectangle compiler source')
    lines=log.splitlines()
    if lines.count('TRACE_EXIT inferior=1 code=0')!=1 or 'Python Exception' in log or 'Error in sourced' in log:
        raise ValueError('Incomplete rectangle driver')
    tables=[json.loads(x.removeprefix('RECT_TABLES ')) for x in lines if x.startswith('RECT_TABLES ')]
    expected={k:hashlib.sha256((work/n).read_bytes()).hexdigest() for k,n in
        (('descriptors','ucode-table.json'),('types','ucode-types.json'))}
    if tables!=[TABLES] or expected!=TABLES:
        raise ValueError('Changed rectangle descriptor/type table capture')
    parsed=frame.validate_observations(work,log)
    if [(e['event'],e['frame'],e['locals'],e['temporary'],e['pool']) for e in parsed['events']]!=[
            ('frame-watch-installed',0,0,0,[]),('frame-write',136,136,0,[])]:
        raise ValueError('Changed rectangle frame observation')
    exits=[json.loads(x.removeprefix('RECT_EXIT ')) for x in lines if x.startswith('RECT_EXIT ')]
    for stage in ('cfe','uopt','ugen','cc'):
        group=[e for e in exits if e.get('stage')==stage]
        if len(group)!=1 or set(group[0])!={'stage','inferior','code'} or group[0]['code']!=0:
            raise ValueError('Incomplete rectangle producer/consumer exit')
    flow=[json.loads(x.removeprefix('RECT_FLOW ')) for x in lines if x.startswith('RECT_FLOW ')]
    if len(flow)!=2:
        raise ValueError('Incomplete rectangle compiler flow')
    for stage,producer,entry,capture in zip(('uopt','ugen'),('cfe','uopt'),flow,parsed['inputs']):
        if (set(entry)!={'stage','inferior','input','output','producer','producer_exits'} or
                entry['stage']!=stage or entry['producer']!=producer or entry['producer_exits']!=[0] or
                entry['inferior']!=capture['inferior'] or entry['input']!=capture['path']):
            raise ValueError('Malformed rectangle compiler flow')
        producer_exit=next(e for e in exits if e['stage']==producer)
        consumer_exit=next(e for e in exits if e['stage']==stage)
        pos=lambda prefix,item:next(i for i,line in enumerate(lines) if line.startswith(prefix) and json.loads(line[len(prefix):])==item)
        if (consumer_exit['inferior']!=entry['inferior'] or not
                pos('RECT_EXIT ',producer_exit)<pos('RECT_FLOW ',entry)<pos('FRAME_INPUT ',capture)<pos('RECT_EXIT ',consumer_exit)):
            raise ValueError('Misordered rectangle compiler flow')
    if flow[0]['output']!=flow[1]['input'] or flow[1]['output']!=flow[1]['input']:
        raise ValueError('Rectangle compiler producer/consumer path mismatch')
    table_pos=next(i for i,x in enumerate(lines) if x.startswith('RECT_TABLES '))
    watch_pos=next(i for i,x in enumerate(lines) if x.startswith('FRAME_TRACE ') and json.loads(x[12:])['event']=='frame-watch-installed')
    ugen_pos=next(i for i,x in enumerate(lines) if x.startswith('FRAME_INPUT ') and json.loads(x[12:])['stage']=='ugen')
    if not ugen_pos<table_pos<watch_pos:
        raise ValueError('Rectangle table probe outside initialized UGEN lifetime')
    if parse_object(work/'baseline.o')!=parse_object(work/'trace.o'):
        raise ValueError('Rectangle traced code, functions or bindings changed')
    if signature(work/'baseline.o')!=signature(work/'trace.o'):
        raise ValueError('Rectangle traced pools changed')
    checked_signature(work/'baseline.o')
    checked_signature(work/'trace.o')
    return parsed


def trace(root,out,label,body):
    root,out=Path(root).resolve(),Path(out).resolve()
    work=out/('compiler-'+label)
    if (work/'receipt.json').exists():
        raise ValueError('Preserve existing rectangle trace; choose a new name')
    full,adapter=prepared(root,out,label,body)
    with patch.object(frame,'screen',adapter),patch.object(frame,'debugger_script',debugger_script):
        record=frame.trace(root,out,'compiler-'+label,body)
    validate(root,work)
    if signature(work/'trace.o')!=signature(full):
        raise ValueError('Traced rectangle differs from complete-owner output')
    result=dict(label=label,normal=record['baseline'],code_unchanged=record['code_unchanged'],
        compiler_sha256=record['compiler_sha256'],events=record['events'],inputs=record['inputs'],
        record_counts={k:len(v) for k,v in record['records'].items()},installable=False)
    (work/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def trace_allocation(root,out,label,body,mode):
    root,out=Path(root).resolve(),Path(out).resolve()
    if mode!=5:
        raise ValueError('Unknown allocation observation mode')
    work=out/('allocation-'+label+'-'+str(mode))
    if (work/'trace.json').exists():
        raise ValueError('Preserve existing allocation trace; choose a new name')
    full,adapter=prepared(root,out,label+'-allocation-'+str(mode),body)
    with patch.object(allocation,'screen',adapter),patch.object(allocation,'debugger_script',allocation_script):
        record=allocation.trace_uopt(root,out,work.name,body,mode=mode)
    if frame.fingerprints(root)!=frame.COMPILERS or signature(work/'trace.o')!=signature(full):
        raise ValueError('Allocation diagnostic differs from complete-owner output')
    record['log_sha256']=hashlib.sha256((work/'debugger.txt').read_bytes()).hexdigest()
    (work/'trace.json').write_text(json.dumps(record,indent=2)+'\n')
    validate_allocation(root,work)
    text=(work/'uoptlist').read_text()
    result=dict(label=label,mode=mode,code_unchanged=record['code_unchanged'],
        normal=record['baseline'],bytes=record['bytes'],trace_sha256=record['trace_sha256'],
        variables=allocation.variable_expressions(text),
        constraints=allocation.allocation_constraints(text) if mode==5 else [],
        caveat=allocation.CAVEAT,installable=False)
    (work/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def validate_allocation(root,work):
    record=json.loads((work/'trace.json').read_text())
    log=(work/'debugger.txt').read_text()
    lines=log.splitlines()
    installed=[json.loads(x.removeprefix('RECT_ALLOC_INSTALLED ')) for x in lines if x.startswith('RECT_ALLOC_INSTALLED ')]
    if len(installed)!=1 or installed[0].get('program')!=str((root/'ido/ido5.3_recomp/uopt').resolve()):
        raise ValueError('Missing owned allocation installation')
    start=next(i for i,x in enumerate(lines) if x.startswith('RECT_ALLOC_INSTALLED '))
    child='TRACE_EXIT inferior=%d code=0'%installed[0]['inferior']
    if (lines.count(child)!=1 or lines.count('RECT_ALLOC_REMOVED')!=1 or
            lines.count(allocation.EXIT_MARKER)!=1 or not
            start<lines.index(child)<lines.index('RECT_ALLOC_REMOVED')<lines.index(allocation.EXIT_MARKER)):
        raise ValueError('Incomplete allocation child/cleanup/driver')
    for marker in ('Allocate diagnostic stream buffer','Suppress diagnostic real-number printer'):
        positions=[i for i,x in enumerate(lines) if x==marker]
        if not positions or not start<min(positions)<=max(positions)<lines.index(child):
            raise ValueError('Allocation diagnostic gate did not fire')
    if (record.get('mode')!=5 or record.get('exit_code')!=0 or not record.get('code_unchanged') or
            hashlib.sha256(log.encode()).hexdigest()!=record.get('log_sha256') or
            frame.fingerprints(root)!=frame.COMPILERS or
            hashlib.sha256((work/'uoptlist').read_bytes()).hexdigest()!=record.get('trace_sha256') or
            hashlib.sha256((work/'baseline.c').read_bytes()).hexdigest()!=record.get('source_sha256')):
        raise ValueError('Changed allocation receipt, source, trace or compiler')
    if parse_object(work/'baseline.o')!=parse_object(work/'trace.o'):
        raise ValueError('Allocation object changed')
    checked_signature(work/'baseline.o')
    checked_signature(work/'trace.o')
    text=(work/'uoptlist').read_text()
    return dict(variables=allocation.variable_expressions(text),
        constraints=allocation.allocation_constraints(text) if record['mode']==5 else [])


def constant_rows(work,stage):
    root=Path(__file__).resolve().parents[2]
    records=validate(root,work)['records'][stage]
    table=json.loads((work/'ucode-table.json').read_text())
    payload=(work/(stage+'.ucode')).read_bytes()
    result=[]
    for r in records:
        if r['name'] not in ('ldc','rldc') or not r['constants']:
            continue
        base=r['byte_offset']+table[r['opcode']]['descriptor'][16]*4+8
        size=r['constants'][0]
        extra=payload[base:base+size] if (((0x004E8000<<(r['type_storage']&31))&0x80000000) or r['opcode']==0x13) else b''
        result.append(dict(byte_offset=r['byte_offset'],name=r['name'],dtype=r['dtype'],constants=r['constants'],
            payload_hex=extra.hex(),text=extra.decode('ascii',errors='backslashreplace')))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--candidate',choices=('selected','mixed-product','mixed-outer'),default='selected')
    parser.add_argument('--name')
    parser.add_argument('--mode',type=int,choices=(5,))
    args=parser.parse_args()
    body=source.SELECTED if args.candidate=='selected' else dict(source.forms())[args.candidate]
    label=args.name or args.candidate
    if args.mode:
        result=trace_allocation(args.root,args.root/source.BUILD,label,body,args.mode)
        print(json.dumps({k:v for k,v in result.items() if k not in ('variables','constraints')},indent=2))
        print('Variables',len(result['variables']),'constraints',len(result['constraints']))
        return
    result=trace(args.root,args.root/source.BUILD,label,body)
    print(json.dumps({k:v for k,v in result.items() if k!='events'},indent=2))
    print('UGEN frame events',len(result['events']))


if __name__=='__main__':
    main()
