"""Retail-only packet contract: FE1C is not an installable C recovery."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset

ENTRY, ROM, FACTORY = 0x1516FE1C, 0x19D2CC, 0x1516D99C
ACTORS, CALLER, CALLER_ROM, TABLE = 0x800CC2D0, 0x15074E04, 0xA22B4, 0x80086694
SPANS = {
    'target': (ROM, 536, 'fe57d3632c9cf7b7d5e132bec9864f8d950c6459d2c3b4beab64f7da58a17d42'),
    'caller': (CALLER_ROM, 124, '841a3d16d6e8f1c4a449cbd4d193dbdb715f14f4413d873c996cf1454965b37e'),
    'table': (0x22B154, 156, '0256182ee002dd91f9303bd38a2446e5e14439ace533a2d524900d713412bd0f'),
}


def short(value):
    return ((value + 0x8000) & 0xFFFF) - 0x8000


def packets(args, state, inherited, mode=0):
    index, scalar, flags, context = args
    pointer = (ACTORS + index * 0x32C + 0x14) & 0xFFFFFFFF
    result = []
    for second in (False, True):
        p = [0] * 49
        for i, value in ((0, 4 if state == 1 else short(pointer >> 16)),
                (1, 0 if state == 1 else short(pointer)), (13, 8 if second else 0),
                (27, 170), (28, 170), (29, 170), (30, 170), (31, scalar & 65535),
                (32, 30), (34, index & 255 if state == 1 else 255), (35, 30),
                (36, 360), (37, 24), (38, 1 if state == 1 else 33), (39, 4),
                (41, 1), (45, 27 if second else 25 if state == 1 else inherited),
                (47, 0x80 if second and mode else flags & 255),
                (48, 0x87654321 if second and mode else context)):
            p[i] = value & 0xFFFFFFFF
        result.append((FACTORY, *p))
    return result


def fixture(args, state, inherited, phase=0):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-768, 256)}
    actor = (ACTORS + args[0] * 0x32C) & 0xFFFFFFFF
    put(memory, actor, state)
    put(memory, STACK + phase - 4, inherited)
    return memory


class PairedOverlayOracle(MaskOracle):
    def __init__(self, words, args, state=1, inherited=0x12345678, phase=0,
            mode=0, fault=None, entry=ENTRY, memory=None, connected=None):
        memory = fixture(args, state, inherited, phase) if memory is None else memory
        super().__init__(words, memory, phase=phase, mode=mode, fault=fault,
            entry=entry, arguments=args, connected=connected)
        self.actor = (ACTORS + args[0] * 0x32C) & 0xFFFFFFFF
        self.input_stack = STACK + phase

    def record_call(self, target):
        if target == ENTRY:
            self.entry_arguments = self.arguments(4)
            self.input_stack = self.r[29]
            self.actor = (ACTORS + self.r[4] * 0x32C) & 0xFFFFFFFF
            return
        args = self.arguments(49) if target == FACTORY else self.arguments(7)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == FACTORY and len(self.calls) == 1 and self.mode:
            # These are explicit guest home writes, not portable C mutations.
            for address, value in ((self.input_stack + 8, 0xABCDEF80),
                    (self.input_stack + 12, 0x87654321), (self.input_stack + 4, 0xFFFFFFFE),
                    (self.input_stack - 4, 0xDEADC0DE), (self.actor, 1)):
                self.put(address, value, 4)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0xABCD0000 + len(self.calls)


class ActorPairedOverlayContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-paired-overlay-contract'
        cls.out.mkdir(exist_ok=True)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.words = list(struct.unpack_from('>134I', cls.rom, ROM))
        cls.caller = list(struct.unpack_from('>31I', cls.rom, CALLER_ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_original_spans_and_actual_live_reference(self):
        for name, (offset, size, digest) in SPANS.items():
            self.assertEqual(hashlib.sha256(self.rom[offset:offset + size]).hexdigest(), digest, name)
        elf = (self.root / 'conker/build/conker.us.elf').read_bytes()
        for address, offset, size in ((CALLER, CALLER_ROM, 124), (TABLE, 0x22B154, 156)):
            start = elf_slot_offset(elf, address, size)
            self.assertEqual(elf[start:start + size], self.rom[offset:offset + size])
        jal = struct.pack('>I', 0x0C000000 | ((ENTRY >> 2) & 0x3FFFFFF))
        self.assertEqual([i for i in range(0, len(self.rom) - 3, 4) if self.rom[i:i + 4] == jal], [0xA22EC])
        table = struct.unpack_from('>39I', self.rom, 0x22B154)
        self.assertEqual(table[7], CALLER)
        self.receipt('references', caller_current_exact_words=31, original_target_words=134,
            callback_table=hex(TABLE), slot=7, only_aligned_JAL_offset=hex(0xA22EC),
            staged_original_not_installed_C=True)

    def test_02_complete_two_packets_widths_boundaries_and_live_homes(self):
        visits, count = set(), 0
        cases = [(i, s, f, c) for i in (0, 1, 25, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)
            for s, f, c in ((0, 0, 0), (0xABCD8000, 0x123400FF, 0x76543210), (0xFFFFFFFF,) * 3)]
        for args in cases:
            for state in (0, 1, 0x100, 0x80000001):
                for inherited in (0, 0x19, 0x123456A5, 0x80000000, 0xFFFFFFFF):
                    for phase in (0, 8):
                        for mode in (0, 1):
                            model = PairedOverlayOracle(self.words, args, state, inherited, phase, mode).run()
                            self.assertEqual(model.calls, packets(args, state, inherited, mode))
                            self.assertEqual(model.r[29], STACK + phase)
                            visits |= model.visits
                            count += 1
        self.assertEqual(visits, set(range(ENTRY, ENTRY + 536, 4)))
        self.receipt('packets', cases=count, packet_words=49, calls=2, every_original_word_visited=True,
            state_test_is_full_word=True, full_inherited_word_forwarded=True,
            scalar_and_actor_class_snapshot=True, flags_and_context_live=True,
            physical_home_probe_not_native_C_or_hardware=True)

    def test_03_inherited_word_is_conditional_and_not_a_fifth_argument(self):
        args = (1, 0xABCD1234, 0xABCDEF80, 0x76543210)
        for phase in (0, 8):
            incoming = STACK + phase
            memory = fixture(args, 1, 0x12345678, phase)
            for i in range(4):
                del memory[incoming - 4 + i]
            direct = PairedOverlayOracle(self.words, args, phase=phase, memory=memory).run()
            self.assertEqual(direct.calls, packets(args, 1, 0))
            self.assertFalse(any(e[0] == 'R' and e[1] == incoming - 4 for e in direct.events))
            put(memory, ACTORS + args[0] * 0x32C, 0)
            with self.assertRaisesRegex(AssertionError, 'unmapped read'):
                PairedOverlayOracle(self.words, args, phase=phase, memory=memory).run()
            put(memory, incoming - 4, 0xABCDEF80)
            put(memory, incoming + 16, 0x11223344)
            model = PairedOverlayOracle(self.words, args, phase=phase, memory=memory).run()
            self.assertEqual(model.calls[0][46], 0xABCDEF80)
            self.assertNotEqual(model.calls[0][46], read(memory, incoming + 16))

    def test_04_real_caller_reaches_both_paths_and_preserves_ambient_input(self):
        code = dict(zip(range(ENTRY, ENTRY + 536, 4), self.words))
        count = 0
        for index in (0, 1, 25):
            for state in (0, 1, 0x80000001):
                for inherited in (0x19, 0x123456A5, 0xFFFFFFFF):
                    args = (index, ACTORS + index * 0x32C, 0x12345678)
                    memory = fixture((index, 0, 0, 0), state, inherited)
                    put(memory, STACK - 0x2C, inherited)
                    model = PairedOverlayOracle(self.caller, args, memory=memory, entry=CALLER, connected=code).run()
                    self.assertEqual(model.entry_arguments, (index, 180, 255, 0))
                    self.assertEqual(model.calls[:2], packets((index, 180, 255, 0), state, inherited))
                    self.assertEqual(model.calls[2], (0x1518D1C0, args[1], 11, 0, 1, 255, 0, 0x80099C1C))
                    count += 1
        self.receipt('caller', connected_cases=count, caller_current_exact=True,
            target_is_staged_original=True, ambient_address='caller entry SP-0x2C',
            no_local_actor_state_guard=True, full_upstream_entry_or_gameplay_not_proven=True)

    def test_05_fired_faults_before_and_after_the_inherited_load(self):
        args = (1, 180, 255, 0)
        whole = PairedOverlayOracle(self.words, args, state=0).run()
        inherited_read = next(i for i, e in enumerate(whole.events) if e[:3] == ('R', STACK - 4, 4))
        count = 0
        for fault in range(whole.accesses):
            model = PairedOverlayOracle(self.words, args, state=0, fault=fault)
            with self.assertRaises(AccessFault):
                model.run()
            self.assertLessEqual(len(model.calls), 2)
            count += 1
        self.assertGreater(inherited_read, 0)
        self.receipt('faults', fired_original_memory_cuts=count, inherited_load_seen=True,
            no_C_equivalence_or_hardware_fault_claim=True)

    def test_06_effective_contract_controls(self):
        args, state, inherited = (1, 0xABCD1234, 0xFFFF0080, 0x76543210), 0x80000001, 0x123456A5
        variants = {
            'byte-state': (27, 0x91180003),
            'zero-inherited': (45, 0x24120000),
            'fifth-argument': (45, 0x8FB20110),
            'byte-inherited': (45, 0x93B200FF),
            'scaled-coordinate': (37, 0x251E0050),
            'wrong-second-type': (53, 0x24120019),
        }
        for name, (index, replacement) in variants.items():
            words = list(self.words)
            self.assertNotEqual(words[index], replacement, name)
            words[index] = replacement
            memory = fixture(args, state, inherited)
            put(memory, STACK + 16, 0x11223344)
            model = PairedOverlayOracle(words, args, state, inherited, memory=memory).run()
            self.assertNotEqual(model.calls, packets(args, state, inherited), name)
        self.receipt('controls', effective_instruction_contract_negatives=list(variants),
            not_proposed_production_guards=True)


if __name__ == '__main__':
    unittest.main()
