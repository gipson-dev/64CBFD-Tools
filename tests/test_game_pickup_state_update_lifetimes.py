"""Private local homes for the complete semantic pickup update."""

from pathlib import Path
from contextlib import ExitStack
from collections import Counter
from dataclasses import replace
import json
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_pickup_state_update_lifetimes as source
from tools.tests import test_game_pickup_state_update_match as previous
from tools.tests import game_pickup_state_update_oracle as guest


ROOT = Path(__file__).resolve().parents[2]


class PickupStateUpdateLifetimeTests(previous.PickupStateUpdateTests):
    @classmethod
    def setUpClass(cls):
        cls.context = ExitStack()
        cls.context.enter_context(patch.object(previous, 'ROOT', ROOT))
        cls.context.enter_context(patch.object(source.core, 'BUILD', source.BUILD))
        cls.context.enter_context(patch.object(source.core, 'SELECTED', source.SELECTED))
        try:
            super().setUpClass()
            # Recover the preceding byte-cursor source without changing old pins.
            cls.old_body = dict(source.core.candidates())['byte-cursor']
            cls.old_obj, cls.old_words, _ = source.core.compile_candidate(ROOT, cls.output, 'previous-byte-cursor', cls.old_body)
            cls.direct_obj, cls.direct_words, _ = source.core.compile_candidate(ROOT, cls.output, 'direct-homes-control', source.DIRECT_HOMES)
            cls.alias_rows = []
            cls.connected_rows = []
            cls.cursor_rows, cls.final_states = [], []
        except BaseException:
            cls.context.close()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
            path = cls.output / 'test-receipt.json'
            row = json.loads(path.read_text())
            row.update(private_homes=source.shape(cls.obj), fired_home_aliases=len(cls.alias_rows),
                effective_previous_home_negatives=sum(r['previous_differs'] for r in cls.alias_rows),
                connected_coordinate_phases=len(cls.connected_rows),
                connected_previous_negatives=sum(r['previous_differs'] for r in cls.connected_rows),
                selector_cursor_aliases=len(cls.cursor_rows),
                literal_final_memory_phases=len(cls.final_states),
                literal_final_FPR_phases=sum(r['FPR_equal'] for r in cls.final_states),
                literal_final_GPR_phases=sum(r['GPR_equal'] for r in cls.final_states))
            path.write_text(json.dumps(row, indent=2) + '\n')
            (cls.output / 'home-aliases.json').write_text(json.dumps(cls.alias_rows, indent=2) + '\n')
            (cls.output / 'connected-coordinate-phases.json').write_text(json.dumps(cls.connected_rows, indent=2) + '\n')
            (cls.output / 'selector-cursor-aliases.json').write_text(json.dumps(cls.cursor_rows, indent=2) + '\n')
            (cls.output / 'literal-final-states.json').write_text(json.dumps(cls.final_states, indent=2) + '\n')
        finally:
            cls.context.close()

    def test_selected_profile_shape_and_initial_source_control(self):
        self.assertEqual((self.report['words'], self.report['frame'], self.report['differences']), (680, 280, 636))
        self.assertEqual(self.report['raw_SHA256'], 'aa2d148b4b51b725d32722cd832571aad2822a9bc68f16a97116b93a3a411f82')
        self.assertEqual(self.words, self.normal)
        self.assertEqual(self.report['diagnostics'], '')

    def test_original_private_workspace_and_capture_homes_emit_from_C(self):
        self.assertEqual(source.shape(self.obj), dict(frame=280, player=0x110,
            pointers=[0xD8, 0xD4, 0xD0, 0xCC, 0xC8, 0xC0, 0xBC, 0xB8, 0xB4, 0xB0, 0xAC, 0xA8],
            attached=0x80, coordinates=[0xF0, 0xEC, 0xE8]))

    def test_cached_selector_home_remains_original_after_cursor_advance(self):
        case = guest.Case(items=(guest.Item(), guest.Item(selector=2)))
        for phase in (0, 8):
            memory = guest.fixture(case)
            a = guest.UpdateOracle(self.retail, memory, case, phase).run()
            b = guest.UpdateOracle(self.words, memory, case, phase).run()
            home = guest.STACK + phase - 280 + 0xD4
            self.assertEqual(guest.read(a.memory, home), guest.BANK + 0xEF0)
            self.assertEqual(guest.read(b.memory, home), guest.read(a.memory, home))

    def test_rotating_selector_uses_its_cached_signed_byte(self):
        case = guest.Case(selector=127)
        model = guest.UpdateOracle(self.words, guest.fixture(case), case).run()
        reads = [e for e in model.events if e[:3] == ('R', guest.SELECTOR, 1)]
        self.assertEqual(len(reads), 1)
        self.assertEqual(guest.read(model.memory, guest.SELECTOR, 1, True), -128)
        _, words, _ = source.core.compile_candidate(ROOT, self.output, 'uncached-selector-control', source.LIVE_CURSOR)
        control = guest.UpdateOracle(words, guest.fixture(case), case).run()
        self.assertEqual(len([e for e in control.events if e[:3] == ('R', guest.SELECTOR, 1)]), 2)

    def test_complete_retail_and_both_compiled_profiles_against_independent_reference(self):
        super().test_complete_retail_and_both_compiled_profiles_against_independent_reference()
        self.assertEqual(self.pairs, 936)
        self.assertEqual(self.read_differences, [])

    def test_raw_profile_is_not_a_matching_credit(self):
        self.assertEqual(self.report['words'], 680)
        self.assertEqual(source.core.WORDS - self.report['words'], 1)
        self.assertFalse(self.report['installed'])
        self.assertEqual(self.report['matching_credit'], 0)

    def test_declaration_partition_changes_only_displacements_and_preserves_77_bindings(self):
        slots = {0x114: 0x110, 0x104: 0xD8, 0x100: 0xD4, 0xFC: 0xD0, 0xF8: 0xCC,
            0xF4: 0xC8, 0xF0: 0xC0, 0xEC: 0xBC, 0xE8: 0xB8, 0xE4: 0xB4,
            0xE0: 0xB0, 0xDC: 0xAC, 0xD8: 0xA8, 0xB0: 0x80,
            0x110: 0xF0, 0x10C: 0xEC, 0x108: 0xE8}
        self.assertEqual(len(self.direct_words), len(self.old_words))
        changed = []
        for i, (old, new) in enumerate(zip(self.old_words, self.direct_words)):
            if old == new:
                continue
            self.assertEqual(old >> 16, new >> 16, i)
            self.assertEqual(old >> 21 & 31, 29, i)
            self.assertIn(old >> 26, (9, 35, 43, 49, 57), i)
            self.assertEqual(new & 65535, slots[old & 65535], i)
            changed.append(dict(index=i, previous=old & 65535, selected=new & 65535))
        self.assertEqual({r['previous'] for r in changed}, set(slots))

        def bindings(obj):
            _, functions, relocations = source.parse_object(obj)
            f = functions[source.core.FUNCTION]
            return {at - f['value']: rows for at, rows in relocations.items()
                if f['value'] <= at < f['value'] + 680 * 4}

        old, new = bindings(self.old_obj), bindings(self.direct_obj)
        self.assertEqual(old, new)
        self.assertEqual(sum(map(len, new.values())), 77)
        (self.output / 'direct-displacement-proof.json').write_text(json.dumps(dict(
            changed_words=changed, bindings=77, private_displacements_only=True), indent=2) + '\n')

    def test_independent_GNU_original_slot_and_explicit_remaining_binding_boundary(self):
        obj = source.original(ROOT, self.output)
        text, functions = source.core.link_owner(ROOT, self.output, obj, source.core.OWNER)
        at = functions[source.core.FUNCTION]['value']
        self.assertEqual(text[at:at + 2724], struct.pack('>681I', *self.retail))

        def counts(path):
            _, functions, rows = source.parse_object(path)
            item = functions[source.core.FUNCTION]
            return Counter(r for at, values in rows.items()
                if item['value'] <= at < item['value'] + item['size'] for r in values)

        raw, retail = counts(self.obj), counts(obj)
        self.assertEqual(sum(raw.values()), 73)
        self.assertEqual(sum(retail.values()), 77)
        expected = Counter({('R_MIPS_HI16', 'D_800D23B0'): 1, ('R_MIPS_LO16', 'D_800D23B0'): 1,
            ('R_MIPS_HI16', 'D_80087340'): 2, ('R_MIPS_LO16', 'D_80087340'): 2,
            ('R_MIPS_HI16', 'D_800BE9E4'): 1, ('R_MIPS_LO16', 'D_800BE9E4'): 1})
        self.assertEqual(retail - raw, expected)
        self.assertEqual(raw - retail, Counter({('R_MIPS_HI16', 'D_800CC2D0'): 2,
            ('R_MIPS_LO16', 'D_800CC2D0'): 2}))
        (self.output / 'remaining-binding-boundary.json').write_text(json.dumps(dict(
            raw_entries=73, retail_entries=77,
            original_extra=[(k, n) for k, n in (retail - raw).items()],
            raw_extra=[(k, n) for k, n in (raw - retail).items()],
            independent_original_link_matches_ROM=True), indent=2) + '\n')

    def test_live_selector_cursor_does_not_reload_its_mutated_cached_home(self):
        for phase in (0, 8):
            home = guest.STACK + phase - 280 + 0xD4
            case = guest.Case(items=(guest.Item(), guest.Item(selector=2, timer=1)),
                actions=((guest.OBJECT, 0, home, guest.ALT + 0xEF0, 4),
                         (guest.OBJECT, 0, guest.ALT + 0xEF4, 3, 4)))
            memory = guest.fixture(case)
            models = [guest.UpdateOracle(words, memory, case, phase).run()
                for words in (self.retail, self.words, self.direct_words)]
            self.assertEqual(previous.observation(models[0]), previous.observation(models[1]))
            self.assertIn(case.actions[0], models[0].fired)
            self.assertNotEqual(previous.observation(models[0]), previous.observation(models[2]))
            type(self).cursor_rows.append(dict(phase=phase, home=home, mutation_fired=True,
                direct_home_control_differs=True))

    def test_complete_final_public_and_private_memory_and_FPR_contents(self):
        for name, case in self.corpus:
            for phase in (0, 8):
                memory = guest.fixture(case)
                a = guest.UpdateOracle(self.retail, memory, case, phase).run()
                b = guest.UpdateOracle(self.words, memory, case, phase).run()
                with self.subTest(case=name, phase=phase):
                    self.assertEqual(a.memory, b.memory)
                    self.assertEqual(a.f, b.f)
                type(self).final_states.append(dict(case=name, phase=phase, memory_equal=a.memory == b.memory,
                    FPR_equal=a.f == b.f, GPR_equal=a.r == b.r))

    def test_real_capture_homes_with_fired_guest_aliases_and_previous_negatives(self):
        player = guest.Player(current=9, override=9)
        base = guest.Case(players=(player,), selector=0,
            items=(guest.Item(timer=0, owner=1),))
        variants = []
        for slot, offset, label in ((0xD8, 0xEB0, 'owners'), (0xD0, 0xF70, 'held'),
                (0xC8, 0x1070, 'timers'), (0xC0, 0x1174, 'kinds'), (0xBC, 0x11F4, 'flags')):
            extra = {'kinds': ((guest.LIST, 0, guest.ALT + offset, 2222, 4),),
                'flags': ((guest.LIST, 0, guest.ALT + offset, 2, 4),),
                'timers': ((guest.LIST, 0, guest.ALT + offset, 1, 4),)}.get(label, ())
            variants.append((label, base, guest.LIST, slot, guest.ALT + offset, extra))
        variants.append(('selectors', replace(base, items=(guest.Item(selector=1, timer=1),
            guest.Item(selector=2, timer=-1))), guest.LIST, 0xD4, guest.ALT + 0xEF0,
            ((guest.LIST, 0, guest.ALT + 0xEF0, 2, 4),)))
        variants.append(('overrides', replace(base, players=(player, player), items=()),
            guest.LIST, 0xCC, guest.ALT + 0xFF0, ((guest.LIST, 0, guest.ALT + 0xFF4, 20, 4),)))
        variants.append(('fixed-target', replace(base, items=(guest.Item(timer=1),)),
            guest.LIST, 0xB8, guest.ALT + 0x1274, ((guest.LIST, 0, guest.ALT + 0x1274, 1, 4),)))
        variants.append(('grace', replace(base, items=(guest.Item(timer=1),)),
            guest.LIST, 0xB4, guest.ALT + 0x12F4, ((guest.LIST, 0, guest.ALT + 0x12F4, 10, 4),)))
        for slot, offset, label in ((0xB0, 0x1374, 'saved-x'), (0xAC, 0x13F4, 'saved-y'), (0xA8, 0x1474, 'saved-z')):
            variants.append((label, replace(base, items=(guest.Item(timer=1, grace=10),)),
                guest.LIST, slot, guest.ALT + offset, ((guest.LIST, 0, guest.ALT + offset, 12345, 4),)))
        for slot, label in ((0xF0, 'coordinate-x'), (0xEC, 'coordinate-y'), (0xE8, 'coordinate-z')):
            variants.append((label, replace(base, items=(guest.Item(timer=1),)),
                guest.COORDS, slot, guest.bits(-123.75), ()))
        variants.append(('attached-list', replace(base, effects=(42, 1), items=()),
            guest.LIST, 0x80, guest.EFFECTS + 0x80, ()))
        variants.append(('player-counter', replace(base, players=(player, guest.Player(override=20)), items=()),
            guest.LIST, 0x110, 1, ()))
        for label, case, target, slot, value, extra in variants:
            for phase in (0, 8):
                address = guest.STACK + phase - 280 + slot
                action = (target, 0, address, value, 4)
                case_with_alias = replace(case, actions=(*case.actions, *extra, action))
                memory = guest.fixture(case_with_alias)
                wanted = guest.UpdateOracle(self.retail, memory, case_with_alias, phase).run()
                actual = guest.UpdateOracle(self.words, memory, case_with_alias, phase).run()
                with self.subTest(home=label, phase=phase):
                    self.assertEqual(previous.observation(actual), previous.observation(wanted))
                    self.assertIn(action, wanted.fired)
                    old = guest.UpdateOracle(self.old_words, memory, case_with_alias, phase).run()
                    differs = previous.observation(old) != previous.observation(wanted)
                    self.assertTrue(differs, 'The previous home layout must be an effective negative')
                type(self).alias_rows.append(dict(home=label, phase=phase, address=address,
                    slot=slot, target=target, mutation_fired=True, previous_differs=differs))

    def test_real_coordinate_helper_valid_and_byte255_rejection(self):
        # The original helper returns zero without writing for index255. This
        # is a guest seeded-RAM check, not a portable-C uninitialized-value test.
        coordinate_words = struct.unpack_from('>35I', self.values['conker/conker.us.bin'], 0x15086CBC - 0x15086364 + 0xB3814)
        for node in (0, 255):
            for random in (False, True):
                case = guest.Case(items=(guest.Item(timer=1, flags=int(random)),), node=node)
                for phase in (0, 8):
                    memory = guest.fixture(case)
                    for offset, number in ((0xF0, -23.75), (0xEC, 123.75), (0xE8, -456.75)):
                        guest.put(memory, guest.STACK + phase - 280 + offset, guest.bits(number), 4)
                    for offset, number in ((0x110, 0.0), (0x10C, 12.5), (0x108, 13.5)):
                        guest.put(memory, guest.STACK + phase - 280 + offset, guest.bits(number), 4)
                    guest.put(memory, 0x80087290, 1, 2)
                    guest.put(memory, 0x800D2350, 0x24800, 4)
                    for axis, number in enumerate((300, -32768, 127)):
                        guest.put(memory, 0x24800 + axis * 2, number, 2)
                    models = []
                    for words in (self.retail, self.words, self.old_words):
                        model = guest.UpdateOracle(words, memory, case, phase)
                        model.code.update(zip(range(guest.COORDS, guest.COORDS + 140, 4), coordinate_words))
                        models.append(model.run())
                    with self.subTest(node=node, random=random, phase=phase):
                        self.assertEqual(previous.observation(models[0]), previous.observation(models[1]))
                        self.assertTrue(set(range(guest.COORDS, guest.COORDS + 20, 4)) & models[0].visits)
                        xyz = (300, -32708, 127) if node == 0 else (3 if random else -23, 183, -456)
                        for axis, value in enumerate(xyz):
                            self.assertEqual(guest.read(models[0].memory, guest.ITEMS + 0x10 + axis * 2, 2, True), value)
                        differs = previous.observation(models[2]) != previous.observation(models[0])
                        self.assertEqual(differs, node == 255)
                    type(self).connected_rows.append(dict(node=node, random=random, phase=phase,
                        real_helper_entered=True, previous_differs=differs))


if __name__ == '__main__':
    unittest.main()
