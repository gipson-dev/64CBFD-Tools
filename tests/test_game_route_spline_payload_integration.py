"""Native C, real callers, actual Make recipe and linked spline installation."""
import csv
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_spline_payload_integration as source
from tools.tests import test_game_route_spline_payload_layout as previous
from tools.tests import test_game_route_spline_payload_recovery as guest

CALLER=0x15087CC0


class CallerOracle(guest.PayloadOracle):
    def __init__(self,words,memory,helpers,phase=0):
        self.trace=[];self.literal=True;self.array_top=guest.STACK+phase-48-44
        guest.guest.base.PointProjectionOracle.__init__(self,words,memory,(),[],phase,CALLER,helpers)

    def record_call(self,target):
        if target==source.ENTRY:self.calls.append((target,self.arguments(3)))
        else:super().record_call(target)


class SplinePayloadIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.installed=source.verify(cls.root,cls.out)=='after'
        with source.historical_view(cls.root,cls.out):
            cls.prediction=source.predict(cls.root,cls.out)
            cls.obj=cls.out/'primary-no-unroll.o';cls.raw,cls.bindings=source.layout.source.checked(cls.obj,True)
            cls.raw_words=source.layout.source.link_literal(cls.root,cls.out,cls.obj)
            cls.normalized,cls.moved=source.layout.normalize(cls.raw,cls.bindings)
        cls.image=source.raw_read(cls.root/'conker/build/conker.us.elf') if cls.installed else source.raw_read(cls.out/'after-elf')
        cls.words=list(struct.unpack_from('>305I',cls.image,source.prior.elf_slot_offset(cls.image,source.ENTRY,1220)))
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=list(struct.unpack_from('>305I',cls.rom,source.ROM))
        cls.assembly,cls.retail_bindings=previous.retail_bindings(cls.root);cls.helpers={};cls.helper_bodies={}
        for entry,count in guest.HELPERS.items():
            at=source.prior.elf_slot_offset(cls.image,entry,count*4);body=list(struct.unpack_from('>%dI'%count,cls.image,at))
            if body!=list(struct.unpack_from('>%dI'%count,cls.rom,entry-0x14FD2B50)):raise ValueError('Changed linked helper')
            cls.helper_bodies[entry]=body;cls.helpers.update(zip(range(entry,entry+count*4,4),body))

    def run(self,result=None):
        with source.historical_view(self.root,self.out):return super().run(result)

    def receipt(self,name,**values):
        values['production_installed']=self.installed
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    test_01_isolated_words_and_bindings=previous.SplinePayloadLayoutTests.test_01_all_305_words_and_independent_retail_bindings
    test_02_full_guest_states=previous.SplinePayloadLayoutTests.test_02_complete_guest_states_real_helpers_and_literal_calls
    test_03_all_fired_prefixes=previous.SplinePayloadLayoutTests.test_03_fired_instruction_memory_prefixes_include_the_saved_roles
    test_04_extrapolation_dependencies=previous.SplinePayloadLayoutTests.test_04_extrapolation_dependencies_and_defined_history_addresses
    test_05_complete_rebases=previous.SplinePayloadLayoutTests.test_05_two_complete_independent_data_and_call_rebases
    test_06_effective_raw_and_recipe_controls=previous.SplinePayloadLayoutTests.test_06_all_raw_words_bindings_and_recipe_controls_fail_closed
    test_07_reject_lower_difference_private_regression=previous.SplinePayloadLayoutTests.test_07_lower_difference_screen_still_fails_private_memory
    test_08_real_private_padder=previous.SplinePayloadLayoutTests.test_08_actual_private_padder_preserves_mixed_profile_owner

    def test_09_native32_effectful_full_arena_and_controls(self):
        result=source.native.qualify(self.root,self.out)
        self.assertEqual(result['cases_per_positive_build'],6270);self.assertEqual(result['effective_controls'],9)
        self.assertTrue(result['all_five_effectful_gates_required']);self.assertFalse(result['smoke_only'])

    def test_10_actual_Make_and_first_prediction_or_installed_audit(self):
        self.assertEqual(self.prediction['after'],source.AFTER)
        plan=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual(plan['actual_expanded_Make_commands'],7)
        self.assertEqual((plan['primary_owner_flag_count'],plan['normal_override_flag_count']),(1,0))
        self.assertTrue(plan['all73_primary_functions_equal']);self.assertTrue(plan['original_four_GLOBAL_ASM_bodies_preserved'])
        if self.installed:self.assertEqual(source.audit(self.root,self.out)['changed_ELF_bytes'],1050)
        else:self.assertEqual(source.verify(self.root,self.out),'before')
        original=source.raw_read(self.out/('before-%02d'%list(source.INPUTS).index('conker/build/conker.us.elf')))
        bad=bytearray(self.rom[source.ROM:source.ROM+1220]);bad[0]^=1
        with self.assertRaises(ValueError):source.predicted_image(original,bad)
        changed=list(source.SYMBOL_ORDERS);old,new=changed[0];changed[0]=(old,tuple(reversed(new)))
        with patch.object(source,'SYMBOL_ORDERS',tuple(changed)),self.assertRaises(ValueError):
            source.predicted_image(original,self.rom[source.ROM:source.ROM+1220])

    def test_11_both_real_dispatch_sites_and_100_connected_cases(self):
        caller=list(struct.unpack_from('>67I',self.image,source.prior.elf_slot_offset(self.image,CALLER,268)))
        self.assertEqual(caller,list(struct.unpack_from('>67I',self.rom,CALLER-0x14FD2B50)))
        sites=[i for i,w in enumerate(caller) if w==(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)]
        self.assertEqual(sites,[43,51]);self.assertEqual([caller[i+1] for i in sites],[0x00003025,0x24060001])
        self.assertEqual([caller[i+2] for i in sites],[0x3C02800D,0x3C02800D])
        found=[];opcode=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)
        with (self.root/'conker/retail_layout.us.txt').open() as stream:
            for row in csv.DictReader(stream):
                if row['section']!='game':continue
                for at in range(int(row['address'],0),int(row['end'],0),4):
                    if struct.unpack_from('>I',self.rom,at-0x14FD2B50)[0]==opcode:found.append((row['function'],at))
        self.assertEqual(found,[('func_15087CC0',0x15087D6C),('func_15087CC0',0x15087D8C)])
        count=0
        for stop in (0,1):
            for slot,initialized,valid,phase in itertools.product((-128,-1,0,1,127),(1,128) if stop else (0,1,128),(1,4),(0,8)):
                memory,args=guest.fixture(initialized=initialized,valid=valid)
                actor=(0x800CC2D0+slot*812)&0xFFFFFFFF
                memory.update({(actor+i)&0xFFFFFFFF:memory[guest.ACTOR+i] for i in range(0x400)})
                guest.put(memory,guest.RECORD+0x30,0,1);guest.put(memory,guest.RECORD+0x31,slot,1)
                guest.put(memory,guest.RECORD+0x48,stop,1)
                guest.put(memory,0x800872A0,guest.RECORD);guest.put(memory,0x800D2398,1,1);guest.put(memory,0x800D23A9,0xA5,1)
                machines=[]
                for body in (self.words,self.truth):
                    helpers=dict(self.helpers);helpers.update(zip(range(source.ENTRY,source.ENTRY+1220,4),body))
                    machines.append(CallerOracle(caller,memory,helpers,phase).run())
                a,b=machines;self.assertEqual(previous.state(a),previous.state(b))
                self.assertEqual([c for c in a.calls if c[0]==source.ENTRY],[(source.ENTRY,(guest.RECORD,actor,stop))])
                self.assertEqual(guest.read(a.memory,0x800D23A9,1),0);count+=1
        self.assertEqual(count,100)
        self.receipt('connected-callers',cases=count,real_dispatcher_words=67,real_payload_words=305,
            real_helper_words=216,original_sites=['0x15087D6C','0x15087D8C'],V0_overwritten_at_both_returns=True,
            unknown_indirect_callers_not_claimed=True)

    def test_12_mixed_stages_and_fixture_changes_fail_closed(self):
        checkpoint=source.prior.candidate.source.checkpoint;read=checkpoint.raw_read
        new=source.expected_inputs(self.root,self.out)
        for path in source.AFTER:
            mapped={str((self.root/p).resolve()):value for p,value in new.items()}
            mapped[str((self.root/path).resolve())]=source.raw_read(self.out/('before-%02d'%list(source.INPUTS).index(path)))
            with patch.object(checkpoint,'raw_read',side_effect=lambda p:mapped.get(str(p.resolve()),read(p))),self.assertRaises(ValueError):
                source.verify(self.root,self.out)
        self.receipt('stage-controls',mixed_stage_rejections=3,first_prediction_pins_unchanged=True)


if __name__=='__main__':unittest.main()
