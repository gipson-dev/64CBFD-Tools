"""Execute ten original caller words, with explicit o32 test trampolines."""
from pathlib import Path
import sys
from tools.experiments import game_projection_record_draw_15035fe8_recovery as source
ROOT=source.ROOT
import json,struct
from tools.tests import game_projection_record_draw_15035fe8_oracle as g
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
OUT=source.OUT;CALLER=0x150197A0

class Connected(TimingOracle):
    def __init__(self,window,callee,memory,c):
        self.c=c;self.trace=[];self.boundaries=[];self.packet=STACK+c.phase-52
        prefix=(0x27BDFFE0,0xAFBF001C,0xAFB00018,0xAFB10014,0x00A08825,0x00801025)
        suffix=(0x02001025,0x8FB10014,0x8FB00018,0x8FBF001C,0x03E00008,0x27BD0020)
        super().__init__(prefix+window+suffix,memory,phase=c.phase,entry=CALLER-24,
                         arguments=(g.cursor(c),c.view),connected={g.ENTRY+4*i:w for i,w in enumerate(callee)})
    def record_call(self,target):
        if target==g.ENTRY:return
        assert target==g.DRAW;args=list(self.arguments(8));assert args[5]==self.packet;args[5]=g.PACKET
        values=tuple(g.read(self.memory,self.packet+i*4)for i in range(4))
        self.trace.append((tuple(args),values,self.memory[g.COUNT]));self.calls.append((target,tuple(args)))
        self.boundaries.append(tuple(self.memory[STACK+self.c.phase-32+i]for i in range(-104,8)))
    hook=g.Oracle.hook

def run():
    rom=(ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>10I',rom,0x46C50)
    assert window[:3]==(0x00402025,0x0D40D7FA,0x02202825)
    assert window[-3:]==(0xAC4B0000,0xAC4A0004,0x24500008)
    assert struct.unpack_from('>I',rom,0x46C54)[0]==0x0D40D7FA
    blob,refs=payload(OUT/'qualified-screen/candidate.o','func_15035FE8');raw=bind(blob,refs);retail=struct.unpack_from('>88I',rom,0x63498)
    cases=calls=0
    for c in list(g.cases(native=True))[:192]:
        if c.view not in(0,3,0xFFFFFFFF):continue
        initial=g.fixture(c);wanted,trace,cursor=g.reference(initial,c,stack_adjust=-32)
        put(wanted,cursor,0xDA380003);put(wanted,cursor+4,0x80089470);models=[]
        for words in(raw,retail):
            model=Connected(window,tuple(words),initial,c).run()
            assert model.trace==trace,(c,'connected calls')
            assert g.public(model.memory)==g.public(wanted),(c,'original post-call matrix stores')
            assert model.r[2]==cursor+8,(c,'consumed cursor')
            models.append(model)
        assert models[0].boundaries==models[1].boundaries and models[0].memory==models[1].memory,(c,'connected complete RAM')
        cases+=1;calls+=len(trace)
    r=dict(cases=cases,logical_draw_calls=calls,actual_original_caller_words=10,synthetic_prefix_words=6,synthetic_suffix_words=6,
           original_JAL_and_delay=True,returned_cursor_consumed_by_original_matrix_stores=True,full_caller_claim=False,matching_credit=0)
    (OUT/'caller.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
