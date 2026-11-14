"""Piece renderer packets, visibility masks, reloads and authentic callback ABI."""
from pathlib import Path
from dataclasses import dataclass, replace
import itertools, json, os, struct
from tools.experiments import game_piece_renderer_1517a3a0_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

RECORD, COMMANDS, SYNC = 0x50000, 0x60000, 0x70000
CULL, CACHE, MATRIX, MATERIAL = 0x1510AEE0, 0x1517A9A8, 0x15043D90, 0x15142FBC
TABLE, PAGE, ALPHA, MODE, LIST = 0x800D9C10, 0x800BE9C0, 0x800DD450, 0x800D2C9C, 0x8008CDF0
FLOATS = (0x800D9B20, 0x800D9B1C, 0x800D35E0, 0x800D35E4)
FIELDS = ((*((a, 4) for a in FLOATS), (PAGE, 1), (ALPHA, 2), (MODE, 4)))
u32 = lambda v: v & 0xffffffff
half = lambda v: ((v & 65535) ^ 32768) - 32768

@dataclass(frozen=True)
class Case:
    category: int = 8
    view: int = 1
    packed: int = 1
    opacity: int = 127
    cached: int = -1
    reject: int = 0
    page: int = 0
    mutation: int = 0
    phase: int = 0
    seed: int = 0

def args(c): return COMMANDS, RECORD, u32(c.view)

def cases():
    for i, (category, reject, view, packed, equal, mutation, phase) in enumerate(itertools.product(
            (0, 8, 9, 12, 89, 255), (0, 1), range(4), (0, 1, 15, 255), (0, 1), (0, 1, 3), (0, 8))):
        opacity = (0, 1, 127, 255)[i % 4]
        yield Case(category, view, packed, opacity, opacity if equal else -1, reject, i & 1, mutation, phase, i)
    for v in range(256):
        yield Case(category=v, reject=1, seed=v)
        yield Case(packed=v, reject=1, seed=v)
        yield Case(opacity=v, cached=v, seed=v)
    for view in (-32768, -1, 4, 7, 8, 15, 28, 31, 32, 32767):
        yield Case(view=view, reject=1, packed=255)

def fixture(c):
    m = {STACK+i: (i*17+c.seed*13+0xa5)&255 for i in range(-512, 512)}
    m.update({RECORD+i: (i*29+c.seed*11+0x5a)&255 for i in range(184)})
    m.update({COMMANDS+i: 0xa5 for i in range(512)})
    for i, a in enumerate(FLOATS): put(m, a, (0x3f800000, 0xbf000000, 0, 0x80000000)[(i+c.seed)%4])
    for a, v, n in ((PAGE, c.page, 1), (ALPHA, c.cached, 2), (MODE, u32(c.seed*0x10203), 4)):
        put(m, a, v & ((1 << (n*8))-1), n)
    m[RECORD] = c.category
    m[RECORD+0x9f] = c.seed & 255
    for i, a in enumerate(range(0x90, 0x9c, 2)):
        put(m, RECORD+a, (0, 32767, 32768, 65535)[(c.seed+i)%4], 2)
    put(m, RECORD+0xa8, (0x3f800000, 0xbf000000, 0, 0x80000000, 0x7fc01234)[c.seed%5])
    m[RECORD+0xb2], m[RECORD+0xb3] = c.packed, c.opacity
    return m

def digest(m):
    values = [m[RECORD+i] for i in range(184)]
    values += [read(m, COMMANDS+i*4) for i in range(128)]
    values += [read(m, a, n) for a, n in FIELDS]
    h = 2166136261
    for v in values: h = u32((h ^ v)*16777619)
    return h

def effects(m, c, target, arguments, ordinal, home):
    if target in (CACHE, MATERIAL):
        put(m, arguments[0], 0xf1000000 | ordinal)
        put(m, arguments[0]+4, 0x12340000 | ordinal)
    if target == MATRIX:
        for i in range(64): m[arguments[0]+i] = (i*7+ordinal)&255
    if c.mutation & 1:
        m[RECORD] = (8, 9, 12, 89)[c.seed%4]
        m[RECORD+0x9f] ^= 0x55
        m[RECORD+0xb2] ^= 0x23
        m[RECORD+0xb3] = (c.opacity+ordinal*17)&255
        for i, a in enumerate(range(0x90, 0x9c, 2)): put(m, RECORD+a, (0x8000+ordinal*13+i)&65535, 2)
        put(m, RECORD+0xa8, 0xbf800000)
        m[PAGE] ^= 1
        put(m, ALPHA, 0xffff, 2)
        put(m, MODE, read(m, MODE)^0x87654321)
        put(m, FLOATS[0], 0xc0000000)
    if c.mutation & 2: put(m, home+8, (ordinal+2)&3)

def result(c, target, arguments):
    if target == CULL: return u32(c.reject)
    if target == MATRIX: return 0xdeadbeef
    return arguments[0]+8*(1+c.seed%2)

def reference(initial, c, sync=SYNC):
    m = dict(initial); calls = []; observations = []; home = STACK+c.phase
    put(m, home+8, c.view)
    def call(target, *a):
        a = tuple(map(u32, a)); calls.append((target, a)); observations.append((digest(m), 0 if target == MATERIAL else None))
        effects(m, c, target, a, len(calls), home)
        if target == MATERIAL: m[sync] = 0x5a
        return result(c, target, a)
    if m[RECORD] not in (12, 89):
        view = half(read(m, home+8)); xyz = [bits(float(half(read(m, RECORD+a, 2)))) for a in (0x90, 0x92, 0x94)]
        answer = call(CULL, u32(TABLE+view*64), *xyz, *(read(m, a) for a in FLOATS), 0, 0)
        view = half(read(m, home+8))
        if answer:
            if m[RECORD] == 8 and m[RECORD+0xb2] & u32(1 << (view&31)):
                m[RECORD+0xb2] = (m[RECORD+0xb2] | u32(16 << (view&31)))&255
            return m, calls, observations, COMMANDS
    view = half(read(m, home+8))
    if m[RECORD] != 9: m[RECORD+0xb2] = (m[RECORD+0xb2] | u32(1 << (view&31)))&255
    cursor = call(CACHE, COMMANDS, m[RECORD+0x9f])
    angles = [bits(float(half(read(m, RECORD+a, 2)))) for a in (0x96, 0x98, 0x9a)]
    scale = read(m, RECORD+0xa8)
    xyz = [bits(float(half(read(m, RECORD+a, 2)))) for a in (0x90, 0x92, 0x94)]
    call(MATRIX, RECORD+m[PAGE]*64+16, *angles, scale, scale, scale, *xyz)
    put(m, cursor, 0xda380003); put(m, cursor+4, RECORD+m[PAGE]*64+16); cursor += 8
    if m[RECORD+0xb3] != half(read(m, ALPHA, 2)):
        put(m, cursor, 0xe7000000); put(m, cursor+4, 0); cursor += 8
        put(m, cursor, 0xfa000000); put(m, cursor+4, m[RECORD+0xb3]); cursor += 8
        put(m, ALPHA, m[RECORD+0xb3], 2)
    m[sync] = 0
    cursor = call(MATERIAL, cursor, read(m, MODE)|0x82ca0,
                  0x5049d8 if m[RECORD] in (8, 9) else 0x504240, sync)
    put(m, cursor, 0xde000000); put(m, cursor+4, LIST); cursor += 8
    return m, calls, observations, cursor

class Oracle(FactoryOracle):
    def __init__(self, words, initial, c, entry=source.ENTRY, connected=None):
        self.observed = []; self.sync = None
        super().__init__(words, initial, c, entry=entry, arguments=args(c), connected=connected)
        self.before_r, self.before_f = self.r[:], self.f[:]
    def execute(self, w):
        if w>>26 == 0 and w&63 == 4:
            self.r[w>>11&31] = u32(self.r[w>>16&31] << (self.r[w>>21&31]&31)); self.r[0] = 0
        else: super().execute(w)
    def record_call(self, target):
        if target == source.ENTRY:
            assert tuple(map(u32, self.arguments(3))) == args(self.case); return
        assert target in (CULL, CACHE, MATRIX, MATERIAL), hex(target)
        a = tuple(map(u32, self.arguments({CULL:10, CACHE:2, MATRIX:10, MATERIAL:4}[target])))
        if target == MATERIAL: self.sync = a[3]; a = (*a[:3], SYNC)
        self.calls.append((target, a)); self.events.append(('CALL', target, a))
        self.observed.append((digest(self.memory), self.memory[self.sync] if target == MATERIAL else None))
    def hook(self, target):
        a = self.calls[-1][1]; effects(self.memory, self.case, target, a, len(self.calls), self.target_home)
        if target == MATERIAL: self.memory[self.sync] = 0x5a
        value = result(self.case, target, a)
        for i in range(4): self.put(self.r[29]+4*i, 0xb5000000+i, 4)
        for i in (1,2,3,*range(4,16),24,25): self.r[i] = 0xa5000000+i
        self.f[:20] = [0xa5000000+i for i in range(20)]; self.hi, self.lo = 0xa5000010, 0xa5000011; self.r[2] = value

def public(m): return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512 and a != SYNC}

def verify(machine, initial, c):
    m, calls, obs, value = reference(initial, c)
    assert (public(machine.memory), machine.calls, machine.observed, machine.r[2]) == (public(m), calls, obs, value), c
    assert machine.r[16:24] == machine.before_r[16:24] and machine.f[20:] == machine.before_f[20:] and machine.r[29] == machine.before_r[29]

def state(m): return m.r, m.f, m.memory, m.calls, m.observed, m.trace, m.hi, m.lo

def load():
    root = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path.cwd())).resolve(); out = root/source.BUILD
    programs = [bound_blob(*payload(out/f, source.NAME)) for f in ('retail.o', 'selected.o', 'guarded.o')]
    assert programs[0] == programs[2]
    return root, out, programs

def main():
    root, out, programs = load(); n = 0; seen = set()
    for c in cases():
        initial = fixture(c); machines = []
        for words in programs:
            m = Oracle(words, initial, c); m.run(); verify(m, initial, c); machines.append(m)
        assert state(machines[0]) == state(machines[2]); seen.update(machines[0].visits); n += 1
    unvisited = sorted((pc-source.ENTRY)//4 for pc in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen)
    assert unvisited == [150], unvisited
    prefixes = 0
    for c in (Case(mutation=3), Case(reject=1), Case(category=9, cached=127)):
        initial = fixture(c); m = Oracle(programs[0], initial, c); m.run()
        for cut in range(m.all_accesses):
            models = []
            for words in (programs[0], programs[2]):
                m = Oracle(words, initial, c); m.cut = cut
                try: m.run()
                except AccessBoundary: pass
                else: raise AssertionError('Missing fired memory boundary')
                models.append(m)
            assert state(models[0]) == state(models[1]); prefixes += 1
    rom = (root/'conker/conker.us.bin').read_bytes(); entries = (8, 9, 12, 89); caller_cases = 0
    # The dispatcher loads slot +8 before this original 8-word call window.
    pc, end = 0x15167898, 0x151678b8
    window = struct.unpack_from('>8I', rom, 0x194d48)
    for descriptor, reject, mutation, phase in itertools.product(entries, (0,1), (0,1), (0,8)):
        address = 0x8008b4a8+descriptor*0x34
        assert struct.unpack_from('>I', rom, 0x22ff68+(address-0x8008b4a8)+8)[0] == source.ENTRY
        c = Case(category=descriptor, reject=reject, mutation=mutation, phase=phase)
        initial = fixture(c); put(initial, 0x71000, 0x12345678); put(initial, RECORD+8, 0x87654321)
        for words in programs:
            code = dict(zip(range(source.ENTRY, source.ENTRY+source.SIZE, 4), words)); code[end] = 0
            m = Oracle(window, initial, c, entry=pc, connected=code)
            m.r[16],m.r[17],m.r[19],m.r[22],m.r[25] = RECORD,0x71000,COMMANDS,c.view,source.ENTRY
            m.before_r = m.r[:]; m.code = WindowCode(m.code, m); m.code.ends = (end,)
            try: m.run()
            except WindowBoundary: pass
            else: raise AssertionError('Missing dispatcher continuation')
            expected_initial = dict(initial); put(expected_initial,0x71000,0x87654321)
            verify(m, expected_initial, c); assert read(m.memory,0x71000) == 0x87654321
        caller_cases += 1
    controls = {'wrong_bypass_category':(8,0x2401000d), 'wrong_retirement_nibble':(55,0x240e0008),
                'wrong_matrix_opcode':(109,0x3c0bda39), 'wrong_alpha_field':(134,0x920b009f),
                'wrong_terminal_opcode':(160,0x3c0add00)}
    killed=[]
    for label,(at,word) in controls.items():
        words=programs[0][:];assert words[at]!=word;words[at]=word;failed=False
        for c in (Case(category=12,reject=1),Case(reject=1,packed=2),Case(seed=19),Case(category=9)):
            initial=fixture(c)
            try:m=Oracle(words,initial,c);m.run();verify(m,initial,c)
            except (AssertionError,KeyError):failed=True;break
        assert failed,label;killed.append(label)
    report = dict(cases=n, observed_words=len(seen), unvisited_word_indices=unvisited, caller_cases=caller_cases,
                  full_state_prefixes=prefixes, providers_modeled=True, native_view_domain='0..3',
                  raw_private_layout_and_access_order_explicit=True, negative_controls=killed)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report),flush=True)

if __name__ == '__main__': main()
