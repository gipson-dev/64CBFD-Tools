"""Both original complete direct callers, retaining all three JAL sites."""
from dataclasses import replace
import itertools,json,struct
from tools.experiments import game_side_effect_constructor_1519f1c8_match as s
from tools.tests import game_side_effect_constructor_1519f1c8_oracle as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
LINK=0x50000

def retail(entry,n):
    raw=(s.ROOT/'conker/conker.us.bin').read_bytes()[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+n*4]
    elf=(s.ROOT/'conker/build/conker.us.elf').read_bytes();off=elf_slot_offset(elf,entry,n*4);assert elf[off:off+n*4]==raw
    return struct.unpack('>'+str(n)+'I',raw)

def main():
    p=s.programs();rom=(s.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((s.ENTRY>>2)&0x3FFFFFF)
    sites=[0x15000000+i-0x2D4B0 for i in range(0x2D4B0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==jal]
    assert len(sites)==3,sites
    count=0
    for entry,n in ((0x1519F3B8,18),(0x151A084C,55)):
        original=retail(entry,n);cleanup=retail(0x151A0928,10)
        for mode,hit,success,effects,phase in itertools.product((6,7),(0,1),(0,1),(0,1,2,4,7),(0,8)):
            c=g.Case(mode=mode,hit=hit,success=success,effects=effects,phase=phase);states=[]
            for label,ws in p.items():
                m=g.fixture(c)
                for i in range(0x60):m[LINK+i]=(i*7+0xA5)&255
                g.put(m,LINK+0x28,g.STATE);m[LINK+0x2C]=mode
                g.put(m,g.ACTOR,1);m[g.STATE+0x1C]=m[g.ACTOR+0x3B];g.put(m,g.ACTOR+0x1D4,1)
                code=dict(zip(range(s.ENTRY,s.ENTRY+s.SIZE,4),ws));code.update(zip(range(0x151A0928,0x151A0950,4),cleanup))
                q=g.Machine(original,m,c,entry=entry,arguments=(g.STATE if entry==0x1519F3B8 else LINK,),code=code)
                q.run();root_calls=[a for t,a in q.calls if t==s.ENTRY]
                assert root_calls==([(g.STATE,6),(g.STATE,7)] if entry==0x1519F3B8 else [(g.STATE,mode)]),root_calls
                if entry==0x1519F3B8:
                    assert [g.read(q.memory,g.STATE+0x58+4*i) for i in range(4)]==[g.OUT if success else 0,0,g.OUT if success else 0,0]
                else:
                    assert g.read(q.memory,LINK+0xE,2)==65535 and q.memory[LINK+0xD]&1
                states.append((g.public(q.memory,c),q.calls,q.snap,q.r[29],tuple(q.r[16:24])))
            assert states.count(states[0])==3,(entry,c);count+=1
    report=dict(complete_original_callers=2,direct_sites=[hex(x) for x in sites],cases_per_stream=count,streams=3,original_cleanup=True,code_image_bytes=len(rom),full_asset_ROM_census=False)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
