"""Real guarded consumer objects, relocation carries and owner qualification."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from tools.tests import remaining_donor_checkpoint as donor_checkpoint
from unittest.mock import patch

from tools.experiments import game_actor_burst_consumer_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_actor_burst_consumer_recovery as recovery
from tools.tests import test_game_actor_burst_packet_match as producer
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_one_shot_timer_match import canonical_symbols, symbol_rows
from tools.check_game_data_layout import audit_layout

SERIALIZATION = (
    (('D_80090CD4', 'D_800A5F3C'), (1, 0),
        ((0x80090CD4, 0, 16, 0, 65521), (0x800A5F3C, 0, 16, 0, 6))),
    (('D_800A8DC0', 'func_10019CFC'), (1, 0),
        ((0x800A8DC0, 0, 16, 0, 65521), (0x10019CFC, 112, 18, 0, 3))),
)


def apply_consumer_symbol_serialization(expected):
    with patch.object(producer, 'SERIALIZATION', SERIALIZATION):
        producer.apply_burst_symbol_serialization(expected)


def expected_consumer_image(before, words):
    expected = bytearray(before)
    offset = image.elf_slot_offset(before, source.ENTRY, 1260)
    expected[offset:offset + 1260] = struct.pack('>315I', *words)
    with patch.object(image.screen, 'ENTRY', source.ENTRY):
        size = image.elf_symbol_size_offset(before, source.FUNCTION)
    if struct.unpack_from('>I', before, size)[0] != 12:
        raise ValueError('Expected original 12-byte consumer symbol')
    struct.pack_into('>I', expected, size, 1260)
    apply_consumer_symbol_serialization(expected)
    return bytes(expected)


class AccessBoundary(Exception):
    pass


class TrackedCode(dict):
    def __init__(self, values, owner):
        super().__init__(values)
        self.owner, self.last_pc, self.last_word = owner, None, 0

    def __getitem__(self, pc):
        self.owner.current_pc = pc
        control = self.last_word >> 26 in (1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 23) or (
            self.last_word >> 26 == 0 and self.last_word & 63 in (8, 9))
        self.owner.delay_of = self.last_pc if control and pc == self.last_pc + 4 else None
        self.last_pc, self.last_word = pc, super().__getitem__(pc)
        return self.last_word


class MatchOracle(recovery.ConsumerOracle):
    def __init__(self, *args, fault=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 1260:
            if self.accesses == self.root_fault:
                raise AccessBoundary
            self.accesses += 1


class GameActorBurstConsumerMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-burst-consumer-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(owner=source.SOURCE, caller=producer.source.SOURCE,
            elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', makefile='conker/Makefile',
            assembly='conker/asm/1D43B0.s', layout='conker/retail_layout.us.txt')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            digests = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                digests[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(digests, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == '50b064c6d7af59a7a78eeece1a2b3c8e32b2886b1695097fd6b43044f2b092ee'
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest
        cls.meta, cls.raw = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.object = cls.out / 'selected.o'
        text, functions, relocations = parse_object(cls.object)
        cls.symbol = functions[source.FUNCTION]
        cls.object_words = list(struct.unpack_from('>313I', text, cls.symbol['value']))
        cls.relocations = {at - cls.symbol['value']: value for at, value in relocations.items()
            if cls.symbol['value'] <= at < cls.symbol['value'] + cls.symbol['size']}
        cls.rows = source.guard_rows(cls.object_words, cls.relocations)
        cls.fields = tuple(cls.rows[0])
        cls.guards = cls.out / 'guards.csv'
        cls.write_rows(cls.guards, cls.rows)
        rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>315I', rom, source.ROM))
        cls.memcpy = tuple(struct.unpack_from('>11I', rom, 0x22EC0))
        cls.layout = cls.out / 'layout.csv'
        cls.layout.write_text('section,filename,function,address,end\n'
            'game,generated_1D43B0,func_151A6F00,0x151A6F00,0x151A73EC\n')
        cls.asm = cls.out / 'target.s'
        block = (cls.out / 'before-assembly').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        cls.asm.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
            'endlabel ' + source.FUNCTION + '\n')
        cls.original = cls.assemble('original', cls.asm.read_text())
        cls.padded = {}
        for name, assembly in (
                ('generated', emit_padded_assembly(cls.object, cls.asm, word_patches_path=cls.guards,
                    filename='generated_1D43B0')),
                ('plain', pad_c_object.emit_padded_assembly(cls.object, cls.layout, 'generated_1D43B0',
                    word_patches_path=cls.guards))):
            cls.padded[name] = cls.assemble(name, assembly)
        cls.words, _ = cls.link(cls.padded['generated'], 'qualified')

    @staticmethod
    def write_rows(path, rows):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        path.write_text(stream.getvalue())

    @classmethod
    def assemble(cls, name, assembly):
        path = cls.out / (name + '.s')
        path.write_text(assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)],
            check=True, capture_output=True)
        return obj

    @classmethod
    def link(cls, obj, name, entry=source.ENTRY, symbols=None):
        script = cls.out / (name + '.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in (symbols or source.SYMBOLS).items()],
            '-o', str(elf), str(obj)], check=True, capture_output=True)
        return list(struct.unpack_from('>315I', sections(elf)['.text'][1])), elf

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_actual_padders_full_words_extent_and_moved_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.symbol['size']), (313, 0x168, 1252))
        self.assertEqual(sum(bool(row['insert_after']) for row in self.rows), 2)
        expected = {at + 4 * sum(site * 4 < at for site in (177, 194)): values
            for at, values in self.relocations.items()}
        for name, obj in self.padded.items():
            _, functions, relocations = parse_object(obj)
            self.assertEqual(functions[source.FUNCTION]['size'], 1260)
            self.assertEqual(relocations, expected)
            words, _ = self.link(obj, name + '-retail')
            self.assertEqual(words, self.retail)
        original, _ = self.link(self.original, 'original-retail')
        self.assertEqual(original, self.retail)
        self.receipt('padders', guards=len(self.rows), two_inserted_idle_words=True,
            both_actual_padders_and_original_match_all315_words=True,
            every_relocation_offset_and_symbol_preserved=True)

    def test_02_independent_rebased_original_links_and_hi_lo_carries(self):
        for index, entry in enumerate((0x15207FF0, 0x15218008, 0x15328000)):
            symbols = {name: value + (index + 1) * 0x10000 + (0x1234 if name.startswith('func_') else 0)
                for name, value in source.SYMBOLS.items()}
            symbols.update(D_800A8DC0=(0x90007FFC, 0x90018004, 0x90028000)[index],
                D_800A8DC4=(0x91008004, 0x91027FFC, 0x91038008)[index])
            original, _ = self.link(self.original, 'original-carry%d' % index, entry, symbols)
            for name, obj in self.padded.items():
                words, _ = self.link(obj, name + '-carry%d' % index, entry, symbols)
                self.assertEqual(words, original)
        self.receipt('links', independent_entries=3, both_data_symbols_carry_independently=True,
            all_JAL_targets_and_internal_branch_distances_match_original=True)

    def test_03_each_guard_and_relocation_expectation_has_effective_controls(self):
        for index, row in enumerate(self.rows):
            for field, bad in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_26:wrong_symbol')):
                rows = [dict(value) for value in self.rows]
                rows[index][field] = bad
                changed = self.out / 'corrupt-guards.csv'
                self.write_rows(changed, rows)
                for emit in (
                        lambda: emit_padded_assembly(self.object, self.asm, word_patches_path=changed,
                            filename='generated_1D43B0'),
                        lambda: pad_c_object.emit_padded_assembly(self.object, self.layout,
                            'generated_1D43B0', word_patches_path=changed)):
                    with self.assertRaisesRegex(ValueError, 'stale word patch|stale relocations'):
                        emit()
        self.receipt('guard-controls', guards=len(self.rows), fired_rejections=len(self.rows) * 4,
            no_unguarded_retail_transplant=True)

    def test_04_complete_owner_neighbors_pools_and_existing_guard_history(self):
        before = (self.out / 'before-owner').read_text()
        after = source.recovered_owner(before)
        (self.out / 'qualified-owner.c').write_text(after)
        old_obj, old_warnings = compile_owner(self.root, self.out, before, 'owner-before')
        new_obj, new_warnings = compile_owner(self.root, self.out, after, 'owner-after')
        self.assertEqual([warning[0] for warning in new_warnings],
            [warning[0] for warning in old_warnings])
        old_text, old_functions, old_relocations = parse_object(old_obj)
        new_text, new_functions, new_relocations = parse_object(new_obj)
        self.assertEqual(set(old_functions), set(new_functions))
        for name, old in old_functions.items():
            if name == source.FUNCTION:
                continue
            new = new_functions[name]
            self.assertEqual(new['size'], old['size'], name)
            self.assertEqual(old_text[old['value']:old['value'] + old['size']],
                new_text[new['value']:new['value'] + new['size']], name)
            normalize = lambda table, f: {at - f['value']: value for at, value in table.items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(normalize(old_relocations, old), normalize(new_relocations, new), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(new_obj))
        target = new_functions[source.FUNCTION]
        self.assertEqual(new_text[target['value']:target['value'] + target['size']],
            struct.pack('>313I', *self.object_words))
        guards = self.out / 'owner-guards.csv'
        current = (self.out / 'before-guards').read_text()
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=self.fields, lineterminator='\n')
        writer.writerows(self.rows)
        guards.write_text(current + stream.getvalue())
        assemblies = (
            emit_padded_assembly(new_obj, self.out / 'before-assembly',
                word_patches_path=guards, filename='generated_1D43B0'),
            pad_c_object.emit_padded_assembly(new_obj, self.out / 'before-layout',
                'generated_1D43B0', word_patches_path=guards))
        for index, assembly in enumerate(assemblies):
            obj = self.assemble('owner-padded%d' % index, assembly)
            text, functions, _ = parse_object(obj)
            target = functions[source.FUNCTION]
            self.assertEqual(text[target['value']:target['value'] + target['size']],
                parse_object(self.padded['generated'])[0][:1260])
        self.receipt('owner', unchanged_neighbors=len(old_functions) - 1,
            raw_target_same_as_isolated_C=True, both_complete_owner_padders_qualified=True,
            existing_pools_and_relative_relocations_and_guard_rows_fixed=True)

    def test_05_guarded_guest_return_states_and_complete_instruction_coverage(self):
        import itertools
        coverage, cases = set(), 0
        for kind, count, phase, outcome, mutation in itertools.product((0, 1, 2, 3, 4, 255, 0x100, 0x103),
                (0, 1, 3), (0, 8), range(3), (0, 1)):
            memory = recovery.fixture(count, seed=1)
            expected = recovery.Reference(memory, kind, outcome=outcome, mutation=mutation).run()
            models = [MatchOracle(body, dict(memory), kind, phase=phase, outcome=outcome,
                mutation=mutation, memcpy_words=self.memcpy).run() for body in (self.retail, self.words)]
            for model in models:
                self.assertEqual(model.records, expected)
            self.assertTrue(producer.complete_state(models[0]) == producer.complete_state(models[1]))
            coverage.update(models[1].visits)
            cases += 1
        for at in (0x1A, 0x1E):
            memory = recovery.fixture()
            recovery.put(memory, recovery.PARAMS + at, 65535, 2)
            model = MatchOracle(self.words, memory, memcpy_words=self.memcpy)
            with self.assertRaises(recovery.GuestBreak):
                model.run()
            coverage.update(model.visits)
        target = set(range(source.ENTRY, source.ENTRY + 1260, 4))
        self.assertEqual(coverage & target, target)
        self.receipt('guarded-guest', domains=cases, reached_words=len(coverage & target),
            all315_reached_with_actual_break_paths_and_restored_idle_slots=True,
            independent_reference_and_complete_modeled_states_agree=True)

    def test_06_public_and_private_input_alias_prefixes(self):
        import itertools
        cases = 0
        for phase, kind, mutation in itertools.product((0, 8), (0, 1, 2, 3, 4, 255), (0, 1)):
            frame = recovery.STACK + phase - 0x168
            for pointer in (recovery.PARAMS, recovery.CREATED + 0x170, 0x800A8DC0 - 4,
                    frame + 0xD0, frame + 0xD4, frame + 0xE8, frame + 0x8C):
                with patch.object(recovery, 'PARAMS', pointer):
                    memory = recovery.fixture(1, seed=1)
                    models = [MatchOracle(body, dict(memory), kind, phase=phase, outcome=2,
                        mutation=mutation, limit=0, memcpy_words=self.memcpy)
                        for body in (self.retail, self.words)]
                    for model in models:
                        with self.assertRaises(recovery.FactoryBoundary):
                            model.run()
                    self.assertTrue(producer.complete_state(models[0]) == producer.complete_state(models[1]))
                    self.assertEqual(models[0].records, models[1].records)
                    self.assertEqual(models[0].current_pc, models[1].current_pc)
                cases += 1
        self.receipt('aliases', first_factory_prefix_pairs=cases,
            source_created_global_and_four_private_input_aliases=True,
            actual_prefix_boundary_fired=True, private_aliases_are_guest_only=True)

    def test_07_fired_root_access_fault_states_pc_and_delay_boundaries(self):
        import itertools
        cuts, slot_witnesses = 0, set()
        for kind, phase, outcome in itertools.product((0, 1, 2, 3, 4, 255), (0, 8), range(3)):
            memory = recovery.fixture(1, seed=1)
            complete = MatchOracle(self.retail, dict(memory), kind, phase=phase,
                outcome=outcome, memcpy_words=self.memcpy).run()
            for cut in range(complete.accesses):
                models = [MatchOracle(body, dict(memory), kind, phase=phase, outcome=outcome,
                    fault=cut, memcpy_words=self.memcpy) for body in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AccessBoundary):
                        model.run()
                self.assertEqual((models[0].current_pc, models[0].delay_of),
                    (models[1].current_pc, models[1].delay_of))
                self.assertTrue(producer.complete_state(models[0]) == producer.complete_state(models[1]))
                self.assertEqual(models[0].records, models[1].records)
                if models[0].current_pc in (0x151A71C0, 0x151A7208):
                    raw = MatchOracle(self.raw, dict(memory), kind, phase=phase,
                        outcome=outcome, fault=cut, memcpy_words=self.memcpy)
                    with self.assertRaises(AccessBoundary):
                        raw.run()
                    self.assertNotEqual((raw.current_pc, raw.delay_of),
                        (models[0].current_pc, models[0].delay_of))
                    slot_witnesses.add(kind)
                cuts += 1
        self.assertEqual(slot_witnesses, {0, 1})
        self.receipt('access-cuts', fired_root_pairs=cuts, domains=36,
            PC_and_modeled_branch_delay_and_all_prefix_states_agree=True,
            both_raw_velocity_store_controls_have_wrong_fault_PC_or_BD=True,
            connected_memcpy_accesses_excluded=True, not_a_hardware_EPC_or_FCSR_claim=True)

    def test_08_unchanged_producer_and_real_dispatcher_table0_use_guarded_provider(self):
        import itertools
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        _, caller = producer.source.compile_candidate(self.root, self.out, 'producer')
        self.assertEqual(caller, list(struct.unpack_from('>67I', rom, producer.source.ROM)))
        parent = list(struct.unpack_from('>38I', rom, producer.PARENT_ROM))
        self.assertEqual(struct.unpack_from('>I', rom, 0x22ABD0)[0], producer.source.ENTRY)
        cases = 0
        for phase, outcome, parent_call, missing in itertools.product((0, 8), range(3), (False, True), (False, True)):
            memory = producer.fixture()
            actual_phase = phase - (0x18 if parent_call else 0)
            packet = producer.STACK + actual_phase - 0x5C
            if missing:
                for hole in producer.HOLES:
                    del memory[packet + hole]
            if parent_call:
                for index in range(3):
                    recovery.put(memory, producer.ACTOR + 0x2C + index * 4, recovery.bits(float(index + 1)))
            models = []
            for provider in (self.retail, self.words):
                connected = dict(zip(range(source.ENTRY, source.ENTRY + 1260, 4), provider))
                connected.update(zip(range(producer.MEMCPY, producer.MEMCPY + 44, 4), self.memcpy))
                if parent_call:
                    connected.update(zip(range(producer.source.ENTRY, producer.source.ENTRY + 268, 4), caller))
                model = producer.BurstOracle(parent if parent_call else caller, dict(memory), phase=phase,
                    entry=producer.PARENT if parent_call else producer.source.ENTRY, connected=connected,
                    arguments=(producer.ACTOR, 0, 0x8765ABCD) if parent_call else None, outcome=outcome).run()
                self.assertEqual((model.factory_count, model.integer_count, model.random_count), (3, 6, 18))
                self.assertEqual(model.calls[0][1], (packet, 1, 255, 1))
                self.assertFalse(any(address <= packet + hole < address + size
                    for address, size, _ in model.reads for hole in producer.HOLES))
                models.append(model)
            self.assertTrue(producer.complete_state(models[0]) == producer.complete_state(models[1]))
            cases += 1
        self.receipt('producer', actual_dispatcher_and_table0_cases=cases,
            unchanged67_word_producer_calls_actual_guarded315_word_object=True,
            all14_input_holes_can_be_unmapped_in_mode1=True,
            native_provider_systems_and_full_gameplay_not_claimed=True)

    def test_09_whole_image_source_guard_history_and_protected_data(self):
        before_source = (self.out / 'before-owner').read_text()
        current_source = (self.root / source.SOURCE).read_text()
        from tools.experiments import game_actor_burst_contact_candidates as contact
        installed_source = source.recovered_owner(before_source)
        contact_source = contact.recovered_owner(installed_source)
        from tools.experiments import game_actor_effect_packet_candidates as effect
        effect_source = effect.recovered_owner(contact_source)
        from tools.experiments import game_actor_threshold_flags_candidates as threshold
        threshold_source = threshold.recovered_owner(effect_source)
        installed = current_source in (installed_source, contact_source, effect_source, threshold_source)
        self.assertIn(current_source, (before_source, installed_source, contact_source, effect_source, threshold_source))
        before = (self.out / 'before-elf').read_bytes()
        expected = expected_consumer_image(before, self.retail) if installed else before
        if current_source in (contact_source, effect_source, threshold_source):
            from tools.tests.test_game_actor_burst_contact_match import expected_contact_image
            rom = (self.root / 'conker/conker.us.bin').read_bytes()
            expected = expected_contact_image(expected, struct.unpack_from('>117I', rom, contact.ROM))
        if current_source in (effect_source, threshold_source):
            from tools.tests.test_game_actor_effect_packet_match import expected_effect_image
            expected = expected_effect_image(expected, struct.unpack_from('>108I', rom, effect.ROM))
        if current_source == threshold_source:
            from tools.tests.test_game_actor_threshold_flags_match import expected_threshold_image
            expected = expected_threshold_image(expected, struct.unpack_from('>47I', rom, threshold.ROM))
        current = donor_checkpoint.previous_input((self.root / self.paths['elf']).read_bytes(), self.paths['elf'], self.root)
        self.assertTrue(current == expected, 'Whole ELF differs from the declared consumer slot/size changes')
        self.assertEqual(canonical_symbols(current), canonical_symbols(expected))
        guards = (self.root / self.paths['guards']).read_text()
        guard_bytes = (self.root / self.paths['guards']).read_bytes()
        # Keep independently corrupted text visible to the old text control.
        if guards == guard_bytes.decode().replace('\r\n', '\n'):
            guards = donor_checkpoint.previous_input(guard_bytes, self.paths['guards'], self.root).decode().replace('\r\n', '\n')
        prior = (self.out / 'before-guards').read_text()
        stream = io.StringIO(newline='')
        csv.DictWriter(stream, fieldnames=self.fields, lineterminator='\n').writerows(self.rows)
        expected_text = prior + stream.getvalue() if installed else prior
        prior_bytes = (self.out / 'before-guards').read_bytes()
        expected_bytes = prior_bytes + stream.getvalue().encode('ascii') if installed else prior_bytes
        if current_source in (effect_source, threshold_source):
            from tools.tests.test_game_actor_effect_packet_match import installed_guards
            expected_text += installed_guards(b'').decode('ascii')
            expected_bytes = installed_guards(expected_bytes)
        if current_source == threshold_source:
            from tools.tests.test_game_actor_threshold_flags_match import installed_guards as threshold_guards
            expected_text += threshold_guards(b'').decode('ascii')
            expected_bytes = threshold_guards(expected_bytes)
        self.assertEqual(guards, expected_text)
        self.assertEqual(donor_checkpoint.previous_input((self.root / self.paths['guards']).read_bytes(), self.paths['guards'], self.root), expected_bytes)
        for name in set(self.paths) - {'owner', 'elf', 'guards'}:
            expected_input = (self.out / ('before-' + name)).read_bytes()
            if name == 'progress':
                from tools.experiments.game_byte_exact_donor_candidates import expected_donor_progress
                expected_input = expected_donor_progress(expected_input, self.root)
            self.assertEqual(donor_checkpoint.previous_input((self.root / self.paths[name]).read_bytes(), self.paths[name], self.root), expected_input, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(data['exact'], data)
        self.receipt('linked-image', installed=installed,
            changed_bytes=sum(a != b for a, b in zip(before, current)), protected_data=data,
            every_undeclared_ELF_byte_and_all_other_source_history_inputs_fixed=True)

    def test_10_effective_whole_image_source_and_guard_corruptions(self):
        read_bytes, read_text = Path.read_bytes, Path.read_text
        elf = self.root / self.paths['elf']
        data = elf.read_bytes()
        for address, size in ((source.ENTRY, 1260), (producer.source.ENTRY, 268)):
            bad = bytearray(data)
            bad[image.elf_slot_offset(data, address, size) + 4] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, v=bytes(bad): v if p == elf else read_bytes(p)):
                with self.assertRaises(AssertionError):
                    self.test_09_whole_image_source_guard_history_and_protected_data()
        owner = self.root / source.SOURCE
        text = owner.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: text + '\n' if p == owner else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_09_whole_image_source_guard_history_and_protected_data()
        guards = self.root / self.paths['guards']
        text = guards.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: text + '\n' if p == guards else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_09_whole_image_source_guard_history_and_protected_data()
        self.receipt('image-controls', target_and_prior_caller_ELF_corruptions=True,
            source_and_guard_changes_rejected=True, no_broad_metadata_exclusions=True)

    def test_11_exact_serialization_accounting_and_effective_metadata_controls(self):
        before = (self.out / 'before-elf').read_bytes()
        path = self.root / self.paths['elf']
        current = donor_checkpoint.previous_input(path.read_bytes(), self.paths['elf'], self.root)
        installed = source.SELECTED in (self.root / source.SOURCE).read_text()
        names = {name for group, _, _ in SERIALIZATION for name in group}
        rows = {name: (at, fields, string) for at, name, fields, string in symbol_rows(current) if name in names}
        old = {name: (at, fields, string) for at, name, fields, string in symbol_rows(before) if name in names}
        record_changes = string_changes = 0
        for group, _, _ in SERIALIZATION:
            record = old[group[0]][0]
            count = len(group) * producer.SYMBOL.size
            record_changes += sum(a != b for a, b in zip(before[record:record + count], current[record:record + count]))
            string = old[group[0]][2]
            count = sum(len(name) + 1 for name in group)
            string_changes += sum(a != b for a, b in zip(before[string:string + count], current[string:string + count]))
        self.assertEqual(record_changes + string_changes, 58 if installed else 0)
        rb = Path.read_bytes
        for name, (at, fields, string) in rows.items():
            for offset in (at, string):
                bad = bytearray(current)
                bad[offset] ^= 1
                with patch.object(Path, 'read_bytes', lambda p, v=bytes(bad): v if p == path else rb(p)):
                    with self.assertRaises(AssertionError):
                        self.test_09_whole_image_source_guard_history_and_protected_data()
        bad = bytearray(before)
        bad[old['D_800A8DC0'][0] + 4] ^= 1
        with self.assertRaises(AssertionError):
            expected_consumer_image(bytes(bad), self.retail)
        offset = image.elf_slot_offset(before, source.ENTRY, 1260)
        code_changes = sum(a != b for a, b in zip(before[offset:offset + 1260], current[offset:offset + 1260]))
        self.receipt('serialization', installed=installed, exact_adjacent_groups=2,
            record_bytes=record_changes, string_bytes=string_changes, instruction_bytes=code_changes,
            all8_current_record_string_controls_and_bad_baseline_rejected=True,
            every_metadata_byte_accounted_without_exclusions=True)
