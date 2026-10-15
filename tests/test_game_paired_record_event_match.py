"""Direct paired-event words, literal private ABI, compiler producers and callers."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_paired_record_event_match as source
from tools.experiments import game_paired_record_event_frame as frame
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import paired_record_event_match_checkpoint as checkpoint
from tools.tests import test_game_paired_record_event as prior
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_dual_factory_preset import state
from tools.tests.test_game_table_range_loader import STACK
from tools.tests import test_game_packed_record_updater_installed as archive


def controls():
    return {
        'wrong-last-slot': source.SELECTED.replace('(u8)(&arg15)[0], arg16', '(u8)(&arg15)[0], arg14'),
        'wrong-byte-slot': source.SELECTED.replace('(u8)arg15, arg16', '(u8)arg12, arg16'),
        'narrow-live-context': source.SELECTED.replace('(void *)arg3', '(void *)(u32)(u16)arg3'),
        'unsigned-coordinate': source.SELECTED.replace('(s16)arg0', '(u16)arg0'),
        'wrong-second-type': source.SELECTED.replace('0, 0, 0, arg11,', '0, 0, 0, arg10,'),
        'wrong-width': source.SELECTED.replace('(u32)arg7 << 12', '(u32)arg8 << 12'),
        'wrong-callback': source.SELECTED.replace('(s32)func_1000EBC4,', '0,'),
    }


class PairedEventMatchCandidateTests(unittest.TestCase):
    def test_scope_and_strict_direct_gate(self):
        self.assertEqual(len(source.PATHS), 57)
        self.assertEqual(len(set(source.PATHS.values())), 57)
        for words, differences, size, diagnostic in ((200, 0, 248, ''), (199, 1, 248, ''),
                (199, 0, 256, ''), (199, 0, 248, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=words,
                    differences=differences, frame=size, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516F548() {\n    return 0;\n}\nvoid other(void) { }\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        self.assertNotIn('volatile', source.SELECTED)
        self.assertNotRegex(source.SELECTED, r'\n    (?:s32|s16|u8|u16) [A-Za-z_]\w*;')
        self.assertIn('s32 arg12, s32 arg13, s32 arg14,', source.SELECTED)


class PairedEventMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>199I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_04_both_original_callers_and_current_placeholder_boundary = prior.PairedEventTests.test_04_both_original_17_slot_caller_windows
    test_05_actual_current_factory_chain_and_event_boundary = prior.PairedEventTests.test_05_current_factory_chain_and_event_packet_boundary
    test_06_all_57_predecessor_corruptions = prior.PairedEventTests.test_06_all_immutable_predecessor_corruptions
    test_08_all_29_neighbors_and_pools_fixed = prior.PairedEventTests.test_08_other_owner_functions_relocations_and_pools_unchanged
    test_11_all_801_original_archive_fingerprints = archive.PackedRecordUpdaterInstalledTests.test_04_all_original_801_archive_fingerprints

    def test_01_direct_words_and_real_production_padder(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['differences'], self.row['frame'], self.row['diagnostics']), (199, 0, 248, ''))
        self.receipt('direct', raw_and_production_padded_words=199, frame=248, guards_added=0,
            profile_changes=0, named_locals=0, source_sha256=self.row['candidate_sha256'])

    def test_02_all_packets_and_complete_private_state(self):
        cases = [(0,) * 17, (0xFFFFFFFF,) * 17,
            tuple((0x80000000, 0xFFFF8000, 0x1234FFFF, 0xFEDCBA98, 0xABCD0080)[i % 5] for i in range(17))]
        cases += [tuple((n * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(17)) for n in range(256)]
        visits = set()
        for args in cases:
            for phase in (0, 8):
                for mode in range(4):
                    pair = [prior.PairedOracle(w, args, phase, mode).run() for w in (self.words, self.truth)]
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    expected = prior.expected(args, mode)
                    self.assertEqual(pair[0].calls, expected)
                    self.assertEqual(pair[0].r[29], STACK + phase)
                    self.assertEqual(pair[0].r[2], 0xABCD0003)
                    calls = [i for i, event in enumerate(pair[0].events) if event[0] == 'CALL']
                    for call in (0, 1):
                        self.assertEqual(pair[0].events[calls[call] - 1], ('W', STACK + phase - 248 + 192, 4, expected[call][-1]))
                    self.assertEqual(pair[0].events[calls[2] - 1], ('W', STACK + phase - 248 + 32, 4, expected[2][9]))
                    visits |= pair[0].visits
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 796, 4)))
        self.receipt('private', paired_cases=len(cases) * 8, all_199_words_visited=True,
            full_literal_state_and_all_49_49_12_words_equal=True, all_three_call_delays_checked=True,
            saved_home_and_live_incoming_and_outgoing_home_writes=True,
            physical_private_writes_not_portable_C_or_gameplay_claim=True)

    def test_03_every_fired_candidate_original_fault_prefix(self):
        args = tuple((0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(17))
        count = 0
        for phase in (0, 8):
            for mode in range(4):
                whole = prior.PairedOracle(self.truth, args, phase, mode).run()
                for fault in range(whole.accesses):
                    pair = [prior.PairedOracle(w, args, phase, mode, fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    count += 1
        self.receipt('prefixes', paired_fired_faults=count, complete_literal_candidate_ROM_prefixes_equal=True)

    def test_07_native_32_bit_O2_O0_and_effective_source_controls(self):
        declarations = ','.join('s32 a%d' % i for i in range(49))
        values = ','.join('(u32)a%d' % i for i in range(49))
        args = ','.join('(s32)original[%d]' % i for i in range(17))
        harness = '''typedef signed char s8; typedef unsigned char u8;
typedef short s16; typedef unsigned short u16; typedef int s32; typedef unsigned int u32;
typedef struct { s32 unused; } struct00;
static u32 captured[3][49], original[17], count;
static void func_1516D99C(DECL){u32 p[49]={VALUES};u32 i;
 if(count<2)for(i=0;i<49;i++)captured[count][i]=p[i];count++;}
s32 func_1000EBC4(struct00 *a,s32 b,s32 c,s32 d){return 0;}
u16 func_1000FA64(u16 a0,s16 a1,s16 a2,s16 a3,s32 a4,u16 a5,s16 a6,s32 a7,void *a8,s32 a9,s32 a10,s32 a11){
 u32 p[12]={a0,(u32)(s32)a1,(u32)(s32)a2,(u32)(s32)a3,(u32)a4,a5,(u32)(s32)a6,(u32)a7,(u32)a8,(u32)a9,(u32)a10,(u32)a11};
 u32 i;if(count==2)for(i=0;i<12;i++)captured[2][i]=p[i];count++;return 0;}
BODY
static void (*volatile invoke)(TYPES)=func_1516F548;
static int check(u32 n){u32 i,k,p[49];count=0;
 for(i=0;i<17;i++)original[i]=0x87650000u+i*0x1020304u+n;
 invoke(ARGS);if(count!=3)return 10;
 for(k=0;k<2;k++){
  for(i=0;i<49;i++)p[i]=0;
  p[0]=(u32)(s32)(s16)original[0];p[1]=(u32)(s32)(s16)original[1];p[2]=(u32)(s32)(s16)original[2];
  p[3]=13;p[5]=103;p[6]=23;p[7]=13;p[10]=18;p[12]=2;
  p[13]=original[4]&255;p[15]=original[6]&255;p[19]=original[10+k];
  p[27]=p[28]=(u32)(s32)(s16)original[7];p[29]=p[30]=(u32)(s32)(s16)original[8];
  p[31]=original[3]&65535;p[32]=original[9]&255;p[33]=20;p[34]=255;p[35]=16;
  p[36]=(u32)(s32)(s16)original[5];p[37]=200;p[38]=1;p[39]=k?6:0;p[41]=1;
  p[47]=original[15]&255;p[48]=original[16];
  for(i=0;i<49;i++)if(p[i]!=captured[k][i])return 11;
 }
 for(i=0;i<12;i++)p[i]=0;p[0]=7;
 p[1]=(u32)(s32)(s16)original[0];p[2]=(u32)(s32)(s16)original[1];p[3]=(u32)(s32)(s16)original[2];
 p[4]=0x36B0;p[5]=1000;p[6]=100;p[7]=(u32)func_1000EBC4;p[8]=original[3];
 for(i=0;i<12;i++)if(p[i]!=captured[2][i])return 12;return 0;}
static int run(void){u32 i;int r;if(sizeof(void*)!=4||sizeof(s32)!=4)return 13;
 for(i=0;i<65536;i++){r=check(i);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('DECL', declarations).replace('VALUES', values).replace('TYPES', ','.join(['s32'] * 17)).replace('ARGS', args)
        runs = [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)]
        runs += [('negative-' + name, body, '-O2', False) for name, body in controls().items()]
        exits = {}
        for name, body, profile, success in runs:
            if not success:
                self.assertNotEqual(body, source.SELECTED, name)
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace('BODY', body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            exits[name] = result.returncode
            self.assertEqual(result.returncode, 0, name) if success else self.assertIn(result.returncode, (10, 11, 12), name)
        self.receipt('native', cases_each_O2_O0=65536, effective_source_controls=7, controlled_exits=exits,
            all_49_49_12_source_expression_words_checked=True, capture_provider_not_complete_production_factory_ABI=True)

    def test_09_three_independent_original_C_rebases(self):
        data, functions, rel = parse_object(self.obj)
        emitted, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION,
            {'func_1516D99C': source.CALLEE, 'func_1000FA64': source.EVENT, 'func_1000EBC4': source.CALLBACK})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in (('selected', emitted), ('original', 'glabel ' + source.FUNCTION + '\n' + original)):
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        args = tuple((0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(17))
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee, event = source.ENTRY + delta, source.CALLEE - delta, source.EVENT + index * 0x10000
            callback = (0x10007FFC, 0x10018004, 0x1000F000)[index]
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for name in ('original', 'selected'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '--defsym=func_1000FA64=0x%X' % event,
                    '--defsym=func_1000EBC4=0x%X' % callback, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>199I', sections(elf)['.text'][1])))
            predicted = list(self.truth)
            for at, target in zip((102, 174, 193), (callee, callee, event)):
                predicted[at] = 0x0C000000 | (target >> 2 & 0x3FFFFFF)
            predicted[177] = 0x3C0E0000 | ((callback + 0x8000) >> 16 & 65535)
            predicted[178] = 0x25CE0000 | (callback & 65535)
            self.assertEqual(outputs[0], predicted)
            self.assertEqual(outputs[1], predicted)
            for mode in range(4):
                model = prior.PairedOracle(outputs[1], args, mode=mode, entry=entry, callee=callee, event=event).run()
                self.assertEqual(model.calls, prior.expected(args, mode, callee, event, callback))
        self.receipt('rebases', independent_original_C_pairs=3, all_199_words_equal=True,
            both_call_targets_and_callback_signed_low_carry_rebased=True)

    def test_10_fired_compiler_producers_and_capture_integrity(self):
        values = {}
        for name, expected in (('initial_inputs', (48, 40, 248)), ('initial_plain_short_temps', (44, 72, 280)),
                ('initial', (48, 40, 248)), ('expression_all', (None, 40, 248))):
            record = frame.trace(self.root, name, previous_input=checkpoint.previous_input)
            defs = {stage: [r['length'] for r in rows if r['name'] == 'def' and r['storage'] == 'M']
                for stage, rows in record['records'].items()}
            self.assertEqual(defs['frontend'], [] if expected[0] is None else [expected[0]])
            self.assertEqual(defs['optimizer'], [expected[1]])
            last = record['events'][-1]
            self.assertEqual((last['locals'], last['saved'], last['outgoing'], last['temporary'], last['frame']), (expected[1], 8, 200, 0, expected[2]))
            self.assertEqual([e['frame'] for e in record['events']], [0, 8, 208, expected[2]])
            self.assertTrue(record['code_unchanged'] and record['standalone_equals_complete_owner'])
            self.assertEqual(record['different_object_sections'], ['.mdebug'])
            if name == 'expression_all':
                self.assertEqual(record['raw_target_sha256'], hashlib.sha256(frame.target(self.obj)[0]).hexdigest())
            work = self.root / frame.source.BUILD / ('frame-' + name)
            log = (work / 'debugger.txt').read_text()
            for prefix in ('FRAME_TRACE ', 'FRAME_INPUT ', 'TRACE_EXIT '):
                bad = '\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
                with self.assertRaises(ValueError):
                    frame.observer.validate_observations(work, bad)
            rb = Path.read_bytes
            for stage in ('frontend', 'optimizer'):
                path = work / (stage + '.ucode')
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\0' if p == path else rb(p)):
                    with self.assertRaises(ValueError):
                        frame.observer.validate_observations(work, log)
            values[name] = dict(frontend=defs['frontend'], optimizer=defs['optimizer'], frame=last['frame'])
        self.receipt('frame', observed=values, matched_source_has_no_CFE_M_reservation=True,
            UOPT_created_40_real_spill_bytes=True, named_reservation_removed_not_frame_patched=True,
            exact_predecessor_adapter_only_for_compiler_context_not_current_image_or_chain=True)

    def test_12_compiled_controls_and_live_tail_schedule(self):
        variants = dict(controls(), cached_tail=source.SELECTED.replace('(u8)(&arg15)[0]', '(u8)arg15'))
        args = tuple((0x87654321 + i * 0x1020304) & 0xFFFFFFFF for i in range(17))
        effective, native_only = [], []
        for name, body in variants.items():
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            failed = any(prior.PairedOracle(words, args, mode=mode).run().calls != prior.expected(args, mode) for mode in range(4))
            if failed:
                self.assertGreater(row['differences'], 0)
                effective.append(name)
            else:
                self.assertEqual(words, self.words, name)
                native_only.append(name)
        self.assertIn('cached_tail', effective)
        self.receipt('controls', effective_guest_controls=effective, optimized_away_native_only=native_only)


if __name__ == '__main__':
    unittest.main()
