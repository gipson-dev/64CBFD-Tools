"""Semantic checkpoint only: no installation or byte-match credit for this target."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_target_timer_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import game_actor_target_timer_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command


class ActorTargetTimerRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified-partial',source.RESEARCH_PARTIAL)
        cls.retail=list(struct.unpack_from('>115I',cls.values['conker/conker.us.bin'],source.ROM))
        cls.random=list(struct.unpack_from('>25I',cls.values['conker/conker.us.bin'],0xDAF18))
        cls.notify=list(struct.unpack_from('>26I',cls.values['conker/conker.us.bin'],0xBC040))

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_compile_boundary_and_frozen_production(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(115,80,60))
        self.assertEqual(self.row['raw_SHA256'],'7a173d55e1f6d80293c18209802ce9ab0bb18cba06317baa1329024ca4adc601')
        self.assertEqual(self.row['diagnostics'],'')
        for path,digest in source.INPUTS.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),digest,path)
        self.assertIn(source.ORIGINAL,(self.root/source.SOURCE).read_text())
        self.receipt('recovery-boundary',**{k:v for k,v in self.row.items() if k!='bindings'},installed=False,matching_credit=0)

    def test_02_complete_public_buffers_stores_callbacks_and_ABI(self):
        visits=set();count=0
        for case in self.cases:
            m=oracle.fixture(case);after,stores,calls,_=oracle.reference(m,case)
            for phase in (0,8):
                for words in (self.retail,self.words):
                    model=oracle.TimerModel(words,m,case,phase).run()
                    self.assertEqual(oracle.public(model.memory),oracle.public(after),case)
                    self.assertEqual(oracle.writes(model),stores,case);self.assertEqual(model.calls,calls,case)
                    if case.target<0:self.assertEqual(model.r[2],0)
                    if words is self.retail:visits|=model.visits
                count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+460,4))-visits,set())
        self.receipt('public-semantics',fixtures=len(self.cases),paired_phase_runs=count,
            all115_retail_words_visited=True,full_public_buffers_and_ordered_stores=True,
            no_general_numeric_return_claim=True,modeled_providers=True)

    def test_03_native_complete_buffers_and_effective_semantic_negatives(self):
        body=source.SELECTED
        for label,opt,sanitize in (('O0','-O0',False),('O2','-O2',False),('UBSan','-O2',True)):
            program=self.out/('native-'+label+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(body,self.cases))
            result=subprocess.run(native_command(opt,sanitize)+['-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(exe)]).returncode,0,label)
        negatives={
            'threshold-equality':body.replace('] < *timer','] <= *timer'),
            'probability-equality':body.replace('] < (s32)','] <= (s32)'),
            'unsigned-probability':body.replace('D_800872E8[D_800E0BD0]','(u8)D_800872E8[D_800E0BD0]'),
            'stale-context-timer':body.replace('    if (*timer == 0)', '    timer = (s32 *)((u8 *)D_800D23B0 + 0x29C) + slot;\n    if (*timer == 0)'),
            'distance-equality':body.replace('distance > 2000.0f','distance >= 2000.0f'),
        }
        for name,negative in negatives.items():
            self.assertNotEqual(body,negative,name)
            program=self.out/('negative-'+name+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(negative,self.cases))
            result=subprocess.run(native_command('-O2',False)+['-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn(subprocess.run([str(exe)]).returncode,(21,23),name)
        self.receipt('native',profiles=3,fixtures_each=len(self.cases),negative_controls=len(negatives),
            result_discarding_void_semantics=True,full_translated_public_buffers=True,
            modeled_float_provider_including_finite_stress_outside_RNG_range=True)

    def test_04_real_64bit_float_RNG_and_incidental_integer_result(self):
        connected={oracle.RANDOM+i*4:w for i,w in enumerate(self.random)}
        seeds=(0,1,2,3,89413,0xFFFFFFFF,0x100000000,0x1FFFFFFFF,0xFFFFFFFFFFFFFFFF,0x123456789ABCDEF0)
        self.assertEqual(oracle.next_seed(89413)&65535,65535)
        self.assertEqual(oracle.f32(oracle.f32(65535.)*oracle.floating(0x37800080)),1.)
        count=0
        for seed in seeds:
            for prob in (-1,0,50,100,127):
                case=oracle.Case(probability=prob);m=oracle.fixture(case)
                oracle.put(m,oracle.SEED,seed,8);oracle.put(m,oracle.SCALE,0x37800080,4)
                after,stores,calls,_=oracle.reference(m,case,seed)
                for words in (self.retail,self.words):
                    model=oracle.TimerModel(words,m,case,connected=connected).run()
                    self.assertEqual(oracle.public(model.memory),oracle.public(after))
                    self.assertEqual(oracle.writes(model),stores);self.assertEqual(model.calls,calls)
                    self.assertEqual(model.r[2],oracle.next_seed(seed)&65535)
                    self.assertTrue(set(connected)<=model.visits)
                count+=1
        self.receipt('actual-RNG',fixtures=count,all25_original_words_connected=True,
            actual64bit_seed_and_1_over_65535_scale=True,residual_V0_is_seed_low16_not_float_cast=True)

    def test_05_real_notification_wrapper_and_fired_access_cuts(self):
        connected={oracle.NOTIFY+i*4:w for i,w in enumerate(self.notify)}
        case=oracle.Case(slot=7,timer=1,notify_change=2,random_change=1)
        m=oracle.fixture(case);oracle.put(m,oracle.ACTORS+7*0x32C+0x13F,0xE3,1)
        after,stores,calls,_=oracle.reference(m,case)
        for words in (self.retail,self.words):
            model=oracle.TimerModel(words,m,case,connected=connected).run()
            self.assertEqual(oracle.public(model.memory),oracle.public(after));self.assertEqual(oracle.writes(model),stores)
            self.assertEqual(model.calls,[oracle.NOTIFY,oracle.SCRIPT,oracle.RANDOM])
            self.assertTrue(set(connected)<=model.visits)
            script=next(e for e in model.events if e[0]=='CALL' and e[1]==oracle.SCRIPT)
            self.assertEqual(script[2],(1,0x20E3,0x61,0x2000))
        # Matching access requests are a narrower claim than hardware exception equivalence.
        case=oracle.Case(slot=7,timer=1,notify_change=3,random_change=1);m=oracle.fixture(case)
        complete=oracle.TimerModel(self.retail,m,case).run();count=0
        for cut in range(complete.accesses):
            models=[]
            for words in (self.retail,self.words):
                model=oracle.TimerModel(words,m,case);model.fault=cut
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,cut);models.append(model)
            self.assertEqual(models[0].requested,models[1].requested)
            self.assertEqual(oracle.writes(models[0]),oracle.writes(models[1]));count+=1
        self.receipt('wrapper-and-cuts',actual26word_wrapper=True,script_provider_modeled=True,
            fired_access_cut_pairs=count,not_FCSR_or_hardware_exception_equivalence=True)

    def test_06_target_publication_alias_and_actual_returning_caller(self):
        case=oracle.Case(target=0);m=oracle.fixture(case);target=oracle.BANKS[0]+0x11C
        oracle.put(m,target,0x01000000,4);oracle.put(m,oracle.ACTORS+0x31C,target-0x129,4)
        after,stores,calls,_=oracle.reference(m,case)
        for words in (self.retail,self.words):
            model=oracle.TimerModel(words,m,case).run()
            self.assertEqual(oracle.public(model.memory),oracle.public(after));self.assertEqual(oracle.writes(model),stores)
        rom=self.values['conker/conker.us.bin'];jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        self.assertEqual([i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==jal],[0xCB5EC])
        count=0
        for case in self.cases[::17]:
            for words in (self.retail,self.words):
                m=oracle.fixture(case);entry=0x1509E13C
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({0x1509E3CC+i*4:w for i,w in enumerate(struct.unpack_from('>4I',rom,0xCB87C))})
                model=oracle.TimerModel(list(struct.unpack_from('>4I',rom,0xCB5EC)),m,case,connected=connected,entry=entry)
                # The dispatched caller's 0x48 frame and saved slots are explicit live-ins.
                frame=oracle.STACK-0x48;model.r[29]=frame
                oracle.put(model.memory,frame+0x24,0xDEAD0000,4);oracle.put(model.memory,frame+0x20,model.before[16],4)
                model.r[16]=oracle.BANKS[1];oracle.put(model.memory,oracle.BANKS[1]+8,case.slot,4)
                model.saved_f=model.f[20:].copy();model.run()
                self.assertEqual(model.caller_args,[(case.slot,)]);count+=1
        self.receipt('caller-and-alias',actual_returning_caller_runs=count,caller_frame_live_in=72,
            full_word_slot_delay_load=True,publication_then_target_reread=True,
            no_native_out_of_bounds_or_numeric_caller_result_claim=True)

    def test_07_whole_owner_profiles_actual_padding_and_production_isolation(self):
        same=mixed.candidate.source.neighbor.same_functions;profiles={}
        for label,normal in (('primary',False),('normal',True)):
            old,diag=source.compile_profile(self.root,self.out,self.values[source.SOURCE].decode(),'before-'+label,normal)
            new,words,row=source.compile_candidate(self.root,self.out,'after-'+label,source.RESEARCH_PARTIAL,normal=normal,whole=True)
            self.assertFalse(diag or row['diagnostics']);self.assertEqual(words,self.words)
            self.assertEqual(same(old,new,(source.FUNCTION,)),72)
            self.assertEqual(normalized_pools(old),normalized_pools(new));profiles[label]=new
        padded=mixed.padded(self.root,self.out,profiles['primary'],'private-padded',
            self.root/'conker/retail_word_patches.us.csv',profiles['normal'])
        baseline=self.root/'conker/build/src/game/generated_B3020.c.o'
        self.assertEqual(same(baseline,padded,(source.FUNCTION,)),72)
        self.assertEqual(normalized_pools(baseline),normalized_pools(padded))
        _,before=source.link_owner(self.root,self.out,baseline,source.OWNER)
        image,after=source.link_owner(self.root,self.out,padded,source.OWNER)
        self.assertEqual(before.keys(),after.keys())
        for name in after:self.assertEqual(before[name]['value'],after[name]['value'],name)
        self.assertEqual(list(struct.unpack_from('>115I',image,after[source.FUNCTION]['value'])),self.words)
        for path,value in self.values.items():self.assertEqual((self.root/path).read_bytes(),value,path)
        self.receipt('owner-isolation',profiles=2,neighbors_each=72,padded_other_functions=72,
            pools_and_all73_function_addresses_fixed=True,all_frozen_production_inputs_unchanged=True)


if __name__=='__main__':unittest.main()
