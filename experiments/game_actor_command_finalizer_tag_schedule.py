"""Fit tag-home and lower-bound placement at the qualified backend boundary."""
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_command_finalizer_schedule as previous

BASE=previous.SELECTED
replace_once=previous.replace_once
ANCHOR='        value = (s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48);'


def first_tag(body,replacement):
    old='        primaryIndex = first;'
    assert body.count(old)==2
    return body.replace(old,replacement,1)


def candidates():
    for early in (False,True):
        body=previous.early_lower(BASE) if early else BASE
        yield 'baseline-'+str(int(early)),body
        for volatile in (False,True):
            tag='*(volatile s32 *)&first' if volatile else 'first'
            if volatile:
                yield 'volatile-'+str(int(early)),first_tag(body,'        primaryIndex = '+tag+';')
            source=first_tag(body,'')
            new=ANCHOR.replace('actor[0x1FE]','(primaryIndex = '+tag+', actor[0x1FE])')
            yield 'inline-tag-v%d-e%d'%(volatile,early),replace_once(source,ANCHOR,new)
            new=ANCHOR.replace('D_80097D48','(primaryIndex = '+tag+', D_80097D48)')
            yield 'inline-constant-v%d-e%d'%(volatile,early),replace_once(source,ANCHOR,new)
    source=first_tag(BASE,'')
    source=replace_once(source,'        lower = 40;\n','')
    for assignments in ('primaryIndex = first, lower = 40','lower = 40, primaryIndex = first'):
        new=ANCHOR.replace('actor[0x1FE]','('+assignments+', actor[0x1FE])')
        yield 'joined-'+str(assignments.startswith('lower')),replace_once(source,ANCHOR,new)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-tag-schedule'
    out.mkdir(exist_ok=True)
    retail=list(struct.unpack_from('>405I',(root/'conker/conker.us.bin').read_bytes(),
        previous.previous.recovery.screen.ROM))
    compiler=previous.previous.previous.previous.flow.roles.fitting.compile_candidate
    records=[]
    for name,body in candidates():
        if args.filter not in name:continue
        meta,words=compiler(root,out,name,body)
        meta['probes']=previous.fault_probes(words,retail)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],
            [(r['first'],r['cut'],r['GPRs'],r['FPRs']) for r in meta['probes'][:3]+meta['probes'][5:6]],flush=True)
    (out/('measurements-'+(args.filter or 'all')+'.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
