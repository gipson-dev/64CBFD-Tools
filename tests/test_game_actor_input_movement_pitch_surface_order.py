"""Qualify complete movement surface ordering against actual retail execution."""
import copy
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_pitch_surface_order as recovery
from tools.tests import test_game_actor_input_movement_release_addressing as prior

source, model, original = recovery.source, prior.model, prior.original


class SurfaceStop(Exception):
    pass


class SurfaceOracle(model.Oracle):
    def execute(self, word):
        if self.current_pc == 0x150F423C:
            raise SurfaceStop
        return super().execute(word)


class MovementPitchSurfaceOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = recovery.qualify(cls.root, cls.out)
        cls.body = recovery.selected_body()
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.bindings = source.parts(cls.obj)[1]
        cls.base28, _ = recovery.previous.previous.normalize(cls.raw_words, cls.truth, cls.bindings)
        cls.harness = original.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.obj = cls.padded
        cls.harness.coverage, cls.harness.providers = set(), set()
        compare = cls.harness.compare

        def three_way(spec, images=None, entry=source.ENTRY):
            return compare(spec, images or (cls.truth, cls.raw_words, cls.words), entry)

        cls.harness.compare = three_way

    def receipt(self, name, **data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_source_controls_extent_and_raw_gain(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences', 'normalized_differences')), (959, 128, 152, 121))
        self.assertEqual((self.row['normalized_exact_opening_words'], self.row['normalized_first_PC']), (478, 0x150F3C6C))
        self.assertEqual(self.words[:478], self.truth[:478])
        self.assertEqual(self.row['normalized_raw_sha'], 'f62f784fb4a8303fd99778f5e7254746f023f9c4980b229f3342b52782073625')
        self.assertEqual((self.row['research_guards'], self.row['new_research_guards'], self.row['production_guards_added'],
                          self.row['matching_credit'], self.row['installed']), (31, 0, 0, 0, False))
        self.assertEqual((self.out / 'expected-surface-guards.csv').read_bytes(),
                         (self.root / recovery.previous.BUILD / 'expected-release-guards.csv').read_bytes())
        self.assertEqual(source.parts(self.obj)[1], source.parts(self.padded)[1])
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body), name)
            raw, _ = source.parts(self.out / (name + '.o'))
            audit = json.loads((self.out / (name + '-audit.json')).read_text())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), audit['raw_sha'])
            words = list(struct.unpack_from('>%dI' % (len(raw) // 4), source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual((len(words), (-words[0]) & 65535, sum(a != b for a, b in zip(words, self.truth))),
                             tuple(audit[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual(audit['raw_neighbors'], 11)
            if len(words) > 959:
                self.assertTrue(audit['padder_rejected'])
            else:
                self.assertEqual(audit['padded_neighbors'], 11)
            rows.append(dict(name=name, words=len(words), differences=audit['differences']))
        self.assertEqual((len(rows), sum(r['words'] > 959 for r in rows), sum(r['words'] < 959 for r in rows)), (31, 2, 1))
        old = list(struct.unpack_from('>959I', source.projection.sections(
            self.root / recovery.previous.BUILD / 'copy-after-heldBy-linked.elf')['.text'][1]))
        changed = [i for i, (a, b) in enumerate(zip(old, self.raw_words)) if a != b]
        gained = [i for i in changed if self.raw_words[i] == self.truth[i]]
        lost = [i for i in changed if old[i] == self.truth[i]]
        self.assertEqual((len(changed), len(gained), len(lost)), (62, 48, 0))
        self.assertEqual(changed[0], 783)
        self.receipt('source-controls', complete_forms=31, overflow_rejections=2, shorter_controls=1,
                     raw_changed_words=len(changed), newly_exact=len(gained), formerly_exact_lost=len(lost), rows=rows,
                     research_table_byte_identical=True, new_research_or_production_rows=0)

    def test_02_existing_effective_heading_role_controls(self):
        with patch.dict(self.row, heading_proof=self.row['proof']['heading']):
            prior.MovementReleaseAddressingTests.test_02_effective_heading_role_deadout_entry_and_literal_controls(self)

    test_03_existing_non_call_heading_kernel = prior.MovementReleaseAddressingTests.test_03_non_call_kernel_poison_yaws_and_guest_aliases
    test_04_complete_public_FP_and_cap = prior.MovementReleaseAddressingTests.test_04_complete_public_FP_and_cap
    pair_at = prior.MovementReleaseAddressingTests.pair_at
    complete_prefixes = prior.MovementReleaseAddressingTests.complete_prefixes
    test_05_private_prefixes_and_existing_complete_paths = prior.MovementReleaseAddressingTests.test_05_extended_private_prefixes_and_complete_existing_paths

    def test_06_release_indices_speed_aliases_and_old_read_rejection(self):
        recovery.measure(self.root, self.out, 'copy-base', dict(recovery.previous.copy_forms())['copy-base'])
        prior.MovementReleaseAddressingTests.test_06_record_indices_speed_order_and_old_candidate_guest_rejection(self)

    test_07_signed_Y_alias_controls = prior.MovementReleaseAddressingTests.test_07_existing_signed_Y_alias_controls
    test_08_clamp_boundaries_and_compiled_wrong_limits = prior.MovementReleaseAddressingTests.test_08_existing_clamp_boundaries_and_wrong_limits
    test_09_native32_UBSan_rebases_and_aliases = prior.MovementReleaseAddressingTests.test_09_native32_UBSan_rebases_and_aliases

    def test_10_surface_branch_packets_FP_and_global_overlap(self):
        old = list(struct.unpack_from('>959I', source.projection.sections(self.out / 'surface-base-linked.elf')['.text'][1]))
        cases, overlaps, rejected, callbacks = 0, 0, 0, 0
        for alias, phase, pattern, held, buttons, below, saved in itertools.product(
                (False, True), (0, 8), (0, 1), (0, 101), (0, 0x4000), (0, 1), (-40., -0., 0., 30.)):
            actor = 0x800A19CC - 0xB8 if alias else model.ACTOR
            memory, case = model.fixture(self.rom, actor=actor, phase=phase, pattern=pattern,
                held=held, buttons=buttons, below=below, velocity=-20., depth=0., position=-5.)
            for off, value, size in ((0x13C, held, 1), (0x86, below, 1), (0x20, model.bits(-20.), 4),
                                     (0x28, model.bits(0.), 4), (0x3C, model.bits(30.), 4)):
                model.put(memory, actor + off, value, size)
            model.put(memory, 0x800CC284, model.INPUT)
            model.put(memory, 0x800A19CC, model.bits(13.25 if pattern else .125))
            model.put(memory, model.STACK + phase - 128 + 0x58, model.bits(1.))
            model.put(memory, model.STACK + phase - 128 + 0x68, model.bits(saved))
            machines = []
            for words in (self.truth, self.raw_words, self.words, old):
                machine = SurfaceOracle(words, memory, case, self.connected)
                machine.r[16], machine.r[29] = actor, model.STACK + phase - 128
                machine.f[16] = model.bits(0.)
                machine.entry = 0x150F40F4
                with self.assertRaises(SurfaceStop):
                    machine.run()
                self.assertEqual(machine.current_pc, 0x150F423C)
                machines.append(machine)
            expected = machines[0]
            for machine in machines[1:3]:
                self.assertEqual((machine.memory, machine.f, machine.calls, machine.observations, machine.fired),
                                 (expected.memory, expected.f, expected.calls, expected.observations, expected.fired))
            inactive = held == buttons == below == 0
            mismatch = machines[3].memory != expected.memory
            self.assertEqual(mismatch, alias and inactive)
            rejected += mismatch
            overlaps += alias
            callbacks += bool(expected.calls)
            cases += 1
        self.assertEqual((cases, overlaps, rejected, callbacks), (256, 128, 16, 224))
        self.receipt('surface-kernel', cases=cases, global_overlaps=overlaps, effective_old_late_global_read_rejections=rejected,
                     cases_with_callbacks=callbacks, actual_retail_not_high_level_model_is_oracle=True,
                     complete_RAM_FP_and_semantic_packets=True, partial_struct_global_overlap_guest_only=True,
                     arbitrary_private_GPR_FCSR_and_native_endianness_not_claimed=True)

    def test_11_owned_backend_layout_and_surface_sites(self):
        record, words, binary = recovery.previous.backend.finish_trace(self.root, self.out, recovery.SELECTED_NAME, self.body)
        self.assertEqual(words, self.raw_words)
        self.assertEqual(source.parts(self.out / 'traces' / recovery.SELECTED_NAME / 'baseline.o'), source.parts(self.obj))
        content = recovery.previous.backend.frame.isolated(self.body)
        layout = recovery.previous.check_layout(record, words, content)
        sites = ((0x150F4148, 0xC7A40068), (0x150F4154, 0x44819000), (0x150F4220, 0xA2000102),
                 (0x150F4224, 0x3C01800A), (0x150F4228, 0x46122182), (0x150F422C, 0xE6060020),
                 (0x150F4230, 0xC42A19CC), (0x150F4234, 0xE61000B8), (0x150F4238, 0xE60A0028))

        def check(current):
            if any(current[(pc - source.ENTRY) // 4] != word for pc, word in sites):
                raise ValueError('Changed movement surface emitted sites')

        check(words)
        controls = 0
        for pc, _ in sites:
            bad = list(words)
            bad[(pc - source.ENTRY) // 4] ^= 1
            with self.assertRaises(ValueError):
                check(bad)
            controls += 1
        for phase in ('frontend', 'optimizer'):
            bad = copy.deepcopy(record)
            next(r for r in bad['records'][phase] if r['name'] == 'def' and r['storage'] == 'M')['length'] += 4
            with self.assertRaises(ValueError):
                recovery.previous.check_layout(bad, words, content)
            controls += 1
        self.receipt('backend', newly_owned_capture=True, normal_and_observed_raw_identical=True,
                     source_sha=record['source_sha'], emitter_events=record['correlated_events'], AS1_instructions=len(binary),
                     layout=layout, new_surface_site_controls=9, total_effective_controls=controls,
                     new_research_guards=0, normalized_output_not_AS1_output=True)

    def test_12_existing_stale_guard_and_relocation_controls(self):
        rows = list(csv.DictReader(io.StringIO((self.out / 'expected-surface-guards.csv').read_text())))
        fields = list(rows[0])
        index = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION and int(row['offset'], 0) == 0x754)
        for n, (key, value) in enumerate((('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_32:wrong'))):
            bad = copy.deepcopy(rows)
            bad[index][key] = value
            text = io.StringIO(newline='')
            writer = csv.DictWriter(text, fieldnames=fields)
            writer.writeheader()
            writer.writerows(bad)
            table = self.out / ('negative-surface-guards-%d.csv' % n)
            table.write_text(text.getvalue())
            with self.assertRaises(ValueError):
                source.literal.padded_object(self.root, self.out, self.obj, 'negative-surface-guard-%d' % n, table)
        self.receipt('padder-controls', effective_actual_rejections=2)

    def test_13_production_predecessors_and_first_images_unchanged(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     immutable_first_image_members=10, installed=False, matching_credit=0, production_guards_added=0)


if __name__ == '__main__':
    unittest.main()
