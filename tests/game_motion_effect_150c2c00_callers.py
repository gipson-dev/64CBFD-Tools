"""Original complete parent through update-table slot 18 and its timer gate."""
from dataclasses import replace
import csv,io,json,struct
from tools.experiments import game_motion_effect_150c2c00_recovery as s
from tools.tests import game_motion_effect_150c2c00_oracle as g

PARENT,PARENT_ROM,TABLE,TICKS=0x15149264,0x176714,0x8008a4e8,0x800be9e4

def main():
    rom=g.rom();parent=list(struct.unpack_from('>45I',rom,PARENT_ROM));assert parent[19]==0x0320f809
    programs=s.programs();seen=set();count=0
    def run(words,c,flag=0,slot=18,changed=False):
        initial=g.fixture(c);initial[g.OWNER+13]=flag;initial[g.OWNER+17]=slot;initial[g.OWNER+16]=255
        g.put(initial,g.OWNER+14,1000,2);g.put(initial,TICKS,3)
        for i in range(20):g.put(initial,TABLE+i*4,struct.unpack_from('>I',rom,0x22efa8+i*4)[0])
        expected=dict(initial)
        if flag:g.put(expected,g.OWNER+14,997,2)
        code=dict(zip(range(s.ENTRY,s.ENTRY+4*len(words),4),words));p=parent[:]
        if changed:assert p[20]==0;p[20]=0x24840004
        m=g.Oracle(p,initial,c,entry=PARENT,connected=code);m.run();g.verify(m,expected,c)
        assert m.target_entries==[s.ENTRY] and g.read(m.memory,g.OWNER+14,2)==(997 if flag else 1000)
        seen.update(m.visits)
    for c in list(g.cases())[::3]:
        for flag in (0,1):
            for words in programs:run(words,c,flag)
            count+=1
    controls=0
    for slot,changed in ((17,False),(18,True)):
        try:run(programs[0],g.Case(),slot=slot,changed=changed)
        except AssertionError:controls+=1
        else:raise AssertionError('Ineffective caller control')
    rows=list(csv.DictReader(io.StringIO((s.ROOT/'conker/retail_layout.us.txt').read_text())));end=max(int(r['end'],16) for r in rows if r['section']=='game')
    jal=0x0c000000|((s.ENTRY>>2)&0x3ffffff)
    calls=[i for i in range(0x2d4b0,0x2d4b0+end-0x15000000,4) if struct.unpack_from('>I',rom,i)[0]==jal]
    pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==s.ENTRY]
    assert not calls and pointers==[0x22eff0]
    report=dict(caller_words=45,caller_cases=count,streams=2,table='D_8008A4E8[18]',indirect_jalr_va='0x151492B0',observed_parent_words=len(seen&set(range(PARENT,PARENT+180,4))),controls=controls,direct_jals=0,aligned_entry_pointers=1,timer_decrement_and_post_update_reload=True,expiry_free_routes_not_claimed=True,physical_stack_match_not_claimed=True,private_uninstalled=True)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
