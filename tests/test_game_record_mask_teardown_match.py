"""Complete mask transfer/teardown, closed spill guards and linked-only audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_mask_teardown_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, TABLE, BUFFER, HELPER = guest.STACK, 0x50000, 0x24000, 0x1503E1F4
CALLER, QUERY, PREPARE, CLOCK, PAIRS, PAIR_TABLE = 0x1503F2B0, 0x1503EF4C, 0x1503ECA0, 0x800BE9E4, 0x55000, 0x8008446C
FREE = screen.SYMBOLS['func_10004074']
address, public, writes = state.address, state.public, state.writes


def fixture(slot=7, marker=1, group=2, count=5, table=True, buffer=True,
        masks=(0xFFFFFFFF, 0xFFFFFFFF), values=(0, 255, 31, 32, 128), flags=0xB5,
        actor_mask=0x12345678, symbols=screen.SYMBOLS, alias=None):
    record = address(symbols['D_800C6660'], slot, 16)
    actor = address(symbols['D_800CC2D0'], slot, 812)
    pointer = TABLE if alias is None else alias
    memory = {STACK+i: 0xA5 for i in range(-0x200, 0x100)}
    for base, length in ((record-16, 48), (actor-16, 844), (BUFFER-16, 32)):
        memory.update({(base+i) & 0xFFFFFFFF: (i*17+0x35) & 255 for i in range(length)})
    if marker:
        put(memory, symbols['D_80084460']+group*4, pointer if table else 0)
        if table:
            put(memory, symbols['D_80098914']+group, count, 1)
            for i in range(count): put(memory, pointer+i, values[i % len(values)], 1)
    put(memory, record, BUFFER if buffer else 0); put(memory, record+4, masks[0]); put(memory, record+8, masks[1])
    put(memory, record+14, group, 1); put(memory, record+15, marker, 1)
    put(memory, actor+0x74, flags, 1); put(memory, actor+0x94, actor_mask)
    return memory


def actions_for(mode, slot=7, symbols=screen.SYMBOLS, pointer=TABLE):
    record = address(symbols['D_800C6660'], slot, 16)
    actor = address(symbols['D_800CC2D0'], slot, 812)
    return {
        'predicate-byte': {('predicate', 0): ((pointer, 7, 1),)},
        'predicate-sentinel': {('predicate', 0): ((pointer, 255, 1),)},
        'predicate-mask': {('predicate', 0): ((actor+0x94, 0x80000000, 4), (record+4, 0, 4), (record+8, 1, 4))},
        'predicate-next': {('predicate', 0): ((pointer+1, 5, 1), (record+15, 0, 1),
            (record+14, 255, 1), (symbols['D_80098914']+2, 0, 1), (symbols['D_80084460']+8, 0, 4))},
        'predicate-buffer': {('predicate', 0): ((record, 0, 4),)},
        'free-mutation': {('free', 0): ((record, 0x98765430, 4), (record+15, 7, 1), (actor+0x74, 0xDA, 1))},
        'free-mask': {('free', 0): ((record+4, 0, 4), (record+8, 0, 4))},
    }.get(mode, {})


class Reference(state.Reference):
    def __init__(self, memory, slot=7, symbols=screen.SYMBOLS, actions=None):
        super().__init__(memory, slot, symbols, actions)
    def call(self, target, args):
        args = tuple(v & 0xFFFFFFFF for v in args)
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        label = 'predicate' if target == self.symbols['func_1503E1F4'] else 'free'
        self.mutate(label)
        if label == 'predicate':
            index, slot = args; record = address(self.symbols['D_800C6660'], slot, 16)
            return int(bool(self.get(record+(4 if index < 32 else 8)) & (1 << (index & 31))))
        return 0xA5000002
    def run(self):
        s, slot = self.symbols, self.slot
        record = address(s['D_800C6660'], slot, 16); actor = address(s['D_800CC2D0'], slot, 812)
        if not self.get(record+15, 1): return self
        group = self.get(record+14, 1)
        bits = self.get(s['D_80084460']+group*4)
        if bits:
            count = self.get(s['D_80098914']+group, 1)
            for index in range(count):
                if self.get(bits+index, 1) != 255 and self.call(s['func_1503E1F4'], (index, slot)):
                    bit = self.get(bits+index, 1); mask = self.get(actor+0x94)
                    self.put(actor+0x94, mask | (1 << (bit & 31)))
        buffer = self.get(record); self.put(record+15, 0, 1)
        if buffer: self.call(s['func_10004074'], (buffer,))
        flags = self.get(actor+0x74, 1)
        self.put(record, 0); self.put(actor+0x74, flags & ~128, 1)
        return self


class TeardownOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, slot=7, phase=0, symbols=screen.SYMBOLS,
            entry=screen.ENTRY, connected=None, actions=None):
        super().__init__(words, memory, arguments=(slot & 0xFFFFFFFF,), phase=phase, entry=entry, connected=connected)
        self.symbols, self.slot, self.actions, self.occurrences = symbols, slot, actions or {}, {}
    def mutate(self, label):
        n = self.occurrences.get(label, 0); self.occurrences[label] = n+1
        for a, value, size in self.actions.get((label, n), ()): self.put(a, value, size)
    def record_call(self, target):
        n = 2 if target == self.symbols['func_1503E1F4'] else 3 if target == QUERY else 1
        args = self.arguments(n); self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        if target == self.symbols['func_1503E1F4']: self.mutate('predicate')
    def hook(self, target):
        if target == self.symbols['func_1503E1F4']:
            index, slot = self.r[4:6]; record = address(self.symbols['D_800C6660'], slot, 16)
            result = int(bool(self.get(record+(4 if index < 32 else 8), 4) & (1 << (index & 31))))
        else:
            assert target in (self.symbols['func_10004074'], PREPARE), hex(target)
            if target == self.symbols['func_10004074']:
                record = address(self.symbols['D_800C6660'], self.slot, 16)
                assert self.memory[record+15] == 0
                self.mutate('free')
            result = 0xA5000002
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.r[2] = result


class GameRecordMaskTeardownMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-mask-teardown-match-test'; cls.out.mkdir(exist_ok=True)
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
        assert cls.baseline['source'] == '2dec3adb58a154d8be55eade61a66857a381e1b45886d8c9d5cc75535b487d4b'
        assert cls.baseline['elf'] == 'f529e1b3dbe2f252a309438b8a3e84bfb587d7f39db0199e48c8627569db62c1'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>89I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        source = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1]
        body = source.split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        guards = (cls.out/'before-guards').read_bytes()
        cls.after_guards = screen.guard_successor(guards)
        (cls.out/'after-guards').write_bytes(cls.after_guards)
        (cls.out/'isolated-guards').write_bytes(screen.guard_successor(guards.splitlines(keepends=True)[0]))
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot,
            word_patches_path=cls.out/'isolated-guards', filename='generated_6B320'))
        cls.helper = list(struct.unpack_from('>27I', cls.before, elf_slot_offset(cls.before, HELPER, 108)))
        assert cls.helper == list(struct.unpack_from('>27I', cls.rom, 0x6B6A4))
        cls.connected = {HELPER+i*4: w for i, w in enumerate(cls.helper)}

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def link(self, name, start=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>89I', sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def compare(self, memory, slot=7, phase=0, actions=None, forms=None, symbols=screen.SYMBOLS,
            start=screen.ENTRY, actual=True):
        expected = Reference(memory, slot, symbols, actions).run()
        words = forms or (self.retail, self.raw, self.padded)
        models = [TeardownOracle(w, memory, slot, phase, symbols, start,
            self.connected if actual else None, actions).run() for w in words]
        for model in models:
            self.assertEqual((public(model.memory), model.calls, writes(model)),
                (public(expected.memory), expected.calls, writes(expected)))
        for i, model in enumerate(models):
            external = [e for e in model.events if e[0] == 'CALL' or not STACK-0x200 <= e[1] < STACK+0x100]
            self.assertEqual(external, [e for e in expected.events if e[0] == 'CALL' or not STACK-0x200 <= e[1] < STACK+0x100])
            if i:
                self.assertEqual((model.r, model.f, model.lo), (models[0].r, models[0].f, models[0].lo))
        if len(models) == 3:
            self.assertEqual((models[0].memory, models[0].events), (models[2].memory, models[2].events))
        return models

    def test_01_full_body_frame_extent_and_closed_guard_pair(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (89, 80, 2))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual([(i*4, a, b) for i, (a, b) in enumerate(zip(self.raw, self.retail)) if a != b],
            [(0x120, 0xAFA20038, 0xAFA2003C), (0x124, 0x8FA20038, 0x8FA2003C)])
        self.assertEqual(self.link('original'), self.retail); self.assertEqual(self.padded, self.retail)
        table = elf_slot_offset(self.before, screen.SYMBOLS['D_80084460'], 12)
        counts = elf_slot_offset(self.before, screen.SYMBOLS['D_80098914'], 3)
        self.assertEqual(struct.unpack_from('>3I', self.before, table), (0, 0, 0))
        self.assertEqual(self.before[counts:counts+3], bytes((27, 31, 45)))
        meta, words = screen.compile_candidate(self.root, self.out, 'compact', profile='compact')
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences'], words), (89, 80, 2, self.raw))
        self.receipt('shape', words=89, direct=87, guards=2, frame=80, extent=356,
            no_profile_change=True, guards_only_closed_private_actor_spill_38_to_3C=True,
            actual_initial_three_null_tables=True, actual_group_counts=[27, 31, 45])

    def test_02_state_domain_pointer_count_mask_and_bit_boundaries(self):
        reached, cases = set(), 0
        for marker in range(256):
            models = self.compare(fixture(marker=marker)); reached.update(models[0].visits); cases += 1
        for count, table, buffer, masks, phase in itertools.product((0, 1, 3, 4, 5, 27, 31, 45, 128, 255),
                (False, True), (False, True), ((0, 0), (0xFFFFFFFF, 0xFFFFFFFF), (0x80000001, 0xA5A5A5A5)), (0, 8)):
            models = self.compare(fixture(count=count, table=table, buffer=buffer, masks=masks), phase=phase)
            reached.update(models[0].visits); cases += 1
        for slot, group, phase in itertools.product((0, 25, -1, 0x80000000, 0x7FFFFFFF), (0, 2, 255), (0, 8)):
            self.compare(fixture(slot=slot, group=group), slot=slot, phase=phase); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+356, 4))), 89)
        self.assertEqual(len(reached & set(self.connected)), 26)
        self.receipt('guest', cases=cases, forms=3, all_state_bytes=True, all_target_words=89,
            actual_predicate_words_reached=26, predicate_total=27, unreachable_duplicate_zero=True,
            no_count_read_for_NULL_table_or_state_zero=True, invalid_slots_and_large_shifts_mapped_guest_only=True)

    def test_03_callback_live_reads_cached_inputs_and_public_aliases(self):
        cases = 0
        for mode, phase in itertools.product(('predicate-byte', 'predicate-sentinel', 'predicate-mask',
                'predicate-next', 'predicate-buffer', 'free-mutation'), (0, 8)):
            models = self.compare(fixture(), phase=phase, actions=actions_for(mode)); cases += 1
            if mode == 'free-mutation':
                record = screen.SYMBOLS['D_800C6660']+7*16
                self.assertEqual(read(models[0].memory, record, 4), 0); self.assertEqual(models[0].memory[record+15], 7)
        actor = screen.SYMBOLS['D_800CC2D0']+7*812
        record = screen.SYMBOLS['D_800C6660']+7*16
        for alias, phase in itertools.product((actor+0x94, actor+0x74, record+4, record+8), (0, 8)):
            self.compare(fixture(alias=alias), phase=phase); cases += 1
        self.receipt('lifetimes', cases=cases, entry_reloaded_after_predicate=True,
            record_count_group_and_table_base_cached=True, mask_and_buffer_and_flag_reads_live=True,
            state_cleared_before_free_pointer_cleared_after=True, free_state_mutation_preserved=True,
            all_external_caller_saved_GPR_FPR_clobbered=True, aliases_mapped_guest_only=True)

    def test_04_independent_relocations(self):
        cases = 0
        for j, start in enumerate((0x15207FFC, 0x15308004)):
            symbols = {name: (0x80107FFC if i % 2 == j else 0x80218004)+i*0x10000
                for i, name in enumerate(screen.SYMBOLS)}
            symbols.update(func_1503E1F4=0x15418004, func_10004074=0x15427FFC)
            forms = tuple(self.link(name, start, symbols) for name in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[2])
            for table, buffer, phase, mode in itertools.product((False, True), (False, True), (0, 8), ('none', 'free-mutation')):
                self.compare(fixture(symbols=symbols, table=table, buffer=buffer), phase=phase, symbols=symbols,
                    start=start, actions=actions_for(mode, symbols=symbols), forms=forms, actual=False); cases += 1
        self.receipt('rebases', symbols=6, links=2, cases=cases, HI_LO_carries=True,
            actual_predicate_retail_only_hook_for_rebases=True)

    def test_05_fired_fault_prefixes_retail_and_guarded_and_raw_public_boundary(self):
        pairs = 0
        for marker, table, buffer, phase in ((0, False, False, 0), (1, False, True, 8), (1, True, True, 0)):
            memory = fixture(marker=marker, table=table, buffer=buffer, count=1)
            complete = TeardownOracle(self.retail, memory, phase=phase, connected=self.connected).run()
            for failure in range(complete.accesses):
                models = [TeardownOracle(w, memory, phase=phase, connected=self.connected)
                    for w in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = failure
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, failure)
                self.assertEqual((models[0].memory, models[0].events, models[0].r),
                    (models[2].memory, models[2].events, models[2].r))
                self.assertEqual(public(models[0].memory), public(models[1].memory))
                a = [e for e in models[0].events if e[0] == 'CALL' or not STACK-0x200 <= e[1] < STACK+0x100]
                b = [e for e in models[1].events if e[0] == 'CALL' or not STACK-0x200 <= e[1] < STACK+0x100]
                self.assertEqual(a, b); pairs += 1
        self.receipt('faults', fired_triplets=pairs, retail_guarded_private_exact=True,
            raw_public_exact_private_spill_address_differs=True, not_portable_C_fault_semantics=True)

    def test_06_fresh_semantic_and_guard_negative_controls(self):
        controls = (
            ('sentinel', screen.SELECTED.replace('bits[index] != 255', 'bits[index] != 128'), 'none'),
            ('cached-bit', screen.SELECTED.replace('    s32 index;', '    s32 index;\n    u8 bit;').replace(
                '                if (bits[index] != 255', '                bit = bits[index];\n                if (bit != 255').replace(
                '1U << bits[index]', '1U << bit'), 'predicate-byte'),
            ('lost-mask', screen.SELECTED.replace('unk94 |=', 'unk94 ='), 'none'),
            ('early-pointer-clear', screen.SELECTED.replace('            func_10004074((void *)record->unk0);',
                '            record->unk0 = 0;\n            func_10004074((void *)record->unk0);'), 'none'),
            ('late-state-clear', screen.SELECTED.replace('        record->unkF = 0;\n', '').replace(
                '        record->unk0 = 0;', '        record->unkF = 0;\n        record->unk0 = 0;'), 'free-mutation'),
            ('stale-final-flag', screen.SELECTED.replace('    s32 index;', '    s32 index;\n    u8 flags;').replace(
                '        record->unkF = 0;', '        flags = D_800CC2D0[slot].unk74;\n        record->unkF = 0;').replace(
                'D_800CC2D0[slot].unk74 &= ~0x80', 'D_800CC2D0[slot].unk74 = flags & ~0x80'), 'free-mutation'))
        for name, body, mode in controls:
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            with self.assertRaises(AssertionError): self.compare(fixture(), forms=(words,), actions=actions_for(mode))
        for index in (0x120//4, 0x124//4):
            wrong = self.padded.copy(); wrong[index] = self.raw[index]
            with self.assertRaises(AssertionError): self.compare(fixture(), forms=(wrong,))
        text = (self.out/'isolated-guards').read_text()
        (self.out/'wrong-guard').write_text(text.replace('0xAFA20038', '0xAFA20034'))
        with self.assertRaises(ValueError):
            emit_padded_assembly(self.out/'selected.o', self.out/'slot.s', word_patches_path=self.out/'wrong-guard', filename='generated_6B320')
        self.receipt('controls', fresh_semantic=6, single_half_pair_rejections=2, stale_expected_word_rejected=True, all_effective=True)

    def test_07_complete_owner_all_neighbors_and_both_real_padders(self):
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
            start, end = item['value'], item['value']+item['size']
            return item['size'], text[start:end], {o-start: r for o, r in relocations.items() if start <= o < end}
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
                subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches', str(self.out/(stage+'-guards'))],
                    check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)],
                    check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+356] = parsed[1][0][start:start+356]
            self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o: r for o, r in parsed[0][2].items() if not start <= o < start+356},
                {o: r for o, r in parsed[1][2].items() if not start <= o < start+356})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', unchanged_neighbors=len(names)-1, GLOBAL_ASM_postprocessed=True,
            pools_exact=True, both_production_padders=True, actual_dispatcher171_and_predicate27_unchanged=True)

    def test_08_literal_source_guard_successor_whole_ELF_and_other_inputs(self):
        before_source = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text()
        now = current != before_source
        self.assertEqual(current, screen.install(before_source) if now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 356)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if now: struct.pack_into('>89I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 356)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            old = (self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(), self.baseline[name])
            if name not in ('source', 'elf'):
                self.assertEqual((self.root/path).read_bytes(), self.after_guards if name == 'guards' and now else old, name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, changed_ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+356], actual[start:start+356])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), guard_prefix_exact_two_rows_only=True,
            literal_no_projection_or_metadata_exception=True, protected_data=data, other_six_inputs_exact=True)

    def test_09_native32_valid_bit_range_all_states_and_callback_mutations(self):
        for profile in ('-O2', '-O0'):
            code, detail = self.run_native('native-'+profile[1:], NATIVE+screen.SELECTED+NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''))
        code, _ = self.run_native('native-negative', NATIVE+screen.SELECTED.replace('bits[index] != 255', 'bits[index] != 31')+NATIVE_MAIN)
        self.assertNotEqual(code, 0)
        self.receipt('native', profiles=['O2', 'O0'], states=256, cases=61440, modes=6,
            counts=[0, 1, 3, 4, 5, 27, 31, 45, 128, 255], bit_values_0_to_31_and_skipped_255=True,
            predicate_defined_mask_hook_not_original_shift_C=True, no_large_native_shift_or_hardware_claim=True)

    def test_10_actual_retail_caller85_and_linked_mask_query30_chain(self):
        caller = list(struct.unpack_from('>85I', self.rom, 0x6C760))
        query = list(struct.unpack_from('>30I', self.before, elf_slot_offset(self.before, QUERY, 120)))
        self.assertEqual(query, list(struct.unpack_from('>30I', self.rom, 0x6C3FC)))
        cases, reached = 0, set()
        for timer, masks, phase, mode in itertools.product((2, 1, 0, -1), ((0, 0), (0xFFFFFFFF, 0xFFFFFFFF), (1, 0), (0, 2)),
                (0, 8), ('none', 'free-mask')):
            memory = fixture(masks=masks); record = screen.SYMBOLS['D_800C6660']+7*16
            actor = screen.SYMBOLS['D_800CC2D0']+7*812
            put(memory, CLOCK, 1); put(memory, record+12, timer, 2)
            put(memory, PAIR_TABLE+8, PAIRS)
            for index, pair in enumerate(((1, 0), (0, 2), (0, 0))):
                put(memory, PAIRS+index*8, pair[0]); put(memory, PAIRS+index*8+4, pair[1])
            actions = actions_for(mode)
            expected_input = memory.copy(); put(expected_input, record+12, timer-1, 2)
            calls = [(PREPARE, 7)]
            if timer-1 <= 0:
                expected = Reference(expected_input, actions=actions).run(); calls += [(screen.ENTRY, 7), *expected.calls]
                for i, bit in enumerate((8, 4, 2)):
                    calls.append((QUERY, 2, i, 7))
                    first, second = read(expected.memory, PAIRS+i*8, 4), read(expected.memory, PAIRS+i*8+4, 4)
                    if (not first or first & read(expected.memory, record+4, 4)) and (not second or second & read(expected.memory, record+8, 4)):
                        put(expected.memory, actor+0x94, read(expected.memory, actor+0x94, 4) | bit)
            else: expected = Reference(expected_input)
            models = []
            for body in (self.retail, self.raw, self.padded):
                connected = dict(self.connected)
                connected.update({screen.ENTRY+i*4: w for i, w in enumerate(body)})
                connected.update({QUERY+i*4: w for i, w in enumerate(query)})
                model = TeardownOracle(caller, memory, phase=phase, entry=CALLER, connected=connected, actions=actions).run()
                self.assertEqual((public(model.memory), model.calls), (public(expected.memory), calls))
                reached.update(model.visits); models.append(model)
            self.assertEqual((models[0].memory, models[0].events, models[0].r),
                (models[2].memory, models[2].events, models[2].r))
            self.assertEqual(models[0].r, models[1].r); cases += 1
        self.receipt('caller', cases=cases, forms=3, complete_retail_caller_words=85,
            caller_C_still_placeholder_not_installed_qualification=True,
            teardown_and_predicate_and_linked_query_hooks_removed=True,
            target_words_reached=len(reached & set(range(screen.ENTRY, screen.ENTRY+356, 4))),
            preparation_and_free_bounded_models=True, query_existing_two_commutative_guards_preserved=True)

    def test_11_effective_stale_installer_and_literal_audit_rejections(self):
        before = (self.out/'before-source').read_text(); qualified = screen.install(before)
        for stale in (qualified, before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        with self.assertRaises(AssertionError): screen.guard_successor(self.after_guards)
        rt, rb = Path.read_text, Path.read_bytes
        source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: actual+'\n' if p == source else rt(p, *a, **k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_guard_successor_whole_ELF_and_other_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        start = elf_slot_offset(actual, screen.ENTRY, 356); extent = installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)
        for offset in (start+4, start+356, extent+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_guard_successor_whole_ELF_and_other_inputs()
        guards = self.root/self.paths['guards']; wrong = bytearray(guards.read_bytes()); wrong[0] ^= 1
        with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_guard_successor_whole_ELF_and_other_inputs()
        self.receipt('integrity-controls', stale_source=2, duplicate_guards=1, source_rejection=1,
            ELF_rejections=3, prefix_guard_rejection=1, all_effective=True, production_inputs_not_mutated=True)


NATIVE = r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
#define NULL ((void *)0)
typedef struct {s32 unk0,unk4,unk8;u8 pad[3],unkF;} struct106;
typedef struct {u8 pad[0x74],unk74,rest[0x1F];s32 unk94;u8 tail[0x294];} struct127;
struct106 D_800C6660[26];struct127 D_800CC2D0[26];u8 D_80098914[256],*D_80084460[256];
static u8 bits[255],buffer[8];static int mode,pred,n,w,error,slot;static u32 actual[256][3],want[256][3];
static struct106 expected;static struct127 expectedActor;
static void record(int label,u32 a,u32 b){if(n>=256){error=1;return;}actual[n][0]=label;actual[n][1]=a;actual[n++][2]=b;}
static void expect(int label,u32 a,u32 b){want[w][0]=label;want[w][1]=a;want[w++][2]=b;}
static void mutate(int label){struct106 *r=D_800C6660+slot;struct127 *a=D_800CC2D0+slot;
    if(label==1 && pred++==0){if(mode==1)bits[0]=7;if(mode==2){a->unk94=(s32)0x80000000U;r->unk4=0;r->unk8=1;}
        if(mode==3){bits[1]=5;r->unkF=0;((u8 *)r)[14]=255;D_80098914[2]=0;D_80084460[2]=0;}
        if(mode==4)r->unk0=0;}
    if(label==2 && mode==5){r->unk0=0x98765430;r->unkF=7;a->unk74=0xDA;}}
s32 func_1503E1F4(s32 index,s32 value){struct106 *r=D_800C6660+value;record(1,index,value);mutate(1);
    return ((u32)(index<32?r->unk4:r->unk8)&(1U<<(index&31)))!=0;}
void func_10004074(void *p){if(D_800C6660[slot].unkF)error=2;record(2,(u32)p,0);mutate(2);}
static void reset(int marker,int count,int table,int live,int mutation){int i;struct106 *r=D_800C6660+slot;
    r->unk0=live?(s32)buffer:0;r->unk4=r->unk8=-1;((u8 *)r)[14]=2;r->unkF=(u8)marker;
    D_800CC2D0[slot].unk74=0xB5;D_800CC2D0[slot].unk94=0x12345678;
    D_80098914[2]=(u8)count;D_80084460[2]=table?bits:0;
    for(i=0;i<255;i++)bits[i]=(u8)(i%5==1?255:(i%5==2?31:i%32));
    n=w=error=pred=0;mode=mutation;}
static void reference(void){struct106 *r=D_800C6660+slot;struct127 *a=D_800CC2D0+slot;
    u8 *t;int count,i;u32 p;if(!r->unkF)return;t=D_80084460[((u8 *)r)[14]];
    if(t){count=D_80098914[((u8 *)r)[14]];for(i=0;i<count;i++)if(t[i]!=255){
        expect(1,i,slot);mutate(1);if((u32)(i<32?r->unk4:r->unk8)&(1U<<(i&31)))a->unk94|=1U<<t[i];}}
    p=(u32)r->unk0;r->unkF=0;if(p){expect(2,p,0);mutate(2);}r->unk0=0;a->unk74&=~128;}
static int report(u32 code,u32 c,u32 i){u32 data[3]={code,c,i};s32 result;
__asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");return (s32)code;}
'''

NATIVE_MAIN = r'''
int run(void){int marker,j,table,live,m,i,k,c=0;static int counts[]={0,1,3,4,5,27,31,45,128,255};
    if(sizeof(void *)!=4 || sizeof(struct106)!=16 || sizeof(struct127)!=812
        || __builtin_offsetof(struct127,unk94)!=0x94)return 1;
    slot=7;for(marker=0;marker<256;marker++)for(j=0;j<10;j++)for(table=0;table<2;table++)for(live=0;live<2;live++)for(m=0;m<6;m++,c++){
        reset(marker,counts[j],table,live,m);reference();expected=D_800C6660[slot];expectedActor=D_800CC2D0[slot];k=w;
        reset(marker,counts[j],table,live,m);w=k;func_1503E260(slot);
        if(n!=w || error)return report(2,c,n);
        for(i=0;i<n*3;i++)if(((u32 *)actual)[i]!=((u32 *)want)[i])return report(3,c,i);
        for(i=0;i<16;i++)if(((u8 *)(D_800C6660+slot))[i]!=((u8 *)&expected)[i])return report(4,c,i);
        for(i=0;i<812;i++)if(((u8 *)(D_800CC2D0+slot))[i]!=((u8 *)&expectedActor)[i])return report(5,c,i);
    }return c==61440?0:6;}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
