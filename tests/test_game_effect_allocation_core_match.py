"""Complete allocation core, live resource count, direct callers and linked audit."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_effect_allocation_core_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests import test_game_trail_effect_constructor_recovery as trail
from tools.tests import test_game_effect_record_constructor_match as effect
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_174BF0.c'
REQUEST, OPTIONAL, CREATED = effect.REQUEST, effect.RENDER, trail.CREATED
RESOURCE, TRAILING = 0x35000, 0x36000
WIDTHS = (0, 1, 127, 128, 255, 256, 0xFFFF0001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def source_pairs(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.INSERT, '')
    assert old.count(screen.ORIGINAL) == 1
    marker = '/* Non-matching placeholders for the text-only asm slice asm/174BF0.s. */'
    pairs = {SOURCE: (old, old.replace(marker, screen.INSERT + marker).replace(screen.ORIGINAL, screen.SELECTED))}
    for path, changes in screen.CALLER_CHANGES.items():
        old = (root / path).read_text()
        for before, after in changes:
            old = old.replace(after, before)
            assert old.count(before) == 1
        new = old
        for before, after in changes:
            new = new.replace(before, after)
        pairs[path] = (old, new)
    return pairs


def fixture(count=3, flags=0x40, entries=7, seed=0, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = trail.fixture(seed=seed)
    for base in (REQUEST, OPTIONAL, effect.DESCRIPTOR):
        memory.update({base + i: (i * 13 + seed * 31 + 0xA5) & 255 for i in range(-16, 512)})
    put(memory, REQUEST + 0xE, flags, 2)
    put(memory, REQUEST + 0x15, entries, 1)
    put(memory, symbols['D_80082FA0'], count)
    return memory


def arguments(width=0x81234580, optional=OPTIONAL, resource=3):
    return (REQUEST, width, width, width, width, width, resource, width, optional, width, width)


def changes(mode, role, index=0, request=REQUEST, optional=OPTIONAL, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    count = symbols['D_80082FA0']
    if role == 'allocate' and mode == 3:
        return ((request + 0xF, 0x40, 1), (request + 0x15, 3, 1), (request, 0x12345678, 4), (count, 0, 4))
    if role == 'copy' and mode == 4 and optional:
        return ((optional, 0x76543210, 4),)
    if role == 'resource' and index == 0 and mode in (1, 2):
        return ((count, 0xFFFFFFFF if mode == 1 else 3, 4),)
    return ()


def reference(memory, args, result, mode, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory, calls = dict(memory), []
    request, size, stride, active, first, second, resource, value, optional, channel, context = args
    kind = 0x4D if read(memory, request + 0xE, 2) & 0x40 else 0x22
    total = (size + read(memory, request + 0x15, 1) * stride + 0xA0) & 0xFFFFFFFF
    calls.append(('allocate', (kind, context, total, 1, channel & 255, 1)))

    def mutate(role, index=0):
        for address, data, width in changes(mode, role, index, request, optional, symbols):
            put(memory, address, data, width)

    mutate('allocate')
    if not result:
        return memory, calls
    put(memory, result + 0x98, result + 0xA0)
    put(memory, result + 0x94, result + 0xA0 + size)
    packet = bytes(memory[request + i] for i in range(28))
    calls.append(('copy', result + 0x10, packet, 28))
    for i, byte in enumerate(packet):
        put(memory, result + 0x10 + i, byte, 1)
    mutate('copy')
    for i, byte in enumerate((0, 0, 0, active, first, second)):
        put(memory, result + 0x2C + i, byte, 1)
    if optional:
        for i in range(9):
            put(memory, result + 0x60 + i * 4, read(memory, optional + i * 4))
    else:
        put(memory, result + 0x7C, 0, 1)
    put(memory, result + 0x34, resource)
    put(memory, result + 0x50, value)
    put(memory, result + 0x38, 0, 1)
    for i in range(4):
        put(memory, result + 0x3C + i * 4, 0)
    put(memory, result + 0x4C, 0)
    if resource:
        i = 0
        while i <= signed(read(memory, symbols['D_80082FA0'])):
            assert i < 4, ('bounded resource fixture', i)
            calls.append(('resource', resource))
            put(memory, result + 0x3C + i * 4, resource_result(i))
            mutate('resource', i)
            i += 1
        calls.append(('trailing',))
        put(memory, result + 0x4C, TRAILING)
    for i in range(3):
        put(memory, result + 0x54 + i * 4, 0)
    calls.append(('zero', result + 0x84, 16))
    for i in range(16):
        put(memory, result + 0x84 + i, 0, 1)
    return memory, calls


def signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def resource_result(index):
    return 0 if index % 3 == 1 else RESOURCE + index * 0x100


class CoreOracle(trail.ConstructorOracle):
    def __init__(self, words, memory, args, result=CREATED, mode=0, phase=0,
            entry=screen.ENTRY, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=args, connected=connected)
        self.fcsr = self.initial_fcsr = 0
        self.result, self.mode = result, mode
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.raw_calls, self.resources = [], 0
        self.request, self.optional = args[0], args[8] if len(args) == 11 else 0

    def record_call(self, target):
        if target == self.symbols['func_15167A68']:
            args = self.arguments(6)
            role, call = 'allocate', ('allocate', args)
        elif target == self.symbols['memcpy']:
            args = self.arguments(3)
            role, call = 'copy', ('copy', args[0], self.packet(args[1], args[2]), args[2])
        elif target == self.symbols['func_1515D480']:
            args = self.arguments(1)
            role, call = 'resource', ('resource', args[0])
        elif target == self.symbols['func_1515D440']:
            args, role, call = (), 'trailing', ('trailing',)
        elif target == self.symbols['bzero']:
            args = self.arguments(2)
            role, call = 'zero', ('zero', *args)
        else:
            assert target in self.connected, hex(target)
            return
        self.raw_calls.append((role, args))
        self.calls.append(call)

    def hook(self, target):
        role, args = self.raw_calls[-1]
        if role == 'allocate':
            value = self.result
        elif role == 'copy':
            destination, source, size = args
            assert size in (12, 20, 28, 32, 60)
            for i in range(size):
                self.put(destination + i, self.get(source + i, 1), 1)
            value = destination
        elif role == 'resource':
            value = resource_result(self.resources)
        elif role == 'trailing':
            value = TRAILING
        else:
            assert role == 'zero'
            destination, size = args
            assert size in (8, 16)
            for i in range(size):
                self.put(destination + i, 0, 1)
            value = 0x76543210
        for address, data, width in changes(self.mode, role, self.resources, self.request, self.optional, self.symbols):
            self.put(address, data, width)
        if role == 'resource':
            self.resources += 1
        if self.mode == 5:
            for i in range(len(args)):
                self.put(self.r[29] + i * 4, 0x76543210 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = value


def symbol_size_offset(data):
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


class GameEffectAllocationCoreMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-effect-allocation-core-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>115I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            prior = json.loads((cls.root / 'conker/build/game-effect-record-constructor-test/after.json').read_text())
            elf = cls.root / 'conker/build/conker.us.elf'
            functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
            slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
                struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
            with (cls.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
                guards = list(csv.DictReader(stream))
            with (cls.root / 'conker/progress.csv').open(newline='') as stream:
                progress = list(csv.DictReader(stream))
            assert slots == prior['slots'] and guards == prior['guards'] and progress == prior['progress']
            assert len(slots) == 6058 and len(guards) == 11475
            pairs = source_pairs(cls.root)
            assert all((cls.root / path).read_text() == texts[0] for path, texts in pairs.items())
            baseline.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256={p: hashlib.sha256(t[0].encode()).hexdigest() for p, t in pairs.items()},
                elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(elf.read_bytes())
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def compare(self, memory, args, result=CREATED, mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None):
        wanted, calls = reference(memory, args, result, mode, symbols)
        models = [CoreOracle(body, memory, args, result, mode, phase, entry, symbols).run()
            for body in ((words,) if words is not None else (self.words, self.retail))]
        for model in models:
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], result)
            self.assertEqual(external(model.memory), external(wanted))
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models

    def test_01_direct_slot_profiles_and_complete_header(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (115, 56, 0))
        self.assertEqual((self.words, self.meta['diagnostics'], self.meta['pool_bytes']), (self.retail, '', 0))
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=115, bytes=460, frame=56, guards=0, profiles=profiles,
            full_eleven_word_interface=True, header_bytes=160, optional_bytes=36))

    def test_02_complete_word_widths_live_count_mutations_and_null(self):
        count, reached = 0, set()
        for bound, flags, optional, resource, result, mode, phase in itertools.product(
                (-2, -1, 0, 1, 2, 3), (0, 0x40), (0, OPTIONAL), (0, 3), (0, CREATED), range(6), (0, 8)):
            memory = fixture(bound, flags, seed=mode)
            models = self.compare(memory, arguments(optional=optional, resource=resource), result, mode, phase)
            reached.update(models[0].visits)
            count += 1
        for index, width in itertools.product((1, 2, 3, 4, 5, 6, 7, 9, 10), WIDTHS):
            args = list(arguments())
            args[index] = width
            self.compare(fixture(), args)
            count += 1
        for entry_count in range(256):
            self.compare(fixture(entries=entry_count), arguments())
            count += 1
        self.assertEqual(len(reached), 115)
        self.receipt('guest', dict(cases=count, executions=count * 2, all_115_words=True,
            unsigned_size_product_and_sum=True, live_global_count=True, helper_mutations=True,
            null_resource_results_stored=True, original_return_and_saved_registers=True, both_SP_phases=True))

    def test_03_lazy_null_public_fault_prefixes_and_optional_aliases(self):
        faults = 0
        for result, optional, phase in itertools.product((0, CREATED), (0, OPTIONAL), (0, 8)):
            memory, args = fixture(), arguments(optional=optional)
            complete = CoreOracle(self.retail, memory, args, result, phase=phase).run()
            used = {e[1] + i for e in public(complete.events) if e[0] in ('R', 'W') for i in range(e[2])}
            for address in sorted(used):
                missing = dict(memory)
                del missing[address]
                models = [CoreOracle(body, missing, args, result, phase=phase) for body in (self.words, self.retail)]
                self.assertEqual([outcome(m) for m in models], [False, False])
                self.assertEqual((external(models[0].memory), public(models[0].events), models[0].calls),
                    (external(models[1].memory), public(models[1].events), models[1].calls))
                faults += 1
            if not result:
                lazy = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x160
                    or a in (REQUEST + 0xE, REQUEST + 0xF, REQUEST + 0x15)}
                self.compare(lazy, args, 0, phase=phase)
        for optional, phase in itertools.product((REQUEST, CREATED + 0x60, CREATED + 0x10), (0, 8)):
            self.compare(fixture(), arguments(optional=optional), phase=phase)
        self.receipt('faults', dict(missing_public_byte_pairs=faults, optional_aliases=6,
            lazy_null_inputs=True, emitted_fault_prefixes_only=True, hardware_traps=False, portable_invalid_C=False))

    def test_04_complete_fitting_controls_and_effective_compiled_negatives(self):
        forms = [('selected', screen.SELECTED), ('three-schedule-words', dict(screen.kind_fitting())['kind-type-u8'])]
        forms += list(screen.candidates())
        forms += [('negative-kind', screen.SELECTED.replace('kind = 0x4D', 'kind = 0x4C')),
            ('negative-request-copy', screen.SELECTED.replace('request, 28)', 'request, 20)')),
            ('negative-active', screen.SELECTED.replace('flags[3] = active', 'flags[3] = 0')),
            ('negative-size', screen.SELECTED.replace('+ extra + 0xA0', '+ extra + 0x98')),
            ('negative-zero', screen.SELECTED.replace('bzero(created->cleared, 0x10)', 'bzero(created->cleared, 8)')),
            ('negative-cached-count', screen.SELECTED.replace('    s32 i;', '    s32 i;\n    s32 cached;').replace(
                '    if (resourceBytes != 0)', '    cached = D_80082FA0;\n    if (resourceBytes != 0)').replace('i <= D_80082FA0', 'i <= cached'))]
        records = []
        for name, body in forms:
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            records.append(meta)
            matched = []
            for result, mode in itertools.product((0, CREATED), (0, 1, 2, 4)):
                memory, args = fixture(count=0), arguments()
                model = CoreOracle(words, memory, args, result, mode).run()
                wanted, calls = reference(memory, args, result, mode)
                matched.append((external(model.memory), model.calls, model.r[2]) == (external(wanted), calls, result))
            self.assertEqual(all(matched), not name.startswith('negative-'), name)
        self.receipt('forms', dict(forms=records, cases_per_form=8, effective_compiled_negatives=6))

    def test_05_owners_actual_padding_and_independent_rebases(self):
        reports, target_obj = {}, None
        pairs = source_pairs(self.root)
        unchanged = 'conker/src/game/generated_204660.c'
        pairs[unchanged] = ((self.root / unchanged).read_text(),) * 2
        for index, (path, texts) in enumerate(pairs.items()):
            objects, warnings = [], []
            for name, source in zip(('baseline', 'selected'), texts):
                stem = 'owner-%d-' % index + name
                obj, diagnostic = compile_owner(self.root, self.out, source, stem)
                processed = self.out / (stem + '-post.o')
                processed.write_bytes(obj.read_bytes())
                subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                    str((self.out / (stem + '.c')).relative_to(self.root / 'conker')), '--post-process',
                    str(processed.relative_to(self.root / 'conker')), '--assembler',
                    'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                    '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
                objects.append(processed)
                warnings.append(diagnostic)
            self.assertEqual(warnings[0], warnings[1], path)
            old, before, old_rel = parse_object(objects[0])
            text, current, rel = parse_object(objects[1])
            self.assertEqual(before.keys(), current.keys())
            for name, fn in current.items():
                if name == screen.FUNCTION:
                    continue
                prior = before[name]
                self.assertEqual(fn['size'], prior['size'], name)
                self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[prior['value']:prior['value'] + prior['size']], name)
                self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                    {o - prior['value']: r for o, r in old_rel.items() if prior['value'] <= o < prior['value'] + prior['size']}, name)
            self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
            reports[path] = dict(functions=len(current), diagnostics=len(warnings[0]))
            if path == SOURCE:
                target_obj = objects[1]
        assembly = emit_padded_assembly(target_obj, self.root / 'conker/asm/174BF0.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_174BF0')
        begin = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[begin:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 460)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            defs = dict(screen.SYMBOLS)
            if variant:
                for i, name in enumerate(defs):
                    defs[name] = ((entry & 0xF0000000) + 0x208000 + i * 0x100
                        if name != 'D_80082FA0' else (0x80207FFC, 0x80208000, 0x80208004)[variant - 1])
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in defs.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>115I', sections(elf)['.text'][1]))
            if not variant:
                self.assertEqual(words, self.retail)
            for bound, mode, result, phase in itertools.product((-1, 0, 3), range(6), (0, CREATED), (0, 8)):
                self.compare(fixture(bound, symbols=defs), arguments(), result, mode, phase, words, entry, defs)
                count += 1
        self.receipt('owner', dict(owners=reports, neighbors_pools_and_relative_relocations_unchanged=True,
            actual_padding_bytes=460, guards=0, independent_links=4, cases=count))

    def test_06_whole_linked_only_core_and_symbol_size_change(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        pairs = source_pairs(self.root)
        self.assertEqual({p: hashlib.sha256(t[0].encode()).hexdigest() for p, t in pairs.items()}, baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == pairs[SOURCE][1]
        self.assertTrue(all((self.root / p).read_text() == t[int(installed)] for p, t in pairs.items()))
        elf = self.root / 'conker/build/conker.us.elf'
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
            struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
        expected = dict(baseline['slots'])
        data = bytearray((self.out / 'before.elf').read_bytes())
        if installed:
            expected[screen.FUNCTION] = dict(address=screen.ENTRY, words=115,
                sha256=hashlib.sha256(struct.pack('>115I', *self.retail)).hexdigest())
            offset = trail.elf_slot_offset(data, screen.ENTRY, 460)
            data[offset:offset + 460] = struct.pack('>115I', *self.retail)
            offset = symbol_size_offset(data)
            self.assertEqual(struct.unpack_from('>I', data, offset)[0], 12)
            struct.pack_into('>I', data, offset, 460)
            self.assertEqual(functions[screen.FUNCTION], self.retail)
        self.assertEqual(slots, expected)
        self.assertEqual(elf.read_bytes(), data)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        for name in ('retail_word_patches.us.csv', 'progress.csv'):
            self.assertEqual((self.root / 'conker' / name).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        self.receipt('linked', dict(installed=installed, symbols=len(slots), target_words=115,
            full_ELF_except_target_and_symbol_size_unchanged=True, symbol_size_change=[12, 460] if installed else None,
            guards=11475, progress_unchanged=True, callers_unchanged=True,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed:
            self.receipt('after', dict(slots=slots, guards=baseline['guards'], progress=baseline['progress']))

    def test_07_native32_header_live_count_optional_and_canaries(self):
        self.fixture = '''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;
typedef int s32;typedef float f32;
#define NULL ((void *)0)
''' + screen.RECORD + r'''
static union { u32 align;u8 bytes[512]; } arena,request,optional;
static u8 *created=arena.bytes+16;
static s32 D_80082FA0,initialBound,resourceBytes,value,payloadBytes;
static u32 width,total;
static int mode,failed,optionalPresent,error,allocated,copied,resources,trailing,zeroed;
static u8 *func_15167A68(s32 kind,s32 context,s32 size,s32 active,u8 channel,u8 one) {
    u32 expected=(u32)payloadBytes+(u32)request.bytes[16+0x15]*width+0xA0;
    if(allocated++ || kind!=((*(u16 *)(request.bytes+16+0xE)&0x40)?0x4D:0x22)
       || (u32)context!=width || (u32)size!=expected || active!=1 || channel!=(u8)width || one!=1) error=1;
    total=(u32)size;
    if(mode==3) { request.bytes[16+0xF]=0x40;request.bytes[16+0x15]=3;
      *(u32 *)(request.bytes+16)=0x12345678;D_80082FA0=0; }
    return failed?NULL:created;
}
static void *memcpy(void *d,const void *s,unsigned int n) {
    unsigned int i;u8 *out=d;const u8 *in=s;
    if(copied++ || d!=created+0x10 || s!=request.bytes+16 || n!=28) error=2;
    for(i=0;i<n;i++) out[i]=in[i];
    if(mode==4 && optionalPresent) *(u32 *)(optional.bytes+16)=0x76543210;
    return d;
}
static u8 *func_1515D480(s32 size) {
    int index=resources++;
    if(size!=resourceBytes || index>=4) error=3;
    if(index==0 && mode==1) D_80082FA0=-1;
    if(index==0 && mode==2) D_80082FA0=3;
    return index%3==1?NULL:(u8 *)(0x35000+index*0x100);
}
static u8 *func_1515D440(void) { if(trailing++) error=4;return (u8 *)0x36000; }
static void bzero(void *d,int n) {
    int i;if(zeroed++ || d!=created+0x84 || n!=16) error=5;
    for(i=0;i<n;i++) ((u8 *)d)[i]=0;
}
static void reset(u32 low) {
    int i;for(i=0;i<512;i++) {
      arena.bytes[i]=(u8)(i*17+0xA5);request.bytes[i]=(u8)(i*13+0x87);optional.bytes[i]=(u8)(i*7+0x89);
    }
    width=0xFFFF0000|low;mode=low%5;failed=(low>>1)&1;optionalPresent=(low>>2)&1;
    initialBound=(s32)(low%6)-2;D_80082FA0=initialBound;
    resourceBytes=(low&8)?(s32)width:0;value=(s32)width;payloadBytes=(s32)(low%129);
    *(u16 *)(request.bytes+16+0xE)=(low&0x10)?0x40:0;
    request.bytes[16+0x15]=(u8)low;
    error=allocated=copied=resources=trailing=zeroed=0;total=0;
}
''' + screen.SELECTED + '\n'
        self.run_host(r'''
u32 low;int i,j,expectedResources;u8 expected[512],*result;u32 word;
if(sizeof(EffectCore15147A80)!=160 || sizeof(EffectOptional15147A80)!=36) return 1;
for(low=0;low<65536;low++) {
    reset(low);for(i=0;i<512;i++) expected[i]=arena.bytes[i];
    result=func_15147A80(request.bytes+16,payloadBytes,(s32)width,(s32)width,(s32)width,
        (s32)width,resourceBytes,value,optionalPresent?optional.bytes+16:NULL,(u8)width,(s32)width);
    if(error || allocated!=1 || result!=(failed?NULL:created)) return 2;
    expectedResources=0;
    if(!failed) {
      *(u8 **)(expected+16+0x98)=created+0xA0;
      *(u8 **)(expected+16+0x94)=created+0xA0+payloadBytes;
      for(i=0;i<28;i++) expected[16+0x10+i]=request.bytes[16+i];
      for(i=0;i<3;i++) expected[16+0x2C+i]=0;
      for(i=0;i<3;i++) expected[16+0x2F+i]=(u8)width;
      if(optionalPresent) for(i=0;i<36;i++) expected[16+0x60+i]=optional.bytes[16+i];
      else expected[16+0x7C]=0;
      *(s32 *)(expected+16+0x34)=resourceBytes;*(s32 *)(expected+16+0x50)=value;
      expected[16+0x38]=0;
      for(i=0;i<5;i++) *(u32 *)(expected+16+0x3C+i*4)=0;
      if(resourceBytes) {
        s32 bound=mode==3?0:initialBound;
        while(expectedResources<=bound) {
          j=expectedResources;word=j%3==1?0:0x35000+(u32)j*0x100;
          *(u32 *)(expected+16+0x3C+j*4)=word;expectedResources++;
          if(j==0 && mode==1) bound=-1;
          if(j==0 && mode==2) bound=3;
        }
        *(u32 *)(expected+16+0x4C)=0x36000;
      }
      for(i=0;i<12;i++) expected[16+0x54+i]=0;
      for(i=0;i<16;i++) expected[16+0x84+i]=0;
    }
    if(copied!=(failed?0:1) || zeroed!=(failed?0:1) || resources!=expectedResources
       || trailing!=(!failed && resourceBytes?1:0)) return 3;
    for(i=0;i<512;i++) if(arena.bytes[i]!=expected[i]) return 4;
}
''')
        self.receipt('native', dict(cases=65536, actual_native32_C=True, complete_160_byte_header=True,
            canary_bytes=512, all_low16_width_patterns=True, unsigned_product_and_sum=True,
            live_resource_bound=True, optional_null_preserves_other_35_bytes=True,
            helper_null_results_preserved=True, allocator_bounded=True, hardware_gameplay=False))

    def test_08_complete_wrapper_trail_and_other_direct_callers(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        copy = functions['memcpy']
        self.assertEqual(len(copy), 11)
        reports, all_core = {}, set()
        for name in ('func_15147DA0', 'func_151DA6F8', 'func_1515C2F0', 'func_151D7830'):
            count, reached = 0, set()
            for bound, result, phase, mode in itertools.product((-1, 0, 3), (0, CREATED), (0, 8), (0, 1, 2, 5)):
                memory = fixture(bound)
                if name == 'func_15147DA0':
                    args = list(effect.arguments())
                    args[12] = OPTIONAL
                elif name == 'func_151DA6F8':
                    args = list(trail.arguments(15, 1, 1))
                    args[12] = OPTIONAL
                elif name == 'func_1515C2F0':
                    args = (REQUEST, 32, effect.DESCRIPTOR, OPTIONAL, 0x81, 0x81234580)
                    memory.update({effect.DESCRIPTOR + i: (i*7+0x87)&255 for i in range(64)})
                else:
                    args = (REQUEST,)
                    put(memory, REQUEST + 0x28, 0x12345678)
                models = []
                for core in (self.words, self.retail):
                    connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 460, 4), core))
                    connected.update(zip(range(addresses['memcpy'], addresses['memcpy'] + 44, 4), copy))
                    if name == 'func_151DA6F8':
                        connected.update(zip(range(addresses['func_15147DA0'], addresses['func_15147DA0'] + 280, 4), functions['func_15147DA0']))
                    model = CoreOracle(functions[name], memory, args, result, mode, phase,
                        addresses[name], connected=connected).run()
                    allocated = model.calls[0]
                    self.assertEqual(allocated[0], 'allocate')
                    if name == 'func_15147DA0':
                        wanted = (0x4D, args[14], (args[2]+0x48+7*0x14+0xA0)&0xFFFFFFFF, 1, args[13]&255, 1)
                        flags = (0,0,0,1,0,1)
                    elif name == 'func_151DA6F8':
                        wanted = (0x22, args[17], 0x58+(args[6]&255)*0x14+0xA0, 1, args[16]&255, 1)
                        flags = (0,0,0,1,0,1)
                    elif name == 'func_1515C2F0':
                        wanted = (0x4D, args[5], args[1]+0x40+7*0x10+0xA0, 1, args[4]&255, 1)
                        flags = (0,0,0,8,8,8)
                    else:
                        wanted = (0x4D, memory[REQUEST+1], 0x20+25*28+0xA0, 1, memory[REQUEST+0xC], 1)
                        flags = (0,0,0,13,16,16)
                    self.assertEqual(allocated[1], wanted)
                    if result:
                        self.assertEqual(bytes(model.memory[result+0x2C+i] for i in range(6)), bytes(flags))
                    if name != 'func_151D7830':
                        self.assertEqual(model.r[2], result)
                    elif result:
                        self.assertEqual(read(model.memory, REQUEST+0x28), result)
                    else:
                        self.assertEqual(read(model.memory, REQUEST+0x28), 0x12345678)
                    copies = [call for call in model.calls if call[0]=='copy']
                    self.assertEqual([call[-1] for call in copies], [] if not result else
                        [28,32] if name=='func_15147DA0' else [28,32,12] if name=='func_151DA6F8'
                        else [28,60] if name=='func_1515C2F0' else [28,28])
                    reached.update(model.visits)
                    all_core.update(model.visits & set(range(screen.ENTRY, screen.ENTRY+460,4)))
                    models.append(model)
                self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                    (models[1].r, models[1].f, models[1].memory, models[1].events))
                count += 1
            reports[name] = dict(caller_words=len(functions[name]), cases=count,
                executions=count*2, reached_words=len(reached))
        self.assertEqual(len(all_core),115)
        self.receipt('callers', dict(callers=reports, all_115_core_words=True, actual_memcpy_words=11,
            full_emitted_callers=True, remaining_allocator_resource_bzero_bounded=True,
            trail_still_61_differences=True, hardware_gameplay=False))


if __name__ == '__main__':
    unittest.main()
