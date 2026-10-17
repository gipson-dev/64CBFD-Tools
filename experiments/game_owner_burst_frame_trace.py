"""Observe the unchanged burst candidate's CFE/UOPT storage and UGEN frame."""
import hashlib
import json
import struct
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_owner_burst_emitter as source
from tools.experiments import game_actor_callback_frame_trace as shared
from tools.experiments.game_frame_timing_frontend import procedure_records

BUILD='conker/build/game-owner-burst-frame-trace'
PREFIX='''#include <ultra64.h>
extern f32 D_800BE9A4, D_800A1950[];
typedef struct {
    u8 *owner;
    u8 owner_id, state, pad6[2];
    f32 value;
    u8 mode, padD[3];
} Generated11FF10Payload;
'''


def isolated_source(body,types=None):return PREFIX+(types or source.TYPE)+'\n'+body+'\n'


def compile_isolated(root,out,label,body,types=None,expected_object=None,shape=None):
    obj,diag=source.compile_owner(root,out,isolated_source(body,types),label)
    if diag:raise ValueError('Burst isolated compiler diagnostics: '+repr(diag))
    expected=expected_object or root/source.BUILD/'candidate.o'
    if source.parts(obj)!=source.parts(expected):raise ValueError('Burst isolation changed target words/relocations')
    shape=shape or (288,344,source.RAW_SHA)
    if hashlib.sha256(source.parts(obj)[0]).hexdigest()!=shape[2]:
        raise ValueError('Unexpected isolated burst code')
    data,functions,_=source.parse_object(obj)
    if set(functions)!={source.FUNCTION}:raise ValueError('Burst trace must contain exactly one function')
    words=source.linked(root,out,obj,label+'-linked')
    if len(words)!=shape[0] or words[0]!=(0x27BD0000|((-shape[1])&65535)):raise ValueError('Changed isolated burst frame')
    return dict(words=shape[0],frame=shape[1],raw_sha=shape[2],target_bindings=len(source.parts(obj)[1]),
        owner_target_identical=True),words


def phase_summary(record,content):
    if record.get('code_unchanged') is not True:raise ValueError('Unqualified burst frame trace')
    phases=record['records'];ent=[r for r in phases['frontend'] if r['name']=='ent']
    if len(ent)!=1:raise ValueError('Burst trace has an ambiguous procedure')
    procedure=ent[0]['block']
    front=procedure_records(phases['frontend'],procedure)
    optimized=procedure_records(phases['optimizer'],procedure)
    field='request.fields' if 'request.fields.position' in content else 'request'
    inputs='inputs.points' if 'inputs.points[0]' in content else 'inputs'
    markers={'payload':'payload.owner = owner;',
        'savedData':'savedData = data;',
        'input0':inputs+'[0] = (BurstVector2D14 *)D_800A1950;',
        'output0':'outputs[0] = &'+field+'.position;',
        'transform':'func_15145EA4('+inputs+', outputs, *(u8 **)(owner + 0x1D4) + 0x3C0, 2);',
        'delta':'delta.x -= '+field+'.position.x;',
        'create':'created = func_1513D2F0(&request, D_800A4AA0, 0x26, 0, 0, 0x25,',
        'copy':'memcpy(created + 0x110, &payload, sizeof(payload));'}
    lines=content.splitlines();positions={}
    for name,statement in markers.items():
        found=[i+1 for i,line in enumerate(lines) if line.strip()==statement]
        if len(found)!=1:raise ValueError('Missing/ambiguous burst source marker: '+name)
        positions[name]=found[0]
    def selected(records):
        current=None;result={k:[] for k in markers}
        for row in records:
            if row['name']=='loc':current=row['words'][1]
            for name,line in positions.items():
                if current==line and row['name'] in ('lda','lod','str','rlda','def','vreg','par','cup'):
                    result[name].append(row)
        return result
    return dict(procedure=procedure,source_lines=positions,frontend_records=len(front),optimizer_records=len(optimized),
        frontend_definitions=[r for r in front if r['name']=='def'],
        optimizer_definitions=[r for r in optimized if r['name']=='def'],
        frontend_markers=selected(front),optimizer_markers=selected(optimized),
        all_definition_fields_are_raw_ucode_operands=True,installable=False)


def checked_layout(summary):
    form=summary.get('form')
    expected={'selected':(188,200,344,{'payload':-144,'input0':-152,'output0':-160,'delta':-172,'request':-92,'savedData':-4}),
        'descriptor-align8':(192,204,352,{'payload':-148,'input0':-156,'output0':-164,'delta':-176,'request':-96,'savedData':-4}),
        'aligned-pairs':(196,208,352,{'payload':-148,'input0':-160,'output0':-168,'delta':-180,'request':-96,'savedData':-4})}
    if form not in expected or summary.get('code_unchanged') is not True:raise ValueError('Unknown/unqualified burst frame summary')
    fm,om,frame,addresses=expected[form]
    def unique(rows):
        if len(rows)!=1:raise ValueError('Ambiguous burst storage observation')
        return rows[0]
    front=unique([r['length'] for r in summary['frontend_definitions'] if r['storage']=='M'])
    opt=unique([r['length'] for r in summary['optimizer_definitions'] if r['storage']=='M'])
    markers=summary['frontend_markers'];observed={}
    for name in ('payload','input0','output0','delta','savedData'):
        operation='str' if name in ('payload','savedData') else 'lda' if name in ('input0','output0') else 'lod'
        size=8 if name in ('input0','output0') else 4
        rows=[r['offset'] for r in markers[name] if r['name']==operation and r['storage']=='M' and r['length']==size]
        if name=='delta' and len(rows)!=2:raise ValueError('Ambiguous burst delta observation')
        observed[name]=unique(rows) if name!='delta' else rows[0]
    observed['request']=unique([r['offset'] for r in markers['output0'] if r['name']=='lda' and r['storage']=='M' and r['length']==88])
    delta=[r['offset'] for r in markers['delta'] if r['name']=='lod' and r['storage']=='M' and r['length']==4]
    if delta!=[observed['delta'],observed['request']+0x1C]:raise ValueError('Changed burst delta/position field binding')
    events=summary['events'];last=events[-1] if events else {}
    if ([e['event'] for e in events]!=['frame-watch-installed','frame-write','frame-write','frame-write']
            or [e['frame'] for e in events]!=[0,96,144,frame]
            or any(e['pool'] or e['temporary'] or e['temp_base'] for e in events)
            or (last.get('saved'),last.get('outgoing'),last.get('locals'))!=(96,48,(opt+7)&~7)
            or last.get('frame')!=96+48+((opt+7)&~7)
            or (front,opt,observed)!=(fm,om,addresses)):
        raise ValueError('Changed burst automatic-storage/frame observations')
    return dict(frontend_local_bytes=front,optimizer_local_bytes=opt,ugen_aligned_local_bytes=(opt+7)&~7,
        frame=frame,saved_bytes=96,outgoing_bytes=48,caller_relative=observed,
        observed_late_frame_growth=False,original_types_not_proven=True,installable=False)


def prove_machine_offsets(layout,words):
    frame=layout['frame'];a=layout['caller_relative']
    offsets={18:a['delta'],30:a['output0'],23:a['input0'],22:a['request']+0x1C,
        4:a['request'],5:a['payload']}
    for register,offset in offsets.items():
        instruction=(9<<26)|(29<<21)|(register<<16)|((frame+offset)&65535)
        if words.count(instruction)!=1:raise ValueError('Emitted burst address disagrees with compiler wire storage')
    saved=(43<<26)|(29<<21)|(16<<16)|((frame+a['savedData'])&65535)
    if words.count(saved)!=1 or words[0]!=(0x27BD0000|((-frame)&65535)):
        raise ValueError('Emitted burst alias/frame disagrees with compiler wire storage')
    return dict(seven_emitted_addresses_checked=True,wire_and_machine_offsets_equal=True)


def trace(root,out,label='selected',form='selected'):
    source.qualify(root,root/source.BUILD)
    body,types=source.SELECTED,source.TYPE;shape=(288,344,source.RAW_SHA)
    expected=root/source.BUILD/'candidate.o'
    if form=='descriptor-align8':
        name,body,types=next(source.alignment_forms())
        if name!=form:raise ValueError('Changed aligned burst screen')
        shape=(288,352,'648dc74818f6fe8e19cab7b8470c6a9d5dafe002848711e5bf6f32d28bb6d18e')
        with patch.object(source,'TYPE',types):
            expected,_,row=source.measure(root,root/source.BUILD,form,body)
        if (row['words'],row['frame'],row['raw_sha'])!=shape:raise ValueError('Changed aligned burst body')
    elif form=='aligned-pairs':
        from tools.experiments import game_owner_burst_storage_candidates as storage
        _,body,types=next(storage.forms());shape=(288,352,'23e2faa5074572a4fddad79b0676cc091d94668583ecf8b952b8015c1dc5f079')
        expected,_,_,row=storage.qualify_aligned(root,root/storage.BUILD)
        if (row['words'],row['frame'],row['raw_sha'])!=shape:raise ValueError('Changed aligned-pair burst body')
    elif form!='selected':raise ValueError('Unknown burst storage trace form')
    def compile(root,work,label,body):return compile_isolated(root,work,label,body,types,expected,shape)
    adapter=SimpleNamespace(compile_candidate=compile)
    with patch.object(shared,'screen',adapter):record=shared.trace(root,out,label,body)
    work=out/label
    content=(work/'baseline.c').read_text()
    if content!=isolated_source(body,types):raise ValueError('Changed burst trace source')
    summary=phase_summary(record,content)
    summary.update(form=form,events=record['events'],compiler_sha256=record['compiler_sha256'],code_unchanged=True,
        source_sha256=hashlib.sha256(content.encode()).hexdigest(),whole_owner_target_identical=True)
    summary['layout']=checked_layout(summary)
    words=list(struct.unpack_from('>288I',source.projection.sections(work/'baseline-linked.elf')['.text'][1]))
    summary['layout'].update(prove_machine_offsets(summary['layout'],words))
    source.freeze(root,root/source.BUILD)
    (work/'burst-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--form',choices=('selected','descriptor-align8','aligned-pairs'),default='selected')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];result=trace(root,root/BUILD,args.form,args.form)
    print(json.dumps({k:result[k] for k in ('procedure','frontend_records','optimizer_records','events',
        'code_unchanged','whole_owner_target_identical','installable')},indent=2),flush=True)
