"""Recover the real burst frame without claiming the remaining words match."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_transition_completion_burst as previous
from tools.experiments import game_text_measurer_frontend_trace as front

BUILD = 'conker/build/game-transition-frame-recovery'
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
EXTRA = {
    'burst_predecessor_screen': ('tools/experiments/game_transition_completion_burst.py', '785c00d6c82485571e8d0afe8a40e0ac771b620b55576de74f2fed4cd61702cf'),
    'burst_predecessor_oracle': ('tools/tests/game_transition_completion_oracle.py', '7322d7bfecd382210bdd8cb3ed7d0a405a1b3294077823e8ab73ba948ada207d'),
    'burst_predecessor_tests': ('tools/tests/test_game_transition_completion_burst.py', '73b1d6860a9105e4116b46fb2c05690706b6b423b9e87a96af0f0615e76a3e0a'),
    'burst_frontend_capture': ('tools/experiments/game_text_measurer_frontend_trace.py', '2f0e95ee88ab412e34743261f9f13b678c8ea9054277fa3bb23e3177789dbe94'),
    'burst_ugen_capture': ('tools/experiments/game_text_measurer_ugen_nodes.py', 'afb7dae1d47e87f7a2b86c1a6eabf852aa47444bf103d3adfbc17911ca2cdd6b'),
}
for key,(path,sha) in EXTRA.items():
    PATHS[key],BASELINE[key] = path,sha
OWNER, FUNCTION, ENTRY, ROM, SIZE = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.SIZE
build, compile_owner, projection = previous.build, previous.compile_owner, previous.projection
link_raw, padded_object, recovered_owner = previous.link_raw, previous.padded_object, previous.recovered_owner
BINDINGS = previous.BINDINGS
RAW_SHA = '2f9a5a88cf77008fb30b41025da490690fe3b135b3e9e761a8b41c8fae9d421b'
CANDIDATE = previous.CANDIDATE
for old,new in (
    ('    f32 scale;\n', ''),
    ('    s32 flag0, flag1;', '    u8 flag0;\n    s32 flag1;'),
    ('                const f32 twoAndHalf = 2.5f;\n                const f32 two = 2.0f;',
     '                /* Reuse the completed-progress temporary as the child speed range. */\n                progress = 2.0f;'),
    ('func_150ADA68() * two + twoAndHalf', 'func_150ADA68() * progress + 2.5f'),
    ('                    scale = func_150ADA68() * 1.789999962f + 1.699999928f;\n'
     '                    descriptor.scale[0] = scale;\n                    descriptor.scale[1] = scale;',
     '                    descriptor.scale[1] = descriptor.scale[0] = func_150ADA68() * 1.789999962f + 1.699999928f;')):
    if CANDIDATE.count(old) != 1:
        raise ValueError('Unknown burst lifetime predecessor')
    CANDIDATE = CANDIDATE.replace(old,new,1)


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):
        previous.freeze(root,out)


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown recovered-frame words/bindings')


def qualify(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):
        obj,padded,images,row = previous.qualify(root,out,CANDIDATE)
    data,functions,relocs = previous.parse_object(obj)
    f=functions[FUNCTION]
    checked_parts(data[f['value']:f['value']+f['size']],
        {a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']})
    if (row['words'],row['frame'],row['differing_words'])!=(251,264,91):
        raise ValueError('Unknown recovered-frame shape')
    return obj,padded,images,row


def capture(root,out,label,body):
    freeze(root,out)
    def compile_candidate(root,work,name,body):
        obj,diag=compile_owner(root,work,recovered_owner((out/'before-tile_owner').read_text(),body),name)
        if diag: raise ValueError(diag)
        data,functions,_=previous.parse_object(obj); f=functions[FUNCTION]
        raw=data[f['value']:f['value']+f['size']]
        return dict(words=len(raw)//4,frame=(-struct.unpack_from('>I',raw)[0])&65535,
            target_sha256=hashlib.sha256(raw).hexdigest()),obj
    screen=SimpleNamespace(compile_candidate=compile_candidate,PROFILES={'owner':('-O2','-g3')},
        compiler=SimpleNamespace(parse_object=previous.parse_object,sections=projection.sections))
    with patch.object(front.trace,'screen',screen):
        return front.capture_frontend(root,out,'capture-'+label,body)


def procedure(records):
    # The unchanged whole owner has six definitions before this target.
    starts=[i for i,row in enumerate(records) if row['name']=='ent']
    if len(starts)!=25:
        raise ValueError('Unknown burst owner procedure inventory')
    selected=[]
    for row in records[starts[6]:]:
        selected.append(row)
        if row['name']=='end': return selected
    raise ValueError('Unterminated burst procedure')


def homes(record):
    rows=procedure(record['records'])
    definitions=[row['length'] for row in rows if row['name']=='def' and row['storage']=='M']
    if len(definitions)!=1:
        raise ValueError('Unknown burst automatic storage declaration')
    return dict(automatic_bytes=definitions[0],
        vregs=[(row['dtype'],row['offset'],row['length'],row['level']) for row in rows if row['name']=='vreg'],
        offsets=sorted({row['offset'] for row in rows if row['storage']=='M' and row['offset'] is not None}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',action='store_true'); args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]; out=root/BUILD
    if args.capture:
        result={name:homes(capture(root,out,name,body)) for name,body in
            (('before',previous.CANDIDATE),('selected',CANDIDATE))}
        print(json.dumps(result,indent=2),flush=True)
    else:
        print(json.dumps(qualify(root,out)[-1],indent=2),flush=True)
