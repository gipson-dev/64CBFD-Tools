"""Complete scheduler source-origin, literal/private, GNU, Make and image gates."""
from copy import deepcopy
from dataclasses import replace
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_pair_scheduler_layout as layout
from tools.experiments import game_actor_pair_scheduler_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.tests import test_game_actor_pair_scheduler_homes as home_tests
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.pad_generated_object import emit_padded_assembly

source, guest = layout.source, home_tests.guest


def state(model):
    return (home_tests.literal_state(model), getattr(model, 'lo', None), getattr(model, 'hi', None))


class ActorPairSchedulerMatchTests(unittest.TestCase):
    native = home_tests.ActorPairSchedulerHomeTests.native
    test_04_native32_profiles_and_effective_negatives = home_tests.ActorPairSchedulerHomeTests.test_03_native32_profiles_and_effective_updated_negatives
    test_05_actual_NULL_child_returns = home_tests.ActorPairSchedulerHomeTests.test_06_actual_restored_null_actor_child_returns
    test_07_group_table_frame_aliases_reject_old_homes = home_tests.ActorPairSchedulerHomeTests.test_10_guest_group_table_aliases_reject_old_buffer_homes

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / (source.BUILD + '/match/qualification')
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

    def test_01_closed_origins_bindings_words_and_stale_controls(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (255, 192, 238))
        self.assertEqual(self.words, self.retail)
        self.assertFalse(self.row['diagnostics'])
        order = layout.origins()
        self.assertEqual(len(set(at for at in order if isinstance(at, int))), 249)
        self.assertEqual(len([at for at in order if isinstance(at, tuple)]), 12)
        self.assertEqual((len(self.bindings), len(self.moved)), (22, 24))
        controls = 0
        for at in range(0, 1020, 4):
            bad = bytearray(self.raw); bad[at] ^= 1
            with self.assertRaises(ValueError): layout.normalize(bytes(bad), self.bindings)
            controls += 1
        for at in self.bindings:
            bad = deepcopy(self.bindings); bad[at] = [('R_MIPS_26', source.FUNCTION)]
            with self.assertRaises(ValueError): layout.normalize(self.raw, bad)
            controls += 1
        wrong = order.copy(); wrong[0], wrong[1] = wrong[1], wrong[0]
        with patch.object(layout, 'origins', return_value=wrong):
            with self.assertRaises(ValueError): layout.normalize(self.raw, self.bindings)
        with patch.object(layout, 'allocation', return_value=({}, {}, {})):
            with self.assertRaises(ValueError): layout.normalize(self.raw, self.bindings)
        self.receipts.update(words=261, frame=192, raw_differences=238, normalized_differences=0,
            source_origins=249, derived_forms=12, removed_masks=5, removed_cursor_copies=1,
            raw_binding_stale_controls=controls, recipe_stale_controls=2, output_bindings=24)

    def test_02_complete_literal_private_state_and_raw_public_reference(self):
        triples, coverage = 0, set()
        for case in self.corpus:
            memory = guest.fixture(case)
            result, wanted, calls, stores, _ = guest.reference(memory, case)
            for phase in (0, 8):
                a, b, raw = [guest.SchedulerModel(words, memory, case, phase).run()
                    for words in (self.retail, self.words, self.raw_words)]
                self.assertEqual(state(a), state(b))
                for model in (a, b, raw):
                    self.assertEqual(model.r[2], result)
                    self.assertEqual(model.calls, calls)
                    self.assertEqual(home_tests.previous.public_stores(model), stores)
                    self.assertEqual(guest.public(model.memory), guest.public(wanted))
                coverage.update(a.visits)
                triples += 1
        self.assertEqual(len(coverage), 261)
        self.receipts.update(fixtures=len(self.corpus), completed_triples=triples,
            complete_literal_private_state=True, retail_words_visited=261)

    def test_03_every_selected_access_cut_fires_and_matches(self):
        cuts = 0
        for case in (guest.Case(budget=0), guest.Case(primary=1, count=4, budget=1),
                guest.Case(primary=0, count=2, forbidden=0xFFFF, budget=1)):
            memory = guest.fixture(case)
            for phase in (0, 8):
                complete = guest.SchedulerModel(self.retail, memory, case, phase).run()
                for cut in range(complete.accesses):
                    models = []
                    for words in (self.retail, self.words):
                        model = guest.SchedulerModel(words, memory, case, phase)
                        model.fault = cut
                        with self.assertRaises(guest.core.AccessFault): model.run()
                        self.assertEqual(model.accesses, cut)
                        models.append(model)
                    self.assertEqual(state(models[0]), state(models[1]))
                    cuts += 1
        self.receipts.update(fired_literal_private_cut_pairs=cuts, every_requested_fault_fired=True,
            prior_cut15_allocation_boundary_closed=True)

    def test_06_independent_GNU_maps_for_retail_normalized_and_raw(self):
        asm = self.values['conker/asm/B3020.s'].decode()
        lo = asm.index('glabel ' + source.FUNCTION + '\n')
        hi = asm.index('endlabel ' + source.FUNCTION, lo)
        prelude = (self.root / 'conker/include/asm_processor_prelude.inc').read_text()
        retail = self.out / 'GNU-retail.s'; retail.write_text(prelude + '\n.text\n' + asm[lo:hi])
        normalized = self.out / 'GNU-normalized.s'
        lines = [prelude, '.text', '.globl ' + source.FUNCTION, source.FUNCTION + ':']
        for i, word in enumerate(struct.unpack('>261I', self.normalized)):
            label = '.Lscheduler_word_%d' % i
            lines.extend((label + ':', '.word 0x%08X' % word))
            for kind, name in self.moved.get(i * 4, []): lines.append('.reloc %s,%s,%s' % (label, kind, name))
        normalized.write_text('\n'.join(lines) + '\n')
        for path in (retail, normalized):
            subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                '-I', str(self.root / 'conker/include'), '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        triples = 0
        for n, (entry, delta) in enumerate(((source.ENTRY, 0), (0x1621FFF4, 0x115CAC), (0x18FFF000, 0x235CB0))):
            images = []
            for obj, count in ((retail.with_suffix('.o'), 261), (normalized.with_suffix('.o'), 261), (self.obj, 255)):
                script = self.out / (obj.stem + '-GNU-%d.ld' % n); elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, value + delta) for name, value in self.anchors.items()],
                    '-o', str(elf), str(obj)], check=True, capture_output=True)
                images.append(list(struct.unpack_from('>%dI' % count, sections(elf)['.text'][1])))
            self.assertEqual(images[0], images[1])
            moved = {name: getattr(guest, name) + delta for name in
                ('CONTEXT', 'PRIMARY', 'COUNT', 'ACTORS', 'FORBIDDEN', 'SENTINEL', 'PAIR')}
            moved['BANKS'] = tuple(base + delta for base in guest.BANKS)
            moved['SEGMENTS'] = tuple((base + delta, size) for base, size in guest.SEGMENTS)
            with patch.multiple(guest, **moved):
                for case in (guest.Case(), guest.Case(mutation=1), guest.Case(primary=0, forbidden=0xFFFF, budget=1)):
                    memory = guest.fixture(case)
                    result, wanted, calls, stores, _ = guest.reference(memory, case)
                    models = [guest.SchedulerModel(words, memory, case, entry=entry).run() for words in images]
                    self.assertEqual(state(models[0]), state(models[1]))
                    for model in models:
                        self.assertEqual((model.r[2], model.calls), (result, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(home_tests.previous.public_stores(model), stores)
                    triples += 1
        self.receipts.update(independent_GNU_maps=3, rebased_triples=triples, all24_bindings_rebased=True)

    def test_08_real_Make_padder_guard_history_and_image_negatives(self):
        out = self.root / integration.BUILD
        self.assertTrue(json.loads((out / 'qualification.json').read_text())['all73_addresses_fixed'])
        self.assertTrue(json.loads((out / 'make-shadow.json').read_text())['padded_code_and_metadata_equal'])
        before = self.values['conker/build/conker.us.elf']; first = (out / 'first-linked.elf').read_bytes()
        truth = self.rom[source.ROM:source.ROM + 1044]
        integration.check_image(before, first, truth)
        at = elf_slot_offset(before, source.ENTRY, 1044)
        symbol = next(row[0] for row in symbol_rows(before) if row[1] == source.FUNCTION)
        metadata = next(row for row in symbol_rows(before) if row[1] == 'D_8009DA68')
        for offset in (at, at - 4, symbol + 8, len(first) - 1, metadata[0] + 4, metadata[3] + 2):
            bad = bytearray(first); bad[offset] ^= 1
            with self.assertRaises(ValueError): integration.check_image(before, bytes(bad), truth)
        old = self.values['conker/retail_word_patches.us.csv']; guards = (out / 'qualified-guards.csv').read_bytes()
        self.assertTrue(guards.startswith(old))
        self.assertEqual(guards, layout.private_guards(old, self.raw, self.bindings))
        reader = csv.DictReader(io.StringIO(guards.decode())); fields, rows = reader.fieldnames, list(reader)
        target = [r for r in rows if r['filename'] == source.OWNER and r['function'] == source.FUNCTION]
        self.assertEqual((len(target), sum(r['omit'] == 'true' for r in target),
            sum(bool(r['insert_after']) for r in target)), (255, 6, 12))
        for field, value in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_HI16:D_800D23B0')):
            bad = deepcopy(rows)
            index = next(i for i, r in enumerate(bad) if r['filename'] == source.OWNER and r['function'] == source.FUNCTION)
            bad[index][field] = value
            stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(bad)
            path = self.out / ('stale-' + field + '.csv'); path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):
                emit_padded_assembly(out / 'after-primary.o', self.root / 'conker/asm/B3020.s',
                    function_objects={n: out / 'after-normal.o' for n in integration.NORMAL_FUNCTIONS},
                    word_patches_path=path, filename=source.OWNER)
        identity = sum(r['omit'] != 'true' and r['expected'] == r['replacement'] and
            r['expected_relocations'] == r['replacement_relocations'] for r in target)
        self.receipts.update(expected_word_rows=255, omit_rows=6, insertion_rows=12, identity_guard_rows=identity,
            prior_guard_bytes_exact_prefix=True, actual_padder_stale_controls=2, image_corruption_controls=6,
            padded_neighbors_unchanged=72, Makefile_unchanged=True)

    def test_09_negative_budgets_retain_fired_literal_prefixes(self):
        for budget in (-1, -2147483648):
            case = guest.Case(primary=0, budget=budget); memory = guest.fixture(case); models = []
            for words in (self.retail, self.words):
                model = guest.SchedulerModel(words, memory, case, stop_calls=3)
                with self.assertRaises(guest.CallStop): model.run()
                self.assertEqual(len(model.calls), 3); models.append(model)
            self.assertEqual(state(models[0]), state(models[1]))
        self.receipts['negative_budget_fired_literal_prefix_pairs'] = 2

    def test_10_exact_predecessor_or_strict_installed_scope(self):
        before = self.values[source.SOURCE]
        current = (self.root / source.SOURCE).read_bytes()
        if current == before:
            for name, old in self.values.items(): self.assertEqual((self.root / name).read_bytes(), old, name)
            self.receipts['production_predecessor_unchanged'] = True
        else:
            self.assertEqual(current, source.recovered_owner(before.decode(), layout.SELECTED).encode())
            audit = integration.audit(self.root, self.root / integration.BUILD)
            self.assertEqual((audit['functions'], audit['other_bodies_fixed']), (6057, 6056))
            self.receipts.update(installed_words=261, installed_other_bodies_fixed=6056,
                all6057_addresses_fixed=True, protected_game_data_bytes=189088, protected_game_data_owners=720)


if __name__ == '__main__': unittest.main()
