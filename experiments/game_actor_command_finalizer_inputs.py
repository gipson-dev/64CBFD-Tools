"""Fit primary numeric-input lifetime and live selector snapshots."""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_scalar as previous
from tools.tests import test_game_actor_command_finalizer_recovery as recovery

BASE=previous.SELECTED


def lower_after_index(body):
    body=previous.previous.flow.replace_once(body,'        lower = 40;\n','')
    marker='        primaryIndex = first;'
    assert body.count(marker)==2
    return body.replace(marker,marker+'\n        lower = 40;',1)


def scoped_input(body,kind='u32',after=False):
    old='''        lower = 40;
        delta = actor[0x1FE];
        primaryIndex = first;
        value = (s32)((f32)(u32)delta * scale * D_80097D48);'''
    assignments=('            primaryIndex = first;\n            lower = 40;' if after else
        '            lower = 40;\n            primaryIndex = first;')
    new='''        {
            %s numeric = actor[0x1FE];
%s
            value = (s32)((f32)(u32)numeric * scale * D_80097D48);
        }'''%(kind,assignments)
    return previous.previous.flow.replace_once(body,old,new)


def secondary_snapshot(body,name):
    assert name in ('primaryIndex','current','delta')
    body=previous.previous.flow.replace_once(body,'    if (second != limit) {',
        '    '+name+' = second;\n    if ('+name+' != limit) {')
    return body


def candidates():
    yield 'baseline',BASE
    yield 'lower-after-index',lower_after_index(BASE)
    for kind,after in itertools.product(('u32','s32'),(False,True)):
        yield 'scoped-%s-a%d'%(kind,after),scoped_input(BASE,kind,after)
    for name in ('primaryIndex','current','delta'):
        yield 'secondary-'+name,secondary_snapshot(BASE,name)
    yield 'volatile-second',previous.previous.flow.replace_once(BASE,'s32 second)','volatile s32 second)')
    old='''        delta = actor[0x1FE];
        primaryIndex = first;
        value = (s32)((f32)(u32)delta * scale * D_80097D48);'''
    direct='''        primaryIndex = first;
        value = (s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48);'''
    body=previous.previous.flow.replace_once(BASE,old,direct)
    yield 'direct-input',body
    yield 'direct-input-lower-after',lower_after_index(body)
    late=previous.previous.flow.replace_once(body,'        lower = 40;\n','')
    anchor='        value = (s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48);'
    yield 'direct-lower-after-conversion',previous.previous.flow.replace_once(late,anchor,anchor+'\n        lower = 40;')
    for name in ('primaryIndex','current','delta'):
        yield 'direct-secondary-'+name,secondary_snapshot(body,name)
    yield 'direct-volatile-second',previous.previous.flow.replace_once(body,'s32 second)','volatile s32 second)')
    for operand in ('scale','D_80097D48'):
        expression=anchor.replace(' * '+operand,' * (lower = 40, '+operand+')')
        yield 'bridge-'+operand,previous.previous.flow.replace_once(late,anchor,expression)
    for order in range(3):
        old='''        primaryIndex = first;
        value = (s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48);'''
        capture='        magnitude = (f32)(u32)actor[0x1FE]'+(' * scale;' if order==2 else ';')
        tag='        primaryIndex = first;'
        new='\n'.join(([capture,tag] if order==0 else [tag,capture])+[
            '        lower = 40;',
            '        value = (s32)(magnitude'+('' if order==2 else ' * scale')+' * D_80097D48);'])
        yield 'bridge-magnitude-'+str(order),previous.previous.flow.replace_once(late,old,new)
    for name in ('current','choose','reverse'):
        old='''        delta = actor[0x1FE];
        primaryIndex = first;
        value = (s32)((f32)(u32)delta * scale * D_80097D48);'''
        new='''        %s = actor[0x1FE];
        primaryIndex = first;
        value = (s32)((f32)(u32)%s * scale * D_80097D48);'''%(name,name)
        yield 'numeric-'+name,previous.previous.flow.replace_once(BASE,old,new)


def observations(words,retail):
    values=[]
    for first,second in ((1,2),(255,2)):
        memory,args=recovery.fixture(0,1,first,second)
        for cut in (7,9):
            models=[]
            for code in (retail,words):
                model=previous.previous.faults.InstructionOracle(code,memory,args)
                model.fault=cut
                try:model.run()
                except recovery.stream.AccessFault:assert model.accesses==cut
                else:raise AssertionError('Missing real instruction fault')
                models.append(model)
            values.append(dict(first=first,second=second,cut=cut,
                equal=previous.previous.faults.state(models[0])==previous.previous.faults.state(models[1]),
                GPRs=[i for i in range(32) if models[0].r[i]!=models[1].r[i]],
                words=['%08X'%m.dispatched_word for m in models],
                memory_equal=models[0].memory==models[1].memory,
                events_equal=models[0].events==models[1].events))
    return values


SELECTED_NAME='direct-lower-after-conversion'
SELECTED=dict(candidates())[SELECTED_NAME]


def recovered_owner(source):
    if source.count(BASE)==1:
        return source.replace(BASE,SELECTED,1)
    if source.count(SELECTED)==1:
        return source
    raise ValueError('Expected the banked scalar body or selected input fit')


def fault_sweep(words,retail):
    domains=[(kind,pattern,1,2,phase) for kind,pattern,phase in
        itertools.product((0,0x42,0x69,0x70,0x7C,0x87),(0,1,3),(0,8))]
    domains += [(kind,0,first,second,phase) for kind,first,second,phase in
        itertools.product((0,0x70),(1,255),(2,255),(0,8))]
    cases=[]
    pairs=equal=0
    for kind,pattern,first,second,phase in domains:
        memory,args=recovery.fixture(kind,pattern,first,second)
        complete=[previous.previous.faults.InstructionOracle(code,memory,args,phase,0xFFFFFFFF).run()
            for code in (retail,words)]
        assert complete[0].accesses==complete[1].accesses
        first_difference=None
        equal_cuts=[]
        for cut in range(complete[0].accesses):
            models=[]
            for code in (retail,words):
                model=previous.previous.faults.InstructionOracle(code,memory,args,phase,0xFFFFFFFF)
                model.fault=cut
                try:model.run()
                except recovery.stream.AccessFault:assert model.accesses==cut
                else:raise AssertionError('Missing real instruction fault')
                assert model.dispatched_word>>26 in (32,33,35,36,37,40,41,43,49,57)
                models.append(model)
            same=previous.previous.faults.state(models[0])==previous.previous.faults.state(models[1])
            pairs+=1
            equal+=same
            if same:equal_cuts.append(cut)
            if not same and first_difference is None:
                first_difference=dict(cut=cut,words=['%08X'%m.dispatched_word for m in models],
                    GPRs=[i for i in range(32) if models[0].r[i]!=models[1].r[i]],
                    memory_equal=models[0].memory==models[1].memory,
                    events_equal=models[0].events==models[1].events,
                    FPRs_equal=models[0].f==models[1].f)
        cases.append(dict(kind=kind,pattern=pattern,selectors=[first,second],phase=phase,
            accesses=complete[0].accesses,equal_cuts=equal_cuts,first_difference=first_difference))
    return dict(cases=cases,fired_pairs=pairs,equal_states=equal,
        first_cuts=dict(Counter(case['first_difference']['cut'] for case in cases)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    parser.add_argument('--faults',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-inputs'
    out.mkdir(exist_ok=True)
    retail=list(struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))
    records=[]
    for name,body in candidates():
        if args.filter not in name:continue
        meta,words=previous.previous.flow.roles.fitting.compile_candidate(root,out,name,body)
        meta['observations']=observations(words,retail)
        if args.faults:
            meta['fault_sweep']=fault_sweep(words,retail)
            print('faults',name,meta['fault_sweep']['equal_states'],
                meta['fault_sweep']['first_cuts'],flush=True)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],
            [(x['first'],x['cut'],x['GPRs']) for x in meta['observations']],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
