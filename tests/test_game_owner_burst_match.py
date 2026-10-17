"""Full burst behavior and retail-normalized private state, never partial C credit."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_owner_burst_match as target
from tools.tests import test_game_owner_burst_emitter as prior
from tools.tests import test_game_owner_burst_literal_and_allocation as research
from tools.tests.test_game_projected_packet_draw import native_command
from tools import pad_generated_object as padder


class BurstMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/target.BUILD
        cls.obj,cls.padded,cls.images,cls.row=target.qualify(cls.root,cls.out)
        prior.OwnerBurstRecoveryTests.setUpClass()
        cls.harness=prior.OwnerBurstRecoveryTests('test_02_full_uniform_stack_public_protocol')

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_shape_closed_groups_and_effective_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(288,336,20))
        self.assertEqual(self.images[1],self.harness.truth)
        self.assertEqual((self.row['unchanged_raw_neighbors'],self.row['unchanged_padded_neighbors']),(11,11))
        bindings=target.source.parts(self.obj)[1];self.assertEqual(len(bindings),25)
        target.prove_groups(self.images[0],self.harness.truth,bindings)
        loaded=padder.load_word_patches(self.out/'expected-guards.csv',target.OWNER);count=0
        for offset,_,_ in target.GUARDS:
            wrong=copy.deepcopy(loaded);wrong[(target.FUNCTION,offset)]['expected']^=1
            with patch.object(padder,'load_word_patches',return_value=wrong):
                with self.assertRaisesRegex(ValueError,'stale word patch'):
                    target.literal.padded_object(self.root,self.out,self.obj,'stale-rejected',self.out/'expected-guards.csv')
            count+=1
        wrong=list(self.images[0]);wrong[0x80//4]^=1<<18
        guards=tuple((o,wrong[o//4],b) for o,_,b in target.GUARDS)
        with patch.object(target,'GUARDS',guards):
            with self.assertRaisesRegex(ValueError,'cycle is not closed'):target.prove_groups(wrong,self.harness.truth,bindings)
        count+=1
        wrong=list(self.images[0]);a,b=0x1FC//4,0x20C//4;wrong[a],wrong[b]=wrong[b],wrong[a]
        guards=tuple((o,wrong[o//4],b) for o,_,b in target.GUARDS)
        with patch.object(target,'GUARDS',guards):
            with self.assertRaisesRegex(ValueError,'dependency order changed'):target.prove_groups(wrong,self.harness.truth,bindings)
        count+=1
        self.receipt('shape',words=288,frame=336,guarded_exact=True,raw_differences=20,
            unguarded_words=268,new_guards=20,effective_controls=count,groups=self.row['groups'])

    def test_02_complete_public_packets_both_initial_scale_values(self):
        research.BurstLiteralTests.test_03_complete_public_packets_with_actual_scale(self)
        packets=json.loads((self.out/'packets-both-values.json').read_text())
        for record in (packets['synthetic'],packets['retail']):
            self.assertTrue(record.pop('private_frame_still_unmatched'))
            record['private_state_qualified_separately']=True
        self.receipt('packets-both-values',**packets)
        self.receipt('packets',**packets['retail'])

    def test_03_complete_private_and_all_fault_prefixes(self):
        specifications=(dict(gate=1),dict(gate=2),dict(gate=3),dict(gate=4),
            dict(state=1,previous=0,time=1.),dict(count=1,time=2.,basis=False),
            dict(state=1,previous=1,time=3.5,allocate=False),
            dict(state=1,previous=1,time=3.5,mode=2),dict(state=1,previous=1,time=3.5,mode=4))
        prefixes=0;completed=0
        for pattern,phase,spec in itertools.product((0,1),(0,8),specifications):
            memory,case=prior.fixture(pattern=pattern,phase=phase,**spec)
            machines=[prior.Oracle(w,memory,case).run() for w in (self.harness.truth,self.images[1])]
            self.assertEqual(prior.state(machines[0]),prior.state(machines[1]));completed+=1
            for cut in range(machines[0].all_accesses):
                pair=[prior.Oracle(w,memory,case) for w in (self.harness.truth,self.images[1])]
                for machine in pair:
                    machine.access_fault=cut
                    with self.assertRaises(prior.faults.AccessBoundary):machine.run()
                self.assertEqual(prior.state(pair[0]),prior.state(pair[1]));prefixes+=1
        memory,case=prior.fixture(state=1,previous=1,pattern=1)
        reference=prior.Oracle(self.harness.truth,memory,case).run();first=None
        for cut in range(reference.all_accesses):
            pair=[prior.Oracle(w,memory,case) for w in (self.harness.truth,self.images[0])]
            for machine in pair:
                machine.access_fault=cut
                with self.assertRaises(prior.faults.AccessBoundary):machine.run()
            if prior.state(pair[0])!=prior.state(pair[1]):first=cut;break
        self.assertIsNotNone(first);self.assertGreater(first,0)
        self.receipt('private',completed_cases=completed,all_memory_fault_prefixes=prefixes,
            raw_first_mismatch=first,guarded_first_cut_also_matches=True,full_register_stack_and_call_state=True,
            no_portable_C_fault_or_hardware_claim=True)

    def test_04_two_carry_rebases_and_full_protocol(self):
        count=0
        for group,entry in enumerate((0x15207FF0,0x15610000)):
            symbols={n:(0x80300000+group*0x100000+i*0x10000+(0x7FFC if (i+group)%2 else 0x8004))
                if v&0x80000000 else 0x15300000+group*0x100000+i*0x1000 for i,(n,v) in enumerate(target.source.SYMBOLS.items())}
            raw,_=target.literal.linked(self.root,self.out,self.obj,'rebase-'+str(group),entry,symbols,symbols['D_800A196C'])
            guarded=target.source.linked(self.root,self.out,self.padded,'guarded-rebase-'+str(group),entry,symbols)
            target.prove_groups(raw,guarded,target.source.parts(self.obj)[1])
            for gate,state,mode,pattern,phase,value in itertools.product((0,1,3),(0,1),(0,2),(0,1),(0,8),(1.25,58.14)):
                memory,case=prior.fixture(gate,state,previous=state,mode=mode,pattern=pattern,phase=phase,symbols=symbols)
                prior.word(memory,symbols['D_800A196C'],value)
                self.harness.compare(memory,case,images=[raw,guarded],entry=entry);count+=1
        self.receipt('rebases',links=2,complete_protocol_cases=count,raw_guard_groups_closed=True,signed_HI16_carries=True)

    def test_05_exact_source_native32_and_effective_controls(self):
        _,body,types=target.form();header='#include <ultra64.h>\n'+prior.NATIVE_TYPES+'\n'+types+'\n'
        driver_text=prior.NATIVE.replace('1.25f','58.14f').replace('r->','r->fields.').replace(
            '__builtin_offsetof(BurstDescriptor2D14,position)','__builtin_offsetof(BurstDescriptor2D14,fields.position)').replace(
            '__builtin_offsetof(BurstDescriptor2D14,byte44)','__builtin_offsetof(BurstDescriptor2D14,fields.byte44)')
        driver=self.out/'native-driver.c';driver.write_text(header+driver_text)
        controls={'equality':body.replace('savedData->value > 1.0f','savedData->value >= 1.0f'),
            'signed-counter':body.replace('(s8)savedData->mode > 0','savedData->mode > 0'),
            'length':body.replace('sizeof(payload)','(sizeof(payload) - 4)'),
            'literal':body.replace('58.14f','58.15f')}
        self.assertTrue(all(text!=body for text in controls.values()))
        for opt in ('-O2','-O0'):
            for label,text in (('selected',body),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(header+text+'\n');exe=self.out/('native-'+label+opt)
                result=subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                result=subprocess.run([str(exe)],capture_output=True)
                if label=='selected':self.assertEqual(result.returncode,0,(opt,result.stderr))
                else:self.assertNotEqual(result.returncode,0,(opt,label))
        self.receipt('native',typed_defined_field_cases_per_profile=960,profiles=['O2','O0'],UBSan=True,
            effective_controls=8,retail_literal_value=True,no_native_padding_or_guest_fault_claim=True)

    def test_06_callback_and_preserved_inputs(self):
        target.source.freeze(self.root,self.root/target.source.BUILD)
        rom=(self.out/'before-retail_rom').read_bytes()
        self.assertEqual(struct.unpack_from('>I',rom,0x22F118)[0],target.ENTRY)
        self.receipt('inputs',protected_entries=len(target.source.PATHS),callback_slot=0x8008A658,
            full_dispatcher_and_provider_runtime_still_unqualified=True)

    def test_07_complete_first_image_and_checkpoint_controls(self):
        from tools.experiments import game_owner_burst_installation as install
        from tools.tests import owner_burst_checkpoint as checkpoint
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        from tools.match_progress import load_elf_functions
        from tools.check_game_data_layout import audit_layout
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual({k:hashlib.sha256(v).hexdigest() for k,v in expected.items()},checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        before_guards=(out/'before-guards').read_bytes()
        self.assertTrue(expected['guards'].startswith(before_guards))
        self.assertEqual(expected['guards'][len(before_guards):].count(b'\n'),20)
        if not (out/'after-elf').exists():self.receipt('installation',installed=False,complete_first_prediction_verified=True);return
        original=Path.read_bytes;count=0
        for key,value in expected.items():
            self.assertEqual((self.root/target.PATHS[key]).read_bytes(),value)
            self.assertEqual(checkpoint.previous_input(value,target.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                path=out/(stage+'-'+key);bad=bytearray(path.read_bytes());bad[len(bad)//2]^=1
                with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else original(p)):
                    with self.assertRaisesRegex(AssertionError,'Changed burst checkpoint fixture'):
                        checkpoint.previous_input(value,target.PATHS[key],self.root)
                count+=1
        before,_,old_addresses=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        after,_,new_addresses=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(old_addresses,new_addresses);self.assertEqual(set(before),set(after))
        self.assertEqual([n for n in before if before[n]!=after[n]],[target.FUNCTION])
        old_symbols=[(n,(f[1],target.SIZE if n==target.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows((out/'before-elf').read_bytes())]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        owned={target.PATHS[k] for k in expected}
        for key,path in target.PATHS.items():
            if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        data=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('installation',installed=True,whole_first_ELF_exact=True,metadata_exclusions=0,
            compared_bodies=len(before),only_target_changed=True,all_addresses_preserved=True,
            checkpoint_members=len(expected),effective_checkpoint_controls=count,game_data=data)


if __name__=='__main__':unittest.main()
