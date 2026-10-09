"""Complete payload callbacks, fade, position and closed return-lifetime guards."""

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

from tools.check_game_data_layout import audit_layout, load_section
from tools.experiments import game_payload_callback_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_graphics_dispatch_match import DispatchOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import external, public, outcome
from tools.tests import test_game_actor_timer_callbacks_match as prior
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
ACTOR, PAYLOAD, ALTERNATE, RECORDS, CALLBACK = 0x20000, 0x21000, 0x22000, 0x30000, 0x15001000
TABLES = tuple(screen.SYMBOLS)


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATIONS + '\n', '')
    assert old.count(screen.ORIGINAL) == 1
    new = old.replace('/* Non-matching placeholders', screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
    return old, new


def fixture(selectors=(1, 1, 1), timer=1, limit=5, scale=3, alpha=255, flags=0x40,
            active=1, cursor=0, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, count in ((ACTOR, 256), (PAYLOAD, 128), (ALTERNATE, 128)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(count)})
    memory.update({RECORDS - 2560 + i: ((0x10200000 + i // 4) >> ((3 - i % 4) * 8)) & 255 for i in range(10240)})
    put(memory, ACTOR + 0x98, PAYLOAD)
    put(memory, ACTOR + 0x94, RECORDS)
    put(memory, ACTOR + 0x1C, timer, 2)
    put(memory, ACTOR + 0x2C, active, 1)
    put(memory, ACTOR + 0x2D, cursor, 1)
    for i, selector in enumerate(selectors):
        put(memory, PAYLOAD + 0x20 + i, selector, 1)
    for offset, value, size in ((0x18, flags, 1), (0x1B, alpha, 1), (0x1C, limit, 2), (0x1E, scale, 2)):
        put(memory, PAYLOAD + offset, value, size)
    # Full-byte synthetic selectors can index adjacent real tables. Shared
    # addresses have one consistent target, rather than conflicting fixtures.
    for stage, name in enumerate(TABLES):
        for i in range(256):
            put(memory, symbols[name] + i * 4, CALLBACK + stage * 0x1000 + i * 4)
    for i in range(-128, 0):
        put(memory, symbols[TABLES[0]] + i * 4, CALLBACK + 0x2000 + (i & 127) * 4)
    return memory


def role(target):
    stage = (target - CALLBACK) // 0x1000
    assert 0 <= stage < 3, hex(target)
    return stage


def actions(stage, mode, symbols):
    if stage == 0:
        return {0: (), 1: ((PAYLOAD + 0x21, 0, 1),),
            2: ((PAYLOAD + 0x21, 255, 1),),
            3: ((ACTOR + 0x98, ALTERNATE, 4),),
            4: ((PAYLOAD + 0x18, 0, 1),),
            5: ((PAYLOAD + 0x1C, 0x7FFF, 2), (PAYLOAD + 0x1E, 0xFFFF, 2)),
            6: ((symbols[TABLES[1]] + 4, CALLBACK + 0x1000 + 28, 4),),
            7: (), 8: ((ACTOR + 0x2D, 0x80, 1),)}[mode]
    if stage == 1:
        return {0: (), 1: ((ACTOR + 0x2C, 0, 1),),
            2: ((ACTOR + 0x2C, 0x80, 1),), 3: ((ACTOR + 0x98, ALTERNATE, 4),),
            4: ((PAYLOAD + 0x22, 0, 1),), 5: ((PAYLOAD + 0x1B, 1, 1),),
            6: ((symbols[TABLES[2]] + 4, CALLBACK + 0x2000 + 32, 4),),
            7: (), 8: ((ACTOR + 0x94, RECORDS + 20, 4),)}[mode]
    return ((ACTOR + 0x2C, 0, 1),) if mode == 1 else ()


def reference(memory, results=(1, 1, 1), mode=0, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory, calls = dict(memory), []
    payload = read(memory, ACTOR + 0x98)
    failed = False
    for stage in range(2):
        selector = read(memory, payload + 0x20 + stage, 1)
        if selector and not failed:
            target = read(memory, symbols[TABLES[stage]] + selector * 4)
            identity = role(target)
            calls.append((target, (ACTOR,)))
            for address, value, size in actions(identity, mode, symbols):
                put(memory, address, value, size)
            failed = results[identity] == 0
    if read(memory, payload + 0x18, 1) & 0x40 and not failed:
        timer = prior.signed(read(memory, ACTOR + 0x1C, 2), 16)
        if timer < prior.signed(read(memory, payload + 0x1C, 2), 16):
            value = timer * prior.signed(read(memory, payload + 0x1E, 2), 16)
            if value < read(memory, payload + 0x1B, 1):
                put(memory, payload + 0x1B, value, 1)
    success = int(not failed)
    if failed:
        selector = read(memory, payload + 0x22, 1)
        if selector:
            target = read(memory, symbols[TABLES[2]] + selector * 4)
            calls.append((target, (ACTOR,)))
            for address, value, size in actions(role(target), mode, symbols):
                put(memory, address, value, size)
    records = read(memory, ACTOR + 0x94)
    if prior.signed(read(memory, ACTOR + 0x2C, 1), 8) > 0:
        source = records + prior.signed(read(memory, ACTOR + 0x2D, 1), 8) * 20
        for i in range(3):
            put(memory, ACTOR + 0x54 + i * 4, read(memory, source + i * 4))
    else:
        for i in range(3):
            put(memory, ACTOR + 0x54 + i * 4, 0)
    return memory, calls, success


class PayloadOracle(DispatchOracle):
    def __init__(self, words, memory, results=(1, 1, 1), mode=0, phase=0, entry=screen.ENTRY, symbols=None):
        TriangleOracle.__init__(self, words, memory, arguments=(ACTOR,), phase=phase, entry=entry)
        self.results, self.mode = results, mode
        self.symbols = screen.SYMBOLS if symbols is None else symbols

    def record_call(self, target):
        self.calls.append((target, self.arguments(1)))

    def hook(self, target):
        stage = role(target)
        for address, value, size in actions(stage, self.mode, self.symbols):
            self.put(address, value, size)
        if self.mode == 7:
            for i in range(4):
                self.put(self.r[29] + i * 4, 0x76540000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.results[stage]


class GamePayloadCallbackUpdateMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-payload-callback-update-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>97I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        if not (cls.out / 'baseline.json').exists():
            old, _ = shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            slots, _ = prior.slot_records(cls.root)
            assert len(slots) == 6058
            before = json.loads((cls.root / 'conker/build/game-actor-timer-callbacks-test/after.json').read_text())
            assert slots == before['slots']
            assert slots[screen.FUNCTION]['words'] == 97
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes()
            (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())
            (cls.out / 'baseline.json').write_text(json.dumps(dict(slots=slots,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, results=(1, 1, 1), mode=0, phase=0, words=None, entry=screen.ENTRY, symbols=None):
        wanted, calls, returned = reference(memory, results, mode, symbols)
        models = []
        for body in ((words,) if words is not None else (self.raw, self.words, self.retail)):
            model = PayloadOracle(body, memory, results, mode, phase, entry, symbols).run()
            self.assertEqual((model.calls, model.r[2], external(model.memory)), (calls, returned, external(wanted)))
            models.append(model)
        if words is None:
            self.assertEqual(public(models[0].events), public(models[1].events))
            self.assertEqual((models[1].r, models[1].f, models[1].events, models[1].memory),
                (models[2].r, models[2].f, models[2].events, models[2].memory))
        return models

    def test_01_complete_slot_guards_profiles_and_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (97, 32, 25))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual({i for i, (a, b) in enumerate(zip(self.raw, self.words)) if a != b}, {i for i, _, _ in screen.PATCHES})
        for i, _, _ in screen.PATCHES:
            stale = list(self.raw); stale[i] ^= 1
            with self.assertRaises(AssertionError): screen.normalize(stale)
        control = list(self.raw); control[5] ^= 1
        normalized = screen.normalize(control)
        self.assertEqual(normalized[5], control[5])
        self.assertEqual({i for i, (a, b) in enumerate(zip(control, normalized)) if a != b}, {i for i, _, _ in screen.PATCHES})
        relocs = [r for items in self.meta['relocations'].values() for r in items]
        self.assertEqual(set(relocs), {(kind, symbol) for kind in ('R_MIPS_HI16', 'R_MIPS_LO16') for symbol in TABLES})
        self.assertTrue(all(offset // 4 not in {i for i, _, _ in screen.PATCHES} for offset in self.meta['relocations']))
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=97, bytes=388, raw_frame=32, retail_frame=48, guards=25, profiles=profiles))

    def test_02_boundaries_live_mutations_and_full_reachable_body(self):
        visited, count = set(), 0
        for stage, selector, mask, phase in itertools.product(range(3), range(256), range(4), (0, 8)):
            selectors = [1, 1, 1]; selectors[stage] = selector
            results = tuple(0 if mask & (1 << i) else 0x80000001 for i in range(2)) + (0xFFFFFFFF,)
            visited.update(self.compare(fixture(selectors=selectors), results, phase=phase)[1].visits)
            count += 1
        for timer, limit, scale, alpha, active, cursor in itertools.product(
                (0, 1, 0x7FFF, 0x8000, 0xFFFF), (0, 1, 0x7FFF, 0x8000),
                (0, 1, 0x7FFF, 0x8000, 0xFFFF), (0, 1, 255), (0, 1, 0x80), (0, 0x7F, 0x80, 0xFF)):
            visited.update(self.compare(fixture(timer=timer, limit=limit, scale=scale, alpha=alpha, active=active, cursor=cursor))[1].visits)
            count += 1
        for mask, mode, phase, value in itertools.product(range(4), range(9), (0, 8), (0x10000, 0x80000000, 0xFFFFFFFF)):
            results = tuple(0 if mask & (1 << i) else value for i in range(2)) + (value,)
            visited.update(self.compare(fixture(), results, mode, phase)[1].visits)
            count += 1
        for flags in range(256):
            visited.update(self.compare(fixture(flags=flags), phase=8)[1].visits)
            count += 1
        reachable = set(range(screen.ENTRY, screen.ENTRY + 388, 4)) - {screen.ENTRY + 85 * 4}
        self.assertEqual(visited, reachable)
        self.receipt('guest', dict(cases=count, executions=count * 3, reachable_words=len(visited),
            raw_public_and_normalized_full_state_agree=True, all_selector_bytes=True,
            captured_payload_live_selectors=True, signed_timer_scale_active_cursor=True,
            four_outgoing_home_clobbers=True, unreachable_word=85))

    def test_03_missing_public_bytes_and_lazy_fields(self):
        count = 0
        for selectors, flags, active, results in (
                ((0, 0, 0), 0, 0, (1, 1, 1)), ((1, 1, 1), 0x40, 1, (1, 1, 1)),
                ((1, 1, 1), 0x40, 1, (0, 1, 1)), ((0, 1, 0), 0x40, 0x80, (1, 0, 1))):
            memory = fixture(selectors=selectors, flags=flags, active=active)
            touched = public(PayloadOracle(self.words, memory, results).run().events)
            addresses = {address + i for _, address, size, _ in touched for i in range(size)}
            for address in sorted(addresses):
                missing = dict(memory); del missing[address]
                models = [PayloadOracle(body, missing, results) for body in (self.words, self.retail)]
                self.assertEqual(outcome(models[0]), outcome(models[1]))
                self.assertEqual((models[0].events, models[0].memory), (models[1].events, models[1].memory))
                count += 1
        memory = fixture(selectors=(0, 0, 0), flags=0, active=0)
        for address in (ACTOR + 0x1C, PAYLOAD + 0x1C, PAYLOAD + 0x1E, ACTOR + 0x2D, RECORDS):
            missing = dict(memory); del missing[address]
            self.compare(missing)
        self.receipt('faults', dict(missing_byte_pairs=count, emitted_order_not_portable_fault_semantics=True,
            private_frame_aliases_not_claimed=True, lazy_timer_fade_cursor_and_record_contents=True))

    def test_04_complete_forms_and_effective_negatives(self):
        negatives = {
            'unsigned-timer': screen.SELECTED.replace('value = *(s16 *)', 'value = *(u16 *)'),
            'unsigned-active': screen.SELECTED.replace('*(s8 *)(actor + 0x2C)', 'actor[0x2C]'),
            'unsigned-cursor': screen.SELECTED.replace('*(s8 *)(actor + 0x2D)', 'actor[0x2D]'),
            'ignored-first-failure': screen.SELECTED.replace('D_8008A3E0[selector](actor) == 0', 'D_8008A3E0[selector](actor) == 7'),
            'reloaded-payload': screen.SELECTED.replace('    selector = payload[0x21];', '    payload = *(u8 **)(actor + 0x98);\n    selector = payload[0x21];'),
            'third-result-return': screen.SELECTED.replace('            D_8008A42C[selector](actor);', '            success = D_8008A42C[selector](actor);'),
        }
        samples = [(fixture(timer=0xFFFF), (1, 1, 1), 0), (fixture(active=0x80), (1, 1, 1), 0),
            (fixture(cursor=0xFF), (1, 1, 1), 0), (fixture(), (0, 1, 0x7F), 0),
            (fixture(), (1, 1, 1), 3), (fixture(), (1, 0, 0x7F), 7),
            (fixture(selectors=(128, 1, 1)), (1, 1, 0), 0)]
        records = []
        for name, body in [*screen.candidates(), *negatives.items()]:
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            differences = 0
            for memory, results, mode in samples:
                model = PayloadOracle(words, memory, results, mode).run()
                wanted, calls, returned = reference(memory, results, mode)
                differences += (model.calls, model.r[2], external(model.memory)) != (calls, returned, external(wanted))
            self.assertEqual(bool(differences), name in negatives or name == 'selector-s8', name)
            records.append(dict(meta, semantic_differences=differences))
        self.receipt('forms', dict(compiled_complete_forms=len(records), effective_negatives=[*negatives, 'selector-s8'],
            samples_per_form=len(samples), records=records))

    def test_05_owner_postprocessing_neighbors_padding_and_rebases(self):
        objects, warnings = [], []
        for name, text in zip(('baseline', 'selected'), shapes(self.root)):
            obj, warning = compile_owner(self.root, self.out, text, 'owner-' + name)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj); warnings.append(warning)
        self.assertEqual(warnings[0], warnings[1])
        old, before, old_rel = parse_object(objects[0]); text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), before.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION: continue
            prev = before[name]
            self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']]), name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prev['value']: r for o, r in old_rel.items() if prev['value'] <= o < prev['value'] + prev['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        guard_file = self.out / 'candidate-guards.csv'
        with (self.out / 'before-retail_word_patches.us.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        with guard_file.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows + screen.guard_rows())
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s', word_patches_path=guard_file, filename='generated_175250')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('\n', assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)) + 1
        self.assertNotIn('.space', assembly[start:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 388)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            symbols = screen.SYMBOLS if not variant else {name: (0x80007FF0, 0x80008000, 0x8000FFF0)[variant - 1] + i * 0x1000 for i, name in enumerate(TABLES)}
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>97I', sections(elf)['.text'][1]))
            if not variant: self.assertEqual(words, self.retail)
            for mask, mode, phase in itertools.product(range(4), range(9), (0, 8)):
                self.compare(fixture(symbols=symbols), tuple(0 if mask & (1 << i) else 0x80000000 for i in range(2)) + (1,), mode, phase, words, entry, symbols)
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=len(warnings[0]),
            pools_and_relative_relocations_unchanged=True, complete_asm_postprocessing=True,
            actual_padding_bytes=388, guards=25, independent_links=4, cases=count))

    def test_06_whole_ELF_identical_guards_append_and_one_conversion_row(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, new = shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == new
        slots, functions = prior.slot_records(self.root)
        self.assertEqual(slots, baseline['slots'])
        self.assertEqual(functions[screen.FUNCTION], self.retail)
        elf = self.root / 'conker/build/conker.us.elf'
        self.assertEqual(elf.read_bytes(), (self.out / 'before.elf').read_bytes())
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        with (self.out / 'before-progress.csv').open(newline='') as stream: progress = list(csv.DictReader(stream))
        with (self.root / 'conker/progress.csv').open(newline='') as stream: after = list(csv.DictReader(stream))
        expected = [dict(row, language='c') if installed and row['function'] == screen.FUNCTION else row for row in progress]
        self.assertEqual(after, expected)
        before = (self.out / 'before-retail_word_patches.us.csv').read_bytes()
        current = (self.root / 'conker/retail_word_patches.us.csv').read_bytes()
        self.assertTrue(current.startswith(before))
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream: guards = list(csv.DictReader(stream))
        with (self.out / 'before-retail_word_patches.us.csv').open(newline='') as stream: old_guards = list(csv.DictReader(stream))
        self.assertEqual(guards, old_guards + (screen.guard_rows() if installed else []))
        self.receipt('linked', dict(installed=installed, symbols=len(slots), full_ELF_byte_identical=True,
            guards=len(guards), conversion_changes=1 if installed else 0, elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed: self.receipt('after', dict(slots=slots, guards=guards, progress=after))

    def test_07_actual_native32_all_timer_patterns_and_selector_bytes(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed char s8;
typedef unsigned short u16;typedef signed short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
''' + screen.DECLARATIONS + r'''
static union { u32 align;u8 b[256]; } actor,wanted;
static union { u32 align;u8 b[128]; } payload,wantedPayload,alternate;
static u32 records[3840];
static u32 results[3];static int logCount,wantCount,logStage[3],wantStage[3],mode,error;
s32 (*D_8008A3E0[256])(u8 *);
s32 (*D_8008A3F8[256])(u8 *);
s32 (*D_8008A42C[256])(u8 *);
static void change(u8 *p,int stage) {
    u8 *q=p==actor.b?payload.b:wantedPayload.b;
    if(stage==0) {
        if(mode==1) q[0x21]=0;
        if(mode==2) q[0x21]=255;
        if(mode==3) *(u8 **)(p+0x98)=alternate.b;
        if(mode==4) q[0x18]=0;
        if(mode==5) {*(u16 *)(q+0x1C)=0x7FFF;*(u16 *)(q+0x1E)=0xFFFF;}
        if(mode==8) p[0x2D]=0x80;
    } else if(stage==1) {
        if(mode==1) p[0x2C]=0;
        if(mode==2) p[0x2C]=0x80;
        if(mode==3) *(u8 **)(p+0x98)=alternate.b;
        if(mode==4) q[0x22]=0;
        if(mode==5) q[0x1B]=1;
        if(mode==8) *(u32 **)(p+0x94)=records+1285;
    } else if(mode==1) p[0x2C]=0;
}
static s32 called(u8 *p,int stage) {
    if(p!=actor.b || logCount>=3) {error=1;return 0;}
    logStage[logCount++]=stage;change(p,stage);return (s32)results[stage];
}
static s32 first(u8 *p) {return called(p,0);}
static s32 second(u8 *p) {return called(p,1);}
static s32 third(u8 *p) {return called(p,2);}
static int model(void) {
    u8 *p=wanted.b,*q=wantedPayload.b;int failed=0,stage,selector,i,success,timer,value;
    for(stage=0;stage<2;stage++) {
        selector=q[0x20+stage];
        if(selector && !failed) {wantStage[wantCount++]=stage;change(p,stage);failed=results[stage]==0;}
    }
    if((q[0x18]&0x40) && !failed) {
        timer=(s16)*(u16 *)(p+0x1C);
        if(timer<(s16)*(u16 *)(q+0x1C)) {
            value=timer*(s16)*(u16 *)(q+0x1E);
            if(value<q[0x1B]) q[0x1B]=(u8)value;
        }
    }
    success=!failed;
    if(failed && q[0x22]) {wantStage[wantCount++]=2;change(p,2);}
    if((s8)p[0x2C]>0) {
        u32 *position=*(u32 **)(p+0x94)+(int)(s8)p[0x2D]*5;
        for(i=0;i<3;i++) *(u32 *)(p+0x54+i*4)=position[i];
    } else for(i=0;i<3;i++) *(u32 *)(p+0x54+i*4)=0;
    return success;
}
''' + screen.SELECTED + r'''
static int check(u16 timer,u16 limit,u16 scale,u8 active,u8 cursor,int a,int b,int c,int mask,int changeMode) {
    int i,result,expected;
    for(i=0;i<256;i++) actor.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<128;i++) payload.b[i]=(u8)(i*17+0xA5);
    *(u8 **)(actor.b+0x98)=payload.b;*(u32 **)(actor.b+0x94)=records+1280;
    *(u16 *)(actor.b+0x1C)=timer;actor.b[0x2C]=active;actor.b[0x2D]=cursor;
    payload.b[0x20]=(u8)a;payload.b[0x21]=(u8)b;payload.b[0x22]=(u8)c;
    payload.b[0x18]=0x40;payload.b[0x1B]=255;
    *(u16 *)(payload.b+0x1C)=limit;*(u16 *)(payload.b+0x1E)=scale;
    for(i=0;i<256;i++) wanted.b[i]=actor.b[i];
    for(i=0;i<128;i++) wantedPayload.b[i]=payload.b[i];
    for(i=0;i<3;i++) results[i]=(mask&(1<<i))?0:0x80000001u+(u32)i;
    mode=changeMode;logCount=wantCount=error=0;
    expected=model();result=func_15147EB8(actor.b);
    if(error || result!=expected || logCount!=wantCount) return 1;
    for(i=0;i<logCount;i++) if(logStage[i]!=wantStage[i]) return 2;
    for(i=0;i<256;i++) if(actor.b[i]!=wanted.b[i]) return 3;
    for(i=0;i<128;i++) if(payload.b[i]!=wantedPayload.b[i]) return 4;
    return 0;
}
'''
        self.run_host(r'''
static u16 scales[]={0,1,0x7FFF,0x8000,0xFFFF};
u32 pattern;int i,j,stage,selectors[3];
for(i=0;i<3840;i++) records[i]=(u32)i*0x10300401u;
for(i=0;i<256;i++) {D_8008A3E0[i]=first;D_8008A3F8[i]=second;D_8008A42C[i]=third;}
for(pattern=0;pattern<65536;pattern++) for(j=0;j<5;j++)
    if(check((u16)pattern,0x7FFF,scales[j],(u8)(pattern&1),(u8)pattern,1,1,1,(int)(pattern>>4)&3,(int)(pattern%6))) return 1;
for(stage=0;stage<3;stage++) for(i=0;i<256;i++) {
    selectors[0]=selectors[1]=selectors[2]=1;selectors[stage]=i;
    if(check(0xFFFF,0x7FFF,1,0x80,0xFF,selectors[0],selectors[1],selectors[2],stage==2?1:0,0)) return 2;
}
''')
        self.receipt('native', dict(cases=65536 * 5 + 768, all_timer_patterns=True,
            signed_scale_active_cursor=True, all_three_selector_bytes=True,
            actual_C_32_bit_pointers=True, actor_canary_bytes=256, payload_canary_bytes=128,
            callback_fixtures_not_hardware_or_gameplay_acceptance=True))

    def test_08_connected_retail_timer_updater_and_actual_first_table_slot(self):
        elf = self.root / 'conker/build/conker.us.elf'
        base, data = load_section(elf, '.game_data')
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A204 - base)[0], screen.ENTRY)
        _, functions = prior.slot_records(self.root)
        outer = functions[prior.screen.FUNCTION]
        self.assertEqual(outer, list(struct.unpack_from('>100I', (self.root / 'conker/conker.us.bin').read_bytes(), prior.screen.ROM)))

        class ConnectedOracle(PayloadOracle):
            def __init__(model, child, memory, results, mode, phase):
                TriangleOracle.__init__(model, outer, memory, arguments=(ACTOR,), phase=phase,
                    entry=prior.screen.ENTRY, connected={screen.ENTRY + i * 4: word for i, word in enumerate(child)})
                model.results, model.mode, model.symbols = results, mode, screen.SYMBOLS

            def record_call(model, target):
                model.calls.append((target, model.arguments(1)))

            def hook(model, target):
                if target == prior.screen.SYMBOLS['func_1516972C']:
                    model.put(ACTOR + 0x50, 0xDDDDDDDD, 4)
                    for register in (1, 2, 3, *range(4, 16), 24, 25):
                        model.r[register] = 0xA5000000 + register
                    model.r[2] = 0xBEEF1234
                    model.f[:20] = [0xA5000000 + i for i in range(20)]
                else:
                    super().hook(target)

        count = 0
        for mask, mode, phase in itertools.product(range(4), range(9), (0, 8)):
            results = tuple(0 if mask & (1 << i) else 0x80000000 for i in range(2)) + (0xFFFFFFFF,)
            memory = fixture()
            put(memory, ACTOR + 0x1E, 0, 2)
            for address, value, size in ((ACTOR + 0x2F, 1, 1), (ACTOR + 0x30, 0, 1),
                    (ACTOR + 0x24, 0xFF, 1), (0x8008A204, screen.ENTRY, 4)):
                put(memory, address, value, size)
            wanted, calls, returned = reference(memory, results, mode)
            calls.insert(0, (screen.ENTRY, (ACTOR,)))
            if not returned:
                calls.append((prior.screen.SYMBOLS['func_1516972C'], (ACTOR,)))
                put(wanted, ACTOR + 0x50, 0xDDDDDDDD)
            models = [ConnectedOracle(body, memory, results, mode, phase).run() for body in (self.raw, self.words, self.retail)]
            for model in models:
                self.assertEqual((model.calls, external(model.memory)), (calls, external(wanted)))
            self.assertEqual((models[1].r, models[1].f, models[1].events, models[1].memory),
                (models[2].r, models[2].f, models[2].events, models[2].memory))
            count += 1
        self.receipt('connected', dict(cases=count, executions=count * 3,
            actual_outer_table_slot=hex(0x8008A204), complete_banked_100_word_updater=True,
            complete_97_word_child=True, inner_callback_and_cleanup_bodies_remain_bounded_hooks=True))

    def test_09_public_payload_and_position_aliases(self):
        count = 0
        for source, mask, phase in itertools.product(
                (ACTOR + 0x50, ACTOR + 0x54, ACTOR + 0x58, PAYLOAD + 0x1C), range(4), (0, 8)):
            memory = fixture(cursor=0)
            put(memory, ACTOR + 0x94, source)
            self.compare(memory, tuple(0 if mask & (1 << i) else 1 for i in range(2)) + (1,), phase=phase)
            count += 1
        for payload, mask, phase in itertools.product((ACTOR, ACTOR + 8, ACTOR + 0x34), range(4), (0, 8)):
            memory = fixture()
            put(memory, ACTOR + 0x98, payload)
            for offset, value, size in ((0x18, 0x40, 1), (0x1B, 255, 1), (0x1C, 5, 2),
                    (0x1E, 0xFFFF, 2), (0x20, 1, 1), (0x21, 1, 1), (0x22, 1, 1)):
                put(memory, payload + offset, value, size)
            self.compare(memory, tuple(0 if mask & (1 << i) else 1 for i in range(2)) + (1,), phase=phase)
            count += 1
        self.receipt('aliases', dict(cases=count, executions=count * 3,
            public_payload_and_sequential_position_aliases=True,
            emitted_streams_not_portable_partial_struct_assignment_or_private_frame_alias_claims=True))


if __name__ == '__main__':
    unittest.main()
