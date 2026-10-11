"""Complete matrix setup, live homes, IEEE-order direction and literal linked audit."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_transform_setup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, RECORD, BANK, OTHER, TYPES = guest.STACK, 0x20000, 0x50000, 0x60000, 0x28000
COPY, INVERT, MULTIPLY, DECOMPOSE = (screen.SYMBOLS[n] for n in
    ('bcopy', 'func_150499A0', 'func_150A7A48', 'func_1503E5F8'))
WIDTHS = {COPY: 3, INVERT: 2, MULTIPLY: 3, DECOMPOSE: 10}
LABELS = {COPY: 'copy', INVERT: 'inverse', MULTIPLY: 'multiply', DECOMPOSE: 'decompose'}
address = state.address


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x600 <= a < STACK+0x140}


def rounded(value):
    return floating(bits(value))


def divide(left, right):
    return rounded(left/right if right else (math.nan if not left else
        math.copysign(math.inf, left*math.copysign(1.0, right))))


def matrix(scale=(2.0, 4.0, 8.0), position=(5.0, 34.0, -3.0), perspective=True):
    result = [0.0]*16
    for i, value in zip((0, 5, 10), scale): result[i] = value
    result[12:15] = position; result[15] = 1.0
    if perspective: result[3], result[7], result[11] = 2.0, 3.0, 4.0
    return tuple(map(bits, result))


def inverse(values):
    a = list(map(floating, values)); result = [0.0]*16
    for i in (0, 5, 10): result[i] = divide(1.0, a[i])
    for axis, i in enumerate((0, 5, 10)):
        result[12+axis] = -rounded(a[12+axis]*result[i])
    result[15] = 1.0
    return tuple(map(bits, result))


def multiply(left, right):
    a, b = list(map(floating, left)), list(map(floating, right)); result = []
    for row in range(4):
        for col in range(4):
            value = rounded(a[row*4]*b[col])
            for k in range(1, 4): value = rounded(value+rounded(a[row*4+k]*b[k*4+col]))
            result.append(bits(value))
    return tuple(result)


def outputs(values):
    return (*values[12:15], 0, 0x80000000, 0, values[0], values[5], values[10])


def fixture(slot=7, index=3, offset=1, absolute=0, group=2, kind=1, phase=0,
        symbols=screen.SYMBOLS, record=RECORD, zero=False):
    actor = address(symbols['D_800CC2D0'], slot, 812)
    control = address(symbols['D_800C6660'], slot, 16)
    memory = {STACK+i: 0xA5 for i in range(-0x600, 0x140)}
    for base, length in ((actor-0x80, 0x3BC), (control-16, 48), (record-16, 136)):
        memory.update({(base+i) & 0xFFFFFFFF: (i*17+0x35) & 255 for i in range(length)})
    for base in (BANK, OTHER):
        for matrix_index in {kind, 0, 1, 2, (index+offset) & 0xFFFFFFFF}:
            start = address(base, matrix_index, 64)
            for i, value in enumerate(matrix((1.0, 2.0, 4.0), (1.0, 2.0, 3.0), False)):
                put(memory, start+i*4, value)
        start = address(base, index+offset, 64)
        selected = matrix(position=(1.25, 27.5, 8.0) if zero else (5.0, 34.0, -3.0))
        for i, value in enumerate(selected): put(memory, start+i*4, value)
    for g in {group, 0, 1, 2, 255}:
        put(memory, symbols['D_80084454']+g*4, TYPES+g*512)
        for i in {index, 0, 1, 2, 3, 4, 5}:
            put(memory, (TYPES+g*512+i) & 0xFFFFFFFF, kind, 1)
    put(memory, actor+0x1D4, BANK)
    for i, value in enumerate((1.25, -2.5, 8.0)): put(memory, actor+0x14+i*4, bits(value))
    put(memory, control+14, group, 1)
    args = (slot & 0xFFFFFFFF, index & 0xFFFFFFFF, offset & 0xFFFFFFFF, record, absolute & 0xFFFFFFFF)
    put(memory, STACK+phase+16, args[4])
    return memory, args


def actions_for(mode, args, phase=0, symbols=screen.SYMBOLS):
    slot, index, _, _, _ = args; actor = address(symbols['D_800CC2D0'], slot, 812)
    control = address(symbols['D_800C6660'], slot, 16); caller = STACK+phase
    return {
        'bank': {('copy', 0): ((actor+0x1D4, OTHER, 4),)},
        'group': {('copy', 0): ((control+14, 1, 1), (TYPES+512+signed(index), 0xFF, 1))},
        'absolute-home': {('copy', 0): ((caller+16, 1, 4),)},
        'index-home': {('copy', 0): ((caller+4, 0, 4),)},
        'slot-home': {('copy', 0): ((caller, 0, 4),)},
        'cached-actor': {('copy', 0): ((caller, 0, 4), (actor+0x1D4, OTHER, 4)),
            ('decompose', 0): ((actor+0x14, bits(-2.0), 4),)},
        'position': {('decompose', 0): ((actor+0x14, bits(20.0), 4),
            (actor+0x18, bits(-10.0), 4), (actor+0x1C, bits(5.0), 4))},
    }.get(mode, {})


class Reference:
    def __init__(self, memory, args, phase=0, symbols=screen.SYMBOLS, actions=None, result=None):
        self.memory = memory.copy(); self.args, self.symbols = args, symbols
        self.caller, self.actions, self.result = STACK+phase, actions or {}, result
        self.calls, self.occurrences = [], {}
        for i, arg in enumerate(args[:3]): put(self.memory, self.caller+i*4, arg)
    def get(self, a, size=4): return read(self.memory, a & 0xFFFFFFFF, size)
    def put(self, a, value, size=4): put(self.memory, a & 0xFFFFFFFF, value, size)
    def mutate(self, label):
        n = self.occurrences.get(label, 0); self.occurrences[label] = n+1
        for a, value, size in self.actions.get((label, n), ()): self.put(a, value, size)
    def call(self, name, args):
        target = self.symbols[name]; self.calls.append((target, *args))
        label = {'bcopy': 'copy', 'func_150499A0': 'inverse',
            'func_150A7A48': 'multiply', 'func_1503E5F8': 'decompose'}[name]
        self.mutate(label)
        if name == 'bcopy':
            a, b, count = args; data = [self.get(a+i, 1) for i in range(count)]
            for i, value in enumerate(data): self.put(b+i, value, 1)
        elif name == 'func_150499A0':
            values = inverse(tuple(self.get(args[0]+i*4) for i in range(16)))
            for i, value in enumerate(values): self.put(args[1]+i*4, value)
        elif name == 'func_150A7A48':
            values = multiply(tuple(self.get(args[0]+i*4) for i in range(16)),
                tuple(self.get(args[1]+i*4) for i in range(16)))
            for i, value in enumerate(values): self.put(args[2]+i*4, value)
        else:
            values = self.result or outputs(tuple(self.get(args[0]+i*4) for i in range(16)))
            for a, value in zip(args[1:], values): self.put(a, value)
    def run(self):
        slot, index, offset, record, _ = self.args; s = self.symbols
        actor = address(s['D_800CC2D0'], slot, 812)
        frame = self.caller-0xD8; primary, other = frame+0x94, frame+0x54
        source = address(self.get(actor+0x1D4), index+offset, 64)
        self.call('bcopy', (source, primary, 64))
        kind = -1
        if not self.get(self.caller+16):
            slot, index = self.get(self.caller), self.get(self.caller+4)
            group = self.get(address(s['D_800C6660'], slot, 16)+14, 1)
            table = self.get(s['D_80084454']+group*4)
            value = self.get(table+signed(index), 1); kind = value if value < 128 else value-256
        if kind != -1:
            self.call('func_150499A0', (address(self.get(actor+0x1D4), kind, 64), other))
            for i, value in ((7, 0), (3, 0), (11, 0), (15, 0x3F800000)): self.put(primary+i*4, value)
            self.call('func_150A7A48', (primary, other, primary))
        self.call('func_1503E5F8', (primary, *(record+i*4 for i in range(9))))
        for i in range(9): self.put(record+(9+i)*4, self.get(record+i*4))
        x = rounded(floating(self.get(record+36))-floating(self.get(actor+20)))
        y = rounded(rounded(floating(self.get(record+40))-floating(self.get(actor+24)))-30.0)
        z = rounded(floating(self.get(record+44))-floating(self.get(actor+28)))
        squared = rounded(rounded(rounded(x*x)+rounded(y*y))+rounded(z*z))
        length = rounded(math.sqrt(squared)); reciprocal = divide(1.0, length if length != 0.0 else 1.0)
        for i, value in enumerate((x, y, z)): self.put(record+72+i*4, bits(rounded(value*reciprocal)))
        return self


class SetupOracle(state.StateOracle):
    def __init__(self, words, memory, args, phase=0, symbols=screen.SYMBOLS, actions=None,
            result=None, connected=None, entry=screen.ENTRY):
        guest.AttachmentOracle.__init__(self, words, memory, arguments=args, phase=phase,
            connected=connected, entry=entry)
        self.args, self.symbols, self.actions, self.result = args, symbols, actions or {}, result
        self.occurrences, self.chain_actor, self.allocation = {}, None, state.BUFFER
    def execute(self, word):
        op, rs, rt, rd, dst, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 17 and rs == 16 and fn in (4, 7):
            if fn == 7: self.f[dst] = self.f[rd] ^ 0x80000000
            else:
                value = floating(self.f[rd]); self.f[dst] = bits(math.sqrt(value) if value >= 0 else math.nan)
        elif op == 0 and fn == 32:
            value = signed(self.r[rs])+signed(self.r[rt]); assert -0x80000000 <= value < 0x80000000
            self.r[rd] = value & 0xFFFFFFFF
        else: super().execute(word)
    def record_call(self, target):
        names = {self.symbols[n]: n for n in ('bcopy', 'func_150499A0', 'func_150A7A48', 'func_1503E5F8')}
        if target in names:
            label = {'bcopy': 'copy', 'func_150499A0': 'inverse',
                'func_150A7A48': 'multiply', 'func_1503E5F8': 'decompose'}[names[target]]
            count = {'copy': 3, 'inverse': 2, 'multiply': 3, 'decompose': 10}[label]
            args = self.arguments(count); self.calls.append((target, *args)); self.events.append(('CALL', target, args))
            self.mutate(label)
        else:
            super().record_call(target)
            if target == screen.ENTRY: self.mutate('setup')
    def hook(self, target):
        names = {self.symbols[n]: n for n in ('bcopy', 'func_150499A0', 'func_150A7A48', 'func_1503E5F8')}
        if target not in names: return super().hook(target)
        name = names[target]; args = self.calls[-1][1:]
        if name == 'bcopy':
            source, destination, count = args; values = [self.get(source+i, 1) for i in range(count)]
            for i, value in enumerate(values): self.put(destination+i, value, 1)
        elif name == 'func_150499A0':
            values = inverse(tuple(self.get(args[0]+i*4, 4) for i in range(16)))
            for i, value in enumerate(values): self.put(args[1]+i*4, value, 4)
        elif name == 'func_150A7A48':
            values = multiply(tuple(self.get(args[0]+i*4, 4) for i in range(16)),
                tuple(self.get(args[1]+i*4, 4) for i in range(16)))
            for i, value in enumerate(values): self.put(args[2]+i*4, value, 4)
        else:
            values = self.result or outputs(tuple(self.get(args[0]+i*4, 4) for i in range(16)))
            for a, value in zip(args[1:], values): self.put(a, value, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.r[2] = 0xA5000002


class GameRecordTransformSetupMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-transform-setup-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'f9e9a919dfbae01d337e9a7c5130e52d5f6f518070f8822f2dd72247535150ef'
        assert cls.baseline['elf'] == '25dd5c57a0dfcffa127574c1a9402176167c67cfe3b4ef1b74e93d5066b46d54'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>141I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        source = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1]
        body = source.split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot, filename='generated_6B320'))

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def link(self, name, start=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()],
            '--defsym=D_800C666E=D_800C6660+14', '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>141I', sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def compare(self, memory, args, phase=0, actions=None, result=None, symbols=screen.SYMBOLS,
            start=screen.ENTRY, forms=None, connected=None):
        expected = Reference(memory, args, phase, symbols, actions, result).run()
        models = [SetupOracle(w, memory, args, phase, symbols, actions, result, connected, start).run()
            for w in forms or (self.retail, self.raw, self.padded)]
        for model in models: self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
        for model in models[1:]:
            self.assertEqual((model.r, model.f, model.lo, model.memory, model.events),
                (models[0].r, models[0].f, models[0].lo, models[0].memory, models[0].events))
        return models

    def test_01_direct_complete_body_frame_and_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']), (141, 216, 0, 0))
        self.assertEqual(self.meta['diagnostics'], ''); self.assertEqual(self.raw, self.retail)
        self.assertEqual(self.padded, self.retail); self.assertEqual(self.link('original'), self.retail)
        for profile in ('compact', 'o1g3', 'o1'):
            meta, words = screen.compile_candidate(self.root, self.out, profile, profile=profile)
            if profile == 'compact': self.assertEqual((meta['body_words'], meta['frame'], words), (141, 216, self.raw))
            else: self.assertNotEqual(words, self.retail)
        self.receipt('shape', words=141, frame=216, extent=564, direct=True, guards=0, no_profile_change=True)

    def test_02_full_absolute_domain_signed_types_offsets_and_zero_length(self):
        cases, reached = 0, set()
        for kind, absolute, phase, zero in itertools.product((-128, -2, -1, 0, 1, 2, 127),
                (0, 1, -1, 256, 0x80000000), (0, 8), (False, True)):
            memory, args = fixture(kind=kind, absolute=absolute, phase=phase, zero=zero)
            models = self.compare(memory, args, phase); reached.update(models[0].visits); cases += 1
        for slot, index, offset, group in itertools.product((0, 25, -1, 0x80000000), (0, 5, -1), (-1, 0, 1), (0, 255)):
            memory, args = fixture(slot=slot, index=index, offset=offset, group=group, kind=-1)
            self.compare(memory, args); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+564, 4))), 141)
        self.receipt('guest', cases=cases, forms=3, all_words=141, signed_minus1_only=True,
            absolute_full_width=True, invalid_slots_types_indices_mapped_guest_only=True, zero_length_fallback=True)

    def test_03_callback_live_homes_cached_actor_and_public_aliases(self):
        cases = 0
        for mode, phase in itertools.product(('bank', 'group', 'absolute-home', 'index-home', 'slot-home', 'cached-actor', 'position'), (0, 8)):
            memory, args = fixture(phase=phase)
            if mode in ('slot-home', 'cached-actor'): put(memory, screen.SYMBOLS['D_800C6660']+14, 0, 1)
            self.compare(memory, args, phase, actions_for(mode, args, phase)); cases += 1
        actor = screen.SYMBOLS['D_800CC2D0']+7*812
        for record, phase in itertools.product((actor, actor+20, actor-36, actor-40), (0, 8)):
            memory, args = fixture(record=record, phase=phase); self.compare(memory, args, phase); cases += 1
        self.receipt('lifetimes', cases=cases, full_width_homes_live_after_copy=True,
            actor_and_record_cached=True, actor_bank_group_index_absolute_reads_live=True,
            external_caller_saved_GPR_FPR_clobbered=True, aliases_guest_only=True)

    def test_04_independent_relocations_and_private_matrix_pointers(self):
        cases = 0
        for link, start in enumerate((0x15207FFC, 0x15308004)):
            symbols = {n: (0x80107FFC if i % 2 == link else 0x80218004)+i*0x10000 for i, n in enumerate(screen.SYMBOLS)}
            for i, name in enumerate(('bcopy', 'func_150499A0', 'func_150A7A48', 'func_1503E5F8')):
                symbols[name] = 0x15408004+i*0x10000
            forms = tuple(self.link(n, start, symbols) for n in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[1]); self.assertEqual(forms[0], forms[2])
            for kind, phase, mode in itertools.product((-1, 1), (0, 8), ('none', 'bank', 'position')):
                memory, args = fixture(kind=kind, phase=phase, symbols=symbols)
                self.compare(memory, args, phase, actions_for(mode, args, phase, symbols), symbols=symbols, start=start, forms=forms); cases += 1
        self.receipt('rebases', symbols=7, links=2, cases=cases, independent_HI_LO_JAL=True,
            private_primary_94_inverse_54_and_ten_argument_outputs_exact=True)

    def test_05_fired_fault_prefixes_all_private_and_public_accesses(self):
        pairs = 0
        for kind, phase in ((-1, 0), (1, 8)):
            memory, args = fixture(kind=kind, phase=phase)
            complete = SetupOracle(self.retail, memory, args, phase).run()
            for fault in range(complete.accesses):
                models = [SetupOracle(w, memory, args, phase) for w in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, fault)
                for model in models[1:]:
                    self.assertEqual((model.memory, model.events, model.r, model.f),
                        (models[0].memory, models[0].events, models[0].r, models[0].f))
                pairs += 1
        self.receipt('faults', fired_triplets=pairs, exact_private_and_public=True, not_portable_C_fault_or_FCSR_proof=True)

    def test_06_fresh_semantic_controls_and_private_overlap(self):
        controls = (
            ('unsigned-type', screen.SELECTED.replace('type = D_80084454', 'type = ((u8 **)D_80084454)'), -2, 'none', None),
            ('wrong-gate', screen.SELECTED.replace('type != -1', 'type != -2'), -1, 'none', None),
            ('byte-absolute', screen.SELECTED.replace('if (absolute != 0)', 'if ((u8)absolute != 0)'), 1, 'none', None),
            ('cached-bank', screen.SELECTED.replace('    s32 type;', '    s32 type;\n    struct255 *bank;').replace(
                '    actor = &D_800CC2D0[slot];', '    actor = &D_800CC2D0[slot];\n    bank = actor->unk1D4;').replace(
                '(f32 (*)[4][4])actor->unk1D4', '(f32 (*)[4][4])bank'), 1, 'bank', None),
            ('reversed-multiply', screen.SELECTED.replace('func_150A7A48(matrix, inverse, matrix)', 'func_150A7A48(inverse, matrix, matrix)'), 1, 'none', None),
            ('missing-snapshot', screen.SELECTED.replace('    ((f32 *)record)[11] = ((f32 *)record)[2];\n', ''), -1, 'none', None),
            ('missing-height', screen.SELECTED.replace(' - 30.0f', ' - 0.0f'), -1, 'none', None),
            ('missing-zero-fallback', screen.SELECTED.replace('length = 1.0f;', 'length = 0.0f;'), -1, 'none', (bits(1.25), bits(27.5), bits(8.0), 0, 0, 0, bits(1), bits(1), bits(1))))
        for name, body, kind, mode, result in controls:
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            memory, args = fixture(kind=kind, absolute=256 if name == 'byte-absolute' else 0)
            if name == 'unsigned-type':
                for i, value in enumerate(matrix((1.0, 2.0, 4.0), (1.0, 2.0, 3.0), False)):
                    put(memory, BANK+254*64+i*4, value)
            actions = actions_for(mode, args)
            expected = Reference(memory, args, actions=actions, result=result).run()
            # Longer controls must not overlap a retail callee in the code map.
            model = SetupOracle(words, memory, args, actions=actions, result=result, entry=0x1523E3C4).run()
            def observable(calls):
                return [(call[0], *(a for a in call[1:] if not STACK-0x600 <= a < STACK+0x140)) for call in calls]
            self.assertNotEqual((public(model.memory), observable(model.calls)),
                (public(expected.memory), observable(expected.calls)), name)
        for phase in (0, 8):
            memory, args = fixture(record=STACK+phase-0xD8+0x94, phase=phase, kind=-1)
            models = [SetupOracle(w, memory, args, phase).run() for w in (self.retail, self.raw, self.padded)]
            for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                (models[0].memory, models[0].events, models[0].r, models[0].f))
        self.receipt('controls', fresh_semantic=8, all_effective=True, private_matrix_record_overlap_cases=2,
            private_overlap_guest_only=True, native_no_alias_or_FCSR_claim=True)

    def test_07_complete_owner_neighbors_caller_and_both_real_padders(self):
        before = (self.out/'before-source').read_text(); objects = []
        for stage, source in (('before', before), ('after', screen.install(before))):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-'+stage)
            subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')), '--post-process',
                str(obj.relative_to(self.root/'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker', check=True, capture_output=True)
            self.assertEqual(warnings, []); objects.append(obj)
        def fingerprint(obj, name):
            text, functions, relocations = parse_object(obj); item = functions[name]
            a, b = item['value'], item['value']+item['size']
            return item['size'], text[a:b], {o-a: r for o, r in relocations.items() if a <= o < b}
        names = set(parse_object(objects[0])[1]); self.assertEqual(names, set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}: self.assertEqual(fingerprint(objects[0], name), fingerprint(objects[1], name), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1], screen.FUNCTION), fingerprint(self.out/'selected.o', screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py', 'pad_generated_object.py'):
            parsed = []
            for stage, obj in zip(('before', 'after'), objects):
                asm = self.out/(route+'-'+stage+'.s')
                args = [str(obj), str(self.out/'before-layout'), 'generated_6B320', str(asm)] if route == 'pad_c_object.py' else [
                    str(obj), str(self.root/'conker/asm/6B320.s'), str(asm), '--filename', 'generated_6B320']
                subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches', str(self.out/'before-guards')],
                    check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)],
                    check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+564] = parsed[1][0][start:start+564]
            self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o: r for o, r in parsed[0][2].items() if not start <= o < start+564},
                {o: r for o, r in parsed[1][2].items() if not start <= o < start+564})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', unchanged_neighbors=len(names)-1, typed_void_contract_no_caller_body_edit=True,
            actual_dispatcher171_unchanged=True, GLOBAL_ASM_decomposer141_preserved=True, pools_exact=True, both_padders=True)

    def test_08_literal_source_whole_ELF_and_all_other_inputs(self):
        before_source = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text()
        now = current != before_source
        self.assertEqual(current, screen.install(before_source) if now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 564)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if now: struct.pack_into('>141I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 564)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            if name not in ('source', 'elf'): self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes(), name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+564], actual[start:start+564])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), literal_no_projection_or_metadata_exception=True,
            seven_other_inputs_exact=True, guard_history_no_changes=True, protected_data=data)

    def test_09_effective_stale_source_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text(); qualified = screen.install(before)
        for stale in (qualified, before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        rt, rb = Path.read_text, Path.read_bytes
        source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: actual+'\n' if p == source else rt(p, *a, **k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_all_other_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        start = elf_slot_offset(actual, screen.ENTRY, 564); extent = installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)
        for offset in (start+4, start+564, extent+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_all_other_inputs()
        guards = self.root/self.paths['guards']; wrong = guards.read_bytes()+b'\n'
        with patch.object(Path, 'read_bytes', lambda p: wrong if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_all_other_inputs()
        self.receipt('integrity-controls', stale_installs=2, source_rejection=1, ELF_rejections=3,
            guard_rejection=1, all_effective=True, production_inputs_not_mutated=True)

    def test_10_native32_bounded_finite_outputs_callbacks_and_controls(self):
        prefix = r'''
typedef unsigned char u8; typedef signed char s8; typedef int s32; typedef float f32;
typedef struct { f32 value[26]; } struct04;
typedef struct { u8 bytes[16]; } struct106;
typedef struct { f32 value[8][4][4]; } struct255;
typedef struct { u8 prefix[20]; f32 x_position, y_position, z_position;
    u8 middle[436]; struct255 *unk1D4; u8 suffix[340]; } struct127;
typedef char actor_size[sizeof(struct127)==812 ? 1 : -1];
typedef char record_size[sizeof(struct04)==104 ? 1 : -1];
struct127 D_800CC2D0[26]; struct106 D_800C6660[26];
static s8 types[3][8]; s8 *D_80084454[3]={types[0],types[1],types[2]};
static struct255 bank, other; static int mode, current_slot, current_index, calls, bad;
static struct04 *destination;
float sqrtf(float value) { float result; __asm__("sqrtss %1,%0":"=x"(result):"x"(value)); return result; }
static unsigned word(float value) { union { float f; unsigned u; } v; v.f=value; return v.u; }
void bcopy(const void *a, void *b, unsigned count) {
    const u8 *source=a; u8 *target=b;
    if(mode==1) D_800CC2D0[current_slot].unk1D4=&other;
    if(mode==2) D_800C6660[current_slot].bytes[14]=1;
    for(unsigned i=0;i<count;i++) target[i]=source[i];
    calls++;
}
void func_150499A0(f32 a[4][4], f32 b[4][4]) {
    for(int r=0;r<4;r++) for(int c=0;c<4;c++) b[r][c]=0;
    for(int i=0;i<3;i++) { b[i][i]=1.0f/a[i][i]; b[3][i]=-a[3][i]*b[i][i]; }
    b[3][3]=1; calls++;
}
void func_150A7A48(f32 a[4][4], f32 b[4][4], f32 out[4][4]) {
    f32 result[4][4];
    for(int r=0;r<4;r++) for(int c=0;c<4;c++) {
        f32 v=a[r][0]*b[0][c]; for(int k=1;k<4;k++) v=v+a[r][k]*b[k][c]; result[r][c]=v;
    }
    for(int r=0;r<4;r++) for(int c=0;c<4;c++) out[r][c]=result[r][c];
    calls++;
}
void func_1503E5F8(f32 a[4][4], f32 *x, f32 *y, f32 *z, f32 *rx, f32 *ry,
    f32 *rz, f32 *sx, f32 *sy, f32 *sz) {
    f32 *p[9]={x,y,z,rx,ry,rz,sx,sy,sz};
    for(int i=0;i<9;i++) if(p[i]!=&destination->value[i]) bad=1;
    *x=a[3][0]; *y=a[3][1]; *z=a[3][2]; *rx=0; *ry=-0.0f; *rz=0;
    *sx=a[0][0]; *sy=a[1][1]; *sz=a[2][2];
    if(mode==3) D_800CC2D0[current_slot].x_position=20.0f;
    calls++;
}
'''
        suffix = r'''
static int run(unsigned *failure) {
    int n=0; const int slots[3]={0,7,25}, absolutes[4]={0,1,256,-1};
    for(int si=0;si<3;si++) for(int ii=0;ii<2;ii++) for(int off=-1;off<=1;off++)
    for(int kind=-1;kind<=1;kind++) for(int ai=0;ai<4;ai++) for(mode=0;mode<4;mode++)
    for(int zero=0;zero<2;zero++) {
        struct04 record; f32 expected[26], primary[4][4], inv[4][4], transformed[4][4];
        current_slot=slots[si]; current_index=1+ii*2; calls=bad=0; destination=&record;
        struct127 *actor=&D_800CC2D0[current_slot]; actor->unk1D4=&bank;
        actor->x_position=1.25f; actor->y_position=-2.5f; actor->z_position=8.0f;
        D_800C6660[current_slot].bytes[14]=2; types[1][current_index]=-1; types[2][current_index]=kind;
        for(int i=0;i<8;i++) for(int r=0;r<4;r++) for(int c=0;c<4;c++) {
            f32 v=r==c ? (r==3 ? 1.0f : (f32)(r+1+i)) : 0;
            if(r==3 && c<3) v=(f32)(c+1+i);
            bank.value[i][r][c]=v; other.value[i][r][c]=v+(r==c && r<3 ? 2.0f : 0.0f);
        }
        int selected=current_index+off;
        if(zero) { bank.value[selected][3][0]=1.25f; bank.value[selected][3][1]=27.5f; bank.value[selected][3][2]=8.0f; }
        bank.value[selected][0][3]=2; bank.value[selected][1][3]=3; bank.value[selected][2][3]=4;
        for(int r=0;r<4;r++) for(int c=0;c<4;c++) primary[r][c]=bank.value[selected][r][c];
        int live_kind=(absolutes[ai] || mode==2) ? -1 : kind, expected_calls=2;
        if(live_kind!=-1) {
            f32 (*a)[4]=mode==1 ? other.value[live_kind] : bank.value[live_kind];
            for(int r=0;r<4;r++) for(int c=0;c<4;c++) inv[r][c]=0;
            for(int i=0;i<3;i++) { inv[i][i]=1.0f/a[i][i]; inv[3][i]=-(a[3][i]*inv[i][i]); }
            inv[3][3]=1; primary[0][3]=primary[1][3]=primary[2][3]=0; primary[3][3]=1;
            for(int r=0;r<4;r++) for(int c=0;c<4;c++) {
                f32 v=primary[r][0]*inv[0][c]; for(int k=1;k<4;k++) v=v+primary[r][k]*inv[k][c]; transformed[r][c]=v;
            }
            for(int r=0;r<4;r++) for(int c=0;c<4;c++) primary[r][c]=transformed[r][c];
            expected_calls=4;
        }
        for(int i=0;i<26;i++) record.value[i]=expected[i]=(f32)(100+i);
        expected[0]=primary[3][0]; expected[1]=primary[3][1]; expected[2]=primary[3][2];
        expected[3]=0; expected[4]=-0.0f; expected[5]=0;
        expected[6]=primary[0][0]; expected[7]=primary[1][1]; expected[8]=primary[2][2];
        for(int i=0;i<9;i++) expected[i+9]=expected[i];
        f32 dx=expected[9]-(mode==3 ? 20.0f : 1.25f), dy=(expected[10]-(-2.5f))-30.0f, dz=expected[11]-8.0f;
        f32 length=sqrtf((dx*dx+dy*dy)+dz*dz); if(length==0) length=1;
        f32 reciprocal=1.0f/length; expected[18]=dx*reciprocal; expected[19]=dy*reciprocal; expected[20]=dz*reciprocal;
        func_1503E3C4(current_slot,current_index,off,&record,absolutes[ai]); n++;
        if(bad || calls!=expected_calls) { failure[0]=n; failure[1]=99; failure[2]=calls; return 1; }
        for(int i=0;i<26;i++) if(word(record.value[i])!=word(expected[i])) {
            failure[0]=n; failure[1]=i; failure[2]=word(record.value[i]); return 1;
        }
    }
    return n==1728 ? 0 : 2;
}
void _start(void) {
    unsigned failure[3]; int result=run(failure);
    if(result) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable();
}
'''
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:], prefix+screen.SELECTED+suffix, profile), (0, ''))
        for name, body in (('height', screen.SELECTED.replace(' - 30.0f', ' - 0.0f')),
                ('sentinel', screen.SELECTED.replace('type != -1', 'type != 0')),
                ('zero', screen.SELECTED.replace('length = 1.0f;', 'length = 0.0f;'))):
            # The sentinel control stays inside the native bank's valid domain.
            control = suffix.replace('kind=-1', 'kind=0') if name == 'sentinel' else suffix
            if name == 'sentinel': control = control.replace('ai=0;ai<4', 'ai=0;ai<1').replace('mode=0;mode<4', 'mode=0;mode<1')
            result, detail = self.run_native('native-negative-'+name, prefix+body+control)
            self.assertEqual(result, 1); self.assertEqual(len(detail), 3)
        self.receipt('native', cases_per_profile=1728, profiles=['O2', 'O0'], full_record_26_words=True,
            callbacks_bank_group_position=True, effective_controls=3, modeled_callees=True,
            no_native_argument_home_alias_invalid_index_or_FCSR_claim=True)

    def test_11_connected_retail_copy_inverse_and_multiply(self):
        functions, _, addresses = load_elf_functions(self.out/'before-elf', 'mips-linux-gnu-objdump')
        copy = functions['bcopy']; self.assertEqual(addresses['bcopy'], COPY)
        self.assertEqual(copy, list(struct.unpack_from('>%dI' % len(copy), self.rom, COPY-0x10000000)))
        bodies = {COPY: copy, INVERT: list(struct.unpack_from('>166I', self.rom, 0x76E50)),
            MULTIPLY: list(struct.unpack_from('>76I', self.rom, 0xD4EF8))}
        connected = {a+i*4: w for a, body in bodies.items() for i, w in enumerate(body)}
        cases = 0
        for kind, phase, mode in itertools.product((-1, 1), (0, 8), ('none', 'bank', 'position')):
            memory, args = fixture(kind=kind, phase=phase)
            self.compare(memory, args, phase, actions_for(mode, args, phase), connected=connected); cases += 1
        self.receipt('connected-helpers', cases=cases, forms=3, linked_bcopy_words=len(copy),
            retail_inverse_words=166, retail_multiply_words=76, decomposition_boundary_modeled=True,
            inverse_and_multiply_current_C_stubs_not_qualified_or_changed=True)

    def test_12_actual_dispatcher171_predicate27_setup141_chain(self):
        caller = list(struct.unpack_from('>171I', self.before, elf_slot_offset(self.before, state.screen.ENTRY, 684)))
        predicate = list(struct.unpack_from('>27I', self.before, elf_slot_offset(self.before, state.HELPER, 108)))
        self.assertEqual(caller, list(struct.unpack_from('>171I', self.rom, state.screen.ROM)))
        self.assertEqual(predicate, list(struct.unpack_from('>27I', self.rom, state.screen.ROM+684)))
        frame = (-caller[0]) & 65535; self.assertEqual(frame, 56)
        symbols = dict(state.screen.SYMBOLS, **screen.SYMBOLS)
        class ChainReference(state.Reference):
            def call(ref, target, args):
                result = super().call(target, args)
                if target == screen.ENTRY:
                    setup = Reference(ref.memory, args, ref.phase-frame, symbols, ref.actions).run()
                    ref.memory = setup.memory; ref.calls.extend(setup.calls)
                return result
        cases = 0
        for count, status, phase, mutate in itertools.product((0, 1, 3, 4), (2, 3), (0, 8), (False, True)):
            memory, args = fixture(index=0, offset=0, kind=-1, symbols=symbols, phase=phase)
            chain_bank = 0x70000
            bank_memory = {a-BANK+chain_bank: v for a, v in memory.items() if BANK <= a < BANK+8*64}
            for index in range(count):
                for i, value in enumerate(matrix(position=(5.0+index, 34.0, -3.0))):
                    put(bank_memory, chain_bank+index*64+i*4, value)
            memory = state.fixture(state=status, count=count, slot=7, types=(255, 254, 255, 255), symbols=symbols)
            memory.update(bank_memory); memory.update({STACK+i: 0xA5 for i in range(-0x600, 0x140)})
            actor = symbols['D_800CC2D0']+7*812; put(memory, actor+0x1D4, chain_bank)
            for i, value in enumerate((1.25, -2.5, 8.0)): put(memory, actor+20+i*4, bits(value))
            control = symbols['D_800C6660']+7*16
            actions = {('decompose', 0): ((actor+20, bits(20.0), 4),)} if mutate else {}
            expected = ChainReference(memory, symbols=symbols, actions=actions); expected.phase=phase; expected.run()
            forms = []
            for body in (self.retail, self.raw, self.padded):
                connected = {a+i*4: w for a, words in ((screen.ENTRY, body), (state.HELPER, predicate)) for i, w in enumerate(words)}
                model = SetupOracle(caller, memory, (7,), phase, symbols, actions, connected=connected, entry=state.screen.ENTRY).run()
                self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
                forms.append(model)
            for model in forms[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                (forms[0].memory, forms[0].events, forms[0].r, forms[0].f))
            self.assertEqual(read(forms[0].memory, control+15, 1), 1)
            cases += 1
        self.receipt('connected-caller', cases=cases, dispatcher_words=171, predicate_words=27, setup_words=141,
            independent_composed_reference=True, live_position_callback=True, allocation_flags_and_state_publish=True,
            other_callees_modeled_not_full_gameplay_qualification=True)

    def test_13_guest_payload_snapshots_and_rounding_boundaries(self):
        vectors = ((0, 0, 0), (0x80000000, 0, 0), (1, 2, 3), (0x80000001, 1, 0),
            (bits(1.0e-20), bits(-1.0e-20), bits(1.0e-20)),
            (bits(1.0e20), bits(-1.0e20), bits(1.0)),
            (0x7F800000, 0, 0), (0xFF800000, 0, 0),
            (0x7FC12345, 0, 0), (bits(1.0000001192092896), bits(1.5), bits(-2.5)))
        cases = 0
        for vector, phase in itertools.product(vectors, (0, 8)):
            memory, args = fixture(kind=-1, phase=phase)
            actor = screen.SYMBOLS['D_800CC2D0']+7*812
            for i, value in enumerate((0.0, -30.0, 0.0)): put(memory, actor+20+i*4, bits(value))
            result = (*vector, 0x80000000, 0x7FC23456, 1, 0x7F800000, 0xFF800000, 0x80000001)
            if any(v & 0x7F800000 == 0x7F800000 and v & 0x7FFFFF for v in vector):
                models = [SetupOracle(w, memory, args, phase, result=result).run() for w in (self.retail, self.raw, self.padded)]
                for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                    (models[0].memory, models[0].events, models[0].r, models[0].f))
            else:
                models = self.compare(memory, args, phase, result=result)
            for model in models:
                self.assertEqual(tuple(read(model.memory, RECORD+36+i*4) for i in range(9)), result)
            cases += 1
        self.receipt('payloads', cases=cases, exact_nine_word_backup_payloads=True,
            signed_zero_subnormal_overflow_infinity_NaN=True,
            NaN_direction_compares_machine_forms_only=True,
            guest_host_float_model_only_not_hardware_FCSR_or_NaN_propagation_proof=True)


if __name__ == '__main__':
    unittest.main()
