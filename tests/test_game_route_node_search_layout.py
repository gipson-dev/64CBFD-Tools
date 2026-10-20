"""Literal route-search words, modeled state, fault cuts and GNU rebases."""

import copy
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_node_search_layout as source
from tools.experiments import game_route_node_search_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_layout import relocate
from tools.tests import test_game_route_node_search_start_home as previous
from tools.tests import game_route_node_search_oracle as guest


ROOT = Path(__file__).resolve().parents[2]


class AccessCut(Exception):
    pass


class CodeFetch(dict):
    def __init__(self, owner):
        super().__init__(owner.code)
        self.owner = owner

    def __getitem__(self, address):
        self.owner.current_pc = address
        return super().__getitem__(address)


class LiteralOracle(guest.SearchOracle):
    def __init__(self, *args, cut=None, **kwargs):
        self.armed, self.provider_active = False, False
        self.own, self.cut, self.fault = [], cut, None
        super().__init__(*args, **kwargs)
        self.code = CodeFetch(self)
        self.armed = True

    def access(self, kind, address, size):
        if self.armed and not self.provider_active:
            event = (self.current_pc, kind, address, size)
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

    def hook(self, target):
        self.provider_active = True
        try:
            super().hook(target)
        finally:
            self.provider_active = False


def state(model):
    return (model.r, model.f, model.condition, model.memory, model.reads,
        model.stores, model.events, model.calls, model.visits,
        model.current_pc, model.own, model.fault)


class RouteNodeSearchLayoutTests(previous.RouteNodeSearchStartHomeTests):
    test_pure_source_origins_branch_delay_and_binding_guards = None

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        cls.fixture = integration.fixture_context(cls.root)
        cls.installed = cls.fixture.__enter__()
        cls.values = source.core.freeze(cls.root, cls.output)
        cls.corpus, cls.code, cls.rows = list(guest.cases()), {}, {}
        _, cls.code[False], cls.rows[False] = source.core.compile_candidate(
            cls.root, cls.output, 'selected-False', source.SELECTED, False)
        cls.raw_obj, cls.raw_words, cls.code[True], cls.report = source.qualify(cls.root, cls.output)
        cls.rows[True] = json.loads((cls.output / 'selected-True.json').read_text())
        raw, bindings = source.core.payload(cls.raw_obj)
        cls.old_layout = source.prior.apply_linked(cls.raw_words, raw, bindings)
        cls.old_capture = list(cls.raw_words)
        for i in source.prior.prior.SLOT_WORDS:
            cls.old_capture[i] = cls.old_capture[i] & 0xFFFF0000 | 0x60
        cls.retail = list(struct.unpack_from('>539I', cls.values['conker/conker.us.bin'], source.ROM))
        _, cls.predecessor, _ = source.core.compile_candidate(
            cls.root, cls.output, 'predecessor', source.prior.prior.prior.SELECTED, True)
        cls.completed, cls.native_count, cls.alias_pairs, cls.alias_negatives = 0, 0, 0, 0
        cls.footprints, cls.native_loop_negatives, cls.coverage = 0, 0, set()
        cls.closed_captures, cls.capture_negatives = 0, 0
        cls.word_negatives, cls.binding_negatives, cls.linked_negatives = 0, 0, 0
        cls.start_aliases, cls.start_negatives, cls.cost_aliases, cls.early_aliases = 0, 0, 0, 0
        cls.start_histories = 0
        cls.extra = {}

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
            path = cls.output / 'test-receipt.json'
            row = json.loads(path.read_text())
            row.update(cls.extra, installed=cls.installed)
            path.write_text(json.dumps(row, indent=2) + '\n')
            print('route-search literal qualification:', cls.extra)
        finally:
            cls.fixture.__exit__(None, None, None)

    def test_complete_owner_profiles_and_predecessor_pins(self):
        before = self.values[source.core.SOURCE].decode()
        unit = source.core.recovered_owner(before, source.SELECTED)
        from tools.tests.game_owner_pool import normalized_pools
        for normal in (False, True):
            a, da = source.core.compile_profile(self.root, self.output, before, 'before-' + str(normal), normal)
            b, db = source.core.compile_profile(self.root, self.output, unit, 'after-' + str(normal), normal)
            self.assertEqual((da, db), ('', ''))
            self.assertEqual(integration.same_functions(a, b, (source.FUNCTION,)), 72)
            self.assertEqual(normalized_pools(a), normalized_pools(b))
            self.assertEqual(source.core.payload(b), source.core.payload(self.output / ('selected-' + str(normal) + '.o')))
        if self.installed:
            integration.audit(self.root, self.root / integration.BUILD)
        else:
            for name, value in self.values.items():
                self.assertEqual((self.root / name).read_bytes(), value)
        owner = self.output / 'after-True.o'
        raw, bindings = source.core.payload(owner)
        self.assertEqual((raw, bindings), source.core.payload(self.raw_obj))
        image, functions = source.core.link_owner(self.root, self.output, owner, source.core.OWNER)
        words = struct.unpack_from('>535I', image, functions[source.FUNCTION]['value'])
        self.assertEqual(source.apply_linked(words, raw, bindings), self.code[True])

    def test_pure_layout_origins_and_all_stale_input_guards(self):
        raw, bindings = source.core.payload(self.raw_obj)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Normalizer read a file')):
            normalized, moved = source.normalize(raw, bindings)
        self.assertEqual(list(struct.unpack('>539I', normalized)),
            relocate(normalized, {}, {}))
        self.assertEqual(self.code[True], self.retail)
        self.assertEqual(sum(map(len, moved.values())), 14)
        order = source.origins()
        self.assertEqual({i for i in order if isinstance(i, int)}, set(range(539)) - source.OMITTED)
        self.assertEqual(len(order), 539)
        for i in range(535):
            stale = bytearray(raw)
            stale[i * 4 + 3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(stale), bindings)
            type(self).word_negatives += 1
            stale = list(self.raw_words)
            stale[i] ^= 0x04000000
            with self.assertRaises(ValueError):
                source.apply_linked(stale, raw, bindings)
            type(self).linked_negatives += 1
        for at, rows in bindings.items():
            for j in range(len(rows)):
                stale = copy.deepcopy(bindings)
                kind, name = stale[at][j]
                stale[at][j] = kind, name + '_stale'
                with self.assertRaises(ValueError):
                    source.normalize(raw, stale)
                type(self).binding_negatives += 1
        controls = 0
        for item, fields in source.OVERRIDES.items():
            for shift, value in fields.items():
                bad = dict(fields)
                bad[shift] = value ^ 1
                with patch.dict(source.OVERRIDES, {item: bad}):
                    with self.assertRaises(ValueError):
                        source.normalize(raw, bindings)
                controls += 1
        type(self).extra['stale_recipe_field_controls'] = controls

    def test_full_modeled_final_state_and_fired_access_cuts(self):
        for case in self.corpus:
            for phase in (0, 8):
                models = [LiteralOracle(code, guest.fixture(case), case, phase).run()
                          for code in (self.retail, self.code[True])]
                self.assertEqual(state(models[0]), state(models[1]), (case, phase))
        ordinary = guest.Case()
        a = LiteralOracle(self.retail, guest.fixture(ordinary), ordinary).run()
        b = LiteralOracle(self.old_layout, guest.fixture(ordinary), ordinary).run()
        self.assertEqual(a.memory, b.memory)
        self.assertNotEqual(state(a), state(b), 'Old allocation is not an effective state negative')
        cuts = 0
        for case in (ordinary, guest.Case(count=0), guest.Case(goals=(5,) * 5, avoid=(1,) * 4),
                     guest.Case(special=tuple(range(6)))):
            for phase in (0, 8):
                baseline = LiteralOracle(self.retail, guest.fixture(case), case, phase).run()
                first, last = {}, {}
                for i, event in enumerate(baseline.own):
                    first.setdefault(event[0], i)
                    last[event[0]] = i
                for at in sorted(set(first.values()) | set(last.values())):
                    models = [LiteralOracle(code, guest.fixture(case), case, phase, cut=at)
                              for code in (self.retail, self.code[True])]
                    for model in models:
                        with self.assertRaises(AccessCut):
                            model.run()
                        self.assertIsNotNone(model.fault, 'Access-cut gate did not fire')
                    self.assertEqual(state(models[0]), state(models[1]), (case, phase, at))
                    cuts += 1
        type(self).extra.update(full_final_model_states=426, fired_access_cuts=cuts,
            effective_old_state_negatives=1, literal_private_state_exact=True,
            hardware_FCSR_modeled=False)

    def test_cached_goal_bound_survives_late_incoming_byte_mutation(self):
        reports = []
        for phase in (0, 8):
            case = guest.Case(goals=(5,) * 5)
            home = guest.STACK + phase - 1536 + 0x607

            class GoalBoundAlias(LiteralOracle):
                def __init__(self, *args, **kwargs):
                    self.goal_reads, self.fired = 0, False
                    super().__init__(*args, **kwargs)

                def get(self, address, size):
                    value = super().get(address, size)
                    if self.armed and (address, size) == (guest.GOALS, 1):
                        self.goal_reads += 1
                        if self.goal_reads == 2:
                            self.provider_active = True
                            self.put(home, 1, 1)
                            self.provider_active = False
                            self.fired = True
                    return value

            models = [GoalBoundAlias(code, guest.fixture(case), case, phase).run()
                      for code in (self.retail, self.code[True], self.old_layout)]
            for model in models:
                self.assertTrue(model.fired)
                self.assertIn((home, 1, 1), model.stores)
            self.assertEqual(state(models[0]), state(models[1]))
            reads = [[x for x in m.reads if not guest.private(x[0])] for m in models]
            self.assertNotEqual(reads[0], reads[2], 'Old bound reload is not an effective read negative')
            reports.append(dict(phase=phase, fired=True, retail_reads=len(reads[0]),
                literal_reads=len(reads[1]), old_reads=len(reads[2])))
        (self.output / 'cached-goal-bound-aliases.json').write_text(json.dumps(reports, indent=2) + '\n')
        type(self).extra['cached_goal_bound_aliases_and_old_negatives'] = 2

    def test_all_539_words_with_fired_inner_flag_alias(self):
        for phase in (0, 8):
            case = guest.Case(special=tuple(range(6)))

            class InnerFlagAlias(LiteralOracle):
                def __init__(self, *args, **kwargs):
                    self.fired = False
                    super().__init__(*args, **kwargs)

                def get(self, address, size):
                    if self.armed and self.current_pc == source.ENTRY + 496 * 4 and not self.fired:
                        self.asserted_alias = (address, size)
                        assert size == 1 and guest.private(address)
                        assert self.memory[address] == 1
                        self.provider_active = True
                        self.put(address, 0, 1)
                        self.provider_active = False
                        self.fired = True
                    return super().get(address, size)

            models = [InnerFlagAlias(code, guest.fixture(case), case, phase).run()
                      for code in (self.retail, self.code[True])]
            for model in models:
                self.assertTrue(model.fired, 'Inner flag alias did not fire')
                self.assertIn(source.ENTRY + 498 * 4, model.visits)
            self.assertEqual(state(models[0]), state(models[1]))
            self.coverage.update((pc - source.ENTRY) // 4 for pc in models[0].visits)
        type(self).extra['fired_inner_flag_aliases'] = 2

    def test_original_GNU_words_bindings_and_independent_rebases(self):
        original = source.original(self.root, self.output)
        original_raw, original_bindings = source.core.payload(original)
        raw, bindings = source.core.payload(self.raw_obj)
        normalized, moved = source.normalize(raw, bindings)
        self.assertEqual((normalized, moved), (original_raw, original_bindings))
        names = {name for rows in moved.values() for _, name in rows}
        plans = [
            (source.ENTRY, {name: int(name.split('_', 1)[1], 16) for name in names}),
            (0x18008000, dict(D_80087298=0x81007FFC, D_80087290=0x81008002,
                D_800D2350=0x8100FFFC, D_800D2354=0x81018000,
                func_15086C70=0x18017FFC, func_15086BD0=0x18018000)),
            (0x19008004, dict(D_80087298=0x8200FFFC, D_80087290=0x82017FFE,
                D_800D2350=0x82018000, D_800D2354=0x82028004,
                func_15086C70=0x19027FFC, func_15086BD0=0x19028000)),
        ]
        runs = 0
        for index, (entry, symbols) in enumerate(plans):
            script = self.output / ('original-rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                '-e', source.FUNCTION, *['--defsym=%s=0x%X' % row for row in symbols.items()],
                '-o', str(elf), str(original)], capture_output=True, check=True)
            address, text = sections(elf)['.text']
            self.assertEqual(address, entry)
            wanted = list(struct.unpack_from('>539I', text))
            emitted = relocate(normalized, moved, symbols)
            self.assertEqual(emitted, wanted)
            for case in (guest.Case(), guest.Case(goals=(5,) * 5, avoid=(1,) * 4),
                         guest.Case(special=tuple(range(6)))):
                memory = guest.fixture(case)
                for name, old, size in (('D_80087298', guest.SELECTED, 1),
                        ('D_80087290', guest.COUNT, 2), ('D_800D2350', guest.NODES, 4),
                        ('D_800D2354', guest.DISTANCE, 4)):
                    for i in range(size):
                        memory[symbols[name] + i] = memory[old + i]
                with patch.multiple(guest, LOOKUP=symbols['func_15086C70'], LENGTH=symbols['func_15086BD0']):
                    for phase in (0, 8):
                        models = [LiteralOracle(code, memory, case, phase, entry).run()
                                  for code in (wanted, emitted)]
                        self.assertEqual(state(models[0]), state(models[1]))
                        runs += 1
        type(self).extra.update(independent_GNU_rebase_plans=3, independent_GNU_rebased_runs=runs)


if __name__ == '__main__':
    unittest.main()
