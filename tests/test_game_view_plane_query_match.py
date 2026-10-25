"""View/plane query: masked bounds, mixed O32 arguments, and retained neighbors."""
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest
from unittest.mock import patch
from tools.experiments import game_view_plane_query_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
SYMBOLS = dict(D_800D3094=0x800D3094, D_800DBFF0=0x800DBFF0,
    D_800D3098=0x800D3098, func_150A2E4C=0x150A2E4C)
VIEWS, RECORDS, PACKET = 0x30000, 0x50000, 0x70000
PARENT, TABLE = 0x150A04D8, 0x8009F568
POINTS = ((0, 0x80000000, 0x3F800000), (0x3FA00000, 0xC1900000, 0x42C80000),
    (0x7F800000, 0xFF800000, 0x7FC12345), (0x7FA12345, 1, 0xFFC12345))
PARENT_TABLE = (0x150A051C, 0x150A06E4, 0x150A05C0, 0x150A05FC, 0x150A063C,
    0x150A0674, 0x150A0674, 0x150A070C, 0x150A0784, 0x150A07AC, 0x150A07D0,
    0x150A08BC, 0x150A097C)


def fixture(view=0, selector=1, count=2, flag=3, point=POINTS[0], symbols=SYMBOLS,
            views=VIEWS, records=RECORDS):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-512, 256)}
    for name, value in (('D_800D3094', count), ('D_800DBFF0', views), ('D_800D3098', records)):
        put(memory, symbols[name], value & 0xFFFFFFFF)
    address = (views + view * 0x9A0) & 0xFFFFFFFF
    for i, value in enumerate(point):
        put(memory, (address + 0x2F8 + 4 * i) & 0xFFFFFFFF, value)
    record = (records + (selector & 0xFFF) * 0x34) & 0xFFFFFFFF
    for i in range(0x34):
        memory[(record + i) & 0xFFFFFFFF] = (i * 29 + 0x5A) & 255
    memory[(record + 0x15) & 0xFFFFFFFF] = flag
    return memory


def expected(initial, view, selector, symbols=SYMBOLS):
    selector &= 0xFFF
    if read(initial, symbols['D_800D3094']) < selector:
        return 1, []
    record = (read(initial, symbols['D_800D3098']) + selector * 0x34) & 0xFFFFFFFF
    if initial[(record + 0x15) & 0xFFFFFFFF] & 3 != 3:
        return 0, []
    address = (read(initial, symbols['D_800DBFF0']) + view * 0x9A0) & 0xFFFFFFFF
    args = (record, *(read(initial, (address + 0x2F8 + 4 * i) & 0xFFFFFFFF) for i in range(3)))
    return 0x87654321, [(symbols['func_150A2E4C'], args)]


class QueryOracle(TimingOracle):
    def __init__(self, words, memory, view=0, selector=1, phase=0, symbols=SYMBOLS,
                 entry=source.ENTRY, connected=None, fault=None, arguments=None):
        super().__init__(words, memory, phase=phase, entry=entry,
            arguments=arguments or (view & 0xFFFFFFFF, selector & 0xFFFFFFFF), connected=connected)
        self.symbols = symbols
        self.root_fault = fault

    def record_call(self, target):
        if target == source.ENTRY:
            count = 2
        else:
            assert target == self.symbols['func_150A2E4C'], hex(target)
            count = 4
        args = self.arguments(count)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == self.symbols['func_150A2E4C']
        for i in range(4):
            self.put(self.r[29] + 4 * i, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo, self.r[2] = 0x87654321, 0x12345678, 0x87654321


def controls():
    body = source.SELECTED
    return dict(no_mask=body.replace('selector &= 0xFFF;', 'selector &= 0xFFFF;'),
        reject_equality=body.replace('< (u32)selector', '<= (u32)selector'),
        signed_count=body.replace('(u32)D_800D3094 < (u32)selector', 'D_800D3094 < selector'),
        wrong_flag=body.replace('& 3) == 3', '& 3) == 2'),
        exact_flag=body.replace('(D_800D3098[selector].flags & 3) == 3', 'D_800D3098[selector].flags == 3'),
        wrong_view=body.replace('[viewIndex]', '[viewIndex ^ 1]'),
        wrong_axis=body.replace('view->unk300', 'view->unk2FC'),
        boolean_return=body.replace('return func_150A2E4C(', 'return !!func_150A2E4C('))


def native_harness(body):
    return '#include <ultra64.h>\n' + source.DECLARATIONS + '''
static struct108 views[4];
static GeneratedCDE80Record records[4096];
struct108 *D_800DBFF0=views;
GeneratedCDE80Record *D_800D3098=records;
s32 D_800D3094;
typedef char ABI[(sizeof(void*)==4 && sizeof(struct108)==0x9A0 &&
 __builtin_offsetof(struct108,unk2F8)==0x2F8 && __builtin_offsetof(struct108,unk300)==0x300 &&
 sizeof(GeneratedCDE80Record)==0x34 && __builtin_offsetof(GeneratedCDE80Record,flags)==0x15 &&
 __builtin_offsetof(GeneratedCDE80Record,field17)==0x17 &&
 __builtin_offsetof(GeneratedCDE80Record,coefficient0)==0x24 &&
 __builtin_offsetof(GeneratedCDE80Record,coefficient2)==0x30)?1:-1];
static u32 calls,error,expectedCalls,index,view;
static u32 word(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
__attribute__((noinline,noclone)) s32 func_150A2E4C(GeneratedCDE80Record *record,f32 x,f32 y,f32 z){
 if(record!=records+index || word(x)!=word(views[view].unk2F8) ||
  word(y)!=word(views[view].unk2FC) || word(z)!=word(views[view].unk300))error=1;
 calls++;return (s32)0x87654321u;
}
''' + body + '''
static int one(u32 selected,u32 count,u32 flags,u32 which){
 u32 result,wanted;
 index=selected&0xFFFu;view=which;D_800D3094=(s32)count;
 records[index].flags=(u8)flags;calls=error=0;
 expectedCalls=count>=index && (flags&3)==3;
 wanted=count<index?1u:expectedCalls?0x87654321u:0u;
 result=(u32)func_150A2FA4((s32)view,(s32)selected);
 if(error || result!=wanted || calls!=expectedCalls)return 23;
 return 0;
}
int run(void){
 u32 i,flag,which;
 for(i=0;i<4;i++){views[i].unk2F8=(f32)(i*7);views[i].unk2FC=(f32)(i*7+1);views[i].unk300=(f32)(i*7+2);}
 for(i=0;i<4096;i++)for(which=0;which<4;which++){
  if(one(i,i,3,which)||one(i,i?i-1:0,3,which)||one(i,i+1,255,which))return 23;
  if(one(i,0xFFFFFFFFu,3,which)||one(i,0x80000000u,3,which))return 23;
 }
 for(flag=0;flag<256;flag++)for(which=0;which<4;which++){
  if(one(1,1,flag,which)||one(0,0,flag,which)||one(0x1001,10,flag,which))return 23;
 }
 return 0;
}
''' + START


class ViewPlaneQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.values = source.snapshot(cls.output)
        cls.installed = (ROOT / source.SOURCE).read_bytes() != cls.values[source.SOURCE]
        source.audit_inputs(ROOT, cls.output) if cls.installed else source.freeze(ROOT, cls.output)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>45I', cls.rom, source.ROM))
        linked, functions = source.link_owner(ROOT, cls.output, cls.output / 'after-owner.o', source.OWNER)
        cls.words = list(struct.unpack_from('>45I', linked, functions[source.FUNCTION]['value']))
        cls.receipt = {}

    def test_01_direct_owner_make_and_word_binding_guards(self):
        raw, bindings = source.payload(self.output / 'after-owner.o')
        source.checked_payload(raw, bindings)
        self.assertEqual(self.words, self.truth)
        q = json.loads((self.output / 'qualification.json').read_text())
        self.assertEqual((q['words'], q['frame'], q['new_guards'], q['relocations']), (45, 24, 0, 7))
        self.assertEqual(json.loads((self.output / 'make-shadow.json').read_text())['actual_Make_commands'], 5)
        for i in range(45):
            wrong = bytearray(raw)
            wrong[4 * i] ^= 1
            with self.assertRaises(ValueError):
                source.checked_payload(bytes(wrong), bindings)
        for at in bindings:
            wrong = dict(bindings)
            wrong[at] = [('R_MIPS_26', 'unknown')]
            with self.assertRaises(ValueError):
                source.checked_payload(raw, wrong)
        self.receipt.update(words=45, frame=24, bindings=7, new_guards=0,
            preserved_neighbors=q['preserved_neighbors'], GLOBAL_ASM_neighbors_preserved=2,
            original_helper_guards_unchanged=True, raw_word_controls=45, binding_controls=7)

    def test_02_guest_boundaries_flags_full_words_and_mixed_arguments(self):
        visits, count = set(), 0
        cases = [(v, s, c, f, p) for v, s, c, f, p in itertools.product(
            (0, 3, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000),
            (0, 1, 0xFFF, 0x1001, 0xFFFFFFFF),
            (0, 1, 0xFFE, 0xFFF, 0x80000000, 0xFFFFFFFF),
            (0, 2, 3, 128, 255), POINTS[:2])]
        cases += [(1, 1, 1, flag, POINTS[flag % 4]) for flag in range(256)]
        for view, selector, limit, flag, point in cases:
            memory = fixture(view, selector, limit, flag, point)
            result, calls = expected(memory, view, selector)
            models = [QueryOracle(words, memory, view, selector, phase=(count & 1) * 8).run()
                for words in (self.truth, self.words)]
            for model in models:
                self.assertEqual((model.r[2], model.calls), (result, calls))
                reads = [event[1] for event in model.events if event[0] == 'R']
                self.assertIn(SYMBOLS['D_800DBFF0'], reads)
                self.assertLess(reads.index(SYMBOLS['D_800D3094']), reads.index(SYMBOLS['D_800DBFF0']))
                visits.update(model.visits)
            self.assertEqual(complete(models[0]), complete(models[1]))
            count += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)) - {0x150A3044})
        self.receipt.update(guest_phases=count, all_256_flag_bytes=True, full_word_view_selectors=True,
            unsigned_count_equality_and_zero_zero=True, mixed_GPR_float_bits=True,
            early_count_and_view_pointer_reads=True, visited_words=44, unreachable_zero_retained=True)

    def test_03_native32_valid_typed_arrays_and_effective_controls(self):
        exits = {}
        for label, opt, body, valid in [('O0', '-O0', source.SELECTED, True),
                ('O2', '-O2', source.SELECTED, True), ('O3', '-O3', source.SELECTED, True)] + [
                (name, '-O2', body, False) for name, body in controls().items()]:
            unit = self.output / ('native-' + label + '.c')
            unit.write_text(native_harness(body))
            exe = unit.with_suffix('')
            p = subprocess.run([*native_command(opt, valid), str(unit), '-o', str(exe)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            p = subprocess.run([str(exe)], timeout=60)
            self.assertEqual(p.returncode, 0 if valid else 23, label)
            exits[label] = p.returncode
        self.receipt.update(native32=exits, selected_UBSan_trap=True, all_4096_indices=True,
            all_256_flag_bytes_native=True, valid_canonical_view_record_arrays=True,
            native_aliases_or_hardware_FCSR_claimed=False, opaque_native_helper=True)

    def test_04_original_helper_and_full_original_caller_route(self):
        helper = list(struct.unpack_from('>38I', self.rom, 0xD02FC))
        padded, functions = source.link_owner(ROOT, self.output, self.output / 'qualified-padded.o', source.OWNER)
        self.assertEqual(struct.unpack_from('>38I', padded, functions['func_150A2E4C']['value']), tuple(helper))
        connected = dict(zip(range(0x150A2E4C, 0x150A2EE4, 4), helper))
        phases, seen = 0, set()
        for view, origins, point in itertools.product((0, 3), ((0, 0, 0), (-32768, 17, 32767), (9, -123, 5)), POINTS[:2]):
            memory = fixture(view, 1, 1, 3, point)
            record = RECORDS + 0x34
            for i, value in enumerate(origins):
                put(memory, record + 2 * i, value & 0xFFFF, 2)
            for offset, value in ((0x24, 1.0), (0x28, 0.5), (0x2C, -2.0), (0x30, 3.0)):
                put(memory, record + offset, bits(value))
            x = floating(bits(floating(point[0]) - origins[0]))
            y = floating(bits(floating(point[1]) - origins[1]))
            z = floating(bits(y - origins[2]))
            value = floating(bits(floating(bits(floating(bits(z * 3.0)) + floating(bits(x * -2.0)))) * 0.5))
            wanted = int(floating(bits(value - y)) <= 0.0)
            models = [QueryOracle(w, memory, view, 1, connected=connected).run() for w in (self.truth, self.words)]
            self.assertEqual(complete(models[0]), complete(models[1]))
            self.assertEqual(models[0].r[2], wanted)
            seen.update(models[0].visits)
            phases += 1
        parent = list(struct.unpack_from('>317I', self.rom, 0xCD988))
        parent_phases = 0
        for view, selector, limit, flag, phase in itertools.product((0, 3), (0, 1, 0x1001),
                (0, 1, 0xFFFFFFFF), (0, 3, 255), (0, 8)):
            memory = fixture(view, selector, limit, flag, POINTS[1])
            put(memory, PACKET + 8, 0x9000 | view)
            for i, address in enumerate(PARENT_TABLE):
                put(memory, TABLE + i * 4, address)
            result, calls = expected(memory, view, selector)
            models = [QueryOracle(parent, memory, phase=phase, entry=PARENT,
                arguments=(selector, 13, PACKET),
                connected=dict(zip(range(source.ENTRY, source.ENTRY + source.SIZE, 4), words))).run()
                for words in (self.truth, self.words)]
            self.assertEqual(complete(models[0]), complete(models[1]))
            self.assertEqual((models[0].r[2], models[0].calls),
                (result, [(source.ENTRY, (view, selector)), *calls]))
            parent_phases += 1
        self.assertEqual((ROOT / 'conker/src/game/generated_CD860.c').read_bytes(),
            self.values['conker/src/game/generated_CD860.c'])
        self.assertEqual((ROOT / 'conker/build/src/game/generated_CD860.c.o').read_bytes(),
            self.values['conker/build/src/game/generated_CD860.c.o'])
        self.receipt.update(original_helper_phases=phases, original_helper_visited_words=len(
            seen & set(range(0x150A2E4C, 0x150A2EE4, 4))), original_helper_words=38,
            original_caller_words=317, original_caller_command=13, original_caller_phases=parent_phases,
            caller_retained_stub_uncredited=True, complete_dispatcher_other_routes_qualified=False)

    def rebased(self, obj, entry, symbols, label):
        text, functions, bindings = source.parse_object(obj)
        assembly, unknown = emit_function(text, functions[source.FUNCTION], bindings, source.FUNCTION, symbols)
        self.assertFalse(unknown)
        p = self.output / label
        p.with_suffix('.s').write_text(assembly)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(p.with_suffix('.o')),
            str(p.with_suffix('.s'))], check=True, capture_output=True)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(p.with_suffix('.ld')),
            '-e', source.FUNCTION, *['--defsym=%s=0x%X' % row for row in symbols.items()],
            '-o', str(p.with_suffix('.elf')), str(p.with_suffix('.o'))], check=True, capture_output=True)
        return list(struct.unpack_from('>45I', sections(p.with_suffix('.elf'))['.text'][1]))

    def test_05_GNU_rebases_guest_aliases_and_fired_fault_prefixes(self):
        objects = (source.original(ROOT, self.output), self.output / 'qualified-padded.o',
            self.output / 'make-shadow/src/game/generated_CDE80.c.o')
        count = 0
        for i, entry in enumerate((source.ENTRY, 0x18017FFC, 0x1A028000)):
            symbols = SYMBOLS if not i else dict(D_800D3094=0x81007FFC + i * 0x10000,
                D_800DBFF0=0x82008000 + i * 0x10000, D_800D3098=0x8300FFFC + i * 0x10000,
                func_150A2E4C=entry + 0x10000)
            images = [self.rebased(obj, entry, symbols, 'rebase-%d-%d' % (i, j)) for j, obj in enumerate(objects)]
            self.assertEqual(images[0], images[1])
            self.assertEqual(images[0], images[2])
            for selector, limit, flag in itertools.product((0, 1, 0x1001), (0, 1, 0xFFFFFFFF), (0, 3, 255)):
                memory = fixture(3, selector, limit, flag, POINTS[1], symbols)
                result, calls = expected(memory, 3, selector, symbols)
                models = [QueryOracle(w, memory, 3, selector, symbols=symbols, entry=entry).run() for w in images[:2]]
                self.assertEqual(complete(models[0]), complete(models[1]))
                self.assertEqual((models[0].r[2], models[0].calls), (result, calls))
                count += 1
        aliases = 0
        for views, records in ((STACK - 0x2F8 - 24, RECORDS),
                (VIEWS, STACK - 24), (VIEWS, STACK - 20), (STACK - 0x2F8, STACK + 32)):
            memory = fixture(0, 0, 0, 3, POINTS[1], views=views, records=records)
            models = [QueryOracle(w, memory, 0, 0).run() for w in (self.truth, self.words)]
            self.assertEqual(complete(models[0]), complete(models[1]))
            aliases += 1
        cuts = 0
        for limit, flag, phase in itertools.product((0, 1), (0, 3, 255), (0, 8)):
            memory = fixture(3, 1, limit, flag)
            accesses = QueryOracle(self.truth, memory, 3, 1, phase=phase).run().root_accesses
            for cut in range(accesses):
                models = [QueryOracle(w, memory, 3, 1, phase=phase, fault=cut) for w in (self.truth, self.words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                self.assertEqual(complete(models[0]), complete(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of, models[0].dispatched_word),
                    (models[1].current_pc, models[1].delay_of, models[1].dispatched_word))
                cuts += 1
        self.receipt.update(GNU_links=9, GNU_rebased_phases=count, guest_stack_aliases=aliases,
            fired_target_fault_prefixes=cuts, literal_complete_guest_states=True,
            portable_C_fault_semantics_claimed=False)

    def test_06_strict_image_inputs_and_stale_stub_negative_controls(self):
        values = source.snapshot(self.output)
        before = values['conker/build/conker.us.elf']
        truth = values['conker/conker.us.bin'][source.ROM:source.ROM + source.SIZE]
        actual = (self.output / 'first-linked.elf').read_bytes()
        source.check_image(before, actual, truth)
        at = source.elf_slot_offset(before, source.ENTRY, source.SIZE)
        offsets = (0, at, at + source.SIZE - 1, at + source.SIZE, len(actual) - 1)
        for offset in offsets:
            wrong = bytearray(actual)
            wrong[offset] ^= 1
            with self.assertRaises(ValueError):
                source.check_image(before, bytes(wrong), truth)
        with self.assertRaises(ValueError):
            source.check_image(before, actual + b'\0', truth)
        with self.assertRaises(ValueError):
            source.checked_payload(*source.payload(self.output / 'before-padded.o'))
        for name in (source.SOURCE, source.OBJECT, 'conker/include/structs.h',
                'conker/retail_word_patches.us.csv', 'conker/asm/CDE80.s',
                'conker/src/game/generated_CD860.c'):
            target = self.output / ('before-' + name.replace('/', '_'))
            original = Path.read_bytes
            def changed(path):
                data = original(path)
                return bytes([data[0] ^ 1]) + data[1:] if path == target else data
            with patch.object(Path, 'read_bytes', changed), self.assertRaises(ValueError):
                source.snapshot(self.output)
        self.receipt.update(strict_image_controls=6, frozen_input_controls=6,
            old_stub_rejected=True, metadata_exclusions=0)
