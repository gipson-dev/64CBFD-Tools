"""Independent full-path normal-execution proof of the selected actor trail.

The raw private record home at SP28 is bijectively exchanged with retail's
SP20 home. Exposed objects have literal homes. Nonvolatile public memory is
stable within quiet epochs; opaque calls may mutate public memory and every
previously exposed object, argument homes, caller registers and FCSR.
Void-return caller scratch registers and literal fault states are not an ABI
output. Saved registers, ordered calls, FP/FCSR, reads and all private bytes
are compared on every path, including likely-branch annulment.
"""
from pathlib import Path
import json, struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

e = g.e
ENTRY = 0x151B01B8
PREP, CLASSIFY, TRANSFORM, TRAIL = 0x1504715C, 0x15134070, 0x15143134, 0x15153F18

class State(g.State):
    def __init__(self, side, remap):
        super().__init__('common')
        self.side = side
        self.remap = remap
        self.r[4], self.r[5] = ('ACTOR',), ('SOURCE',)
        self.r[29], self.r[31] = ('STACK', 0), ('RETURN',)
        self.mem = {off: ('PRIVATE_ENTRY', off) for off in range(-160, 16)}
        self.exposed = set()

    def canonical(self, off):
        if self.remap:
            if -120 <= off < -116: return off - 8
            if -128 <= off < -124: return off + 8
        return off

    def load(self, address, size, pool=b''):
        if e.tagged(address, 'STACK'):
            off = address[1]
            assert size in (1, 2, 4) and off % size == 0 and -160 <= off and off + size <= 16
            return g.join([self.mem[self.canonical(off+i)] for i in range(size)])
        return super().load(address, size, pool)

    def store(self, address, size, value):
        if e.tagged(address, 'STACK'):
            off = address[1]
            assert size in (1, 2, 4) and off % size == 0 and -160 <= off and off + size <= 16
            for i in range(size): self.mem[self.canonical(off+i)] = g.byte(value, 8*(size-i-1))
        else: super().store(address, size, value)

    def frame(self): return tuple(self.mem[off] for off in range(-160, 16))

class Program(g.Program):
    def __init__(self, words, terms):
        e.Program.__init__(self, words, b'', ENTRY)
        self.terms = terms
        self.seen = set()

    def call(self, s, target):
        n = {PREP:2, CLASSIFY:1, TRANSFORM:3, TRAIL:5}[target]
        args = tuple(s.r[4:4+min(n,4)]) + tuple(s.load(e.add(s.r[29],16+4*i),4) for i in range(max(0,n-4)))
        assert s.r[29] == ('STACK', -160)
        if target == PREP:
            assert args[0] == ('STACK', -116) and args[1] == ('ACTOR',), ('surface ABI', args)
            s.exposed.add((-116, -80))
        elif target == CLASSIFY:
            e.plain(args[0])
        elif target == TRANSFORM:
            assert args[0] == 0x800AA120 and args[1] == ('STACK', -68), ('transform ABI', args)
            e.plain(args[2])
            s.exposed.add((-68, -56))
        else:
            assert args == (('STACK', -76), ('STACK', -68), ('STACK', -116), 255, 1), ('trail ABI', args)
            s.exposed.update({(-76, -68), (-68, 0)})
        s.trace.append(('CALL', target, args, s.fcsr))
        s.trace.append(('PRIVATE_FRAME', s.frame()))
        ordinal = sum(s.calls.values())
        s.calls[target] += 1
        s.epoch += 1
        for begin, end in sorted(s.exposed):
            for off in range(begin,end): s.mem[off] = ('PROVIDER_BYTE', ordinal, off)
        for i in range(max(4,n)): s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
        for i in (1,2,3,*range(4,16),24,25): s.r[i] = ('CALLER',ordinal,i)
        for i in range(20): s.f[i] = ('CALLER_FP',ordinal,i)
        s.r[2] = ('RESULT',target,ordinal)
        s.r[31] = ('CALL_RETURN',ordinal)
        s.hi,s.lo,s.fcsr = ('CALL_HI',ordinal),('CALL_LO',ordinal),('CALL_FCSR',ordinal)
        s.condition = ('CALL_CONDITION',ordinal)

def prove(raw, retail, remap=True):
    terms = Terms()
    values, coverage = [], {}
    for side, words in (('raw',raw),('retail',retail)):
        p = Program(words,terms)
        paths = p.paths(0,{-4:'return'},State(side,remap and side=='raw'))
        results = {}
        for key,s in paths.items():
            assert s.r[29] == ('STACK',0) and s.r[31] == ('RETURN',)
            assert all(s.r[i] == ('ENTRY',i) for i in (*range(16,24),28,30))
            assert s.f[20:] == [('ENTRY_FP',i) for i in range(20,32)]
            results[key] = (s.trace,s.read_set,s.frame(),s.fcsr,tuple(sorted(s.calls.items())))
        values.append(results)
        coverage[side] = p.seen
    a,b = values
    assert a.keys() == b.keys(), ('path predicates',len(a),len(b))
    for key in a:
        if a[key] != b[key]:
            part = next(i for i,(x,y) in enumerate(zip(a[key],b[key])) if x!=y)
            if part == 0:
                x,y=a[key][0],b[key][0]
                at=next((i for i,(u,v) in enumerate(zip(x,y)) if u!=v),min(len(x),len(y)))
                raise AssertionError(('trace',key,at,repr(x[at] if at<len(x) else '<end>')[:1800],repr(y[at] if at<len(y) else '<end>')[:1800]))
            raise AssertionError(('state',key,part,repr(a[key][part])[:1400],repr(b[key][part])[:1400]))
    for side,seen in coverage.items(): assert seen == set(range(0,512,4)), ('coverage',side,len(seen))
    return dict(paths=len(a),coverage={k:len(v) for k,v in coverage.items()},private_and_incoming_bytes=176,
                full_normal_execution=True,all_saved_registers_restored=True,ordered_calls_and_FP_status=True,
                arbitrary_public_aliases_and_retained_exposed_mutations=True,void_return_scratch_uncredited=True)

def main(raw,truth):
    from tools.tests import game_actor_trail_151b01b8_derive as derive
    from tools.experiments import game_actor_trail_151b01b8_match as source
    p=source.OUT
    derived=derive.derive(raw)
    assert derived==truth
    report=dict(raw_relation=prove(raw,truth),derived_relation=prove(derived,truth,False))
    negatives=[]
    for label,old,new in (
        ('surface-home',0x27A4002C,0x27A40030),
        ('heading-half',0x94EA007A,0x94EA0078),
        ('disabled-type',0x24010002,0x24010003),
        ('count-base',0x240D000A,0x240D000B),
        ('retained-record-home',0x8FA30020,0x8FA30024),
        ('selector-byte',0xA3B90090,0xA3B90091),
        ('frame-restore',0x27BD00A0,0x27BD00A8)):
        bad=truth[:];assert bad.count(old)==1,(label,old)
        bad[bad.index(old)]=new
        try:prove(bad,truth,False)
        except(AssertionError,ValueError,KeyError):negatives.append(label)
        else:raise AssertionError(('ineffective proof control',label))
    renamed=[]
    for w in truth:
        op=w>>26
        fields=(21,16,11)if op==0 else(16,)if op==17 and w>>21&31==4 else(21,)if op in(49,57)else()if op in(3,17)else(21,16)
        for shift in fields:
            reg=w>>shift&31
            if reg in(24,25):w=(w&~(31<<shift))|((49-reg)<<shift)
        renamed.append(w)
    report['positive_GPR_allocation']=prove(renamed,truth,False)
    report['effective_negatives']=negatives
    (p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report
