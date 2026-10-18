"""Native32, real Make/padder, whole-image prediction and connected caller gates."""
import csv
from contextlib import nullcontext
import io
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_integration as source
from tools.experiments import game_route_projection_native as native
from tools.tests import test_game_route_projection_setup as guest
from tools.tests.test_game_route_projection_lifetime_fit import cases
from tools import pad_generated_object as padder


class AllAccessOracle(guest.ProjectionOracle):
    def __init__(self,*args,**kwargs):
        self.access_pcs={};super().__init__(*args,**kwargs)

    def access(self):
        before=self.all_accesses
        super().access()
        if self.all_accesses>before:
            pc=self.current_pc;self.access_pcs[pc]=self.access_pcs.get(pc,0)+1


class CallerOracle(AllAccessOracle):
    def __init__(self,words,memory,connected,phase):
        self.trace=[];self.access_pcs={}
        guest.base.PointProjectionOracle.__init__(self,words,memory,(),[],phase,0x15087CC0,connected)

    def record_call(self,target):
        if target==source.ENTRY:self.calls.append((target,self.arguments(2)))
        else:super().record_call(target)


class ProjectionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.installed=source.raw_read(cls.root/'conker/src/game/generated_B3020.c')==source.expected_inputs(cls.root,cls.out)['conker/src/game/generated_B3020.c']
        with source.historical_view(cls.root,cls.out) if cls.installed else nullcontext():
            cls.primary,cls.override,cls.padded,cls.row=source.qualify(cls.root,cls.out)
            cls.prediction=source.predict(cls.root,cls.out);cls.make=source.make_shadow(cls.root,cls.out)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        data,functions=source.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words=list(struct.unpack_from('>321I',data,functions[source.FUNCTION]['value']))
        if cls.installed:
            image=source.raw_read(cls.root/'conker/build/conker.us.elf')
            cls.words=list(struct.unpack_from('>321I',image,source.elf_slot_offset(image,source.ENTRY,1284)))
            for entry,count in guest.HELPERS.items():
                offset=source.elf_slot_offset(image,entry,count*4)
                if image[offset:offset+count*4]!=cls.rom[entry-0x14FD2B50:entry-0x14FD2B50+count*4]:
                    raise ValueError('Installed projection helper differs from retail')
        cls.truth=list(struct.unpack_from('>321I',cls.rom,source.ROM));cls.helpers={}
        for entry,count in guest.HELPERS.items():
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,cls.rom,entry-0x14FD2B50)))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_actual_profiles_padding_and_first_prediction(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual((self.row['raw_words'],self.row['primary_target_words'],self.row['no_unroll_neighbors']),(335,246,72))
        self.assertEqual((self.row['guards'],self.row['omitted'],self.row['bindings']),(335,14,18))
        self.assertEqual(self.prediction['changed_bytes'],974)
        self.assertEqual(self.prediction['elf_sha256'],'7eb93e57d28fed26f58b58751c8884b3478f1db71b3fc8b2766022c7d75d27c6')
        self.assertEqual(self.make['actual_expanded_Make_commands'],7)
        self.assertTrue(self.make['original_four_GLOBAL_ASM_bodies_preserved'])

    def test_02_native32_actual_C_and_effective_controls(self):
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():row=native.qualify(self.root,self.out)
        self.assertEqual((row['cases_per_positive_build'],row['effective_controls']),(8225,6))
        self.assertEqual([row['exits'][p] for p in ('O0','O2','O2-UBSAN')],[0,0,0])
        for p in native.controls():self.assertIn(row['exits'][p],(21,22,23))

    def test_03_complete_guard_prefix_omissions_and_relocations(self):
        with source.historical_view(self.root,self.out) if self.installed else nullcontext():values=source.freeze(self.root,self.out)
        before=values['conker/retail_word_patches.us.csv']
        raw,bindings=source.candidate.checked(self.override)
        actual=(self.out/'qualified-guards.csv').read_bytes()
        self.assertTrue(actual.startswith(before));self.assertEqual(actual,source.recovered_guards(before,raw,bindings))
        rows=list(csv.DictReader(io.StringIO(actual.decode())));rows=[r for r in rows if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual([int(r['offset'],0) for r in rows],list(range(0,1340,4)))
        self.assertEqual(sum(r['omit']=='true' for r in rows),14)
        self.assertTrue(all(r['expected_relocations'] and r['replacement_relocations'] for r in rows))
        self.assertEqual(sum(r['replacement_relocations']!='-' for r in rows),18)
        with self.assertRaisesRegex(ValueError,'stale word patch'):
            padder.emit_padded_assembly(self.primary,self.root/'conker/asm/B3020.s',filename=source.OWNER,
                word_patches_path=self.out/'qualified-guards.csv')
        with self.assertRaisesRegex(ValueError,'Existing projection guards'):source.recovered_guards(actual,raw,bindings)

    def test_04_every_word_and_binding_is_guarded_in_actual_padder(self):
        primary=padder.parse_object(self.primary);text,functions,relocations=padder.parse_object(self.override)
        f=functions[source.FUNCTION];patches=padder.load_word_patches(self.out/'qualified-guards.csv',source.OWNER)
        checks=0
        def emit(changed):
            def parse(path):return changed if Path(path)==self.override else primary
            with patch.object(padder,'parse_object',side_effect=parse),patch.object(padder,'load_word_patches',return_value=patches):
                padder.emit_padded_assembly(self.primary,self.root/'conker/asm/B3020.s',function_objects={source.FUNCTION:self.override},
                    filename=source.OWNER,word_patches_path=self.out/'qualified-guards.csv')
        for index in range(335):
            bad=bytearray(text);bad[f['value']+index*4]^=1
            with self.assertRaisesRegex(ValueError,'stale word patch'):emit((bytes(bad),functions,relocations))
            checks+=1
        selected=[at for at in relocations if f['value']<=at<f['value']+f['size']]
        for at in selected:
            bad=dict(relocations);bad.pop(at)
            with self.assertRaisesRegex(ValueError,'stale relocations'):emit((text,functions,bad))
            checks+=1
        self.assertEqual((len(selected),checks),(18,353))
        self.receipt('padder-controls',parent_words=335,removed_bindings=18,checks=checks,all_effective=True)

    def test_05_normalized_guest_complete_memory_and_call_contract(self):
        total=0
        for memory,args in cases():
            expected,calls,_=guest.reference(memory,args);phase=(total&1)*8
            a,b=[AllAccessOracle(w,memory,args,self.helpers,phase).run() for w in (self.words,self.truth)]
            self.assertEqual((a.memory,a.r,a.f,a.calls),(b.memory,b.r,b.f,b.calls))
            self.assertEqual((guest.public(a.memory),a.calls),(guest.public(expected),calls));total+=1
        self.assertEqual(total,575);self.receipt('normalized-guest',paired_cases=total,complete_memories_registers_FP_and_calls_equal=True)

    def test_06_fired_nonnull_fault_prefixes_include_actual_helpers(self):
        complete=prefixes=child_accesses=0
        for state,position,alias,phase in itertools.product((2,3),(0,3),(0,1),(0,8)):
            memory,args=guest.fixture(state,position,alias=alias)
            plain=guest.ProjectionOracle(self.truth,memory,args,self.helpers,phase).run()
            full=AllAccessOracle(self.truth,memory,args,self.helpers,phase).run()
            self.assertGreater(len(full.calls),0);self.assertEqual(full.all_accesses,plain.all_accesses)
            observed=sum(n for pc,n in full.access_pcs.items() if any(start<=pc<start+words*4 for start,words in guest.HELPERS.items()))
            self.assertGreater(observed,0);child_accesses+=observed
            for cut in range(full.all_accesses):
                machines=[]
                for words in (self.words,self.truth):
                    m=AllAccessOracle(words,memory,args,self.helpers,phase);m.access_fault=cut
                    with self.assertRaises(guest.base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,cut);machines.append(m)
                a,b=machines
                self.assertEqual((a.memory,a.r,a.f,a.calls,a.current_pc,a.delay_of),
                    (b.memory,b.r,b.f,b.calls,b.current_pc,b.delay_of));prefixes+=1
            complete+=1
        self.assertEqual((complete,prefixes,child_accesses),(16,2148,780))
        self.receipt('normalized-nonnull-faults',complete_cases=complete,paired_fired_prefixes=prefixes,
            helper_accesses_included=child_accesses,complete_memory_GP_FP_calls_PC_delay_equal=True,
            synthetic_access_boundary_not_hardware_exception=True)

    def test_07_retail_direct_caller_arguments_and_ignored_return(self):
        with (self.root/'conker/retail_layout.us.txt').open() as stream:rows=list(csv.DictReader(stream))
        sites=[]
        opcode=(3<<26)|((source.ENTRY>>2)&0x3FFFFFF)
        for row in rows:
            if row['section']!='game':continue
            start,end=int(row['address'],0),int(row['end'],0);at=start-0x14FD2B50
            for offset in range(0,end-start,4):
                if struct.unpack_from('>I',self.rom,at+offset)[0]==opcode:sites.append((row['function'],start+offset))
        self.assertEqual(sites,[('func_15087CC0',0x15087D4C)])
        caller=list(struct.unpack_from('>67I',self.rom,0x15087CC0-0x14FD2B50))
        self.assertEqual(caller[(0x15087D54-0x15087CC0)//4],0x3C02800D)
        high=caller[(0x15087D10-0x15087CC0)//4]&65535;low=caller[(0x15087D14-0x15087CC0)//4]&65535
        actor_base=((high<<16)+(low^32768)-32768)&0xFFFFFFFF
        self.assertEqual(actor_base,0x800CC2D0)
        count=0
        for state,slot,flag,phase in itertools.product((2,3),(0,1,127,-1,-128),(0,64),(0,8)):
            memory,args=guest.fixture(state,1,flag=flag);actor=(actor_base+slot*0x32C)&0xFFFFFFFF
            for i in range(0x400):memory[actor+i]=memory[guest.ACTOR+i]
            guest.put(memory,guest.RECORD+0x31,slot,1);guest.put(memory,0x800872A0,guest.RECORD)
            guest.put(memory,0x800D2398,1,1);guest.put(memory,0x800D23A9,0xA5,1)
            expected=dict(memory);guest.put(expected,0x800D23A9,0,1)
            expected,calls,_=guest.reference(expected,(guest.RECORD,actor));machines=[]
            for words in (self.words,self.truth):
                connected=dict(self.helpers);connected.update(zip(range(source.ENTRY,source.ENTRY+1284,4),words))
                m=CallerOracle(caller,memory,connected,phase).run();machines.append(m)
                self.assertEqual(m.calls,[(source.ENTRY,(guest.RECORD,actor)),*calls]);self.assertEqual(m.r[2],1)
                self.assertEqual(guest.public(m.memory),guest.public(expected))
            a,b=machines;self.assertEqual((a.memory,a.r,a.f),(b.memory,b.r,b.f));count+=1
        self.assertEqual(count,40)
        self.receipt('connected-retail-caller',direct_sites=sites,paired_cases=count,record_stride=132,actor_stride=812,
            actor_base='0x800CC2D0',signed_actor_slot=True,arguments_correct=True,V0_immediately_overwritten=True,caller_itself_not_installed=True)

    def test_08_successor_and_live_stage_controls_fail_closed(self):
        expected=source.expected_inputs(self.root,self.out)
        self.assertEqual(source.verify(self.root,self.out),'after' if self.installed else 'before')
        original_read=source.raw_read
        for path,name in source.SUCCESSOR_FILES.items():
            target=self.out/name
            def corrupt(p,*args,**kwargs):
                data=original_read(p,*args,**kwargs);return data+b'\0' if p==target else data
            with patch.object(source,'raw_read',side_effect=corrupt),self.assertRaisesRegex(ValueError,'Changed first projection successor'):
                source.expected_inputs(self.root,self.out)
            checkpoint=source.candidate.source.checkpoint;original=checkpoint.raw_read
            other=(self.out/('before-%02d'%list(source.INPUTS).index(path))).read_bytes() if self.installed else expected[path]
            def mixed(p,*args,**kwargs):return other if p==self.root/path else original(p,*args,**kwargs)
            with patch.object(checkpoint,'raw_read',side_effect=mixed),self.assertRaisesRegex(ValueError,'Mixed or uninstalled'):
                source.verify(self.root,self.out)
        self.receipt('successor-controls',corrupted_successors=4,mixed_live_stages=4,all_effective=True)

    def test_09_installed_linked_audit_when_present(self):
        if not self.installed:
            self.assertEqual(source.verify(self.root,self.out),'before');return
        row=source.audit(self.root,self.out)
        self.assertEqual(row['changed_ELF_bytes'],974);self.assertEqual(row['functions'],6057)


if __name__=='__main__':unittest.main()
