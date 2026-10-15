"""Capture scanner compiler nodes with the existing owned-child trace gates."""
import argparse
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_texture_vertex_span_controlflow as flow
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_text_measurer_frontend_trace as capture
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.pad_generated_object import parse_object

BUILD=flow.BUILD+'/ucode'


def phase_summary(record,text,initializations=None):
    if record.get('code_unchanged') is not True:
        raise ValueError('Scanner compiler capture not qualified')
    statements=initializations if initializations is not None else {
        'stage = 0;':'stage','maximum = 0;':'maximum','nested = 0;':'nested',
        'trimFirst = 0;':'trimFirst','count = 3;':'count'}
    if not statements or 'count' not in statements.values() or len(set(statements.values()))!=len(statements):
        raise ValueError('Scanner source roles must be distinct and include count')
    lines=text.splitlines()
    positions={}
    for statement,name in statements.items():
        matches=[i+1 for i,line in enumerate(lines) if line.strip()==statement]
        if not matches:
            raise ValueError('Missing scanner initialization source line')
        positions[matches[0]]=name
    def bindings(rows,storage):
        current=None
        found={}
        for row in rows:
            if row['name']=='loc':
                line=row['words'][1]
                current=positions.get(line)
            if current and row['name']=='str' and row['storage']==storage:
                if current in found:
                    raise ValueError('Duplicate scanner initialization binding')
                found[current]=row['offset']
        if set(found)!=set(statements.values()):
            raise ValueError('Incomplete scanner initialization bindings')
        return found
    optimized=record['optimizer_records']
    end=[row for row in optimized if row['name'] in ('ldc','rldc') and row['constants'] and row['constants'][0]==0xFFFFFFDF]
    if not end:
        raise ValueError('Missing scanner end-tag allocation evidence')
    registers=bindings(optimized,'R')
    observed={event['raw44']//4 for event in record['complete']['events'] if event['type_storage']>>5==3}
    if not set(registers.values())<=observed:
        raise ValueError('Assigned scanner registers not observed in UGEN')
    return dict(frontend_offsets=bindings(record['records'],'M'),optimizer_registers=registers,
        count_materialization_register=registers['count'],
        end_tag_unallocated_literals=sum(row['name']=='ldc' for row in end),
        end_tag_allocated_registers=sorted({row['words'][1] for row in end if row['name']=='rldc'}),
        final_ugen_observes_assigned_registers=True,optimizer_records=record['optimizer_record_count'],
        frontend_records=record['record_count'],ugen_events=record['complete']['event_count'],
        code_unchanged=record['code_unchanged'],installable=False)


def compile_target(root,out,name,body):
    text='#include <ultra64.h>\n'+source.DECLARATIONS+'\n'+body+'\n'
    obj,diagnostics=build.compile_owner(root,out,text,name)
    data,functions=build.link_owner(root,out,obj,source.OWNER)
    info=functions[source.FUNCTION]
    words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
    retail=list(struct.unpack_from('>339I',(root/'conker/conker.us.bin').read_bytes(),source.ROM))
    return dict(words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-len(retail)),
        diagnostics=diagnostics,profile=['-O2','-g3']),words


def trace_target(root,out,label,body,initializations=None):
    source.freeze(root,root/source.BUILD)
    with patch.object(capture.trace.screen,'compile_candidate',side_effect=compile_target),\
            patch.dict(capture.trace.screen.PROFILES,owner=('-O2','-g3')):
        record=capture.capture_frontend(root,out,label,body)
    baseline=record['complete']['baseline']
    if baseline['diagnostics'] or baseline['profile']!=['-O2','-g3']:
        raise ValueError('Unexpected scanner trace compile profile or diagnostic')
    # The standalone trace must reproduce the qualified complete-owner target.
    work=out/label
    obj,diagnostics=build.compile_owner(root,work,source.recover((root/source.BUILD/'before-owner').read_text(),body),'owner')
    standalone,sf,sr=parse_object(work/'baseline.o')
    owner,of,orel=parse_object(obj)
    a,b=sf[source.FUNCTION],of[source.FUNCTION]
    relative=lambda rel,info:{at-info['value']:value for at,value in rel.items() if info['value']<=at<info['value']+info['size']}
    if diagnostics or (a['size'],standalone[a['value']:a['value']+a['size']],relative(sr,a)) != \
            (b['size'],owner[b['value']:b['value']+b['size']],relative(orel,b)):
        raise ValueError('Standalone scanner trace differs from the complete owner')
    record['standalone_matches_complete_owner_target']=True
    (work/'frontend.json').write_text(json.dumps(record,indent=2)+'\n')
    summary=phase_summary(record,(work/'baseline.c').read_text(),initializations)
    (work/'phase-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return record


def trace_allocation(root,out,label,body):
    source.freeze(root,root/source.BUILD)
    with patch.object(allocation.screen,'compile_candidate',side_effect=compile_target),\
            patch.dict(allocation.screen.PROFILES,owner=('-O2','-g3')):
        record=allocation.trace_uopt(root,out,label,body,mode=5)
    text=(out/label/'uoptlist').read_text()
    variables=allocation.variable_expressions(text)
    constraints=allocation.allocation_constraints(text)
    record.update(variables=variables,constraints=constraints)
    (out/label/'allocation.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',choices=('homes','for-increment','explicit-stage-values'),default='homes')
    parser.add_argument('--allocation',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    out.mkdir(exist_ok=True)
    body=dict(flow.variants())[args.candidate]
    if args.allocation:
        record=trace_allocation(root,out,args.candidate+'-allocation',body)
        print(json.dumps(dict(candidate=args.candidate,variables=len(record['variables']),
            constraints=len(record['constraints']),code_unchanged=record['code_unchanged'],
            caveat=record['caveat']),indent=2))
        return
    record=trace_target(root,out,args.candidate,body)
    print(json.dumps(dict(candidate=args.candidate,frontend_records=record['record_count'],
        optimizer_records=record['optimizer_record_count'],ugen_events=record['complete']['event_count'],
        code_unchanged=record['code_unchanged'],standalone_owner_agreement=True,
        baseline=record['complete']['baseline']),indent=2))


if __name__=='__main__':
    main()
