"""Ordered float rejection, caller window, owner isolation and literal image gate."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_rectangle_bounds_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.check_game_data_layout import audit_layout

WIDTH, HEIGHT, BASE = screen.SYMBOLS.values()
RECORD = 0x22000
DIMENSIONS = (0, 1, 2, 3, 320, 0x01000001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
FLOATS = (0, 0x80000000, 1, 0x80000001, bits(-1.0), bits(1.0), 0x3FFFFFFF,
          bits(2.0), 0x40000001, bits(3.0), 0x7F7FFFFF, 0xFF7FFFFF,
          0x7F800000, 0xFF800000, 0x7FC00001, 0xFFC12345)
INDICES = (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def cases():
    for width, height in itertools.product(DIMENSIONS, repeat=2):
        maximum = bits(floating(bits(float(signed(width)))) - 2.0)
        vertical = bits(float(signed(height)))
        default = [bits(2.0), maximum, 0, vertical]
        yield width, height, tuple(default)
        for field, value in itertools.product(range(4), FLOATS):
            bounds = default.copy()
            bounds[field] = value
            yield width, height, tuple(bounds)
        yield width, height, (0x7FC00001,) * 4


def fixture(width, height, bounds, index=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x80, 0x80)}
    memory.update({RECORD + i: (i * 13 + 0xA5) & 255 for i in range(-16, 0x190)})
    for address in (WIDTH, HEIGHT, BASE):
        memory.update({address + i: 0xA5 for i in range(4)})
    put(memory, WIDTH, width)
    put(memory, HEIGHT, height)
    put(memory, BASE, (RECORD - index * 0x180) & 0xFFFFFFFF)
    for offset, value in zip((0x2C, 0x30, 0x24, 0x28), bounds):
        put(memory, RECORD + offset, value)
    return memory


def reference(width, height, bounds):
    left, right, top, bottom = map(floating, bounds)
    maximum = floating(bits(floating(bits(float(signed(width)))) - 2.0))
    vertical = floating(bits(float(signed(height))))
    return int(not (left < 2.0 or maximum < right or top < 0.0 or vertical < bottom))


class AccessFault(Exception):
    pass


class BoundsOracle(TriangleOracle):
    def __init__(self, words, memory, index=0, phase=0, entry=screen.ENTRY, connected=None):
        self.fault, self.accesses = None, 0
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(index,), connected=connected)

    def get(self, address, size):
        if self.fault == self.accesses:
            raise AccessFault()
        self.accesses += 1
        return super().get(address, size)


class WindowEnd(Exception):
    pass


class CallerWindow(BoundsOracle):
    def record_call(self, target):
        assert target == screen.ENTRY
        self.calls.append((target, self.r[4]))

    def put(self, address, value, size):
        super().put(address, value, size)
        if address == RECORD + 1:
            assert size == 1
            raise WindowEnd()


class GameRectangleBoundsMatchTests(unittest.TestCase):
    run_native = native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-rectangle-bounds-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_before = cls.owner_before.replace(screen.SELECTED, screen.ORIGINAL)
        cls.owner_before = cls.owner_before.replace('s32 func_1501AE94(s32 arg0);', 's32 func_1501AE94();')
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'direct')
        cls.old_meta, cls.old = screen.compile_candidate(cls.root, cls.out, 'placeholder', screen.ORIGINAL)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>44I', cls.rom, screen.ROM))

    def test_01_complete_direct_body_original_profile_and_no_pool(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
                          self.meta['pool_bytes'], self.meta['diagnostics']), (44, 0, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.old_meta['body_words'], self.old_meta['differences']), (3, 37))
        self.assertTrue(all(not value[1] for name, value in sections(self.out / 'direct.o').items()
            if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
        self.assertNotIn('volatile', screen.SELECTED)

    def test_02_rounding_boundaries_nan_full_word_indices_and_complete_state(self):
        count, visited = 0, set()
        for position, (width, height, bounds) in enumerate(cases()):
            index = INDICES[position % len(INDICES)]
            for phase in (0, 8):
                memory = fixture(width, height, bounds, index)
                pair = [BoundsOracle(words, memory, index, phase).run() for words in (self.retail, self.words)]
                for field in ('memory', 'events', 'r', 'f', 'condition', 'reads'):
                    self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
                self.assertEqual(pair[1].r[2], reference(width, height, bounds))
                self.assertEqual(pair[1].memory, memory)
                self.assertEqual(pair[1].calls, [])
                visited.update(pair[1].visits)
                count += 1
        self.assertEqual(count, 10692)
        self.assertEqual(reference(320, 0x7FFFFFFF, (bits(2.0), bits(3.0), 0, 0x4F000000)), 1)
        self.assertEqual(BoundsOracle(self.words, fixture(320, 240, (0x7FC00001,) * 4)).run().r[2], 1)
        self.assertEqual(BoundsOracle(self.old, fixture(320, 240, (bits(2.0), bits(3.0), 0, bits(1.0)))).run().r[2], 0)
        (self.out / 'guest.json').write_text(json.dumps(dict(cases=count, visited_words=len(visited),
            all44_words_byte_exact=True, sparse_full_word_indices_guest_only=True,
            quiet_nan_ordered_results=True, FCSR_EPC_exception_hardware_not_claimed=True), indent=2) + '\n')

    def test_03_short_circuit_reads_missing_storage_and_fired_access_cuts(self):
        paths = ((bits(1.0), bits(3.0), 0, bits(1.0)),
                 (bits(2.0), bits(400.0), 0, bits(1.0)),
                 (bits(2.0), bits(3.0), bits(-1.0), bits(1.0)),
                 (bits(2.0), bits(3.0), 0, bits(300.0)),
                 (bits(2.0), bits(3.0), 0, bits(1.0)))
        counts = []
        fired = 0
        for phase, bounds in itertools.product((0, 8), paths):
            memory = fixture(320, 240, bounds)
            normal = BoundsOracle(self.words, memory, phase=phase).run()
            addresses = [address for address, _, _ in normal.reads]
            self.assertEqual(addresses[:4], [WIDTH, BASE, RECORD + 0x2C, HEIGHT])
            counts.append(len(addresses))
            for address, size, _ in normal.reads:
                for byte in range(size):
                    missing = dict(memory)
                    del missing[address + byte]
                    with self.assertRaises(AssertionError):
                        BoundsOracle(self.words, missing, phase=phase).run()
            for offset in (0x30, 0x24, 0x28):
                if RECORD + offset not in addresses:
                    missing = {a: b for a, b in memory.items() if not RECORD + offset <= a < RECORD + offset + 4}
                    self.assertEqual(BoundsOracle(self.words, missing, phase=phase).run().r[2], 0)
            for fault in range(normal.accesses):
                pair = [BoundsOracle(words, memory, phase=phase) for words in (self.retail, self.words)]
                for model in pair:
                    model.fault = fault
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, fault)
                self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f, pair[0].condition),
                                 (pair[1].memory, pair[1].events, pair[1].r, pair[1].f, pair[1].condition))
                fired += 1
            terminal = BoundsOracle(self.words, memory, phase=phase)
            terminal.fault = normal.accesses
            terminal.run()
        self.assertEqual(counts, [4, 5, 6, 7, 7] * 2)
        self.assertEqual(fired, 58)
        (self.out / 'faults.json').write_text(json.dumps(dict(fired_pairs=fired, counts=counts), indent=2) + '\n')

    def native_source(self, body):
        constants = ','.join('0x%Xu' % word for word in FLOATS)
        dimensions = ','.join('0x%Xu' % word for word in DIMENSIONS)
        return ('''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
static s32 D_800BE620,D_800BE624,D_800BE628;
static u8 storage[4*0x180+32] __attribute__((aligned(16))),saved[sizeof(storage)];
typedef char ABI[(sizeof(void*)==4 && sizeof(f32)==4 && sizeof(s32)==4)?1:-1];
static u32 values[]={''' + constants + '};\nstatic u32 dimensions[]={' + dimensions + '};\n' + body + '''
static int check(void){
 u32 i,j,k,v,seed=0x12345678u;f32 limit,height,*record;int expected,result;u8 *base=storage+16;
 for(j=0;j<sizeof(storage);j++)storage[j]=(u8)(j*13+0xA5);
 for(i=0;i<8192;i++)for(k=0;k<4;k++){
  D_800BE620=(s32)dimensions[i%9];D_800BE624=(s32)dimensions[i/9%9];D_800BE628=(s32)(u32)base;
  record=(f32*)(base+k*0x180);limit=(f32)D_800BE620;limit=limit-2.0f;height=(f32)D_800BE624;
  record[11]=2.0f;record[12]=limit;record[9]=0.0f;record[10]=height;
  for(j=0;j<4;j++){
   seed=seed*1664525u+1013904223u;
   if((i&3)==0)v=0x7FC00001u;else if((i&3)==1)continue;else v=values[(seed>>24)%16];
   *(u32*)(record+(j==0?11:j==1?12:j==2?9:10))=v;
  }
  expected=1;
  if(record[11]<2.0f)expected=0;
  else if(limit<record[12])expected=0;
  else if(record[9]<0.0f)expected=0;
  else if(height<record[10])expected=0;
  for(j=0;j<sizeof(storage);j++)saved[j]=storage[j];
  result=func_1501AE94((s32)k);
  if(result!=expected)return 1;
  for(j=0;j<sizeof(storage);j++)if(storage[j]!=saved[j])return 2;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
''')

    def test_04_native32_actual_body_and_effective_nan_margin_index_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(screen.SELECTED), profile), (0, ''))
        controls = [('inside-conjunction', screen.SELECTED[:screen.SELECTED.index('    if (')] +
            '    return (record[11] >= 2.0f) && (maxX >= record[12]) && (record[9] >= 0.0f) && (maxY >= record[10]);\n}'),
            ('wrong-margin', screen.SELECTED.replace('D_800BE620 - 2.0f', 'D_800BE620')),
            ('wrong-index', screen.SELECTED.replace('0x180', '0x184'))]
        for name, body in controls:
            self.assertNotEqual(body, screen.SELECTED)
            code, _ = self.run_native('negative-' + name, self.native_source(body))
            self.assertIn(code, (1, 2))
        (self.out / 'native.json').write_text(json.dumps(dict(cases_per_profile=32768,
            comparisons=65536, profiles=['O2', 'O0'], SSE2_single_precision=True,
            native_indices=[0, 1, 2, 3], complete_storage_unchanged=True), indent=2) + '\n')

    def test_05_actual_owner_neighbors_pools_and_padders(self):
        objects = [compile_owner(self.root, self.out, source, name) for source, name in
                   ((self.owner_before, 'owner-before'), (self.owner_after, 'owner-after'))]
        self.assertEqual([warnings for _, warnings in objects], [[], []])
        before, after = [parse_object(obj) for obj, _ in objects]
        self.assertEqual(before[1].keys(), after[1].keys())
        for name in before[1]:
            a, b = before[1][name], after[1][name]
            if name != screen.FUNCTION:
                self.assertEqual(before[0][a['value']:a['value'] + a['size']], after[0][b['value']:b['value'] + b['size']], name)
                self.assertEqual({o - a['value']: r for o, r in before[2].items() if a['value'] <= o < a['value'] + a['size']},
                                 {o - b['value']: r for o, r in after[2].items() if b['value'] <= o < b['value'] + b['size']}, name)
        isolated = parse_object(self.out / 'direct.o')
        target = after[1][screen.FUNCTION]
        self.assertEqual(after[0][target['value']:target['value'] + 176], isolated[0][:176])
        self.assertEqual({o - target['value']: r for o, r in after[2].items()
            if target['value'] <= o < target['value'] + 176}, isolated[2])
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        with (self.root / 'conker/retail_layout.us.txt').open(newline='') as stream:
            rows = [row for row in csv.DictReader(stream) if row['filename'] == 'game_476D0']
        self.assertEqual({row['function'] for row in rows}, set(before[1]))
        fragments = []
        for row in rows:
            original = self.root / ('conker/asm/nonmatchings/game_476D0/' + row['function'] + '.s')
            if original.exists():
                fragments.append(original.read_text())
            else:
                lines = ['glabel ' + row['function']]
                for address in range(int(row['address'], 0), int(row['end'], 0), 4):
                    offset = screen.ROM + address - screen.ENTRY
                    word = struct.unpack_from('>I', self.rom, offset)[0]
                    lines.append('/* %X %08X %08X */ .word 0x%08X' % (offset, address, word, word))
                fragments.append('\n'.join(lines))
        reference_path = self.out / 'owner-reference.s'
        reference_path.write_text('\n'.join(fragments))
        padded = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            asm = self.out / (script + '.s')
            args = [str(objects[1][0]), str(self.root / 'conker/retail_layout.us.txt'), 'game_476D0', str(asm)] if script == 'pad_c_object.py' else [
                str(objects[1][0]), str(reference_path), str(asm), '--filename', 'game_476D0']
            result = subprocess.run([sys.executable, str(self.root / 'tools' / script), *args,
                '--word-patches', str(self.root / 'conker/retail_word_patches.us.csv')], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(obj), str(asm)], check=True, capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0], padded[1])
        self.assertEqual(padded[0][1][screen.FUNCTION]['size'], 176)
        (self.out / 'owner.json').write_text(json.dumps(dict(neighbors=len(after[1]) - 1,
            both_full_owner_padders_identical=True, normalized_pools_equal=True), indent=2) + '\n')

    def test_06_independent_original_rebases_and_real_caller_store_window(self):
        asm = self.out / 'original.s'
        asm.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' +
            (self.root / 'conker/asm/nonmatchings/game_476D0/func_1501AE94.s').read_text())
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        layouts = [(screen.ENTRY, screen.SYMBOLS),
            (0x1521AE94, dict(D_800BE620=0x80107FFC, D_800BE624=0x80108004, D_800BE628=0x80217FFC)),
            (0x1531AE94, dict(D_800BE620=0x80208004, D_800BE624=0x80317FFC, D_800BE628=0x80418004))]
        for i, (entry, symbols) in enumerate(layouts):
            with patch.object(screen, 'ENTRY', entry), patch.object(screen, 'SYMBOLS', symbols):
                _, candidate = screen.compile_candidate(self.root, self.out, 'rebase-' + str(i))
            ld = self.out / ('original-' + str(i) + '.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(ld), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            self.assertEqual(candidate, list(struct.unpack('>44I', sections(elf)['.text'][1])))
        call_entry = 0x1501AE1C
        caller = list(struct.unpack_from('>5I', self.rom, 0x482CC))
        count = 0
        for bounds in ((bits(2.0), bits(3.0), 0, bits(1.0)), (bits(1.0), bits(3.0), 0, bits(1.0)), (0x7FC00001,) * 4):
            for index, phase in itertools.product((0, 1, 2), (0, 8)):
                memory = fixture(320, 240, bounds, index)
                pair = []
                for words in (self.retail, self.words):
                    connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 176, 4), words))
                    model = CallerWindow(caller, memory, index, phase, call_entry, connected)
                    model.r[16], model.r[17], model.r[14] = index * 0x180, BASE, RECORD
                    model.f[6] = bits(1.0)
                    with self.assertRaises(WindowEnd):
                        model.run()
                    self.assertEqual(model.memory[RECORD + 1], reference(320, 240, bounds))
                    expected = dict(memory)
                    put(expected, RECORD + 0x84, bits(1.0))
                    put(expected, RECORD + 1, reference(320, 240, bounds), 1)
                    self.assertEqual(model.memory, expected)
                    self.assertEqual(model.calls, [(screen.ENTRY, index)])
                    pair.append(model)
                self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f),
                                 (pair[1].memory, pair[1].events, pair[1].r, pair[1].f))
                count += 1
        self.assertEqual(count, 18)
        (self.out / 'caller.json').write_text(json.dumps(dict(cases=count, authentic_caller_words=5,
            complete_350_word_caller_not_exercised=True, post_status_store_stop=True), indent=2) + '\n')

    def test_07_literal_whole_image_protected_inputs_and_game_data(self):
        current = (self.root / self.paths['elf']).read_bytes()
        offset = elf_slot_offset(current, screen.ENTRY, 176)
        self.assertEqual(offset, elf_slot_offset(self.before, screen.ENTRY, 176))
        source = (self.root / screen.SOURCE).read_text()
        expected = bytearray(self.before)
        if source == self.owner_after:
            expected[offset:offset + 176] = struct.pack('>44I', *self.retail)
            with patch.multiple(descriptor.screen, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
                self.assertEqual(size_offset, descriptor.size_field(current))
            struct.pack_into('>I', expected, size_offset, 176)
        else:
            self.assertEqual(source, self.owner_before)
        self.assertEqual(current, bytes(expected))
        for name in ('guards', 'progress', 'layout', 'makefile'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'linked-audit.json').write_text(json.dumps(dict(installed=source == self.owner_after,
            literal_image_only_target_slot_and_size_changed=True, data=data), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
