"""Bounded correction-loop layout, source effects, fired cuts and GNU rebases."""
from collections import Counter
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_actor_update_prefix_layout as layout
from tools.experiments import game_route_actor_update_native as native
from tools.tests import test_game_route_actor_update as guest


class PrefixStop(Exception):
    pass


class PrefixCode(guest.base.faults.TrackedCode):
    def __getitem__(self, pc):
        if pc in self.owner.exit_addresses:
            self.owner.stopped = (pc - guest.ENTRY) // 4
            self.owner.current_pc, self.owner.delay_of = pc, None
            raise PrefixStop
        return super().__getitem__(pc)


class PrefixOracle(guest.UpdateOracle):
    def __init__(self, words, memory, args, helpers, phase=0, effect=0, raw=False):
        super().__init__(words[:layout.WORDS], memory, args, phase, helpers, effect)
        indices = layout.EXITS if raw else layout.EXITS.values()
        self.exit_addresses = {guest.ENTRY + i * 4 for i in indices}
        self.code = PrefixCode(dict(self.code), self)
        self.caller_accesses, self.caller_fault, self.stopped = 0, None, None

    def access(self):
        if self.own_instruction and guest.ENTRY <= self.current_pc < guest.ENTRY + layout.WORDS * 4:
            if self.caller_accesses == self.caller_fault:
                raise guest.base.faults.AccessBoundary
            self.caller_accesses += 1
        super().access()

    def bounded(self):
        try:
            self.run()
        except PrefixStop:
            return self
        raise AssertionError('Prefix returned without its explicit exit gate')


def state(model):
    return (model.memory, model.r, model.f, model.events, model.calls, model.provider_calls,
        model.current_pc, model.delay_of, model.lo, model.condition, model.caller_accesses)


class RouteActorUpdatePrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / layout.BUILD
        cls.values = layout.source.source.freeze(cls.root, cls.out)
        obj, cls.raw_words, cls.row = layout.source.qualify(cls.root, cls.root / layout.source.BUILD)
        cls.raw, cls.bindings = layout.source.checked(obj)
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.anchors = {name: int(name.rsplit('_', 1)[1], 16) if name != 'bcopy' else guest.COPY
            for entries in cls.moved.values() for _, name in entries}
        cls.words = layout.relocate(cls.normalized, cls.moved, cls.anchors)
        cls.retail = list(struct.unpack_from('>604I', cls.values['conker/conker.us.bin'], guest.ROM))
        cls.helpers = {}
        for address, count in guest.HELPERS.items():
            at = layout.source.source.prior.elf_slot_offset(cls.values['conker/build/conker.us.elf'], address, count * 4)
            words = list(struct.unpack_from('>%dI' % count, cls.values['conker/build/conker.us.elf'], at))
            if words != list(struct.unpack_from('>%dI' % count, cls.values['conker/conker.us.bin'], address - 0x14FD2B50)):
                raise ValueError('Changed real helper in prefix qualification')
            cls.helpers.update(zip(range(address, address + count * 4, 4), words))
        cls.constants = native.static_constants(cls.root)

    def receipt(self, name, **values):
        values.update(raw_SHA256=layout.source.RAW_SHA, normalized_prefix_SHA256=layout.NORMALIZED_SHA,
            prefix_words=layout.WORDS, full_function_words=604, installed=False, matching_credit=0)
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def models(self, memory, args, phase=0, effect=0):
        return [PrefixOracle(w, memory, args, self.helpers, phase, effect, raw=raw)
            for w, raw in ((self.retail, False), (self.words, False), (self.raw_words, True))]

    def compare(self, memory, args, phase=0, effect=0):
        pair = [m.bounded() for m in self.models(memory, args, phase, effect)]
        self.assertEqual(state(pair[0]), state(pair[1]))
        self.assertEqual(layout.EXITS[pair[2].stopped], pair[0].stopped)
        self.assertEqual(guest.public(pair[0].memory), guest.public(pair[2].memory))
        self.assertEqual(pair[0].calls, pair[2].calls)
        self.assertEqual(pair[0].provider_calls, pair[2].provider_calls)
        frame = guest.STACK + phase - 456
        if guest.read(memory, guest.TABLE):
            self.assertEqual(guest.read(pair[0].memory, frame + 0x68), guest.read(pair[2].memory, frame + 0x54))
            for offset in (0x15C, 0x19C, 0x1A0, 0x1AC, 0x1B0, 0x1B4, 0x1B8, 0x1BC):
                self.assertEqual(guest.read(pair[0].memory, frame + offset), guest.read(pair[2].memory, frame + offset))
            self.assertEqual(guest.read(pair[0].memory, frame + 0x1A8), guest.read(pair[2].memory, frame + 0x160))
        return pair

    def test_01_all_244_words_from_closed_source_recipe(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('No file or retail input in normalizer')):
            raw, moved = layout.normalize(self.raw, self.bindings)
        self.assertEqual(layout.relocate(raw, moved, self.anchors), self.retail[:layout.WORDS])
        self.assertEqual(sorted(layout.origins()), list(range(layout.WORDS)))
        self.assertEqual(len(moved), 20)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['neighbors']),
            (594, 456, 450, 72))
        self.assertEqual(len(self.words), 244)
        self.receipt('literal-prefix', differences=0, origin_permutation=244, scheduling_NOP_replaced_by_error_copy=1,
            scalar_home_changes=3, integer_commutative_address_sum=1, bindings=20,
            no_float_arithmetic_reassociation=True, executable_tail_not_emitted=True)

    def test_02_same_connected_corpus_stops_before_every_unqualified_exit(self):
        exits, reached = Counter(), set()
        for row in native.cases():
            memory, args = native.fixture(row, self.constants)
            models = self.compare(memory, args, effect=row.get('effect', 0))
            exits[models[0].stopped] += 1
            reached.update(models[0].visits)
        self.assertEqual(sum(exits.values()), 553)
        self.assertEqual(set(exits), {244, 380, 593})
        for phase, index in itertools.product((0, 8), (0, 0xFFFFFFFF, 0x80000000)):
            memory, args = native.fixture({}, self.constants)
            guest.put(memory, guest.TABLE, 0)
            models = self.compare(memory, (index, *args[1:]), phase)
            self.assertEqual(models[0].stopped, 593)
        for phase, limit in itertools.product((0, 8), (-4., 4.)):
            memory, args = native.fixture(dict(mode=1), self.constants)
            guest.put(memory, guest.RECORDS + 4, guest.bits(limit))
            models = self.compare(memory, args, phase)
            reached.update(models[0].visits)
        self.assertTrue({guest.ENTRY + i * 4 for i in (66, 72, 73)} <= reached)
        self.assertEqual([i for i in range(layout.WORDS) if guest.ENTRY + i * 4 not in reached], [54])
        self.receipt('connected-prefix', existing_corpus_cases=553, null_table_cases=6,
            additional_upper_and_lower_clamp_cases=4,
            exit_counts=dict(exits), real_helper_words=len(self.helpers),
            reached_prefix_words=len({at for at in reached if guest.ENTRY <= at < guest.ENTRY + layout.WORDS * 4}),
            unreached_prefix_indices=[i for i in range(layout.WORDS) if guest.ENTRY + i * 4 not in reached],
            source_public_and_actual_helper_calls_equal=True, raw_private_register_parity_not_claimed=True)

    def test_03_fired_caller_access_prefixes_include_the_old_cut14_failure(self):
        cuts = old_rejects = 0
        for phase, row in itertools.product((0, 8), ({'mode': 0}, {'mode': 1},
                {'mode': 2, 'position': (-300., 100.)})):
            memory, args = native.fixture(row, self.constants)
            complete = self.models(memory, args, phase)[0].bounded()
            for cut in range(complete.caller_accesses):
                pair = self.models(memory, args, phase)[:2]
                for model in pair:
                    model.caller_fault = cut
                    with self.assertRaises(guest.base.faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.caller_accesses, cut)
                    self.assertIsNone(model.stopped)
                self.assertEqual(state(pair[0]), state(pair[1]))
                cuts += 1
            old = self.models(memory, args, phase)[2]
            old.caller_fault = 14
            with self.assertRaises(guest.base.faults.AccessBoundary):
                old.run()
            retail = self.models(memory, args, phase)[0]
            retail.caller_fault = 14
            with self.assertRaises(guest.base.faults.AccessBoundary):
                retail.run()
            self.assertNotEqual(state(old), state(retail))
            old_rejects += 1
        self.receipt('caller-cuts', fired_cuts=cuts, equal_states=cuts, raw_cut14_rejections=old_rejects,
            both_stack_phases=True, complete_memory_and_registers_and_calls_and_PC_compared=True,
            stops_before_unqualified_tail=True, hardware_FCSR_and_arbitrary_aliases_not_claimed=True)

    def test_04_each_raw_word_binding_and_register_recipe_is_guarded(self):
        for index in range(594):
            damaged = bytearray(self.raw)
            damaged[4 * index] ^= 1
            with self.assertRaises(ValueError):
                layout.normalize(damaged, self.bindings)
        for at in self.bindings:
            damaged = dict(self.bindings)
            damaged.pop(at)
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, damaged)
        controls = 0
        for table in (layout.GP, layout.FP):
            for index, rename in table.items():
                changed = dict(rename)
                changed[next(iter(changed))] ^= 1
                with patch.dict(table, {index: changed}), self.assertRaises(ValueError):
                    layout.normalize(self.raw, self.bindings)
                controls += 1
        self.receipt('closed-controls', raw_word_controls=594, binding_controls=70, register_recipe_controls=controls)

    def test_05_independent_GNU_relocations_include_carry_boundaries(self):
        locations = {}
        for hi, lo, name in ((13, 14, 'D_800872A0'), (24, 25, 'D_800CC2D0'), (38, 42, 'D_800D2390'),
                (43, 56, 'D_8009D9E0'), (60, 67, 'D_8009D9E4'), (77, 78, 'D_8009D9E8'), (214, 216, 'D_800BE9E4')):
            locations[hi], locations[lo] = ('R_MIPS_HI16', name), ('R_MIPS_LO16', name)
        for index, name in ((89, 'func_15088F30'), (107, 'func_150498A4'), (113, 'func_150498A4'),
                (196, 'func_15088A08'), (210, 'func_15042D78'), (242, 'bcopy')):
            locations[index] = ('R_MIPS_26', name)
        self.assertEqual({i * 4: [v] for i, v in locations.items()}, self.moved)
        lines = ['.set noreorder', '.text', '.globl prefix', '.type prefix,@function', 'prefix:']
        for index, word in enumerate(self.retail[:layout.WORDS]):
            if index in locations:
                kind, name = locations[index]
                mask = 0x3FFFFFF if kind == 'R_MIPS_26' else 65535
                lines.extend(['.word 0x%08X' % (word & ~mask), '.reloc .-4,%s,%s' % (kind, name)])
            else:
                lines.append('.word 0x%08X' % word)
        lines.append('.size prefix,.-prefix')
        unit, obj = self.out / 'independent.s', self.out / 'independent.o'
        unit.write_text('\n'.join(lines) + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(unit)],
            check=True, capture_output=True)
        maps = [self.anchors]
        for base in (0x80000000, 0):
            anchors = dict(self.anchors)
            for j, name in enumerate(sorted({name for kind, name in locations.values() if kind != 'R_MIPS_26'})):
                anchors[name] = base + (j + 1) * 0x10000 + (0x7FFC, 0x8000, 0x8004)[j % 3]
            for j, name in enumerate(sorted({name for kind, name in locations.values() if kind == 'R_MIPS_26'})):
                anchors[name] = 0x15300000 + j * 0x10000
            maps.append(anchors)
        script = self.out / 'independent.ld'
        script.write_text('SECTIONS { .text 0x15087350 : { *(.text) } }\n')
        for index, anchors in enumerate(maps):
            elf, binary = self.out / ('rebase%d.elf' % index), self.out / ('rebase%d.bin' % index)
            subprocess.run(['mips-linux-gnu-ld', '-T', str(script), '-e', 'prefix',
                *['--defsym=%s=0x%X' % item for item in sorted(anchors.items())], '-o', str(elf), str(obj)],
                check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-objcopy', '-O', 'binary', '--only-section=.text', str(elf), str(binary)],
                check=True, capture_output=True)
            actual = list(struct.unpack('>244I', binary.read_bytes()))
            self.assertEqual(actual, layout.relocate(self.normalized, self.moved, anchors))
        self.receipt('GNU-rebases', independent_GNU_maps=3, original_and_two_complete_rebases=True,
            distinct_data_HI_LO_carries=True, all_six_calls_relocated=True, rebased_runtime_not_claimed=True)

    def test_06_effective_error_copy_and_home_negatives(self):
        for index, word, position in ((152, 0, (-300., 100.)),
                (211, self.words[211] & 0xFFFF0000 | 0x160, (20., 10.))):
            memory, args = native.fixture(dict(mode=1, position=position), self.constants)
            expected = self.models(memory, args)[0].bounded()
            self.assertEqual(sum(target == guest.ADVANCE for target, _ in expected.calls), 11 if index == 152 else 0)
            changed = list(self.words)
            changed[index] = word
            actual = PrefixOracle(changed, memory, args, self.helpers).bounded()
            self.assertTrue(guest.public(expected.memory) != guest.public(actual.memory),
                'Emitted error control did not change public memory at word %d' % index)
        self.receipt('semantic-controls', effective_emitted_word_negatives=2,
            wrong_error_copy_and_call_save_detected_by_public_memory=True)

    def test_07_all_production_inputs_still_frozen(self):
        layout.source.source.freeze(self.root, self.out)
        owner = self.values['conker/src/game/generated_B3020.c'].decode()
        lo, hi = layout.source.source.function_span(owner, layout.source.source.FUNCTION)
        self.assertEqual(owner[lo:hi], 's32 func_15087350() {\n    return 0;\n}')
        old = self.root / layout.source.BUILD / 'native'
        receipt = json.loads((old / 'native32.json').read_text())
        self.assertEqual(receipt['raw_target_SHA256'], layout.source.RAW_SHA)
        self.assertEqual(receipt['cases_per_positive_build'], 553)
        text = (old / 'native-O2.c').read_text()
        a, b = native.function_span(text, layout.source.source.FUNCTION)
        body = native.strip_externs(layout.source.selected())
        lo, hi = native.function_span(body, layout.source.source.FUNCTION)
        self.assertEqual(text[a:b], body[lo:hi])
        self.receipt('frozen', protected_inputs=len(self.values), original_stub_and_counts_unchanged=True,
            source_native_qualification_reused_not_rerun=True, no_production_build_or_capture=True)


if __name__ == '__main__':
    unittest.main()
