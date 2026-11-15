"""Retained exit window and complete fifteen-word type-gated wrapper."""
from dataclasses import replace
from collections import Counter
import json,struct
from tools.experiments import game_actor_exit_150c3d5c_recovery as s
from tools.tests import game_actor_exit_150c3d5c_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

WINDOW,END,WINDOW_ROM=0x150C3D04,0x150C3D34,0xF11B4
WRAPPER,WRAPPER_ROM=0x151711C4,0x19E674

def check(words,c,wrapper=False,enabled=True,wrong_argument=False):
    initial=g.fixture(c)
    if wrapper:initial[g.OWNER+4]=0x33 if enabled else 0
    active=enabled if wrapper else True
    expected,calls,observed=g.reference(initial,c) if active else (g.public(initial),[],[])
    counts=Counter(t for t,a in calls)
    extra=[(g.PARENT_STATE,(g.OWNER,1))] if wrapper else [(g.PARENT_AUDIO,(0x93,g.OWNER,32000,200,2500)),(g.PARENT_STATE,(g.OWNER,1))]
    for t,args in extra:
        g.effect(expected,c,t,counts[t]);counts[t]+=1;calls.append((t,args))
    connected=dict(zip(range(s.ENTRY,s.ENTRY+4*len(words),4),words))
    if wrapper:
        entry=WRAPPER;code=list(struct.unpack_from('>15I',g.rom(),WRAPPER_ROM))
    else:
        entry=WINDOW;code=list(struct.unpack_from('>12I',g.rom(),WINDOW_ROM));connected[END]=0
        if wrong_argument:code[1]=0x00002025
    m=g.Oracle(code,initial,c,entry=entry,connected=connected)
    if not wrapper:
        m.r[16]=g.OWNER;m.before[16]=g.OWNER;m.code=WindowCode(m.code,m);m.code.ends=(END,)
    try:m.run()
    except WindowBoundary:assert not wrapper
    else:assert wrapper
    assert g.public(m.memory)==expected,('caller memory',c,wrapper,enabled)
    assert m.calls==calls and m.observed==observed,('caller interface',c,wrapper,enabled)
    assert m.entries==([g.OWNER] if active else [])
    assert m.r[29]==m.before[29] and m.r[16]==m.before[16] and m.f[20:]==m.before_f[20:]
    return m

def main():
    programs=s.programs();n=0
    for c in list(g.cases())[::4]:
        for phase in (0,8):
            c=replace(c,phase=phase)
            for wrapper,enabled in ((False,True),(True,True),(True,False)):
                for words in programs:check(words,c,wrapper,enabled)
                n+=1
    try:check(programs[1],g.Case(),wrong_argument=True)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Wrong actor argument accepted')
    report=dict(cases=n,streams=2,exit_window_words=12,wrapper_words=15,wrapper_type=0x33,
        original_constructor_words=48,original_decoder_words=5,actor_argument_control_effective=True,
        complete_state_parent_uncredited=True,installed=False,c_match_credit=0)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
