"""Timed vertical oscillation: ABI, float order, timer and strict image."""
from dataclasses import dataclass, replace
from pathlib import Path
import itertools
import json
import math
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_vertical_bob_match as source

from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_sine_phase_update import wrap
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
RECORD, TABLE, CALLER, RELEASE, WRAP_BOUND = 0x30000, 0x800898B0, 0x151321D0, 0x1516972C, 0x800A56A4
OFFSETS = (0x20, 0x24, 0x28, 0x50, 0x54, 0x58, 0x174, 0x178, 0x17C)
SYMBOLS = dict(sinf=source.SINE, func_15144B68=source.WRAP,
               D_800BE9A4=source.CLOCK, D_800BE9E4=0x800BE9E4)


def half(word):
    return ((word & 65535) ^ 32768)-32768


@dataclass(frozen=True)
class Case:
    remaining: int = 5
    tick: int = 1
    clock: int = bits(1.)
    fields: tuple = tuple(bits(v) for v in (7., 8., 9., -2., 3., 4., .5, .25, 2.))
    wrapped: int = bits(1.5)
    sine: int = bits(.25)
    mode: int = 0
    alias: object = None
    seed: int = 0xA5


def corpus():
    for remaining, tick, mode in itertools.product((-32768, -1, 0, 1, 2, 32767),
            (0, 1, 3, 0xFFFFFFFF, 32768, 0xFFFF8000, 0x7FFFFFFF, 0x80000000), range(4)):
        yield Case(remaining=remaining, tick=tick, mode=mode)
    values = (0., -0., 1.75, -2.75, 16777216., -16777216., 1e20, -1e20)
    for i in range(256):
        yield Case(remaining=(-1, 0, 1, 32767)[i % 4], tick=(0, 1, 3, 32768)[i % 4],
            clock=bits((0., -0., .125, -.25, 1., -1., 4., 2.)[i % 8]),
            fields=tuple(bits(values[(i+j) % 8]) for j in range(6))+
                   (bits((i % 25-12)*.75), bits((i % 7-3)*.25), bits(values[(i+6) % 8])),
            mode=i % 4, seed=i)
    for field, value, remaining in itertools.product(range(9),
            (1, 0x80000001, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7FA12345), (0, 1)):
        fields = list(Case().fields); fields[field] = value
        yield replace(Case(), fields=tuple(fields), remaining=remaining)
    for name, offset, mode, remaining in itertools.product(('D_800BE9A4', 'D_800BE9E4'),
            (0x20, 0x24, 0x28, 0x50, 0x54, 0x58, 0x170, 0x174, 0x178, 0x17C), range(4), (0, 1)):
        yield Case(alias=(name, offset), mode=mode, remaining=remaining)


def address(case, symbols):
    return RECORD if case.alias is None else (symbols[case.alias[0]]-case.alias[1]) & 0xFFFFFFFF


def fixture(case, symbols=None):
    s = symbols or SYMBOLS; p = address(case, s)
    m = {STACK+i: (i*17+0xA5) & 255 for i in range(-0x800, 0x400)}
    for base, size in ((p-16, 0x1A0), (s['D_800BE9A4']-16, 96), (s['D_800BE9E4']-16, 36)):
        for i in range(size): m.setdefault(base+i, (i*13+case.seed) & 255)
    for at, value in trig.GLOBALS.items(): put(m, at, value)
    put(m, WRAP_BOUND, 0x40C90FDB)
    for off, value in zip(OFFSETS, case.fields): put(m, p+off, value)
    put(m, p+0x170, case.remaining, 2); put(m, p+0x172, 0xD4C3, 2)
    put(m, s['D_800BE9A4'], case.clock); put(m, s['D_800BE9E4'], case.tick)
    return m


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x800 <= a < STACK+0x400}


def effects(memory, p, s, ordinal, mode):
    if ordinal == 1 and mode & 1:
        for off, value in ((0x174, 77.), (0x178, -.25), (0x17C, -3.5), (0x54, 11.)):
            put(memory, p+off, bits(value))
        put(memory, p+0x170, 7, 2)
        put(memory, s['D_800BE9A4'], bits(2.)); put(memory, s['D_800BE9E4'], 4)
    if ordinal == 2 and mode & 2:
        for off, value in ((0x174, -7.), (0x17C, 6.), (0x54, -5.)):
            put(memory, p+off, bits(value))
        put(memory, p+0x170, -1, 2)
        put(memory, s['D_800BE9A4'], bits(.125)); put(memory, s['D_800BE9E4'], 0xFFFFFFFF)


def observation(memory, p, s):
    return tuple(read(memory, p+off) for off in (0x24, 0x54, 0x170, 0x174, 0x178, 0x17C)) + (
        read(memory, s['D_800BE9A4']), read(memory, s['D_800BE9E4']))


def reference(case, symbols=None, real=False, memory=None):
    s = symbols or SYMBOLS; p = address(case, s)
    m = dict(fixture(case, s) if memory is None else memory); calls = []; observations = []
    if half(read(m, p+0x170, 2)) > 0:
        phase = bits(floating(read(m, p+0x174)) +
                     floating(bits(floating(read(m, p+0x178))*floating(read(m, s['D_800BE9A4'])))))
        put(m, p+0x174, phase)
        for ordinal, name in enumerate(('func_15144B68', 'sinf'), 1):
            arg = read(m, p+0x174)
            calls.append((s[name], arg)); observations.append(observation(m, p, s))
            result = ((wrap(arg) if ordinal == 1 else trig.reference(arg)) if real else
                      (case.wrapped if ordinal == 1 else case.sine))
            if not real: effects(m, p, s, ordinal, case.mode)
            if ordinal == 1: put(m, p+0x174, result)
        value = bits(floating(bits(floating(result)*floating(read(m, p+0x17C)))) +
                     floating(read(m, p+0x54)))
        put(m, p+0x24, value)
        put(m, p+0x170, half(read(m, p+0x170, 2))-signed(read(m, s['D_800BE9E4'])), 2)
    else:
        # Match the integer struct-copy order, including NaN payload bits.
        x, y = read(m, p+0x50), read(m, p+0x54)
        put(m, p+0x20, x); z = read(m, p+0x58)
        put(m, p+0x24, y); put(m, p+0x28, z)
    return m, calls, observations


class BobOracle(TimingOracle):
    def __init__(self, words, case, phase=0, symbols=None, entry=source.ENTRY,
                 connected=None, real=False, memory=None):
        self.case, self.targets, self.real = case, symbols or SYMBOLS, real
        self.record = address(case, self.targets); self.visits = set(); self.helper_observations = []
        super().__init__(words, fixture(case, self.targets) if memory is None else memory,
                         phase=phase, entry=entry, arguments=(self.record,), connected=connected)

    def execute(self, word):
        self.visits.add(self.current_pc)
        op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
        rd, fd, fn = word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 0 and fn == 3:
            self.r[rd] = signed(self.r[rt]) >> fd & 0xFFFFFFFF
        elif op == 32:
            off = (word & 65535)-65536 if word & 32768 else word & 65535
            value = self.get((self.r[rs]+off) & 0xFFFFFFFF, 1)
            self.r[rt] = (value-256 if value & 128 else value) & 0xFFFFFFFF
        elif op == 17 and rs == 16 and fn == 13:
            self.f[fd] = math.trunc(floating(self.f[rd])) & 0xFFFFFFFF
        elif op == 17 and rs == 16 and fn == 7:
            self.f[fd] = self.f[rd] ^ 0x80000000
        else: super().execute(word)

    def record_call(self, target):
        if target in (self.targets['func_15144B68'], self.targets['sinf']):
            args = self.f[12]
            self.helper_observations.append(observation(self.memory, self.record, self.targets))
        elif target in (source.ENTRY, RELEASE): args = (self.r[4],)
        else: raise AssertionError(('Unbounded bob call', hex(target)))
        self.calls.append((target, args)); self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == RELEASE:
            put(self.memory, self.r[4]+0x10, 0); result = 0
        else:
            ordinal = 1 if target == self.targets['func_15144B68'] else 2
            assert target == self.targets['func_15144B68' if ordinal == 1 else 'sinf']
            result = ((wrap(self.f[12]) if ordinal == 1 else trig.reference(self.f[12])) if self.real else
                      (self.case.wrapped if ordinal == 1 else self.case.sine))
            if not self.real: effects(self.memory, self.record, self.targets, ordinal, self.case.mode)
        for i in range(4): self.put(self.r[29]+i*4, 0xB5000000+i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.f[0] = result
        self.hi, self.lo = 0x87654321, 0x12345678


def native_harness(body, cases):
    rows = []
    def native_word(memory, off):
        value = read(memory, RECORD+off)
        return ((value << 16) | (value >> 16)) & 0xFFFFFFFF if off == 0x170 else value
    for c in cases:
        before = fixture(c); after, calls, _ = reference(c)
        arrays = [','.join('0x%Xu' % native_word(m, off) for off in range(0, 0x180, 4))
                  for m in (before, after)]
        args = [v for _, v in calls] + [0, 0]
        values = (c.clock, c.tick, c.wrapped, c.sine, c.mode, len(calls), args[0], args[1],
                  read(after, source.CLOCK), read(after, SYMBOLS['D_800BE9E4']))
        rows.append('{{%s},{%s},%s}' % (*arrays, ','.join('0x%Xu' % v for v in values)))
    return '#include <PR/ultratypes.h>\n' + source.TYPES + r'''
typedef char actor_size[sizeof(BobActor200930)==0x180?1:-1];
typedef char position_offset[__builtin_offsetof(BobActor200930,position)==0x20?1:-1];
typedef char base_offset[__builtin_offsetof(BobActor200930,base)==0x50?1:-1];
typedef char bob_offset[__builtin_offsetof(BobActor200930,bob)==0x170?1:-1];
typedef char phase_offset[__builtin_offsetof(BobState200930,phase)==4?1:-1];
typedef char rate_offset[__builtin_offsetof(BobState200930,rate)==8?1:-1];
typedef char amplitude_offset[__builtin_offsetof(BobState200930,amplitude)==12?1:-1];
typedef char timer_width[sizeof(((BobState200930*)0)->remaining)==2?1:-1];
typedef struct {u32 before[96],after[96],clock,tick,wrapped,sine,mode,calls,arg0,arg1,clockAfter,tickAfter;} Case;
static const Case cases[]={''' + ',\n'.join(rows) + r'''};
static struct {u32 left[4];BobActor200930 actor;u32 right[4];} storage;
static const Case *c; static u32 ordinal,error;
f32 D_800BE9A4; s32 D_800BE9E4;
static u32 word(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 number(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static void effect(u32 n){BobActor200930 *a=&storage.actor;
 if(n==1&&(c->mode&1)){a->bob.phase=77;a->bob.rate=-.25f;a->bob.amplitude=-3.5f;a->base.y=11;
  a->bob.remaining=7;D_800BE9A4=2;D_800BE9E4=4;}
 if(n==2&&(c->mode&2)){a->bob.phase=-7;a->bob.amplitude=6;a->base.y=-5;
  a->bob.remaining=-1;D_800BE9A4=.125f;D_800BE9E4=-1;}
}
__attribute__((noinline)) f32 func_15144B68(f32 x){if(ordinal++!=0||word(x)!=c->arg0)error=23;
 effect(1);return number(c->wrapped);}
__attribute__((noinline)) f32 sinf(f32 x){if(ordinal++!=1||word(x)!=c->arg1)error=23;
 effect(2);return number(c->sine);}
''' + body + r'''
static s32(*volatile callback)(BobActor200930*)=func_151D3D50;
static int run(void){u32 n,i,j;u8 *p=(u8*)&storage.actor;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];ordinal=error=0;
  for(i=0;i<4;i++){storage.left[i]=0xA5A5A5A5;storage.right[i]=0x5A5A5A5A;}
  for(i=0;i<96;i++)for(j=0;j<4;j++)p[i*4+j]=(u8)(c->before[i]>>(j*8));
  D_800BE9A4=number(c->clock);D_800BE9E4=(s32)c->tick;
  if(callback(&storage.actor)!=1||ordinal!=c->calls||error||word(D_800BE9A4)!=c->clockAfter||
   (u32)D_800BE9E4!=c->tickAfter)return 23;
  for(i=0;i<96;i++)for(j=0;j<4;j++)if(p[i*4+j]!=(u8)(c->after[i]>>(j*8)))return 23;
  for(i=0;i<4;i++)if(storage.left[i]!=0xA5A5A5A5||storage.right[i]!=0x5A5A5A5A)return 23;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''


class VerticalBobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT/source.BUILD
        cls.values = source.snapshot(cls.output); cls.rom = cls.values['conker/conker.us.bin']
        cls.installed = source.digest((ROOT/source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)
        else:
            for name, wanted in source.INPUTS.items():
                if source.digest((ROOT/name).read_bytes()) != wanted:
                    raise ValueError('Timed-oscillation predecessor changed: '+name)
        cls.obj, diag = source.compile_owner(ROOT, cls.output,
            '#include <ultra64.h>\n'+source.TYPES+source.DECLARATIONS+source.SELECTED, 'fresh-selected')
        if diag: raise ValueError(diag)
        data, funcs = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.words = list(struct.unpack_from('>45I', data, funcs[source.FUNCTION]['value']))
        cls.truth = list(struct.unpack_from('>45I', cls.rom, source.ROM)); cls.cases = list(corpus())
        cls.native_cases = []
        for c in cls.cases:
            if c.alias is not None: continue
            m = fixture(c); active = half(read(m, RECORD+0x170, 2)) > 0
            if active and (not all(math.isfinite(floating(v)) for v in (c.clock, *c.fields, c.wrapped, c.sine))): continue
            if active and not -65536 <= signed(c.tick) <= 65536: continue
            if active:
                left = -1 if c.mode & 2 else 7 if c.mode & 1 else c.remaining
                right = -1 if c.mode & 2 else 4 if c.mode & 1 else signed(c.tick)
                if not -0x80000000 <= left-right <= 0x7FFFFFFF: continue
            after, _, _ = reference(c)
            if active and any(math.isnan(floating(read(after, RECORD+off))) for off in OFFSETS): continue
            cls.native_cases.append(c)
        cls.receipt = dict(installed=cls.installed,
                           cases=len(cls.cases), native_cases=len(cls.native_cases))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt, indent=2)+'\n')
        print('Timed vertical oscillation qualification:', cls.receipt, flush=True)

    def test_01_complete_direct_body_bindings_owner_and_old_stub(self):
        self.assertEqual(self.words, self.truth)
        raw, bindings = source.payload(self.obj); source.checked_payload(raw, bindings)
        self.assertEqual((len(raw), self.words[0]), (180, 0x27BDFFE0))
        self.assertEqual(source.payload(source.original(ROOT, self.output)), (raw, bindings))
        self.assertEqual(source.payload(self.output/'qualified-padded.o'), (raw, bindings))
        for i in range(45):
            wrong = bytearray(raw); wrong[i*4] ^= 1
            with self.assertRaises(ValueError): source.checked_payload(bytes(wrong), bindings)
        for at in bindings:
            wrong = dict(bindings); wrong[at] = [('R_MIPS_26', 'D_800BE9E4')]
            with self.assertRaises(ValueError): source.checked_payload(raw, wrong)
        self.assertEqual(json.loads((self.output/'qualification.json').read_text())['preserved_neighbors'], 27)
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'], 5)
        old = self.values['conker/build/conker.us.elf']
        stale = struct.unpack_from('>45I', old, source.elf_slot_offset(old, source.ENTRY, 180))
        m = BobOracle(stale, Case()).run(); self.assertEqual(m.r[2], 0); self.assertFalse(m.calls)
        self.receipt.update(words=45, frame=32, bindings=6, guards=0, raw_corruptions=45,
                            binding_corruptions=6, neighbors=27, actual_Make_commands=5)

    def test_02_signed_timer_late_reads_aliases_and_complete_state(self):
        visits = set()
        for c, phase in itertools.product(self.cases, (0, 8)):
            expected, calls, obs = reference(c); models = []
            for words in (self.truth, self.words):
                m = BobOracle(words, c, phase).run()
                self.assertEqual((public(m.memory), m.calls, m.helper_observations), (public(expected), calls, obs))
                self.assertEqual((m.r[2], m.r[29]), (1, STACK+phase)); models.append(m); visits.update(m.visits)
            self.assertEqual(complete(models[0]), complete(models[1]))
        # Retail retains a duplicate LW after an unconditional branch. It is unreachable.
        root = set(range(source.ENTRY, source.ENTRY+180, 4))
        self.assertEqual(root-visits, {source.ENTRY+136})
        self.receipt.update(guest_phases=len(self.cases)*2, reachable_words_executed=44,
            unreachable_preserved_word_offset=136, helper_side_effects=True,
            guest_global_alias_phases=sum(c.alias is not None for c in self.cases)*2,
            portable_alias_or_fault_semantics_claimed=False)

    def native(self, body, name, opt='-O2'):
        path = self.output/(name+opt+'.c'); exe = path.with_suffix('.elf')
        path.write_text(native_harness(body, self.native_cases))
        command = ['gcc', '-m32', '-std=c99', '-D_LANGUAGE_C', opt, '-fno-pie', '-no-pie', '-nostdlib',
            '-fno-stack-protector', '-fno-builtin', '-msse2', '-mfpmath=sse', '-ffp-contract=off',
            '-mstackrealign', '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration', '-I', str(ROOT/'conker/include/2.0L'),
            '-Wl,-e,_start', str(path), '-o', str(exe)]
        result = subprocess.run(command, capture_output=True, text=True)
        (self.output/(name+opt+'-compile.txt')).write_text(result.stdout+result.stderr)
        if result.returncode: raise ValueError(result.stdout+result.stderr)
        return subprocess.run([str(exe)], capture_output=True).returncode

    def test_03_native32_SDK_layout_order_and_effective_negatives(self):
        for opt in ('-O0', '-O2', '-O3'): self.assertEqual(self.native(source.SELECTED, 'native', opt), 0)
        controls = {
            'zero-timer-active': source.SELECTED.replace('remaining > 0', 'remaining >= 0'),
            'unsigned-gate': source.SELECTED.replace('bob->remaining > 0', '(u16)bob->remaining > 0'),
            'wrong-output': source.SELECTED.replace('actor->position.y =', 'actor->position.x ='),
            'missing-base': source.SELECTED.replace(' + actor->base.y', ''),
            'wrong-rate': source.SELECTED.replace('bob->rate *', 'bob->amplitude *'),
            'lost-wrap': source.SELECTED.replace('bob->phase = func_15144B68', 'func_15144B68'),
            'cached-tick': source.SELECTED.replace('    BobState200930 *bob', '    s32 cached = D_800BE9E4;\n    BobState200930 *bob').replace('remaining -= D_800BE9E4', 'remaining -= cached'),
            'wrong-decrement': source.SELECTED.replace('remaining -=', 'remaining +='),
            'incomplete-restore': source.SELECTED.replace('actor->position = actor->base;', 'actor->position.y = actor->base.y;'),
            'lost-return': source.SELECTED.replace('return 1;', 'return 0;'),
        }
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED); self.assertEqual(self.native(body, name), 23, name)
        self.receipt.update(native_profiles=3, native_SDK_types=True, trap_UBSan=True,
            native_semantic_negatives=len(controls), native_excludes_signed32_subtraction_overflow=True,
            finite_active_math_only=True, inactive_bit_copy_includes_NaN_and_infinity=True)

    def test_04_connected_original_math_helpers(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context = type('Original', (), dict(root=ROOT, out=self.output))
        connected = {}
        for name, asm, at, rom, size in (
            ('sinf', 'conker/asm/nonmatchings/libultra/gu/sinf/sinf.s', source.SINE, 0x75210, 416),
            ('func_15144B68', 'conker/asm/nonmatchings/game_16EE20/func_15144B68.s', source.WRAP, 0x172018, 96)):
            obj = ViewListSetupTests.original.__func__(context, 'original-'+name, self.values[asm].decode(), name)
            data, funcs = source.link_owner(ROOT, self.output, obj, source.OWNER)
            payload = data[funcs[name]['value']:funcs[name]['value']+size]
            self.assertEqual(payload, self.rom[rom:rom+size])
            connected.update({at+i: struct.unpack_from('>I', payload, i)[0] for i in range(0, size, 4)})
        count = 0; visits = set()
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x24A164)[0], 0x40C90FDB)
        for angle, clock, remaining, phase in itertools.product((-90., -7., -0., 0., .25, 1.5, 7., 90., floating(0x7FC12345)),
                (0., 1., -1., 4.), (0, 1), (0, 8)):
            fields = list(Case().fields); fields[6] = bits(angle)
            c = Case(fields=tuple(fields), clock=bits(clock), remaining=remaining)
            expected, calls, obs = reference(c, real=True); models = []
            for words in (self.truth, self.words):
                m = BobOracle(words, c, phase, connected=connected, real=True).run()
                self.assertEqual((public(m.memory), m.calls, m.helper_observations), (public(expected), calls, obs))
                models.append(m); visits.update(m.visits)
            self.assertEqual(complete(models[0]), complete(models[1])); count += 1
        self.assertTrue(set(range(source.WRAP, source.WRAP+96, 4)) <= visits)
        self.receipt.update(actual_math_phases=count, GNU_original_helper_words=128,
            all_wrap_words_visited=True, hardware_FCSR_or_infinite_wrap_completion_claimed=False)

    def test_05_actual_slot12_original_caller_return_gate(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        jal = struct.pack('>I', 0x0C000000 | (source.ENTRY >> 2 & 0x3FFFFFF))
        literal = struct.pack('>I', source.ENTRY)
        self.assertEqual([i for i in range(0, len(self.rom), 4) if self.rom[i:i+4] == jal], [])
        self.assertEqual([i for i in range(0, len(self.rom), 4) if self.rom[i:i+4] == literal], [0x22E3A0])
        table = struct.unpack_from('>25I', self.rom, 0x22E370)
        self.assertEqual((table[0], table[12]), (0, source.ENTRY))
        context = type('Original', (), dict(root=ROOT, out=self.output))
        obj = ViewListSetupTests.original.__func__(context, 'original-dispatcher',
            self.values['conker/asm/15F680.s'].decode(), 'func_151321D0')
        data, funcs = source.link_owner(ROOT, self.output, obj, 'generated_15F680')
        payload = data[funcs['func_151321D0']['value']:funcs['func_151321D0']['value']+476]
        self.assertEqual(payload, self.rom[0x15F680:0x15F85C])
        caller = struct.unpack('>119I', payload); count = 0
        for slot, timer, remaining, parent_remaining, tick, mode, phase in itertools.product(
                (0, 12), (0, 1), (-1, 0, 1), (-1, 0, 4), (0, 1, 3), range(4), (0, 8)):
            c = Case(remaining=remaining, tick=tick, mode=mode); memory = fixture(c); p = RECORD
            # Fence unrelated secondary providers, alpha/animation and geometry paths.
            put(memory, p+0x60, 0x00280000 | timer*0x80)
            put(memory, p+0x64, parent_remaining, 2)
            for off, value in ((0x71, slot), (0x72, 0), (0x76, 0)): put(memory, p+off, value, 1)
            put(memory, p+0x10, 0xDEADBEEF)
            for i, value in enumerate(table): put(memory, TABLE+i*4, value)
            expected = dict(memory); put(expected, p+0x60, read(expected, p+0x60) & ~0x200000)
            calls = []; obs = []
            if slot:
                expected, math_calls, obs = reference(c, memory=expected)
                calls = [(source.ENTRY, (p,))] + math_calls
            stop = False
            if timer:
                counter = half(read(expected, p+0x64, 2))-signed(read(expected, SYMBOLS['D_800BE9E4']))
                put(expected, p+0x64, counter, 2); stop = half(counter) < 0
            if stop:
                put(expected, p+0x10, 0); calls.append((RELEASE, (p,)))
            models = []
            for words in (self.truth, self.words):
                connected = {source.ENTRY+i*4: w for i, w in enumerate(words)}
                m = BobOracle(caller, c, phase, entry=CALLER, connected=connected, memory=memory).run()
                self.assertEqual((public(m.memory), m.calls, m.helper_observations), (public(expected), calls, obs))
                self.assertEqual(m.r[29], STACK+phase); models.append(m)
            self.assertEqual(complete(models[0]), complete(models[1])); count += 1
        old = self.values['conker/build/conker.us.elf']
        c = Case(remaining=0); memory = fixture(c)
        put(memory, RECORD+0x60, 0x00280000); put(memory, RECORD+0x10, 0xDEADBEEF)
        for off, value in ((0x71, 12), (0x72, 0), (0x76, 0)): put(memory, RECORD+off, value, 1)
        for i, value in enumerate(table): put(memory, TABLE+i*4, value)
        stale_target = struct.unpack_from('>45I', old, source.elf_slot_offset(old, source.ENTRY, 180))
        stale = BobOracle(caller, c, entry=CALLER, memory=memory,
            connected={source.ENTRY+i*4: w for i, w in enumerate(stale_target)}).run()
        self.assertEqual(stale.calls, [(source.ENTRY, (RECORD,)), (RELEASE, (RECORD,))])
        self.assertEqual(read(stale.memory, RECORD+0x10), 0)
        self.assertEqual(struct.unpack_from('>3I', old, source.elf_slot_offset(old, CALLER, 12)), (0x00001025, 0x03E00008, 0))
        self.receipt.update(actual_original_caller_words=119, actual_original_caller_phases=count,
            registry_entries=25, registry_slot=12, literal_ROM='22E3A0', direct_calls=0,
            unrelated_dispatcher_paths_fenced=True, all119_words_executed_claimed=False,
            retained_parent_stub_uncredited=True, stale_target_wrong_release_demonstrated=True,
            full_provider_or_gameplay_claimed=False)

    def test_06_nine_GNU_links_all_six_bindings(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        count = 0
        for index, entry in enumerate((source.ENTRY, 0x18017FFC, 0x1A028000)):
            symbols = SYMBOLS if index == 0 else dict(sinf=0x15088004+index*0x10000,
                func_15144B68=0x15197FFC+index*0x10000, D_800BE9A4=0x80348000+index*0x100000,
                D_800BE9E4=0x80357FFC+index*0x100000)
            images = []
            for label, obj in (('original', source.original(ROOT, self.output)), ('C', self.obj), ('padded', self.output/'qualified-padded.o')):
                data, funcs, relocations = source.parse_object(obj)
                asm, unknown = emit_function(data, funcs[source.FUNCTION], relocations, source.FUNCTION, symbols)
                self.assertEqual(unknown, [])
                stem = self.output/('rebase-%d-%s' % (index, label)); stem.with_suffix('.s').write_text(asm)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(stem.with_suffix('.o')),
                                str(stem.with_suffix('.s'))], capture_output=True, check=True)
                stem.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(stem.with_suffix('.ld')),
                    '-e', source.FUNCTION, *['--defsym=%s=0x%X' % pair for pair in symbols.items()],
                    '-o', str(stem.with_suffix('.elf')), str(stem.with_suffix('.o'))], capture_output=True, check=True)
                images.append(struct.unpack_from('>45I', sections(stem.with_suffix('.elf'))['.text'][1]))
            self.assertEqual(images[0], images[1]); self.assertEqual(images[0], images[2])
            for remaining, mode, phase in itertools.product((0, 1), range(4), (0, 8)):
                c = Case(remaining=remaining, mode=mode); expected, calls, obs = reference(c, symbols); models = []
                for words in images:
                    m = BobOracle(words, c, phase, symbols, entry).run()
                    self.assertEqual((public(m.memory), m.calls, m.helper_observations), (public(expected), calls, obs)); models.append(m)
                self.assertEqual(complete(models[0]), complete(models[1])); self.assertEqual(complete(models[0]), complete(models[2])); count += 1
        self.receipt.update(independent_GNU_links=9, rebased_phases=count, HI_LO_low_carries=True)

    def test_07_fired_target_access_fault_prefixes(self):
        count = 0
        for remaining, mode, alias, phase in itertools.product((0, 1), (0, 3),
                (None, ('D_800BE9E4', 0x170)), (0, 8)):
            c = Case(remaining=remaining, mode=mode, alias=alias); good = BobOracle(self.truth, c, phase).run()
            for cut in range(good.root_accesses):
                models = [BobOracle(words, c, phase) for words in (self.truth, self.words)]
                for m in models:
                    m.root_fault = cut
                    with self.assertRaises(faults.AccessBoundary): m.run()
                    self.assertEqual(m.root_accesses, cut)
                self.assertEqual(complete(models[0]), complete(models[1])); count += 1
        self.assertGreater(count, 0); self.receipt.update(fired_fault_prefixes=count, portable_fault_claimed=False)

    def test_08_strict_image_and_installed_input_guards(self):
        before = self.values['conker/build/conker.us.elf']; retail = self.rom[source.ROM:source.ROM+180]
        predicted = source.predicted_image(before, retail); source.check_image(before, predicted, retail)
        self.assertEqual(predicted, (self.output/'first-linked.elf').read_bytes())
        at = source.elf_slot_offset(before, source.ENTRY, 180)
        for offset in (0, at-1, at, at+176, at+180, len(before)-1):
            wrong = bytearray(predicted); wrong[offset] ^= 1
            with self.assertRaises(ValueError): source.check_image(before, bytes(wrong), retail)
        with self.assertRaises(ValueError): source.check_image(before, predicted[:-1], retail)
        original = Path.read_bytes; installed = {ROOT/n: data for n, data in self.values.items()}
        installed[ROOT/source.SOURCE] = source.recovered_owner(self.values[source.SOURCE].decode()).encode()
        installed[ROOT/source.OBJECT] = original(self.output/'qualified-padded.o')
        installed[ROOT/'conker/build/conker.us.elf'] = predicted
        def read_input(p): return installed[p] if p in installed else original(p)
        with patch.object(Path, 'read_bytes', read_input): source.audit_inputs(ROOT, self.output)
        mutations = 0
        for name in (source.SOURCE, source.OBJECT, 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/asm/15F680.s', 'conker/include/structs.h'):
            for path in (ROOT/name, self.output/('before-'+name.replace('/', '_'))):
                old = read_input(path); wrong = bytearray(old); wrong[len(wrong)//2] ^= 1
                with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == path else read_input(p)):
                    with self.assertRaises(ValueError): source.audit_inputs(ROOT, self.output)
                mutations += 1
        with patch.object(Path, 'read_bytes', lambda p: self.values[source.OBJECT] if p == ROOT/source.OBJECT else read_input(p)):
            with self.assertRaises(ValueError): source.audit_inputs(ROOT, self.output)
        self.receipt.update(strict_image_negatives=7, installed_and_frozen_mutations=mutations,
                            inputs=len(source.INPUTS), valid_installed_map_verified=True,
                            stale_installed_object_rejected=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
