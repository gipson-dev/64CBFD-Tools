"""Packed callback widths, live arithmetic, real updater and deferred renderer evidence."""
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_packed_record_scale as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests import test_game_packed_record_updater as updater

RECORD = 0x20000


def fixture(intensity=127, counter=1, delta=1, speed=3, base=0xFEDC, record=RECORD, step=source.DELTA):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-1024, 512)}
    memory.update({record + i: (i * 13 + 0xC5) & 255 for i in range(-16, 96)})
    for offset, value in ((0x1F, intensity), (0x24, counter), (0x26, speed), (0x2C, base >> 8), (0x2D, base & 255)):
        put(memory, record + offset, value, 1)
    put(memory, step, delta)
    return memory


def reference(memory, record=RECORD, step=source.DELTA):
    memory = dict(memory)
    value = read(memory, record + 31, 1)
    if read(memory, record + 36, 1):
        if value != 255:
            value = signed((value + read(memory, step) * 128) & 0xFFFFFFFF)
            value = min(value, 255)
            put(memory, record + 31, value, 1)
    elif value:
        value = signed((value - read(memory, step) * read(memory, record + 38, 1)) & 0xFFFFFFFF)
        value = max(value, 0)
        put(memory, record + 31, value, 1)
    if read(memory, record + 36, 1) == 0 and value == 0:
        return memory, 1
    base = read(memory, record + 44, 1) * 256 + read(memory, record + 45, 1)
    result = signed((base * value) & 0xFFFFFFFF) // 128
    put(memory, record + 22, result, 2)
    put(memory, record + 20, result, 2)
    return memory, 0


class ScaleOracle(MaskOracle):
    def __init__(self, words, memory, record=RECORD, phase=0, fault=None, entry=source.ENTRY):
        super().__init__(words, memory, entry=entry, arguments=(record,), phase=phase, fault=fault)

    def execute(self, word):
        if word >> 26 != 32:
            return super().execute(word)
        self.dispatched_word, self.own_instruction = word, True
        try:
            CopyOracle.execute(self, word)
        finally:
            self.own_instruction = False

    def record_call(self, target):
        raise AssertionError(('unexpected leaf call', target))


def state(model):
    return model.memory, model.r, model.f, model.lo, model.events, model.accesses


def controls():
    return {
        'early-byte-truncation': source.SELECTED.replace('value = (s32)((u32)value +', 'value = (u8)((u32)value +'),
        'signed-intensity': source.SELECTED.replace('value = record[0x1F]', 'value = (s8)record[0x1F]'),
        'wrong-fade-speed': source.SELECTED.replace('record[0x26]', 'record[0x27]'),
        'premature-completion': source.SELECTED.replace('record[0x24] == 0 && value == 0', 'record[0x24] == 0'),
        'wrong-product-scale': source.SELECTED.replace('scale >>= 7;', 'scale >>= 8;'),
        'lost-second-extent': source.SELECTED.replace('    *(s16 *)(record + 0x14) = scale;\n', ''),
    }


class PackedRecordScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>47I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_exact_guarded_slot_all_neighbors_and_closed_load_schedule(self):
        self.assertEqual(self.words, self.truth)
        before, diagnostics = build.compile_owner(self.root, self.out,
            (self.out / 'before-preset_owner').read_text(), 'before')
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
        f = new[1][source.FUNCTION]
        raw = new[0][f['value']:f['value'] + f['size']]
        data, rel = source.normalize(raw, source.RELOCATIONS)
        self.assertEqual(rel[76], source.RELOCATIONS[80])
        self.assertNotIn(80, rel)
        for i in range(47):
            bad = bytearray(raw)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), source.RELOCATIONS)
        for at in source.RELOCATIONS:
            bad = dict(source.RELOCATIONS)
            bad.pop(at)
            with self.assertRaises(ValueError):
                source.normalize(raw, bad)
        self.assertEqual(struct.unpack_from('>I', data, 84)[0], 0x03190019)
        self.receipt('owner', words=47, raw_differences=3, guarded_differences=0,
            unchanged_neighbors=len(new[1]) - 1, pools_and_relative_relocations_fixed=True,
            all_word_flips_and_missing_relocations_rejected=True,
            closed_T8_T9_operand_exchange_before_commutative_multu=True, LO16_moved_80_to_76=True)

    def test_02_all_intensity_bytes_word_boundaries_and_record_aliases(self):
        count = 0
        deltas = (0, 1, 2, 255, 256, 0xFFFFFFFF, 0xFFFFFFFE, 0x80000000, 0x7FFFFFFF, 0x01000000, 0x87654321)
        for i in range(2048):
            for record in (RECORD, STACK + 32, source.DELTA - 28):
                memory = fixture(i & 255, (i >> 3) & 1, deltas[(i // 7) % len(deltas)],
                    (i * 19) & 255, (i * 65521) & 65535, record)
                expected = reference(memory, record)
                pair = [ScaleOracle(w, memory, record).run() for w in (self.words, self.truth)]
                self.assertEqual(state(pair[0]), state(pair[1]))
                self.assertEqual((pair[0].memory, pair[0].r[2]), expected)
                raw = ScaleOracle(self.raw, memory, record).run()
                self.assertEqual((raw.memory, raw.r[2]), expected)
                self.assertEqual([e for e in raw.events if e[0] == 'W'], [e for e in pair[0].events if e[0] == 'W'])
                count += 1
        for intensity, counter in ((255, 1), (0, 0)):
            model = ScaleOracle(self.words, fixture(intensity, counter)).run()
            self.assertFalse(any(e[0] == 'R' and e[1] == source.DELTA for e in model.events))
        self.receipt('semantics', cases=count, all_intensity_bytes=True, signed_word_wrap_and_clamps=True,
            raw_and_guarded_memory_return_write_traces_equal=True, stack_and_delta_aliases=True,
            raw_read_order_is_not_retail_fault_order=True, bypasses_do_not_read_delta=True)

    def test_03_all_fired_retail_guest_access_prefixes(self):
        count = 0
        for intensity in (0, 1, 127, 255):
            for counter in (0, 1):
                for phase in (0, 8):
                    memory = fixture(intensity, counter, 0xFFFFFFFF)
                    whole = ScaleOracle(self.words, memory, phase=phase).run()
                    for fault in range(whole.accesses):
                        pair = [ScaleOracle(w, memory, phase=phase, fault=fault) for w in (self.words, self.truth)]
                        for model in pair:
                            with self.assertRaises(AccessFault):
                                model.run()
                        self.assertEqual(state(pair[0]), state(pair[1]))
                        count += 1
        self.receipt('prefixes', paired_fired_access_faults=count, guarded_only=True,
            emitted_guest_not_portable_C_or_hardware_fault_claim=True)

    def test_04_effective_compiled_negatives(self):
        cases = [(v, c, d, s, b) for v in (0, 1, 127, 128, 254, 255) for c in (0, 1)
            for d in (1, 0xFFFFFFFF, 0x87654321) for s in (3, 255) for b in (0xFFFF, 0x8081)]
        for name, body in controls().items():
            _, words, _ = source.measure(self.root, self.out, 'negative-' + name, body)
            failures = 0
            for case in cases:
                memory = fixture(*case)
                model = ScaleOracle(words, memory).run()
                failures += (model.memory, model.r[2]) != reference(memory)
            self.assertGreater(failures, 0, name)
        self.receipt('controls', six_effective_compiled_negatives=True, mutants_receive_no_matching_guards=True)

    def test_05_actual_native32_C_O2_O0_and_controls(self):
        fixture_c = '''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;
static s32 D_800BE9E4;static u8 record[80] __attribute__((aligned(16))),expected[80];
''' + source.SELECTED + '''
static s32 (*volatile invoke)(u8*)=func_1516ECAC;
static int run(void){u32 i,j,d,v,c,b,p,s;int result;static const u32 steps[]={0,1,2,255,256,0xFFFFFFFFu,0xFFFFFFFEu,0x80000000u,0x7FFFFFFFu,0x01000000u,0x87654321u};
 if(sizeof(void*)!=4||sizeof(s32)!=4)return 10;
 for(i=0;i<8192;i++){for(j=0;j<80;j++)record[j]=expected[j]=(u8)(j*13+0xC5);
  v=i&255;c=(i>>3)&1;d=steps[(i/7)%11];s=(i*19)&255;b=(i*65521)&65535;
  record[31]=expected[31]=(u8)v;record[36]=expected[36]=(u8)c;record[38]=expected[38]=(u8)s;
  record[44]=expected[44]=(u8)(b>>8);record[45]=expected[45]=(u8)b;
  if(c){if(v!=255){v+=d*128;if((s32)v>=256)v=255;expected[31]=(u8)v;}}
  else if(v){v-=d*s;if(v&0x80000000u)v=0;expected[31]=(u8)v;}
  result=c==0&&v==0?1:0;
  if(!result){p=b*v;p=(u32)((s32)p>>7);*(s16*)(expected+22)=(s16)p;*(s16*)(expected+20)=(s16)p;}
  D_800BE9E4=(s32)d;if(invoke(record)!=result)return 11;
  for(j=0;j<80;j++)if(record[j]!=expected[j])return 12;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for name, body, profile, ok in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(fixture_c.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-misleading-indentation', '-Wno-unused-parameter', str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, ok, (name, result.returncode))
        self.receipt('native', actual_selected_C=True, cases_per_O2_O0=8192,
            six_effective_compiled_negatives=True, no_signed_overflow_or_negative_shift_relaxation=True)

    def test_06_independent_original_assembly_and_rebases(self):
        data, fs, rel = parse_object(self.obj)
        f = fs[source.FUNCTION]
        normalized, moved = source.normalize(data[f['value']:f['value'] + f['size']], source.RELOCATIONS)
        data = bytearray(data)
        data[f['value']:f['value'] + f['size']] = normalized
        rel = {p: v for p, v in rel.items() if not f['value'] <= p < f['value'] + f['size']}
        rel.update({f['value'] + p: v for p, v in moved.items()})
        text, missing = emit_function(bytes(data), f, rel, source.FUNCTION, {'D_800BE9E4': source.DELTA})
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], capture_output=True, check=True)
        for index, text_delta, step in ((0, 0, source.DELTA), (1, 0x10000, 0x80318004), (2, -0x10000, 0x80507FFC)):
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % (source.ENTRY + text_delta))
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, index))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    '--defsym=D_800BE9E4=0x%X' % step, '-o', str(elf), str(self.out / (label + '-reloc.o'))], capture_output=True, check=True)
                outputs.append(sections(elf)['.text'][1][:188])
            self.assertEqual(outputs[0], outputs[1])
            memory = fixture(counter=0, step=step)
            model = ScaleOracle(list(struct.unpack('>47I', outputs[0])), memory, entry=source.ENTRY + text_delta).run()
            self.assertEqual((model.memory, model.r[2]), reference(memory, step=step))
        self.receipt('rebases', independent_original_text_delta_pairs=3, signed_low_carry_boundaries=True)

    def test_07_actual_updater_dispatch_then_real_callback_and_cleanup(self):
        image = (self.out / 'before-elf').read_bytes()
        connected = {}
        for entry, rom, count in ((source.ENTRY, source.ROM, 47), (0x1516972C, 0x196BDC, 28)):
            words = self.words if entry == source.ENTRY else list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        update_words = list(struct.unpack_from('>48I', image, elf_slot_offset(image, 0x1516D678, 192)))
        self.assertEqual(update_words, list(struct.unpack_from('>48I', self.rom, 0x19AB28)))
        self.assertEqual(struct.unpack_from('>9I', self.rom, 0x231660)[1], source.ENTRY)
        removed = active = 0
        for i in range(256):
            memory = updater.fixture(i, 1, 1)
            for off, value in ((31, i), (38, 3), (44, 0xFE), (45, 0xDC)):
                put(memory, updater.RECORD + off, value, 1)
            callback_input = dict(memory)
            put(callback_input, updater.RECORD + 36, max(i - 1, 0), 1)
            callback_state, result = reference(callback_input, updater.RECORD)
            model = updater.UpdaterOracle(update_words, memory, connected=connected).run()
            expected = dict(callback_state)
            calls = [(source.ENTRY, updater.RECORD)]
            if result:
                removed += 1
                self.assertEqual(model.unlink_lifetime, [0])
                put(expected, updater.BINDING + 4, 0, 2)
                put(expected, updater.RECORD, 0, 1)
                calls.extend([(0x1516972C, updater.RECORD), (updater.UNLINK, updater.RECORD)])
            else:
                active += 1
                self.assertEqual(model.unlink_lifetime, [])
                y = updater.short(read(expected, updater.RECORD + 16, 2))
                velocity = updater.short(read(expected, updater.RECORD + 24, 2))
                fixed = (y * 256 + read(expected, updater.RECORD + 37, 1) + velocity) & 0xFFFFFFFF
                put(expected, updater.RECORD + 16, signed(fixed) >> 8, 2)
                put(expected, updater.RECORD + 37, fixed, 1)
            for base, length in ((updater.RECORD, 64), (updater.BINDING, 16)):
                for j in range(length):
                    self.assertEqual(model.memory[base + j], expected[base + j])
            self.assertEqual(model.callbacks, [])
            self.assertEqual(model.calls, calls)
        self.assertGreater(removed, 0)
        self.assertGreater(active, 0)
        self.receipt('connected', actual_updater_callback_cleanup_cases=256, actual_table_index=1,
            removed=removed, active=active, callback_not_opaque=True, lower_unlink_destructor_providers_opaque=True)

    def test_08_deferred_renderer_inherits_stack_word_through_actual_texture_helpers(self):
        connected = {}
        for entry, rom, count in ((0x15142E24, 0x1702D4, 102), (0x15094FE8, 0xC2498, 30),
                (0x15095060, 0xC2510, 29)):
            words = struct.unpack_from('>%dI' % count, self.rom, rom)
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        words = list(struct.unpack_from('>153I', self.rom, 0x19ABE8))
        texture, output, private = 0x30000, 0x40000, STACK - 0x98

        class RendererAudit(MaskOracle):
            def __init__(self, memory):
                super().__init__(words, memory, entry=0x1516D738,
                    arguments=(output, RECORD, 0x12345678), connected=connected)
                self.render_modes = []

            def record_call(self, target):
                self.calls.append((target, *self.arguments(2)))

            def hook(self, target):
                self.assert_target(target)
                result = 0x123456 if target == 0x1514306C else self.r[4]
                if target == 0x15142FBC:
                    self.render_modes.append(self.r[5])
                for reg in (1, 2, 3, *range(4, 16), 24, 25):
                    self.r[reg] = 0xA5000000 + reg
                self.r[2] = result

            def assert_target(self, target):
                assert target in (0x1514306C, 0x150950D4, 0x15142FBC, 0x15095760), hex(target)

        count = 0
        for kind in (0, 5):
            mode = 2 if kind == 5 else 1
            for mode_hit in (False, True):
                for texture_hit in (False, True):
                    for seed in (0, 0x100000, 0xA55A33CC):
                        memory = fixture()
                        for base, size in ((texture, 32), (output, 128), (0x800D2C90, 0x120),
                                (0x800DD1B0, 0x80), (0x800BE616, 4), (0x800BE9F0, 4), (0x8008CA4C, 4)):
                            memory.update({base + i: 0 for i in range(size)})
                        for offset in range(0x1A, 0x23):
                            put(memory, RECORD + offset, 0, 1)
                        put(memory, texture, 0x1000)
                        put(memory, texture + 10, kind, 1)
                        put(memory, 0x8008CA4C, texture)
                        put(memory, 0x800D2C9C, 0x200)
                        put(memory, 0x800DD1BC, mode if mode_hit else -1, 2)
                        for address, value in ((0x800DD1B0, 0x123456 if texture_hit else -1),
                                (0x800DD208, 2), (0x800DD20C, 0x100), (0x800DD210, 0x100),
                                (0x800DD214, private + 0x84)):
                            put(memory, address, value)
                        put(memory, private + 0x5C, seed)
                        model = RendererAudit(memory).run()
                        expected = seed if mode_hit else (0x100000 if mode == 2 else 0)
                        self.assertEqual(model.render_modes, [expected | 0x2E00])
                        accesses = [e for e in model.events if e[0] in ('R', 'W') and e[1] == private + 0x5C]
                        self.assertEqual(accesses[0][0], 'R' if mode_hit else 'W')
                        if mode_hit:
                            self.assertEqual(accesses, [('R', private + 0x5C, 4, seed)])
                        if not texture_hit:
                            self.assertEqual(read(model.memory, private + 0x94), 0x800D2C90)
                        count += 1
        self.receipt('renderer-deferral', cases=count, real_texture_cache_wrapper_and_packet_writer=True,
            cache_hit_reads_inherited_sp_5C=True, packet_writer_only_touches_sp_94=True,
            lower_image_selection_submission_and_final_projection_opaque=True,
            no_renderer_install_or_C_exact_credit=True)


if __name__ == '__main__':
    unittest.main()
