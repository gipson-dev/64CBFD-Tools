"""Full packet, ABI, fault prefixes, native C, copied owner and rebased original."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_factory_preset_wrapper as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK


def packet(args):
    result = [0] * 49
    for index, value in ((0, 2), (3, 45), (5, 255), (6, 255), (7, 255), (12, 2),
            (19, 1), (27, 80), (28, 80), (31, args[1]), (32, 10), (33, 10),
            (34, args[0]), (35, 60), (38, 129), (39, 4), (41, 1), (45, 4),
            (46, 2), (47, args[2] & 255), (48, args[3])):
        result[index] = value & 0xFFFFFFFF
    return tuple(result)


def controls():
    return {
        'narrow-first': source.SELECTED.replace('0xA, 0xA, arg0,', '0xA, 0xA, (u8) arg0,'),
        'narrow-second': source.SELECTED.replace('0, 0, arg1,', '0, 0, (u16) arg1,'),
        'wide-third': source.SELECTED.replace('(u8) arg2', 'arg2'),
        'wrong-preset': source.SELECTED.replace('0x2D,', '0x2C,'),
        'wrong-last': source.SELECTED.replace('(u8) arg2, arg3)', '(u8) arg2, arg0)'),
    }


class PresetOracle(MaskOracle):
    def __init__(self, words, args, phase=0, mode=0, fault=None, entry=source.ENTRY, callee=source.CALLEE):
        memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-256, 256)}
        memory.update({0x20000 + i: 0xA5 for i in range(16)})
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault,
            entry=entry, arguments=args)
        self.args, self.callee = args, callee

    def record_call(self, target):
        assert target == self.callee
        args = self.arguments(49)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == self.callee
        if self.mode:
            for i in range(4):
                self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        if self.mode == 2:
            for i in range(4):
                self.put(STACK + self.phase + i * 4, 0xC5000000 + i, 4)
            self.put(0x20004, self.args[3], 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]


def state(model):
    return (model.memory, model.r, model.f, model.events, model.calls, model.accesses)


class FactoryPresetWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.result = source.qualify(cls.root, cls.out)
        cls.retail = list(struct.unpack_from('>78I', (cls.root / 'conker/conker.us.bin').read_bytes(), source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_direct_slot_real_padder_and_unchanged_owner_neighbors(self):
        self.assertEqual(self.words, self.retail)
        before, diagnostics = build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, info in old[1].items():
            if name == source.FUNCTION:
                continue
            other = new[1][name]
            self.assertEqual(info['size'], other['size'], name)
            self.assertEqual(old[0][info['value']:info['value'] + info['size']],
                new[0][other['value']:other['value'] + other['size']], name)
            rel = lambda obj, f: [(p - f['value'], r) for p, r in obj[2].items()
                if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(rel(old, info), rel(new, other), name)
        self.assertEqual(normalized_pools(before), normalized_pools(self.obj))
        self.receipt('owner', words=78, raw_and_production_padded_exact=True,
            unchanged_neighbors=len(old[1]) - 1, unchanged_relative_relocations_and_pools=True,
            guards_added=0, flags=['-O2', '-g3'], diagnostics='')

    def test_02_complete_packet_high_bits_provider_and_stack_lifetimes(self):
        cases = [(0, 0, 0, 0), (0xFFFFFFFF,) * 4, (0x80000000, 0xFFFF0000, 0xFFFFFF80, 0x76543210)]
        cases += [tuple((i * 1664525 + 1013904223 + j * 0x372159AB) & 0xFFFFFFFF
            for j in range(4)) for i in range(128)]
        for args in cases:
            for phase in (0, 8):
                for mode in range(3):
                    models = [PresetOracle(words, args, phase, mode).run() for words in (self.words, self.retail)]
                    self.assertEqual(state(models[0]), state(models[1]))
                    model = models[0]
                    self.assertEqual(model.calls, [(source.CALLEE, *packet(args))])
                    self.assertEqual(model.r[2], 0xA5000002)
                    self.assertEqual(model.r[29], STACK + phase)
                    self.assertEqual(model.visits, set(range(source.ENTRY, source.ENTRY + 312, 4)))
                    self.assertEqual(model.events[0], ('W', STACK + phase - 4, 4, 0xDEAD0000))
                    call = next(i for i, event in enumerate(model.events) if event[0] == 'CALL')
                    self.assertEqual(model.events[call - 1], ('W', STACK + phase - 16, 4, args[3]))
                    for i, value in enumerate(args):
                        self.assertEqual(read(model.memory, STACK + phase + i * 4),
                            0xC5000000 + i if mode == 2 else value)
        self.receipt('abi', cases=len(cases) * 6, packet_words=49, phases=[0, 8], frame=208,
            all_78_instructions_visited=True, saved_RA_and_registers=True, final_argument_in_call_delay=True,
            outgoing_and_incoming_home_clobbers_and_provider_effects=True,
            factory_is_opaque_not_recovered=True, guest_low_word_model_not_hardware_runtime=True)

    def test_03_all_guest_memory_fault_prefixes(self):
        args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678)
        total = 0
        for phase in (0, 8):
            complete = PresetOracle(self.words, args, phase, 2).run()
            for fault in range(complete.accesses):
                pair = [PresetOracle(words, args, phase, 2, fault) for words in (self.words, self.retail)]
                for model in pair:
                    with self.assertRaises(AccessFault):
                        model.run()
                self.assertEqual(state(pair[0]), state(pair[1]))
                total += 1
        self.receipt('prefixes', paired_injected_guest_access_faults=total,
            emitted_guest_order_only_not_portable_C_fault_semantics=True)

    def test_04_five_effective_compiled_negative_controls(self):
        args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678)
        rows = []
        for name, body in controls().items():
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            self.assertGreater(row['differences'], 0, name)
            model = PresetOracle(words, args).run()
            self.assertNotEqual(model.calls, [(source.CALLEE, *packet(args))], name)
            rows.append(row)
        self.receipt('controls', effective_compiled_negatives=rows)

    def test_05_actual_native32_C_at_two_profiles_and_all_negatives(self):
        params = ','.join('u32 p%d' % i for i in range(49))
        capture = ','.join('p%d' % i for i in range(49))
        fixture = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned short u16;
static u32 captured[49],count;static u32 original[4];
__attribute__((noinline,noclone)) s32 func_1516D99C(''' + params + '''){
 u32 values[49]={''' + capture + '''};u32 i;count++;
 for(i=0;i<49;i++)captured[i]=values[i];return (s32)0xABCDEF01u;
}
''' + source.SELECTED + '''
static void (*volatile invoke)(s32,s32,s32,s32)=func_1516F1C0;
static int check(u32 i){u32 j,expected[49]={0};count=0;
 original[0]=0x87650000u+i;original[1]=0xFEDC0000u+i;
 original[2]=0xA55A0000u+i;original[3]=i^0x12345678u;
 expected[0]=2;expected[3]=45;expected[5]=expected[6]=expected[7]=255;
 expected[12]=2;expected[19]=1;expected[27]=expected[28]=80;
 expected[31]=original[1];expected[32]=expected[33]=10;expected[34]=original[0];
 expected[35]=60;expected[38]=129;expected[39]=4;expected[41]=1;
 expected[45]=4;expected[46]=2;expected[47]=original[2]&255;expected[48]=original[3];
 invoke((s32)original[0],(s32)original[1],(s32)original[2],(s32)original[3]);
 if(count!=1)return 10;for(j=0;j<49;j++)if(captured[j]!=expected[j])return 11;return 0;}
static int run(void){u32 i;int result;if(sizeof(void*)!=4||sizeof(s32)!=4)return 12;
 for(i=0;i<65536;i++){result=check(i);if(result)return result;}return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True),
                ('O0', source.SELECTED, '-O0', True)] + [('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation', '-Wno-unused-parameter',
                str(path), '-o', str(path.with_suffix(''))],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], capture_output=True, timeout=30)
            self.assertEqual(result.returncode == 0, ok, (name, result.returncode))
        self.receipt('native', profiles=['O2', 'O0'], cases_per_profile=65536,
            actual_selected_C_and_49_word_provider_ABI=True, five_effective_compiled_negatives=True,
            native32_not_N64_runtime=True)

    def test_06_independently_assembled_original_and_three_call_rebases(self):
        data, functions, rel = parse_object(self.obj)
        anchors = {'func_1516D99C': source.CALLEE}
        selected, missing = emit_function(data, functions[source.FUNCTION], rel, source.FUNCTION, anchors)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        texts = dict(selected=selected, original='glabel ' + source.FUNCTION + '\n' + original)
        for label, body in texts.items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
                capture_output=True, check=True)
        for index, delta in enumerate((0, 0x10000, -0x10000)):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for label in texts:
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '-o', str(elf), str(self.out / (label + '-reloc.o'))],
                    capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:312])
            self.assertEqual(outputs[0], outputs[1])
            words = list(struct.unpack('>78I', outputs[0]))
            args = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678)
            model = PresetOracle(words, args, entry=entry, callee=callee).run()
            self.assertEqual(model.calls, [(callee, *packet(args))])
        self.receipt('rebases', independent_text_and_call_target_pairs=3,
            original_assembly_reference=True, rebased_guest_packet_checks=True)


if __name__ == '__main__':
    unittest.main()
