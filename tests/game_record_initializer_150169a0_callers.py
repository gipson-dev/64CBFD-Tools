"""Authentic category-load delay slot and direct parent call, privately."""
import itertools,json,struct
from tools.tests import game_record_initializer_150169a0_oracle as g
from tools.tests import game_record_initializer_150169a0_return as return_use
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START,END,ROM=0x15007ed0,0x15007ed8,0x35380

def aligned(rom,value):
    needle=struct.pack('>I',value);p=-1;answer=[]
    while True:
        p=rom.find(needle,p+1)
        if p<0:return answer
        if p%4==0:answer.append(p)

def main():
    rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();jal=0xc000000|((g.source.ENTRY>>2)&0x3ffffff)
    assert aligned(rom,jal)==[ROM] and aligned(rom,g.source.ENTRY)==[]
    words=struct.unpack_from('>2I',rom,ROM);assert words==(jal,0x8c84e9f0)
    return_use.prove(rom)
    count=0
    for scene,selector,mode,phase in itertools.product((0,26,36,54),(0,8,37),(0,10),(0,8)):
        c=g.Case(category=scene,scene=scene,selected=selector,players=2,mode=mode,phase=phase)
        for code,pool,entry in g.source.programs():
            initial=g.fixture(c);want,calls,obs=g.reference(initial,c)
            initial.update({g.source.POOL+i:b for i,b in enumerate(pool)})
            connected=dict(zip(range(entry,entry+len(code)*4,4),code));connected[END]=0
            window=(0xc000000|((entry>>2)&0x3ffffff),words[1])
            m=g.Oracle(window,initial,c,entry=START,connected=connected);m.r[4]=0x800c0000
            saved=(m.r[16:24],m.r[29],m.f[20:]);m.code=WindowCode(m.code,m);m.code.ends=(END,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing authentic caller boundary')
            assert g.public(m.memory)==g.public(want) and m.calls==calls and m.init_observations==obs,c
            assert(m.r[16:24],m.r[29],m.f[20:])==saved
        count+=1
    report=dict(direct_sites=1,literal_pointers=0,caller_cases=count,streams=2,original_window_words=2,category_delay_load=True,raw_callee_named_relocation=g.source.RAW_ENTRY,result_ignored_proven=True,complete_caller_unqualified=True,uncredited=True)
    (g.source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
