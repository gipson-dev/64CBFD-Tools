"""Group-2 active timer reload, ordered expiry and literal linked audit."""
import hashlib
import itertools
import json
import re
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_mask_active_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests import test_game_record_mask_teardown_match as teardown
from tools.tests import test_game_record_mask_finish_match as finish
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, QUERY = guest.STACK, 0x1503EF4C
SYMBOLS = {**state.screen.SYMBOLS, **teardown.screen.SYMBOLS,
    **finish.SYMBOLS, **screen.SYMBOLS}
address, public = state.address, finish.public
FLAGS = (0, 0xFFFFFFFF, 0x80000000, 0x12345678, 14)


def signed16(value):
    value &= 65535
    return value if value < 32768 else value-65536


def fixture(slot=7, timer=1, clock=1, flags=0x12345678,
        masks=(0xFFFFFFFF, 0xFFFFFFFF), pairs=((1, 0), (0, 2), (0, 0)),
        symbols=SYMBOLS, marker=1, count=5, table=True, buffer=True):
    memory = teardown.fixture(slot=slot, marker=marker, count=count,
        table=table, buffer=buffer, masks=masks, actor_mask=flags, symbols=symbols)
    memory.update({STACK+i: 0xA5 for i in range(-0x800, 0x140)})
    put(memory, address(symbols['D_800C6660'], slot, 16)+12, timer, 2)
    put(memory, symbols['D_800BE9E4'], clock)
    put(memory, symbols['D_8008446C']+8, finish.PAIRS)
    for i, pair in enumerate(pairs):
        put(memory, finish.PAIRS+i*8, pair[0])
        put(memory, finish.PAIRS+i*8+4, pair[1])
    return memory


class Reference(state.Reference):
    def __init__(self, memory, slot=7, results=(1, 1, 1), symbols=SYMBOLS,
            actions=None, actual=False):
        super().__init__(memory, slot, symbols, actions)
        self.results, self.actual = results, actual
    def call(self, target, args):
        args = tuple(v & 0xFFFFFFFF for v in args)
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        if target == self.symbols['func_1503ECA0']:
            self.mutate('prepare')
        elif target == self.symbols['func_1503E260']:
            self.mutate('teardown')
            if self.actual:
                inner = teardown.Reference(self.memory, self.slot, self.symbols, self.actions).run()
                self.memory = inner.memory; self.calls.extend(inner.calls); self.events.extend(inner.events)
        else:
            assert target == self.symbols['func_1503EF4C'] and args[:2] == (2, self.occurrences.get('query', 0))
            self.mutate('query')
            return finish.paired_mask(self.memory, args[1], self.slot, self.symbols) if self.actual else self.results[args[1]]
        return 0xA5000002
    def run(self):
        s, slot = self.symbols, self.slot
        self.call(s['func_1503ECA0'], (slot,))
        timer = address(s['D_800C6660'], slot, 16)+12
        clock = self.get(s['D_800BE9E4'])
        self.put(timer, signed16(self.get(timer, 2))-clock, 2)
        if signed16(self.get(timer, 2)) > 0:
            return self
        self.call(s['func_1503E260'], (slot,))
        for i, bit in enumerate((8, 4, 2)):
            if self.call(s['func_1503EF4C'], (2, i, slot)):
                flags = address(s['D_800CC2D0'], slot, 812)+148
                self.put(flags, self.get(flags) | bit)
        return self


class ActiveOracle(teardown.TeardownOracle):
    def __init__(self, words, memory, slot=7, results=(1, 1, 1), phase=0,
            symbols=SYMBOLS, start=screen.ENTRY, actions=None, connected=None, actual=False):
        super().__init__(words, memory, slot, phase, symbols, start, connected, actions)
        self.results, self.actual, self.query_number = results, actual, 0
    def record_call(self, target):
        s = self.symbols
        if target == s['func_1503EF4C']:
            args = self.arguments(3)
            assert args == (2, self.query_number % 3, self.slot & 0xFFFFFFFF), args
            self.query_number += 1
        elif target == s['func_1503E1F4']:
            args = self.arguments(2)
        else:
            assert target in (s['func_1503ECA0'], s['func_1503E260'], s['func_10004074']), hex(target)
            args = self.arguments(1)
            if target != s['func_10004074']:
                assert args == (self.slot & 0xFFFFFFFF,), args
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        for name, label in (('func_1503ECA0', 'prepare'), ('func_1503E260', 'teardown'),
                ('func_1503EF4C', 'query'), ('func_1503E1F4', 'predicate')):
            if target == s[name]:
                self.mutate(label)
                if label == 'prepare':
                    self.query_number = 0
    def hook(self, target):
        s = self.symbols
        if target == s['func_1503EF4C']:
            assert not self.actual
            result = self.results[(self.query_number-1) % 3] & 0xFFFFFFFF
        elif target in (s['func_1503E260'], s['func_1503ECA0']):
            if target == s['func_1503E260']:
                assert not self.actual
            result = 0xA5000002
        else:
            return super().hook(target)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.r[2] = result


class GameRecordMaskActiveMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-mask-active-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
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
        assert cls.baseline['source'] == 'eab97cc6ad4b03b8384b63bb8d9db13ceed0a84a09dfe78a1c8c15cb11c42295'
        assert cls.baseline['elf'] == '97ce8226e215f210817865fa0cd8e213da38f42849ba641cc1bb82244603be45'
        assert cls.baseline['guards'] == '92f39fbf0bf509614ecff961e3a654e01d30c98666c3c65f224884f57102206e'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>85I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        body = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot, filename='generated_6B320'))
        cls.connected = {}
        for entry, rom, count in ((QUERY, 0x6C3FC, 30), (teardown.screen.ENTRY, 0x6B710, 89),
                (state.HELPER, 0x6B6A4, 27)):
            words = list(struct.unpack_from('>%dI' % count, cls.before, elf_slot_offset(cls.before, entry, count*4)))
            assert words == list(struct.unpack_from('>%dI' % count, cls.rom, rom))
            cls.connected.update({entry+i*4: word for i, word in enumerate(words)})

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def link(self, name, start=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>85I', sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded'):
            type(self)._padded = self.link('padded')
        return type(self)._padded

    def compare(self, memory, slot=7, results=(1, 1, 1), phase=0, actions=None,
            actual=False, symbols=SYMBOLS, start=screen.ENTRY, forms=None):
        expected = Reference(memory, slot, results, symbols, actions, actual).run()
        models = [ActiveOracle(words, memory, slot, results, phase, symbols, start, actions,
            self.connected if actual else None, actual).run() for words in forms or (self.retail, self.raw, self.padded)]
        for model in models:
            self.assertEqual((public(model.memory), model.calls, state.writes(model)),
                (public(expected.memory), expected.calls, state.writes(expected)))
            self.assertEqual(model.query_number, expected.occurrences.get('query', 0))
        for model in models[1:]:
            self.assertEqual((model.memory, model.events, model.r, model.f, model.lo),
                (models[0].memory, models[0].events, models[0].r, models[0].f, models[0].lo))
        return models

    def test_01_all85_direct_and_existing_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']),
            (85, 32, 0, 0))
        self.assertEqual(self.raw, self.retail); self.assertEqual(self.padded, self.retail)
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'], 340)
        for profile in ('compact', 'o1g3', 'o1'):
            meta, words = screen.compile_candidate(self.root, self.out, profile, profile=profile)
            if profile == 'compact': self.assertEqual(words, self.retail)
            else: self.assertEqual((meta['body_words'], meta['differences']), (92, 88))
        self.receipt('shape', words=85, frame=32, direct=True, guards=0, pools=0)

    def test_02_timer_truncation_all_results_bits_and_words(self):
        cases, reached = 0, set()
        for timer, clock, phase in itertools.product((32767, 32768, 65535, 0, 1, 2),
                (0, 1, -1, 32768, 65536, 0x80000000, 0x7FFFFFFF), (0, 8)):
            memory = fixture(timer=timer, clock=clock)
            models = self.compare(memory, phase=phase); reached.update(models[0].visits); cases += 1
        for results, flags, phase in itertools.product(tuple(itertools.product((0, 1, -1, 0x80000000), repeat=3)), FLAGS, (0, 8)):
            self.compare(fixture(flags=flags), results=results, phase=phase); cases += 1
        for bit, results in itertools.product(range(32), tuple(itertools.product((0, 1), repeat=3))):
            self.compare(fixture(flags=1 << bit), results=results); cases += 1
        for slot in (-1, 0, 25, 26, 0x7FFFFFFF, 0x80000000):
            self.compare(fixture(slot=slot), slot=slot); cases += 1
        self.assertEqual(reached, set(range(screen.ENTRY, screen.ENTRY+340, 4)))
        self.receipt('matrix', cases=cases, reached_words=len(reached),
            signed_reloaded_halfword_after_wrapping_subtract=True, all_nonzero_results=True, mapped_invalid_slots_guest_only=True)

    def test_03_effective_callback_lifetimes_and_public_aliases(self):
        record = address(SYMBOLS['D_800C6660'], 7, 16); flags = address(SYMBOLS['D_800CC2D0'], 7, 812)+148
        choices = (
            {('prepare', 0): ((record+12, 2, 2),)},
            {('prepare', 0): ((SYMBOLS['D_800BE9E4'], 0xFFFF, 4),)},
            {('prepare', 0): ((flags, 0x80000000, 4),)},
            {('teardown', 0): ((record+12, 300, 2),)},
            {('teardown', 0): ((flags, 0x40000000, 4),)},
            *({('query', i): ((flags, 0x80000000+i, 4),)} for i in range(3)),
        )
        cases = 0
        baseline = self.compare(fixture())[0]
        for actions, phase in itertools.product(choices, (0, 8)):
            models = self.compare(fixture(), actions=actions, phase=phase)
            self.assertTrue((public(models[0].memory), models[0].calls) != (public(baseline.memory), baseline.calls))
            cases += 1
        for phase in (0, 8):
            s = dict(SYMBOLS, D_800BE9E4=SYMBOLS['D_800C6660']+12)
            forms = tuple(self.link(n, screen.ENTRY, s) for n in ('original', 'selected', 'padded'))
            memory = fixture(slot=0, timer=1, clock=0x00010002, symbols=s)
            models = self.compare(memory, slot=0, phase=phase, symbols=s, forms=forms)
            self.assertEqual(read(models[0].memory, s['D_800BE9E4']), 0xFFFF0002); cases += 1
            s = dict(SYMBOLS, D_800CC2D0=finish.PAIRS+8-148)
            forms = tuple(self.link(n, screen.ENTRY, s) for n in ('original', 'selected', 'padded'))
            memory = fixture(slot=0, symbols=s, flags=0, masks=(4, 0), pairs=((0, 0), (0, 0), (0, 0)), marker=0)
            models = self.compare(memory, slot=0, phase=phase, actual=True, symbols=s, forms=forms)
            self.assertEqual(read(models[0].memory, finish.PAIRS+8), 10); cases += 1
        self.receipt('lifetimes-aliases', cases=cases, effective_callbacks=16,
            timer_clock_word_and_flag_pair_aliases=True, mapped_guest_not_portable_alias_or_allocation_proof=True)

    def test_04_actual_teardown89_predicate27_query30_chain(self):
        cases, reached = 0, set()
        for timer, masks, marker, count, phase, mode in itertools.product(
                (2, 1, 0, -1), ((0, 0), (0xFFFFFFFF, 0xFFFFFFFF), (1, 0), (0, 2)),
                (0, 1), (0, 3, 5), (0, 8), ('none', 'free-mask', 'free-mutation')):
            memory = fixture(timer=timer, masks=masks, marker=marker, count=count)
            actions = teardown.actions_for(mode)
            models = self.compare(memory, phase=phase, actual=True, actions=actions)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+340, 4))), 85)
        self.assertEqual(len(reached & set(range(QUERY, QUERY+120, 4))), 29)
        self.assertGreater(len(reached & set(range(teardown.screen.ENTRY, teardown.screen.ENTRY+356, 4))), 80)
        self.receipt('actual-chain', cases=cases, active85_teardown89_predicate27_query30_actual=True,
            preparation_and_free_bounded_models=True, original_helper_dead_words_preserved=True)

    def test_05_independent_rebases_and_all_fired_faults(self):
        cases, faults = 0, 0
        for j, start in enumerate((0x15207FFC, 0x15308004)):
            s = dict(SYMBOLS)
            for i, name in enumerate(screen.SYMBOLS):
                s[name] = (0x15140000+i*0x100+j*0x10000 if name.startswith('func_') else
                    (0x80107FFC if i % 2 == j else 0x80218004)+i*0x10000)
            forms = tuple(self.link(n, start, s) for n in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[1]); self.assertEqual(forms[0], forms[2])
            for timer, results, phase in itertools.product((2, 1), tuple(itertools.product((0, 1), repeat=3)), (0, 8)):
                self.compare(fixture(timer=timer, symbols=s), results=results, phase=phase, symbols=s, start=start, forms=forms); cases += 1
        for timer, actual, results in itertools.product((2, 1), (False, True), ((0, 0, 0), (1, 1, 1))):
            memory = fixture(timer=timer)
            code = self.connected if actual else None
            full = ActiveOracle(self.retail, memory, results=results, connected=code, actual=actual).run()
            for fault in range(full.accesses):
                models = [ActiveOracle(w, memory, results=results, connected=code, actual=actual)
                    for w in (self.retail, self.raw, self.padded)]
                for m in models:
                    m.fault = fault
                    with self.assertRaises(guest.AccessFault): m.run()
                    self.assertEqual(m.accesses, fault)
                for m in models[1:]:
                    self.assertEqual((m.memory, m.events, m.r, m.f), (models[0].memory, models[0].events, models[0].r, models[0].f))
                faults += 1
        self.receipt('rebases-faults', links=2, symbols=6, cases=cases, fired_fault_triplets=faults,
            actual_teardown_and_queries_in_fault_domain=True, no_portable_C_fault_or_hardware_claim=True)

    def test_06_effective_fresh_semantic_controls(self):
        controls = (
            ('expiry', screen.SELECTED.replace(' <= 0', ' < 0'), fixture(timer=1), (1, 1, 1)),
            ('unsigned-timer', screen.SELECTED.replace('s16 *', 'u16 *'), fixture(timer=0), (1, 1, 1)),
            ('add', screen.SELECTED.replace(' -= D_800BE9E4', ' += D_800BE9E4'), fixture(timer=1), (1, 1, 1)),
            ('first-bit', screen.SELECTED.replace(' |= 8', ' |= 16'), fixture(flags=0), (1, 1, 1)),
            ('nonzero', screen.SELECTED.replace(' != 0', ' == 1'), fixture(flags=0), (-1, -1, -1)),
            ('no-teardown', screen.SELECTED.replace('        func_1503E260(slot);', ''), fixture(), (1, 1, 1)),
        )
        for name, source, memory, results in controls:
            self.assertNotEqual(source, screen.SELECTED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, source)
            model = ActiveOracle(words, memory, results=results).run()
            expected = Reference(memory, results=results).run()
            self.assertTrue((public(model.memory), model.calls) != (public(expected.memory), expected.calls), name)
        wrong = screen.SELECTED.replace('func_1503EF4C(2,', 'func_1503EF4C(1,')
        _, words = screen.compile_candidate(self.root, self.out, 'negative-selector', wrong)
        with self.assertRaises(AssertionError): ActiveOracle(words, fixture()).run()
        wide = screen.SELECTED.replace('    struct106 *control;', '    struct106 *control;\n    s32 timer;').replace(
            '    *(s16 *)((u8 *)control + 0xC) -= D_800BE9E4;',
            '    timer = *(s16 *)((u8 *)control + 0xC) - D_800BE9E4;\n    *(s16 *)((u8 *)control + 0xC) = timer;').replace(
            '    if (*(s16 *)((u8 *)control + 0xC) <= 0)', '    if (timer <= 0)')
        _, words = screen.compile_candidate(self.root, self.out, 'negative-wide-branch', wide)
        model = ActiveOracle(words, fixture(timer=32767, clock=-1)).run()
        self.assertNotEqual(model.calls, Reference(fixture(timer=32767, clock=-1)).run().calls)
        self.receipt('controls', semantic=8, all_effective=True, zero_boundary_and_halfword_wrap_discriminate=True)

    def test_07_complete_owner_and_both_padders(self):
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
            text, functions, relocs = parse_object(obj); item = functions[name]
            a, b = item['value'], item['value']+item['size']
            return item['size'], text[a:b], {o-a:r for o,r in relocs.items() if a <= o < b}
        names = set(parse_object(objects[0])[1]); self.assertEqual(names, set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(objects[0], name), fingerprint(objects[1], name), name)
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
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)], check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+340] = parsed[1][0][start:start+340]
            self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start <= o < start+340},
                {o:r for o,r in parsed[1][2].items() if not start <= o < start+340})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', neighbors=len(names)-1, pools_exact=True, both_production_padders=True,
            GLOBAL_ASM_processed=True, dispatcher_finish_teardown_predicate_query_preparation_unchanged=True)

    def test_08_literal_source_whole_ELF_and_seven_inputs(self):
        source = (self.out/'before-source').read_text(); now = (self.root/screen.SOURCE).read_text()
        changed = now != source
        self.assertEqual(now, screen.install(source) if changed else source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 340)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if changed:
            struct.pack_into('>85I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 340)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            old = (self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(), self.baseline[name])
            if name not in ('source', 'elf'): self.assertEqual((self.root/path).read_bytes(), old, name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=changed, changed_ELF_bytes=sum(a != b for a,b in zip(self.before, actual)),
            target_bytes=sum(a != b for a,b in zip(self.before[start:start+340], actual[start:start+340])),
            extent_bytes=sum(a != b for a,b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), seven_inputs_exact=True,
            literal_no_projection_or_metadata_exception=True, protected_data=data)

    def test_09_effective_stale_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for source in (screen.install(before), before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(source)
        rt, rb = Path.read_text, Path.read_bytes
        source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p,*a,**k: actual+'\n' if p == source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_seven_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        start = elf_slot_offset(actual, screen.ENTRY, 340)
        extent = installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)
        for offset in (start+4, start+340, extent+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_seven_inputs()
        guards = self.root/self.paths['guards']; wrong = bytearray(guards.read_bytes()); wrong[0] ^= 1
        with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_whole_ELF_and_seven_inputs()
        self.receipt('integrity-controls', stale=2, source=1, ELF=3, guards=1, all_effective=True)

    def test_10_original_group2_dispatch_finish_active_chain(self):
        dispatch_entry, finish_entry = state.screen.ENTRY, finish.screen.ENTRY
        dispatch_words = list(struct.unpack_from('>171I', self.before, elf_slot_offset(self.before, dispatch_entry, 684)))
        finish_words = list(struct.unpack_from('>81I', self.before, elf_slot_offset(self.before, finish_entry, 324)))
        self.assertEqual(dispatch_words, list(struct.unpack_from('>171I', self.rom, state.screen.ROM)))
        self.assertEqual(finish_words, list(struct.unpack_from('>81I', self.rom, finish.screen.ROM)))
        for name, entries in (('D_8008443C', (0x1503EFC4, 0x1503F108, finish_entry)),
                ('D_80084448', (0x1503EEC0, 0x1503EEC0, screen.ENTRY))):
            actual = struct.unpack_from('>3I', self.before, elf_slot_offset(self.before, SYMBOLS[name], 12))
            self.assertEqual(actual, entries)
        class ChainReference(state.Reference):
            def call(model, target, args):
                if target in (finish_entry, screen.ENTRY):
                    model.calls.append((target, *args))
                    inner = (finish.Reference(model.memory, args[0], symbols=SYMBOLS, actual=True).run()
                        if target == finish_entry else Reference(model.memory, args[0], symbols=SYMBOLS,
                            actions=model.actions, actual=True).run())
                    model.memory = inner.memory; model.calls.extend(inner.calls)
                    return 0xA5000002
                return super().call(target, args)
        class ChainOracle(ActiveOracle):
            def execute(model, word):
                if word >> 26 == 32:
                    rs, rt, imm = word >> 21 & 31, word >> 16 & 31, word & 65535
                    a = (model.r[rs]+(imm if imm < 32768 else imm-65536)) & 0xFFFFFFFF
                    value = model.get(a, 1)
                    model.r[rt] = (value if value < 128 else value-256) & 0xFFFFFFFF
                else:
                    super().execute(word)
            def record_call(model, target):
                if target in (finish_entry, screen.ENTRY):
                    args = model.arguments(1); model.calls.append((target, *args)); model.events.append(('CALL', target, args))
                elif target in (SYMBOLS['func_1503ECA0'], SYMBOLS['func_1503E260'], QUERY,
                        SYMBOLS['func_10004074'], SYMBOLS['func_1503E1F4']):
                    super().record_call(target)
                else:
                    state.StateOracle.record_call(model, target)
            def hook(model, target):
                if target in (SYMBOLS['func_1503ECA0'], SYMBOLS['func_10004074']):
                    super().hook(target)
                else:
                    state.StateOracle.hook(model, target)
        cases = 0
        for marker, count, clock, phase, mode in itertools.product((1, 2, 3), (0, 1, 3),
                (1, 300, -1), (0, 8), ('none', 'free-mutation')):
            memory = state.fixture(state=marker, count=count, group=2, existing=True, types=(254,), symbols=SYMBOLS)
            record = address(SYMBOLS['D_800C6660'], 7, 16)
            put(memory, record+12, 1, 2); put(memory, SYMBOLS['D_800BE9E4'], clock)
            put(memory, SYMBOLS['D_8008443C']+8, finish_entry); put(memory, SYMBOLS['D_80084448']+8, screen.ENTRY)
            put(memory, SYMBOLS['D_80084460']+8, 0)
            put(memory, SYMBOLS['D_8008446C']+8, finish.PAIRS)
            for i, pair in enumerate(((1, 0), (0, 2), (0, 0))):
                put(memory, finish.PAIRS+i*8, pair[0]); put(memory, finish.PAIRS+i*8+4, pair[1])
            actions = teardown.actions_for(mode)
            expected = ChainReference(memory, symbols=SYMBOLS, actions=actions).run(); models = []
            for words in (self.retail, self.raw, self.padded):
                code = dict(self.connected)
                code.update({finish_entry+i*4:w for i,w in enumerate(finish_words)})
                code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                model = ChainOracle(dispatch_words, memory, start=dispatch_entry, actions=actions, connected=code, actual=True)
                model.chain_actor = None; model.allocation = state.BUFFER
                model.run(); models.append(model)
                self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
            for model in models[1:]:
                self.assertEqual((model.memory, model.events, model.r, model.f),
                    (models[0].memory, models[0].events, models[0].r, models[0].f))
            cases += 1
        self.receipt('original-dispatch-chain', cases=cases,
            actual_dispatch171_finish81_active85_teardown89_predicate27_query30=True,
            original_group2_finish_and_active_tables=True, initial_NULL_teardown_table=True,
            preparation_free_and_motion_matrix_tails_bounded_models=True, element_skip_fixtures_not_full_gameplay=True)

    def test_11_native32_timer_width_flags_callbacks_and_actual_helper(self):
        helper = re.findall(r'^s32 func_1503EF4C\([^;{}]+\) \{.*?^\}', (self.out/'before-source').read_text(), re.M | re.S)
        self.assertEqual(len(helper), 1)
        prefix = NATIVE+helper[0].replace('func_1503EF4C', 'actual_mask_query')+NATIVE_QUERY
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:], prefix+screen.SELECTED+NATIVE_MAIN, profile), (0, ''))
        for name, body in (('expiry', screen.SELECTED.replace(' <= 0', ' < 0')),
                ('unsigned', screen.SELECTED.replace('s16 *', 'u16 *')),
                ('bit', screen.SELECTED.replace(' |= 8', ' |= 16'))):
            code, detail = self.run_native('native-negative-'+name, prefix+body+NATIVE_MAIN)
            self.assertEqual(code, 1); self.assertEqual(len(detail), 3)
        self.receipt('native', profiles=['O2', 'O0'], modeled_cases_per_profile=21600,
            actual_helper_cases_per_profile=1200, effective_controls=3,
            all26_actor_control_records_canaries_and_protocol=True, no_signed32_overflow_fixtures=True,
            native_truncation_qualified_GCC32_not_general_portability_or_physical_store_hardware_claim=True)


NATIVE = r'''
typedef unsigned char u8; typedef short s16; typedef unsigned short u16;
typedef int s32; typedef unsigned int u32;
typedef struct {s32 unk0,unk4,unk8;u8 pad[3],unkF;} struct106;
typedef struct {u8 prefix[148];s32 unk94;u8 tail[660];} struct127;
static struct106 D_800C6660[26],expectedControl[26];
static struct127 D_800CC2D0[26],expectedActor[26];
static s32 D_800BE9E4,pairs[6],*D_8008446C[3]={0,0,pairs};
#define D_800C6664 ((u8 *)D_800C6660+4)
#define D_800C6668 ((u8 *)D_800C6660+8)
static int slot,mode,row,n,error,useActual,expectClock;
static u32 results[3],trace[5][4],expectedTrace[5][4];
static s16 *timer(void){return (s16 *)((u8 *)&D_800C6660[slot]+12);}
static void record(u32 label,u32 a,u32 b,u32 c){
    if(n>=5){error=1;return;}trace[n][0]=label;trace[n][1]=a;trace[n][2]=b;trace[n++][3]=c;
}
static void mutate(int label,int index){
    if(label==1 && mode==1)*timer()=2;
    if(label==1 && mode==2)D_800BE9E4=-1;
    if(label==2 && mode==3){D_800CC2D0[slot].unk94=(s32)0x80000000U;*timer()=300;}
    if(label==3 && mode==4)D_800CC2D0[slot].unk94=(s32)(0x80000000U+(u32)index);
    if(label==2 && mode==5){D_800C6660[slot].unk4=0;D_800C6660[slot].unk8=0;}
}
void func_1503ECA0(s32 value){if(value!=slot)error=2;record(1,value,0,0);mutate(1,0);}
void func_1503E260(s32 value){if(value!=slot)error=3;record(2,value,0,0);mutate(2,0);}
static u32 reference_query(int index){
    u32 first=(u32)pairs[index*2],second=(u32)pairs[index*2+1];
    if(first && !(first&(u32)D_800C6660[slot].unk4))return 0;
    if(second && !(second&(u32)D_800C6660[slot].unk8))return 0;
    return 1;
}
static void reference(void){
    static u32 bits[3]={8,4,2};s32 value;
    record(1,slot,0,0);mutate(1,0);value=(s32)*timer()-D_800BE9E4;*timer()=(s16)value;
    if(*timer()>0)return;
    record(2,slot,0,0);mutate(2,0);
    for(int i=0;i<3;i++){record(3,2,i,slot);mutate(3,i);
        if(useActual?reference_query(i):results[i])D_800CC2D0[slot].unk94=(s32)((u32)D_800CC2D0[slot].unk94|bits[i]);}
}
static void reset(s16 t,s32 clock,u32 flags,int which,int m,int actual,u32 mask1,u32 mask2,int pattern){
    for(u32 i=0;i<sizeof(D_800C6660);i++)((u8 *)D_800C6660)[i]=(u8)(i*17+53);
    for(u32 i=0;i<sizeof(D_800CC2D0);i++)((u8 *)D_800CC2D0)[i]=(u8)(i*13+37);
    slot=which;mode=m;row=n=error=0;useActual=actual;D_800BE9E4=clock;*timer()=t;
    D_800CC2D0[slot].unk94=(s32)flags;D_800C6660[slot].unk4=(s32)mask1;D_800C6660[slot].unk8=(s32)mask2;
    for(int i=0;i<6;i++)pairs[i]=pattern==0?0:pattern==1?(1<<(i%3)):pattern==2?(s32)0x80000000U:-1;
}
static int report(u32 a,u32 b,u32 c){u32 data[3]={a,b,c};s32 r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
'''

NATIVE_QUERY = r'''
s32 func_1503EF4C(s32 group,s32 index,s32 value){
    if(group!=2 || index!=row || value!=slot)error=4;
    row++;record(3,group,index,value);mutate(3,index);
    return useActual?actual_mask_query(group,index,value):(s32)results[index];
}
'''

NATIVE_MAIN = r'''
static int qualify(s16 t,s32 clock,u32 flags,int which,int m,int actual,u32 mask1,u32 mask2,int pattern,u32 c){
    int wantN;
    reset(t,clock,flags,which,m,actual,mask1,mask2,pattern);reference();wantN=n;expectClock=D_800BE9E4;
    for(u32 i=0;i<sizeof(expectedControl);i++)((u8 *)expectedControl)[i]=((u8 *)D_800C6660)[i];
    for(u32 i=0;i<sizeof(expectedActor);i++)((u8 *)expectedActor)[i]=((u8 *)D_800CC2D0)[i];
    for(int i=0;i<n;i++)for(int j=0;j<4;j++)expectedTrace[i][j]=trace[i][j];
    reset(t,clock,flags,which,m,actual,mask1,mask2,pattern);func_1503F2B0(slot);
    if(error || n!=wantN || D_800BE9E4!=expectClock)return report(c,0,error);
    for(int i=0;i<n;i++)for(int j=0;j<4;j++)if(trace[i][j]!=expectedTrace[i][j])return report(c,1,i*4+j);
    for(u32 i=0;i<sizeof(expectedControl);i++)if(((u8 *)expectedControl)[i]!=((u8 *)D_800C6660)[i])return report(c,2,i);
    for(u32 i=0;i<sizeof(expectedActor);i++)if(((u8 *)expectedActor)[i]!=((u8 *)D_800CC2D0)[i])return report(c,3,i);
    return 0;
}
static int run(void){
    static s16 timers[6]={32767,-32768,-1,0,1,2};static s32 clocks[5]={0,1,-1,32768,65536};
    static u32 flags[5]={0,0xFFFFFFFFU,0x80000000U,0x12345678U,14};
    static int slots[3]={0,7,25};static u32 masks[5]={0,1,2,0x80000000U,0xFFFFFFFFU};
    u32 cases=0;
    if(sizeof(void *)!=4 || sizeof(struct106)!=16 || sizeof(struct127)!=812)return 2;
    for(int t=0;t<6;t++)for(int k=0;k<5;k++)for(int f=0;f<5;f++)for(int r=0;r<8;r++)for(int s=0;s<3;s++)for(int m=0;m<6;m++){
        results[0]=(r&1)?0xFFFFFFFFU:0;results[1]=(r&2)?0x80000000U:0;results[2]=(r&4)?1:0;cases++;
        if(qualify(timers[t],clocks[k],flags[f],slots[s],m,0,~0U,~0U,0,cases))return 1;
    }
    if(cases!=21600)return 3;
    for(int t=0;t<4;t++)for(int a=0;a<5;a++)for(int b=0;b<5;b++)for(int p=0;p<4;p++)for(int s=0;s<3;s++){
        cases++;if(qualify(timers[t+2],1,0xFFFFFFFFU,slots[s],0,1,masks[a],masks[b],p,cases))return 1;
    }
    return cases==22800?0:4;
}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
