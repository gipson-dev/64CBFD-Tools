"""Round-robin selector: numeric search, signed guest edges, ABI and layout."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_round_robin_slot_candidates as source
from tools.experiments import game_round_robin_slot_layout as layout
from tools.experiments import game_round_robin_slot_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_round_robin_slot_oracle as oracle
from tools.tests.test_game_packed_peer_lookup_match import state
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
s32 D_800D23B0;s8 D_8008FD8C;u16 D_800D18A0;
u8 D_800CC2D0[27*0x32C] __attribute__((aligned(16)));
SOURCE_BODY
typedef struct {s32 cursor,count;u16 mask;u8 pattern;u32 expected,cursorAfter;} Case;
static const Case cases[]={CASES};
static u8 context[0x1710] __attribute__((aligned(16))),nodes[27][0x90] __attribute__((aligned(16)));
static u8 savedContext[0x1710],savedActors[27*0x32C],savedNodes[27][0x90];
static u32 failure;
static u32 stage(u32 index,u32 pattern){
    if(pattern<4)return pattern==0?0:pattern==1?1:pattern==2?3:7;
    if(pattern<8)return index%4==pattern-4?7:0;
    return ((index*17+pattern*13)^(index>>2))&7;
}
static void setup(const Case *c){
    u32 i,j,value;
    D_800D23B0=(s32)context;D_8008FD8C=c->count;D_800D18A0=c->mask;
    for(i=0;i<sizeof(context);i++)context[i]=0xA5;context[0x1702]=(u8)c->cursor;
    for(i=0;i<sizeof(D_800CC2D0);i++)D_800CC2D0[i]=0xA5;
    for(i=0;i<27;i++){
        for(j=0;j<0x90;j++)nodes[i][j]=0xA5;
        value=i<26?stage(i,c->pattern):0;
        *(u32 *)(D_800CC2D0+i*0x32C)=value&1?0x12340000+i:0;
        *(u8 **)(D_800CC2D0+i*0x32C+0x31C)=value&2?nodes[i]:0;
        nodes[i][0x84]=value&4?(i&1?0x80:0xFF):0;
    }
    for(i=0;i<sizeof(context);i++)savedContext[i]=context[i];
    for(i=0;i<sizeof(D_800CC2D0);i++)savedActors[i]=D_800CC2D0[i];
    for(i=0;i<27;i++)for(j=0;j<0x90;j++)savedNodes[i][j]=nodes[i][j];
}
static void checkMemory(void){
    u32 i,j;
    for(i=0;i<sizeof(context);i++)if(i!=0x1702 && context[i]!=savedContext[i])failure=21;
    for(i=0;i<sizeof(D_800CC2D0);i++)if(D_800CC2D0[i]!=savedActors[i])failure=21;
    for(i=0;i<27;i++)for(j=0;j<0x90;j++)if(nodes[i][j]!=savedNodes[i][j])failure=21;
}
void _start(void){
    u32 n,v,available,expected;const Case *c;Case sweep={-1,26,0,3,0,0};
    if(sizeof(void*)!=4 || sizeof(s8)!=1)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++){
        c=cases+n;setup(c);
        if((u32)func_1508C9CC()!=c->expected || context[0x1702]!=c->cursorAfter)failure=21;
        if(D_800D23B0!=(s32)context || D_8008FD8C!=c->count || D_800D18A0!=c->mask)failure=21;
        checkMemory();
    }
    setup(&sweep);
    for(v=0;!failure && v<65536;v++){
        context[0x1702]=255;D_800D18A0=v;available=(~v)&65535;
        expected=available?(u32)__builtin_ctz(available):16;
        if((u32)func_1508C9CC()!=expected || context[0x1702]!=expected)failure=21;
        if(D_800D23B0!=(s32)context || D_8008FD8C!=26 || D_800D18A0!=v)failure=21;
    }
    checkMemory();
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class RoundRobinSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.words=layout.relocate(cls.normalized,cls.moved,oracle.DEFAULT)
        cls.retail=list(struct.unpack_from('>47I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all_words_origins_bindings_and_guards(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(47,0,14,''))
        self.assertEqual(self.words,self.retail);self.assertEqual(sorted(layout.origins()),list(range(47)))
        self.assertEqual(len(self.moved),8);self.assertEqual(sum(self.moved.get(at)!=entries for at,entries in self.bindings.items()),3)
        guards=layout.private_guards(self.values['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        self.assertTrue(guards.startswith(self.values['conker/retail_word_patches.us.csv']))
        rows=[r for r in csv.DictReader(io.StringIO(guards.decode())) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(rows),14);self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in rows))

    def test_02_numeric_reference_and_complete_literal_state(self):
        visits=set();pairs=0
        for case in self.cases:
            for phase in (0,8):
                memory=oracle.fixture(case,phase);wanted,after=oracle.reference(memory)
                models=[oracle.SlotModel(words,memory,phase).run() for words in (self.retail,self.words,self.raw_words)]
                self.assertEqual(state(models[0]),state(models[1]),case)
                for model in models:
                    self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)),case);self.assertFalse(model.calls)
                visits.update(models[0].visits);pairs+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+188,4)),visits)
        self.receipt('functional-cases',cases=len(self.cases),phases=2,paired_literal_runs=pairs,raw_public_same_corpus=pairs,
            visited_words=47,all256_cursor_and_count_bytes_in_guest=True,wide_guest_backing_not_portable_array_claim=True)

    def test_03_fired_access_cuts_and_cached_state_aliases(self):
        count=0
        for case in (oracle.Case(-1,0,0,0),oracle.Case(-1,4,0,0),oracle.Case(3,4,0,1),
                oracle.Case(0,4,0,2),oracle.Case(-1,4,0,3),oracle.Case(3,4,0xFFFF,3),oracle.Case(1,4,0,6)):
            for phase in (0,8):
                memory=oracle.fixture(case,phase);run=oracle.SlotModel(self.retail,memory,phase).run()
                for cut in range(run.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=oracle.SlotModel(words,memory,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));count+=1
        aliases=0
        for at in (oracle.COUNT,oracle.MASK,oracle.MASK+1,oracle.STATE,oracle.ACTORS,oracle.NESTED+128*256+0x84):
            for phase in (0,8):
                memory=oracle.fixture(oracle.Case(-1,4,0,3),phase)
                oracle.put(memory,oracle.STATE,(at-0x1702)&0xFFFFFFFF,4)
                wanted,after=oracle.reference(memory);models=[oracle.SlotModel(words,memory,phase).run() for words in (self.retail,self.words)]
                self.assertEqual(state(models[0]),state(models[1]));self.assertEqual((models[0].r[2],models[0].memory),(wanted,after));aliases+=1
        self.receipt('fired-cuts',pairs=count,all_requested_cuts_fired=True,guest_alias_pairs=aliases,
            cached_state_pointer_and_delayed_single_byte_store=True)

    def test_04_native32_numeric_cases_mask_sweep_and_effective_negatives(self):
        rows=[]
        for case in oracle.native_cases():
            result,memory=oracle.reference(oracle.fixture(case));cursor=oracle.read(memory,oracle.CONTEXT+0x1702,1)
            rows.append('{%d,%d,%d,%d,0x%Xu,%d}'%(case.cursor,case.count,case.mask,case.pattern,result,cursor))
        body=source.FITTED;template=NATIVE.replace('CASES',',\n'.join(rows))
        controls={'o0':body,'o2':body,'ubsan':body,
            'wrong-wrap':body.replace('slot >= count','slot > count'),
            'wrong-ready':body.replace('nested[0x84] != 0','1'),
            'wrong-mask':body.replace('!(D_800D18A0 & (1U << slot))','1'),
            'wrong-first':body.replace('                attempts = count;\n',''),
            'wrong-entry':body.replace('    do {','    while (attempts < count) {').replace('    } while (attempts < count);','    }')}
        exits={}
        for name,unit in controls.items():
            if name not in ('o0','o2','ubsan'):self.assertNotEqual(unit,body)
            path=self.out/('native-'+name+'.c');path.write_text(template.replace('SOURCE_BODY',source.DECLARATIONS+unit));exe=path.with_suffix('')
            result=subprocess.run([*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0 if name in ('o0','o2','ubsan') else 21,'',''),name);exits[name]=result.returncode
        self.receipt('native-cases',fixtures=len(rows),all_mask_values=65536,extra_calls_per_positive=65536,exits=exits,
            native_indices_0_through25=True,extra_slot26_backing_for_wrong_wrap_negative_only=True,
            actor_nodes_and_other_context_bytes_unchanged=True,arbitrary_negative_indices_guest_only=True)

    def test_05_actual_returning_caller_window(self):
        rom=self.values['conker/conker.us.bin'];entry=0x1509E488
        window=list(struct.unpack_from('>4I',rom,0xCB938));epilogue=list(struct.unpack_from('>3I',rom,0xCBADC))
        self.assertEqual(window,[0x0D423273,0,0x10000066,0x8FBF0014]);self.assertEqual(epilogue,[0x27BD0018,0x03E00008,0])
        count=0
        for case in self.cases[::67]+self.cases[-12:]:
            for phase in (0,8):
                memory=oracle.fixture(case,phase);oracle.put(memory,oracle.STACK+phase+0x14,0xDEAD0000,4)
                wanted,after=oracle.reference(memory);models=[]
                for words in (self.retail,self.words):
                    model=oracle.SlotModel(window,memory,phase,entry);model.before[29]=oracle.STACK+phase+0x18
                    model.code.update(zip(range(source.ENTRY,source.ENTRY+188,4),words))
                    model.code.update(zip(range(0x1509E62C,0x1509E638,4),epilogue));model.run()
                    self.assertEqual(model.caller_args,[()]);self.assertEqual((model.r[2],model.memory),(wanted,after));models.append(model)
                self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('ABI-window',actual_retail_sites=1,actual_caller_words=7,pairs=count,no_arguments=True,
            result_propagates_through_actual_branch_RA_restore_and_epilogue=True,full_caller_not_executed=True)

    def test_06_independent_GNU_maps_execute_all_bindings(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text();original=self.out/'original.s'
        original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>47I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];lines+=['.word 0x%08X'%(word&0xFFFF0000),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
                '-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        maps=((source.ENTRY,oracle.STATE,oracle.COUNT,oracle.MASK,oracle.ACTORS,oracle.CONTEXT,oracle.NESTED),
            (0x1621FFF4,0x80218004,0x8032FFFF,0x8043FFFE,0x80540000,0x98000,0xA0000),
            (0x18FFF000,0x8065FFFC,0x80768004,0x8087FFFE,0x80980000,0xC0000,0xD0000))
        count=0
        for n,(entry,state_address,count_address,mask,actors,context,nested) in enumerate(maps):
            anchors=dict(zip(oracle.DEFAULT,(state_address,count_address,mask,actors)));images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-map-%d.ld'%n);elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:188])
            self.assertEqual(*images);words=list(struct.unpack('>47I',images[0]));self.assertEqual(words,layout.relocate(self.normalized,self.moved,anchors))
            for case in self.cases[::41]+self.cases[-12:]:
                for phase in (0,8):
                    memory=oracle.fixture(case,phase,anchors,context,nested);wanted,after=oracle.reference(memory,anchors)
                    model=oracle.SlotModel(words,memory,phase,entry).run();self.assertEqual((model.r[2],model.memory),(wanted,after));count+=1
        self.receipt('GNU-maps',maps=maps,executed_mapped_cases=count,code_all_globals_context_and_nodes_rebased=True,all8_bindings_independently_assembled=True)

    def test_07_corruption_controls(self):
        count=0
        for at in (0,28,64,187):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown round-robin'):layout.normalize(bytes(bad),self.bindings)
            count+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown round-robin'):layout.normalize(self.raw,bad)
            count+=1
        with patch.object(layout,'GP',{3:6,5:3,6:5}):
            with self.assertRaisesRegex(ValueError,'Changed round-robin'):layout.normalize(self.raw,self.bindings)
        self.receipt('corruption-controls',raw_binding_recipe_controls=count+1)

    def test_08_actual_owner_padder_and_stale_guards(self):
        out=self.root/integration.BUILD;result=integration.qualify(self.root,out);self.assertEqual(result['word_differences'],0)
        reader=csv.DictReader(io.StringIO((out/'qualified-guards.csv').read_text()));rows=list(reader)
        for index in (len(rows)-14,len(rows)-8,len(rows)-1):
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

    def test_09_actual_Make_first_image_and_corruptions(self):
        out=self.root/integration.BUILD;integration.make_shadow(self.root,out);self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        before=source.freeze(self.root,out)['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+188]
        expected=integration.predicted_image(before,truth)
        for at in (64,elf_slot_offset(before,source.ENTRY,188)+28,len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
