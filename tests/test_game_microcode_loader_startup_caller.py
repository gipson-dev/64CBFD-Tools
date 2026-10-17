"""Complete original startup caller and its actual void-loader call/post-call cut."""
import itertools
import json
from pathlib import Path
import struct
import unittest

from tools.experiments import game_microcode_loader_installation as source
from tools.tests import game_microcode_loader_oracle as model
from tools.tests import test_game_microcode_loader_lifetimes as connected
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as tracking

ENTRY, JOIN = 0x15008138, 0x1500814C


class Join(Exception): pass


class Code(tracking.TrackedCode):
    def __getitem__(self, pc):
        if pc == JOIN: raise Join
        return super().__getitem__(pc)


class StartupCut(connected.Connected):
    def __init__(self, words, memory, args, helper, phase, mode):
        model.submit.machine.InitializeOracle.__init__(self, words, memory, args, helper, phase, entry=ENTRY)
        self.variant, self.paired = model.selectors(memory[model.read(memory, model.STATE) + 43], model.read(memory, model.FLAG))
        self.loader_mode, self.dma_count = mode, 0
        self.code = Code(self.code, self)


class MicrocodeLoaderStartupCallerTests(unittest.TestCase):
    def test_complete426_word_original_caller_and_192_real_post_call_cuts(self):
        root = Path(__file__).resolve().parents[2]; out = root / source.BUILD
        source.freeze(root, out); obj, padded, raw, row = source.fit.qualify(root, out)
        context = type('OriginalContext', (), dict(root=root, out=out))
        original = assembly.ViewListSetupTests.original.__func__(context, 'original-startup-caller',
            (out / 'before-startup_caller').read_text(), 'func_15007B3C')
        data, functions = source.source.build.link_owner(root, out, original, 'game_34F20')
        f = functions['func_15007B3C']; body = data[f['value']:f['value'] + f['size']]
        rom = (out / 'before-retail_rom').read_bytes()
        self.assertEqual((len(body), body), (1704, rom[0x34FEC:0x35694]))
        cut = list(struct.unpack_from('>5I', body, ENTRY - 0x15007B3C))
        self.assertEqual(cut, [0x0D40730F, 0, 0x3C04800D, 0x2484C2D0, 0x8C990000])
        data, placed = source.source.build.link_owner(root, out, padded, source.source.OWNER)
        normalized = list(struct.unpack_from('>97I', data, placed[source.source.FUNCTION]['value']))
        truth = list(struct.unpack_from('>97I', rom, source.source.ROM)); self.assertEqual(normalized, truth)
        cases = 0
        for value, flag, cache, phase, mode, pattern in itertools.product((0, 3, 130, 255), (0, 1, 0x10000),
                (0, 1), (0, 8), (0, 15), (0, 1)):
            memory = model.fixture(value, flag, cache); wanted_t9 = (0, 0xDEADBEEF)[pattern]
            model.put(memory, 0x800CC2D0, wanted_t9)
            args = (0, 0, 0, 0) if pattern == 0 else (0xDEADBEEF, 0x80000000, 0x10000, 0xFFFFFFFF)
            expected, calls, observations, fired = model.reference(memory, mode); machines = []
            for words in (truth, raw, normalized):
                helper = dict(zip(range(source.source.ENTRY, source.source.ENTRY + len(words) * 4, 4), words))
                m = StartupCut(cut, memory, args, helper, phase, mode)
                with self.assertRaises(Join): m.run()
                self.assertEqual(model.submit.public(m.memory), model.submit.public(expected))
                self.assertEqual(m.calls, [(source.source.ENTRY, ()), *calls])
                self.assertEqual(m.observations, observations); self.assertEqual(m.fired, fired)
                self.assertEqual(m.r[4], 0x800CC2D0); self.assertEqual(m.r[25], wanted_t9)
                self.assertEqual(m.r[29], model.STACK + phase); self.assertEqual(m.r[31], 0x15008140)
                machines.append(m)
            self.assertEqual(connected.state(machines[0]), connected.state(machines[2])); cases += 1
        self.assertEqual(cases, 192)
        (out / 'startup-caller.json').write_text(json.dumps(dict(full_original_words=426,
            three_way_actual_call_cuts=cases, actual_delay_NOP=True, ignored_incoming_four_word_patterns=True,
            real_post_call_object_pointer_and_first_word=True, no_interpreted_return_value=True,
            extended_high_byte_table_is_synthetic=True, full_startup_and_hardware_not_claimed=True), indent=2) + '\n')


if __name__ == '__main__': unittest.main()
