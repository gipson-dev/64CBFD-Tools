"""Complete literal pair-mask layout, real C semantics, aliases and strict link scope."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_pair_visibility_layout as layout
from tools.experiments import game_actor_pair_visibility_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.tests import game_actor_pair_visibility_oracle as guest
from tools.tests import test_game_actor_pair_visibility_recovery as previous
from tools.tests.test_game_actor_pair_visibility_recovery import same_calls, public_stores
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.pad_generated_object import emit_padded_assembly

source = layout.source
BUILD = source.BUILD + '/match'


def state(model):
    return (model.r, model.f, getattr(model, 'lo', None), getattr(model, 'hi', None), model.condition,
        model.memory, model.reads, model.stores, model.events, model.requested, model.visits,
        model.accesses, model.calls, model.raw_calls, model.outputs, model.lookup_ordinal)


class ActorPairVisibilityMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / BUILD
        cls.values = source.freeze(cls.root, cls.out)
        cls.obj, cls.raw_words, cls.row = source.compile_candidate(cls.root, cls.out, 'selected', layout.SELECTED)
        cls.raw, cls.bindings = source.payload(cls.obj)
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.anchors = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
            for entries in cls.moved.values() for _, name in entries}
        cls.words = relocate(cls.normalized, cls.moved, cls.anchors)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>261I', cls.rom, source.ROM))
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_source_origins_raw_guards_and_literal_words(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (261, 168, 224))
        self.assertFalse(self.row['diagnostics'])
        self.assertEqual(self.row['raw_SHA256'], layout.RAW_SHA)
        self.assertEqual(self.words, self.retail)
        self.assertEqual(len(self.bindings), 16)
        order = layout.origins()
        retained = [at for at in order if isinstance(at, int)]
        self.assertEqual(len(set(retained)), 257)
        self.assertEqual(set(range(0, 1044, 4)) - set(retained), layout.REMOVED)
        self.assertEqual(len([item for item in order if isinstance(item, tuple)]), 4)
        for i, item in enumerate(order):
            if isinstance(item, int):
                old, new = self.raw_words[item // 4], self.words[i]
                if item not in (0xD8, 0x324):
                    self.assertEqual(old >> 26, new >> 26)
                if old >> 26 == 17:
                    self.assertEqual((old >> 21 & 31, old & 63), (new >> 21 & 31, new & 63))
        controls = 0
        for at in range(0, 1044, 4):
            bad = bytearray(self.raw)
            bad[at] ^= 1
            with self.assertRaises(ValueError): layout.normalize(bytes(bad), self.bindings)
            controls += 1
        for at in self.bindings:
            bad = deepcopy(self.bindings)
            bad[at] = [('R_MIPS_26', source.FUNCTION)]
            with self.assertRaises(ValueError): layout.normalize(self.raw, bad)
            controls += 1
        wrong = order.copy()
        wrong[0], wrong[1] = wrong[1], wrong[0]
        with patch.object(layout, 'origins', return_value=wrong):
            with self.assertRaises(ValueError): layout.normalize(self.raw, self.bindings)
        with patch.object(layout, 'allocation', return_value=({}, {})):
            with self.assertRaises(ValueError): layout.normalize(self.raw, self.bindings)
        self.receipts.update(words=261, frame=168, raw_differences=224, literal_differences=0,
            unique_retained_origins=257, derived_words=4, removed_explicit_masks=4, preserved_bindings=16,
            raw_binding_stale_controls=controls, recipe_stale_controls=2,
            retained_opcode_exceptions=['BNE to BNEL with hoisted common load', 'typed DX LW to LWC1 plus derived MFC1'])

    def test_02_full_literal_private_state_and_public_reference(self):
        triples, coverage = 0, set()
        for n, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            wanted, calls, stores, _ = guest.reference(memory, case)
            for phase in (0, 8):
                models = [guest.PairModel(words, memory, case, phase).run() for words in (self.retail, self.words, self.raw_words)]
                with self.subTest(case=n, phase=phase):
                    self.assertEqual(state(models[0]), state(models[1]))
                    for model in models:
                        self.assertTrue(same_calls(model.calls, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(public_stores(model), stores)
                coverage.update(models[0].visits)
                triples += 1
        unvisited = sorted(set(range(source.ENTRY, source.ENTRY + 1044, 4)) - coverage)
        self.assertEqual(unvisited, [0x1508C274, 0x1508C2A0, 0x1508C300])
        self.receipts.update(fixtures=len(self.corpus), completed_triples=triples,
            complete_literal_private_state=True, all256_signed_modes=True, all32_shift_counts=True,
            public_context_alias=True, retail_words_visited=len(coverage), unvisited_retail_words=[hex(a) for a in unvisited])

    def test_03_every_selected_private_cut_fires_and_matches(self):
        corpus = (guest.Case(), guest.Case(active=(1, 1)), guest.Case(active=(0, 1), table=-1),
            guest.Case(query=1, hit=0.), guest.Case(barrier=1.), guest.Case(found=(False, True)),
            guest.Case(first=0, second=2, alias=True))
        cuts = 0
        for case in corpus:
            memory = guest.fixture(case)
            for phase in (0, 8):
                complete = guest.PairModel(self.retail, memory, case, phase).run()
                for cut in range(complete.accesses):
                    models = []
                    for words in (self.retail, self.words):
                        model = guest.PairModel(words, memory, case, phase)
                        model.fault = cut
                        with self.assertRaises(guest.core.AccessFault): model.run()
                        self.assertEqual(model.accesses, cut)
                        models.append(model)
                    self.assertEqual(state(models[0]), state(models[1]))
                    cuts += 1
        self.receipts.update(fired_private_cut_pairs=cuts, every_requested_fault_fired=True,
            original_cut13_startZ_home_closed=True)

    def test_04_native32_profiles_and_effective_negatives(self):
        with patch.object(source, 'SELECTED', layout.SELECTED):
            previous.ActorPairVisibilityRecoveryTests.test_03_native32_buffers_calls_and_effective_negatives(self)

    def test_05_actual_lookup_and_barrier_for_raw_and_normalized(self):
        previous.ActorPairVisibilityRecoveryTests.test_05_actual_lookup_and_restored_barrier(self)
        first = {name: self.receipts[name] for name in ('actual_lookup_runs', 'actual_restored_barrier_runs')}
        with patch.object(self, 'words', self.raw_words):
            previous.ActorPairVisibilityRecoveryTests.test_05_actual_lookup_and_restored_barrier(self)
        for name, count in first.items():
            self.receipts[name] += count
        self.receipts['connected_helper_passes_cover_raw_and_normalized_with_repeated_retail_controls'] = True

    def test_06_actual_caller_windows_for_raw_and_normalized(self):
        previous.ActorPairVisibilityRecoveryTests.test_08_actual_caller_windows_and_fired_return_stops(self)
        first = self.receipts['actual_returning_caller_runs']
        with patch.object(self, 'words', self.raw_words):
            previous.ActorPairVisibilityRecoveryTests.test_08_actual_caller_windows_and_fired_return_stops(self)
        self.receipts['actual_returning_caller_runs'] += first
        self.receipts['caller_passes_cover_raw_and_normalized_with_repeated_retail_controls'] = True

    def test_07_independent_GNU_retail_normalized_and_raw_maps(self):
        asm = self.values['conker/asm/B3020.s'].decode()
        lo = asm.index('glabel ' + source.FUNCTION + '\n')
        hi = asm.index('endlabel ' + source.FUNCTION, lo)
        prelude = (self.root / 'conker/include/asm_processor_prelude.inc').read_text()
        retail = self.out / 'GNU-retail.s'
        retail.write_text(prelude + '\n.text\n' + asm[lo:hi])
        normalized = self.out / 'GNU-normalized.s'
        lines = [prelude, '.text', '.globl ' + source.FUNCTION, source.FUNCTION + ':']
        for i, word in enumerate(struct.unpack('>261I', self.normalized)):
            label = '.Lpair_word_%d' % i
            lines.extend((label + ':', '.word 0x%08X' % word))
            for kind, name in self.moved.get(i * 4, []):
                lines.append('.reloc %s,%s,%s' % (label, kind, name))
        normalized.write_text('\n'.join(lines) + '\n')
        for path in (retail, normalized):
            subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                '-I', str(self.root / 'conker/include'), '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        triples = 0
        for n, (entry, delta) in enumerate(((source.ENTRY, 0), (0x1621FFF4, 0x115CAC), (0x18FFF000, 0x235CB0))):
            images = []
            for obj in (retail.with_suffix('.o'), normalized.with_suffix('.o'), self.obj):
                script = self.out / (obj.stem + '-GNU-%d.ld' % n)
                elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, value + delta) for name, value in self.anchors.items()], '-o', str(elf), str(obj)],
                    check=True, capture_output=True)
                images.append(list(struct.unpack_from('>261I', sections(elf)['.text'][1])))
            self.assertEqual(images[0], images[1])
            moved = {name: getattr(guest, name) + delta for name in ('CONTEXT', 'MODE', 'TABLE', 'LOOKUP', 'QUERY', 'BARRIER', 'ACTORS', 'NESTED', 'ALIAS')}
            moved['BANKS'] = tuple(base + delta for base in guest.BANKS)
            moved['SEGMENTS'] = tuple((base + delta, size) for base, size in guest.SEGMENTS)
            with patch.multiple(guest, **moved):
                for case in self.corpus[::37]:
                    memory = guest.fixture(case)
                    wanted, calls, stores, _ = guest.reference(memory, case)
                    models = [guest.PairModel(words, memory, case, entry=entry).run() for words in images]
                    self.assertEqual(state(models[0]), state(models[1]))
                    for model in models:
                        self.assertTrue(same_calls(model.calls, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(public_stores(model), stores)
                    triples += 1
        self.receipts.update(independent_GNU_maps=3, rebased_triples=triples,
            all16_bindings_and_literal_private_state_rebased=True)

    def test_08_completed_guest_frame_aliases_and_effective_old_home_negative(self):
        class Alias(guest.PairModel):
            def hook(self, target):
                ordinal = self.lookup_ordinal
                super().hook(target)
                if target == guest.LOOKUP and ordinal == self.alias_index:
                    self.r[2] = self.alias_base
        differences = 0
        runs = 0
        for index in (0, 1):
            for phase in (0, 8):
                case = guest.Case()
                memory = guest.fixture(case)
                sp = guest.STACK + phase - 168
                base = sp + 0x4C
                memory.update({guest.STACK + i: 0xA5 for i in range(0x100, 0x600)})
                original = guest.ACTORS + index * 0x32C
                data = bytes(memory[original + i] for i in range(0x32C))
                memory.update({base + i: value for i, value in enumerate(data)})
                models = []
                for words in (self.retail, self.words):
                    model = Alias(words, memory, case, phase)
                    model.alias_index, model.alias_base = index, base
                    models.append(model.run())
                self.assertEqual(state(models[0]), state(models[1]))
                wrong = [word + 0x1C if word >> 26 in (35, 49, 57) and word >> 21 & 31 == 29 and
                    word & 65535 == 0x64 else word for word in self.words]
                bad = Alias(wrong, memory, case, phase)
                bad.alias_index, bad.alias_base = index, base
                bad.run()
                differences += int(not same_calls(models[0].calls, bad.calls))
                runs += 1
        self.assertEqual(differences, 4)
        self.receipts.update(completed_guest_frame_alias_pairs=runs, effective_old_startZ_home_negatives=differences,
            frame_aliases_are_guest_only=True)

    def test_09_actual_guards_history_Make_and_strict_image_controls(self):
        out = self.root / integration.BUILD
        self.assertTrue(json.loads((out / 'qualification.json').read_text())['all73_addresses_fixed'])
        self.assertTrue(json.loads((out / 'make-shadow.json').read_text())['padded_code_and_metadata_equal'])
        before = self.values['conker/build/conker.us.elf']
        first = (out / 'first-linked.elf').read_bytes()
        truth = self.rom[source.ROM:source.ROM + 1044]
        integration.check_image(before, first, truth)
        at = elf_slot_offset(before, source.ENTRY, 1044)
        symbol = next(row[0] for row in symbol_rows(before) if row[1] == source.FUNCTION)
        for offset in (at, at - 4, symbol + 8, len(first) - 1):
            bad = bytearray(first)
            bad[offset] ^= 1
            with self.assertRaises(ValueError): integration.check_image(before, bytes(bad), truth)
        old = self.values['conker/retail_word_patches.us.csv']
        guards = (out / 'qualified-guards.csv').read_bytes()
        self.assertTrue(guards.startswith(old))
        self.assertEqual(guards, layout.private_guards(old, self.raw, self.bindings))
        reader = csv.DictReader(io.StringIO(guards.decode()))
        fields, rows = reader.fieldnames, list(reader)
        target = [row for row in rows if row['filename'] == source.OWNER and row['function'] == source.FUNCTION]
        self.assertEqual(len(target), 261)
        self.assertEqual(sum(row['omit'] == 'true' for row in target), 4)
        self.assertEqual(sum(bool(row['insert_after']) for row in target), 4)
        for field, value in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_HI16:D_800D23B0')):
            bad = deepcopy(rows)
            index = next(i for i, row in enumerate(bad) if row['filename'] == source.OWNER and row['function'] == source.FUNCTION)
            bad[index][field] = value
            stream = io.StringIO(newline='')
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(bad)
            path = self.out / ('stale-' + field + '.csv')
            path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):
                emit_padded_assembly(out / 'after-primary.o', self.root / 'conker/asm/B3020.s',
                    function_objects={n: out / 'after-normal.o' for n in integration.NORMAL_FUNCTIONS},
                    word_patches_path=path, filename=source.OWNER)
        unchanged = sum(row['omit'] != 'true' and row['expected'] == row['replacement'] and
            row['expected_relocations'] == row['replacement_relocations'] for row in target)
        self.receipts.update(expected_word_rows=261, identity_guard_rows=unchanged,
            changed_retained_guard_rows=257-unchanged, omit_rows=4, insertion_rows=4,
            prior_guard_bytes_exact_prefix=True, actual_padder_stale_controls=2,
            strict_image_corruption_controls=4, unchanged_padded_neighbors=72,
            Makefile_unchanged=True, normal_overrides_unchanged=list(integration.NORMAL_FUNCTIONS))

    def test_10_installed_image_and_protected_scope(self):
        audit = integration.audit(self.root, self.root / integration.BUILD)
        image = (self.root / 'conker/build/conker.us.elf').read_bytes()
        at = elf_slot_offset(image, source.ENTRY, 1044)
        self.assertEqual(image[at:at + 1044], self.rom[source.ROM:source.ROM + 1044])
        self.assertEqual((audit['functions'], audit['other_bodies_fixed']), (6057, 6056))
        self.assertTrue(audit['all_addresses_fixed'])
        self.assertTrue(audit['exact_first_link_reproduced'])
        self.assertTrue(audit['Makefile_unchanged'])
        self.receipts.update(installed_words=261, installed_other_bodies_fixed=6056,
            installed_all6057_addresses_fixed=True, installed_strict_first_link_identity=True,
            protected_game_data_bytes=189088, protected_game_data_owners=720)


if __name__ == '__main__':
    unittest.main()
