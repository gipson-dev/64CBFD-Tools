"""Execute the original eight-word call window inside explicit o32 scaffolding."""
from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
import json,struct
from tools.tests import game_projection_filtered_draw_15035d6c_oracle as g
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
OUT=source.OUT;WINDOW=0x150318A0

class Connected(TimingOracle):
    def __init__(self,window,callee,memory,c):
        self.c=c;self.observed=[]
        prefix=(0x27BDFEE8,0xAFBF0114,0xAFB00110,0xAFB1010C,0x00808025,0x00A08825,
            0xAFA600EC,0xAFA700E8,0x8FAE0128,0xAFAE00E4)
        suffix=(0x02001025,0x8FB1010C,0x8FB00110,0x8FBF0114,0x03E00008,0x27BD0118)
        super().__init__(prefix+window+suffix,memory,phase=c.phase,entry=WINDOW-4*len(prefix),
            arguments=(g.cursor(c),g.DESC,c.red,c.green,c.blue),
            connected={g.ENTRY+4*i:w for i,w in enumerate(callee)})
    def record_call(self,target):
        assert target==g.ENTRY
        args=self.arguments(5);self.observed.append(tuple(args))
    def hook(self,target):raise AssertionError(('unexpected external helper',target))

def run():
    rom=(ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>8I',rom,0x5ED50)
    assert window==(0x8FAE00E4,0x02002025,0x02202825,0x8FA600EC,0x8FA700E8,0x0D40D75B,0xAFAE0010,0x00408025),window
    blob,refs=payload(OUT/'qualified-screen/candidate.o','func_15035D6C');raw=bind(blob,refs);retail=struct.unpack_from('>159I',rom,0x6321C)
    count=0
    for c in list(g.cases(native=True))[:128]:
        initial=g.fixture(c);wanted,trace,cursor=g.reference(initial,c);models=[]
        for words in(raw,retail):
            model=Connected(window,tuple(words),initial,c).run()
            assert model.observed==[(g.cursor(c),g.DESC,c.red,c.green,c.blue)],(c,'all five actual arguments')
            writes=[v for v in model.events if v[0]=='W'and not STACK-512<=v[1]<STACK+1024]
            assert writes==trace and g.public(model.memory)==g.public(wanted),(c,'connected complete public memory')
            assert model.r[2]==cursor,(c,'original returned cursor consumption')
            models.append(model)
        assert models[0].memory==models[1].memory,(c,'connected complete guest RAM')
        count+=1
    r=dict(cases=count,actual_original_caller_words=8,synthetic_prefix_words=10,synthetic_suffix_words=6,
        original_JAL_and_blue_delay_store=True,returned_cursor_consumed_by_original_S0_move=True,
        full_caller_claim=False,caller_C_body_still_unrecovered=True,matching_credit=0)
    (OUT/'caller.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
