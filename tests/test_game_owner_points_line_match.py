"""Complete line body, closed scheduling, aliases, native32 and linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_line_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_points_initializer_recovery as initial
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests import test_game_random_curve_record as native

ACTOR, GLOBAL, UPDATE, TABLE, REMOVE = 0x20000, 0x800AA3C4, 0x151B3184, 0x8008FAF8, 0x1516972C
SCALE = 0x3DCCCCCD
PAIRS = ((0, 0), (0x80000000, 0x80000000), (0, 0x80000000), (0x80000000, 0),
    (bits(-30.25), bits(100.125)), (bits(10), bits(-20)), (1, 0x80000001),
    (0x007FFFFF, 0x00800000), (0x7F7FFFFF, 0x7F7FFFFF),
    (0xFF7FFFFF, 0x7F7FFFFF), (bits(2 ** 24), bits(2 ** 24 + 10)),
    (0x7F800000, 0), (0xFF800000, 0x7F800000), (0x7FC12345, 0), (0x7F812345, 0))


def fixture(pair=4, flags=255, actor=ACTOR, global_address=GLOBAL, scale=SCALE):
    memory = {STACK + i: (i * 13 + 7) & 255 for i in range(-0x600, 0x140)}
    memory.update({actor + i: (i * 17 + 0x35) & 255 for i in range(-16, 0x190)})
    initial.put(memory, actor + 0x14, PAIRS[pair][0])
    initial.put(memory, actor + 0x20, PAIRS[pair][1])
    memory[actor + 0x10] = flags
    initial.put(memory, global_address, scale)
    return memory


def reference(memory, actor=ACTOR, global_address=GLOBAL):
    result = memory.copy()
    first = initial.read(result, actor + 0x14)
    last = initial.read(result, actor + 0x20)
    negative = bits(floating(first) - floating(last)) ^ 0x80000000
    for offset, value in ((0x48, first), (0x4C, 0), (0x50, 0)):
        initial.put(result, actor + offset, value)
    step = bits(floating(negative) * floating(initial.read(result, global_address)))
    x = bits(floating(first) + floating(step))
    for index in range(1, 10):
        for offset, value in ((0, x), (4, 0), (8, 0)):
            initial.put(result, actor + 0x48 + index * 24 + offset, value)
        x = bits(floating(x) + floating(step))
    result[actor + 0x10] &= ~2
    return result


class LineOracle(initial.PointOracle):
    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
        else:
            super().execute(word)

    def record_call(self, target):
        assert target in (screen.ENTRY, REMOVE)
        self.calls.append((target, self.r[4]))

    def hook(self, target):
        assert target == REMOVE
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register


class GameOwnerPointsLineMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-line-test'
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.fitted = screen.recipe(cls.raw)[0]
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>44I', cls.rom, screen.ROM))
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
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields, cls.old_rows = reader.fieldnames, list(reader)
        cls.rows = screen.guard_rows(cls.out / 'selected.o')
        assert not any(row['function'] == screen.FUNCTION for row in cls.old_rows)
        cls.guards = cls.out / 'qualified-guards.csv'
        for path, rows in ((cls.guards, cls.old_rows + cls.rows), (cls.out / 'isolated-guards.csv', cls.rows)):
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
        asm = (cls.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        cls.fragment = begin + asm.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        (cls.out / 'slot.s').write_text(cls.fragment)
        (cls.out / 'original.s').write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + cls.fragment)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.out / 'original.o'), str(cls.out / 'original.s')], cwd=cls.root, check=True, capture_output=True)
        (cls.out / 'fitted.s').write_text(emit_padded_assembly(cls.out / 'selected.o', cls.out / 'slot.s',
            word_patches_path=cls.out / 'isolated-guards.csv', filename='generated_1E0560'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.out / 'fitted.o'), str(cls.out / 'fitted.s')], check=True, capture_output=True)
        cls.coverage, cls.cases = [set(), set(), set()], 0
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        cls.fixture = '''typedef unsigned char u8; typedef unsigned int u32;
typedef int s32; typedef float f32;
''' + screen.TYPES + '''
static u8 storage[0x400] __attribute__((aligned(16)));
static u8 expected[0x400] __attribute__((aligned(16)));
static f32 *scale;
#define D_800AA3C4 (*scale)
static u32 word(f32 value){union{f32 f;u32 u;} v;v.f=value;return v.u;}
static f32 number(u32 value){union{f32 f;u32 u;} v;v.u=value;return v.f;}
static int nanWord(u32 value){return (value&0x7FFFFFFF)>0x7F800000;}
static u32 add(u32 a,u32 b){volatile f32 v=number(a)+number(b);return word(v);}
static void reset(int flags,int seed,int alias,u32 a,u32 b,u32 factor){
    int i;OwnerPoints3A7C *owner=(OwnerPoints3A7C *)(storage+16);
    for(i=0;i<0x400;i++)storage[i]=(u8)(i*17+seed*13+0x35);
    *(u32 *)&owner->start.x=a;*(u32 *)&owner->end.x=b;owner->flags=(u8)flags;
    scale=(f32 *)(storage+16+(alias<0?0x300:alias));*(u32 *)scale=factor;
}
static void reference(void){
    int i,k;u32 a,b,d,step,x;volatile f32 difference,product;
    OwnerPoints3A7C *owner=(OwnerPoints3A7C *)(expected+16);
    for(k=0;k<0x400;k++)expected[k]=storage[k];
    a=*(u32 *)&owner->start.x;b=*(u32 *)&owner->end.x;
    difference=number(a)-number(b);d=word(difference)^0x80000000;
    *(u32 *)&owner->points[0].position.x=a;
    *(u32 *)&owner->points[0].position.y=0;*(u32 *)&owner->points[0].position.z=0;
    product=number(d)*number(*(u32 *)(expected+((u8 *)scale-storage)));step=word(product);
    x=add(a,step);
    for(i=1;i<10;i++){
        *(u32 *)&owner->points[i].position.x=x;
        *(u32 *)&owner->points[i].position.y=0;*(u32 *)&owner->points[i].position.z=0;
        x=add(x,step);
    }
    owner->flags&=~2;
}
static int check(int classify){
    int i,j;u32 a,b;
    for(i=0;i<0x400;i++){
        if(classify && i>=16+0x60 && i<16+0x138 && (i-16-0x48)%24<4){
            j=i&~3;a=*(u32 *)(storage+j);b=*(u32 *)(expected+j);
            if(nanWord(a)&&nanWord(b))continue;
        }
        if(storage[i]!=expected[i])return 1;
    }
    return 0;
}
''' + screen.SELECTED + '\n'

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, phase=0, global_address=GLOBAL, bodies=None, entry=screen.ENTRY):
        expected = reference(memory, actor, global_address)
        models = [LineOracle(words, memory, actor, phase, entry).run() for words in bodies or (self.retail, self.raw, self.fitted)]
        for index, model in enumerate(models):
            self.assertEqual(model.memory, expected)
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.calls, [])
            if bodies is None: self.coverage[index].update(model.visits)
        if bodies is None:
            self.assertEqual(models[0].events, models[2].events)
            reads = lambda model: [event for event in model.events if event[0] == 'R']
            self.assertEqual(reads(models[0]), reads(models[1]))
            writes = lambda model: Counter(event for event in model.events if event[0] == 'W')
            self.assertEqual(writes(models[0]), writes(models[1]))
        self.cases += 1
        return models

    def test_01_complete_shape_closed_omissions_and_recipe(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (46, 0, 37, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual(len(self.rows), 46)
        self.assertEqual([int(row['offset'], 16) for row in self.rows if row['omit'] == 'true'], [4, 44])
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x24EE84)[0], SCALE)
        self.receipt('shape', dict(raw=self.meta, normalized_words=44, normalized_differences=0,
            guards=46, omissions=['0x4', '0x2C'], no_padding=True))

    def test_02_flags_geometry_special_float_and_complete_memory(self):
        start = self.cases
        for flags, pair, phase in itertools.product(range(256), range(len(PAIRS)), (0, 8)):
            self.compare(fixture(pair, flags), phase=phase)
        self.assertEqual(self.coverage[0], set(range(screen.ENTRY, screen.ENTRY + 176, 4)))
        self.assertEqual(self.coverage[1], set(range(screen.ENTRY, screen.ENTRY + 184, 4)))
        self.assertEqual(self.coverage[2], self.coverage[0])
        self.receipt('matrix', dict(cases=self.cases - start, executions=(self.cases - start) * 3,
            reached_words=[44, 46, 44], all_flags=True, unused_velocities_and_private_stack_untouched=True,
            raw_ordered_reads_and_write_multisets_equal=True, fitted_full_event_order_equal=True,
            arithmetic_NaNs_use_bounded_model_not_hardware_payload_or_FCSR_acceptance=True))

    def test_03_constant_aliases_and_effective_full_compiled_negatives(self):
        start = self.cases
        for offset, pair, phase in itertools.product((0x14, 0x20, 0x48, 0x4C, 0x50, 0x54, 0x60, 0x64, 0x78), (1, 4, 10), (0, 8)):
            address = GLOBAL - offset
            self.compare(fixture(pair, actor=address), actor=address, phase=phase)
        for scale, pair in itertools.product((0, 0x80000000, bits(1), bits(-1), 1, 0x80000001, 0x7F800000, 0x7FC12345), (1, 4, 10)):
            self.compare(fixture(pair, scale=scale))
        scenarios = {
            'negative-reversed-subtraction': fixture(1),
            'negative-early-scale': fixture(4, actor=GLOBAL - 0x48),
            'negative-nine-points': fixture(),
            'negative-formula': fixture(10),
            'negative-velocity-clear': fixture(),
            'negative-wrong-flag': fixture(),
        }
        for name, body in screen.candidates():
            if name not in scenarios: continue
            _, words = screen.compile_candidate(self.root, self.out, name, body)
            memory = scenarios[name]
            address = GLOBAL - 0x48 if name == 'negative-early-scale' else ACTOR
            good = LineOracle(self.retail, memory, address).run()
            bad = LineOracle(words, memory, address).run()
            self.assertNotEqual(good.memory, bad.memory, name)
        self.receipt('aliases', dict(positive_cases=self.cases - start, effective_full_compiled_negatives=len(scenarios),
            negative_zero_reverse_and_repeated_rounding_controls=True))

    def test_04_normalized_fault_prefixes_and_unused_input_fields(self):
        count = 0
        addresses = [(ACTOR + 0x14, 4), (ACTOR + 0x20, 4), (GLOBAL, 4), (ACTOR + 0x10, 1)]
        addresses += [(ACTOR + 0x48 + index * 24 + axis * 4, 4) for index in range(10) for axis in range(3)]
        for address, size in addresses:
            memory = fixture()
            for i in range(size): del memory[address + i]
            outcomes = []
            for words in (self.retail, self.fitted):
                model = LineOracle(words, memory)
                with self.assertRaises(AssertionError): model.run()
                outcomes.append((model.memory, model.events))
            self.assertEqual(outcomes[0], outcomes[1])
            count += 1
        memory = fixture()
        for offset in (0x18, 0x1C, 0x24, 0x28):
            for i in range(4): del memory[ACTOR + offset + i]
        for index in range(10):
            for i in range(12): del memory[ACTOR + 0x54 + index * 24 + i]
        self.compare(memory)
        self.receipt('faults', dict(paired_fitted_fault_prefixes=count, unused_YZ_inputs_and_velocity_fields_unread=True,
            raw_scheduling_fault_prefix_not_equal_or_claimed=True, no_portable_C_or_hardware_fault_claim=True))

    def test_05_actual_native32_complete_C_and_typed_record(self):
        self.run_host('''
int f,seed,alias,a,b;OwnerPoints3A7C *owner=(OwnerPoints3A7C *)(storage+16);
static u32 patterns[]={0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,
0x3F800000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345};
static int offsets[]={0x14,0x20,0x48,0x4C,0x50,0x54,0x60,0x64,0x78};
if(sizeof(void *)!=4 || sizeof(*owner)!=0x138 || sizeof(owner->points[0])!=24 ||
 (u8 *)&owner->start-(u8 *)owner!=0x14 || (u8 *)&owner->end-(u8 *)owner!=0x20 ||
 (u8 *)&owner->points-(u8 *)owner!=0x48)return 1;
for(f=0;f<256;f++)for(seed=0;seed<32;seed++){
 reset(f,seed,-1,word((f32)seed*.25f-30.25f),word(100.125f-(f32)seed*.5f),0x3DCCCCCD);
 reference();if(func_151B48DC(owner)!=1 || check(0))return 2;
}
for(alias=0;alias<9;alias++)for(seed=0;seed<32;seed++){
 reset(255,seed,offsets[alias],word((f32)seed*.25f-30.25f),word(100.125f-(f32)seed*.5f),0x3DCCCCCD);
 reference();if(func_151B48DC(owner)!=1 || check(0))return 3;
}
for(a=0;a<14;a++)for(b=0;b<14;b++){
 reset(255,0,-1,patterns[a],patterns[b],0x3DCCCCCD);reference();
 if(func_151B48DC(owner)!=1 || check(1))return 4;
}
''')
        self.receipt('native32', dict(finite_complete_memory_cases=8192, aliases=288,
            special_float_pairs=196, record_bytes=312, point_stride=24,
            first_X_raw_payload_and_all_zero_YZ_exact=True, arithmetic_NaNs_classified_not_payload_claimed=True))

    def test_06_original_and_guarded_independent_relocations_dispatch(self):
        cases = 0
        for index, (entry, address) in enumerate(((screen.ENTRY, GLOBAL), (0x15218000, 0x80128004),
                (0x15307FF0, 0x80137FFC), (0x15417FFC, 0x80148000))):
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for label, obj, length in (('original', self.out / 'original.o', 44), ('raw', self.out / 'selected.o', 46), ('fitted', self.out / 'fitted.o', 44)):
                elf = self.out / ('rebase-%d-%s.elf' % (index, label))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    '--defsym=D_800AA3C4=0x%X' % address, '-o', str(elf), str(obj)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[2])
            for pair, phase in itertools.product((1, 4, 10, 13), (0, 8)):
                self.compare(fixture(pair, global_address=address), phase=phase, global_address=address, bodies=bodies, entry=entry)
                cases += 1
        dispatch = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        for flags, phase in itertools.product((0, 2, 4, 8, 12, 0xA4), (0, 8)):
            memory = fixture(flags=flags)
            memory[ACTOR + 0x2C] = memory[ACTOR + 0x2D] = 255
            memory[ACTOR + 0x34] = 4
            initial.put(memory, TABLE + 16, screen.ENTRY)
            models = []
            for words in (self.retail, self.raw, self.fitted):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(words) * 4, 4), words))
                models.append(LineOracle(dispatch, memory, phase=phase, entry=UPDATE, connected=connected).run())
            self.assertEqual(models[0].memory, models[1].memory)
            self.assertEqual((models[0].memory, models[0].events, models[0].calls), (models[2].memory, models[2].events, models[2].calls))
            called = not flags & 12
            self.assertEqual(models[0].calls, [(screen.ENTRY, ACTOR)] if called else [])
            self.assertEqual(models[0].memory[ACTOR + 0x10], flags & ~2 if called else flags | 2)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345C8)[0], screen.ENTRY)
        self.receipt('rebases-dispatch', dict(independent_links=12, symbol_sets=4, rebase_cases=cases,
            complete_original_dispatch_words=81, dispatch_cases=12, registered_pointer='0x8008FB08'))

    def test_07_copied_owner_actual_padder_and_unchanged_neighbors(self):
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
                self.assertEqual(new[f['value']:f['value'] + f['size']], parse_object(self.out / 'selected.o')[0][:184])
                continue
            prev = old_functions[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(new_relocations, f)),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']], relative(old_relocations, prev)), name)
        self.assertEqual(normalized_pools(objects[0][0]), normalized_pools(objects[1][0]))
        padded = []
        for i, (obj, _) in enumerate(objects):
            path = self.out / ('padded-%d.s' % i)
            path.write_text(emit_padded_assembly(obj, self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.out / 'before-guards' if i == 0 else self.guards, filename='generated_1E0560'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        old, of, _ = padded[0]
        new, nf, _ = padded[1]
        f = nf[screen.FUNCTION]
        self.assertEqual((f['value'], f['size']), (of[screen.FUNCTION]['value'], 176))
        self.assertEqual(new[:f['value']], old[:f['value']])
        self.assertEqual(new[f['value'] + 176:], old[f['value'] + 176:])
        self.assertEqual(nf['func_151B498C']['value'] - f['value'], 176)
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_equal=True,
            zero_diagnostics=True, all_other_padded_owner_bytes_equal=True, target_size=176))

    def test_08_actual_padder_stale_word_and_relocation_controls(self):
        data = (self.out / 'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(data)
        headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
        names_section = headers[header[13]]
        names = data[names_section[4]:names_section[4] + names_section[5]]
        text_sections = [s for s in headers if names[s[0]:].split(b'\0', 1)[0] == b'.text']
        self.assertEqual(len(text_sections), 1)
        text_offset = text_sections[0][4]
        raw_text = parse_object(self.out / 'selected.o')[0]
        for i in range(46):
            changed = bytearray(data)
            word = struct.unpack_from('>I', raw_text, i * 4)[0]
            struct.pack_into('>I', changed, text_offset + i * 4, word ^ 0x10000)
            obj = self.out / 'stale.o'
            obj.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'stale word patch.*\\+0x%X:' % (i * 4)):
                emit_padded_assembly(obj, self.out / 'slot.s', word_patches_path=self.out / 'isolated-guards.csv', filename='generated_1E0560')
        rows = [dict(row) for row in self.rows]
        rows[7]['expected_relocations'] = '-'
        path = self.out / 'stale-relocations.csv'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'stale relocations'):
            emit_padded_assembly(self.out / 'selected.o', self.out / 'slot.s', word_patches_path=path, filename='generated_1E0560')
        self.receipt('stale', dict(actual_padder_stale_word_rejections=46, relocated_HI16_control_effective=True))

    def test_09_entire_linked_ELF_protected_data_and_guard_history(self):
        source = (self.root / screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name, path in self.paths.items(): self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), self.baseline[name])
            self.receipt('installation', dict(installed=False, production_baseline_unchanged=True))
            return
        self.assertEqual(source, screen.install((self.out / 'before-source').read_text()))
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)), self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith((self.out / 'before-guards').read_bytes()))
        self.assertEqual((self.root / self.paths['progress']).read_bytes(), (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>44I', expected, elf_slot_offset(before, screen.ENTRY, 176), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 176)
        actual = (self.root / self.paths['elf']).read_bytes()
        em, am = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(em[:4], am[:4])
        for section in em[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        start, data = sections(self.root / self.paths['elf'])['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, TABLE + 16 - start)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, GLOBAL - start)[0], SCALE)
        self.receipt('installation', dict(installed=True, all_176_target_bytes_retail_exact=True,
            only_target_slot_and_symbol_extent_semantically_changed=True, decoded_ELF_metadata_equal=True,
            old_guard_prefix_and_conversion_rows_unchanged=True, protected_data=audit))


if __name__ == '__main__':
    unittest.main()
