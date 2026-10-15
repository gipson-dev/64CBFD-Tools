"""Preset-0x1B packet, literal ABI/faults, native C and current factory chain."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_fade_record_preset as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_dual_factory_preset as dual
from tools.tests import test_game_record_factory as factory
from tools.tests import test_game_table_fade_match as archive


def packet(args):
    result = [0] * 49
    for i in range(3):
        value = args[i] & 65535
        result[i] = (value - (65536 if value & 32768 else 0)) & 0xFFFFFFFF
    for index, value in ((3, 27), (5, 255), (6, 255), (7, 255), (9, 255),
            (10, 255), (11, 255), (12, 3), (27, 1024), (28, 1024), (31, 2),
            (34, 255), (35, 15), (38, 9), (40, 255), (41, 10), (42, 90),
            (43, 5), (44, args[3]), (47, args[4] & 255), (48, args[5])):
        result[index] = value & 0xFFFFFFFF
    return tuple(result)


class PresetOracle(dual.DualOracle):
    def __init__(self, words, args, phase=0, mode=0, fault=None, entry=source.ENTRY, callee=source.CALLEE):
        super().__init__(words, args, phase, mode, fault, entry, callee)

    def hook(self, target):
        assert target == self.callee
        if self.mode:
            for i in range(4):
                self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        if self.mode == 2:
            for i in range(6):
                self.put(STACK + self.phase + i * 4, 0xC5000100 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.lo, self.condition, self.r[2] = 0x87654321, True, 0xABCD0001


def controls():
    return {
        'byte-x': source.SELECTED.replace('        arg0, arg1, arg2,', '        (u8)arg0, arg1, arg2,'),
        'byte-y': source.SELECTED.replace('        arg0, arg1, arg2,', '        arg0, (u8)arg1, arg2,'),
        'byte-z': source.SELECTED.replace('        arg0, arg1, arg2,', '        arg0, arg1, (u8)arg2,'),
        'narrow-variant': source.SELECTED.replace('5, arg3, 0, 0,', '5, (u8)arg3, 0, 0,'),
        'wide-flag': source.SELECTED.replace('(u8)arg4', 'arg4'),
        'wrong-context': source.SELECTED.replace('(u8)arg4, arg5', '(u8)arg4, arg3'),
        'wrong-preset': source.SELECTED.replace('arg2, 0x1B,', 'arg2, 0x1A,'),
        'wrong-size': source.SELECTED.replace('0x400, 0x400,', '0x400, 0x401,'),
    }


class PresetCandidateTests(unittest.TestCase):
    def test_scope_placeholder_and_direct_match_gate(self):
        self.assertEqual(len(source.PATHS), 57)
        self.assertEqual(len(set(source.PATHS.values())), 57)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        for count, differences, frame, diagnostic in ((80, 0, 208, ''), (81, 1, 208, ''),
                (81, 0, 216, ''), (81, 0, 208, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count,
                    differences=differences, frame=frame, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))
        before = 's32 func_1516FA88() {\n    return 0;\n}\nvoid other(void) {}\n'
        self.assertTrue(source.recovered_owner(before).endswith('void other(void) {}\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))


class FadePresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>81I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = archive.TableFadeMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_direct_words_real_padder_and_all_owner_neighbors(self):
        self.assertEqual(self.words, self.truth)
        obj, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        self.receipt('owner', raw_and_padded_words=81, frame=208, unchanged_neighbors=len(old[1]) - 1,
            relative_relocations_and_pools_fixed=True, guards_added=0, profile_changes=0)

    def test_02_complete_packet_private_state_and_provider_writes(self):
        cases = [(0,) * 6, (0xFFFFFFFF,) * 6,
            (0x80000000, 0xFFFF0000, 0xFFFFFF80, 0x100, 0xFFFF0080, 0x12345678)]
        cases += [tuple((i * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(6))
            for i in range(256)]
        visits = set()
        for args in cases:
            for phase in (0, 8):
                for mode in range(3):
                    pair = [PresetOracle(w, args, phase, mode).run() for w in (self.words, self.truth)]
                    self.assertEqual(dual.state(pair[0]), dual.state(pair[1]))
                    self.assertEqual(pair[0].calls, [(source.CALLEE, *packet(args))])
                    self.assertEqual(pair[0].r[29], STACK + phase)
                    self.assertEqual(pair[0].r[2], 0xABCD0001)
                    call = next(i for i, event in enumerate(pair[0].events) if event[0] == 'CALL')
                    self.assertEqual(pair[0].events[call - 1], ('W', STACK + phase - 208 + 192, 4, args[5]))
                    visits |= pair[0].visits
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 324, 4)))
        self.receipt('abi', paired_cases=len(cases) * 6, full_packet_words=49,
            all_81_words_visited=True, all_private_state_equal=True, final_context_in_call_delay=True,
            physical_noncanonical_inputs_and_home_writes_not_portable_C_claim=True)

    def test_03_every_fired_guest_memory_fault_prefix(self):
        args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x100, 0xFFFF00A5, 0x7FFFFFFF)
        count = 0
        for phase in (0, 8):
            for mode in range(3):
                whole = PresetOracle(self.truth, args, phase, mode).run()
                for fault in range(whole.accesses):
                    pair = [PresetOracle(w, args, phase, mode, fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(dual.state(pair[0]), dual.state(pair[1]))
                    count += 1
        self.receipt('faults', fired_prefix_pairs=count, full_literal_state_equal=True,
            not_portable_C_fault_or_hardware_claim=True)

    def test_04_compiled_negative_controls(self):
        args = (0x8765FEDC, 0xFEDCBA98, 0xFFFFFF80, 0x100, 0xFFFF00A5, 0x7FFFFFFF)
        effective = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = PresetOracle(words, args).run()
            self.assertNotEqual(model.calls, [(source.CALLEE, *packet(args))], name)
            effective.append(name)
        self.assertEqual(set(effective), set(controls()))
        self.receipt('controls', effective_guest=effective, no_mutant_guards=True)

    def test_05_native32_packet_at_O2_O0_and_eight_negatives(self):
        types = ['s16' if i in (0, 1, 2, 27, 28, 29, 30, 36) else
            'u16' if i in (31, 37, 38) else 's32' if i in (44, 47, 48) else 'u8' for i in range(49)]
        params = ','.join('%s p%d' % (t, i) for i, t in enumerate(types))
        capture = ','.join('p%d' % i for i in range(49))
        harness = '''typedef unsigned int u32;typedef int s32;typedef short s16;typedef unsigned short u16;typedef unsigned char u8;
static u32 captured[49],count;
__attribute__((noinline,noclone)) void func_1516D99C(''' + params + '''){
 u32 v[49]={''' + capture + '''};u32 i;for(i=0;i<49;i++)captured[i]=v[i];count++;
}
''' + source.SELECTED + '''
static void (*volatile invoke)(s16,s16,s16,s32,s32,s32)=func_1516FA88;
static int check(u32 n){u32 a[6],p[49],i;count=0;
 for(i=0;i<6;i++)a[i]=0x87650000u+i*0x1020304u+n;
 invoke((s16)a[0],(s16)a[1],(s16)a[2],(s32)a[3],(s32)a[4],(s32)a[5]);
 if(count!=1)return 10;for(i=0;i<49;i++)p[i]=0;
 for(i=0;i<3;i++){u32 low=a[i]&65535;p[i]=low<32768?low:low-65536u;}
 p[3]=27;p[5]=p[6]=p[7]=p[9]=p[10]=p[11]=255;p[12]=3;p[27]=p[28]=1024;p[31]=2;
 p[34]=p[40]=255;p[35]=15;p[38]=9;p[41]=10;p[42]=90;p[43]=5;p[44]=a[3];p[47]=a[4]&255;p[48]=a[5];
 for(i=0;i<49;i++)if(p[i]!=captured[i])return 11;return 0;
}
static int run(void){u32 i;int r;if(sizeof(void*)!=4||sizeof(s16)!=2)return 12;
 for(i=0;i<65536;i++){r=check(i);if(r)return r;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            native = harness.replace(source.SELECTED, body)
            path.write_text(native)
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode, 0 if ok else 11, name)
        self.receipt('native', cases_per_O2_O0=65536, all_16bit_coordinate_patterns=True,
            full_packet_provider=True, effective_native_negatives=8)

    def test_06_independent_original_and_three_call_rebases(self):
        data, functions, rel = parse_object(self.obj)
        emitted, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION, {'func_1516D99C': source.CALLEE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for name, body in dict(selected=emitted, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (name + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for name in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (name, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '-o', str(elf), str(self.out / (name + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(list(struct.unpack_from('>81I', sections(elf)['.text'][1])))
            self.assertEqual(outputs[0], outputs[1])
            args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x100, 0xFFFF00A5, 0x7FFFFFFF)
            self.assertEqual(PresetOracle(outputs[0], args, entry=entry, callee=callee).run().calls, [(callee, *packet(args))])
        self.receipt('rebases', independent_original_C_pairs=3, full_81_word_equality=True)

    def test_07_actual_current_factory_allocator_and_record_fields(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        cases = 0
        for variant in (0, 1, 0x100, 0x80000000, 0xFFFFFFFF):
            for flags in (0, 0x7F, 0x80, 0xFF, 0x12345600):
                args = (0x8765FEDC, 0xFEDCBA98, 0xFFFFFF80, variant, flags, 0x7FFFFFFF)
                p = packet(args)
                for result in (0, factory.RECORD):
                    for phase in (0, 8):
                        pair = [factory.FactoryOracle(w, args, result=result, phase=phase,
                            entry=source.ENTRY, connected=connected, chain=True).run() for w in (self.words, self.truth)]
                        self.assertEqual(dual.state(pair[0]), dual.state(pair[1]))
                        self.assertEqual(pair[0].calls[0], (source.CALLEE, *p))
                        self.assertEqual(pair[0].calls[1], (0x15167A68, 102 if variant else 17, args[5], 76, 0, flags & 255, 1))
                        if result:
                            expected = factory.reference(factory.fixture(p), p, result)[0]
                            for at in range(result + 14, result + 76):
                                self.assertEqual(pair[0].memory[at], expected[at], hex(at))
                            self.assertEqual(pair[0].memory[result], 102 if variant else 17)
                            self.assertEqual(pair[0].memory[result + 1], args[5] & 255)
                            self.assertEqual(pair[0].memory[result + 12], flags & 255)
                            self.assertEqual(pair[0].memory[result + 68], 3 if variant else 10)
                        cases += 1
        self.receipt('chain', paired_cases=cases, freshly_exact_current_bodies=[125, 28],
            null_success_and_fullword_variant_and_record_fields=True, lower_heap_registration_opaque=True,
            no_full_caller_gameplay_claim=True)

    def test_09_complete_rom_aligned_reference_screen_and_archival_form(self):
        calls, pointers = [], []
        jal = 0x0C000000 | ((source.ENTRY >> 2) & 0x3FFFFFF)
        for offset in range(0, len(self.rom) - 3, 4):
            word = struct.unpack_from('>I', self.rom, offset)[0]
            if word == jal:
                calls.append(offset)
            if word == source.ENTRY:
                pointers.append(offset)
        self.assertEqual((calls, pointers), ([], []))
        donor = source.build.body((self.out / 'before-archive_preset').read_text(), source.FUNCTION)
        _, words, row = source.measure(self.root, self.out, 'archival', donor)
        self.assertEqual(row['diagnostics'], '')
        self.assertEqual((row['words'], row['differences']), (78, 80))
        args = (0x8765FEDC, 0xFEDCBA98, 0xFFFFFF80, 0x100, 0xFFFF00A5, 0x7FFFFFFF)
        self.assertEqual(PresetOracle(words, args).run().calls, [(source.CALLEE, *packet(args))])
        self.receipt('reference-screen', aligned_ROM_bytes=len(self.rom), direct_JAL_words=calls,
            literal_address_words=pointers, not_proof_of_unreachability=True,
            archival_words=row['words'], archival_differences=row['differences'], recovered_formals='s16,s16,s16,s32,s32,s32')


if __name__ == '__main__':
    unittest.main()
