"""Mask/dataflow proof, literal private/fault/rebase checks and current callback chain."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_color_fade_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_record_color_fade as prior
from tools.tests import test_game_record_fade_callback as fade
from tools.tests import test_game_packed_record_updater as updater


def expression(op, *args):
    if op == 'and' and args[1] == 0xFFFFFFFF:
        return args[0]
    if op == 'or' and args[1] == 0:
        return args[0]
    if all(isinstance(a, int) for a in args):
        a, b = args
        return {'add': lambda: a + b, 'sub': lambda: a - b, 'and': lambda: a & b,
            'or': lambda: a | b, 'shl': lambda: a << b,
            'ashr': lambda: fade.signed(a) >> b}[op]() & 0xFFFFFFFF
    return (op, *args)


def disjoint(a, size_a, b, size_b):
    if isinstance(a, int) and isinstance(b, int):
        return not ({(a + i) & 0xFFFFFFFF for i in range(size_a)} & {(b + i) & 0xFFFFFFFF for i in range(size_b)})
    if isinstance(a, tuple) and isinstance(b, tuple) and a[:2] == b[:2] and a[0] == 'address':
        return a[2] + size_a <= b[2] or b[2] + size_b <= a[2]
    return False


def symbolic_paths(words, identities):
    """Compare every syntactic CFG path, including infeasible width combinations."""
    paths = {}

    def walk(pc, regs, lo, stores, branches):
        regs, stores = list(regs), list(stores)

        def execute(word):
            nonlocal lo
            op, rs, rt, rd = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            imm = fade.short(word)
            address = ((regs[rs] + imm) & 0xFFFFFFFF if isinstance(regs[rs], int) else ('address', regs[rs], imm))
            if op == 0:
                fn, shift = word & 63, word >> 6 & 31
                if fn in (0, 3):
                    regs[rd] = expression('shl' if fn == 0 else 'ashr', regs[rt], shift)
                elif fn == 4:
                    count = regs[rs]
                    if isinstance(count, tuple) and count[0] == 'and' and count[2] == 31:
                        count = count[1]
                    regs[rd] = expression('shl', regs[rt], ('low5', count))
                elif fn in (33, 35, 37):
                    regs[rd] = expression({33: 'add', 35: 'sub', 37: 'or'}[fn], regs[rs], regs[rt])
                elif fn == 25:
                    lo = ('multiply-low32', regs[rs], regs[rt])
                elif fn == 18:
                    regs[rd] = lo
                else:
                    raise AssertionError(('unsupported symbolic R', hex(word)))
            elif op == 9:
                regs[rt] = expression('add', regs[rs], imm)
            elif op == 10:
                regs[rt] = ('signed-lt', regs[rs], imm)
            elif op == 12:
                regs[rt] = expression('and', regs[rs], word & 65535)
            elif op == 15:
                regs[rt] = (word & 65535) << 16
            elif op in (32, 33, 35, 36):
                size = {32: 1, 33: 2, 35: 4, 36: 1}[op]
                relevant = tuple(s for s in stores if not disjoint(address, size, s[0], s[1]))
                regs[rt] = ('read', address, size, op in (32, 33), relevant)
            elif op in (40, 41):
                size = 1 if op == 40 else 2
                stores.append((address, size, expression('and', regs[rt], (1 << (size * 8)) - 1)))
            else:
                raise AssertionError(('unsupported symbolic op', hex(word)))
            regs[0] = 0

        while True:
            assert 0 <= pc < len(words) and len(branches) <= len(words), 'Invalid or cyclic proof CFG'
            word = words[pc]
            op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
            if op == 0 and word & 63 == 8:
                target = regs[rs]
                execute(words[pc + 1])
                key = tuple((i, taken) for i, _, taken in branches)
                result = (regs[2], tuple(regs[i] for i in (*range(16, 24), 28, 29, 30, 31)),
                    target, tuple(stores), tuple(branches))
                assert key not in paths
                paths[key] = result
                return
            if op in (1, 4, 5, 6, 7, 20, 21, 22, 23):
                kind = ('REGIMM', rt) if op == 1 else ('branch', op & 15)
                condition = (kind, regs[rs], regs[rt] if op in (4, 5, 20, 21) else 0)
                likely = rt in (2, 3) if op == 1 else op >= 20
                outcomes = (True,) if op == 4 and rs == rt == 0 else (False, True)
                for taken in outcomes:
                    saved_regs, saved_lo, saved_stores = list(regs), lo, list(stores)
                    if taken or not likely:
                        execute(words[pc + 1])
                    next_pc = pc + 1 + fade.short(word) if taken else pc + 2
                    walk(next_pc, regs, lo, stores, (*branches, (identities[pc], condition, taken)))
                    regs[:], lo, stores[:] = saved_regs, saved_lo, saved_stores
                return
            execute(word)
            pc += 1

    walk(0, [0, *(('input', i) for i in range(1, 32))], ('input-LO',), [], ())
    return paths


class ColorMatchCandidateTests(unittest.TestCase):
    def test_strict_shape_gate_and_REGIMM_branch_kind(self):
        for count, differences, frame, diagnostic in ((97, 89, 0, ''), (98, 88, 0, ''), (98, 89, 8, ''), (98, 89, 0, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count,
                    differences=differences, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'Unknown defined'):
                    source.qualify(Path('.'), Path('.'))
        self.assertEqual(source.registers(0x04630003, {2: 3, 3: 2}), 0x04430003)
        self.assertIn('& 31', source.SELECTED)
        self.assertEqual(source.SELECTED.split('s32 func_', 1)[1], prior.source.SELECTED.split('s32 func_', 1)[1])


class ColorFadeMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>97I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = prior.ColorFadeTests.test_08_all_original_801_archive_fingerprints

    def test_01_exact_padding_29_neighbors_and_all_raw_relocation_corruptions(self):
        self.assertEqual(self.words, self.truth)
        raw, rel = source.raw_target(self.obj)
        before, diagnostic = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        for i in range(98):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'Unknown color-fade'):
                source.normalize(bytes(bad), rel)
        for at in rel:
            bad = dict(rel)
            bad.pop(at)
            with self.assertRaisesRegex(ValueError, 'Unknown color-fade'):
                source.normalize(raw, bad)
        rows = list(csv.DictReader(io.StringIO((self.out / 'qualified-guards.csv').read_text())))
        rows = [row for row in rows if row['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 84)
        self.assertEqual([(r['offset'], r['omit']) for r in rows if r['omit'] == 'true'], [('0x60', 'true')])
        self.assertTrue(all(not r['insert_after'] for r in rows))
        self.receipt('owner', raw_words=98, raw_differences=89, guarded_words=97, guards=84, omitted_mask=1,
            all_98_word_flips_and_six_missing_bindings_rejected=True, all_29_neighbors_and_pools_fixed=True)

    def test_02_symbolic_dependency_memory_CFG_and_mask_proof(self):
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        a, b = list(struct.unpack('>98I', raw)), list(struct.unpack('>97I', normalized))
        order = [old for old, _ in source.plan()]
        self.assertEqual(sorted(order), [i for i in range(98) if i != 24])
        self.assertEqual(a[24], 0x3328001F)
        self.assertEqual((a[25] >> 21 & 31, a[25] & 63), (8, 4))
        self.assertEqual((a[24] >> 26, a[24] >> 21 & 31, a[24] >> 16 & 31, a[24] & 65535), (12, 25, 8, 31))
        for i, old in enumerate(order):
            self.assertEqual(b[i] >> 26, a[old] >> 26)
            if a[old] >> 26 == 0:
                self.assertEqual(b[i] & 2047, a[old] & 2047)
            elif a[old] >> 26 in (1, 4, 5, 6, 7, 20, 21, 22, 23):
                self.assertEqual(order[i + 1], old + 1)
                self.assertEqual(order[i + 1 + fade.short(b[i])], old + 1 + fade.short(a[old]))
            if old not in (17, 19) and a[old] >> 26 != 0:
                self.assertEqual(b[i] & 65535, a[old] & 65535)
        for words, bindings in ((a, rel), (b, moved)):
            for offset, entries in bindings.items():
                kind = entries[0][0]
                words[offset // 4] = words[offset // 4] & 0xFFFF0000 | (
                    (source.STEP + 0x8000) >> 16 & 65535 if kind == 'R_MIPS_HI16' else source.STEP & 65535)
        old_paths = symbolic_paths(a, list(range(98)))
        new_paths = symbolic_paths(b, order)
        self.assertEqual(new_paths, old_paths)
        self.receipt('symbolic-proof', all_syntactic_CFG_paths=len(old_paths), including_infeasible_width_paths=True,
            complete_return_ABI_branch_conditions_and_symbolic_stores_equal=True,
            unknown_global_record_aliases_retained_in_memory_versions=True,
            only_disjoint_record_reads_reordered=True, low5_SLLV_mask_canonicalization=True,
            no_retail_word_array_or_bounded_value_substitute=True)

    def test_03_full_private_and_independent_public_pairs(self):
        cases = [dict(value=v, active=(0, 1, 128, 255)[(v + d) % 4], delta=delta,
            shift=(0, 1, 3, 15, 31, 32, 63, 255)[(v * 3 + d) % 8],
            width=fade.short(v * 317 + d * 101), height=fade.short(v * 65539 - d),
            dx=v, dy=v ^ 255, phase=v ^ 127) for v in range(256) for d, delta in enumerate(fade.STEPS)]
        cases += [dict(value=128, active=0, delta=1, shift=n, dx=0, dy=0) for n in range(256)]
        cases += [dict(value=255, active=1, delta=0, phase=n, dx=0, dy=0) for n in range(256)]
        cases += [dict(value=8, active=0, delta=0xFFFFFFE1, shift=3, dx=0, dy=0),
            dict(value=255, active=1, delta=0, height=-1, dx=0, dy=0)]
        visits = set()
        for i, args in enumerate(cases):
            memory = prior.fixture(**args)
            pair = [prior.ColorOracle(w, memory, phase=(i & 1) * 8).run() for w in (self.words, self.truth, self.raw_words)]
            self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
            expected = prior.reference(memory)
            for model in pair:
                self.assertEqual((fade.external(model.memory), model.r[2]), expected)
            visits |= pair[0].visits
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 388, 4)) - {0x1516FCC0})
        self.receipt('private', normalized_original_pairs=len(cases), raw_public_pairs=len(cases),
            all_96_reachable_words_visited=True, dead_FCC0_preserved=True, complete_literal_state_equal=True)

    def test_04_all_fired_fault_prefixes_and_bounded_aliases(self):
        count, aliases = 0, 0
        for args in (dict(value=128, active=0, delta=1, shift=32),
                dict(value=8, active=0, delta=0xFFFFFFE1, shift=3, dx=0),
                dict(value=255, active=1, delta=0), dict(value=1, active=0, delta=1),
                dict(value=255, active=1, delta=1, width=0, dx=0)):
            for phase in (0, 8):
                memory = prior.fixture(**args)
                whole = prior.ColorOracle(self.truth, memory, phase=phase).run()
                for fault in range(whole.accesses):
                    pair = [prior.ColorOracle(w, memory, phase=phase, fault=fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                    count += 1
        for offset in (0, 0x14, 0x1C, 0x24, 0x2C):
            record = source.STEP - offset
            for delta in (0, 1, 0xFFFFFFFF, 0x80000000):
                memory = prior.fixture(value=64, active=1, delta=delta, record=record)
                pair = [prior.ColorOracle(w, memory, record=record).run() for w in (self.words, self.truth)]
                self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                self.assertEqual((fade.external(pair[0].memory), pair[0].r[2]), prior.reference(memory, record))
                aliases += 1
        self.receipt('faults', fired_literal_prefix_pairs=count, bounded_guest_alias_pairs=aliases,
            not_portable_C_fault_or_hardware_claim=True)

    def test_05_native32_UBSan_and_eight_controls(self):
        with patch.object(prior, 'source', source):
            prior.ColorFadeTests.test_05_native32_defined_math_O2_O0_and_eight_negatives(self)

    def test_06_original_and_normalized_rebases(self):
        data, functions, rel = parse_object(self.padded)
        emitted, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION, {'D_800BE9E4': source.STEP})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta, step in ((0, 0, source.STEP), (1, 0x10000, 0x80207FFC), (2, -0x10000, 0x80318004)):
            entry, outputs = source.ENTRY + delta, []
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            for name in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=D_800BE9E4=0x%X' % step, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>97I', sections(elf)['.text'][1])))
            expected = list(self.truth)
            for hi, lo in ((6, 7), (20, 21), (31, 33)):
                expected[hi] = expected[hi] & 0xFFFF0000 | ((step + 0x8000) >> 16 & 65535)
                expected[lo] = expected[lo] & 0xFFFF0000 | (step & 65535)
            self.assertEqual(outputs, [expected, expected])
            for shift in (0, 31, 32, 255):
                memory = prior.fixture(shift=shift, delta=0xFFFFFFE1, dx=0, step=step)
                pair = [prior.ColorOracle(w, memory, entry=entry, step=step).run() for w in outputs]
                self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                self.assertEqual((fade.external(pair[0].memory), pair[0].r[2]), prior.reference(memory, step=step))
        self.receipt('rebases', original_normalized_pairs=3, all_97_words_equal=True,
            three_HI_LO_pairs_and_signed_low_carry=True, full_private_pairs=12)

    def test_07_dispatcher_callback_and_full_cleanup_chain(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        table = image[elf_slot_offset(image, source.TABLE, 36):][:36]
        self.assertEqual(table, self.rom[0x231660:0x231660 + 36])
        self.assertEqual(struct.unpack('>9I', table), updater.TARGETS)
        callback = image[elf_slot_offset(image, source.ENTRY, 388):][:388]
        installed = callback == self.rom[source.ROM:source.ROM + 388]
        if not installed:
            self.assertEqual(callback[:12], struct.pack('>3I', 0x00001025, 0x03E00008, 0))
        bodies = {}
        for entry, rom, count in ((source.CALLER, 0x19AB28, 48), (source.REMOVE, 0x196BDC, 28)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            bodies[entry] = words
        count, completions, destructors = 0, 0, set()
        for i in range(64):
            for binding in (0, prior.BINDING):
                for phase in (0, 8):
                    record = (prior.RECORD, source.STEP - 0x14, source.STEP - 0x24)[i % 3]
                    memory = prior.fixture(value=i * 37 & 255, active=i % 4, delta=fade.STEPS[i % 12],
                        shift=i * 9 & 255, width=i * 317, dx=i ^ 255, binding=binding, record=record)
                    pointer = updater.DESTRUCTOR if i & 4 else 0
                    put(memory, updater.TYPE_TABLE + 2 * 52, pointer)
                    expected = dict(memory)
                    counter = read(expected, record + 0x24, 1)
                    if counter:
                        put(expected, record + 0x24, max(0, fade.signed(counter - read(expected, source.STEP))), 1)
                    public, done = prior.reference(expected, record)
                    expected.update(public)
                    calls = [(source.ENTRY, record)]
                    if done:
                        if binding:
                            put(expected, binding + 4, 0, 2)
                        calls += [(source.REMOVE, record), (updater.UNLINK, record)]
                        put(expected, record, i % 3, 1)
                        if i % 3 == 2:
                            target = pointer or updater.DEFAULT
                            calls.append((target, record))
                            put(expected, record + 47, 0x6D, 1)
                            destructors.add(target)
                        completions += 1
                    else:
                        fixed = fade.short(read(expected, record + 0x10, 2)) * 256 + read(expected, record + 0x25, 1)
                        fixed = fade.signed(fixed + fade.short(read(expected, record + 0x18, 2)) * read(expected, source.STEP))
                        put(expected, record + 0x10, fixed >> 8, 2)
                        put(expected, record + 0x25, fixed, 1)
                    pair = []
                    for words in (self.words, self.truth):
                        connected = dict(zip(range(source.REMOVE, source.REMOVE + 112, 4), bodies[source.REMOVE]))
                        connected.update(zip(range(source.ENTRY, source.ENTRY + 388, 4), words))
                        model = prior.ColorOracle(bodies[source.CALLER], memory, phase=phase,
                            record=record, entry=source.CALLER, connected=connected)
                        model.release_type = i % 3
                        pair.append(model.run())
                    self.assertEqual(fade.state(pair[0]), fade.state(pair[1]))
                    self.assertEqual(fade.external(pair[0].memory), fade.external(expected))
                    self.assertEqual(pair[0].calls, calls)
                    if done:
                        self.assertEqual(pair[0].unlink_lifetime, [0 if binding else None])
                    count += 1
        self.assertGreater(completions, 0)
        self.assertLess(completions, count)
        self.assertEqual(destructors, {updater.DEFAULT, updater.DESTRUCTOR})
        self.receipt('chain', paired_cases=count, cleanup_cases=completions, release_types=[0, 1, 2],
            both_default_and_type_destructors_fired=True, delta_aliases=True, table_slot=4,
            installed_callback_exact=installed, only_staged_before_adoption=not installed,
            freshly_exact_caller_cleanup_words=[48, 28], lower_unlink_destructors_opaque=True,
            no_full_gameplay_claim=True)

    def test_09_proof_and_real_padder_negative_controls(self):
        raw, rel = source.raw_target(self.obj)
        normal, moved = source.normalize(raw, rel)
        original_words, normalized_words = list(struct.unpack('>98I', raw)), list(struct.unpack('>97I', normal))
        order = [i for i, _ in source.plan()]
        for words, bindings in ((original_words, rel), (normalized_words, moved)):
            for offset, entries in bindings.items():
                value = (source.STEP + 0x8000) >> 16 if entries[0][0] == 'R_MIPS_HI16' else source.STEP
                words[offset // 4] = words[offset // 4] & 0xFFFF0000 | (value & 65535)
        expected = symbolic_paths(original_words, list(range(98)))
        variants = {}
        wrong = list(normalized_words)
        wrong[24] = wrong[24] & ~(31 << 21) | 8 << 21
        variants['stale-mask-register'] = wrong
        wrong = list(normalized_words)
        wrong[26] = wrong[26] & ~(31 << 16) | 2 << 16
        variants['REGIMM-kind'] = wrong
        wrong = list(normalized_words)
        wrong[69], wrong[74] = wrong[74], wrong[69]
        variants['wrong-color-lifetime'] = wrong
        wrong = list(normalized_words)
        wrong[84] = wrong[84] & ~(31 << 11) | 25 << 11
        variants['early-factor-clobber'] = wrong
        for name, words in variants.items():
            self.assertNotEqual(symbolic_paths(words, order), expected, name)
        independent = list(normalized_words)
        independent[74], independent[75] = independent[75], independent[74]
        independent_order = list(order)
        independent_order[74], independent_order[75] = independent_order[75], independent_order[74]
        self.assertEqual(symbolic_paths(independent, independent_order), expected)
        manifest = (self.out / 'qualified-guards.csv').read_text()
        rows = list(csv.DictReader(io.StringIO(manifest)))
        fields = next(csv.reader(io.StringIO(manifest)))
        target = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION)
        hi = next(i for i, row in enumerate(rows) if row['function'] == source.FUNCTION and row['offset'] == '0x18')
        for name in ('stale-word', 'stale-binding', 'missing-omit'):
            changed = [dict(row) for row in rows]
            if name == 'stale-word':
                changed[target]['expected'] = '0xFFFFFFFF'
            elif name == 'stale-binding':
                changed[hi]['expected_relocations'] = '-'
            else:
                changed = [row for row in changed if not (row['function'] == source.FUNCTION and row['omit'] == 'true')]
            path = self.out / ('negative-' + name + '.csv')
            with path.open('w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fields, lineterminator='\n')
                writer.writeheader()
                writer.writerows(changed)
            with self.assertRaises(ValueError):
                from tools.pad_generated_object import emit_padded_assembly
                emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER, word_patches_path=path)
        self.receipt('proof-controls', four_effective_dependency_mutants=True, independent_schedule_accepted=True,
            three_real_padder_corruptions_rejected=True)


if __name__ == '__main__':
    unittest.main()
