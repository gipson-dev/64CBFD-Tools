"""Private whole-scanner qualification without installing or crediting a match."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import game_texture_vertex_span_oracle as model
from tools.tests import game_texture_vertex_span_native as native
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object

SELECTED='explicit-shared-end'


class TextureVertexSpanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)
        cls.before=(cls.out/'before-owner').read_text()
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>339I',cls.rom,source.ROM))
        cls.body=dict(source.variants())[SELECTED]
        cls.obj,cls.diagnostics=build.compile_owner(cls.root,cls.out,source.recover(cls.before,cls.body),'qualified')
        data,functions=build.link_owner(cls.root,cls.out,cls.obj,source.OWNER)
        cls.info=functions[source.FUNCTION]
        cls.words=list(struct.unpack_from('>%dI'%(cls.info['size']//4),data,cls.info['value']))
        cls.rows=list(model.cases())

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_shape_screens_and_explicit_nonmatch_boundary(self):
        self.assertEqual((self.info['size'],self.words[0],self.diagnostics),(1356,0x27BDFF58,''))
        self.assertEqual(sum(a!=b for a,b in zip(self.words,self.retail)),259)
        screens=json.loads((self.out/'screens.json').read_text())
        self.assertEqual(len(screens),23)
        self.assertEqual(next(r for r in screens if r['label']==SELECTED)['differences'],259)
        self.assertEqual(self.words[:11],self.retail[:11])
        self.assertEqual((self.words[11],self.retail[11]),(0x27A500A4,0x27A500A0))
        self.assertNotEqual(self.words,self.retail)
        self.receipt('shape',screens=len(screens),words=339,frame=168,raw_word_differences=259,
            private_extent_home=[164,160],saved_registers_match=True,installed=False,new_match_credit=False)

    def test_02_raw_neighbors_pools_and_both_padders(self):
        old,diagnostics=build.compile_owner(self.root,self.out,self.before,'before')
        a,af,ar=parse_object(old)
        b,bf,br=parse_object(self.obj)
        self.assertEqual(set(af),set(bf))
        relative=lambda rows,info:{at-info['value']:v for at,v in rows.items() if info['value']<=at<info['value']+info['size']}
        for name in set(bf)-{source.FUNCTION}:
            x,y=af[name],bf[name]
            self.assertEqual(x['size'],y['size'],name)
            self.assertEqual(a[x['value']:x['value']+x['size']],b[y['value']:y['value']+y['size']],name)
            self.assertEqual(relative(ar,x),relative(br,y),name)
        self.assertEqual((diagnostics,normalized_pools(old)),('',normalized_pools(self.obj)))
        assemblies=(pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,
            word_patches_path=self.root/source.PATHS['guards']),
            emit_padded_assembly(self.obj,self.root/source.PATHS['original'],filename=source.OWNER,
                word_patches_path=self.root/source.PATHS['guards']))
        for label,text in zip(('primary','generated'),assemblies):
            path=self.out/(label+'.s')
            path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+text)
            obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
            at=functions[source.FUNCTION]['value']
            self.assertEqual(data[at:at+1356],struct.pack('>339I',*self.words))
            self.assertNotEqual(data[at:at+1356],struct.pack('>339I',*self.retail))
        self.receipt('neighbors',raw_neighbors=len(bf)-1,pools_and_relative_relocations_fixed=True,
            both_padders_preserve_candidate_nonmatch=True,no_new_guards=True)

    def test_03_guest_complete_scanner_provider_effects_and_boundaries(self):
        seen=set()
        cases=0
        for row in self.rows:
            expected,result,_=model.reference(row['memory'],row['args'],row['mode'])
            for phase in (0,8):
                for words in (self.retail,self.words):
                    instance=model.SpanOracle(words,row['memory'],row['args'],row['mode'],phase).run()
                    self.assertEqual((model.external_memory(instance.memory),instance.r[2]),
                        (model.external_memory(expected),result))
                    self.assertEqual(len(instance.calls),1)
                    if words is self.retail:
                        seen.update(instance.visits)
                cases+=1
        self.assertGreaterEqual(len(seen),330)
        missing=sorted(set(range(source.ENTRY,source.ENTRY+1356,4))-seen)
        self.receipt('guest',cases=cases,retail_reached_words=len(seen),unreached=[hex(x) for x in missing],
            both_stack_phases=True,ordered_scan_backtrack_and_nested_textures=True,
            signed_end_opcodes_unsigned_vertex_addresses_and_all_packed_fields=True,
            original_and_raw_public_storage_result_and_provider_packet_agree=True,
            resource_provider_bounded_not_actual_loading=True,not_full_private_or_fault_equivalence=True)

    def test_04_native32_explicit_endian_bridge_and_backing_storage(self):
        self.assertEqual(native.run(self.out,'selected',self.rows,self.body),[0,0])
        receipt=json.loads((self.out/'native-selected.json').read_text())
        self.assertIn('vertexBase',receipt['diagnostics'][0])
        self.receipt('native',cases_per_profile=len(self.rows),profiles=['O2','O0'],
            actual_body_with_three_explicit_big_endian_opcode_bridges=True,
            all_148_backing_words_provider_packet_and_canaries=True,
            known_maybe_uninitialized_diagnostic_retained=True,
            defined_vertex_base_domain_only=True,no_native_private_frame_fault_or_hardware_claim=True)

    def test_05_effective_compiled_guest_and_native_semantic_controls(self):
        witnesses=[]
        for label,body in source.negatives(self.body).items():
            self.assertNotEqual(body,self.body)
            obj,diagnostics=build.compile_owner(self.root,self.out,source.recover(self.before,body),'negative-'+label)
            data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
            info=functions[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            self.assertEqual(diagnostics,'')
            witness=None
            for index,row in enumerate(self.rows):
                expected,result,_=model.reference(row['memory'],row['args'],row['mode'])
                instance=model.SpanOracle(words,row['memory'],row['args'],row['mode']).run()
                if (model.external_memory(instance.memory),instance.r[2])!=(model.external_memory(expected),result):
                    witness=row
                    break
            self.assertIsNotNone(witness,label)
            statuses=native.run(self.out,label,[witness],body)
            self.assertEqual(statuses,[2,2],(label,statuses))
            witnesses.append(dict(label=label,case=index,guest_returned=True,native_status=statuses))
        self.receipt('controls',effective_controls=witnesses,crashes_not_used_as_witnesses=True)

    def test_06_private_state_and_fired_prefixes_remain_unmatched(self):
        row=next(r for r in self.rows if len(model.reference(r['memory'],r['args'],r['mode'])[2])>4)
        instances=[model.SpanOracle(w,row['memory'],row['args'],row['mode']).run() for w in (self.retail,self.words)]
        self.assertNotEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))
        mismatches=[]
        count=min(64,*(x.root_accesses for x in instances))
        for cut in range(count):
            prefixes=[]
            for words in (self.retail,self.words):
                instance=model.SpanOracle(words,row['memory'],row['args'],row['mode'],fault=cut)
                with self.assertRaises(faults.AccessBoundary):
                    instance.run()
                self.assertEqual(instance.root_accesses,cut)
                prefixes.append(instance)
            if machine.complete_state(prefixes[0])!=machine.complete_state(prefixes[1]):
                mismatches.append(dict(cut=cut,PC=[x.current_pc for x in prefixes],delay=[x.delay_of for x in prefixes]))
        self.assertTrue(mismatches)
        self.receipt('private-boundary',fired_prefix_pairs=count,nonmatching_pairs=len(mismatches),first=mismatches[0],
            full_return_state_mismatch=True,no_private_schedule_guards_or_installation=True)

    def test_07_immutable_production_archive_and_original_caller_boundary(self):
        source.freeze(self.root,self.out)
        rb=Path.read_bytes
        for key,path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),source.BASELINE[key],key)
            frozen=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==frozen else rb(p)):
                with self.assertRaisesRegex(ValueError,'immutable texture vertex span input'):
                    source.freeze(self.root,self.out)
        archive=self.root/'../Another Source/CBFD-Recompiled/conker/conker/src/game_138520.c'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),'4c7932efd534f588ea02099b9ac32657de498be6cef55bc35d3f3b08bc0754d2')
        self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_138520/func_1510BF60.s")',archive.read_text())
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x139A0C),(0x0D442FD8,0x8C840E00))
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x139BB0),(0x0D442FD8,0xAFA80030))
        self.assertIn('s32 func_1510C4AC() {\n    return 0;',self.before)
        exists=Path.exists
        manifest=self.out/'baseline.json'
        with patch.object(Path,'exists',lambda p:False if p==manifest else exists(p)):
            with self.assertRaisesRegex(ValueError,'Changed texture vertex span baseline'):
                with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==self.root/source.PATHS['owner'] else rb(p)):
                    source.freeze(self.root,self.out)
        self.receipt('ownership',all_production_inputs=len(source.PATHS),unchanged=True,archive_not_a_C_donor=True,
            two_original_direct_calls=True,actual_caller_still_stub=True,full_source_goal_open=True)

    def test_08_unreachable_duplicate_loads_and_undefined_base_boundary(self):
        dead=(0x1510C044,0x1510C098,0x1510C210)
        destinations=set()
        for i,word in enumerate(self.retail):
            op=word>>26
            if op in (1,4,5,6,7,20,21,22,23):
                immediate=word&65535
                destinations.add(source.ENTRY+i*4+4+(immediate if immediate<32768 else immediate-65536)*4)
        for address in dead:
            self.assertNotIn(address,destinations)
            self.assertEqual(self.retail[(address-source.ENTRY)//4-2]>>16,0x1000)
        receipt=json.loads((self.out/'guest.json').read_text())
        self.assertEqual(receipt['unreached'],[hex(x) for x in dead])
        self.assertEqual(receipt['retail_reached_words'],336)
        row=model.fixture([(0xFD000000,model.TEXTURE),(0x01000000,model.VERTICES),(0xDF000000,0)])
        with self.assertRaisesRegex(ValueError,'No defined vertex base'):
            model.reference(row['memory'],row['args'])
        values=[]
        for phase in (0,8):
            instance=model.SpanOracle(self.retail,row['memory'],row['args'],phase=phase).run()
            values.append(instance.r[2])
        self.assertNotEqual(values[0],values[1])
        self.receipt('domain',retail_unreachable_duplicate_words=[hex(x) for x in dead],
            no_direct_branch_entry_and_preceding_unconditional_branch=True,
            undefined_vertex_base_original_returns=values,not_portable_C_input=True,
            native_warning_not_suppressed_or_production_repaired=True)

    def test_09_external_output_aliases_and_resource_slots(self):
        rows=[]
        commands=[(0,0),(0x01000000,model.VERTICES),(0xFD000000,model.TEXTURE),
            model.triangle(6,[1,5,3,2,7,4]),(0xDF000000,0)]
        for resource in range(8):
            for output in (model.CACHE+resource*4,model.COMMANDS+4,model.COMMANDS+12):
                row=model.fixture(commands,resource=resource,output=output)
                expected,result,_=model.reference(row['memory'],row['args'])
                for phase in (0,8):
                    for words in (self.retail,self.words):
                        instance=model.SpanOracle(words,row['memory'],row['args'],phase=phase).run()
                        self.assertEqual((model.external_memory(instance.memory),instance.r[2]),
                            (model.external_memory(expected),result))
                rows.append(row)
        self.assertEqual(native.run(self.out,'external-aliases',rows,self.body),[0,0])
        self.receipt('aliases',guest_cases=len(rows)*2,native_cases_per_profile=len(rows),
            output_aliases_cache_and_display_list_payloads=True,resource_slots=8,
            no_private_stack_alias_or_production_claim=True)


if __name__=='__main__':
    unittest.main()
