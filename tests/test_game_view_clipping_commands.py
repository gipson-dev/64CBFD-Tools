"""Whole clipping-plane command and queue qualification."""
from pathlib import Path
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_clipping_commands as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function,nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import game_view_clipping_oracle as model
from tools.tests import game_view_clipping_native as native
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import view_clipping_checkpoint as checkpoint

SERIALIZATION=()


def expected_image(before,rom):
    expected=bytearray(before)
    for name,entry,address,count in source.TARGETS:
        at=elf_slot_offset(before,entry,count*4)
        expected[at:at+count*4]=rom[address:address+count*4]
        rows=[(at,fields) for at,label,fields,_ in machine.symbol_rows(before) if label==name]
        assert len(rows)==1 and rows[0][1][1:]==(entry,12,18,0,5)
        struct.pack_into('>I',expected,rows[0][0]+8,count*4)
    with patch.object(machine,'SERIALIZATION',SERIALIZATION):
        machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class ViewClippingCommandsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        source.freeze(cls.root,cls.out)
        cls.before = (cls.out/'before-owner').read_text()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.obj,cls.diagnostics = build.compile_owner(cls.root,cls.out,source.recover(cls.before),'qualified')
        cls.raw_data,cls.raw_functions=build.link_owner(cls.root,cls.out,cls.obj,source.OWNER)
        cls.guard_bytes=source.guard_manifest((cls.out/'before-guards').read_bytes())
        cls.guards=cls.out/'qualified-guards.csv'
        cls.guards.write_bytes(cls.guard_bytes)
        padded=pad_c_object.emit_padded_assembly(cls.obj,cls.root/source.PATHS['layout'],source.OWNER,word_patches_path=cls.guards)
        cls.primary=cls.assemble(padded,'primary')
        cls.data,cls.functions=build.link_owner(cls.root,cls.out,cls.primary,source.OWNER)
        cls.words,cls.retail,cls.raw = {},{},{}
        for name,entry,rom,count in source.TARGETS:
            info=cls.functions[name]
            cls.words[entry]=list(struct.unpack_from('>%dI' % count,cls.data,info['value']))
            old=cls.raw_functions[name]
            cls.raw[entry]=list(struct.unpack_from('>%dI' % (old['size']//4),cls.raw_data,old['value']))
            cls.retail[entry]=list(struct.unpack_from('>%dI' % count,cls.rom,rom))

    @classmethod
    def assemble(cls,text,label):
        path=cls.out/(label+'.s')
        path.write_text('.include "'+str(cls.root/'conker/include/asm_processor_prelude.inc')+'"\n'+text)
        obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        return obj

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_complete_retail_words_both_padders_and_FP_roles(self):
        self.assertEqual(self.diagnostics,'')
        self.assertEqual(self.raw[model.COMMAND],self.retail[model.COMMAND])
        self.assertEqual((len(self.raw[model.QUEUE]),self.raw[model.QUEUE][0]),(55,0x27BDFFC0))
        self.assertEqual([(i*4,a,b) for i,(a,b) in enumerate(zip(self.raw[model.QUEUE],self.retail[model.QUEUE])) if a!=b],list(source.GUARDS))
        for _,expected,replacement in source.GUARDS:
            mask=31<<16
            if expected>>26==17:
                mask|=31<<11
            self.assertEqual(expected&~mask,replacement&~mask)
        for name,entry,_,count in source.TARGETS:
            self.assertEqual(self.raw_functions[name]['size'],count*4)
            self.assertEqual(self.words[entry],self.retail[entry])
        assembly=emit_padded_assembly(self.obj,self.root/source.PATHS['original'],filename=source.OWNER,word_patches_path=self.guards)
        data,functions=build.link_owner(self.root,self.out,self.assemble(assembly,'generated'),source.OWNER)
        for name,entry,_,count in source.TARGETS:
            self.assertEqual(data[functions[name]['value']:functions[name]['value']+count*4],struct.pack('>%dI'%count,*self.retail[entry]))
        screens=json.loads((self.out/'screens.json').read_text())
        self.assertEqual(len(screens),24)
        self.assertTrue(all(not r['differences'] and r['bytes']==196 for r in screens if r['function']==source.COMMAND))
        self.receipt('words',command_direct_words=49,queue_words=55,queue_FP_role_guards=7,
            frames=[40,64],both_padders=True,guards_change_only_FP_register_fields=True,complete_queue_screens=12)

    def test_02_raw_owner_neighbors_pools_and_relative_relocations(self):
        old,diagnostics=build.compile_owner(self.root,self.out,self.before,'before-owner')
        a,af,ar=parse_object(old)
        b,bf,br=parse_object(self.obj)
        self.assertEqual(set(af),set(bf))
        relative=lambda rows,info:{at-info['value']:v for at,v in rows.items() if info['value']<=at<info['value']+info['size']}
        for name in set(bf)-{source.COMMAND,source.QUEUE}:
            x,y=af[name],bf[name]
            self.assertEqual(x['size'],y['size'],name)
            self.assertEqual(a[x['value']:x['value']+x['size']],b[y['value']:y['value']+y['size']],name)
            self.assertEqual(relative(ar,x),relative(br,y),name)
        self.assertEqual((diagnostics,normalized_pools(old)),('',normalized_pools(self.obj)))
        self.receipt('neighbors',unchanged_raw_functions=len(bf)-2,pools_and_relocations_fixed=True,
            private_view_size_and_offsets_preserved=True)

    def test_03_independent_original_generated_rebases(self):
        raw,functions,relocations=parse_object(self.obj)
        patched=bytearray(raw)
        for offset,expected,replacement in source.GUARDS:
            at=functions[source.QUEUE]['value']+offset
            self.assertEqual(struct.unpack_from('>I',patched,at)[0],expected)
            self.assertFalse(relocations.get(at))
            struct.pack_into('>I',patched,at,replacement)
        anchors=nm_anchors(self.root/source.PATHS['elf'])
        full=(self.out/'before-original').read_text()
        for name,entry,_,count in source.TARGETS:
            original='glabel '+name+full.split('glabel '+name,1)[1].split('endlabel '+name,1)[0]+'endlabel '+name+'\n'
            original_obj=self.assemble(original,name+'-original')
            emitted,unresolved=emit_function(patched,functions[name],relocations,name,anchors)
            self.assertFalse(unresolved)
            generated_obj=self.assemble(emitted,name+'-generated')
            info=functions[name]
            used={n for at,rows in relocations.items() if info['value']<=at<info['value']+count*4 for _,n in rows}
            for delta in (0,0x1000000):
                outputs=[]
                for label,obj in (('original',original_obj),('generated',generated_obj)):
                    script=self.out/('%s-%s-%X.ld'%(name,label,delta))
                    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(entry+delta))
                    elf=script.with_suffix('.elf')
                    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,
                        *['--defsym=%s=0x%X'%(n,anchors[n]+delta) for n in sorted(used)],'-o',str(elf),str(obj)],capture_output=True,check=True)
                    self.assertEqual(nm_anchors(elf)[name],entry+delta)
                    outputs.append(sections(elf)['.text'][1][:count*4])
                self.assertEqual(outputs[0],outputs[1])
                if not delta:
                    self.assertEqual(outputs[0],struct.pack('>%dI'%count,*self.retail[entry]))

    def compare(self,case,phase=0,connected=False):
        table={}
        if connected:
            info=self.functions['func_1510B5F8']
            body=list(struct.unpack_from('>38I',self.data,info['value']))
            self.assertEqual(body,list(struct.unpack_from('>38I',self.rom,0x138AA8)))
            table={model.CHILD+i*4:w for i,w in enumerate(body)}
        expected,calls=model.reference(case['memory'],case['args'],case['root'],case['mode'],phase,connected)
        instances=[]
        for words in (self.retail[case['root']],self.words[case['root']],self.raw[case['root']]):
            instance=model.ClippingOracle(words,case['memory'],case['args'],case['root'],case['mode'],phase,connected=table).run()
            self.assertEqual((model.family.parent.external(instance.memory),instance.calls),(model.family.parent.external(expected),calls))
            instances.append(instance)
        self.assertEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))
        return instances

    def test_04_command_defaults_payloads_aliases_and_live_homes(self):
        cases,coverage=0,set()
        for case in model.command_cases():
            for phase in (0,8):
                coverage.update(self.compare(case,phase)[0].visits)
                cases+=1
        self.assertEqual(coverage,set(range(model.COMMAND,model.COMMAND+196,4)))
        self.receipt('command',cases=cases,all_49_words_reached=True,positive_and_negative_zero_defaults=True,
            three_mutable_entry_homes_guest_only=True,field_aliases_and_all_seven_call_words=True,
            raw_and_padded_public_full_padded_private_state=True,no_hardware_FCSR_claim=True)

    def test_05_queue_signed_live_count_base_reload_and_consumption(self):
        cases,coverage=0,set()
        for case in model.queue_cases():
            for phase in (0,8):
                coverage.update(self.compare(case,phase)[0].visits)
                cases+=1
        self.assertEqual(coverage,set(range(model.QUEUE,model.QUEUE+220,4)))
        self.receipt('queue',cases=cases,all_55_words_reached=True,signed_inclusive_live_count_and_base=True,
            raw_and_padded_public_full_padded_private_state=True,dirty_default_and_row_storage_aliases=True)

    def test_06_every_fired_root_access_prefix(self):
        prefixes=0
        cases=[dict(memory=model.fixture(pattern=2,alias=alias),args=(0,0,0),root=model.COMMAND,mode=mode)
            for alias,mode in itertools.product((False,True),(0,4))]
        cases += [dict(memory=model.fixture(count,2,skip),args=(),root=model.QUEUE,mode=mode)
            for count,skip,mode in itertools.product((-1,0,3,5),(0,0x3F),(0,1,4))]
        for case in cases:
            for phase in (0,8):
                full=model.ClippingOracle(self.retail[case['root']],case['memory'],case['args'],case['root'],case['mode'],phase).run()
                for cut in range(full.root_accesses):
                    instances=[]
                    for words in (self.retail[case['root']],self.words[case['root']]):
                        instance=model.ClippingOracle(words,case['memory'],case['args'],case['root'],case['mode'],phase,fault=cut)
                        with self.assertRaises(faults.AccessBoundary):
                            instance.run()
                        instances.append(instance)
                    self.assertEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))
                    self.assertEqual((instances[0].current_pc,instances[0].delay_of),(instances[1].current_pc,instances[1].delay_of))
                    prefixes+=1
        self.receipt('prefixes',fired_prefixes=prefixes,full_padded_state_PC_delay_identity=True,
            helpers_atomic_no_portable_C_fault_or_hardware_exception_claim=True)

    def test_07_native_actual_C_banks_and_effective_controls(self):
        rows=native.vectors()
        self.assertEqual(len(rows),180)
        self.assertEqual(native.run(self.out,'selected',rows),[0,0])
        for label,command,queue,row,status in native.negatives(rows):
            self.assertNotEqual((command,queue),(source.COMMAND_BODY,source.QUEUE_BODY))
            self.assertEqual(native.run(self.out,label,[row],command,queue),[status,status],label)
        self.receipt('native',cases_per_profile=180,profiles=['O2','O0'],effective_controls=9,
            all_1288_backing_words_base_packets_and_canaries=True,private_view_size_384_scale_offset_132=True,
            endian_normalized_dirty_row_and_default_aliases=True,no_native_homes_faults_or_FCSR_claim=True)

    def test_08_effective_IDO_semantic_controls(self):
        for label,command,queue,row,_ in native.negatives(native.vectors()):
            obj,diagnostics=build.compile_owner(self.root,self.out,source.recover(self.before,command,queue),'negative-'+label)
            data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
            info=functions[source.COMMAND if row['root']==model.COMMAND else source.QUEUE]
            words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            self.assertEqual(diagnostics,'')
            # An oversized wrong body must not overlap its actual callee address.
            instance=model.ClippingOracle(words,row['memory'],row['args'],row['root'],row['mode'],entry=0x15200000)
            try:
                instance.run()
            except AssertionError as error:
                raise AssertionError(label+': '+str(error)+' at '+hex(instance.current_pc)) from error
            self.assertNotEqual((model.family.parent.external(instance.memory),instance.calls),
                (model.family.parent.external(row['expected']),row['calls']),label)

    def test_09_actual_matrix_child_connections(self):
        cases=0
        for index,near,far,mode,phase in itertools.product((0,1,3),(0,model.bits(2)),(0,model.bits(5)),range(5),(0,8)):
            self.compare(dict(memory=model.fixture(pattern=2),args=(index,near,far),root=model.COMMAND,mode=mode),phase,True)
            cases+=1
        for count,skip,mode,phase in itertools.product((-1,0,3),(0,5),range(5),(0,8)):
            self.compare(dict(memory=model.fixture(count,2,skip),args=(),root=model.QUEUE,mode=mode),phase,True)
            cases+=1
        self.receipt('connected',cases=cases,actual_two_roots_and_matrix_child_words=142,
            full_padded_state_all_packets_and_live_changes=True,SDK_providers_bounded_not_actual_math=True)

    def test_10_guard_corruption_frozen_inputs_and_original_call_sites(self):
        source.freeze(self.root,self.out)
        rb=Path.read_bytes
        for key in source.BASELINE:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'immutable clipping command input'):
                    source.freeze(self.root,self.out)
        for line,(_,expected,_) in zip(source.GUARD_ROWS.splitlines(keepends=True),source.GUARDS):
            bad=self.guard_bytes.replace(line.encode(),line.replace('0x%08X'%expected,'0x%08X'%(expected^1),1).encode())
            self.assertNotEqual(bad,self.guard_bytes)
            path=self.out/'invalid-guards.csv'
            path.write_bytes(bad)
            with self.assertRaises(ValueError):
                pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,word_patches_path=path)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.obj,self.root/source.PATHS['original'],filename=source.OWNER,word_patches_path=path)
        invalid=self.guard_bytes.replace(source.GUARD_ROWS.encode(),source.GUARD_ROWS.replace(',-,-,',',R_MIPS_HI16:D_800D9AF8,-,',1).encode())
        path=self.out/'invalid-relocation-guards.csv'
        path.write_bytes(invalid)
        with self.assertRaises(ValueError):
            pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,word_patches_path=path)
        with self.assertRaises(ValueError):
            emit_padded_assembly(self.obj,self.root/source.PATHS['original'],filename=source.OWNER,word_patches_path=path)
        archive=self.root/'../Another Source/CBFD-Recompiled/conker/conker/src/game_138520.c'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),'4c7932efd534f588ea02099b9ac32657de498be6cef55bc35d3f3b08bc0754d2')
        for name,_,_,_ in source.TARGETS:
            self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_138520/'+name+'.s")',archive.read_text())
        for at,branch in ((0x52C7C,0x10000377),(0x52CE8,0x1000035C)):
            self.assertEqual(struct.unpack_from('>4I',self.rom,at),(0x0D442D16,0x8CE60000,branch,0x24020001))
        self.assertEqual(struct.unpack_from('>3I',self.rom,0x45D9C),(0x0D442D47,0,0x0D406417))

    def test_11_raw_queue_roles_are_not_full_private_equivalence(self):
        memory=model.fixture(count=0,pattern=3)
        instances=[model.ClippingOracle(words,memory,root=model.QUEUE).run() for words in (self.retail[model.QUEUE],self.raw[model.QUEUE])]
        self.assertEqual((model.family.parent.external(instances[0].memory),instances[0].calls),
            (model.family.parent.external(instances[1].memory),instances[1].calls))
        self.assertNotEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))

    def test_12_installed_source_guards_progress_and_independent_closed_image(self):
        source.freeze(self.root,self.out)
        expected=dict(owner=source.recover(self.before).encode(),guards=self.guard_bytes,
            elf=expected_image((self.out/'before-elf').read_bytes(),self.rom))
        for key,path in source.PATHS.items():
            self.assertEqual((self.root/path).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        self.assertEqual((self.root/source.PATHS['owner']).read_text(),expected['owner'].decode())
        self.assertEqual(hashlib.sha256(expected['elf']).hexdigest(),checkpoint.AFTER['elf'])
        data=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('image',ELF_sha256=hashlib.sha256(expected['elf']).hexdigest(),
            changed_bytes=sum(a!=b for a,b in zip((self.out/'before-elf').read_bytes(),expected['elf'])),
            code_extents=[[12,196],[12,220]],exact_symbol_string_groups=len(SERIALIZATION),
            non_target_definition_changes=0,every_other_ELF_byte_fixed=True,protected_data=data,
            headers_profiles_progress_and_all_old_guard_bytes_fixed=True)

    def test_13_effective_current_and_immutable_image_controls(self):
        rb,rt=Path.read_bytes,Path.read_text
        for key,relative in source.PATHS.items():
            path=self.root/relative
            bad=rb(path)+b'\n'
            with patch.object(Path,'read_bytes',lambda p,value=bad:value if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_12_installed_source_guards_progress_and_independent_closed_image()
        path=self.root/source.PATHS['owner']
        with patch.object(Path,'read_text',lambda p,*a,**k:rt(p,*a,**k)+'\n' if p==path else rt(p,*a,**k)):
            with self.assertRaises(AssertionError):
                self.test_12_installed_source_guards_progress_and_independent_closed_image()
        path=self.root/source.PATHS['elf']
        current=rb(path)
        offsets=[]
        for name,entry,_,_ in source.TARGETS:
            target=next(row for row in machine.symbol_rows(current) if row[1]==name)
            offsets += [target[0]+8,target[3],elf_slot_offset(current,entry,4)]
        offsets += [elf_slot_offset(current,entry,4) for entry in (model.CHILD,0x1510B3B0,0x150A7790)]
        for offset in offsets:
            bad=bytearray(current)
            bad[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_12_installed_source_guards_progress_and_independent_closed_image()
        before=bytearray((self.out/'before-elf').read_bytes())
        target=next(row for row in machine.symbol_rows(before) if row[1]==source.COMMAND)
        before[target[0]+4]^=1
        with self.assertRaises(AssertionError):
            expected_image(bytes(before),self.rom)
        exists=Path.exists
        path=self.out/'baseline.json'
        with patch.object(Path,'exists',lambda p:False if p==path else exists(p)):
            with self.assertRaisesRegex(ValueError,'Changed clipping command baseline'):
                source.freeze(self.root,self.out)
        self.receipt('image-controls',current_inputs=len(source.PATHS),in_file_byte_flips=len(offsets),
            changed_baseline_definition_rejected=True,current_state_recapture_refused=True)

    def test_14_exact_inverse_unknown_input_and_capture_controls(self):
        self.test_12_installed_source_guards_progress_and_independent_closed_image()
        checkpoint.freeze_after(self.root)
        rb=Path.read_bytes
        for relative,key in checkpoint.PATHS.items():
            current=(self.root/relative).read_bytes()
            before=checkpoint.fixture(self.root,'before',key)
            self.assertEqual(checkpoint.previous_input(current,relative,self.root),before)
            self.assertEqual(checkpoint.previous_input(current,self.root/relative,self.root),before)
            self.assertEqual(checkpoint.previous_input(current+b'\n',relative,self.root),current+b'\n')
            self.assertEqual(checkpoint.previous_input(current,'unowned-path',self.root),current)
            for stage in ('before','after'):
                path=self.out/(stage+'-'+key)
                with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                    with self.assertRaisesRegex(AssertionError,'clipping command fixture'):
                        if stage=='before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        path=self.root/source.PATHS['owner']
        with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
            with self.assertRaisesRegex(AssertionError,'Unexpected installed clipping command input'):
                checkpoint.freeze_after(self.root)


if __name__ == '__main__':
    unittest.main()
