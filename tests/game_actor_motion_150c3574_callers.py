"""Original state dispatch window; the surrounding parent is uncredited."""
from dataclasses import replace
from collections import Counter
import hashlib,json,struct
from tools.experiments import game_actor_motion_150c3574_recovery as s
from tools.tests import game_actor_motion_150c3574_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

ENTRY,END,TABLE=0x1504AB00,0x1504AB38,0x80086014
ROM=0x77FB0

def check(words,c,blocked=False,null=False,window=None):
    initial=g.fixture(c);g.put(initial,g.OWNER+0x25C,0x200 if blocked else 0)
    g.put(initial,TABLE+24*4,0 if null else s.ENTRY)
    expected,calls=g.reference(initial,c) if not blocked and not null else (g.public(initial),[])
    if window is None:
        rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()
        window=list(struct.unpack_from('>14I',rom,ROM))
    connected=dict(zip(range(s.ENTRY,s.ENTRY+4*len(words),4),words));connected[END]=0
    m=g.Oracle(window,initial,c,entry=ENTRY,connected=connected)
    m.r[16]=g.OWNER;m.before[16]=g.OWNER
    m.code=WindowCode(m.code,m);m.code.ends=(END,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller did not reach the declared window boundary')
    assert g.public(m.memory)==expected,('caller memory',c,blocked,null)
    assert m.calls==calls,('caller calls',c,blocked,null,m.calls,calls)
    assert m.entries==([] if blocked or null else [g.OWNER])
    assert m.r[16]==g.OWNER and m.r[29]==m.before[29]
    assert m.f[20:]==m.before_f[20:]
    return m

def main():
    truth,raw=s.programs();rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()
    # The retained table and the loaded retail input must independently agree.
    assert struct.unpack_from('>I',rom,0x22AB34)[0]==s.ENTRY
    window=list(struct.unpack_from('>14I',rom,ROM));visits=set();n=0
    assert window[11]==0x0040F809 and window[12]==0x02002025
    values=[replace(c,seed=c.seed+5) for c in list(g.cases())[::8]]
    for c in values:
        for blocked,null in ((False,False),(True,False),(False,True)):
            for words in (truth,raw):visits.update(check(words,c,blocked,null,window).visits)
            n+=1
    broken=window[:];broken[12]=0x00002025
    try:check(raw,values[0],window=broken)
    except (AssertionError,KeyError):pass
    else:raise AssertionError('Caller argument control did not fail')
    report=dict(cases=n,streams=2,retail_window_words=14,retail_window_sha256=hashlib.sha256(struct.pack('>14I',*window)).hexdigest(),
        dispatch_table=hex(TABLE),slot=24,jalr=hex(ENTRY+44),return_ignored=True,
        effective_controls=1,whole_parent_qualified=False,installed=False,c_match_credit=0)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
