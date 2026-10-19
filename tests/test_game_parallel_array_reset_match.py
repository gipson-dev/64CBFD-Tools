"""Two reset loops: ordered writes, current bounds, literal ABI and image gates."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_parallel_array_reset_candidates as source
from tools.experiments import game_parallel_array_reset_layout as layout
from tools.experiments import game_parallel_array_reset_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_parallel_array_reset_oracle as oracle
from tools.tests.test_game_packed_peer_lookup_match import state
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


NATIVE=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
s32 D_800D23B0;
SOURCE_BODY
typedef struct {s32 first,second;u32 pattern,start,count;} Case;
static const Case cases[]={CASES};
static const u32 patches[]={PATCHES};
static u32 memory[1280] __attribute__((aligned(16))),wanted[1280];
void _start(void){
    u32 n,i,value;const Case *c;u8 *bytes=(u8 *)memory;u32 failure=0;
    if(sizeof(void*)!=4 || sizeof(s32)!=4)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++){
        c=cases+n;
        for(i=0;i<1280;i++)memory[i]=wanted[i]=(i*0x1020305u)^(c->pattern*0x01010101u)^0xA53C719Bu;
        memory[4]=wanted[4]=(u32)c->first;memory[0xEA4/4]=wanted[0xEA4/4]=(u32)c->second;
        D_800D23B0=(s32)bytes;
        for(i=0;i<c->count;i++){value=c->start+i*2;wanted[patches[value]]=patches[value+1];}
        func_1508DA1C();
        if(D_800D23B0!=(s32)bytes)failure=21;
        for(i=0;i<1280;i++)if(memory[i]!=wanted[i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class ParallelArrayResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.words=layout.relocate(cls.normalized,cls.moved,oracle.DEFAULT)
        cls.retail=list(struct.unpack_from('>52I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_frame_source_origins_bindings_and_guards(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(52,8,19,''))
        self.assertEqual(self.words,self.retail);self.assertEqual(sorted(layout.origins()),list(range(52)));self.assertEqual(self.moved,self.bindings)
        guards=layout.private_guards(self.values['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        self.assertTrue(guards.startswith(self.values['conker/retail_word_patches.us.csv']))
        rows=[r for r in csv.DictReader(io.StringIO(guards.decode())) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(rows),19);self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in rows))

    def test_02_independent_ordered_stores_and_complete_literal_state(self):
        visits=set();pairs=changed=0;modes=set()
        for case in self.cases:
            for phase in (0,8):
                memory,_=oracle.fixture(case,phase);trace=[];after=oracle.reference(memory,trace=trace)
                models=[oracle.ResetModel(words,memory,phase).run() for words in (self.retail,self.words,self.raw_words)]
                self.assertEqual(state(models[0]),state(models[1]),case)
                for model in models:
                    self.assertEqual(oracle.public(model.memory),oracle.public(after),case);self.assertFalse(model.calls)
                    stores=[e[1:] for e in model.events if e[0]=='W' and not oracle.STACK-256<=e[1]<oracle.STACK+128]
                    self.assertEqual(stores,trace,case)
                if oracle.read(after,oracle.STATE,4)!=oracle.read(memory,oracle.STATE,4):changed+=1;modes.add(case.mode)
                visits.update(models[0].visits);pairs+=1
        self.assertEqual(modes,{1,2,3,4});self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+208,4)))
        self.receipt('functional-cases',cases=len(self.cases),phases=2,paired_literal_runs=pairs,raw_public_same_corpus=pairs,
            all52_words_visited=True,ordered_public_stores_checked=True,fired_context_redirections=changed,redirection_modes=sorted(modes),no_numeric_return_contract=True)

    def test_03_fired_access_cuts_aliases_and_large_count_prefixes(self):
        count=0
        cases=(oracle.Case(0,0),oracle.Case(-1,3),oracle.Case(2,0),oracle.Case(2,3),
            oracle.Case(2,4,7,1,1),oracle.Case(0,4,127,3,2))
        for case in cases:
            for phase in (0,8):
                memory,_=oracle.fixture(case,phase);run=oracle.ResetModel(self.retail,memory,phase).run()
                for cut in range(run.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=oracle.ResetModel(words,memory,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual((state(models[0]),models[0].requested),(state(models[1]),models[1].requested));count+=1
        probes=0
        for case,cut in ((oracle.Case(0x7FFFFFFF,0),10),(oracle.Case(0,0x7FFFFFFF),12)):
            memory,_=oracle.fixture(case);models=[]
            for words in (self.retail,self.words):
                model=oracle.ResetModel(words,memory);model.fault=cut
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,cut);models.append(model)
            self.assertEqual(state(models[0]),state(models[1]));probes+=1
        memory,_=oracle.fixture(oracle.Case(1,0),context=oracle.STATE-0xEB0);models=[]
        for words in (self.retail,self.words):
            model=oracle.ResetModel(words,memory);model.fault=5
            with self.assertRaises(oracle.core.AccessFault):model.run()
            self.assertEqual(model.accesses,5);self.assertEqual(model.requested,('R',15,4));models.append(model)
        self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(oracle.read(models[0].memory,oracle.STATE,4),0xFFFFFFFF)
        self.receipt('fired-cuts',pairs=count,all_requested_cuts_fired=True,huge_signed_count_prefixes=probes,
            first_store_alias_prefix=1,cut_before_unaligned_count_read=True,not_complete_huge_scans_or_hardware_faults=True)

    def test_04_native32_full_numeric_buffers_and_five_source_negatives(self):
        rows=[];patches=[]
        for case in oracle.native_cases():
            before,context=oracle.fixture(case);after=oracle.reference(before);start=len(patches)
            for i in range(oracle.SIZE//4):
                value=oracle.read(after,context+i*4,4)
                if value!=oracle.read(before,context+i*4,4):patches.extend((i,value))
            rows.append('{%d,%d,%d,%d,%d}'%(case.first,case.second,case.pattern,start,(len(patches)-start)//2))
        body=source.FITTED;template=NATIVE.replace('CASES',',\n'.join(rows)).replace('PATCHES',','.join('0x%Xu'%v for v in patches))
        controls={'o0':body,'o2':body,'ubsan':body,
            'wrong-first-value':body.replace('resetEB0[i] = -1','resetEB0[i] = 0'),
            'wrong-enabled':body.replace('reset1070[i] = 1','reset1070[i] = 0'),
            'wrong-second-bound':body.replace('D_800D23B0 + 0xEA4','D_800D23B0 + 0x10'),
            'wrong-pending':body.replace('reset12F4[i] = 0','reset12F4[i] = 1'),
            'wrong-first-equality':body.replace('i < *(s32 *)(state + 0x10)','i <= *(s32 *)(state + 0x10)')}
        exits={}
        for name,unit in controls.items():
            if name not in ('o0','o2','ubsan'):self.assertNotEqual(unit,body)
            path=self.out/('native-'+name+'.c');path.write_text(template.replace('SOURCE_BODY',source.DECLARATIONS+unit));exe=path.with_suffix('')
            result=subprocess.run([*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0 if name in ('o0','o2','ubsan') else 21,'',''),name);exits[name]=result.returncode
        self.receipt('native-cases',fixtures=len(rows),numeric_words_per_fixture=1280,first_count_max48_second_max32=True,
            endian_neutral_expected_word_patches=True,exits=exits,guest_null_context_redirections_not_native_C_claims=True)

    def test_05_effective_cached_bound_controls_in_guest(self):
        marker='    s32 *reset12F4 = (s32 *)(state + 0x12F4);'
        second=source.FITTED.replace(marker,marker+'\n    s32 limit;').replace(
            '    for (i = 0; i < *(s32 *)((u8 *)D_800D23B0 + 0xEA4); i++) {',
            '    limit = *(s32 *)((u8 *)D_800D23B0 + 0xEA4);\n    for (i = 0; i < limit; i++) {')
        _,words,row=source.compile_candidate(self.root,self.out,'wrong-cached-second',second)
        self.assertFalse(row['diagnostics']);memory,_=oracle.fixture(oracle.Case(0,4,7,1,1));wanted=oracle.reference(memory)
        control=oracle.ResetModel(words,memory).run();self.assertNotEqual(oracle.public(control.memory),oracle.public(wanted))
        self.assertEqual(oracle.read(control.memory,oracle.STATE,4),0)
        first=source.FITTED.replace(marker,marker+'\n    s32 limit = *(s32 *)(state + 0x10);').replace(
            'for (; i < *(s32 *)(state + 0x10); i++)','for (; i < limit; i++)')
        _,words,row=source.compile_candidate(self.root,self.out,'wrong-cached-first',first);self.assertFalse(row['diagnostics'])
        memory,_=oracle.fixture(oracle.Case(1,0),context=oracle.STATE-0xEB0);fired=None
        for cut in range(16):
            control=oracle.ResetModel(words,memory);control.fault=cut
            with self.assertRaises(oracle.core.AccessFault):control.run()
            self.assertEqual(control.accesses,cut)
            if control.requested==('R',0xEA3,4):fired=cut;break
            self.assertNotEqual(control.requested,('R',15,4))
        self.assertIsNotNone(fired)
        self.receipt('cached-bound-controls',second_bound_public_negative_fired=True,first_bound_fault_order_negative_fired=True,
            first_control_cut=fired,original_next_unaligned_address=15,cached_first_next_unaligned_address=0xEA3,
            both_stop_before_alignment_check=True,not_hardware_exception_evidence=True)

    def test_06_actual_void_caller_window_preserves_literal_residual_state(self):
        rom=self.values['conker/conker.us.bin'];entry=0x1509E0F8
        window=list(struct.unpack_from('>4I',rom,0xCB5A8));epilogue=list(struct.unpack_from('>4I',rom,0xCB87C))
        self.assertEqual(window,[0x0D423687,0,0x100000B2,0x8FBF0024]);self.assertEqual(epilogue,[0x8FB00020,0x27BD0048,0x03E00008,0])
        count=0
        for case in self.cases[::23]+self.cases[-12:]:
            for phase in (0,8):
                memory,_=oracle.fixture(case,phase);oracle.put(memory,oracle.STACK+phase+0x24,0xDEAD0000,4)
                oracle.put(memory,oracle.STACK+phase+0x20,0x5A001234,4);wanted=oracle.reference(memory);models=[]
                for words in (self.retail,self.words):
                    model=oracle.ResetModel(window,memory,phase,entry);model.before[29]=oracle.STACK+phase+0x48
                    model.r[16]=model.before[16]=0x5A001234
                    model.code.update(zip(range(source.ENTRY,source.ENTRY+208,4),words))
                    model.code.update(zip(range(0x1509E3CC,0x1509E3DC,4),epilogue));model.run()
                    self.assertEqual(model.caller_args,[()]);self.assertEqual(oracle.public(model.memory),oracle.public(wanted));models.append(model)
                self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('ABI-window',actual_retail_sites=1,actual_caller_words=8,pairs=count,no_arguments=True,
            explicit_caller_frame_livein=True,full_caller_not_executed=True,numeric_V0_not_assumed=True)

    def test_07_independent_GNU_code_pointer_and_context_maps(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text();original=self.out/'original.s'
        original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>52I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];lines+=['.word 0x%08X'%(word&0xFFFF0000),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
                '-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        maps=((source.ENTRY,oracle.STATE,oracle.CONTEXT),(0x1621FFF4,0x80218004,0x98000),(0x18FFF000,0x8065FFFC,0xC0000));count=0
        for n,(entry,address,context) in enumerate(maps):
            anchors={'D_800D23B0':address};images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-map-%d.ld'%n);elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800D23B0=0x%X'%address,'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:208])
            self.assertEqual(*images);words=list(struct.unpack('>52I',images[0]));self.assertEqual(words,layout.relocate(self.normalized,self.moved,anchors))
            for case in self.cases[::19]+self.cases[-12:]:
                for phase in (0,8):
                    memory,_=oracle.fixture(case,phase,anchors,context);wanted=oracle.reference(memory,anchors)
                    model=oracle.ResetModel(words,memory,phase,entry).run();self.assertEqual(oracle.public(model.memory),oracle.public(wanted));count+=1
        self.receipt('GNU-maps',maps=maps,executed_mapped_cases=count,code_global_and_ordinary_or_alias_context_rebased=True,all2_bindings_independently_assembled=True)

    def test_08_corruption_controls(self):
        count=0
        for at in (0,32,116,207):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown parallel-reset'):layout.normalize(bytes(bad),self.bindings)
            count+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown parallel-reset'):layout.normalize(self.raw,bad)
            count+=1
        with patch.object(layout,'EARLY',{**layout.EARLY,4:3}):
            with self.assertRaisesRegex(ValueError,'Changed parallel-reset'):layout.normalize(self.raw,self.bindings)
        self.receipt('corruption-controls',raw_binding_recipe_controls=count+1)

    def test_09_actual_owner_padder_and_stale_manifest(self):
        out=self.root/integration.BUILD;result=integration.qualify(self.root,out);self.assertEqual(result['word_differences'],0)
        reader=csv.DictReader(io.StringIO((out/'qualified-guards.csv').read_text()));rows=list(reader)
        for index in (len(rows)-19,len(rows)-10,len(rows)-1):
            for field in ('expected','expected_relocations'):
                bad=[dict(r) for r in rows];bad[index][field]='0xFFFFFFFF' if field=='expected' else 'R_MIPS_26:'+source.FUNCTION
                text=io.StringIO();writer=csv.DictWriter(text,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
                path=self.out/('bad-%d-%s.csv'%(index,field));path.write_text(text.getvalue())
                with self.assertRaisesRegex(ValueError,'stale word patch' if field=='expected' else 'stale relocations'):
                    emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                        function_objects={'func_150891E8':out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        else:integration.audit(self.root,out)

    def test_10_actual_Make_first_image_and_image_corruptions(self):
        out=self.root/integration.BUILD;integration.make_shadow(self.root,out);self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        before=source.freeze(self.root,out)['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+208]
        expected=integration.predicted_image(before,truth)
        for at in (64,elf_slot_offset(before,source.ENTRY,208)+116,len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
