"""Direct event packet match, helper mutation, original homes and image gate."""
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

from tools.experiments import game_event_record_constructor_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.check_game_data_layout import audit_layout

ACTOR, ALT, THIRD, CREATED = 0x22000, 0x23000, 0x24000, 0x26000
FLAGS = (0, 1, 2, 0x100, 0x80000000, 0xFFFFFFFF)
CODES = (0, 1, 0xFF, 0x100, 0x80000001, 0xFFFFFFFF)
COORDS = (0, 1, 0x7FFF, 0x8000, 0x8001, 0xFFFF)
IDS = (0, 1, 0x80000000, 0xFFFFFFFF)
RESET, PROJECT, CREATE, COPY = screen.SYMBOLS.values()
CREATE_ARGS = (0x12C, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0x2C, 0x14, 0xFF, 0)


def fixture(flag=0, code=0, coordinate=0, seed=0):
    memory = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x200, 0x100)}
    for base in (ACTOR, ALT, THIRD, CREATED):
        memory.update({base + i: (i * 13 + seed * 7 + 0xA5) & 255 for i in range(-0x40, 0xA0)})
        put(memory, base, coordinate if base == ACTOR else 0x8001 + (base - ACTOR) // 0x1000, 2)
        put(memory, base + 4, coordinate ^ 0xFFFF if base == ACTOR else 0x7FFD - (base - ACTOR) // 0x1000, 2)
        put(memory, base + 0x1C, code ^ (base - ACTOR))
        put(memory, base + 0x20, flag if base != THIRD else (0 if flag else 0x80000000))
    return memory


def mutation_actions(target, mutation, stack):
    if mutation == 1 and target == RESET:
        return [(ACTOR, 0x8000, 2), (ACTOR + 4, 0x7FFF, 2), (ACTOR + 0x1C, 0x12345678, 4)]
    if mutation == 1 and target == PROJECT:
        return [(ACTOR + 0x20, 0, 4)]
    if mutation == 2 and target == RESET:
        return [(stack, ALT, 4)]
    if mutation == 2 and target == PROJECT:
        return [(stack, THIRD, 4)]
    return []


class RecordOracle(TriangleOracle):
    def __init__(self, words, memory, phase=0, mutation=0, result=CREATED, projection=0, entry=screen.ENTRY):
        self.fault, self.accesses, self.in_hook = None, 0, False
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(ACTOR,))
        self.mutation, self.result, self.projection = mutation, result, projection
        self.packet, self.raw_calls = None, []

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
        self.in_hook = True
        try:
            count = {RESET: 1, PROJECT: 2, CREATE: 9, COPY: 3}[target]
            args = self.arguments(count)
            if target == CREATE:
                assert args == CREATE_ARGS, args
            if target == COPY:
                assert args[2] == 20
                self.packet = bytes(self.peek(args[1] + i, 1) for i in range(20))
            self.raw_calls.append((target, args))
            self.calls.append((target, args))
            self.events.append(('CALL', target, args))
        finally:
            self.in_hook = False

    def hook(self, target):
        self.in_hook = True
        try:
            for address, value, size in mutation_actions(target, self.mutation, STACK + (self.before[29] - STACK)):
                self.put(address, value, size)
            result = self.projection if target == PROJECT else self.result if target == CREATE else 0xA5000000
            if target == COPY:
                destination, source, size = self.raw_calls[-1][1]
                for i in range(size):
                    self.put(destination + i, self.peek(source + i, 1), 1)
                result = destination
            for register in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[register] = 0xA5000000 + register
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            self.r[2] = result & 0xFFFFFFFF
        finally:
            self.in_hook = False


class AccessFault(Exception):
    pass


def expected_packet(memory, phase, mutation, projection):
    updated = dict(memory)
    put(updated, ACTOR + 0x14, 1, 1)
    packet = bytearray(memory[STACK + phase - 0x14 + i] for i in range(20))
    struct.pack_into('>I', packet, 0, ACTOR)
    packet[4] = read(updated, ACTOR + 0x1C) & 255
    pointer = ACTOR
    for target in (RESET, PROJECT):
        for address, value, size in mutation_actions(target, mutation, STACK + phase):
            put(updated, address, value, size)
        if mutation == 2:
            pointer = read(updated, STACK + phase)
    struct.pack_into('>I', packet, 8, projection)
    packet[12] = 3 if read(updated, pointer + 0x20) else 0
    struct.pack_into('>I', packet, 16, 0)
    return bytes(packet), updated


class GameEventRecordConstructorMatchTests(unittest.TestCase):
    run_native = native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-event-record-constructor-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.owner_before = (cls.out / 'before-source').read_text()
        cls.owner_before = cls.owner_before.replace(screen.NEW_FLAGS, screen.OLD_FLAGS, 1)
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.body = screen.selected(cls.owner_before)
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'direct', cls.body)
        cls.old_meta, cls.old_words = screen.compile_candidate(cls.root, cls.out, 'old-source', screen.function_body(cls.owner_before))
        cls.retail = list(struct.unpack_from('>52I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))

    def test_01_raw_word_flag_tests_recover_complete_body_and_frame(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']), (52, 88, 0, 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.old_meta['body_words'], self.old_meta['frame'], self.old_meta['differences']), (50, 80, 37))
        self.assertNotIn('volatile', self.body)
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertTrue(all(not value[1] for name, value in sections(self.out / 'direct.o').items()
            if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))

    def test_02_packets_helpers_aliases_and_incoming_home_redirects(self):
        cases = 0
        for index, phase, mutation, result in itertools.product(range(864), (0, 8), range(3), (0, CREATED, ACTOR - 0x28)):
            flag, code, coordinate, projection = FLAGS[index % 6], CODES[index // 6 % 6], COORDS[index // 36 % 6], IDS[index // 216 % 4]
            memory = fixture(flag, code, coordinate, index % 2)
            pair = [RecordOracle(words, memory, phase, mutation, result, projection).run() for words in (self.retail, self.words)]
            for field in ('memory', 'events', 'r', 'f', 'calls', 'packet'):
                self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
            packet, updated = expected_packet(memory, phase, mutation, projection)
            self.assertEqual(pair[1].r[2], 1)
            self.assertEqual([target for target, _ in pair[1].calls], [RESET, PROJECT, CREATE] + ([COPY] if result else []))
            self.assertEqual(pair[1].calls[0][1], (0,))
            pointer = ALT if mutation == 2 else ACTOR
            after_reset = dict(memory)
            for address, value, size in mutation_actions(RESET, mutation, STACK + phase):
                put(after_reset, address, value, size)
            narrow = lambda value: (value if value < 32768 else value - 65536) & 0xFFFFFFFF
            self.assertEqual(pair[1].calls[1][1], (narrow(read(after_reset, pointer, 2)), narrow(read(after_reset, pointer + 4, 2))))
            if result:
                self.assertEqual(pair[1].packet, packet)
                self.assertEqual(bytes(pair[1].memory[result + 0x28 + i] for i in range(20)), packet)
            else:
                self.assertIsNone(pair[1].packet)
            cases += 1
        self.assertEqual(cases, 15552)
        memory = fixture(flag=0x80000000, coordinate=0x7FFF)
        old = RecordOracle(self.old_words, memory, mutation=2).run()
        direct = RecordOracle(self.words, memory, mutation=2).run()
        self.assertEqual(old.calls[1], direct.calls[1])
        self.assertEqual(old.packet, direct.packet)
        pair = [RecordOracle(words, memory) for words in (self.old_words, self.words)]
        for model in pair:
            model.fault = 1
            with self.assertRaises(AccessFault):
                model.run()
        self.assertNotEqual(pair[0].r[29], pair[1].r[29])
        (self.out / 'guest.json').write_text(json.dumps(dict(cases=cases, padding_all20_guest_bytes=True,
            live_parameter_home_mutations_guest_ABI_only=True, old_source_packet_equivalent=True,
            old_source_frame_cut_effectively_rejected=True), indent=2) + '\n')

    def test_03_fail_closed_and_all_own_instruction_access_cuts(self):
        for offset, size in ((0x14, 1), (0x1C, 4), (0, 2), (4, 2), (0x20, 4)):
            for byte in range(size):
                memory = fixture()
                del memory[ACTOR + offset + byte]
                with self.assertRaises(AssertionError):
                    RecordOracle(self.words, memory).run()
        count = 0
        for phase, mutation, result in itertools.product((0, 8), range(3), (0, CREATED)):
            memory = fixture(flag=0x80000000, code=0x123456FF, coordinate=0x8000)
            normal = RecordOracle(self.words, memory, phase, mutation, result, 0xFFFFFFFF).run()
            for fault in range(normal.accesses):
                pair = [RecordOracle(words, memory, phase, mutation, result, 0xFFFFFFFF) for words in (self.retail, self.words)]
                for model in pair:
                    model.fault = fault
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, fault)
                self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f),
                                 (pair[1].memory, pair[1].events, pair[1].r, pair[1].f))
                count += 1
            terminal = RecordOracle(self.words, memory, phase, mutation, result, 0xFFFFFFFF)
            terminal.fault = normal.accesses
            terminal.run()
        (self.out / 'faults.json').write_text(json.dumps(dict(fired_pairs=count, own_routine_only=True,
            opaque_helper_accesses_excluded=True, PC_FCSR_hardware_not_claimed=True), indent=2) + '\n')

    def native_source(self, body):
        return ('#define NULL ((void *)0)\ntypedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef short s16;typedef signed char s8;\n' + screen.DECLARATIONS + r'''
static u8 storage[0xC0] __attribute__((aligned(16))),created[0x80] __attribute__((aligned(16))),witness[20];
static u8 *input=storage+0x40,*allocation;
static int step,error,mutation,copied;static s32 projection,originalCode;
static s16 expectedX,expectedZ;
static u32 flags[]={0,1,2,0x100,0x80000000u,0xFFFFFFFFu};
static u32 codes[]={0,1,0xFF,0x100,0x80000001u,0xFFFFFFFFu};
static u32 coords[]={0,1,0x7FFF,0x8000,0x8001,0xFFFF};
static u32 ids[]={0,1,0x80000000u,0xFFFFFFFFu};
struct ExpectedPacket {void *owner;u8 code,pad[3];s32 id;u8 flags,pad2[3];s32 zero;};
typedef char ABI4[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(struct ExpectedPacket)==20)?1:-1];
void func_1510F800(s32 value){
 if(step++!=0 || value!=0 || input[0x14]!=1) error=1;
 if(mutation){*(s16*)input=-32768;*(s16*)(input+4)=32767;*(s32*)(input+0x1C)=0x12345678;expectedX=-32768;expectedZ=32767;}
}
s32 func_1510FD20(s32 x,s32 z){
 if(step++!=1 || x!=expectedX || z!=expectedZ) error=2;
 if(mutation) *(s32*)(input+0x20)=0;
 return projection;
}
void *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,struct37 *g,u8 h,s32 i){
 if(step++!=2 || a!=0x12C || b!=-1 || c!=-1 || d!=-1 || e!=0 || f!=0x2C || (u32)g!=20 || h!=255 || i!=0) error=3;
 return allocation;
}
void *memcpy(void *d,const void *s,unsigned int n){
 u32 i;u8 *out=(u8*)d;const u8 *in=(const u8*)s;
 if(step++!=3 || n!=20 || out!=allocation+0x28) error=4;
 for(i=0;i<n;i++) witness[i]=in[i];
 for(i=0;i<n;i++) out[i]=in[i];
 copied=1;return d;
}
''' + body + r'''
static int check(void){
 u32 i,j;int m,r;struct ExpectedPacket *packet;
 for(i=0;i<4096;i++)for(m=0;m<2;m++)for(r=0;r<3;r++){
  for(j=0;j<sizeof(storage);j++)storage[j]=(u8)(j*13+0xA5);
  for(j=0;j<sizeof(created);j++)created[j]=(u8)(j*7+0x5A);
  expectedX=(s16)coords[i%6];expectedZ=(s16)(coords[i%6]^0xFFFFu);
  *(s16*)input=expectedX;*(s16*)(input+4)=expectedZ;
  originalCode=(s32)codes[i/6%6];*(s32*)(input+0x1C)=originalCode;
  *(s32*)(input+0x20)=(s32)flags[i/36%6];projection=(s32)ids[i/216%4];
  mutation=m;step=error=copied=0;allocation=r==0?(u8*)0:r==1?created:input-0x28;
  if(func_15015104(input)!=1 || error || step!=(allocation?4:3) || copied!=(allocation!=0))return 1;
  if(input[0x14]!=1 || storage[0]!=0xA5 || storage[sizeof(storage)-1]!=(u8)((sizeof(storage)-1)*13+0xA5))return 2;
  if(allocation){
   packet=(struct ExpectedPacket*)(allocation+0x28);
   if(packet->owner!=input || packet->code!=(u8)originalCode || packet->id!=projection || packet->zero!=0) return 3;
   if(packet->flags!=(mutation?0:flags[i/36%6]?3:0))return 4;
   for(j=0;j<20;j++)if(((u8*)packet)[j]!=witness[j])return 5;
  }
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
''')

    def test_04_native32_defined_fields_all_copied_bytes_and_effective_controls(self):
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-' + profile[1:], self.native_source(self.body), profile), (0, ''))
        for name, old, new in (('wrong-code', 'data.unk4 = *(s32 *)(arg0 + 0x1C);', 'data.unk4 = *(s32 *)(arg0 + 0x1C) + 1;'),
                ('wrong-flags', '(flags ? 1 : 0) | (flags ? 2 : 0)', '(flags ? 1 : 0)'),
                ('wrong-return', 'return 1;', 'return 0;')):
            body = self.body.replace(old, new)
            self.assertNotEqual(body, self.body)
            code, _ = self.run_native('negative-' + name, self.native_source(body))
            self.assertIn(code, (1, 2, 3, 4, 5))
        (self.out / 'native.json').write_text(json.dumps(dict(cases_per_profile=24576, profiles=['O2', 'O0'],
            comparisons=49152, padding_content_not_portably_fixed=True, all20_copy_witness_bytes_checked=True,
            incoming_home_redirects_guest_only=True), indent=2) + '\n')

    def test_05_actual_copied_owner_neighbors_pools_and_both_padders(self):
        objects, warnings = [], []
        for name, source in (('before', self.owner_before), ('after', self.owner_after)):
            obj, diagnostics = compile_owner(self.root, self.out, source, 'owner-' + name)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj)
            warnings.append(diagnostics)
        self.assertEqual(warnings[0], warnings[1])
        before, after = [parse_object(obj) for obj in objects]
        self.assertEqual(before[1].keys(), after[1].keys())
        for name, current in after[1].items():
            if name == screen.FUNCTION:
                continue
            previous = before[1][name]
            self.assertEqual(after[0][current['value']:current['value'] + current['size']],
                             before[0][previous['value']:previous['value'] + previous['size']], name)
            self.assertEqual({o - current['value']: r for o, r in after[2].items() if current['value'] <= o < current['value'] + current['size']},
                             {o - previous['value']: r for o, r in before[2].items() if previous['value'] <= o < previous['value'] + previous['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        fn = after[1][screen.FUNCTION]
        isolated = parse_object(self.out / 'direct.o')
        self.assertEqual(after[0][fn['value']:fn['value'] + 208], isolated[0][:208])
        self.assertEqual({offset - fn['value']: r for offset, r in after[2].items()
            if fn['value'] <= offset < fn['value'] + 208}, isolated[2])
        reference = self.out / 'owner-reference.s'
        with (self.root / 'conker/retail_layout.us.txt').open(newline='') as stream:
            rows = [row for row in csv.DictReader(stream) if row['filename'] == 'game_40490']
        self.assertEqual({row['function'] for row in rows}, set(before[1]))
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        fragments = []
        for row in rows:
            name = row['function']
            asm = self.root / ('conker/asm/nonmatchings/game_40490/' + name + '.s')
            if asm.exists():
                fragments.append(asm.read_text())
                continue
            # Already-matched routines have no split assembly; retain their retail metadata.
            start, end = int(row['address'], 0), int(row['end'], 0)
            fragment = ['glabel ' + name]
            for address in range(start, end, 4):
                offset = screen.ROM + address - screen.ENTRY
                word = struct.unpack_from('>I', rom, offset)[0]
                fragment.append('/* %X %08X %08X */ .word 0x%08X' % (offset, address, word, word))
            fragments.append('\n'.join(fragment))
        reference.write_text('\n'.join(fragments))
        padded = []
        for name, obj in zip(('before', 'after'), objects):
            asm = self.out / ('legacy-owner-' + name + '.s')
            subprocess.run([sys.executable, str(self.root / 'tools/pad_c_object.py'), str(obj),
                str(self.root / 'conker/retail_layout.us.txt'), 'game_40490', str(asm),
                '--word-patches', str(self.root / 'conker/retail_word_patches.us.csv')], check=True, capture_output=True)
            assembled = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(assembled), str(asm)], check=True, capture_output=True)
            padded.append(parse_object(assembled))
            rejected = subprocess.run([sys.executable, str(self.root / 'tools/pad_generated_object.py'),
                str(obj), str(reference), str(self.out / ('strict-owner-' + name + '.s')),
                '--filename', 'game_40490', '--word-patches', str(self.root / 'conker/retail_word_patches.us.csv')],
                capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('patched func_15014094 is 0xB8 bytes but its retail span is only 0xB0', rejected.stderr)
        self.assertEqual(padded[0][1].keys(), padded[1][1].keys())
        target = padded[1][1][screen.FUNCTION]
        expected = bytearray(padded[0][0])
        expected[target['value']:target['value'] + 208] = padded[1][0][target['value']:target['value'] + 208]
        self.assertEqual(bytes(expected), padded[1][0])
        outside = lambda parsed: {offset: r for offset, r in parsed[2].items()
            if not target['value'] <= offset < target['value'] + 208}
        self.assertEqual(outside(padded[0]), outside(padded[1]))
        self.assertEqual({offset - target['value']: r for offset, r in padded[1][2].items()
            if target['value'] <= offset < target['value'] + 208}, isolated[2])
        for name in padded[0][1]:
            previous, current = padded[0][1][name], padded[1][1][name]
            self.assertEqual(previous['value'], current['value'])
            if name != screen.FUNCTION:
                self.assertEqual(previous, current)
        self.assertEqual(normalized_pools(self.out / 'legacy-owner-before.o'),
                         normalized_pools(self.out / 'legacy-owner-after.o'))

        layout = self.out / 'target-layout.csv'
        with layout.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=('section', 'filename', 'function', 'address', 'end'))
            writer.writeheader()
            writer.writerows(row for row in rows if row['function'] == screen.FUNCTION)
        target_reference = self.root / 'conker/asm/nonmatchings/game_40490/func_15015104.s'
        outputs = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            asm = self.out / (script + '.s')
            args = [str(self.out / 'direct.o'), str(layout), 'game_40490', str(asm)] if script == 'pad_c_object.py' else [
                str(self.out / 'direct.o'), str(target_reference), str(asm), '--filename', 'game_40490']
            subprocess.run([sys.executable, str(self.root / 'tools' / script), *args], check=True, capture_output=True)
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'), '-o', str(obj), str(asm)],
                           check=True, capture_output=True)
            outputs.append(parse_object(obj))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0][1][screen.FUNCTION]['size'], 208)
        (self.out / 'owner.json').write_text(json.dumps(dict(neighbors=len(after[1]) - 1, warnings=len(warnings[1]),
            target_both_padders_identical=True, normalized_pools_equal=True,
            production_legacy_before_after_only_target_changed=True,
            strict_full_owner_rejects_unchanged_preexisting_neighbor_overflow=True), indent=2) + '\n')

    def test_06_independent_original_links_and_symbol_rebases(self):
        asm = self.out / 'original.s'
        asm.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' +
            (self.root / 'conker/asm/nonmatchings/game_40490/func_15015104.s').read_text())
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        for i, entry in enumerate((screen.ENTRY, 0x15215104, 0x15315104)):
            symbols = screen.SYMBOLS if i == 0 else {name: 0x15080000 + j * 0x100 for j, name in enumerate(screen.SYMBOLS)}
            with patch.object(screen, 'ENTRY', entry), patch.object(screen, 'SYMBOLS', symbols):
                _, candidate = screen.compile_candidate(self.root, self.out, 'rebase-' + str(i), self.body)
            ld = self.out / ('original-' + str(i) + '.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(ld), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            self.assertEqual(candidate, list(struct.unpack('>52I', sections(elf)['.text'][1])))

    def test_07_literal_whole_image_and_protected_inputs(self):
        current = (self.root / 'conker/build/conker.us.elf').read_bytes()
        offset = elf_slot_offset(current, screen.ENTRY, 208)
        self.assertEqual(offset, elf_slot_offset(self.before, screen.ENTRY, 208))
        source = (self.root / screen.SOURCE).read_text()
        expected = bytearray(self.before)
        if source == self.owner_after:
            expected[offset:offset + 208] = struct.pack('>52I', *self.retail)
            with patch.multiple(descriptor.screen, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
                self.assertEqual(descriptor.size_field(current), size_offset)
            struct.pack_into('>I', expected, size_offset, 208)
        else:
            self.assertEqual(source, self.owner_before)
        self.assertEqual(current, bytes(expected))
        for name in ('guards', 'progress', 'layout', 'makefile'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        data = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'linked-audit.json').write_text(json.dumps(dict(installed=source == self.owner_after,
            literal_image_only_declared_slot_and_size_field=True, data=data), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
