from dataclasses import dataclass
from pathlib import Path
import json
import struct

from tools.tests import game_localized_trail_factory_oracle as base
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

ENTRY = 0x15154884
ROM = 0x181D34
WORDS = 129
SIZE = 516
POSITION = 0x22000
ACTOR = 0x24000
STACK = base.STACK


@dataclass(frozen=True)
class Case:
    seed: int
    phase: int
    positive: int
    allocated: int
    mutation: int

    @property
    def lifetime(self):
        values = (0xC0000000, 0, 0x3F000000, 0x3F800000, 0x41200000)
        return values[(self.seed + self.positive) % len(values)] if not self.positive else values[2 + self.seed % 3]

    @property
    def amplitude(self): return bits(-3.5 + self.seed * 0.25)
    @property
    def height(self): return bits(100.0 + self.seed)
    @property
    def slot(self): return self.seed & 255
    @property
    def context(self): return u32(0xD4000000 + self.seed * 0x101)


def u32(v): return v & 0xFFFFFFFF
def bits(v): return struct.unpack('>I', struct.pack('>f', float(v)))[0]
def floating(v): return struct.unpack('>f', struct.pack('>I', u32(v)))[0]
def fm(a, b): return bits(floating(a) * floating(b))
def fa(a, b): return bits(floating(a) + floating(b))
def fd(a, b): return bits(floating(a) / floating(b))
def put(m, p, v, n=4): base.put(m, p, v, n)
def get(m, p, n=4): return base.get(m, p, n)
def data(m, p, n): return bytes(m[p + i] for i in range(n))


def rng(index, case):
    return bits((0.0, 0.25, 0.5, 0.75, 1.25, -0.5)[(index + case.seed) % 6])


def set_constants(m, s, late=False):
    values = (2.0, 4.0, -1.0, 8.0, 0.5) if not late else (3.0, -2.0, 6.0, 1.5, -4.0)
    for name, value in zip(('D_800A601C', 'D_800A6020', 'D_800A6024', 'D_800A6028', 'D_800A602C'), values):
        put(m, s[name], bits(value))


def fixture(case, s):
    home = STACK + case.phase
    m = {home + i: 0xCC for i in range(-4096, 2048)}
    for base_address, size in ((POSITION, 12), (ACTOR, 0x200)):
        for i in range(size): m[base_address + i] = (i * 17 + case.seed * 9 + 0x31) & 255
    for i, value in enumerate((bits(1.5), bits(-2.25), bits(7.75))): put(m, POSITION + 4 * i, value)
    set_constants(m, s)
    return m


def build_descriptor(initial, case, s):
    d = bytearray([0xCC] * 120)
    def w(at, value, n=4): d[at:at+n] = u32(value).to_bytes(n, 'big')
    one, zero = bits(1.0), 0
    for at, value in ((0, one), (4, one), (8, zero), (12, zero)): w(at, value)
    for i in range(3): w(0x10 + 4*i, fm(rng(i, case), bits(360.0)))
    for at in (0x1C, 0x20, 0x24): w(at, one)
    d[0x28:0x34] = data(initial, POSITION, 12)
    for at in (0x34, 0x38, 0x3C): w(at, zero)
    w(0x40, fa(fm(rng(3, case), get(initial, s['D_800A6020'])), get(initial, s['D_800A6024'])))
    w(0x44, zero)
    w(0x48, fa(fm(rng(4, case), get(initial, s['D_800A6028'])), get(initial, s['D_800A602C'])))
    w(0x4C, zero); w(0x50, 0x140); w(0x54, 0x12C, 2); w(0x56, 0x55, 2)
    w(0x58, 0, 1); w(0x5C, 0); w(0x60, 0xFF, 1); w(0x61, 0x12, 1)
    for at in range(0x62, 0x68): w(at, 0, 1)
    w(0x68, 2, 1); w(0x6A, 0, 1); w(0x6C, 0); w(0x70, 0, 1)
    w(0x72, 1, 2); w(0x74, 0xFF, 2)
    return bytes(d)


def reference(initial, case, s):
    m = dict(initial); calls = []; payloads = []; descriptor = None
    if floating(case.lifetime) <= 0.0: return m, calls, payloads, 0
    p = bytearray(20)
    for at, value in ((0, case.lifetime), (4, case.amplitude), (8, case.height), (12, 0),
                      (16, fd(get(m, s['D_800A601C']), case.lifetime))): p[at:at+4] = u32(value).to_bytes(4, 'big')
    if case.mutation:
        for i, value in enumerate((bits(9.0), bits(8.0), bits(7.0))): put(m, POSITION + 4*i, value)
        set_constants(m, s, True)
    descriptor = build_descriptor(m, case, s)
    calls.extend((s['func_150ADA68'], ()) for _ in range(5))
    calls.append((s['func_15132A4C'], ('descriptor', 0, 0, 20, case.slot, case.context)))
    value = ACTOR if case.allocated else 0
    payloads.append((descriptor, bytes(p) if value else None, value if value else None))
    if value:
        calls.append((s['memcpy'], (ACTOR + 0x170, 'payload', 20)))
        for i, byte in enumerate(p): m[ACTOR + 0x170 + i] = byte
    return m, calls, payloads, value


class Machine(FactoryOracle):
    def __init__(self, words, memory, case, entry, s):
        self.case, self.s, self.target = case, s, entry
        self.rng_i = 0; self.snapshots = []
        super().__init__(words, memory, case, entry=entry, s={},
                         arguments=(POSITION, case.lifetime, case.amplitude, case.height,
                                    case.slot, case.context))
    def record_call(self, target):
        counts = {self.target: 6, self.s['func_150ADA68']: 0,
                  self.s['func_15132A4C']: 6, self.s['memcpy']: 3}
        assert target in counts, hex(target)
        args = tuple(u32(v) for v in self.arguments(counts[target]))
        self.calls.append((target, args)); self.events.append(('CALL', target, args))
        if target == self.s['func_15132A4C']:
            self.snapshots.append((data(self.memory, args[0], 120), None, None))
        elif target == self.s['memcpy']:
            descriptor, _, _ = self.snapshots[-1]
            self.snapshots[-1] = (descriptor, data(self.memory, args[1], args[2]), args[0] - 0x170)
    def hook(self, target):
        value = 0x76543210; fvalue = None
        if target == self.s['func_150ADA68']:
            fvalue = rng(self.rng_i, self.case); self.rng_i += 1
            if self.rng_i == 3 and self.case.mutation:
                for i, v in enumerate((bits(9.0), bits(8.0), bits(7.0))): put(self.memory, POSITION + 4*i, v)
            if self.rng_i == 4 and self.case.mutation: set_constants(self.memory, self.s, True)
        elif target == self.s['func_15132A4C']:
            value = ACTOR if self.case.allocated else 0
        else:
            assert target == self.s['memcpy']; a = self.calls[-1][1]
            copy = data(self.memory, a[1], a[2])
            for i, byte in enumerate(copy): self.memory[a[0] + i] = byte
            value = a[0]
        for i in range(4): self.put(self.r[29] + 4*i, 0xB5000000 + i, 4)
        for reg in (1,2,3,*range(4,16),24,25): self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo, self.r[2] = 0xA5000010, 0xA5000011, u32(value)
        if fvalue is not None: self.f[0] = fvalue


def programs(out, layout):
    q = json.loads((out/'private-layout-v1.json').read_text()); row=q['layouts'][layout]; result=[]
    for label in ('original','C','raw'):
        image=(out/f'layout-{layout}-{label}.elf').read_bytes(); at=elf_slot_offset(image,row['entry'],SIZE)
        result.append(struct.unpack_from('>129I',image,at))
    return row['entry'],row['symbols'],result


def public(m, case):
    home=STACK+case.phase
    return {a:b for a,b in m.items() if not home-4096 <= a < home+2048}


def norm_calls(machine):
    out=[]
    for target,args in machine.calls:
        a=list(args)
        if target==machine.s['func_15132A4C']: a[0]='descriptor'
        elif target==machine.s['memcpy']: a[1]='payload'
        out.append((target,tuple(a)))
    return out


def semantic(machine):
    return (public(machine.memory,machine.case),norm_calls(machine),machine.snapshots,
            [machine.r[i] for i in (*range(16,24),28,29,30,31)],machine.f[20:],machine.hi,machine.lo)


def qualify(root, out):
    seen=set(); executions=0; success=set()
    cases=[Case(i%16,(i&1)*8,1 if i%4 else 0,(i>>2)&1,(i>>3)&1) for i in range(256)]
    for layout in range(3):
        entry,s,codes=programs(out,layout); shift=entry-ENTRY
        for case in cases:
            initial=fixture(case,s); models=[Machine(code,dict(initial),case,entry,s).run() for code in codes]
            assert models[0].memory==models[1].memory and models[0].r==models[1].r and models[0].f==models[1].f
            assert semantic(models[0])==semantic(models[2]),(layout,case)
            expected,calls,payloads,value=reference(initial,case,s)
            assert public(models[0].memory,case)==public(expected,case)
            assert norm_calls(models[0])==calls
            if floating(case.lifetime)>0:
                assert models[0].snapshots==payloads,(layout,case,models[0].snapshots,payloads)
            assert models[0].r[2]==value
            for model in models[:2]: seen.update(pc-shift for pc in model.visits if entry<=pc<entry+SIZE)
            success.add((floating(case.lifetime)>0,case.allocated));executions+=3
    missing=set(range(ENTRY,ENTRY+SIZE,4))-seen
    assert missing=={ENTRY+0x38},list(map(hex,sorted(missing)))
    report=dict(success=True,private_only=True,matching_credit=0,cases_per_layout=256,
                independent_GNU_links=3,executions=executions,root_words=129,covered_words=len(seen),
                unreachable_duplicate_one_constant_word=['0x151548BC'],
                positive_zero_negative_lifetime=True,allocation_success_failure=True,
                complete_position_descriptor_payload_snapshots=True,all_five_RNG_calls=True,
                live_position_and_constant_mutations=True,original_and_normalized_full_state_equal=True,
                raw_C_public_state_equal=True)
    (out/'private-guest-v1.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    root=Path.cwd()
    print(json.dumps(qualify(root,root/'conker/build/game-effect-actor-constructor-15154884-match'),indent=2))

