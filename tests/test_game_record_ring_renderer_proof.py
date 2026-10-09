"""Independent live-value gates for the complete, still-uninstalled renderer."""

import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_record_ring_renderer_candidates as screen
from tools.experiments import game_record_ring_renderer_proof as proof
from tools.pad_generated_object import parse_object
from tools.tests import test_game_record_ring_renderer_recovery as recovery


def field(word, shift, reg):
    return word & ~(31 << shift) | reg << shift


class GameRecordRingRendererProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-ring-renderer-test/proof'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected', screen.SETUP_FITTED)
        cls.retail = list(struct.unpack_from('>405I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.ordered = proof.factor_order(cls.words)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_complete_cfg_live_values_and_unreachable_word(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (405, 208, 185))
        result = proof.Proof(self.words, self.retail).run()
        self.assertEqual((result['reachable_nodes'], result['checked_words'], result['call_sites']), (383, 404, 6))
        self.assertEqual(result['missing_words'], [0x1A8])
        self.assertEqual(self.words[0x1A8 // 4], self.retail[0x1A8 // 4])
        self.assertEqual(sum(a != b for a, b in zip(self.ordered, self.retail)), 182)
        self.assertEqual(result['obligations'], 560)
        result.update(raw_differences=185, factor_differing_words=8, save_differing_words=2,
            GP_differing_words_outside_factor=175, factor_order_GP_differences=5,
            after_factor_order_differences=182, no_production_normalization=True)
        self.receipt('live-values', result)

    def test_must_equal_meet_keeps_path_correlation_and_volatile_kills(self):
        start = proof.initial()
        direct = proof.Proof.write(start, 1, 33)
        swapped = proof.Proof.write(start, 1, 34)
        joined = proof.meet(direct, swapped)
        self.assertNotEqual(joined[1], joined[33])
        self.assertNotEqual(joined[1], joined[34])
        self.assertEqual(proof.meet(direct, direct), direct)
        self.assertEqual(proof.meet(direct, swapped), proof.meet(swapped, direct))
        check = proof.Proof(self.words, self.retail)
        after = check.edge_step(0x8C, start, True, True, False)
        for reg in (*range(1, 16), 24, 25):
            if reg != 2:
                self.assertNotEqual(after[reg], after[32 + reg])
        for reg in range(20):
            self.assertNotEqual(after[64 + reg], after[96 + reg])
        self.assertEqual(after[2], after[34])
        for reg in range(16, 24):
            self.assertEqual(after[reg], after[32 + reg])
        for reg in range(20, 32):
            self.assertEqual(after[64 + reg], after[96 + reg])

    def test_effective_live_operand_negatives_not_mask_agreement(self):
        cases = ((0x18, 21, 4, 'output aliases owner'),
            (0x60, 21, 21, 'backend receives view as owner'),
            (0x158, 21, 3, 'volatile value after mode call'),
            (0x2A0, 16, 7, 'wrong seed alpha product'),
            (0x5C4, 21, 19, 'loop decrements output instead of index'),
            (0x610, 16, 24, 'loop reads killed volatile goal'))
        witnesses = []
        for pc, shift, reg, name in cases:
            bad = list(self.words)
            bad[pc // 4] = field(bad[pc // 4], shift, reg)
            self.assertEqual(bad[pc // 4] & ~proof.gp_mask(bad[pc // 4]),
                self.words[pc // 4] & ~proof.gp_mask(self.words[pc // 4]))
            with self.assertRaisesRegex(ValueError, 'live input mismatch') as result:
                proof.Proof(bad, self.retail).run()
            witnesses.append(dict(change=pc, name=name, rejection=str(result.exception)))
        self.receipt('live-negatives', dict(controls=witnesses, effective=len(witnesses),
            all_opcode_literal_masks_agree=True, not_timeout_or_unsupported=True))

    def test_structural_reserved_bits_dead_code_and_save_window_negatives(self):
        cases = ((0x8, 1 << 21, 'reserved SLL source'),
            (0x560, 1, 'FP compare function'),
            (0x610, 1, 'branch displacement'),
            (0x1A8, 1 << 16, 'changed dead word'),
            (0x24, 0x3C, 'save overlaps SP50'),
            (0x14, 1 << 16, 'wrong saved entry register'),
            (0x278, 1 << 30, 'annulled factor conversion delay'))
        witnesses = []
        for pc, xor, name in cases:
            bad = list(self.words)
            bad[pc // 4] ^= xor
            with self.assertRaises(ValueError) as result:
                proof.Proof(bad, self.retail).run()
            witnesses.append(dict(change=pc, name=name, rejection=str(result.exception)))
        for pc in (0x8C, 0xEC, 0x104, 0x114, 0x148, 0x56C):
            bad, other = list(self.words), list(self.retail)
            bad[pc // 4] = other[pc // 4] = 0x0D400000
            with self.assertRaisesRegex(ValueError, 'unmodelled call'):
                proof.Proof(bad, other).run()
        for pc, reg in ((0x170, 0), (0x564, 2)):
            bad, other = list(self.words), list(self.retail)
            bad[pc // 4] = field(bad[pc // 4], 16, reg)
            other[pc // 4] = field(other[pc // 4], 16, reg)
            with self.assertRaisesRegex(ValueError, 'unsupported .* subtype'):
                proof.Proof(bad, other).run()
        self.receipt('structural-negatives', dict(controls=witnesses, unknown_call_controls=6,
            unsupported_branch_subtype_controls=2,
            complete_shape_literals_FP_fields_and_save_window_checked=True))

    @staticmethod
    def factor_model(body, opacity, flag, fp=0x3FC00000, missing=None):
        memory = {}
        recovery.put(memory, recovery.OWNER + 0x1C, opacity, 2)
        if missing is not None:
            del memory[recovery.OWNER + 0x1C + missing]
        model = recovery.RibbonOracle(list(body[0x278 // 4:0x29C // 4]) + [0x03E00008, 0], memory)
        model.r[20] = model.before[20] = recovery.OWNER
        model.r[15] = flag
        model.f[10] = fp
        return model

    def test_exhaustive_signed_opacity_factor_block_and_conversion_delay(self):
        cases = 0
        for opacity in range(-32768, 32768):
            for flag in (0, 8):
                models = [self.factor_model(body, opacity, flag).run() for body in (self.words, self.ordered)]
                a, b = models
                self.assertEqual((a.r, a.f, a.memory, a.events), (b.r, b.f, b.memory, b.events))
                self.assertEqual(a.r[3], opacity * 12 & 255 if flag else 255)
                self.assertEqual(a.f[16], 1)
                cases += 1
        patterns = (0, 0x80000000, 1, 0x80000001, 0x007FFFFF, 0x00800000,
            0x7F7FFFFF, 0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345)
        edges = 0
        for fp, flag, opacity in itertools.product(patterns, (0, 8), (-32768, -1, 0, 19, 32767)):
            a, b = [self.factor_model(body, opacity, flag, fp).run() for body in (self.words, self.ordered)]
            self.assertEqual((a.r, a.f, a.events), (b.r, b.f, b.events))
            edges += 1
        bad = list(self.words)
        bad[0x278 // 4] |= 1 << 30
        good = self.factor_model(self.words, 19, 0).run()
        wrong = self.factor_model(bad, 19, 0).run()
        self.assertNotEqual(good.f[16], wrong.f[16])
        self.receipt('factor-domain', dict(pairs=cases, executions=cases * 2, FP_edge_pairs=edges,
            full_GP_FP_memory_access_identity=True, reused_MIPS_oracle=True,
            annulled_delay_control_effective=True, hardware_FCSR_traps=False))

    def test_factor_optional_halfword_fault_and_preceding_conversion(self):
        cases = 0
        for flag, missing in itertools.product((0, 8), (0, 1)):
            models = [self.factor_model(body, 19, flag, missing=missing) for body in (self.words, self.ordered)]
            for model in models:
                if flag:
                    with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                        model.run()
                else:
                    model.run()
                self.assertEqual(model.f[16], 1)
            self.assertEqual((models[0].r, models[0].f, models[0].events),
                (models[1].r, models[1].f, models[1].events))
            cases += 1
        self.receipt('factor-faults', dict(pairs=cases, executions=cases * 2, optional_halfword=True,
            truncation_always_precedes_halfword_fault=True, not_portable_C_fault_semantics=True))

    def test_complete_factor_reorder_memory_state_and_public_prefixes(self):
        cases = 0
        for flags, pattern, view, phase, mode in itertools.product((0, 2, 8, 10), range(3),
                (0, 3, -1), (0, 8), (0, 1, 6, 7, 8, 11)):
            memory = recovery.fixture(flags=flags, pattern=pattern, view=view)
            models = [recovery.RibbonAccessOracle(body, memory, view, mode=mode, phase=phase).run()
                for body in (self.words, self.ordered, self.retail)]
            a, ordered, retail = models
            self.assertEqual((a.r, a.f, a.memory, a.events, a.calls),
                (ordered.r, ordered.f, ordered.memory, ordered.events, ordered.calls))
            self.assertEqual(a.memory, retail.memory)
            self.assertEqual(a.calls, retail.calls)
            self.assertEqual(a.r[2], retail.r[2])
            public = lambda model: [e for e in model.events if e[0] == 'CALL' or
                not recovery.STACK - 0x600 <= e[1] < recovery.STACK + 0x140]
            self.assertEqual(public(a), public(retail))
            cases += 1
        self.receipt('whole-entry', dict(cases=cases, executions=cases * 3,
            raw_vs_factor_order_complete_memory_GP_FP_events_identical=True,
            raw_vs_retail_complete_exit_memory_and_public_prefixes_identical=True,
            raw_vs_retail_private_GP_FP_or_fault_prefix_identity=False, installed=False))

    def test_original_and_candidate_independent_symbol_rebase_proofs(self):
        asm, obj = self.out / 'original.s', self.out / 'original.o'
        original = (self.root / 'conker/asm/nonmatchings/generated_204660/func_151D80C4.s').read_text()
        asm.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n.type ' + screen.FUNCTION +
            ', @function\n' + original + '\n.size ' + screen.FUNCTION + ', . - ' + screen.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)],
            cwd=self.root, check=True, capture_output=True)
        _, functions, original_rel = parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'], 1620)
        _, _, fitted_rel = parse_object(self.out / 'selected.o')
        self.assertCountEqual([r for rows in original_rel.values() for r in rows],
            [r for rows in fitted_rel.values() for r in rows])
        self.assertEqual(sum(map(len, original_rel.values())), 16)
        results = []
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = dict(screen.SYMBOLS)
            if variant:
                for index, name in enumerate(n for n in symbols if n.startswith('D_')):
                    symbols[name] = 0x70000000 + (index + 1) * 0x100000 + (0x7FFC, 0x8000, 0xFFF8)[(index + variant) % 3]
                for index, name in enumerate(recovery.TARGET_NAMES.values()):
                    symbols[name] = (entry & 0xF0000000) + 0x100800 + index * 0x100
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for kind, object_ in (('original', obj), ('candidate', self.out / 'selected.o')):
                elf = self.out / ('rebase-%d-%s.elf' % (variant, kind))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(object_)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>405I', screen.sections(elf)['.text'][1])))
            if not variant:
                self.assertEqual(bodies, [self.retail, self.words])
            result = proof.Proof(bodies[1], bodies[0], entry=entry, symbols=symbols).run()
            self.assertEqual((result['checked_words'], result['obligations']), (404, 560))
            result.update(entry=entry, independent_links=True, relocation_uses=16)
            results.append(result)
        self.receipt('rebases', dict(symbol_sets=4, proofs=results, HI16_carry_LO16_sign_and_JAL_regions=True))


if __name__ == '__main__':
    unittest.main()
