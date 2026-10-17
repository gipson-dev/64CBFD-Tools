"""Fingerprint-locked record-gate compiler evidence, never a production install."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_actor_record_gate_recovery as source
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.experiments import game_text_measurer_frontend_trace as frontend

BUILD='conker/build/game-actor-record-gate-compiler'
REMAINING=source.SELECTED.replace('i < 2','i - 2 < 0')
HASHES={'normal':source.RAW_SHA,'remaining':'c40d55e7f1512f0526b4c49ec71fd463f089e8407f8a489c956fc7f796e3e09d'}
PROCEDURE=760

def lifecycle(root,log):
    programs=[Path(p) for p in re.findall(r'(?m)^process \d+ is executing new program: (.+)$',log)]
    expected=[root/'ido/ido5.3_recomp'/name for name in ('cfe','uopt','ugen','as1')]
    exits=re.findall(r'(?m)^TRACE_EXIT inferior=(\d+) code=(\S+)$',log)
    if programs!=expected or exits!=[(str(i),'0') for i in (2,3,4,5,1)]:
        raise ValueError('Compiler producer/consumer/driver lifecycle incomplete')
    positions=[]
    for program,index in zip(expected,range(2,6)):
        positions.extend((log.index('executing new program: '+str(program)),log.index('TRACE_EXIT inferior='+str(index)+' code=0')))
    if positions!=sorted(positions) or not re.search(r'(?m)^\*?\s+1\s+<null>',log):
        raise ValueError('Compiler lifecycle ordering or final cleanup incomplete')
    return dict(children=['cfe','uopt','ugen','as1'],child_and_driver_exit_codes=[0]*5,final_inferior_null=True)

def body(variant):
    if variant not in HASHES:raise ValueError('Unknown record-gate trace variant')
    return source.SELECTED if variant=='normal' else REMAINING

def owner(root,variant):
    source.freeze(root,root/source.BUILD)
    return source.recovered_owner((root/source.BUILD/'before-record_gate_owner').read_text(),body(variant))

def adapter(content,variant):
    def compile_baseline(root,work,label,actual):
        if actual!=content:raise ValueError('Changed complete record-gate trace owner')
        obj,diag=source.compile_owner(root,work,actual,label);raw,_=source.parts(obj)
        if diag or hashlib.sha256(raw).hexdigest()!=HASHES[variant]:raise ValueError('Changed record-gate baseline words')
        return dict(function=source.FUNCTION,raw_sha256=HASHES[variant],words=len(raw)//4,diagnostics=diag),None
    return SimpleNamespace(compile_candidate=compile_baseline,PROFILES={'owner':('-O2','-g3')},
        compiler=SimpleNamespace(parse_object=source.parse_object,sections=source.projection.sections))

def procedure(text):
    first='IN LOCAL OPTIMIZATION OF '+source.FUNCTION;last='IN REEMISSION OF '+source.FUNCTION
    if text.count(first)!=1 or text.count(last)!=1:raise ValueError('Missing/duplicate record-gate procedure')
    return text[text.index(first):text.index(last,text.index(first))+len(last)]

def allocation_facts(text,variant):
    body(variant);block=procedure(text)
    variables=allocation.variable_expressions(block);constraints=allocation.allocation_constraints(block)
    counters=[v for v in variables if (v['storage'],v['procedure'],v['offset'])==('M',PROCEDURE,-4)]
    if len(counters)!=1 or not counters[0]['virtual_register'] or counters[0]['identity']!='168|0':
        raise ValueError('Changed record-gate counter identity')
    by_expression={r['expression']:r for r in constraints}
    if len(by_expression)!=len(constraints):raise ValueError('Duplicate record-gate allocation expression')
    expected={4:('168|0',14),51:('250|0',15),52:('1509|0',16),53:('1493|0',17),
        54:('160|0',18),56:('1557|0',14),60:('1573|0',16)}
    if variant=='normal':expected[61]=('2|0',19)
    for expression,(identity,color) in expected.items():
        if expression not in by_expression or (by_expression[expression]['identity'],by_expression[expression]['color'])!=(identity,color):
            raise ValueError('Changed record-gate allocated role: '+str(expression))
    bounds=[r for r in constraints if r['identity']=='2|0']
    if (len(bounds)==1)!=(variant=='normal'):raise ValueError('Changed bound-two allocation')
    interference=by_expression[4]['interference']
    if (61 in interference)!=(variant=='normal'):raise ValueError('Changed bound/counter interference')
    if variant=='normal' and not set((14,15,16,17,18)).issubset(by_expression[61]['forbidden']):
        raise ValueError('Missing bound-two forbidden colors')
    return dict(procedure=PROCEDURE,counter=counters[0],roles={str(k):by_expression[k] for k in expected},
        bound_two_saved_color=19 if bounds else None,actor_array_saved_color=14,
        bound_interferes_with_counter=bool(bounds),suppressed_real_numbers_not_interpreted=True,
        original_source_or_retail_allocator_not_observed=True)

def observe(root,variant='normal',mode=5):
    if mode not in (5,6):raise ValueError('Only qualified mode5/mode6 captures are used')
    content=owner(root,variant);out=root/BUILD;name=variant+'-mode-'+str(mode)
    with patch.object(allocation,'screen',adapter(content,variant)):
        complete=allocation.trace_uopt(root,out,name,content,mode)
    work=out/name;log=(work/'debugger.txt').read_text()
    ended=lifecycle(root,log)
    if log.splitlines().count('Allocate diagnostic stream buffer')!=1 or 'Suppress diagnostic real-number printer' not in log:
        raise ValueError('Required record-gate diagnostic probes did not fire')
    block=procedure((work/'uoptlist').read_text());facts=allocation_facts((work/'uoptlist').read_text(),variant) if mode==5 else None
    (work/'target.txt').write_text(block)
    source.freeze(root,root/source.BUILD)
    result=dict(variant=variant,mode=mode,complete=complete,facts=facts,installable=False,
        target_listing_sha256=hashlib.sha256(block.encode()).hexdigest(),production_unchanged=True,lifecycle=ended)
    (work/'compiler.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def procedure_records(records):
    starts=[i for i,r in enumerate(records) if r['name']=='ent' and r['block']==PROCEDURE]
    if len(starts)!=1:raise ValueError('Missing/duplicate target wire entry')
    lo=starts[0];ends=[i for i in range(lo+1,len(records)) if records[i]['name']=='ent']
    if not ends or records[ends[0]]['block']!=772:raise ValueError('Changed target wire successor')
    result=records[lo:ends[0]]
    if sum(r['name']=='end' for r in result)!=1:raise ValueError('Incomplete target wire scope')
    return result

def wire_facts(before,after):
    a,b=procedure_records(before),procedure_records(after)
    gate=lambda rs:[r for r in rs if r['name']=='lod' and (r['dtype'],r['storage'],r['block'],r['offset'])==('A','S',747,0)]
    gates=[len(gate(a)),len(gate(b))]
    comparisons=[sum(r['name']=='les' and r['dtype']=='J' for r in rs) for rs in (a,b)]
    unequal=[r for r in b if r['name']=='neq' and r['dtype']=='J']
    bounds=[r for r in b if r['name']=='rldc' and r['constants'] and r['constants'][0]==2]
    if gates!=[2,1] or comparisons!=[2,0] or len(unequal)!=1:
        raise ValueError('Changed gate CSE or signed loop-test rewrite')
    if len(bounds)!=1 or bounds[0]['words'][1]!=21:raise ValueError('Changed bound-two hardware register')
    actor=lambda rs,name:[r for r in rs if r['name']==name and r['storage']=='S' and r['block']==752 and r['offset']==0]
    address=[actor(a,'lda'),actor(b,'rlda')]
    if list(map(len,address))!=[5,2] or any(r['words'][2]!=16 for r in address[1]):
        raise ValueError('Changed actor-array address promotion')
    return dict(procedure=PROCEDURE,scoped_record_counts=[len(a),len(b)],initial_global_loads=gates,
        signed_less_than_records=comparisons,optimized_signed_unequal_records=1,
        bound_two_hardware_GPR=21,actor_address_records=[5,2],actor_address_hardware_GPR=16,
        original_source_types_not_inferred=True)

def wire(root):
    content=owner(root,'normal');out=root/BUILD;name='normal-wire'
    with patch.object(frontend.trace,'screen',adapter(content,'normal')):
        complete=frontend.capture_frontend(root,out,name,content)
    ended=lifecycle(root,(out/name/'debugger.txt').read_text())
    facts=wire_facts(complete['records'],complete['optimizer_records'])
    source.freeze(root,root/source.BUILD)
    result=dict(facts=facts,complete=complete,code_unchanged=complete['code_unchanged'],
        installable=False,production_unchanged=True,lifecycle=ended)
    (out/name/'compiler-wire.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--wire',action='store_true')
    parser.add_argument('--variant',choices=tuple(HASHES),default='normal');parser.add_argument('--mode',type=int,choices=(5,6),default=5)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    result=wire(root) if args.wire else observe(root,args.variant,args.mode)
    print(json.dumps({k:v for k,v in result.items() if k!='complete'},indent=2),flush=True)
