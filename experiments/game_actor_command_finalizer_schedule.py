"""Screen literal finalizer scheduling with the existing ABI and compiler profile."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_inputs as previous

BASE=previous.SELECTED
replace_once=previous.previous.previous.flow.replace_once


def jitter_order(body):
    return replace_once(body,'*(s8 *)(actor + 0x202) * actor[0x1FE]',
        'actor[0x1FE] * *(s8 *)(actor + 0x202)')


def timer_order(body):
    return replace_once(body,'actor[0x200] >= D_800BE9E4','D_800BE9E4 <= actor[0x200]')


def early_lower(body):
    body=replace_once(body,'        lower = 40;\n','')
    anchor='        primaryIndex = first;\n        value = (s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48);'
    return replace_once(body,anchor,'        lower = 40;\n'+anchor)


def branch_lower(body,after=False):
    body=replace_once(body,'        lower = 40;\n','')
    for assignment in ('scale = D_80097D40;',
            'scale = (f32)(u32)actor[0x201] * D_80097D44;'):
        old='            '+assignment
        new=(old+'\n            lower = 40;' if after else
            '            lower = 40;\n'+old)
        body=replace_once(body,old,new)
    return body


def candidates():
    for jitter,timer in itertools.product((False,True),repeat=2):
        body=BASE
        if jitter:body=jitter_order(body)
        if timer:body=timer_order(body)
        prefix='j%d-t%d'%(jitter,timer)
        yield prefix+'-late',body
        yield prefix+'-early',early_lower(body)
        for after in (False,True):
            yield prefix+'-branches-'+str(int(after)),branch_lower(body,after)
        for early in (False,True):
            source=early_lower(body) if early else body
            for declaration in ('u32 lower;','register s32 lower;'):
                name=declaration.split()[0]
                yield prefix+'-'+name+'-'+str(int(early)),replace_once(source,'s32 lower;',declaration)
    for early in (False,True):
        body=jitter_order(early_lower(BASE) if early else BASE)
        for old,new in (
                ('s32 primaryIndex;','u32 primaryIndex;'),
                ('s32 primaryIndex;','register s32 primaryIndex;'),
                ('f32 scale;','register f32 scale;'),
                ('f32 magnitude;','register f32 magnitude;'),
                ('s16 value =','register s16 value ='),
                ('s32 limit;','register s32 limit;'),
                ('s32 delta;','register s32 delta;'),
                ('s32 first,','register s32 first,')):
            name=new.split()[1] if new.startswith('register') else 'unsigned-index'
            if new.startswith('register'):name+='-'+new.split()[2].rstrip(';=,')
            yield 'hint-'+name+'-'+str(int(early)),replace_once(body,old,new)
    for name in ('delta','current'):
        for inline in (False,True):
            if inline:
                body=replace_once(BASE,'actor[0x1FE] / limit)',
                    '('+name+' = actor[0x1FE]) / limit)')
            else:
                anchor='        value = (s32)((f32)(*(s8 *)(actor + 0x202) * actor[0x1FE] / limit)'
                replacement='        '+name+' = actor[0x1FE];\n'+anchor.replace('actor[0x1FE]',name)
                body=replace_once(BASE,anchor,replacement)
            yield 'product-'+name+'-'+str(int(inline)),body


SELECTED_NAME='j1-t0-late'
SELECTED=dict(candidates())[SELECTED_NAME]


def recovered_owner(source):
    if source.count(BASE)==1:
        return source.replace(BASE,SELECTED,1)
    if source.count(SELECTED)==1:
        return source
    raise ValueError('Expected the banked direct-input body or selected schedule fit')


def fault_probes(words,retail):
    records=[]
    recovery=previous.recovery
    for first,second in ((1,2),(255,2)):
        memory,args=recovery.fixture(0,1,first,second)
        for cut in (7,9,10,17,18):
            models=[]
            for code in (retail,words):
                model=previous.previous.previous.faults.InstructionOracle(code,memory,args)
                model.fault=cut
                try:model.run()
                except recovery.stream.AccessFault:assert model.accesses==cut
                else:raise AssertionError('Missing real instruction fault')
                models.append(model)
            records.append(dict(first=first,cut=cut,
                equal=previous.previous.previous.faults.state(models[0])==
                    previous.previous.previous.faults.state(models[1]),
                GPRs=[i for i in range(32) if models[0].r[i]!=models[1].r[i]],
                FPRs=[i for i in range(32) if models[0].f[i]!=models[1].f[i]],
                words=['%08X'%m.dispatched_word for m in models],
                memory_equal=models[0].memory==models[1].memory,
                events_equal=models[0].events==models[1].events))
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    parser.add_argument('--faults',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-schedule'
    out.mkdir(exist_ok=True)
    retail=list(struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),
        previous.recovery.screen.ROM))
    records=[]
    compiler=previous.previous.previous.flow.roles.fitting.compile_candidate
    for name,body in candidates():
        if args.filter not in name:continue
        meta,words=compiler(root,out,name,body)
        meta['body_sha256']=hashlib.sha256(struct.pack('>%dI'%len(words),*words)).hexdigest()
        meta['probes']=fault_probes(words,retail)
        if args.faults:meta['fault_sweep']=previous.fault_sweep(words,retail)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],
            [(r['first'],r['cut'],r['GPRs'],r['FPRs']) for r in meta['probes'][:3]+meta['probes'][5:6]],
            meta.get('fault_sweep',{}).get('first_cuts'),flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
