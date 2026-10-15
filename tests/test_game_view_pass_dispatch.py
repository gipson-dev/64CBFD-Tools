"""Selected-view cursor, live-gate, SDK connection and raw-owner qualification."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_view_pass_dispatch as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_pass_dispatch_oracle as model
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools import pad_c_object


class ViewPassDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.record=source.qualify(cls.root,cls.out)
        cls.before=(cls.out/'before-dispatch_owner').read_text()
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>79I',cls.rom,source.ROM))
        legacy=build.body(cls.before,source.FUNCTION)
        cls.old_meta,cls.old_words,cls.old_obj=source.measure(cls.root,cls.out,'legacy',legacy)
        cls.rows=list(itertools.product(model.VIEWS,range(16),range(5)))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def native(self,label,body,rows):
        path=self.out/('native-'+label+'.c')
        path.write_text(model.native_program(body,rows))
        statuses=[]
        for profile in ('O2','O0'):
            binary=path.with_suffix('.'+profile)
            result=subprocess.run(['cc','-m32','-'+profile,'-std=c11','-fno-strict-aliasing','-fno-builtin',
                '-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector',
                '-Wall','-Wextra','-Werror',str(path),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stderr),(0,''))
            statuses.append(subprocess.run([str(binary)],capture_output=True).returncode)
        return statuses

    def test_01_all_words_real_frame_and_diagnostic_scope(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual((self.record['words'],self.record['frame'],self.record['differences']),(79,40,0))
        self.assertEqual((self.old_meta['words'],self.old_meta['frame'],self.old_meta['differences']),(79,48,54))
        def warnings(text):
            lines=text.splitlines()
            return [lines[i+1].strip() for i,line in enumerate(lines) if line.startswith('cfe: Warning 712:')]
        old=warnings(self.old_meta['diagnostics'])
        current=warnings(self.record['diagnostics'])
        self.assertEqual(len(old),5)
        self.assertEqual(current,[line for line in old if 'temp_s0 = func_1501A490' not in line])
        self.assertEqual(self.record['diagnostics'].count('cfe: Warning'),4)
        obj,diagnostics=source.isolated_owner(self.root,self.out,'isolated-selected',source.SELECTED,('-O2','-g3'))
        self.assertEqual(diagnostics,'')
        def signature(path):
            data,functions,relocations=parse_object(path)
            f=functions[source.FUNCTION]
            return data[f['value']:f['value']+f['size']],{at-f['value']:v for at,v in relocations.items()
                if f['value']<=at<f['value']+f['size']}
        self.assertEqual(signature(obj),signature(self.obj))
        self.receipt('shape',words=79,frame=40,raw_differences=0,guards_added=0,
            original_profile_unchanged=True,isolated_target_zero_diagnostics=True,
            existing_neighbor_warnings=4,target_warning_removed=True)

    def test_02_neighbors_pools_and_primary_padder(self):
        a,af,ar=parse_object(self.old_obj)
        b,bf,br=parse_object(self.obj)
        self.assertEqual(set(af),set(bf))
        relative=lambda rel,f:{at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
        for name in set(af)-{source.FUNCTION}:
            x,y=af[name],bf[name]
            self.assertEqual((x['size'],a[x['value']:x['value']+x['size']],relative(ar,x)),
                (y['size'],b[y['value']:y['value']+y['size']],relative(br,y)),name)
        self.assertEqual(normalized_pools(self.old_obj),normalized_pools(self.obj))
        assembly=pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,
            word_patches_path=self.root/source.PATHS['guards'])
        path=self.out/'padded.s'
        path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+assembly)
        obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
        f=functions[source.FUNCTION]
        self.assertEqual(data[f['value']:f['value']+f['size']],struct.pack('>79I',*self.retail))
        self.receipt('neighbors',raw_neighbors=len(af)-1,all_bytes_sizes_relative_relocations_and_pools_fixed=True,
            production_padder_exact=True,no_new_guards=True)

    def test_03_guest_calls_storage_gates_and_private_state(self):
        coverage=set()
        old_public=0
        for view,flags,pattern in self.rows:
            memory=model.fixture(flags,pattern)
            expected,result,calls=model.reference(memory,view,flags,pattern)
            for phase in (0,8):
                instances=[model.DispatchOracle(words,memory,view,flags,pattern,phase).run()
                    for words in (self.retail,self.words)]
                self.assertEqual(model.state(instances[0]),model.state(instances[1]))
                self.assertEqual((model.external(instances[1].memory),instances[1].r[2],instances[1].calls),
                    (model.external(expected),result,calls))
                old=model.DispatchOracle(self.old_words,memory,view,flags,pattern,phase).run()
                self.assertEqual((model.external(old.memory),old.r[2],old.calls),
                    (model.external(expected),result,calls))
                old_public+=1
                coverage.update(instances[0].visits)
        self.assertEqual(len(coverage),79)
        first=self.rows[0]
        memory=model.fixture(first[1],first[2])
        old=model.DispatchOracle(self.old_words,memory,*first).run()
        new=model.DispatchOracle(self.words,memory,*first).run()
        self.assertNotEqual(model.state(old),model.state(new))
        self.receipt('guest',cases=len(self.rows)*2,old_public_agreements=old_public,
            all_79_words_reached=True,selected_full_private_state_exact=True,old_private_frame_differs=True,
            six_ordered_provider_packets_live_globals_and_unsigned_payload_wrap=True)

    def test_04_native_real_body_and_four_returned_controls(self):
        rows=model.native_rows(self.rows)
        self.assertEqual(self.native('selected',source.SELECTED,rows),[0,0])
        negatives=dict(
            viewport=source.SELECTED.replace('((u32)view * 0x180)','((u32)view * 0x100)'),
            query=source.SELECTED.replace('func_1517EFAC(view) != 0','0'),
            mask=source.SELECTED.replace('(D_800D18A0 & (1U << view)) != 0','(D_800D18A0 & (1U << view)) == 0'),
            cached_gate=source.SELECTED.replace('s16 view) {','s16 view) {\n    u8 disabledBefore = D_800BEAC0;').replace(
                'if (D_800BEAC0 != 0)','if (disabledBefore != 0)'))
        controls=[]
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            _,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            witness=None
            for row in rows:
                view,flags,pattern=row
                memory=model.fixture(flags,pattern)
                expected,result,calls=model.reference(memory,view,flags,pattern)
                instance=model.DispatchOracle(words,memory,*row).run()
                if (model.external(instance.memory),instance.r[2],instance.calls)!=(model.external(expected),result,calls):
                    witness=row
                    break
            self.assertIsNotNone(witness,label)
            statuses=self.native(label,body,[witness])
            self.assertEqual(statuses,[2,2])
            controls.append(dict(label=label,witness=witness,statuses=statuses,guest_returned=True))
        self.receipt('native',cases_per_profile=len(rows),profiles=['O2','O0'],zero_diagnostics=True,
            all_128_command_words_six_globals_and_canaries=True,ordered_O32_packets=True,
            explicit_viewport_word_and_pointer_log_bridges=True,defined_variable_shift_domain=True,
            not_native_private_frame_or_full_GPU_renderer=True,controls=controls)

    def test_05_paired_fired_parent_access_prefixes(self):
        count=0
        for view,flags,pattern in itertools.product((0,1,31,0xFFFFFFFF),(0,1,2,4,8),range(5)):
            memory=model.fixture(flags,pattern)
            total=model.DispatchOracle(self.retail,memory,view,flags,pattern).run().accesses
            for cut in range(total):
                instances=[]
                for words in (self.retail,self.words):
                    instance=model.DispatchOracle(words,memory,view,flags,pattern,fault=cut)
                    with self.assertRaises(model.machine.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses,cut)
                    instances.append(instance)
                self.assertEqual(model.state(instances[0]),model.state(instances[1]))
                count+=1
        self.receipt('prefixes',paired_fired_prefixes=count,all_complete_states_match=True,
            modeled_parent_access_boundary_not_hardware_exceptions=True)

    def test_06_actual_select_helper_compilation_and_connections(self):
        owner=(self.out/'before-owner').read_text()
        obj,_=build.compile_owner(self.root,self.out,owner,'select-owner')
        assembly=emit_padded_assembly(obj,self.root/source.PATHS['original'],filename='generated_138520',
            word_patches_path=self.root/source.PATHS['guards'])
        path=self.out/'select-padded.s'
        path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+assembly)
        padded=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
        data,functions=build.link_owner(self.root,self.out,padded,'generated_138520')
        f=functions['func_1510B958']
        words=list(struct.unpack_from('>30I',data,f['value']))
        retail=list(struct.unpack_from('>30I',self.rom,0x138E08))
        self.assertEqual(words,retail)
        before=(self.out/'before-elf').read_bytes()
        at=elf_slot_offset(before,0x1510B958,120)
        self.assertEqual(before[at:at+120],struct.pack('>30I',*retail))
        connected={0x1510B958+i*4:word for i,word in enumerate(words)}
        count=0
        for view,flags,pattern in itertools.product(range(4),range(16),range(5)):
            memory=model.fixture(flags,pattern)
            base=0x30000
            model.put(memory,source.GLOBALS['base'],base)
            for offset,value in ((0x64,0.25),(0x68,0.5),(0x6C,2.0),(0x70,4.0),(0x74,6.0),(0x78,8.0)):
                bits=struct.unpack('>I',struct.pack('>f',value))[0]
                model.put(memory,base+view*384+offset,bits)
            expected,result,calls=model.reference(memory,view,flags,pattern)
            for address,value in zip(model.PLANE,(-1.75,-0.5)):
                model.put(expected,address,struct.unpack('>I',struct.pack('>f',value))[0])
            instances=[model.DispatchOracle(parent,memory,view,flags,pattern,connected=connected).run()
                for parent in (self.retail,self.words)]
            self.assertEqual(model.state(instances[0]),model.state(instances[1]))
            self.assertEqual((model.external(instances[1].memory),instances[1].r[2],instances[1].calls),
                (model.external(expected),result,calls))
            count+=1
        self.receipt('connections',actual_compiled_select_words=30,connections=count,
            actual_plane_outputs_and_parent_call_packets=True,finite_exact_FP_cases=True,
            remaining_render_helpers_opaque_not_hardware_or_full_scene_acceptance=True)

    def test_07_original_assembly_and_three_independent_rebases(self):
        raw,functions,relocations=parse_object(self.obj)
        anchors={('D_%08X'%address):address for address in source.GLOBALS.values()}
        anchors.update({('func_%08X'%address):address for address in source.CALLEES.values()})
        assembly,unresolved=emit_function(raw,functions[source.FUNCTION],relocations,source.FUNCTION,anchors)
        self.assertEqual(unresolved,[])
        original='.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+(self.out/'before-dispatch_original').read_text()
        for label,text in (('selected',assembly),('original',original)):
            path=self.out/(label+'-reloc.s')
            path.write_text(text)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path)],
                capture_output=True,check=True)
        for index,(text_delta,global_delta,call_delta) in enumerate(((0,0,0),(0x5000,0x19C0,0x1000),(-0x7000,0x19E0,0x2000))):
            values={name:value+(global_delta if name.startswith('D_') else call_delta) for name,value in anchors.items()}
            outputs=[]
            for label in ('selected','original'):
                obj=self.out/(label+'-reloc.o')
                script=self.out/('rebase-%d.ld'%index)
                elf=self.out/(label+'-rebase-%d.elf'%index)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+text_delta))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in values.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
                outputs.append(sections(elf)['.text'][1][:316])
            self.assertEqual(outputs[0],outputs[1])
        self.receipt('rebases',independent_pairs=3,original_assembly_reference=True,
            global_signed_low_carry_and_external_call_relocations=True)

    def test_08_bounded_screens_and_exact_forms(self):
        groups=(('screens.json',16),('index-screens.json',6),('shift-screens.json',2))
        exact=[]
        for filename,count in groups:
            path=self.out/filename
            before=path.read_bytes()
            rows=json.loads(before)
            self.assertEqual(len(rows),count)
            exact.extend(row['label'] for row in rows if row['differences']==0)
            self.assertEqual(path.read_bytes(),before)
        self.assertEqual(exact,['unsigned-scale-o2g3','unsigned-shift-o2g3'])
        self.receipt('screen-summary',groups=[count for _,count in groups],total=24,exact=exact,
            private_O1g3_isolated_controls_not_production_profile_changes=True)


if __name__=='__main__':
    unittest.main()
