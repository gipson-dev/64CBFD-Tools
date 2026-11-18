"""Reuse the qualified damping model and execute the complete retail dispatcher."""
import itertools
import json
import struct
from tools.experiments import game_horizontal_damping_151afea4_match as s
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_four_damping_callbacks_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary


def programs():
    result = []
    for label in ('original', 'owner', 'padded-generated', 'padded-generic'):
        raw, refs = s.payload(s.OUT / (label + '.o'), s.NAME)
        result.append(bound_blob(raw, refs, {'D_800BE9E4': g.TICK}))
    return result


def guest():
    seen = set()
    count = 0
    for c in g.cases():
        models = []
        for words in programs_cache:
            model = g.Oracle(words, c, s.ENTRY).run()
            expected, calls, result = g.reference(c, model.initial)
            assert (g.public(model.memory), model.calls, model.r[2]) == (g.public(expected), calls, result), c
            assert model.r[16:24] == model.before[16:24] and model.r[28:] == model.before[28:]
            assert model.f[20:] == model.before_f[20:]
            models.append(model)
        assert all((m.memory, m.r, m.f, m.trace) == (models[0].memory, models[0].r, models[0].f, models[0].trace) for m in models)
        seen.update(models[0].visits)
        count += 1
    assert sum(s.ENTRY + 4 * i in seen for i in range(106)) == 106
    report = dict(cases_per_stream=count, streams=4, retail_words_visited=106,
                  independent_finite_reference=True, complete_guest_state_and_access_order_equal=True)
    (s.OUT / 'guest-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def state(m):
    return m.memory, m.r, m.f, m.calls, m.trace, m.current_pc, m.delay_of, m.hi, m.lo, m.condition


def boundaries():
    cuts = 0
    for tick in (0, 1, 4, 5):
        c = next(c for c in g.cases() if c.tick == tick)
        full = g.Oracle(programs_cache[0], c, s.ENTRY).run()
        for cut in range(full.all_accesses):
            states = []
            for words in programs_cache:
                model = g.Oracle(words, c, s.ENTRY)
                model.cut = cut
                try:
                    model.run()
                except AccessBoundary:
                    states.append(state(model))
                else:
                    raise AssertionError(('unreached access cut', tick, cut))
            assert all(v == states[0] for v in states)
            cuts += 1
    high_cuts = 0
    for tick in (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF):
        c = g.Case(tick, g.bits(1.), g.bits(-2.), g.bits(.75))
        for cut in range(80):
            states = []
            for words in programs_cache:
                model = g.Oracle(words, c, s.ENTRY)
                model.cut = cut
                try:
                    model.run()
                except AccessBoundary:
                    states.append(state(model))
                else:
                    raise AssertionError(('unreached high-tick cut', tick, cut))
            assert all(v == states[0] for v in states)
            high_cuts += 1
    report = dict(access_cut_quadruples=cuts, high_tick_prefix_cuts=high_cuts,
                  hardware_fault_behavior_qualified=False)
    (s.OUT / 'boundaries-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


CALLER, CALLER_END = 0x151303EC, 0x15130A9C
TABLE, RELEASE = 0x80089760, 0x1516972C


class Parent(FactoryOracle):
    def __init__(self, caller, target, c, flags=0):
        memory = g.fixture(c)
        memory.update({g.RECORD + i: (i * 19 + 37) & 255 for i in range(0xAC, 0x100)})
        for at, value in ((0x20, 0), (0x68, flags)):
            g.put(memory, g.RECORD + at, value)
        g.put(memory, 0x800BE9A4, g.bits(.5))
        memory[g.RECORD + 0x72] = 6
        memory[g.RECORD + 0x73] = 255
        g.put(memory, TABLE + 24, s.ENTRY)
        connected = {s.ENTRY + 4 * i: word for i, word in enumerate(target)}
        super().__init__(caller, memory, c, entry=CALLER, arguments=(g.RECORD,), connected=connected)
        self.target_args = []

    def record_call(self, target):
        if target == s.ENTRY:
            args = tuple(self.arguments(2))
            self.target_args.append(args)
        else:
            assert target == RELEASE
            self.calls.append((target, tuple(self.arguments(1))))

    def hook(self, target):
        assert target == RELEASE
        self.r[2] = 0


def caller():
    rom = (s.FROZEN / 'conker/conker.us.bin').read_bytes()
    assert struct.unpack_from('>I', rom, 0x22E220 + 24)[0] == s.ENTRY
    words = list(struct.unpack_from('>428I', rom, CALLER - 0x15000000 + 0x2D4B0))
    seen = set()
    count = 0
    for tick, flags, phase in itertools.product((0, 1, 2, 3, 4, 5, 7, 8, 15, 16), (0, 2, 4, 6), (0, 8)):
        c = g.Case(tick, g.bits(1.25), g.bits(-2.5), g.bits(.75), phase)
        models = [Parent(words, target, c, flags).run() for target in programs_cache]
        for model in models:
            assert model.target_args == [(g.RECORD, g.STACK + phase - 16)]
            assert not model.calls and model.r[2] == 1
            assert model.r[29] == g.STACK + phase
        assert all(state(m) == state(models[0]) for m in models)
        seen.update(pc for pc in models[0].visits if CALLER <= pc < CALLER_END)
        count += 1
    wrong = programs_cache[0][:]
    assert wrong[-3] == 0x24020001
    wrong[-3] = 0x24020000
    model = Parent(words, wrong, g.Case(1, g.bits(1.25), g.bits(-2.5), g.bits(.75))).run()
    assert model.calls == [(RELEASE, (g.RECORD,))]
    report = dict(complete_caller_words=428, cases_per_stream=count, streams=4,
                  caller_words_visited=len(seen), callback_index=6,
                  full_parent_all_paths_qualified=False, selected_complete_parent_paths=True,
                  return_zero_control_reaches_release=True)
    (s.OUT / 'caller-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


programs_cache = []


def prepare():
    programs_cache[:] = programs()
