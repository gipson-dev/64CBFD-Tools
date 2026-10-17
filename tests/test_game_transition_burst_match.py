"""Real object layout, narrow scratch guards, full state/faults and first-image gate."""
import csv
from functools import lru_cache
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.experiments import game_transition_burst_match as source
from tools.experiments import game_transition_burst_installation as install
from tools.tests import game_transition_burst_match_oracle as oracle
from tools.tests import game_transition_frame_native as native
from tools.tests import test_game_transition_frame_lifetimes as frame_tests
from tools.tests import test_game_transition_completion_burst as caller_tests
from tools.tests import transition_burst_checkpoint as checkpoint
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.check_game_data_layout import audit_layout

model=oracle.previous


class BurstMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>251I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-burst',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)
        cls.factory=assembly.ViewListSetupTests.original.__func__(context,'original-factory',
            (cls.out/'before-transition_factory').read_text(),'func_1515548C')

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_words_real_homes_pool_neighbors_and_scratch_bijection(self):
        self.assertEqual(source.normalize(self.images[0]),self.truth)
        self.assertEqual(self.images[1],self.truth)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['descriptor'],self.row['payload']),
            (251,264,0xAC,0x9C))
        self.assertEqual((self.row['raw_differences'],self.row['unchanged_raw_padded_neighbors']),(11,24))
        self.assertEqual(set(source.SCRATCH_MAP),set(source.SCRATCH_MAP.values()))
        for a,b in source.PATCHES.values():
            if a>>26!=0:self.assertEqual(a&65535,b&65535)
        self.assertEqual(self.images[0][:189],self.truth[:189]);self.assertEqual(self.images[0][210:],self.truth[210:])
        source.checked_parts(*source.parts(self.obj))

    def test_02_guest_full_memory_return_state_access_order_and_public_reference(self):
        count=0;seen=set()
        for memory,seed,pattern,mode,phase in frame_tests.cases():
            expected,calls,children=model.reference(memory,seed,pattern,mode)
            machines=[oracle.BurstOracle(words,memory,self.rom,seed,pattern,mode,phase).run()
                for words in (self.truth,*self.images)]
            for machine in machines:
                self.assertEqual(model.public(machine.memory,pattern,mode,children),expected)
                self.assertEqual(machine.calls,calls);self.assertEqual(machine.r[2],1)
                self.assertEqual(oracle.state(machine),oracle.state(machines[0]))
            seen.update(machines[0].visits);count+=1
        self.assertEqual({pc-source.ENTRY for pc in seen if source.ENTRY<=pc<source.ENTRY+source.SIZE},
            set(range(0,1004,4))-{540,600})
        self.receipt('guest',three_way_cases=count,full_memory_all_inherited_padding_and_return_state=True,
            all_actual_ISA_access_order=True,natural_target_words=249,actual_factory_words=54,
            actual_copy_words=11,actual_tag_leaves=2,not_real_allocator_RNG_direction_sine_or_hardware=True)

    def test_03_native_full_typed_body_and_effective_width_controls(self):
        controls=native.controls
        def adapted(body):
            forms=controls(body);forms['word_gate']=(body.replace('transition->state & 1','*(u32 *)transition & 1'),0)
            if any(text==body for text,_ in forms.values()):raise ValueError('Ineffective native burst control')
            return forms
        with patch.object(frame_tests,'source',source),patch.object(native,'controls',adapted):
            frame_tests.FrameLifetimeTests.test_03_native32_full_body_separate_typed_caller_and_endian_limits(self)

    def test_04_all_actual_access_fault_prefixes_with_factory_and_copy(self):
        count=0;fired=0;words_seen=set()
        cases=((0,0.,1.,0,1,0),(1,0.9,-1.,0,1,0),(1,1.,1.,0,1,3),
               (1,1.,1.,1,0,2),(1,1.,1.,0,2,1))
        for flags,progress,tick,seed,pattern,mode in cases:
            memory=model.fixture(flags,progress,tick,seed)
            for phase in (0,8):
                complete=oracle.BurstOracle(self.truth,memory,self.rom,seed,pattern,mode,phase).run()
                for cut in range(complete.all_accesses):
                    states=[]
                    for words in (self.truth,self.images[1]):
                        machine=oracle.BurstOracle(words,memory,self.rom,seed,pattern,mode,phase)
                        machine.access_fault=cut
                        with self.assertRaises(faults.AccessBoundary):machine.run()
                        states.append(oracle.state(machine));words_seen.add(machine.current_pc);fired+=1
                    self.assertEqual(states[0],states[1]);count+=1
        self.receipt('faults',paired_prefixes=count,positively_fired_instances=fired,
            distinct_faulting_instruction_addresses=len(words_seen),factory_and_copy_accesses_included=True,
            guarded_complete_modeled_state_and_IO=True,not_portable_C_faults_or_MMU_FCSR_CP0=True)

    def test_05_independent_rebases_with_actual_relocated_factory(self):
        count=0
        for index,low in enumerate((0x7FFC,0x8000,0x8004)):
            entry=0x15208004+index*0x10000;base=0x15400000+index*0x100000
            anchors=dict(D_800A0860=0x80110000+index*0x10000+low,
                D_800BE9A4=0x80200000+index*0x10000+low,D_80082FA0=0x80300000+index*0x10000+low,
                D_8008FCD0=0x80400000+index*0x10000+low,
                func_150ADA20=base,func_150ADA68=base+0x1000,func_15143874=base+0x2000,
                func_1515548C=base+0x3000,memcpy=base+0x4000,sinf=base+0x5000,
                func_15167A68=base+0x6000,func_151555AC=base+0x7000)
            anchors.update({'D_800A%04X'%(0x0860+i*4):anchors['D_800A0860']+i*4 for i in range(6)})
            targets=[('original',self.original)]
            for label,obj in (('raw',self.obj),('guarded',self.padded)):
                raw,bindings=source.parts(obj)
                bindings={at:[(kind,'D_800A0860' if name=='.rodata' else name) for kind,name in rs] for at,rs in bindings.items()}
                text,unresolved=emit_function(raw,dict(value=0,size=source.SIZE),bindings,source.FUNCTION,anchors)
                self.assertFalse(unresolved)
                path=self.out/('rebase-%d-%s.s'%(index,label));path.write_text(text);target=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
                targets.append((label,target))
            images=[];factories=[]
            for label,obj in targets:
                script=self.out/('rebase-%d-%s.ld'%(index,label));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { %s(.text) } .factory 0x%X : SUBALIGN(4) { %s(.text) } }\n'%
                    (entry,obj.relative_to(self.root),anchors['func_1515548C'],self.factory.relative_to(self.root)))
                linked=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in anchors.items() if item[0]!='func_1515548C'],
                    '-o',str(elf),str(obj.relative_to(self.root)),str(self.factory.relative_to(self.root))],
                    cwd=self.root,capture_output=True,text=True)
                self.assertEqual(linked.returncode,0,linked.stderr)
                sections=source.projection.sections(elf)
                images.append(list(struct.unpack('>251I',sections['.text'][1][:source.SIZE])))
                factories.append(sections['.factory'][1][:216])
            self.assertEqual(images[0],images[2]);self.assertEqual(source.normalize(images[1]),images[0])
            self.assertTrue(factories[0]==factories[1]==factories[2])
            relocated=SimpleNamespace(**{name:getattr(model.source,name) for name in dir(model.source) if name.isupper()})
            for field,name in (('RANDOM','func_150ADA20'),('RANDOM_FLOAT','func_150ADA68'),('DIRECTION','func_15143874'),
                    ('FACTORY','func_1515548C'),('MEMCPY','memcpy'),('SINE','sinf'),('ALLOCATOR','func_15167A68'),
                    ('MODE','D_80082FA0'),('TIMESTEP','D_800BE9A4'),('TAG_TABLE','D_8008FCD0'),('POOL','D_800A0860')):
                setattr(relocated,field,anchors[name])
            relocated.ENTRY=entry;relocated.TAG=base+0x8020
            rom=bytearray(self.rom);rom[0x18293C:0x18293C+216]=factories[0]
            with patch.object(model,'source',relocated),patch.object(model,'ALT_TAG',relocated.TAG-12):
                for seed,pattern,mode,phase in itertools.product((0,0xFFFFFFFF),(0,1),(0,1,2,3),(0,8)):
                    memory=model.fixture(1,1.,1.,seed);expected,calls,children=model.reference(memory,seed,pattern,mode)
                    machines=[oracle.BurstOracle(words,memory,rom,seed,pattern,mode,phase,entry).run() for words in images]
                    for machine in machines:
                        self.assertEqual(model.public(machine.memory,pattern,mode,children),expected)
                        self.assertEqual(machine.calls,calls);self.assertEqual(oracle.state(machine),oracle.state(machines[0]))
                    count+=1
        self.receipt('rebases',independent_target_links=9,symbol_sets=3,three_way_cases=count,
            actual_factory_relocated_and_executed=True,all31_bindings_and_signed_low_carries=True,
            local_pool_rebound_to_retail_anchor_not_suppressed=True)

    def test_06_original_kind12_caller_window(self):
        with patch.object(caller_tests,'source',source):
            caller_tests.CompletionBurstTests.test_05_original_kind12_callback_window_and_success_return(self)

    def test_07_raw_binding_and_guard_corruption_controls(self):
        raw,bindings=source.parts(self.obj)
        for i in range(251):
            wrong=bytearray(raw);wrong[i*4+3]^=1
            with self.assertRaisesRegex(ValueError,'words/bindings'):source.checked_parts(wrong,bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],bindings[at][0][1]+'-wrong')]
            with self.assertRaisesRegex(ValueError,'words/bindings'):source.checked_parts(raw,wrong)
        rows=list(csv.DictReader(io.StringIO(source.guard_bytes((self.out/'before-guards').read_bytes()).decode())))
        indices=[i for i,r in enumerate(rows) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(indices),11)
        for i in indices:
            changed=[dict(r) for r in rows];changed[i]['expected']='0x%08X'%(int(changed[i]['expected'],16)^1)
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(changed[0]),lineterminator='\n')
            writer.writeheader();writer.writerows(changed);path=self.out/('wrong-guard-%d.csv'%i);path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):source.padded_object(self.root,self.out,self.obj,'wrong-guard-%d'%i,path)
        self.receipt('corruption',word_controls=251,binding_controls=31,positively_fired_guard_controls=11)

    def test_08_all_live_and_frozen_inputs_remain_pinned(self):
        source.freeze(self.root,self.out);real=hashlib.sha256;cache={}
        for key,path in source.PATHS.items():
            current=self.root/path;frozen=self.out/('before-'+key)
            cache[current]=current.read_bytes();cache[frozen]=frozen.read_bytes()
            normalized=checkpoint.previous_input(cache[current],path,self.root)
            self.assertEqual(real(normalized).hexdigest(),source.BASELINE[key]);self.assertEqual(normalized,cache[frozen])
        for key in checkpoint.AFTER:
            for stage in ('before','after'):
                path=self.root/install.BUILD/(stage+'-'+key);cache[path]=path.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        count=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Unknown burst match input'),(self.out/('before-'+key),'Changed burst match fixture')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def read_bytes(path):return wrong if path==target else cache[path]
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda path:path in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message):source.freeze(self.root,self.out)
                count+=1
        source.freeze(self.root,self.out)
        self.receipt('inputs',entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),fired_controls=count)

    def test_09_first_complete_installed_image_and_all_game_data(self):
        if not checkpoint.AFTER:self.skipTest('First complete image not installed yet')
        expected=install.expected_inputs(self.root,self.root/install.BUILD)
        self.assertEqual(json.loads((self.root/install.BUILD/'initial-prediction.json').read_text()),checkpoint.AFTER)
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        self.receipt('installed',first_complete_image_exact=True,metadata_exclusions=0,all_data=report)

    def test_10_checkpoint_fixtures_and_unknown_successors_reject(self):
        if not checkpoint.AFTER:self.skipTest('First complete image not installed yet')
        original=Path.read_bytes;count=0
        for key in checkpoint.AFTER:
            current=(self.root/source.PATHS[key]).read_bytes();wrong=bytearray(current);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
            for stage in ('before','after'):
                target=self.root/install.BUILD/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed burst checkpoint fixture'):
                        checkpoint.previous_input(current,source.PATHS[key],self.root)
                count+=1
        self.receipt('checkpoint',positively_fired_controls=count,paths=sorted(checkpoint.AFTER))

    def test_11_owned_compiler_captures_explain_real_aggregate_homes(self):
        out=self.root/'conker/build/game-transition-burst-object-captures'
        records=[source.previous.capture(self.root,out,name,body) for name,body in
            (('before',source.previous.CANDIDATE),('selected',source.CANDIDATE))]
        rows=[]
        for record in records:
            procedure=source.previous.previous.procedure(record['records'])
            rows.append({length:sorted({r['offset'] for r in procedure if r['name']=='lda' and
                r['storage']=='M' and r['length']==length}) for length in (88,16)})
            self.assertTrue(record['code_unchanged']);self.assertTrue(record['complete']['code_unchanged'])
            self.assertEqual(record['frontend']['producer_exits'],[0]);self.assertEqual(record['optimizer']['producer_exits'],[0])
            self.assertEqual(source.previous.previous.homes(record)['automatic_bytes'],128)
        self.assertEqual(rows,[{88:[-88],16:[-104]},{88:[-92],16:[-108]}])
        for name in ('baseline.o','trace.o'):source.checked_parts(*source.parts(out/'capture-selected'/name))
        self.receipt('compiler-homes',automatic_bytes=128,before=rows[0],selected=rows[1],
            real_progress_declaration_precedes_complete_objects=True,not_original_source_order_uniqueness=True,
            fired_owned_probes_complete_cleaned_and_normal_candidate_inventories_unchanged=True)

    def test_12_real_scalar_placement_controls_and_wrong_home_rejection(self):
        before=(self.out/'before-tile_owner').read_text();matched=[]
        for label,line in (('transition','    TransitionPayloadFC5F0 *transition;\n'),
                ('child','    u8 *child;\n'),('flag1','    s32 flag1;\n')):
            body=source.previous.CANDIDATE
            self.assertEqual(body.count(line),1)
            body=body.replace(line,'').replace('    BurstDescriptorFC5F0 descriptor;',line+'    BurstDescriptorFC5F0 descriptor;',1)
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'placement-'+label)
            self.assertFalse(diag);source.checked_parts(*source.parts(obj));matched.append(label)
        wrong,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,source.previous.CANDIDATE),'wrong-homes')
        self.assertFalse(diag)
        with self.assertRaisesRegex(ValueError,'words/bindings'):source.checked_parts(*source.parts(wrong))
        data,functions=source.link_raw(self.root,self.out,wrong);f=functions[source.FUNCTION]
        words=list(struct.unpack_from('>251I',data,f['value']))
        with self.assertRaisesRegex(ValueError,'scratch relabeling'):source.normalize(words)
        with self.assertRaises(ValueError):source.padded_object(self.root,self.out,wrong,'wrong-homes',self.out/'candidate-guards.csv')
        self.receipt('placement',other_real_scalars_emit_identical_words_and_bindings=matched,
            wrong_home_raw_normalizer_and_actual_padder_reject=True,no_dummy_storage_or_SP_guard=True)


if __name__=='__main__':unittest.main()
