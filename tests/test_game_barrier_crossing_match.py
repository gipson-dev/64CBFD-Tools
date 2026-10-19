"""Crossing word provenance, literal private cuts, callers, rebases and image gates."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_barrier_crossing_home_fit as source
from tools.experiments import game_barrier_crossing_layout as layout
from tools.experiments import game_barrier_crossing_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_barrier_crossing_oracle as guest
from tools.tests import test_game_barrier_crossing_recovery as recovery
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.pad_generated_object import emit_padded_assembly


def state(model):
    return (model.r, model.f, model.lo, model.condition, model.memory, model.events,
        model.reads, model.stores, model.requested, model.visits, model.calls, model.accesses)


class MatchModel(guest.CrossingModel):
    def __init__(self, words, memory, case, phase=0, connected=None, entry=source.ENTRY):
        super().__init__(words, memory, case, phase)
        self.entry = entry
        self.code = {entry + i * 4: word for i, word in enumerate(words)}
        self.code.update(connected or {})

    def record_call(self, target):
        if target == source.ENTRY:
            self.caller_args.append((self.f[12], self.f[14], self.r[6], self.r[7],
                guest.read(self.memory, self.r[29] + 16, 4)))
            return
        super().record_call(target)


class CallerStop(Exception):
    pass


class StopCode(dict):
    def __init__(self, code, stop):
        super().__init__(code)
        self.stop, self.fired = stop, 0

    def __getitem__(self, address):
        if address == self.stop:
            self.fired += 1
            raise CallerStop()
        return super().__getitem__(address)


class BarrierCrossingMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.values = source.freeze(cls.root, cls.out)
        before = cls.values[source.SOURCE].decode()
        cls.initial, cls.selected = source.source.original_body(before), source.selected_body(before)
        cls.obj, cls.raw_words, cls.row = source.compile_candidate(cls.root, cls.out)
        cls.raw, cls.bindings = source.payload(cls.obj)
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.anchors = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
            for entries in cls.moved.values() for _, name in entries}
        cls.normalized_words = layout.relocate(cls.normalized, cls.moved, cls.anchors)
        cls.retail = list(struct.unpack_from('>207I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.words = {'raw': cls.raw_words, 'normalized': cls.normalized_words}
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'match-receipt.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_words_origins_bindings_opcodes_and_stale_controls(self):
        self.assertEqual(self.normalized_words, self.retail)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (207, 144, 63))
        self.assertFalse(self.row['diagnostics'])
        order = layout.origins()
        self.assertEqual(set(order) - {None}, set(range(207)) - {0x154 // 4})
        self.assertEqual(order.count(None), 1)
        old, new = struct.unpack('>207I', self.raw), struct.unpack('>207I', self.normalized)
        for dest, origin in enumerate(order):
            if origin is None:
                continue
            a, b = old[origin], new[dest]
            self.assertEqual(a >> 26, b >> 26)
            if a >> 26 == 17 and a >> 21 & 31 in (4, 16, 20):
                self.assertEqual((a >> 21 & 31, a & 63), (b >> 21 & 31, b & 63))
                if a >> 21 & 31 == 4:
                    self.assertEqual(a >> 16 & 31, b >> 16 & 31)
            if a >> 26 in (33, 35, 36, 43, 49, 53, 57, 61):
                self.assertEqual(a, b)
        controls = 0
        for at in range(0, 828, 4):
            bad = bytearray(self.raw)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                layout.normalize(bytes(bad), self.bindings)
            controls += 1
        for at in self.bindings:
            bad = deepcopy(self.bindings)
            bad[at] = [('R_MIPS_26', source.FUNCTION)]
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, bad)
            controls += 1
        self.assertEqual(self.bindings, self.moved)
        self.receipts.update(raw_binding_stale_controls=controls, retained_source_origins=206,
            omitted_signed_end_copy=1, derived_tangent_copy=1, all207_words_and5_bindings_exact=True,
            frame_and_scalar_homes_recovered_in_C=True, not_direct_compiler_identity=True)

    def test_02_public_reference_literal_private_memory_and_states(self):
        triples, covered = 0, set()
        for n, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            value, wanted, calls, _, _ = guest.reference(memory, case)
            for phase in (0, 8):
                models = [MatchModel(words, memory, case, phase).run()
                    for words in (self.retail, self.normalized_words, self.raw_words)]
                with self.subTest(case=n, phase=phase):
                    self.assertEqual(state(models[0]), state(models[1]))
                    for model in models:
                        self.assertTrue(guest.equivalent(model.f[0], value))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(model.calls, calls)
                    self.assertEqual(models[0].memory, models[2].memory)
                    self.assertEqual(models[0].reads, models[2].reads)
                    self.assertEqual(models[0].stores, models[2].stores)
                covered.update(models[0].visits)
                triples += 1
        self.assertEqual(len(covered), 198)
        self.receipts.update(public_triples=triples, fixtures=len(self.corpus), retail_words_visited=len(covered),
            unvisited_retail_offsets=['0x%X' % at for at in range(0, 828, 4) if source.ENTRY + at not in covered],
            raw_private_memory_and_access_traces_equal=True)

    def test_03_fired_literal_private_prefixes(self):
        cases = (guest.Case(), guest.Case(count=0), guest.Case(extra=1, count=4),
            guest.Case(extra=2, count=4), guest.Case(mutation=2), guest.Case(mutation=1),
            guest.Case(neighbors=(255,) * 5), guest.Case(first_type=2))
        cuts = 0
        for case in cases:
            memory = guest.fixture(case)
            for phase in (0, 8):
                complete = MatchModel(self.retail, memory, case, phase).run()
                for cut in range(complete.accesses):
                    pair = []
                    for words in (self.retail, self.normalized_words):
                        model = MatchModel(words, memory, case, phase)
                        model.fault = cut
                        with self.assertRaises(guest.core.AccessFault):
                            model.run()
                        self.assertEqual(model.accesses, cut)
                        pair.append(model)
                    self.assertEqual(state(pair[0]), state(pair[1]), (case, phase, cut))
                    cuts += 1
        self.receipts['fired_literal_private_cut_pairs'] = cuts

    def test_04_native32_and_semantic_negative_controls(self):
        recovery.BarrierCrossingRecoveryTests.test_native32_both_semantic_bodies_and_effective_negative_controls(self)

    def test_05_actual_height_helper(self):
        recovery.BarrierCrossingRecoveryTests.test_actual_height_helper_before_count_and_pointer_capture(self)

    def test_06_actual_returning_caller_prefix(self):
        entry, stop = 0x15085EC8, 0x15085EEC
        code = struct.unpack_from('>10I', self.values['conker/conker.us.bin'], 0xB3378)
        window = {entry + i * 4: word for i, word in enumerate(code)}
        runs = 0
        for case in (guest.Case(), guest.Case(count=0), guest.Case(extra=1, count=4),
                guest.Case(mutation=2), guest.Case(point=(0., 0., -10.))):
            for phase in (0, 8):
                pair = []
                expected = guest.reference(guest.fixture(case), case)[0]
                for words in (self.retail, self.normalized_words, self.raw_words):
                    model = MatchModel(words, guest.fixture(case), case, phase, window)
                    model.entry = entry
                    model.f[24], model.f[26], model.f[28] = map(guest.bits, case.point)
                    model.f[2], model.f[18] = map(guest.bits, case.delta)
                    model.f[16] = guest.bits(1.25)
                    saved = model.f[20:].copy()
                    model.code = StopCode(model.code, stop)
                    with self.assertRaises(CallerStop):
                        model.run()
                    self.assertEqual(model.code.fired, 1)
                    self.assertEqual(model.caller_args, [tuple(map(guest.bits, case.point + case.delta))])
                    self.assertEqual(model.r[29], guest.STACK + phase)
                    self.assertEqual(model.r[31], stop)
                    self.assertEqual(model.f[20:], saved)
                    self.assertTrue(guest.equivalent(model.f[0], expected))
                    pair.append(model)
                    runs += 1
                self.assertEqual(state(pair[0]), state(pair[1]))
        self.receipts.update(actual_returning_caller_runs=runs, caller_stop_fired=True,
            actual_prefix='15085EC8..15085EEC', not_full_caller_or_gameplay=True)

    def test_07_independent_GNU_rebases(self):
        asm = self.values['conker/asm/B3020.s'].decode()
        start = asm.index('glabel ' + source.FUNCTION + '\n')
        end = asm.index('endlabel ' + source.FUNCTION, start)
        prelude = (self.root / 'conker/include/asm_processor_prelude.inc').read_text()
        retail = self.out / 'GNU-retail.s'
        retail.write_text(prelude + '\n.text\n' + asm[start:end])
        normalized = self.out / 'GNU-normalized.s'
        lines = [prelude, '\n.text\n.globl ' + source.FUNCTION, source.FUNCTION + ':']
        for i, word in enumerate(struct.unpack('>207I', self.normalized)):
            lines.append('.word 0x%08X' % word)
            for kind, name in self.moved.get(i * 4, []):
                lines.append('.reloc .-4,%s,%s' % (kind, name))
        normalized.write_text('\n'.join(lines) + '\n')
        for path in (retail, normalized):
            subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                '-I', str(self.root / 'conker/include'), '-o', str(path.with_suffix('.o')), str(path)],
                check=True, capture_output=True)
        pairs = 0
        for n, (entry, delta) in enumerate(((source.ENTRY, 0), (0x1621FFF4, 0x115CAC), (0x18FFF000, 0x235CB0))):
            anchors = {name: address + delta for name, address in self.anchors.items()}
            images = []
            for obj in (retail.with_suffix('.o'), normalized.with_suffix('.o'), self.obj):
                script = self.out / (obj.stem + '-GNU-%d.ld' % n)
                elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in anchors.items()], '-o', str(elf), str(obj)],
                    check=True, capture_output=True)
                images.append(sections(elf)['.text'][1][:828])
            self.assertEqual(images[0], images[1])
            self.assertEqual(list(struct.unpack('>207I', images[1])), layout.relocate(self.normalized, self.moved, anchors))
            moved = {name: getattr(guest, name) + delta for name in ('NODES', 'COUNT', 'HEIGHT')}
            moved['BANKS'] = tuple(base + n * 0x40000 for base in guest.BANKS)
            moved['SEGMENTS'] = ((moved['NODES'], 4), (moved['COUNT'], 2), *((b, 4096) for b in moved['BANKS']))
            with patch.multiple(guest, **moved):
                for case in self.corpus[::13]:
                    memory = guest.fixture(case)
                    value, wanted, calls, _, _ = guest.reference(memory, case)
                    models = [MatchModel(list(struct.unpack('>207I', image)), memory, case, entry=entry).run()
                        for image in images]
                    self.assertEqual(state(models[0]), state(models[1]))
                    for model in models:
                        self.assertTrue(guest.equivalent(model.f[0], value))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(model.calls, calls)
                    pairs += 1
        self.receipts.update(independent_GNU_maps=3, GNU_rebased_triples=pairs,
            all5_bindings_checked_against_independent_retail_assembly=True)

    def test_08_completed_guest_frame_aliases_and_effective_home_negative(self):
        differences = 0
        for home in (0x42, 0x4C):
            case = guest.Case(count=1, band=0x5A if home == 0x42 else 0,
                point=(50., 0., -100.), delta=(0., 1000.))
            memory = guest.fixture(case)
            base = guest.STACK - 144 + home
            memory.update({base + i: memory[guest.BANKS[0] + i] for i in range(4096)})
            guest.put(memory, guest.NODES, base, 4)
            models = [MatchModel(words, memory, case).run() for words in (self.retail, self.normalized_words)]
            self.assertEqual(state(models[0]), state(models[1]))
            bad = [word + 8 if word >> 26 in (49, 57) and word >> 21 & 31 == 29 and
                word & 65535 == 0x50 else word for word in self.normalized_words]
            wrong = MatchModel(bad, memory, case).run()
            differences += int(wrong.f[0] != models[0].f[0])
        self.assertGreater(differences, 0)
        self.receipts.update(completed_guest_frame_alias_pairs=2, effective_old_minimum_home_negative=True,
            frame_aliases_are_not_portable_native_C=True)

    def test_09_padder_guards_history_and_strict_complete_image_controls(self):
        out = self.root / integration.BUILD
        self.assertTrue(json.loads((out / 'qualification.json').read_text())['all73_addresses_and_extents_fixed'])
        self.assertTrue(json.loads((out / 'make-shadow.json').read_text())['padded_code_and_metadata_equal'])
        self.assertTrue(json.loads((out / 'first-link.json').read_text())['exact_prediction'])
        before = self.values['conker/build/conker.us.elf']
        actual = (out / 'first-linked.elf').read_bytes()
        truth = self.values['conker/conker.us.bin'][source.ROM:source.ROM + 828]
        integration.check_image(before, actual, truth)
        slot = elf_slot_offset(before, source.ENTRY, 828)
        symbol = next(row[0] for row in symbol_rows(before) if row[1] == source.FUNCTION)
        for at in (slot, slot - 4, symbol + 8, len(actual) - 1):
            bad = bytearray(actual)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                integration.check_image(before, bytes(bad), truth)
        old = self.values['conker/retail_word_patches.us.csv']
        guards = (out / 'qualified-guards.csv').read_bytes()
        self.assertEqual(guards, layout.private_guards(old, self.raw, self.bindings))
        self.assertTrue(guards.startswith(old))
        reader = csv.DictReader(io.StringIO(guards.decode()))
        fields = reader.fieldnames
        rows = list(reader)
        target = [row for row in rows if row['filename'] == source.OWNER and row['function'] == source.FUNCTION]
        self.assertEqual(len(target), 207)
        for name, value in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_26:' + source.FUNCTION)):
            bad = deepcopy(rows)
            index = next(i for i, row in enumerate(bad) if row['filename'] == source.OWNER and row['function'] == source.FUNCTION)
            bad[index][name] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=fields)
            writer.writeheader()
            writer.writerows(bad)
            manifest = self.out / ('stale-' + name + '.csv')
            manifest.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                emit_padded_assembly(out / 'after-primary.o', self.root / 'conker/asm/B3020.s',
                    function_objects={name: out / 'after-normal.o' for name in integration.NORMAL_FUNCTIONS},
                    word_patches_path=manifest, filename=source.OWNER)
        self.receipts.update(strict_image_corruption_controls=4, actual_padder_stale_controls=2,
            historical_guard_prefix_preserved=True, guard_rows=207,
            identity_guards=sum(row['expected'] == row['replacement'] and row['expected_relocations'] ==
                row['replacement_relocations'] and row['omit'] == 'false' for row in target))

    def test_10_installed_production_image_and_scope(self):
        result = integration.audit(self.root, self.root / integration.BUILD)
        actual = (self.root / 'conker/build/conker.us.elf').read_bytes()
        at = elf_slot_offset(actual, source.ENTRY, 828)
        self.assertEqual(list(struct.unpack_from('>207I', actual, at)), self.retail)
        self.assertEqual(result['other_bodies_fixed'], 6056)
        self.receipts.update(installed_production_image_verified=True,
            all6056_other_bodies_and_all6057_addresses_fixed=True,
            complete_image_has_no_symbol_or_metadata_changes=True)


if __name__ == '__main__':
    unittest.main()
