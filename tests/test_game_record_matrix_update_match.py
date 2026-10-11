"""Complete matrix rebuild, live/cached lifetimes and literal linked audit."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_matrix_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests import test_game_record_transform_setup_match as setup
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, BUFFER, OTHER, THIRD, BANK, BANK2, TYPES = guest.STACK, 0x24000, 0x34000, 0x44000, 0x70000, 0x90000, 0x50000
FACTOR = 0x3C8EFA35
TRANSLATE, ROTATE, SCALE, MULTIPLY, FINISH = (screen.SYMBOLS[n] for n in
    ('func_150A7DA0', 'func_150A8050', 'func_150A7CB0', 'func_150A7A48', 'func_15043EC8'))
WIDTHS = dict(translate=4, rotate=4, scale=4, multiply=3, finish=7)
LABELS = {TRANSLATE: 'translate', ROTATE: 'rotate', SCALE: 'scale', MULTIPLY: 'multiply', FINISH: 'finish'}
address, rounded, multiply = state.address, setup.rounded, setup.multiply


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x800 <= a < STACK+0x140}


def identity():
    return tuple(bits(1.0) if i in (0, 5, 10, 15) else 0 for i in range(16))


def rotation(angles, factor=FACTOR):
    radians = [rounded(floating(a)*floating(factor)) for a in angles]
    cx, cy, cz = [rounded(math.cos(a)) for a in radians]
    sx, sy, sz = [rounded(math.sin(a)) for a in radians]
    product = lambda a, b: rounded(a*b)
    xy, yy = product(sx, sy), product(cx, sy)
    values = (product(cy, cz), product(cy, sz), -sy, 0.0,
        rounded(product(xy, cz)-product(cx, sz)), rounded(product(xy, sz)+product(cx, cz)), product(sx, cy), 0.0,
        rounded(product(yy, cz)+product(sx, sz)), rounded(product(yy, sz)-product(sx, cz)), product(cx, cy), 0.0,
        0.0, 0.0, 0.0, 1.0)
    return tuple(map(bits, values))


def transformed(label, args, memory):
    if label == 'translate':
        values = list(identity()); values[12:15] = args[1:]; return tuple(values)
    if label == 'scale':
        values = [0]*16
        for i, value in zip((0, 5, 10), args[1:]): values[i] = value
        values[15] = bits(1.0); return tuple(values)
    if label == 'rotate': return rotation(args[1:])
    if label == 'multiply':
        return multiply(tuple(read(memory, args[0]+i*4) for i in range(16)),
            tuple(read(memory, args[1]+i*4) for i in range(16)))
    values = [read(memory, args[0]+i*4) for i in range(16)]
    values[12:15] = args[4:]
    for row, scale in enumerate(args[1:4]):
        for col in range(3):
            i = row*4+col; values[i] = bits(rounded(floating(values[i])*floating(scale)))
    return tuple(values)


def fixture(count=4, kinds=(-1, -2, 1, 0), flag=1, slot=7, group=2, phase=0,
        symbols=screen.SYMBOLS, bank=BANK, buffer=BUFFER):
    actor = address(symbols['D_800CC2D0'], slot, 812)
    control = address(symbols['D_800C6660'], slot, 16)
    memory = {STACK+i: 0xA5 for i in range(-0x800, 0x140)}
    memory.update({actor+i: 0x35 for i in range(-16, 844)})
    put(memory, actor+0x1D4, bank)
    if not bank: return memory
    memory.update({control+i: 0x35 for i in range(-16, 48)})
    put(memory, control, buffer); put(memory, control+14, group, 1)
    for g in {0, 1, 2, group, 255}:
        put(memory, symbols['D_80098914']+g, count, 1)
        put(memory, symbols['D_80084454']+g*4, TYPES+g*512)
        for index in range(count): put(memory, TYPES+g*512+index, kinds[index % len(kinds)], 1)
    for base in {buffer, OTHER, THIRD}:
        memory.update({base+i: 0x35 for i in range(-16, count*104+32)})
        for index in range(count):
            for i, value in enumerate((5.25+(base-BUFFER)/65536, 34.5+index, -3.0,
                    15.0+index+(base-BUFFER)/4096, -25.0, 35.0,
                    1.5+(base-BUFFER)/65536, 2.0, 0.75)):
                put(memory, base+index*104+36+i*4, bits(value))
            put(memory, base+index*104+100, flag, 1)
    for base in {bank, BANK2}:
        for index in set(range(count)) | set(kinds):
            start = address(base, index, 64)
            for i, value in enumerate(setup.matrix((1.0, 2.0, 4.0), (2.0+index, -1.0, 3.0), False)):
                put(memory, start+i*4, value)
    put(memory, actor+0x1D4, bank); put(memory, control, buffer); put(memory, control+14, group, 1)
    return memory


def actions_for(mode, slot=7, symbols=screen.SYMBOLS):
    control = address(symbols['D_800C6660'], slot, 16)
    actor = address(symbols['D_800CC2D0'], slot, 812)
    return {
        'bank': {('translate', 0): ((actor+0x1D4, BANK2, 4),)},
        'position-buffer': {('translate', 0): ((control, OTHER, 4),)},
        'rotation-buffer': {('multiply', 0): ((control, THIRD, 4),)},
        'scale-buffer': {('rotate', 0): ((control, OTHER, 4),)},
        'cached-destination': {('rotate', 0): ((actor+0x1D4, BANK2, 4),)},
        'cached-type': {('translate', 0): ((control+14, 1, 1), (TYPES+512, 255, 1))},
        'cached-cursor-count': {('rotate', 0): ((control+14, 1, 1), (symbols['D_80098914']+2, 0, 1),
            (symbols['D_80084454']+2*4, TYPES+512, 4), (TYPES+2*512+1, 254, 1))},
        'late-snapshot': {('multiply', 1): ((control, THIRD, 4),)},
        'absolute-position': {('rotate', 0): ((BUFFER+36, bits(123.5), 4),)},
    }.get(mode, {})


class Reference:
    def __init__(self, memory, slot=7, phase=0, symbols=screen.SYMBOLS, actions=None):
        self.memory, self.slot, self.phase, self.symbols = memory.copy(), slot, phase, symbols
        self.actions, self.occurrences, self.calls = actions or {}, {}, []
    def get(self, a, size=4): return read(self.memory, a & 0xFFFFFFFF, size)
    def call(self, label, args):
        name = {'translate': 'func_150A7DA0', 'rotate': 'func_150A8050', 'scale': 'func_150A7CB0',
            'multiply': 'func_150A7A48', 'finish': 'func_15043EC8'}[label]
        self.calls.append((self.symbols[name], *args))
        n = self.occurrences.get(label, 0); self.occurrences[label] = n+1
        for a, value, size in self.actions.get((label, n), ()): put(self.memory, a, value, size)
        values = transformed(label, args, self.memory)
        destination = args[2] if label == 'multiply' else args[0]
        for i, value in enumerate(values): put(self.memory, destination+i*4, value)
    def run(self):
        s = self.symbols; actor = address(s['D_800CC2D0'], self.slot, 812)
        control = address(s['D_800C6660'], self.slot, 16)
        if not self.get(actor+0x1D4): return self
        group = self.get(control+14, 1); count = self.get(s['D_80098914']+group, 1)
        types = self.get(s['D_80084454']+group*4); temporary = STACK+self.phase-0xB8+0x64
        for index in range(count):
            if self.get(types+index, 1) == 254: continue
            element = address(self.get(control), index, 104)
            if not self.get(element+100, 1): continue
            group = self.get(control+14, 1)
            current = self.get(s['D_80084454']+group*4); kind = self.get(current+index, 1)
            kind = kind if kind < 128 else kind-256
            destination = address(self.get(actor+0x1D4), index, 64)
            if kind != -1:
                self.call('translate', (temporary, *(self.get(element+36+i*4) for i in range(3))))
                self.call('multiply', (temporary, address(self.get(actor+0x1D4), kind, 64), temporary))
                element = address(self.get(control), index, 104)
                self.call('rotate', (destination, *(self.get(element+48+i*4) for i in range(3))))
                self.call('multiply', (destination, temporary, destination))
                element = address(self.get(control), index, 104)
                self.call('scale', (temporary, *(self.get(element+60+i*4) for i in range(3))))
                self.call('multiply', (temporary, destination, destination))
            else:
                self.call('rotate', (destination, *(self.get(element+48+i*4) for i in range(3))))
                element = address(self.get(control), index, 104)
                self.call('finish', (destination, *(self.get(element+60+i*4) for i in range(3)),
                    *(self.get(element+36+i*4) for i in range(3))))
        return self


class UpdateOracle(state.StateOracle):
    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
        else: super().execute(word)
    def record_call(self, target):
        names = {self.symbols[n]: label for n, label in (('func_150A7DA0', 'translate'), ('func_150A8050', 'rotate'),
            ('func_150A7CB0', 'scale'), ('func_150A7A48', 'multiply'), ('func_15043EC8', 'finish'))}
        if target in names:
            label = names[target]; args = self.arguments(WIDTHS[label])
            self.calls.append((target, *args)); self.events.append(('CALL', target, args)); self.mutate(label)
        elif target in (0x150AD780, 0x150AD78C):
            args = (self.f[12],); self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        else: super().record_call(target)
    def hook(self, target):
        if target in (0x150AD780, 0x150AD78C):
            value = bits((math.cos if target == 0x150AD780 else math.sin)(floating(self.f[12])))
            for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000+reg
            self.f[:20] = [0xA5000000+i for i in range(20)]; self.f[0] = value
            return
        names = {self.symbols[n]: label for n, label in (('func_150A7DA0', 'translate'), ('func_150A8050', 'rotate'),
            ('func_150A7CB0', 'scale'), ('func_150A7A48', 'multiply'), ('func_15043EC8', 'finish'))}
        if target not in names: return super().hook(target)
        label, args = names[target], self.calls[-1][1:]
        values = transformed(label, args, self.memory); destination = args[2] if label == 'multiply' else args[0]
        for i, value in enumerate(values): self.put(destination+i*4, value, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.r[2] = 0xA5000002


class GameRecordMatrixUpdateMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-matrix-update-match-test'; cls.out.mkdir(exist_ok=True)
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
        assert cls.baseline['source'] == '7eb13c78160b463708784daeca18041496c8f48939092ce55c3636b93d86324f'
        assert cls.baseline['elf'] == 'f464f3d3e466ee2be9c4a2b012d21475c48d2676f9e556823d109adc9d17ebf8'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>138I', cls.rom, screen.ROM))
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
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>138I', sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def compare(self, memory, slot=7, phase=0, actions=None, symbols=screen.SYMBOLS,
            start=screen.ENTRY, forms=None, connected=None, check_reference=True):
        expected = Reference(memory, slot, phase, symbols, actions).run() if check_reference else None
        models = [UpdateOracle(w, memory, slot, symbols, phase, start, connected, actions).run()
            for w in forms or (self.retail, self.raw, self.padded)]
        for model in models:
            if expected:
                calls = [c for c in model.calls if c[0] not in (0x150AD780, 0x150AD78C)]
                self.assertEqual((public(model.memory), calls), (public(expected.memory), expected.calls))
        for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f, model.lo),
            (models[0].memory, models[0].events, models[0].r, models[0].f, models[0].lo))
        return models

    def test_01_complete_direct_body_frame_and_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']), (138, 184, 0, 0))
        self.assertEqual(self.raw, self.retail); self.assertEqual(self.padded, self.retail); self.assertEqual(self.link('original'), self.retail)
        for profile in ('compact', 'o1g3', 'o1'):
            meta, words = screen.compile_candidate(self.root, self.out, profile, profile=profile)
            if profile == 'compact': self.assertEqual((meta['body_words'], meta['frame'], words), (138, 184, self.retail))
            else: self.assertNotEqual(words, self.retail)
        self.receipt('shape', words=138, frame=184, direct=True, guards=0, no_profile_change=True)

    def test_02_unsigned_counts_signed_types_all_words_and_empty_gates(self):
        cases, reached = 0, set()
        for count, kinds, flag, phase in itertools.product((0, 1, 3, 4, 5, 27, 31, 45, 128, 255),
                ((-2,), (-1,), (0,), (-128, -2, 127, -1)), (0, 255), (0, 8)):
            memory = fixture(count, kinds, flag, phase=phase)
            models = self.compare(memory, phase=phase); reached.update(models[0].visits); cases += 1
        for slot, group, bank in itertools.product((0, 25, -1, 0x80000000), (0, 255), (0, BANK)):
            memory = fixture(1, (-1,), slot=slot, group=group, bank=bank)
            self.compare(memory, slot); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+552, 4))), 137)
        self.receipt('guest', cases=cases, forms=3, reachable_target_words=137, unreachable_duplicate_load_offset=0x1A0,
            bank_NULL_unused_tables_unmapped=True, signed_minus2_outer_minus1_inner=True,
            invalid_slot_kind_mapping_guest_only=True)

    def test_03_callback_lifetimes_public_and_private_aliases(self):
        cases = 0
        for mode, phase, kinds in itertools.product(('bank', 'position-buffer', 'rotation-buffer', 'scale-buffer',
                'cached-destination', 'cached-type', 'cached-cursor-count', 'late-snapshot', 'absolute-position'),
                (0, 8), ((1, -1, 0, -2), (-1, 1, -2, 0))):
            memory = fixture(kinds=kinds, phase=phase)
            self.compare(memory, phase=phase, actions=actions_for(mode)); cases += 1
        actor = screen.SYMBOLS['D_800CC2D0']+7*812
        for buffer, phase in itertools.product((BANK, BANK+64, actor-36), (0, 8)):
            self.compare(fixture(1, (-1,), buffer=buffer, phase=phase), phase=phase); cases += 1
        for phase in (0, 8):
            memory = fixture(1, (-1,), buffer=STACK+phase-0xB8+0x64-36, phase=phase)
            self.compare(memory, phase=phase, check_reference=False); cases += 1
        self.receipt('lifetimes', cases=cases, cached_initial_cursor_count_and_destination=True,
            live_group_bank_and_record_buffer_reloads=True, clobbered_caller_saved_GPR_FPR=True,
            public_and_private_aliases_guest_only=True)

    def test_04_independent_rebases_and_seven_argument_payloads(self):
        cases = 0
        for link, start in enumerate((0x15207FFC, 0x15308004)):
            symbols = {n: (0x80107FFC if i % 2 == link else 0x80218004)+i*0x10000 for i, n in enumerate(screen.SYMBOLS)}
            for i, name in enumerate(('func_150A7DA0', 'func_150A8050', 'func_150A7CB0', 'func_150A7A48', 'func_15043EC8')):
                symbols[name] = 0x15408004+i*0x10000
            forms = tuple(self.link(n, start, symbols) for n in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[1]); self.assertEqual(forms[0], forms[2])
            for kinds, phase, mode in itertools.product(((-1,), (1,)), (0, 8), ('none', 'bank', 'rotation-buffer')):
                memory = fixture(2, kinds, phase=phase, symbols=symbols)
                self.compare(memory, phase=phase, actions=actions_for(mode, symbols=symbols), symbols=symbols, start=start, forms=forms); cases += 1
        self.receipt('rebases', symbols=9, links=2, cases=cases, independent_HI_LO_JAL=True,
            private_matrix64_and_full_seven_argument_float_bits_exact=True)

    def test_05_fired_fault_prefixes(self):
        pairs = 0
        for kinds, phase in (((-1,), 0), ((1,), 8)):
            memory = fixture(1, kinds, phase=phase); complete = UpdateOracle(self.retail, memory, phase=phase, symbols=screen.SYMBOLS).run()
            for fault in range(complete.accesses):
                models = [UpdateOracle(w, memory, phase=phase, symbols=screen.SYMBOLS) for w in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, fault)
                for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                    (models[0].memory, models[0].events, models[0].r, models[0].f))
                pairs += 1
        self.receipt('faults', fired_triplets=pairs, private_and_public_exact=True, not_portable_C_fault_or_FCSR_proof=True)

    def test_06_fresh_effective_semantic_controls(self):
        controls = (
            ('wrong-outer', screen.SELECTED.replace('case -2:', 'case -1:'), (-1,), 'none'),
            ('wrong-inner', screen.SELECTED.replace('type != -1', 'type != -2'), (-1,), 'none'),
            ('halfword-position', screen.SELECTED.replace('((u32 *)element)[9]', 'element->unk24'), (1,), 'none'),
            ('lost-buffer-reload', screen.SELECTED.replace('                        element = (struct04 *)D_800C6660[slot].unk0 + index;\n', ''), (1,), 'rotation-buffer'),
            ('reversed-multiply', screen.SELECTED.replace('func_150A7A48(matrix, destination, destination)', 'func_150A7A48(destination, matrix, destination)'), (1,), 'none'),
            ('lost-position', screen.SELECTED.replace('((f32 *)element)[9], ((f32 *)element)[10], ((f32 *)element)[11]);', '0.0f, 0.0f, 0.0f);'), (-1,), 'none'))
        for name, body, kinds, mode in controls:
            self.assertNotEqual(body, screen.SELECTED, name)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            memory = fixture(1, kinds); actions = actions_for(mode)
            expected = Reference(memory, actions=actions).run()
            model = UpdateOracle(words, memory, symbols=screen.SYMBOLS, start=0x1523E82C, actions=actions).run()
            def observable(calls):
                return [(c[0], *(a for a in c[1:] if not STACK-0x800 <= a < STACK+0x140)) for c in calls]
            self.assertTrue((public(model.memory), observable(model.calls)) !=
                (public(expected.memory), observable(expected.calls)), name)
        self.receipt('controls', fresh_semantic=6, all_effective_public_not_private_layout=True)

    def test_07_complete_owner_neighbors_and_both_real_padders(self):
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
                subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches', str(self.out/'before-guards')], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)], check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+552] = parsed[1][0][start:start+552]; self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o: r for o, r in parsed[0][2].items() if not start <= o < start+552},
                {o: r for o, r in parsed[1][2].items() if not start <= o < start+552})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', unchanged_neighbors=len(names)-1, pools_exact=True, both_padders=True,
            dispatcher171_setup141_and_GLOBAL_ASM141_unchanged=True, only_void_forward_declaration_changed=True)

    def test_08_literal_source_whole_ELF_and_other_inputs(self):
        before_source = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text(); now = current != before_source
        self.assertEqual(current, screen.install(before_source) if now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 552); extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if now: struct.pack_into('>138I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 552)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            if name not in ('source', 'elf'): self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes(), name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+552], actual[start:start+552])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), literal_no_projection_or_metadata_exception=True,
            seven_other_inputs_exact=True, protected_data=data)

    def test_09_effective_stale_source_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for stale in (screen.install(before), before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        rt, rb = Path.read_text, Path.read_bytes; source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: actual+'\n' if p == source else rt(p, *a, **k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_other_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        for offset in (elf_slot_offset(actual, screen.ENTRY, 552)+4, elf_slot_offset(actual, screen.ENTRY, 552)+552,
                installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_other_inputs()
        guards = self.root/self.paths['guards']; wrong = guards.read_bytes()+b'\n'
        with patch.object(Path, 'read_bytes', lambda p: wrong if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_other_inputs()
        self.receipt('integrity-controls', stale_installs=2, source=1, ELF=3, guards=1, all_effective=True)

    def test_10_connected_actual_matrix_helpers_with_bounded_trig_leaves(self):
        specs = ((TRANSLATE, 0xD5250, 20), (SCALE, 0xD5160, 20), (FINISH, 0x71378, 41),
            (ROTATE, 0xD5500, 84), (MULTIPLY, 0xD4EF8, 76))
        bodies = {a: list(struct.unpack_from('>%dI' % count, self.rom, rom)) for a, rom, count in specs}
        for a, rom, count in specs[:3]:
            self.assertEqual(bodies[a], list(struct.unpack_from('>%dI' % count, self.before, elf_slot_offset(self.before, a, count*4))))
        connected = {a+i*4: w for a, words in bodies.items() for i, w in enumerate(words)}
        factor = struct.unpack_from('>I', self.before, elf_slot_offset(self.before, 0x8009F6C0, 4))[0]
        self.assertEqual(factor, FACTOR); cases = 0
        for count, kinds, phase, mode in itertools.product((1, 3), ((-1,), (1,), (-1, -2, 0)), (0, 8),
                ('none', 'bank', 'rotation-buffer')):
            memory = fixture(count, kinds, phase=phase); put(memory, 0x8009F6C0, factor)
            self.compare(memory, phase=phase, actions=actions_for(mode), connected=connected); cases += 1
        self.receipt('connected-helpers', cases=cases, forms=3, linked_translate20_scale20_finish41=True,
            retail_rotate84_multiply76_current_C_placeholders_not_qualified=True,
            only_sine_cosine_leaves_modeled_no_hardware_FCSR_or_trig_library_claim=True)

    def test_11_actual_dispatcher_setup_predicate_update_chain(self):
        caller = list(struct.unpack_from('>171I', self.before, elf_slot_offset(self.before, state.screen.ENTRY, 684)))
        predicate = list(struct.unpack_from('>27I', self.before, elf_slot_offset(self.before, state.HELPER, 108)))
        setup_words = list(struct.unpack_from('>141I', self.before, elf_slot_offset(self.before, setup.screen.ENTRY, 564)))
        for a, rom, words in ((state.screen.ENTRY, state.screen.ROM, caller),
                (state.HELPER, state.screen.ROM+684, predicate), (setup.screen.ENTRY, setup.screen.ROM, setup_words)):
            self.assertEqual(words, list(struct.unpack_from('>%dI' % len(words), self.rom, rom)))
        frame = (-caller[0]) & 65535; self.assertEqual(frame, 56)
        symbols = dict(state.screen.SYMBOLS, **setup.screen.SYMBOLS); symbols.update(screen.SYMBOLS)
        class ChainOracle(UpdateOracle, setup.SetupOracle):
            def __init__(model, words, memory, phase, connected, actions):
                state.StateOracle.__init__(model, words, memory, symbols=symbols, phase=phase,
                    start=state.screen.ENTRY, connected=connected, actions=actions)
                model.result = None
            def record_call(model, target):
                super().record_call(target)
                if target == screen.ENTRY: model.mutate('tail2')
        class ChainReference(state.Reference):
            def call(ref, target, args):
                result = super().call(target, args)
                if target in (screen.ENTRY, setup.screen.ENTRY):
                    if target == setup.screen.ENTRY:
                        put(ref.memory, STACK+ref.phase-frame+16, args[4])
                    body = Reference(ref.memory, args[0], ref.phase-frame, symbols, ref.actions) if target == screen.ENTRY else \
                        setup.Reference(ref.memory, args, ref.phase-frame, symbols, ref.actions)
                    body.run(); ref.memory = body.memory; ref.calls.extend(body.calls)
                return result
        cases = 0
        for count, status, phase, change_buffer in itertools.product((0, 1, 3, 4), (1, 2, 3), (0, 8), (False, True)):
            memory = fixture(count, (-1, -2, 0, -1), phase=phase, symbols=symbols)
            banks = {a: v for a, v in memory.items() if BANK <= a < BANK+256*64}
            others = {a: v for a, v in memory.items() if OTHER <= a < OTHER+count*104}
            memory = state.fixture(state=status, count=count, types=(255, 254, 0, 255), symbols=symbols,
                existing=status == 1, flag=1)
            memory.update(banks); memory.update(others); memory.update({STACK+i: 0xA5 for i in range(-0x800, 0x140)})
            actor = symbols['D_800CC2D0']+7*812; control = symbols['D_800C6660']+7*16
            put(memory, actor+0x1D4, BANK)
            for i, value in enumerate((1.25, -2.5, 8.0)): put(memory, actor+20+i*4, bits(value))
            if status == 1:
                initial = fixture(count, (-1, -2, 0, -1), symbols=symbols)
                memory.update({a: v for a, v in initial.items() if BUFFER <= a < BUFFER+count*104})
            actions = {('tail1', 0): ((control, OTHER, 4),)} if change_buffer else {}
            expected = ChainReference(memory, symbols=symbols, actions=actions); expected.phase=phase; expected.run()
            models = []
            for body in (self.retail, self.raw, self.padded):
                connected = {a+i*4: w for a, words in ((screen.ENTRY, body), (state.HELPER, predicate),
                    (setup.screen.ENTRY, setup_words)) for i, w in enumerate(words)}
                model = ChainOracle(caller, memory, phase, connected, actions).run()
                self.assertEqual(model.calls, expected.calls)
                actual_public, expected_public = public(model.memory), public(expected.memory)
                differences = [(hex(a), actual_public.get(a), expected_public.get(a)) for a in actual_public.keys() | expected_public.keys()
                    if actual_public.get(a) != expected_public.get(a)]
                self.assertFalse(differences, (count, status, phase, change_buffer, differences[:12]))
                models.append(model)
            for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                (models[0].memory, models[0].events, models[0].r, models[0].f))
            cases += 1
        self.receipt('connected-caller', cases=cases, dispatcher171_setup141_predicate27_update138=True,
            independent_composed_reference=True, tail_callback_buffer_reload=True,
            remaining_callees_modeled_not_full_gameplay_proof=True)

    def test_12_raw_float_payload_width_and_O32_homes(self):
        payloads = ((0, 0x80000000, 1), (0x7FC12345, 0x7F800000, 0xFF800000),
            (bits(1.0000001192092896), bits(-1.5), 0x80000001))
        cases = 0
        for payload, kinds, phase in itertools.product(payloads, ((-1,), (1,)), (0, 8)):
            memory = fixture(1, kinds, phase=phase)
            for i, value in enumerate(payload): put(memory, BUFFER+36+i*4, value)
            models = self.compare(memory, phase=phase)
            for model in models:
                selected = [c for c in model.calls if c[0] in (TRANSLATE, FINISH)]
                self.assertEqual(tuple(selected[0][2:5] if kinds == (1,) else selected[0][5:8]), payload)
            cases += 1
        self.receipt('payloads', cases=cases, exact_full_position_words_in_GPR_or_three_stack_homes=True,
            signed_zero_subnormal_infinity_NaN=True, modeled_arithmetic_not_hardware_NaN_FCSR_proof=True)

    def test_13_native32_valid_domain_callbacks_and_controls(self):
        prefix = r'''
#define NULL ((void *)0)
typedef unsigned char u8; typedef signed char s8; typedef unsigned short u16;
typedef short s16; typedef unsigned u32; typedef int s32; typedef float f32;
typedef struct { u32 prefix[9]; u16 unk24,unk26; s16 unk28,unk2A;
    s32 unk2C,unk30,unk34,unk38,unk3C,unk40,unk44; u32 tail[7]; u8 unk64,unk65,pad[2]; } struct04;
typedef struct { s32 unk0,unk4,unk8; u8 tail[4]; } struct106;
typedef struct { f32 values[256][4][4]; } struct255;
typedef struct { u8 prefix[20]; f32 x,y,z; u8 middle[436]; struct255 *unk1D4; u8 suffix[340]; } struct127;
typedef char actor_size[sizeof(struct127)==812?1:-1]; typedef char record_size[sizeof(struct04)==104?1:-1];
struct127 D_800CC2D0[26]; struct106 D_800C6660[26]; u8 D_80098914[3];
static s8 row[3][256]; s8 *D_80084454[3]={row[0],row[1],row[2]};
static struct255 banks[2],expected_banks[2]; static struct04 buffers[3][256],expected_buffers[3][256];
static int mode,current_slot,occurrences[5]; static unsigned trace[2048][8],expected_trace[2048][8],used,expected_used;
static unsigned word(f32 v) { union { f32 f; unsigned u; } a; a.f=v; return a.u; }
static void copy(void *b,const void *a,unsigned n) { u8 *d=b; const u8 *s=a; for(unsigned i=0;i<n;i++) d[i]=s[i]; }
static void mutate(int label) {
    int n=occurrences[label]++; struct106 *r=&D_800C6660[current_slot];
    if(mode==1 && label==0 && n==0) D_800CC2D0[current_slot].unk1D4=&banks[1];
    if(mode==2 && label==1 && n==0) r->unk0=(s32)&buffers[1][0];
    if(mode==3 && label==3 && n==0) r->unk0=(s32)&buffers[2][0];
    if(mode==4 && label==1 && n==0) { D_80098914[((u8 *)r)[14]]=0; ((u8 *)r)[14]=1; row[2][1]=-2; }
    if(mode==5 && label==1 && n==0) D_800CC2D0[current_slot].unk1D4=&banks[1];
}
static void note(int label,const u32 *args,int n) {
    if(used>=2048) __builtin_trap();
    trace[used][0]=label; for(int i=0;i<7;i++) trace[used][i+1]=i<n?args[i]:0; used++; mutate(label);
}
static void unit(f32 m[4][4]) { for(int r=0;r<4;r++) for(int c=0;c<4;c++) m[r][c]=r==c?1.0f:0.0f; }
void func_150A7DA0(f32 m[4][4],u32 x,u32 y,u32 z) {
    u32 args[3]={x,y,z}; note(0,args,3); unit(m); ((u32 *)m)[12]=x; ((u32 *)m)[13]=y; ((u32 *)m)[14]=z;
}
void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z) {
    u32 args[3]={word(x),word(y),word(z)}; note(1,args,3); unit(m); m[0][1]=x; m[1][2]=y; m[2][0]=z;
}
void func_150A7CB0(u32 *m,u32 x,u32 y,u32 z) {
    u32 args[3]={x,y,z}; note(2,args,3); for(int i=0;i<16;i++) m[i]=0; m[0]=x; m[5]=y; m[10]=z; m[15]=word(1.0f);
}
void func_150A7A48(f32 a[4][4],f32 b[4][4],f32 out[4][4]) {
    u32 args[1]={0}; f32 temp[4][4]; note(3,args,0);
    for(int r=0;r<4;r++) for(int c=0;c<4;c++) {
        f32 v=a[r][0]*b[0][c]; for(int k=1;k<4;k++) v=v+a[r][k]*b[k][c]; temp[r][c]=v;
    }
    copy(out,temp,64);
}
void func_15043EC8(f32 m[4][4],f32 sx,f32 sy,f32 sz,f32 x,f32 y,f32 z) {
    u32 args[6]={word(sx),word(sy),word(sz),word(x),word(y),word(z)}; note(4,args,6);
    m[3][0]=x; m[3][1]=y; m[3][2]=z; f32 scales[3]={sx,sy,sz};
    for(int r=0;r<3;r++) for(int c=0;c<3;c++) m[r][c]=m[r][c]*scales[r];
}
static void reference(int slot) {
    if(!D_800CC2D0[slot].unk1D4) return;
    struct106 *control=&D_800C6660[slot]; int group=((u8 *)control)[14];
    int limit=D_80098914[group]; s8 *cursor=D_80084454[group]; int i=0;
    while(i<limit) {
        int skip=cursor[i]==-2; struct04 *e=(struct04 *)control->unk0+i;
        if(!skip && e->unk64) {
            int kind=D_80084454[((u8 *)control)[14]][i]; f32 (*dest)[4]=D_800CC2D0[slot].unk1D4->values[i];
            if(kind==-1) {
                f32 *v=(f32 *)e; func_150A8050(dest,v[12],v[13],v[14]);
                v=(f32 *)((struct04 *)control->unk0+i); func_15043EC8(dest,v[15],v[16],v[17],v[9],v[10],v[11]);
            } else {
                f32 temp[4][4]; u32 *v=(u32 *)e;
                func_150A7DA0(temp,v[9],v[10],v[11]);
                func_150A7A48(temp,D_800CC2D0[slot].unk1D4->values[kind],temp);
                f32 *angles=(f32 *)((struct04 *)control->unk0+i); func_150A8050(dest,angles[12],angles[13],angles[14]);
                func_150A7A48(dest,temp,dest);
                v=(u32 *)((struct04 *)control->unk0+i); func_150A7CB0((u32 *)temp,v[15],v[16],v[17]);
                func_150A7A48(temp,dest,dest);
            }
        }
        i++;
    }
}
static void initialize(int count,int slot,int pattern,int flag,int ready) {
    current_slot=slot; used=0; for(int i=0;i<5;i++) occurrences[i]=0;
    for(int g=0;g<3;g++) { D_80098914[g]=count; for(int i=0;i<256;i++) row[g][i]=pattern==0?-1:pattern==1?1:(i%4==1?-2:i%4==2?-1:0); }
    D_800C6660[slot].unk0=(s32)&buffers[0][0]; ((u8 *)&D_800C6660[slot])[14]=2;
    D_800CC2D0[slot].unk1D4=ready?&banks[0]:0;
    for(int b=0;b<3;b++) for(int i=0;i<256;i++) {
        for(int k=0;k<26;k++) ((u32 *)&buffers[b][i])[k]=0x35353535;
        f32 *v=(f32 *)&buffers[b][i]; v[9]=5.25f+b; v[10]=34.5f+i; v[11]=-3;
        v[12]=0.125f+b*0.25f; v[13]=-0.25f; v[14]=0.5f; v[15]=1.5f+b; v[16]=2; v[17]=0.75f;
        buffers[b][i].unk64=flag;
    }
    for(int b=0;b<2;b++) for(int i=0;i<256;i++) {
        unit(banks[b].values[i]); banks[b].values[i][0][0]=1+b; banks[b].values[i][1][1]=2;
        banks[b].values[i][2][2]=4; banks[b].values[i][3][0]=2+i;
    }
}
'''
        suffix = r'''
static int run(u32 *failure) {
    const int counts[9]={0,1,3,4,27,31,45,128,255},slots[3]={0,7,25}; unsigned cases=0;
    for(int c=0;c<9;c++) for(int s=0;s<3;s++) for(int pattern=0;pattern<3;pattern++)
    for(int flag=0;flag<2;flag++) for(int ready=0;ready<2;ready++) for(mode=0;mode<6;mode++) {
        initialize(counts[c],slots[s],pattern,flag,ready); reference(slots[s]);
        copy(expected_banks,banks,sizeof(banks)); copy(expected_buffers,buffers,sizeof(buffers));
        expected_used=used; copy(expected_trace,trace,used*sizeof(trace[0]));
        s32 expected_pointer=D_800C6660[slots[s]].unk0; int expected_group=((u8 *)&D_800C6660[slots[s]])[14];
        struct255 *expected_bank=D_800CC2D0[slots[s]].unk1D4;
        initialize(counts[c],slots[s],pattern,flag,ready); func_1503E82C(slots[s]); cases++;
        if(used!=expected_used || D_800C6660[slots[s]].unk0!=expected_pointer ||
            ((u8 *)&D_800C6660[slots[s]])[14]!=expected_group || D_800CC2D0[slots[s]].unk1D4!=expected_bank) {
            failure[0]=cases; failure[1]=99; failure[2]=used; return 1;
        }
        for(unsigned i=0;i<used*8;i++) if(((u32 *)trace)[i]!=((u32 *)expected_trace)[i]) {
            failure[0]=cases; failure[1]=98; failure[2]=i; return 1;
        }
        for(unsigned i=0;i<sizeof(banks)/4;i++) if(((u32 *)banks)[i]!=((u32 *)expected_banks)[i]) {
            failure[0]=cases; failure[1]=i; failure[2]=((u32 *)banks)[i]; return 1;
        }
        for(unsigned i=0;i<sizeof(buffers)/4;i++) if(((u32 *)buffers)[i]!=((u32 *)expected_buffers)[i]) {
            failure[0]=cases; failure[1]=97; failure[2]=i; return 1;
        }
    }
    return cases==1944 ? 0 : 2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:], prefix+screen.SELECTED+suffix, profile), (0, ''))
        controls = (('outer', screen.SELECTED.replace('case -2:', 'case -1:')),
            ('width', screen.SELECTED.replace('((u32 *)element)[9]', 'element->unk24')),
            ('reload', screen.SELECTED.replace('                        element = (struct04 *)D_800C6660[slot].unk0 + index;\n', '')))
        for name, body in controls:
            result, detail = self.run_native('native-negative-'+name, prefix+body+suffix)
            self.assertEqual(result, 1); self.assertEqual(len(detail), 3)
        self.receipt('native', cases_per_profile=1944, profiles=['O2', 'O0'], finite_valid_domain=True,
            callbacks=6, exact_banks_records_and_raw_command_payloads=True, effective_controls=3,
            rotation_is_explicit_boundary_model_no_trig_hardware_or_alias_claim=True)


if __name__ == '__main__':
    unittest.main()
