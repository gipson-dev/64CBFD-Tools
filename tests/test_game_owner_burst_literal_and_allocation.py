"""Qualify the real scale pool and improved body without installing a mismatch."""
import copy
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_owner_burst_literal_candidates as literal
from tools.experiments import game_owner_burst_allocation_stages as stages
from tools.tests import test_game_owner_burst_emitter as prior
from tools.tests import test_game_owner_burst_frame_trace as packets


class BurstLiteralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/literal.BUILD
        cls.obj,cls.padded,cls.images,cls.row=literal.qualify(cls.root,cls.out)
        cls.trace=stages.trace(cls.root,cls.root/stages.BUILD)
        prior.OwnerBurstRecoveryTests.setUpClass()
        cls.harness=prior.OwnerBurstRecoveryTests('test_02_full_uniform_stack_public_protocol')

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def fixture(self,*args,**kwargs):
        memory,case=prior.fixture(*args,**kwargs)
        prior.put(memory,case['symbols']['D_800A196C'],0x42688F5C)
        return memory,case

    def compare(self,memory,case,images=None,entry=literal.source.ENTRY):
        return self.harness.compare(memory,case,images=images or [self.harness.truth,*self.images],entry=entry)

    def test_01_literal_pool_and_full_owner_isolation(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(288,352,75))
        self.assertEqual((self.row['unchanged_raw_neighbors'],self.row['unchanged_padded_neighbors']),(11,11))
        self.assertEqual(self.images[0],self.images[1]);self.assertEqual(len(self.row['bindings']),25)
        self.assertEqual(self.row['literal_binding']['addends'],[0,0])
        self.assertEqual(self.row['literal_binding']['live_bytes'],4)
        memory,case=prior.fixture()
        self.compare(memory,case)
        self.receipt('shape',words=288,frame=352,retail_frame=336,unequal_words=75,
            raw_padded_equal=True,raw_padded_neighbors=11,literal_pool_live_bytes=4,
            terminal_alignment_not_installed=True,synthetic_scale_memory_also_checked=True,
            new_guards=0,installed=False,matching_credit=0)

    def test_02_pool_binding_negative_controls(self):
        source=literal.source;original_sections=source.projection.sections;sections=original_sections(self.obj);count=0
        for value in (bytes.fromhex('42688f5d')+b'\0'*12,sections['.rodata'][1][:-1],
                sections['.rodata'][1][:-1]+b'\1',b''):
            wrong=dict(sections);wrong['.rodata']=(0,value)
            with patch.object(source.projection,'sections',lambda p:wrong if p==self.obj else original_sections(p)):
                with self.assertRaises(ValueError):literal.pool_binding(self.root,self.out,self.obj)
            count+=1
        with patch.object(literal,'nm_anchors',return_value={'D_800A196C':literal.POOL_ADDRESS+4}):
            with self.assertRaises(ValueError):literal.pool_binding(self.root,self.out,self.obj)
        count+=1
        data,functions,relocations=source.parse_object(self.obj);offsets=[o for o,r in relocations.items() if any(s=='.rodata' for _,s in r)];offsets.sort()
        original_parser=source.parse_object
        for offset,mask in ((offsets[0],1),(offsets[1],4),(offsets[0],1<<16),(offsets[1],1<<26)):
            wrong=bytearray(data);struct.pack_into('>I',wrong,offset,struct.unpack_from('>I',wrong,offset)[0]^mask)
            with patch.object(source,'parse_object',lambda p:(wrong,functions,relocations) if p==self.obj else original_parser(p)):
                with self.assertRaises(ValueError):literal.pool_binding(self.root,self.out,self.obj)
            count+=1
        wrong=copy.deepcopy(relocations);wrong[offsets[0]]=[('R_MIPS_32','.rodata')]
        with patch.object(source,'parse_object',lambda p:(data,functions,wrong) if p==self.obj else original_parser(p)):
            with self.assertRaises(ValueError):literal.pool_binding(self.root,self.out,self.obj)
        count+=1
        with self.assertRaises(ValueError):literal.linked(self.root,self.out,self.obj,'wrong-section',pool_address=literal.POOL_ADDRESS+4)
        count+=1
        self.receipt('pool-controls',effective_controls=count)

    def test_03_complete_public_packets_with_actual_scale(self):
        harness=packets.BurstFrameTests('test_03_complete_uniform_and_nonuniform_public_packets')
        harness.harness=self.harness;harness.images=self.images;harness.out=self.out
        harness.test_03_complete_uniform_and_nonuniform_public_packets()
        synthetic=json.loads((self.out/'packets.json').read_text())
        original=prior.fixture
        def initialized(*args,**kwargs):
            memory,case=original(*args,**kwargs);prior.put(memory,case['symbols']['D_800A196C'],0x42688F5C)
            return memory,case
        with patch.object(prior,'fixture',initialized):harness.test_03_complete_uniform_and_nonuniform_public_packets()
        self.receipt('packets-both-values',synthetic=synthetic,retail=json.loads((self.out/'packets.json').read_text()),
            initial_scale_values=['1.25','58.14f'],ordinary_cases=7800,model_FP_edges=56,padding_not_masked=True)

    def test_04_rebases_and_remaining_private_gap(self):
        count=0
        for group,entry in enumerate((0x15207FF0,0x15610000)):
            symbols={n:(0x80300000+group*0x100000+i*0x10000+(0x7FFC if (i+group)%2 else 0x8004))
                if v&0x80000000 else 0x15300000+group*0x100000+i*0x1000 for i,(n,v) in enumerate(literal.source.SYMBOLS.items())}
            words,_=literal.linked(self.root,self.out,self.obj,'rebase-'+str(group),entry,symbols,symbols['D_800A196C'])
            padded=literal.source.linked(self.root,self.out,self.padded,'padded-rebase-'+str(group),entry,symbols)
            self.assertEqual(words,padded)
            for gate,state,mode,pattern,phase in itertools.product((0,1,3),(0,1),(0,2),(0,1),(0,8)):
                self.compare(*self.fixture(gate,state,previous=state,mode=mode,pattern=pattern,phase=phase,symbols=symbols),images=[words,padded],entry=entry);count+=1
        memory,case=self.fixture(pattern=1)
        machines=[prior.Oracle(w,memory,case) for w in (self.harness.truth,*self.images)]
        for machine in machines:
            machine.access_fault=0
            with self.assertRaises(prior.faults.AccessBoundary):machine.run()
        self.assertNotEqual(prior.state(machines[0]),prior.state(machines[1]))
        self.assertEqual(machines[0].r[29]-machines[1].r[29],16)
        self.receipt('rebases-private',links=2,full_protocol_cases=count,signed_HI16_carries=True,
            raw_padded_equal=True,first_fault_cut=0,SP_gap=16,installable=False)

    def test_05_native32_actual_literal_defined_fields(self):
        form=next(literal.forms());harness=packets.BurstFrameTests('test_05_native32_aligned_packet_fields')
        harness.root=self.root;harness.out=self.out
        with patch.object(packets.storage,'forms',lambda:iter([form])),patch.object(prior,'NATIVE',prior.NATIVE.replace('1.25f','58.14f')):
            harness.test_05_native32_aligned_packet_fields()

    def test_06_global_coloring_provenance_and_controls(self):
        work=self.root/stages.BUILD/'aligned-pairs';log=(work/'debugger.txt').read_text()
        record=json.loads((work/'local-receipt.json').read_text());wire=json.loads((work/'receipt.json').read_text())
        words=list(struct.unpack_from('>288I',literal.source.projection.sections(work/'baseline-linked.elf')['.text'][1]))
        facts=stages.facts(record,log,wire,words);self.assertEqual(facts,self.trace['facts']);count=0
        events=self.trace['events'];corrupt=[]
        for i in range(5):
            for key in ('host_pc','cursor','selector_word'):
                bad=copy.deepcopy(events);bad[i][key]^=4;corrupt.append(bad)
            for j in range(3):
                for key in ('live_image','live_bit','assigned_word'):
                    bad=copy.deepcopy(events);bad[i]['nodes'][j][key]^=1<<24 if key=='assigned_word' else 4;corrupt.append(bad)
        bad=copy.deepcopy(events);bad[2]['nodes'][0]['words'][8]^=4;corrupt.append(bad)
        for bad in corrupt:
            iterator=iter(bad);text='\n'.join('BURST_STAGE '+json.dumps(next(iterator)) if s.startswith('BURST_STAGE ') else s for s in log.splitlines())
            with self.assertRaises(ValueError):stages.facts(record,text,wire,words)
            count+=1
        for prefix in ('BURST_STAGE ','BURST_STAGE_REMOVED '):
            text='\n'.join(s for s in log.splitlines() if not s.startswith(prefix))
            with self.assertRaises(ValueError):stages.facts(record,text,wire,words)
            count+=1
        for expected in (0x26700028,0x00601025):
            bad=list(words);bad[bad.index(expected)]^=1
            with self.assertRaises(ValueError):stages.facts(record,log,wire,bad)
            count+=1
        bad=copy.deepcopy(wire)
        next(r for r in bad['records']['optimizer'] if r['name']=='str' and r['storage']=='R' and r['dtype']=='L' and r['offset']==3)['offset']=2
        with self.assertRaises(ValueError):stages.facts(record,log,bad,words)
        count+=1
        self.receipt('stage-controls',effective_controls=count,stages=5,colors_before=[0,0,0],
            colors_after=[14,2,1],output_GPRs=[16,3,2],reservation_survives_global_coloring=True)

    def test_07_frame_only_source_forms_and_baseline(self):
        expected=[(288,352,75,0),(290,344,181,2),(293,352,244,5),(289,344,115,1),
            (289,344,253,1),(294,344,244,6),(295,336,263,7),(288,352,75,0),
            (288,344,75,0),(289,344,115,1),(288,336,20,0),(288,336,20,0)]
        self.assertEqual(len(list(literal.forms())),len(expected))
        rows=[]
        for (label,body,types),shape in zip(literal.forms(),expected):
            obj,words,row=literal.measure(self.root,self.out,label,body,types)
            self.assertEqual(tuple(row[k] for k in ('words','frame','differences','extent_gap')),shape)
            if row['extent_gap']:
                with self.assertRaises(ValueError):literal.padded_object(self.root,self.out,obj,'reject-'+label)
            rows.append(dict(label=label,**row))
        literal.source.freeze(self.root,self.root/literal.source.BUILD)
        self.receipt('screens-baseline',forms=rows,actual_overflow_rejections=7,
            complete_production_baseline_unchanged=True,installed=False,matching_credit=0)


if __name__=='__main__':unittest.main()
