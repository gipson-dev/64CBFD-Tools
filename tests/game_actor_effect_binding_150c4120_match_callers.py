"""Connected original callers and all known retail callback return sinks."""
from dataclasses import replace
from functools import lru_cache
import csv,json,struct
from tools.experiments import game_actor_effect_binding_150c4120_match as s
from tools.tests import game_actor_effect_binding_150c4120_oracle as g
from tools.tests import game_actor_effect_binding_150c4120_callers as old_callers
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

@lru_cache(maxsize=1)
def rom():return (s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()

def words(start,end):return list(struct.unpack_from('>%dI'%((end-start)//4),rom(),start-0x15000000+0x2D4B0))

def check(body,c,route,poison=None):
    c=replace(c,context=1) if route=='direct' else replace(c,lifetime=-1,priority=255,context=1)
    initial=g.fixture(c)
    connected=dict(zip(range(s.ENTRY,s.ENTRY+s.SIZE,4),body));connected.update(zip(range(old_callers.ENTRY,old_callers.ENTRY+40,4),old_callers.original_window()))
    if route=='direct':
        start,end=0x15027940,0x15029BA4;code=words(start,start+20)
        g.put(initial,g.STACK+c.phase+0x662,g.args(c)[1],2);initial[g.STACK+c.phase+0x773]=g.args(c)[2]&255
    elif route=='wrapper-parent':
        start,end=0x1506A2C8,0x1506A4DC;code=words(start,start+16)
        g.put(initial,g.STACK+c.phase+0x80,g.OWNER);g.put(initial,g.STACK+c.phase+0x168,0x12345678)
    else:
        assert route=='dispatch';start,end=0x1514D248,0x1514D270;code=words(start,end)
        g.put(initial,0x8008AB34,old_callers.ENTRY);g.put(initial,g.STACK+c.phase+0x48,g.OWNER)
    expected,calls,packets=g.reference(initial,c)
    class CallerOracle(g.Oracle):
        def record_call(self,t):
            if t==old_callers.ENTRY:
                assert self.r[4]==g.OWNER;return
            super().record_call(t)
    connected[end]=0;m=CallerOracle(code,initial,c,entry=start,connected=connected)
    if route=='direct':m.r[4]=g.OWNER;m.r[7]=1
    if route=='dispatch':m.r[2]=49;m.r[3]=0xA5
    class Code(WindowCode):
        def __getitem__(self,pc):
            if poison is not None and route=='direct' and pc==0x1502794C:self.owner.r[2]=poison
            return super().__getitem__(pc)
    m.code=Code(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not stop')
    assert g.public(m.memory,c)==expected and m.calls==calls,(route,c,m.calls,calls)
    entry=(g.OWNER,g.u32(g.signed16(g.args(c)[1])),g.args(c)[2]&255,1)
    assert m.entries==[entry],(route,m.entries,entry)
    assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.f[20:]==m.before_f[20:]
    if route=='direct':assert m.r[2]==1
    if route=='dispatch':assert m.r[3]==0xA5
    return m

def rw(w):
    op,fn=w>>26,w&63;rs,rt,rd=w>>21&31,w>>16&31,w>>11&31
    if op==0:
        if fn in (0,2,3):return {rt},{rd}
        if fn in (8,9):return {rs},({rd} if fn==9 else set())
        if fn in (16,18):return set(),{rd}
        return {rs,rt},({rd} if fn in (32,33,34,35,36,37,38,39,42,43) else set())
    if op in (2,3):return set(),set()
    if op in (4,5,20,21):return {rs,rt},set()
    if op in (1,6,7,22,23):return {rs},set()
    if op in (8,9,10,11,12,13,14):return {rs},{rt}
    if op==15:return set(),{rt}
    if op in (32,33,34,35,36,37,38,39):return {rs},{rt}
    if op in (40,41,42,43,46):return {rs,rt},set()
    if op in (49,57):return {rs},set()
    if op==17:
        fmt=w>>21&31
        return ({rt},set()) if fmt==4 else (set(),{rt}) if fmt==0 else (set(),set())
    raise AssertionError(('unsupported return audit opcode',hex(w)))

def return_sink(start,low,high):
    data=words(low,high);visited=set();kills=set();pending=[start]
    def inspect(pc):
        assert low<=pc<high,('return audit escaped',hex(pc));w=data[(pc-low)//4];use,define=rw(w)
        assert 2 not in use,('callback result read before overwrite',hex(pc),hex(w))
        if 2 in define:kills.add(pc);return w,True
        return w,False
    while pending:
        pc=pending.pop()
        if pc in visited:continue
        visited.add(pc);w,dead=inspect(pc)
        if dead:continue
        op,fn=w>>26,w&63
        if op in (2,3,4,5,6,7,20,21,22,23) or op==0 and fn in (8,9):
            assert not (op==0 and fn==8),('callback result propagated to parent return',hex(pc))
            likely=op in (20,21,22,23)
            _,delay_kills=inspect(pc+4)
            if op==3 or op==0 and fn==9:
                if not delay_kills:pending.append(pc+8)
            elif op==2:
                if not delay_kills:pending.append(((pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2))
            else:
                target=pc+4+4*(((w&65535)^32768)-32768)
                unconditional=op in (4,20) and (w>>21&31)==(w>>16&31)
                if not delay_kills:pending.append(target)
                if not unconditional and (likely or not delay_kills):pending.append(pc+8)
        else:pending.append(pc+4)
    assert kills
    return dict(start=hex(start),visited=len(visited),kill_addresses=[hex(v) for v in sorted(kills)])

def audit():
    result=[return_sink(0x1502794C,0x150265CC,0x15029BB8),return_sink(0x1506A2D0,0x15065A5C,0x1506A5F0)]
    result += [return_sink(pc,0x1514D15C,0x1514D310) for pc in (0x1514D26C,0x1514D2AC,0x1514D2F8)]
    # Data-word and JAL inventories include retained ASM callers, which a
    # source-only search misses. Restrict JAL hits to the retail Game code.
    data=rom();hits={}
    for target in (s.ENTRY,old_callers.ENTRY):
        pattern=struct.pack('>I',0x0C000000|((target>>2)&0x3FFFFFF));at=0;found=[]
        while (at:=data.find(pattern,at))>=0:
            if at%4==0:found.append(at)
            at+=1
        hits[target]=found
    assert hits[s.ENTRY]==[0x54DF4,0x17CA28] and hits[old_callers.ENTRY]==[0x97778]
    assert struct.unpack_from('>I',data,0x22F5F4)[0]==old_callers.ENTRY
    assert 0x8008AA70+49*4==0x8008AB34
    return dict(direct_root_calls=2,direct_wrapper_calls=1,loaded_table='D_8008AA70[49]',return_sinks=result,
        known_return_results_ignored=True,whole_parent_execution_uncredited=True)

def main():
    report=audit();programs=s.programs();count=0
    for c in g.cases():
        for route in ('direct','wrapper-parent','dispatch'):
            machines=[check(body,c,route) for body in programs]
            public=lambda m:{p:v for p,v in m.memory.items() if not g.STACK-2048<=p<g.STACK+2048}
            assert public(machines[0])==public(machines[1])==public(machines[2])
            count+=1
    for body in programs:
        for poison in (0,0xFFFFFFFF,0x12345678):check(body,g.Case(),route='direct',poison=poison)
        old_callers.check(body,g.Case())
    report.update(connected_cases=count,streams=3,root_window_words=5,wrapper_parent_words=4,dispatcher_window_words=10,wrapper_words=10,return_poison_controls=9,literal_guest_padding_compared=True)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
