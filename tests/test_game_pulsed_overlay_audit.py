"""Prove inherited pulse-off state without installing an undefined C read."""
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_pulsed_overlay_audit as source
from tools.tests import game_pulsed_overlay_oracle as model
from tools.tests import game_shared_overlay_oracle as caller
from tools.tests import test_game_view_list_setup as original
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_color_overlay_draw import state


class PulsedOverlayAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out);cls.images=source.images(cls.root,cls.out)
        cls.elf=(cls.out/'before-elf').read_bytes();cls.screens=source.screens(cls.root,cls.out)
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.obj=original.ViewListSetupTests.original.__func__(context,'original-pulse',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(cls.root,cls.out,cls.obj,source.OWNER)
        f=functions[source.FUNCTION]
        cls.assembled=list(struct.unpack_from('>111I',data,f['value']))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.out/'zero-substitution-rejected.o',source.OWNER)
        f=functions[source.FUNCTION]
        cls.zero=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        cls.helpers=model.helpers(cls.images)
        cls.leaf_helpers={pc:w for pc,w in cls.helpers.items() if not source.ENTRY<=pc<source.ENTRY+444}

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def execute(self,memory,args,phase=0):
        return model.PulseOracle(self.images['pulse'],memory,args,phase,connected=self.leaf_helpers).run()

    def test_01_original111_word_object_and_private_read_static_provenance(self):
        self.assertEqual(self.assembled,self.images['pulse'])
        raw,functions,bindings=source.previous.parse_object(self.obj);f=functions[source.FUNCTION]
        self.assertEqual(f['size'],444);self.assertEqual(len(bindings),16)
        words=self.images['pulse'];self.assertEqual(words[:3],[0x27BDFFD0,0xAFBF001C,0xAFA40030])
        self.assertEqual(words[0x4C//4],0x11E00018);self.assertEqual(words[0x50//4],0xC7A20020)
        self.assertEqual(words[0x9C//4],0x44801000)
        stack_stores=[(i*4,w&65535) for i,w in enumerate(words) if w>>21&31==29 and w>>26 in (40,41,43,57,61)]
        self.assertEqual(stack_stores,[(4,0x1C),(8,0x30),(0x198,0x14),(0x1A8,0x10)])
        self.assertFalse(any(offset<=0x20<offset+4 for _,offset in stack_stores))
        self.assertEqual(self.images['caller'][0],0x27BDFFD8)
        archive=(self.out/'before-pulse_archive').read_text()
        lo,hi=source.build.function_span(archive,source.FUNCTION)
        self.assertIn('f32 sp20;',archive[lo:hi]);self.assertIn('var_f2 = sp20;',archive[lo:hi])
        self.assertNotIn('sp20 =',archive[lo:hi])
        self.receipt('static',retail_words=111,original_assembled_and_bound=True,bindings=16,
            frame=48,blend_read_offset=32,caller_frame=40,caller_entry_relative_read=-56,
            no_dominating_local_write=True,archive_also_uninitialized=True,not_source_acceptance=True)

    def test_02_actual_pulse_wave_and_draw_chain_complete_reference(self):
        seen=set();count=0;reads=0;enabled=0
        for timer,alpha,pulse,angle,palette,seed,phase in itertools.product((0,1,65535),(0,1,127,255),
                (0,1,255),(0,64,128,192,255),(0,1,255),model.SEEDS,(0,8)):
            memory,args=model.fixture(self.elf,timer,alpha,pulse,angle,palette,seed,phase)
            expected,result,calls,packet=model.reference(memory,args[0],phase)
            m=self.execute(memory,args,phase);count+=1;seen.update(m.visits)
            self.assertEqual(model.draw.public(m.memory),model.draw.public(expected))
            self.assertEqual((m.r[2],m.calls,m.draw_packets),(result,calls,[] if packet is None else [packet]))
            active=bool(timer and alpha)
            self.assertEqual(len(m.read_provenance),int(active))
            if active:
                row,written=m.read_provenance[0];self.assertFalse(written)
                self.assertEqual(row,(source.ENTRY+0x50,source.ENTRY+0x4C,model.STACK+phase-0x10,4,seed))
                reads+=1;enabled+=bool(pulse)
            self.assertEqual(model.DRAW in m.visits,active)
            self.assertEqual(model.SHIFT in m.visits,bool(active and pulse))
            self.assertEqual(model.WAVE in m.visits,bool(active and pulse))
        own={pc for pc in seen if source.ENTRY<=pc<source.ENTRY+444}
        self.receipt('guest',cases=count,read_before_local_write_witnesses=reads,pulse_enabled_chains=enabled,
            natural_wrapper_words=len(own),unvisited_offsets=sorted(pc-source.ENTRY for pc in set(range(source.ENTRY,source.ENTRY+444,4))-own),
            actual_shift_slot_words=12,actual_wave_words=36,actual_draw_words=197,
            independent_literal_packet_reference=True,not_native_or_hardware_FP_acceptance=True)

    def test_03_real_setter_updater_and_zero_substitution_counterexamples(self):
        witnesses=[]
        for pulse,seed,phase in itertools.product((0,1),model.SEEDS,(0,8)):
            memory,args=model.fixture(self.elf,timer=0,alpha=0,pulse=255,seed=seed,phase=phase)
            setter=model.PulseOracle(self.images['setter'],memory,(0,9,4,127,pulse),phase,source.SPANS['setter'][0]).run()
            self.assertEqual(model.read(setter.memory,model.PULSE,1),pulse)
            model.put(setter.memory,0x800BE9E4,1)
            update=model.PulseOracle(self.images['update'],setter.memory,(0,),phase,source.SPANS['update'][0]).run()
            self.assertEqual(model.read(update.memory,model.TIMER,2),8)
            self.assertEqual(model.read(update.memory,model.ANGLE,1),4)
            m=self.execute(update.memory,args,phase)
            actual=model.reference(update.memory,args[0],phase)
            zero=model.reference(update.memory,args[0],phase,zero=True)
            control=model.PulseOracle(self.zero,update.memory,args,phase,connected=self.leaf_helpers).run()
            self.assertEqual(m.draw_packets,[actual[3]])
            self.assertEqual(control.draw_packets,[zero[3]])
            self.assertEqual(model.draw.public(control.memory),model.draw.public(zero[0]))
            if actual[3]!=zero[3]:witnesses.append(dict(pulse=pulse,seed=seed,phase=phase,retail=actual[3],zero=zero[3]))
            self.assertFalse(m.read_provenance[0][1])
        self.assertTrue(witnesses);self.assertEqual({r['pulse'] for r in witnesses},{0})
        self.assertTrue(any(r['seed']==model.bits(.25) for r in witnesses))
        self.receipt('setter-witnesses',actual_setter_and_updater_cases=24,counterexamples=witnesses,
            public_setter_accepts_pulse_zero=True,actual_compiled_zero_candidate_rejected=True,no_fake_zero_blend=True)

    def test_04_complete175word_caller_with_actual_pulse_chain(self):
        count=0;seen=set()
        for views,counter,disabled,pattern,pulse,seed,phase in itertools.product((0,1),(0,4,5,128),
                (0,1),range(4),(0,1),(0,model.bits(.25)),(0,8)):
            memory=caller.fixture(views,counter,pattern,disabled,pattern&1)
            additions,_=model.fixture(self.elf,pulse=pulse,seed=seed,phase=phase,caller_frame=True)
            memory.update(additions)
            # The leaf's pointer-cell canaries overlap the caller's dimensions.
            model.put(memory,caller.WIDTH,320);model.put(memory,caller.HEIGHT,240)
            nested=[]
            old_returned=caller.returned
            def returned(target,args,ordinal,selected):
                if target==source.ENTRY:return args[0]+40
                return old_returned(target,args,ordinal,selected)
            def effects(memory,target,args,ordinal,mode):
                if target==source.ENTRY:
                    after,_,calls,_=model.reference(memory,args[0],phase,caller_frame=True)
                    memory.clear();memory.update(after);nested.extend(calls)
                return False
            with patch.object(caller,'returned',side_effect=returned),patch.object(caller,'effects',side_effect=effects):
                expected,calls,_,_,_,result=caller.reference(memory,pattern)
            expanded=[]
            for target,args in calls:
                expanded.append((target,args))
                if target==source.ENTRY:expanded.extend(nested)
            m=model.CallerOracle(self.images['caller'],memory,(caller.CURSOR,),self.helpers,phase,pattern).run()
            self.assertEqual(model.draw.public(m.memory),model.draw.public(expected))
            self.assertEqual((m.r[2],m.calls),(result,expanded))
            self.assertEqual(m.read_provenance[0][0][2],model.STACK+phase-0x38)
            self.assertFalse(m.read_provenance[0][1]);seen.update(m.visits);count+=1
        missing=set(range(source.SPANS['caller'][0],source.SPANS['caller'][0]+700,4))-seen
        self.assertFalse(missing,sorted(missing))
        self.receipt('caller',cases=count,all175_caller_words=True,actual111_12_36_197_chain=True,
            inherited_word_below_caller_SP=True,other_scene_providers_bounded_opaque=True,
            not_full_provider_stack_history_or_gameplay=True)

    def test_05_positively_fired_private_read_and_packet_fault_prefixes(self):
        count=0;read_fired=0
        for pulse,seed,phase in itertools.product((0,1),(0,model.bits(.25)),(0,8)):
            memory,args=model.fixture(self.elf,pulse=pulse,seed=seed,phase=phase)
            complete=self.execute(memory,args,phase)
            for cut in range(complete.all_accesses):
                models=[]
                for body in (self.images['pulse'],self.assembled):
                    m=model.PulseOracle(body,memory,args,phase,connected=self.leaf_helpers);m.access_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);models.append(m)
                self.assertTrue(state(models[0])==state(models[1]));count+=1
                if models[0].current_pc==source.ENTRY+0x50:read_fired+=1
        self.assertEqual(read_fired,8)
        self.receipt('faults',positively_fired_prefix_pairs=count,inherited_read_faults=read_fired,
            independent_assembled_vs_ROM_words=True,not_CP0_or_portable_C_fault_acceptance=True)

    def test_06_all_screens_rejected_and154_input_corruptions_fail_closed(self):
        self.assertEqual([(r['words'],r['differences']) for r in self.screens],[(93,101),(112,101),(110,80)])
        self.assertEqual([r['unchanged_raw_neighbors'] for r in self.screens],[27]*3)
        self.assertTrue(all(not r['installable'] and not r['matching_credit'] for r in self.screens))
        self.assertFalse(hasattr(source,'SELECTED'))
        self.assertEqual(len(source.PATHS),154);read=Path.read_bytes
        for relative in source.PATHS.values():
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.receipt('unchanged',protected_input_entries=154,distinct_paths=len(set(source.PATHS.values())),
            all_source_ELF_CSV_guards_archive_inputs_byte_identical=True,production_changes=0,matching_credit=0,
            rejected_source_forms=3,no_native_acceptance_claim=True)

    def test_07_original_ten_word_sequence_packet_sets_pulse_one_on_both_speed_routes(self):
        class PacketJoin(Exception):pass
        class PacketCode(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==0x15025ECC:raise PacketJoin
                return super().__getitem__(pc)
        class PacketOracle(model.PulseOracle):
            def record_call(self,target):
                if target!=source.SPANS['setter'][0]:raise AssertionError('Unexpected setter packet target')
                args=self.arguments(5)
                assert args[4]==1,'Sequence pulse-one packet changed'
                self.calls.append((target,args));self.events.append(('CALL',target,args))
        helper=dict(zip(range(0x1517F720,0x1517F75C,4),self.images['setter']))
        seen=set();count=0
        for speed,palette,phase in itertools.product((0,1,-1,-32768,32767),(-128,-1,0,127),(0,8)):
            memory,_=model.fixture(self.elf,phase=phase)
            model.put(memory,model.draw.PACKET+5,palette&255,1)
            model.put(memory,model.draw.PACKET+6,speed&65535,2)
            m=PacketOracle(self.images['setter_packet'],memory,(0,9),phase,0x15025EA4,helper)
            m.r[18]=model.draw.PACKET;m.code=PacketCode(m.code,m);m.code[0x15025ECC]=0
            with self.assertRaises(PacketJoin):m.run()
            self.assertEqual(m.calls,[(0x1517F720,(palette&model.MASK,9,(speed or 4)&model.MASK,127,1))])
            self.assertEqual(model.read(m.memory,model.PULSE,1),1);seen.update(m.visits);count+=1
        self.assertTrue(set(range(0x15025EA4,0x15025ECC,4))<=seen)
        bad=list(self.images['setter_packet']);self.assertEqual(bad[4],0x24180001);bad[4]=0x24180000
        m=PacketOracle(bad,memory,(0,9),phase,0x15025EA4,helper);m.r[18]=model.draw.PACKET;m.code=PacketCode(m.code,m);m.code[0x15025ECC]=0
        with self.assertRaisesRegex(AssertionError,'pulse-one'):m.run()
        self.receipt('sequence-packet',bounded_packet_cases=count,all10_packet_words=True,
            actual15_word_setter=True,both_speed_routes=True,pulse_one_negative_fired=True,
            not_complete_sequence_engine_or_all_program_invariant=True)


if __name__=='__main__':unittest.main()
