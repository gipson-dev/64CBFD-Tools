"""Bounded owner, caller, padder, and native checks for the session reset."""
import csv
import io
import struct
import subprocess
import unittest

from tools.experiments import game_session_reset_match as match
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_queued_segment_writer import STACK

ENTRY = 0x1500E5C0
CALLS = (0x15012470, 0x15008A10, 0x15012770, 0x100226F0)
RANGES = ((0x800E0950,20), (0x800D9890,0xE0), (0x80088870,4),
          (0x800BE500,5), (0x80088980,1), (0x800D9AA0,12),
          (0x800BE4F0,4), (0x80088B40,1), (0x800B0DF0,4))


def fixture(seed):
    memory = {STACK+i:(seed+i*7)&255 for i in range(-0x200,0x80)}
    for address, length in RANGES:
        memory.update({address+i:(seed*11+i*3+0x57)&255 for i in range(-8,length+8)})
    return memory


class ResetOracle(TriangleOracle):
    def __init__(self, words, seed, mode, entry=ENTRY, connected=None, tail=False):
        self.mode = mode
        super().__init__(words, fixture(seed), entry=entry, arguments=(0,0,0,0),
                         connected=connected, tail=tail)

    def record_call(self, target):
        assert target in CALLS or target == ENTRY, hex(target)
        self.calls.append((target, tuple(self.r[4:6]) if target == CALLS[-1] else ()))

    def hook(self, target):
        assert target in CALLS
        if target == CALLS[-1]:
            address, length = self.r[4:6]
            assert (address,length) == (0x800BE500,5)
            for i in range(length):
                self.put(address+i,0,1)
        elif self.mode:
            self.put(0x800D9921,0x30+CALLS.index(target),1)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]


def external(model):
    memory = {a:v for a,v in model.memory.items() if not STACK-0x200 <= a < STACK+0x80}
    events = [e for e in model.events if e[0] in ('R','W') and not STACK-0x200 <= e[1] < STACK+0x80]
    return memory, model.calls, events


class StopAccess(Exception):
    pass


class CutOracle(ResetOracle):
    def __init__(self, *args, cut=None, **kwargs):
        self.cut, self.accesses = cut, 0
        super().__init__(*args, **kwargs)

    def check(self, address):
        if self.recording and not STACK-0x200 <= address < STACK+0x80:
            if self.cut == self.accesses:
                raise StopAccess()
            self.accesses += 1

    def get(self, address, size):
        self.check(address)
        return super().get(address,size)

    def put(self, address, value, size):
        self.check(address)
        return super().put(address,value,size)


def run_cut(words, seed, mode, cut=None):
    model = CutOracle(words,seed,mode,cut=cut)
    try:
        model.run()
        stopped = False
    except StopAccess:
        stopped = True
    return stopped, model.accesses, external(model)


class GameSessionResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare()
        cls.retail = cls.state['retail_words']
        cls.candidate = cls.state['compiled_words']

    def test_01_both_padders(self):
        first, second = match.pad_both(self.state)
        self.assertEqual(match.payload(first), match.payload(second))
        self.assertEqual(len(match.MANIFEST['guard_rows']),31)

    def test_02_guest_access_and_controls(self):
        for seed in range(12):
            for mode in (0,1):
                retail = ResetOracle(self.retail,seed,mode).run()
                candidate = ResetOracle(self.candidate,seed,mode).run()
                self.assertEqual(external(retail),external(candidate))
        bad = list(self.retail)
        self.assertEqual(bad[0x34//4:0x3c//4], [0xA040FFFD,0xA040FFFE])
        bad[0x34//4],bad[0x38//4] = bad[0x38//4],bad[0x34//4]
        self.assertNotEqual(external(ResetOracle(self.retail,0,0).run()),
                            external(ResetOracle(bad,0,0).run()))

    def test_03_access_prefixes(self):
        checked = 0
        for seed in range(6):
            for mode in (0,1):
                complete = run_cut(self.retail,seed,mode)
                self.assertFalse(complete[0])
                for cut in range(complete[1]+1):
                    self.assertEqual(run_cut(self.retail,seed,mode,cut),
                                     run_cut(self.candidate,seed,mode,cut))
                    checked += 1
        self.assertEqual(checked,882)

    def test_04_original_caller_window(self):
        rom = (match.ROOT/'conker/conker.us.bin').read_bytes()
        caller = list(struct.unpack_from('>4I',rom,0x3B9E4))
        self.assertEqual(caller,[0x0D403970,0,0x3C18800B,0x8F180DF0])
        # The last two words form a test-only return after the original window.
        window = caller+[0x02C00008,0]
        outcomes = []
        for words in (self.retail,self.candidate):
            connected = {ENTRY+4*i:w for i,w in enumerate(words)}
            model = ResetOracle(window,7,1,entry=0x1500E534,connected=connected,tail=True)
            model.r[22] = model.before[22] = 0xDEAD0000
            model.run()
            outcomes.append((model.r[24],external(model)))
        self.assertEqual(outcomes[0],outcomes[1])
        self.assertEqual([a for a,_ in outcomes[0][1][1]],[ENTRY,*CALLS])

    def test_05_guard_rejection(self):
        with self.state['guards'].open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        counts = [0,0]
        for i in range(len(rows)):
            for kind in (0,1):
                if kind == 1 and rows[i]['expected_relocations'] in ('','-'):
                    continue
                altered = [dict(row) for row in rows]
                if kind == 0:
                    altered[i]['expected'] = hex(int(altered[i]['expected'],0)^1)
                else:
                    altered[i]['expected_relocations'] = '-'
                buffer = io.StringIO(newline='')
                writer = csv.DictWriter(buffer,fieldnames=fields,lineterminator='\n')
                writer.writeheader()
                writer.writerows(altered)
                path = match.OUT/'bad-guards.csv'
                path.write_text(buffer.getvalue())
                with self.assertRaises(ValueError):
                    match.pad_c_object.emit_padded_assembly(self.state['normal'],
                        match.ROOT/'conker/retail_layout.us.txt', match.OWNER,
                        function_objects={match.NAME:self.state['special']},word_patches_path=path)
                counts[kind] += 1
        self.assertEqual(counts,[31,12])

    def test_06_native32(self):
        from tools.tests import game_session_reset_native
        game_session_reset_native.main()

    def test_07_rebased_retail_comparison(self):
        padded, _ = match.pad_both(self.state)
        data, refs = match.payload(padded)
        text = ('.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+match.NAME+
                '\n.type '+match.NAME+',@function\n'+match.NAME+':\n')
        for i,(word,) in enumerate(struct.iter_unpack('>I',data)):
            for kind,symbol in refs.get(4*i,[]):
                text += '.reloc ., '+kind+', '+symbol+'\n'
            text += '.word 0x%08X\n' % word
        obj = match.assemble(text+'.size '+match.NAME+',.-'+match.NAME+'\n','rebase-normalized')
        names = sorted({name for entries in refs.values() for _,name in entries})
        for low in (0,0x7FF0,0x8000,0xFFF0):
            symbols = {name:(0x150A0000+i*0x1000 if name.startswith('func_') else
                       0x100226F0 if name=='bzero' else 0x81000000+i*0x10000+low)
                       for i,name in enumerate(names)}
            symbols['D_800E0964'] = symbols['D_800E0950']+20
            symbols['D_800D9946'] = symbols['D_800D993A']+12
            results = []
            for variant,path in enumerate((match.OUT/'retail.o',obj)):
                script = match.OUT/('rebase-%04x-%d.ld' % (low,variant))
                script.write_text('SECTIONS { .text 0x1500E5C0 : SUBALIGN(4) { *(.text) } }\n')
                elf, binary = script.with_suffix('.elf'), script.with_suffix('.bin')
                command = ['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,
                    *['--defsym=%s=0x%X' % pair for pair in symbols.items()],'-o',str(elf),str(path)]
                result = subprocess.run(command,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',
                                str(elf),str(binary)],check=True,capture_output=True)
                results.append(binary.read_bytes()[:332])
            self.assertEqual(results[0],results[1])

    def test_08_bad_replacements_are_detected(self):
        with self.state['guards'].open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        for i in (0,len(rows)//2,len(rows)-1):
            changed = [dict(row) for row in rows]
            changed[i]['replacement'] = hex(int(changed[i]['replacement'],0)^1)
            buffer = io.StringIO(newline='')
            writer = csv.DictWriter(buffer,fieldnames=fields,lineterminator='\n')
            writer.writeheader()
            writer.writerows(changed)
            path = match.OUT/'bad-replacement.csv'
            path.write_text(buffer.getvalue())
            text = match.pad_c_object.emit_padded_assembly(self.state['normal'],
                match.ROOT/'conker/retail_layout.us.txt',match.OWNER,
                function_objects={match.NAME:self.state['special']},word_patches_path=path)
            obj = match.assemble(text,'bad-replacement')
            self.assertNotEqual(match.payload(obj), (self.state['retail'],self.state['retail_refs']))



if __name__ == '__main__':
    unittest.main()
