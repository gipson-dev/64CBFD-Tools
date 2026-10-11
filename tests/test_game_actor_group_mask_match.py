"""Direct actor mask command, actual helper/callers and literal linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_group_mask_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed

STACK, RECORDS, PAIR = guest.STACK, 0x800C6660, 0x24000
CURRENT, GROUP, ENTRY_BYTE = 0x800D154C, 0x800D1890, 0x800D1891
HELPER = screen.SYMBOLS['func_1503DF0C']
LINKS = ((screen.ENTRY, screen.SYMBOLS),
    (0x15207FFC, dict(D_800CC2D0=0x80107FFC, D_8008446C=0x80118004, func_1503DF0C=0x15218004)),
    (0x15308004, dict(D_800CC2D0=0x80218004, D_8008446C=0x80207FFC, func_1503DF0C=0x15327FFC)))
CALLERS = ((0x1507DB44, 8, 'conker/src/game_A9D90.c'),
    (0x150772E8, 12, 'conker/src/game_A28B0.c'), (0x1507A270, 13, 'conker/src/game_A28B0.c'))


def slot_index(actor, base):
    difference = signed((actor - base) & 0xFFFFFFFF)
    return (abs(difference) // 0x32C) * (-1 if difference < 0 else 1)


def location(base, index, stride):
    return (base + (index & 0xFFFFFFFF) * stride) & 0xFFFFFFFF


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x100 <= a < STACK + 0x100}


def events(model):
    return [e for e in model.events if e[0] == 'CALL' or not STACK - 0x100 <= e[1] < STACK + 0x100]


def fixture(delta=7*0x32C, group=3, entry=2, pattern=0, symbols=screen.SYMBOLS, alias=0):
    actor = (symbols['D_800CC2D0'] + delta) & 0xFFFFFFFF
    record = location(RECORDS, slot_index(actor, symbols['D_800CC2D0']), 16)
    memory = {STACK+i: 0xA5 for i in range(-0x100, 0x100)}
    memory.update({record+i: (i*19+0x35) & 255 for i in range(-16, 32)})
    pair = record + alias if alias else PAIR
    values = ((0, 0xFFFFFFFF), (0x80000000, 0x12345678), (0xA5A5A5A5, 0x5A5A5A5A))[pattern]
    if entry != -1:
        table = location(symbols['D_8008446C'], group, 4)
        put(memory, table, (pair-entry*8) & 0xFFFFFFFF)
        put(memory, pair, values[0]); put(memory, pair+4, values[1])
    put(memory, CURRENT, actor); put(memory, GROUP, group, 1); put(memory, ENTRY_BYTE, entry, 1)
    return memory, actor


def reference(memory, actor, group, entry, symbols=screen.SYMBOLS, actual=True):
    state, trace = memory.copy(), []
    def get(address):
        value = read(state, address, 4); trace.append(('R', address, 4, value)); return value
    def store(address, value, size=4):
        put(state, address, value, size); trace.append(('W', address, size, value & ((1 << (size*8))-1)))
    index = slot_index(actor, symbols['D_800CC2D0'])
    if entry != -1:
        pair = location(get(location(symbols['D_8008446C'], group, 4)), entry, 8)
        masks = (get(pair), get((pair+4) & 0xFFFFFFFF))
    else:
        masks = (0xFFFFFFFF, 0xFFFFFFFF)
    args = (index & 0xFFFFFFFF, group & 0xFFFFFFFF, *masks)
    trace.append(('CALL', symbols['func_1503DF0C'], args))
    if actual:
        record = location(RECORDS, index, 16)
        first, second = get(record+4), get(record+8)
        store(record+4, first | masks[0]); store(record+8, second | masks[1])
        store(record+14, group, 1); store(record+15, 2, 1)
    return state, trace, args


class MaskOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, actor, group, entry, phase=0, start=screen.ENTRY,
            symbols=screen.SYMBOLS, connected=None):
        super().__init__(words, memory, arguments=(actor & 0xFFFFFFFF, group & 0xFFFFFFFF,
            entry & 0xFFFFFFFF, 0x81234567), phase=phase, entry=start, connected=connected)
        self.symbols = symbols
    def execute(self, word):
        if word >> 26 == 32:
            rs, rt, imm = word >> 21 & 31, word >> 16 & 31, word & 65535
            address = (self.r[rs] + (imm if imm < 32768 else imm-65536)) & 0xFFFFFFFF
            value = self.get(address, 1)
            self.r[rt] = (value if value < 128 else value-256) & 0xFFFFFFFF
        else:
            super().execute(word)
    def record_call(self, target):
        assert target in (screen.ENTRY, self.symbols['func_1503DF0C']), hex(target)
        args = tuple(self.r[4:7 if target == screen.ENTRY else 8])
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
    def hook(self, target):
        assert target == self.symbols['func_1503DF0C']
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register


class GameActorGroupMaskMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-actor-group-mask-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
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
        assert cls.baseline['source'] == 'ba7ca1c269efca89aa7fd0b81d13403e032927a1d4e67f8238df80e72435a03f'
        assert cls.baseline['elf'] == '9f2c45ce2994dafadbaa9bce9c640e61852b6f2ebf4d2a34a41d1d1438bbcb25'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>39I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        source = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1]
        body = source.split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot))
        cls.helper_source = (cls.out/'before-source').read_text().split('void func_1503DF0C(', 1)[1]
        cls.helper_source = 'void func_1503DF0C('+cls.helper_source.split('\n}\n', 1)[0]+'\n}'
        cls.helper = list(struct.unpack_from('>15I', cls.before, elf_slot_offset(cls.before, HELPER, 60)))
        assert cls.helper == list(struct.unpack_from('>15I', cls.rom, screen.ROM+156))
        cls.connected = {HELPER+i*4: w for i, w in enumerate(cls.helper)}

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def link(self, name, start=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        data = sections(elf)['.text'][1]
        size = parse_object(self.out/(name+'.o'))[1][screen.FUNCTION]['size']
        return list(struct.unpack_from('>%dI' % (size//4), data))[:39]

    def compare(self, memory, actor, group, entry, phase=0, forms=None, start=screen.ENTRY,
            symbols=screen.SYMBOLS, actual=True):
        expected, trace, args = reference(memory, actor, group, entry, symbols, actual)
        models = [MaskOracle(words, memory, actor, group, entry, phase, start, symbols,
            self.connected if actual else None).run() for words in (forms or (self.retail, self.raw, self.padded))]
        for model in models:
            self.assertEqual((public(model.memory), events(model), model.calls),
                (public(expected), trace, [(symbols['func_1503DF0C'], *args)]))
        for model in models[1:]:
            self.assertEqual((model.memory, model.events, model.r, model.lo),
                (models[0].memory, models[0].events, models[0].r, models[0].lo))
        return models

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'):
            type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def test_01_direct_body_profiles_extent_and_real_helper(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (39, 24, 0))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual(self.raw, self.retail); self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.retail)
        meta, words = screen.compile_candidate(self.root, self.out, 'compact', profile='compact')
        self.assertEqual((meta['body_words'], meta['differences'], words), (39, 0, self.retail))
        with patch.multiple(screen.compiler, ENTRY=HELPER, ROM=screen.ROM+156, WORDS=15,
                FUNCTION='func_1503DF0C', RECORD='', DECLARATIONS='#include "variables.h"\n',
                SYMBOLS=dict(D_800C6660=RECORDS)):
            meta, words = screen.compiler.compile_candidate(self.root, self.out, 'actual-helper', self.helper_source)
        self.assertEqual((meta['body_words'], meta['differences'], words), (15, 0, self.helper))
        self.assertEqual(self.raw[24], 0x8C470004)
        self.receipt('shape', direct_words=39, helper_direct_words=15, frame=24, extent=156,
            new_guards=0, owner_and_compact_diagnostic_profiles_exact=True, call_delay_reads_second_mask=True)

    def test_02_full_width_signed_slot_and_entry_group_matrix(self):
        cases, reached = 0, set()
        for delta, group, entry, pattern, phase in itertools.product(
                (0, 7*812, 25*812, -812, -811, -813, 811, 813, 0x7FFFFFFF, -0x80000000),
                (0, 3, 255, 256, -1, 0x80000000), (-1, 0, 2, -2, 0x7FFFFFFF, -0x80000000), range(3), (0, 8)):
            memory, actor = fixture(delta, group, entry, pattern)
            models = self.compare(memory, actor, group, entry, phase)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+156, 4))), 39)
        self.assertEqual(len(reached & set(self.connected)), 15)
        self.receipt('guest', cases=cases, forms=3, wrapper_words=39, helper_words=15,
            invalid_values_mapped_guest_only=True, no_actor_dereference=True, signed_division_truncates_toward_zero=True)

    def test_03_sentinel_no_table_and_live_pair_aliases(self):
        cases = 0
        for group, alias, entry, phase in itertools.product((3, 255, 256), (4, 8, 12), (-1, 2), (0, 8)):
            memory, actor = fixture(group=group, entry=entry, alias=alias)
            models = self.compare(memory, actor, group, entry, phase); cases += 1
            if entry == -1:
                self.assertNotIn(location(screen.SYMBOLS['D_8008446C'], group, 4), public(memory))
                self.assertEqual(len([e for e in events(models[0]) if e[0] == 'R']), 2)
        self.receipt('aliases', cases=cases, actual_helper=True, both_masks_loaded_before_helper_writes=True,
            sentinel_never_reads_group_pointer=True)

    def test_04_independent_relocations_and_call_clobber(self):
        cases = 0
        for start, symbols in LINKS:
            raw, original, padded = (self.link(name, start, symbols) for name in ('selected', 'original', 'padded'))
            self.assertEqual(raw, original); self.assertEqual(raw, padded)
            for delta, group, entry, phase in itertools.product((0, -813, 25*812), (0, 256), (-1, 2), (0, 8)):
                memory, actor = fixture(delta, group, entry, symbols=symbols)
                self.compare(memory, actor, group, entry, phase, (original, raw, padded), start, symbols, actual=False)
                cases += 1
        self.receipt('rebases', links=len(LINKS), cases=cases, carry_crossing_hi_lo=True,
            helper_hook_clobbers_all_caller_saved_GPRs=True, actual_helper_separately_executed=True)

    def test_05_fired_private_and_public_access_fault_prefixes(self):
        pairs = 0
        for entry, phase in itertools.product((-1, 2), (0, 8)):
            memory, actor = fixture(entry=entry)
            complete = MaskOracle(self.retail, memory, actor, 3, entry, phase, connected=self.connected).run()
            for failure in range(complete.accesses):
                models = [MaskOracle(words, memory, actor, 3, entry, phase, connected=self.connected)
                    for words in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = failure
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, failure)
                for model in models[1:]:
                    self.assertEqual((model.memory, model.events, model.r, model.lo),
                        (models[0].memory, models[0].events, models[0].r, models[0].lo)); pairs += 1
        self.receipt('faults', fired_comparison_pairs=pairs, includes_private_homes_and_public_mask_reads_writes=True,
            guest_fault_prefix_not_portable_C_fault_semantics=True)

    def test_06_effective_fresh_semantic_controls(self):
        controls = (('wrong-stride', screen.SELECTED.replace('/ (s32)sizeof(struct127)', '/ 0x330'), -1),
            ('wrong-sentinel', screen.SELECTED.replace('entry != -1', 'entry >= 0'), -2),
            ('wrong-second-mask', screen.SELECTED.replace('[entry][1]', '[entry][0]'), 2),
            ('wrong-all-mask', screen.SELECTED.replace('group, -1, -1', 'group, 0, -1'), -1))
        for name, body, entry in controls:
            _, words = screen.compile_candidate(self.root, self.out, name, body)
            memory, actor = fixture(delta=-813, entry=entry, pattern=1)
            with self.assertRaises(AssertionError): self.compare(memory, actor, 3, entry, forms=(words,))
        self.receipt('controls', freshly_compiled_mutations=len(controls), all_effective=True)

    def test_07_copied_owner_all_neighbors_pools_and_both_real_padders(self):
        before = (self.out/'before-source').read_text(); objects = {}
        for stage, source in (('before', before), ('after', screen.install(before))):
            obj, warnings = compile_owner(self.root, self.out, source, 'owner-'+stage)
            subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')), '--post-process',
                str(obj.relative_to(self.root/'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker',
                check=True, capture_output=True)
            self.assertEqual(warnings, []); objects[stage] = obj
        def fingerprint(obj, name):
            text, functions, relocations = parse_object(obj); item = functions[name]
            start, end = item['value'], item['value']+item['size']
            return item['size'], text[start:end], {o-start: r for o, r in relocations.items() if start <= o < end}
        names = set(parse_object(objects['before'])[1]); self.assertEqual(names, set(parse_object(objects['after'])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(objects['before'], name), fingerprint(objects['after'], name), name)
        self.assertEqual(normalized_pools(objects['before']), normalized_pools(objects['after']))
        self.assertEqual(fingerprint(objects['after'], screen.FUNCTION), fingerprint(self.out/'selected.o', screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py', 'pad_generated_object.py'):
            parsed = []
            for stage in ('before', 'after'):
                asm = self.out/(route+'-'+stage+'.s')
                args = [str(objects[stage]), str(self.out/'before-layout'), 'generated_6B320', str(asm)] if route == 'pad_c_object.py' else [
                    str(objects[stage]), str(self.root/'conker/asm/6B320.s'), str(asm), '--filename', 'generated_6B320']
                subprocess.run(['python3', str(self.root/'tools'/route), *args,
                    '--word-patches', str(self.out/'before-guards')], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)],
                    check=True, capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+156] = parsed[1][0][start:start+156]
            self.assertEqual(bytes(expected), parsed[1][0])
            self.assertEqual({o: v for o, v in parsed[0][2].items() if not start <= o < start+156},
                {o: v for o, v in parsed[1][2].items() if not start <= o < start+156})
            routes.append(parsed[1])
        self.assertEqual(routes[0], routes[1])
        self.receipt('owner', neighbors=len(names)-1, real_padders=2, warnings=0, other_bytes_extents_relocations_pools_exact=True)

    def test_08_literal_whole_ELF_and_every_assignment_input(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
        before_source = (self.out/'before-source').read_text(); actual_source = (self.root/screen.SOURCE).read_text()
        now = actual_source != before_source
        self.assertEqual(actual_source, screen.install(before_source) if now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 156)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if now:
            struct.pack_into('>39I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 156)
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            if name not in ('source', 'elf'):
                self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes(), name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, changed_ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+156], actual[start:start+156])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(), other_seven_inputs_exact=True,
            literal_no_projection_or_metadata_exception=True, protected_data=data)

    def test_09_native32_actual_helper_and_byte_domain(self):
        for profile in ('-O2', '-O0'):
            code, detail = self.run_native('native-'+profile[1:], NATIVE+screen.SELECTED+'\n'+self.helper_source+NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''))
        code, _ = self.run_native('native-negative', NATIVE+screen.SELECTED.replace('[entry][1]', '[entry][0]')+'\n'+self.helper_source+NATIVE_MAIN)
        self.assertNotEqual(code, 0)
        self.receipt('native', profiles=['O2', 'O0'], cases=256*256*3, aliases=9, valid_actor_slots=26,
            full_group_and_signed_entry_byte_domains=True, actual_helper_C=True, effective_second_mask_control=True,
            native32_valid_fixtures_not_invalid_guest_or_portable64_or_hardware=True)

    def test_10_actual_three_callers_with_wrapper_and_helper_hooks_removed(self):
        cases, reached = 0, set()
        for start, count, source_path in CALLERS:
            name = 'func_%08X' % start
            text = (self.root/source_path).read_text(); body = text.split('void '+name+'(', 1)[1].split('\n}', 1)[0]
            body = 'void '+name+'('+body+'\n}'
            symbols = dict(func_1503DE70=screen.ENTRY, D_800D154C=CURRENT, D_800D1890=GROUP, D_800D1891=ENTRY_BYTE)
            with patch.multiple(screen.compiler, ENTRY=start, ROM=start-0x15000000+0x2D4B0, WORDS=count,
                    FUNCTION=name, RECORD='', DECLARATIONS='#include "variables.h"\nvoid func_1503DE70();\n', SYMBOLS=symbols):
                meta, words = screen.compiler.compile_candidate(self.root, self.out, name, body)
            retail = list(struct.unpack_from('>%dI' % count, self.rom, start-0x15000000+0x2D4B0))
            self.assertEqual(words, retail); self.assertEqual(meta['differences'], 0)
            self.assertEqual(list(struct.unpack_from('>%dI' % count, self.before, elf_slot_offset(self.before, start, count*4))), retail)
            for slot, group, byte, phase in itertools.product((0, 7, 25), (0, 3, 255), (0, 2, 127, 128, 254, 255), (0, 8)):
                entry = (byte if byte < 128 else byte-256) if start == 0x1507A270 else -1
                memory, actor = fixture(slot*812, group, entry)
                put(memory, ENTRY_BYTE, byte, 1)
                expected, _, args = reference(memory, actor, group, entry)
                models = []
                for wrapper in (self.retail, self.raw):
                    connected = dict(self.connected); connected.update({screen.ENTRY+i*4: w for i, w in enumerate(wrapper)})
                    model = MaskOracle(words, memory, actor, group, entry, phase, start, connected=connected).run()
                    self.assertEqual(public(model.memory), public(expected))
                    self.assertEqual(model.calls, [(screen.ENTRY, actor, group, entry & 0xFFFFFFFF), (HELPER, *args)])
                    reached.update(model.visits); models.append(model)
                self.assertEqual((models[0].memory, models[0].events, models[0].r),
                    (models[1].memory, models[1].events, models[1].r)); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+156, 4))), 39)
        self.assertEqual(len(reached & set(self.connected)), 15)
        self.assertEqual(sum(len(set(range(a, a+n*4, 4)) & reached) for a, n, _ in CALLERS), 33)
        self.receipt('callers', callers=3, cases=cases, forms=2, wrapper_hook_removed=True,
            helper_hook_removed=True, all_wrapper_words=39, helper_words=15,
            complete_callers_reached=sum(len(set(range(a, a+n*4, 4)) & reached) for a, n, _ in CALLERS))

    def test_11_effective_literal_audit_and_stale_install_controls(self):
        before = (self.out/'before-source').read_text()
        qualified = screen.install(before)
        source_path, elf_path, guard_path = (self.root/self.paths[n] for n in ('source', 'elf', 'guards'))
        text_reader, byte_reader = Path.read_text, Path.read_bytes
        actual_source = source_path.read_text()
        for wrong in (actual_source+'\n', actual_source.replace(screen.FUNCTION, 'func_1503DE71', 1)):
            with patch.object(Path, 'read_text', lambda p, *a, **k: wrong if p == source_path else text_reader(p, *a, **k)):
                with self.assertRaises(AssertionError): self.test_08_literal_whole_ELF_and_every_assignment_input()
        actual = elf_path.read_bytes()
        start = elf_slot_offset(actual, screen.ENTRY, 156)
        extent = installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)
        for offset in (start+4, start+156, extent+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf_path else byte_reader(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_whole_ELF_and_every_assignment_input()
        wrong = bytearray(guard_path.read_bytes()); wrong[0] ^= 1
        with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == guard_path else byte_reader(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_whole_ELF_and_every_assignment_input()
        for stale in (qualified, before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        self.receipt('integrity-controls', source_rejections=2, word_neighbor_extent_rejections=3,
            guard_rejections=1, stale_installer_rejections=2, all_effective=True, production_inputs_not_mutated=True)


NATIVE = r'''
typedef unsigned char u8; typedef int s32; typedef unsigned int u32;
typedef struct {u8 bytes[0x32C];} struct127;
typedef struct {s32 unk0,unk4,unk8;u8 pad[3],unkF;} struct106;
struct127 D_800CC2D0[26]; struct106 D_800C6660[26]; s32 *D_8008446C[256];
static s32 pairs[256][256][2]; static struct106 expected[26];
typedef char widths[(sizeof(void *)==4 && sizeof(struct127)==812 && sizeof(struct106)==16)?1:-1];
void func_1503DF0C(s32,s32,s32,s32);
static void copy(u8 *to,const u8 *from,u32 n){u32 i;for(i=0;i<n;i++)to[i]=from[i];}
static int report(u32 code,u32 c,u32 i){u32 data[3]={code,c,i};s32 result;
__asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");return (s32)code;}
'''

NATIVE_MAIN = r'''
int run(void) {
    u32 group,byte,pattern,i,c=0,slot,first,second; s32 entry;
    for(group=0;group<256;group++) {
        D_8008446C[group]=(s32 *)(pairs[group]+128);
        for(byte=0;byte<256;byte++) {
            entry=byte<128?(s32)byte:(s32)byte-256;
            pairs[group][entry+128][0]=(s32)(0x80000000U ^ (group*0x10203U+byte));
            pairs[group][entry+128][1]=(s32)(0x12345678U ^ (byte*0xABCDEU+group));
            for(pattern=0;pattern<3;pattern++,c++) {
                slot=(group+byte+pattern)%26;
                for(i=0;i<sizeof(D_800C6660);i++)((u8 *)D_800C6660)[i]=(u8)(i*19+pattern*17);
                copy((u8 *)expected,(u8 *)D_800C6660,sizeof(expected));
                first=entry==-1?0xFFFFFFFFU:(u32)pairs[group][entry+128][0];
                second=entry==-1?0xFFFFFFFFU:(u32)pairs[group][entry+128][1];
                expected[slot].unk4=(s32)((u32)expected[slot].unk4|first);
                expected[slot].unk8=(s32)((u32)expected[slot].unk8|second);
                ((u8 *)(expected+slot))[14]=(u8)group;expected[slot].unkF=2;
                func_1503DE70(D_800CC2D0+slot,(s32)group,entry);
                for(i=0;i<sizeof(expected);i++)if(((u8 *)expected)[i]!=((u8 *)D_800C6660)[i])return report(1,c,i);
            }
        }
    }
    for(slot=0;slot<3;slot++)for(pattern=4;pattern<=12;pattern+=4,c++) {
        s32 *pair=(s32 *)((u8 *)(D_800C6660+slot)+pattern);
        for(i=0;i<sizeof(D_800C6660);i++)((u8 *)D_800C6660)[i]=(u8)(i*19+pattern);
        D_8008446C[3]=pair;
        copy((u8 *)expected,(u8 *)D_800C6660,sizeof(expected));
        first=(u32)pair[0];second=(u32)pair[1];
        expected[slot].unk4=(s32)((u32)expected[slot].unk4|first);
        expected[slot].unk8=(s32)((u32)expected[slot].unk8|second);
        ((u8 *)(expected+slot))[14]=3;expected[slot].unkF=2;
        func_1503DE70(D_800CC2D0+slot,3,0);
        for(i=0;i<sizeof(expected);i++)if(((u8 *)expected)[i]!=((u8 *)D_800C6660)[i])return report(2,c,i);
    }
    return 0;
}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''
