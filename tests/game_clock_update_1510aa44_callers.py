"""Actual clock registration, both guarded callers, and ignored return values."""
import itertools,json,struct
from tools.tests import game_clock_update_1510aa44_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
TABLE,SCRIPT=0x80088C90,0x260000

class Window(WindowCode):
    def __getitem__(self,pc):
        if pc==getattr(self.owner,'poison_pc',None):self.owner.r[2]=self.owner.poison
        return super().__getitem__(pc)

def run(m,end,registers,poison_pc=None,poison=0):
    m.poison_pc,m.poison=poison_pc,poison;m.code=Window(m.code,m);m.code.ends=(end,)
    for reg,value in registers.items():m.r[reg]=value&0xffffffff
    before=m.r[:];saved_fp=m.f[20:]
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller window boundary')
    # The bounded parents intentionally advance saved loop registers.
    assert m.r[29]==before[29]and m.f[20:]==saved_fp
    return m

def main():
    rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();delta=0x15000000-0x2d4b0
    original=lambda a,n:list(struct.unpack_from('>%dI'%n,rom,a-delta))
    allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3])
    assert [i*4 for i,w in enumerate(allwords)if w==g.source.ENTRY]==[0x22d978]
    assert not[i for i,w in enumerate(allwords)if w>>26 in(2,3)and(w&0x3ffffff)<<2==g.source.ENTRY&0xfffffff]
    assert struct.unpack_from('>3I',rom,0x22d978)==(g.source.ENTRY,0,0)
    assert TABLE+46*12==0x80088eb8
    initial,args=g.fixture(3599,1,2,0,3);g.put(initial,SCRIPT+8,46)
    for i in range(12):initial[TABLE+46*12+i]=rom[0x22d978+i]
    expected=dict(initial)
    for p,v,n in((g.OWNER+56,g.source.ENTRY,4),(g.OWNER+120,0,4),(g.OWNER+146,0,1)):g.put(expected,p,v,n)
    m=g.Oracle(original(0x1509ebbc,22),initial,args,entry=0x1509ebbc,connected={0x1509ed5c:0})
    # Registration legitimately changes S0 only through our supplied script role;
    # the original installer preserves all those roles through the bounded exit.
    m=run(m,0x1509ed5c,{16:SCRIPT,2:g.OWNER});assert g.public(m.memory)==g.public(expected)
    assert all(0x1509ebbc+i*4 in m.visits for i in range(22))
    programs=[g.source.bound(*payload(g.source.OUT/n,g.source.NAME))for n in('retail.o','selected.o','guarded.o')];count=0
    for lane in(0,1):
        start,end,after=(0x15113ed4,0x15113f08,0x15113ef0)if lane==0 else(0x15113f94,0x1511400c,0x15113fc8)
        window=original(start,(end-start)//4)
        for clock,step,mode,gate,iteration,phase in itertools.product((3599,53999,2591999),(1,60),(0,3),(0,1),(0,)if lane==0 else(0,1),(0,8)):
            initial,args=g.fixture(clock,step,2,0,3,mode=mode,phase=phase);initial[g.OWNER+110]=gate;g.put(initial,g.OWNER+56,g.source.ENTRY);g.put(initial,0x80087380,0x87654321);g.put(initial,0x800d23c0,0x270000);g.put(initial,0x270002,iteration+1,2)
            prepared=dict(initial)
            if lane and iteration and not gate:
                for at,v,n in((90,111,2),(92,222,2),(94,333,2),(128,0x11223344,4)):g.put(prepared,g.OWNER+at,v,n)
            want,calls,snapshots=(prepared,[],[])if gate else g.model(prepared,args)
            for w in programs:
                outcomes=[]
                for poison in(0,0xffffffff,0x7fffffff,0x12345678):
                    code=dict(zip(range(g.source.ENTRY,g.source.ENTRY+len(w)*4,4),w));code[end]=0
                    m=g.Oracle(window,initial,args,entry=start,connected=code)
                    m=run(m,end,{4:iteration+1,16:g.OWNER,17:iteration,18:1 if not lane else 0,19:111,20:222,21:333,22:0x11223344,23:0,30:0},after,poison)
                    assert(g.public(m.memory),m.calls,m.snapshots)==(g.public(want),calls,snapshots)
                    assert m.r[2]==0x87654321;outcomes.append((m.memory,m.r,m.f,m.condition,m.trace))
                assert all(v==outcomes[0]for v in outcomes[1:])
            count+=1
    report=dict(registry_table=TABLE,registry_index=46,registry_ROM=0x22d978,installer_words=22,all_installer_words_visited=True,caller_sites=2,caller_cases=count,streams=3,return_poison_values=4,return_ignored=True,gate_and_repeated_iteration=True,full_parent_claimed=False)
    (g.source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
