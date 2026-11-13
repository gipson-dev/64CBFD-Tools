"""Compare every modeled retail/padded memory-fault prefix for the point routine."""
from tools.experiments.game_point_descriptor_151382e0_match import ROOT, OUT
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle, Case, STACK, put
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

ENTRY, SUBMIT, SOURCE, SURFACE = 0x151382E0, 0x15153F18, 0x30000, 0x60000
symbols = {row[1]: row[2][1] for row in symbol_rows((ROOT / 'conker/build/conker.us.elf').read_bytes())}


def words(path):
    raw, refs = payload(path, 'func_151382E0')
    return bound_blob(raw, refs, {name: symbols[name] for rows in refs.values() for _, name in rows})


class Machine(FactoryOracle):
    def __init__(self, program, memory, args, phase):
        super().__init__(program, memory, Case(phase=phase), entry=ENTRY, arguments=args)

    def record_call(self, target):
        assert target == SUBMIT
        self.calls.append((target, tuple(self.arguments(5))))

    def hook(self, target):
        assert target == SUBMIT
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]


def state(machine):
    return (machine.memory, machine.r, machine.f, machine.trace, machine.calls,
            machine.events, machine.current_pc, machine.delay_of, machine.all_accesses)


programs = [words(OUT / name) for name in ('durable-retail.o', 'durable-point-padded.o')]
cuts = 0
for category in (0, 1, 2, 255):
    for phase in (0, 8):
        for stack_input in (False, True):
            memory = {STACK + i: (i * 17 + 13) & 255 for i in range(-0x600, 0x140)}
            source = STACK + phase + 0x20 if stack_input else SOURCE
            for i, value in enumerate((0x3f800000, 0x80000000, 0x7fc12345)):
                put(memory, source + i * 4, value)
            for i in range(5):
                put(memory, 0x800A4830 + i * 4, 0x3f800000 + i)
            memory[0x800A3FE6] = category
            args = (source, 0, SURFACE, 255, 0x81234567)
            good = Machine(programs[0], memory, args, phase).run()
            for cut in range(good.all_accesses):
                models = []
                for program in programs:
                    machine = Machine(program, memory, args, phase)
                    machine.cut = cut
                    try:
                        machine.run()
                    except AccessBoundary:
                        pass
                    else:
                        raise AssertionError(('fault boundary did not fire', category, phase, cut))
                    assert machine.all_accesses == cut
                    models.append(machine)
                assert state(models[0]) == state(models[1]), (category, phase, stack_input, cut)
                cuts += 1
print(cuts, 'retail/padded guest fault-prefix pairs matched; this is instruction-level evidence')
