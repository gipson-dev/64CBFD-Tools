"""Complete packed-peer lookup: numeric C, literal state, ABI and layout gates."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_peer_lookup_candidates as source
from tools.experiments import game_packed_peer_lookup_layout as layout
from tools.experiments import game_packed_peer_lookup_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_packed_peer_lookup_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.pad_generated_object import emit_padded_assembly


NATIVE=r'''
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
u8 *D_800D23C0;u32 D_80087380;
SOURCE_BODY
typedef struct {u32 args[3],count;u16 lengths[4],entries[4][8];u32 expected;} TestCase;
static const TestCase cases[]={CASES};
static u8 bytes[96] __attribute__((aligned(16))),saved[96];
void _start(void){
    u32 failure=0,n,i,j,v;const TestCase *c;PackedPeerRow *rows=(PackedPeerRow *)bytes;
    if(sizeof(void*)!=4 || sizeof(PackedPeerRow)!=24 || sizeof(u16)!=2)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++){
        c=cases+n;for(i=0;i<96;i++)bytes[i]=0xA5;
        D_80087380=c->count;D_800D23C0=bytes;
        for(i=0;i<c->count;i++){rows[i].count=c->lengths[i];for(j=0;j<c->lengths[i];j++)rows[i].entries[j]=c->entries[i][j];}
        for(i=0;i<96;i++)saved[i]=bytes[i];
        if((u32)func_1508ECC0(c->args[0],c->args[1],c->args[2])!=c->expected)failure=21;
        if(D_80087380!=c->count || D_800D23C0!=bytes)failure=21;
        for(i=0;i<96;i++)if(saved[i]!=bytes[i])failure=21;
    }
    D_80087380=1;D_800D23C0=bytes;rows[0].count=3;
    rows[0].entries[0]=0x1001;rows[0].entries[1]=0x2002;rows[0].entries[2]=0x1003;
    for(i=0;i<96;i++)saved[i]=bytes[i];
    for(v=0;!failure && v<65536;v++){
        if(func_1508ECC0(v,1,2)!=((v&15)==1?2:-1))failure=21;
        if(func_1508ECC0(1,v,2)!=((v==1||v==3)?2:-1))failure=21;
        if(func_1508ECC0(1,1,v)!=(v==1?3:v==2?2:-1))failure=21;
    }
    if(D_80087380!=1 || D_800D23C0!=bytes)failure=21;
    for(i=0;i<96;i++)if(saved[i]!=bytes[i])failure=21;
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


def state(model):return (model.r,model.f,model.lo,model.memory,model.events,model.calls,model.caller_args)


class PackedPeerLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={'D_80087380':oracle.COUNT,'D_800D23C0':oracle.TABLE}
        cls.words=layout.relocate(cls.normalized,cls.moved,cls.anchors)
        cls.retail=list(struct.unpack_from('>63I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def model(self,words,case,phase=0,entry=source.ENTRY):
        memory,args=oracle.fixture(case,phase);return oracle.LookupModel(words,memory,args,phase=phase,entry=entry)

    def test_01_complete_source_layout_and_origin_accounting(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(60,8,60,''))
        self.assertEqual(self.words,self.retail);self.assertEqual(len(self.moved),4)
        self.assertEqual(sorted(i for i in layout.origins() if i is not None),list(range(60)))
        self.assertEqual(sum(i is None for i in layout.origins()),3)
        guards=layout.private_guards(self.values['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        self.assertTrue(guards.startswith(self.values['conker/retail_word_patches.us.csv']))
        rows=[r for r in csv.DictReader(io.StringIO(guards.decode())) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(rows),60);self.assertEqual(sum(bool(r['insert_after']) for r in rows),3)
        self.assertTrue(all(r['omit']=='false' for r in rows))

    def test_02_independent_algorithm_complete_state_and_readonly_public_memory(self):
        visits=set();pairs=0
        for case in self.cases:
            for phase in (0,8):
                wanted=oracle.expected(case)&0xFFFFFFFF;original=self.model(self.retail,case,phase).run()
                normalized=self.model(self.words,case,phase).run();raw=self.model(self.raw_words,case,phase).run()
                self.assertEqual(state(original),state(normalized));self.assertEqual(original.r[2],wanted,case)
                before,_=oracle.fixture(case,phase)
                for model in (original,normalized,raw):
                    self.assertEqual(model.r[2],wanted,case);self.assertEqual(oracle.public(model.memory),oracle.public(before))
                    self.assertFalse(model.calls)
                visits.update(original.visits);pairs+=1
        self.receipt('functional-cases',cases=len(self.cases),phases=2,paired_literal_runs=pairs,raw_public_runs=pairs,
            retail_visited_words=len(visits),all63_words_compared_statically=True,public_bytes_unchanged=True)

    def test_03_fired_access_cuts_empty_gate_and_private_alias(self):
        cases=(oracle.Case((1,1,2),()),oracle.Case((1,1,2),((),)),oracle.Case((1,1,2),((0x1001,0x2002),)),
            oracle.Case((1,1,1),((0x1001,0x1001),)),oracle.Case((1,1,2),((0x1001,),(0x1001,0x2002))))
        count=0
        for case in cases:
            for phase in (0,8):
                run=self.model(self.retail,case,phase).run()
                if not case.rows:self.assertFalse(any(e[0]=='R' and e[1]==oracle.TABLE for e in run.events))
                for cut in range(run.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=self.model(words,case,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));count+=1
        for phase in (0,8):
            case=oracle.Case((0x00011001,0x20020001,2),((0,0,0,0),))
            memory,args=oracle.fixture(case,phase,arena=oracle.STACK+phase-8);models=[]
            for words in (self.retail,self.words):models.append(oracle.LookupModel(words,memory,args,phase=phase).run())
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(models[0].r[2],2)
        self.receipt('fired-cuts',pairs=count,all_requested_cuts_fired=True,caller_home_alias_pairs=2,
            aliases_guest_only=True,empty_count_does_not_read_table=True)

    def test_04_wide_counts_and_fullword_entry_abi(self):
        pairs=0
        for size in (0x8000,0xFFFF):
            case=oracle.Case((1,1,2),((0x1001,0x2002),));memory,args=oracle.fixture(case)
            oracle.put(memory,oracle.ARENA+2,size,2)
            for words in (self.retail,self.words):
                self.assertEqual(oracle.LookupModel(words,memory,args).run().r[2],2)
            pairs+=1
        for size in (0x10000,0x80000000,0xFFFFFFFF):
            case=oracle.Case((1,1,2),((),(),(),()));memory,args=oracle.fixture(case);oracle.put(memory,oracle.COUNT,size,4)
            states=[]
            for words in (self.retail,self.words):
                model=oracle.LookupModel(words,memory,args);model.fault=8
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,8);states.append(state(model))
            self.assertEqual(*states);pairs+=1
        self.receipt('wide-counts',guest_pairs=pairs,fullword_unsigned_row_count_and_unsigned_halfword_entry_count=True,
            large_row_count_probes_are_fired_prefixes_not_complete_iterations=True)

    def test_05_native32_numeric_fixture_corpus_and_all_halfword_views(self):
        number=lambda v:'0x%Xu'%(v&0xFFFFFFFF)
        rows=[]
        for case in self.cases:
            lengths=[len(row) for row in case.rows]+[0]*(4-len(case.rows))
            entries=[tuple(row)+(0,)*(8-len(row)) for row in case.rows]+[(0,)*8]*(4-len(case.rows))
            rows.append('{{%s},%s,{%s},{%s},%s}'%(','.join(map(number,case.arguments)),number(len(case.rows)),
                ','.join(map(number,lengths)),','.join('{'+','.join(map(number,row))+'}' for row in entries),number(oracle.expected(case))))
        template=NATIVE.replace('CASES',',\n'.join(rows));body=source.FITTED
        controls={'o0':body,'o2':body,'ubsan':body,
            'wrong-or':body.replace('(group << 12) + value','(group << 12) | value'),
            'wrong-self':body.replace(' && peerIndex != keyIndex',''),
            'wrong-mask':body.replace(' & 0xFFF',''),
            'wrong-fallback':body.replace('                return -1;','                break;')}
        exits={}
        for name,unit in controls.items():
            if name not in ('o0','o2','ubsan'):self.assertNotEqual(unit,body)
            path=self.out/('native-'+name+'.c');path.write_text(template.replace('SOURCE_BODY',unit));exe=path.with_suffix('')
            command=[*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            result=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True);want=0 if name in ('o0','o2','ubsan') else 21
            self.assertEqual((result.returncode,result.stdout,result.stderr),(want,'',''),name);exits[name]=result.returncode
        self.receipt('native-cases',fixture_cases=len(self.cases),halfword_views=3,values_per_view=65536,
            extra_sweep_calls_per_positive=196608,public_bytes_checked_per_fixture=96,exits=exits)

    def test_06_corruption_controls_and_static_reference_boundary(self):
        for at in (0,8,40,239):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown packed-peer'):layout.normalize(bytes(bad),self.bindings)
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_LO16','D_80087380')]
            if bad==self.bindings:bad[at]=[('R_MIPS_HI16','D_800D23C0')]
            with self.assertRaisesRegex(ValueError,'Unknown packed-peer'):layout.normalize(self.raw,bad)
        bad=deepcopy(layout.GP);bad[19]={13:25}
        with patch.object(layout,'GP',bad):
            with self.assertRaisesRegex(ValueError,'Changed peer layout'):layout.normalize(self.raw,self.bindings)
        rom=self.values['conker/conker.us.bin']
        words=struct.unpack('>%dI'%(len(rom)//4),rom)
        self.assertNotIn(source.ENTRY,words);self.assertNotIn(0x0D423B30,words)
        self.receipt('reference-boundary',named_direct_callers_found=0,aligned_address_and_JAL_hits=0,
            indirect_or_computed_callers_not_excluded=True,source_and_binding_controls=9)

    def test_07_actual_owner_profiles_padder_and_stale_manifest_controls(self):
        out=self.root/integration.BUILD;result=integration.qualify(self.root,out)
        self.assertEqual(result['word_differences'],0)
        good=(out/'qualified-guards.csv').read_bytes();reader=csv.DictReader(io.StringIO(good.decode()));rows=list(reader)
        for index in (len(rows)-60,len(rows)-56,len(rows)-1):
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

    def test_08_independent_GNU_maps_execute_code_globals_and_rows(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        original=self.out/'original.s';original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>63I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];lines+=['.word 0x%08X'%(word&0xFFFF0000),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
                '-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        maps=((source.ENTRY,oracle.COUNT,oracle.TABLE,oracle.ARENA),(0x1621FFF4,0x8020FFF4,0x80318004,0x94000),
            (0x18FFF000,0x80428004,0x8053FFFC,0x98000));count=0
        selected=self.cases[::28]+self.cases[-15:]
        for n,(entry,count_address,table_address,arena) in enumerate(maps):
            anchors={'D_80087380':count_address,'D_800D23C0':table_address};images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-map-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:252])
            self.assertEqual(*images);words=list(struct.unpack('>63I',images[0]));self.assertEqual(words,layout.relocate(self.normalized,self.moved,anchors))
            for case in selected:
                for phase in (0,8):
                    memory,args=oracle.fixture(case,phase,count_address,table_address,arena)
                    model=oracle.LookupModel(words,memory,args,phase=phase,entry=entry).run()
                    self.assertEqual(model.r[2],oracle.expected(case)&0xFFFFFFFF)
                    self.assertEqual(oracle.public(model.memory),oracle.public(memory));count+=1
        self.receipt('GNU-maps',maps=maps,executed_mapped_cases=count,code_globals_and_row_pointer_rebased=True,
            all4_bindings_independently_assembled=True)

    def test_09_synthetic_fullword_call_windows_and_original_argument_homes(self):
        entry=0x16200000;window=[0x0D423B30,0x02C03025,0x02E00008,0];count=0
        cases=[self.cases[i] for i in (0,1,2,3,4,100,500,1000)]+self.cases[-15:]
        for case in cases:
            for phase in (0,8):
                memory,args=oracle.fixture(case,phase);models=[]
                for words in (self.retail,self.words):
                    model=oracle.LookupModel(window,memory,args,phase=phase,entry=entry)
                    model.r[22]=model.before[22]=args[2];model.r[23]=model.before[23]=0xDEAD0000
                    model.before[31]=entry+8;model.code.update(zip(range(source.ENTRY,source.ENTRY+252,4),words));model.run()
                    self.assertEqual(model.caller_args,[(source.ENTRY,*args)])
                    self.assertEqual(model.r[2],oracle.expected(case)&0xFFFFFFFF)
                    self.assertEqual(tuple(oracle.read(model.memory,oracle.STACK+phase+i*4,4) for i in range(3)),args)
                    models.append(model)
                self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('ABI-windows',pairs=count,synthetic_not_retail_caller=True,third_fullword_set_in_delay_slot=True,
            all_original_argument_homes_checked=True)

    def test_10_actual_Make_first_image_and_literal_corruption_checks(self):
        out=self.root/integration.BUILD;integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        before=source.freeze(self.root,out)['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+252]
        expected=integration.predicted_image(before,truth)
        for at in (64,integration.elf_slot_offset(before,source.ENTRY,252)+100,len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
