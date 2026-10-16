"""Real initializer/FOV/trig/projection chain; angle and SDK leaves stay bounded."""
import itertools
import struct
import unittest
from unittest.mock import patch

from tools.tests import test_game_viewport_initialize_match as matching
from tools.tests import game_viewport_initialize_oracle as model
from tools.tests import game_view_projection_family_oracle as family
from tools.tests import test_game_view_fov_transfer as transfer
from tools.tests import test_game_view_projection_command as command
from tools.tests import test_game_trig_match as trig
from tools.tests import test_game_cosine_match as cosine
from tools.tests.test_game_record_constructor_match import elf_slot_offset

SLOTS = ((model.BOUNDS, 0x48344, 44), (model.CLAMP, 0x483F4, 87),
    (model.TRANSFER, 0x48550, 99), (model.SINE, 0x75210, 104), (model.COSINE, 0x750B0, 88),
    (command.ENTRY, 0x1385D8, 129), (model.FINAL, 0x1387DC, 33), (family.CHILD, 0x138AA8, 38))


def fixture(index, layout, flag, page):
    memory, args = model.fixture(index, layout, transfer=flag, page=page)
    # The reused SDK provider publishes its own explicit alternate bank.
    memory.update({family.THIRD + i:memory[model.THIRD + i] for i in range(0x2200)})
    for address, value in {**trig.GLOBALS, **trig.COS_GLOBALS,
            transfer.DEG_HALF:0x3C0EFA35, transfer.DEG_X:0x42E52EE0, transfer.DEG_Y:0x42E52EE0,
            command.COEF_X:0x3C0EFA35, command.COEF_Y:0x3C0EFA35,
            command.FOV_OVERRIDE:model.bits(3.0), command.NEAR_OVERRIDE:0, command.FAR_OVERRIDE:0,
            command.NEAR_DEFAULT:model.bits(0.125), command.FAR_DEFAULT:model.bits(1000.)}.items():
        model.put(memory, address, value)
    memory.update({0x800D9AC0 + i:0xA5 for i in range(0x80)})
    return memory, args


def reference(initial, args, sdk_mode):
    def project(memory, packet, calls):
        result, nested = command.reference(memory, packet, real_trig=True)
        calls.extend(nested)
        result, sdk = family.child_reference(result, nested[-1][1], sdk_mode)
        calls.extend(sdk); memory.update(result)
    nested_calls = []; pending_angle = 0
    def provider(memory, index, target, ordinal, mode):
        nonlocal pending_angle
        calls = []
        if target == model.SINE:
            row = model.read(memory, model.BASE) + index * 384
            fov, constant = (0x6C, 0x800968EC) if ordinal == 1 else (0x70, 0x800968F0)
            pending_angle = model.mul(model.mul(model.read(memory, row + fov), model.bits(0.5)), model.read(memory, constant))
        if target == model.TRANSFER:
            result, nested = transfer.reference_model(memory, index, args[1], real_trig=True)
            memory.update(result); calls.extend(nested)
            project(memory, nested[-1][1], calls)
        elif target == model.FINAL:
            row = model.read(memory, model.BASE) + index * 384
            packet = (index, 0, 0, model.read(memory, row + 0x84))
            calls.append((command.ENTRY, (*packet, 0)))
            project(memory, (*packet, 0), calls)
            index, x, y, scale = packet
            for p, value in ((0, scale), (4, x), (8, y)):
                model.put(memory, 0x800D9AC0 + index * 12 + p, value)
            memory[0x800D9AF0] = 1
        else: assert target in (model.SINE, model.COSINE, model.BOUNDS, model.CLAMP)
        nested_calls.append(calls)
        return False
    def answer(ordinal, seed):
        return (trig.reference if ordinal & 1 else cosine.reference)(pending_angle)
    with patch.object(model, 'effects', provider), patch.object(model, 'answer', answer):
        memory, calls, complete = model.reference(initial, args)
    assert len(calls) == len(nested_calls)
    return memory, [item for call, nested in zip(calls, nested_calls) for item in (call, *nested)], complete


class ConnectedOracle(model.InitializeOracle):
    def __init__(self, *args, sdk_mode=0, **kwargs):
        super().__init__(*args, **kwargs); self.sdk_mode = sdk_mode

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 7:
            self.f[word >> 6 & 31] = self.f[word >> 11 & 31] ^ 0x80000000
        else: super().execute(word)

    def record_call(self, target):
        counts = {model.TRANSFER:2, model.BOUNDS:1, model.CLAMP:4, model.FINAL:4,
            command.ENTRY:5, family.CHILD:7, family.PERSPECTIVE:7, family.FIXED:2}
        packet = (self.f[12],) if target in (model.SINE, model.COSINE) else (
            (self.f[12], self.f[14]) if target == transfer.ATAN else self.arguments(counts[target]))
        self.calls.append((target, packet)); self.events.append(('CALL', target, packet))

    def hook(self, target):
        packet = self.calls[-1][1]; value = None
        if target == transfer.ATAN:
            start = next(i for i, (t, _) in enumerate(self.calls) if t == model.TRANSFER)
            value = transfer.answer(0, len(self.calls) - start - 1)
        elif target == family.PERSPECTIVE: family.perspective_effect(self.memory, packet, self.sdk_mode)
        else:
            assert target == family.FIXED, hex(target)
            family.fixed_effect(self.memory, packet)
        for i in range(4): self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25): self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344 + len(self.calls)
        if value is not None: self.f[0] = value


class ViewportInitializeConnectedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        matching.ViewportInitializeMatchTests.setUpClass.__func__(cls)

    receipt = matching.ViewportInitializeMatchTests.receipt

    def test_real_chain_independent_reference_and_three_literal_states(self):
        before = (self.out / 'before-elf').read_bytes(); helpers = {}
        for va, rom, count in SLOTS:
            at = elf_slot_offset(before, va, count * 4); data = before[at:at + count * 4]
            self.assertEqual(data, self.rom[rom:rom + count * 4], hex(va))
            helpers.update(zip(range(va, va + count * 4, 4), struct.unpack('>%dI' % count, data)))
        cases = 0; visited = set()
        for index, layout, flag, phase, sdk_mode in itertools.product((0, 1, 3), (0, 1, 3), (0, 1), (0, 8), (0, 1, 2)):
            memory, args = fixture(index, layout, flag, phase // 8)
            expected, calls, complete = reference(memory, args, sdk_mode); self.assertTrue(complete)
            machines = []
            for words in (self.truth, self.raw, self.emitted):
                m = ConnectedOracle(words, memory, args, helpers, phase, sdk_mode=sdk_mode).run()
                self.assertEqual(m.calls, calls, (index, layout, flag, phase, sdk_mode))
                self.assertTrue(model.public(m.memory) == model.public(expected), (index, layout, flag, phase, sdk_mode))
                visited.update(m.visits); machines.append(m)
            for m in machines[1:]: self.assertEqual(matching.state(m), matching.state(machines[0]))
            cases += 1
        for va, _, count in SLOTS: self.assertTrue(visited & set(range(va, va + count * 4, 4)), hex(va))
        self.receipt('connected-chain', three_way_cases=cases, original_ELF_and_retail_exact_helper_words=622,
            actual_FOV99_sine104_cosine88_bounds44_clamp87_wrapper33_parent129_child38=True,
            independent_reference_all_public_words_and_nested_ABI=True, full_literal_private_state=True,
            angle_and_two_SDK_leaves_bounded=True, SDK_base_page_callback_modes=[0, 1, 2],
            hardware_FCSR_pixels_and_full_gameplay_not_claimed=True)


if __name__ == '__main__': unittest.main()
