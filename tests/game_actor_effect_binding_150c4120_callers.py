"""Complete original ten-word actor binding wrapper, with its fixed arguments."""
from dataclasses import replace
from functools import lru_cache
import json,struct
from tools.experiments import game_actor_effect_binding_150c4120_recovery as s
from tools.tests import game_actor_effect_binding_150c4120_oracle as g
ENTRY,ROM,WORDS=0x1514F568,0x17CA18,10

@lru_cache(maxsize=1)
def original_window():
    return struct.unpack_from('>10I',(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes(),ROM)

def check(words,c,broken=False):
    c=replace(c,lifetime=-1,priority=255,context=1);initial=g.fixture(c)
    expected,calls,packets=g.reference(initial,c)
    code=list(original_window())
    assert 0x24070001 in code
    if broken:code[code.index(0x24070001)]=0x24070000
    connected=dict(zip(range(s.ENTRY,s.ENTRY+4*len(words),4),words))
    m=g.Oracle(code,initial,c,entry=ENTRY,connected=connected);m.run()
    assert g.public(m.memory,c)==expected and m.calls==calls
    assert m.entries==[g.args(c)] and m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.f[20:]==m.before_f[20:]
    return m

def main():
    programs=s.programs();n=0
    for c in list(g.cases())[::2]:
        for phase in (0,8):
            c=replace(c,phase=phase)
            for words in programs:check(words,c)
            n+=1
    try:check(programs[1],g.Case(),broken=True)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Wrong wrapper context accepted')
    report=dict(cases=n,streams=2,original_wrapper_words=WORDS,original_factory_words=110,original_copy_words=11,
        context_control_effective=True,wrapper_return_uncredited=True,padding_bytes_uncredited=7,installed=False,c_match_credit=0)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
