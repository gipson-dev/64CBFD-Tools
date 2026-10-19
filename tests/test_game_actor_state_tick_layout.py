"""Actor-tick complete origins, literal private state, aliases and GNU maps."""

import copy
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_layout as layout
from tools.experiments.game_remaining_donor_candidates import sections
from tools.tests import test_game_actor_state_tick_candidates as guest
from tools.tests import test_game_actor_state_tick_homes as homes
from tools.tests import test_game_actor_state_tick_draw as draw
from tools.tests import test_game_actor_state_tick_spills as spills


ROOT = Path(__file__).resolve().parents[2]


class AccessFault(Exception):
    pass


class LiteralOracle(guest.TickOracle):
    def __init__(self, *args, **kwargs):
        self.observing = self.in_provider = True
        self.accesses, self.fault, self.requested = 0, None, None
        self.executed = []
        super().__init__(*args, **kwargs)
        self.observing = self.in_provider = False

    def access(self, kind, address, size):
        if self.observing or self.in_provider:
            return
        self.requested = kind, address, size
        if self.accesses == self.fault:
            raise AccessFault()
        self.accesses += 1

    def get(self, address, size):
        self.access('R', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        self.access('W', address, size)
        return super().put(address, value, size)

    def execute(self, word):
        self.executed.append(word)
        return super().execute(word)

    def record_call(self, target):
        self.observing = True
        try:
            return super().record_call(target)
        finally:
            self.observing = False

    def hook(self, target):
        self.in_provider = True
        try:
            return super().hook(target)
        finally:
            self.in_provider = False


def state(model):
    return (model.r, model.f, model.memory, model.stores, model.reads, model.visits,
            model.accesses, model.requested, model.condition, model.calls, model.events,
            model.executed, model.provider.calls, model.provider.occurrences,
            model.provider.random_index, getattr(model, 'lo', None), getattr(model, 'hi', None))


def assemble(root, output, name, text):
    asm = output / (name + '.s')
    asm.write_text((root / 'conker/include/asm_processor_prelude.inc').read_text() + '\n.text\n' + text)
    obj = asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
        '-I', str(root / 'conker/include'), '-o', str(obj), str(asm)], check=True, capture_output=True)
    return obj


def original_function(text, name):
    opening, closing = 'glabel ' + name + '\n', 'endlabel ' + name
    if text.count(opening) != 1 or text.count(closing) != 1:
        raise ValueError('Unknown original actor-tick extent')
    return ('.type ' + name + ',@function\n' + opening +
            text.split(opening, 1)[1].split(closing, 1)[0] + closing +
            '\n.size ' + name + ',.-' + name + '\n')


def link_map(output, name, obj, anchors):
    script = output / (name + '.ld')
    script.write_text('SECTIONS { .text 0x1508A6FC : SUBALIGN(4) { *(.text) } }\n')
    elf = script.with_suffix('.elf')
    result = subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', script.name,
        '-e', 'func_1508A6FC', '--no-warn-mismatch',
        *['--defsym=%s=0x%X' % item for item in anchors.items()], '-o', elf.name, obj.name],
        cwd=output, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode())
    data = sections(elf)['.text'][1]
    if any(data[2712:]):
        raise ValueError('Nonzero actor-tick GNU alignment tail')
    return list(struct.unpack_from('>678I', data))


class ActorStateTickLayoutTests(unittest.TestCase):
    maxDiff = 1200
    test_empty_inactive_first_seen_and_all_sixteen_slots = guest.ActorStateTickCandidateTests.test_empty_inactive_first_seen_and_all_sixteen_slots
    test_categories_timer_signs_states_actions_and_probability = guest.ActorStateTickCandidateTests.test_categories_timer_signs_states_actions_and_probability
    test_opaque_helpers_can_replace_global_and_mutate_captured_inputs = guest.ActorStateTickCandidateTests.test_opaque_helpers_can_replace_global_and_mutate_captured_inputs
    test_actor_action_call_save_is_a_full_word_not_a_byte = draw.ActorStateTickDrawTests.test_actor_action_call_save_is_a_full_word_not_a_byte

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / layout.BUILD / 'test'
        from tools.experiments.game_actor_state_tick_integration import fixture_context
        with fixture_context(cls.root) as cls.installed:
            cls.report, cls.baseline, cls.words = layout.qualify(cls.root, cls.output)
        cls.raw, cls.bindings = layout.source.prior.prior.prior.payload(cls.output / 'selected.o')
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.retail = list(struct.unpack_from('>678I', (cls.root / 'conker/conker.us.bin').read_bytes(),
                                            layout.source.prior.prior.prior.ROM))
        cls.completed, cls.literal_pairs, cls.alias_pairs, cls.alias_negatives = 0, 0, 0, 0
        cls.action_word_pairs, cls.cut_pairs, cls.gnu_runs, cls.coverage = 0, 0, 0, set()

    @classmethod
    def tearDownClass(cls):
        receipt = dict(cls.report, complete_fixtures=cls.completed, literal_private_pairs=cls.literal_pairs,
            alias_pairs=cls.alias_pairs, effective_wrong_layout_negatives=cls.alias_negatives,
            action_word_pairs=cls.action_word_pairs, fired_access_cut_pairs=cls.cut_pairs,
            completed_GNU_rebased_runs=cls.gnu_runs, retail_words_visited=len(cls.coverage),
            installed=cls.installed, matching_credit=1 if cls.installed else 0)
        (cls.output / 'test-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('actor-state layout qualification:', receipt)

    def compare(self, memory, phase=0, **providers):
        expected, calls, stores, result = guest.reference(memory, **providers)
        for target, occurrence in providers.get('actions', {}):
            self.assertGreater(sum(c[0] == target for c in calls), occurrence, 'Mutation did not fire')
        models = [LiteralOracle(w, memory, phase, **providers).run() for w in (self.retail, self.words)]
        self.assertTrue(state(models[0]) == state(models[1]), 'Literal/private machine state differs')
        for model in models:
            self.assertEqual(model.calls, calls)
            self.assertEqual([s for s in model.stores if not guest.private(s[0])], stores)
            self.assertEqual({a: b for a, b in model.memory.items() if not guest.private(a)},
                             {a: b for a, b in expected.items() if not guest.private(a)})
            self.assertEqual(model.r[2], result)
        type(self).completed += 1
        type(self).literal_pairs += 1
        type(self).coverage.update(models[0].visits)

    def test_complete_origins_bindings_and_expected_source_fields(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual(hashlib.sha256(self.normalized).hexdigest(), layout.NORMALIZED_SHA)
        order = layout.origins()
        self.assertEqual((len(order), sum(isinstance(i, int) for i in order)), (678, 675))
        self.assertEqual(set(range(678)) - {i for i in order if isinstance(i, int)}, layout.REMOVED)
        memory = [i for i, w in enumerate(struct.unpack('>678I', self.raw)) if w >> 26 in layout.MEMORY]
        self.assertTrue(all(order.count(i) == 1 for i in memory))
        self.assertEqual(len(memory), self.report['retained_memory_instructions'])
        self.assertEqual(sum(map(len, self.moved.values())), 62)
        for at, item in enumerate(order):
            if isinstance(item, int) and item * 4 in self.bindings:
                self.assertEqual(self.moved[at * 4], self.bindings[item * 4])
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Recipe read a file')):
            self.assertEqual(layout.normalize(self.raw, self.bindings), (self.normalized, self.moved))

    def test_all_changed_word_binding_and_recipe_controls_reject(self):
        for at in range(678):
            wrong = bytearray(self.raw)
            wrong[at * 4] ^= 1
            with self.assertRaises(ValueError):
                layout.normalize(bytes(wrong), self.bindings)
        for at in self.bindings:
            wrong = copy.deepcopy(self.bindings)
            wrong[at] = [('R_MIPS_26', 'func_1508A6FC')]
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, wrong)
        for key, value in (('REGISTERS', {}), ('SLOTS', {}), ('SCHEDULE', {}), ('BRANCH_TARGETS', {})):
            with patch.object(layout, key, value):
                with self.assertRaises(ValueError):
                    layout.normalize(self.raw, self.bindings)

    def test_all_twenty_nine_frame_aliases_and_wrong_layout_controls(self):
        names = (*layout.source.MATCHED_HOMES, *spills.CURSORS, 'eventByte', 'drawActor')
        self.assertEqual(len(names), 29)
        for name, phase in itertools.product(names, (0, 8)):
            memory, options, target = (draw.alias_case(name, phase) if name in layout.source.MATCHED_HOMES
                                       else spills.alias_case(name, phase))
            plain = {k: v for k, v in options.items() if k != 'actions'}
            base = LiteralOracle(self.retail, memory, phase, **plain).run()
            retail, candidate = (LiteralOracle(w, memory, phase, **options).run()
                                  for w in (self.retail, self.words))
            for model in (retail, candidate):
                self.assertGreater(model.provider.occurrences.get(target, 0), 0)
            self.assertTrue(homes.observation(retail) != homes.observation(base), 'Ineffective retail alias')
            self.assertTrue(state(retail) == state(candidate))
            type(self).alias_pairs += 1
            if name not in layout.source.MATCHED_HOMES and name != 'actionRow':
                old = guest.TickOracle(self.baseline, memory, phase, **options)
                try:
                    old.run()
                except AssertionError as error:
                    self.assertIn('unmapped', str(error))
                else:
                    self.assertTrue(homes.observation(old) != homes.observation(retail),
                                    'Ineffective wrong-layout control')
                self.assertGreater(old.provider.occurrences.get(target, 0), 0)
                type(self).alias_negatives += 1

    def test_cached_timer_alias_now_matches_literal_retail(self):
        for phase in (0, 8):
            memory = guest.fixture(category=0xB9, action=5, seed=0)
            guest.put(memory, guest.STATE + 0x29C, 5)
            guest.put(memory, guest.ALT_STATE + 0x29C, 19)
            options = dict(actions={(guest.STATUS, 0):
                ((guest.STACK + phase - 288 + 0xC4, guest.ALT_STATE + 0x29C, 4),)})
            a, b = (LiteralOracle(w, memory, phase, **options).run() for w in (self.retail, self.words))
            self.assertGreater(a.provider.occurrences.get(guest.STATUS, 0), 0)
            self.assertIn((guest.STATE + 0x29C, 4, 0), a.stores)
            self.assertTrue(state(a) == state(b))
            old = guest.TickOracle(self.baseline, memory, phase, **options).run()
            self.assertTrue(homes.observation(old) != homes.observation(a))

    def test_every_requested_access_cut_fires_with_equal_prefix_state(self):
        cases = [guest.fixture(count=0, category=0xB7),
                 guest.fixture(count=1, category=0xB7, action=5, seed=0),
                 guest.fixture(count=1, category=0xB9, action=5, seed=2)]
        for memory, phase in itertools.product(cases, (0, 8)):
            completed = LiteralOracle(self.retail, memory, phase).run()
            for cut in range(completed.accesses):
                pair = []
                for words in (self.retail, self.words):
                    model = LiteralOracle(words, memory, phase)
                    model.fault = cut
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    pair.append(model)
                self.assertTrue(state(pair[0]) == state(pair[1]), 'Access-cut prefix state differs')
                type(self).cut_pairs += 1

    def test_original_assembly_and_three_independent_GNU_symbol_maps(self):
        original = original_function((self.root / 'conker/asm/B3020.s').read_text(), 'func_1508A6FC')
        obj = assemble(self.root, self.output, 'original', original)
        self.assertEqual(layout.source.prior.prior.prior.payload(obj), (self.normalized, self.moved))
        lines = ['.globl func_1508A6FC', '.type func_1508A6FC,@function', 'func_1508A6FC:']
        for i, word in enumerate(struct.unpack('>678I', self.normalized)):
            label = '.Ltick_word_%d' % i
            lines.extend((label + ':', '.word 0x%08X' % word))
            for kind, name in self.moved.get(i * 4, ()):
                lines.append('.reloc ' + label + ',' + kind + ',' + name)
        normal = assemble(self.root, self.output, 'normalized', '\n'.join(lines) + '\n')
        base = layout.anchors(self.bindings)
        fields = {name: value for name, value in vars(guest).items() if name.isupper() and isinstance(value, int)}
        mapping = {key: next((name for name, value in base.items() if value == address), None)
                   for key, address in fields.items()}
        mapping = {key: name for key, name in mapping.items() if name}
        for phase in range(3):
            anchors = dict(base)
            if phase:
                for i, name in enumerate(sorted(anchors)):
                    anchors[name] = (0x16000000 + phase * 0x100000 + i * 0x10000 if name.startswith('func_')
                                     else 0x71000000 + phase * 0x1000000 + i * 0x100000 +
                                     (0x7FFC if phase == 1 else 0x8000))
            images = [link_map(self.output, '%s-map-%d' % (label, phase), image, anchors)
                      for label, image in (('original', obj), ('normalized', normal), ('raw', self.output / 'selected.o'))]
            self.assertEqual(images[0], images[1])
            self.assertEqual(layout.relocate(self.normalized, self.moved, anchors), images[0])
            self.assertEqual(layout.relocate(self.raw, self.bindings, anchors), images[2])
            rebased = {key: anchors[name] for key, name in mapping.items()}
            rebased['ARITY'] = {anchors[next(name for name, value in base.items() if value == target)]: count
                                for target, count in guest.ARITY.items()}
            with patch.multiple(guest, **rebased):
                for seed in (0, 1, 2):
                    memory = guest.fixture(category=0xB9, action=5, seed=seed)
                    models = [LiteralOracle(w, memory).run() for w in images]
                    self.assertTrue(state(models[0]) == state(models[1]))
                    self.assertTrue(homes.observation(models[0]) == homes.observation(models[2]))
                    type(self).gnu_runs += 3


if __name__ == '__main__':
    unittest.main()
