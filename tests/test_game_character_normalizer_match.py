"""Complete glyph lookup, first matches, O32 home and literal installation audit."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_character_normalizer_candidates as screen
from tools.experiments import game_extended_character_metrics_candidates as metrics
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK=guest.STACK


def fixture(table,word,phase=0,address=screen.TABLE):
    memory={STACK+i:0xA5 for i in range(-128,0x200)}
    memory.update({address+i:v for i,v in enumerate(table)})
    return memory


def reference(memory,word,phase=0,table=screen.TABLE):
    result=memory.copy();put(result,STACK+phase,word)
    events=[('W',STACK+phase,4,word&0xFFFFFFFF)]
    original=word&255;normalized=original-32 if 97<=original<123 else original
    if original==32:return result,events,96
    for index in range(95):
        value=read(result,table+index,1);events.append(('R',table+index,1,value))
        if value==normalized:return result,events,index
    return result,events,original


class LookupOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,word,phase=0,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,arguments=(word,),phase=phase,entry=entry,connected=connected)
    def record_call(self,target):
        assert target==screen.ENTRY
        self.calls.append((target,*self.arguments(1)))
        self.events.append(('CALL',target,tuple(self.arguments(1))))


class GameCharacterNormalizerMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-character-normalizer-match-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            makefile='conker/Makefile',assembly='conker/asm/6E770.s',
            table_data='conker/asm/data/2275E0.data.s',metrics_pool='conker/asm/data/23D570.rodata.s',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',undefined_symbols='conker/undefined_syms_auto.txt',
            layout='conker/retail_layout.us.txt')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='8677e241aee0ae98694ab04154d4d1949de586b49d86e64e110edc37cfb33473'
        assert cls.baseline['elf']=='1337dd11530d3ef13938f6cf3995e65acee4357cae88832059f50559aa7a7d07'
        assert cls.baseline['guards']=='9b08dabc9ccc24cfa82b40ec626d3f5f73a7521f89d5a118f8e62773ccfea168'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>68I',cls.rom,screen.ROM))
        cls.table=cls.rom[screen.TABLE_ROM:screen.TABLE_ROM+96]
        assert cls.table==(cls.before[elf_slot_offset(cls.before,screen.TABLE,96):][:96])
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rel=cls.meta['relocations'];cls.guarded=screen.normalize(cls.raw,cls.rel)
        cls.old_source=(cls.out/'before-source').read_text();cls.asm=(cls.out/'before-assembly').read_text()
        cls.guards=screen.guard_successor((cls.out/'before-guards').read_bytes())
        (cls.out/'guards.csv').write_bytes(cls.guards)
        header=(cls.out/'before-guards').read_bytes().splitlines(keepends=True)[0]
        (cls.out/'leaf-guards.csv').write_bytes(screen.guard_successor(header))
        body=cls.asm.split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        original='.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+',@function\n'+\
            screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n'
        cls.assemble('original',original)
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,
            word_patches_path=cls.out/'leaf-guards.csv',filename='generated_6E770'))
        cls.fitted=cls.link('fitted')
        cls.owners=[];run=subprocess.run
        def compact(command,*a,**k):
            if str(command[0]).endswith('/cc'):command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*a,**k)
        for stage,source in (('before',cls.old_source),('after',screen.install(cls.old_source))):
            with patch('subprocess.run',side_effect=compact):
                obj,warnings=compile_owner(cls.root,cls.out,source,'owner-'+stage)
            assert not warnings,warnings
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/('owner-'+stage+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=cls.root/'conker',check=True,capture_output=True)
            cls.owners.append(obj)

    @classmethod
    def link(cls,name,entry=screen.ENTRY,table=screen.TABLE):
        script=cls.out/(name+'-%X-%X.ld'%(entry,table));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%(name,table+value-screen.TABLE) for name,value in screen.SYMBOLS.items()],
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>65I',sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,word,table=None,phase=0,address=screen.TABLE,entry=screen.ENTRY,forms=None):
        table=self.table if table is None else table;memory=fixture(table,word,phase,address)
        expected=reference(memory,word,phase,address)
        forms=(self.retail[:65],self.raw,self.fitted) if forms is None else forms
        models=[LookupOracle(w,memory,word,phase,entry).run() for w in forms]
        for model in models:
            self.assertEqual((model.memory,model.events,model.r[2]),expected)
            self.assertEqual(model.calls,[])
        self.assertEqual((models[0].r,models[0].f),(models[-1].r,models[-1].f))
        return models

    def test_01_complete_shape_guards_all_bytes_and_first_matches(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(65,0,12,0))
        self.assertEqual(self.guarded,self.retail[:65]);self.assertEqual(self.fitted,self.retail[:65])
        self.assertEqual(self.link('original'),self.retail[:65]);self.assertEqual(self.retail[65:],[0,0,0])
        reached=set();cases=0
        for code,upper,phase in itertools.product(range(256),(0,0xA5123400,0xFFFFFF00),(0,8)):
            models=self.compare(upper|code,phase=phase);reached.update(models[0].visits);cases+=1
        for index,phase in itertools.product(range(95),(0,8)):
            table=bytearray([0xF1]*96);table[index]=0xF2
            models=self.compare(0xF2,table,phase);reached.update(models[0].visits)
            self.assertEqual(models[0].r[2],index);cases+=1
        for code,phase in itertools.product((0,32,97,122,0xF2),(0,8)):
            table=bytearray([0xF1]*96);table[95]=0xF2
            self.compare(code,table,phase);cases+=1
        table=bytearray([0xF1]*96);table[3]=table[94]=0xF2
        self.assertEqual(self.compare(0xF2,table)[0].r[2],3);cases+=1
        unreachable={screen.ENTRY+i*4 for i in (44,49,54,59)}
        self.assertEqual(reached,set(range(screen.ENTRY,screen.ENTRY+260,4))-unreachable)
        self.receipt('semantic',cases=cases,all61_reachable_words=True,four_original_unreachable_words_literal_exact=True,
            complete65_word_body_and_three_original_zero_tails=True,
            guarded_complete_state_raw_memory_events_return=True,all95_first_matches=True,
            duplicate_first_absent_original_lowercase_space_early_return=True,no_pool_frame_helpers=True)

    def test_02_private_home_aliases_and_independent_rebases(self):
        cases=0
        for phase,offset,word in itertools.product((0,8),(0,-12),(0,0x30313233,0xA5123461,0xFFFFFFFF)):
            address=STACK+phase+offset
            forms=tuple(self.link(name,screen.ENTRY,address) for name in ('original','selected','fitted'))
            self.compare(word,self.table,phase,address,forms=forms);cases+=1
        for entry,address in ((0x15207FFC,0x80107FFC),(0x15318004,0x80218004)):
            forms=tuple(self.link(name,entry,address) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[2])
            for code,phase in itertools.product((0,32,48,49,50,51,97,122,0xEA,0xF4,0xF2),(0,8)):
                self.compare(code,phase=phase,address=address,entry=entry,forms=forms);cases+=1
        self.receipt('homes-rebases',cases=cases,original_full_incoming_word_store_before_table_reads=True,
            links2_HI_LO_carries_and_table4_symbols=True,private_home_aliases_guest_only=True)

    def test_03_fired_access_faults_and_space_does_not_read_table(self):
        faults=0
        for word,phase in itertools.product((32,48,49,50,51,97,0xEA,0xF4,0xF2),(0,8)):
            memory=fixture(self.table,word,phase)
            full=LookupOracle(self.retail[:65],memory,word,phase).run()
            for index in range(full.accesses):
                models=[LookupOracle(w,memory,word,phase) for w in (self.retail[:65],self.fitted)]
                for model in models:
                    model.fault=index
                    with self.assertRaises(guest.AccessFault):model.run()
                    self.assertEqual(model.accesses,index)
                self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                    (models[1].memory,models[1].events,models[1].r,models[1].f));faults+=1
        memory=fixture(self.table,32)
        memory={a:v for a,v in memory.items() if not screen.TABLE<=a<screen.TABLE+96}
        for words in (self.retail[:65],self.raw,self.fitted):
            model=LookupOracle(words,memory,32).run();self.assertEqual(model.r[2],96)
            self.assertEqual(model.events,[('W',STACK,4,32)])
        self.receipt('faults',fired_pairs=faults,guarded_full_partial_state=True,space_has_one_store_no_read=True,
            raw_private_fault_registers_and_portable_hardware_faults_not_claimed=True)

    @staticmethod
    def negatives():
        return (
            ('lower',screen.SELECTED.replace('character >= 0x61','character >= 0x62'),97,0),
            ('upper',screen.SELECTED.replace('character < 0x7B','character < 0x7A'),122,0),
            ('space',screen.SELECTED.replace('return 0x60','return 0x61'),32,0),
            ('fallback',screen.SELECTED.replace('return original','return normalized'),97,1),
            ('short-table',screen.SELECTED.replace('index != 0x5F','index != 0x5B'),0xF2,2),
            ('duplicate',screen.SELECTED.replace('normalized == cursor[0]','index != 3 && normalized == cursor[0]'),0xF2,3),
        )

    def control_table(self,kind):
        table=bytearray(self.table)
        if kind:table[:]=bytes([0xF1]*96)
        if kind==2:table[94]=0xF2
        if kind==3:table[3]=table[94]=0xF2
        return table

    def test_04_effective_compiled_controls_and_guard_rejection(self):
        for name,body,word,kind in self.negatives():
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            table=self.control_table(kind);memory=fixture(table,word)
            expected=reference(memory,word)[2]
            model=LookupOracle(words,memory,word).run();self.assertNotEqual(model.r[2],expected,name)
        bad=list(self.raw);bad[6]^=1
        with self.assertRaises(AssertionError):screen.normalize(bad,self.rel)
        header=(self.out/'before-guards').read_bytes().splitlines(keepends=True)[0]
        rows=[row for row in screen.GUARD_ROWS if int(row[2],0)!=35*4]
        stream=io.StringIO(newline='');csv.writer(stream).writerows(rows)
        missing=self.out/'missing.csv';missing.write_bytes(header+stream.getvalue().encode('ascii'))
        self.assemble('missing',emit_padded_assembly(self.out/'selected.o',self.out/'slot.s',
            word_patches_path=missing,filename='generated_6E770'))
        words=self.link('missing');self.assertNotEqual(words,self.retail[:65])
        memory=fixture(self.control_table(3),0xF2)
        self.assertNotEqual(LookupOracle(words,memory,0xF2).run().r[2],3)
        self.receipt('controls',compiled_semantic6=True,stale_expected_word_rejected=True,
            missing_counter_guard_effective_public_mismatch=True)

    def test_05_complete_owner_seven_neighbors_pools_and_both_padders(self):
        def fingerprint(obj,name):
            text,functions,relocs=parse_object(obj);f=functions[name];a,b=f['value'],f['value']+f['size']
            return f['size'],text[a:b],{o-a:r for o,r in relocs.items() if a<=o<b}
        names=set(parse_object(self.owners[0])[1]);self.assertEqual(names,set(parse_object(self.owners[1])[1]))
        for name in names-{screen.FUNCTION}:self.assertEqual(fingerprint(self.owners[0],name),fingerprint(self.owners[1],name),name)
        self.assertEqual(normalized_pools(self.owners[0]),normalized_pools(self.owners[1]))
        self.assertEqual(fingerprint(self.owners[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes=[]
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed=[]
            for stage,obj in zip(('before','after'),self.owners):
                asm=self.out/(route+'-'+stage+'.s');guards=self.out/('before-guards' if stage=='before' else 'guards.csv')
                args=[str(obj),str(self.out/'before-layout'),'generated_6E770',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6E770.s'),str(asm),'--filename','generated_6E770']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(guards),
                    '--rodata-symbol',metrics.ANCHOR],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
                self.assertNotIn('.rodata',sections(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value'];expected=bytearray(parsed[0][0])
            self.assertEqual(fingerprint(self.out/(route+'-after.o'),screen.FUNCTION),
                fingerprint(self.out/'fitted.o',screen.FUNCTION))
            expected[start:start+272]=parsed[1][0][start:start+272]
            self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start<=o<start+272},
                {o:r for o,r in parsed[1][2].items() if not start<=o<start+272})
            for name in names-{screen.FUNCTION}:self.assertEqual(parsed[0][1][name],parsed[1][1][name])
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors7=True,all_other_bodies_extents_relocations_and_pools_exact=True,
            actual_no_unroll_GLOBAL_ASM_both_padders_existing_metrics_binding=True)

    def test_06_actual_call_and_return_mask_windows(self):
        cases=0
        for start,end in ((0x15041BD8,0x15041BE0),(0x15042968,0x15042974)):
            words=list(struct.unpack_from('>%dI'%((end-start)//4+1),self.rom,start-0x15000000+0x2D4B0))
            for word,phase in itertools.product(range(256),(0,8)):
                models=[];memory=fixture(self.table,word,phase)
                expected=reference(memory,word,phase)[2]
                for body in (self.retail[:65],self.fitted):
                    connected={screen.ENTRY+i*4:w for i,w in enumerate(body)}
                    connected[end+4]=0x03C00008;connected[end+8]=0
                    model=LookupOracle(words,memory,word,phase,start,connected)
                    model.tail=True;model.r[30]=model.before[30]=0xDEAD0000
                    model.run();models.append(model)
                    self.assertEqual(model.calls,[(screen.ENTRY,word)])
                    self.assertEqual(model.r[2],expected);self.assertEqual(model.r[3],expected&255)
                self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                    (models[1].memory,models[1].events,models[1].r,models[1].f));cases+=1
        self.receipt('call-windows',cases=cases,original_JAL_delay_store_and_return_mask=True,
            no_lookup_hook_synthetic_exit_not_full_formatter_or_measurer=True)

    def native_source(self,body):
        initial=','.join(str(v) for v in self.table)
        return NATIVE.replace('INITIAL_TABLE',initial)+body+NATIVE_MAIN

    def test_07_native32_full_C_table_canaries_and_effective_controls(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(screen.SELECTED),profile),(0,''))
        for name,body,word,kind in self.negatives():
            code,detail=self.run_native('native-negative-'+name,self.native_source(body))
            self.assertEqual(code,1,name);self.assertEqual(len(detail),3,name)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=2655,all_table_and_guard_canaries=True,
            actual_semantic_body_original_table_and_all95_forced_first_matches=True,effective_controls6=True,
            byte_narrowing_int_pointer4_no_private_home_hardware_claim=True)

    def test_08_literal_source_whole_ELF_guard_prefix_and_ten_inputs(self):
        before=(self.out/'before-source').read_text();current=(self.root/screen.SOURCE).read_text();changed=current!=before
        self.assertEqual(current,screen.install(before) if changed else before)
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,272)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if changed:
            struct.pack_into('>68I',expected,start,*self.retail);struct.pack_into('>I',expected,extent,260)
        self.assertEqual(actual,bytes(expected))
        self.assertEqual((self.root/self.paths['guards']).read_bytes(),self.guards if changed else (self.out/'before-guards').read_bytes())
        for name,path in self.paths.items():
            old=(self.out/('before-'+name)).read_bytes();self.assertEqual(hashlib.sha256(old).hexdigest(),self.baseline[name])
            if name not in ('source','elf','guards'):self.assertEqual((self.root/path).read_bytes(),old,name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=changed,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+272],actual[start:start+272])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            entire_ELF_literal_target_size_only=True,old_guard_prefix_and_exact12_rows=True,
            ten_other_inputs_exact=True,protected_data=data)

    def test_09_effective_stale_and_integrity_controls(self):
        for source in (screen.install(self.old_source),self.old_source+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError):screen.install(source)
        with self.assertRaises(AssertionError):screen.guard_successor(self.guards)
        rt,rb=Path.read_text,Path.read_bytes;source=self.root/screen.SOURCE;current=source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:current+'\n' if p==source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError):self.test_08_literal_source_whole_ELF_guard_prefix_and_ten_inputs()
        elf=self.root/self.paths['elf'];actual=elf.read_bytes();start=elf_slot_offset(actual,screen.ENTRY,272)
        extent=installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,start+264,start-4,extent+3,elf_slot_offset(actual,screen.TABLE,96)+94):
            wrong=bytearray(actual);wrong[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p==elf else rb(p)):
                with self.assertRaises(AssertionError):self.test_08_literal_source_whole_ELF_guard_prefix_and_ten_inputs()
        guards=self.root/self.paths['guards'];data=guards.read_bytes()
        with patch.object(Path,'read_bytes',lambda p:data+b'\n' if p==guards else rb(p)):
            with self.assertRaises(AssertionError):self.test_08_literal_source_whole_ELF_guard_prefix_and_ten_inputs()
        self.receipt('integrity-controls',source1_ELF5_guard1_stale_source2_duplicate_guard1=True,all_effective=True)


NATIVE=r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
static const u8 originalTable[96]={INITIAL_TABLE};
static struct {u32 before;u8 table[96];u32 after;} arena;
#define D_80085930 arena.table[0]
#define D_80085931 arena.table[1]
#define D_80085932 arena.table[2]
#define D_80085933 (arena.table+3)
static u8 wanted[96];
static int report(u32 a,u32 b,u32 c){u32 data[3]={a,b,c};int r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
static void reset(int mode,int index){
    arena.before=0xA51234FF;arena.after=0xF12345A5;
    for(int i=0;i<96;i++)arena.table[i]=mode?0xF1:originalTable[i];
    if(mode==2)arena.table[94]=0xF2;
    if(mode==3)arena.table[3]=arena.table[94]=0xF2;
    if(mode==4)arena.table[95]=0xF2;
    if(mode==5)arena.table[index]=0xF2;
    for(int i=0;i<96;i++)wanted[i]=arena.table[i];
}
static s32 reference(u8 input){
    u8 normalized=(input>=97&&input<123)?input-32:input;
    if(input==32)return 96;
    for(s32 i=0;i<95;i++)if(wanted[i]==normalized)return i;
    return input;
}
'''
NATIVE_MAIN=r'''
static int check(s32 input,u32 cases){
    s32 want=reference((u8)input),actual=func_15042C40((u8)input);
    if(actual!=want)return report(cases,(u32)actual,(u32)want);
    for(u32 i=0;i<96;i++)if(arena.table[i]!=wanted[i])return report(cases,1,i);
    if(arena.before!=0xA51234FF||arena.after!=0xF12345A5)return report(cases,2,0);
    return 0;
}
static int run(void){u32 cases=0;int result;
    if(sizeof(void *)!=4||sizeof(s32)!=4||sizeof(u8)!=1)return 2;
    for(s32 code=-128;code<384;code++)for(int mode=0;mode<5;mode++,cases++){
        reset(mode,0);result=check(code,cases);if(result)return result;
    }
    for(int i=0;i<95;i++,cases++){reset(5,i);result=check(0xF2,cases);if(result)return result;}
    return cases==2655?0:3;
}
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':
    unittest.main()
