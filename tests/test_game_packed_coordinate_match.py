"""Full matching preset, private frame/fault order, native C and actual factory chain."""
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_packed_coordinate_expression_fit as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_factory_preset_wrapper as wrapper
from tools.tests import test_game_packed_coordinate_preset as packet_model
from tools.tests import test_game_record_factory as factory
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_record_constructor_match import elf_slot_offset

ARGS = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678, 0xA55A1357)


def controls():
    return {
        'wrong-coordinate-half': source.SELECTED.replace('(s16)(arg0 >> 16)', '(s16)arg0'),
        'wrong-scale-word': source.SELECTED.replace('0x155, arg1,', '0x155, (arg1 ^ 1),'),
        'wrong-script-byte': source.SELECTED.replace('(u8)arg2', '(u8)((u32)arg2 >> 8)'),
        'wrong-flag-byte': source.SELECTED.replace('(u8)arg3', '(u8)((u32)arg3 >> 8)'),
        'wrong-preset': source.SELECTED.replace('0, 0, 0, 0, 4, 0, 0, 0,', '0, 0, 0, 0, 3, 0, 0, 0,'),
        'wrong-fifth-word': source.SELECTED.replace('(u8)arg3, arg4)', '(u8)arg3, arg1)'),
    }


class PackedCoordinateMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>85I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def model(self, words, args=ARGS, phase=0, mode=0, fault=None, entry=source.ENTRY, callee=source.CALLEE):
        return wrapper.PresetOracle(words, args, phase, mode, fault, entry, callee)

    def test_01_all_raw_and_padded_words_and_all_owner_neighbors(self):
        self.assertEqual(self.words, self.truth)
        before, diagnostics = build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            rel = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, f), rel(new, g), name)
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        self.receipt('owner', words=85, raw_and_production_padded_exact=True,
            unchanged_neighbors=len(new[1]) - 1, relative_relocations_and_pools_fixed=True,
            new_guards=0, compiler_profile_changes=0)

    def test_02_full_packet_registers_private_stack_and_provider_clobbers(self):
        cases = [(0,) * 5, (0xFFFFFFFF,) * 5, ARGS,
            (0x80007FFF, 0x80000000, 0x100, 0xFF, 0x76543210)]
        cases += [tuple((i * 1664525 + j * 0x1234567 + 1013904223) & 0xFFFFFFFF for j in range(5)) for i in range(512)]
        for args in cases:
            for phase in (0, 8):
                for mode in range(3):
                    pair = [self.model(w, args, phase, mode).run() for w in (self.words, self.truth)]
                    self.assertEqual(wrapper.state(pair[0]), wrapper.state(pair[1]))
                    model = pair[0]
                    self.assertEqual(model.calls, [(source.CALLEE, *packet_model.packet(args))])
                    self.assertEqual(model.r[29], wrapper.STACK + phase)
                    self.assertEqual(model.visits, set(range(source.ENTRY, source.ENTRY + 340, 4)))
                    call = next(i for i, event in enumerate(model.events) if event[0] == 'CALL')
                    self.assertEqual(model.events[call - 1], ('W', wrapper.STACK + phase - 20, 4, args[3] & 255))
        self.receipt('abi', cases=len(cases) * 6, all_85_instructions_visited=True,
            exact_registers_private_stack_access_trace_and_49_word_packet=True,
            incoming_outgoing_home_clobbers=True, final_flag_store_in_call_delay=True,
            actual_heap_hardware_and_gameplay_not_claimed=True)

    def test_03_all_fired_guest_access_fault_prefixes(self):
        count = 0
        for phase in (0, 8):
            whole = self.model(self.words, phase=phase, mode=2).run()
            for fault in range(whole.accesses):
                pair = [self.model(w, phase=phase, mode=2, fault=fault) for w in (self.words, self.truth)]
                for model in pair:
                    with self.assertRaises(AccessFault):
                        model.run()
                self.assertEqual(wrapper.state(pair[0]), wrapper.state(pair[1]))
                count += 1
        self.receipt('prefixes', paired_fired_guest_access_faults=count,
            emitted_guest_order_only_not_portable_C_or_hardware_fault_semantics=True)

    def test_04_six_effective_compiled_semantic_negatives(self):
        for name, body in controls().items():
            _, words, row = source.source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = self.model(words).run()
            self.assertNotEqual(model.calls, [(source.CALLEE, *packet_model.packet(ARGS))], name)
        self.receipt('controls', six_effective_compiled_negatives=True, no_matching_guards_for_mutants=True)

    def test_05_native32_actual_selected_C_and_six_controls(self):
        params = ','.join('%s p%d' % ('s16' if i < 2 else 'u32', i) for i in range(49))
        values = ','.join('p%d' % i for i in range(49))
        fixture = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
static u32 captured[49],count,original[5];
__attribute__((noinline,noclone)) void func_1516D99C(''' + params + '''){
 u32 values[49]={''' + values + '''};u32 i;count++;for(i=0;i<49;i++)captured[i]=values[i];}
''' + source.SELECTED + '''
static __typeof__(&func_1516E778) volatile invoke=func_1516E778;
static int run(void){u32 i,j,e[49];if(sizeof(void*)!=4||sizeof(s32)!=4)return 10;
 for(i=0;i<65536;i++){for(j=0;j<49;j++)e[j]=0;
 original[0]=((i^0x8000)<<16)|i;original[1]=0xFEDC0000u|i;original[2]=0x87654300u|((i*17)&255);
 original[3]=0xA55A0000u|((i*31)&65535);original[4]=i*1664525u+1013904223u;
 e[0]=(u32)(s32)(s16)(original[0]>>16);e[1]=(u32)(s32)(s16)original[0];e[3]=original[2]&255;
 e[12]=4;e[16]=e[17]=e[18]=255;e[20]=e[21]=8;e[22]=1;e[27]=e[28]=e[29]=e[30]=341;
 e[31]=original[1];e[32]=30;e[34]=255;e[35]=40;e[36]=360;e[37]=24;e[38]=33;e[39]=4;e[41]=1;e[47]=original[3]&255;e[48]=original[4];
 count=0;invoke(original[0],(s32)original[1],(s32)original[2],(s32)original[3],(s32)original[4]);
 if(count!=1)return 11;for(j=0;j<49;j++)if(captured[j]!=e[j])return 12;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + name, body, '-O2', False) for name, body in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, ok, (name, result.returncode))
        self.receipt('native', actual_selected_C=True, cases_per_O2_O0=65536, six_effective_controls=True,
            first_two_formals_signed_halfwords_rest_explicit_word_capture=True,
            guest_raw_frame_and_actual_callee_storage_qualified_separately=True)

    def test_06_independent_original_assembly_and_three_call_rebases(self):
        data, fs, rel = parse_object(self.obj)
        text, missing = emit_function(data, fs[source.FUNCTION], rel, source.FUNCTION, {'func_1516D99C': source.CALLEE})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:340])
            self.assertEqual(outputs[0], outputs[1])
            model = self.model(list(struct.unpack('>85I', outputs[0])), entry=entry, callee=callee).run()
            self.assertEqual(model.calls, [(callee, *packet_model.packet(ARGS))])
        self.receipt('rebases', independent_original_text_and_call_pairs=3, complete_packets_checked=True)

    def test_07_actual_factory_allocator_and_complete_record_storage(self):
        before = (self.out / 'before-elf').read_bytes()
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, before, elf_slot_offset(before, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        for i in range(256):
            args = tuple((i * 1664525 + j * 0x1020304 + 1013904223) & 0xFFFFFFFF for j in range(5))
            result = 0 if i % 4 == 0 else factory.RECORD
            phase = (i & 1) * 8
            model = factory.FactoryOracle(self.words, args, result, phase=phase, entry=source.ENTRY, connected=connected, chain=True).run()
            self.assertEqual(model.calls[0], (source.CALLEE, *packet_model.packet(args)))
            self.assertEqual(model.calls[1], (0x15167A68, 17, args[4], 76, 0, args[3] & 255, 1))
            self.assertEqual(model.calls[2], (factory.ALLOCATE, 76, 1, 0, 0, 1))
            self.assertEqual(len(model.calls), 3 if not result else 4)
            if result:
                expected = factory.reference(factory.fixture(packet_model.packet(args)), packet_model.packet(args), result)[0]
                for address in range(factory.RECORD + 14, factory.RECORD + 76):
                    self.assertEqual(model.memory[address], expected[address])
                self.assertEqual(model.memory[factory.RECORD], 17)
                self.assertEqual(model.memory[factory.RECORD + 1], args[4] & 255)
                self.assertEqual(model.memory[factory.RECORD + 12], args[3] & 255)
        self.receipt('chain', actual_wrapper_factory_allocator_cases=256, actual_callee_words=[125, 28],
            null_and_registered_records=True, only_lower_heap_and_registration_providers_opaque=True,
            no_full_gameplay_or_host_acceptance_claim=True)


if __name__ == '__main__':
    unittest.main()
