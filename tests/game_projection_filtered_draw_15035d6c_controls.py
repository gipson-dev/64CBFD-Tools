from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields
from tools.tests.game_projection_filtered_draw_15035d6c_proof import prove
OUT=source.OUT
def run():
    blob,refs=payload(OUT/'qualified-screen/candidate.o','func_15035D6C');raw=list(bind(blob,refs))
    retail=struct.unpack_from('>159I',(ROOT/'conker/conker.us.bin').read_bytes(),0x6321C)
    changes={'render-mode-byte':(0x90d9000b,-1),'record-alpha-byte':(0x90d80004,1),
        'next-record-stride':(0x24c6000c,4),'wrong-shift-mask':(0x304f001f,-24),
        'blue-home':(0x8fa80030,-4),'env-opcode':(0x3c0cfb00,0x100),
        'count-reload-address':(0x90423f00,4),'saved-S6-home':(0xafb6001c,-4)}
    rejected={}
    for name,(word,delta)in changes.items():
        assert word in raw,(name,hex(word));changed=[w+delta if w==word else w for w in raw]
        try:prove(changed,retail)
        except AssertionError as error:
            message=str(error);assert not any(s in message for s in('unsupported','unbounded','escaped code')),message
            rejected[name]=message
        else:raise AssertionError('Ineffective control: '+name)
    alternate=[]
    for w in raw:
        changed=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in(14,15):changed=(changed&~(31<<shift))|((29-reg)<<shift)
        alternate.append(changed)
    assert alternate!=raw;positive=prove(alternate,retail)
    r=dict(effective_controls=len(rejected),rejected=rejected,positive_T6_T7_reallocation=True,
        positive_paths=positive['paths'],matching_credit=0)
    (OUT/'proof-controls.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

    return r
