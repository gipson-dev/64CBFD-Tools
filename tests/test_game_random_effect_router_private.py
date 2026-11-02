"""Guest semantics, callback ABI, and source controls for func_151AE890."""
import hashlib
import itertools
import math
from pathlib import Path
import struct
import unittest

from tools.experiments import game_random_effect_router_guard_match as match
from tools.experiments.game_four_head_lookup_match import payload
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK


ACTOR = 0x20000
RANDOM = 0x150ADA68
COMPLEX_EFFECT = 0x151AE984
SIMPLE_EFFECT = 0x151AEAB4
THRESHOLD = 0x800A9D84
FLAG_THRESHOLD = 0x800A9D88


def fixture(gate, flag_gate, actor_byte):
    memory = {STACK + offset: (offset * 17 + 0xA5) & 0xFF
              for offset in range(-0x200, 0x100)}
    memory.update({ACTOR + offset: (offset * 19 + 0xA5) & 0xFF
                   for offset in range(0x40)})
    put(memory, THRESHOLD, bits(gate))
    put(memory, FLAG_THRESHOLD, bits(flag_gate))
    memory[ACTOR + 0xC] = actor_byte
    return memory


def reference(first, second, gate, flag_gate, position, payload, actor_byte):
    first_float = floating(first)
    if first_float < gate:
        return ((RANDOM,),)
    if first_float < 0.25:
        return ((RANDOM,), (RANDOM,),
                (SIMPLE_EFFECT, position, int(0.0 < floating(second)), actor_byte))
    return ((RANDOM,), (RANDOM,),
            (COMPLEX_EFFECT, position, *payload,
             int(flag_gate < floating(second)), actor_byte))


class Oracle(TriangleOracle):
    def __init__(self, words, memory, position, payload, actor_byte, randoms):
        arguments = (0, 0, position[2], payload[0], payload[1], payload[2], ACTOR)
        super().__init__(words, memory, entry=match.ENTRY, arguments=arguments)
        self.f[12], self.f[14] = position[:2]
        self.randoms = iter(randoms)
        self.effect_calls = []
        self.actor_byte = actor_byte

    def position(self, address):
        return tuple(self.get(address + index * 4, 4) for index in range(3))

    def record_call(self, target):
        if target == RANDOM:
            self.effect_calls.append((RANDOM,))
        elif target == SIMPLE_EFFECT:
            self.effect_calls.append((target, self.position(self.r[4]),
                                      self.r[5], self.r[6]))
        elif target == COMPLEX_EFFECT:
            self.effect_calls.append((target, self.position(self.r[4]),
                                      self.r[5], self.r[6], self.r[7],
                                      self.get(self.r[29] + 0x10, 4),
                                      self.get(self.r[29] + 0x14, 4)))
        else:
            raise AssertionError("Unexpected random-effect provider " + hex(target))

    def hook(self, target):
        if target == RANDOM:
            self.f[0] = next(self.randoms)
            return
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + index for index in range(20)]


class GameRandomEffectRouterPrivateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / match.BUILD
        cls.names = (match.SOURCE, match.PATHS["elf"], match.PATHS["object"],
                     match.PATHS["guards"], "conker/progress.csv")
        cls.before = {name: hashlib.sha256((cls.root / name).read_bytes()).hexdigest()
                      for name in cls.names}
        cls.report, _, cls.obj, *_ = match.prepare(cls.root, cls.output)
        raw, _ = payload(cls.obj, match.FUNCTION)
        cls.candidate = list(struct.unpack(">%dI" % match.WORDS,
                                           match.linked_payload(raw)))
        cls.retail = list(struct.unpack(">%dI" % match.WORDS,
                                        match.retail_bytes(cls.root)))

    def compare(self, first, second, gate=0.1, flag_gate=0.5,
                position=(0x3FA00000, 0xC0200000, 0x40700000),
                payload=(0x3F19999A, 0xBF4CCCCD, 0x7FC12345), actor_byte=0x7E):
        memory = fixture(gate, flag_gate, actor_byte)
        expected = reference(first, second, gate, flag_gate,
                             position, payload, actor_byte)
        models = [Oracle(words, memory, position, payload, actor_byte,
                         (first, second)).run()
                  for words in (self.retail, self.candidate)]
        for model in models:
            self.assertEqual(tuple(model.effect_calls), expected)
        self.assertEqual((models[0].memory, models[0].r, models[0].f,
                          models[0].condition, models[0].effect_calls),
                         (models[1].memory, models[1].r, models[1].f,
                          models[1].condition, models[1].effect_calls))
        return models

    def test_01_all_routes_threshold_edges_flags_and_payload_bits(self):
        samples = tuple(bits(value) for value in
                        (-math.inf, -0.0, 0.0, 0.099, 0.1, 0.249, 0.25, 1.0,
                         math.inf)) + (0x7FC12345,)
        flags = tuple(bits(value) for value in
                      (-math.inf, -0.0, 0.0, 0.499, 0.5, 0.501, math.inf)) + (0x7FC54321,)
        visits = set()
        cases = 0
        for first, second, actor_byte in itertools.product(samples, flags, (0, 0x7E, 0xFF)):
            models = self.compare(first, second, actor_byte=actor_byte)
            visits.update(models[0].visits)
            cases += 1
        self.assertEqual(cases, 240)
        self.assertGreaterEqual(len(visits), 56)

    def test_02_coordinates_raw_payloads_callback_table_and_inputs(self):
        positions = ((bits(0.0), bits(-0.0), bits(1.0)),
                     (bits(-17.5), bits(2048.25), bits(math.inf)),
                     (0x7FC12345, 0xFF800000, 0x00000001))
        payloads = ((0, 1, 0xFFFFFFFF),
                    (0x3F800000, 0xBF800000, 0x7FC54321),
                    (0x80000000, 0x7F800000, 0x00800000))
        for position, values in itertools.product(positions, payloads):
            self.compare(bits(0.5), bits(0.75), position=position, payload=values)
            self.compare(bits(0.2), bits(-1.0), position=position, payload=values)
        rom = (self.root / "conker/conker.us.bin").read_bytes()
        self.assertEqual(struct.unpack_from(">I", rom, 0x22E548)[0], match.ENTRY)
        table = (self.root / "conker/asm/data/22E4E0.rodata.s").read_text()
        self.assertIn("22E548 80089A88 151AE890", table)
        self.assertIn("func_151AE890", table)
        self.assertEqual(self.before, {name: hashlib.sha256(
            (self.root / name).read_bytes()).hexdigest() for name in self.names})

    def test_03_source_types_keep_effect_payload_words_unpromoted(self):
        source, _ = match.candidate.production_source((self.root / match.SOURCE).read_text())
        self.assertIn("s32 effect_arg0_bits", source)
        self.assertIn("s32 effect_arg1_bits", source)
        self.assertIn("s32 effect_arg2_bits", source)
        self.assertNotIn("EffectConstructorFn", source)
        self.assertEqual(self.report["frame"], 56)
        self.assertEqual(self.report["relocations"], 9)


if __name__ == "__main__":
    unittest.main()
