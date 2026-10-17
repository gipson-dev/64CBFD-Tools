"""Complete frame fits: literal memory/call cuts, native controls, no installation."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_sequence_record_setup as source
from tools.experiments import game_sequence_record_setup_frame as fit
from tools.experiments import game_sequence_state_reset as reset
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests import game_sequence_record_setup_native as native
from tools.tests import game_sequence_record_setup_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

EXPECTED = {
    'fitted': (473,273,'7788dad5751c126602de6768351244a490c80821b78d6106939d836bcfef8087',
        'a38503432609c98b268268bf4f62232923fee37d648c62cf1e9857c56b2680f4'),
    'preheader': (474,275,'7591a7e391b9c2d3a36cd1e86e8200e5794d8f5f1ef149f0ec1b20bc2708e2e8',
        '19aeaceffebfc1008e6faa7023b1bacc129f134af966962ced320d537e6cd331'),
}
HOMES = (0x3C,0x40,0x44,0x48,0x54,0x58,0x5C,0x70)


class Observed(model.SetupOracle):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.cuts=[]

    def record_call(self,target):
        super().record_call(target)
        self.cuts.append((tuple(self.r[i] for i in (*range(16,24),28,29,30)),
            tuple(model.read(self.memory,self.r[29]+offset) for offset in HOMES)))


def shape(word,index,route=None):
    op=word>>26
    if op in (1,4,5,6,7,20,21,22,23):
        displacement=word&65535
        if displacement&32768:displacement-=65536
        target=index+1+displacement
        return op,word>>16&31 if op==1 else None,route[target] if route is not None else target
    return (op,word&2047) if op==0 else (op,word&0x3FFFFFF) if op in (2,3) else (op,word&65535)


def controls(body):
    stale=fit.change(body,'    s32 value;','    s32 value;\n    SequenceRuntime49D30 *cachedRuntime;')
    stale=fit.change(stale,'        if ((D_800C35C8[slot])[i] != 0) {',
        '        if ((D_800C35C8[slot])[i] != 0) {\n            cachedRuntime = D_800C3A50[slot];')
    stale=fit.change(stale,'(D_800C3A50[slot])[i].','cachedRuntime[i].',2)
    cached=fit.change(body,'    s32 value;','    s32 value;\n    s32 cachedStatus;')
    cached=fit.change(cached,'    value = D_800C35EA[slot];',
        '    cachedStatus = D_800C35EA[slot];\n    value = cachedStatus;')
    cached=fit.change(cached,'if (D_800C35EA[slot] != 0)','if (cachedStatus != 0)')
    truncated,count=re.subn(r'(bundle\[[^\]]+\]\.bytes) >> 3',r'(u16)\1 >> 3',body)
    if count!=4:raise ValueError('Unknown descriptor controls')
    return dict(half_descriptor_size=truncated,
        missing_descriptor_group=fit.change(body,'    cursor += header->activeCount;\n',''),
        wrong_capacity=fit.change(body,'bytes = value * 2','bytes = value * 4',2),
        stale_runtime=stale,
        wrong_process_index=fit.change(body,'func_15020388(i, slot);','func_15020388(i + 1, slot);'),
        signed_total=fit.change(body,'(u16)D_800C3C9A * 12','(s16)D_800C3C9A * 12'),
        stale_request_status=cached,
        wrong_callback_parameter=fit.change(body,'D_800840FC[hook](scene, sequence, slot, parameter)',
            'D_800840FC[hook](scene, sequence, slot, 0)'))


class SequenceRecordSetupFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/fit.BUILD
        cls.variants={}
        for label,body in fit.forms('selected'):
            cls.variants[label]=(body,*source.measure(cls.root,cls.out,label,body))
        cls.truth=list(struct.unpack_from('>473I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_complete_original_both_frame_fits_all89_bindings_and_56_neighbors(self):
        original=assembly.ViewListSetupTests.original.__func__(self,'original-frame-setup',
            (self.out/'before-view_list_caller_original').read_text(),source.FUNCTION)
        data,functions=source.build.link_owner(self.root,self.out,original,source.OWNER)
        f=functions[source.FUNCTION]
        self.assertEqual((f['size'],data[f['value']:f['value']+f['size']]),
            (1892,struct.pack('>473I',*self.truth)))
        before,diagnostics=source.compile_owner(self.root,self.out,
            (self.out/'before-view_list_caller_owner').read_text(),'frame-neighbor-before',True)
        self.assertEqual(diagnostics,'')
        rows={}
        for label,(body,obj,words,row) in self.variants.items():
            count,differences,raw_hash,bindings_hash=EXPECTED[label]
            self.assertEqual((row['words'],row['frame'],row['differences']),(count,120,differences))
            self.assertEqual(row['raw_sha256'],raw_hash)
            self.assertEqual(len(row['bindings']),89)
            self.assertEqual(hashlib.sha256(json.dumps(row['bindings'],sort_keys=True).encode()).hexdigest(),bindings_hash)
            self.assertEqual(row['diagnostics'],'');self.assertFalse(row['pools'])
            self.assertEqual(words[:12],self.truth[:12])
            self.assertEqual(same_functions(before,obj,(source.FUNCTION,)),56)
            if label=='fitted':
                route={i:None if i==95 else i if i<95 or i>=279 else i-1 for i in range(473)}
                unused=[278];missing=[95];changed=[(281,281)]
            else:
                route={i:i if i<279 else i+1 for i in range(473)}
                unused=[279];missing=[];changed=[(281,282)]
            actual_missing=[i for i in route if route[i] is None]
            actual_unused=sorted(set(range(len(words)))-{i for i in route.values() if i is not None})
            actual_changed=[(i,k) for i,k in route.items() if k is not None and
                shape(self.truth[i],i,route)!=shape(words[k],k)]
            self.assertEqual((actual_missing,actual_unused,actual_changed),(missing,unused,changed))
            rows[label]=dict(words=count,frame=120,word_differences=differences,
                missing_original_words=missing,extra_C_words=unused,nonregister_changed_words=changed)
        self.receipt('frame-boundary',variants=rows,all56_neighbors=True,all89_bindings_pinned=True,
            register_free_routing_diagnostic_not_a_guard_plan=True,no_guards_or_installation_or_credit=True)

    def test_02_full_three_way_memory_events_private_homes_and_saved_roles_at_every_call(self):
        visits={label:set() for label in ('original',*self.variants)};count=0;fired=set()
        for memory,args,config in model.cases():
            reference=model.Reference(memory,args,config).run()
            for phase in (0,8):
                original=Observed(self.truth,memory,args,config,reference.allocations,phase).run()
                self.assertTrue(model.public(original.memory)==model.public(reference.memory),(args,config,phase))
                self.assertEqual(original.calls,reference.calls)
                self.assertEqual(original.provider.snapshots,reference.snapshots)
                self.assertEqual(original.provider.fired,reference.fired)
                visits['original'].update(original.visits);fired.update(reference.fired)
                events=[e for e in original.events if e[0] in ('R','W')]
                for label,(_,_,words,_) in self.variants.items():
                    entry=source.ENTRY if label=='fitted' else fit.WITNESS_ENTRY
                    actual=Observed(words,memory,args,config,reference.allocations,phase,entry=entry).run()
                    self.assertTrue(actual.memory==original.memory,(label,args,config,phase))
                    self.assertEqual(actual.calls,reference.calls)
                    self.assertEqual(actual.provider.snapshots,reference.snapshots)
                    self.assertEqual(actual.provider.fired,reference.fired)
                    self.assertEqual(actual.cuts,original.cuts,(label,args,config,phase))
                    self.assertEqual([e for e in actual.events if e[0] in ('R','W')],events,(label,args,config,phase))
                    visits[label].update(actual.visits)
                count+=1
        for label,words,entry in [('original',self.truth,source.ENTRY)]+[
                (label,v[2],source.ENTRY if label=='fitted' else fit.WITNESS_ENTRY) for label,v in self.variants.items()]:
            self.assertEqual(visits[label]&set(range(entry,entry+len(words)*4,4)),set(range(entry,entry+len(words)*4,4)))
        self.assertEqual(len(fired),8)
        self.receipt('frame-guest',three_way_cases=count,all473_473_474_words_visited=True,
            all_memory_including_private_stack=True,all_ordered_memory_events=True,
            all_saved_GPR_GP_SP_FP_roles_and_eight_literal_homes_at_every_provider=True,
            final_saved_GPR_FPR_SP_RA_ABI=True,positive_gates=sorted(fired),
            preheader_entry=fit.WITNESS_ENTRY,original_entry_for_fitted=True,
            scratch_register_fault_state_and_full_gameplay_not_qualified=True)

    def test_03_all58_bounded_screens_and_private_witness_placement_controls(self):
        rows=[];labels=set()
        for label,body in fit.forms('all'):
            self.assertNotIn(label,labels);labels.add(label)
            row=fit.run(self.root,self.out,label,body)
            self.assertEqual(row['diagnostics'],'');self.assertFalse(row['pools'])
            rows.append({k:row[k] for k in ('label','words','frame','differences','raw_sha256','save_words_match')})
        self.assertEqual(len(rows),58)
        with patch.object(fit,'WITNESS_ENTRY',source.ENTRY):
            with self.assertRaisesRegex(ValueError,'private witness placement'):
                fit.run(self.root,self.out,'overlapping-witness-control',dict(fit.indexed_forms())['indexed-rows'])
        with patch.object(fit,'WITNESS_ENTRY',0x26010000):
            with self.assertRaisesRegex(ValueError,'private witness placement'):
                fit.run(self.root,self.out,'wrong-region-control',fit.FITTED)
        self.receipt('frame-screens',rows=rows,two_witnesses_each_not_full_alternative_qualification=True,
            both_private_placement_controls_fired=True,original_recovery_selected_unchanged=True)

    def test_04_all136_live_production_inputs_unchanged_and_unknowns_rejected(self):
        read=Path.read_bytes
        for key,relative in source.PATHS.items():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            self.assertEqual(hashlib.sha256(read(target)).hexdigest(),source.BASELINE[key])
        self.assertEqual(source.SELECTED,source.INITIAL)
        self.receipt('frame-inputs',unchanged_inputs=len(source.PATHS),corruptions_rejected=len(source.PATHS),
            production_source_guards_image_progress_and_original_recovery_unchanged=True)

    def test_05_both_actual_native_bodies_O2_O0_UBSan_and_sixteen_effective_controls(self):
        caller=self.out/'frame-native-caller.c';caller.write_text(native.program())
        reset_unit=self.out/'frame-native-reset.c'
        reset_unit.write_text(native.BODY_HEADER+reset.SELECTED.replace('func_1501D044','actual_reset')+'\n')
        exits={}
        for label,(body,_,_,_) in self.variants.items():
            variants=[('o2','-O2',body),('o0','-O0',body)]+[(name,'-O2',changed) for name,changed in controls(body).items()]
            for name,opt,changed in variants:
                if name not in ('o2','o0'):self.assertNotEqual(changed,body)
                unit=self.out/('frame-native-'+label+'-'+name+'.c');unit.write_text(native.BODY_HEADER+changed+'\n')
                exe=unit.with_suffix('.elf')
                command=[*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                    str(unit.relative_to(self.root)),str(reset_unit.relative_to(self.root)),str(caller.relative_to(self.root)),
                    '-o',str(exe.relative_to(self.root))]
                built=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
                self.assertEqual(built.returncode,0,built.stderr)
                ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
                exits[label+'-'+name]=ran.returncode
                if name in ('o2','o0'):self.assertEqual(ran.returncode,0,(label,name,ran.stdout,ran.stderr))
                else:self.assertIn(ran.returncode,(21,22),(label,name,ran.stdout,ran.stderr))
        self.receipt('frame-native',cases_each_body_each_profile=sum(1 for _ in native.cases()),exits=exits,
            both_actual_C_bodies_separate_caller_providers_and_actual_reset=True,
            all756_fields_bank_padding_canaries_allocated_bytes_and_gaps=True,
            exact_packets_31_lane_snapshots_and_positive_counters=True,UBSan=True,no_fwrapv=True,
            opaque_provider_contract_not_retail_hardware_or_gameplay=True)


if __name__=='__main__':unittest.main()
