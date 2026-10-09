"""Direct actor-type0x33 update, complete original dispatch and installation audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_actor_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_table_range_loader import STACK, native

ACTOR = 0x20000
FIRST = (0x151B3F28, 0x151B2FA0)
THIRD = (0x151B3A7C, 0x151B3CF0, 0x151B3FDC, 0x151B42A4, 0x151B48DC, 0x151B4B78)
CLEANUP, WALKER = 0x1516972C, 0x151670C0


def put(memory, address, value, size=4):
    for i in range(size):
        memory[address + i] = value >> ((size - i - 1) * 8) & 255


def read(memory, address, size=4):
    return int.from_bytes(bytes(memory[address + i] for i in range(size)), 'big')


def signed16(value):
    value &= 65535
    return value - 65536 if value & 32768 else value


def signed8(value):
    return value - 256 if value & 128 else value


def fixture(flags=0, timer=0, delta=1, selectors=(-1, -1, -1)):
    memory = {STACK + i: 0xA5 for i in range(-0x500, 0x100)}
    memory.update({ACTOR + i: (i * 17 + 0x35) & 255 for i in range(-16, 0x190)})
    put(memory, 0x800BE9E4, delta)
    memory[ACTOR + 0x10] = flags
    put(memory, ACTOR + 0x12, timer, 2)
    for offset, value in zip((0x2C, 0x2D, 0x34), selectors):
        memory[ACTOR + offset] = value & 255
    for base, targets in ((0x8008FAF0, FIRST), (0x8008FAF8, THIRD)):
        for index, target in enumerate(targets):
            put(memory, base + index * 4, target)
        for index in (-128, -2, 127):
            if base + index * 4 not in memory:
                put(memory, base + index * 4, targets[0])
    return memory


def reference(memory, results, actions):
    memory = memory.copy()
    calls, writes = [], []

    def store(address, value, size):
        put(memory, address, value, size)
        writes.append((address, size, value & ((1 << (size * 8)) - 1)))

    def call(target, args):
        index = len(calls)
        calls.append((target, *args))
        for address, value, size in actions.get(index, ()):
            store(address, value, size)
        return results[index % len(results)] & 0xFFFFFFFF

    remove = False
    if memory[ACTOR + 0x10] & 1:
        store(ACTOR + 0x12, signed16(read(memory, ACTOR + 0x12, 2)) -
              read(memory, 0x800BE9E4), 2)
        remove = signed16(read(memory, ACTOR + 0x12, 2)) < 0
    if not remove:
        for offset, coordinate, endpoint in ((0x2C, 0x14, 1), (0x2D, 0x20, 0)):
            selector = signed8(memory[ACTOR + offset])
            if selector != -1:
                target = read(memory, 0x8008FAF0 + selector * 4)
                remove |= call(target, (ACTOR, ACTOR + coordinate, endpoint)) == 0
        flags = memory[ACTOR + 0x10]
        if flags & 12:
            store(ACTOR + 0x10, flags | 2, 1)
        else:
            selector = signed8(memory[ACTOR + 0x34])
            if selector != -1:
                remove |= call(read(memory, 0x8008FAF8 + selector * 4), (ACTOR,)) == 0
    if remove:
        call(CLEANUP, (ACTOR,))
    return memory, calls, writes


class ActorOracle(TriangleOracle):
    def __init__(self, words, memory, results=(1,), actions=None, phase=0,
                 connected=None, entry=screen.ENTRY, delete_next=False):
        super().__init__(words, memory, phase=phase, connected=connected,
                         entry=entry, arguments=(ACTOR,))
        self.results = results
        self.mutations = actions or {}
        self.delete_next = delete_next
        self.dispatches = []

    def execute(self, word):
        if word >> 26 == 32:
            rs, rt = word >> 21 & 31, word >> 16 & 31
            offset = signed16(word & 65535)
            self.r[rt] = signed8(self.get((self.r[rs] + offset) & 0xFFFFFFFF, 1)) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def get(self, address, size):
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        return super().get(address, size)

    def record_call(self, target):
        if target == screen.ENTRY:
            self.dispatches.append(self.r[4])
            return
        assert target in (*FIRST, *THIRD, CLEANUP)
        count = 3 if self.r[31] in (0x151B31FC, 0x151B323C) else 1
        self.calls.append((target, *self.r[4:4 + count]))
        self.events.append(('CALL', self.calls[-1]))

    def hook(self, target):
        index = len(self.calls) - 1
        result = self.results[index % len(self.results)] & 0xFFFFFFFF
        if target == CLEANUP and self.delete_next:
            self.put(self.r[4] + 8, 0, 4)
        for address, value, size in self.mutations.get(index, ()):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


class GameOwnerActorUpdateMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-actor-update-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>81I', cls.rom, screen.ROM))
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
                         guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        cls.installed = screen.SELECTED in (cls.root / screen.SOURCE).read_text()
        if not cls.installed and not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, results=(1,), actions=None, phase=0):
        actions = actions or {}
        expected, calls, writes = reference(memory, results, actions)
        models = [ActorOracle(words, memory, results, actions, phase).run()
                  for words in (self.retail, self.words)]
        external = lambda values: {a: b for a, b in values.items()
                                  if not STACK - 0x500 <= a < STACK + 0x100}
        for model in models:
            self.assertEqual(external(model.memory), external(expected))
            self.assertEqual(model.calls, calls)
            self.assertEqual([(a, n, v) for kind, a, n, v in
                              (e for e in model.events if e[0] == 'W')
                              if not STACK - 0x500 <= a < STACK + 0x100], writes)
        self.assertEqual(models[0].memory, models[1].memory)
        self.assertEqual(models[0].events, models[1].events)
        return models

    def test_01_complete_direct_shape_and_controls(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
                         (81, 32, 0, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(self.words, self.retail)
        rows = []
        for profile in screen.compiler.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            self.assertEqual(meta['diagnostics'], '')
            if profile in ('o2g3', 'o2'):
                self.assertEqual(words, self.retail)
            else:
                self.assertNotEqual(words, self.retail)
            rows.append(meta)
        meta, words = screen.compile_candidate(self.root, self.out, 'unfitted', screen.UNFITTED)
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (81, 32, 6))
        self.assertEqual([i for i, (a, b) in enumerate(zip(words, self.words)) if a != b],
                         [0x6C // 4, 0x78 // 4, 0xAC // 4, 0xB8 // 4, 0x104 // 4, 0x114 // 4])
        self.receipt('shape', dict(selected=self.meta, profiles=rows, guards=0,
                                  unfitted_stack_byte_control=meta))

    def test_02_guest_boundaries_callbacks_and_complete_coverage(self):
        coverage = [set(), set()]
        cases = 0
        settings = itertools.product((0, 1, 2, 4, 8, 12, 13, 0x80, 0xFF),
            ((-1, -1, -1), (0, 1, 0), (1, 0, 5), (0, -1, 2), (-1, 1, 3),
             (-1, -1, 4), (-128, -2, 127), (127, -128, -2)),
            ((0, 1), (1, 1), (-1, 0), (-32768, 1), (32767, -1),
             (0, 0x80000000), (0, 65536)),
            ((1, 1, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 0),
             (0xFFFFFFFF, 0x80000000, 0x12345678)), (0, 8))
        for flags, selectors, (timer, delta), results, phase in settings:
            for i, model in enumerate(self.compare(fixture(flags, timer, delta, selectors), results, phase=phase)):
                coverage[i].update(model.visits)
            cases += 1
        self.assertEqual(cases, 6048)
        self.assertEqual(coverage, [set(range(screen.ENTRY, screen.ENTRY + 324, 4))] * 2)
        self.receipt('guest', dict(cases=cases, executions=cases * 2, complete_words_reached=81,
                                  complete_memory_and_access_trace_equal=True,
                                  strict_mapped_reads_and_writes=True, hostile_volatile_clobbers=True))

    def test_03_fresh_callback_mutations_and_effective_controls(self):
        mutations = (
            {0: ((ACTOR + 0x2D, 1, 1),)},
            {0: ((ACTOR + 0x2D, 255, 1),)},
            {0: ((ACTOR + 0x10, 4, 1), (ACTOR + 0x34, 5, 1))},
            {0: ((ACTOR + 0x34, 5, 1),), 1: ((ACTOR + 0x10, 8, 1),)},
            {0: ((ACTOR + 0x10, 0, 1),), 1: ((ACTOR + 0x34, 2, 1),)},
            {0: ((ACTOR + 0x14, 0x12345678, 4), (ACTOR + 0x2C, 1, 1))},
        )
        cases = 0
        for flags, results, actions, phase in itertools.product((0, 4, 8),
                ((1, 1, 1), (0, 1, 1), (1, 0, 1), (0, 0, 0)), mutations, (0, 8)):
            self.compare(fixture(flags, 10, 1, (0, 0, 0)), results, actions, phase)
            cases += 1
        # Real semantic mutations, not just a source-text check, must fail the oracle.
        bad = screen.SELECTED.replace('    if (remove) {', '    if (!remove) {')
        _, words = screen.compile_candidate(self.root, self.out, 'wrong-cleanup', bad)
        wrong = ActorOracle(words, fixture(selectors=(-1, -1, -1))).run()
        self.assertNotEqual(wrong.calls, reference(fixture(), (1,), {})[1])
        self.receipt('mutations', dict(cases=cases, executions=cases * 2,
                                      wrong_cleanup_control_detected=True))

    def test_04_actual_c_native32_callbacks_timer_and_byte_sentinels(self):
        self.fixture = r"""
typedef signed char s8; typedef unsigned char u8; typedef short s16; typedef int s32;
typedef unsigned int u32;
static u8 actor[0x180], expected[0x180];
s32 D_800BE9E4;
static int calls, deletes, error, masks, mutate;
static s32 cb(u8 *a, void *point, s32 endpoint) {
    int index=calls++;
    if(a!=actor || point!=actor+(endpoint?0x14:0x20) || endpoint!=(index?0:1)) error=1;
    if(mutate && index==0) { actor[0x2D]=1; actor[0x10]=4; }
    return masks&(1<<index)?0:-1;
}
static s32 third(u8 *a) {
    int index=calls++;
    if(a!=actor) error=2;
    return masks&(1<<index)?0:(s32)0x80000000;
}
s32 (*D_8008FAF0[])(u8 *, void *, s32)={cb,cb};
s32 (*D_8008FAF8[])(u8 *)={third,third,third,third,third,third};
void func_1516972C(u8 *a) { if(a!=actor) error=3; deletes++; }
""" + screen.SELECTED + '\n'
        self.run_host(r"""
static s32 times[]={-32768,-1,0,1,32767};
static s32 steps[]={-1,0,1,65536,(s32)0x80000000};
int f,t,d,i,n,remove; s16 newTime; u8 flags;
for(f=0;f<256;f++) for(t=0;t<5;t++) for(d=0;d<5;d++)
for(masks=0;masks<8;masks++) for(mutate=0;mutate<2;mutate++) {
    for(i=0;i<0x180;i++) actor[i]=expected[i]=(u8)(i*17+0x35);
    actor[0x10]=expected[0x10]=(u8)f;
    *(s16 *)(actor+0x12)=*(s16 *)(expected+0x12)=(s16)times[t];
    actor[0x2C]=expected[0x2C]=0; actor[0x2D]=expected[0x2D]=0;
    actor[0x34]=expected[0x34]=5; D_800BE9E4=steps[d];
    calls=deletes=error=0; remove=0; n=0;
    if(f&1) {
        newTime=(s16)((u32)times[t]-(u32)steps[d]);
        *(s16 *)(expected+0x12)=newTime; remove=newTime<0;
    }
    if(!remove) {
        if(mutate) { expected[0x2D]=1; expected[0x10]=4; }
        remove=(masks&3)!=0; n=2; flags=expected[0x10];
        if(flags&12) expected[0x10]|=2;
        else { n=3; remove|=(masks&4)!=0; }
    }
    func_151B3184(actor);
    if(error || calls!=n || deletes!=remove) return 1;
    for(i=0;i<0x180;i++) if(actor[i]!=expected[i]) return 2;
}
""")
        self.receipt('native32', dict(cases=102400, complete_actor_bytes_checked=384,
                                     timer_wrap_and_callbacks_and_post_callback_flags=True))

    def test_05_complete_retail_walker_registered_dispatch_and_saved_next(self):
        walker = list(struct.unpack_from('>74I', self.rom, 0x194570))
        cases = 0
        for phase, nesting, count in itertools.product((0, 8), (0, 2), (0, 1, 2, 3)):
            memory = fixture(1, 0)
            for base, size in ((0x8008B4A8, 101 * 0x34), (0x800DCE50, 2 * 0x1A0),
                               (0x800DD198, 64)):
                memory.update({base + i: 0 for i in range(size)})
            memory[0x800DD190] = nesting
            put(memory, 0x8008BF04, screen.ENTRY)
            actors = [ACTOR + i * 0x200 for i in range(count)]
            for index, actor in enumerate(actors):
                memory.update({actor + i: 0xA5 for i in range(0x180)})
                memory[actor + 0x10] = 1
                put(memory, actor + 0x12, 0, 2)
                put(memory, actor + 8, actors[index + 1] if index + 1 < count else 0)
            put(memory, 0x800DCE50 + 0x33 * 4, actors[0] if actors else 0)
            # The second row independently uses the same registered update callback.
            put(memory, 0x800DCE50 + 0x1A0 + 0x33 * 4, actors[-1] if actors else 0)
            models = []
            for words in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 324, 4), words))
                models.append(ActorOracle(walker, memory, phase=phase, connected=connected,
                                          entry=WALKER, delete_next=True).run())
            expected = actors + (actors[-1:] if actors else [])
            for model in models:
                self.assertEqual(model.dispatches, expected)
                self.assertEqual(model.calls, [(CLEANUP, a) for a in expected])
                self.assertEqual(model.memory[0x800DD190], nesting)
                self.assertEqual(read(model.memory, 0x800DD198 + (nesting + 1) * 4), 0)
                self.assertTrue(set(range(screen.ENTRY, screen.ENTRY + 40, 4)) <= model.visits if count else True)
            self.assertEqual(models[0].memory, models[1].memory)
            self.assertEqual(models[0].events, models[1].events)
            cases += 1
        self.receipt('walker', dict(cases=cases, executions=cases * 2, original_walker_words=74,
                                    both_rows_and_saved_next_delay_slot=True,
                                    original_walker_not_installed_C=True, callback_and_cleanup_hooks_bounded=True))

    def test_06_independent_original_relocations_and_rebases(self):
        owner = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        original = begin + owner.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + original)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
                       cwd=self.root, check=True, capture_output=True)
        uses = lambda path: Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj), uses(self.out / 'selected.o'))
        for index, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if index == 0 else {
                name: (entry & 0xF0000000) + 0x108008 + i * 0x100
                for i, name in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, path in (('original', obj), ('candidate', self.out / 'selected.o')):
                elf = self.out / ('rebase-%d-%s.elf' % (index, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                    '-e', screen.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
                    '-o', str(elf), str(path)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>81I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            if index == 0:
                self.assertEqual(bodies[0], self.retail)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, exact_words_per_set=81,
                                    relocation_uses=sum(uses(obj).values())))

    def test_07_actual_owner_neighbors_and_padding(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
        objects, warnings = [], []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            warnings.append(diagnostics)
        self.assertEqual(warnings[0], warnings[1])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == screen.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
                                       if f['value'] <= o < f['value'] + f['size']}
            self.assertEqual(relative(nrels, function), relative(orels, prior), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, funcs, _ = parse_object(self.out / 'selected.o')
        self.assertEqual(new[nf[screen.FUNCTION]['value']:nf[screen.FUNCTION]['value'] + 324],
                         isolated[funcs[screen.FUNCTION]['value']:funcs[screen.FUNCTION]['value'] + 324])
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        (self.out / 'padded.s').write_text(assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(self.out / 'padded.o'),
                        str(self.out / 'padded.s')], check=True, capture_output=True)
        self.receipt('owner', dict(neighbors=len(nf) - 1, existing_warnings=len(warnings[0]), new_warnings=0,
                                  pools_and_relative_relocations_preserved=True, actual_padder_passes=True))

    def test_08_production_baseline_or_only_target_installation(self):
        current = {name: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                   for name, path in self.paths.items()}
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2309C4)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>2I', self.rom, 0x2345B0), FIRST)
        self.assertEqual(struct.unpack_from('>6I', self.rom, 0x2345B8), THIRD)
        elf = sections(self.root / self.paths['elf'])
        address, data = elf['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008BF04 - address)[0], screen.ENTRY)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        if not self.installed:
            self.assertEqual(current, self.baseline)
        else:
            self.assertEqual((self.root / screen.SOURCE).read_text().count(screen.SELECTED), 1)
            self.assertNotIn(screen.ORIGINAL, (self.root / screen.SOURCE).read_text())
            for name in ('guards', 'progress'):
                self.assertEqual((self.root / self.paths[name]).read_bytes(),
                                 (self.out / ('before-' + name)).read_bytes())
            expected = bytearray((self.out / 'before-elf').read_bytes())
            header = ELF_HEADER.unpack_from(expected)
            records = [SECTION_HEADER.unpack_from(expected, header[6] + i * header[11])
                       for i in range(header[12])]
            start, game = elf['.game']
            section = next(s for s in records if s[3] == start and s[1] == 1)
            struct.pack_into('>81I', expected, section[4] + screen.ENTRY - start, *self.retail)
            table = next(s for s in records if s[1] == 2)
            strings = records[table[6]]
            names = expected[strings[4]:strings[4] + strings[5]]
            offsets = [offset + 8 for offset in range(table[4], table[4] + table[5], table[9])
                if names[SYMBOL.unpack_from(expected, offset)[0]:].split(b'\0', 1)[0] == screen.FUNCTION.encode()]
            self.assertEqual(len(offsets), 1)
            struct.pack_into('>I', expected, offsets[0], 324)
            self.assertEqual(bytes(expected), (self.root / self.paths['elf']).read_bytes())
        self.receipt('installation', dict(installed=self.installed, hashes=current, protected_data=audit,
            registered_pointer='0x8008BF04', exact_words=81 if self.installed else 0,
            entire_ELF_only_target_slot_and_target_size_change=self.installed,
            all_existing_guard_bytes_and_conversion_rows_preserved=True))

    def test_09_lazy_reads_and_missing_byte_fault_prefixes(self):
        cases = (
            (fixture(0), (0x800BE9E4, 0x800BE9E5, 0x800BE9E6, 0x800BE9E7), False),
            (fixture(1, 0), (ACTOR + 0x2C, ACTOR + 0x2D, ACTOR + 0x34), False),
            (fixture(4), (ACTOR + 0x34,), False),
            (fixture(0), (ACTOR + 0x2C,), True),
            (fixture(1, 2), (0x800BE9E4,), True),
            (fixture(0, selectors=(0, 0, 0)), (ACTOR + 0x2D,), True),
        )
        for memory, missing, fault in cases:
            for address in missing:
                del memory[address]
            models = [ActorOracle(words, memory) for words in (self.retail, self.words)]
            for model in models:
                if fault:
                    with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                        model.run()
                else:
                    model.run()
            self.assertEqual(models[0].memory, models[1].memory)
            self.assertEqual(models[0].events, models[1].events)
        self.receipt('faults', dict(cases=6, executions=12, lazy_exit_cases=3,
                                   missing_byte_cases=3, complete_access_prefix_equal=True,
                                   portable_C_fault_or_hardware_claim=False))


if __name__ == '__main__':
    unittest.main()
