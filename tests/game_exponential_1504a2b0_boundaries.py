"""Access-prefix and independently linked relocation checks for the candidate."""
import struct
import subprocess

from tools.experiments import game_exponential_1504a2b0_match as packet
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_exponential_1504a2b0_oracle as g


class AccessBoundary(Exception):
    pass


class FaultOracle(g.Oracle):
    def __init__(self, words, memory, value, cut=None):
        super().__init__(words, memory, value)
        self.cut = cut; self.accesses = 0

    def get(self, address, size):
        if self.accesses == self.cut:
            raise AccessBoundary
        self.accesses += 1
        return super().get(address, size)


def access_prefixes(state):
    cases = [g.bits(v) for v in (0., 0.5, -0.5, 1000., -1000.)]
    count = 0
    for value in cases:
        programs = g.programs(state)
        full = FaultOracle(programs[1], g.fixture(), value).run()
        for cut in range(full.accesses):
            observations = []
            for words in programs:
                machine = FaultOracle(words, g.fixture(), value, cut)
                try:
                    machine.run()
                    raise AssertionError(('missing guest access cut', cut))
                except AccessBoundary:
                    pass
                observations.append((machine.memory, machine.events, machine.f[12]))
            assert observations.count(observations[0]) == len(observations), (hex(value),cut)
            count += 1
    return {'cases':len(cases), 'access_cuts':count, 'scope':'guest read-prefix model, not portable C fault semantics'}


def exceptional_prefixes(state):
    # These cases have an invalid C float-to-s32 conversion. Compare only the
    # bounded instruction model; the result is not a C or hardware claim.
    cases = (0x7F800000,0xFF800000,0x7FC12345,0xFFC12345,0x7F7FFFFF,0xFF7FFFFF)
    for value in cases:
        observations = []
        for program in g.programs(state):
            m = g.Oracle(program, g.fixture(), value)
            try:
                m.run()
            except AssertionError as error:
                assert str(error) == 'triangle instruction budget exhausted', (hex(value),error)
            else:
                raise AssertionError(('unexpected termination in bounded model', hex(value)))
            observations.append((m.memory, [e for e in m.events if e[0] == 'R'], m.f[12]))
        assert observations.count(observations[0]) == len(observations), hex(value)
    return {'cases':len(cases), 'instruction_budget_per_run':50000,
            'scope':'bounded guest prefixes only; invalid C float-to-int conversion and no FCSR proof'}


def rebase(state):
    count = 0
    for k, entry in enumerate((0x15001000, 0x1F008000, 0x1000FFF0)):
        symbols = dict(D_800990A0=0x80007FFC+k*0x100000,
                       D_800990A4=0x80018000+k*0x100000,
                       D_800990A8=0x8002FFF8+k*0x100000)
        programs = g.programs(state, symbols)
        for i, key in enumerate(('after','retail','generated','generic')):
            source = state[key]
            script = packet.OUT/('rebase-%d-%d.ld'%(k,i))
            elf = packet.OUT/('rebase-%d-%d.elf'%(k,i))
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            argv = ['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',packet.NAME,
                    *['--defsym=%s=0x%X'%(name,value) for name,value in symbols.items()],
                    '-o',str(elf),str(source)]
            result = subprocess.run(argv, cwd=packet.ROOT/'conker', capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            linked = sections(elf)['.text'][1][:len(programs[i])*4]
            assert linked == struct.pack('>%dI'%len(programs[i]), *programs[i]), (entry,key)
        for value in (0., -0., .5, -.5, 2., -2., 1000., -1000.):
            word = g.bits(value); expected = g.reference(word)
            for program in programs:
                m = g.Oracle(program, g.fixture(symbols), word, entry=entry).run()
                assert m.f[0] == expected and m.memory == m.initial_mem
            count += 1
    return {'bases':3, 'programs_per_base':4, 'cases':count, 'actual_gnu_links':12}
