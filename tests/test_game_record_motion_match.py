"""Full signed-step integration, self-alias lifetimes and guarded dead tail."""
import hashlib
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_motion_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests import test_game_record_matrix_update_match as matrix
from tools.tests import test_game_record_transform_setup_match as setup
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, BUFFER, OTHER, TYPES = guest.STACK, 0x24000, 0x34000, 0x50000
address, rounded = state.address, setup.rounded


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x800 <= a < STACK+0x140}


def fixture(count=3, kinds=(-1, -2, -1), flag=1, step=1, slot=7, group=2,
        symbols=screen.SYMBOLS, buffer=BUFFER):
    control = address(symbols['D_800C6660'], slot, 16)
    memory = {STACK+i: 0xA5 for i in range(-0x800, 0x140)}
    for base, length in ((control-16, 48), (buffer-16, count*104+32), (OTHER-16, count*104+32)):
        memory.update({(base+i) & 0xFFFFFFFF: 0x35 for i in range(length)})
    for base in {buffer, OTHER}:
        for index in range(count):
            for i, value in enumerate((5.25+index, 34.5, -3.0, 15.0, -25.0, 35.0,
                    1.5, 2.0, 0.75, 1.25, -2.5, 4.0, -0.125, 0.25, 0.5, -0.75)):
                put(memory, base+index*104+36+i*4, bits(value))
            put(memory, base+index*104+100, flag, 1)
    for g in {0, 1, 2, group, 255}:
        put(memory, symbols['D_80098914']+g, count, 1)
        put(memory, symbols['D_80084454']+g*4, TYPES+g*512)
        for index in range(count): put(memory, TYPES+g*512+index, kinds[index % len(kinds)], 1)
    put(memory, control, buffer); put(memory, control+14, group, 1); put(memory, symbols['D_800BE9E4'], step)
    return memory


def alias_fixture(mode, symbols=screen.SYMBOLS):
    control = symbols['D_800C6660']+7*16
    buffers = {'pointer': control-36, 'group': control-24,
        'count': symbols['D_80098914']-36, 'step': symbols['D_800BE9E4']-36}
    buffer = buffers[mode]; memory = fixture(3, (-1,), symbols=symbols, buffer=buffer)
    if mode == 'pointer':
        old = read(memory, control); desired = OTHER
        put(memory, buffer+72, bits(rounded(floating(desired)-floating(old))))
        for i in (10, 11, 12, 13, 14, 19, 20, 21, 22, 23, 24): put(memory, buffer+i*4, 0)
        put(memory, control, buffer)
    elif mode == 'group':
        old, desired = 0x3F000200, 0x3F000100
        put(memory, control+12, old)
        put(memory, buffer+72, bits(rounded(floating(desired)-floating(old))))
        put(memory, TYPES+512+1, 0, 1)
    elif mode == 'count':
        put(memory, symbols['D_80098914'], 0x00000300)
        put(memory, buffer+72, 0x80000300)
    else:
        put(memory, symbols['D_800BE9E4'], 1); put(memory, buffer+72, 0x80000001)
    return memory


class Reference:
    def __init__(self, memory, slot=7, symbols=screen.SYMBOLS):
        self.memory, self.slot, self.symbols = memory.copy(), slot, symbols
        self.updated = []
    def get(self, a, size=4): return read(self.memory, a & 0xFFFFFFFF, size)
    def run(self):
        s = self.symbols; control = address(s['D_800C6660'], self.slot, 16)
        group = self.get(control+14, 1); step = rounded(float(signed(self.get(s['D_800BE9E4']))))
        self.count = self.get(s['D_80098914']+group, 1)
        for index in range(self.count):
            element = address(self.get(control), index, 104)
            if not self.get(element+100, 1): continue
            group = self.get(control+14, 1); table = self.get(s['D_80084454']+group*4)
            if self.get(table+index, 1) != 255: continue
            for target, rate in ((*zip(range(9, 15), range(18, 24)), (19, 24))):
                old = floating(self.get(element+target*4)); velocity = floating(self.get(element+rate*4))
                put(self.memory, element+target*4, bits(rounded(old+rounded(velocity*step))))
            self.updated.append(index)
        return self


class MotionOracle(matrix.UpdateOracle):
    pass


class GameRecordMotionMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-motion-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'd6392a89c3f3d6b935549e56ab00c0f737b51e21a6e451ff32f6d483fe4916c2'
        assert cls.baseline['elf'] == 'd0111ec67ddfe4c6b836061caaa483457e2d38ee6b582a087d45b2d5397672cd'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>73I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        source = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1]
        body = source.split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.guards = cls.out/'successor-guards'; cls.guards.write_bytes(screen.guard_successor((cls.out/'before-guards').read_bytes()))
        cls.isolated_guards = cls.out/'isolated-guards'
        with cls.isolated_guards.open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(next(csv.reader(io.StringIO(cls.guards.read_text())))); writer.writerows(screen.GUARD_ROWS)
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot, word_patches_path=cls.isolated_guards, filename='generated_6B320'))

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def link(self, name, start=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld'); script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))], check=True, capture_output=True)
        words = 71 if name == 'selected' else 73
        return list(struct.unpack_from('>%dI' % words, sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def compare(self, memory, slot=7, phase=0, symbols=screen.SYMBOLS, start=screen.ENTRY, forms=None):
        expected = Reference(memory, slot, symbols).run()
        models = [MotionOracle(w, memory, slot, symbols, phase, start).run() for w in forms or (self.retail, self.raw, self.padded)]
        for model in models:
            self.assertEqual(public(model.memory), public(expected.memory)); self.assertFalse(model.calls)
        for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
            (models[0].memory, models[0].events, models[0].r, models[0].f))
        return models

    def test_01_all_reachable_words_direct_dead_tail_only_and_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['differences'], self.meta['pool_bytes']), (71, 1, 0))
        self.assertEqual(self.raw, self.retail[:71]); self.assertEqual(self.padded, self.retail); self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.retail[71:], [0x03E00008, 0])
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'], 284)
        self.assertEqual(parse_object(self.out/'padded.o')[1][screen.FUNCTION]['size'], 288)
        for profile in ('compact', 'o1g3', 'o1'):
            meta, words = screen.compile_candidate(self.root, self.out, profile, profile=profile)
            if profile == 'compact': self.assertEqual(words, self.raw)
            else: self.assertNotEqual(words, self.raw)
        self.receipt('shape', direct_reachable_words=71, full_slot=73, leaf_no_frame=True,
            one_expected_NOP_insertion_unreachable_JR_plus_padding_NOP=True, not_full_direct_C=True)

    def test_02_counts_sign_width_gates_and_all_reachable_words(self):
        cases, reached = 0, set()
        for count, kinds, flag, phase, step in itertools.product((0, 1, 3, 4, 5, 27, 31, 45, 128, 255),
                ((-1,), (-2,), (-128, -2, -1, 0, 1, 127)), (0, 255), (0, 8), (-1, 0, 5)):
            models = self.compare(fixture(count, kinds, flag, step), phase=phase); reached.update(models[0].visits); cases += 1
        for step, phase in itertools.product((1, 2, 0x7FFFFFFF, -0x80000000, 0x1000001, -0x1000001), (0, 8)):
            self.compare(fixture(step=step), phase=phase); cases += 1
        for slot, group in itertools.product((0, 25, -1, 0x80000000), (0, 255)):
            self.compare(fixture(1, (-1,), slot=slot, group=group), slot); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+284, 4))), 71)
        self.assertNotIn(screen.ENTRY+284, reached)
        self.receipt('guest', cases=cases, forms=3, all_reachable_words=71, unsigned_count=True,
            signed_full_step_single_rounding=True, sole_minus1_type_and_nonzero_flag=True,
            invalid_slots_mapped_guest_only=True)

    def test_03_self_alias_live_pointer_group_cached_count_step(self):
        cases = 0
        for mode, phase in itertools.product(('pointer', 'group', 'count', 'step'), (0, 8)):
            memory = alias_fixture(mode); self.compare(memory, phase=phase); cases += 1
            expected = Reference(memory).run(); control = screen.SYMBOLS['D_800C6660']+7*16
            if mode == 'pointer': self.assertEqual(read(expected.memory, control), OTHER)
            if mode == 'group': self.assertEqual(read(expected.memory, control+14, 1), 1); self.assertEqual(expected.updated, [0, 2])
            if mode == 'count': self.assertEqual(read(expected.memory, screen.SYMBOLS['D_80098914']+2, 1), 0); self.assertEqual(expected.updated, [0, 1, 2])
            if mode == 'step': self.assertEqual(read(expected.memory, screen.SYMBOLS['D_800BE9E4']), 0); self.assertEqual(expected.updated, [0, 1, 2])
        self.receipt('aliases', cases=cases, all_effective=True, live_buffer_group_cached_count_step=True,
            mapped_guest_only_not_portable_C_alias_proof=True)

    def test_04_independent_symbol_rebases(self):
        cases = 0
        for j, start in enumerate((0x15207FFC, 0x15308004)):
            symbols = {name: (0x80107FFC if i % 2 == j else 0x80218004)+i*0x10000 for i, name in enumerate(screen.SYMBOLS)}
            forms = tuple(self.link(name, start, symbols) for name in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0][:71], forms[1]); self.assertEqual(forms[0], forms[2])
            for kinds, phase, step in itertools.product(((-1,), (-2,)), (0, 8), (-1, 1, 0x1000001)):
                self.compare(fixture(kinds=kinds, step=step, symbols=symbols), phase=phase, symbols=symbols, start=start, forms=forms); cases += 1
        self.receipt('rebases', symbols=4, links=2, cases=cases, HI_LO_carries=True, raw_prefix_and_guarded_tail_exact=True)

    def test_05_fired_fault_prefixes(self):
        pairs = 0
        for kinds, flag in (((-1,), 1), ((-2,), 1), ((-1,), 0)):
            memory = fixture(1, kinds, flag); complete = MotionOracle(self.retail, memory, symbols=screen.SYMBOLS, start=screen.ENTRY).run()
            for fault in range(complete.accesses):
                models = [MotionOracle(w, memory, symbols=screen.SYMBOLS, start=screen.ENTRY) for w in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, fault)
                for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                    (models[0].memory, models[0].events, models[0].r, models[0].f))
                pairs += 1
        self.receipt('faults', fired_triplets=pairs, exact_all_accesses=True, dead_tail_never_executes=True,
            not_portable_C_fault_or_hardware_FCSR_proof=True)

    def test_06_effective_semantic_and_dead_tail_controls(self):
        controls = (('type', screen.SELECTED.replace('[index] == -1', '[index] == -2'), fixture()),
            ('flag', screen.SELECTED.replace('unk64 != 0', 'unk64 == 0'), fixture()),
            ('zero-step', screen.SELECTED.replace('f32 step = D_800BE9E4', 'f32 step = 0.0f'), fixture()),
            ('lost-acceleration', screen.SELECTED.replace('            ((f32 *)element)[19] += ((f32 *)element)[24] * step;\n', ''), fixture()),
            ('cached-buffer', screen.SELECTED.replace('    struct04 *element;', '    struct04 *element;\n    struct04 *buffer = (struct04 *)D_800C6660[slot].unk0;').replace(
                '(struct04 *)D_800C6660[slot].unk0 + index', 'buffer + index').replace('((struct04 *)D_800C6660[slot].unk0)[index]', 'buffer[index]'), alias_fixture('pointer')),
            ('live-count', screen.SELECTED.replace('index < count', 'index < D_80098914[((u8 *)&D_800C6660[slot])[0xE]]'), alias_fixture('count')))
        for name, body, memory in controls:
            self.assertNotEqual(body, screen.SELECTED); _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            model = MotionOracle(words, memory, symbols=screen.SYMBOLS, start=0x1523EA54).run()
            self.assertTrue(public(model.memory) != public(Reference(memory).run().memory), name)
        slot = self.out/'slot.s'; unguarded = self.out/'unguarded.s'
        self.assemble('unguarded', emit_padded_assembly(self.out/'selected.o', slot, filename='generated_6B320'))
        self.assertNotEqual(self.link('unguarded'), self.retail)
        wrong = self.out/'wrong-guards'; wrong.write_bytes(self.isolated_guards.read_bytes().replace(
            b'generated_6B320,func_1503EA54,0x118,0x00000000', b'generated_6B320,func_1503EA54,0x118,0x00000001'))
        with self.assertRaises(ValueError): emit_padded_assembly(self.out/'selected.o', slot, word_patches_path=wrong, filename='generated_6B320')
        self.receipt('controls', fresh_semantic=6, effective_public=True, missing_tail_byte_check=True,
            stale_expected_word_rejected=True, no_runtime_claim_for_unreachable_tail=True)

    def test_07_complete_owner_neighbors_and_both_padders(self):
        before = (self.out/'before-source').read_text(); objects = []
        for stage, source in (('before', before), ('after', screen.install(before))):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-'+stage)
            subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')), '--post-process',
                str(obj.relative_to(self.root/'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker', check=True, capture_output=True)
            self.assertEqual(warnings, []); objects.append(obj)
        def fingerprint(obj, name):
            text, functions, relocations = parse_object(obj); item = functions[name]
            a, b = item['value'], item['value']+item['size']
            return item['size'], text[a:b], {o-a: r for o, r in relocations.items() if a <= o < b}
        names = set(parse_object(objects[0])[1]); self.assertEqual(names, set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}: self.assertEqual(fingerprint(objects[0], name), fingerprint(objects[1], name), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1], screen.FUNCTION), fingerprint(self.out/'selected.o', screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py', 'pad_generated_object.py'):
            parsed = []
            for stage, obj in zip(('before', 'after'), objects):
                asm = self.out/(route+'-'+stage+'.s'); guards = self.out/'before-guards' if stage == 'before' else self.guards
                args = [str(obj), str(self.out/'before-layout'), 'generated_6B320', str(asm)] if route == 'pad_c_object.py' else [
                    str(obj), str(self.root/'conker/asm/6B320.s'), str(asm), '--filename', 'generated_6B320']
                subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches', str(guards)], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)], check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+292] = parsed[1][0][start:start+292]; self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o: r for o, r in parsed[0][2].items() if not start <= o < start+292},
                {o: r for o, r in parsed[1][2].items() if not start <= o < start+292})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1]); self.receipt('owner', unchanged_neighbors=len(names)-1,
            pools_exact=True, both_padders=True, caller171_setup141_matrix138_decomposer141_unchanged=True)

    def test_08_literal_source_ELF_guard_successor_and_six_inputs(self):
        before_source = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text(); now = current != before_source
        self.assertEqual(current, screen.install(before_source) if now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 292); extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if now: struct.pack_into('>73I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 288)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            if name == 'guards': self.assertEqual((self.root/path).read_bytes(), screen.guard_successor((self.out/('before-'+name)).read_bytes()) if now else (self.out/('before-'+name)).read_bytes())
            elif name not in ('source', 'elf'): self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes(), name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+292], actual[start:start+292])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), literal_no_projection_or_metadata_exception=True,
            guard_prefix_plus_one_dead_tail_row=True, six_other_inputs_exact=True, protected_data=data)

    def test_09_effective_stale_source_guard_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for stale in (screen.install(before), before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        with self.assertRaises(AssertionError): screen.guard_successor(self.guards.read_bytes())
        rt, rb = Path.read_text, Path.read_bytes; source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: actual+'\n' if p == source else rt(p, *a, **k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_ELF_guard_successor_and_six_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes(); start = elf_slot_offset(actual, screen.ENTRY, 292)
        for offset in (start+4, start+284, start+292, installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_ELF_guard_successor_and_six_inputs()
        guards = self.root/self.paths['guards']; wrong = guards.read_bytes()+b'\n'
        with patch.object(Path, 'read_bytes', lambda p: wrong if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_ELF_guard_successor_and_six_inputs()
        self.receipt('integrity-controls', stale_installs=2, stale_guard=1, source=1, ELF=4, guards=1, all_effective=True)

    def test_10_unmapped_gates_and_float_boundaries(self):
        cases = 0
        for count, flag in ((0, 1), (3, 0)):
            memory = fixture(count, flag=flag)
            for a in list(memory):
                if screen.SYMBOLS['D_80084454'] <= a < screen.SYMBOLS['D_80084454']+1024 or TYPES <= a < TYPES+131072:
                    del memory[a]
                if count == 0 and BUFFER <= a < BUFFER+104: del memory[a]
            self.compare(memory); cases += 1
        payloads = ((0, 0x80000000), (1, 0x80000001), (bits(1.0000001192092896), bits(0.5)),
            (bits(2.0e38), bits(2.0e38)), (0x7F800000, 0), (0x7FC12345, 0x3F800000))
        for (old, rate), step, phase in itertools.product(payloads, (0, 1, -1), (0, 8)):
            memory = fixture(1, (-1,), step=step)
            for i in range(9, 15): put(memory, BUFFER+i*4, old)
            for i in range(18, 25): put(memory, BUFFER+i*4, rate)
            models = [MotionOracle(w, memory, phase=phase, symbols=screen.SYMBOLS, start=screen.ENTRY).run()
                for w in (self.retail, self.raw, self.padded)]
            for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                (models[0].memory, models[0].events, models[0].r, models[0].f))
            if old & 0x7F800000 != 0x7F800000:
                self.assertEqual(public(models[0].memory), public(Reference(memory).run().memory))
            cases += 1
        self.receipt('payloads', cases=cases, empty_and_flag_zero_tables_unmapped=True,
            finite_signed_zero_subnormal_overflow_reference=True, infinity_NaN_machine_forms_only=True,
            no_hardware_FCSR_or_NaN_propagation_claim=True)

    def test_11_native32_full_counts_and_signed_steps(self):
        prefix = r'''
typedef unsigned char u8; typedef signed char s8; typedef unsigned short u16; typedef short s16;
typedef unsigned u32; typedef int s32; typedef float f32;
typedef struct { u32 prefix[9]; u16 unk24,unk26; s16 unk28,unk2A; s32 unk2C,unk30,unk34,unk38,unk3C,unk40,unk44;
    u32 tail[7]; u8 unk64,unk65,pad[2]; } struct04;
typedef struct { s32 unk0,unk4,unk8; u8 tail[4]; } struct106;
typedef char record_size[sizeof(struct04)==104?1:-1]; typedef char control_size[sizeof(struct106)==16?1:-1];
struct106 D_800C6660[26]; s32 D_800BE9E4; u8 D_80098914[3];
static s8 rows[3][256]; s8 *D_80084454[3]={rows[0],rows[1],rows[2]};
static struct04 records[256],expected[256];
static void initialize(int count,int pattern,int flag,int slot,s32 step) {
    for(int g=0;g<3;g++) { D_80098914[g]=count; for(int i=0;i<256;i++) rows[g][i]=pattern==0?-1:pattern==1?-2:(s8)((i%5)-3); }
    D_800BE9E4=step; D_800C6660[slot].unk0=count?(s32)records:0; ((u8 *)&D_800C6660[slot])[14]=slot%3;
    for(int i=0;i<256;i++) {
        for(int j=0;j<26;j++) ((u32 *)&records[i])[j]=0x35353535;
        f32 *p=(f32 *)&records[i];
        for(int j=0;j<6;j++) { p[9+j]=(f32)(i+j)+0.25f; p[18+j]=(j-2)*0.125f; }
        p[24]=-0.75f; records[i].unk64=flag;
    }
}
static void reference(int slot) {
    int group=((u8 *)&D_800C6660[slot])[14], limit=D_80098914[group]; f32 delta=(f32)D_800BE9E4;
    for(int i=0;i<limit;i++) {
        if(rows[group][i]!=-1 || !records[i].unk64) continue;
        f32 *p=(f32 *)&records[i];
        for(int j=0;j<6;j++) { f32 product=p[18+j]*delta; p[9+j]=p[9+j]+product; }
        f32 acceleration=p[24]*delta; p[19]=p[19]+acceleration;
    }
}
'''
        suffix = r'''
static int run(u32 *failure) {
    const s32 steps[8]={0,1,-1,5,0x7FFFFFFF,(s32)0x80000000u,0x1000001,-0x1000001};
    const int slots[3]={0,7,25}; unsigned cases=0;
    for(int count=0;count<256;count++) for(int t=0;t<8;t++) for(int pattern=0;pattern<3;pattern++)
    for(int flag=0;flag<2;flag++) for(int s=0;s<3;s++) {
        initialize(count,pattern,flag,slots[s],steps[t]); reference(slots[s]);
        for(unsigned i=0;i<sizeof(records)/4;i++) ((u32 *)expected)[i]=((u32 *)records)[i];
        initialize(count,pattern,flag,slots[s],steps[t]); func_1503EA54(slots[s]); cases++;
        for(unsigned i=0;i<sizeof(records)/4;i++) if(((u32 *)records)[i]!=((u32 *)expected)[i]) {
            failure[0]=cases; failure[1]=i; failure[2]=((u32 *)records)[i]; return 1;
        }
    }
    return cases==36864?0:2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:], prefix+screen.SELECTED+suffix, profile), (0, ''))
        for name, body in (('type', screen.SELECTED.replace('[index] == -1', '[index] == -2')),
                ('step', screen.SELECTED.replace('f32 step = D_800BE9E4', 'f32 step = 0.0f')),
                ('acceleration', screen.SELECTED.replace('            ((f32 *)element)[19] += ((f32 *)element)[24] * step;\n', ''))):
            result, detail = self.run_native('native-negative-'+name, prefix+body+suffix)
            self.assertEqual(result, 1); self.assertEqual(len(detail), 3)
        self.receipt('native', cases_per_profile=36864, profiles=['O2', 'O0'], counts_all_0_through255=True,
            signed_steps_and_24bit_rounding=True, all_record_words_and_skipped_bytes_checked=True,
            effective_controls=3, aliases_and_dead_tail_and_FCSR_not_native_claims=True)

    def test_12_actual_five_body_dispatcher_chain(self):
        specs = ((state.screen.ENTRY, state.screen.ROM, 171), (state.HELPER, state.screen.ROM+684, 27),
            (setup.screen.ENTRY, setup.screen.ROM, 141), (matrix.screen.ENTRY, matrix.screen.ROM, 138))
        bodies = {a: list(struct.unpack_from('>%dI' % n, self.before, elf_slot_offset(self.before, a, n*4))) for a, _, n in specs}
        for a, rom, n in specs: self.assertEqual(bodies[a], list(struct.unpack_from('>%dI' % n, self.rom, rom)))
        frame = (-bodies[state.screen.ENTRY][0]) & 65535; self.assertEqual(frame, 56)
        symbols = dict(state.screen.SYMBOLS, **setup.screen.SYMBOLS); symbols.update(matrix.screen.SYMBOLS); symbols.update(screen.SYMBOLS)
        class ChainOracle(MotionOracle, setup.SetupOracle):
            def __init__(model, memory, phase, connected, actions):
                state.StateOracle.__init__(model, bodies[state.screen.ENTRY], memory, symbols=symbols, phase=phase,
                    start=state.screen.ENTRY, connected=connected, actions=actions); model.result=None
            def record_call(model, target):
                super().record_call(target)
                if target == screen.ENTRY: model.mutate('tail1')
                if target == matrix.screen.ENTRY: model.mutate('tail2')
        class ChainReference(state.Reference):
            def call(ref, target, args):
                result = super().call(target, args)
                if target == setup.screen.ENTRY:
                    put(ref.memory, STACK+ref.phase-frame+16, args[4])
                    body = setup.Reference(ref.memory, args, ref.phase-frame, symbols, ref.actions).run()
                    ref.memory = body.memory; ref.calls.extend(body.calls)
                if target == screen.ENTRY: ref.memory = Reference(ref.memory, args[0], symbols).run().memory
                if target == matrix.screen.ENTRY:
                    body = matrix.Reference(ref.memory, args[0], ref.phase-frame, symbols, ref.actions).run()
                    ref.memory = body.memory; ref.calls.extend(body.calls)
                return result
        cases = 0
        for count, status, phase, delta in itertools.product((0, 1, 3, 4), (1, 2, 3), (0, 8), (-1, 5)):
            initial = matrix.fixture(count, (-1, -2, 0, -1), phase=phase, symbols=symbols)
            memory = state.fixture(state=status, count=count, types=(255, 254, 0, 255), symbols=symbols,
                existing=status == 1, flag=1)
            memory.update({a: v for a, v in initial.items() if matrix.BANK <= a < matrix.BANK+256*64})
            if status == 1: memory.update({a: v for a, v in initial.items() if BUFFER <= a < BUFFER+count*104})
            memory.update({STACK+i: 0xA5 for i in range(-0x800, 0x140)})
            actor = symbols['D_800CC2D0']+7*812; put(memory, actor+0x1D4, matrix.BANK)
            for i, value in enumerate((1.25, -2.5, 8.0)): put(memory, actor+20+i*4, bits(value))
            put(memory, symbols['D_800BE9E4'], delta)
            actions = {('tail1', 0): ((symbols['D_800BE9E4'], delta, 4),)}
            expected = ChainReference(memory, symbols=symbols, actions=actions); expected.phase=phase; expected.run()
            models = []
            for words in (self.retail, self.raw, self.padded):
                connected = {a+i*4: w for a, body in bodies.items() if a != state.screen.ENTRY for i, w in enumerate(body)}
                connected.update({screen.ENTRY+i*4: w for i, w in enumerate(words)})
                model = ChainOracle(memory, phase, connected, actions).run(); models.append(model)
                self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
            for model in models[1:]: self.assertEqual((model.memory, model.events, model.r, model.f),
                (models[0].memory, models[0].events, models[0].r, models[0].f))
            cases += 1
        self.receipt('connected-caller', cases=cases, dispatcher171_setup141_predicate27_motion73_matrix138=True,
            independent_composed_reference=True, remaining_SDK_callbacks_modeled_not_full_gameplay=True)


if __name__ == '__main__':
    unittest.main()
