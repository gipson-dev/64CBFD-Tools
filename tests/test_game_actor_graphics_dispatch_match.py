"""Complete graphics forwarding, live dispatch, return sources and linked audit."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout, load_section
from tools.experiments import game_actor_graphics_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests import test_game_trail_effect_constructor_recovery as layout
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_174BF0.c'
ACTOR, COMMANDS, RESULT, CALLBACK_RESULT = 0x20000, 0x30000, 0x31000, 0x32000
CALLBACK, OTHER = 0x15001000, 0x15002000
WIDTHS = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0xFFFF0001, 0x12348000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.INSERT, '')
    assert old.count(screen.ORIGINAL) == 1
    new = old.replace('/* Non-matching placeholders', screen.INSERT + '/* Non-matching placeholders', 1).replace(
        screen.ORIGINAL, screen.SELECTED)
    return old, new


def signed_half(value):
    value &= 65535
    return (value if value < 32768 else value - 65536) & 0xFFFFFFFF


def fixture(selector=1, flags=0x20, optional=0x81234580, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    memory.update({ACTOR + i: (i * 17 + 0xA5) & 255 for i in range(-16, 0x100)})
    put(memory, ACTOR + 0x1E, flags, 2)
    put(memory, ACTOR + 0x28, optional)
    put(memory, ACTOR + 0x31, selector, 1)
    for i in range(-128, 256):
        put(memory, symbols['D_8008A2A4'] + i * 4, CALLBACK + (i & 3) * 0x100)
    return memory


def mutations(memory, mode, symbols):
    if mode in (1, 2, 3):
        put(memory, ACTOR + 0x31, (0, 1, 19)[mode - 1], 1)
        put(memory, ACTOR + 0x28, 0x76543210)
        put(memory, ACTOR + 0x1E, 0xFFFF, 2)
    if mode == 4:
        for i in range(1, 19):
            put(memory, symbols['D_8008A2A4'] + i * 4, OTHER + (i & 3) * 0x100)


def reference(memory, args, result, callback_result, mode, symbols):
    memory = dict(memory)
    commands, actor, index = args
    optional = read(memory, actor + 0x28) if read(memory, actor + 0x1E, 2) & 0x20 else 0
    calls = [('graphics', (commands, actor + 0x34, 0, 0, 0, signed_half(index), actor + 0x54, 2, optional))]
    mutations(memory, mode, symbols)
    selector = read(memory, actor + 0x31, 1)
    if selector >= 19:
        calls.append(('destroy', (actor,)))
        put(memory, actor + 0x50, 0xDDDDDDDD)
    elif selector:
        target = read(memory, symbols['D_8008A2A4'] + selector * 4)
        calls.append(('callback', target, (actor, result, signed_half(index))))
        put(memory, actor + 0x50, 0xCCCCCCCC)
        result = callback_result
    return memory, calls, result


class DispatchOracle(TriangleOracle):
    def __init__(self, words, memory, args=(COMMANDS, ACTOR, 0x81238000), result=RESULT,
            callback_result=CALLBACK_RESULT, mode=0, phase=0, entry=screen.ENTRY, symbols=None, callbacks=None):
        super().__init__(words, memory, arguments=args, phase=phase, entry=entry)
        self.result, self.callback_result, self.mode = result, callback_result, mode
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.callbacks = {base + i * 0x100 for base in (CALLBACK, OTHER) for i in range(4)} if callbacks is None else callbacks

    def execute(self, word):
        if word >> 26 == 32:
            rs, rt, imm = word >> 21 & 31, word >> 16 & 31, word & 65535
            address = (self.r[rs] + (imm if imm < 32768 else imm - 65536)) & 0xFFFFFFFF
            value = self.get(address, 1)
            self.r[rt] = (value if value < 128 else value - 256) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def record_call(self, target):
        if target == self.symbols['func_151462C8']:
            self.calls.append(('graphics', self.arguments(9)))
        elif target == self.symbols['func_1516972C']:
            self.calls.append(('destroy', self.arguments(1)))
        else:
            assert target in self.callbacks, hex(target)
            self.calls.append(('callback', target, self.arguments(3)))

    def hook(self, target):
        call = self.calls[-1]
        if call[0] == 'graphics':
            before = dict(self.memory)
            mutations(self.memory, self.mode, self.symbols)
            # Route fixture writes through the existing oracle access log.
            for address, value in list(self.memory.items()):
                if before.get(address) != value:
                    self.memory[address] = before[address]
                    self.put(address, value, 1)
            result = self.result
            if self.mode == 5:
                for i in range(9):
                    self.put(self.r[29] + i * 4, 0x76540000 + i, 4)
        elif call[0] == 'destroy':
            self.put(call[1][0] + 0x50, 0xDDDDDDDD, 4)
            result = 0xBEEF1234
        else:
            self.put(call[2][0] + 0x50, 0xCCCCCCCC, 4)
            result = self.callback_result
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


def size_offset(data):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    offsets = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == screen.FUNCTION:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                offsets.append(offset + 8)
    assert len(offsets) == 1
    return offsets[0]


def slot_records(root):
    functions, _, addresses = load_elf_functions(str(root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
    return {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
        struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}, functions


class GameActorGraphicsDispatchMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-graphics-dispatch-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>52I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            prior = json.loads((cls.root / 'conker/build/game-effect-allocation-core-test/after.json').read_text())
            slots, _ = slot_records(cls.root)
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert (slots, guards, progress) == (prior['slots'], prior['guards'], prior['progress'])
            assert len(slots) == 6058 and len(guards) == 11475
            old, _ = shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes()
            baseline.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def compare(self, memory, args=(COMMANDS, ACTOR, 0x81238000), result=RESULT, callback_result=CALLBACK_RESULT,
            mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None, callbacks=None):
        symbols = screen.SYMBOLS if symbols is None else symbols
        wanted, calls, returned = reference(memory, args, result, callback_result, mode, symbols)
        models = []
        for body in ((words,) if words is not None else (self.words, self.retail)):
            model = DispatchOracle(body, memory, args, result, callback_result, mode, phase, entry, symbols, callbacks).run()
            self.assertEqual((model.calls, model.r[2], external(model.memory)), (calls, returned, external(wanted)))
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].events, models[0].memory),
                (models[1].r, models[1].f, models[1].events, models[1].memory))
        return models

    def test_01_complete_direct_slot_profiles_and_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (52, 56, 0))
        self.assertEqual((self.words, self.meta['diagnostics'], self.meta['pool_bytes']), (self.retail, '', 0))
        relocs = [r for items in self.meta['relocations'].values() for r in items]
        self.assertEqual({symbol for _, symbol in relocs}, set(screen.SYMBOLS))
        self.assertEqual([sum(k == kind for k, _ in relocs) for kind in ('R_MIPS_26', 'R_MIPS_HI16', 'R_MIPS_LO16')], [2, 1, 1])
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=52, bytes=208, frame=56, guards=0, profiles=profiles))

    def test_02_all_selector_bytes_signed_widths_live_mutations_and_returns(self):
        count, reached = 0, set()
        for selector, mode, phase in itertools.product(range(256), range(6), (0, 8)):
            models = self.compare(fixture(selector), mode=mode, phase=phase)
            reached.update(models[0].visits)
            count += 1
        for selector, flags, width, result, callback_result, phase in itertools.product(
                (0, 1, 18, 19, 128, 255), (0, 0x20, 0xFFDF, 0xFFFF), WIDTHS, (0, RESULT), (0, CALLBACK_RESULT), (0, 8)):
            models = self.compare(fixture(selector, flags), (COMMANDS, ACTOR, width), result, callback_result, phase=phase)
            reached.update(models[0].visits)
            count += 1
        for optional in WIDTHS:
            self.compare(fixture(optional=optional))
            count += 1
        self.assertEqual(len(reached), 52)
        self.receipt('guest', dict(cases=count, executions=count * 2, all_52_words=True,
            all_256_selector_bytes=True, live_selector_and_callback_table=True, signed_halfword=True,
            callback_result_not_graphics_result=True, destructor_return_ignored=True, both_SP_phases=True,
            saved_GP_FP=True, nine_argument_outgoing_home_clobbers=True))

    def test_03_lazy_optional_table_and_missing_public_byte_fault_prefixes(self):
        faults = 0
        for selector, flags, phase in itertools.product((0, 1, 18, 19, 255), (0, 0x20), (0, 8)):
            memory = fixture(selector, flags)
            complete = DispatchOracle(self.retail, memory, phase=phase).run()
            used = {e[1] + i for e in public(complete.events) if e[0] in ('R', 'W') for i in range(e[2])}
            for address in sorted(used):
                missing = dict(memory)
                del missing[address]
                models = [DispatchOracle(body, missing, phase=phase) for body in (self.words, self.retail)]
                self.assertEqual([outcome(model) for model in models], [False, False])
                self.assertEqual((external(models[0].memory), public(models[0].events), models[0].calls),
                    (external(models[1].memory), public(models[1].events), models[1].calls))
                faults += 1
            minimal = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x140 or a in used}
            self.compare(minimal, phase=phase)
        self.receipt('faults', dict(missing_public_byte_pairs=faults, optional_read_only_when_flag_set=True,
            table_read_only_for_1_through_18=True, graphics_inputs_opaque_in_bounded_fixture=True,
            fault_prefix_not_portable_C_or_hardware_acceptance=True))

    def test_04_complete_forms_and_effective_semantic_negatives(self):
        negatives = {
            'negative-optional-flag': screen.SELECTED.replace('& 0x20', '& 0x10'),
            'negative-zero-index': screen.SELECTED.replace('        index, actor + 0x54', '        0, actor + 0x54'),
            'negative-threshold': screen.SELECTED.replace('>= 0x13', '>= 0x12'),
            'negative-discard-callback': screen.SELECTED.replace('return D_8008A2A4[selector]', 'D_8008A2A4[selector]'),
            'negative-fixed-flags': screen.SELECTED.replace('actor + 0x54, 2, optional', 'actor + 0x54, 1, optional'),
            'negative-stale-selector': screen.SELECTED.replace('    commands = func_', '    selector = actor[0x31];\n    commands = func_').replace('    selector = actor[0x31];\n    if', '    if'),
        }
        samples = [(fixture(s), (COMMANDS, ACTOR, 0x81238000), m) for s, m in ((0, 0), (1, 0), (18, 0), (19, 0), (255, 0), (0, 2), (1, 3), (18, 4))]
        records, effective = [], []
        for name, body in [*screen.candidates(), *negatives.items()]:
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            failed = False
            for memory, args, mode in samples:
                # First require complete execution; faults are not negative proof.
                DispatchOracle(words, memory, args, mode=mode).run()
                wanted, calls, returned = reference(memory, args, RESULT, CALLBACK_RESULT, mode, screen.SYMBOLS)
                model = DispatchOracle(words, memory, args, mode=mode).run()
                failed |= (model.calls, model.r[2], external(model.memory)) != (calls, returned, external(wanted))
            if name in negatives:
                self.assertTrue(failed, name)
                effective.append(name)
            records.append(dict(meta, semantic_difference=failed))
        self.assertEqual(len(effective), 6)
        self.receipt('forms', dict(complete_compiled_forms=len(records), cases_per_form=len(samples), effective_negatives=effective, records=records))

    def test_05_owner_neighbors_actual_padding_and_independent_links(self):
        objects, warnings = [], []
        for name, text in zip(('baseline', 'selected'), shapes(self.root)):
            obj, diagnostic = compile_owner(self.root, self.out, text, 'owner-' + name)
            objects.append(obj)
            warnings.append(diagnostic)
        self.assertEqual(warnings[0], warnings[1])
        old, before, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), before.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION:
                continue
            prior = before[name]
            self.assertEqual(fn['size'], prior['size'], name)
            self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[prior['value']:prior['value'] + prior['size']], name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prior['value']: r for o, r in old_rel.items() if prior['value'] <= o < prior['value'] + prior['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/174BF0.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_174BF0')
        begin = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[begin:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 208)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        cases = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            defs = dict(screen.SYMBOLS)
            if variant:
                defs = dict(func_151462C8=(entry & 0xF0000000) + 0x208000,
                    func_1516972C=(entry & 0xF0000000) + 0x208100,
                    D_8008A2A4=(0x80007FF0, 0x80008000, 0x8000FFF0)[variant - 1])
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % (n, v) for n, v in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>52I', sections(elf)['.text'][1]))
            if not variant:
                self.assertEqual(words, self.retail)
            for selector, mode, phase in itertools.product((0, 1, 18, 19, 255), range(6), (0, 8)):
                self.compare(fixture(selector, symbols=defs), mode=mode, phase=phase, words=words, entry=entry, symbols=defs)
                cases += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, pools_and_relative_relocations_unchanged=True,
            diagnostics=len(warnings[0]), actual_padding_bytes=208, guards=0, independent_links=4, cases=cases))

    def test_06_whole_ELF_only_target_and_symbol_size_change(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, new = shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == new
        slots, functions = slot_records(self.root)
        expected = dict(baseline['slots'])
        data = bytearray((self.out / 'before.elf').read_bytes())
        if installed:
            expected[screen.FUNCTION] = dict(address=screen.ENTRY, words=52,
                sha256=hashlib.sha256(struct.pack('>52I', *self.retail)).hexdigest())
            offset = layout.elf_slot_offset(data, screen.ENTRY, 208)
            data[offset:offset + 208] = struct.pack('>52I', *self.retail)
            offset = size_offset(data)
            self.assertEqual(struct.unpack_from('>I', data, offset)[0], 12)
            struct.pack_into('>I', data, offset, 208)
            self.assertEqual(functions[screen.FUNCTION], self.retail)
        self.assertEqual(slots, expected)
        elf = self.root / 'conker/build/conker.us.elf'
        self.assertEqual(elf.read_bytes(), data)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        for name in ('retail_word_patches.us.csv', 'progress.csv'):
            self.assertEqual((self.root / 'conker' / name).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        self.receipt('linked', dict(installed=installed, symbols=len(slots), guards=11475,
            full_ELF_except_target_and_its_symbol_size_unchanged=True, symbol_size_change=[12, 208] if installed else None,
            progress_unchanged=True, elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed:
            self.receipt('after', dict(slots=slots, guards=baseline['guards'], progress=baseline['progress']))

    def test_07_native32_all_halfword_patterns_all_selectors_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed short s16;
typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
#define NULL ((void *)0)
''' + screen.DECLARATIONS + r'''
static union { u32 align;u8 b[256]; } actor,expectedStorage;
#define expected expectedStorage.b
static u8 commands[16],graphics[16],callback[16];
static u32 arguments[9],optionalWord;
static int expectedIndex,mode,error,count,selector;
u8 *(*D_8008A2A4[256])(u8 *,u8 *,s16);
static u8 *dispatch(u8 *a,u8 *g,s16 index) {
    if(a!=actor.b || g!=graphics || index!=expectedIndex) error=1;
    if(count++!=1) error=2;
    *(u32 *)(a+0x50)=0xCCCCCCCC;
    return callback;
}
void func_1516972C(u8 *a) {
    if(a!=actor.b || count++!=1) error=3;
    *(u32 *)(a+0x50)=0xDDDDDDDD;
}
u8 *func_151462C8(u8 *g,void *d,u8 m,u8 *a,u8 slot,s16 index,void *p,u8 flags,s32 extra) {
    u32 actual[9];int i;
    actual[0]=(u32)g;actual[1]=(u32)d;actual[2]=m;actual[3]=(u32)a;actual[4]=slot;
    actual[5]=(u32)index;actual[6]=(u32)p;actual[7]=flags;actual[8]=(u32)extra;
    for(i=0;i<9;i++) if(actual[i]!=arguments[i]) error=4;
    if(count++!=0) error=5;
    if(mode) {
        actor.b[0x31]=(u8)(mode==1?0:mode==2?1:19);
        *(u16 *)(actor.b+0x1E)=0xFFFF;*(u32 *)(actor.b+0x28)=0x76543210;
    }
    return graphics;
}
''' + screen.SELECTED
        self.run_host(r'''
int i,j,k,n,width;u8 *result;static int choices[]={0,1,18,19,255};
for(width=0;width<65536;width++) for(j=0;j<5;j++) for(k=0;k<2;k++) {
    for(i=0;i<256;i++) actor.b[i]=(u8)(i*17+0xA5);
    selector=choices[j];mode=(width<256)?width%4:0;
    *(u16 *)(actor.b+0x1E)=(u16)(k?0x20:0);
    optionalWord=0x81230000u|(u32)width;*(u32 *)(actor.b+0x28)=optionalWord;
    actor.b[0x31]=(u8)selector;
    expectedIndex=(int)(s16)width;
    arguments[0]=(u32)commands;arguments[1]=(u32)(actor.b+0x34);arguments[2]=0;arguments[3]=0;
    arguments[4]=0;arguments[5]=(u32)expectedIndex;arguments[6]=(u32)(actor.b+0x54);arguments[7]=2;
    arguments[8]=k?optionalWord:0;
    for(i=0;i<256;i++) {expected[i]=actor.b[i];D_8008A2A4[i]=dispatch;}
    if(mode) {
        selector=mode==1?0:mode==2?1:19;expected[0x31]=(u8)selector;
        *(u16 *)(expected+0x1E)=0xFFFF;*(u32 *)(expected+0x28)=0x76543210;
    }
    if(selector) *(u32 *)(expected+0x50)=selector>=19?0xDDDDDDDD:0xCCCCCCCC;
    count=error=0;result=func_15147C4C(commands,actor.b,(s16)(0xFFFF0000u|(u32)width));
    if(error || count!=(selector?2:1)) return 1;
    if(result!=(selector && selector<19?callback:graphics)) return 2;
    for(i=0;i<256;i++) if(actor.b[i]!=expected[i]) return 3;
}
for(n=0;n<256;n++) {
    mode=0;expectedIndex=-32768;count=error=0;actor.b[0x31]=(u8)n;
    *(u16 *)(actor.b+0x1E)=0;arguments[8]=0;
    arguments[5]=(u32)expectedIndex;
    result=func_15147C4C(commands,actor.b,(s16)0x8000);
    if(error || count!=(n?2:1) || result!=(n && n<19?callback:graphics)) return 4;
}
''')
        self.receipt('native', dict(cases=65536 * 10 + 256, all_65536_signed_halfword_patterns=True,
            all_256_selectors=True, helper_mutations=True, canary_bytes=256, distinct_callback_return=True,
            helpers_bounded_not_hardware_or_gameplay_acceptance=True))

    def test_08_actual_protected_callback_table_targets_and_incoming_pointer_witnesses(self):
        base, data = load_section(self.root / 'conker/build/conker.us.elf', '.game_data')
        self.assertTrue(audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')['exact'])
        table = struct.unpack_from('>19I', data, screen.SYMBOLS['D_8008A2A4'] - base)
        self.assertEqual(table, (0, 0x1514803C, 0x15197148, 0x1519D9F4, 0x150DD640,
            0x1519FE6C, 0x151A3BE4, 0x150B4710, 0x1515C6F4, 0x151CDE20,
            0x151BCA90, 0x151B6928, 0x1519B4B8, 0x150D4300, 0x151B7C38,
            0x151CF380, 0x151D80C4, 0x150D9C7C, 0x151D1C98))
        refs = [base + i for i in range(0, len(data) - 3, 4) if struct.unpack_from('>I', data, i)[0] == screen.ENTRY]
        self.assertEqual(refs, [0x8008BB98, 0x8008C454])
        _, functions = slot_records(self.root)
        self.assertTrue(all('func_%08X' % target in functions for target in table[1:]))
        count = 0
        for selector, flags, width, result, callback_result, phase in itertools.product(
                (*range(19), 19, 255), (0, 0x20), (0, 0x7FFF, 0x8000, 0xFFFF), (0, RESULT), (0, CALLBACK_RESULT), (0, 8)):
            memory = fixture(selector, flags)
            for i, target in enumerate(table):
                put(memory, screen.SYMBOLS['D_8008A2A4'] + i * 4, target)
            self.compare(memory, (COMMANDS, ACTOR, width), result, callback_result, phase=phase, callbacks=set(table[1:]))
            count += 1
        self.receipt('table', dict(entries=19, nonnull_dispatch_targets=18, cases=count,
            actual_table_targets=[hex(t) for t in table], incoming_pointer_witnesses=[hex(a) for a in refs],
            actual_callback_bodies_and_upstream_dispatch_not_executed=True))


if __name__ == '__main__':
    unittest.main()
