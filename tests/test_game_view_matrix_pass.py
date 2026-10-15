"""Per-view matrix pass literal shape and protocol qualification."""
from pathlib import Path
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_view_matrix_pass as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_view_orthographic_setup as sdk_build
from tools.experiments.alternative_source_draft_word_screen import emit_function,nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests import game_view_matrix_pass_oracle as model
from tools.tests import game_view_matrix_pass_native as native
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import view_matrix_pass_checkpoint as checkpoint

SERIALIZATION=()


def expected_image(before,rom):
    expected=bytearray(before)
    for name,entry,address,count in ((source.FUNCTION,source.ENTRY,source.ROM,73),
            (source.MULTIPLY,source.MULTIPLY_ENTRY,source.MULTIPLY_ROM,78)):
        at=elf_slot_offset(before,entry,count*4)
        expected[at:at+count*4]=rom[address:address+count*4]
        rows=[(at,fields) for at,label,fields,_ in machine.symbol_rows(before) if label==name]
        assert len(rows)==1 and rows[0][1][1:]==(entry,12,18,0,5)
        struct.pack_into('>I',expected,rows[0][0]+8,count*4)
    with patch.object(machine,'SERIALIZATION',SERIALIZATION):
        machine.apply_burst_symbol_serialization(expected)
    return bytes(expected)


class ViewMatrixPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        source.freeze(cls.root,cls.out)
        cls.before=(cls.out/'before-owner').read_text()
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.obj,cls.diagnostics=build.compile_owner(cls.root,cls.out,source.recover(cls.before),'qualified')
        cls.raw_data,cls.raw_functions=build.link_owner(cls.root,cls.out,cls.obj,source.OWNER)
        cls.info=cls.raw_functions[source.FUNCTION]
        cls.raw=list(struct.unpack_from('>%dI'%(cls.info['size']//4),cls.raw_data,cls.info['value']))
        cls.guard_bytes=source.guard_manifest((cls.out/'before-guards').read_bytes())
        cls.guards=cls.out/'qualified-guards.csv'
        cls.guards.write_bytes(cls.guard_bytes)
        padded=pad_c_object.emit_padded_assembly(cls.obj,cls.root/source.PATHS['layout'],source.OWNER,word_patches_path=cls.guards)
        cls.primary=cls.assemble(padded,'primary')
        cls.data,cls.functions=build.link_owner(cls.root,cls.out,cls.primary,source.OWNER)
        cls.words=list(struct.unpack_from('>73I',cls.data,cls.functions[source.FUNCTION]['value']))
        cls.retail=list(struct.unpack_from('>73I',cls.rom,source.ROM))
        assembly=source.restored_multiply_assembly((cls.out/'before-multiply_original').read_text())
        cls.multiply_assembly=cls.out/'qualified-multiply.s'
        cls.multiply_assembly.write_text(assembly)
        text=source.restored_multiply_owner((cls.out/'before-multiply_owner').read_text()).replace(
            source.ASSEMBLY.removeprefix('conker/'),str(cls.multiply_assembly.relative_to(cls.root/'conker')))
        cls.multiply_obj,cls.multiply_diagnostics=build.compile_owner(cls.root,cls.out,text,'restored-multiply')
        raw,functions,_=parse_object(cls.multiply_obj)
        info=functions[source.MULTIPLY]
        cls.multiply=list(struct.unpack_from('>78I',raw,info['value']))
        cls.sdk_obj,cls.sdk_diagnostics=sdk_build.compile_sdk(cls.root,cls.out,(cls.out/'before-sdk').read_text(),source.PATHS['sdk'],'sdk')
        assembly=pad_c_object.emit_padded_assembly(cls.sdk_obj,cls.root/source.PATHS['layout'],'mtxutil2',word_patches_path=cls.guards)
        cls.sdk_padded=cls.assemble(assembly,'sdk-padded')
        sdk,functions=build.link_owner(cls.root,cls.out,cls.sdk_padded,'mtxutil2')
        cls.converter=list(struct.unpack_from('>46I',sdk,functions['guMtxL2F']['value']))
        before=(cls.out/'before-elf').read_bytes()
        cls.frustum=list(struct.unpack_from('>61I',before,elf_slot_offset(before,model.FRUSTUM,244)))
        cls.connected={entry+i*4:word for entry,words in ((model.CONVERT,cls.converter),(model.MULTIPLY,cls.multiply),(model.FRUSTUM,cls.frustum)) for i,word in enumerate(words)}

    @classmethod
    def assemble(cls,text,label):
        path=cls.out/(label+'.s')
        path.write_text('.include "'+str(cls.root/'conker/include/asm_processor_prelude.inc')+'"\n'+text)
        obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        return obj

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_complete_retail_words_frame_homes_and_both_padders(self):
        self.assertEqual((self.diagnostics,self.info['size'],self.words),('',292,self.retail))
        self.assertEqual(self.words[0],0x27BDFF70)
        self.assertEqual(self.raw[25],0x27B3004C)
        expected=[(offset,a,b) for offset,a,b in source.GUARDS]
        actual=[(i*4,a,b) for i,(a,b) in enumerate(zip(self.raw,self.retail)) if a!=b]
        self.assertEqual([x[0] for x in actual],[x[0] for x in expected])
        for offset,a,b in actual:
            row=next(row for row in expected if row[0]==offset)
            mask=0xFFFF0000 if offset in (0xD4,0xD8) else 0xFFFFFFFF
            self.assertEqual((a&mask,b&mask),(row[1]&mask,row[2]&mask))
        generated=emit_padded_assembly(self.obj,self.root/source.PATHS['original'],filename=source.OWNER,word_patches_path=self.guards)
        data,functions=build.link_owner(self.root,self.out,self.assemble(generated,'generated'),source.OWNER)
        at=functions[source.FUNCTION]['value']
        self.assertEqual(data[at:at+292],struct.pack('>73I',*self.retail))
        screens=json.loads((self.out/'screens.json').read_text())
        self.assertEqual(len(screens),25)
        selected=next(r for r in screens if r['label']=='typed-fixed-array-temporary-first-s16')
        self.assertEqual((selected['bytes'],selected['frame'],len(selected['differences'])),(292,144,20))
        self.receipt('words',words=73,frame=144,projection_offset=76,guards=20,
            no_frame_home_call_or_branch_guards=True,both_padders=True,complete_screens=25)

    def test_02_both_raw_owner_neighbor_and_pool_preservation(self):
        for key,obj,excluded in (('owner',self.obj,source.FUNCTION),('multiply_owner',self.multiply_obj,source.MULTIPLY)):
            old,diagnostics=build.compile_owner(self.root,self.out,(self.out/('before-'+key)).read_text(),'before-'+key)
            a,af,ar=parse_object(old)
            b,bf,br=parse_object(obj)
            self.assertEqual(set(af),set(bf))
            relative=lambda rows,info:{at-info['value']:v for at,v in rows.items() if info['value']<=at<info['value']+info['size']}
            for name in set(bf)-{excluded}:
                x,y=af[name],bf[name]
                self.assertEqual(x['size'],y['size'],name)
                self.assertEqual(a[x['value']:x['value']+x['size']],b[y['value']:y['value']+y['size']],name)
                self.assertEqual(relative(ar,x),relative(br,y),name)
            self.assertEqual((diagnostics,normalized_pools(old)),('',normalized_pools(obj)))
        self.receipt('neighbors',caller_raw_neighbors=13,multiply_raw_neighbors=3,pools_and_relocations_fixed=True)

    def test_03_original_kernel_and_fresh_SDK_converter_slots(self):
        self.assertEqual((self.multiply_diagnostics,self.multiply),('',list(struct.unpack_from('>78I',self.rom,source.MULTIPLY_ROM))))
        self.assertEqual(self.multiply[0],0xE7B4FFE0)
        self.assertEqual(self.multiply[1],0x27BDFFE0)
        self.assertEqual(self.multiply[-2:],[0,0])
        self.assertEqual(self.sdk_diagnostics,'uld:\nWarning: -Xfullwarn not supported.\n')
        self.assertEqual(self.converter,list(struct.unpack_from('>46I',self.rom,0x21D368)))
        _,functions,_=parse_object(self.sdk_obj)
        self.assertEqual(functions['guMtxL2F']['size'],180)
        self.assertEqual(self.frustum,list(struct.unpack_from('>61I',self.rom,0x486DC)))
        self.assertEqual(self.converter[-1],0)
        self.assertEqual((self.converter[44],self.multiply[75],self.frustum[58]),(0x27BD0010,0x27BD0020,0x27BD0040))
        self.receipt('dependencies',original_kernel_slot_words=78,kernel_instructions=76,SDK_instructions=45,
            SDK_slot_padding_words=1,frustum_slot_words=61,restoration_not_C_match_credit=True,
            baseline_math_dependency_is_empty_C_placeholder=True)

    def compare(self,case,phase=0,connected=False):
        expected,calls=model.reference(case['memory'],case['mode'],phase,case['seed'],connected)
        instances=[]
        for words in (self.retail,self.words,self.raw):
            instance=model.MatrixPassOracle(words,case['memory'],case['mode'],phase,case['seed'],
                connected=self.connected if connected else {}).run()
            self.assertEqual((model.family.parent.external(instance.memory),model.canonical_calls(instance.calls)),
                (model.family.parent.external(expected),model.canonical_calls(calls)))
            if connected:
                self.assertEqual([target for target,_,_ in instance.return_mutations],
                    [target for target,_ in instance.calls if target in (model.CONVERT,model.MULTIPLY,model.FRUSTUM)])
            instances.append(instance)
        self.assertEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))
        return instances

    def test_04_live_pages_base_count_matrices_and_aliases(self):
        coverage,cases=set(),0
        for case in model.cases():
            for phase in (0,8):
                instance=self.compare(case,phase)[0]
                if instance.calls:
                    self.assertEqual(instance.calls[0][1][0],machine.STACK+phase-0x44)
                coverage.update(instance.visits)
                cases+=1
        self.assertEqual(coverage,set(range(source.ENTRY,source.ENTRY+292,4)))
        self.receipt('guest',cases=cases,all_73_words_reached=True,full_padded_return_state=True,
            raw_and_padded_public_agreement=True,unsigned_pages=[0,1,128,255],
            two_converters_ordered_product_frustum_and_live_reload=True,
            finite_FP_model_not_hardware_FCSR=True)

    def test_05_actual_converter_kernel_and_frustum_connections(self):
        cases=0
        for count,page,pattern,mode,phase in itertools.product((-1,0,3),(0,1),range(3),range(5),(0,8)):
            self.compare(dict(memory=model.fixture(count,page,pattern),mode=mode,seed=pattern),phase,True)
            cases+=1
        self.receipt('connected',cases=cases,actual_caller_converter_kernel_frustum=True,
            freshly_compiled_SDK=True,all_matrices_normals_and_call_packets=True,
            trig_provider_bounded_not_actual_trig_or_hardware=True)

    def test_06_fired_root_access_prefixes(self):
        prefixes=0
        for count,page,mode,phase in itertools.product((-1,0,3),(0,255),(0,1,2,4),(0,8)):
            memory=model.fixture(count,page,1)
            full=model.MatrixPassOracle(self.retail,memory,mode,phase).run()
            for cut in range(full.root_accesses):
                instances=[]
                for words in (self.retail,self.words):
                    instance=model.MatrixPassOracle(words,memory,mode,phase,fault=cut)
                    with self.assertRaises(faults.AccessBoundary):
                        instance.run()
                    instances.append(instance)
                self.assertEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))
                self.assertEqual((instances[0].current_pc,instances[0].delay_of),(instances[1].current_pc,instances[1].delay_of))
                prefixes+=1
        self.receipt('prefixes',fired_prefixes=prefixes,full_state_PC_delay_identity=True,
            helpers_atomic_no_portable_C_fault_or_hardware_exception_claim=True)

    def test_07_native_actual_C_and_guest_checked_quiet_provider_vectors(self):
        rows=native.vectors()
        self.assertEqual(len(rows),120)
        with patch.object(model.planes,'RETURNS',native.trig_returns()):
            for row in rows:
                expected,calls=model.reference(row['memory'],row['mode'],seed=row['seed'])
                self.assertEqual((model.family.parent.external(expected),model.canonical_calls(calls)),
                    (model.family.parent.external(row['expected']),row['calls']))
                self.compare(row,connected=True)
        self.assertEqual(native.run(self.out,'selected',rows),[0,0])
        for label,body,row in native.negatives(rows):
            self.assertNotEqual(body,source.BODY,label)
            self.assertEqual(native.run(self.out,label,[row],body),[1,1],label)
        raw_rows=native.vectors(False)
        witness=next(r for r in raw_rows if model.read(r['memory'],model.COUNT)==0 and r['memory'][model.PAGE]==0 and r['mode']==3 and r['seed']==0)
        self.assertEqual(native.run(self.out,'host-snan-witness',[witness],quiet=False),[0,2])
        receipt=json.loads((self.out/'native-host-snan-witness.json').read_text())
        self.assertEqual(receipt['details'][1][3:5],[0x7F812345,0x7FC12345])
        self.receipt('native',cases_per_profile=120,profiles=['O2','O0'],effective_semantic_controls=6,
            actual_pass_decoder_and_frustum_C=True,product_independent_C_reference_not_MIPS_execution=True,
            all_backing_matrices_normals_globals_tables_and_canaries=True,
            quiet_provider_vectors_independently_checked_in_guest=True,
            raw_host_signaling_NaN_ABI_quieting_witness_retained=True,
            no_host_private_frame_or_hardware_FCSR_claim=True)

    def test_08_effective_compiled_IDO_semantic_controls(self):
        for label,body,row in native.negatives(native.vectors(False)):
            obj,diagnostics=build.compile_owner(self.root,self.out,source.recover(self.before,body),'negative-'+label)
            data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
            info=functions[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            self.assertEqual(diagnostics,'')
            expected,calls=model.reference(row['memory'],row['mode'],seed=row['seed'])
            instance=model.MatrixPassOracle(words,row['memory'],row['mode'],seed=row['seed'],entry=0x15200000,
                expected_calls=model.canonical_calls(calls))
            mismatch=False
            try:
                instance.run()
            except model.ProtocolMismatch:
                mismatch=True
            self.assertTrue(mismatch or (model.family.parent.external(instance.memory),model.canonical_calls(instance.calls)) !=
                (model.family.parent.external(expected),model.canonical_calls(calls)),label)

    def test_09_original_kernel_and_converter_ordered_overlaps(self):
        left,right=0x50000,0x51000
        kernel_cases,converter_cases,prefixes=0,0,0
        for destination,pattern,phase in itertools.product((left-4,left,left+4,right-4,right,right+4,0x52000),range(3),(0,8)):
            memory=model.fixture(-1)
            for base in (left-64,right-64,0x52000-64):
                memory.update({base+i:(i*13+0xA5)&255 for i in range(0x180)})
            for i in range(16):
                model.put(memory,left+i*4,model.bits((i*3+pattern)%13-6))
                model.put(memory,right+i*4,model.bits(((i*7+pattern)%17-8)*0.25))
            expected=dict(memory)
            model.multiply(expected,left,right,destination)
            actual=model.MatrixPassOracle(self.multiply,memory,phase=phase,entry=model.MULTIPLY,arguments=(left,right,destination)).run()
            self.assertEqual(model.family.parent.external(actual.memory),model.family.parent.external(expected))
            self.assertEqual(actual.visits,set(range(model.MULTIPLY,model.MULTIPLY+76*4,4)))
            kernel_cases+=1
        for destination,pattern,phase in itertools.product((left-32,left,left+4,left+32,0x52000),range(4),(0,8)):
            memory=model.fixture(-1)
            for base in (left-64,0x52000-64):
                memory.update({base+i:(i*13+0xA5)&255 for i in range(0x180)})
            for i,word in enumerate(model.packed(pattern)):
                model.put(memory,left+i*4,word)
            expected=dict(memory)
            model.decode(expected,destination,left)
            actual=model.MatrixPassOracle(self.converter,memory,phase=phase,entry=model.CONVERT,arguments=(destination,left)).run()
            self.assertEqual(model.family.parent.external(actual.memory),model.family.parent.external(expected))
            converter_cases+=1
        memory=model.fixture(-1)
        for base in (left-64,right-64):
            memory.update({base+i:(i*13+0xA5)&255 for i in range(0x180)})
        for i in range(16):
            model.put(memory,left+i*4,model.bits(i*0.25-2))
            model.put(memory,right+i*4,model.bits(i*0.5-3))
        for entry,words,args in ((model.MULTIPLY,self.multiply,(left,right,left+4)),(model.CONVERT,self.converter,(left+4,left))):
            full=model.MatrixPassOracle(words,memory,entry=entry,arguments=args).run()
            for cut in range(full.root_accesses):
                instance=model.MatrixPassOracle(words,memory,entry=entry,arguments=args,fault=cut)
                with self.assertRaises(faults.AccessBoundary):
                    instance.run()
                self.assertEqual(instance.root_accesses,cut)
                prefixes+=1
        self.receipt('kernels',original_product_overlap_cases=kernel_cases,actual_C_SDK_overlap_cases=converter_cases,
            fired_helper_prefixes=prefixes,all_76_product_instructions_reached=True,
            right_snapshot_and_rowwise_left_order=True,finite_FP_model_not_hardware=True)

    def test_10_literal_signed16_loop_tail_and_wide_type_boundary(self):
        cases=0
        for initial,count,wanted in ((0x7FFE,0x7FFF,0x7FFF),(0x7FFF,-1,0xFFFF8000),(0xFFFFFFFF,0,0)):
            memory=model.fixture(count)
            instances=[]
            for words in (self.retail,self.words):
                instance=model.MatrixPassOracle(words,memory,fault=2)
                instance.r[16]=initial
                instance.r[20]=model.PAGE
                instance.r[21]=model.BASE
                instance.entry=source.ENTRY+53*4
                with self.assertRaises(faults.AccessBoundary):
                    instance.run()
                self.assertEqual((instance.r[16],instance.current_pc),(wanted,source.ENTRY+27*4))
                instances.append(instance)
            self.assertEqual(machine.complete_state(instances[0]),machine.complete_state(instances[1]))
            cases+=1
        wide=source.BODY.replace('    s16 index;','    s32 index;')
        obj,diagnostics=build.compile_owner(self.root,self.out,source.recover(self.before,wide),'wide-index-shape')
        data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
        info=functions[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        self.assertEqual(diagnostics,'')
        self.assertNotEqual(words,self.retail)
        self.assertEqual(native.run(self.out,'wide-index-bounded',native.vectors(),wide),[0,0])
        self.receipt('width',actual_tail_state_cases=cases,signed16_wrap_to_negative_proved=True,
            wide_control_bytes=info['size'],wide_bounded_native_agreement_not_word_match=True,
            seeded_tail_not_whole_function_at_extreme_counts=True)

    def test_11_expected_word_relocation_frozen_input_and_caller_controls(self):
        source.freeze(self.root,self.out)
        rb=Path.read_bytes
        for key in source.BASELINE:
            path=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaisesRegex(ValueError,'immutable view matrix pass input'):
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
        line=next(line for line in source.GUARD_ROWS.splitlines(keepends=True) if ',0xD4,' in line)
        path=self.out/'invalid-relocation.csv'
        path.write_bytes(self.guard_bytes.replace(line.encode(),line.replace('R_MIPS_HI16:D_80082FA0','-',1).encode()))
        with self.assertRaises(ValueError):
            pad_c_object.emit_padded_assembly(self.obj,self.root/source.PATHS['layout'],source.OWNER,word_patches_path=path)
        for at,after in ((0x46620,0x0D443E00),(0x46710,0x8E190000)):
            self.assertEqual(struct.unpack_from('>3I',self.rom,at),(0x0D442DA4,0,after))
        with self.assertRaises(ValueError):
            source.expected_progress(b'wrong')

    def test_12_independent_original_and_generated_rebases(self):
        data,functions,relocations=parse_object(self.obj)
        info=functions[source.FUNCTION]
        patched=bytearray(data)
        for offset,expected,replacement in source.GUARDS:
            at=info['value']+offset
            self.assertEqual(struct.unpack_from('>I',patched,at)[0],expected)
            struct.pack_into('>I',patched,at,replacement)
        anchors=nm_anchors(self.root/source.PATHS['elf'])
        emitted,unresolved=emit_function(patched,info,relocations,source.FUNCTION,anchors)
        self.assertFalse(unresolved)
        original=(self.out/'before-original').read_text()
        original='glabel '+source.FUNCTION+original.split('glabel '+source.FUNCTION,1)[1].split('endlabel '+source.FUNCTION,1)[0]+'endlabel '+source.FUNCTION+'\n'
        variants=(('original',self.assemble(original,'independent-original')),('generated',self.assemble(emitted,'independent-generated')))
        used={name for at,rows in relocations.items() if info['value']<=at<info['value']+292 for _,name in rows}
        for delta in (0,0x1000000):
            outputs=[]
            for label,obj in variants:
                script=self.out/('%s-%X.ld'%(label,delta))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+delta))
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%(name,anchors[name]+delta) for name in sorted(used)],'-o',str(elf),str(obj)],capture_output=True,check=True)
                self.assertEqual(nm_anchors(elf)[source.FUNCTION],source.ENTRY+delta)
                outputs.append(sections(elf)['.text'][1][:292])
            self.assertEqual(outputs[0],outputs[1])
            if not delta:
                self.assertEqual(outputs[0],struct.pack('>73I',*self.retail))

    def test_13_archive_and_exact_progress_ownership(self):
        archive=self.root/'../Another Source/CBFD-Recompiled/conker/conker/src/game_138520.c'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),'4c7932efd534f588ea02099b9ac32657de498be6cef55bc35d3f3b08bc0754d2')
        self.assertIn('#pragma GLOBAL_ASM("asm/nonmatchings/game_138520/func_1510B690.s")',archive.read_text())
        before=(self.out/'before-progress').read_bytes()
        expected=source.expected_progress(before)
        old,new=before.splitlines(keepends=True),expected.splitlines(keepends=True)
        self.assertEqual(len(old),len(new))
        changed=[(a,b) for a,b in zip(old,new) if a!=b]
        self.assertEqual(len(changed),1)
        self.assertIn(b',func_150A7A48,353008200,312,c',changed[0][0])
        self.assertIn(b',func_150A7A48,353008200,312,asm',changed[0][1])
        with self.assertRaises(ValueError):
            source.expected_progress(expected)

    def test_14_installed_sources_progress_guards_and_independent_closed_image(self):
        source.freeze(self.root,self.out)
        expected=dict(owner=source.recover(self.before).encode(),guards=self.guard_bytes,
            multiply_owner=source.restored_multiply_owner((self.out/'before-multiply_owner').read_text()).encode(),
            progress=source.expected_progress((self.out/'before-progress').read_bytes()),
            elf=expected_image((self.out/'before-elf').read_bytes(),self.rom))
        for key,path in source.PATHS.items():
            self.assertEqual((self.root/path).read_bytes(),expected.get(key,(self.out/('before-'+key)).read_bytes()),key)
        for key in ('owner','multiply_owner'):
            self.assertEqual((self.root/source.PATHS[key]).read_text(),expected[key].decode())
        self.assertEqual(hashlib.sha256(expected['elf']).hexdigest(),checkpoint.AFTER['elf'])
        checkpoint.check_assembly(self.root)
        self.assertEqual((self.root/source.ASSEMBLY).read_text(),source.restored_multiply_assembly((self.out/'before-multiply_original').read_text()))
        data=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('image',ELF_sha256=hashlib.sha256(expected['elf']).hexdigest(),
            changed_bytes=sum(a!=b for a,b in zip((self.out/'before-elf').read_bytes(),expected['elf'])),
            code_extents=[[12,292],[12,312]],exact_symbol_string_groups=len(SERIALIZATION),
            non_target_definition_changes=0,every_other_ELF_byte_fixed=True,protected_data=data,
            progress_only_product_c_to_asm=True,all_old_guard_profile_header_bytes_fixed=True)

    def test_15_effective_current_image_source_and_capture_controls(self):
        rb,rt=Path.read_bytes,Path.read_text
        for relative in list(source.PATHS.values())+[source.ASSEMBLY]:
            path=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_14_installed_sources_progress_guards_and_independent_closed_image()
        for relative in (source.PATHS['owner'],source.PATHS['multiply_owner'],source.ASSEMBLY):
            path=self.root/relative
            with patch.object(Path,'read_text',lambda p,*a,**k:rt(p,*a,**k)+'\n' if p==path else rt(p,*a,**k)):
                with self.assertRaises(AssertionError):
                    self.test_14_installed_sources_progress_guards_and_independent_closed_image()
        path=self.root/source.PATHS['elf']
        current=rb(path)
        offsets=[]
        for name,entry in ((source.FUNCTION,source.ENTRY),(source.MULTIPLY,source.MULTIPLY_ENTRY)):
            target=next(row for row in machine.symbol_rows(current) if row[1]==name)
            offsets += [target[0]+8,target[3],elf_slot_offset(current,entry,4)]
        offsets += [elf_slot_offset(current,entry,4) for entry in (model.CONVERT,model.FRUSTUM,0x1510B458)]
        for offset in offsets:
            bad=bytearray(current)
            bad[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_14_installed_sources_progress_guards_and_independent_closed_image()
        for name in (source.FUNCTION,source.MULTIPLY):
            before=bytearray((self.out/'before-elf').read_bytes())
            target=next(row for row in machine.symbol_rows(before) if row[1]==name)
            before[target[0]+4]^=1
            with self.assertRaises(AssertionError):
                expected_image(bytes(before),self.rom)
        exists=Path.exists
        path=self.out/'baseline.json'
        with patch.object(Path,'exists',lambda p:False if p==path else exists(p)):
            with self.assertRaisesRegex(ValueError,'Changed view matrix pass baseline'):
                source.freeze(self.root,self.out)
        self.receipt('image-controls',current_inputs=len(source.PATHS)+1,in_file_byte_flips=len(offsets),
            changed_baseline_definitions_rejected=2,current_state_recapture_refused=True)

    def test_16_exact_inverse_unknown_input_and_capture_controls(self):
        self.test_14_installed_sources_progress_guards_and_independent_closed_image()
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
                    with self.assertRaisesRegex(AssertionError,'matrix pass fixture'):
                        if stage=='before':
                            checkpoint.previous_input(current,relative,self.root)
                        else:
                            checkpoint.freeze_after(self.root)
        path=self.root/source.PATHS['owner']
        with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
            with self.assertRaisesRegex(AssertionError,'Unexpected installed matrix pass input'):
                checkpoint.freeze_after(self.root)
        path=self.root/source.ASSEMBLY
        current=(self.root/source.PATHS['elf']).read_bytes()
        with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==path else rb(p)):
            for action in (lambda:checkpoint.freeze_after(self.root),
                    lambda:checkpoint.previous_input(current,source.PATHS['elf'],self.root)):
                with self.assertRaisesRegex(AssertionError,'Unexpected installed matrix product assembly'):
                    action()


if __name__=='__main__':
    unittest.main()
