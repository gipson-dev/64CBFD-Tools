"""Full record dispatcher, callback lifetimes and literal linked-only audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_state_dispatch_candidates as screen
from tools.experiments import game_actor_update_dispatch_candidates as caller
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_actor_update_dispatch_match as dispatch
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, BUFFER, OTHER, TYPES = guest.STACK, 0x24000, 0x34000, 0x50000
CALLER, HELPER = 0x1502BD84, 0x1503E1F4
CALLBACKS = {label: {group: 0x15180000+kind*0x1000+group*4 for group in range(256)}
    for kind, label in enumerate(('element', 'finish', 'active'))}
LABELS = {screen.SYMBOLS[name]: label for name, label in (
    ('allocate_memory', 'allocate'), ('func_1503E1F4', 'predicate'), ('func_1503E3C4', 'setup'),
    ('func_1503EA54', 'tail1'), ('func_1503E82C', 'tail2'))}
LABELS.update({target: label for label, rows in CALLBACKS.items() for target in rows.values()})
COUNTS = dict(allocate=4, predicate=2, setup=5, element=2, finish=1, active=1, tail1=1, tail2=1)


def address(base, slot, stride):
    return (base+(slot & 0xFFFFFFFF)*stride) & 0xFFFFFFFF


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x200 <= a < STACK+0x100}


def writes(model):
    return [e for e in model.events if e[0] == 'W' and not STACK-0x200 <= e[1] < STACK+0x100]


def fixture(state=3, count=5, slot=7, group=0, existing=False, actor_ready=True,
        masks=(0xFFFFFFFF, 0xFFFFFFFF), types=None, flag=0, symbols=screen.SYMBOLS, buffer=BUFFER):
    record = address(symbols['D_800C6660'], slot, 16)
    actor = address(symbols['D_800CC2D0'], slot, 812)
    memory = {STACK+i: 0xA5 for i in range(-0x200, 0x100)}
    for base, length in ((record-16, 48), (actor-16, 844),
            (buffer-16, max(count, 5)*104+32), (OTHER-16, max(count, 5)*104+32)):
        memory.update({(base+i) & 0xFFFFFFFF: (i*17+0x35) & 255 for i in range(length)})
    for g in set((group, 0, 1, 2, 255)):
        put(memory, symbols['D_80098914']+g, count, 1)
        put(memory, symbols['D_80084454']+g*4, TYPES+g*256)
        for i in range(256):
            put(memory, TYPES+g*256+i, (types[i % len(types)] if types else (0, 254, 255, 128, 127)[i % 5]), 1)
        for label, name in (('element', 'D_80084430'), ('finish', 'D_8008443C'), ('active', 'D_80084448')):
            put(memory, symbols[name]+g*4, CALLBACKS[label][g])
    put(memory, record, buffer if existing else 0)
    put(memory, record+4, masks[0]); put(memory, record+8, masks[1])
    put(memory, record+14, group, 1); put(memory, record+15, state, 1)
    put(memory, actor+0x74, 0x35, 1); put(memory, actor+0x1D4, 0xABCDEF00 if actor_ready else 0)
    for base in (buffer, OTHER):
        for i in range(max(count, 5)): put(memory, base+i*104+100, flag, 1)
    return memory


def actions_for(mode, slot=7, symbols=screen.SYMBOLS, buffer=BUFFER):
    record = address(symbols['D_800C6660'], slot, 16)
    actor = address(symbols['D_800CC2D0'], slot, 812)
    choices = {
        'allocate-group': {('allocate', 0): ((record+14, 1, 1), (symbols['D_80098914']+1, 0, 1), (record, OTHER, 4))},
        'predicate-pointer': {('predicate', 0): ((record, OTHER, 4),)},
        'predicate-flag': {('predicate', 0): ((buffer+100, 9, 1),)},
        'setup-group': {('setup', 0): ((record+14, 1, 1), (record, OTHER, 4), (record+15, 0, 1))},
        'element-lifetime': {('element', 0): ((record+14, 2, 1), (record, OTHER, 4),
            (buffer+100, 9, 1), (TYPES+1, 0, 1), (symbols['D_80084454'], TYPES+256, 4),
            (symbols['D_80098914'], 0, 1))},
        'finish-state': {('finish', 0): ((record+14, 1, 1), (record+15, 0, 1))},
        'active-clear': {('active', 0): ((record+15, 0, 1),)},
        'tail-clear': {('tail1', 0): ((record+15, 0, 1),)},
        'caller-active-clear': {('active', 0): ((actor, 0, 4),)},
    }
    return choices.get(mode, {})


class Reference:
    def __init__(self, memory, slot=7, symbols=screen.SYMBOLS, actions=None, allocation=BUFFER):
        self.memory, self.events, self.calls = memory.copy(), [], []
        self.slot, self.symbols, self.actions, self.allocation = slot, symbols, actions or {}, allocation
        self.occurrences = {}
    def get(self, a, size=4):
        value = read(self.memory, a, size); self.events.append(('R', a, size, value)); return value
    def put(self, a, value, size=4):
        put(self.memory, a, value, size); self.events.append(('W', a, size, value & ((1 << (size*8))-1)))
    def mutate(self, label):
        n = self.occurrences.get(label, 0); self.occurrences[label] = n+1
        for a, value, size in self.actions.get((label, n), ()): self.put(a, value, size)
    def call(self, target, args):
        args = tuple(v & 0xFFFFFFFF for v in args)
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        label = label_for(target, self.symbols); self.mutate(label)
        if label == 'allocate': return self.allocation
        if label == 'predicate':
            index, slot = args
            record = address(self.symbols['D_800C6660'], slot, 16)
            return int(bool(self.get(record+(4 if index < 32 else 8)) & (1 << (index & 31))))
        return 0xA5000002
    def run(self):
        s, slot = self.symbols, self.slot
        record = address(s['D_800C6660'], slot, 16); actor = address(s['D_800CC2D0'], slot, 812)
        state = self.get(record+15, 1)
        if state == 2:
            flags, ready = self.get(actor+0x74, 1), self.get(actor+0x1D4)
            self.put(actor+0x74, flags | 128, 1); state = 3
            if not ready: return self
        if state == 3:
            group, current = self.get(record+14, 1), self.get(record)
            count = self.get(s['D_80098914']+group, 1)
            if not current:
                buffer = self.call(s['allocate_memory'], (count*104, 1, 0, 0))
                if not buffer: return self
                self.put(record, buffer)
                order = list(range(count % 4))
                for i in range(count % 4, count, 4): order.extend((i+1, i+2, i+3, i))
                for i in order: self.put(buffer+i*104+100, 0, 1)
            group = self.get(record+14, 1)
            types = self.get(s['D_80084454']+group*4)
            for index in range(count):
                if self.get(types+index, 1) == 254: continue
                element = address(self.get(record), index, 104)
                if self.call(s['func_1503E1F4'], (index, slot)) and self.get(element+100, 1) == 0:
                    self.call(s['func_1503E3C4'], (slot, index, 0, element, 0))
                    group = self.get(record+14, 1)
                    self.call(self.get(s['D_80084430']+group*4), (element, slot))
                    self.put(element+100, 1, 1)
            group = self.get(record+14, 1)
            self.call(self.get(s['D_8008443C']+group*4), (slot,))
            state = 1; self.put(record+15, 1, 1)
        if state == 1:
            group = self.get(record+14, 1)
            self.call(self.get(s['D_80084448']+group*4), (slot,))
            if self.get(record+15, 1):
                self.call(s['func_1503EA54'], (slot,)); self.call(s['func_1503E82C'], (slot,))
        return self


def label_for(target, symbols):
    for name, label in (('allocate_memory', 'allocate'), ('func_1503E1F4', 'predicate'),
            ('func_1503E3C4', 'setup'), ('func_1503EA54', 'tail1'), ('func_1503E82C', 'tail2')):
        if target == symbols[name]: return label
    return LABELS[target]


class StateOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, slot=7, symbols=screen.SYMBOLS, phase=0,
            start=screen.ENTRY, connected=None, actions=None, allocation=BUFFER, chain_actor=None):
        arguments = (slot & 0xFFFFFFFF,) if chain_actor is None else (chain_actor, slot & 0xFFFFFFFF)
        super().__init__(words, memory, arguments=arguments, phase=phase, entry=start, connected=connected)
        self.symbols, self.actions, self.allocation = symbols, actions or {}, allocation
        self.occurrences, self.chain_actor = {}, chain_actor
    def execute(self, word):
        if word >> 26 == 32:
            rs, rt, imm = word >> 21 & 31, word >> 16 & 31, word & 65535
            a = (self.r[rs]+(imm if imm < 32768 else imm-65536)) & 0xFFFFFFFF
            value = self.get(a, 1); self.r[rt] = (value if value < 128 else value-256) & 0xFFFFFFFF
        else: super().execute(word)
    def record_call(self, target):
        if target in dispatch.COUNTS and target != screen.ENTRY:
            args = self.arguments(dispatch.COUNTS[target])
        else:
            args = self.arguments(1 if target == screen.ENTRY else COUNTS[label_for(target, self.symbols)])
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        if target == self.symbols['func_1503E1F4']:
            self.mutate('predicate')
    def mutate(self, label):
        n = self.occurrences.get(label, 0); self.occurrences[label] = n+1
        for a, value, size in self.actions.get((label, n), ()): self.put(a, value, size)
    def hook(self, target):
        if self.chain_actor is not None and target in dispatch.COUNTS and target != screen.ENTRY:
            if target == 0x1503A08C: self.put(self.chain_actor+0x1D4, 0xABCDEF00, 4)
            result = 0xA5000002
        else:
            label = label_for(target, self.symbols)
            if label != 'predicate': self.mutate(label)
            result = self.allocation if label == 'allocate' else 0xA5000002
            if label == 'predicate':
                index, slot = self.r[4:6]
                record = address(self.symbols['D_800C6660'], slot, 16)
                result = int(bool(self.get(record+(4 if index < 32 else 8), 4) & (1 << (index & 31))))
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = result


class GameRecordStateDispatchMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-state-dispatch-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, caller='conker/src/game/generated_58F80.c',
            elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s',
            symbols='conker/symbol_addrs.us.txt', undefined='conker/undefined_funcs_auto.txt',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'b8430ca27296d5711b518bc5610a56e48618d16cd4285c2bf15418b16ebd67dc'
        assert cls.baseline['elf'] == '43c9d060b98cb1f8662d6d8e34f84eb9497cf0dfc4be19843595a03a422fac2f'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>171I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        source = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1]
        body = source.split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot))
        cls.helper = list(struct.unpack_from('>27I', cls.before, elf_slot_offset(cls.before, HELPER, 108)))
        assert cls.helper == list(struct.unpack_from('>27I', cls.rom, screen.ROM+684))
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
        return list(struct.unpack_from('>%dI' % (size//4), data))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words

    def compare(self, memory, slot=7, phase=0, actions=None, allocation=BUFFER,
            forms=None, start=screen.ENTRY, symbols=screen.SYMBOLS, actual=True):
        expected = Reference(memory, slot, symbols, actions, allocation).run()
        models = [StateOracle(words, memory, slot, symbols, phase, start,
            self.connected if actual else None, actions, allocation).run()
            for words in (forms or (self.retail, self.raw, self.padded))]
        for model in models:
            self.assertEqual((public(model.memory), model.calls, writes(model)),
                (public(expected.memory), expected.calls, writes(expected)))
        for model in models[1:]:
            self.assertEqual((model.memory, model.events, model.r, model.f, model.lo),
                (models[0].memory, models[0].events, models[0].r, models[0].f, models[0].lo))
        return models

    def test_01_complete_shape_and_profile_discrimination(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (171, 56, 0))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual(self.raw, self.retail); self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.padded, self.retail)
        meta, _ = screen.compile_candidate(self.root, self.out, 'compact', profile='compact')
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (153, 72, 168))
        self.assertEqual(self.raw[142:144], [0x24030001, 0xA2AF000F])
        self.receipt('shape', words=171, extent=684, frame=56, direct=True, no_new_guards=True,
            no_profile_change=True, no_pools=True, compact_negative_profile=[153, 72, 168])

    def test_02_state_byte_domain_and_allocation_gates(self):
        reached, cases = set(), 0
        for state, phase in itertools.product(range(256), (0, 8)):
            models = self.compare(fixture(state=state), phase=phase)
            reached.update(models[0].visits); cases += 1
        for state, ready, existing, allocation, count in itertools.product((1, 2, 3), (False, True),
                (False, True), (0, BUFFER), (0, 1, 4, 5)):
            memory = fixture(state=state, actor_ready=ready, existing=existing, count=count)
            models = self.compare(memory, allocation=allocation); reached.update(models[0].visits); cases += 1
            record = screen.SYMBOLS['D_800C6660']+7*16
            if state == 2 and not ready:
                self.assertEqual(models[0].calls, []); self.assertEqual(models[0].memory[record+15], 2)
            if state == 3 and not existing and not allocation:
                self.assertEqual(len(models[0].calls), 1); self.assertEqual(read(models[0].memory, record, 4), 0)
        for masks, mode in itertools.product(((0, 0), (0xFFFFFFFF, 0xFFFFFFFF)), ('none', 'active-clear')):
            models = self.compare(fixture(count=45, masks=masks), actions=actions_for(mode))
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY, screen.ENTRY+684, 4))), 171)
        self.assertEqual(len(reached & set(self.connected)), 26)  # Retail's unreachable duplicate zero at +0x60.
        self.receipt('states', cases=cases, all_state_bytes=True, target_words_reached=171,
            helper_words_reached=26, helper_words_total=27, full_helper_hook_removed=True)

    def test_03_unsigned_counts_signed_types_masks_and_unrolled_clears(self):
        cases, reached = 0, set()
        for count, existing, flag, masks in itertools.product((0, 1, 3, 4, 5, 27, 31, 45, 127, 128, 255),
                (False, True), (0, 1), ((0, 0), (0xFFFFFFFF, 0xFFFFFFFF), (0x80000001, 0xA5A5A5A5))):
            models = self.compare(fixture(count=count, existing=existing, flag=flag, masks=masks))
            reached.update(models[0].visits); cases += 1
        for slot, group, phase in itertools.product((0, 25, -1, 0x80000000, 0x7FFFFFFF), (0, 2, 255), (0, 8)):
            self.compare(fixture(slot=slot, group=group, count=3, types=(254, 255, 128)), slot=slot, phase=phase); cases += 1
        self.assertEqual(len(reached & set(self.connected)), 26)
        self.receipt('counts', cases=cases, forms=3, counts=[0, 1, 3, 4, 5, 27, 31, 45, 127, 128, 255],
            sentinel_only_signed_minus_two=True, real_helper_MIPS_masked_shift=True,
            invalid_slots_mapped_guest_only=True, unrolled_write_order_checked=True)

    def test_04_callback_live_reads_and_cached_lifetimes(self):
        cases = 0
        for mode, existing, phase in itertools.product(('allocate-group', 'predicate-pointer', 'predicate-flag',
                'setup-group', 'element-lifetime', 'finish-state', 'active-clear', 'tail-clear'), (False, True), (0, 8)):
            models = self.compare(fixture(existing=existing), phase=phase, actions=actions_for(mode)); cases += 1
            if mode == 'tail-clear': self.assertEqual(models[0].calls[-1][0], screen.SYMBOLS['func_1503E82C'])
            if mode == 'setup-group':
                self.assertIn((CALLBACKS['element'][1], BUFFER, 7), models[0].calls)
            if mode == 'predicate-pointer':
                self.assertIn((screen.SYMBOLS['func_1503E3C4'], 7, 0, 0, BUFFER, 0), models[0].calls)
        self.receipt('lifetimes', cases=cases, all_caller_saved_GPR_and_FPR_clobbered_at_external_calls=True,
            count_and_type_base_cached=True, group_pointer_flag_reads_live=True,
            element_computed_before_predicate=True, flag_written_after_callback=True, tails_gate_once=True)

    def test_05_independent_symbol_rebases(self):
        cases = 0
        for link in range(2):
            start = (0x15207FFC, 0x15308004)[link]
            symbols = {name: (0x80107FFC if i % 2 == link else 0x80218004)+i*0x10000
                for i, name in enumerate(screen.SYMBOLS)}
            for i, name in enumerate(('allocate_memory', 'func_1503E1F4', 'func_1503E3C4', 'func_1503EA54', 'func_1503E82C')):
                symbols[name] = 0x15408004+i*0x10000
            forms = tuple(self.link(name, start, symbols) for name in ('original', 'selected', 'padded'))
            self.assertEqual(forms[0], forms[1]); self.assertEqual(forms[0], forms[2])
            for state, phase, mode in itertools.product((1, 2, 3), (0, 8), ('none', 'setup-group', 'tail-clear')):
                self.compare(fixture(state=state, symbols=symbols), phase=phase, symbols=symbols, start=start,
                    actions=actions_for(mode, symbols=symbols), forms=forms, actual=False); cases += 1
        self.receipt('rebases', independently_mapped_symbols=12, links=2, cases=cases,
            HI_LO_carries=True, predicate_boundary_hook_only_for_rebases=True)

    def test_06_effective_access_fault_prefixes(self):
        pairs = 0
        for state, ready, phase in ((2, False, 0), (3, True, 8), (1, True, 0)):
            memory = fixture(state=state, actor_ready=ready, count=1)
            complete = StateOracle(self.retail, memory, phase=phase, connected=self.connected).run()
            for failure in range(complete.accesses):
                models = [StateOracle(words, memory, phase=phase, connected=self.connected)
                    for words in (self.retail, self.raw, self.padded)]
                for model in models:
                    model.fault = failure
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses, failure)
                for model in models[1:]:
                    self.assertEqual((model.memory, model.events, model.r, model.f),
                        (models[0].memory, models[0].events, models[0].r, models[0].f)); pairs += 1
        self.receipt('faults', fired_pairs=pairs, private_and_public=True, not_portable_C_fault_semantics=True)

    def test_07_effective_fresh_semantic_controls(self):
        controls = (
            ('sentinel', screen.SELECTED.replace('case -2:', 'case -1:'), 'none', 3, BUFFER),
            ('lost-actor-flag', screen.SELECTED.replace('unk74 |= 0x80', 'unk74 = 0x80'), 'none', 2, BUFFER),
            ('early-publish', screen.SELECTED.replace('            if (buffer == NULL)',
                '            record->unk0 = 123;\n            if (buffer == NULL)'), 'none', 3, 0),
            ('late-element', screen.SELECTED.replace('element->unk64 == 0',
                '(element = (struct04 *)record->unk0 + index)->unk64 == 0'), 'predicate-pointer', 3, BUFFER),
            ('early-flag', screen.SELECTED.replace('                    D_80084430',
                '                    element->unk64 = 1;\n                    D_80084430').replace(
                '                    element->unk64 = 1;\n                }', '                }'), 'element-lifetime', 3, BUFFER),
            ('repeat-tail-gate', screen.SELECTED.replace('            func_1503E82C(slot);',
                '            if (record->unkF != 0) func_1503E82C(slot);'), 'tail-clear', 3, BUFFER))
        for name, body, mode, state, allocation in controls:
            self.assertNotEqual(body, screen.SELECTED)
            _, words = screen.compile_candidate(self.root, self.out, 'negative-'+name, body)
            with self.assertRaises(AssertionError):
                self.compare(fixture(state=state), forms=(words,), actions=actions_for(mode), allocation=allocation)
        self.receipt('controls', freshly_compiled=6, all_effective=True)

    def compile_complete_owner(self, source, name):
        obj, warnings = compile_owner(self.root, self.out, source, name)
        subprocess.run(['python3', str(self.root/'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
            str((self.out/(name+'.c')).relative_to(self.root/'conker')), '--post-process',
            str(obj.relative_to(self.root/'conker')), '--assembler',
            'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
            '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root/'conker', check=True, capture_output=True)
        self.assertEqual(warnings, [])
        return obj

    def test_08_complete_owners_neighbors_pools_and_both_real_padders(self):
        receipts = []
        for key, owner, asm_name, install in (('source', 'generated_6B320', '6B320', screen.install),
                ('caller', 'generated_58F80', '58F80', screen.install_caller)):
            before = (self.out/('before-'+key)).read_text()
            objects = [self.compile_complete_owner(text, owner+'-'+stage) for stage, text in
                (('before', before), ('after', install(before)))]
            def fingerprint(obj, name):
                text, functions, relocations = parse_object(obj); item = functions[name]
                start, end = item['value'], item['value']+item['size']
                return item['size'], text[start:end], {o-start: r for o, r in relocations.items() if start <= o < end}
            names = set(parse_object(objects[0])[1]); self.assertEqual(names, set(parse_object(objects[1])[1]))
            for name in names-({screen.FUNCTION} if key == 'source' else set()):
                self.assertEqual(fingerprint(objects[0], name), fingerprint(objects[1], name), name)
            self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
            if key == 'source':
                self.assertEqual(fingerprint(objects[1], screen.FUNCTION), fingerprint(self.out/'selected.o', screen.FUNCTION))
            routes = []
            for route in ('pad_c_object.py', 'pad_generated_object.py'):
                parsed = []
                for stage, obj in zip(('before', 'after'), objects):
                    asm = self.out/(owner+'-'+route+'-'+stage+'.s')
                    args = [str(obj), str(self.out/'before-layout'), owner, str(asm)] if route == 'pad_c_object.py' else [
                        str(obj), str(self.root/('conker/asm/'+asm_name+'.s')), str(asm), '--filename', owner]
                    subprocess.run(['python3', str(self.root/'tools'/route), *args, '--word-patches', str(self.out/'before-guards')],
                        check=True, capture_output=True)
                    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(asm.with_suffix('.o')), str(asm)],
                        check=True, capture_output=True)
                    parsed.append(parse_object(asm.with_suffix('.o')))
                expected = bytearray(parsed[0][0]); start, end = 0, 0
                if key == 'source':
                    start = parsed[1][1][screen.FUNCTION]['value']; end = start+684
                    expected[start:end] = parsed[1][0][start:end]
                self.assertEqual(bytes(expected), parsed[1][0])
                self.assertEqual({o: r for o, r in parsed[0][2].items() if not start <= o < end},
                    {o: r for o, r in parsed[1][2].items() if not start <= o < end})
                routes.append(parsed[1])
            self.assertEqual(routes[0], routes[1])
            receipts.append(dict(owner=owner, unchanged_functions=len(names)-(key == 'source'),
                GLOBAL_ASM_postprocessed=True, pools_exact=True, both_padders=True))
        self.receipt('owners', owners=receipts, caller_prototype_only=True)

    def test_09_literal_linked_ELF_and_all_inputs(self):
        before_source = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text()
        now = current != before_source
        self.assertEqual(current, screen.install(before_source) if now else before_source)
        before_caller = (self.out/'before-caller').read_text()
        self.assertEqual((self.root/self.paths['caller']).read_text(), screen.install_caller(before_caller) if now else before_caller)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before, screen.ENTRY, 684)
        extent = installed.symbol_size_offset(self.before, screen.FUNCTION, screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.before, extent)[0], 12)
        if now:
            struct.pack_into('>171I', expected, start, *self.retail); struct.pack_into('>I', expected, extent, 684)
            expected = bytearray(screen.swap_metadata_pair(expected))
        self.assertEqual(bytes(expected), actual)
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(), self.baseline[name])
            if name not in ('source', 'caller', 'elf'):
                self.assertEqual((self.root/path).read_bytes(), (self.out/('before-'+name)).read_bytes(), name)
        data = audit_layout(self.root/self.paths['elf'], self.root/'conker'); self.assertTrue(data['exact'], data)
        self.receipt('linked', installed=now, changed_ELF_bytes=sum(a != b for a, b in zip(self.before, actual)),
            target_bytes=sum(a != b for a, b in zip(self.before[start:start+684], actual[start:start+684])),
            extent_bytes=sum(a != b for a, b in zip(self.before[extent:extent+4], actual[extent:extent+4])),
            metadata_pair_bytes=6 if now else 0,
            ELF_sha256=hashlib.sha256(actual).hexdigest(), literal_no_projection_exact_measured_two_symbol_permutation_only=True,
            all_other_inputs_exact=True,
            protected_data=data)

    def test_10_complete_caller_chain_with_dispatcher_and_predicate_hooks_removed(self):
        _, words = caller.compile_candidate(self.root, self.out, 'actual-caller', caller.BASELINE)
        retail = list(struct.unpack_from('>88I', self.rom, 0x59234)); self.assertEqual(words, retail)
        self.assertEqual(list(struct.unpack_from('>88I', self.before, elf_slot_offset(self.before, CALLER, 352))), retail)
        reached, cases = set(), 0
        for state, allocation, mode, phase in itertools.product((1, 2, 3), (0, BUFFER),
                ('none', 'caller-active-clear'), (0, 8)):
            memory = fixture(state=state, count=4); actor = screen.SYMBOLS['D_800CC2D0']+7*812
            for offset, value, size in ((0, 1, 4), (4, 0, 1), (5, 0, 1), (0xA4, 0, 1),
                    (0xF8, 0, 4), (0x260, 0, 4), (0x1C9, 0, 1)):
                put(memory, actor+offset, value, size)
            actions = actions_for(mode); models = []
            expected_input = memory.copy(); put(expected_input, actor+0x1D4, 0xABCDEF00)
            expected = Reference(expected_input, actions=actions, allocation=allocation).run()
            for target in (self.retail, self.raw, self.padded):
                connected = dict(self.connected); connected.update({screen.ENTRY+i*4: w for i, w in enumerate(target)})
                model = StateOracle(words, memory, phase=phase, start=CALLER, connected=connected,
                    actions=actions, allocation=allocation, chain_actor=actor).run()
                target_calls = [call for call in model.calls if call[0] not in dispatch.COUNTS or call[0] == screen.ENTRY]
                self.assertEqual(target_calls, [(screen.ENTRY, 7), *expected.calls])
                expected_calls = [(0x1502E4C4, 7), (0x1502DF38, 7, 0), (0x1503A08C, actor),
                    (0x150345E4, 7), (0x1503A830, actor), (screen.ENTRY, 7), *expected.calls]
                if read(expected.memory, actor, 4): expected_calls += [(0x1502EEF4, 7), (0x1502F264, 7)]
                self.assertEqual(model.calls, expected_calls)
                self.assertEqual(public(model.memory), public(expected.memory))
                reached.update(model.visits); models.append(model)
            for model in models[1:]:
                self.assertEqual((model.memory, model.events, model.r, model.f),
                    (models[0].memory, models[0].events, models[0].r, models[0].f))
            cases += 1
        self.receipt('caller', cases=cases, forms=3, complete_caller_words=88,
            dispatcher_hook_removed=True, predicate_hook_removed=True,
            target_words_reached=len(reached & set(range(screen.ENTRY, screen.ENTRY+684, 4))),
            other_caller_helpers_allocator_setup_callbacks_and_tails_bounded_models=True)

    def test_11_native32_bounded_callbacks_and_count_state_domains(self):
        for profile in ('-O2', '-O0'):
            code, detail = self.run_native('native-'+profile[1:], NATIVE+screen.SELECTED+NATIVE_MAIN, profile)
            self.assertEqual((code, detail), (0, ''))
        code, _ = self.run_native('native-negative', NATIVE+screen.SELECTED.replace('case -2:', 'case -1:')+NATIVE_MAIN)
        self.assertNotEqual(code, 0)
        self.receipt('native', profiles=['O2', 'O0'], cases=256*2+11*3*2*9,
            native32_valid_slots=True, predicate_defined_unsigned_mask_hook_not_existing_C_helper=True,
            real_predicate_guest_only=True, effective_sentinel_control=True, no_hardware_or_gameplay_claim=True)

    def test_12_effective_stale_install_and_literal_audit_controls(self):
        before = (self.out/'before-source').read_text(); qualified = screen.install(before)
        for stale in (qualified, before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        text_reader, byte_reader = Path.read_text, Path.read_bytes
        source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path, 'read_text', lambda p, *a, **k: actual+'\n' if p == source else text_reader(p, *a, **k)):
            with self.assertRaises(AssertionError): self.test_09_literal_linked_ELF_and_all_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        start = elf_slot_offset(actual, screen.ENTRY, 684)
        extent = installed.symbol_size_offset(actual, screen.FUNCTION, screen.ENTRY)
        pair = screen.metadata_pair(actual)
        for offset in (start+4, start+684, extent+3, pair[0][0]+7, pair[0][1]+8):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path, 'read_bytes', lambda p: bytes(wrong) if p == elf else byte_reader(p)):
                with self.assertRaises(AssertionError): self.test_09_literal_linked_ELF_and_all_inputs()
        guards = self.root/self.paths['guards']; wrong = guards.read_bytes()+b'\n'
        with patch.object(Path, 'read_bytes', lambda p: wrong if p == guards else byte_reader(p)):
            with self.assertRaises(AssertionError): self.test_09_literal_linked_ELF_and_all_inputs()
        self.receipt('integrity-controls', stale_installs=2, source_rejection=1, ELF_rejections=5, guard_rejection=1,
            all_effective=True, production_inputs_not_mutated=True)


    def test_13_guest_buffer_aliases_and_actual_three_group_tables(self):
        record = screen.SYMBOLS['D_800C6660']+7*16
        actor = screen.SYMBOLS['D_800CC2D0']+7*812
        cases = 0
        for buffer, state, existing, phase in itertools.product((actor+0x10, record-85, record-86, TYPES-99),
                (2, 3), (False, True), (0, 8)):
            memory = fixture(state=state, group=2, existing=existing, buffer=buffer)
            put(memory, record+15, state, 1); put(memory, record+14, 2, 1)
            put(memory, actor+0x74, 0x35, 1)
            self.compare(memory, phase=phase, allocation=buffer); cases += 1
        def block(a, size):
            return self.before[elf_slot_offset(self.before, a, size):][:size]
        tables = {name: struct.unpack('>3I', block(screen.SYMBOLS[name], 12)) for name in
            ('D_80084430', 'D_8008443C', 'D_80084448', 'D_80084454')}
        counts = list(block(screen.SYMBOLS['D_80098914'], 3))
        self.assertEqual(counts, [27, 31, 45])
        actual_labels = {target: label for name, label in (('D_80084430', 'element'),
            ('D_8008443C', 'finish'), ('D_80084448', 'active')) for target in tables[name]}
        with patch.dict(LABELS, actual_labels):
            for group, existing, phase in itertools.product(range(3), (False, True), (0, 8)):
                memory = fixture(group=group, count=counts[group], existing=existing)
                for g in range(3):
                    put(memory, screen.SYMBOLS['D_80098914']+g, counts[g], 1)
                    for name in tables: put(memory, screen.SYMBOLS[name]+g*4, tables[name][g])
                    types = tables['D_80084454'][g]
                    for i, byte in enumerate(block(types, counts[g])): put(memory, types+i, byte, 1)
                self.compare(memory, phase=phase); cases += 1
        self.receipt('aliases-and-tables', cases=cases, mapped_guest_aliases=['actor flag', 'record state', 'record group', 'type byte'],
            actual_group_counts=counts, actual_signed_type_arrays_and_callback_addresses=True,
            callback_implementations_still_bounded_models=True, alias_cases_not_portable_C_claim=True)


NATIVE = r'''
typedef unsigned char u8; typedef signed char s8; typedef int s32; typedef unsigned int u32;
#define NULL ((void *)0)
typedef struct {u8 pad[100],unk64,tail[3];} struct04;
typedef struct {s32 unk0,unk4,unk8;u8 pad[3],unkF;} struct106;
typedef struct {u8 pad[0x74],unk74,rest[0x15F];void *unk1D4;u8 tail[0x154];} struct127;
struct106 D_800C6660[26];struct127 D_800CC2D0[26];u8 D_80098914[256];s8 *D_80084454[256];
void (*D_80084430[256])(struct04 *,s32);void (*D_8008443C[256])(s32);void (*D_80084448[256])(s32);
static struct04 buffer[255],other[255];static s8 types[3][256];
static u32 got[2048][6],want[2048][6];static int n,w,error,mode,failAllocation,slot;
static struct106 expected;static struct04 expectedBuffer[255],expectedOther[255];
static int predicateCalls,setupCalls,elementCalls;
static void record(int label,s32 a,s32 b,s32 c,s32 d,s32 e) {
    u32 *p;if(n>=2048){error=1;return;}p=got[n++];p[0]=label;p[1]=a;p[2]=b;p[3]=c;p[4]=d;p[5]=e;
}
static void expect(int label,s32 a,s32 b,s32 c,s32 d,s32 e) {
    u32 *p=want[w++];p[0]=label;p[1]=a;p[2]=b;p[3]=c;p[4]=d;p[5]=e;
}
static void mutate(int label,struct04 *element) {
    struct106 *r=D_800C6660+slot;
    if(mode==1 && label==1){((u8 *)r)[14]=1;D_80098914[1]=0;r->unk0=(s32)other;}
    if(mode==2 && label==2 && predicateCalls++==0)r->unk0=(s32)other;
    if(mode==3 && label==2 && predicateCalls++==0)buffer[0].unk64=9;
    if(mode==4 && label==3 && setupCalls++==0){((u8 *)r)[14]=1;r->unk0=(s32)other;r->unkF=0;}
    if(mode==5 && label==4 && elementCalls++==0){((u8 *)r)[14]=2;r->unk0=(s32)other;
        element->unk64=9;types[0][1]=0;D_80084454[0]=types[1];D_80098914[0]=0;}
    if(mode==6 && label==5){((u8 *)r)[14]=1;r->unkF=0;}
    if(mode==7 && label==6)r->unkF=0;
    if(mode==8 && label==7)r->unkF=0;
}
s32 allocate_memory(s32 size,s32 flag,s32 a,s32 b){record(1,size,flag,a,b,0);mutate(1,NULL);return failAllocation?0:(s32)buffer;}
s32 func_1503E1F4(s32 index,s32 value){struct106 *r=D_800C6660+value;record(2,index,value,0,0,0);
    mutate(2,NULL);return (((u32)(index<32?r->unk4:r->unk8))&(1U<<(index&31)))!=0;}
s32 func_1503E3C4(s32 value,s32 index,s32 zero,struct04 *e,s32 last){record(3,value,index,zero,(s32)e,last);mutate(3,e);return -123;}
static void element0(struct04 *e,s32 value){record(4,(s32)e,value,0,0,0);mutate(4,e);}
static void element1(struct04 *e,s32 value){record(4,(s32)e,value,1,0,0);mutate(4,e);}
static void element2(struct04 *e,s32 value){record(4,(s32)e,value,2,0,0);mutate(4,e);}
static void finish(s32 value){record(5,value,((u8 *)(D_800C6660+slot))[14],0,0,0);mutate(5,NULL);}
static void active(s32 value){record(6,value,((u8 *)(D_800C6660+slot))[14],0,0,0);mutate(6,NULL);}
s32 func_1503EA54(s32 value){record(7,value,0,0,0,0);mutate(7,NULL);return -123;}
s32 func_1503E82C(s32 value){record(8,value,0,0,0,0);mutate(8,NULL);return -123;}
static void copy(u8 *to,const u8 *from,u32 size){u32 i;for(i=0;i<size;i++)to[i]=from[i];}
static void reset(int state,int count,int existing,int mutation,int fail) {
    int i,g;struct106 *r=D_800C6660+slot;
    for(i=0;i<255;i++){buffer[i].unk64=other[i].unk64=0;}
    r->unk0=existing?(s32)buffer:0;r->unk4=r->unk8=-1;((u8 *)r)[14]=0;r->unkF=(u8)state;
    D_800CC2D0[slot].unk74=0x35;D_800CC2D0[slot].unk1D4=(void *)1;
    for(g=0;g<3;g++){D_80098914[g]=(u8)count;D_80084454[g]=types[g];D_8008443C[g]=finish;D_80084448[g]=active;
        for(i=0;i<256;i++)types[g][i]=(s8)((i%5)==1?-2:(i%5)==2?-1:(i%5)==3?-128:0);}
    D_80084430[0]=element0;D_80084430[1]=element1;D_80084430[2]=element2;
    n=w=error=predicateCalls=setupCalls=elementCalls=0;mode=mutation;failAllocation=fail;
}
static void reference(void) {
    struct106 *r=D_800C6660+slot;struct04 *e;int state=r->unkF,count,index; s8 *t;
    if(state==2){D_800CC2D0[slot].unk74|=128;state=3;if(!D_800CC2D0[slot].unk1D4)return;}
    if(state==3){count=D_80098914[((u8 *)r)[14]];
        if(!r->unk0){expect(1,count*104,1,0,0,0);mutate(1,NULL);if(failAllocation)return;r->unk0=(s32)buffer;
            for(index=0;index<count;index++)buffer[index].unk64=0;}
        t=D_80084454[((u8 *)r)[14]];
        for(index=0;index<count;index++)if(t[index]!=-2){
            e=(struct04 *)r->unk0+index;expect(2,index,slot,0,0,0);mutate(2,NULL);
            if((((u32)(index<32?r->unk4:r->unk8))&(1U<<(index&31))) && !e->unk64){
                expect(3,slot,index,0,(s32)e,0);mutate(3,e);expect(4,(s32)e,slot,((u8 *)r)[14],0,0);mutate(4,e);e->unk64=1;}}
        expect(5,slot,((u8 *)r)[14],0,0,0);mutate(5,NULL);r->unkF=1;state=1;}
    if(state==1){expect(6,slot,((u8 *)r)[14],0,0,0);mutate(6,NULL);
        if(r->unkF){expect(7,slot,0,0,0,0);mutate(7,NULL);expect(8,slot,0,0,0,0);mutate(8,NULL);}}
}
static int report(u32 code,u32 c,u32 i){u32 data[3]={code,c,i};s32 result;
__asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");return (s32)code;}
'''

NATIVE_MAIN = r'''
int run(void) {
    int state,j,existing,m,fail,c=0,i,k;u8 flag;static int counts[]={0,1,3,4,5,27,31,45,127,128,255};
    if(sizeof(void *)!=4 || sizeof(struct04)!=104 || sizeof(struct106)!=16 || sizeof(struct127)!=812
        || __builtin_offsetof(struct127,unk1D4)!=0x1D4)return 1;
    slot=7;
    for(state=0;state<256;state++)for(existing=0;existing<2;existing++,c++){
        reset(state,5,existing,0,0);reference();expected=D_800C6660[slot];flag=D_800CC2D0[slot].unk74;k=w;
        copy((u8 *)expectedBuffer,(u8 *)buffer,sizeof(buffer));copy((u8 *)expectedOther,(u8 *)other,sizeof(other));
        reset(state,5,existing,0,0);w=k;func_1503DF48(slot);
        if(n!=w || error || D_800CC2D0[slot].unk74!=flag)return report(2,c,n);
        for(i=0;i<n*6;i++)if(((u32 *)got)[i]!=((u32 *)want)[i])return report(3,c,i);
        for(i=0;i<16;i++)if(((u8 *)(D_800C6660+slot))[i]!=((u8 *)&expected)[i])return report(4,c,i);
        for(i=0;i<255;i++)if(buffer[i].unk64!=expectedBuffer[i].unk64 || other[i].unk64!=expectedOther[i].unk64)return report(5,c,i);
    }
    for(j=0;j<11;j++)for(state=1;state<=3;state++)for(existing=0;existing<2;existing++)for(m=0;m<9;m++,c++){
        fail=(j==0 && !existing);reset(state,counts[j],existing,m,fail);reference();
        expected=D_800C6660[slot];flag=D_800CC2D0[slot].unk74;k=w;
        copy((u8 *)expectedBuffer,(u8 *)buffer,sizeof(buffer));copy((u8 *)expectedOther,(u8 *)other,sizeof(other));
        reset(state,counts[j],existing,m,fail);w=k;func_1503DF48(slot);
        if(n!=w || error || D_800CC2D0[slot].unk74!=flag)return report(6,c,n);
        for(i=0;i<n*6;i++)if(((u32 *)got)[i]!=((u32 *)want)[i])return report(7,c,i);
        for(i=0;i<16;i++)if(((u8 *)(D_800C6660+slot))[i]!=((u8 *)&expected)[i])return report(8,c,i);
        for(i=0;i<255;i++)if(buffer[i].unk64!=expectedBuffer[i].unk64 || other[i].unk64!=expectedOther[i].unk64)return report(9,c,i);
    }
    return c==1106?0:10;
}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
