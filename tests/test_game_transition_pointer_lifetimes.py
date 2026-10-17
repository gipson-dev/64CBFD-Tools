"""Recovered real pointer/flag lifetimes are progress, not installation permission."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_transition_pointer_lifetimes as source
from tools.tests import game_transition_completion_oracle as model
from tools.tests import game_transition_frame_native as native
from tools.tests import test_game_transition_frame_lifetimes as frame_tests
from tools.tests import test_game_transition_completion_burst as caller_tests
from tools.tests import transition_child_motion_checkpoint as checkpoint


class PointerLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]; cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>251I',cls.rom,source.ROM))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_real_prefix_roles_branch_and_tail_but47_words_remain(self):
        self.assertEqual(self.images[0],self.images[1])
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differing_words']),(251,264,47))
        self.assertEqual((self.row['unchanged_raw_padded_neighbors'],self.row['new_guards']),(24,0))
        self.assertEqual(self.images[0][:47],self.truth[:47])
        self.assertEqual(self.images[0][210:],self.truth[210:])
        self.assertEqual(self.images[0][175:184],self.truth[175:184])
        self.assertEqual(len(self.row['pure_stack_shift_words']),36)
        self.assertEqual(len(self.row['scratch_role_words']),11)
        self.assertEqual(self.row['mixed_stack_and_scratch_word'],192)
        self.assertEqual((self.row['descriptor'],self.row['payload']),(0xB0,0xA0))
        with self.assertRaisesRegex(ValueError,'complete word/frame/private'): source.require_installable(self.row)
        self.receipt('boundary',raw_sha256=source.RAW_SHA,exact_prefix_words=47,exact_tail_words=41,
            parent_S4_payload_S3_transition_home_84=True,raw_words_still_different=47,
            not_object_or_scratch_or_private_or_installation_acceptance=True)

    def test_02_extended_guest_public_reference_with_actual_factory_copy_and_tags(self):
        with patch.object(frame_tests,'source',source):
            frame_tests.FrameLifetimeTests.test_02_extended_public_reference_real_factory_copy_and_tag_leaves(self)

    def test_03_native32_full_body_and_current_width_controls(self):
        original=native.controls
        def controls(body):
            forms=original(body)
            forms['word_gate']=(body.replace('transition->state & 1','*(u32 *)transition & 1'),0)
            if any(candidate==body for candidate,_ in forms.values()):
                raise ValueError('A pointer-lifetime native control is ineffective')
            return forms
        with patch.object(frame_tests,'source',source),patch.object(native,'controls',controls):
            frame_tests.FrameLifetimeTests.test_03_native32_full_body_separate_typed_caller_and_endian_limits(self)

    def test_04_owned_frontend_captures_keep_128_byte_region_and_nested_call_home(self):
        before=source.capture(self.root,self.out,'before',source.previous.CANDIDATE)
        after=source.capture(self.root,self.out,'selected')
        homes=[source.previous.homes(record) for record in (before,after)]
        self.assertEqual([h['automatic_bytes'] for h in homes],[128,128])
        self.assertEqual(homes[0]['vregs'],[('R',-128,4,1)])
        self.assertEqual(homes[0],homes[1])
        rows=source.previous.procedure(after['records'])
        loads=[i for i,r in enumerate(rows) if r['name']=='lod' and r['storage']=='M' and r['offset']==-128]
        self.assertEqual(len(loads),3)
        first=loads[0]
        self.assertTrue(any(r['name']=='cup' for r in rows[first-18:first]))
        self.assertTrue(any(r['name']=='par' for r in rows[first+1:first+8]))
        for record in (before,after):
            self.assertTrue(record['code_unchanged']); self.assertTrue(record['complete']['code_unchanged'])
            self.assertFalse(record['installable'])
            self.assertEqual(record['frontend']['producer_exits'],[0])
            self.assertEqual(record['optimizer']['producer_exits'],[0])
        self.receipt('compiler-homes',before=homes[0],selected=homes[1],
            nested_call_and_chained_assignment_reuse_one_anonymous_home=True,
            fired_owned_captures_complete_cleaned_up_and_normal_objects_unchanged=True,
            not_actual_retail_CFE_or_home_recovery=True)

    def test_05_every_current_input_and_frozen_fixture_corruption_fires(self):
        source.freeze(self.root,self.out); cache={}; real=hashlib.sha256
        for key,path in source.PATHS.items():
            current=self.root/path; frozen=self.out/('before-'+key)
            cache[current]=current.read_bytes(); cache[frozen]=frozen.read_bytes()
            normalized=checkpoint.previous_input(cache[current],path,self.root)
            self.assertEqual(real(normalized).hexdigest(),source.BASELINE[key])
            self.assertEqual(cache[frozen],normalized)
        from tools.experiments.game_transition_child_motion_installation import BUILD
        for key in checkpoint.AFTER:
            for stage in ('before','after'):
                path=self.root/BUILD/(stage+'-'+key); cache[path]=path.read_bytes()
        @lru_cache(None)
        def digest(data): return real(data)
        count=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Unknown burst input'),
                    (self.out/('before-'+key),'Changed burst fixture')):
                wrong=bytearray(cache[target]); wrong[len(wrong)//2]^=1; wrong=bytes(wrong)
                def read_bytes(path): return wrong if path==target else cache[path]
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda path:path in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message): source.freeze(self.root,self.out)
                count+=1
        source.freeze(self.root,self.out)
        self.assertEqual((len(source.PATHS),len(set(source.PATHS.values())),count),(195,179,390))
        self.receipt('inputs',entries=195,distinct_paths=179,positively_fired_live_and_fixture_controls=count,
            exact_existing_child_successors_only=True)

    def test_06_all_raw_word_and_binding_controls_fire(self):
        data,functions,relocs=source.parse_object(self.obj); f=functions[source.FUNCTION]
        raw=data[f['value']:f['value']+f['size']]
        bindings={a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']}
        source.checked_parts(raw,bindings)
        for i in range(251):
            wrong=bytearray(raw); wrong[i*4+3]^=1
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(wrong,bindings)
        for at in bindings:
            wrong=dict(bindings); wrong[at]=[(bindings[at][0][0],bindings[at][0][1]+'-wrong')]
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(raw,wrong)
        self.receipt('raw-corruption',fired_word_controls=251,fired_binding_controls=len(bindings),new_guards=0)

    def test_07_original_kind12_callback_window(self):
        with patch.object(caller_tests,'source',source):
            caller_tests.CompletionBurstTests.test_05_original_kind12_callback_window_and_success_return(self)

    def test_08_production_remains_the_committed_child_motion_baseline(self):
        for path,key in checkpoint.PATHS.items():
            data=(self.root/path).read_bytes()
            self.assertEqual(data,checkpoint.fixture(self.root,'after',key))
        self.assertIn('s32 func_150CF800() {\n    return 0;\n}',
            (self.root/source.PATHS['tile_owner']).read_text())
        self.receipt('production',no_source_image_manifest_data_profile_or_conversion_credit=True,
            private_rebase_fault_and_first_image_gates_still_open=True)


if __name__=='__main__': unittest.main()
