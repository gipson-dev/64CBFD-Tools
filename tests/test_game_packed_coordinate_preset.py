"""Non-installable preset candidates: full packet semantics, not a matching claim."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_coordinate_preset as source
from tools.tests import test_game_factory_preset_wrapper as previous


def short(value):
    return (value & 65535) - (65536 if value & 32768 else 0)


def packet(args):
    result = [0] * 49
    for index, value in ((0, short(args[0] >> 16)), (1, short(args[0])), (3, args[2] & 255),
            (12, 4), (16, 255), (17, 255), (18, 255), (20, 8), (21, 8), (22, 1),
            (27, 341), (28, 341), (29, 341), (30, 341), (31, args[1]),
            (32, 30), (34, 255), (35, 40), (36, 360), (37, 24), (38, 33),
            (39, 4), (41, 1), (47, args[3] & 255), (48, args[4])):
        result[index] = value & 0xFFFFFFFF
    return tuple(result)


class CoordinatePresetCandidateTests(unittest.TestCase):
    def test_only_the_pinned_placeholder_changes_and_50_unique_inputs(self):
        before = 's32 func_1516E778() {\n    return 0;\n}\nvoid other(void) { }\n'
        self.assertEqual(source.recovered_owner(before), source.SELECTED + 'void other(void) { }\n')
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(len(set(source.PATHS.values())), 50)

    def test_all_fourteen_bodies_keep_the_full_five_input_contract(self):
        candidates = source.candidates()
        self.assertEqual(len(candidates), 14)
        self.assertEqual(len(set(candidates.values())), 14)
        for body in candidates.values():
            self.assertIn('(u8)arg2', body)
            self.assertIn('(u8)arg3, arg4', body)
            for forbidden in ('GLOBAL_ASM', 'volatile', '(u16)arg1'):
                self.assertNotIn(forbidden, body)

    def test_mismatching_or_warning_candidates_cannot_pass_installation_gate(self):
        for count, differences, diagnostics in ((84, 79, ''), (85, 46, ''), (85, 0, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(
                    words=count, differences=differences, diagnostics=diagnostics))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))


class CoordinatePresetDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.measure(cls.root, cls.out, 'selected', source.SELECTED)
        cls.original = list(struct.unpack_from('>85I', (cls.root / 'conker/conker.us.bin').read_bytes(), source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_selected_shape_and_complete_retail_packet_at_both_stack_phases(self):
        self.assertEqual((self.row['words'], self.row['differences'], self.row['diagnostics']), (85, 46, ''))
        cases = [(0, 0, 0, 0, 0), (0xFFFFFFFF,) * 5,
            (0x80007FFF, 0x87654321, 0xFFFFFF80, 0x12345678, 0xFEDCBA98),
            (0x7FFF8000, 0xFFFFFFFF, 0x80, 0x80000000, 1)]
        cases += [tuple((i * 1664525 + j * 0x1234567 + 1013904223) & 0xFFFFFFFF for j in range(5)) for i in range(256)]
        for args in cases:
            for phase in (0, 8):
                for mode in range(3):
                    for words in (self.words, self.original):
                        model = previous.PresetOracle(words, args, phase, mode, entry=source.ENTRY).run()
                        self.assertEqual(model.calls, [(source.CALLEE, *packet(args))])
                        self.assertEqual(model.r[29], previous.STACK + phase)
        self.receipt('packet', cases=len(cases) * 6, raw_words=85, real_word_differences=46,
            original_and_selected_complete_49_word_packets_equal=True,
            no_private_schedule_fault_prefix_or_whole_owner_installation_claim=True)

    def test_02_actual_native32_all_shapes_and_two_effective_controls(self):
        params = ','.join(('%s p%d' % ('s16' if i < 2 else 'u32', i)) for i in range(49))
        capture = ','.join('p%d' % i for i in range(49))
        fixture = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
static u32 captured[49],count,original[5];
__attribute__((noinline,noclone)) void func_1516D99C(''' + params + '''){
 u32 values[49]={''' + capture + '''};u32 i;count++;for(i=0;i<49;i++)captured[i]=values[i];}
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
        variants = [(name, body, '-O2', True) for name, body in source.candidates().items()]
        variants += [('selected-O0', source.SELECTED, '-O0', True),
            ('negative-word', source.SELECTED.replace('0x155, arg1,', '0x155, (u16)arg1,'), '-O2', False),
            ('negative-coordinate', source.SELECTED.replace('(s16)(arg0 >> 16)', '(s16)arg0'), '-O2', False)]
        for name, body, profile, expected in variants:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, expected, (name, result.returncode))
        self.receipt('native-packets', all_14_shapes_O2=True, selected_O0=True, cases_per_shape=65536,
            two_effective_controls=True, explicit_49_word_capture_provider=True,
            coordinate_parameters_use_actual_signed_halfword_types=True,
            not_actual_factory_private_ABI_or_retail_schedule_or_installed_match=True)


if __name__ == '__main__':
    unittest.main()
