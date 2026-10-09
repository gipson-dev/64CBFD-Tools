"""Exhaustive signed-duration qualification and byte-preserving alpha cleanup."""
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
from tools.experiments import game_ribbon_alpha_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests import test_game_random_curve_record as native

ACTOR, PAYLOAD = 0x20000, 0x21000
BOUNDARIES = (0, 1, 31, 32, 33, 255, 4095, 32767, 32768, 32769, 65504, 65535)
ALIASES = (PAYLOAD, ACTOR, ACTOR + 1, ACTOR + 0x7D, ACTOR + 0x7E,
    ACTOR + 0x7F, ACTOR + 0x80, ACTOR + 0x81)


def fixture(value, payload=PAYLOAD):
    memory = {base + i: (i * 17 + 0xA5) & 255
        for base, size in ((ACTOR, 0xC0), (PAYLOAD, 0x40)) for i in range(size)}
    put(memory, ACTOR + 0x1C, value, 2)
    put(memory, ACTOR + 0x98, payload)
    return memory


def alpha(value):
    signed = value if value < 32768 else value - 65536
    return min(signed * 8, 255) & 255


class AlphaOracle(TriangleOracle):
    def __init__(self, words, memory, phase=0, entry=screen.ENTRY):
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(ACTOR,))

    def get(self, address, size):
        if any(address + i not in self.memory for i in range(size)):
            raise KeyError(('read', address, size))
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording and any(address + i not in self.memory for i in range(size)):
            raise KeyError(('write', address, size))
        super().put(address, value, size)


class GameRibbonAlphaTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-ribbon-alpha-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>15I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
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

    def test_01_original_and_safe_body_direct_match(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (15, 0, 0, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertFalse(self.meta['relocations'])
        records = []
        for name, body in (('original', screen.ORIGINAL), ('selected', screen.SELECTED)):
            for profile in ('o2g3', 'o2', 'o1g3', 'o1'):
                meta, words = screen.compile_candidate(self.root, self.out, name + '-' + profile, body, profile)
                records.append(meta)
                if profile.startswith('o2'):
                    self.assertEqual(words, self.retail)
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(row['function'] == screen.FUNCTION for row in csv.DictReader(stream)))
        self.receipt('shape', dict(records=records, target_guards=0, already_exact_before_cleanup=True))

    def test_02_exhaustive_signed_halfwords_and_ordered_access(self):
        coverage = set()
        template = fixture(0)
        for value in range(65536):
            memory = template.copy()
            put(memory, ACTOR + 0x1C, value, 2)
            expected = memory.copy()
            put(expected, PAYLOAD + 0x1B, alpha(value), 1)
            for words in (self.words, self.retail):
                model = AlphaOracle(words, memory, phase=8 if value & 1 else 0).run()
                self.assertEqual(model.memory, expected)
                self.assertEqual(model.r[2], 1)
                self.assertEqual(model.calls, [])
                self.assertEqual(model.events, [
                    ('R', ACTOR + 0x1C, 2, value),
                    ('R', ACTOR + 0x98, 4, PAYLOAD),
                    ('W', PAYLOAD + 0x1B, 1, alpha(value))])
                coverage.update(model.visits)
        self.assertEqual(coverage, {screen.ENTRY + i * 4 for i in (*range(10), 12, 13, 14)})
        self.receipt('guest', dict(cases=65536, executions=131072, reachable_words=13,
            unreachable_words=[10, 11], full_memory_and_ordered_access=True,
            portable_signed_product_range=[-262144, 262136]))

    def test_03_aliases_and_every_missing_access_byte(self):
        for value, payload, phase in itertools.product(BOUNDARIES, ALIASES, (0, 8)):
            memory = fixture(value, payload)
            expected = memory.copy()
            put(expected, payload + 0x1B, alpha(value), 1)
            for words in (self.words, self.retail):
                model = AlphaOracle(words, memory, phase).run()
                self.assertEqual(model.memory, expected)
                self.assertEqual(model.r[2], 1)
                self.assertEqual(model.events[-1], ('W', payload + 0x1B, 1, alpha(value)))
                self.assertEqual(model.events[:2], [('R', ACTOR + 0x1C, 2, value),
                    ('R', ACTOR + 0x98, 4, payload)])
        addresses = [ACTOR + 0x1C, ACTOR + 0x1D, *range(ACTOR + 0x98, ACTOR + 0x9C),
            PAYLOAD + 0x1B]
        for address in addresses:
            memory = fixture(65535)
            del memory[address]
            models = [AlphaOracle(words, memory) for words in (self.words, self.retail)]
            for model in models:
                with self.assertRaises(KeyError):
                    model.run()
            self.assertEqual(models[0].events, models[1].events)
            self.assertEqual(models[0].memory, models[1].memory)
        self.receipt('aliases', dict(cases=len(BOUNDARIES) * len(ALIASES) * 2,
            missing_byte_pairs=len(addresses), fault_prefix_guest_only=True))

    def test_04_actual_native32_exhaustive_callback_and_aliases(self):
        self.fixture = 'typedef unsigned char u8; typedef short s16; typedef int s32;\n' + screen.SELECTED + r'''
static union { unsigned int align; u8 bytes[0x100]; } actor, payload;
static s32 (*callback)(u8 *)=func_151490C8;
'''
        self.run_host(r'''
unsigned int value, i, mode;
u8 expected[0x100], *destination;
for(mode=0;mode<9;mode++) {
    for(value=0;value<65536;value++) {
        s32 signedValue=value<32768?(s32)value:(s32)value-65536;
        s32 product=signedValue*8;
        for(i=0;i<0x100;i++) { actor.bytes[i]=0xa5; payload.bytes[i]=0x5a; }
        destination=mode?actor.bytes+(mode==1?0:mode==2?1:0x7d+mode-3):payload.bytes;
        *(s16 *)(actor.bytes+0x1c)=(s16)signedValue;
        *(u8 **)(actor.bytes+0x98)=destination;
        for(i=0;i<0x100;i++) { expected[i]=actor.bytes[i]; }
        if(mode) expected[destination-actor.bytes+0x1b]=(u8)(product>=256?255:product);
        if(callback(actor.bytes)!=1) return 1;
        for(i=0;i<0x100;i++) {
            if(actor.bytes[i]!=expected[i]) return 2;
            if(payload.bytes[i]!=(mode || i!=0x1b?0x5a:(u8)(product>=256?255:product))) return 3;
        }
    }
}
''')
        self.receipt('native', dict(cases=9 * 65536, actual_native32=True,
            typed_callback=True, full_actor_payload_canaries=True, hardware_or_whole_caller_proven=False))

    def test_05_copied_owner_neighbors_and_effective_negatives(self):
        source = (self.root / screen.SOURCE).read_text()
        before = source.replace(screen.SELECTED, screen.ORIGINAL)
        self.assertEqual(before.count(screen.ORIGINAL), 1)
        objects = []
        for name, text in (('before', before), ('after', before.replace(screen.ORIGINAL, screen.SELECTED))):
            obj, diagnostics = compile_owner(self.root, self.out, text, name)
            self.assertEqual(diagnostics, [])
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((self.out / (name + '.c')).relative_to(self.root / 'conker')),
                '--post-process', str(obj.relative_to(self.root / 'conker')),
                '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
        old, old_fn, old_rel = parse_object(objects[0])
        new, new_fn, new_rel = parse_object(objects[1])
        self.assertEqual(old_fn, new_fn)
        self.assertEqual(old, new)
        self.assertEqual(old_rel, new_rel)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertTrue(emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250'))
        negatives = {'unsigned-duration': screen.SELECTED.replace('*(s16 *)', '*(u16 *)'),
            'wrong-scale': screen.SELECTED.replace('* 8', '* 4'),
            'low-clamp': screen.SELECTED.replace('temp_v1 = 0xFF;', 'temp_v1 = 0xFE;'),
            'wrong-output': screen.SELECTED.replace('temp_v0 + 0x1B', 'temp_v0 + 0x1A')}
        cases = [fixture(65535), fixture(1), fixture(32), fixture(31)]
        for (name, body), memory in zip(negatives.items(), cases):
            _, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            self.assertNotEqual(AlphaOracle(words, memory).run().memory,
                AlphaOracle(self.words, memory).run().memory, name)
        self.receipt('owner', dict(neighbors=len(new_fn) - 1, entire_owner_text_unchanged=True,
            pools_and_relocations_unchanged=True, actual_padder_accepts=True, negatives=list(negatives)))

    def test_06_independent_assembly_links(self):
        assembly = (self.root / 'conker/asm/175250.s').read_text().split('glabel ' + screen.FUNCTION, 1)[1]
        assembly = 'glabel ' + screen.FUNCTION + assembly.split('endlabel ' + screen.FUNCTION, 1)[0]
        original = self.out / 'original.s'
        original.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + assembly)
        obj = original.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(original)],
            cwd=self.root, check=True, capture_output=True)
        for entry in (screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000):
            bodies = []
            script = self.out / ('rebase-%x.ld' % entry)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            for name, path in (('original', obj), ('candidate', self.out / 'selected.o')):
                elf = self.out / ('rebase-%x-%s.elf' % (entry, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                    '-e', screen.FUNCTION, '-o', str(elf), str(path)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>15I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            for value in BOUNDARIES:
                memory = fixture(value)
                models = [AlphaOracle(words, memory, entry=entry).run() for words in bodies]
                self.assertEqual(models[0].memory, models[1].memory)
                self.assertEqual(models[0].events, models[1].events)
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, relocation_uses=0, cases=48))

    def test_07_linked_audit_and_callback_table(self):
        elf = self.root / 'conker/build/conker.us.elf'
        data = sections(elf)
        actual = [chunk[screen.ENTRY - address:screen.ENTRY - address + 60]
            for address, chunk in data.values() if address <= screen.ENTRY and screen.ENTRY + 60 <= address + len(chunk)]
        self.assertEqual(actual, [struct.pack('>15I', *self.retail)])
        address = 0x8008A410
        pointers = [chunk[address - base:address - base + 4] for base, chunk in data.values()
            if base <= address and address + 4 <= base + len(chunk)]
        self.assertEqual(pointers, [struct.pack('>I', screen.ENTRY)])
        baseline_path = self.out / 'baseline.json'
        if not baseline_path.exists():
            self.skipTest('installation audit requires immutable local pre-edit baseline; retail/table checked')
        baseline = json.loads(baseline_path.read_text())
        for name, path in dict(elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
                progress='conker/progress.csv').items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + name)).read_bytes())
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[name])
        audit = audit_layout(elf, self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('audit', dict(whole_ELF_byte_identical=True, guards_and_progress_identical=True,
            source_sha256=hashlib.sha256((self.root / screen.SOURCE).read_bytes()).hexdigest(),
            protected_data_layout=audit, callback_selector=6, new_exact_or_conversion_credit=0))


if __name__ == '__main__':
    unittest.main()
