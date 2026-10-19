"""Core operation provenance, real casts/spills, bounded guests and independent links."""
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_actor_update_core_layout as layout
from tools.experiments import game_route_actor_update_native as native
from tools.tests import test_game_route_actor_update as guest
from tools.tests import test_game_route_actor_update_prefix_layout as previous


class RouteActorUpdateCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        context = patch.object(previous, 'layout', layout)
        context.start()
        cls.addClassCleanup(context.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / layout.BUILD
        cls.values = layout.source.source.freeze(cls.root, cls.out)
        obj, cls.raw_words, cls.row = layout.source.qualify(cls.root, cls.root / layout.source.BUILD)
        cls.raw, cls.bindings = layout.source.checked(obj)
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        aliases = dict(bcopy=guest.COPY, sinf=guest.SIN, cosf=guest.COS)
        cls.anchors = {name: aliases[name] if name in aliases else int(name.rsplit('_', 1)[1], 16)
            for entries in cls.moved.values() for _, name in entries}
        cls.words = layout.relocate(cls.normalized, cls.moved, cls.anchors)
        cls.retail = list(struct.unpack_from('>604I', cls.values['conker/conker.us.bin'], guest.ROM))
        cls.helpers = {}
        for address, count in guest.HELPERS.items():
            at = layout.source.source.prior.elf_slot_offset(cls.values['conker/build/conker.us.elf'], address, count * 4)
            words = list(struct.unpack_from('>%dI' % count, cls.values['conker/build/conker.us.elf'], at))
            if words != list(struct.unpack_from('>%dI' % count, cls.values['conker/conker.us.bin'], address - 0x14FD2B50)):
                raise ValueError('Changed real helper in core qualification')
            cls.helpers.update(zip(range(address, address + count * 4, 4), words))
        cls.constants = native.static_constants(cls.root)

    def receipt(self, name, **values):
        values.update(raw_SHA256=layout.source.RAW_SHA, normalized_core_SHA256=layout.NORMALIZED_SHA,
            core_words=490, full_function_words=604, installed=False, matching_credit=0)
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def model(self, words, memory, args, phase=0, effect=0, raw=False):
        return previous.PrefixOracle(words, memory, args, self.helpers, phase, effect, raw)

    def compare(self, memory, args, phase=0, effect=0):
        models = [self.model(words, memory, args, phase, effect, raw).bounded()
            for words, raw in ((self.retail, False), (self.words, False), (self.raw_words, True))]
        self.assertEqual(previous.state(models[0]), previous.state(models[1]))
        self.assertEqual(layout.EXITS[models[2].stopped], models[0].stopped)
        self.assertTrue(guest.public(models[0].memory) == guest.public(models[2].memory), 'Raw/core public effects differ')
        self.assertEqual(models[0].calls, models[2].calls)
        self.assertEqual(models[0].provider_calls, models[2].provider_calls)
        if guest.ENTRY + 401 * 4 in models[0].visits:
            frame = guest.STACK + phase - 456
            self.assertEqual(guest.read(models[0].memory, frame + 0x1C0), models[2].f[22])
        return models

    def test_01_closed_490_word_core_and_operation_inventory(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Normalizer must not read files')):
            normalized, moved = layout.normalize(self.raw, self.bindings)
        self.assertEqual(layout.relocate(normalized, moved, self.anchors), self.retail[:490])
        order = layout.origins()
        originals = Counter(value for value in order if isinstance(value, int))
        self.assertEqual(set(range(244, 481)) - set(originals), {285, 391, 440, 459})
        self.assertEqual({i: n for i, n in originals.items() if n != 1}, {312: 2, 444: 2})
        self.assertEqual(Counter(value[0] for value in order if not isinstance(value, int)),
            Counter({'cast-store': 3, 'cast-load': 3, 'start-z-save': 1, 'start-z-load': 1, 'hazard': 3}))
        for i in (419, 435, 443):
            self.assertEqual(self.words[i], 0)
            for j in (i - 1, i + 1):
                self.assertEqual((self.words[j] >> 26, self.words[j] >> 21 & 31, self.words[j] & 63), (17, 16, 2))
        self.assertEqual((len(moved), sum(e[0][0] == 'R_MIPS_26' for e in moved.values())), (60, 20))
        first, earlier = layout.prefix.normalize(self.raw, self.bindings)
        self.assertEqual(normalized[:len(first)], first)
        self.assertEqual({i: v for i, v in moved.items() if i < 976}, earlier)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['neighbors']),
            (594, 456, 450, 72))
        self.receipt('literal-core', literal_differences=0, bindings=60, calls=20, earlier244_unchanged=True,
            three_real_cast_spill_pairs=True, startZ_save_and_reload=True,
            three_multiply_spacing_slots=True, branch_likely_and_mask_coalescing_explicit=True,
            two_finite_commutative_FP_sums=True, no_reassociation=True, ranking_return_not_emitted=True)

    def test_02_connected_corpus_and_both_phase_boundary_witnesses(self):
        reached, exits, cases = set(), Counter(), 0
        for row in native.cases():
            memory, args = native.fixture(row, self.constants)
            models = self.compare(memory, args, effect=row.get('effect', 0))
            exits[models[0].stopped] += 1
            reached.update(models[0].visits)
            cases += 1
        self.assertEqual(cases, 553)
        for phase, index in itertools.product((0, 8), (0, 0xFFFFFFFF, 0x80000000)):
            memory, args = native.fixture({}, self.constants)
            guest.put(memory, guest.TABLE, 0)
            self.assertEqual(self.compare(memory, (index, *args[1:]), phase)[0].stopped, 593)
        for phase, limit in itertools.product((0, 8), (-4., 4.)):
            memory, args = native.fixture(dict(mode=1), self.constants)
            guest.put(memory, guest.RECORDS + 4, guest.bits(limit))
            reached.update(self.compare(memory, args, phase)[0].visits)
        for mode, active, phase in itertools.product((0, 1, 2, 128), (0, 256), (0, 8)):
            memory, args = native.fixture(dict(mode=mode, active=active), self.constants)
            reached.update(self.compare(memory, args, phase, effect=5)[0].visits)
        for phase in (0, 8):
            memory, args = native.fixture(dict(mode=0), self.constants)
            for node, x in enumerate((-1, 0, 1, 0)):
                for slot, value in ((node, x), (128 + node, x + 1)):
                    guest.put(memory, guest.ROUTES + slot * 16, value & 65535, 2)
                    guest.put(memory, guest.ROUTES + slot * 16 + 4, 0, 2)
            models = self.compare(memory, args, phase)
            self.assertTrue(guest.ENTRY + 450 * 4 in models[0].visits, 'Unit-length projection branch did not fire')
            self.assertEqual(models[0].f[0], guest.bits(1.))
            self.assertEqual(guest.read(models[0].memory, guest.RECORDS), 0)
            reached.update(models[0].visits)
        self.assertEqual(set(exits), {490, 491, 593})
        self.assertEqual([i for i in range(490) if guest.ENTRY + i * 4 not in reached], [54])
        self.receipt('connected-core', existing_corpus_cases=553, extra_cases=28, total_bounded_cases=581,
            exit_counts=dict(exits), helper_words=len(self.helpers),
            visited_core_words=len({at for at in reached if guest.ENTRY <= at < guest.ENTRY + 490 * 4}),
            unvisited_core_indices=[i for i in range(490) if guest.ENTRY + i * 4 not in reached],
            raw_public_actual_args_calls_and_startZ_storage_equal=True,
            complete_normalized_retail_state_equal=True, arbitrary_aliases_and_FCSR_not_claimed=True)

    def test_03_every_fired_caller_cut_on_six_core_paths(self):
        cuts = 0
        for phase, row in itertools.product((0, 8), ({'mode': 0}, {'mode': 1},
                {'mode': 2, 'position': (-300., 100.)})):
            memory, args = native.fixture(row, self.constants)
            total = self.model(self.retail, memory, args, phase).bounded().caller_accesses
            for cut in range(total):
                models = [self.model(words, memory, args, phase) for words in (self.retail, self.words)]
                for model in models:
                    model.caller_fault = cut
                    with self.assertRaises(guest.base.faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.caller_accesses, cut)
                    self.assertIsNone(model.stopped)
                self.assertEqual(previous.state(models[0]), previous.state(models[1]))
                cuts += 1
        self.receipt('caller-cuts', fired_cuts=cuts, equal_complete_states=cuts, phases=2, paths_per_phase=3,
            rank_and_helper_internal_cuts_or_hardware_faults_not_claimed=True)

    def test_04_full_signed_cast_payloads_and_private_spill_accesses(self):
        count = 0
        for phase, value in itertools.product((0, 8), (-2147483648., -65536.75, -32769.5, -1.75,
                -0., 0., 32768.75, 65536.75, 2147483520.)):
            memory, args = native.fixture(dict(mode=1, active=0, position=(value, 0.)), self.constants)
            guest.put(memory, guest.ACTORS + 0x18, guest.bits(value))
            models = self.compare(memory, args, phase)
            frame = guest.STACK + phase - 456
            expected = []
            for address in (0x800D239C, 0x800D23A0, 0x800D23A4):
                number = guest.floating(guest.read(models[0].memory, address))
                self.assertTrue(math.isfinite(number) and -2147483648. <= number < 2147483648.)
                expected.append(math.trunc(number) & 0xFFFFFFFF)
            for model in models[:2]:
                accesses = [(kind, size, word) for kind, address, size, word in model.trace if address == frame + 0x48]
                self.assertEqual(accesses, [(kind, 4, word) for word in expected for kind in ('W', 'R')])
            count += 1
        self.receipt('coordinate-spills', wide_signed_cases=count, both_phases=True,
            all_three_full32_cast_words_and_six_stack_accesses_equal=True,
            no_short_cast_or_volatile_original_type_claim=True)

    def test_05_all_source_inputs_and_core_recipes_fail_closed(self):
        for i in range(594):
            changed = bytearray(self.raw)
            changed[4 * i] ^= 1
            with self.assertRaises(ValueError):
                layout.normalize(changed, self.bindings)
        for at in self.bindings:
            changed = dict(self.bindings)
            changed.pop(at)
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, changed)
        controls = 0
        for table in (layout.GP, layout.FP):
            for i, rename in table.items():
                changed = dict(rename)
                changed[next(iter(changed))] ^= 1
                with patch.dict(table, {i: changed}), self.assertRaises(ValueError):
                    layout.normalize(self.raw, self.bindings)
                controls += 1
        order = layout.origins()
        derived = [i for i, value in enumerate(order) if not isinstance(value, int)]
        for i in derived:
            changed = list(order)
            entry = list(changed[i])
            entry[1] += 1
            changed[i] = tuple(entry)
            with patch.object(layout, 'origins', return_value=changed), self.assertRaises(ValueError):
                layout.normalize(self.raw, self.bindings)
        self.receipt('closed-controls', raw_word_mutations=594, binding_removals=70,
            suffix_register_mutations=controls, derived_operation_mutations=len(derived))

    def test_06_independent_GNU_links_for_all_60_bindings(self):
        locations = {}
        pairs = ((13,14,'D_800872A0'),(24,25,'D_800CC2D0'),(38,42,'D_800D2390'),
            (43,56,'D_8009D9E0'),(60,67,'D_8009D9E4'),(77,78,'D_8009D9E8'),(214,216,'D_800BE9E4'),
            (259,260,'D_800D239C'),(266,267,'D_800D23A0'),(273,274,'D_800D2398'),(277,278,'D_800D23A4'),
            (283,286,'D_800CC310'),(287,288,'D_8009D9F0'),(313,316,'D_800D2104'),(319,356,'D_800D2390'),
            (430,431,'D_800D2398'),(451,452,'D_800D2398'),(456,458,'D_800D23A9'),
            (463,467,'D_800D18A0'),(472,474,'D_800BE9E4'))
        for hi, lo, name in pairs:
            locations[hi], locations[lo] = ('R_MIPS_HI16', name), ('R_MIPS_LO16', name)
        calls = ((89,'func_15088F30'),(107,'func_150498A4'),(113,'func_150498A4'),(196,'func_15088A08'),
            (210,'func_15042D78'),(242,'bcopy'),(248,'func_15088A08'),(253,'func_15088F30'),
            (257,'func_150497E0'),(264,'func_150497E0'),(271,'func_150497E0'),(292,'sinf'),(304,'cosf'),
            (385,'func_15088F30'),(389,'func_150497E0'),(394,'func_150497E0'),(403,'func_15088F30'),
            (407,'func_150497E0'),(413,'func_150497E0'),(488,'func_1508802C'))
        for i, name in calls:
            locations[i] = ('R_MIPS_26', name)
        self.assertEqual({i * 4: [entry] for i, entry in locations.items()}, self.moved)
        lines = ['.set noreorder','.text','.globl core','.type core,@function','core:']
        for i, word in enumerate(self.retail[:490]):
            if i in locations:
                kind, name = locations[i]
                mask = 0x3FFFFFF if kind == 'R_MIPS_26' else 65535
                lines += ['.word 0x%08X' % (word & ~mask), '.reloc .-4,%s,%s' % (kind, name)]
            else:
                lines.append('.word 0x%08X' % word)
        lines.append('.size core,.-core')
        unit, obj = self.out/'independent.s', self.out/'independent.o'
        unit.write_text('\n'.join(lines)+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(unit)], check=True,capture_output=True)
        maps = [self.anchors]
        for base in (0x80000000, 0):
            anchors = dict(self.anchors)
            for j, name in enumerate(sorted(name for name in anchors if name.startswith('D_'))):
                anchors[name] = base + (j+1)*0x10000 + (0x7FFC,0x8000,0x8004)[j%3]
            for j, name in enumerate(sorted({name for _,name in calls})):
                anchors[name] = 0x15300000 + j*0x10000
            maps.append(anchors)
        script = self.out/'independent.ld'
        script.write_text('SECTIONS { .text 0x15087350 : { *(.text) } }\n')
        for i, anchors in enumerate(maps):
            elf, binary = self.out/('map%d.elf'%i), self.out/('map%d.bin'%i)
            subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e','core',
                *['--defsym=%s=0x%X'%item for item in sorted(anchors.items())],'-o',str(elf),str(obj)],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-objcopy','-O','binary','--only-section=.text',str(elf),str(binary)],
                check=True,capture_output=True)
            data = binary.read_bytes()
            self.assertEqual(data[1960:], bytes(len(data)-1960))
            self.assertEqual(list(struct.unpack('>490I',data[:1960])),layout.relocate(self.normalized,self.moved,anchors))
        self.receipt('GNU-rebases', independent_maps=3, bindings=60, calls=20, distinct_HI_LO_carry_maps=2,
            rebased_runtime_and_actual_Make_padder_not_claimed=True)

    def test_07_effective_spill_negatives_and_all_byte_shift_values(self):
        for index, home, mode in ((349,0x4C,1),(415,0x1BC,0)):
            memory, args = native.fixture(dict(mode=mode, active=0), self.constants)
            expected = self.model(self.retail,memory,args).bounded()
            self.assertIn(guest.ENTRY+index*4, expected.visits)
            changed = list(self.words)
            changed[index] = changed[index]&0xFFFF0000 | home
            actual = self.model(changed,memory,args).bounded()
            self.assertTrue(guest.public(expected.memory)!=guest.public(actual.memory),
                'Spill control did not affect public memory at word %d' % index)
        memory,args = native.fixture({},self.constants)
        for byte in range(256):
            a = guest.UpdateOracle([0],memory,args)
            b = guest.UpdateOracle([0],memory,args)
            value = guest.signed(byte,8)&0xFFFFFFFF
            a.r[13],a.r[24] = value,1
            b.r[15],b.r[25] = value,1
            a.execute(self.raw_words[459]);a.execute(self.raw_words[460])
            b.execute(self.words[469])
            self.assertEqual(a.r[14],1<<(value&31))
            self.assertEqual(b.r[24],a.r[14])
        self.receipt('semantic-controls', effective_spill_controls=2, all256_signed_shift_bytes=256,
            direct_SLLV_matches_original_ANDI_SLLV=True, no_external_domain_narrowing=True)

    def test_08_frozen_inputs_and_old_source_native_receipts(self):
        layout.source.source.freeze(self.root,self.out)
        owner = self.values['conker/src/game/generated_B3020.c'].decode()
        lo,hi = layout.source.source.function_span(owner,layout.source.source.FUNCTION)
        self.assertEqual(owner[lo:hi],'s32 func_15087350() {\n    return 0;\n}')
        old = self.root/layout.source.BUILD/'native'
        record = json.loads((old/'native32.json').read_text())
        self.assertEqual(record['raw_target_SHA256'],layout.source.RAW_SHA)
        text = (old/'native-O2.c').read_text()
        a,b = native.function_span(text,layout.source.source.FUNCTION)
        body = native.strip_externs(layout.source.selected())
        lo,hi = native.function_span(body,layout.source.source.FUNCTION)
        self.assertEqual(text[a:b],body[lo:hi])
        self.receipt('frozen', protected_inputs=len(self.values), source_native_not_rerun=True,
            no_production_source_ELF_guards_counts_README_change=True, no_capture_or_installation=True)


if __name__ == '__main__':
    unittest.main()
