"""Qualify stage provenance and the prolog-only improvement without match credit."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_record_gate_compiler_trace as source
from tools.tests import test_game_actor_record_gate_recovery as model
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import read
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

class RecordGateCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.normal=source.observe(cls.root,'normal',5);cls.mode6=source.observe(cls.root,'normal',6)
        cls.remaining=source.observe(cls.root,'remaining',5);cls.wire=source.wire(cls.root)
        cls.rom=(cls.root/source.source.BUILD/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>139I',cls.rom,source.source.ROM))
        cls.objects={name:cls.out/(name+'-mode-5')/'baseline.o' for name in ('normal','remaining')}
        cls.words={name:source.source.linked(cls.root,cls.out,obj,name+'-linked') for name,obj in cls.objects.items()}

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_fired_probes_full_object_identity_and_stage_transformations(self):
        for result in (self.normal,self.mode6,self.remaining):
            self.assertTrue(result['complete']['code_unchanged']);self.assertFalse(result['installable'])
        facts=self.wire['facts'];self.assertEqual(facts['initial_global_loads'],[2,1])
        self.assertEqual(facts['signed_less_than_records'],[2,0]);self.assertEqual(facts['bound_two_hardware_GPR'],21)
        self.assertEqual(facts['actor_address_records'],[5,2])
        self.assertEqual(self.normal['facts']['bound_two_saved_color'],19)
        self.assertIsNone(self.remaining['facts']['bound_two_saved_color'])
        self.assertEqual(self.normal['facts']['actor_array_saved_color'],self.remaining['facts']['actor_array_saved_color'])
        self.assertEqual(self.wire['complete']['record_count'],939)
        self.assertEqual(self.wire['complete']['optimizer_record_count'],1023)
        self.receipt('stages',UOPT_captures=3,CFE_UOPT_UGEN_wire_capture=1,
            full_normal_objects_identical=True,producer_consumer_driver_completion=True,
            facts=facts,normal_bound_saved_color=19,remaining_bound_saved_color=None,
            suppressed_real_timings_or_original_retail_compiler_not_claimed=True)

    def test_02_effective_wire_and_allocation_counterexamples(self):
        complete=self.wire['complete'];count=0
        for stage,name in (('records','lod'),('optimizer_records','rldc'),('optimizer_records','rlda')):
            wrong=copy.deepcopy(complete)
            records=wrong[stage]
            at=next(i for i,r in enumerate(records) if (r['name']==name and
                (r['block']==747 if name=='lod' else r['constants'] and r['constants'][0]==2 if name=='rldc' else r['block']==752)))
            if name=='lod':records.pop(at)
            elif name=='rldc':records[at]['words'][1]=20
            else:records[at]['words'][2]=17
            with self.assertRaises(ValueError):source.wire_facts(wrong['records'],wrong['optimizer_records'])
            count+=1
        before=copy.deepcopy(complete['records']);before[next(i for i,r in enumerate(before) if r['name']=='ent' and r['block']==760)]['block']=761
        with self.assertRaises(ValueError):source.wire_facts(before,complete['optimizer_records'])
        count+=1
        for variant in ('normal','remaining'):
            text=(self.out/(variant+'-mode-5')/'uoptlist').read_text()
            for old,new in (('M  760    -4vreg','M  760    -8vreg'),('IN LOCAL OPTIMIZATION OF '+model.source.FUNCTION,'wrong procedure')):
                self.assertIn(old,text)
                with self.assertRaises(ValueError):source.allocation_facts(text.replace(old,new),variant)
                count+=1
        log=(self.out/'normal-mode-5'/'debugger.txt').read_text()
        for wrong in (log.replace('TRACE_EXIT inferior=3 code=0','TRACE_EXIT inferior=3 code=1'),
                log.replace('TRACE_EXIT inferior=5 code=0',''),log.replace('/ido5.3_recomp/as1','/ido5.3_recomp/other')):
            with self.assertRaises(ValueError):source.lifecycle(self.root,wrong)
            count+=1
        self.receipt('controls',effective_wire_and_allocation_controls=count,unknown_procedures_rejected=True)

    def test_03_prolog_recovered_but_full_slot_still_rejected(self):
        words=self.words['remaining'];self.assertEqual(len(words),135)
        raw,_=model.source.parts(self.objects['remaining']);self.assertEqual(hashlib.sha256(raw).hexdigest(),source.HASHES['remaining'])
        self.assertEqual(words[:8],self.truth[:8]);self.assertEqual(sum(a!=b for a,b in zip(words,self.truth)),126)
        self.assertEqual(same_functions(self.objects['normal'],self.objects['remaining'],(model.source.FUNCTION,)),11)
        self.assertEqual(normalized_pools(self.objects['normal']),normalized_pools(self.objects['remaining']))
        text=emit_padded_assembly(self.objects['remaining'],self.root/model.source.BUILD/'before-record_gate_original',
            filename=model.source.OWNER,word_patches_path=self.root/model.source.BUILD/'before-guards')
        asm=self.out/'remaining-padded.s';asm.write_text(text);obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
        data,fs=model.source.build.link_owner(self.root,self.out,obj,model.source.OWNER)
        slot=struct.unpack_from('>139I',data,fs[model.source.FUNCTION]['value'])
        self.assertEqual(sum(a!=b for a,b in zip(slot,self.truth)),130)
        matched=0
        for cut in range(8):
            memory=model.fixture();machines=[model.Oracle(w,memory) for w in (self.truth,words)]
            for m in machines:
                m.access_fault=cut
                with self.assertRaises(faults.AccessBoundary):m.run()
            if cut<7:self.assertEqual(model.private(machines[0]),model.private(machines[1]));matched+=1
            else:self.assertNotEqual(model.private(machines[0]),model.private(machines[1]))
        self.receipt('prolog',retail_words=139,control_words=135,frame=64,first_eight_words_exact=True,
            early_fault_equal_prefixes=matched,next_fault_rejects_at=7,raw_overlap_differences=126,
            padded_slot_differences=130,unchanged_neighbors=11,actor_base_and_gate_CSE_still_unrecovered=True,
            installable=False,no_matching_credit=True)

    def test_04_public_and_connected_helpers_preserved(self):
        cases=0
        lookup={model.LOOKUP+i*4:w for i,w in enumerate(struct.unpack_from('>28I',self.rom,0x141E5C))}
        setter={model.OVERLAY+i*4:w for i,w in enumerate(struct.unpack_from('>6I',self.rom,0x1C37C8))}
        for gate,masks,selector,value,present,phase in itertools.product(range(3),range(4),(0,1,100,255),
                (0,1,0xffffffff,0x80000000,0x7fffffff),(False,True),(0,8)):
            memory=model.fixture(gate,masks,selector,value,present)
            want,calls=model.reference(memory,selector,value,present)
            m=model.Oracle(self.words['remaining'],memory,phase=phase,present=present).run()
            self.assertEqual((model.public(m.memory),m.calls),(model.public(want),calls));cases+=1
        sparse=connected=0
        for delta,masks,mode,phase in itertools.product((-321,-160,-159,-1,0,159,160,321,0x7fffffff,0x80000000),range(4),range(5),(0,8)):
            memory=model.fixture(masks=masks,delta=delta);want,calls=model.reference(memory,delta=delta,mode=mode)
            m=model.Oracle(self.words['remaining'],memory,phase,delta,True,mode).run()
            self.assertEqual((model.public(m.memory),m.calls),(model.public(want),calls));sparse+=1
        for value,phase in itertools.product((0,255,256,0xffffffff,0x80000000,0x7fffffff),(0,8)):
            memory=model.fixture(masks=2,value=value);want,calls=model.reference(memory,value=value,actual_offsets=True)
            m=model.Oracle(self.words['remaining'],memory,phase=phase,connected={**lookup,**setter}).run()
            self.assertEqual((model.public(m.memory),m.calls),(model.public(want),calls));connected+=1
        self.receipt('public',core_cases=cases,sparse_mutation_cases=sparse,actual_lookup_setter_cases=connected,
            public_only_not_full_private_equivalence=True)

    def test_05_native32_and_effective_bound_control(self):
        head='#include <ultra64.h>\n'+model.source.TYPE;driver=self.out/'native-driver.c';driver.write_text(head+model.NATIVE)
        for opt in ('-O2','-O0'):
            for label,body in (('remaining',source.REMAINING),('wrong-bound',source.REMAINING.replace('i - 2 < 0','i - 1 < 0'))):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(model.native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='remaining' else 22)
        model.source.freeze(self.root,self.root/model.source.BUILD)
        self.receipt('native',cases_per_profile=256,profiles=['O2','O0'],UBSan=True,effective_bound_controls=2,
            valid_complete_objects_and_bounded_counter=True,production_source_ELF_guards_unchanged=True,
            INT_MIN_and_sparse_guest_arithmetic_excluded=True)

if __name__=='__main__':unittest.main()
