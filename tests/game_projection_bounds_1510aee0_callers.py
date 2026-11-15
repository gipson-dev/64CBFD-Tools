"""The four original projection call windows and complete ten-word packets."""
import itertools,json,struct
from tools.tests import game_projection_bounds_1510aee0_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def main():
    rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();programs=[g.source.bound(*payload(g.source.OUT/n,g.source.NAME))for n in('retail.o','selected.o','guarded.o')];count=0
    class CallerOracle(g.Oracle):
        def record_call(self,t):assert t==g.source.ENTRY and tuple(self.arguments(10))==tuple(self.expected_args)
    for pc in(0x151767cc,0x15176830,0x15177138,0x1517a448):
        window=struct.unpack_from('>2I',rom,pc-0x15000000+0x2d4b0);assert window[0]==0xc000000|((g.source.ENTRY>>2)&0x3ffffff)
        delay=window[1];assert delay>>26==57 and delay>>21&31==29 and delay&65535==28;freg=delay>>16&31
        for x,y,z,output,phase in itertools.product((0.,2.),(0.,-2.),(-4.,1.),(0,1,3,4),(0,8)):
            initial,args=g.fixture(x,y,z,output,phase=phase);answer,want,_=g.model(initial,args,phase)
            for w in programs:
                end=pc+8;code=dict(zip(range(g.source.ENTRY,g.source.ENTRY+len(w)*4,4),w));code[end]=0
                m=CallerOracle(window,initial,args,phase,entry=pc,connected=code);m.expected_args=args;m.f[freg]=args[7];m.code=WindowCode(m.code,m);m.code.ends=(end,)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Missing original caller boundary')
                assert(m.r[2],m.memory)==(answer,want)
            count+=1
    jal=0xc000000|((g.source.ENTRY>>2)&0x3ffffff);words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);direct=[i*4 for i,w in enumerate(words)if w==jal];pointers=[i*4 for i,w in enumerate(words)if w==g.source.ENTRY]
    assert direct==[0x1a3c7c,0x1a3ce0,0x1a45e8,0x1a78f8] and not pointers
    report=dict(direct_sites=4,caller_cases=count,streams=3,full_ten_word_packets=True,literal_registry_pointers=0,full_parent_claimed=False)
    (g.source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
