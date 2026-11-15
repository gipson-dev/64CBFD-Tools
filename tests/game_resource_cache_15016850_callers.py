"""The authentic caller's two-word JAL window; full parent remains unqualified."""
import itertools,json,struct
from tools.tests import game_resource_cache_15016850_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def main():
    rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0xc000000|((g.source.ENTRY>>2)&0x3ffffff)
    assert[i*4 for i,w in enumerate(allwords)if w==jal]==[0x4451c]and not[i for i,w in enumerate(allwords)if w==g.source.ENTRY]
    start,end=0x1501706c,0x15017074;window=struct.unpack_from('>2I',rom,0x4451c);assert window==(jal,0)
    programs=[g.source.bound(*payload(g.source.OUT/n,g.source.NAME))for n in('retail.o','selected.o')];count=0
    for response,mode,phase in itertools.product((0,2),range(16),(0,8)):
        initial,args=g.fixture((1,187,2),response,mode,phase);want,calls,obs=g.model(initial,args)
        for words in programs:
            code=dict(zip(range(g.source.ENTRY,g.source.ENTRY+len(words)*4,4),words));code[end]=0
            m=g.Oracle(window,initial,args,entry=start,connected=code);saved=m.r[16:24];stack=m.r[29];fp=m.f[20:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original caller boundary')
            assert(g.public(m.memory),m.calls,m.cache_observations)==(g.public(want),calls,obs)
            assert(m.r[16:24],m.r[29],m.f[20:])==(saved,stack,fp)
        count+=1
    report=dict(direct_sites=1,caller_cases=count,streams=2,original_window_words=2,literal_pointer_count=0,complete_parent_or_return_contract_claimed=False,private=True)
    (g.source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
