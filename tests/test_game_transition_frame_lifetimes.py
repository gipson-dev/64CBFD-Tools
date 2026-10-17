"""Same retail frame is progress, not a certificate for the remaining 91 words."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_transition_frame_lifetimes as source
from tools.tests import game_transition_completion_oracle as model
from tools.tests import game_transition_frame_native as native
from tools.tests import test_game_transition_completion_burst as prior_tests
from tools.tests.test_game_projected_packet_draw import native_command


def cases():
    yield from model.cases()
    for seed,flags,progress,timestep,pattern,mode,phase in itertools.product(
            (0x80000000,0xFFFFFFFF),(1,255),(0.9,1.),(-1.,1.),range(3),range(4),(0,8)):
        yield model.fixture(flags,progress,timestep,seed),seed,pattern,mode,phase


class FrameLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]; cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>251I',cls.rom,source.ROM))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_correct_frame_count_pool_neighbors_but91_word_gap(self):
        self.assertEqual(self.images[0],self.images[1])
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differing_words']),(251,264,91))
        self.assertEqual(self.row['raw_sha256'],source.RAW_SHA)
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],24)
        self.assertEqual(self.row['new_guards'],0)
        with self.assertRaisesRegex(ValueError,'complete word/frame/private'):
            source.previous.require_installable(self.row)

    def test_02_extended_public_reference_real_factory_copy_and_tag_leaves(self):
        count=0; visited=set()
        for memory,seed,pattern,mode,phase in cases():
            expected,calls,children=model.reference(memory,seed,pattern,mode)
            for words in (self.truth,*self.images):
                m=model.CompletionOracle(words,memory,self.rom,seed,pattern,mode,phase).run()
                self.assertEqual(model.public(m.memory,pattern,mode,children),expected,(seed,pattern,mode,phase))
                self.assertEqual(m.calls,calls)
                self.assertEqual(m.r[2],1)
                if words is self.truth: visited.update(m.visits)
            count+=1
        self.assertEqual({pc-source.ENTRY for pc in visited if source.ENTRY<=pc<source.ENTRY+source.SIZE},
            set(range(0,1004,4))-{540,600})
        self.receipt('public-guest',three_way_cases=count,natural_retail_words=249,
            high_bit_unsigned_RNG=True,actual_factory_words=54,actual_copy_words=11,actual_tag_leaves=2,
            public_bytes_calls_and_live_padding=True,not_private_stack_or_real_heap_or_hardware_acceptance=True)

    def test_03_native32_full_body_separate_typed_caller_and_endian_limits(self):
        caller,driver=self.out/'native-caller.c',self.out/'native-driver.c'
        caller.write_text(native.CALLER); driver.write_text(native.DRIVER)
        forms=[('o2','-O2',source.CANDIDATE,0),('o0','-O0',source.CANDIDATE,0)]
        forms += [(name,'-O2',body,code) for name,(body,code) in native.controls(source.CANDIDATE).items()]
        exits={}
        for name,opt,body,wanted in forms:
            path=self.out/('native-'+name+'.c'); path.write_text(native.HEADER+body+'\n'); exe=path.with_suffix('.elf')
            command=[*native_command(opt),'-g','-mstackrealign','-malign-double',
                *[str(p.relative_to(self.root)) for p in (path,caller,driver)],'-o',str(exe.relative_to(self.root))]
            compiled=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
            self.assertEqual(ran.returncode,wanted,(name,ran.stderr)); exits[name]=ran.returncode
        # These two wrong N64 reads pass the little-endian fields checks. Prove
        # their actual emitted big-endian code still fails the independent guest.
        rejected=[]; memory=model.fixture(1,1.,1.,0); expected,calls,children=model.reference(memory)
        for name in ('word_gate','word_slot'):
            body,_=native.controls(source.CANDIDATE)[name]
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(
                (self.out/'before-tile_owner').read_text(),body),'endian-'+name)
            self.assertFalse(diag)
            data,functions=source.link_raw(self.root,self.out,obj); f=functions[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            m=model.CompletionOracle(words,memory,self.rom).run()
            self.assertTrue(m.calls!=calls or model.public(m.memory,1,0,children)!=expected)
            rejected.append(name)
        self.receipt('native',cases_each=1728,exits=exits,UBSan=True,separate_full_body_and_typed_caller=True,
            initialized_descriptor_payload_bytes=98,six_descriptor_padding_bytes_excluded=True,
            all_parent_output_and_outer_canaries=True,wrong_width_controls_pass_native_but_fail_guest=rejected,
            not_N64_byte_order_private_padding_or_hardware_acceptance=True)

    def test_04_fingerprint_locked_captures_explain_144_to128_frontend_homes(self):
        captures={name:source.capture(self.root,self.out,name,body) for name,body in
            (('before',source.previous.CANDIDATE),('selected',source.CANDIDATE))}
        before,after=(source.homes(captures[name]) for name in ('before','selected'))
        self.assertEqual((before['automatic_bytes'],after['automatic_bytes']),(144,128))
        self.assertEqual(before['vregs'],[('R',-144,4,1)])
        self.assertEqual(after['vregs'],[('R',-128,4,1)])
        for name,record in captures.items():
            self.assertTrue(record['code_unchanged'])
            self.assertTrue(record['complete']['code_unchanged'])
            self.assertFalse(record['complete']['installable'])
            self.assertEqual(record['frontend']['producer_exits'],[0])
            self.assertEqual(record['optimizer']['producer_exits'],[0])
        self.receipt('compiler-homes',before=before,selected=after,
            whole_normal_object_words_functions_bindings_pools_unchanged_by_capture=True,
            owned_fired_probes_completed_and_removed=True,not_suppressed_real_timing_or_match_proof=True)

    def test_05_original_callback_window_remains_qualified(self):
        with patch.object(prior_tests,'source',source):
            prior_tests.CompletionBurstTests.test_05_original_kind12_callback_window_and_success_return(self)

    def test_06_every_live_and_frozen_input_gate_fires(self):
        real=hashlib.sha256
        @lru_cache(None)
        def digest(data): return real(data)
        cache={}
        for key,path in source.PATHS.items():
            current=self.root/path; frozen=self.out/('before-'+key)
            data=current.read_bytes()
            self.assertEqual(real(data).hexdigest(),source.BASELINE[key]); self.assertEqual(frozen.read_bytes(),data)
            cache[current]=cache[frozen]=data
        controls=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Unknown burst input'),
                    (self.out/('before-'+key),'Changed burst fixture')):
                wrong=bytearray(cache[target]); wrong[len(wrong)//2]^=1; wrong=bytes(wrong)
                def read_bytes(path): return wrong if path==target else cache[path]
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda path:path in cache),\
                        patch.object(source.previous.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message): source.freeze(self.root,self.out)
                controls+=1
        source.freeze(self.root,self.out)
        self.receipt('protected-inputs',entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            fired_live_and_fixture_controls=controls,production_source_ELF_data_profiles_guards_progress_unchanged=True,
            private_relocation_fault_and_installation_gates_open=True)

    def test_07_every_raw_word_and_binding_guard_fires(self):
        data,functions,relocs=source.previous.parse_object(self.obj); f=functions[source.FUNCTION]
        raw=data[f['value']:f['value']+f['size']]
        bindings={a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']}
        source.checked_parts(raw,bindings)
        for i in range(251):
            wrong=bytearray(raw); wrong[i*4+3]^=1
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(wrong,bindings)
        for at in bindings:
            wrong=dict(bindings); wrong[at]=[(bindings[at][0][0],bindings[at][0][1]+'-wrong')]
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(raw,wrong)
        self.receipt('raw-corruption',fired_word_controls=251,fired_binding_controls=len(bindings),new_instruction_patches=0)


if __name__=='__main__':
    unittest.main()
