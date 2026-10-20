"""Literal pickup-update origins, machine-state boundaries and original rebases."""

from pathlib import Path
from contextlib import ExitStack
import copy
import json
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_pickup_state_update_layout as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_pickup_state_update_lifetimes as previous
from tools.tests import game_pickup_state_update_oracle as guest


ROOT = Path(__file__).resolve().parents[2]


class AccessCut(Exception):
    pass


class CodeFetch(dict):
    def __init__(self, model):
        super().__init__(model.code)
        self.model = model

    def __getitem__(self, address):
        self.model.current_pc = address
        return super().__getitem__(address)


class CutOracle(guest.UpdateOracle):
    def __init__(self, *args, cut=None, **kwargs):
        self.armed, self.provider_active = False, False
        self.own, self.cut, self.fault = [], cut, None
        super().__init__(*args, **kwargs)
        self.code = CodeFetch(self)
        self.armed = True

    def access(self, kind, address, size):
        if self.armed and not self.provider_active:
            event = self.current_pc, kind, address, size
            if len(self.own) == self.cut:
                self.fault = event
                raise AccessCut()
            self.own.append(event)

    def get(self, address, size):
        self.access('R', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        self.access('W', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        self.provider_active = True
        try:
            super().record_call(target)
        finally:
            self.provider_active = False

    def hook(self, target):
        self.provider_active = True
        try:
            super().hook(target)
        finally:
            self.provider_active = False


def state(model):
    return (model.r, model.f, model.condition, model.lo, model.memory,
        model.reads, model.stores, model.events, model.calls, model.visits,
        model.own, model.fault, model.current_pc)


def representative_cases():
    return [
        guest.Case(),
        guest.Case(players=(guest.Player(current=9, override=20),)),
        guest.Case(players=(guest.Player(current=9, override=9),), selector=0, effects=(1, 42, 29)),
        guest.Case(items=(guest.Item(timer=1, flags=1, target=2),)),
        guest.Case(items=(guest.Item(timer=0, owner=1),)),
        guest.Case(players=(guest.Player(charge=4),), items=(guest.Item(timer=0, owner=1, kind=2222),)),
    ]


class PickupStateUpdateLayoutTests(previous.PickupStateUpdateLifetimeTests):
    @classmethod
    def setUpClass(cls):
        cls.outer = ExitStack()
        from tools.experiments import game_pickup_state_update_integration as integration
        cls.installed = cls.outer.enter_context(integration.fixture_context(ROOT))
        cls.outer.enter_context(patch.object(previous, 'ROOT', ROOT))
        cls.outer.enter_context(patch.object(source.prior, 'BUILD', source.BUILD))
        try:
            super().setUpClass()
            cls.raw, cls.bindings = source.payload(cls.obj)
            cls.raw_words = cls.words
            cls.words = source.apply_linked(cls.raw_words, cls.raw, cls.bindings)
            cls.normal = source.apply_linked(cls.normal, cls.raw, cls.bindings)
            cls.extra = {}
        except BaseException:
            cls.outer.close()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
            path = cls.output / 'test-receipt.json'
            row = json.loads(path.read_text())
            row.update(cls.extra, normalized_words=681, normalized_bindings=77,
                normalized_SHA256=source.NORMALIZED_SHA, experimental_byte_exact=True,
                installed=cls.installed, matching_credit=int(cls.installed))
            path.write_text(json.dumps(row, indent=2) + '\n')
            print('pickup literal qualification:', cls.extra)
        finally:
            cls.outer.close()

    def test_production_inputs_unchanged(self):
        if self.installed:
            from tools.experiments import game_pickup_state_update_integration as integration
            report = integration.audit(ROOT, ROOT / integration.BUILD)
            self.assertTrue(report['exact_first_link_reproduced'])
        else:
            super().test_production_inputs_unchanged()

    def test_complete_unlinked_original_slot_and_bindings(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Normalizer read a file')):
            result, moved = source.normalize(self.raw, self.bindings)
        self.assertEqual(len(result), 681 * 4)
        self.assertEqual(sum(map(len, moved.values())), 77)
        original = source.prior.original(ROOT, self.output)
        self.assertEqual((result, moved), source.payload(original))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(source.recipe_signature(), source.RECIPE_SHA)
        self.assertEqual(len(source.origins()), 681)
        consumed = {v if isinstance(v, int) else v[1] for v in source.origins()}
        self.assertEqual(consumed, set(range(680)) - source.OMITTED)
        for pos, item in enumerate(source.origins()):
            if not isinstance(item, int) and item[0] == 'delay':
                self.assertTrue(source.branch(self.words[pos - 1]))
                self.assertEqual(self.words[pos], 0)
        self.extra.update(retained_unique_origins=667, coalesced_origins=13,
            duplicate_origin_uses=14, mandatory_delay_copies=5)

    def test_all_stale_input_linked_binding_and_operand_recipe_controls(self):
        for i in range(680):
            raw = bytearray(self.raw)
            raw[i * 4 + 3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(raw), self.bindings)
            linked = self.raw_words.copy()
            linked[i] ^= 0x04000000
            with self.assertRaises(ValueError):
                source.apply_linked(linked, self.raw, self.bindings)
        bindings = 0
        for at, values in self.bindings.items():
            for j in range(len(values)):
                wrong = copy.deepcopy(self.bindings)
                kind, name = wrong[at][j]
                wrong[at][j] = kind, name + '_stale'
                with self.assertRaises(ValueError):
                    source.normalize(self.raw, wrong)
                bindings += 1
        fields = 0
        for pos, values in source.REGISTERS.items():
            for shift, register in values.items():
                with patch.dict(values, {shift: register ^ 1}):
                    with self.assertRaises(ValueError):
                        source.normalize(self.raw, self.bindings)
                fields += 1
        for pos, destination in source.BRANCH_EXCEPTIONS.items():
            with patch.dict(source.BRANCH_EXCEPTIONS, {pos: destination ^ 1}):
                with self.assertRaises(ValueError):
                    source.normalize(self.raw, self.bindings)
        self.extra.update(stale_raw_words=680, stale_linked_words=680,
            stale_bindings=bindings, stale_operand_fields=fields,
            stale_branch_destinations=len(source.BRANCH_EXCEPTIONS))

    def test_complete_literal_final_GPR_FPR_condition_and_memory_states(self):
        count = 0
        for name, case in self.corpus:
            for phase in (0, 8):
                memory = guest.fixture(case)
                models = [CutOracle(words, memory, case, phase).run()
                    for words in (self.retail, self.words)]
                self.assertEqual(state(models[0]), state(models[1]), (name, phase))
                count += 1
        self.extra.update(complete_final_model_states=count, hardware_FCSR_modeled=False)

    def test_fired_first_last_own_access_cuts_and_effective_raw_state_negative(self):
        count = 0
        for number, case in enumerate(representative_cases()):
            for phase in (0, 8):
                memory = guest.fixture(case)
                whole = CutOracle(self.retail, memory, case, phase).run()
                by_pc = {}
                for i, event in enumerate(whole.own):
                    by_pc.setdefault(event[0], []).append(i)
                cuts = sorted({i for indices in by_pc.values() for i in (indices[0], indices[-1])})
                for cut in cuts:
                    models = [CutOracle(words, memory, case, phase, cut=cut)
                        for words in (self.retail, self.words)]
                    for model in models:
                        with self.assertRaises(AccessCut):
                            model.run()
                        self.assertIsNotNone(model.fault)
                        self.assertEqual(len(model.own), cut)
                    self.assertEqual(state(models[0]), state(models[1]), (number, phase, cut))
                    count += 1
        case = guest.Case()
        memory = guest.fixture(case)
        original = CutOracle(self.retail, memory, case, cut=12)
        raw = CutOracle(self.raw_words, memory, case, cut=12)
        for model in (original, raw):
            with self.assertRaises(AccessCut):
                model.run()
        self.assertEqual(original.memory, raw.memory)
        self.assertNotEqual(original.r, raw.r)
        self.extra.update(fired_own_access_cuts=count, effective_raw_state_negatives=1)

    def test_independent_GNU_code_data_rebases_including_signed_LO16_carry(self):
        original = source.prior.original(ROOT, self.output)
        _, original_bindings = source.payload(original)
        names = {name for rows in (*self.bindings.values(), *original_bindings.values())
            for _, name in rows}
        plans = ((0x00100000, 0x00003000), (0x01000000, 0x00013000), (0x02000000, -0x00005000))
        count = 0
        for plan, (code_delta, data_delta) in enumerate(plans):
            entry = source.ENTRY + code_delta
            symbols = {name: (int(name.split('_', 1)[1], 16) +
                (data_delta if name.startswith('D_') else code_delta)) & 0xFFFFFFFF for name in names}

            def linked(obj, label, size):
                script = self.output / (label + '.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                elf = self.output / (label + '.elf')
                result = subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                    '-e', source.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
                    '-o', str(elf), str(obj)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = sections(elf)['.text'][1]
                return list(struct.unpack_from('>%dI' % size, data))

            raw = linked(self.obj, 'rebased-raw-' + str(plan), 680)
            truth = linked(original, 'rebased-original-' + str(plan), 681)
            fitted = source.apply_linked(raw, self.raw, self.bindings)
            self.assertEqual(fitted, truth)
            inverse = {value: int(name.split('_', 1)[1], 16)
                for name, value in symbols.items() if name.startswith('func_')}

            class Rebased(guest.UpdateOracle):
                def record_call(self, target):
                    super().record_call(inverse[target])

                def hook(self, target):
                    super().hook(inverse[target])

            for case in representative_cases():
                for phase in (0, 8):
                    memory = {(a + data_delta if a >= 0x80000000 else a) & 0xFFFFFFFF: v
                        for a, v in guest.fixture(case).items()}
                    models = []
                    for code in (truth, fitted):
                        model = Rebased(code, memory, case, phase)
                        model.entry = entry
                        model.code = dict(zip(range(entry, entry + 2724, 4), code))
                        models.append(model.run())
                    a, b = models
                    self.assertEqual((a.r, a.f, a.condition, a.memory, a.events, a.calls, a.visits),
                        (b.r, b.f, b.condition, b.memory, b.events, b.calls, b.visits))
                    count += 1
        self.extra.update(independent_GNU_rebase_plans=3, independent_GNU_rebased_phases=count)
