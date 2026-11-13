"""Exercise the original direct-call windows, not the complete callers."""
import itertools
import struct
from tools.tests import game_camera_state_15125924_direct_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary


def run():
    rom = (g.root/'conker/conker.us.bin').read_bytes()
    streams = [g.words(g.out/f) for f in ('retail.o', 'after.o', 'padded.o')]
    for start, register in ((0x15005718, 17), (0x15122f50, 16)):
        end = start + 8
        window = struct.unpack_from('>2I', rom, start-0x15000000+0x2d4b0)
        assert window == (0x0d449649, 0x02202025 if register == 17 else 0x02002025)

        class Connected(g.Machine):
            def __init__(self, words, case, initial):
                self.c = case
                code = dict(zip(range(g.ENTRY, g.ENTRY+len(words)*4, 4), words))
                code[end] = 0
                FactoryOracle.__init__(self, window, initial, case, entry=start, s=g.SYMS,
                                       arguments=(), connected=code)
                self.r[register] = g.CAMERA
                self.code = WindowCode(self.code, self)
                self.code.ends = (end,)

            def record_call(self, target):
                if target == g.ENTRY:
                    self.calls.append((target, tuple(self.arguments(1))))
                else:
                    super().record_call(target)

        count = 0
        for flags, present, status, value, first, second, mutation in itertools.product(
                (0, 0x40, 0x80), (0, 1), (0, 1), (0., 1.25), (0, 1), (0, 1), (0, 1)):
            case = g.Case(present=present, flags=flags, flags84=0x4000, status=status,
                          value=value, first=first, second=second, mutate=mutation)
            initial = g.fixture(case)
            expected, calls = g.reference(initial, case)
            for words in streams:
                machine = Connected(words, case, initial.copy())
                try:
                    machine.run()
                    raise AssertionError('caller boundary not reached')
                except WindowBoundary:
                    pass
                assert (g.public(machine.memory, case), machine.calls) == (
                    expected, [(g.ENTRY, (g.CAMERA,))]+calls), (hex(start), case, machine.calls)
            count += 1
        assert count == 192
