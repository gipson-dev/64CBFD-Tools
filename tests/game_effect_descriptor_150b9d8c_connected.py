"""Connect the original RNG and inventory visible code-image references."""
import hashlib
import itertools
import struct

from tools.experiments import game_effect_descriptor_150b9d8c_screen as packet
from tools.match_progress import load_elf_functions
from tools.tests import game_effect_descriptor_150b9d8c_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_random_colored_effect_descriptor_oracle import Oracle as RngInstructions
from tools.tests.test_game_random_selector_outputs_match import SEEDS

SEED=0x800885B0


class RealRng(RngInstructions):
    def __init__(self,ws,c,m,code):
        self.c=c;self.home=g.STACK+c.phase;self.draw=0;self.packets=[]
        FactoryOracle.__init__(self,ws,m,c,entry=g.ENTRY,s=g.SYMS,connected=code,arguments=(c.actor,));self.before=self.r[:]
    record_call=g.Machine.record_call
    hook=g.Machine.hook
    def execute(self,w):
        super().execute(w)
        if w>>26==17 and (w>>21&31)==0:self.r[w>>16&31]=self.f[w>>11&31]&0xFFFFFFFF;self.r[0]=0


def actual_rng(state):
    rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();rng=struct.unpack_from('>18I',rom,g.RNG-0x15000000+0x2D4B0)
    live,_,_=load_elf_functions(str(packet.ROOT/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert tuple(live['func_150ADA20'])==rng
    code=dict(zip(range(g.RNG,g.RNG+4*len(rng),4),rng));visited=set();count=0
    for seed,phase,selector in itertools.product(SEEDS,(0,8),(-1,0)):
        c=g.Case(phase=phase,selector=selector);initial=g.fixture(c);g.put(initial,SEED,seed,8);states=[]
        for words in g.programs(state):
            m=RealRng(words,c,initial.copy(),code).run()
            public={a:b for a,b in m.memory.items() if not g.STACK+phase-4096<=a<g.STACK+phase+2048}
            states.append((public,m.calls,m.packets));visited|=m.visits&set(code)
        assert states.count(states[0])==4,(seed,c)
        count+=1
    assert visited==set(code)
    return {'cases':count,'rng_words':len(code),'visited_rng_words':len(visited)}


def caller_census():
    data=(packet.ROOT/'conker/conker.us.bin').read_bytes()
    assert hashlib.sha256(data).hexdigest()==packet.MANIFEST['rom_sha256']
    entry=g.ENTRY; patterns={'pointer':entry,'jal':0x0C000000|((entry>>2)&0x3FFFFFF),
                            'jump':0x08000000|((entry>>2)&0x3FFFFFF)}
    hits={name:[i for i in range(0,len(data)-3,4) if data[i:i+4]==struct.pack('>I',word)]
          for name,word in patterns.items()}
    assert not any(hits.values()),hits
    split=[]
    for pos in range(2,len(data)-1,4):
        if data[pos:pos+2]!=b'\x9d\x8c':continue
        low=struct.unpack_from('>I',data,pos-2)[0];register=low>>21&31
        for distance in range(4,129,4):
            if pos-2-distance<0:break
            high=struct.unpack_from('>I',data,pos-2-distance)[0]
            if high>>26==15 and high&65535 in (0x150B,0x150C) and high>>16&31==register:
                split.append((pos-2-distance,pos-2))
    assert not split,split
    control=struct.pack('>I',0x150B9D14)
    assert data.count(control)==1
    return {'aligned_code_image_hits':hits,'nearby_split_pairs':split,'neighbor_pointer_positive_control':hex(data.index(control)),
            'scope':'literal pointer, direct J/JAL and nearby LUI pairs; dynamic or external dispatch unresolved'}
