"""Authentic three direct call windows and four registry entries, privately."""
import itertools,json,struct
from tools.tests import game_particle_common_15175958_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound

def main():
    rom=(g.ROOT/'conker/conker.us.bin').read_bytes()
    retail=list(struct.unpack_from('>961I',rom,0x1a2e08));raw=bound(*payload(g.OUT/'selected.o',g.source.NAME));programs=(retail,raw)
    cases=[g.Case(flags=flags,mode=mode,phase=phase,seed=5,cooldown_zero=1)for flags,mode,phase in itertools.product((0,4,0x40,0x200,0x3ff),(0,1,9,15),(0,8))]
    def direct(w,initial,c):
        m=g.Oracle(w,initial,c);m.run();return g.base.public(m.memory),m.calls,m.observed
    def run(window,start,end,w,initial,c,descriptor=None):
        code=dict(zip(range(g.ENTRY,g.ENTRY+len(w)*4,4),w));code[end]=0
        m=g.Oracle(window,initial,c,entry=start,connected=code);m.r[16]=g.P
        if descriptor is not None:m.r[17],m.r[18]=g.base.TRACK,descriptor
        m.before=m.r[:];m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
        try:m.run()
        except WindowBoundary:pass
        else:raise AssertionError('Missing authentic caller boundary')
        assert m.r[16:24]==m.before_r[16:24]and m.r[29:31]==m.before_r[29:31]and m.f[20:]==m.before_f[20:]
        return g.base.public(m.memory),m.calls,m.observed
    calls=registry=0
    for pc in(0x15176af8,0x15176b58,0x15176dd4):
        window=struct.unpack_from('>2I',rom,pc-0x15000000+0x2d4b0);assert window[0]==0xc000000|((g.ENTRY>>2)&0x3ffffff)
        for c in cases:
            initial=g.fixture(c)
            for w in programs:assert run(window,pc,pc+8,w,initial,c)==direct(w,initial,c)
            calls+=1
    start,end=0x15167164,0x15167178;window=struct.unpack_from('>5I',rom,0x194614)
    for index in(10,20,68,69):
        descriptor=0x8008b4a8+index*0x34;assert struct.unpack_from('>I',rom,0x22ff68+index*0x34)[0]==g.ENTRY
        for c in cases:
            initial=g.fixture(c);g.put(initial,descriptor,g.ENTRY);g.put(initial,g.base.TRACK,0x12345678)
            expected=dict(initial);g.put(expected,g.base.TRACK,g.read(initial,g.P+8));assert expected!=initial
            for w in programs:assert run(window,start,end,w,initial,c,descriptor)==direct(w,expected,c)
            registry+=1
    c=g.Case();initial=g.fixture(c);descriptor=0x8008b4a8+10*0x34;g.put(initial,descriptor,g.ENTRY);g.put(initial,g.base.TRACK,0x12345678)
    expected=dict(initial);g.put(expected,g.base.TRACK,g.read(initial,g.P+8));bad=list(window);stores=[i for i,w in enumerate(bad)if w>>26==43];assert len(stores)==1;bad[stores[0]]=0
    assert run(bad,start,end,raw,initial,c,descriptor)!=direct(raw,expected,c),'Ineffective missing bookkeeping control'
    report=dict(direct_sites=3,direct_cases=calls,registry_entries=4,registry_cases=registry,streams=2,bookkeeping_control_killed=True,full_parent_claimed=False,private=True)
    (g.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
