"""Behavior and padding checks for the type-0x64 timer callback."""
import csv
import io
import itertools
import struct
import subprocess
import unittest
from tools.experiments import game_type64_timer_match as match
from tools.tests import game_type64_timer_oracle as oracle

class GameType64TimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = match.prepare()

    def test_01_padders_and_guards(self):
        first, second = match.pad_both(self.state)
        self.assertEqual(match.payload(first),match.payload(second))
        self.assertEqual(len(match.MANIFEST['guard_rows']),76)
        self.assertEqual(sum(bool(row['insert_after']) for row in match.MANIFEST['guard_rows']),2)

    def test_02_guest_normal_and_signed_boundaries(self):
        cases=[]
        for selector,timer,delta,height,mutation,phase in itertools.product((0,1,2),(0,15,180),(0,1,20),
                (0x4197ffff,0x41980000,0x7fc00000),(0,1),(0,8)):
            cases.append(oracle.Case(0,selector,timer,0,1,delta,height,mutation,phase))
        for state,timer,fade,ticks,mutation,phase in itertools.product((1,2,3,4),(0,1,180,65535),
                (0,9,10,11,254,255),(0,1,10),(0,1),(0,8)):
            cases.append(oracle.Case(state,0,timer,fade,ticks,1,0x41980000,mutation,phase))
        edge=(-2147483648,-2147483647,-214748365,-1,0,1,214748364,214748365,2147483647)
        for state,timer,fade,ticks,mutation,phase in itertools.product((0,1,2,3),(0,1,65535),
                (0,1,254,255),edge,(0,1),(0,8)):
            cases.append(oracle.Case(state,1,timer,fade,ticks,ticks,0x41980000,mutation,phase))
        self.assertEqual(len(cases),3204)
        for case in cases:
            expected,calls=oracle.reference(case)
            for words in (self.state['retail_words'],self.state['raw_words']):
                model=oracle.Oracle(words,case);model.run()
                self.assertEqual((oracle.public(model.memory),model.calls2),(expected,calls),case)
                self.assertEqual(model.r[16:24],model.initialregs[16:24])
                self.assertEqual(model.r[28:],model.initialregs[28:])
                self.assertEqual(model.f[20:],model.initialf[20:])

    def test_03_threshold_mutation_is_detected(self):
        source=self.state['source'];self.assertEqual(source.count('height >= 19.0f'),1)
        mutant,_=match.compile_owner(match.ROOT,match.OUT,source.replace('height >= 19.0f','height > 19.0f'),'threshold-mutant')
        words=oracle.load(mutant)
        case=oracle.Case(0,0,0,0,1,0,0x41980000,0,0)
        expected,calls=oracle.reference(case);model=oracle.Oracle(words,case);model.run()
        self.assertNotEqual((oracle.public(model.memory),model.calls2),(expected,calls))

    def test_04_guard_rejection(self):
        fields=None;rows=match.MANIFEST['guard_rows'];counts=[0,0,0,0]
        with self.state['guard'].open(newline='') as stream:fields=csv.DictReader(stream).fieldnames
        for i,row in enumerate(rows):
            for kind in (0,1):
                if kind==1 and row['expected_relocations'] in ('','-'):continue
                changed=[dict(r) for r in rows]
                if kind==0:changed[i]['expected']=hex(int(row['expected'],0)^1)
                else:changed[i]['expected_relocations']='-'
                buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(changed)
                path=match.OUT/'invalid-guards.csv';path.write_text(buf.getvalue())
                with self.assertRaises(ValueError):
                    match.pad_c_object.emit_padded_assembly(self.state['raw_obj'],self.state['layout'],match.OWNER,word_patches_path=path)
                counts[kind]+=1
                with self.assertRaises(ValueError):
                    match.pad_generated_object.emit_padded_assembly(self.state['raw_obj'],self.state['target'],filename=match.OWNER,word_patches_path=path)
                counts[2+kind]+=1
        self.assertEqual(counts,[76,6,76,6])

    def test_05_rebased_links(self):
        objects=(*match.pad_both(self.state),self.state['retail_obj']);links=0;results={}
        for index,obj in enumerate(objects):
            data,refs=match.payload(obj);names=sorted({name for entries in refs.values() for _,name in entries})
            for low in (0,0x7ffc,0x8000,0xfffc):
                syms={name:(0x10010000 if name.startswith('func_') else 0x80010000)+i*0x10000+low for i,name in enumerate(names)}
                expected=match.bound_blob(data,refs,syms);script=match.OUT/('rebase-%d-%04x.ld'%(index,low));script.write_text('SECTIONS { .text 0x151041E4 : SUBALIGN(4) { *(.text) } }\n')
                elf=script.with_suffix('.elf');args=['mips-linux-gnu-ld','-T',str(script),'-e',match.NAME,*['--defsym=%s=0x%X'%pair for pair in syms.items()],'-o',str(elf),str(obj)]
                proc=subprocess.run(args,capture_output=True,text=True);self.assertEqual(proc.returncode,0,proc.stderr)
                binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
                words=list(struct.unpack_from('>170I',binary.read_bytes()));self.assertEqual(words,expected);results[index,low]=words;links+=1
        self.assertEqual(links,12)
        for low in (0,0x7ffc,0x8000,0xfffc):self.assertEqual(results[0,low],results[1,low]);self.assertEqual(results[1,low],results[2,low])

    def test_06_native(self):
        from tools.tests import game_type64_timer_native
        game_type64_timer_native.main()

    def test_07_connected_retail_walker(self):
        from tools.tests import game_type64_walker_oracle as walker
        rom=(match.ROOT/'conker/conker.us.bin').read_bytes()
        walker_words=struct.unpack_from('>74I',rom,0x194698)
        child=oracle.ENTRY
        class Combined(walker.Oracle):
            def __init__(self,child_words,wcase,tcase,memory):
                super().__init__(walker_words,wcase);self.tcase=tcase;self.memory.update(memory)
                self.code.update(dict(zip(range(child,child+len(child_words)*4,4),child_words)));self.events2=[]
            def record_call(self,target):
                assert target==child or target in oracle.SIGNATURE,hex(target)
                args=tuple(self.arguments(1 if target==child else oracle.SIGNATURE[target]))
                self.events2.append((target,args));self.calls.append((target,args))
            def hook(self,target):
                assert target in oracle.SIGNATURE
                if self.tcase.mutation and target==oracle.START:
                    walker.put(self.memory,oracle.REC+0x10,oracle.ALT);walker.put(self.memory,oracle.REC+0x14,oracle.ALT)
                if self.tcase.mutation and target==oracle.ADJUST:walker.put(self.memory,oracle.OWNER+0x318,oracle.ALT_ACTOR)
                for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
                for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
                self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
        cases=[]
        for selector,height,mutation,row,phase in itertools.product((0,1,2),(0x4197ffff,0x41980000),(0,1),(0,1),(0,8)):
            cases.append((oracle.Case(0,selector,15,0,1,20,height,mutation,phase),row))
        for state,timer,fade,ticks,mutation,row in itertools.product((1,2,3,4),(0,180),(0,11,255),(0,1),(0,1),(0,1)):
            cases.append((oracle.Case(state,0,timer,fade,ticks,1,0x41980000,mutation,0),row))
        self.assertEqual(len(cases),240)
        for case,row in cases:
            wc=walker.Case(0,0,0,case.phase);memory=walker.fixture(wc);memory.update(oracle.fixture(case))
            memory.update({walker.TABLE+i:b for i,b in enumerate(rom[0x22FF68:0x22FF68+101*52])})
            walker.put(memory,oracle.REC+8,0);walker.put(memory,walker.LISTS+row*0x1a0+100*4,oracle.REC)
            self.assertEqual(walker.read(memory,walker.TABLE+100*52+4),child)
            expected,events=oracle.reference(case);want=walker.public(dict(memory));want.update(expected)
            walker.put(want,oracle.REC+8,0);walker.put(want,walker.SLOTS+4,0)
            for child_words in (self.state['retail_words'],self.state['raw_words']):
                model=Combined(child_words,wc,case,memory);model.run()
                self.assertEqual((walker.public(model.memory),model.events2),(want,[(child,(oracle.REC,))]+events),case)
                self.assertEqual(model.r[16:24],model.before[16:24]);self.assertEqual(model.r[28:],model.before[28:])

    def test_08_external_access_cuts(self):
        class Boundary(Exception):pass
        class Cut(oracle.Oracle):
            def __init__(self,words,case,cut):self.boundary=cut;self.external_count=0;super().__init__(words,case)
            def check(self,address):
                if self.own_instruction and not oracle.STACK-2048<=address<oracle.STACK+512:
                    if self.external_count==self.boundary:raise Boundary()
                    self.external_count+=1
            def get(self,address,size):self.check(address);return super().get(address,size)
            def put(self,address,value,size):
                if self.recording:self.check(address)
                return super().put(address,value,size)
        cases=[oracle.Case(0,0,15,0,1,1,0x41980000,0,0),oracle.Case(0,1,15,0,1,1,0x41980000,1,8),
            oracle.Case(1,0,15,254,1,1,0x41980000,0,0),oracle.Case(2,0,0,0,1,1,0x41980000,1,8),
            oracle.Case(3,0,0,11,1,1,0x41980000,0,0),oracle.Case(3,0,0,9,1,1,0x41980000,0,8)]
        count=0
        for case in cases:
            total=Cut(self.state['retail_words'],case,None);total.run()
            for cut in range(total.external_count):
                values=[]
                for words in (self.state['retail_words'],self.state['raw_words']):
                    model=Cut(words,case,cut)
                    with self.assertRaises(Boundary):model.run()
                    values.append((oracle.public(model.memory),model.calls2))
                self.assertEqual(values[0],values[1],(case,cut));count+=1
        self.assertEqual(count,44)

    def test_09_wrong_replacements_are_detected(self):
        rows=match.MANIFEST['guard_rows'];fields=list(rows[0]);inserts=[i for i,r in enumerate(rows) if r['insert_after']]
        controls=[(0,'replacement'),(len(rows)//2,'replacement'),(len(rows)-1,'replacement')]+[(i,'insert_after') for i in inserts]
        self.assertEqual(len(controls),5)
        for index,key in controls:
            broken=[dict(r) for r in rows];broken[index][key]=hex(int(broken[index][key],0)^1)
            buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(broken)
            path=match.OUT/'wrong-replacement.csv';path.write_text(buf.getvalue())
            assembly=match.pad_c_object.emit_padded_assembly(self.state['raw_obj'],self.state['layout'],match.OWNER,word_patches_path=path)
            obj=match.assemble(assembly,'wrong-replacement');raw,refs=match.payload(obj)
            words=match.bound_blob(raw,refs,{nm:self.state['symbols'][nm] for group in refs.values() for _,nm in group})
            self.assertNotEqual(tuple(words),self.state['retail_words'],(index,key))

if __name__ == '__main__':
    unittest.main()
