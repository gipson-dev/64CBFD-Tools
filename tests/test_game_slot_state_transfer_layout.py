"""Qualify explicit complete layout in isolation and through the actual padder."""
from copy import deepcopy
from dataclasses import replace
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_slot_state_transfer_candidates as source
from tools.experiments import game_slot_state_transfer_layout as layout
from tools.experiments import game_slot_state_transfer_value_homes as values
from tools.experiments import game_slot_state_transfer_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import game_slot_state_transfer_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_route_projection_integration as mixed
from tools.tests import test_game_slot_state_transfer_recovery as recovery

BUILD=source.BUILD+'/layout'


def state(model):
    return (model.r,model.f,model.lo,model.memory,model.events,model.calls,model.captures,model.private)


class SlotTransferLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/BUILD
        cls.inputs=source.freeze(cls.root,cls.out)
        cls.values=cls.inputs;cls.cases=list(oracle.cases())
        cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={name:int(name.split('_')[1],16) for entries in cls.moved.values() for _,name in entries}
        cls.words=layout.relocate(cls.normalized,cls.moved,cls.anchors)
        cls.retail=list(struct.unpack_from('>189I',cls.inputs['conker/conker.us.bin'],source.ROM))

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def model(self,words,case,phase=0,entry=source.ENTRY):
        memory,args=oracle.fixture(case,phase)
        return oracle.TransferModel(words,memory,args,case,phase,entry)

    def test_01_complete_words_bindings_and_origin_accounting(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(189,80,100,''))
        self.assertEqual(sorted(layout.origins()),list(range(189)))
        self.assertEqual(len(self.bindings),26);self.assertEqual(len(self.moved),26)
        moved=[(old,new) for new,old in enumerate(layout.origins()) if old*4 in self.bindings and old!=new]
        self.assertEqual(moved,[(143,141),(145,142)])
        guards=layout.private_guards(self.inputs['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        prefix=self.inputs['conker/retail_word_patches.us.csv'];self.assertTrue(guards.startswith(prefix))
        rows=list(csv.DictReader(io.StringIO(guards.decode())))
        target=[r for r in rows if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(target),100);self.assertTrue(all(r['omit']=='false' and not r['insert_after'] for r in target))
        self.receipt('complete-shape',words=189,differences=0,frame=80,guard_rows=100,
            all_source_words_retained_once=True,moved_bindings=moved,production_installed=False)

    def test_02_literal_state_and_independent_public_reference(self):
        count=0
        for case in oracle.cases():
            for phase in (0,8):
                memory,args=oracle.fixture(case,phase);wanted,calls,captures=oracle.reference(memory,args,case)
                a=self.model(self.retail,case,phase).run();b=self.model(self.words,case,phase).run()
                self.assertEqual(state(a),state(b));self.assertEqual(a.r[2],0)
                self.assertEqual((oracle.public(b.memory),b.calls,b.captures),(oracle.public(wanted),calls,captures))
                count+=1
        self.receipt('literal-state',paired_runs=count,GP_FP_LO_private_RAM_and_ordered_events_equal=True,
            independent_reference=True,bounded_providers_only=True)

    def test_03_every_sampled_access_cut_fires_and_has_identical_state(self):
        count=0
        cases=(oracle.Case(),oracle.Case(mutate=1),oracle.Case(flags=0),oracle.Case(mode=0),
            oracle.Case(lookup=0),oracle.Case(level=50),oracle.Case(locked=65535),oracle.Case(destination=5,source=5))
        for case in cases:
            for phase in (0,8):
                a=self.model(self.retail,case,phase).run();b=self.model(self.words,case,phase).run()
                self.assertEqual(a.accesses,b.accesses)
                for cut in range(a.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=self.model(words,case,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('fired-cuts',pairs=count,all_requested_cuts_fired=True,private_and_fault_state_equal=True,
            modeled_access_faults_not_hardware_exceptions=True)

    def test_04_raw_binding_and_recipe_corruptions_are_rejected(self):
        count=0
        for at in (0,76,216,572,755):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown slot-transfer'):layout.normalize(bytes(bad),self.bindings)
            count+=1
        for at in (16,140,572,580):
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown slot-transfer'):layout.normalize(self.raw,bad)
            count+=1
        bad=deepcopy(layout.GP);bad[19]={25:12}
        with patch.object(layout,'GP',bad):
            with self.assertRaisesRegex(ValueError,'Changed slot-transfer layout'):layout.normalize(self.raw,self.bindings)
        order=layout.origins();order[171],order[173]=order[173],order[171]
        with patch.object(layout,'origins',return_value=order):
            with self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
        self.receipt('corruption-controls',fired=count+2,raw_bytes=5,bindings=4,register_recipe=1,schedule=1)

    def test_05_computed_null_equivalence_and_disjoint_actor_fields(self):
        probes=0
        for offset,_ in layout.CHECKS.values():
            for high in (0,0x7FFF0000,0x80000000,0xFFFF0000):
                for low in range(65536):
                    value=high|low
                    self.assertEqual(oracle.u32(value+offset)==0,value==oracle.u32(-offset));probes+=1
            for value in (oracle.u32(-offset-1),oracle.u32(-offset),oracle.u32(-offset+1)):
                self.assertEqual(oracle.u32(value+offset)==0,value==oracle.u32(-offset));probes+=1
        for base in (0,0x800CC2D0,0xFFFFFF00,0xFFFFFFFF):
            byte=oracle.u32(base+0x125);pointer={oracle.u32(base+0x31C+i) for i in range(4)}
            self.assertNotIn(byte,pointer)
        self.receipt('algebra-controls',computed_address_probes=probes,all_u32_exhaustiveness_claimed=False,
            wrapping_add_zero_iff_original_base_is_negative_offset=True,actor125_and_actor31C_disjoint=True)

    def test_06_both_owner_profiles_actual_padder_and_guard_negatives(self):
        same=mixed.candidate.source.neighbor.same_functions
        profiles={}
        for label,normal in (('primary',False),('normal',True)):
            old,diag=source.compile_profile(self.root,self.out,self.inputs[source.SOURCE].decode(),'before-'+label,normal)
            obj,_,row=source.compile_candidate(self.root,self.out,'after-'+label,normal=normal,whole=True)
            self.assertEqual(diag,'');self.assertEqual(row['diagnostics'],'');profiles[label]=obj
            self.assertEqual(same(old,obj,(source.FUNCTION,)),72);self.assertEqual(normalized_pools(old),normalized_pools(obj))
            raw,bindings=source.payload(obj);self.assertEqual(layout.normalize(raw,bindings),(self.normalized,self.moved))
        good=layout.private_guards(self.inputs['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        manifest=self.out/'qualified-guards.csv';manifest.write_bytes(good)
        def padded(path):
            return emit_padded_assembly(profiles['primary'],self.root/'conker/asm/B3020.s',
                function_objects={'func_150891E8':profiles['normal']},word_patches_path=path,filename=source.OWNER)
        assembly=self.out/'qualified-padded.s';assembly.write_text(padded(manifest));obj=assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
            '-o',str(obj),str(assembly)],check=True,capture_output=True)
        image,functions=source.link_owner(self.root,self.out,obj,source.OWNER)
        self.assertEqual(list(struct.unpack_from('>189I',image,functions[source.FUNCTION]['value'])),self.retail)
        self.assertEqual(same(self.root/'conker/build/src/game/generated_B3020.c.o',obj,(source.FUNCTION,)),72)
        reader=csv.DictReader(io.StringIO(good.decode()));rows=list(reader);count=0
        for index in (len(rows)-100,len(rows)-50,len(rows)-1):
            for field in ('expected','expected_relocations'):
                bad=[dict(r) for r in rows];bad[index][field]='0xFFFFFFFF' if field=='expected' else 'R_MIPS_26:'+source.FUNCTION
                text=io.StringIO();writer=csv.DictWriter(text,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
                path=self.out/('bad-%d-%s.csv'%(index,field));path.write_text(text.getvalue())
                with self.assertRaisesRegex(ValueError,'stale word patch' if field=='expected' else 'stale relocations'):padded(path)
                count+=1
        installed=(self.root/source.SOURCE).read_bytes()!=self.inputs[source.SOURCE]
        if installed:integration.audit(self.root,self.root/integration.BUILD)
        else:
            for name,value in self.inputs.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        self.receipt('owner-padder',profiles=2,neighbors_per_profile=72,padded_neighbors=72,guard_negatives_fired=count,
            actual_padder_and_assembler=True,exact_installed_successor_audited=installed,predecessor_unchanged=not installed)

    def test_07_independent_GNU_all_binding_maps_and_code_rebased_execution(self):
        asm=self.inputs['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        original=self.out/'original.s';original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>189I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];mask=0x3FFFFFF if kind=='R_MIPS_26' else 65535
                lines+=['.word 0x%08X'%(word&~mask),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
                '-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        maps=[]
        for n,entry in enumerate((source.ENTRY,0x1621FFF4,0x18FFF000)):
            anchors={}
            for index,(name,value) in enumerate(sorted(self.anchors.items())):
                anchors[name]=value if n==0 else ((0x16010000+n*0x10000+index*0x20) if name.startswith('func_') else
                    (0x80200000+n*0x10000+index*0x1000+(0xFFF4 if index&1 else 0x8004)))
            images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-map-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:756])
            self.assertEqual(*images);self.assertEqual(list(struct.unpack('>189I',images[0])),layout.relocate(self.normalized,self.moved,anchors))
            maps.append(dict(entry=entry,anchors=anchors))
        runs=0
        for entry in (0x1621FFF4,0x18FFF000):
            for case in (oracle.Case(),oracle.Case(mutate=1),oracle.Case(flags=0),oracle.Case(level=50),oracle.Case(mode=0),oracle.Case(lookup=0)):
                for phase in (0,8):
                    a=self.model(self.retail,case,phase,entry).run();b=self.model(self.words,case,phase,entry).run()
                    self.assertEqual(state(a),state(b));runs+=1
        self.receipt('GNU-maps',maps=maps,code_rebased_paired_runs=runs,
            all_binding_maps_independently_assembled=True,rebased_data_and_helper_runtime_claimed=False)

    def test_08_meaningful_value_homes_preserve_bounded_algorithm_but_do_not_fit(self):
        rows=[]
        for name,body in values.candidates():
            _,words,row=source.compile_candidate(self.root,self.root/values.BUILD,name,body)
            self.assertEqual(row['diagnostics'],'');self.assertGreaterEqual(row['differences'],100)
            for case in (oracle.Case(),oracle.Case(mutate=1),oracle.Case(flags=0),oracle.Case(mode=0),oracle.Case(lookup=0),oracle.Case(level=50)):
                memory,args=oracle.fixture(case);wanted,calls,captures=oracle.reference(memory,args,case)
                actual=self.model(words,case).run()
                self.assertEqual((oracle.public(actual.memory),actual.calls,actual.captures),(oracle.public(wanted),calls,captures))
            rows.append(dict(name=name,words=row['words'],frame=row['frame'],differences=row['differences'],raw_SHA256=row['raw_SHA256']))
        self.assertEqual(len(rows),12)
        self.receipt('value-home-screens',screens=rows,bounded_profiles_per_screen=6,screen_mutates_production_source=False)

    def test_09_native32_complete_source_and_effective_controls(self):
        recovery.GameSlotStateTransferRecoveryTests.test_04_native32_named_observables_and_effective_controls(self)

    def test_10_actual_shadow_Make_and_exact_first_or_installed_image(self):
        out=self.root/integration.BUILD;integration.qualify(self.root,out);integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        before=source.freeze(self.root,out)['conker/build/conker.us.elf']
        truth=self.inputs['conker/conker.us.bin'][source.ROM:source.ROM+756]
        expected=integration.predicted_image(before,truth)
        for at in (64,integration.elf_slot_offset(before,source.ENTRY,756)+100,len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Slot-transfer image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=self.inputs[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
