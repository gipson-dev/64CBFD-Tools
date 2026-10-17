"""Keep the complete completion-burst candidate reproducible and uninstalled."""
import hashlib
from functools import lru_cache
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_transition_completion_burst as source
from tools.tests import game_transition_completion_oracle as model


class CompletionBurstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]; cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>251I',cls.rom,source.ROM))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_count_pool_24_neighbors_but93_differences_and_larger_frame(self):
        self.assertEqual(self.images[0],self.images[1])
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differing_words']), (251,280,93))
        self.assertEqual(self.row['raw_sha256'],'7078b69bf81d2546d26b134ae2a7e48cf1763e36b53029102e13469467ed7940')
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],24)
        self.assertEqual(self.row['new_guards'],0)
        self.assertEqual(source.projection.sections(self.obj)['.rodata'][1],source.POOL_BYTES+bytes(8))
        self.assertEqual(self.rom[0x245320:0x245338],source.POOL_BYTES)
        with self.assertRaisesRegex(ValueError,'complete word/frame/private'):
            source.require_installable(self.row)
        with self.assertRaisesRegex(ValueError,'No installation path'):
            source.require_installable(dict(self.row,installable=True,differing_words=0,frame=264))

    def test_02_public_reference_real_factory_copies_tag_and_scripted_effects(self):
        count=0; visited=set(); lengths=set(); child_counts=set()
        for memory,seed,pattern,mode,phase in model.cases():
            expected,calls,children=model.reference(memory,seed,pattern,mode)
            for words in (self.truth,*self.images):
                m=model.CompletionOracle(words,memory,self.rom,seed,pattern,mode,phase).run()
                self.assertEqual(model.public(m.memory,pattern,mode,children),expected,(seed,pattern,mode,phase))
                self.assertEqual(m.calls,calls,(seed,pattern,mode,phase))
                self.assertEqual(m.r[2],1)
                if words is self.truth: visited.update(m.visits)
                lengths.update(c[1] for c in m.calls if c[0]=='copy')
            child_counts.add(children); count+=1
        self.assertEqual(child_counts,{0,2,3,4,5}); self.assertEqual(lengths,{16,88})
        self.assertTrue(set(range(source.TAG,source.TAG+12,4)) <= visited)
        self.assertTrue(set(range(source.MEMCPY,source.MEMCPY+44,4)) <= visited)
        self.receipt('public-guest',three_way_cases=count,child_counts=sorted(child_counts),
            actual_factory_words=54,actual_copy_words=11,actual_tag_leaves=2,
            visited_retail_offsets=[i*4 for i in range(251) if source.ENTRY+i*4 in visited],
            public_bytes_and_calls=True,helper_clobbers=True,mutable_parent_and_tag=True,
            inherited_descriptor_bytes_excluded=6,live_padding_mode_compared=True,
            not_private_stack_or_native_or_real_heap_or_hardware_acceptance=True)

    def test_03_four_effective_source_controls_do_not_pass_public_reference(self):
        forms={
            'word-gate':source.CANDIDATE.replace('record[0x70] & 1','*(u32 *)(record + 0x70) & 1'),
            'word-slot':source.CANDIDATE.replace('16, record[0xC], record[1]','16, *(u32 *)(record + 0xC), record[1]'),
            'child-count':source.CANDIDATE.replace('(func_150ADA20() & 3) + 2','(func_150ADA20() & 3) + 1'),
            'short-payload':source.CANDIDATE.replace('child + 0x70, &payload, 16','child + 0x70, &payload, 15'),
        }
        memory=model.fixture(1,1.,1.,0); expected,calls,children=model.reference(memory)
        rejected=[]
        for name,body in forms.items():
            self.assertNotEqual(body,source.CANDIDATE)
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(
                (self.out/'before-tile_owner').read_text(),body),'control-'+name)
            self.assertFalse(diag)
            data,functions=source.link_raw(self.root,self.out,obj); f=functions[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            m=model.CompletionOracle(words,memory,self.rom).run()
            self.assertTrue(m.calls!=calls or model.public(m.memory,1,0,children)!=expected,name)
            rejected.append(name)
        self.receipt('effective-controls',rejected=rejected,full_source_controls=True)

    def test_04_all_live_inputs_and_frozen_fixtures_remain_pinned(self):
        controls=0; cached={}
        real_digest=hashlib.sha256
        @lru_cache(None)
        def digest(data): return real_digest(data)
        for key,path in source.PATHS.items():
            data=(self.root/path).read_bytes()
            frozen=self.out/('before-'+key)
            self.assertEqual(real_digest(data).hexdigest(),source.BASELINE[key])
            self.assertEqual(frozen.read_bytes(),data)
            cached[self.root/path]=cached[frozen]=data
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Unknown burst input'),
                    (self.out/('before-'+key),'Changed burst fixture')):
                corrupted=bytearray(cached[target]); corrupted[len(corrupted)//2]^=1
                wrong=bytes(corrupted)
                def read_bytes(path): return wrong if path==target else cached[path]
                # Cache only unchanged bytes, not the injected artifact or live reads afterwards.
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda path:path in cached),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message): source.freeze(self.root,self.out)
                controls+=1
        source.freeze(self.root,self.out)
        self.assertIn('s32 func_150CF800() {\n    return 0;\n}',(self.root/source.PATHS['tile_owner']).read_text())
        self.receipt('protected-inputs',entries=len(source.PATHS),fired_live_and_fixture_controls=controls,
            distinct_paths=len(set(source.PATHS.values())),
            full_source_ELF_guards_makefiles_data_profiles_and_progress_unchanged=True,
            future_native_relocation_fault_private_and_first_image_gates_open=True)

    def test_05_original_kind12_callback_window_and_success_return(self):
        entry,join=0x15154CE8,0x15154D14
        caller=list(struct.unpack_from('>11I',self.rom,0x182198))
        self.assertEqual(caller,[0x3C198009,0x032BC821,0x8F39ACC8,0xAFA40020,0xA3A5001B,
            0x0320F809,0,0x8FA40020,0x14400002,0x83A5001B,0x24050001])
        count=0
        for flags,progress,seed,pattern,mode,phase in itertools.product((0,1),(0.,1.),range(4),(0,2),(0,1),(0,8)):
            memory=model.fixture(flags,progress,1.,seed)
            model.put(memory,0x8008ACF8,source.ENTRY)
            model.put(memory,model.STACK+phase+0x20,model.RECORD)
            model.put(memory,model.STACK+phase+0x1B,0,1)
            expected,calls,children=model.reference(memory,seed,pattern,mode)
            for words in (self.truth,*self.images):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words))
                connected[join]=0xFFFFFFFF
                m=model.CompletionOracle(caller,memory,self.rom,seed,pattern,mode,phase,entry,connected)
                m.r[11]=48; m.r[5]=0
                with self.assertRaises(model.CallerJoin): m.run()
                self.assertEqual((m.current_pc,m.forwarded,m.r[2],m.r[4],m.r[5]),
                    (join,model.RECORD,1,model.RECORD,0))
                self.assertEqual(m.calls,calls)
                self.assertEqual(model.public(m.memory,pattern,mode,children),expected)
            count+=1
        self.receipt('caller-window',three_way_cases=count,actual_words=11,kind=12,
            pointer_restored_after_call=True,success_return_consumed=True,not_full_dispatcher_acceptance=True)

    def test_06_every_candidate_word_and_binding_corruption_fires(self):
        raw,functions,relocations=source.parse_object(self.obj); f=functions[source.FUNCTION]
        body=raw[f['value']:f['value']+f['size']]
        bindings={a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']}
        source.checked_parts(body,bindings)
        for i in range(source.WORDS):
            changed=bytearray(body); changed[i*4+3]^=1
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(changed,bindings)
        for at in bindings:
            changed=dict(bindings); changed[at]=[(bindings[at][0][0],bindings[at][0][1]+'-wrong')]
            with self.assertRaisesRegex(ValueError,'words/bindings'): source.checked_parts(body,changed)
        self.receipt('raw-corruption',fired_word_controls=251,fired_binding_controls=len(bindings),
            not_instruction_patches=True)


if __name__=='__main__':
    unittest.main()
