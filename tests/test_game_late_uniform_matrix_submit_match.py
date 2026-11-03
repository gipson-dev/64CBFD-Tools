"""Semantic and strict-image gates for func_1518A914."""

import itertools
from pathlib import Path
import struct

from tools.experiments import game_late_uniform_matrix_submit_candidates as candidate
from tools.experiments import game_late_uniform_matrix_submit_match as match
from tools.tests import test_game_uniform_matrix_submit_match as base
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_frame_timing_oracle import STACK, put, read


ROOT = Path(__file__).resolve().parents[2]
STATE = base.STATE
OUTPUT = base.OUTPUT


def fixture(seed):
    memory = {STACK + index: (index * 17 + 0xA5) & 0xFF
              for index in range(-0x500, 0x100)}
    memory.update({STATE + index: (index * 13 + seed * 19 + 0x59) & 0xFF
                   for index in range(-16, 0x130)})
    memory.update({OUTPUT + index: (index * 11 + seed * 23 + 0x37) & 0xFF
                   for index in range(0x80)})
    values = {
        0x48: (seed - 7) * 1.25,
        0x4C: (9 - seed) * -0.75,
        0x50: (seed % 5 - 2) * 3.5,
        0x100: (seed % 13 - 6) * 0.125,
        0x104: (seed % 11 - 5) * -0.25,
        0x108: (seed % 7 - 3) * 0.5,
        0x10C: (0.0, -0.5, 1.25, -2.0)[seed & 3],
    }
    for offset, value in values.items():
        put(memory, STATE + offset, bits(value))
    return memory


def mutate(memory, seed, mode):
    if mode & 1:
        put(memory, STATE + 0x10C,
            bits((-1.0, 0.5, 2.0)[seed % 3]))
    if mode & 2:
        put(memory, STATE + 0x48, bits((seed + 1) * -2.25))
        put(memory, STATE + 0x4C, bits((seed - 3) * 1.75))
        put(memory, STATE + 0x50, bits((seed % 7 - 3) * -4.0))
    if mode & 4:
        put(memory, STATE + 0x100, bits(97.0))
        put(memory, STATE + 0x104, bits(98.0))
        put(memory, STATE + 0x108, bits(99.0))


def reference(initial, seed, mode):
    memory = dict(initial)
    rotations = tuple(read(memory, STATE + offset)
                      for offset in (0x100, 0x104, 0x108))
    values = base.matrix_seed(seed)
    mutate(memory, seed, mode)
    values[12] = read(memory, STATE + 0x48)
    values[13] = read(memory, STATE + 0x4C)
    values[14] = read(memory, STATE + 0x50)
    scale = read(memory, STATE + 0x10C)
    for index in (0, 1, 2, 4, 5, 6, 8, 9, 10):
        values[index] = base.product(values[index], scale)
    for index, value in enumerate(values):
        put(memory, OUTPUT + index * 4, value)
    return memory, [(base.ROTATE, rotations), (base.CONVERT, tuple(values))]


ORIGINAL_NATIVE_SOURCE = base.native_source


def native_source(body):
    return ORIGINAL_NATIVE_SOURCE(body).replace(
        "UniformMatrixState1515858C", "UniformMatrixState1518A914").replace(
        "func_1515858C", "func_1518A914")


class LateUniformMatrixSubmitTest(base.UniformMatrixSubmitTest):
    @classmethod
    def setUpClass(cls):
        cls._originals = {
            "candidate": base.candidate,
            "match": base.match,
            "fixture": base.fixture,
            "mutate": base.mutate,
            "reference": base.reference,
            "native_source": base.native_source,
        }
        base.candidate = candidate
        base.match = match
        base.fixture = fixture
        base.mutate = mutate
        base.reference = reference
        base.native_source = native_source

    @classmethod
    def tearDownClass(cls):
        for name, value in cls._originals.items():
            setattr(base, name, value)

    def test_guest_semantics_cover_every_word(self):
        data = (ROOT / match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM + match.SIZE]
        words = list(struct.unpack(">%dI" % match.WORDS, data))
        seen = set()
        count = 0
        for seed, mode, phase in itertools.product(range(32), range(8), (0, 8)):
            initial = fixture(seed)
            wanted, calls = reference(initial, seed, mode)
            model = base.MatrixSubmitOracle(words, initial, seed, mode, phase).run()
            self.assertEqual(base.public(model.memory), base.public(wanted))
            self.assertEqual(model.calls, calls)
            self.assertEqual(model.r[2], 1)
            self.assertEqual(model.ordinal, 2)
            seen.update(pc - match.ENTRY for pc in model.visits
                        if match.ENTRY <= pc < match.ENTRY + match.SIZE)
            count += 1
        self.assertEqual(count, 512)
        self.assertEqual(seen, set(range(0, match.COMPACT_SIZE, 4)))
        self.assertEqual(words[-1], 0)

    def test_direct_owner_and_full_image(self):
        candidate_report = candidate.compare("test-direct-owner", candidate.SELECTED)
        self.assertEqual(candidate_report["words"], match.COMPACT_WORDS)
        self.assertEqual(candidate_report["frame"], match.RETAIL_FRAME)
        self.assertEqual(candidate_report["differences"], 0)
        result = match.prepare(ROOT)
        report = result["report"]
        installed = candidate.SELECTED in (ROOT / candidate.SOURCE).read_text()
        self.assertEqual(report["source_installed"], installed)
        self.assertEqual(report["words"], match.WORDS)
        self.assertEqual(report["compact_words"], match.COMPACT_WORDS)
        self.assertEqual(report["trailing_pad_words"], 1)
        self.assertEqual(report["guards"], 0)
        self.assertEqual(report["natural_positional_differences"], 0)
        self.assertEqual(report["changed_bodies"], [match.FUNCTION])
        self.assertTrue(report["all_addresses_fixed"])
        self.assertEqual(report["strict_exclusions"], 0)
        self.assertTrue(report["game_data"]["exact"])


if __name__ == "__main__":
    base.unittest.main()
