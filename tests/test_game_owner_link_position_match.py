"""Raw C, return-copy guards, aliases and complete linked installation audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_link_position_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle, put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests import test_game_random_curve_record as native
from tools.tests.test_game_owner_actor_update_match import ActorOracle
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.game_owner_pool import normalized_pools

ACTOR, SOURCE, ALTERNATE, OUTPUT = 0x20000, 0x21000, 0x22000, 0x23000
GLOBAL, UPDATE, REMOVE, TABLE = 0x800AA3AC, 0x151B3184, 0x1516972C, 0x8008FAF0
PATTERNS = (0, 0x80000000, 1, 0x80000001, 0x3F800000, 0x7F7FFFFF,
    0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345, 0xFFFFFFFF)
MODES = (0, 1, 255, 256, 257, 0x80000000, 0xFFFFFF00, 0xFFFFFFFF)


def fixture(flags=0, state=0, pattern=0, global_address=GLOBAL):
    memory = {STACK + i: (i * 13 + 0xA5) & 255 for i in range(-0x600, 0x100)}
    for base, size in ((ACTOR, 0x180), (SOURCE, 0x80), (ALTERNATE, 0x80), (OUTPUT, 0x20),
            (global_address - 16, 32), (TABLE, 16)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(size)})
    put(memory, ACTOR + 0x150, SOURCE)
    put(memory, ACTOR + 0x154, 0x87, 1)
    put(memory, ACTOR + 0x10, flags, 1)
    for base in (SOURCE, ALTERNATE):
        put(memory, base, int(state != 1))
        put(memory, base + 0x3B, 0x86 if state == 2 else 0x87, 1)
        for i in range(3):
            put(memory, base + 0x14 + i * 4, PATTERNS[(pattern + i + (3 if base == ALTERNATE else 0)) % len(PATTERNS)])
    put(memory, global_address, 0x453B8000)
    return memory


class LinkOracle(ActorOracle):
    def __init__(self, words, memory, **kwargs):
        TriangleOracle.__init__(self, words, memory, **kwargs)

    def record_call(self, target):
        assert target in (screen.ENTRY, REMOVE)
        self.calls.append((target, *self.r[4:7]) if target == screen.ENTRY else (target, self.r[4]))

    def hook(self, target):
        assert target == REMOVE
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register


class GameOwnerLinkPositionMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-link-position-test'
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.fitted = screen.recipe(cls.raw)[0]
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>45I', cls.rom, screen.ROM))
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
        assert not any(r['function'] == screen.FUNCTION for r in cls.old_rows)
        cls.guards = cls.out / 'qualified-guards.csv'
        with cls.guards.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(cls.old_rows + cls.rows)
        asm = (cls.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        cls.fragment = begin + asm.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        (cls.out / 'original.s').write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + cls.fragment)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.out / 'original.o'),
            str(cls.out / 'original.s')], cwd=cls.root, check=True, capture_output=True)
        with (cls.out / 'isolated-guards.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(cls.rows)
        cls.folded = cls.out / 'folded.o'
        (cls.out / 'slot.s').write_text(cls.fragment)
        (cls.out / 'folded.s').write_text(emit_padded_assembly(cls.out / 'selected.o', cls.out / 'slot.s',
            word_patches_path=cls.out / 'isolated-guards.csv', filename='generated_1E0560'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(cls.folded),
            str(cls.out / 'folded.s')], check=True, capture_output=True)
        cls.coverage, cls.cases = set(), 0
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        cls.fixture = '''typedef unsigned char u8; typedef unsigned int u32;
typedef int s32; typedef float f32;
''' + screen.TYPES + '''
static union { u32 align; u8 bytes[0x180]; } actor, source, alternate;
static union { u32 bits[8]; f32 numbers[8]; } output, constant;
#define D_800AA3AC constant.numbers[2]
static void reset(int flags,int state,u32 x) {
    int i;
    for(i=0;i<0x180;i++)actor.bytes[i]=source.bytes[i]=alternate.bytes[i]=0xA5;
    for(i=0;i<8;i++)output.bits[i]=0xA5A5A5A5;
    *(u8 **)(actor.bytes+0x150)=source.bytes;
    actor.bytes[0x154]=0x87;actor.bytes[0x10]=(u8)flags;
    *(u32 *)source.bytes=(u32)(state!=1);source.bytes[0x3B]=(u8)(state==2?0x86:0x87);
    *(u32 *)(source.bytes+0x14)=x;*(u32 *)(source.bytes+0x18)=0x80000000;
    *(u32 *)(source.bytes+0x1C)=0x7FC12345;
    *(u32 *)(alternate.bytes+0x18)=0x12345678;*(u32 *)(alternate.bytes+0x1C)=0x89ABCDEF;
    constant.bits[2]=0x453B8000;
}
''' + screen.SELECTED + '\n'

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, mode=1, output=OUTPUT, phase=0, bodies=None, entry=screen.ENTRY):
        models = [LinkOracle(words, memory, phase=phase, entry=entry,
            arguments=(ACTOR, output, mode)).run() for words in bodies or (self.retail, self.raw, self.fitted)]
        for model in models[1:]:
            self.assertEqual((model.memory, model.events, model.r[2]),
                (models[0].memory, models[0].events, models[0].r[2]))
        self.assertEqual(tuple(models[0].memory[STACK + phase + 8 + i] for i in range(4)),
            tuple(mode.to_bytes(4, 'big')))
        self.coverage.update(models[0].visits)
        self.cases += 1
        return models

    def test_01_complete_raw_shape_and_closed_recipe(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')), (44, 0, 16, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual(len(self.rows), 44)
        self.assertEqual(sum(bool(r['insert_after']) for r in self.rows), 1)
        self.assertEqual(self.rows[31]['insert_after'], '0x00601025')
        for i in range(44):
            changed = self.raw.copy()
            changed[i] ^= 0x10000
            with self.assertRaisesRegex(ValueError, 'stale complete'):
                screen.recipe(changed)
        self.receipt('shape', dict(raw=self.meta, normalized_words=45, normalized_differences=0,
            guard_rows=44, inserted_shared_return_copies=1, every_stale_word_rejected=True))

    def test_02_complete_guest_width_flags_and_raw_float_bits(self):
        start = self.cases
        for mode, flags, state, pattern, phase in itertools.product(MODES, (0, 4, 8, 12, 0xA5, 255),
                range(3), range(len(PATTERNS)), (0, 8)):
            model = self.compare(fixture(flags, state, pattern), mode, phase=phase)[0]
            expected_result = int(not (mode & 255) or state == 0)
            self.assertEqual(model.r[2], expected_result)
            self.assertEqual(model.memory[ACTOR + 0x10], (flags & ~4) if mode & 255 and state == 0 else
                (flags | 12) if mode & 255 else (flags & ~8))
        self.assertEqual(self.coverage, set(range(screen.ENTRY, screen.ENTRY + 180, 4)) - {screen.ENTRY + 0x6C})
        self.receipt('matrix', dict(cases=self.cases - start, executions=(self.cases - start) * 3,
            full_word_argument_home=True, preserved_GP_FP_and_SP=True, public_access_order_equal=True,
            reached_retail_words=44, unreachable_retail_load_offset='0x6C', raw_float_bits=True))

    def test_03_overlapping_outputs_and_effective_negative_controls(self):
        count = 0
        for output, mode in itertools.product((ACTOR + 0x10, ACTOR + 0x14, ACTOR + 0x150,
                SOURCE + 0x14, SOURCE + 0x18, SOURCE + 0x1C, GLOBAL - 8, GLOBAL), (0, 1)):
            memory = fixture(255)
            if output == ACTOR + 0x150:
                put(memory, SOURCE + 0x14, ALTERNATE)
            self.compare(memory, mode, output)
            count += 1
        memory = fixture()
        put(memory, SOURCE + 0x14, ALTERNATE)
        cached = self.raw.copy()
        cached[17] = 0x00C04825
        cached[20] = 0x00C05025
        good = self.compare(memory, output=ACTOR + 0x150)[0]
        bad = LinkOracle(cached, memory, arguments=(ACTOR, ACTOR + 0x150, 1)).run()
        self.assertNotEqual(good.memory, bad.memory)
        late = self.raw.copy()
        late[35], late[36] = late[36], late[35]
        good = self.compare(fixture(), mode=0, output=GLOBAL - 8)[0]
        bad = LinkOracle(late, fixture(), arguments=(ACTOR, GLOBAL - 8, 0)).run()
        self.assertNotEqual(good.memory, bad.memory)
        self.receipt('aliases', dict(cases=count + 2, effective_cached_link_and_late_constant_controls=True))

    def test_04_fault_prefixes_and_disabled_null_link(self):
        count = 0
        for mode, address, length in ((1, ACTOR + 0x150, 4), (1, SOURCE, 4), (1, ACTOR + 0x154, 1),
                (1, SOURCE + 0x3B, 1), (1, SOURCE + 0x14, 4), (1, SOURCE + 0x18, 4),
                (1, SOURCE + 0x1C, 4), (1, OUTPUT, 4), (1, OUTPUT + 4, 4), (1, OUTPUT + 8, 4),
                (1, ACTOR + 0x10, 1), (0, GLOBAL, 4), (0, OUTPUT, 4), (0, OUTPUT + 8, 4)):
            memory = fixture()
            for i in range(length):
                del memory[address + i]
            outcomes = []
            for words in (self.retail, self.raw, self.fitted):
                model = LinkOracle(words, memory, arguments=(ACTOR, OUTPUT, mode))
                with self.assertRaises(AssertionError):
                    model.run()
                outcomes.append((model.memory, model.events))
            self.assertEqual(outcomes[0], outcomes[1])
            self.assertEqual(outcomes[0], outcomes[2])
            count += 1
        memory = fixture()
        put(memory, ACTOR + 0x150, 0)
        self.compare(memory, mode=0)
        for words in (self.retail, self.raw, self.fitted):
            with self.assertRaises(AssertionError):
                LinkOracle(words, memory, arguments=(ACTOR, OUTPUT, 1)).run()
        self.receipt('faults', dict(paired_fault_prefixes=count, null_enabled_link_faults=True,
            disabled_null_link_is_not_read=True, emitted_guest_order_only_not_portable_C_fault_semantics=True))

    def test_05_actual_native32_complete_C_and_aliases(self):
        self.run_host('''
static u32 patterns[]={0,0x80000000,1,0x80000001,0x3F800000,0x7F7FFFFF,
0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,0xFFFFFFFF};
static u32 modes[]={0,1,255,256,257,0x80000000,0xFFFFFF00,0xFFFFFFFF};
int f,s,p,m,result;
for(f=0;f<256;f++)for(s=0;s<3;s++)for(p=0;p<12;p++)for(m=0;m<8;m++){
 reset(f,s,patterns[p]);result=func_151B3F28(actor.bytes,output.numbers+1,(u8)modes[m]);
 if(result!=((modes[m]&255)?s==0:1))return 1;
 if(actor.bytes[0x10]!=((modes[m]&255)?s==0?(f&~4):(f|12):(f&~8)))return 2;
 if(output.bits[0]!=0xA5A5A5A5||output.bits[4]!=0xA5A5A5A5)return 3;
 if(modes[m]&255){
  if(s==0){if(output.bits[1]!=patterns[p]||output.bits[2]!=0x80000000||output.bits[3]!=0x7FC12345)return 4;}
  else if(output.bits[1]!=0xA5A5A5A5||output.bits[2]!=0xA5A5A5A5||output.bits[3]!=0xA5A5A5A5)return 5;
 }else if(output.bits[1]!=0||output.bits[2]!=0x453B8000||output.bits[3]!=0)return 6;
}
reset(0,0,(u32)alternate.bytes);
if(func_151B3F28(actor.bytes,(f32 *)(actor.bytes+0x150),1)!=1)return 7;
if(*(u32 *)(actor.bytes+0x154)!=0x12345678||*(u32 *)(actor.bytes+0x158)!=0x89ABCDEF)return 8;
reset(0,0,0x3F800000);
if(func_151B3F28(actor.bytes,(f32 *)(source.bytes+0x18),1)!=1)return 9;
if(*(u32 *)(source.bytes+0x18)!=0x3F800000||*(u32 *)(source.bytes+0x1C)!=0x3F800000
 ||*(u32 *)(source.bytes+0x20)!=0x3F800000)return 10;
reset(0,0,0);*(u8 **)(actor.bytes+0x150)=(u8 *)0;
if(func_151B3F28(actor.bytes,constant.numbers,0)!=1)return 11;
if(constant.bits[0]!=0||constant.bits[1]!=0x453B8000||constant.bits[2]!=0)return 12;
''')
        self.receipt('native32', dict(matrix_cases=256 * 3 * 12 * 8, alias_cases=3,
            actual_complete_C=True, raw_NaN_signed_zero_and_infinity_bits=True))

    def test_06_independent_rebases_and_complete_original_dispatch(self):
        for i, address in enumerate((GLOBAL, 0x80107FFC, 0x80108000, 0x8011FFFC)):
            entry = (screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)[i]
            script = self.out / ('rebase-%d.ld' % i)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, obj, length in (('original', self.out / 'original.o', 45),
                    ('raw', self.out / 'selected.o', 44), ('folded', self.folded, 45)):
                elf = self.out / ('rebase-%d-%s.elf' % (i, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    '--defsym=D_800AA3AC=0x%X' % address, '-o', str(elf), str(obj)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % length, sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[2])
            for mode, state in itertools.product((0, 1, 256), range(3)):
                self.compare(fixture(state=state, global_address=address), mode, bodies=bodies, entry=entry)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2345B0)[0], screen.ENTRY)
        update = list(struct.unpack_from('>81I', self.rom, 0x1E0634))
        for state, flags, phase in itertools.product(range(3), (0, 4, 8, 12), (0, 8)):
            memory = fixture(flags, state)
            put(memory, TABLE, screen.ENTRY)
            memory[ACTOR + 0x2C] = memory[ACTOR + 0x2D] = 0
            memory[ACTOR + 0x34] = 255
            models = []
            for words in (self.retail, self.raw, self.fitted):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(words) * 4, 4), words))
                models.append(LinkOracle(update, memory, phase=phase, entry=UPDATE,
                    arguments=(ACTOR,), connected=connected).run())
            for model in models[1:]:
                self.assertEqual((model.memory, model.events, model.calls),
                    (models[0].memory, models[0].events, models[0].calls))
            self.assertEqual([call for call in models[0].calls if call[0] == screen.ENTRY],
                [(screen.ENTRY, ACTOR, ACTOR + 0x14, 1), (screen.ENTRY, ACTOR, ACTOR + 0x20, 0)])
            self.assertEqual(any(call[0] == REMOVE for call in models[0].calls), state != 0)
        self.receipt('rebases-dispatch', dict(independent_links=12, symbol_sets=4, cases=36,
            full_original_dispatch_words=81, dispatch_cases=24, registered_pointer='0x8008FAF0',
            success_and_failure_removal_contract=True))

    def test_07_copied_owner_neighbors_and_actual_padder(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.TYPES + screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
        objects = []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            self.assertEqual(diagnostics, [])
            objects.append(obj)
        old, old_functions, old_relocations = parse_object(objects[0])
        new, new_functions, new_relocations = parse_object(objects[1])
        self.assertEqual(old_functions.keys(), new_functions.keys())
        relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
            if f['value'] <= o < f['value'] + f['size']}
        for name, f in new_functions.items():
            if name == screen.FUNCTION:
                self.assertEqual(new[f['value']:f['value'] + f['size']], parse_object(self.out / 'selected.o')[0][:176])
                continue
            prev = old_functions[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(new_relocations, f)),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']], relative(old_relocations, prev)), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        padded = []
        for i, obj in enumerate(objects):
            guards = self.out / 'before-guards' if i == 0 else self.guards
            path = self.out / ('padded-%d.s' % i)
            path.write_text(emit_padded_assembly(obj, self.root / 'conker/asm/1E0560.s',
                word_patches_path=guards, filename='generated_1E0560'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
                check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        old, of, _ = padded[0]
        new, nf, _ = padded[1]
        f = nf[screen.FUNCTION]
        self.assertEqual((f['value'], f['size']), (of[screen.FUNCTION]['value'], 180))
        self.assertEqual(new[:f['value']], old[:f['value']])
        self.assertEqual(new[f['value'] + 180:], old[f['value'] + 180:])
        # The target relocations are unresolved here; independent links are the byte-exact gate.
        self.assertEqual(nf['func_151B3FDC']['value'] - f['value'], 180)
        self.receipt('owner', dict(neighbors=len(nf) - 1, pools_and_relative_relocations_equal=True,
            zero_diagnostics=True, all_other_padded_owner_bytes_equal=True, target_size=180))

    def test_08_entire_ELF_and_protected_data_installation(self):
        source = (self.root / screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name, path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), self.baseline[name])
            self.receipt('installation', dict(installed=False, production_baseline_unchanged=True))
            return
        before_source = (self.out / 'before-source').read_text()
        self.assertEqual(source, before_source.replace('/* Non-matching placeholders',
            screen.TYPES + screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED))
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)), self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith((self.out / 'before-guards').read_bytes()))
        self.assertEqual((self.root / self.paths['progress']).read_bytes(), (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>45I', expected, elf_slot_offset(before, screen.ENTRY, 180), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 180)
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
        self.assertEqual(struct.unpack_from('>I', data, TABLE - start)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, GLOBAL - start)[0], 0x453B8000)
        self.receipt('installation', dict(installed=True, all_180_target_bytes_retail_exact=True,
            only_target_slot_and_symbol_extent_semantically_changed=True, decoded_ELF_metadata_equal=True,
            old_guard_history_and_conversion_rows_unchanged=True, protected_data=audit))

    def test_09_actual_padder_rejects_every_stale_word_and_relocation(self):
        data = (self.out / 'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(data)
        headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
        names_section = headers[header[13]]
        names = data[names_section[4]:names_section[4] + names_section[5]]
        text_sections = [s for s in headers if names[s[0]:].split(b'\0', 1)[0] == b'.text']
        self.assertEqual(len(text_sections), 1)
        text_offset = text_sections[0][4]
        raw_text = parse_object(self.out / 'selected.o')[0]
        for i in range(44):
            changed = bytearray(data)
            word = struct.unpack_from('>I', raw_text, i * 4)[0]
            struct.pack_into('>I', changed, text_offset + i * 4, word ^ 1)
            obj = self.out / 'stale.o'
            obj.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'stale word patch.*\\+0x%X:' % (i * 4)):
                emit_padded_assembly(obj, self.out / 'slot.s',
                    word_patches_path=self.out / 'isolated-guards.csv', filename='generated_1E0560')
        rows = [dict(r) for r in self.rows]
        rows[33]['expected_relocations'] = '-'
        path = self.out / 'stale-relocations.csv'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'stale relocations'):
            emit_padded_assembly(self.out / 'selected.o', self.out / 'slot.s',
                word_patches_path=path, filename='generated_1E0560')
        self.receipt('stale', dict(actual_padder_stale_words_rejected=44, relocation_control_effective=True))


if __name__ == '__main__':
    unittest.main()
