"""Recover burst pointer/flag lifetimes while refusing the remaining object/scratch gap."""
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_transition_frame_lifetimes as previous

BUILD='conker/build/game-transition-pointer-recovery'
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
for key,path,sha in (
    ('burst_frame_screen','tools/experiments/game_transition_frame_lifetimes.py',
     '1b090f7ef7ade1fa315c086e13f22e6a6cb6420ce5cfeb6ff1b9f448a19da240'),
    ('burst_frame_tests','tools/tests/test_game_transition_frame_lifetimes.py',
     '576b56010767a27dd079b26979dc063f759edf0653e776602da328d23b6cb3d5')):
    PATHS[key],BASELINE[key]=path,sha
OWNER,FUNCTION,ENTRY,ROM,SIZE=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.SIZE
build,compile_owner,projection=previous.build,previous.compile_owner,previous.projection
link_raw,padded_object,recovered_owner=previous.link_raw,previous.padded_object,previous.recovered_owner
parse_object=previous.previous.parse_object
require_installable=previous.previous.require_installable
BINDINGS=dict(previous.BINDINGS)
for old,new in ((716,720),(796,800),(816,820)):
    BINDINGS[new]=BINDINGS.pop(old)
RAW_SHA='d33c00e67089d81062e952c8cc23cf779f48ac15ca2b1fee3f63c06018a2df86'
SCRATCH=(189,190,191,192,193,194,197,198,201,208,209)
CANDIDATE=previous.CANDIDATE
for old,new in (
    ('    if (record[0x70] & 1) {\n        transition = (TransitionPayloadFC5F0 *)(record + 0x70);',
     '    transition = (TransitionPayloadFC5F0 *)(record + 0x70);\n    if (transition->state & 1) {'),
    ('                    flag0 = 0;\n                    if (func_150ADA20() & 1) {\n                        flag0 = 2;\n                    }',
     '                    if (func_150ADA20() & 1) {\n                        flag0 = 2;\n                    } else {\n                        flag0 = 0;\n                    }')):
    if CANDIDATE.count(old)!=1: raise ValueError('Unknown burst pointer predecessor')
    CANDIDATE=CANDIDATE.replace(old,new,1)


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):
        previous.freeze(root,out)


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown pointer-recovered words/bindings')


def differences(truth,words):
    if len(truth)!=251 or len(words)!=251: raise ValueError('Unknown burst extent')
    changes=[i for i,(a,b) in enumerate(zip(truth,words)) if a!=b]
    shifted=[i for i in changes if i not in SCRATCH]
    if len(changes)!=47 or len(shifted)!=36 or any(
            (truth[i]&0xFFFF0000)!=(words[i]&0xFFFF0000) or
            (words[i]&65535)-(truth[i]&65535)!=4 or
            (truth[i]>>21)&31!=29 for i in shifted):
        raise ValueError('Unknown pointer-recovered difference classes')
    if set(changes)!=set(shifted)|set(SCRATCH) or truth[:47]!=words[:47] or truth[210:]!=words[210:]:
        raise ValueError('Burst pointer/flag prefix or tail regressed')
    return dict(pure_stack_shift_words=shifted,scratch_role_words=list(SCRATCH),mixed_stack_and_scratch_word=192,
        exact_prefix_words=47,exact_tail_words=41,descriptor=0xB0,payload=0xA0,
        retail_descriptor=0xAC,retail_payload=0x9C)


def qualify(root,out):
    freeze(root,out)
    with patch.multiple(previous.previous,PATHS=PATHS,BASELINE=BASELINE):
        obj,padded,images,row=previous.previous.qualify(root,out,CANDIDATE)
    raw,functions,relocs=parse_object(obj); f=functions[FUNCTION]
    checked_parts(raw[f['value']:f['value']+f['size']],
        {a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']})
    if (row['words'],row['frame'],row['differing_words'])!=(251,264,47):
        raise ValueError('Unknown pointer-recovered shape')
    truth=list(struct.unpack_from('>251I',(out/'before-retail_rom').read_bytes(),ROM))
    row.update(differences(truth,images[0]))
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


def capture(root,out,label,body=CANDIDATE):
    freeze(root,out)
    return previous.capture(root,out,label,body)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
