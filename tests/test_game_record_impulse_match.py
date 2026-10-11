"""Six-draw impulse semantics, retained RNG, caller ABI and literal linked audit."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_impulse_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly, ELF_HEADER, SECTION_HEADER, SYMBOL
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_random_selector_outputs_match as rng
from tools.tests import test_game_record_transform_setup_match as setup
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, RECORD, OTHER, THIRD = guest.STACK, 0x24000, 0x34000, 0x44000
RANDOM, SEED = 0x150ADA20, rng.SEED
rounded = setup.rounded
CALLERS = ((0x1503F078, 0x6C528, 13, bits(2.0), bits(2.0), 0),
    (0x1503F0AC, 0x6C55C, 11, bits(1.0), bits(2.0), 1),
    (0x1503F0D8, 0x6C588, 12, bits(2.06), bits(3.0), 1))


def rotated_symbol_tables(data):
    header = ELF_HEADER.unpack_from(data)
    sections_ = [SECTION_HEADER.unpack_from(data, header[6]+i*header[11]) for i in range(header[12])]
    tables = [s for s in sections_ if s[1] == 2]; assert len(tables) == 1
    table = tables[0]; strings = sections_[table[6]]
    names = data[strings[4]:strings[4]+strings[5]]
    offsets = [o for o in range(table[4], table[4]+table[5], table[9])
        if names[SYMBOL.unpack_from(data, o)[0]:].split(b'\0', 1)[0] == b'D_80098920']
    assert len(offsets) == 1 and table[9] == 16
    start = offsets[0]; records = [SYMBOL.unpack_from(data, start+i*16) for i in range(4)]
    expected_names = (b'D_80098920', b'D_8009D4C0', b'D_8009D880', b'D_8009D0F0')
    assert tuple(names[r[0]:].split(b'\0', 1)[0] for r in records) == expected_names
    assert tuple(r[1:] for r in records) == (
        (0x80098920, 0, 16, 0, 0xFFF1), (0x8009D4C0, 0, 16, 0, 6),
        (0x8009D880, 0, 16, 0, 6), (0x8009D0F0, 0, 16, 0, 6))
    assert tuple(r[0] for r in records) == tuple(records[0][0]+i*11 for i in range(4))
    string_start = strings[4]+records[0][0]
    assert data[string_start:string_start+44] == b'\0'.join(expected_names)+b'\0'
    result = bytearray(data)
    for i, source in enumerate((1, 2, 3, 0)):
        SYMBOL.pack_into(result, start+i*16, records[i][0], *records[source][1:])
    result[string_start:string_start+44] = b'\0'.join(expected_names[1:]+expected_names[:1])+b'\0'
    return result, start, string_start


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x800 <= a < STACK+0x140}


def fixture(symbols=screen.SYMBOLS, record=RECORD, scale=0x3CE0E0E1, seed=1):
    memory = {STACK+i: 0xA5 for i in range(-0x800, 0x140)}
    for base in {record, RECORD, OTHER, THIRD}:
        memory.update({base+i: 0x35 for i in range(-16, 120)})
        for i, value in enumerate((1.25, -2.5, 4.0, 5.0, 6.0, 7.0, -0.75)):
            put(memory, base+72+i*4, bits(value))
    for name, value in (('D_80098920', scale), ('D_80098924', 0xBE99999A)):
        for i in range(4): memory.setdefault(symbols[name]+i, 0)
        put(memory, symbols[name], value)
    put(memory, SEED, seed, 8)
    return memory


class Reference:
    def __init__(self, memory, args, randoms, symbols=screen.SYMBOLS, phase=0,
            actions=None, actual=False, home=None):
        self.memory, self.args, self.randoms, self.symbols = memory.copy(), args, randoms, symbols
        self.phase, self.actions, self.actual = phase, actions or {}, actual
        self.home = STACK+phase if home is None else home
        self.calls = []

    def draw(self):
        index = len(self.calls); self.calls.append((self.symbols['func_150ADA20'],))
        for a, value, size in self.actions.get(index, ()): put(self.memory, a, value, size)
        if self.actual:
            value = rng.next_seed(read(self.memory, SEED, 8)); put(self.memory, SEED, value, 8)
        else: value = self.randoms[index]
        return value & 0xFFFFFFFF

    def run(self):
        record, horizontal, vertical, mode = self.args
        put(self.memory, self.home, record)
        scale = floating(read(self.memory, self.symbols['D_80098920']))
        h = rounded(floating(horizontal)*scale); v = rounded(floating(vertical)*scale)
        coefficients = [h, v, h]
        for i, coefficient in enumerate(coefficients): put(self.memory, self.home-16+i*4, bits(coefficient))
        mask, bias = (0x80, 127) if mode else (255, 0)
        for i in range(3):
            value = self.draw()
            coefficient = floating(read(self.memory, self.home-16+i*4))
            old = floating(read(self.memory, record+72+i*4))
            factor = rounded(rounded(float((value & mask)+bias)*coefficient)+2.0)
            put(self.memory, record+72+i*4, bits(rounded(old*factor)))
        record = read(self.memory, self.home)
        for i in range(3):
            value = self.draw()
            put(self.memory, record+84+i*4, bits(rounded(float((value & 255)-128)*0.03125)))
        acceleration = read(self.memory, self.symbols['D_80098924'])
        put(self.memory, read(self.memory, self.home)+96, acceleration)
        return self


class ImpulseOracle(rng.RandomOutputsOracle, guest.AttachmentOracle):
    def __init__(self, words, memory, args, randoms, phase=0, symbols=screen.SYMBOLS,
            start=screen.ENTRY, actions=None, connected=None, actual=False):
        guest.AttachmentOracle.__init__(self, words, memory, phase=phase, entry=start,
            arguments=args, connected=connected)
        self.randoms, self.symbols, self.number = randoms, symbols, 0
        self.actions, self.actual = actions or {}, actual
        self.callbacks = []

    def record_call(self, target):
        if target == screen.ENTRY:
            self.callbacks.append((target, *self.arguments(4)))
            return
        assert target == self.symbols['func_150ADA20'], hex(target)
        self.calls.append((target,)); self.events.append(('CALL', target))
        for a, value, size in self.actions.get(self.number, ()): self.put(a, value, size)
        self.number += 1

    def hook(self, target):
        assert target == self.symbols['func_150ADA20'] and not self.actual
        value = self.randoms[self.number-1]
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000+register
        self.r[2] = value & 0xFFFFFFFF
        self.f[:20] = [0xA5000000+i for i in range(20)]


class GameRecordImpulseMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-impulse-match-test'; cls.out.mkdir(exist_ok=True)
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
        assert cls.baseline['source'] == 'e367e9c05a6fbdd714f4ea53cb88939e32a50361fb08640f67d403d5593f3d41'
        assert cls.baseline['elf'] == 'acd55ef04121c1aad24f275cdb53e7a313d3f8608317ce381b09c200105cd666'
        assert cls.baseline['guards'] == '50d69274e599b51d2cebee2e9942b09fad6a7c75f7d91a56f2666c6d823a872b'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>74I', cls.rom, screen.ROM))
        cls.random = list(struct.unpack_from('>18I', cls.rom, 0xDAED0))
        assert cls.random == list(struct.unpack_from('>18I', cls.before, elf_slot_offset(cls.before, RANDOM, 72)))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        body = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split('endlabel '+screen.FUNCTION, 1)[0]
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
        return list(struct.unpack_from('>74I', sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def compare(self, memory, args=(RECORD, bits(2), bits(3), 0), randoms=(0, 127, 128, 255, 1, 0),
            phase=0, actions=None, symbols=screen.SYMBOLS, start=screen.ENTRY, forms=None, actual=False):
        expected = Reference(memory, args, randoms, symbols, phase, actions, actual).run()
        code = {symbols['func_150ADA20']+i*4: w for i, w in enumerate(self.random)} if actual else {}
        models = [ImpulseOracle(w, memory, args, randoms, phase, symbols, start, actions, code, actual).run()
            for w in forms or (self.retail, self.raw, self.padded)]
        for model in models:
            self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
            self.assertEqual(model.number, 6)
        for model in models[1:]: self.assertEqual((model.memory, model.events), (models[0].memory, models[0].events))
        self.assertEqual((models[0].r, models[0].f), (models[-1].r, models[-1].f))
        return models

    def test_01_shape_guard_cycle_and_profiles(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'], self.meta['pool_bytes']), (74, 96, 5, 0))
        self.assertEqual([i*4 for i, (a, b) in enumerate(zip(self.raw, self.retail)) if a != b], [72, 84, 96, 104, 108])
        self.assertEqual(self.padded, self.retail); self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'], 296)
        for profile in ('compact', 'o1g3', 'o1'):
            _, words = screen.compile_candidate(self.root, self.out, profile, profile=profile)
            if profile == 'compact': self.assertEqual(words, self.raw)
            else: self.assertNotEqual(words, self.raw)
        self.receipt('shape', words=74, frame=96, unchanged_words=69, guards=5, new_pool_bytes=0, not_direct_exact=True)

    def test_02_all_low_bytes_modes_and_reachable_words(self):
        cases, reached = 0, set()
        for byte, mode, phase in itertools.product(range(256), (0, 1, -1, 256, 0x80000000), (0, 8)):
            randoms = tuple((0xABCD0000 | ((byte+i*53)&255)) for i in range(6))
            models = self.compare(fixture(), args=(RECORD, bits(2.06), bits(3), mode), randoms=randoms, phase=phase)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+296, 4))), 74)
        self.receipt('guest', cases=cases, forms=3, all_words=74, full_32bit_mode=True, six_draws=True, saved_F20_F21_and_GPRs=True)

    def test_03_callback_lifetimes_and_mapped_aliases(self):
        cases = 0
        for index, phase in itertools.product(range(6), (0, 8)):
            actions = {index: ((RECORD+72+(index%3)*4, bits(11.5), 4),
                (screen.SYMBOLS['D_80098920'], bits(9), 4), (screen.SYMBOLS['D_80098924'], bits(-7), 4))}
            self.compare(fixture(), phase=phase, actions=actions); cases += 1
        for phase in (0, 8):
            home = STACK+phase
            actions = {0: ((home, OTHER, 4), (home+4, 0, 4), (home+8, 0, 4), (home+12, 0, 4)),
                5: ((home, THIRD, 4), (screen.SYMBOLS['D_80098924'], bits(-9), 4))}
            models = self.compare(fixture(), phase=phase, actions=actions)
            self.assertEqual(read(models[0].memory, OTHER+84), bits((255-128)*0.03125))
            self.assertEqual(read(models[0].memory, THIRD+96), bits(-9)); cases += 1
            for record in (screen.SYMBOLS['D_80098920']-72, home-88):
                memory = fixture(record=record)
                if record == home-88:
                    final = bits((1-128)*0.03125)+96
                    memory.update({final+i: 0x35 for i in range(4)})
                self.compare(memory, args=(record, bits(2), bits(3), 1), phase=phase); cases += 1
        self.receipt('lifetimes', cases=cases, cached_coefficients_first_pointer_mask_bias=True,
            live_velocity_after_call_second_and_final_home_reloads=True, acceleration_after_sixth=True,
            global_and_private_coefficient_aliases=True, home_private_aliases_guest_only=True)

    def test_04_retained_actual64_rng_and_seed_alias(self):
        cases, reached = 0, set()
        for seed, mode, phase, alias in itertools.product(rng.SEEDS, (0, 1), (0, 8), (False, True)):
            record = SEED-72 if alias else RECORD
            models = self.compare(fixture(seed=seed, record=record), args=(record, bits(1), bits(2), mode), phase=phase, actual=True)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(RANDOM, RANDOM+72, 4))), 18)
        self.receipt('actual-rng', cases=cases, instructions=18, seed64=True, ordered_seed_velocity_alias=True, RNG_unconverted=True)

    def test_05_rebases_and_fired_fault_prefixes(self):
        cases = 0
        for j, start in enumerate((0x15207FFC, 0x15308004)):
            symbols = {name: ((0x151ADA20+j*0x10000) if name == 'func_150ADA20' else
                (0x80107FFC if i % 2 == j else 0x80218004)+i*0x10000) for i, name in enumerate(screen.SYMBOLS)}
            forms = tuple(self.link(name, start, symbols) for name in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[2])
            for mode, phase in itertools.product((0, 256), (0, 8)):
                self.compare(fixture(symbols), args=(RECORD, bits(2), bits(3), mode), phase=phase, symbols=symbols, start=start, forms=forms); cases += 1
        faults = 0
        for mode in (0, 1):
            memory = fixture(); args = (RECORD, bits(2), bits(3), mode); values = (0, 127, 128, 255, 1, 0)
            complete = ImpulseOracle(self.retail, memory, args, values).run()
            for fault in range(complete.accesses):
                models = [ImpulseOracle(w, memory, args, values) for w in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, fault)
                for model in models[1:]: self.assertEqual((model.memory, model.events, model.r), (models[0].memory, models[0].events, models[0].r))
                self.assertEqual(models[0].f, models[2].f); faults += 1
        self.receipt('rebases-faults', symbol_links=2, cases=cases, fault_triplets=faults, all_fired=True,
            guarded_all_state_exact=True, raw_scratch_FPR_allocation_only=True, no_portable_fault_FCSR_claim=True)

    def test_06_effective_semantic_and_stale_guard_controls(self):
        controls = (
            ('wrong-mask', screen.SELECTED.replace('mask = 0x80', 'mask = 0xFF')),
            ('wrong-bias', screen.SELECTED.replace('bias = 0x7F', 'bias = 0')),
            ('overwrite', screen.SELECTED.replace('[18 + index] *=', '[18 + index] =')),
            ('lost-acceleration', screen.SELECTED.replace('[24] = D_80098924', '[24] = 0.0f')),
            ('wrong-angular', screen.SELECTED.replace('- 0x80', '- 0x7F')))
        for name, body in controls:
            self.assertNotEqual(body, screen.SELECTED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            args = (RECORD, bits(2), bits(3), 1); values = (0, 127, 128, 255, 1, 0)
            model = ImpulseOracle(words, fixture(), args, values, start=screen.ENTRY).run()
            self.assertNotEqual(public(model.memory), public(Reference(fixture(), args, values).run().memory), name)
        wrong = self.out/'wrong-guards'; wrong.write_bytes(self.isolated_guards.read_bytes().replace(b'0x46006302', b'0x46006303'))
        with self.assertRaises(ValueError): emit_padded_assembly(self.out/'selected.o', self.out/'slot.s', word_patches_path=wrong, filename='generated_6B320')
        self.receipt('controls', fresh_semantic=5, all_effective=True, stale_expected_word_rejected=True)

    def test_07_complete_owner_typed_callers_and_both_padders(self):
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
            expected[start:start+296] = parsed[1][0][start:start+296]; self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o: r for o, r in parsed[0][2].items() if not start <= o < start+296},
                {o: r for o, r in parsed[1][2].items() if not start <= o < start+296})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1]); self.receipt('owner', unchanged_neighbors=len(names)-1,
            both_padders=True, pools_exact=True, callers13_11_12_unchanged=True, callback_types_pointer_s32=True)

    def test_08_literal_source_ELF_guards_and_six_inputs(self):
        before_source = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text(); now = current != before_source
        self.assertEqual(current, screen.install(before_source) if now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 296); extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 28)
        if now:
            struct.pack_into('>74I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 296)
            expected, _, _ = rotated_symbol_tables(expected)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            if name == 'guards': self.assertEqual((self.root/path).read_bytes(),
                screen.guard_successor((self.out/'before-guards').read_bytes()) if now else (self.out/('before-guards')).read_bytes())
            elif name not in ('source', 'elf'): self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes(), name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+296], actual[start:start+296])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), explicit_four_entry_symbol_string_rotation=True,
            metadata_bytes=sum(a != b for a, b in zip(self.before, actual))-
                sum(a != b for a, b in zip(self.before[start:start+296], actual[start:start+296]))-
                sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            literal_every_other_byte_exact_no_generic_exception=True,
            guard_prefix_plus_five_rows=True, six_other_inputs_exact=True, protected_data=data)

    def test_09_effective_install_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for stale in (screen.install(before), before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        with self.assertRaises(AssertionError): screen.guard_successor(self.guards.read_bytes())
        rt, rb = Path.read_text, Path.read_bytes; source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: actual+'\n' if p == source else rt(p, *a, **k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_ELF_guards_and_six_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes(); start = elf_slot_offset(actual, screen.ENTRY, 296)
        _, symbol_start, string_start = rotated_symbol_tables(self.before)
        for offset in (start+4, start+72, start+296, installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)+3,
                symbol_start+4, symbol_start+15, string_start+8, string_start+44):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_ELF_guards_and_six_inputs()
        guards = self.root/self.paths['guards']; wrong = guards.read_bytes()+b'\n'
        with patch.object(Path, 'read_bytes', lambda p: wrong if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_ELF_guards_and_six_inputs()
        self.receipt('integrity-controls', stale_installs=2, duplicate_guards=1, source=1, ELF=8, guards=1, all_effective=True)

    def test_10_actual_three_callers_to_impulse_to_rng(self):
        cases = 0
        table = self.rom[0x2275E0+0x80084430-0x80082B20:0x2275E0+0x80084430-0x80082B20+12]
        self.assertEqual(struct.unpack('>3I', table), tuple(a for a, *_ in CALLERS))
        for entry, rom, n, horizontal, vertical, mode in CALLERS:
            body = list(struct.unpack_from('>%dI' % n, self.before, elf_slot_offset(self.before, entry, n*4)))
            self.assertEqual(body, list(struct.unpack_from('>%dI' % n, self.rom, rom)))
            for seed, phase, unused in itertools.product(rng.SEEDS, (0, 8), (0, 255, 256, 0xFFFFFFFF)):
                memory = fixture(seed=seed); args = (RECORD, horizontal, vertical, mode)
                expected = Reference(memory, args, (), phase=phase, actual=True, home=STACK+phase-24).run()
                models = []
                for words in (self.retail, self.raw, self.padded):
                    connected = {screen.ENTRY+i*4: w for i, w in enumerate(words)}
                    connected.update({RANDOM+i*4: w for i, w in enumerate(self.random)})
                    model = ImpulseOracle(body, memory, (RECORD, unused), (), phase=phase, start=entry,
                        connected=connected, actual=True).run(); models.append(model)
                    self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
                    self.assertEqual(model.callbacks, [(screen.ENTRY, *args)])
                for model in models[1:]: self.assertEqual((model.memory, model.events), (models[0].memory, models[0].events))
                self.assertEqual((models[0].r, models[0].f), (models[2].r, models[2].f)); cases += 1
        self.receipt('connected-callers', cases=cases, actual_callback_table=True,
            callers13_11_12_impulse74_rng18=True, full_unused_callback_argument=True, not_gameplay_acceptance=True)

    def test_11_native32_profiles_and_effective_controls(self):
        prefix = r'''
typedef unsigned u32; typedef int s32; typedef float f32; typedef struct { u32 words[26]; } struct04;
f32 D_80098920,D_80098924;
static struct04 records[3],expected[3]; static u32 draws[6]; static int number,mutate;
s32 func_150ADA20(void) {
    int i=number++;
    if(mutate) { ((f32 *)&records[0])[18+i%3]=11.5f; D_80098920=9.0f; D_80098924=-7.0f; }
    return (s32)draws[i];
}
static void initialize(int byte,int action) {
    mutate=action; number=0; D_80098920=0.027450980618596077f; D_80098924=-0.3f;
    for(int i=0;i<6;i++) draws[i]=0xABCD0000u|((byte+i*53)&255);
    for(int r=0;r<3;r++) {
        for(int j=0;j<26;j++) records[r].words[j]=0x35353535;
        for(int j=0;j<7;j++) ((f32 *)&records[r])[18+j]=(j-2)*1.25f;
    }
}
static void reference(struct04 *record,f32 h,f32 v,s32 mode) {
    f32 coefficients[3]={h*D_80098920,v*D_80098920,h*D_80098920};
    for(int i=0;i<3;i++) {
        int value=func_150ADA20(); f32 coefficient=coefficients[i],old=((f32 *)record)[18+i];
        f32 product=((value&(mode?128:255))+(mode?127:0))*coefficient;
        f32 factor=product+2.0f; ((f32 *)record)[18+i]=old*factor;
    }
    for(int i=0;i<3;i++) ((f32 *)record)[21+i]=((func_150ADA20()&255)-128)*0.03125f;
    ((f32 *)record)[24]=D_80098924;
}
'''
        callbacks = '\n'.join('void func_%X(struct04 *record,s32 unused) { func_1503EB78(record,%sf,%sf,%d); }' %
            (a, ('2.0','1.0','2.06')[i], ('2.0','2.0','3.0')[i], mode) for i, (a, _, _, _, _, mode) in enumerate(CALLERS))
        suffix = r'''
static void (*table[3])(struct04 *,s32)={func_1503F078,func_1503F0AC,func_1503F0D8};
static int run(u32 *failure) {
    const s32 modes[5]={0,1,-1,256,(s32)0x80000000u}; const f32 horizontal[4]={0.0f,-0.0f,2.06f,-3.25f};
    unsigned cases=0;
    for(int byte=0;byte<256;byte++) for(int m=0;m<5;m++) for(int h=0;h<4;h++) for(int action=0;action<2;action++) {
        initialize(byte,action); reference(&records[0],horizontal[h],3.0f,modes[m]);
        for(int r=0;r<3;r++) for(int j=0;j<26;j++) expected[r].words[j]=records[r].words[j];
        initialize(byte,action); func_1503EB78(&records[0],horizontal[h],3.0f,modes[m]); cases++;
        for(int r=0;r<3;r++) for(int j=0;j<26;j++) if(expected[r].words[j]!=records[r].words[j]) {
            failure[0]=cases; failure[1]=r*26+j; failure[2]=records[r].words[j]; return 1;
        }
        if(number!=6) return 3;
    }
    for(int byte=0;byte<256;byte++) for(int c=0;c<3;c++) for(int u=0;u<3;u++) {
        initialize(byte,0); reference(&records[0],c==1?1.0f:c==2?2.06f:2.0f,c==2?3.0f:2.0f,c!=0);
        for(int r=0;r<3;r++) for(int j=0;j<26;j++) expected[r].words[j]=records[r].words[j];
        initialize(byte,0); table[c](&records[0],u==0?0:u==1?256:-1); cases++;
        for(int r=0;r<3;r++) for(int j=0;j<26;j++) if(expected[r].words[j]!=records[r].words[j]) {
            failure[0]=cases; failure[1]=r*26+j; failure[2]=records[r].words[j]; return 1;
        }
        if(number!=6) return 3;
    }
    return cases==12544?0:2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result==1) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        for profile in ('-O2', '-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:], prefix+screen.SELECTED+callbacks+suffix, profile), (0, ''))
        for name, body in (('mask', screen.SELECTED.replace('mask = 0x80', 'mask = 0xFF')),
                ('overwrite', screen.SELECTED.replace('[18 + index] *=', '[18 + index] =')),
                ('acceleration', screen.SELECTED.replace('[24] = D_80098924', '[24] = 0.0f'))):
            result, detail = self.run_native('native-negative-'+name, prefix+body+callbacks+suffix)
            self.assertEqual(result, 1); self.assertEqual(len(detail), 3)
        self.receipt('native', cases_per_profile=12544, profiles=['O2','O0'], all_record_words=True,
            callbacks_pointer_s32=True, six_draws=True, live_velocity_acceleration_mutations=True,
            effective_controls=3, no_private_alias_FCSR_claim=True)

    def test_12_float_payload_boundaries(self):
        cases = 0
        for horizontal, vertical, scale, mode, phase in itertools.product(
                (0, 0x80000000, 1, 0x80000001, bits(1.0000001192092896), bits(-4.25)),
                (bits(3), 0x80000000), (0x3CE0E0E1, 0x80000000), (0, 1), (0, 8)):
            self.compare(fixture(scale=scale), args=(RECORD, horizontal, vertical, mode), phase=phase); cases += 1
        for payload in (0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345, 0x7F7FFFFF):
            memory = fixture(); args = (RECORD, payload, bits(3), 1); values = (0, 127, 128, 255, 1, 0)
            models = [ImpulseOracle(w, memory, args, values).run() for w in (self.retail, self.raw, self.padded)]
            for model in models[1:]: self.assertEqual((model.memory, model.events), (models[0].memory, models[0].events))
            self.assertEqual((models[0].r, models[0].f), (models[2].r, models[2].f)); cases += 1
        self.receipt('float-boundaries', cases=cases, finite_and_signed_zero_subnormal_reference=True,
            infinity_NaN_overflow_machine_forms_only=True, no_hardware_FCSR_proof=True)


if __name__ == '__main__':
    unittest.main()
