"""Complete endpoint-pair semantics, aliases, real dispatcher and linked audit."""
import csv
import hashlib
import itertools
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_endpoint_pair_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_random_curve_record as native

ACTOR, PACKET, TABLE, DISPATCH = 0x20000, 0x21000, 0x8008A8D8, 0x15149434
WORD_VALUES = (0, 1, 0x80000000, 0xFFFFFFFF)
CODE_PAIRS = ((0, 255), (255, 0), (0x45, 0x90))
ALIASES = (-4, 0, 4, 8, 12, -8, -16, -20)


def cases():
    for values, codes in itertools.product(itertools.product(WORD_VALUES, repeat=4), CODE_PAIRS):
        yield (*values, *codes, 0x2D, None)
    for kind, match in itertools.product(range(256), (False, True)):
        yield (1, 0x80000000, 1 if match else 0, 0x80000000 if match else 0,
            kind, 255 - kind, 0xA5BC0000 | kind, None)
    for byte in range(256):
        yield (0xFFFFFFFF, 0, 0xFFFFFFFF, 0, byte, byte ^ 255, 0x2D, None)
        yield (0xFFFFFFFF, 0, 0, 0xFFFFFFFF, byte, byte ^ 255, 0x2D, None)
    for offset, values, codes in itertools.product(ALIASES, itertools.product((0, 1), repeat=4), CODE_PAIRS):
        yield (*values, *codes, 0x2D, offset)


def fixture(case, phase=0, packet=None):
    first, second, dest_first, dest_second, code_first, code_second, kind, offset = case
    pointer = packet if packet is not None else PACKET if offset is None else ACTOR + 0x28 + offset
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x100, 0x140)}
    for base, size in ((ACTOR - 32, 0x180), (PACKET - 16, 48)):
        memory.update({base + i: (i * 13 + 0x5A) & 255 for i in range(size)})
    put(memory, pointer, first)
    put(memory, pointer + 4, second)
    put(memory, pointer + 8, code_first, 1)
    put(memory, pointer + 9, code_second, 1)
    put(memory, ACTOR + 0x28, dest_first)
    put(memory, ACTOR + 0x30, dest_second)
    return memory, (ACTOR, pointer, kind)


def reference(memory, args, phase=0):
    memory, events = memory.copy(), []
    def get(address, size):
        if any(address + i not in memory for i in range(size)):
            raise KeyError(('read', address, size))
        value = int.from_bytes(bytes(memory[address + i] for i in range(size)), 'big')
        events.append(('R', address, size, value))
        return value
    def write(address, value, size):
        if any(address + i not in memory for i in range(size)):
            raise KeyError(('write', address, size))
        put(memory, address, value, size)
        events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))
    owner, packet, kind = args
    fault = None
    try:
        write(STACK + phase + 8, kind, 4)
        if kind & 255 == 0x2D:
            first, existing = get(packet, 4), get(owner + 0x28, 4)
            if first == existing:
                second = get(packet + 4, 4)
                write(owner + 0x28, second, 4)
                write(owner + 0x2C, get(packet + 9, 1), 1)
                second, first = get(packet + 4, 4), get(packet, 4)
            else:
                second = get(packet + 4, 4)
                if second == existing:
                    write(owner + 0x28, first, 4)
                    write(owner + 0x2C, get(packet + 8, 1), 1)
                    second, first = get(packet + 4, 4), get(packet, 4)
            existing = get(owner + 0x30, 4)
            if first == existing:
                write(owner + 0x30, second, 4)
                write(owner + 0x34, get(packet + 9, 1), 1)
            elif second == existing:
                write(owner + 0x30, first, 4)
                write(owner + 0x34, get(packet + 8, 1), 1)
    except KeyError as error:
        fault = error.args[0]
    return memory, events, fault


class PairOracle(TriangleOracle):
    def __init__(self, words, memory, args, phase=0, entry=screen.ENTRY, connected=None):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=args, connected=connected)

    def get(self, address, size):
        if any(address + i not in self.memory for i in range(size)):
            raise KeyError(('read', address, size))
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording and any(address + i not in self.memory for i in range(size)):
            raise KeyError(('write', address, size))
        super().put(address, value, size)

    def record_call(self, target):
        assert target == screen.ENTRY
        self.calls.append((target, self.arguments(3)))


def run(model):
    fault = None
    try:
        model.run()
    except KeyError as error:
        fault = error.args[0]
    return model.memory, model.events, fault


def size_field(data):
    h = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, h[6] + i * h[11]) for i in range(h[12])]
    offsets = []
    for section in headers:
        if section[1] != 2:
            continue
        names_section = headers[section[6]]
        names = data[names_section[4]:names_section[4] + names_section[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == screen.FUNCTION:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                offsets.append(offset + 8)
    assert len(offsets) == 1
    return offsets[0]


class GameEndpointPairTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-endpoint-pair-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>39I', rom, screen.ROM))
        cls.dispatch = list(struct.unpack_from('>23I', rom, 0x1768E4))
        cls.all_cases = list(cases())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists() and screen.ORIGINAL in (cls.root / screen.SOURCE).read_text():
            hashes = {}
            for name, path in dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
                    guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv').items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def test_01_direct_complete_shape_and_profile(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (39, 0, 0, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertFalse(self.meta['relocations'])
        records = []
        for profile in ('o2g3', 'o2', 'o1g3', 'o1'):
            meta, _ = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            records.append(meta)
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(row['function'] == screen.FUNCTION for row in csv.DictReader(stream)))
        self.receipt('shape', dict(records=records, raw_byte_exact=True, target_guards=0))

    def test_02_independent_ordered_reference_and_all_branches(self):
        coverage, count = set(), 0
        for case, phase in itertools.product(self.all_cases, (0, 8)):
            memory, args = fixture(case, phase)
            expected = reference(memory, args, phase)
            self.assertIsNone(expected[2])
            for words in (self.words, self.retail):
                model = PairOracle(words, memory, args, phase)
                self.assertEqual(run(model), expected)
                self.assertEqual(model.calls, [])
                coverage.update(model.visits)
            count += 1
        self.assertEqual(coverage, {screen.ENTRY + i * 4 for i in range(39) if i != 17})
        self.receipt('guest', dict(cases=count, executions=count * 2, reachable_words=38,
            unreachable_word_indices=[17], all_command_and_associated_byte_values=True,
            all_four_endpoint_class_combinations=True, full_memory_and_ordered_access=True,
            alias_layouts=len(ALIASES)))

    def test_03_missing_bytes_lazy_gate_and_argument_home_aliases(self):
        count = 0
        probes = [self.all_cases[i] for i in (0, 3, 9, 21, 100, 765, 1792, 1804, 2100)]
        for case in probes:
            memory, args = fixture(case)
            accesses = reference(memory, args)[1]
            for address in sorted({a + i for _, a, size, _ in accesses for i in range(size)}):
                missing = memory.copy()
                del missing[address]
                expected = reference(missing, args)
                for words in (self.words, self.retail):
                    self.assertEqual(run(PairOracle(words, missing, args)), expected)
                count += 1
        for phase, offset, kind in itertools.product((0, 8), (0, 4, 8, 12), (0, 0x2D, 0xABCD002D)):
            case = (1, 2, 1, 2, 0x81, 0xFE, kind, None)
            memory, args = fixture(case, phase, packet=STACK + phase + offset)
            expected = reference(memory, args, phase)
            for words in (self.words, self.retail):
                self.assertEqual(run(PairOracle(words, memory, args, phase)), expected)
        for kind in range(256):
            if kind == 45:
                continue
            memory = {STACK + i: 0xA5 for i in range(32)}
            args = (0, 0, kind)
            for words in (self.words, self.retail):
                self.assertEqual(run(PairOracle(words, memory, args)), reference(memory, args))
        self.receipt('faults', dict(missing_byte_pairs=count, argument_home_alias_cases=48,
            lazy_command_cases=255, emitted_guest_fault_prefix_not_C_or_hardware=True))

    def test_04_native32_defined_fields_aliases_and_actual_dispatch_source(self):
        dispatcher_source = (self.root / 'conker/src/game/done/game_1765E0.c').read_text()
        dispatcher = re.search(r'void func_15149434\([^;{}]+\) \{\n.*?\n\}', dispatcher_source, re.S).group(0)
        rows = ',\n'.join('{' + ','.join('0x%08Xu' % (v & 0xFFFFFFFF) for v in case[:7])
            + ',' + str(-999 if case[7] is None else case[7]) + '}' for case in self.all_cases)
        self.fixture = '''typedef unsigned char u8; typedef int s32; typedef unsigned int u32;
typedef struct { u8 reserved[0x13]; u8 unk13; u8 rest[0x10]; } struct260;
typedef char SelectorOffset[(__builtin_offsetof(struct260,unk13)==0x13)?1:-1];
static void (*D_8008A8D8[74])(struct260 *,s32,u8);
''' + screen.SELECTED + '''
static void adapter(struct260 *owner,s32 address,u8 kind) {
    func_151B2F04((u8 *)owner,(u8 *)address,kind);
}
''' + dispatcher + '''
static union { u32 align; u8 bytes[0x400]; } actual, expected;
static u32 rows[][8]={
''' + rows + r'''
};
static u32 load(const u8 *p) { return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24); }
static void store(u8 *p,u32 v) { int i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8)); }
static void ref(u8 *owner,u8 *packet,u8 kind) {
    u8 *pair=owner+0x28;
    if(kind!=45)return;
    if(load(packet)==load(pair)) { store(pair,load(packet+4));pair[4]=packet[9]; }
    else if(load(packet+4)==load(pair)) { store(pair,load(packet));pair[4]=packet[8]; }
    if(load(packet)==load(pair+8)) { store(pair+8,load(packet+4));pair[12]=packet[9]; }
    else if(load(packet+4)==load(pair+8)) { store(pair+8,load(packet));pair[12]=packet[8]; }
}
static void initialize(u32 *row) {
    int i,offset=(s32)row[7]==-999?0x200:0x80+0x28+(s32)row[7];
    for(i=0;i<0x400;i++)actual.bytes[i]=(u8)(i*13+0x5a);
    store(actual.bytes+offset,row[0]);store(actual.bytes+offset+4,row[1]);
    actual.bytes[offset+8]=(u8)row[4];actual.bytes[offset+9]=(u8)row[5];
    store(actual.bytes+0xa8,row[2]);store(actual.bytes+0xb0,row[3]);
}
static void (*callback)(u8 *,u8 *,u8)=func_151B2F04;
'''
        self.run_host(r'''
u32 row,mode,i; int offset; u8 index;
D_8008A8D8[18]=adapter;
for(row=0;row<sizeof(rows)/sizeof(rows[0]);row++) {
    offset=(s32)rows[row][7]==-999?0x200:0xa8+(s32)rows[row][7];
    for(mode=0;mode<6;mode++) {
        initialize(rows[row]);
        index=mode<=1?18:mode==2?0:mode==3?73:mode==4?74:255;
        actual.bytes[0x93]=index;
        for(i=0;i<0x400;i++)expected.bytes[i]=actual.bytes[i];
        if(mode<=1)ref(expected.bytes+0x80,expected.bytes+offset,(u8)rows[row][6]);
        if(mode==0)callback(actual.bytes+0x80,actual.bytes+offset,(u8)rows[row][6]);
        else func_15149434((struct260 *)(actual.bytes+0x80),(s32)(actual.bytes+offset),(u8)rows[row][6]);
        for(i=0;i<0x400;i++)if(actual.bytes[i]!=expected.bytes[i])return 1;
    }
}
''')
        self.receipt('native', dict(cases=len(self.all_cases) * 6, actual_native32=True,
            typed_direct_callback=True, actual_dispatch_source_with_layout_projection=True,
            existing_integer_packet_interface_via_typed_adapter=True,
            complete_actual_expected_canaries=True, all_other_table_entries_bounded_NULL=True))

    def test_05_copied_owner_and_effective_negatives(self):
        source = (self.root / screen.SOURCE).read_text()
        before = source.replace(screen.SELECTED, screen.ORIGINAL)
        self.assertEqual(before.count(screen.ORIGINAL), 1)
        objects, owner_diagnostics = [], []
        for name, text in (('before', before), ('after', before.replace(screen.ORIGINAL, screen.SELECTED))):
            obj, diagnostics = compile_owner(self.root, self.out, text, name)
            owner_diagnostics.append(diagnostics)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((self.out / (name + '.c')).relative_to(self.root / 'conker')),
                '--post-process', str(obj.relative_to(self.root / 'conker')),
                '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
        self.assertEqual(owner_diagnostics[0], owner_diagnostics[1])
        self.assertEqual(len(owner_diagnostics[0]), 4)
        self.assertTrue(all(code == '712' and line.strip() in (
            'func_151B220C(arg0);', 'func_151B2FD0(arg0);')
            for code, line, _ in owner_diagnostics[0]))
        old, old_fn, old_rel = parse_object(objects[0])
        new, new_fn, new_rel = parse_object(objects[1])
        self.assertEqual(old_fn.keys(), new_fn.keys())
        for name, function in new_fn.items():
            if name == screen.FUNCTION:
                continue
            prior = old_fn[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            self.assertEqual({o-function['value']:r for o,r in new_rel.items()
                if function['value']<=o<function['value']+function['size']},
                {o-prior['value']:r for o,r in old_rel.items()
                if prior['value']<=o<prior['value']+prior['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertTrue(emit_padded_assembly(objects[1], self.root / 'conker/asm/1DF510.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_1DF510'))
        negatives = {'wrong-gate': screen.SELECTED.replace('0x2D', '0x2E'),
            'wrong-code': screen.SELECTED.replace('pair[4] = packet[9]', 'pair[4] = packet[8]'),
            'skip-second': screen.SELECTED.replace('if (*(s32 *)packet == *(s32 *)(pair + 8))',
                'if (0)'),
            'wrong-destination': screen.SELECTED.replace('pair[12]', 'pair[13]'),
            'cached-packet': screen.SELECTED.replace('    u8 *pair =', '    s32 first = *(s32 *)packet;\n'
                '    s32 second = *(s32 *)(packet + 4);\n    u8 *pair =').replace(
                '*(s32 *)(packet + 4)', 'second').replace('*(s32 *)packet', 'first').replace(
                's32 first = first;', 's32 first = *(s32 *)packet;').replace(
                's32 second = second;', 's32 second = *(s32 *)(packet + 4);')}
        for name, body in negatives.items():
            _, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            effective = False
            for case in self.all_cases:
                memory, args = fixture(case)
                if run(PairOracle(words, memory, args))[0] != reference(memory, args)[0]:
                    effective = True
                    break
            self.assertTrue(effective, name)
        self.receipt('owner', dict(neighbors=len(new_fn)-1, unchanged_pools_relative_relocations=True,
            existing_owner_diagnostics=4, new_owner_diagnostics=0,
            actual_padder_accepts=True, negatives=list(negatives), negatives_change_final_memory=True))

    def test_06_independent_original_candidate_links(self):
        assembly = (self.root / 'conker/asm/1DF510.s').read_text().split('glabel ' + screen.FUNCTION, 1)[1]
        assembly = 'glabel ' + screen.FUNCTION + assembly.split('endlabel ' + screen.FUNCTION, 1)[0]
        original = self.out / 'original.s'
        original.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + assembly)
        obj = original.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(original)],
            cwd=self.root, check=True, capture_output=True)
        probes = self.all_cases[::73]
        for entry in (screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000):
            bodies = []
            script = self.out / ('rebase-%x.ld' % entry)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            for name, path in (('original', obj), ('candidate', self.out / 'selected.o')):
                elf = self.out / ('rebase-%x-%s.elf' % (entry, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                    '-e', screen.FUNCTION, '-o', str(elf), str(path)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>39I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            for case, phase in itertools.product(probes, (0, 8)):
                memory, args = fixture(case, phase)
                expected = reference(memory, args, phase)
                for words in bodies:
                    self.assertEqual(run(PairOracle(words, memory, args, phase, entry=entry)), expected)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, relocation_uses=0,
            cases=4 * len(probes) * 2, exact_at_each_link=True))

    def test_07_actual_dispatcher_guest(self):
        count = 0
        for selector, command, phase in itertools.product(range(256), (0, 45, 0xABC0002D, 255), (0, 8)):
            case = (1, 2, 1, 2, 0xAA, 0xFE, command, None)
            memory, args = fixture(case, phase)
            put(memory, ACTOR + 0x13, selector, 1)
            for index in range(74):
                put(memory, TABLE + index * 4, screen.ENTRY if index == 18 else 0)
            outcomes = []
            for words in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 156, 4), words))
                model = PairOracle(self.dispatch, memory, args, phase, entry=DISPATCH, connected=connected).run()
                self.assertEqual(len(model.calls), int(selector == 18))
                if selector == 18:
                    self.assertEqual(model.calls, [(screen.ENTRY, (ACTOR, PACKET, command & 255))])
                outcomes.append((model.memory, model.events, model.calls))
            self.assertEqual(outcomes[0], outcomes[1])
            expected = reference(memory, (ACTOR, PACKET, command & 255), phase)[0] if selector == 18 else memory
            self.assertEqual({a:v for a,v in outcomes[0][0].items() if ACTOR-32<=a<ACTOR+0x160},
                {a:v for a,v in expected.items() if ACTOR-32<=a<ACTOR+0x160})
            count += 1
        self.receipt('dispatcher', dict(cases=count, executions=count*2, actual_retail_dispatch_words=23,
            all_selector_bytes_and_word_command_truncation=True, other_slots_bounded_NULL=True))

    def test_08_installed_whole_ELF_and_actual_table(self):
        current = (self.root / 'conker/build/conker.us.elf').read_bytes()
        elf_sections = sections(self.root / 'conker/build/conker.us.elf')
        address = TABLE + 18 * 4
        pointers = [chunk[address-base:address-base+4] for base,chunk in elf_sections.values()
            if base<=address and address+4<=base+len(chunk)]
        self.assertEqual(pointers, [struct.pack('>I', screen.ENTRY)])
        caller = [chunk[DISPATCH-base:DISPATCH-base+92] for base,chunk in elf_sections.values()
            if base<=DISPATCH and DISPATCH+92<=base+len(chunk)]
        self.assertEqual(caller, [struct.pack('>23I', *self.dispatch)])
        if not (self.out / 'baseline.json').exists():
            self.skipTest('immutable local pre-install history is absent; actual table/caller checked')
        baseline = json.loads((self.out / 'baseline.json').read_text())
        before = (self.out / 'before-elf').read_bytes()
        installed = screen.SELECTED in (self.root / screen.SOURCE).read_text()
        if installed:
            expected = bytearray(before)
            offset = elf_slot_offset(before, screen.ENTRY, 156)
            expected[offset:offset+156] = struct.pack('>39I', *self.retail)
            size = size_field(before)
            self.assertEqual(size_field(current), size)
            self.assertEqual(struct.unpack_from('>I', before, size)[0], 12)
            self.assertEqual(struct.unpack_from('>I', current, size)[0], 156)
            struct.pack_into('>I', expected, size, 156)
            self.assertEqual(current, bytes(expected))
        else:
            self.assertEqual(current, before)
        for name,path in dict(guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv').items():
            value = (self.root / path).read_bytes()
            self.assertEqual(value, (self.out / ('before-'+name)).read_bytes())
            self.assertEqual(hashlib.sha256(value).hexdigest(), baseline[name])
        audit = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('audit', dict(installed=installed, only_target_slot_and_size_change=installed,
            guards_and_progress_identical=True, protected_data_layout=audit,
            source_sha256=hashlib.sha256((self.root / screen.SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest(), actual_callback_selector=18,
            actual_dispatcher_identical_to_retail=True))


if __name__ == '__main__':
    unittest.main()
