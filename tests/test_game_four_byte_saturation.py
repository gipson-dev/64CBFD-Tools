"""Four byte counters: direct words, conditional accesses, callback and full image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_four_byte_saturation as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_quad_edge_emitter as edge
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_table_debris_native import TYPES


def fixture(values=(0, 254, 255, 128), step=2, counters=source.COUNTERS, increment=source.STEP):
    memory = {edge.STACK+i: (i*17+0xA5) & 255 for i in range(-256, 256)}
    memory.update({counters+i: 0xA5 for i in range(-4, 8)})
    memory.update({counters+i: v for i, v in enumerate(values)})
    memory[increment] = step
    return memory


def reference(initial, counters=source.COUNTERS, increment=source.STEP, mutate=False):
    memory, events = dict(initial), []
    for i in range(4):
        current = memory[counters+i]
        events.append(('R', counters+i, 1, current))
        if mutate and counters+i == increment:
            memory[increment] = (current+73) & 255
        if current < 255:
            step = memory[increment]
            events.append(('R', increment, 1, step))
            if mutate:
                memory[increment] = (step+73) & 255
            value = min(current+step, 255)
            memory[counters+i] = value
            events.append(('W', counters+i, 1, value))
    return memory, events


class CounterOracle(edge.EdgeOracle):
    def __init__(self, words, memory, increment=source.STEP, mutate=False, **kwargs):
        self.increment, self.mutate = increment, mutate
        super().__init__(words, memory, (), entry=kwargs.pop('entry', source.ENTRY), **kwargs)

    def get(self, address, size):
        value = super().get(address, size)
        if self.mutate and self.own_instruction and address == self.increment:
            self.memory[address] = (value+73) & 255
        return value

    def record_call(self, target):
        self.calls.append(target)

    def hook(self, target):
        for register in (*range(1, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]


def controls():
    b = source.SELECTED
    return {
        'signed-counter': b.replace('(s32)D_800DD2A0[index]', '(s32)(s8)D_800DD2A0[index]').replace(
            'value = D_800DD2A0[index]', 'value = (s8)D_800DD2A0[index]'),
        'signed-increment': b.replace('+ D_800BE9A0', '+ (s8)D_800BE9A0'),
        'wrap-before-clamp': b.replace('value = D_800DD2A0[index] + D_800BE9A0;', 'value = (u8)(D_800DD2A0[index] + D_800BE9A0);'),
        'wrong-ceiling': b.replace('value = 255;', 'value = 254;'),
        'missing-last': b.replace('index < 4', 'index < 3'),
        'crossed-store': b.replace('D_800DD2A0[index] = value;', 'D_800DD2A0[(index+1) & 3] = value;'),
        'unconditional-saturated': b.replace('D_800DD2A0[index] < 255', 'D_800DD2A0[index] <= 255'),
        'skip-zero-step-store': b.replace('D_800DD2A0[index] = value;', 'if (D_800BE9A0) D_800DD2A0[index] = value;'),
        'cached-step': b.replace('    s32 value;', '    s32 value;\n    s32 step = D_800BE9A0;').replace('+ D_800BE9A0;', '+ step;'),
    }


def native_harness():
    return TYPES+r'''
u8 D_800DD2A0[4], D_800BE9A0;
void func_1516D400(void);static void(*volatile invoke)(void)=func_1516D400;
static int run(void){u32 a,b,i;u8 old[4];if(sizeof(void*)!=4)return 21;
 for(a=0;a<256;a++)for(b=0;b<256;b++){
  old[0]=(u8)a;old[1]=(u8)(a+1);old[2]=(u8)(a^128);old[3]=(u8)(a^255);
  for(i=0;i<4;i++)D_800DD2A0[i]=old[i];D_800BE9A0=(u8)b;invoke();
  for(i=0;i<4;i++){u32 expected=(u32)old[i]+b;if(expected>255)expected=255;
   if(D_800DD2A0[i]!=expected)return 20;}if(D_800BE9A0!=b)return 22;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


class FourByteSaturationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>58I', cls.rom, source.ROM))

    def receipt(self, name, **data):
        (self.out / (name+'.json')).write_text(json.dumps(data, indent=2)+'\n')

    def test_01_direct_shape_all_owner_neighbors_bindings_and_guards(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['differences'], self.row['diagnostics']), (58, 0, ''))
        source.checked_object(self.obj)
        obj, diag = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'neighbor-baseline')
        self.assertFalse(diag)
        old, new = parse_object(obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value']+f['size']], new[0][g['value']:g['value']+g['size']], name)
            relative = lambda o, f: {a-f['value']: v for a, v in o[2].items() if f['value'] <= a < f['value']+f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(self.row['pools'], {})
        self.receipt('shape', words=58, frame=0, neighbors=len(old[1])-1, all_raw_neighbors_identical=True,
            accessor_byte_view_preserves_prior_guard_fingerprints=True, padding_words=0, target_guards=0)

    def test_02_byte_boundaries_all_steps_order_and_saved_state(self):
        count, visits = 0, set()
        for value, step, phase, mutate in itertools.product((0, 1, 127, 128, 253, 254, 255), range(256), (0, 8), (False, True)):
            memory = fixture((value, (value+1) & 255, value ^ 128, value ^ 255), step)
            expected, events = reference(memory, mutate=mutate)
            models = [CounterOracle(w, memory, phase=phase, mutate=mutate).run() for w in (self.truth, self.words)]
            for m in models:
                self.assertEqual((m.memory, m.events, m.calls), (expected, events, []))
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            visits.update(models[0].visits)
            count += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY+232, 4)))
        for step in (0, 255):
            memory = fixture((255,)*4, step)
            models = [CounterOracle(w, memory).run() for w in (self.truth, self.words)]
            for m in models:
                self.assertEqual((m.memory, m.events), reference(memory))
                self.assertEqual(m.accesses, 4)
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
        self.receipt('boundaries', paired_cases=count+2, all_increment_bytes=True, all_58_instructions_visited=True,
            all_saturated_no_increment_read_or_write=True, unchanged_stack_and_surrounding_bytes=True,
            live_mutations_guest_only_not_portable_C_concurrency=True)

    def test_03_native32_exhaustive_O2_O0_UBSan_and_effective_negatives(self):
        harness = self.out / 'native-harness.c'
        harness.write_text(native_harness())
        exits = {}
        negatives = list(controls().items())[:6]
        for label, body, opt, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)]+[
                ('negative-'+n, b, '-O2', False) for n, b in negatives]:
            path = self.out / ('native-'+label+'.c')
            path.write_text(TYPES+'typedef signed char s8;\nextern u8 D_800DD2A0[4], D_800BE9A0;\n'+body)
            command = ['cc', '-m32', opt, '-std=c11', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie',
                '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            else:
                command += ['-Wno-type-limits']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertEqual(result.returncode, 0 if valid else 20, label)
            exits[label] = result.returncode
        self.receipt('native', exhaustive_start_step_pairs_per_O2_O0=65536, separate_units=True,
            selected_UBSan=True, native_alias_or_fault_claim=False, exits=exits)

    def test_04_effective_compiled_guest_access_and_value_negatives(self):
        rejected = []
        cases = [((0, 127, 254, 255), n) for n in (0, 1, 2, 127, 128, 255)]+[((255,)*4, 255)]
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            obj, _, _ = source.measure(self.root, self.out, 'negative-'+name, body)
            data, funcs = source.build.link_owner(self.root, self.out, obj, source.OWNER)
            f = funcs[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (f['size']//4), data, f['value']))
            for values, step in cases:
                memory = fixture(values, step)
                m = CounterOracle(words, memory).run()
                if (m.memory, m.events) != reference(memory):
                    rejected.append(name)
                    break
            else:
                self.fail('Ineffective compiled negative: '+name)
        self.receipt('negatives', compiled_observable_rejections=rejected, unsupported_instruction_failures_accepted=False)

    def test_05_fired_instruction_fault_prefixes(self):
        count = 0
        for values, step, phase in itertools.product(((0, 127, 254, 255), (255,)*4), (0, 255), (0, 8)):
            memory = fixture(values, step)
            complete = CounterOracle(self.words, memory, phase=phase).run()
            for fault in range(complete.accesses):
                models = []
                for w in (self.truth, self.words):
                    m = CounterOracle(w, memory, phase=phase, fault=fault)
                    with self.assertRaises(edge.AccessFault):
                        m.run()
                    self.assertEqual(m.accesses, fault)
                    models.append(m)
                self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                count += 1
        self.receipt('faults', fired_prefix_pairs=count, guest_instruction_order_only=True)

    def test_06_independent_original_rebases_low_carries_and_guest_aliases(self):
        original = (self.out / 'before-preset_original').read_text().split('glabel '+source.FUNCTION+'\n', 1)[1].split('endlabel '+source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "'+str(self.root / 'conker/include/asm_processor_prelude.inc')+'"\n.type '+source.FUNCTION+
            ', @function\nglabel '+source.FUNCTION+'\n'+original+'\n.size '+source.FUNCTION+', . - '+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        text, funcs, rel = parse_object(path.with_suffix('.o'))
        f = funcs[source.FUNCTION]
        old = text[f['value']:f['value']+f['size']]
        old_rel = {a-f['value']: v for a, v in rel.items() if f['value'] <= a < f['value']+f['size']}
        raw, bindings = source.checked_object(self.obj)
        count = 0
        for entry, counters, increment in ((0x15201000, 0x80127FFE, 0x80218001),
                (0x15302000, 0x8013FFFE, 0x80220001), (0x15403000, 0x8014FFFE, 0x8014FFFE),
                (0x15504000, 0x8015FFFE, 0x80160000)):
            links = {'D_800DD2A%d' % i: counters+i for i in range(4)}
            links['D_800BE9A0'] = increment
            streams = []
            for i, (data, rows) in enumerate(((raw, bindings), (old, old_rel))):
                asm, missing = emit_function(data, dict(value=0, size=len(data)), rows, source.FUNCTION, links)
                self.assertFalse(missing)
                file = self.out / ('rebase-%X-%d.s' % (entry, i))
                file.write_text(asm)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(file.with_suffix('.o')), str(file)], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(file.with_suffix('.ld')), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % v for v in links.items()], '-o', str(file.with_suffix('.elf')), str(file.with_suffix('.o'))], check=True, capture_output=True)
                streams.append(list(struct.unpack_from('>58I', sections(file.with_suffix('.elf'))['.text'][1])))
            self.assertEqual(streams[0], streams[1])
            for values, step, mutate in itertools.product(((0, 127, 254, 255), (255,)*4), (0, 1, 255), (False, True)):
                memory = fixture(values, step, counters, increment)
                models = [CounterOracle(w, memory, increment=increment, mutate=mutate, entry=entry).run() for w in streams]
                for m in models:
                    self.assertEqual((m.memory, m.events), reference(memory, counters, increment, mutate))
                self.assertEqual(edge.state(models[0]), edge.state(models[1]))
                count += 1
        self.receipt('rebases', independent_original_sets=4, paired_cases=count,
            counter_addends_and_both_symbols_rebound=True, guest_only_overlap_and_mutation=True)

    def test_07_current_driver_and_actual_table_registration(self):
        image = (self.out / 'before-elf').read_bytes()
        at = elf_slot_offset(image, source.DRIVER, 92)
        driver = image[at:at+92]
        self.assertEqual(driver, self.rom[0x1944C0:0x19451C])
        table = image[elf_slot_offset(image, source.TABLE, 0x1484):][:0x1484]
        self.assertEqual(table, self.rom[0x22FF68:0x2313EC])
        self.assertEqual(struct.unpack_from('>I', table, 17*0x34+0x18)[0], source.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x231438)[0], source.ENTRY)
        expected_calls = [struct.unpack_from('>I', table, i*0x34+0x18)[0] for i in range(101)]
        expected_calls = [a for a in expected_calls if a]
        self.assertEqual(expected_calls.count(source.ENTRY), 1)
        count = 0
        for values, step, phase in itertools.product(((0, 127, 254, 255), (255,)*4), (0, 255), (0, 8)):
            memory = fixture(values, step)
            memory.update({source.TABLE+i: v for i, v in enumerate(table)})
            models = [CounterOracle(list(struct.unpack('>23I', driver)), memory, phase=phase, entry=source.DRIVER,
                connected=dict(zip(range(source.ENTRY, source.ENTRY+232, 4), w))).run() for w in (self.truth, self.words)]
            self.assertEqual(edge.state(models[0]), edge.state(models[1]))
            for m in models:
                self.assertEqual(m.calls, expected_calls)
                expected, _ = reference(memory)
                self.assertEqual([m.memory[source.COUNTERS+i] for i in range(4)], [expected[source.COUNTERS+i] for i in range(4)])
            count += 1
        self.receipt('callback', paired_cases=count, driver_words=23, table_records=101, reached_record=17,
            other_callbacks_opaque_and_clobbering=True, second_record_102_outside_this_driver=True,
            full_gameplay_claim=False)

    def test_08_object_word_binding_pool_and_input_corruption_rejection(self):
        text, funcs, rel = parse_object(self.obj)
        f = funcs[source.FUNCTION]
        for i in range(58):
            bad = bytearray(text)
            bad[f['value']+i*4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), funcs, rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad = dict(rel)
            bad[f['value']+at] = [(rel[f['value']+at][0][0], 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, funcs, bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source, 'sections', return_value={'.data': (0, b'X')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-'+key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        self.receipt('corruptions', words=58, relocation_bindings=20, unexpected_pool_rejected=True, frozen_inputs=len(source.PATHS))

    def test_09_preinstall_prediction_and_all_live_inputs(self):
        row = source.prelink_prediction(self.root, self.out)
        self.assertEqual((row['changed_ELF_bytes'], row['metadata_exclusions']), (164, 0))
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual(row['after'], {k: hashlib.sha256(v).hexdigest() for k, v in expected.items()})
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **row['after'])))


if __name__ == '__main__':
    unittest.main()
