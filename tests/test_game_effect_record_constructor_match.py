"""Direct effect-record match, complete caller ABI and whole linked audit."""

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
from tools.experiments import game_effect_record_constructor_candidates as screen
from tools.experiments import game_trail_effect_constructor_matching as fitting
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import public, external, outcome
from tools.tests import test_game_trail_effect_constructor_recovery as caller
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
CALLER_SOURCE = caller.SOURCE
REQUEST, DESCRIPTOR, RENDER, ALTERNATE = 0x24000, 0x25000, 0x26000, 0x27000
CREATED, PAYLOAD = caller.CREATED, caller.PAYLOAD
WIDTHS = (0, 1, 127, 128, 255, 256, 0xFFFF0001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.INSERT, '')
    assert old.count(screen.ORIGINAL) == 1
    new = old.replace('/* Non-matching placeholders', screen.INSERT + '/* Non-matching placeholders', 1).replace(
        screen.ORIGINAL, screen.SELECTED)
    current = (root / CALLER_SOURCE).read_text()
    old_caller = current.replace(screen.CALLER_SELECTED, screen.CALLER_ORIGINAL)
    assert old_caller.count(screen.CALLER_ORIGINAL) == 1
    return (old, new), (old_caller, old_caller.replace(screen.CALLER_ORIGINAL, screen.CALLER_SELECTED))


def fixture(seed=0):
    memory = caller.fixture(seed=seed)
    for base in (REQUEST, DESCRIPTOR, RENDER, ALTERNATE):
        memory.update({base + i: (i * 13 + seed * 31 + 0xA5) & 255 for i in range(-16, 512)})
    return memory


def arguments(width=0x81234580):
    return (REQUEST, DESCRIPTOR, width, width, width, width, width, width, width,
        width, width, RENDER, width, width, width)


def mutations(mode, role, result):
    if role == 'allocate' and mode == 1:
        return ((DESCRIPTOR + 4, 0x12345678, 4), (RENDER + 8, 0xFEDCBA98, 4),
            ) + (((result + 0x98, ALTERNATE, 4),) if result else ())
    if role == 'copy' and mode == 2:
        return ((result + 0x98, ALTERNATE, 4), (RENDER + 12, 0x76543210, 4))
    return ()


def mutation(memory, mode, role, result):
    for address, value, size in mutations(mode, role, result):
        put(memory, address, value, size)


def reference(memory, args, result, mode):
    memory = dict(memory)
    request, descriptor, size, *rest = args
    put(memory, request + 0x10, 1)
    expected_args = (request, (size + 0x48) & 0xFFFFFFFF, 0x14, 1, 0, 1,
        args[9], args[10], args[12], args[13] & 255, args[14])
    calls = [('allocate', expected_args)]
    mutation(memory, mode, 'allocate', result)
    if result:
        payload = read(memory, result + 0x98)
        packet = bytes(memory[descriptor + i] for i in range(32))
        calls.append(('copy', payload, packet, 32))
        for i, byte in enumerate(packet):
            put(memory, payload + i, byte, 1)
        mutation(memory, mode, 'copy', result)
        for i, value in enumerate(args[3:9]):
            put(memory, payload + 0x20 + i, value, 1)
        for i in range(8):
            put(memory, payload + 0x28 + i * 4, read(memory, args[11] + i * 4))
    return memory, calls


class EffectRecordOracle(caller.ConstructorOracle):
    def __init__(self, words, memory, args, result=CREATED, mode=0, phase=0,
            entry=screen.ENTRY, symbols=None, connected=None):
        super().__init__(words, memory, args, result, phase, entry,
            dict(screen.SYMBOLS, func_15147DA0=screen.ENTRY) if symbols is None else symbols, connected)
        self.mode = mode

    def record_call(self, target):
        if target == self.symbols['func_15147A80']:
            args = self.arguments(11)
            self.raw_calls.append(('allocate', args))
            self.calls.append(('allocate', args))
        else:
            assert target == self.symbols['memcpy'], hex(target)
            args = self.arguments(3)
            self.raw_calls.append(('copy', args))
            self.calls.append(('copy', args[0], self.packet(args[1], args[2]), args[2]))

    def hook(self, target):
        role, args = self.raw_calls[-1]
        if role == 'allocate':
            result = self.result
        else:
            destination, source, size = args
            assert 0 <= size <= 32
            for i in range(size):
                self.put(destination + i, self.get(source + i, 1), 1)
            result = destination
        if self.mode == 3:
            for i in range(11 if role == 'allocate' else 3):
                self.put(self.r[29] + i * 4, 0x76543210 + i, 4)
        for address, value, size in mutations(self.mode, role, self.result):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


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


class GameEffectRecordConstructorMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-effect-record-constructor-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>70I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            prior = json.loads((cls.root / 'conker/build/game-trail-effect-constructor-test/after.json').read_text())
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
            source, source_caller = shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == source[0]
            assert (cls.root / CALLER_SOURCE).read_text() == source_caller[0]
            baseline.write_text(json.dumps(dict(slots=slots, guards=guards, progress=progress,
                source_sha256=[hashlib.sha256(text[0].encode()).hexdigest() for text in (source, source_caller)],
                elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()), indent=2) + '\n')
            (cls.out / 'before.elf').write_bytes(elf.read_bytes())
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def compare(self, memory, args, result=CREATED, mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None):
        wanted, calls = reference(memory, args, result, mode)
        if symbols:
            calls[0] = ('allocate', calls[0][1])
        models = []
        for body in ((words,) if words is not None else (self.words, self.retail)):
            model = EffectRecordOracle(body, memory, args, result, mode, phase, entry, symbols).run()
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], result)
            self.assertEqual(external(model.memory), external(wanted))
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                (models[1].r, models[1].f, models[1].memory, models[1].events))
        return models

    def test_01_direct_complete_slot_profiles_and_word_interface(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (70, 64, 0))
        self.assertEqual((self.words, self.meta['diagnostics'], self.meta['pool_bytes']), (self.retail, '', 0))
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=70, bytes=280, frame=64, guards=0, profiles=profiles,
            word_parameters_3_through_10=True, unsigned_size_addition=True))

    def test_02_full_word_inputs_widths_live_reads_null_and_original_return(self):
        count, reached = 0, set()
        for width, mode, result, phase in itertools.product(WIDTHS, range(4), (0, CREATED), (0, 8)):
            models = self.compare(fixture(mode), arguments(width), result, mode, phase)
            reached.update(models[0].visits)
            count += 1
        for index, width in itertools.product(range(2, 15), WIDTHS):
            if index == 11:
                continue
            args = list(arguments())
            args[index] = width
            self.compare(fixture(), args)
            count += 1
        for index, byte in itertools.product(range(3, 9), range(256)):
            args = list(arguments())
            args[index] = 0x12340000 | byte
            self.compare(fixture(), args)
            count += 1
        self.assertEqual(len(reached), 70)
        self.receipt('guest', dict(cases=count, executions=count * 2, all_70_words=True,
            all_six_low_byte_outputs=True, full_fade_words_not_narrowed=True,
            live_descriptor_render_and_payload_pointer=True, saved_GP_FP=True,
            memcpy_return_ignored=True, both_SP_phases=True))

    def test_03_null_lazy_inputs_faults_and_safe_aliases(self):
        faults, aliases = 0, 0
        for mode, result, phase in itertools.product((0, 3), (0, CREATED), (0, 8)):
            memory, args = fixture(), arguments()
            complete = EffectRecordOracle(self.retail, memory, args, result, mode, phase).run()
            used = {e[1] + i for e in public(complete.events) if e[0] in ('R', 'W') for i in range(e[2])}
            for address in sorted(used):
                missing = dict(memory)
                del missing[address]
                models = [EffectRecordOracle(body, missing, args, result, mode, phase) for body in (self.words, self.retail)]
                self.assertEqual([outcome(model) for model in models], [False, False])
                self.assertEqual((external(models[0].memory), public(models[0].events), models[0].calls),
                    (external(models[1].memory), public(models[1].events), models[1].calls))
                faults += 1
            if not result:
                lazy = {a: v for a, v in memory.items() if STACK - 0x600 <= a < STACK + 0x160
                    or REQUEST + 0x10 <= a < REQUEST + 0x14}
                self.compare(lazy, args, 0, mode, phase)
        for desc, render, phase in itertools.product((DESCRIPTOR, REQUEST), (RENDER, DESCRIPTOR, PAYLOAD + 0x28), (0, 8)):
            args = list(arguments())
            args[1], args[11] = desc, render
            self.compare(fixture(), args, phase=phase)
            aliases += 1
        self.receipt('faults', dict(missing_public_byte_pairs=faults, safe_aliases=aliases,
            lazy_null_inputs=True, emitted_fault_prefixes_only=True, hardware_traps=False,
            portable_invalid_C=False))

    def test_04_complete_source_controls_and_effective_compiled_negatives(self):
        variants = list(screen.candidates()) + [
            ('negative-state', screen.SELECTED.replace('request + 0x10) = 1', 'request + 0x10) = 0')),
            ('negative-size', screen.SELECTED.replace('+ 0x48, 0x14', '+ 0x40, 0x14')),
            ('negative-fade-word', screen.SELECTED.replace('        fadeFlag, fadeAlpha,', '        (u8)fadeFlag, fadeAlpha,')),
            ('negative-copy', screen.SELECTED.replace('memcpy(payload, descriptor, 32);', 'memcpy(payload, descriptor, 24);')),
            ('negative-return', screen.SELECTED.replace('    return created;', '    return payload;'))]
        records = []
        for name, body in variants:
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            records.append(meta)
            results = []
            for width, result, mode in itertools.product((0x81234580, 0xFFFFFFFF), (0, CREATED), (0, 1, 2)):
                memory, args = fixture(), arguments(width)
                model = EffectRecordOracle(words, memory, args, result, mode).run()
                wanted, calls = reference(memory, args, result, mode)
                results.append((external(model.memory), model.calls, model.r[2]) == (external(wanted), calls, result))
            self.assertEqual(all(results), not (name.startswith('negative-') or name == 'narrow1'), name)
        self.receipt('forms', dict(forms=records, cases_per_form=12, effective_compiled_negatives=6))

    def owner_pair(self, texts, prefix):
        objects, warnings = [], []
        for name, source in zip(('baseline', 'selected'), texts):
            stem = prefix + '-' + name
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
        return objects, len(current), len(warnings[0])

    def test_05_two_owners_unchanged_caller_actual_padding_and_rebases(self):
        source, caller_source = shapes(self.root)
        objects, count, warnings = self.owner_pair(source, 'owner')
        caller_objects, caller_count, caller_warnings = self.owner_pair(caller_source, 'caller-owner')
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
        begin = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), begin)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[begin:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[begin:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 280)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        cases = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            defs = dict(screen.SYMBOLS, func_15147DA0=entry)
            if variant:
                for i, name in enumerate(screen.SYMBOLS):
                    defs[name] = (entry & 0xF0000000) + 0x208000 + i * 0x100
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % (name, defs[name]) for name in screen.SYMBOLS], '-o', str(elf), str(obj)],
                check=True, capture_output=True)
            words = list(struct.unpack_from('>70I', sections(elf)['.text'][1]))
            if not variant:
                self.assertEqual(words, self.retail)
            for width, result, mode, phase in itertools.product((0x81234580, 0xFFFFFFFF), (0, CREATED), range(4), (0, 8)):
                self.compare(fixture(), arguments(width), result, mode, phase, words, entry, defs)
                cases += 1
        self.receipt('owner', dict(neighbors=count - 1, caller_functions=caller_count,
            pools_and_relative_relocations_unchanged=True, diagnostics=[warnings, caller_warnings],
            caller_prototype_only_and_all_its_bytes_unchanged=True, actual_padding_bytes=280,
            guards=0, independent_links=4, cases=cases))

    def test_06_whole_linked_only_target_and_symbol_size_change(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        source, caller_source = shapes(self.root)
        self.assertEqual([hashlib.sha256(text[0].encode()).hexdigest() for text in (source, caller_source)], baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == source[1]
        self.assertEqual((self.root / CALLER_SOURCE).read_text(), caller_source[int(installed)])
        elf = self.root / 'conker/build/conker.us.elf'
        functions, _, addresses = load_elf_functions(str(elf), 'mips-linux-gnu-objdump')
        slots = {n: dict(address=addresses[n], words=len(w), sha256=hashlib.sha256(
            struct.pack('>%dI' % len(w), *w)).hexdigest()) for n, w in functions.items()}
        expected = dict(baseline['slots'])
        data = bytearray((self.out / 'before.elf').read_bytes())
        if installed:
            expected[screen.FUNCTION] = dict(address=screen.ENTRY, words=70,
                sha256=hashlib.sha256(struct.pack('>70I', *self.retail)).hexdigest())
            offset = caller.elf_slot_offset(data, screen.ENTRY, 280)
            data[offset:offset + 280] = struct.pack('>70I', *self.retail)
            offset = symbol_size_offset(data)
            self.assertEqual(struct.unpack_from('>I', data, offset)[0], 12)
            struct.pack_into('>I', data, offset, 280)
            self.assertEqual(functions[screen.FUNCTION], self.retail)
        self.assertEqual(slots, expected)
        self.assertEqual(elf.read_bytes(), data)
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        for name in ('retail_word_patches.us.csv', 'progress.csv'):
            self.assertEqual((self.root / 'conker' / name).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        self.receipt('linked', dict(installed=installed, symbols=len(slots), target_words=70,
            full_ELF_except_target_and_its_symbol_size_unchanged=True, symbol_size_change=[12, 280] if installed else None,
            guards=11475, progress_unchanged=True, caller_unchanged=True,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed:
            self.receipt('after', dict(slots=slots, guards=baseline['guards'], progress=baseline['progress']))

    def test_07_native32_complete_word_transport_live_mutations_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
#define NULL ((void *)0)
''' + screen.RENDER + r'''
static union { u32 align;u8 b[512]; } actor,storage,alternate,request,descriptor,render;
static u8 *created=actor.b+16,*payload=storage.b+16,*other=alternate.b+16;
static u32 input;static int mode,failed,calls,copies,error;
static void *memcpy(void *d,const void *s,unsigned int n) {
    unsigned int i;u8 *out=d;const u8 *in=s;
    if(copies++ || n!=32 || d!=(mode==1?other:payload) || s!=descriptor.b+16) error=1;
    for(i=0;i<n;i++) out[i]=in[i];
    if(mode==2) { *(u8 **)(created+0x98)=other;*(u32 *)(render.b+16+12)=0x76543210; }
    return d;
}
static u8 *func_15147A80(void *r,s32 size,s32 kind,s32 active,s32 zero,s32 one,
    s32 ff,s32 fa,s32 extra,u8 channel,s32 context) {
    if(calls++ || r!=request.b+16 || *(u32 *)(request.b+16+0x10)!=1
       || (u32)size!=input+0x48U || kind!=0x14 || active!=1 || zero || one!=1
       || (u32)ff!=input || (u32)fa!=input || (u32)extra!=input
       || channel!=(u8)input || (u32)context!=input) error=2;
    if(mode==1) { *(u32 *)(descriptor.b+16+4)=0x12345678;
      *(u32 *)(render.b+16+8)=0xFEDCBA98;*(u8 **)(created+0x98)=other; }
    return failed?NULL:created;
}
static void initialize(void) {
    int i;for(i=0;i<512;i++) {
      actor.b[i]=(u8)(i*13+0xA5);storage.b[i]=(u8)(i*17+0x87);alternate.b[i]=(u8)(i*7+0x81);
      request.b[i]=(u8)(i*19+0x89);descriptor.b[i]=(u8)(i*11+0x85);render.b[i]=(u8)(i*5+0x8F);
    } *(u8 **)(created+0x98)=payload;calls=copies=error=0;
}
''' + screen.SELECTED + '\n'
        self.run_host(r'''
u32 low;int i;u8 before[512],otherBefore[512],expected[512];u8 *result,*chosen;
for(low=0;low<65536;low++) {
    input=0xFFFF0000|low;mode=low%3;failed=(low>>1)&1;initialize();
    for(i=0;i<512;i++) { before[i]=storage.b[i];otherBefore[i]=alternate.b[i]; }
    result=func_15147DA0(request.b+16,descriptor.b+16,(s32)input,(s32)input,
        (s32)input,(s32)input,(s32)input,(s32)input,(s32)input,(s32)input,
        (s32)input,render.b+16,(s32)input,(u8)input,(s32)input);
    if(error || calls!=1 || copies!=(failed?0:1) || result!=(failed?NULL:created)) return 1;
    chosen=mode==1?alternate.b:storage.b;
    for(i=0;i<512;i++) expected[i]=mode==1?otherBefore[i]:before[i];
    if(!failed) {
      for(i=0;i<32;i++) expected[16+i]=descriptor.b[16+i];
      for(i=0;i<6;i++) expected[16+0x20+i]=(u8)input;
      for(i=0;i<32;i++) expected[16+0x28+i]=render.b[16+i];
    }
    for(i=0;i<512;i++) {
      if(chosen[i]!=expected[i]) return 2;
      if((mode==1?storage.b[i]:alternate.b[i])!=(mode==1?before[i]:otherBefore[i])) return 3;
    }
    if(*(u32 *)(request.b+16+0x10)!=1) return 4;
}
''')
        self.receipt('native', dict(cases=65536, actual_native32_C=True,
            full_word_high_bits=True, all_six_low_byte_outputs=True, unsigned_size_wrap=True,
            live_descriptor_render_reads=True, captured_payload_pointer=True,
            two_512_byte_canary_regions=True, allocator_bounded=True, hardware_gameplay=False))

    def test_08_complete_banked_caller_and_actual_memcpy(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        main = functions[fitting.recovery.FUNCTION]
        copy = functions['memcpy']
        self.assertEqual((addresses[fitting.recovery.FUNCTION], len(main), addresses['memcpy'], len(copy)),
            (fitting.recovery.ENTRY, 144, screen.SYMBOLS['memcpy'], 11))
        count, reached = 0, set()
        for selector, tables, opaque, fade, result, phase in itertools.product((0, 15), range(4), (0, 1),
                (0, 1), (0, CREATED), (0, 8)):
            memory, args = caller.fixture(selector, tables), caller.arguments(selector, opaque, fade)
            call, payload = caller.expected(memory, args)
            models = []
            for body in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 280, 4), body))
                connected.update(zip(range(addresses['memcpy'], addresses['memcpy'] + 44, 4), copy))
                model = caller.ConstructorOracle(main, memory, args, result, phase, connected=connected).run()
                self.assertEqual(model.r[2], result)
                self.assertEqual(model.calls[0], call)
                self.assertEqual(model.calls[1], ('allocate', call[1],
                    (0x58, 0x14, 1, 0, 1, 2 if fade else 0, 255 if fade else 0, args[12], args[16], args[17])))
                if result:
                    self.assertEqual(model.calls[2:], [('copy', PAYLOAD, call[2], 32), ('copy', PAYLOAD + 0x48, payload, 12)])
                else:
                    self.assertEqual(len(model.calls), 2)
                reached.update(model.visits)
                models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].memory, models[0].events),
                (models[1].r, models[1].f, models[1].memory, models[1].events))
            count += 1
        self.assertEqual(len(reached), 225)
        self.receipt('caller', dict(cases=count, executions=count * 2, complete_caller_words=144,
            complete_callee_words=70, memcpy_words=11, all_225_words=True,
            allocation_core_bounded=True, caller_remains_61_differences=True, hardware_gameplay=False))

    def test_09_constructor_fitting_forms_defined_records_only(self):
        records = []
        output = self.root / 'conker/build/game-trail-effect-constructor-matching'
        for name, body, types in fitting.candidates():
            source = output / (name + '.c')
            expected_source = '#include <ultra64.h>\n' + types + fitting.recovery.DECLARATIONS + body + '\n'
            self.assertEqual(source.read_text(), expected_source, name)
            _, functions, _ = parse_object(output / (name + '.o'))
            fn = functions[fitting.recovery.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (fn['size'] // 4), sections(output / (name + '.elf'))['.text'][1], fn['value']))
            end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
            self.assertFalse(any(words[end:]))
            words = words[:end]
            differences = sum(a != b for a, b in itertools.zip_longest(words,
                struct.unpack_from('>144I', (self.root / 'conker/conker.us.bin').read_bytes(), fitting.recovery.ROM), fillvalue=0))
            for tables, opaque, fade, result in itertools.product(range(4), (0, 1), (0, 1), (0, CREATED)):
                memory, args = caller.fixture(15, tables), caller.arguments(15, opaque, fade)
                model = caller.ConstructorOracle(words, memory, args, result).run()
                call, payload = caller.expected(memory, args)
                self.assertEqual(model.calls, [call] + ([('copy', PAYLOAD + 0x48, payload, 12)] if result else []), name)
                self.assertEqual(model.r[2], result)
            records.append(dict(name=name, words=end, frame=(-words[0]) & 65535, differences=differences))
        self.receipt('caller-fitting', dict(complete_forms=len(records), cases_per_form=32,
            cached_sources_exact=True, defined_records_and_return_qualified=True, installed=False,
            no_added_tail_or_guards=True, measurements=records))


if __name__ == '__main__':
    unittest.main()
