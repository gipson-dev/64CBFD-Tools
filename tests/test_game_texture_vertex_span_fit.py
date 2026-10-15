"""Qualify recovered real homes without installing the unmatched scanner."""
from pathlib import Path
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import test_game_texture_vertex_span as prior
from tools.tests import game_texture_vertex_span_oracle as model
from tools.pad_generated_object import parse_object


class TextureVertexSpanFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/fit.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root,cls.root/source.BUILD)
        cls.before=(cls.root/source.BUILD/'before-owner').read_text()
        cls.body=fit.HOMES
        cls.meta,cls.words,cls.obj=fit.measure(cls.root,cls.out,'qualified-homes',cls.body)
        cls.info={'size':cls.meta['bytes']}
        cls.diagnostics=cls.meta['diagnostics']
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>339I',cls.rom,source.ROM))
        cls.rows=list(model.cases())

    receipt=prior.TextureVertexSpanTests.receipt

    def test_01_actual_homes_not_extra_arrays_or_match_credit(self):
        self.assertEqual((self.meta['bytes'],self.meta['frame'],self.meta['differences'],
            self.diagnostics,self.meta['extent_home']),(1356,168,258,'',160))
        self.assertEqual(self.words[:12],self.retail[:12])
        self.assertEqual(self.meta['stack_stores'],[20,24,28,32,36,*range(88,136,4),148,172])
        call='    func_1510D0EC(resource, &extent, 3, 0);'
        self.assertEqual(self.body.split(call,1)[1],fit.SEED.split(call,1)[1])
        self.assertEqual(self.body.count('indices[12]'),1)
        self.assertNotEqual(self.words,self.retail)
        self.receipt('homes',words=339,frame=168,differences=258,extent=160,indices=88,vertexBase=148,
            only_existing_local_declarations_reordered=True,first_12_words_exact=True,
            installed=False,new_match_credit=False)

    test_02_neighbors_and_both_padders=prior.TextureVertexSpanTests.test_02_raw_neighbors_pools_and_both_padders
    test_03_guest_public_and_reachable_words=prior.TextureVertexSpanTests.test_03_guest_complete_scanner_provider_effects_and_boundaries
    test_04_native_public_and_diagnostic_boundary=prior.TextureVertexSpanTests.test_04_native32_explicit_endian_bridge_and_backing_storage
    test_05_seven_effective_semantic_controls=prior.TextureVertexSpanTests.test_05_effective_compiled_guest_and_native_semantic_controls
    test_06_private_state_and_fired_prefixes=prior.TextureVertexSpanTests.test_06_private_state_and_fired_prefixes_remain_unmatched
    test_08_unreachable_and_undefined_base_boundary=prior.TextureVertexSpanTests.test_08_unreachable_duplicate_loads_and_undefined_base_boundary
    test_09_external_aliases=prior.TextureVertexSpanTests.test_09_external_output_aliases_and_resource_slots

    def test_07_frozen_inputs_and_production_are_unchanged(self):
        frozen=self.root/source.BUILD
        source.freeze(self.root,frozen)
        rb=Path.read_bytes
        for key,relative in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root/relative).read_bytes()).hexdigest(),source.BASELINE[key],key)
            path=frozen/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'immutable texture vertex span input'):
                    source.freeze(self.root,frozen)
        self.receipt('production',inputs=len(source.PATHS),all_current_and_before_hashes_fixed=True)

    def test_10_private_home_aliases_improve_against_the_previous_source(self):
        old,diagnostics=build.compile_owner(self.root,self.out,source.recover(self.before,fit.SEED),'old-homes')
        data,functions=build.link_owner(self.root,self.out,old,source.OWNER)
        info=functions[source.FUNCTION]
        old_words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        self.assertEqual(diagnostics,'')
        cases=0
        for kind in (5,6,16):
            for phase in (0,8):
                for home in (0x58,0x94,0xA0):
                    output=model.machine.STACK+phase-0xA8+home
                    row=model.fixture([(0,0),(0x01000000,model.VERTICES),(0xFD000000,model.TEXTURE),
                        model.triangle(kind,[1,5,3]),(0xDF000000,0)],output=output)
                    results=[]
                    for words in (self.retail,self.words,old_words):
                        instance=model.SpanOracle(words,row['memory'],row['args'],phase=phase).run()
                        results.append((instance.r[2],model.read(instance.memory,output),
                            model.external_memory(instance.memory)))
                    self.assertEqual(results[0],results[1])
                    self.assertNotEqual(results[0],results[2])
                    cases+=1
        self.receipt('private-aliases',cases=cases,old_source_mismatches=cases,new_source_agrees=cases,
            guest_only_not_portable_C_or_full_private_state=True)

    def test_11_compiled_screens_and_advisory_proposals_are_measured(self):
        filenames=('screens.json','homes-screens.json','return-screens.json',
            'control-screens.json','exit-screens.json','advisory-screens.json')
        groups=(fit.variants,fit.home_variants,fit.return_variants,fit.control_variants,fit.exit_variants,fit.advisory_variants)
        inputs={filename:(self.out/filename).read_bytes() for filename in filenames}
        counts=[]
        for filename,forms in zip(filenames,groups):
            rows=json.loads((self.out/filename).read_text())
            self.assertEqual([r['label'] for r in rows],[label for label,_ in forms()])
            self.assertTrue(all(r['diagnostics']=='' and r['differences']>0 for r in rows))
            counts.append(len(rows))
        baseline,functions,relocations=parse_object(self.obj)
        info=functions[source.FUNCTION]
        literal=baseline[info['value']:info['value']+info['size']]
        capture_changes=[(0x14C,0x8E230000,0x8E250000),(0x168,0x8E230000,0x8E250000),
            (0x180,0x8E230000,0x8E220000),(0x188,0x10600003,0x10400003),
            (0x18C,0x01C3082B,0x01C2082B),(0x514,0x8FB80094,0x8FAF0094),
            (0x518,0x24EE0001,0x24F80001),(0x51C,0x000E7900,0x00187100),
            (0x520,0x030FC821,0x01CFC821),(0x524,0x03231023,0x03251023),
            (0x528,0x00027103,0x0002C103),(0x52C,0x01C01025,0x03001025)]
        for label,_ in fit.advisory_variants():
            data,fs,rs=parse_object(self.out/(label+'.o'))
            current=fs[source.FUNCTION]
            body=data[current['value']:current['value']+current['size']]
            self.assertEqual(len(body),len(literal))
            changes=[(i*4,a[0],b[0]) for i,(a,b) in enumerate(zip(struct.iter_unpack('>I',literal),
                struct.iter_unpack('>I',body))) if a!=b]
            self.assertEqual(changes,capture_changes if label.endswith('-capture-first') else [],label)
            relative=lambda r,f:{at-f['value']:v for at,v in r.items() if f['value']<=at<f['value']+f['size']}
            self.assertEqual(relative(rs,current),relative(relocations,info),label)
        self.receipt('screen-summary',groups=counts,total=sum(counts),advisory_controls=7,
            constant_forms_identical=3,capture_forms=4,capture_GPR_words_changed=12,
            all_other_bytes_and_relative_relocations_fixed=True,no_exact_form=True)
        for filename,data in inputs.items():
            self.assertEqual((self.out/filename).read_bytes(),data,'Screen input overwritten: '+filename)


if __name__=='__main__':
    unittest.main()
