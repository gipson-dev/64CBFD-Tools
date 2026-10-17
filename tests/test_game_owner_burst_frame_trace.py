"""Observe the upstream frame budget and qualify aligned packets without credit."""
import copy
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_owner_burst_frame_trace as trace
from tools.experiments import game_owner_burst_storage_candidates as storage
from tools.experiments import game_owner_burst_emitter as source
from tools.tests import test_game_owner_burst_emitter as prior
from tools.tests.test_game_projected_packet_draw import native_command


class BurstFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/trace.BUILD
        cls.traces={}
        for form in ('selected','descriptor-align8','aligned-pairs'):
            cls.traces[form]=trace.trace(cls.root,cls.out,form,form)
        cls.obj,cls.padded,cls.images,cls.row=storage.qualify_aligned(cls.root,cls.root/storage.BUILD)
        prior.OwnerBurstRecoveryTests.setUpClass()
        cls.harness=prior.OwnerBurstRecoveryTests('test_02_full_uniform_stack_public_protocol')

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_wire_addresses_are_actual_emitted_addresses(self):
        expected={k:v-0x150 for k,v in dict(payload=0xBC,input0=0xB0,output0=0xA8,
            delta=0x9C,request=0xF0,savedData=0x14C).items()}
        for form,record in self.traces.items():
            layout=trace.checked_layout(record)
            words=list(struct.unpack_from('>288I',source.projection.sections(self.out/form/'baseline-linked.elf')['.text'][1]))
            self.assertTrue(trace.prove_machine_offsets(layout,words)['wire_and_machine_offsets_equal'])
            self.assertEqual((record['frontend_records'],record['optimizer_records']),(513,466))
        self.assertEqual(self.traces['aligned-pairs']['layout']['caller_relative'],expected)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(288,352,85))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],11)
        self.assertEqual(source.parts(self.obj)[1],source.parts(self.harness.obj)[1])
        self.receipt('storage',observed={k:v['layout'] for k,v in self.traces.items()},
            aligned_packets_at_retail_caller_relative_addresses=True,frame_still_16_bytes_large=True,
            source_types_are_candidates_not_original_type_proof=True,installed=False,matching_credit=0)

    def test_02_effective_trace_and_machine_negative_controls(self):
        count=0
        for form,record in self.traces.items():
            controls=[]
            bad=copy.deepcopy(record);bad['code_unchanged']=False;controls.append(bad)
            bad=copy.deepcopy(record);bad['events'][-1]['frame']+=8;controls.append(bad)
            bad=copy.deepcopy(record);bad['events'][-1]['locals']+=8;controls.append(bad)
            bad=copy.deepcopy(record);bad['events'][-1]['pool']=[{'pointer':4,'size':4,'offset':0}];controls.append(bad)
            bad=copy.deepcopy(record);next(r for r in bad['frontend_definitions'] if r['storage']=='M')['length']+=4;controls.append(bad)
            bad=copy.deepcopy(record);next(r for r in bad['optimizer_definitions'] if r['storage']=='M')['length']+=4;controls.append(bad)
            bad=copy.deepcopy(record);next(r for r in bad['frontend_markers']['input0'] if r['storage']=='M')['offset']-=4;controls.append(bad)
            for bad in controls:
                with self.assertRaises(ValueError):trace.checked_layout(bad)
                count+=1
            work=self.out/form;log=(work/'debugger.txt').read_text()
            for prefix in ('FRAME_TRACE ','FRAME_INPUT ','TRACE_EXIT '):
                bad='\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
                with self.assertRaises(ValueError):trace.shared.validate_observations(work,bad)
                count+=1
            original=Path.read_bytes;target=work/'frontend.ucode';wrong=bytearray(target.read_bytes());wrong[8]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p==target else original(p)):
                with self.assertRaises(ValueError):trace.shared.validate_observations(work,log)
            count+=1
            content=(work/'baseline.c').read_text()
            wire=json.loads((work/'receipt.json').read_text())
            self.assertEqual(trace.phase_summary(wire,content)['frontend_markers'],record['frontend_markers'])
            with self.assertRaisesRegex(ValueError,'Missing/ambiguous'):
                trace.phase_summary(wire,content.replace('payload.owner = owner;','payload.owner = other;'))
            count+=1
            words=list(struct.unpack_from('>288I',source.projection.sections(work/'baseline-linked.elf')['.text'][1]));words[0]^=8
            with self.assertRaises(ValueError):trace.prove_machine_offsets(record['layout'],words)
            count+=1
        self.receipt('controls',effective_fail_closed_controls=count)

    def compare(self,memory,case):
        return self.harness.compare(memory,case,images=[self.harness.truth,*self.images])

    def test_03_complete_uniform_and_nonuniform_public_packets(self):
        count=0;seen=set()
        for pattern,phase,gate,state,previous,counter,time,step,basis,allocate in itertools.product(
                (0,1),(0,8),range(5),(0,1),(0,1),(0,3,128),(1.,4.5),(0.,1.),(False,True),(False,True)):
            machines,_=self.compare(*prior.fixture(gate,state,previous,counter,time,step,basis,allocate,pattern=pattern,phase=phase))
            count+=1;seen.update(machines[0].visits)
        for pattern,phase,mode,samples in itertools.product((0,1),(0,8),range(1,5),((0.,0.),(.5,.25),(.875,.999))):
            self.compare(*prior.fixture(state=1,previous=1,pattern=pattern,phase=phase,mode=mode,samples=samples));count+=1
        for pattern,phase,counter in itertools.product((0,1),(0,8),(1,127,255)):
            self.compare(*prior.fixture(count=counter,time=2.5,step=0.,pattern=pattern,phase=phase));count+=1
        edges=0
        for pattern,phase,override in itertools.product((0,1),(0,8),(-1.,-.5,2147483648.,4294967040.,4294967296.,math.inf,math.nan)):
            machines,_=self.compare(*prior.fixture(count=1,time=2.,step=0.,mode=3,base_override=override,pattern=pattern,phase=phase))
            seen.update(machines[0].visits);edges+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen,{source.ENTRY+0x8C})
        self.receipt('packets',full_public_memory_and_call_packets=count,model_FP_edges=edges,
            nonuniform_padding_not_masked=True,retail_reachable_words=len(seen),opaque_providers=True,
            private_frame_still_unmatched=True,not_hardware_or_general_FCSR_acceptance=True)

    def test_04_private_gap_and_retail_sized_overflow_rejected(self):
        memory,case=prior.fixture(pattern=1)
        machines=[prior.Oracle(w,memory,case) for w in (self.harness.truth,*self.images)]
        for machine in machines:
            machine.access_fault=0
            with self.assertRaises(prior.faults.AccessBoundary):machine.run()
        self.assertNotEqual(prior.state(machines[0]),prior.state(machines[1]))
        self.assertEqual(machines[0].r[29]-machines[1].r[29],16)
        form,body,types=list(storage.forms())[-1]
        obj,words,row=storage.measure(self.root,self.root/storage.BUILD,form,body,types)
        self.assertEqual((len(words),row['frame'],row['differences']),(295,336,264))
        with self.assertRaises(ValueError):source.padded_object(self.root,self.root/storage.BUILD,obj,'overflow-rejected')
        self.receipt('private-gap',first_fault_cut=0,aligned_SP_gap=16,frame_fit_words=295,
            frame_fit_overflow_words=7,frame_fit_overlapping_differences=264,installable=False)

    def test_05_native32_aligned_packet_fields(self):
        _,body,types=next(storage.forms())
        header='#include <ultra64.h>\n'+prior.NATIVE_TYPES+'\n'+types+'\n'
        driver_text=prior.NATIVE.replace('r->','r->fields.').replace(
            '__builtin_offsetof(BurstDescriptor2D14,position)','__builtin_offsetof(BurstDescriptor2D14,fields.position)').replace(
            '__builtin_offsetof(BurstDescriptor2D14,byte44)','__builtin_offsetof(BurstDescriptor2D14,fields.byte44)')
        driver=self.out/'native-driver.c';driver.write_text(header+driver_text)
        controls={'equality':body.replace('data->value > 1.0f','data->value >= 1.0f'),
            'signed-counter':body.replace('(s8)data->mode > 0','data->mode > 0').replace('(s8)savedData->mode > 0','savedData->mode > 0'),
            'length':body.replace('sizeof(payload)','(sizeof(payload) - 4)')}
        for opt in ('-O2','-O0'):
            for label,content in (('selected',body),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(header+content+'\n');exe=self.out/('native-'+label+opt)
                built=subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
                self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                result=subprocess.run([str(exe)],capture_output=True)
                if label=='selected':self.assertEqual(result.returncode,0,(opt,result.stderr))
                else:self.assertNotEqual(result.returncode,0,(opt,label))
        self.receipt('native',typed_defined_field_cases_per_profile=960,profiles=['O2','O0'],UBSan=True,
            effective_controls=6,no_native_private_stack_or_padding_claim=True)

    def test_06_production_baseline_unchanged(self):
        from tools.tests import owner_burst_checkpoint as latest
        source.freeze(self.root,self.root/source.BUILD)
        for key,path in source.PATHS.items():
            self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(self.root/source.BUILD/('before-'+key)).read_bytes())
        self.receipt('baseline',entire_ELF_and_all_protected_inputs_unchanged=True,new_guards=0,matching_credit=0)


if __name__=='__main__':unittest.main()
