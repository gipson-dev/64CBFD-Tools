"""Qualify complete pair-mask C while keeping its private/layout mismatch explicit."""
from dataclasses import replace
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_pair_visibility_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_actor_pair_visibility_oracle as guest
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command
from tools.pad_generated_object import emit_padded_assembly, parse_object


def same_calls(a, b):
    if len(a) != len(b):
        return False
    for left, right in zip(a, b):
        if len(left) != len(right) or left[0] != right[0]:
            return False
        for i, (x, y) in enumerate(zip(left[1:], right[1:])):
            floating = left[0] == guest.BARRIER or left[0] == guest.QUERY and (i < 6 or i == 14)
            if x != y and not (floating and math.isnan(guest.floating(x)) and math.isnan(guest.floating(y))):
                return False
    return True


def public_stores(model):
    return [row for row in model.stores if not guest.STACK - 0x600 <= row[0] < guest.STACK + 0x100]


class ActorPairVisibilityRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD / 'recovery'
        cls.values = source.freeze(cls.root, cls.out)
        cls.obj, cls.words, cls.row = source.compile_candidate(cls.root, cls.out)
        cls.raw, cls.bindings = source.payload(cls.obj)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>261I', cls.rom, source.ROM))
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_complete_source_and_explicit_matching_boundary(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (261, 168, 225))
        self.assertFalse(self.row['diagnostics'])
        self.assertEqual(self.row['raw_SHA256'], '47c32436c59af38d13f62bf3a2e5ab11f07d3b25ad6b3b0fd33c378bf4c6de16')
        self.assertEqual(len(self.bindings), 16)
        self.assertEqual(self.words[:7], self.retail[:7])
        self.assertEqual((self.words[8], self.words[11]), (0xAFA000A0, 0xAFA000A4))
        self.assertEqual((-self.retail[0]) & 65535, 168)
        self.assertNotEqual(self.words, self.retail)
        self.assertIn('void func_1508C1A4(s32 first, s32 second)', source.SELECTED)
        self.assertNotIn('temp_v0', source.SELECTED)
        self.receipts.update(raw_words=261, raw_frame=168, raw_differences=225, retail_words=261,
            retail_frame=168, matching_credit=0, production_installed=False, raw_bindings=16,
            frame_RA_incoming_and_two_flag_homes_match=True)

    def test_02_public_reference_calls_mutations_and_live_context_alias(self):
        pairs, coverage = 0, set()
        for n, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            wanted, calls, stores, _ = guest.reference(memory, case)
            for phase in (0, 8):
                for words in (self.retail, self.words):
                    with self.subTest(case=n, phase=phase, retail=words is self.retail):
                        model = guest.PairModel(words, memory, case, phase).run()
                        self.assertTrue(same_calls(model.calls, calls), (model.calls, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(public_stores(model), stores)
                        if words is self.retail:
                            coverage.update(model.visits)
                pairs += 1
        unvisited = sorted(set(range(source.ENTRY, source.ENTRY + 1044, 4)) - coverage)
        self.receipts.update(fixtures=len(self.corpus), public_pairs=pairs, all256_signed_modes=True,
            all32_MIPS_shift_counts=True, complete_live_context_alias=True,
            retail_words_visited=len(coverage), unvisited_retail_words=[hex(a) for a in unvisited])

    def test_03_native32_buffers_calls_and_effective_negatives(self):
        def run(name, body, opt='-O2'):
            path, exe = self.out / (name + '.c'), self.out / name
            path.write_text(guest.native_harness(body, self.corpus))
            built = subprocess.run(native_command(opt) + ['-mstackrealign', '-fno-strict-aliasing', str(path), '-o', str(exe)],
                cwd=self.root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            return subprocess.run([str(exe)], capture_output=True, text=True)
        for opt in ('-O0', '-O2', '-O3'):
            result = run('native' + opt[1:], source.SELECTED, opt)
            self.assertEqual(result.returncode, 0, (opt, result.stdout, result.stderr))
        negatives = {
            'unmasked-key': source.SELECTED.replace('first & 0xFFFF0FFF', 'first').replace('second & 0xFFFF0FFF', 'second'),
            'unsigned-height': source.SELECTED.replace('(f32)*(s16 *)(nested + 0x114)', '(f32)*(u16 *)(nested + 0x114)'),
            'unsigned-coordinates': source.SELECTED.replace('(f32)*(s16 *)(actor +', '(f32)*(u16 *)(actor +'),
            'wrong-kind-mask': source.SELECTED.replace('& 0x7F', '& 0xFF'),
            'wrong-query-abi': source.SELECTED.replace('x, y, startZ, dx, dy, dz, 0, 0,', 'x, y, dx, startZ, dy, dz, 0, 0,'),
            'inclusive-hit': source.SELECTED.replace('distance < hitDistance', 'distance <= hitDistance'),
            'barrier-clears-both': source.SELECTED.replace('clear = 0;', 'clear = 0;\n                queryClear = 0;'),
            'barrier-zero-blocks': source.SELECTED.replace('> 0.0f', '>= 0.0f'),
            'cached-context': source.SELECTED.replace('    u32 *row;', '    u32 *row;\n    s32 context = D_800D23B0;').replace('(u8 *)D_800D23B0', '(u8 *)context'),
        }
        negatives = {name: body for name, body in negatives.items() if body != source.SELECTED}
        for name, body in negatives.items():
            result = run('negative-' + name, body)
            self.assertNotEqual(result.returncode, 0, name)
        self.receipts.update(native32_profiles=3, native32_UBSan=True, effective_native_negatives=len(negatives),
            native_complete_buffers_and_ordered_calls=True, NaN_results_compared_by_class=True)

    def test_04_fired_private_home_boundary_is_not_matching(self):
        case = guest.Case()
        for cut in range(40):
            models = []
            for words in (self.retail, self.words):
                model = guest.PairModel(words, guest.fixture(case), case)
                model.fault = cut
                with self.assertRaises(guest.core.AccessFault):
                    model.run()
                self.assertEqual(model.accesses, cut)
                models.append(model)
            self.assertEqual(guest.public(models[0].memory), guest.public(models[1].memory))
            self.assertEqual(models[0].r[29], models[1].r[29])
            if models[0].requested != models[1].requested:
                break
        else:
            self.fail('Expected a fired differing private scalar home')
        self.assertEqual(models[0].requested, ('W', guest.STACK - 168 + 0x64, 4))
        self.assertEqual(models[1].requested, ('W', guest.STACK - 168 + 0x80, 4))
        self.receipts.update(fired_private_home_cut=cut, retail_startZ_home='SP+0x64',
            raw_startZ_home='SP+0x80', private_matching=False, frame_and_RA_home_match=True,
            earlier_matching_memory_requests_do_not_imply_register_matching=True)

    def test_05_actual_lookup_and_restored_barrier(self):
        lookup = list(struct.unpack_from('>55I', self.rom, 0x8C3A4))
        self.assertEqual(lookup[-2:], [0x03E00008, 0])
        connected = {guest.LOOKUP + i * 4: w for i, w in enumerate(lookup)}
        # Use the actual fixed actor table and backed inactive records for its unrolled scan.
        regions = tuple((0x800CC2D0, 26 * 0x32C) if base == guest.ACTORS else (base, size) for base, size in guest.SEGMENTS)
        lookup_runs = 0
        with patch.multiple(guest, ACTORS=0x800CC2D0, SEGMENTS=regions):
            for case in (guest.Case(kinds=(1, 1)), guest.Case(kinds=(1, 31), active=(1, 0)),
                    guest.Case(kinds=(1, 1), first=7, second=8, found=(False, False))):
                memory = guest.fixture(case)
                for i in range(2, 26):
                    guest.put(memory, guest.ACTORS + i * 0x32C, 0, 4)
                for i in range(2):
                    guest.put(memory, guest.ACTORS + i * 0x32C + 0x13F, i, 1)
                wanted, calls, stores, _ = guest.reference(memory, case)
                for phase in (0, 8):
                    for words in (self.retail, self.words):
                        model = guest.PairModel(words, memory, case, phase, connected).run()
                        self.assertTrue(same_calls(model.calls, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(public_stores(model), stores)
                        self.assertEqual(model.lookup_ordinal, 0)
                        lookup_runs += 1
        barrier = struct.unpack_from('>207I', self.rom, 0xB4244)
        actual = {guest.BARRIER + i * 4: w for i, w in enumerate(barrier)}
        height = 0x15085DA8
        class Connected(guest.PairModel):
            def record_call(self, target):
                if target == height:
                    self.height_calls = getattr(self, 'height_calls', []) + [self.f[12]]
                else:
                    super().record_call(target)
            def hook(self, target):
                if target != height:
                    return super().hook(target)
                self.in_hook = True
                try:
                    for i in range(4):
                        self.put(self.r[29] + i * 4, 0xBA000000 + i, 4)
                    for reg in (1, 2, 3, *range(4, 16), 24, 25):
                        self.r[reg] = 0xA5000000 + reg
                    self.r[2] = 2
                    self.f[:20] = [0xA5000000 + i for i in range(20)]
                finally:
                    self.in_hook = False
        barrier_runs = 0
        for count in (0, 2):
            case = guest.Case(points=((50., 0., -10.), (50., 0., 10.)), barrier=10. if count else -1.)
            memory = guest.fixture(case)
            for i in range(32):
                memory[0x34000 + i] = 0xA5
            for a, value, size in ((0x800D2350, 0x34000, 4), (0x80087290, count, 2),
                    (0x34000, 0, 2), (0x34004, 0, 2), (0x34006, 2, 1), (0x3400E, 1, 1),
                    (0x34010, 100, 2), (0x34014, 0, 2), (0x3401E, 1, 1)):
                guest.put(memory, a, value, size)
            for i in range(5):
                guest.put(memory, 0x34009 + i, 1 if i == 0 else 255, 1)
            wanted, calls, stores, _ = guest.reference(memory, case)
            for phase in (0, 8):
                for words in (self.retail, self.words):
                    model = Connected(words, memory, case, phase, actual).run()
                    self.assertEqual(model.height_calls, [guest.bits(40.)])
                    self.assertTrue(same_calls(model.calls, calls))
                    self.assertEqual(guest.public(model.memory), guest.public(wanted))
                    self.assertEqual(public_stores(model), stores)
                    barrier_runs += 1
        self.receipts.update(actual_lookup_runs=lookup_runs, actual_lookup_words=55,
            actual_restored_barrier_runs=barrier_runs, actual_barrier_words=207, opaque_height_category=2,
            no_full_collision_provider_or_gameplay_claim=True)

    def test_06_independent_GNU_rebases(self):
        asm = self.values['conker/asm/B3020.s'].decode()
        lo = asm.index('glabel ' + source.FUNCTION + '\n')
        hi = asm.index('endlabel ' + source.FUNCTION, lo)
        retail = self.out / 'GNU-retail.s'
        retail.write_text((self.root / 'conker/include/asm_processor_prelude.inc').read_text() + '\n.text\n' + asm[lo:hi])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
            '-I', str(self.root / 'conker/include'), '-o', str(retail.with_suffix('.o')), str(retail)], check=True, capture_output=True)
        pairs = 0
        for n, (entry, delta) in enumerate(((source.ENTRY, 0), (0x1621FFF4, 0x115CAC), (0x18FFF000, 0x235CB0))):
            anchors = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
                for entries in self.bindings.values() for _, name in entries}
            images = []
            for obj, count in ((retail.with_suffix('.o'), 261), (self.obj, 261)):
                script = self.out / (obj.stem + '-GNU-%d.ld' % n)
                elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % (name, value + delta) for name, value in anchors.items()], '-o', str(elf), str(obj)],
                    check=True, capture_output=True)
                images.append(list(struct.unpack_from('>%dI' % count, sections(elf)['.text'][1])))
            moved = {name: getattr(guest, name) + delta for name in ('CONTEXT', 'MODE', 'TABLE', 'LOOKUP', 'QUERY', 'BARRIER', 'ACTORS', 'NESTED', 'ALIAS')}
            moved['BANKS'] = tuple(base + delta for base in guest.BANKS)
            moved['SEGMENTS'] = tuple((base + delta, size) for base, size in guest.SEGMENTS)
            with patch.multiple(guest, **moved):
                for case in self.corpus[::37]:
                    memory = guest.fixture(case)
                    wanted, calls, stores, _ = guest.reference(memory, case)
                    for words in images:
                        model = guest.PairModel(words, memory, case, entry=entry).run()
                        self.assertTrue(same_calls(model.calls, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(public_stores(model), stores)
                    pairs += 1
        self.receipts.update(independent_GNU_maps=3, rebased_public_pairs=pairs,
            raw_source_and_original_assembly_linked_independently=True, literal_rebase_matching=False)

    def test_07_owner_profiles_actual_padding_and_unchanged_inputs(self):
        out = self.out / 'owner'
        values = source.freeze(self.root, out)
        same = mixed.candidate.source.neighbor.same_functions
        for normal in (False, True):
            label = 'normal' if normal else 'primary'
            before, diagnostics = source.compile_profile(self.root, out, values[source.SOURCE].decode(), 'before-' + label, normal)
            after, _, row = source.compile_candidate(self.root, out, 'after-' + label, normal=normal, whole=True)
            self.assertFalse(diagnostics)
            self.assertFalse(row['diagnostics'])
            self.assertEqual((row['words'], row['frame'], row['differences']), (261, 168, 225))
            self.assertEqual(same(before, after, (source.FUNCTION,)), 72)
            self.assertEqual(normalized_pools(before), normalized_pools(after))
        asm = out / 'qualified-padded.s'
        overrides = ('func_150891E8', 'func_1508BC20', 'func_15089BC0')
        asm.write_text(emit_padded_assembly(out / 'after-primary.o', self.root / 'conker/asm/B3020.s',
            function_objects={n: out / 'after-normal.o' for n in overrides},
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename=source.OWNER))
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
            '-I', str(self.root / 'conker/include'), '-o', str(obj), str(asm)], check=True, capture_output=True)
        baseline = self.root / 'conker/build/src/game/generated_B3020.c.o'
        self.assertEqual(same(baseline, obj, (source.FUNCTION,)), 72)
        a, fa = source.link_owner(self.root, out, baseline, source.OWNER)
        b, fb = source.link_owner(self.root, out, obj, source.OWNER)
        at = fa[source.FUNCTION]['value']
        self.assertEqual(a[:at], b[:at])
        self.assertEqual(a[at + 1044:], b[at + 1044:])
        self.assertEqual(fa.keys(), fb.keys())
        self.assertTrue(all(fa[n]['value'] == fb[n]['value'] for n in fa))
        self.assertEqual(normalized_pools(baseline), normalized_pools(obj))
        self.assertNotEqual(b[at:at + 1044], self.rom[source.ROM:source.ROM + 1044])
        (out / 'proposed-owner.c').write_text(source.recovered_owner(values[source.SOURCE].decode()))
        (out / 'qualified-guards.csv').write_bytes(values['conker/retail_word_patches.us.csv'])
        shutil.copyfile(out / 'after-normal.o', out / 'override-normal.o')
        shutil.copyfile(out / 'after-primary.o', out / 'primary-no-unroll.o')
        with patch.multiple(mixed, freeze=source.freeze, recovered_owner=source.recovered_owner,
                recovered_makefile=lambda before: before, recovered_guards=lambda before, *unused: before):
            shadow = mixed.make_shadow(self.root, out)
        actual = out / 'make-shadow/src/game/generated_B3020.c.o.normal.compact'
        self.assertEqual(source.payload(actual), source.payload(out / 'after-normal.o'))
        self.assertTrue(shadow['padded_code_and_metadata_equal'])
        for name, value in values.items():
            self.assertEqual((self.root / name).read_bytes(), value, name)
        self.receipts.update(owner_profiles=2, raw_and_padded_neighbors_fixed=72,
            all73_owner_addresses_fixed=True, all_existing_pools_fixed=True,
            production_inputs_unchanged=True, no_new_guards_or_profile_change=True,
            actual_expanded_Make_commands=7, actual_Make_padded_bytes_and_metadata_equal=True)

    def test_08_actual_caller_windows_and_fired_return_stops(self):
        class Returned(Exception):
            pass
        class StopWords(dict):
            def __getitem__(self, pc):
                if pc == self.stop:
                    raise Returned()
                return super().__getitem__(pc)
        runs = 0
        for entry, stop in ((0x1508C7CC, 0x1508C7E4), (0x1508C950, 0x1508C958)):
            prefix = struct.unpack_from('>%dI' % ((stop - entry) // 4), self.rom, entry - 0x15000000 + 0x2D4B0)
            connected = {entry + i * 4: word for i, word in enumerate(prefix)}
            connected[stop] = struct.unpack_from('>I', self.rom, stop - 0x15000000 + 0x2D4B0)[0]
            for case in (guest.Case(), guest.Case(query=1, hit=0.), guest.Case(barrier=1.), guest.Case(found=(False, True))):
                memory = guest.fixture(case)
                expected = memory.copy()
                before_stores = []
                row = guest.bank(case) + case.second * 4 + 0x16C0
                original = guest.read(memory, row, 4)
                keep = ~(0x10001 << case.first) & 0xFFFFFFFF
                if entry == 0x1508C7CC:
                    guest.put(expected, row, original & keep, 4)
                    before_stores = [(row, 4, original & keep)]
                wanted, calls, stores, _ = guest.reference(expected, case)
                for phase in (0, 8):
                    for words in (self.retail, self.words):
                        model = guest.PairModel(words, memory, case, phase, connected)
                        model.entry = entry
                        model.r[3], model.r[6], model.r[15], model.r[24] = row - 0x16C0, case.second, original, keep
                        model.r[16], model.r[20] = 0x35000, case.first
                        saved = {r: model.r[r] for r in (*range(16, 24), 28, 29, 30)}
                        model.code = StopWords(model.code)
                        model.code.stop = stop
                        with self.assertRaises(Returned):
                            model.run()
                        self.assertIn(stop, model.visits)
                        self.assertEqual(model.caller_args, [(case.first, case.second)])
                        self.assertTrue(same_calls(model.calls, calls))
                        self.assertEqual(guest.public(model.memory), guest.public(wanted))
                        self.assertEqual(public_stores(model), before_stores + stores)
                        for reg, value in saved.items():
                            self.assertEqual(model.r[reg], value + (1 if entry == 0x1508C7CC and reg == 16 else 0))
                        self.assertEqual(model.f[20:], model.saved_f)
                        runs += 1
        self.receipts.update(actual_returning_caller_runs=runs,
            actual_caller_stops=['1508C7E4', '1508C958'], every_caller_stop_fired=True,
            first_caller_delay_store_executed=True, no_full_pair_scheduler_claim=True)


if __name__ == '__main__':
    unittest.main()
