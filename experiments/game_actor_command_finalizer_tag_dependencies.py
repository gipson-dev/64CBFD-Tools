"""Fit genuine tag arithmetic dependencies without changing the caller ABI."""
import argparse
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_schedule as previous

BASE=previous.SELECTED
replace_once=previous.replace_once


def tag_arithmetic(body,complete=False,both=False,before_scale=False):
    setter='        primaryIndex = first;'
    assert body.count(setter)==2
    biases=('primaryBias','secondaryBias') if both else ('primaryBias',)
    for index,bias in enumerate(biases):
        expression='(u32)first * 6'+(' + '+bias if complete else '')
        new='        primaryIndex = '+expression+';'
        if index==0:
            body=body.replace(setter,new,1)
        else:
            body=replace_once(body,setter,new)
        old='(u32)primaryIndex * 6 + '+bias
        body=replace_once(body,old,'primaryIndex' if complete else '(u32)primaryIndex + '+bias)
    if before_scale:
        first='        primaryIndex = (u32)first * 6'+(' + primaryBias' if complete else '')+';'
        assert first+'\n' in body
        body=body.replace(first+'\n','',1)
        body=replace_once(body,'    if (first != limit) {','    if (first != limit) {\n'+first)
    return body


def candidates():
    for early in (False,True):
        base=previous.early_lower(BASE) if early else BASE
        yield 'baseline-'+str(int(early)),base
        for complete,both,before in itertools.product((False,True),repeat=3):
            yield 'tag-c%d-b%d-s%d-e%d'%(complete,both,before,early),tag_arithmetic(base,complete,both,before)


def advised_placements():
    early=previous.early_lower(BASE)
    a=replace_once(early,'        lower = 40;\n','')
    setter='        primaryIndex = first;'
    assert a.count(setter)==2
    yield 'advised-after-tag',a.replace(setter,setter+'\n        lower = 40;',1)
    yield 'advised-before-tag',early


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    parser.add_argument('--advised',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-tag-dependencies'
    out.mkdir(exist_ok=True)
    retail=list(struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),
        previous.previous.recovery.screen.ROM))
    compiler=previous.previous.previous.previous.flow.roles.fitting.compile_candidate
    records=[]
    for name,body in (advised_placements() if args.advised else candidates()):
        if args.filter not in name:continue
        meta,words=compiler(root,out,name,body)
        meta['probes']=previous.fault_probes(words,retail)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],
            [(r['first'],r['cut'],r['GPRs'],r['FPRs']) for r in meta['probes'][:3]+meta['probes'][5:6]],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
