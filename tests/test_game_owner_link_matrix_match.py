"""Direct 65-word match, link aliases, complete caller/helper and linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_link_matrix_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_random_curve_record as native
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests import test_game_point_transform_match as point
from tools.tests import test_game_owner_actor_update_match as actor

ACTOR, LINK, FIRST, SECOND, OUTPUT = 0x20000, 0x21000, 0x22000, 0x23000, 0x24000
PALETTE, ALTERNATE = 0x28000, 0x30000
HELPER, WRAPPER, DISPATCH, REMOVE, TABLE = 0x15143134, 0x151B2FA0, 0x151B3184, 0x1516972C, 0x8008FAF0
MODES = (0, 1, 255, 256, 257, 0x80000000, 0xFFFFFF00, 0xFFFFFFFF)


def fixture(flags=255, state=0, index=0, link=LINK, actor_address=ACTOR):
    memory = {STACK + i: (i * 13 + 0xA5) & 255 for i in range(-0x600, 0x140)}
    for base, length in ((ACTOR, 0x190), (link, 40), (FIRST, 0x1E0), (SECOND, 0x1E0),
            (OUTPUT, 32), (PALETTE, 128), (ALTERNATE, 128),
            (PALETTE + index * 64, 128), (ALTERNATE + index * 64, 128), (TABLE, 16)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(length)})
    for offset, value, size in ((0, FIRST, 4), (4, 0x87, 1), (5, index, 1),
            (0x14, SECOND, 4), (0x18, 0x87, 1), (0x19, index, 1)):
        put(memory, link + offset, value, size)
    for base, bank in ((FIRST, PALETTE), (SECOND, ALTERNATE)):
        put(memory, base, 1)
        put(memory, base + 0x3B, 0x87, 1)
        put(memory, base + 0x1D4, bank)
    for offset, value in zip((8, 12, 16, 28, 32, 36),
            (0x3F800000, 0x80000000, 0x7FC12345, 0xBF800000, 1, 0x7F800000)):
        put(memory, link + offset, value)
    if state in (1, 2): put(memory, (FIRST if state == 1 else SECOND) + 0x1D4, 0)
    if state in (3, 5): put(memory, FIRST if state == 3 else SECOND, 0)
    if state in (4, 6): put(memory, (FIRST if state == 4 else SECOND) + 0x3B, 0x86, 1)
    put(memory, actor_address + 0x10, flags, 1)
    return memory


def reference(memory, arguments):
    memory = memory.copy()
    owner, link, destination, mode = arguments
    first, second = point.read(memory, link), point.read(memory, link + 0x14)
    if not point.read(memory, first + 0x1D4) or not point.read(memory, second + 0x1D4):
        memory[owner + 0x10] |= 12
        return point.external_memory(memory), [], 1
    if (not point.read(memory, first) or memory[link + 4] != memory[first + 0x3B] or
            not point.read(memory, second) or memory[link + 0x18] != memory[second + 0x3B]):
        return point.external_memory(memory), [], 0
    enabled = bool(mode & 255)
    memory[owner + 0x10] &= ~(4 if enabled else 8)
    source = link + (8 if enabled else 28)
    node, offset = (first, 5) if enabled else (second, 25)
    matrix = point.read(memory, node + 0x1D4) + memory[link + offset] * 64
    # Deliberately bounded helper: sequential raw-word copies salted by matrix[0].
    for i in range(3):
        put(memory, destination + i * 4, point.read(memory, source + i * 4) ^ point.read(memory, matrix))
    return point.external_memory(memory), [(HELPER, source, destination, matrix)], 1


class LinkOracle(actor.ActorOracle):
    def __init__(self, words, memory, arguments, phase=0, entry=screen.ENTRY, connected=None, helper=HELPER):
        TriangleOracle.__init__(self, words, memory, arguments=arguments, phase=phase, entry=entry, connected=connected)
        self.helper = helper

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 39:
            rs, rt, rd = word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            self.r[rd] = ~(self.r[rs] | self.r[rt]) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        assert target in (self.helper, screen.ENTRY, WRAPPER, REMOVE)
        self.calls.append((target, *self.r[4:7]) if target != REMOVE else (target, self.r[4]))

    def hook(self, target):
        if target == self.helper:
            source, destination, matrix = self.r[4:7]
            for i in range(3): self.put(destination + i * 4, self.get(source + i * 4, 4) ^ self.get(matrix, 4), 4)
        else:
            assert target == REMOVE
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register


class ConnectedOracle(point.PointOracle):
    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 39:
            LinkOracle.execute(self, word)
        else:
            super().execute(word)

    def record_call(self, target):
        if target in (HELPER, screen.ENTRY):
            self.calls.append((target, *self.r[4:7]))
        else:
            super().record_call(target)


class GameOwnerLinkMatrixMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-link-matrix-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>65I', cls.rom, screen.ROM))
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(baseline.read_text())
        cls.coverage, cls.cases = set(), 0
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        cls.fixture = '''typedef unsigned char u8; typedef unsigned int u32;
typedef int s32; typedef float f32;
#define NULL ((void *)0)
''' + screen.TYPES + screen.DECLARATIONS + '''
static union {u32 align; u8 bytes[0x200];} owner, first, second;
static struct {u8 prefix[16];OwnerMatrixLink47D8 value;} linkStorage;
#define fixtureLink linkStorage.value
static u32 palette[4096],alternate[4096],destination[5];
static u32 calls; static f32 *seenPoint,*seenDestination; static u8 *seenMatrix;
void func_15143134(f32 *p,f32 *out,u8 *matrix) {
    int i;calls++;seenPoint=p;seenDestination=out;seenMatrix=matrix;
    for(i=0;i<3;i++)((u32 *)out)[i]=((u32 *)p)[i]^*(u32 *)matrix;
}
static void reset(int flags,int state,int index) {
    int i;calls=0;
    for(i=0;i<0x200;i++)owner.bytes[i]=first.bytes[i]=second.bytes[i]=0xA5;
    for(i=0;i<4096;i++){palette[i]=(u32)i;alternate[i]=(u32)i^0xFFFFFFFF;}
    for(i=0;i<5;i++)destination[i]=0xA5A5A5A5;
    fixtureLink.first=first.bytes;fixtureLink.second=second.bytes;
    fixtureLink.firstEpoch=fixtureLink.secondEpoch=0x87;fixtureLink.firstMatrix=fixtureLink.secondMatrix=(u8)index;
    for(i=0;i<3;i++){((u32 *)fixtureLink.firstPosition)[i]=0x80000000+(u32)i;
        ((u32 *)fixtureLink.secondPosition)[i]=0x7F800000+(u32)i;}
    *(u32 *)first.bytes=*(u32 *)second.bytes=1;
    first.bytes[0x3B]=second.bytes[0x3B]=0x87;
    *(u8 **)(first.bytes+0x1D4)=(u8 *)palette;*(u8 **)(second.bytes+0x1D4)=(u8 *)alternate;
    if(state==1)*(u8 **)(first.bytes+0x1D4)=NULL;
    if(state==2)*(u8 **)(second.bytes+0x1D4)=NULL;
    if(state==3)*(u32 *)first.bytes=0;
    if(state==4)first.bytes[0x3B]=0x86;
    if(state==5)*(u32 *)second.bytes=0;
    if(state==6)second.bytes[0x3B]=0x86;
    owner.bytes[0x10]=(u8)flags;
}
''' + screen.SELECTED + '\n#define link fixtureLink\n'

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=1, phase=0, owner=ACTOR, link=LINK, destination=OUTPUT):
        args = (owner, link, destination, mode)
        models = [LinkOracle(words, memory, args, phase).run() for words in (self.retail, self.words)]
        self.assertEqual((models[0].memory, models[0].events, models[0].calls, models[0].r[2]),
            (models[1].memory, models[1].events, models[1].calls, models[1].r[2]))
        self.assertEqual((point.external_memory(models[0].memory), models[0].calls, models[0].r[2]), reference(memory, args))
        self.assertEqual(point.read(models[0].memory, STACK + phase + 12), mode)
        self.assertEqual(point.read(models[0].memory, STACK + phase + 8), destination)
        self.coverage.update(models[0].visits)
        self.cases += 1
        return models[0]

    def test_01_complete_direct_shape(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (65, 24, 0, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.words, self.retail)
        self.assertEqual(parse_object(self.out / 'selected.o')[2], {232: [('R_MIPS_26', 'func_15143134')]})
        self.receipt('shape', dict(raw=self.meta, new_guards=0))

    def test_02_widths_gates_all_flags_and_indices(self):
        start = self.cases
        for mode, flags, state, index, phase in itertools.product(MODES, (0, 4, 8, 12, 0xA5, 255), range(7), (0, 1, 127, 255), (0, 8)):
            self.compare(fixture(flags, state, index), mode, phase)
        for index, mode in itertools.product(range(256), (0, 1)):
            self.compare(fixture(index, index=index), mode)
        expected = set(range(screen.ENTRY, screen.ENTRY + 260, 4)) - {screen.ENTRY + 0x4C, screen.ENTRY + 0xD8}
        self.assertEqual(self.coverage, expected)
        self.receipt('matrix', dict(cases=self.cases - start, executions=(self.cases - start) * 2,
            reachable_words=63, unreachable_repeated_loads=['0x4C', '0xD8'],
            full_argument_homes_saved_registers_stack_and_all_memory_equal=True))

    def test_03_aliases_and_effective_compiled_controls(self):
        count = 0
        for mode, destination in itertools.product((0, 1), (OUTPUT, LINK + 8, LINK + 12, LINK + 28, FIRST, FIRST + 0x1D4, ACTOR + 0x10)):
            self.compare(fixture(), mode, destination=destination)
            count += 1
        for base, offset, mode in ((FIRST, 0x1D7, 1), (SECOND, 0x1D7, 0), (LINK, 5, 1),
                (LINK, 25, 0), (LINK, 3, 1), (LINK, 4, 1), (FIRST, 3, 1)):
            owner = base + offset - 0x10
            memory = fixture(12, actor_address=owner)
            if base == LINK and offset == 3:
                node = FIRST + 12
                memory.update({node + i: 0xA5 for i in range(0x1E0)})
                put(memory, node, 1)
                put(memory, node + 0x3B, 0x87, 1)
                put(memory, node + 0x1D4, PALETTE)
            if base == LINK and offset == 4:
                put(memory, FIRST + 0x3B, 12, 1)
            # Index aliases change12 to8/4, so retain both banks' selected entries.
            for bank in (PALETTE, ALTERNATE):
                for i in range(12 * 64 + 128): memory.setdefault(bank + i, i & 255)
            self.compare(memory, mode, owner=owner)
            count += 1
        scenarios = {
            'negative-full-word-selector': (fixture(), (ACTOR, LINK, OUTPUT, 256)),
            'negative-wrong-flag': (fixture(), (ACTOR, LINK, OUTPUT, 1)),
            'negative-wrong-output': (fixture(), (ACTOR, LINK, OUTPUT, 1)),
            'negative-short-index': (fixture(index=1), (ACTOR, LINK, OUTPUT, 1)),
            'negative-missing-epoch': (fixture(state=4), (ACTOR, LINK, OUTPUT, 1)),
            'negative-cached-palette': (fixture(12, actor_address=FIRST + 0x1C7), (FIRST + 0x1C7, LINK, OUTPUT, 1)),
        }
        for name, body in screen.candidates():
            if name not in scenarios: continue
            _, words = screen.compile_candidate(self.root, self.out, name, body)
            memory, args = scenarios[name]
            good = LinkOracle(self.words, memory, args).run()
            bad = LinkOracle(words, memory, args).run()
            self.assertNotEqual((point.external_memory(good.memory), good.calls, good.r[2]),
                (point.external_memory(bad.memory), bad.calls, bad.r[2]), name)
        self.receipt('aliases', dict(alias_cases=count, effective_complete_compiled_controls=len(scenarios)))

    def test_04_fault_prefixes_and_short_circuit(self):
        cases = ((LINK, 4), (LINK + 20, 4), (FIRST + 0x1D4, 4), (SECOND + 0x1D4, 4),
            (FIRST, 4), (LINK + 4, 1), (FIRST + 0x3B, 1), (SECOND, 4), (LINK + 24, 1),
            (SECOND + 0x3B, 1), (ACTOR + 0x10, 1), (LINK + 5, 1), (LINK + 25, 1), (OUTPUT, 4))
        for address, length in cases:
            mode = 0 if address == LINK + 25 else 1
            memory = fixture()
            for i in range(length): del memory[address + i]
            outcomes = []
            for words in (self.retail, self.words):
                model = LinkOracle(words, memory, (ACTOR, LINK, OUTPUT, mode))
                with self.assertRaises(AssertionError): model.run()
                outcomes.append((model.memory, model.events, model.calls))
            self.assertEqual(outcomes[0], outcomes[1])
        memory = fixture(state=1)
        for i in range(4): del memory[SECOND + 0x1D4 + i]
        self.compare(memory)
        memory = fixture(state=3)
        del memory[LINK + 4]
        self.compare(memory)
        self.receipt('faults', dict(paired_fault_prefixes=len(cases), missing_first_palette_and_dead_first_short_circuit=True,
            emitted_guest_order_only_not_portable_C_fault_semantics=True))

    def test_05_actual_native32_full_C_and_record_layout(self):
        self.run_host('''
static u32 modes[]={0,1,255,256,257,0x80000000,0xFFFFFF00,0xFFFFFFFF};
int f,s,m,i,result,expected;u32 mask,*p;f32 *input;
if(sizeof(void *)!=4 || sizeof(link)!=40 || (u8 *)&link.firstMatrix-(u8 *)&link!=5 ||
 (u8 *)&link.firstPosition-(u8 *)&link!=8 || (u8 *)&link.second-(u8 *)&link!=20 ||
 (u8 *)&link.secondEpoch-(u8 *)&link!=24 || (u8 *)&link.secondPosition-(u8 *)&link!=28)return 1;
for(f=0;f<256;f++)for(s=0;s<7;s++)for(m=0;m<8;m++) {
 reset(f,s,f);result=func_151B47D8(owner.bytes,&link,(f32 *)(destination+1),(u8)modes[m]);
 expected=s<3?1:0;if(result!=expected)return 2;
 mask=(modes[m]&255)?4:8;
 if(owner.bytes[0x10]!=(s==0?((u32)f&~mask):(u32)(s<3?(f|12):f)))return 3;
 if(calls!=(s==0?1u:0u))return 4;
 if(s==0){input=(modes[m]&255)?link.firstPosition:link.secondPosition;
 p=(modes[m]&255)?palette:alternate;
 if(seenPoint!=input || seenDestination!=(f32 *)(destination+1) || seenMatrix!=(u8 *)(p+f*16))return 5;
 for(i=0;i<3;i++)if(destination[i+1]!=(((u32 *)input)[i]^p[f*16]))return 6;}
 else for(i=1;i<4;i++)if(destination[i]!=0xA5A5A5A5)return 7;
 if(destination[0]!=0xA5A5A5A5 || destination[4]!=0xA5A5A5A5)return 8;
}
reset(12,0,12);
if(func_151B47D8((u8 *)&linkStorage+5,&link,(f32 *)destination,1)!=1 ||
 seenMatrix!=(u8 *)(palette+8*16) || link.firstMatrix!=8)return 9;
reset(12,0,12);
if(func_151B47D8((u8 *)&linkStorage+25,&link,(f32 *)destination,0)!=1 ||
 seenMatrix!=(u8 *)(alternate+4*16) || link.secondMatrix!=4)return 10;
''')
        self.receipt('native32', dict(full_C_cases=256 * 7 * 8, byte_indices_and_flags=256,
            typed_record_size=40, index_aliases=2, helper_is_bounded_word_copy=True))

    def test_06_independent_rebases_complete_wrapper_and_dispatch(self):
        wrapper = list(struct.unpack_from('>12I', self.rom, 0x1E0450))
        dispatch = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        for entry, helper in ((screen.ENTRY, HELPER), (0x15218000, 0x15228000), (0x15307FF0, 0x15318004), (0x15417FFC, 0x15428000)):
            meta, words = screen.compile_candidate(self.root, self.out, 'rebase-%X' % entry,
                symbols={'func_15143134': helper}, entry=entry)
            expected = self.retail.copy()
            expected[58] = 0x0C000000 | ((helper >> 2) & 0x3FFFFFF)
            self.assertEqual(words, expected)
            self.assertEqual(meta['body_words'], 65)
            for mode, state in itertools.product((0, 1, 256), range(7)):
                memory = fixture(state=state)
                model = LinkOracle(words, memory, (ACTOR, LINK, OUTPUT, mode), entry=entry, helper=helper).run()
                public, calls, result = reference(memory, (ACTOR, LINK, OUTPUT, mode))
                self.assertEqual((point.external_memory(model.memory), model.r[2]), (public, result))
                self.assertEqual(model.calls, [(helper, *call[1:]) for call in calls])
        for state, mode, phase in itertools.product(range(7), (0, 1, 256), (0, 8)):
            memory = fixture(state=state, link=ACTOR + 0x150)
            connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 260, 4), self.words))
            model = LinkOracle(wrapper, memory, (ACTOR, OUTPUT, mode), phase, WRAPPER, connected).run()
            public, calls, result = reference(memory, (ACTOR, ACTOR + 0x150, OUTPUT, mode))
            self.assertEqual((point.external_memory(model.memory), model.r[2]), (public, result))
            self.assertEqual(model.calls[1:], calls)
        for state, phase in itertools.product(range(7), (0, 8)):
            memory = fixture(state=state, link=ACTOR + 0x150)
            memory[ACTOR + 0x2C] = memory[ACTOR + 0x2D] = 1
            memory[ACTOR + 0x34] = 255
            memory[ACTOR + 0x10] &= ~1
            put(memory, TABLE + 4, WRAPPER)
            models = []
            for words in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 260, 4), words))
                connected.update(zip(range(WRAPPER, WRAPPER + 48, 4), wrapper))
                models.append(LinkOracle(dispatch, memory, (ACTOR,), phase, DISPATCH, connected).run())
            self.assertEqual((models[0].memory, models[0].events, models[0].calls), (models[1].memory, models[1].events, models[1].calls))
            self.assertEqual(any(c[0] == REMOVE for c in models[0].calls), state >= 3)
            self.assertEqual(sum(c[0] == screen.ENTRY for c in models[0].calls), 2)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345B4)[0], WRAPPER)
        self.receipt('rebases-dispatch', dict(independent_symbols_sets=4, rebase_cases=84,
            complete_wrapper_words=12, wrapper_cases=42, complete_dispatch_words=81, dispatch_cases=14,
            registered_wrapper_pointer='0x8008FAF4'))

    def test_07_connected_complete_original_point_transform(self):
        helper = list(struct.unpack_from('>98I', self.rom, point.screen.ROM))
        count = 0
        for mode, packed, nonzero, alias in itertools.product((0, 1), (0, 1), (False, True), (False, True)):
            matrix_memory, _ = point.fixture(packed, pattern=0x3F800000)
            memory = fixture()
            for address, value in matrix_memory.items():
                if address in range(point.STATUS - 4, point.STATUS + 28) or address == point.FLAG:
                    memory[address] = value
            payload = bytes(matrix_memory[point.MATRIX + i] for i in range(64))
            for bank in (PALETTE, ALTERNATE): memory.update({bank + i: value for i, value in enumerate(payload)})
            source = LINK + (8 if mode else 28)
            for i in range(3): put(memory, source + i * 4, 0x3F800000 if nonzero and i == 0 else 0)
            destination = source if alias else OUTPUT
            models = []
            for words in (self.retail, self.words):
                connected = dict(zip(range(HELPER, HELPER + 392, 4), helper))
                models.append(ConnectedOracle(words, memory, (ACTOR, LINK, destination, mode), entry=screen.ENTRY, connected=connected).run())
            self.assertEqual((models[0].memory, models[0].events, models[0].calls), (models[1].memory, models[1].events, models[1].calls))
            self.assertEqual(models[0].r[2], 1)
            self.assertEqual(point.read(models[0].memory, point.STATUS), 0)
            expected = (3.75, -4.5, 5.75) if nonzero else (3.25, -4.5, 5.75)
            if packed and not nonzero: expected = (3.25, -5.5, 4.75)
            self.assertEqual(tuple(point.floating(point.read(models[0].memory, destination + i * 4)) for i in range(3)), expected)
            count += 1
        self.receipt('connected-helper', dict(cases=count, complete_original_helper_words=98,
            packed_float_nonzero_translation_in_place=True, lower_SDK_and_transform_helpers_are_bounded_models=True))

    def test_08_copied_owner_and_actual_padder(self):
        before = (self.out / 'before-source').read_text()
        objects = [compile_owner(self.root, self.out, body, name) for name, body in
            (('owner-before', before), ('owner-after', screen.install(before)))]
        for _, diagnostics in objects: self.assertEqual(diagnostics, [])
        old, old_functions, old_relocations = parse_object(objects[0][0])
        new, new_functions, new_relocations = parse_object(objects[1][0])
        self.assertEqual(old_functions.keys(), new_functions.keys())
        relative = lambda rels, f: {o - f['value']: r for o, r in rels.items() if f['value'] <= o < f['value'] + f['size']}
        for name, f in new_functions.items():
            if name == screen.FUNCTION:
                self.assertEqual(new[f['value']:f['value'] + f['size']], parse_object(self.out / 'selected.o')[0][:260])
                continue
            prev = old_functions[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(new_relocations, f)),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']], relative(old_relocations, prev)), name)
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for i, (obj, _) in enumerate(objects):
            path = self.out / ('padded-%d.s' % i)
            path.write_text(emit_padded_assembly(obj, self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.out / 'before-guards', filename='generated_1E0560'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        old, of, _ = padded[0]
        new, nf, _ = padded[1]
        f = nf[screen.FUNCTION]
        self.assertEqual((f['value'], f['size']), (of[screen.FUNCTION]['value'], 260))
        self.assertEqual(new[:f['value']], old[:f['value']])
        self.assertEqual(new[f['value'] + 260:], old[f['value'] + 260:])
        self.assertEqual(nf['func_151B48DC']['value'] - f['value'], 260)
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_equal=True,
            zero_diagnostics=True, all_other_padded_owner_bytes_equal=True, target_size=260))

    def test_09_entire_linked_ELF_and_protected_data(self):
        source = (self.root / screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name, path in self.paths.items(): self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), self.baseline[name])
            self.receipt('installation', dict(installed=False, production_baseline_unchanged=True))
            return
        self.assertEqual(source, screen.install((self.out / 'before-source').read_text()))
        for name in ('guards', 'progress'): self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>65I', expected, elf_slot_offset(before, screen.ENTRY, 260), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 260)
        actual = (self.root / self.paths['elf']).read_bytes()
        em, am = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(em[:4], am[:4])
        for section in em[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('installation', dict(installed=True, all_260_target_bytes_retail_exact=True,
            only_target_slot_and_symbol_extent_semantically_changed=True, all_other_ELF_bytes_and_decoded_metadata_equal=True,
            guards_and_conversion_rows_unchanged=True, protected_data=audit))


if __name__ == '__main__':
    unittest.main()
