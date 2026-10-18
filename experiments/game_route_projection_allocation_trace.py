"""Fingerprint-locked isolated projection allocation observation; no installation."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_route_projection_unrolled_fit as source
from tools.experiments import game_remaining_donor_candidates as compiler
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.experiments.game_actor_record_gate_compiler_trace import lifecycle
from tools.experiments import game_packet_rectangle_allocator_trace as native

BUILD='conker/build/game-route-projection-allocation-trace'
PREFIX='''#include <ultra64.h>
extern s16 D_80087290;
extern u8 *D_800D2350;
u8 func_1508907C(u8, u8, u8, u8);
'''
FLAGS=('-O2','-g3','-Wo,-loopunroll,0')
compile_owner=source.source.neighbor.baseline.model.compile_owner


def isolated(root,out):
    source.source.freeze(root,out)
    obj,diagnostics=compile_owner(root,out,PREFIX+source.SELECTED,'isolated')
    source.checked(obj)
    if diagnostics or set(source.source.neighbor.parse_object(obj)[1])!={source.source.FUNCTION}:
        raise ValueError('Unexpected isolated projection diagnostics or scope')
    return obj


CRITICAL=(2,18,27,109,113,262)
COLORS={2:19,18:18,27:15,109:14,113:16,262:17}
CHOICES=(109,27,113,262,18,2)


def facts(text):
    first='IN LOCAL OPTIMIZATION OF '+source.source.FUNCTION
    last='IN REEMISSION OF '+source.source.FUNCTION
    if text.count(first)!=1 or text.count(last)!=1:raise ValueError('Missing/duplicate projection procedure')
    block=text[text.index(first):text.index(last)+len(last)]
    variables=allocation.variable_expressions(block);constraints=allocation.allocation_constraints(block)
    indexed={r['expression']:r for r in constraints}
    if len(indexed)!=len(constraints):raise ValueError('Duplicate projection allocation expression')
    expected={('P',0):18,('P',4):2,('M',-8):27,('M',-50):109,('M',-51):113,('M',-60):15}
    for key,expression in expected.items():
        matches=[v for v in variables if (v['storage'],v['offset'])==key]
        if len(matches)!=1 or (matches[0]['procedure'],matches[0]['expression'])!=(749,expression):
            raise ValueError('Changed projection input/local identity')
        if indexed[expression]['identity']!=matches[0]['identity']:
            raise ValueError('Variable and allocated live range disagree')
    for expression,color in COLORS.items():
        if expression not in indexed or indexed[expression]['color']!=color:
            raise ValueError('Changed projection saved allocation')
    if indexed[15]['color']!=-1:raise ValueError('Entry object is not the observed spill')
    if any(not (set(CRITICAL)-{key})<=set(indexed[key]['interference']) for key in CRITICAL):
        raise ValueError('Changed six-role interference clique')
    return block,variables,constraints


def color_events(log,constraints):
    lines=log.splitlines()
    events=[json.loads(line.removeprefix('RECT_COLOR ')) for line in lines if line.startswith('RECT_COLOR ')]
    expected_prefix=['local-entry','local-entry-return','global-entry','initialized']
    if len(events)!=168 or [e['event'] for e in events[:4]]!=expected_prefix or events[-1]['event']!='global-entry-return':
        raise ValueError('Incomplete projection allocation event sequence')
    markers=[json.loads(l.removeprefix('RECT_ALLOC_INSTALLED ')) for l in lines if l.startswith('RECT_ALLOC_INSTALLED ')]
    if len(markers)!=1:raise ValueError('Missing/duplicate allocator install')
    owned={(e['inferior'],e['pid'],e['table']) for e in events}
    if len(owned)!=1 or events[0]['inferior']!=markers[0]['inferior'] or events[0]['pid']<=0:
        raise ValueError('Wrong allocator process/table ownership')
    positions=[i for i,l in enumerate(lines) if l.startswith('RECT_COLOR ')]
    child='TRACE_EXIT inferior=%d code=0'%markers[0]['inferior']
    if not lines.index('RECT_COLOR_INSTALLED')<min(positions)<=max(positions)<lines.index(child)<lines.index('RECT_COLOR_REMOVED'):
        raise ValueError('Misordered allocator probe lifetime')
    returns={0x48FC16:'local-entry-return',0x4810ED:'compute-save-return',
        0x4813A1:'needsplit-return',0x48FC86:'global-entry-return'}
    addresses=native.POINTS.copy()
    addresses.update(returns)
    pointers={r['index']:(r['ichain'],r['live']) for r in events[0]['rows']}
    if set(pointers)!=set(CRITICAL):raise ValueError('Changed critical allocator rows')
    for index,event in enumerate(events,1):
        if event['sequence']!=index or addresses.get(event['host_pc'])!=event['event']:
            raise ValueError('Wrong allocator sequence or instruction')
        if len(event['rows'])!=6 or {r['index'] for r in event['rows']}!=set(CRITICAL):
            raise ValueError('Missing/duplicate critical live-range row')
        for row in event['rows']:
            if (row['ichain'],row['live'])!=pointers.get(row['index']) or native.decode(row)['expression']!=row['index']:
                raise ValueError('Changed critical live-range identity')
            if event['event']=='initialized' or event['event'].endswith('-return'):native.checked_units(row)
        active=event['active']
        if active and active['index'] in CRITICAL:
            snapshot=next(r for r in event['rows'] if r['index']==active['index'])
            if any(active[key]!=snapshot[key] for key in ('ichain','live','head','table_entry','ichain_prefix')):
                raise ValueError('Active allocator row disagrees with its snapshot')
    initial=[native.decode(r) for r in events[3]['rows']]
    if any(set(r['forbidden'])&set(range(14,20)) for r in initial):
        raise ValueError('Saved colors were already forbidden before selection')
    chosen=[e for e in events if e['event']=='chosen' and e['active']['index'] in CRITICAL]
    if tuple(e['active']['index'] for e in chosen)!=CHOICES:raise ValueError('Changed saved-role selection order')
    final={r['index']:native.decode(r) for r in events[-1]['rows']}
    indexed={r['expression']:r for r in constraints}
    for key,color in COLORS.items():
        if final[key]['assigned']!=color or final[key]['forbidden']!=indexed[key]['forbidden']:
            raise ValueError('Native and printed allocated colors disagree')
    return events,dict(event_count=len(events),choice_order=list(CHOICES),
        initially_forbidden_saved_colors=False,final_colors=COLORS,
        native_gain_bits={e['active']['index']:native.decode(e['active'])['save_bits'] for e in chosen})


def observe(root,colors=False):
    out=root/BUILD;isolated(root,out);content=PREFIX+source.SELECTED
    def compile_baseline(root,work,name,actual):
        if actual!=content:raise ValueError('Changed isolated projection input')
        obj,diagnostics=compile_owner(root,work,actual,name);source.checked(obj)
        if diagnostics:raise ValueError('Changed isolated projection diagnostics')
        return dict(function=source.source.FUNCTION,raw_sha256=source.RAW_SHA,words=321,diagnostics=diagnostics),None
    adapter=SimpleNamespace(compile_candidate=compile_baseline,PROFILES={'owner':FLAGS},
        compiler=SimpleNamespace(parse_object=source.source.neighbor.parse_object,sections=compiler.sections))
    name='selected-colors' if colors else 'selected-mode-5'
    if colors:
        observer=native.OBSERVERS.replace('(123,137)',repr(CRITICAL))
        if observer==native.OBSERVERS:raise ValueError('Missing allocator index anchors')
        with patch.object(allocation,'screen',adapter),patch.object(native,'OBSERVERS',observer), \
                patch.object(allocation,'debugger_script',native.allocation_script):
            complete=allocation.trace_uopt(root,out,name,content,5)
    else:
        with patch.object(allocation,'screen',adapter):complete=allocation.trace_uopt(root,out,name,content,5)
    work=out/name;log=(work/'debugger.txt').read_text()
    ended=lifecycle(root.resolve(),log)
    if log.splitlines().count('Allocate diagnostic stream buffer')!=1 or 'Suppress diagnostic real-number printer' not in log:
        raise ValueError('Projection diagnostic probes did not fire')
    block,variables,constraints=facts((work/'uoptlist').read_text())
    source.source.freeze(root,out)
    result=dict(complete=complete,lifecycle=ended,variables=variables,constraints=constraints,
        target_sha256=hashlib.sha256(block.encode()).hexdigest(),installable=False,
        suppressed_real_costs_not_interpreted=True)
    if colors:
        events,summary=color_events(log,constraints);result['color_facts']=summary
        (work/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    (work/'target.txt').write_text(block)
    (work/'projection.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def audit(root,colors=False):
    out=root/BUILD;source.source.freeze(root,out)
    work=out/('selected-colors' if colors else 'selected-mode-5')
    record=json.loads((work/'trace.json').read_text());log=(work/'debugger.txt').read_text()
    if allocation.compiler_fingerprints(root)!=allocation.COMPILERS or record.get('exit_code')!=0 or \
            record.get('code_unchanged') is not True or record.get('compiler_sha256')!=allocation.COMPILERS:
        raise ValueError('Incomplete/changed projection compiler receipt')
    if (work/'baseline.c').read_text()!=PREFIX+source.SELECTED or \
            hashlib.sha256((work/'baseline.c').read_bytes()).hexdigest()!=record.get('source_sha256'):
        raise ValueError('Changed projection diagnostic source')
    payload=(work/'uoptlist').read_bytes()
    if hashlib.sha256(payload).hexdigest()!=record.get('trace_sha256') or len(payload)!=record.get('bytes'):
        raise ValueError('Changed projection diagnostic listing')
    if log.splitlines().count('Allocate diagnostic stream buffer')!=1 or 'Suppress diagnostic real-number printer' not in log or \
            'Python Exception' in log or 'Error in sourced command' in log:
        raise ValueError('Missing/failed projection diagnostic probe')
    ended=lifecycle(root.resolve(),log)
    before,after=work/'baseline.o',work/'trace.o';source.checked(before);source.checked(after)
    if source.source.neighbor.parse_object(before)!=source.source.neighbor.parse_object(after):
        raise ValueError('Trace changed complete object text/definitions/bindings')
    a,b=compiler.sections(before),compiler.sections(after)
    pools={n for n in a.keys()|b.keys() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if any(a.get(n)!=b.get(n) for n in pools):raise ValueError('Trace changed object pools')
    block,variables,constraints=facts(payload.decode())
    result=dict(lifecycle=ended,variables=variables,constraints=constraints,
        raw_sha256=source.RAW_SHA,target_sha256=hashlib.sha256(block.encode()).hexdigest(),
        debugger_sha256=hashlib.sha256(log.encode()).hexdigest(),installable=False,
        reused_completed_capture=True,suppressed_real_costs_not_interpreted=True)
    if colors:
        events,summary=color_events(log,constraints);result['color_facts']=summary
        (work/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    (work/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observe',action='store_true')
    parser.add_argument('--colors',action='store_true');parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.observe or args.colors or args.audit:
        result=audit(root,args.colors) if args.audit else observe(root,args.colors)
        print(json.dumps({k:v for k,v in result.items() if k not in ('complete','variables','constraints')},indent=2))
    else:
        obj=isolated(root,root/BUILD);print(json.dumps(dict(object=str(obj),raw_sha256=source.RAW_SHA,identical_to_owner=True)))
