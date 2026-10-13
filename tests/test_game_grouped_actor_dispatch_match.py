"""Descriptor/actor lifetime, actual connected helpers and linked image isolation."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_grouped_actor_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests.test_game_one_shot_timer_match import symbol_rows, canonical_symbols
from tools.check_game_data_layout import audit_layout

GATES, RECORDS, LOOKUP, APPEND = screen.SYMBOLS.values()
GATE_DATA, RECORD_DATA, ACTOR, ALT = 0x22000, 0x23000, 0x26000, 0x27000
REG_COUNT, REG_BASE, OUTPUT_COUNT, OUTPUT, CALL_COUNT = 0x800DBEF0, 0x800DBEF4, 0x800C354A, 0x800C3550, 0x800C363A
CALLER = 0x15022754
GATE_VALUES, TYPE_VALUES = (0, 1, 3, 0x100, 0x8000, 0xFFFF), (0, 1, 3, 0x103, 0x8003, 0xFFFF)
BYTE_VALUES, STATES = (0, 1, 2, 0x7F, 0x80, 0x81, 0xFE, 0xFF), (0, 1, 2, 0x80, 0xFF)
INDICES = (0, 1, 7, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def source_function(source, name):
    match = re.search(r'(?:void|u8 \*)\s*' + name + r'\([^;{}]+\) \{\n.*?\n\}', source, re.S)
    if match is None:
        raise ValueError('Expected complete semantic function ' + name)
    return match.group(0)


def fixture(index=0, group=0, gate=1, kind=3, slot=1, state=1, tag=7):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x200, 0x80)}
    for base, size in ((GATE_DATA, 16), (RECORD_DATA, 64), (ACTOR, 160), (ALT, 160)):
        memory.update({base + i: (i * 13 + 0xA5) & 255 for i in range(size)})
    gate_slot, record_slot = (GATES + group * 4) & 0xFFFFFFFF, (RECORDS + group * 4) & 0xFFFFFFFF
    for address in (gate_slot, record_slot):
        memory.update({address + i: 0xA5 for i in range(4)})
    put(memory, gate_slot, (GATE_DATA - index * 2) & 0xFFFFFFFF)
    put(memory, record_slot, (RECORD_DATA - index * 8) & 0xFFFFFFFF)
    put(memory, GATE_DATA, gate, 2)
    put(memory, RECORD_DATA, kind, 2)
    put(memory, RECORD_DATA + 2, slot, 1)
    put(memory, ACTOR + 0x6E, state, 1)
    put(memory, ACTOR + 0x72, tag, 1)
    return memory


def apply_dispatch_symbol_serialization(expected):
    pair = {'D_800C35C8': 0x800C35C8, 'D_80099DEC': 0x80099DEC}
    rows = {name: (offset, fields, string) for offset, name, fields, string in symbol_rows(expected) if name in pair}
    assert set(rows) == set(pair)
    first, second = (rows[name] for name in pair)
    for name, value in pair.items():
        _, fields, string = rows[name]
        assert fields[1:] == (value, 0, 16, 0, 65521)
        assert expected[string:string + 11] == name.encode() + b'\0'
    assert abs(first[0] - second[0]) == 16
    assert abs(first[2] - second[2]) == 11
    struct.pack_into('>I', expected, first[0] + 4, second[1][1])
    struct.pack_into('>I', expected, second[0] + 4, first[1][1])
    expected[first[2]:first[2] + 11] = b'D_80099DEC\0'
    expected[second[2]:second[2] + 11] = b'D_800C35C8\0'


class AccessFault(Exception):
    pass


class DispatchOracle(TriangleOracle):
    def __init__(self, words, memory, index=0, group=0, phase=0, result=ACTOR, mutation=0,
                 entry=screen.ENTRY, connected=None):
        self.fault, self.accesses, self.in_hook = None, 0, False
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(index, group), connected=connected)
        self.result, self.mutation = result, mutation

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
        assert target in (screen.ENTRY, LOOKUP, APPEND)
        args = tuple(self.r[4:5 if target == LOOKUP else 6])
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        self.in_hook = True
        try:
            if target == LOOKUP:
                if self.mutation == 1:
                    self.put(ACTOR + 0x6E, 1, 1)
                    self.put(ACTOR + 0x72, 0xFF, 1)
                    self.put(RECORD_DATA, 0, 2)
                elif self.mutation == 2:
                    self.put(self.before[29] + 4, 0x80000001, 4)
                result = self.result
            else:
                assert target == APPEND
                if self.mutation:
                    self.put(ACTOR + 0x6E, 0x80, 1)
                    self.put(ACTOR + 0x72, 0x81, 1)
                if self.mutation == 2:
                    self.put(self.r[29] + 0x1C, ALT, 4)
                result = 0xA5000002
            for register in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[register] = 0xA5000000 + register
            self.f[:20] = [0xA5000000 + i for i in range(20)]
            self.r[2] = result
        finally:
            self.in_hook = False


def connected_fixture(group, count, mode, state):
    memory = fixture()
    for base, size in ((REG_COUNT, 4), (REG_BASE, 4), (GATES, 12), (RECORDS, 12),
                       (CALL_COUNT, 3), (OUTPUT_COUNT, 3), (OUTPUT, 90), (ACTOR, 800)):
        memory.update({base + i: 0xA5 for i in range(size)})
    put(memory, REG_COUNT, 5)
    put(memory, REG_BASE, ACTOR)
    for i in range(5):
        put(memory, ACTOR + i * 160 + 0x72, i + 1, 1)
        put(memory, ACTOR + i * 160 + 0x6E, state, 1)
    for g in range(3):
        gate_data, record_data = GATE_DATA + g * 32, RECORD_DATA + g * 64
        memory.update({gate_data + i: 0xA5 for i in range(32)})
        memory.update({record_data + i: 0xA5 for i in range(64)})
        put(memory, GATES + g * 4, gate_data)
        put(memory, RECORDS + g * 4, record_data)
        put(memory, CALL_COUNT + g, count, 1)
        put(memory, OUTPUT_COUNT + g, 2, 1)
        put(memory, OUTPUT + g * 30, 2, 1)
        put(memory, OUTPUT + g * 30 + 1, 4, 1)
        for i in range(8):
            put(memory, gate_data + i * 2, 0 if mode == 0 else 0x8000, 2)
            put(memory, record_data + i * 8, 0x103 if mode == 1 else 3, 2)
            put(memory, record_data + i * 8 + 2, 1 if mode == 3 else i % 6, 1)
    return memory


def connected_reference(memory, group):
    expected, calls = dict(memory), []
    index = 0
    while index < read(expected, CALL_COUNT + group, 1):
        calls.append((screen.ENTRY, (index, group)))
        gate = read(expected, GATES + group * 4) + index * 2
        record = read(expected, RECORDS + group * 4) + index * 8
        if read(expected, gate, 2) and read(expected, record, 2) == 3:
            slot = read(expected, record + 2, 1)
            calls.append((LOOKUP, (slot,)))
            actor = next((ACTOR + i * 160 for i in range(5) if slot and read(expected, ACTOR + i * 160 + 0x72, 1) == slot), 0)
            if actor and read(expected, actor + 0x6E, 1) == 1:
                value = read(expected, actor + 0x72, 1)
                calls.append((APPEND, (value, group)))
                count = read(expected, OUTPUT_COUNT + group, 1)
                if value not in [read(expected, OUTPUT + group * 30 + i, 1) for i in range(count)]:
                    put(expected, OUTPUT + group * 30 + count, value, 1)
                    put(expected, OUTPUT_COUNT + group, count + 1, 1)
                put(expected, actor + 0x6E, 0, 1)
        index += 1
    return expected, calls


class GameGroupedActorDispatchMatchTests(unittest.TestCase):
    run_native = native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-grouped-actor-dispatch-test'
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
        cls.owner_before = (cls.out / 'before-source').read_text().replace(screen.SELECTED, screen.ORIGINAL).replace(screen.TABLE_DECLARATIONS, '')
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.before = (cls.out / 'before-elf').read_bytes()
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'direct')
        cls.old_meta, cls.old = screen.compile_candidate(cls.root, cls.out, 'placeholder', screen.ORIGINAL)
        cls.other_meta, cls.other = screen.compile_candidate(cls.root, cls.out, 'record-first',
            screen.SELECTED.replace('    u8 *actor;\n    u8 *record;', '    u8 *record;\n    u8 *actor;'))
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>38I', cls.rom, screen.ROM))
        cls.helpers = {}
        for address, rom, words in ((LOOKUP, 0x141E5C, 28), (APPEND, 0x4FAF0, 31)):
            body = list(struct.unpack_from('>%dI' % words, cls.rom, rom))
            cls.helpers.update(zip(range(address, address + words * 4, 4), body))
        cls.caller = list(struct.unpack_from('>26I', cls.rom, 0x4FC04))
        cls.lookup_source = source_function((cls.root / 'conker/src/game/generated_13D350.c').read_text(), 'func_151149AC')
        cls.append_source = source_function(cls.owner_before, 'func_15022640')
        cls.caller_source = source_function(cls.owner_before, 'func_15022754')

    def test_01_complete_direct_body_real_spill_home_and_unchanged_helpers(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
                          self.meta['pool_bytes'], self.meta['diagnostics']), (38, 32, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.other_meta['body_words'], self.other_meta['frame'], self.other_meta['differences']), (38, 32, 2))
        self.assertEqual((self.old_meta['body_words'], self.old_meta['differences']), (3, 37))
        for address, rom, size in ((LOOKUP, 0x141E5C, 112), (APPEND, 0x4FAF0, 124), (CALLER, 0x4FC04, 104)):
            offset = elf_slot_offset(self.before, address, size)
            self.assertEqual(self.before[offset:offset + size], self.rom[rom:rom + size])
        self.assertTrue(all(not value[1] for name, value in sections(self.out / 'direct.o').items()
            if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))

    def test_02_guest_typed_gates_mutations_and_private_homes(self):
        count = 0
        for i, phase, result, mutation in itertools.product(range(1440), (0, 8), (0, ACTOR), range(3)):
            index, group = INDICES[i % 6], INDICES[i // 6 % 6]
            gate, kind = GATE_VALUES[i % 6], TYPE_VALUES[i // 6 % 6]
            slot, state, tag = BYTE_VALUES[i // 36 % 8], STATES[i // 288 % 5], BYTE_VALUES[i * 13 % 8]
            memory = fixture(index, group, gate, kind, slot, state, tag)
            pair = [DispatchOracle(words, memory, index, group, phase, result, mutation).run() for words in (self.retail, self.words)]
            for field in ('memory', 'events', 'r', 'f', 'calls'):
                self.assertEqual(getattr(pair[0], field), getattr(pair[1], field))
            expected = dict(memory)
            calls = []
            if gate and kind == 3:
                calls.append((LOOKUP, (slot,)))
                if mutation == 1:
                    put(expected, ACTOR + 0x6E, 1, 1)
                    put(expected, ACTOR + 0x72, 0xFF, 1)
                    put(expected, RECORD_DATA, 0, 2)
                if result and read(expected, ACTOR + 0x6E, 1) == 1:
                    calls.append((APPEND, (read(expected, ACTOR + 0x72, 1), 0x80000001 if mutation == 2 else group)))
                    if mutation:
                        put(expected, ACTOR + 0x6E, 0x80, 1)
                        put(expected, ACTOR + 0x72, 0x81, 1)
                    put(expected, (ALT if mutation == 2 else ACTOR) + 0x6E, 0, 1)
            self.assertEqual(pair[1].calls, calls)
            external = lambda m: {a: b for a, b in m.items() if not STACK - 0x200 <= a < STACK + 0x80}
            self.assertEqual(external(pair[1].memory), external(expected))
            count += 1
        self.assertEqual(count, 17280)
        old = DispatchOracle(self.old, fixture()).run()
        self.assertEqual(old.calls, [])
        pair = [DispatchOracle(words, fixture(), mutation=2).run() for words in (self.other, self.words)]
        self.assertNotEqual(pair[0].memory[ALT + 0x6E], pair[1].memory[ALT + 0x6E])
        (self.out / 'guest.json').write_text(json.dumps(dict(cases=count, group_home_and_actor_home_mutations_guest_only=True,
            source_order_control_effectively_rejected=True, sparse_full_word_indices_guest_only=True), indent=2) + '\n')

    def test_03_fail_closed_short_circuit_fields_and_all_own_access_cuts(self):
        cases = ((0, 3, 0, 1), (1, 0x103, ACTOR, 1), (1, 3, 0, 1), (1, 3, ACTOR, 0), (1, 3, ACTOR, 1))
        count = 0
        for phase, mutation, (gate, kind, result, state) in itertools.product((0, 8), range(3), cases):
            memory = fixture(gate=gate, kind=kind, state=state)
            normal = DispatchOracle(self.words, memory, phase=phase, result=result, mutation=mutation).run()
            for address, size, _ in normal.reads:
                if STACK - 0x200 <= address < STACK + 0x80:
                    continue
                for byte in range(size):
                    missing = dict(memory)
                    del missing[address + byte]
                    with self.assertRaises(AssertionError):
                        DispatchOracle(self.words, missing, phase=phase, result=result, mutation=mutation).run()
            if not gate:
                missing = {a: b for a, b in memory.items() if not RECORDS <= a < RECORDS + 4 and not RECORD_DATA <= a < RECORD_DATA + 64}
                self.assertEqual(DispatchOracle(self.words, missing, phase=phase).run().calls, [])
            for fault in range(normal.accesses):
                pair = [DispatchOracle(words, memory, phase=phase, result=result, mutation=mutation) for words in (self.retail, self.words)]
                for model in pair:
                    model.fault = fault
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses, fault)
                self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f),
                                 (pair[1].memory, pair[1].events, pair[1].r, pair[1].f))
                count += 1
            terminal = DispatchOracle(self.words, memory, phase=phase, result=result, mutation=mutation)
            terminal.fault = normal.accesses
            terminal.run()
        (self.out / 'faults.json').write_text(json.dumps(dict(fired_pairs=count, provider_accesses_excluded=True), indent=2) + '\n')

    def native_source(self, body, real=False):
        prefix = '''#define NULL ((void*)0)
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
static u16 gateData[3][8];static u8 records[3][64] __attribute__((aligned(8))),actors[800];
static u16 *D_800C35C8[3];static u8 *D_800C35F0[3];static u8 D_800C363A[3],D_800C354A[3],D_800C3550[3][30];
static s32 D_800DBEF0;static u8 *D_800DBEF4;
typedef char ABI[(sizeof(void*)==4 && sizeof(u16)==2 && sizeof(s32)==4)?1:-1];
static int error,mutation,calls,resultFlag;static u8 expectedSlot,expectedTag;static s32 expectedGroup;
'''
        if real:
            source = prefix + self.lookup_source + '\n' + self.append_source + '\n' + body + '\n' + self.caller_source
            check = '''
static int check(void){
 int g,n,mode,state,i,j,k;u8 expectedFlags[5],expectedRows[3][30],expectedCounts[3];
 for(g=0;g<3;g++)for(n=0;n<=5;n++)for(mode=0;mode<4;mode++)for(state=0;state<3;state++){
  D_800DBEF0=5;D_800DBEF4=actors;
  for(i=0;i<800;i++)actors[i]=(u8)(i*13+0xA5);
  for(i=0;i<5;i++){actors[i*160+0x72]=(u8)(i+1);actors[i*160+0x6E]=(u8)state;expectedFlags[i]=(u8)state;}
  for(i=0;i<3;i++){
   D_800C35C8[i]=gateData[i];D_800C35F0[i]=records[i];D_800C363A[i]=(u8)n;D_800C354A[i]=expectedCounts[i]=2;
   for(j=0;j<30;j++)D_800C3550[i][j]=expectedRows[i][j]=(u8)(j*7+0xA5);
   D_800C3550[i][0]=expectedRows[i][0]=2;D_800C3550[i][1]=expectedRows[i][1]=4;
   for(j=0;j<8;j++){gateData[i][j]=mode==0?0:0x8000;*(u16*)(records[i]+j*8)=mode==1?0x103:3;records[i][j*8+2]=mode==3?1:(u8)(j%6);}
  }
  for(i=0;i<n;i++)if(mode>1){
   int slot=mode==3?1:i%6;
   if(slot && expectedFlags[slot-1]==1){
    int seen=0;for(k=0;k<expectedCounts[g];k++)if(expectedRows[g][k]==slot)seen=1;
    if(!seen)expectedRows[g][expectedCounts[g]++]=(u8)slot;
    expectedFlags[slot-1]=0;
   }
  }
  func_15022754(g);
  for(i=0;i<5;i++)if(actors[i*160+0x6E]!=expectedFlags[i])return 1;
  for(i=0;i<3;i++){if(D_800C354A[i]!=expectedCounts[i])return 2;for(j=0;j<30;j++)if(D_800C3550[i][j]!=expectedRows[i][j])return 3;}
 }
 return 0;
}
'''
        else:
            source = prefix + '''
u8 *func_151149AC(u8 slot){
 if(slot!=expectedSlot)error=1;
 calls++;
 if(mutation){actors[0x6E]=1;actors[0x72]=0xFF;}
 return resultFlag?actors:NULL;
}
void func_15022640(s32 value,s32 group){
 if(value!=expectedTag || group!=expectedGroup || actors[0x6E]!=1)error=2;
 calls++;
 if(mutation){actors[0x6E]=0x80;actors[0x72]=0x81;}
}
''' + body
            check = '''
static int check(void){
 u16 gates[]={0,1,3,0x100,0x8000,0xFFFF},types[]={0,1,3,0x103,0x8003,0xFFFF};u8 states[]={0,1,2,0x80,0xFF};
 int i,g,x,m,r,j;u8 before[800],wanted[800];
 for(i=0;i<2048;i++)for(m=0;m<2;m++)for(r=0;r<2;r++){
  g=i%3;x=i%8;for(j=0;j<3;j++){D_800C35C8[j]=gateData[j];D_800C35F0[j]=records[j];}
  for(j=0;j<800;j++)actors[j]=before[j]=wanted[j]=(u8)(j*13+0xA5);
  gateData[g][x]=gates[i%6];*(u16*)(records[g]+x*8)=types[i/6%6];expectedSlot=records[g][x*8+2]=(u8)i;
  actors[0x6E]=before[0x6E]=wanted[0x6E]=states[i/36%5];actors[0x72]=wanted[0x72]=(u8)(i*13);
  error=calls=0;mutation=m;resultFlag=r;expectedGroup=g;expectedTag=m?0xFF:actors[0x72];
  if(gateData[g][x] && *(u16*)(records[g]+x*8)==3){
   if(m){wanted[0x6E]=1;wanted[0x72]=0xFF;}
   if(r && wanted[0x6E]==1){if(m)wanted[0x72]=0x81;wanted[0x6E]=0;}
  }
  func_150226BC(x,g);
  if(error)return 1;
  if(calls!=((gateData[g][x] && *(u16*)(records[g]+x*8)==3)?1+(r && (m || before[0x6E]==1)):0))return 2;
  for(j=0;j<800;j++)if(actors[j]!=wanted[j])return 3;
 }
 return 0;
}
'''
        return source + check + '\nvoid _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}\n'

    def test_04_connected_actual_caller_lookup_append_and_native_source(self):
        count = 0
        for group, total, mode, state, phase in itertools.product(range(3), (0, 1, 3, 5), range(4), (0, 1, 2), (0, 8)):
            memory = connected_fixture(group, total, mode, state)
            expected, calls = connected_reference(memory, group)
            pair = []
            for words in (self.retail, self.words):
                connected = dict(self.helpers)
                connected.update(zip(range(screen.ENTRY, screen.ENTRY + 152, 4), words))
                model = DispatchOracle(self.caller, memory, group, 0, phase, entry=CALLER, connected=connected).run()
                self.assertEqual(model.calls, calls)
                external = lambda m: {a: b for a, b in m.items() if not STACK - 0x200 <= a < STACK + 0x80}
                self.assertEqual(external(model.memory), external(expected))
                pair.append(model)
            self.assertEqual((pair[0].memory, pair[0].events, pair[0].r, pair[0].f),
                             (pair[1].memory, pair[1].events, pair[1].r, pair[1].f))
            count += 1
        self.assertEqual(count, 288)
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-real-' + profile[1:], self.native_source(screen.SELECTED, True), profile), (0, ''))
            self.assertEqual(self.run_native('native-provider-' + profile[1:], self.native_source(screen.SELECTED), profile), (0, ''))
        controls = [('narrow-type', screen.SELECTED.replace('*(u16 *)record != 3', 'record[0] != 3')),
                    ('early-clear', screen.SELECTED.replace('            func_15022640', '            actor[0x6E] = 0;\n            func_15022640')
                        .replace('            actor[0x6E] = 0;\n        }', '        }'))]
        for name, body in controls:
            self.assertNotEqual(body, screen.SELECTED)
            code, _ = self.run_native('negative-' + name, self.native_source(body))
            self.assertIn(code, (1, 2, 3))
        (self.out / 'connected.json').write_text(json.dumps(dict(guest_cases=count, caller_words=26,
            lookup_words=28, append_words=31, actual_instructions=True, native_profiles=['O2', 'O0'],
            native_real_cases_per_profile=216, native_provider_cases_per_profile=8192,
            native_comparisons=16816), indent=2) + '\n')

    def test_05_copied_owner_neighbors_pools_and_both_padders(self):
        objects = [screen.compile_owner(self.root, self.out, source, name) for source, name in
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
        self.assertEqual(after[0][target['value']:target['value'] + 152], isolated[0][:152])
        self.assertEqual({o - target['value']: r for o, r in after[2].items()
            if target['value'] <= o < target['value'] + 152}, isolated[2])
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for script in ('pad_c_object.py', 'pad_generated_object.py'):
            asm = self.out / (script + '.s')
            args = [str(objects[1][0]), str(self.root / 'conker/retail_layout.us.txt'), 'generated_49D30', str(asm)] if script == 'pad_c_object.py' else [
                str(objects[1][0]), str(self.root / 'conker/asm/49D30.s'), str(asm), '--filename', 'generated_49D30']
            result = subprocess.run([sys.executable, str(self.root / 'tools' / script), *args,
                '--word-patches', str(self.root / 'conker/retail_word_patches.us.csv')], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-I', str(self.root / 'conker'),
                '-o', str(obj), str(asm)], check=True, capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0], padded[1])
        self.assertEqual(padded[0][1][screen.FUNCTION]['size'], 152)
        (self.out / 'owner.json').write_text(json.dumps(dict(neighbors=len(after[1]) - 1,
            both_full_owner_padders_identical=True, normalized_pools_equal=True), indent=2) + '\n')

    def test_06_independent_original_symbol_rebases(self):
        original = (self.root / 'conker/asm/49D30.s').read_text().split('glabel ' + screen.FUNCTION + '\n', 1)[1]
        original = 'glabel ' + screen.FUNCTION + '\n' + original.split('endlabel ' + screen.FUNCTION, 1)[0] + 'endlabel ' + screen.FUNCTION + '\n'
        asm = self.out / 'original.s'
        asm.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + original)
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        for i, entry, symbols in ((0, screen.ENTRY, screen.SYMBOLS),
            (1, 0x152226BC, dict(screen.SYMBOLS, D_800C35C8=0x80107FFC, D_800C35F0=0x80208004)),
            (2, 0x153226BC, dict(screen.SYMBOLS, D_800C35C8=0x80318004, D_800C35F0=0x80417FFC))):
            with patch.object(screen, 'ENTRY', entry), patch.object(screen, 'SYMBOLS', symbols):
                _, candidate = screen.compile_candidate(self.root, self.out, 'rebase-' + str(i))
            ld = self.out / ('original-' + str(i) + '.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            elf = ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(ld), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            raw = sections(elf)['.text'][1]
            self.assertEqual(candidate, list(struct.unpack_from('>38I', raw)))
            self.assertFalse(any(raw[152:]))

    def test_07_literal_whole_image_protected_inputs_and_game_data(self):
        current = (self.root / self.paths['elf']).read_bytes()
        offset = elf_slot_offset(current, screen.ENTRY, 152)
        self.assertEqual(offset, elf_slot_offset(self.before, screen.ENTRY, 152))
        source = (self.root / screen.SOURCE).read_text()
        expected = bytearray(self.before)
        if source == self.owner_after:
            expected[offset:offset + 152] = struct.pack('>38I', *self.retail)
            with patch.multiple(descriptor.screen, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
                self.assertEqual(size_offset, descriptor.size_field(current))
            struct.pack_into('>I', expected, size_offset, 152)
            self.assertEqual(canonical_symbols(bytes(expected)), canonical_symbols(current))
            if self.before[offset:offset + 152] != struct.pack('>38I', *self.retail):
                apply_dispatch_symbol_serialization(expected)
        else:
            self.assertEqual(source, self.owner_before)
        self.assertEqual(current, bytes(expected))
        for name in ('guards', 'progress', 'layout', 'makefile'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'linked-audit.json').write_text(json.dumps(dict(installed=source == self.owner_after,
            literal_image_only_target_slot_size_and_closed_abs_serialization=True,
            named_symbols_unchanged_except_target_size=True,
            abs_pair=['D_800C35C8', 'D_80099DEC'], data=data), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
