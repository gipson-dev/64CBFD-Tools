"""Complete first-match query, byte ABI, aliases, faults and installation."""
import hashlib
import csv
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_record_index_query_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.game_owner_pool import normalized_pools

S = screen.SYMBOLS
STACK, RECORDS, ACTOR = guest.STACK, 0x24000, 0x28000
DEFINED = b'func_15083E0C = 0x15083E0C; // type:func defined:true'
ASSIGNMENT = b'func_15083E0C = 0x15083E0C;'
OLD_LAYOUT = b'game,generated_AEB40,func_15083DA0,0x15083DA0,0x15083E90'
NEW_LAYOUT = b'game,generated_AEB40,func_15083DA0,0x15083DA0,0x15083E0C'
TARGET_LAYOUT = b'game,generated_AEB40,func_15083E0C,0x15083E0C,0x15083E90'


def fixture(selector=7,count=3,position=1,duplicate=False,records=RECORDS,symbols=S):
    memory={STACK+i:0xA5 for i in range(-0x100,0x100)}
    for i in range(4): memory[symbols['D_800D20FC']+i]=0xA5
    memory[symbols['D_800D2100']]=0xA5
    for i in range(count+2):
        address=(records+i*48+40)&0xFFFFFFFF
        memory[address]=(selector+1)&255
        memory[(address-1)&0xFFFFFFFF]=0
        memory[(records+i*48+2)&0xFFFFFFFF]=0xA5
    if 0<=position<count:
        memory[(records+position*48+40)&0xFFFFFFFF]=selector&255
        if duplicate: memory[(records+(count-1)*48+40)&0xFFFFFFFF]=selector&255
    put(memory,symbols['D_800D20FC'],records)
    put(memory,symbols['D_800D2100'],count,1)
    return memory


def reference(memory,selector=7,symbols=S,phase=0):
    memory=memory.copy(); events=[]
    def get(address,size):
        assert all(address+i in memory for i in range(size)), ('reference unmapped read',address,size)
        value=read(memory,address,size); events.append(('R',address,size,value)); return value
    value=selector&0xFFFFFFFF
    put(memory,STACK+phase,value); events.append(('W',STACK+phase,4,value))
    selector=value&255; result=0xFFFFFFFF
    if selector:
        count=get(symbols['D_800D2100'],1)
        if count:
            records=get(symbols['D_800D20FC'],4)
            for i in range(count):
                if get((records+i*48+40)&0xFFFFFFFF,1)==selector:
                    result=i; break
    return memory,events,result


class IndexOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,selector=7,symbols=S,phase=0,entry=screen.ENTRY):
        super().__init__(words,memory,arguments=(selector,),phase=phase,entry=entry)
    def execute(self,word):
        if word>>26==32: CopyOracle.execute(self,word)
        else: super().execute(word)
    def hook(self,target): raise AssertionError(('unexpected query call',target))


class GameRecordIndexQueryTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-index-query-test'; cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text(); hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        if not (cls.out/'census-baseline.json').exists():
            data=(cls.root/'conker/retail_layout.us.txt').read_bytes()
            assert OLD_LAYOUT in data and TARGET_LAYOUT not in data
            (cls.out/'before-layout').write_bytes(data)
            (cls.out/'census-baseline.json').write_text(json.dumps(
                dict(layout_sha256=hashlib.sha256(data).hexdigest()),indent=2)+'\n')
        cls.census_baseline=json.loads((cls.out/'census-baseline.json').read_text())
        assert hashlib.sha256((cls.out/'before-layout').read_bytes()).hexdigest()==cls.census_baseline['layout_sha256']
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>33I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        slot=cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_AEB40'))
    @classmethod
    def link(cls,name,symbols=S,entry=screen.ENTRY):
        script=cls.out/('%s-%X.ld'%(name,entry)); elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>33I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):
        if name=='baseline': raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**{k:v for k,v in settings.items() if k!='entry'})
        models=[IndexOracle(w,memory,**settings).run() for w in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((model.memory,model.events,model.r[2]),expected); self.assertEqual(model.calls,[])
        self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
        return models
    def test_01_complete_direct_shape_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(33,0,0,0,''))
        self.assertEqual(self.raw,self.retail); self.assertEqual(self.raw[0],0xAFA40000)
        for name in ('original','selected','padded'): self.assertEqual(self.link(name),self.retail)
        _,functions,relocations=parse_object(self.out/'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'],132); self.assertEqual(len(relocations),4)
        self.receipt('shape',words=33,frame=0,direct_match=True,new_guards=0,relocations=4,
            original_full_word_argument_home_and_independent_assembly_padding_exact=True)
    def test_02_independent_byte_domains_first_duplicates_and_boundaries(self):
        cases=0; coverage=set()
        for selector,count,path,phase in itertools.product(range(256),(0,1,2,128,255),range(4),(0,8)):
            position=(-1,0,count//2,count-1)[path]
            memory=fixture(selector,count,position,duplicate=path==2)
            models=self.compare(memory,selector=selector,phase=phase)
            coverage.update(models[0].visits); cases+=1
        for selector,upper in itertools.product(range(256),(0x100,0xFFFF0000,0x80000000,0x7FFFFF00)):
            self.compare(fixture(selector,3,2),selector=upper|selector); cases+=1
        # Every count byte is interpreted as unsigned, not just the selected boundaries.
        for count in range(256):
            self.compare(fixture(255,count,count-1),selector=255); cases+=1
        for records,position,phase in itertools.product(
                (0xFFFFFFD8,0xFFFFFFC8,0x7FFFFFF0,0x80000010),(-1,0,2),(0,8)):
            self.compare(fixture(count=3,position=position,records=records),phase=phase); cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+132,4)))
        self.receipt('guest',cases=cases,executions=cases*2,reached_words=33,
            all_selectors_counts_full_upper_argument_words_first_duplicate_and_last_matches=True,
            complete_memory_access_order_return_and_GP_FPR_preservation=True,
            wrapped_record_pointer_cases_guest_only=True)
    def test_03_argument_home_aliases_short_circuits_and_fired_full_faults(self):
        cases=[]
        for selector,count,position in ((0,255,-1),(7,0,-1),(7,1,-1),(7,3,2),(255,255,254)):
            cases.append((fixture(selector,count,position),dict(selector=selector)))
        memory=fixture(0)
        for address in list(memory):
            if address>=0x80000000: del memory[address]
        cases.append((memory,dict(selector=0)))
        memory=fixture(count=0)
        for i in range(4): del memory[S['D_800D20FC']+i]
        cases.append((memory,{}))
        memory=fixture(count=3,position=0)
        del memory[RECORDS+48+40]
        cases.append((memory,{}))
        faults=0
        for phase in (0,8):
            varied=list(cases)
            home=STACK+phase
            symbols=dict(D_800D2100=home+3,D_800D20FC=S['D_800D20FC'])
            varied.append((fixture(selector=7,count=1,position=0,symbols=symbols),dict(symbols=symbols)))
            symbols=dict(D_800D2100=S['D_800D2100'],D_800D20FC=home)
            varied.append((fixture(selector=7,count=2,position=1,records=0x240007,symbols=symbols),
                dict(selector=0x240007,symbols=symbols)))
            varied.append((fixture(count=2,position=1,records=home-40),{}))
            for memory,settings in varied:
                symbols=settings.get('symbols',S)
                forms=tuple(self.link(n,symbols) for n in ('original','selected')) if symbols!=S else (self.retail,self.raw)
                models=self.compare(memory,forms=forms,phase=phase,**settings)
                for index in range(models[0].accesses):
                    pair=[IndexOracle(w,memory,phase=phase,**settings) for w in forms]
                    for model in pair:
                        model.fault=index
                        with self.assertRaises(guest.AccessFault): model.run()
                        self.assertEqual(model.accesses,index)
                    self.assertEqual((pair[0].memory,pair[0].events,pair[0].calls),
                        (pair[1].memory,pair[1].events,pair[1].calls)); faults+=1
        self.receipt('aliases',cases=(len(cases)+3)*2,executions=(len(cases)+3)*4,
            fired_fault_pairs=faults,private_home_aliases_count_pointer_and_record_fields=True,
            zero_selector_skips_unmapped_globals_zero_count_skips_pointer_first_match_stops=True)
    def test_04_rebased_control_addresses_and_signed_low_carries(self):
        cases=0
        for entry,count,pointer in ((0x15207FF0,0x80117FFC,0x80128004),
                (0x15308004,0x80218004,0x80227FFC),(0x15417FFC,0x80327FFC,0x80338004)):
            symbols=dict(zip(S,(count,pointer)))
            forms=tuple(self.link(n,symbols,entry) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for selector,size,position in ((0,3,1),(7,0,-1),(7,3,-1),(7,3,0),(255,255,254)):
                self.compare(fixture(selector,size,position,symbols=symbols),forms=forms,
                    selector=selector,symbols=symbols,entry=entry); cases+=1
        self.receipt('links',symbol_sets=3,links=9,cases=cases,executions=cases*3,
            both_control_HI_LO_pairs_independently_rebased=True)
    def test_05_actual_copied_owner_and_both_production_padding_routes(self):
        before=(self.out/'before-source').read_text(); objects=[]; warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name); warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj)
        self.assertEqual(warnings,[[],[]]); parsed=[parse_object(o) for o in objects]
        def fingerprint(data,name):
            text,functions,relocations=data; f=functions[name]; start,end=f['value'],f['value']+f['size']
            return f['size'],text[start:end],{o-start:v for o,v in relocations.items() if start<=o<end}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION: self.assertEqual(fingerprint(parsed[0],name),fingerprint(parsed[1],name),name)
        self.assertEqual(fingerprint(parsed[1],screen.FUNCTION),fingerprint(parse_object(self.out/'selected.o'),screen.FUNCTION))
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for route in ('layout','generated'):
            padded=[]
            for i,obj in enumerate(objects):
                asm=self.out/('owner-%s-%d.s'%(route,i))
                if route=='layout':
                    layout=self.out/'before-layout' if i==0 else self.root/'conker/retail_layout.us.txt'
                    args=['pad_c_object.py',str(obj),str(layout),'generated_AEB40',str(asm)]
                else:
                    args=['pad_generated_object.py',str(obj),str(self.root/'conker/asm/AEB40.s'),str(asm),
                        '--filename','generated_AEB40','--rodata-symbol','jtbl_8009CC40_game']
                subprocess.run(['python3',str(self.root/'tools'/args[0]),*args[1:],
                    '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                padded.append(parse_object(asm.with_suffix('.o')))
            start=padded[1][1][screen.FUNCTION]['value']; expected=bytearray(padded[0][0])
            expected[start:start+132]=padded[1][0][start:start+132]; self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<start+132},
                {o:v for o,v in padded[1][2].items() if not start<=o<start+132})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            all_neighbor_bytes_extents_relocations_pools_guard_fingerprints_exact=True)
    def test_06_effective_fresh_compiler_semantic_controls(self):
        controls=(
            ('zero','return -1;','return 0;',fixture(selector=0),dict(selector=0)),
            ('selector','u8 selector','u32 selector',fixture(),dict(selector=0x107)),
            ('field','[0x28]','[0x27]',fixture(count=1,position=0),{}),
            ('comparison','== selector','!= selector',fixture(count=3,position=1),{}),
            ('bound','i < D_800D2100','i <= D_800D2100',fixture(count=1,position=1),{}),
            ('count','extern u8 D_800D2100','extern s8 D_800D2100',fixture(count=255,position=254),{}))
        for name,old,new,memory,settings in controls:
            if name=='bound': put(memory,RECORDS+48+40,7,1)
            if name in ('field','count'):
                from unittest.mock import patch
                target='RECORD' if name=='field' else 'DECLARATIONS'
                with patch.object(screen,target,getattr(screen,target).replace(old,new)):
                    _,words=screen.compile_candidate(self.root,self.out,'negative-'+name)
            else:
                _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            self.assertNotEqual(words,self.raw)
            correct=IndexOracle(self.raw,memory,**settings).run()
            wrong=IndexOracle(words,memory,**settings).run()
            self.assertNotEqual(correct.r[2],wrong.r[2],name)
        self.receipt('negative',fresh_IDO_controls=len(controls),all_effective=True)
    def test_07_native32_full_domains_and_effective_negative(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.RECORD+NATIVE_TABLE+
                screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,[5120,0,0]))
        bad=screen.SELECTED.replace('return -1;','return 0;')
        result,_=self.run_native('native-negative',NATIVE_PREFIX+screen.RECORD+NATIVE_TABLE+bad+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=5120,executions=10240,profiles=['O2','O0'],
            record_pointer_integer_widths_checked=True,effective_negative=1,
            globals_and_record_data_unchanged=True,private_home_faults_guest_only=True)
    def test_08_immutable_baselines_and_whole_linked_installation(self):
        with self.assertRaisesRegex(ValueError,'immutable'): self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('linked',installed=False); return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        expected=bytearray(self.before)
        struct.pack_into('>33I',expected,elf_slot_offset(self.before,screen.ENTRY,132),*self.retail)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12); struct.pack_into('>I',expected,extent,132)
        defined=DEFINED in (self.root/self.paths['symbols']).read_bytes()
        if defined:
            self.assertEqual(struct.unpack_from('>H',self.before,extent+6)[0],0xFFF1)
            struct.pack_into('>H',expected,extent+6,5)
        actual=(self.root/self.paths['elf']).read_bytes(); self.assertEqual(bytes(expected),actual)
        for name in ('guards','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        if not defined:
            for name in ('progress','symbols','undefined'):
                self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        else:
            before_symbols=(self.out/'before-symbols').read_bytes()
            symbols=(self.root/self.paths['symbols']).read_bytes()
            self.assertTrue(symbols.startswith(before_symbols)); self.assertEqual(symbols[len(before_symbols):].strip(),DEFINED)
            before_undefined=(self.out/'before-undefined').read_bytes()
            lines=before_undefined.splitlines(keepends=True)
            self.assertEqual(sum(line.rstrip(b'\r\n')==ASSIGNMENT for line in lines),1)
            self.assertEqual((self.root/self.paths['undefined']).read_bytes(),
                b''.join(line for line in lines if line.rstrip(b'\r\n')!=ASSIGNMENT))
            before_layout=(self.out/'before-layout').read_bytes()
            newline=b'\r\n' if b'\r\n' in before_layout else b'\n'
            self.assertEqual((self.root/'conker/retail_layout.us.txt').read_bytes(),
                before_layout.replace(OLD_LAYOUT,NEW_LAYOUT+newline+TARGET_LAYOUT))
            before_rows=list(csv.reader((self.out/'before-progress').read_text().splitlines()))
            expected_rows=[row.copy() for row in before_rows]
            matches=[i for i,row in enumerate(expected_rows) if len(row)==7 and row[3]=='func_15083DA0']
            self.assertEqual(len(matches),1); i=matches[0]
            self.assertEqual(expected_rows[i][5],'240'); expected_rows[i][5]='108'
            expected_rows.insert(i+1,['us','game','generated_AEB40',screen.FUNCTION,str(screen.ENTRY),'132','c'])
            self.assertEqual(list(csv.reader((self.root/self.paths['progress']).read_text().splitlines())),expected_rows)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            only_target_slot_extent_and_optional_ABS_to_game_section_change=True,
            all_other_ELF_bytes_metadata_exact=True,guards_unchanged=True,
            explicit_native_census_correction=defined,protected_data=audit)
    def test_09_complete_retail_caller_return_and_requery_paths(self):
        outer_entry,outer_rom,length=0x15097910,0xC4DC0,47
        outer=list(struct.unpack_from('>47I',self.rom,outer_rom))
        self.assertNotEqual(list(struct.unpack_from('>47I',self.before,
            elf_slot_offset(self.before,outer_entry,length*4))),outer)
        lookup,initialize=0x15083E90,0x15082A44
        class Connected(IndexOracle):
            def __init__(model,memory,inner,selector,result,found,phase,remove):
                super().__init__(outer,memory,selector=selector,phase=phase,entry=outer_entry)
                model.code.update({screen.ENTRY+i*4:w for i,w in enumerate(inner)})
                model.result,model.found,model.remove=result,found,remove
            def record_call(model,target):
                assert target in (screen.ENTRY,lookup,initialize)
                args=tuple(model.r[4:5] if target!=initialize else model.r[4:8])
                if target==initialize: args+= (read(model.memory,model.r[29]+16,4),)
                model.calls.append((target,*args)); model.events.append(('CALL',target,args))
            def hook(model,target):
                assert target in (lookup,initialize)
                if target==initialize and model.remove:
                    for i in range(3): model.put(RECORDS+i*48+40,8,1)
                for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]
                model.r[2]=model.found if target==lookup else model.result
        cases=0; invocations=0
        for selector,position,found,result,remove,phase in itertools.product(
                (0,7,0x107),(-1,0,2),(0,ACTOR),(0,1),(False,True),(0,8)):
            memory=fixture(selector&255,3,position)
            for i in range(812): memory[ACTOR+i]=0xA5
            put(memory,ACTOR+0x13F,5,1)
            models=[Connected(memory,w,selector,result,found,phase,remove).run() for w in (self.retail,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
            index=position if selector&255 and position>=0 else -1
            if index<0: expected=0xFFFFFFFF
            elif found: expected=5|0x2000
            elif not result: expected=0xFFFFFFFF
            elif remove: expected=0xFFFFFFFF
            else: expected=index|(0x2000 if index else 0)
            self.assertEqual(models[0].r[2],expected)
            invocations+=sum(c[0]==screen.ENTRY for c in models[0].calls); cases+=1
        self.receipt('connected',complete_retail_caller_words=47,cases=cases,executions=cases*2,
            query_invocations_per_form=invocations,sentinel_flags_and_requery_results_checked=True,
            caller_is_currently_unrecovered_not_installed_linked_caller=True,
            lookup_and_initializer_callbacks_bounded=True)
    def test_10_durable_native_definition_actual_Splat_writer_and_census(self):
        source=self.root/'conker/symbol_addrs.us.txt'; text=source.read_text()
        if DEFINED.decode() not in text:
            self.assertIn(ASSIGNMENT,(self.root/self.paths['undefined']).read_bytes())
            self.receipt('census',installed=False); return
        script=r'''
import sys
from pathlib import Path
from types import SimpleNamespace
from intervaltree import IntervalTree
root,out=map(Path,sys.argv[1:])
sys.path.insert(0,str(root/'tools/n64splat/src'))
from splat.util import symbols,options
from splat.scripts import split
source=root/'conker/symbol_addrs.us.txt';text=source.read_text()
line='func_15083E0C = 0x15083E0C; // type:func defined:true'
for defined in (True,False):
    symbols.all_symbols=[];symbols.all_symbols_dict={};symbols.all_symbols_ranges=IntervalTree()
    lines=text.splitlines() if defined else text.replace(line,line.replace('defined:true','defined:false')).splitlines()
    symbols.handle_sym_addrs(source,lines,[])
    matches=[s for s in symbols.all_symbols if s.name=='func_15083E0C']
    assert len(matches)==1
    target=matches[0];target.referenced=True
    assert (target.vram_start,target.type,target.defined)==(0x15083E0C,'func',defined)
    symbols.add_symbol(symbols.Symbol(0x15500000,given_name='unresolved_canary',type='func',referenced=True))
    dest=out/('Splat-defined-%s.txt'%defined)
    options.opts=SimpleNamespace(create_undefined_funcs_auto=True,undefined_funcs_auto_path=dest)
    split.write_undefined_funcs_auto()
    expected=('' if defined else 'func_15083E0C = 0x15083E0C;\n')+'unresolved_canary = 0x15500000;\n'
    assert dest.read_text()==expected
print('actual parser/writer and missing-defined negative passed')
'''
        result=subprocess.run(['python3','-c',script,str(self.root),str(self.out)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('missing-defined negative passed',result.stdout)
        self.receipt('census',installed=True,actual_Splat_parser_writer=True,tracked_defined_symbol_durable=True,
            undefined_unresolved_canary_retained=True,missing_defined_negative_effective=True,
            only_target_C_row_added_and_previous_boundary_shortened=True,no_full_extraction=True)


NATIVE_PREFIX=r'''
#include <stddef.h>
typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4)?1:-1];
u8 D_800D2100;
'''
NATIVE_TABLE=r'''
IndexRecord15083E0C *D_800D20FC;
typedef char record_width[(sizeof(IndexRecord15083E0C)==48)?1:-1];
static IndexRecord15083E0C records[256];
'''
NATIVE_RUNNER=r'''
static u32 results[3];
static int run(void) {
    unsigned selector,c,path,i,cases=0; int got,wanted,position;
    const unsigned counts[5]={0,1,2,128,255};
    D_800D20FC=records;
    for(selector=0;selector<256;selector++) for(c=0;c<5;c++) for(path=0;path<4;path++) {
        unsigned count=counts[c];
        D_800D2100=(u8)count;
        position=path==0?-1:path==1?0:path==2?(int)(count/2):(int)count-1;
        for(i=0;i<256;i++) records[i].identity=(u8)(selector+1);
        if(position>=0 && (unsigned)position<count) {
            records[position].identity=(u8)selector;
            if(path==2) records[count-1].identity=(u8)selector;
        }
        wanted=-1;
        if(selector) for(i=0;i<count;i++) if(records[i].identity==selector) { wanted=(int)i; break; }
        got=func_15083E0C((u8)selector);
        if(got!=wanted) return 1;
        if(D_800D2100!=count || D_800D20FC!=records) return 2;
        for(i=0;i<sizeof(records);i++) {
            unsigned expected=(u8)(selector+1);
            unsigned record=i/48;
            if(position>=0 && (unsigned)position<count && ((int)record==position || (path==2 && record==count-1))) expected=selector;
            if(i%48!=40) expected=0;
            if(((u8*)records)[i]!=expected) return 3;
        }
        cases++;
    }
    results[0]=cases; return 0;
}
void _start(void) {
    int result=run();
    __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(results),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");
    __builtin_unreachable();
}
'''


if __name__=='__main__': unittest.main()
