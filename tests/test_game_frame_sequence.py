"""Direct frame-coordinator match, live callback contracts and bounded cuts."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_sequence as source
from tools.tests import frame_sequence_checkpoint as checkpoint
from tools.tests import game_frame_sequence_oracle as model
from tools.tests import game_frame_sequence_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections


class Join(Exception):pass


class StopCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==0x1501891C:
            self.owner.current_pc=pc
            raise Join
        return super().__getitem__(pc)


class FrameSequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>185I',cls.rom,source.ROM))
        data,functions=source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words=list(struct.unpack_from('>185I',data,functions[source.FUNCTION]['value']))
        read=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p:checkpoint.previous_input(read(p),p,cls.root)):
            model.prepare.ViewMatrixPrepareTests.setUpClass()
        helper=model.prepare.ViewMatrixPrepareTests
        cls.connected=dict(helper.connected)
        cls.connected.update({0x15094EA0+i*4:w for i,w in enumerate(helper.words)})
        cls.helpers=helper

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_direct185_words_frame_40_return_and_fresh_helpers(self):
        self.assertEqual((self.raw,self.words),(self.truth,self.truth))
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['new_guards']),(185,40,0,0))
        self.assertEqual((self.row['target_diagnostics_empty'],self.row['preserved_owner_warnings']),(True,4))
        self.assertEqual(self.helpers.words,list(struct.unpack_from('>40I',self.rom,0xC2350)))
        self.assertEqual(self.helpers.converter,list(struct.unpack_from('>46I',self.rom,0x21D368)))
        self.assertEqual(self.helpers.multiply,list(struct.unpack_from('>78I',self.rom,0xD4EF8)))
        self.assertEqual(self.helpers.sdk_diagnostics,'uld:\nWarning: -Xfullwarn not supported.\n')
        self.assertEqual(self.helpers.kernel_diagnostics,'')
        targets={int(name[5:],16) for bindings in source.RELOCATIONS.values() for kind,name in bindings if kind=='R_MIPS_26'}
        self.assertEqual(targets,set(model.SIGNATURES))

    def test_02_ordered_protocol_live_gates_508_ages_and_complete_state(self):
        count,visits,actions=0,set(),set()
        for views,pattern,disabled,mode,phase in itertools.product((-1,0,1,3),range(4),(0,1,128,255),range(8),(0,8)):
            memory=model.fixture(views,pattern,disabled)
            expected,calls,fired=model.reference(memory,mode,phase)
            models=[model.FrameOracle(words,memory,mode,phase).run() for words in (self.truth,self.raw,self.words)]
            for m in models:
                self.assertEqual(model.public(m.memory),model.public(expected),(views,pattern,disabled,mode,phase))
                self.assertEqual((m.calls,m.frame_actions,m.r[2]),(calls,fired,1))
                self.assertEqual(model.state(m),model.state(models[0]))
            visits.update(models[-1].visits)
            actions.update(fired)
            count+=1
        # Every disabled byte value, not only the ordinary boolean encodings.
        for disabled in range(256):
            memory=model.fixture(-1,disabled%4,disabled)
            expected,calls,fired=model.reference(memory)
            m=model.FrameOracle(self.words,memory).run()
            self.assertEqual((model.public(m.memory),m.calls,m.frame_actions,m.r[2]),(model.public(expected),calls,fired,1))
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+740,4))-visits,set())
        self.assertEqual({mode for _,_,mode in actions},set(range(1,8)))
        self.receipt('guest',three_way_cases=count,disabled_byte_sweep=256,words_covered=185,
            page_records=508,complete_modeled_state=True,fired_effect_sites=len(actions),
            opaque_callbacks_are_ABI_contracts_not_restored_gameplay=True)

    def test_03_every_root_access_fault_prefix_and_byte_wrap(self):
        memory=model.fixture(3,3)
        complete=model.FrameOracle(self.words,memory).run()
        count=0
        for cut in range(complete.root_accesses):
            models=[model.FrameOracle(words,memory,fault=cut) for words in (self.truth,self.words)]
            for m in models:
                with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(m.root_accesses,cut)
            self.assertEqual(model.state(models[0]),model.state(models[1]))
            count+=1
        wraps=[]
        for views in (254,255,256):
            memory=model.fixture(views,3)
            expected,calls,fired=model.reference(memory,8)
            m=model.FrameOracle(self.words,memory,8).run()
            self.assertEqual((model.public(m.memory),m.calls,m.frame_actions,m.r[2]),(model.public(expected),calls,fired,1))
            indices=[a[0] for t,a in m.calls if t==0x15094EA0]
            self.assertEqual(indices,list(range(255)) if views==254 else list(range(256))+[0])
            wraps.append(len(indices))
        # Unchanged positive bounds >=255 do not terminate the byte loop.
        # Stop at its 257th invocation; do not alter or clamp retail code.
        prefixes=0
        for views in (255,256,0x7FFFFFFF):
            memory=model.fixture(views,3)
            target=0x1510FC34 if views==0x7FFFFFFF else 0x15094EA0
            models=[model.FrameOracle(words,memory,target_limit=(target,257)) for words in (self.truth,self.words)]
            for m in models:
                with self.assertRaises(model.CallBoundary):m.run()
            self.assertEqual(model.state(models[0]),model.state(models[1]))
            selected=[args[0] for t,args in models[-1].calls if t==target]
            self.assertEqual(selected,list(range(len(selected))) if views==0x7FFFFFFF else list(range(256))+[0])
            prefixes+=1
        self.receipt('faults',every_root_access_prefixes=count,wrapping_case_invocations=wraps,
            bounded_nonterminating_or_large_prefixes=prefixes,portable_C_fault_or_hardware_claim=False)

    def test_04_real_matrix_preparation_and_original_upstream_success_gate(self):
        count,invocations=0,0
        for views,pattern,mode,phase in itertools.product((-1,0,1,3),range(4),range(8),(0,8)):
            memory=model.fixture(views,pattern,pattern&1)
            expected,calls,fired=model.reference(memory,mode,phase,connected=True)
            models=[model.FrameOracle(words,memory,mode,phase,connected=self.connected).run() for words in (self.truth,self.words)]
            for m in models:
                self.assertEqual((model.public(m.memory),m.calls,m.frame_actions,m.r[2]),(model.public(expected),calls,fired,1))
            self.assertEqual(model.state(models[0]),model.state(models[1]))
            count+=1
            invocations+=sum(t==0x15094EA0 for t,_ in calls)
        before=(self.out/'before-elf').read_bytes()
        upstream=next(r for r in symbol_rows(before) if r[1]=='func_1501878C')
        self.assertEqual(upstream[2][1:3],(0x1501878C,12))
        cut=list(struct.unpack_from('>8I',self.rom,source.ROM+0x150188FC-source.ENTRY))
        for disabled in (0,1,128,255):
            memory=model.fixture(-1,2,disabled)
            models=[]
            for words in (self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                m=model.FrameOracle(cut,memory,entry=0x150188FC,connected=connected)
                m.code=StopCode(m.code,m)
                with self.assertRaises(Join):m.run()
                self.assertEqual(m.r[17],0x800C0000)
                if not disabled:self.assertEqual(m.r[2],1)
                self.assertEqual(sum(t==source.ENTRY for t,_ in m.calls),int(not disabled))
                models.append(m)
            self.assertEqual(model.state(models[0]),model.state(models[1]))
        self.receipt('connected',cases=count,preparation_invocations=invocations,real_helper_words=[40,46,78],
            upstream_original_cut_words=8,upstream_join='0x1501891C',installed_upstream_still_12_byte_stub=True,
            whole_upstream_or_gameplay_parity_not_claimed=True)

    def test_05_native32_actual_source_and_effective_controls(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native.program())
        exits={}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (name,'-O2',body,False) for name,body in native.controls().items()]:
            if not valid:self.assertNotEqual(body,source.SELECTED)
            path=self.out/('native-body-'+label+'.c')
            path.write_text(native.HEADER+body)
            exe=self.out/('native-'+label)
            result=subprocess.run([*native_command(opt,valid),'-mstackrealign','-fno-strict-aliasing',str(path),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30)
            self.assertIn(result.returncode,(0,) if valid else tuple(range(21,28)),(label,result.stderr))
            exits[label]=result.returncode
        self.receipt('native',cases_per_selected=131,separate_units_native32_O2_O0_UBSan=True,
            python_expected_callback_packets_and_ages=True,fixture_storage_binding_not_shared_header_redefinition=True,exits=exits)

    def test_06_neighbors_screens_warnings_and_frozen_negative_controls(self):
        before=(self.out/'before-dispatch_owner').read_text()
        obj,diagnostics=source.build.compile_owner(self.root,self.out,before,'neighbor-before')
        self.assertEqual(source.warning_sites(before,diagnostics),source.warning_sites(source.recovered_owner(before),self.row['diagnostics']))
        old,new=parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(old[1]),set(new[1]))
        binding=lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value']<=a<f['value']+f['size']}
        for name,f in old[1].items():
            if name==source.FUNCTION:continue
            g=new[1][name]
            self.assertEqual(old[0][f['value']:f['value']+f['size']],new[0][g['value']:g['value']+g['size']],name)
            self.assertEqual(binding(old,f),binding(new,g),name)
        self.assertEqual(len(old[1])-1,15)
        for label,body in source.forms():
            row=json.loads((self.out/(label+'.json')).read_text())
            self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(before,body))
            t,f,r=parse_object(self.out/(label+'.o'))
            f=f[source.FUNCTION]
            self.assertEqual(hashlib.sha256(t[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            self.assertEqual(binding((t,{},r),f),{int(a):[tuple(v) for v in values] for a,values in row['relocations'].items()})
            data=sections(self.out/(label+'.elf'))['.text'][1]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            differences=sum(a!=b for a,b in zip(words,self.truth))+abs(len(words)-185)
            self.assertEqual((len(words),(-words[0])&65535,differences),(row['words'],row['frame'],row['differences']))
            self.assertEqual(source.warning_sites(source.recovered_owner(before,body),row['diagnostics']),source.warning_sites(before,diagnostics))
            self.assertFalse(row['pools'])
        text,functions,rel=new
        f=functions[source.FUNCTION]
        for i in range(185):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in source.RELOCATIONS:
            bad=dict(rel);bad[f['value']+offset]=[('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        for diagnostic in ('',self.row['diagnostics']+'\n',self.row['diagnostics'].replace('Warning 712','Warning 713',1),
                self.row['diagnostics'].replace('illegal combination','another combination',1)):
            with self.assertRaises(ValueError):source.warning_sites(source.recovered_owner(before),diagnostic)
        read=Path.read_bytes
        for key in source.PATHS:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaisesRegex((ValueError,AssertionError),'fixture'):source.freeze(self.root,self.out)

    def test_07_symbol_carries_addends_and_complete_first_prediction(self):
        text,functions,rel=parse_object(self.obj)
        f=functions[source.FUNCTION]
        raw=list(struct.unpack_from('>185I',text,f['value']))
        names=sorted({n for rows in source.RELOCATIONS.values() for _,n in rows})
        for ordinal,table in enumerate((0x90008010,0x9000FFF0)):
            anchors={n:(0x15120000+i*0x40 if n.startswith('func_') else 0x90020000+i*0x20000+(0x7FF0 if i%2 else 0xFFF0)) for i,n in enumerate(names)}
            anchors['D_80043B40']=table
            assembly,unresolved=emit_function(text,f,rel,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            obj=self.helpers.assemble(assembly,'frame-rebase-'+str(ordinal))
            script=self.out/('rebase-%d.ld'%ordinal)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
            elf=script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
            actual=list(struct.unpack_from('>185I',sections(elf)['.text'][1]))
            expected=raw.copy()
            for offset,bindings in source.RELOCATIONS.items():
                kind,name=bindings[0];value=anchors[name]
                if offset in (648,652):value+=0xFE0
                if kind=='R_MIPS_26':expected[offset//4]=(raw[offset//4]&0xFC000000)|((value>>2)&0x03FFFFFF)
                else:expected[offset//4]=(raw[offset//4]&0xFFFF0000)|(((value+0x8000)>>16)&65535 if kind=='R_MIPS_HI16' else value&65535)
            self.assertEqual(actual,expected)
        row=source.prelink_prediction(self.root,self.out)
        self.assertEqual(row['after'],checkpoint.AFTER)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_serialization_bytes'],row['metadata_exclusions']),(516,16,0))
        slot=(self.out/'predicted-slot.bin').read_bytes()
        for i in range(185):
            bad=bytearray(slot);bad[i*4]^=1
            with self.assertRaises(ValueError):source.slot_expected_image((self.out/'before-elf').read_bytes(),bytes(bad))
        structural=source.slot_expected_image((self.out/'before-elf').read_bytes(),slot)
        for at in (0,2775472,3059951,2927376,3184631):
            bad=bytearray(structural);bad[at]^=1
            with self.assertRaises(ValueError):source.serialize_metadata(bytes(bad))


if __name__=='__main__':unittest.main()
