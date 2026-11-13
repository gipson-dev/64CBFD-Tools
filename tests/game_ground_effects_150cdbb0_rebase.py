"""Verify relocation bindings with actual GNU links at independent bases."""
import struct
import subprocess

from tools.experiments import game_ground_effects_150cdbb0_match as packet
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_ground_effects_150cdbb0_oracle as g


def run(state):
    programs=g.programs(state);count=0
    for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
        for i,key in enumerate(('after','retail','generated','generic')):
            script=packet.OUT/('rebase-%d-%d.ld'%(k,i));elf=packet.OUT/('rebase-%d-%d.elf'%(k,i))
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            argv=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',packet.NAME,
                  *['--defsym=%s=0x%X'%(name,value)for name,value in g.SYMS.items()],'-o',str(elf),str(state[key])]
            result=subprocess.run(argv,cwd=packet.ROOT/'conker',capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            linked=sections(elf)['.text'][1][:4*len(programs[i])]
            assert linked==struct.pack('>%dI'%len(programs[i]),*programs[i]),(entry,key)
        for actor,hit,mutation in ((0,0,0),(g.ACTOR,0,3),(g.ACTOR,1,0),(g.ACTOR,1,7)):
            c=g.Case(actor=actor,hit=hit,mutation=mutation);initial=g.fixture(c);expected=g.reference(initial,c)
            for words in programs:
                m=g.Machine(words,c,initial.copy(),entry=entry).run()
                assert (g.public(m.memory,c),m.calls)==expected,(entry,c)
            count+=1
    return {'bases':3,'programs_per_base':4,'cases':count,'actual_gnu_links':12}
