"""Fit early selector snapshots and retail bound/clamp control flow."""
import argparse
import itertools
import json
from pathlib import Path

from tools.experiments import game_actor_command_finalizer_roles as roles

BASE=roles.SELECTED


def replace_once(body,old,new):
    assert body.count(old)==1,(old,body.count(old))
    return body.replace(old,new,1)


def early_gate(body,name='primaryIndex',where='type'):
    assert name in ('primaryIndex','current')
    if where=='type':
        marker='    if (value == 0x70)'
    elif where=='noise':
        marker='    if ((delta = value) == 0x69'
    else:
        assert where=='gate'
        marker='    limit = 0xFF;'
    body=replace_once(body,marker,'    '+name+' = first;\n'+marker)
    return replace_once(body,'    if (first != limit)','    if ('+name+' != limit)')


def bounds(body):
    return replace_once(body,'''        if (actor[4] == 0x42) {
            lower = 80;
            upper = 120;
        } else {
            upper = 60;
        }''','''        upper = 60;
        if (actor[4] == 0x42) {
            lower = 80;
            upper = 120;
        }''')


def clamp(body):
    return replace_once(body,'''            current = value < 256 ? value : limit;
            value = current;''','''            current = value;
            if (value >= 256) {
                current = limit;
            }
            value = current;''')


def invert_suppression(body):
    return replace_once(body,'''    if (value == 0x70) {
        suppressed = 1;
    } else {
        suppressed = 0;
    }''','''    if (value != 0x70) {
        suppressed = 0;
    } else {
        suppressed = 1;
    }''')


def numeric(body,name,inline=False):
    old='''        current = actor[0x1FE];
        primaryIndex = first;
        value = (s32)((f32)(u32)current * scale * D_80097D48);'''
    assert name in ('current','delta','value')
    if inline:
        new='''        primaryIndex = first;
        value = (s32)((f32)(u32)(%s = actor[0x1FE]) * scale * D_80097D48);'''%name
    else:
        new='''        %s = actor[0x1FE];
        primaryIndex = first;
        value = (s32)((f32)(u32)%s * scale * D_80097D48);'''%(name,name)
    return replace_once(body,old,new)


def promoted_noise(body,name,placement):
    old='(delta = value) == 0x69 || delta == 0x7C || delta == 0x87'
    choices=(
        'value == 0x69 || (%s = value) == 0x7C || %s == 0x87',
        '(%s = value) == 0x69 || value == 0x7C || %s == 0x87',
        'value == 0x69 || (%s = value) == 0x7C || value == 0x87')
    template=choices[placement]
    return replace_once(body,old,template%((name,name) if template.count('%s')==2 else name))


def candidates():
    yield 'baseline',BASE
    yield 'bounds',bounds(BASE)
    yield 'clamp',clamp(BASE)
    yield 'inverted-suppression',invert_suppression(BASE)
    for name,where in itertools.product(('primaryIndex','current'),('type','noise','gate')):
        body=early_gate(BASE,name,where)
        for bound,forward in itertools.product((False,True),repeat=2):
            form=body
            if bound:form=bounds(form)
            if forward:form=clamp(form)
            yield 'gate-%s-%s-b%d-c%d'%(name,where,bound,forward),form
    for name,inline,bound in itertools.product(('current','delta','value'),(False,True),(False,True)):
        body=numeric(BASE,name,inline)
        if bound:body=bounds(body)
        yield 'numeric-%s-i%d-b%d'%(name,inline,bound),body
    for name,placement in itertools.product(('current','delta'),range(3)):
        yield 'noise-%s-p%d'%(name,placement),promoted_noise(BASE,name,placement)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-flow'
    out.mkdir(exist_ok=True)
    records=[]
    for name,body in candidates():
        if args.filter not in name:continue
        record,_=roles.fitting.compile_candidate(root,out,name,body)
        records.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
