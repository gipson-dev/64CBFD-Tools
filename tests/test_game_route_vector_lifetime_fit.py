"""Keep rejected lifetime probes reproducible without relaxing the retail gate."""
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_vector_lifetime_fit as source
from tools.tests import test_game_route_vector_builder as vector


class RouteVectorLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.receipt=source.qualify(cls.root,cls.out)
        cls.values=source.freeze(cls.root,cls.out)
        cls.truth=struct.unpack_from('>83I',cls.values['conker/conker.us.bin'],source.model.ROM)
        cls.bodies=[]
        for name in ('local-baseline','named-declarations-0123'):
            _,words,_=source.measure(cls.root,cls.out,name,dict(list(source.forms())+list(source.declaration_forms()))[name])
            cls.bodies.append(words)

    def test_01_complete_screen_and_unchanged_owner(self):
        rows=self.receipt['candidates'];self.assertEqual(len(rows),28)
        self.assertEqual(len({r['name'] for r in rows}),28)
        for row in rows:
            self.assertEqual((row['frame'],row['neighbors'],row['saved']),(16,72,[(18,12),(17,8),(16,4)]))
            self.assertFalse(row['diagnostics']);self.assertFalse(row['installable'])
        self.assertEqual({r['raw_sha256'] for r in rows},{source.RAW_SHA,source.NAMED_SHA})
        self.assertEqual(self.receipt['matching_credit'],0)

    def test_02_argument_qualifiers_and_pure_declarations_only(self):
        base=dict(source.forms())['local-baseline'];statements=base.split('\n\n',1)[1]
        for name,body in source.forms():
            self.assertEqual(body.split('\n\n',1)[1],statements,name)
            self.assertNotIn('const u8',body);self.assertNotIn('const f32',body)
        before=self.values['conker/src/game/generated_B3020.c'].decode()
        for name,body in list(source.forms())+list(source.declaration_forms()):
            owner=source.owner(before,body)
            header=next(line for line in body.splitlines() if line.startswith('void func_15088F30('))
            self.assertIn('    extern '+header[:-2]+';',owner)
        for _,body in source.declaration_forms():
            tail=body.split('\n\n',1)[1]
            if 'tableSource' in tail:
                tail=tail.replace('    tableSource = &D_800D2350;\n    pointCount = 4;\n','').replace(
                    'table = *tableSource;','table = D_800D2350;').replace('== pointCount)','== 4)').replace(
                    'slot != pointCount','slot != 4')
            self.assertEqual(tail,statements)
        with self.assertRaises(ValueError):source.owner(before.replace('extern s32 func_15088F30();','extern void func_15088F30();'),base)
        with self.assertRaises(ValueError):source.owner(before,base.replace('void func_15088F30(','s32 func_15088F30('))

    def test_03_bounded_guest_trace_ABI_and_effective_unsigned_control(self):
        cases=[(mask,pattern,coordinate,speed,0) for mask,pattern,coordinate,speed in itertools.product(
            (0,5,15),(0,2,18,242),(0,1,6),(0x3F000000,0xBF000000))]
        cases.extend((mask,pattern,0,speed,alias) for alias,mask,pattern,speed in itertools.product(
            range(1,11),(0,5),(2,242),(0x3F000000,0x3F800000)))
        cases.extend((0,242,0,speed,0) for speed in vector.SPEEDS)
        witnesses=[]
        for index,words in enumerate(self.bodies):
            mutant=list(words);at=next(i for i,w in enumerate(words) if w>>26==33);mutant[at]|=4<<26
            witness=False
            for count,p in enumerate(cases):
                memory,args=vector.fixture(*p);expected,trace=vector.reference(memory,args)
                for body in (words,self.truth):
                    m=vector.VectorOracle(body,memory,args,(count&1)*8).run()
                    self.assertEqual((vector.public(m.memory),m.trace),(vector.public(expected),trace))
                    self.assertEqual(m.calls,[]);self.assertEqual(m.f[20:],m.saved_f)
                    for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                if not witness:
                    bad=vector.VectorOracle(mutant,memory,args).run()
                    witness=vector.public(bad.memory)!=vector.public(expected)
            self.assertTrue(witness);witnesses.append(witness)
        (self.out/'guest-lifetime.json').write_text(json.dumps(dict(
            cases_per_body=len(cases),raw_bodies=2,paired_executions=len(cases)*2,
            exact_public_memory_and_trace=True,guest_aliases=10,effective_unsigned_controls=len(witnesses),
            native_or_full_fault_equivalence_not_claimed=True,matching_credit=0),indent=2)+'\n')

    def test_04_first_private_store_still_rejects_both_bodies(self):
        source.model.require_retail_stack_contract(self.truth)
        for words in self.bodies:
            with self.assertRaisesRegex(ValueError,'not installable'):source.model.require_retail_stack_contract(words)
            machines=[];memory,args=vector.fixture()
            for body in (words,self.truth):
                m=vector.VectorOracle(body,memory,args);m.access_fault=1
                with self.assertRaises(vector.base.faults.AccessBoundary):m.run()
                machines.append(m)
            self.assertNotEqual(machines[0].memory,machines[1].memory)
            self.assertEqual(vector.read(machines[0].memory,vector.STACK-4),machines[0].before[18])
            self.assertEqual(vector.read(machines[1].memory,vector.STACK-4),machines[1].before[17])

    def test_05_live_and_snapshot_inputs_fail_closed(self):
        raw=source.model.raw_read;count=0
        paths=list(source.INPUTS)
        for index,name in enumerate(paths):
            for target in (self.root/name,self.out/('before-%02d'%index)):
                def corrupt(path,*args,**kwargs):
                    data=raw(path,*args,**kwargs)
                    return data+b'\0' if path==target else data
                with patch.object(Path,'read_bytes',corrupt),self.assertRaises(ValueError):source.freeze(self.root,self.out)
                count+=1
        self.assertEqual(count,26);source.freeze(self.root,self.out)
        self.assertEqual(source.model.INPUTS['conker/build/conker.us.elf'],
            'a5c5541dc8f6863ebefac2896237ce0bc39a88e3893711c35cd0393fd851ecd7')

    def test_06_all_raw_words_and_bindings_fail_closed(self):
        for named,label in ((False,'local-baseline'),(True,'named-declarations-0123')):
            obj=self.out/(label+'.o');text,functions,rel=source.model.parse_object(obj);f=functions[source.model.FUNCTION]
            source.checked_screen(obj,named)
            for at in range(f['value'],f['value']+f['size'],4):
                bad=bytearray(text);bad[at]^=1
                with patch.object(source.model,'parse_object',return_value=(bytes(bad),functions,rel)),self.assertRaises(ValueError):
                    source.checked_screen(obj,named)
            for at in (at for at in rel if f['value']<=at<f['value']+f['size']):
                bad=dict(rel);bad[at]=[('R_MIPS_HI16','D_800D2354')]
                with patch.object(source.model,'parse_object',return_value=(text,functions,bad)),self.assertRaises(ValueError):
                    source.checked_screen(obj,named)


if __name__=='__main__':unittest.main()
