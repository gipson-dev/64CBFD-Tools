"""Direct dispatcher match, opaque callback effects and complete linked-slot audit."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_mode_callback_dispatch_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_table_range_loader as table
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.check_game_data_layout import audit_layout

STACK, MARKER = table.STACK, 0x22000
TARGETS = (0x15010000, 0x15010100, 0x15010200)
MODES = (*range(256), 0x100, 0x101, 0x102, 0x10000001, 0x10000002,
         0x7FFFFFFF, 0x80000000, 0x80000001, 0x80000002, 0xFFFFFFFF)
PAIRS = ((TARGETS[0], TARGETS[1]), (TARGETS[2], TARGETS[0]), (TARGETS[1], TARGETS[2]))
LATCHES = (0, 1, 0x80000000, 0xFFFFFFFF)


def fixture(pair=PAIRS[0], latch=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x100, 0x80)}
    for address, value in zip(screen.SYMBOLS.values(), (*pair, latch)):
        put(memory, address, value)
    put(memory, MARKER, 0)
    return memory


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x100 <= a < STACK + 0x80}


class DispatchOracle(TriangleOracle):
    def __init__(self, words, memory, mode, phase=0, mutation=0, entry=screen.ENTRY):
        self.fault, self.accesses, self.in_hook = None, 0, False
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(mode,))
        self.mutation = mutation

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault == self.accesses:
                raise AccessFault()
            self.accesses += 1

    def get(self, address, size):
        self.gate()
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording and any(address + i not in self.memory for i in range(size)):
            raise KeyError('Unmapped dispatcher write')
        self.gate()
        return super().put(address, value, size)

    def record_call(self, target):
        if target not in TARGETS:
            raise ValueError('Unknown opaque callback')
        self.calls.append(target)
        self.events.append(('CALL', target, ()))

    def hook(self, target):
        self.in_hook = True
        try:
            self.get(screen.SYMBOLS['D_800DD1B0'], 4)
            self.put(MARKER, target, 4)
            if self.mutation:
                self.put(screen.SYMBOLS['D_800DD1B0'], 0xA5000000 | self.mutation, 4)
            if self.mutation == 2:
                self.put(screen.SYMBOLS['D_80082BD0'], TARGETS[2], 4)
                self.put(screen.SYMBOLS['D_80082BD4'], TARGETS[2], 4)
            for reg in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[reg] = 0xA5000000 + reg
        finally:
            self.in_hook = False


class AccessFault(Exception):
    pass


class GameModeCallbackDispatchMatchTests(unittest.TestCase):
    run_native = native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-mode-callback-dispatch-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root / screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.retail = list(struct.unpack_from('>40I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'direct')

    def test_01_original_profile_complete_slot_and_no_guards_or_pools(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']), (38, 48, 0, 0))
        self.assertEqual(self.words, self.retail[:38])
        self.assertEqual(self.retail[38:], [0, 0])
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.meta['profile'], 'o2g3')
        self.assertEqual(len(self.meta['relocations']), 6)
        self.assertTrue(all(not value[1] for name, value in sections(self.out / 'direct.o').items()
            if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))

    def test_02_mode_domain_callback_mutations_and_complete_guest_state(self):
        cases = 0
        for mode, phase, mutation, pair, latch in itertools.product(MODES, (0, 8), range(3), PAIRS, LATCHES):
            memory = fixture(pair, latch)
            models = [DispatchOracle(words, memory, mode, phase, mutation).run() for words in (self.retail, self.words)]
            for field in ('memory', 'events', 'r', 'f', 'calls'):
                self.assertEqual(getattr(models[0], field), getattr(models[1], field))
            target = pair[mode - 1] if mode in (1, 2) else None
            expected = public(memory)
            if target:
                put(expected, MARKER, target)
                if mutation == 2:
                    for address in list(screen.SYMBOLS.values())[:2]:
                        put(expected, address, TARGETS[2])
            put(expected, screen.SYMBOLS['D_800DD1B0'], 0xFFFFFFFF)
            self.assertEqual(public(models[1].memory), expected)
            self.assertEqual(models[1].calls, [target] if target else [])
            self.assertEqual(models[1].events[-1], ('R', STACK + phase - 0x30 + 0x20, 4, models[1].before[18]))
            cases += 1
        self.assertEqual(cases, 19152)
        (self.out / 'guest.json').write_text(json.dumps(dict(cases=cases, actual_full_dispatcher=True,
            callbacks_opaque_ABI_clobber_models=True, hardware_gameplay_not_claimed=True), indent=2) + '\n')

    def test_03_fail_closed_and_all_own_instruction_access_cuts(self):
        first, second, latch = screen.SYMBOLS.values()
        for mode, required in ((1, first), (2, second), (0, latch)):
            for byte in range(4):
                memory = fixture()
                del memory[required + byte]
                with self.assertRaises(KeyError if mode == 0 else AssertionError):
                    DispatchOracle(self.words, memory, mode).run()
        memory = fixture()
        for address in (first, second):
            for byte in range(4):
                del memory[address + byte]
        model = DispatchOracle(self.words, memory, 0).run()
        self.assertEqual(model.calls, [])
        count = 0
        for mode, phase, mutation in itertools.product((0, 1, 2, 3, 0xFFFFFFFF), (0, 8), range(3)):
            memory = fixture(latch=0x12345678)
            normal = DispatchOracle(self.words, memory, mode, phase, mutation).run()
            for fault in range(normal.accesses):
                pair = [DispatchOracle(words, memory, mode, phase, mutation) for words in (self.retail, self.words)]
                for model in pair:
                    model.fault = fault
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, fault)
                self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f),
                                 (pair[1].memory, pair[1].events, pair[1].r, pair[1].f))
                count += 1
            terminal = DispatchOracle(self.words, memory, mode, phase, mutation)
            terminal.fault = normal.accesses
            terminal.run()
            self.assertEqual(terminal.accesses, normal.accesses)
        (self.out / 'faults.json').write_text(json.dumps(dict(fired_pairs=count,
            own_routine_R_W_only=True, opaque_callback_accesses_excluded=True), indent=2) + '\n')

    def native_source(self, body):
        modes = ','.join('0x%Xu' % mode for mode in MODES)
        return ('typedef unsigned char u8;typedef unsigned int u32;typedef int s32;\n' + screen.DECLARATIONS + r'''
static int calls,observed,mutation;
static s32 initial,entryLatch;
static u32 fence0=0x12345678u,fence1=0x87654321u;
static void callbackA(void);static void callbackB(void);static void callbackC(void);
GameModeCallback D_80082BD0,D_80082BD4;
s32 D_800DD1B0;
static void record(int id) {
 calls++;observed=id;entryLatch=D_800DD1B0;
 if(mutation) D_800DD1B0=(s32)(0xA5000000u|(u32)mutation);
 if(mutation==2){D_80082BD0=callbackC;D_80082BD4=callbackC;}
}
static void callbackA(void){record(1);}static void callbackB(void){record(2);}static void callbackC(void){record(3);}
typedef char ABI4[(sizeof(s32)==4 && sizeof(void*)==4 && sizeof(GameModeCallback)==4)?1:-1];
''' + body + '\nstatic const u32 modes[]={' + modes + r'''};
static int check(void) {
 u32 i;int p,m,l,expected;GameModeCallback functions[3]={callbackA,callbackB,callbackC};
 int first[3]={0,2,1},second[3]={1,0,2};u32 latches[4]={0,1,0x80000000u,0xFFFFFFFFu};
 for(i=0;i<sizeof(modes)/sizeof(modes[0]);i++)for(p=0;p<3;p++)for(m=0;m<3;m++)for(l=0;l<4;l++) {
  calls=observed=0;mutation=m;initial=(s32)latches[l];entryLatch=0;
  D_80082BD0=functions[first[p]];D_80082BD4=functions[second[p]];D_800DD1B0=initial;
  func_15008930((s32)modes[i]);
  expected=modes[i]==1?first[p]+1:modes[i]==2?second[p]+1:0;
  if(calls!=(expected!=0) || observed!=expected) return 1;
  if(expected && entryLatch!=initial) return 2;
  if(D_800DD1B0!=-1) return 3;
  if(fence0!=0x12345678u || fence1!=0x87654321u) return 4;
  if(m==2 && expected && (D_80082BD0!=callbackC || D_80082BD4!=callbackC)) return 5;
 }
 D_80082BD0=D_80082BD4=(GameModeCallback)0;D_800DD1B0=17;calls=0;func_15008930(-1);
 if(calls || D_800DD1B0!=-1) return 6;
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
''')

    def test_04_native32_and_effective_callback_latch_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(screen.SELECTED), profile), (0, ''))
        controls = [('wrong-latch', 'D_800DD1B0 = -1;', 'D_800DD1B0 = 0;'),
                    ('skip-callback', '            (*cursor)();', '            (void)cursor;')]
        for name, old, new in controls:
            body = screen.SELECTED.replace(old, new)
            self.assertNotEqual(body, screen.SELECTED)
            code, _ = self.run_native('negative-' + name, self.native_source(body))
            self.assertIn(code, (1, 2, 3, 4, 5, 6))
        (self.out / 'native.json').write_text(json.dumps(dict(cases_per_profile=9576, profiles=['O2', 'O0'],
            comparisons=19152, integer_pointer_callback_bytes4=True, opaque_callbacks=True), indent=2) + '\n')

    def test_05_production_copied_owner_pools_neighbor_and_both_padders(self):
        objects = [compile_owner(self.root, self.out, body, name) for body, name in
                   ((self.owner_before, 'owner-before'), (self.owner_after, 'owner-after'))]
        self.assertEqual([warnings for _, warnings in objects], [[], []])
        before, after = [parse_object(obj) for obj, _ in objects]
        self.assertEqual(set(before[1]), {'func_15008870', screen.FUNCTION})
        self.assertEqual(set(before[1]), set(after[1]))
        neighbor = 'func_15008870'
        def body(parsed, name):
            entry = parsed[1][name]
            return parsed[0][entry['value']:entry['value'] + entry['size']]
        self.assertEqual(body(before, neighbor), body(after, neighbor))
        isolated = parse_object(self.out / 'direct.o')
        self.assertEqual(body(after, screen.FUNCTION)[:152], body(isolated, screen.FUNCTION)[:152])
        start = after[1][screen.FUNCTION]['value']
        self.assertEqual({offset - start: entries for offset, entries in after[2].items() if start <= offset < start + 152}, isolated[2])
        pools = [sections(obj) for obj, _ in objects]
        for name in pools[0].keys() | pools[1].keys():
            if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')):
                self.assertEqual(pools[0].get(name), pools[1].get(name))
        reference = self.out / 'owner-reference.s'
        reference.write_text('\n'.join((self.root / ('conker/asm/nonmatchings/game_35D20/' + name + '.s')).read_text()
            for name in ('func_15008870', screen.FUNCTION)))
        padded = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            asm = self.out / (script + '.s')
            args = [str(objects[1][0]), str(self.root / 'conker/retail_layout.us.txt'), 'game_35D20', str(asm)] if script == 'pad_c_object.py' else [
                str(objects[1][0]), str(reference), str(asm), '--filename', 'game_35D20']
            subprocess.run([sys.executable, str(self.root / 'tools' / script), *args], check=True, capture_output=True)
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'), '-o', str(obj), str(asm)],
                           check=True, capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0], padded[1])
        target = padded[0][1][screen.FUNCTION]
        self.assertEqual(target['size'], 152)
        self.assertEqual(padded[0][0][target['value'] + 152:target['value'] + 160], b'\0' * 8)

    def test_06_independent_links_and_rebased_data_symbols(self):
        asm = self.out / 'independent-original.s'
        original = (self.root / 'conker/asm/nonmatchings/game_35D20/func_15008930.s').read_text()
        asm.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + original)
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        links = [(screen.ENTRY, screen.SYMBOLS), (0x15208930, dict(D_80082BD0=0x80107FFC, D_80082BD4=0x80108004, D_800DD1B0=0x80118000)),
                 (0x15308930, dict(D_80082BD0=0x80208004, D_80082BD4=0x80217FFC, D_800DD1B0=0x80227FF0))]
        for i, (entry, symbols) in enumerate(links):
            with patch.object(screen, 'ENTRY', entry), patch.object(screen, 'SYMBOLS', symbols):
                meta, candidate = screen.compile_candidate(self.root, self.out, 'rebase-' + str(i))
            script = self.out / ('original-' + str(i) + '.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack('>40I', sections(elf)['.text'][1]))
            self.assertEqual(candidate, words[:38])
            self.assertEqual(words[38:], [0, 0])
            self.assertEqual(meta['frame'], 48)

    def test_07_baseline_or_installed_linked_image_only_target_can_change(self):
        current = (self.root / 'conker/build/conker.us.elf').read_bytes()
        offset = elf_slot_offset(current, screen.ENTRY, 160)
        old = elf_slot_offset(self.before, screen.ENTRY, 160)
        self.assertEqual(offset, old)
        source = (self.root / screen.SOURCE).read_text()
        expected = bytearray(self.before)
        if source == self.owner_after:
            self.assertEqual(current[offset:offset + 160], struct.pack('>40I', *self.retail))
            expected[old:old + 160] = struct.pack('>40I', *self.retail)
            with patch.multiple(descriptor.screen, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
                self.assertEqual(descriptor.size_field(current), size_offset)
            struct.pack_into('>I', expected, size_offset, 152)
        else:
            self.assertEqual(source, self.owner_before)
        self.assertEqual(current, bytes(expected))
        self.assertEqual(metadata(current)[2], metadata(bytes(expected))[2])
        for name in ('guards', 'progress', 'layout', 'makefile'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        report = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertEqual((report['exact'], report['bytes'], report['owner_count'], report['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'linked-audit.json').write_text(json.dumps(dict(installed=source == self.owner_after,
            literal_whole_ELF_only_target_slot_and_target_size_field_changed=True,
            guards_progress_layout_profile_unchanged=True, data_bytes=report['bytes'], data_owners=report['owner_count']), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
