"""Actor-type dispatch, complete owner/table binding and whole-image isolation."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_type_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.check_game_data_layout import audit_layout

ACTORS, PROVIDER, CALLER = 0x800CC2D0, 0x1503B9BC, 0x150345E4
INDICES = (0, 1, 25, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def selected(kind):
    return kind in (0, 1, 2, 3, 4, 0x80, 0xB0)


def fixture(index, kind, pool, caller=False, state=1, flag=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x200, 0x80)}
    actor = (ACTORS + index * 0x32C) & 0xFFFFFFFF
    memory[(actor + 4) & 0xFFFFFFFF] = kind
    memory.update({screen.TABLE + i: value for i, value in enumerate(pool)})
    if caller:
        memory.update({actor + i: 0xA5 for i in range(0x1D8)})
        put(memory, actor, state)
        put(memory, actor + 4, kind, 1)
        put(memory, actor + 5, flag, 1)
        put(memory, actor + 0x1D4, 1)
    return memory


class AccessFault(Exception):
    pass


class DispatchOracle(TriangleOracle):
    def __init__(self, words, memory, index=0, phase=0, mutation=0, entry=screen.ENTRY, connected=None):
        self.fault, self.accesses, self.in_hook = None, 0, False
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(index,), connected=connected)
        self.index, self.mutation = index, mutation

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault == self.accesses:
                raise AccessFault()
            self.accesses += 1

    def get(self, address, size):
        self.gate()
        return super().get(address, size)

    def put(self, address, value, size):
        self.gate()
        return super().put(address, value, size)

    def record_call(self, target):
        assert target in (screen.ENTRY, PROVIDER)
        args = (self.r[4],)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == PROVIDER and self.r[4] == self.index
        self.in_hook = True
        try:
            if self.mutation:
                self.put((ACTORS + self.index * 0x32C + 4) & 0xFFFFFFFF, 5, 1)
            for register in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[register] = 0xA5000000 + register
            self.f[:20] = [0xA5000000 + i for i in range(20)]
        finally:
            self.in_hook = False


class GameActorTypeDispatchMatchTests(unittest.TestCase):
    run_native = native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-type-dispatch-test'
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
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.meta, cls.words, cls.pool = screen.compile_candidate(cls.root, cls.out, 'direct')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>42I', cls.rom, screen.ROM))
        cls.original_pool = cls.rom[screen.TABLE_ROM:screen.TABLE_ROM + 32]
        cls.caller = list(struct.unpack_from('>81I', cls.rom, 0x61A94))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_direct_complete_slot_table_and_discriminating_controls(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['diagnostics'], self.meta['pool_bytes']), (42, 24, 0, '', 32))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.pool, self.original_pool)
        self.assertEqual(struct.unpack('>5I', self.pool[:20]), (screen.ENTRY + 144,) * 5)
        self.assertEqual(self.pool[20:], bytes(12))
        measurements = []
        for name, body in screen.candidates():
            meta, words, pool = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            measurements.append(meta)
            if meta['differences'] == 0:
                self.assertEqual(words, self.retail)
                self.assertEqual(pool, self.pool)
        self.assertEqual([m['differences'] for m in measurements], [0, 0, 0, 2, 31])
        self.receipt('controls', measurements=measurements)

    def test_02_guest_all_bytes_full_indices_mutations_and_fired_fault_prefixes(self):
        cases, cuts = 0, 0
        coverage = set()
        for kind, index, phase, mutation in itertools.product(range(256), INDICES, (0, 8), (0, 1)):
            memory = fixture(index, kind, self.pool)
            pair = [DispatchOracle(words, memory, index, phase, mutation).run() for words in (self.retail, self.words)]
            for field in ('memory', 'events', 'r', 'f', 'calls'):
                self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
            self.assertEqual(pair[0].calls, [(PROVIDER, (index,))] if selected(kind) else [])
            self.assertEqual(pair[0].memory[(ACTORS + index * 0x32C + 4) & 0xFFFFFFFF],
                5 if selected(kind) and mutation else kind)
            coverage.update(pair[0].visits)
            cases += 1
        self.assertEqual(cases, 6144)
        self.assertEqual(coverage, set(range(screen.ENTRY, screen.ENTRY + 168, 4)))
        for kind in range(256):
            memory = fixture(0, kind, self.pool)
            for words in (self.retail, self.words):
                if kind >= 5:
                    sparse = {a: v for a, v in memory.items() if not screen.TABLE <= a < screen.TABLE + 32}
                    DispatchOracle(words, sparse).run()
                broken = dict(memory)
                del broken[ACTORS + 4]
                with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                    DispatchOracle(words, broken).run()
        for kind in (0, 4, 5, 0x80, 0x81, 0xB0, 0xFF):
            memory = fixture(0, kind, self.pool)
            complete = DispatchOracle(self.words, memory).run()
            for cut in range(complete.accesses):
                pair = []
                for words in (self.retail, self.words):
                    model = DispatchOracle(words, memory)
                    model.fault = cut
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                    pair.append(model)
                for field in ('memory', 'events', 'r', 'f', 'calls', 'visits'):
                    self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
                cuts += 1
        for slot in range(5):
            broken = fixture(0, slot, self.pool)
            put(broken, screen.TABLE + slot * 4, 0x1BAD0000)
            for words in (self.retail, self.words):
                with self.assertRaisesRegex(AssertionError, 'unowned jump'):
                    DispatchOracle(words, broken).run()
        self.receipt('guest', cases=cases, fired_cut_pairs=cuts, covered_words=len(coverage))

    def native_source(self, body):
        return '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
u8 D_800CC2D4[26*0x32C];int count,expected,mutation,error;
void func_1503B9BC(s32 index){if(index!=expected)error=1;count++;if(mutation)D_800CC2D4[index*0x32C]=5;}
''' + body + '''
int check(void){int kind,index,m,i;unsigned char before[26*0x32C];
 if(sizeof(void*)!=4)return 9;
 for(kind=0;kind<256;kind++)for(index=0;index<26;index++)for(m=0;m<2;m++){
  for(i=0;i<26*0x32C;i++)D_800CC2D4[i]=before[i]=(u8)(i*13+165);
  D_800CC2D4[index*0x32C]=before[index*0x32C]=(u8)kind;
  expected=index;mutation=m;count=error=0;
  if(m && (kind<5 || kind==128 || kind==176))before[index*0x32C]=5;
  func_1503453C(index);
  if(error || count!=(kind<5 || kind==128 || kind==176))return 1;
  for(i=0;i<26*0x32C;i++)if(D_800CC2D4[i]!=before[i])return 2;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''

    def test_03_native32_actual_source_and_effective_negative_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(screen.SELECTED), profile), (0, ''))
        negatives = {'signed-byte': screen.SELECTED.replace('    switch (D_800CC2D4[(u32)index * 0x32C]) {',
                '    s32 type = ((signed char *)D_800CC2D4)[(u32)index * 0x32C];\n    switch (type) {'),
            'missing-high': screen.SELECTED.replace('        case 0xB0:\n', ''),
            'wrong-stride': screen.SELECTED.replace('0x32C', '0x32B'),
            'wrong-argument': screen.SELECTED.replace('func_1503B9BC(index)', 'func_1503B9BC(0)')}
        for name, body in negatives.items():
            self.assertNotEqual(body, screen.SELECTED)
            self.assertIn(self.run_native('negative-' + name, self.native_source(body))[0], (1, 2))
        self.receipt('native', cases_per_profile=13312, profiles=['O2', 'O0'], effective_negatives=4, valid_indices_only=True)

    def test_04_actual_connected_caller_with_live_actor_type_recheck(self):
        cases = 0
        for index, kind, state, flag, mutation, phase in itertools.product((0, 1, 25),
                (0, 5, 0x80, 0xB0, 0xFF), (0, 1, 0x22), (0, 7), (0, 1), (0, 8)):
            memory = fixture(index, kind, self.pool, True, state, flag)
            pair = []
            for words in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 168, 4), words))
                pair.append(DispatchOracle(self.caller, memory, index, phase, mutation, entry=CALLER, connected=connected).run())
            for field in ('memory', 'events', 'r', 'f', 'calls'):
                self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
            target_calls = int(state == 1 or flag == 7) + int(state == 0x22)
            provider_calls = min(target_calls, 1) if mutation else target_calls
            expected = provider_calls if selected(kind) else 0
            self.assertEqual(sum(t == PROVIDER for t, _ in pair[0].calls), expected)
            self.assertEqual(sum(t == screen.ENTRY for t, _ in pair[0].calls), target_calls)
            cases += 1
        self.assertEqual(cases, 360)
        self.receipt('connected', cases=cases, caller_words=81, caller_original_instructions=True, provider_opaque=True)

    def test_05_actual_owner_neighbors_new_table_and_both_padders(self):
        objects = [screen.compile_owner(self.root, self.out, source, name) for source, name in
            ((self.owner_before, 'owner-before'), (self.owner_after, 'owner-after'))]
        self.assertEqual([warnings for _, warnings in objects], [[], []])
        before, after = [parse_object(obj) for obj, _ in objects]
        self.assertEqual(before[1].keys(), after[1].keys())
        for name in before[1]:
            a, b = before[1][name], after[1][name]
            if name != screen.FUNCTION:
                self.assertEqual(before[0][a['value']:a['value'] + a['size']], after[0][b['value']:b['value'] + b['size']], name)
                self.assertEqual({o-a['value']: r for o,r in before[2].items() if a['value'] <= o < a['value']+a['size']},
                    {o-b['value']: r for o,r in after[2].items() if b['value'] <= o < b['value']+b['size']}, name)
        old_pools, new_pools = [normalized_pools(obj) for obj, _ in objects]
        self.assertEqual(old_pools['.data'], new_pools['.data'])
        self.assertIn(old_pools['.rodata'], (None, (b'', ())))
        self.assertEqual(new_pools['.rodata'], (bytes(32), tuple((i*4, screen.FUNCTION, 144) for i in range(5))))
        isolated = parse_object(self.out / 'direct.o')
        target = after[1][screen.FUNCTION]
        self.assertEqual(after[0][target['value']:target['value']+168], isolated[0][:168])
        self.assertEqual({o-target['value']: r for o,r in after[2].items() if target['value'] <= o < target['value']+168}, isolated[2])
        padded = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            asm = self.out / (script + '.s')
            args = [str(objects[1][0]), str(self.root / 'conker/retail_layout.us.txt'), 'generated_61490', str(asm)] if script == 'pad_c_object.py' else [
                str(objects[1][0]), str(self.root / 'conker/asm/61490.s'), str(asm), '--filename', 'generated_61490']
            result = subprocess.run([sys.executable, str(self.root / 'tools' / script), *args,
                '--word-patches', str(self.root / 'conker/retail_word_patches.us.csv'), '--rodata-symbol', screen.ANCHOR], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(obj), str(asm)], check=True, capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0], padded[1])
        self.assertEqual(padded[0][1][screen.FUNCTION]['size'], 168)
        self.receipt('owner', neighbors=len(after[1])-1, both_full_owner_padders_identical=True,
            new_pool_only_five_target_entries=True, original_global_asm_postprocessed=True)

    def test_06_independent_original_rebases_and_lo16_carries(self):
        original = (self.root / 'conker/asm/61490.s').read_text().split('glabel ' + screen.FUNCTION + '\n', 1)[1]
        original = 'glabel ' + screen.FUNCTION + '\n' + original.split('endlabel ' + screen.FUNCTION, 1)[0] + 'endlabel ' + screen.FUNCTION + '\n'
        asm = self.out / 'original.s'
        asm.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + original)
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        for i, entry, table, actor in ((0, screen.ENTRY, screen.TABLE, 0x800CC2D4),
                (1, 0x1523453C, 0x90007FFC, 0x80118004), (2, 0x1533453C, 0x90018004, 0x80217FFC)):
            symbols = dict(screen.SYMBOLS, D_800CC2D4=actor)
            with patch.multiple(screen, ENTRY=entry, TABLE=table, SYMBOLS=symbols):
                _, candidate, pool = screen.compile_candidate(self.root, self.out, 'rebase-' + str(i))
            self.assertEqual(struct.unpack('>5I', pool[:20]), (entry+144,)*5)
            ld = self.out / ('original-' + str(i) + '.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(ld), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in dict(symbols, jtbl_80097D20=table).items()],
                '-o', str(elf), str(obj)], check=True, capture_output=True)
            self.assertEqual(candidate, list(struct.unpack_from('>42I', sections(elf)['.text'][1])))

    def test_07_literal_whole_image_fixed_table_and_protected_inputs(self):
        current = (self.root / self.paths['elf']).read_bytes()
        source = (self.root / screen.SOURCE).read_text()
        expected = bytearray(self.before)
        offset = elf_slot_offset(self.before, screen.ENTRY, 168)
        self.assertEqual(offset, elf_slot_offset(current, screen.ENTRY, 168))
        if source == self.owner_after:
            expected[offset:offset+168] = struct.pack('>42I', *self.retail)
            with patch.multiple(descriptor.screen, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
            struct.pack_into('>I', expected, size_offset, 168)
        else:
            self.assertEqual(source, self.owner_before)
        self.assertEqual(canonical_symbols(bytes(expected)), canonical_symbols(current))
        self.assertEqual(current, bytes(expected))
        for name in ('guards', 'progress', 'layout'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-'+name)).read_bytes())
        make_before = (self.out / 'before-makefile').read_text()
        make_after = make_before.replace('$(BUILD_DIR)/$(SRC_DIR)/game/generated_5D2C0.c.o: RETAIL_RODATA_SYMBOL := jtbl_80096F40_game',
            '$(BUILD_DIR)/$(SRC_DIR)/game/generated_5D2C0.c.o: RETAIL_RODATA_SYMBOL := jtbl_80096F40_game\n'
            '$(BUILD_DIR)/$(SRC_DIR)/game/generated_61490.c.o: RETAIL_RODATA_SYMBOL := ' + screen.ANCHOR + '\n'
            '$(BUILD_DIR)/$(SRC_DIR)/game/generated_61490.c.o: Makefile')
        self.assertEqual((self.root / self.paths['makefile']).read_text(), make_after if source == self.owner_after else make_before)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('linked-audit', installed=source == self.owner_after, literal_whole_image=True,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)), data=data)


if __name__ == '__main__':
    unittest.main()
