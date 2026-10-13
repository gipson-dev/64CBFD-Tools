"""Test opening allocation with real type promotions and selector qualifiers."""
import argparse
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_flow as flow
from tools.tests import test_game_actor_command_finalizer_flow as faults

BASE=flow.BASE


def ordinary(body):
    return flow.replace_once(body,'volatile s32 first,','s32 first,')


def wide_value(body):
    body=flow.replace_once(body,'    s16 value = actor[4];','    s32 value = actor[4];')
    assert body.count('value = (s32)((f32)')==2
    body=body.replace('value = (s32)((f32)','value = (s16)(s32)((f32)')
    body=flow.replace_once(body,'        value = actor[0x1FE] + *(s8 *)(actor + 0x203);',
        '        value = (s16)(actor[0x1FE] + *(s8 *)(actor + 0x203));')
    return body


def category_bound(body,reverse=False,late=False):
    body=flow.replace_once(body,'    if (value == 0x70)',
        '    lower = 0x7C;\n    if (value == 0x70)')
    head,tail=body.split('    limit = 0xFF;',1)
    head=flow.replace_once(head,'value == 0x7C','lower == value' if reverse else 'value == lower')
    head=flow.replace_once(head,'delta == 0x7C','delta == lower')
    body=head+'    limit = 0xFF;'+tail
    if late:
        body=flow.replace_once(body,'    lower = 40;\n','')
        body=flow.replace_once(body,'        current = actor[0x1FE];',
            '        lower = 40;\n        current = actor[0x1FE];')
    return body


def split_noise(body,all_cases=False):
    old='''    if ((delta = value) == 0x69 || delta == 0x7C || delta == 0x87) {
        noise = 0;
    } else {
        noise = 10;
    }'''
    if all_cases:
        new='''    if ((delta = value) == 0x69) {
        noise = 0;
    } else if (delta == 0x7C) {
        noise = 0;
    } else if (delta == 0x87) {
        noise = 0;
    } else {
        noise = 10;
    }'''
    else:
        new='''    if ((delta = value) == 0x69 || delta == 0x7C) {
        noise = 0;
    } else {
        if (delta == 0x87) {
            noise = 0;
        } else {
            noise = 10;
        }
    }'''
    return flow.replace_once(body,old,new)


def reorder_noise(body):
    first=body.index('    if (value == 0x7C)')
    second=body.index('    if ((delta = value) == 0x69')
    end=body.index('    limit = 0xFF;')
    return body[:first]+body[second:end]+body[first:second]+body[end:]


def candidates():
    yield 'baseline',BASE
    for qualified,wide,numeric in itertools.product((True,False),(False,True),('current','delta','value')):
        body=BASE if qualified else ordinary(BASE)
        body=flow.numeric(body,numeric)
        if wide:body=wide_value(body)
        yield 'q%d-w%d-n%s'%(qualified,wide,numeric),body
    for name,placement in itertools.product(('current','delta'),range(3)):
        yield 'ordinary-noise-%s-p%d'%(name,placement),ordinary(flow.promoted_noise(BASE,name,placement))
    for wide,where in itertools.product((False,True),('numeric','index','conversion')):
        body=ordinary(BASE)
        if wide:body=wide_value(body)
        body=flow.replace_once(body,'    lower = 40;\n','')
        markers={'numeric':'        current = actor[0x1FE];','index':'        primaryIndex = first;',
            'conversion':'        value = (s16)(s32)((f32)(u32)current' if wide else
                '        value = (s32)((f32)(u32)current'}
        marker=markers[where]
        if where=='index':
            assert body.count(marker)==2
            body=body.replace(marker,'        lower = 40;\n'+marker,1)
        else:
            body=flow.replace_once(body,marker,'        lower = 40;\n'+marker)
        yield 'ordinary-w%d-lower-%s'%(wide,where),body
    for qualified,reverse,late in itertools.product((True,False),(False,True),(False,True)):
        body=BASE if qualified else ordinary(BASE)
        yield 'bound-q%d-r%d-l%d'%(qualified,reverse,late),category_bound(body,reverse,late)
    for qualified in (True,False):
        body=BASE if qualified else ordinary(BASE)
        yield 'advisory-cast-q%d'%qualified,flow.replace_once(body,'delta = value','delta = (s16)value')
        yield 'advisory-order-q%d'%qualified,reorder_noise(body)
        for all_cases in (False,True):
            yield 'split-q%d-all%d'%(qualified,all_cases),split_noise(body,all_cases)
    for bound,forward in itertools.product((False,True),repeat=2):
        body=reorder_noise(BASE)
        if bound:body=flow.bounds(body)
        if forward:body=flow.clamp(body)
        yield 'order-b%d-c%d'%(bound,forward),body
    for numeric,late in itertools.product(('current','delta'),(False,True)):
        body=flow.numeric(ordinary(BASE),numeric)
        body=split_noise(body)
        if late:
            body=flow.replace_once(body,'    lower = 40;\n','')
            marker='        '+numeric+' = actor[0x1FE];'
            body=flow.replace_once(body,marker,'        lower = 40;\n'+marker)
            body=flow.bounds(body)
        yield 'nested-n%s-l%d'%(numeric,late),body


SELECTED_NAME='nested-ndelta-l1'
SELECTED=dict(candidates())[SELECTED_NAME]


def recovered_owner(source):
    if source.count(BASE)==1:
        return source.replace(BASE,SELECTED,1)
    if source.count(SELECTED)==1:
        return source
    raise ValueError('Expected the banked role-fit body or selected opening body')


def opening(words,retail):
    memory,args=faults.recovery.fixture(0,1)
    equal=[]
    result={}
    for cut in range(6):
        pair=[]
        for code in (retail,words):
            model=faults.InstructionOracle(code,memory,args)
            model.fault=cut
            try:model.run()
            except faults.recovery.stream.AccessFault:
                assert model.accesses==cut
            else:raise AssertionError('Expected real instruction fault')
            pair.append(model)
        same=faults.state(pair[0])==faults.state(pair[1])
        equal.append(same)
        if cut==5:
            result=dict(cut5_GPRs=[i for i in range(32) if pair[0].r[i]!=pair[1].r[i]],
                cut5_words=['%08X'%m.dispatched_word for m in pair],
                cut5_word_indices=[i for i,w in enumerate(words) if w==pair[1].dispatched_word],
                retail_selector_load_indices=[i for i,w in enumerate(words) if w==0x8FAE0050],
                memory_equal=pair[0].memory==pair[1].memory,events_equal=pair[0].events==pair[1].events,
                FPRs_equal=pair[0].f==pair[1].f,RA_equal=pair[0].r[31]==pair[1].r[31])
    return dict(equal_cuts=equal,**result)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-opening'
    out.mkdir(exist_ok=True)
    retail=list(struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),flow.roles.fitting.recovery.ROM))
    records=[]
    for name,body in candidates():
        if args.filter not in name:continue
        record,words=flow.roles.fitting.compile_candidate(root,out,name,body)
        record['opening']=opening(words,retail)
        records.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],
            record['opening']['cut5_GPRs'],record['opening']['retail_selector_load_indices'],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
