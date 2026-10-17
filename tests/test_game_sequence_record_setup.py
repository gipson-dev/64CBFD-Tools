"""Complete uninstalled setup candidate: public semantics, boundary packets and input scope."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_record_setup as source
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object
from tools.tests import game_sequence_record_setup_oracle as model
from tools.tests import test_game_view_list_setup as assembly


class SequenceRecordSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.raw,cls.row=source.measure(cls.root,cls.out,'qualified',source.SELECTED)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>473I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_complete_recovery_explicitly_not_installable_and_all56_neighbors(self):
        old,diagnostics=source.compile_owner(self.root,self.out,(self.out/'before-view_list_caller_owner').read_text(),'neighbor-before',True)
        self.assertEqual(same_functions(old,self.obj,(source.FUNCTION,)),56)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(471,168,405))
        self.assertEqual(self.row['raw_sha256'],'0449520a1d8dccf7146bd689a066643509537fc0d183fdcf6758c516b3ec6000')
        self.assertEqual(len(self.row['bindings']),89)
        self.assertEqual(hashlib.sha256(json.dumps(self.row['bindings'],sort_keys=True).encode()).hexdigest(),
            '1bf30d7917bda0cc768cc13c0c307f5c6bb42fe72c3dee9d84960877357eb74c')
        self.assertEqual(self.row['diagnostics'],'');self.assertFalse(self.row['pools']);self.assertEqual(diagnostics,'')
        self.assertEqual(self.raw[1:11],self.truth[1:11])
        self.assertEqual(len(model.Reference(*model.fixture()).run().allocations),11)
        self.receipt('boundary',candidate_words=471,retail_words=473,candidate_frame=168,retail_frame=120,
            word_differences=405,unchanged_raw_neighbors=56,no_guards_or_installation=True,
            no_matching_credit=True,complete_body_not_truncated_to_retail_slot=True)

    def test_02_full_original_and_actual_C_against_ordered_reference(self):
        count=0;visits=[set(),set()];fired=set();saw_large=False
        for memory,args,config in model.cases():
            ref=model.Reference(memory,args,config).run();saw_large|=any(size>=131070 for _,size,_ in ref.allocations)
            for phase in (0,8):
                for i,words in enumerate((self.truth,self.raw)):
                    m=model.SetupOracle(words,memory,args,config,ref.allocations,phase)
                    saved_fpr=m.f[20:];m.run()
                    self.assertEqual(model.public(m.memory),model.public(ref.memory),(args,config,phase,i))
                    self.assertEqual(m.calls,ref.calls);self.assertEqual(m.provider.snapshots,ref.snapshots)
                    self.assertEqual(m.provider.fired,ref.fired);visits[i].update(m.visits);fired.update(m.provider.fired)
                    for reg in (*range(16,24),28,29,30,31):self.assertEqual(m.r[reg],m.before[reg])
                    self.assertEqual(m.f[20:],saved_fpr)
                count+=1
        for seen,n in zip(visits,(473,471)):
            self.assertEqual(seen & set(range(source.ENTRY,source.ENTRY+n*4,4)),set(range(source.ENTRY,source.ENTRY+n*4,4)))
        self.assertTrue(saw_large)
        self.assertEqual(fired,{'cached-bundle-header','runtime-reload','wide-capacity','live-request-status','late-count','live-loop-count','empty-after-helper','hook-count'})
        self.receipt('guest',two_way_cases=count,all473_original_and471_C_words_visited=True,
            actual_packets_and_boundary_snapshots=True,positive_mutation_gates=sorted(fired),
            unsigned_word_sizes_half_counts_and_low16_sum=True,large_capacity_memory_fully_bounded=True,
            saved_GPR_FPR_SP_ABI=True,opaque_providers_not_gameplay_acceptance=True)

    def test_03_original473_word_artifact_and_every_frozen_input_fails_closed(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-setup',
            (self.out/'before-view_list_caller_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(self.root,self.out,original,source.OWNER);f=functions[source.FUNCTION]
        self.assertEqual(data[f['value']:f['value']+f['size']],self.rom[source.ROM:source.ROM+1892]);self.assertEqual(f['size'],1892)
        read=Path.read_bytes
        for key,relative in source.PATHS.items():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        for key,relative in source.PATHS.items():self.assertEqual(hashlib.sha256(read(self.root/relative)).hexdigest(),source.BASELINE[key])
        self.receipt('inputs',unchanged_inputs=len(source.PATHS),unknown_input_corruptions=len(source.PATHS),
            complete_original473_independently_assembled=True,production_owner_guards_ELF_and_progress_unchanged=True)

    def test_04_bounded_source_screens_do_not_resolve_the_frame_or_promote(self):
        rows=[]
        for label,body in [*source.offset_forms(),*source.runtime_forms(),*source.total_forms()]:
            _,words,row=source.measure(self.root,self.out,label,body)
            self.assertEqual(row['frame'],168);self.assertEqual(row['diagnostics'],'');self.assertFalse(row['pools'])
            for fixture in (model.fixture(),model.fixture(mode=63)):
                ref=model.Reference(*fixture).run();m=model.SetupOracle(words,*fixture,ref.allocations).run()
                self.assertEqual(model.public(m.memory),model.public(ref.memory));self.assertEqual(m.calls,ref.calls)
                self.assertEqual(m.provider.snapshots,ref.snapshots)
            rows.append({k:row[k] for k in ('label','words','frame','differences','raw_sha256')})
        self.assertEqual(len(rows),5);self.assertEqual(source.SELECTED,source.INITIAL)
        self.receipt('source-screens',rows=rows,selected_unchanged=True,
            two_guest_witnesses_each_not_full_qualification_of_alternatives=True,matching_frame_not_recovered=True)


if __name__=='__main__':unittest.main()
