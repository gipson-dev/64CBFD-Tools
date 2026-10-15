"""Type gate, complete 49-word packet, private ABI, native C and real factory chain."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_type_preset as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_factory_preset_wrapper as wrapper
from tools.tests import test_game_record_factory as factory
from tools.tests import test_game_packed_color_match as previous
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

ARGS = (0x87654321, 0xFEDCBA98, 0xFFFFFF80, 0x12345678)


def packet(args):
    result = [0] * 49
    for index, value in ((0, 5), (3, 4), (5, 255), (6, 255), (7, 255), (12, 2),
            (19, 8), (27, 292), (28, 292), (31, args[1]), (34, args[0]),
            (35, 12), (38, 129), (39, 2), (41, 1), (45, 5),
            (47, args[2] & 255), (48, args[3])):
        result[index] = value & 0xFFFFFFFF
    return tuple(result)


def gate_address(args, table=source.TABLE, stride=0x32C):
    return (table + args[0] * stride) & 0xFFFFFFFF


def prime_gate(memory, args, kind=0x3A, table=source.TABLE):
    wrong, correct = gate_address(args, table, 0x330), gate_address(args, table)
    for at in (wrong, correct):
        memory.update({at + i: 0 for i in range(4)})
    memory.update({correct + i: value for i, value in enumerate((kind, 0xA5, 0x5A, 0xC3))})


def type_after_homes(memory, args, phase=0, table=source.TABLE):
    memory = dict(memory)
    put(memory, wrapper.STACK + phase - 4, 0xDEAD0000)
    for index, value in enumerate(args):
        put(memory, wrapper.STACK + phase + index * 4, value)
    return read(memory, gate_address(args, table), 1)


class ActorPresetOracle(wrapper.PresetOracle):
    def __init__(self, words, args=ARGS, kind=0x3A, phase=0, mode=0, fault=None,
            entry=source.ENTRY, callee=source.CALLEE, table=source.TABLE):
        super().__init__(words, args, phase, mode, fault, entry, callee)
        prime_gate(self.memory, args, kind, table)


def controls():
    return {
        'wrong-type': source.SELECTED.replace('type == 0x3A', 'type == 0x3B'),
        'wrong-stride': source.SELECTED.replace('* 0x32C', '* 0x330'),
        'word-gate': source.SELECTED.replace('u8 type = D_800CC2D4[(u32)arg0 * 0x32C]',
            'u32 type = *(u32 *)(D_800CC2D4 + (u32)arg0 * 0x32C)'),
        'wrong-actor-bit': source.SELECTED.replace('0, 0, arg0, 0xC,', '0, 0, (arg0 ^ 1), 0xC,'),
        'wrong-second-bit': source.SELECTED.replace('0x124, 0, 0, arg1,', '0x124, 0, 0, (arg1 ^ 1),'),
        'wide-flag': source.SELECTED.replace('(u8)arg2', 'arg2'),
        'wrong-last': source.SELECTED.replace('(u8)arg2, arg3)', '(u8)arg2, arg1)'),
        'wrong-preset': source.SELECTED.replace('0x124, 0x124', '0x125, 0x124'),
    }


def narrow_expressions():
    return {
        'narrow-actor': source.SELECTED.replace('0, 0, arg0, 0xC,', '0, 0, (u8)arg0, 0xC,'),
        'narrow-second': source.SELECTED.replace('0x124, 0, 0, arg1,', '0x124, 0, 0, (u16)arg1,'),
    }


class ActorPresetCandidateTests(unittest.TestCase):
    def test_scoped_recipes_fingerprints_and_match_gate(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(len(set(source.PATHS.values())), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        before = 'extern s32 D_800BE9E4;\ns32 func_1516ED68() {\n    return 0;\n}\nvoid other(void) { }\n'
        for body in source.candidates().values():
            self.assertNotIn('volatile', body)
            self.assertEqual(source.build.body(body, source.FUNCTION), body[body.index('void func_'):].strip())
            self.assertTrue(source.recovered_owner(before, body).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        for count, differences, diagnostics in ((90, 0, ''), (91, 1, ''), (91, 0, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, differences=differences, diagnostics=diagnostics))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))


class ActorPresetMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>91I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = previous.PackedColorMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_direct_words_real_padder_and_all_owner_neighbors(self):
        self.assertEqual(self.words, self.truth)
        obj, diagnostics = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
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
        self.assertEqual(struct.unpack_from('>4I', self.rom, 0x56F50),
            (0x0D45BB5A, 0x00592823, 0x1000003E, 0x24020001))
        self.receipt('owner', raw_and_padded_words=91, differences=0, new_guards=0,
            unchanged_neighbors=len(new[1]) - 1, pools_and_relative_relocations_fixed=True, frame=208,
            direct_caller_sets_its_own_V0_after_call=True)

    def test_02_all_gate_bytes_full_packet_private_stack_and_clobbers(self):
        cases = [(kind, tuple((kind * 1664525 + j * 0x1234567 + 1013904223) & 0xFFFFFFFF for j in range(4))) for kind in range(256)]
        cases += [(0x3A, ARGS), (0x3A, (0,) * 4), (0x3A, (0xFFFFFFFF,) * 4)]
        cases += [(0x3A, tuple((i * 1664525 + j * 0x372159AB + 1013904223) & 0xFFFFFFFF for j in range(4))) for i in range(512)]
        called = rejected = 0
        visits = set()
        for kind, args in cases:
            for phase in (0, 8):
                for mode in range(3):
                    models = [ActorPresetOracle(w, args, kind, phase, mode) for w in (self.words, self.truth)]
                    observed = type_after_homes(models[0].memory, args, phase)
                    pair = [model.run() for model in models]
                    self.assertEqual(wrapper.state(pair[0]), wrapper.state(pair[1]))
                    expected = [(source.CALLEE, *packet(args))] if observed == 0x3A else []
                    self.assertEqual(pair[0].calls, expected)
                    self.assertEqual(pair[0].r[29], wrapper.STACK + phase)
                    visits |= pair[0].visits
                    self.assertEqual(pair[0].events[0], ('W', wrapper.STACK + phase - 4, 4, 0xDEAD0000))
                    if expected:
                        called += 1
                        call = next(i for i, event in enumerate(pair[0].events) if event[0] == 'CALL')
                        self.assertEqual(pair[0].events[call - 1], ('W', wrapper.STACK + phase - 72, 4, args[0]))
                    else:
                        rejected += 1
                        self.assertEqual(pair[0].r[2], observed)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 364, 4)))
        self.receipt('abi', cases=len(cases) * 6, called=called, rejected=rejected, all_256_types=True,
            all_91_instructions_visited=True, full_49_word_packet_and_private_state_equal=True,
            wrapped_word_indices_are_backed_guest_fixtures_not_native_array_domain=True,
            provider_home_clobbers=True, final_actor_word_store_in_call_delay=True)

    def test_03_home_and_outgoing_aliases_and_fired_fault_prefixes(self):
        aliases = 0
        for phase in (0, 8):
            for address in (wrapper.STACK + phase - 4, wrapper.STACK + phase + 4,
                    wrapper.STACK + phase + 8, wrapper.STACK + phase + 12,
                    wrapper.STACK + phase - 208 + 0x4C):
                index = (((address - source.TABLE) // 4) * pow(203, -1, 2**30)) % (2**30)
                args = (index, 0x3A123456, 0x3A6543FF, 0x3AABCDEF)
                pair = [ActorPresetOracle(w, args, phase=phase, mode=2) for w in (self.words, self.truth)]
                kind = type_after_homes(pair[0].memory, args, phase)
                pair = [model.run() for model in pair]
                self.assertEqual(wrapper.state(pair[0]), wrapper.state(pair[1]))
                self.assertEqual(pair[0].calls, [(source.CALLEE, *packet(args))] if kind == 0x3A else [])
                aliases += 1
        prefixes = 0
        for kind in (0, 0x3A, 255):
            for phase in (0, 8):
                whole = ActorPresetOracle(self.words, ARGS, kind, phase, 2).run()
                for fault in range(whole.accesses):
                    pair = [ActorPresetOracle(w, ARGS, kind, phase, 2, fault) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(wrapper.state(pair[0]), wrapper.state(pair[1]))
                    prefixes += 1
        self.receipt('prefixes', backed_guest_aliases=aliases, paired_fired_guest_faults=prefixes,
            private_registers_stack_and_events_equal=True, not_portable_C_fault_or_hardware_claim=True)

    def test_04_eight_effective_compiled_controls(self):
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            model = ActorPresetOracle(words).run()
            self.assertNotEqual(model.calls, [(source.CALLEE, *packet(ARGS))], name)
        for name, body in narrow_expressions().items():
            _, words, row = source.measure(self.root, self.out, 'prototype-' + name, body)
            self.assertEqual((row['words'], row['differences'], row['diagnostics']), (91, 0, ''))
            self.assertEqual(words, self.words)
        self.receipt('controls', effective_compiled_controls=8, no_matching_guards=True,
            two_narrowing_casts_IDO_redundant_under_actual_callee_prototype=True,
            native_word_capture_controls_check_those_expression_widths_separately=True)

    def test_05_native32_bounded_actor_array_word_capture_and_controls(self):
        params = ','.join('%s p%d' % ('s16' if i < 2 else 'u32', i) for i in range(49))
        capture = ','.join('p%d' % i for i in range(49))
        harness = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
u8 D_800CC2D4[0x330*512+4] __attribute__((aligned(16)));
static u32 captured[49],count;
__attribute__((noinline,noclone)) void func_1516D99C(''' + params + '''){
 u32 values[49]={''' + capture + '''};u32 i;count++;for(i=0;i<49;i++)captured[i]=values[i];}
''' + source.SELECTED + '''
static void (*volatile invoke)(s32,s32,s32,s32)=func_1516ED68;
static int run(void){u32 i,j,index,kind,a1,a2,a3,offset,e[49];
 if(sizeof(void*)!=4||sizeof(s32)!=4)return 10;
 for(i=0;i<131072;i++){
  index=i>>8;kind=i&255;offset=index*0x32C;
  D_800CC2D4[offset]=(u8)kind;D_800CC2D4[offset+1]=0xA5;D_800CC2D4[offset+2]=0x5A;D_800CC2D4[offset+3]=0xC3;
  a1=0xFEDC0000u|((i*17)&65535);a2=0x87650000u|((i*31)&65535);a3=i*1664525u+1013904223u;
  for(j=0;j<49;j++){captured[j]=0xDEADBEEFu;e[j]=0;}
  e[0]=5;e[3]=4;e[5]=e[6]=e[7]=255;e[12]=2;e[19]=8;e[27]=e[28]=292;
  e[31]=a1;e[34]=index;e[35]=12;e[38]=129;e[39]=2;e[41]=1;e[45]=5;e[47]=a2&255;e[48]=a3;
  count=0;invoke((s32)index,(s32)a1,(s32)a2,(s32)a3);
  if(count!=(kind==58?1u:0u))return 11;
  for(j=0;j<49;j++)if(captured[j]!=(kind==58?e[j]:0xDEADBEEFu))return 12;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        variants = [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)]
        variants += [('negative-' + n, b, '-O2', False) for n, b in controls().items()]
        variants += [('native-only-' + n, b, '-O2', False) for n, b in narrow_expressions().items()]
        for name, body, profile, expected in variants:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, expected, (name, result.returncode))
        self.receipt('native', cases_per_O2_O0=131072, actor_indices=[0, 511], all_256_types_per_actor=True,
            all_eight_controls_effective=True, two_additional_native_narrowing_controls=True,
            explicit_word_capture_provider=True,
            real_narrow_callee_storage_qualified_separately=True, arbitrary_guest_addresses_not_native_C_claim=True)

    def test_06_independent_original_assembly_table_and_call_rebases(self):
        data, fs, rel = parse_object(self.obj)
        anchors = {'func_1516D99C': source.CALLEE, 'D_800CC2D4': source.TABLE}
        text, missing = emit_function(data, fs[source.FUNCTION], rel, source.FUNCTION, anchors)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for index, (delta, table) in enumerate(((0, source.TABLE), (0x10000, 0x80317FFC), (-0x10000, 0x80528004))):
            entry, callee = source.ENTRY + delta, source.CALLEE - delta
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=func_1516D99C=0x%X' % callee, '--defsym=D_800CC2D4=0x%X' % table,
                    '-o', str(elf), str(self.out / (label + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(sections(elf)['.text'][1][:364])
            self.assertEqual(outputs[0], outputs[1])
            for kind in (0x39, 0x3A):
                model = ActorPresetOracle(list(struct.unpack('>91I', outputs[0])), ARGS, kind,
                    entry=entry, callee=callee, table=table).run()
                self.assertEqual(model.calls, [(callee, *packet(ARGS))] if kind == 0x3A else [])
        self.receipt('rebases', independent_original_text_table_call_pairs=3, signed_low_carry_boundaries=True,
            full_packet_and_rejected_path_checked=True)

    def test_07_actual_factory_allocator_registration_and_rejected_gate(self):
        before = (self.out / 'before-elf').read_bytes()
        connected = {}
        for entry, rom, count in ((source.CALLEE, 0x19AE4C, 125), (0x15167A68, 0x194F18, 28)):
            words = list(struct.unpack_from('>%dI' % count, before, elf_slot_offset(before, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        rejected = null = records = 0
        for i in range(256):
            args = (i + 256, 0xFEDC0000 | i, 0xA55A0000 | i * 257, i * 1664525 + 1013904223)
            args = tuple(a & 0xFFFFFFFF for a in args)
            result, kind = (0 if i % 4 == 0 else factory.RECORD), (0x39 if i % 5 == 0 else 0x3A)
            model = factory.FactoryOracle(self.words, args, result, phase=(i & 1) * 8,
                entry=source.ENTRY, connected=connected, chain=True)
            prime_gate(model.memory, args, kind)
            model.run()
            if kind != 0x3A:
                rejected += 1
                self.assertEqual(model.calls, [])
                baseline = factory.fixture(args)
                for address in range(factory.RECORD, factory.RECORD + 76):
                    self.assertEqual(model.memory[address], baseline[address])
                continue
            self.assertEqual(model.calls[0], (source.CALLEE, *packet(args)))
            self.assertEqual(model.calls[1], (0x15167A68, 17, args[3], 76, 0, args[2] & 255, 1))
            self.assertEqual(model.calls[2], (factory.ALLOCATE, 76, 1, 0, 0, 1))
            self.assertEqual(len(model.calls), 3 if not result else 4)
            if result:
                records += 1
                expected = factory.reference(factory.fixture(packet(args)), packet(args), result)[0]
                for address in range(factory.RECORD + 14, factory.RECORD + 76):
                    self.assertEqual(model.memory[address], expected[address])
                self.assertEqual(model.memory[factory.RECORD], 17)
                self.assertEqual(model.memory[factory.RECORD + 1], args[3] & 255)
                self.assertEqual(model.memory[factory.RECORD + 12], args[2] & 255)
            else:
                null += 1
        self.assertTrue(rejected and null and records)
        self.receipt('chain', actual_wrapper_factory_allocator_cases=256, gate_rejected=rejected,
            null=null, registered=records, actual_callee_words=[125, 28],
            only_lower_heap_and_registration_providers_opaque=True, no_full_gameplay_or_host_claim=True)


if __name__ == '__main__':
    unittest.main()
