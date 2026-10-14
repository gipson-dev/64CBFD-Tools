"""Three direct donor transfers: active ABI, complete owners and closed image."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from tools.tests import remaining_donor_checkpoint as donor_checkpoint
from unittest.mock import patch

from tools.experiments import game_byte_exact_donor_candidates as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import load_symbol_addrs
from tools.tests import test_game_actor_burst_packet_match as producer
from tools.tests import test_game_actor_burst_consumer_match as consumer
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

TIMERS, SELECTOR, COUNT, TABLE = 0x800DBFF4, 0x800CC40F, 0x800DC9F0, 0x80089F9C
ACTOR, RELEASE, SUBMIT, HANDLER = 0x21000, 0x1517E134, 0x1509BFB0, 0x18001000
BEFORE_ELF = '294eba92c9b31ea335a560d67f8536a30993fc1fa429796df1c486fb532f7ddd'


class DonorOracle(producer.BurstOracle):
    def __init__(self, words, memory, spec, arguments=(), phase=0, mutation=False, fault=None):
        super().__init__(words, memory, entry=spec['entry'], arguments=arguments or (0,), phase=phase)
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = consumer.TrackedCode(self.code, self)
        self.spec, self.mutation = spec, mutation

    def access(self):
        if self.own_instruction and self.spec['entry'] <= self.current_pc < self.spec['entry'] + self.spec['words'] * 4:
            if self.accesses == self.root_fault:
                raise consumer.AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        assert target in (RELEASE, SUBMIT) or HANDLER <= target < HANDLER + 1024
        args = tuple(self.arguments(6 if target == SUBMIT else 2 if target == RELEASE else 1))
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == RELEASE and self.mutation:
            self.put(COUNT, 0x12345678, 4)
            self.put(ACTOR + 0x168, 255, 1)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344


def fixture():
    memory = {producer.STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    memory.update({ACTOR + i: 0xA5 for i in range(0x300)})
    for i in range(4):
        put(memory, TIMERS + i, (0, 1, 255, 7)[i], 1)
    put(memory, COUNT, 7)
    put(memory, ACTOR + 0x154, 0x25000)
    put(memory, ACTOR + 0x168, 3, 1)
    for i in range(256):
        put(memory, TABLE + i * 4, HANDLER + i * 4)
    for i in (0, 1, 3, 203):
        put(memory, SELECTOR + i * 812, i & 255, 1)
    return memory


class GameByteExactDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-byte-exact-donors'
        cls.out.mkdir(exist_ok=True)
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        assert cls.baseline['elf'] == BEFORE_ELF
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.records, cls.words, cls.retail = {}, {}, {}
        for name, spec in source.TARGETS.items():
            cls.records[name], cls.words[name] = source.compile_candidate(cls.root, cls.out, name, spec)
            cls.retail[name] = list(struct.unpack_from('>%dI' % spec['words'], cls.rom, spec['rom']))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_all_three_emit_complete_retail_words_without_guards(self):
        for name, spec in source.TARGETS.items():
            self.assertEqual((self.records[name]['words'], self.records[name]['differences'], self.records[name]['warnings']),
                (spec['words'], 0, []))
            self.assertEqual(self.words[name], self.retail[name])
        self.receipt('direct', functions=3, words=[26, 32, 27], new_guards=0,
            active_headers_prototypes_and_descriptive_locals=True)

    def test_02_each_timer_byte_zero_and_unsigned_edges(self):
        name = 'func_15125628'
        seen = set()
        for slot, value in itertools.product(range(4), range(256)):
            memory = fixture()
            put(memory, TIMERS + slot, value, 1)
            expected = dict(memory)
            for index in range(4):
                byte = read(memory, TIMERS + index, 1)
                put(expected, TIMERS + index, byte - 1 if byte else 0, 1)
            models = [DonorOracle(body, memory, source.TARGETS[name]).run() for body in (self.retail[name], self.words[name])]
            self.assertEqual(models[0].memory, expected)
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            seen.update(models[0].visits)
        self.assertEqual(seen, set(range(0x15125628, 0x15125690, 4)))
        self.receipt('timer', cases=1024, all26_words=True, zero_never_wraps=True)

    def test_03_full_unsigned_selector_six_word_calls_and_stack_arguments(self):
        name = 'func_1507D158'
        cases = 0
        for index, selector, phase, payload in itertools.product((0, 1, 3, 203), (0, 1, 127, 128, 255), (0, 8),
                ((0, 0, 0, 0), (0xFFFFFFFF, 0x80000000, 0x12345678, 0x87654321))):
            memory = fixture()
            put(memory, SELECTOR + index * 812, selector, 1)
            args = (index, *payload)
            models = [DonorOracle(body, memory, source.TARGETS[name], args, phase).run() for body in (self.retail[name], self.words[name])]
            self.assertEqual(models[0].calls, [(SUBMIT, (3, selector | 0x2000, *payload))])
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            cases += 1
        self.receipt('selector', cases=cases, six_exact_arguments=True, full32_bit_payload_and_two_SP_phases=True)

    def test_04_attachment_reloads_wrapping_counter_and_live_subtype_dispatch(self):
        name = 'func_151411E4'
        cases, seen = 0, set()
        for attached, mutation, count, subtype, phase in itertools.product((False, True), (False, True),
                (0, 1, 0x80000000, 0xFFFFFFFF), (0, 3, 255), (0, 8)):
            memory = fixture()
            put(memory, ACTOR + 0x154, 0x25000 if attached else 0)
            put(memory, ACTOR + 0x168, subtype, 1)
            put(memory, COUNT, count)
            models = [DonorOracle(body, memory, source.TARGETS[name], (ACTOR,), phase, mutation).run()
                for body in (self.retail[name], self.words[name])]
            calls = [(RELEASE, (0x25000, ACTOR))] if attached else []
            live = 255 if attached and mutation else subtype
            calls.append((HANDLER + live * 4, (ACTOR,)))
            self.assertEqual(models[0].calls, calls)
            self.assertEqual(read(models[0].memory, COUNT), ((0x12345678 if attached and mutation else count) - 1) & 0xFFFFFFFF)
            loads = [event for event in models[0].events if event[:3] == ('R', ACTOR + 0x154, 4)]
            self.assertEqual(len(loads), 2 if attached else 1)
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(0x151411E4, 0x15141250, 4)))
        self.receipt('release', cases=cases, double_read=True, live_count_subtype_callback=True,
            unsigned_counter_wrap=True, all27_words=True, helpers_still_bounded_hooks=True)

    def test_05_all_fired_root_access_prefixes(self):
        cuts = 0
        for name, spec in source.TARGETS.items():
            args = {'func_15125628': (), 'func_1507D158': (3, 1, 2, 3, 4), 'func_151411E4': (ACTOR,)}[name]
            memory = fixture()
            complete = DonorOracle(self.retail[name], memory, spec, args, mutation=True).run()
            for cut in range(complete.accesses):
                models = [DonorOracle(body, memory, spec, args, mutation=True, fault=cut)
                    for body in (self.retail[name], self.words[name])]
                for model in models:
                    with self.assertRaises(consumer.AccessBoundary):
                        model.run()
                self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                cuts += 1
        self.receipt('prefixes', fired_pairs=cuts, PC_and_modeled_BD=True, not_hardware_fault_acceptance=True)

    def test_06_complete_owner_raw_neighbors_pools_warnings_and_both_padders(self):
        counts = {}
        for name, spec in source.TARGETS.items():
            before = (self.out / ('before-' + spec['owner'])).read_text()
            old, w0 = source.compile_complete_owner(self.root, self.out, before, spec['owner'] + '-before')
            new, w1 = source.compile_complete_owner(self.root, self.out, source.recovered_owner(before, name), spec['owner'] + '-after')
            self.assertEqual(w0, w1)
            old_text, old_funcs, old_reloc = parse_object(old)
            new_text, new_funcs, new_reloc = parse_object(new)
            self.assertEqual(set(old_funcs), set(new_funcs))
            for function, previous in old_funcs.items():
                current = new_funcs[function]
                self.assertEqual(previous['size'], current['size'], function)
                if function == name:
                    continue
                self.assertEqual(old_text[previous['value']:previous['value'] + previous['size']],
                    new_text[current['value']:current['value'] + current['size']], function)
                relative = lambda table, info: {at - info['value']: v for at, v in table.items()
                    if info['value'] <= at < info['value'] + info['size']}
                self.assertEqual(relative(old_reloc, previous), relative(new_reloc, current), function)
            self.assertEqual(normalized_pools(old), normalized_pools(new))
            padded = pad_c_object.emit_padded_assembly(new, self.root / 'conker/retail_layout.us.txt', spec['owner'],
                word_patches_path=self.root / 'conker/retail_word_patches.us.csv')
            self.assertIn(name, padded)
            isolated = self.out / (name + '.o')
            asm = self.out / (name + '-reference.s')
            original = (self.root / ('conker/asm/nonmatchings/' + spec['owner'] + '/' + name + '.s')).read_text()
            if 'endlabel ' + name not in original:
                original += '\nendlabel ' + name + '\n'
            asm.write_text(original)
            original_path = self.out / (name + '-original.s')
            original_path.write_text('.include "' + str(self.root / 'tools/asm-processor/prelude.inc') + '"\n' + original)
            original_obj = original_path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(original_obj), str(original_path)],
                check=True, capture_output=True)
            def link(obj, label, entry, symbols):
                script = self.out / (name + '-' + label + '.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', name,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)],
                    check=True, capture_output=True)
                return list(struct.unpack_from('>%dI' % spec['words'], sections(elf)['.text'][1]))
            symbols = load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt'))
            symbols.update(D_800DBFF4=TIMERS, D_800DBFF5=TIMERS + 1, D_800DBFF6=TIMERS + 2,
                D_800DBFF7=TIMERS + 3, D_800CC40F=SELECTOR, D_800DC9F0=COUNT, D_80089F9C=TABLE,
                func_1509BFB0=SUBMIT, func_1517E134=RELEASE)
            salt = dict(symbols, D_800DBFF4=0x90007FFF, D_800DBFF5=0x90008000,
                D_800DBFF6=0x90008001, D_800DBFF7=0x90008002, D_800CC40F=0x90007FFC,
                D_800DC9F0=0x91008004, D_80089F9C=0x92007FFC)
            layout = self.out / (name + '-layout.csv')
            layout.write_text('section,filename,function,address,end\n'
                'game,%s,%s,0x%X,0x%X\n' % (spec['owner'], name, spec['entry'], spec['entry'] + spec['words'] * 4))
            for index, text in enumerate((emit_padded_assembly(isolated, asm, filename=spec['owner']),
                    pad_c_object.emit_padded_assembly(isolated, layout, spec['owner']))):
                path = self.out / (name + '-pad%d.s' % index)
                path.write_text('.include "' + str(self.root / 'tools/asm-processor/prelude.inc') + '"\n' + text)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
                    check=True, capture_output=True)
                data, functions, _ = parse_object(path.with_suffix('.o'))
                self.assertEqual(functions[name]['size'], spec['words'] * 4)
                for version, (entry, anchors) in enumerate(((spec['entry'], symbols), (0x15228008, salt))):
                    reference = link(original_obj, 'original%d-%d' % (index, version), entry, anchors)
                    self.assertEqual(link(path.with_suffix('.o'), 'pad%d-%d' % (index, version), entry, anchors), reference)
            counts[name] = len(old_funcs) - 1
        self.receipt('owners', neighbors=counts, raw_words_relative_relocs_pools_warnings_fixed=True,
            full_owner_padding_and_both_isolated_padders=True, independent_original_rebased_carry_links=True)

    def test_07_whole_elf_and_guards_unchanged_only_three_C_rows(self):
        self.assertEqual(donor_checkpoint.previous_input((self.root / 'conker/build/conker.us.elf').read_bytes(), 'conker/build/conker.us.elf', self.root), (self.out / 'before-elf').read_bytes())
        self.assertEqual((self.root / 'conker/retail_word_patches.us.csv').read_bytes(), (self.out / 'before-guards').read_bytes())
        installed = []
        for name, spec in source.TARGETS.items():
            before = (self.out / ('before-' + spec['owner'])).read_text()
            actual = (self.root / ('conker/src/' + spec['owner'] + '.c')).read_text()
            after = source.recovered_owner(before, name)
            self.assertIn(actual, (before, after))
            if actual == after:
                installed.append(name)
        expected = (self.out / 'before-progress').read_bytes()
        for name in installed:
            matching = [line for line in expected.splitlines(keepends=True) if b',' + name.encode() + b',' in line]
            self.assertEqual(len(matching), 1)
            self.assertTrue(matching[0].endswith(b',asm\n'))
            expected = expected.replace(matching[0], matching[0].replace(b',asm\n', b',c\n'))
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), expected)
        data = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertTrue(data['exact'])
        self.assertEqual((data['bytes'], data['owner_count']), (189088, 720))
        self.receipt('image', installed=installed, all_ELF_and_guard_bytes_fixed=True,
            converted_rows_only=len(installed), protected_data=data)

    def test_08_effective_semantic_and_immutable_input_controls(self):
        changes = {'func_15125628': ('!= 0', '!= 1'), 'func_1507D158': ('0x2000', '0x4000'),
            'func_151411E4': ('-= 1', '-= 2')}
        args = {'func_15125628': (), 'func_1507D158': (3, 1, 2, 3, 4), 'func_151411E4': (ACTOR,)}
        for name, (old, new) in changes.items():
            spec = source.TARGETS[name]
            body = spec['body'].replace(old, new)
            self.assertNotEqual(body, spec['body'])
            _, words = source.compile_candidate(self.root, self.out, name, spec, body, name + '-negative')
            memory = fixture()
            wrong = DonorOracle(words, memory, spec, args[name]).run()
            right = DonorOracle(self.retail[name], memory, spec, args[name]).run()
            self.assertNotEqual((wrong.memory, wrong.calls), (right.memory, right.calls), name)
        rb = Path.read_bytes
        for file in ('conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv', 'conker/progress.csv'):
            path = self.root / file
            bad = bytearray(rb(path))
            bad[-1] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_whole_elf_and_guards_unchanged_only_three_C_rows()
        self.receipt('controls', three_effective_compiled_semantic_controls=True,
            three_effective_ELF_guard_progress_corruptions=True)

    def test_09_native32_timer_pairs_and_untouched_bytes(self):
        body = source.TARGETS['func_15125628']['body']
        native = 'typedef int s32;typedef unsigned char u8;u8 D_800DBFF4[4];\n' + body + '''
static int run(void){unsigned a,b,i;u8 before[4];
for(a=0;a<256;a++)for(b=0;b<256;b++){
 D_800DBFF4[0]=a;D_800DBFF4[1]=b;D_800DBFF4[2]=255-a;D_800DBFF4[3]=255-b;
 for(i=0;i<4;i++)before[i]=D_800DBFF4[i];
 func_15125628();
 for(i=0;i<4;i++)if(D_800DBFF4[i]!=(before[i]?before[i]-1:0))return 1;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status));__builtin_unreachable();}
'''
        for profile in ('-O2', '-O0'):
            path = self.out / ('native-timer' + profile + '.c')
            path.write_text(native)
            binary = path.with_suffix('')
            compiled = subprocess.run(['cc', '-m32', profile, '-std=c99', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)],
                capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(subprocess.run([str(binary)]).returncode, 0)
        self.receipt('native', timer_pairs_per_profile=65536, profiles=['O2', 'O0'],
            not_all_wrapper_or_handler_native_acceptance=True)


if __name__ == '__main__':
    unittest.main()
