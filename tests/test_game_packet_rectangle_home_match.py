"""Check real compiler lifetimes, private-home closure and the actual successor."""
import copy
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_home_match as source
from tools.experiments import game_packet_rectangle_clip_homes as homes
from tools.tests import game_packet_rectangle_oracle as guest
from tools.tests import test_game_packet_rectangle_recovery as corpus


class FrameTrace(guest.RectangleOracle):
    def __init__(self,words,memory,args,**kwargs):
        self.home_accesses,self.roles = [],{}
        self.private_words = {words[i]:i for i in (134,*source.PATCHES)}
        super().__init__(words,memory,args,**kwargs)

    def observed(self,address,size,value,kind):
        if not self.own_instruction:
            return
        start = self.incoming-136
        base = self.dispatched_word>>21&31
        if address < start+136 and start < address+size:
            if base != 29:
                raise ValueError('External object aliases the callee-owned frame')
            index = self.private_words[self.dispatched_word]
            role = 'dead' if index == 134 else 'X' if index in (205,224,242) else 'Y'
            offset = 2 if index == 211 else 0
            self.home_accesses.append((kind,role,offset,size,value))
            if kind == 'W' and role != 'dead':
                self.roles[role] = value & 0xFFFFFFFF
        else:
            self.home_accesses.append((kind,address,size,value))

    def get(self,address,size):
        value = super().get(address,size)
        self.observed(address,size,value,'R')
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording:
            self.observed(address,size,value&((1<<(size*8))-1),'W')


def state(model):
    start = model.incoming-136
    # Only the sixteen bytes containing the two homes and dead flag spill differ.
    # Check their live logical values separately and retain all caller stack bytes.
    memory = {a:v for a,v in model.memory.items() if not start <= a < start+16}
    events = [e for e in model.events if not (e[0] in ('R','W') and start <= e[1] < start+16)]
    return (memory,model.r,model.f,model.hi,model.lo,model.fcsr,model.condition,
        events,model.calls,model.accesses,model.home_accesses,model.roles)


class RectangleHomeMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.stage = source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.qualified = source.qualify(cls.root,cls.out)
            cls.capture = homes.validate(cls.root,cls.root/homes.BUILD)
        cls.truth = struct.unpack_from('>346I',source.raw_read(cls.root/'conker/conker.us.bin'),source.ROM)
        before = source.raw_read(cls.out/'before-elf')
        cls.raw = struct.unpack_from('>346I',before,source.elf_slot_offset(before,source.ENTRY,1384))

    def test_01_current_native_capture_and_all_screens(self):
        self.assertEqual(self.capture['record_counts'],dict(frontend=1366,optimizer=1212))
        self.assertEqual((self.capture['events'],self.capture['selected_expressions']), (24,20))
        self.assertEqual(self.capture['blockers'],{347:[[73,235],[107]],354:[[235],[107,349],[347]]})
        rows = json.loads((self.root/homes.BUILD/'screens.json').read_text())
        self.assertEqual(len(rows),9)
        for row,(label,body) in zip(rows,homes.forms()):
            self.assertEqual(row['label'],label)
            obj = self.root/homes.BUILD/(label+'.o')
            data,functions = homes.build.link_owner(self.root,self.root/homes.BUILD,obj,homes.OWNER)
            _,_,actual = homes.previous.facts(obj,data,functions,list(self.truth))
            for k,v in actual.items():
                self.assertEqual(row[k],v,(label,k))
            self.assertEqual(homes.previous.same_functions(self.root/homes.BUILD/'predecessor.o',obj,(source.FUNCTION,)),18)
            self.assertEqual(homes.previous.normalized_pools(obj),homes.previous.normalized_pools(self.root/homes.BUILD/'predecessor.o'))
            self.assertEqual((self.root/homes.BUILD/(label+'.c')).read_text(),
                homes.recovered_owner(source.raw_text(self.root/'conker/src/game/generated_C1D70.c'),body))
        self.assertEqual(min(r['differences'] for r in rows),6)

    def test_02_native_identity_vector_and_interference_controls(self):
        work = self.root/homes.BUILD/'compiler-selected-gates'
        events = [json.loads(x[10:]) for x in (work/'debugger.txt').read_text().splitlines() if x.startswith('RECT_TEMP ')]
        with homes.current_context():
            constraints = homes.compiler.validate_allocation(self.root,self.root/homes.BUILD/'allocation-selected-5')['constraints']
        controls = []
        for field,value in (('index',156),('temporary',0),('ichain',0),('pid',0),('inferior',99),('host_pc',0)):
            bad = copy.deepcopy(events)
            bad[6][field] = value
            controls.append(bad)
        for index in (12,14):
            bad = copy.deepcopy(events)
            raw = bytearray.fromhex(bad[index]['forbidden']['raw'])
            raw[3] ^= 0x80
            bad[index]['forbidden']['raw'] = raw.hex()
            controls.append(bad)
        controls.extend((events[:-1],events[::-1]))
        bad = copy.deepcopy(events)
        for row in bad:
            row['pid'] = 0
        controls.append(bad)
        for bad in controls:
            with self.assertRaises((ValueError,StopIteration)):
                homes.checked_events(bad,constraints)
        bad = copy.deepcopy(constraints)
        row = next(r for r in bad if r['expression']==347)
        row['interference'] = [i for i in row['interference'] if i not in (73,235)]
        with self.assertRaises(ValueError):
            homes.checked_events(events,bad)

    def test_03_complete_cfg_and_effective_home_controls(self):
        self.assertEqual(source.proof(self.raw,self.truth)['states'],384)
        for index in source.PATCHES:
            bad = list(self.truth)
            bad[index] ^= 4
            with self.assertRaises(ValueError):
                source.proof(self.raw,bad)
        for index in (0,134,205,210,211,224,242,254,344,345):
            b = list(self.truth)
            b[index] ^= 1<<16
            with self.assertRaises(ValueError):
                source.proof(self.raw,b)
        a,b = list(self.raw),list(self.truth)
        a[198] = b[198] = 0x27A10010
        with self.assertRaisesRegex(ValueError,'escapes'):
            source.proof(a,b)
        self.assertEqual((self.qualified['words'],self.qualified['frame'],self.qualified['guards'],
            self.qualified['normalized_differences']),(346,136,6,0))

    def test_04_external_state_and_live_home_values(self):
        count = 0
        for memory,args in corpus.cases():
            expected,cursor,trap = guest.reference(memory,args)
            self.assertIsNone(trap)
            for phase in (0,8):
                a = FrameTrace(self.raw,memory,args,phase=phase).run()
                b = FrameTrace(self.truth,memory,args,phase=phase).run()
                self.assertEqual(state(a),state(b))
                self.assertEqual((guest.base.public(b.memory),b.r[2]),(guest.base.public(expected),cursor))
                count += 1
        self.assertEqual(count,5760)

    def test_05_every_fault_prefix_and_private_value_control(self):
        prefixes = 0
        for flip,inset,tint,phase,position in itertools.product(range(4),(0,1),(0,1),(0,8),(-4.75,4.25)):
            memory,args = guest.fixture((2.5,3.25,position,-4.125,4096.,32.5,20.25),
                flip=flip,tint=tint,offsets=(17,inset,-5),animation=129,frame=127,speed=255,timestep=255)
            complete = FrameTrace(self.raw,memory,args,phase=phase).run()
            for fault in range(complete.accesses):
                states = []
                for words in (self.raw,self.truth):
                    model = FrameTrace(words,memory,args,phase=phase,fault=fault)
                    with self.assertRaises(guest.base.edge.AccessFault):
                        model.run()
                    states.append(state(model))
                self.assertEqual(*states)
                prefixes += 1
        memory,args = guest.fixture((2.5,3.25,4.25,-4.125,4096.,32.5,20.25))
        a = FrameTrace(self.raw,memory,args).run()
        bad = list(self.raw)
        bad[205] ^= 1<<16
        b = FrameTrace(bad,memory,args).run()
        self.assertEqual(guest.base.public(a.memory),guest.base.public(b.memory))
        self.assertNotEqual(state(a),state(b))
        (self.out/'fault-prefixes.json').write_text(json.dumps(dict(states=64,equal_prefixes=prefixes,
            private_value_control=True,fully_mapped_private_frame_contract=True),indent=2)+'\n')

    def test_06_private_frame_alias_is_rejected_not_hidden(self):
        memory,args = guest.fixture()
        for offset in (0,4,8,12,132):
            model = FrameTrace(self.raw,memory,(guest.STACK-136+offset,*args[1:]))
            with self.assertRaisesRegex(ValueError,'aliases'):
                model.run()

    def test_07_pinned_inputs_fixtures_and_no_repeat(self):
        with source.historical_view(self.root,self.out):
            read = Path.read_bytes
            for index,relative in enumerate(homes.INPUTS):
                for path in (self.root/relative,self.root/homes.BUILD/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                        with self.assertRaises(ValueError):
                            homes.freeze(self.root,self.root/homes.BUILD)
            with self.assertRaisesRegex(ValueError,'Preserve existing'):
                homes.trace(self.root,self.root/homes.BUILD)
            with self.assertRaisesRegex(ValueError,'Preserve existing'):
                homes.allocation(self.root,self.root/homes.BUILD)

    def test_08_serial_view_exact_successor_and_real_image(self):
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        original = Path.read_bytes
        with self.assertRaisesRegex(RuntimeError,'test exception'):
            with source.historical_view(self.root,self.out):
                with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                    with source.historical_view(self.root,self.out):
                        pass
                raise RuntimeError('test exception')
        self.assertIs(Path.read_bytes,original)
        if self.stage == 'after':
            audit = source.audit(self.root,self.out)
            self.assertEqual((audit['functions'],audit['changed_ELF_bytes']),(6057,6))

    def test_09_source_regressions_in_explicit_predecessor_view(self):
        from tools.tests import test_game_packet_rectangle_clip_phases as previous
        cases = unittest.defaultTestLoader.loadTestsFromTestCase(previous.RectangleClipPhaseTests)
        # The actual successor audit above replaces the old installed-image test.
        cases = unittest.TestSuite(case for case in cases if case._testMethodName !=
            'test_12_first_prediction_and_installed_scope')
        self.assertEqual(cases.countTestCases(),12)
        with source.historical_view(self.root,self.out):
            result = unittest.TextTestRunner(verbosity=1).run(cases)
        self.assertTrue(result.wasSuccessful())


if __name__ == '__main__':
    unittest.main()
