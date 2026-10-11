"""Complete identity selector, retail restart, saturation and caller publication."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_identity_selector_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_animation_child_cleanup as cleanup
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

S, STACK, RECORDS = screen.SYMBOLS, guest.STACK, 0x24000


def fixture(identities=(),count=None,base=RECORDS,symbols=S,full=False):
    count=len(identities) if count is None else count
    memory={STACK+i:0xA5 for i in range(-0x100,0x100)}
    if full: memory.update({base+i:0 for i in range(256*52)})
    for i in range(256):
        memory[(base+i*48+40)&0xFFFFFFFF]=identities[i] if i<len(identities) else 0
        memory[(base+i*48+39)&0xFFFFFFFF]=0
    for i in range(4): memory[symbols['D_800D20FC']+i]=0xA5
    memory[symbols['D_800D2100']]=0xA5
    put(memory,symbols['D_800D2100'],count,1); put(memory,symbols['D_800D20FC'],base)
    return memory


def reference(memory,symbols=S):
    memory=memory.copy(); events=[]
    def get(address,size):
        assert all(address+i in memory for i in range(size)),('reference unmapped read',address,size)
        value=read(memory,address,size); events.append(('R',address,size,value)); return value
    count=get(symbols['D_800D2100'],1); identity=1; cursor=0
    if count:
        base=get(symbols['D_800D20FC'],4)
        while cursor<count:
            if get((base+cursor*48+40)&0xFFFFFFFF,1)==identity:
                identity+=1; cursor=1
            else: cursor+=1
            assert identity<=256, 'bounded byte-identity reference exceeded'
    return memory,events,min(identity,255)


def trace_range(*args):
    return range(400000) if args==(50000,) else range(*args)


class SelectorOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,symbols=S,phase=0,entry=screen.ENTRY):
        super().__init__(words,memory,arguments=(),phase=phase,entry=entry)
    def execute(self,word):
        if word>>26==32: CopyOracle.execute(self,word)
        elif word>>26==0 and word&63==27: cleanup.CleanupOracle.execute(self,word)
        else: super().execute(word)
    def run(self):
        # Keep the proven runner; only its finite loop budget grows for saturated scans.
        with patch.dict(guest.TriangleOracle.run.__globals__,range=trace_range):
            return super().run()
    def hook(self,target): raise AssertionError(('unexpected selector call',target))


class GameRecordIdentitySelectorTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-identity-selector-test'; cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt')
        if not (cls.out/'baseline.json').exists():
            assert (cls.root/screen.SOURCE).read_text().count(screen.ORIGINAL)==1
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.before=(cls.out/'before-elf').read_bytes(); cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>27I',cls.rom,screen.ROM))
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
        return list(struct.unpack_from('>27I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):
        if name=='baseline': raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,settings.get('symbols',S))
        models=[SelectorOracle(w,memory,**settings).run() for w in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((model.memory,model.events,model.r[2]),expected); self.assertEqual(model.calls,[])
        self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
        return models
    def test_01_complete_direct_shape_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(27,0,0,0,''))
        self.assertEqual(self.raw,self.retail)
        for name in ('original','selected','padded'): self.assertEqual(self.link(name),self.retail)
        _,functions,relocations=parse_object(self.out/'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'],108); self.assertEqual(len(relocations),4)
        self.receipt('shape',words=27,frame=0,direct_match=True,new_guards=0,relocations=4,
            original_restart_to_one_and_full_word_candidate_exact=True)
    def test_02_exhaustive_pairs_counts_restarts_and_saturation(self):
        cases=0; coverage=set()
        for first,second in itertools.product(range(256),repeat=2):
            models=self.compare(fixture((first,second))); cases+=1
            coverage.update(models[0].visits)
        for count in range(256):
            self.compare(fixture((1,2),count=count)); cases+=1
        for values in ((),(0,),(1,),(2,1),(2,1,0),(0,2,1),(1,1,2),(1,3,2),
                tuple(range(1,256)),tuple(range(255,0,-1)),(0,*range(1,255))):
            for phase in (0,8):
                models=self.compare(fixture(values),phase=phase); cases+=1
                coverage.update(models[0].visits)
        for base,values in itertools.product((0xFFFFFFD8,0x7FFFFFF0,0x80000010),((0,),(2,1,0),(0,2,1))):
            self.compare(fixture(values,base=base)); cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+108,4)))
        self.assertEqual(reference(fixture((2,1,0)))[2],2)
        self.assertEqual(reference(fixture(tuple(range(1,256))))[2],255)
        self.receipt('guest',cases=cases,executions=cases*2,reached_words=27,
            exhaustive_two_record_byte_pairs_and_every_count=True,
            restart_skips_index_zero_duplicate_and_saturated_result_checked=True,
            complete_memory_access_order_return_and_GP_FPR_preserved=True,
            wrapped_pointers_guest_only=True,proven_runner_budget_only_locally_extended=400000)
    def test_03_short_circuits_aliases_and_fired_fault_prefixes(self):
        memory=fixture(())
        for i in range(4): del memory[S['D_800D20FC']+i]
        cases=[(memory,{}),(fixture((0,)),{}),(fixture((2,1,0)),{}),
            (fixture((0,2,1)),{}),(fixture(count=128),{}),(fixture(count=255),{})]
        aliased=dict(D_800D2100=RECORDS+40,D_800D20FC=S['D_800D20FC'])
        cases.append((fixture((0,2,1),symbols=aliased),dict(symbols=aliased)))
        aliased=dict(D_800D2100=S['D_800D2100'],D_800D20FC=RECORDS+40)
        cases.append((fixture((1,2,0),symbols=aliased),dict(symbols=aliased)))
        aliased=dict(D_800D2100=S['D_800D20FC']+3,D_800D20FC=S['D_800D20FC'])
        cases.append((fixture((1,2,0),count=7,base=RECORDS+7,symbols=aliased),dict(symbols=aliased)))
        cases.append((fixture((2,1,0),base=STACK-40),{}))
        faults=0
        for memory,settings in cases:
            symbols=settings.get('symbols',S)
            forms=tuple(self.link(n,symbols) for n in ('original','selected')) if symbols!=S else (self.retail,self.raw)
            models=self.compare(memory,forms=forms,**settings)
            for index in range(models[0].accesses):
                pair=[SelectorOracle(w,memory,**settings) for w in forms]
                for model in pair:
                    model.fault=index
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,index)
                self.assertEqual((pair[0].memory,pair[0].events,pair[0].calls,pair[0].r,pair[0].f),
                    (pair[1].memory,pair[1].events,pair[1].calls,pair[1].r,pair[1].f)); faults+=1
        memory=fixture(tuple(range(1,256))); models=self.compare(memory)
        sample=(0,1,2,models[0].accesses-1)
        for index in sample:
            pair=[SelectorOracle(w,memory) for w in (self.retail,self.raw)]
            for model in pair:
                model.fault=index
                with self.assertRaises(guest.AccessFault): model.run()
                self.assertEqual(model.accesses,index)
            self.assertEqual((pair[0].memory,pair[0].events,pair[0].r,pair[0].f),
                (pair[1].memory,pair[1].events,pair[1].r,pair[1].f))
        self.receipt('aliases',cases=len(cases),executions=len(cases)*2,all_access_fault_pairs=faults,
            sampled_saturated_fault_pairs=len(sample),saturated_fault_ordinals=sample,
            count_pointer_record_and_stack_aliases=True,zero_count_skips_unmapped_pointer=True,
            helper_does_not_write_argument_home_or_record_memory=True)
    def test_04_independent_global_rebases_and_signed_low_carries(self):
        cases=0
        for entry,count,pointer in ((0x15207FF0,0x80117FFC,0x80128004),
                (0x15308004,0x80218004,0x80227FFC),(0x15417FFC,0x80327FFC,0x80338004)):
            symbols=dict(zip(S,(count,pointer)))
            forms=tuple(self.link(n,symbols,entry) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for values in ((),(1,),(2,1,0),(0,2,1),(1,3,2)):
                self.compare(fixture(values,symbols=symbols),forms=forms,symbols=symbols,entry=entry); cases+=1
        self.receipt('links',symbol_sets=3,links=9,cases=cases,executions=cases*3,
            both_global_HI_LO_pairs_independently_rebased=True)
    def test_05_actual_copied_owner_and_both_padding_routes(self):
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
                    args=['pad_c_object.py',str(obj),str(self.out/'before-layout'),'generated_AEB40',str(asm)]
                else:
                    args=['pad_generated_object.py',str(obj),str(self.root/'conker/asm/AEB40.s'),str(asm),
                        '--filename','generated_AEB40','--rodata-symbol','jtbl_8009CC40_game']
                subprocess.run(['python3',str(self.root/'tools'/args[0]),*args[1:],
                    '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                padded.append(parse_object(asm.with_suffix('.o')))
            start=padded[1][1][screen.FUNCTION]['value']; expected=bytearray(padded[0][0])
            expected[start:start+108]=padded[1][0][start:start+108]; self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<start+108},
                {o:v for o,v in padded[1][2].items() if not start<=o<start+108})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            existing_record_typedef_moved_without_neighbor_fingerprint_changes=True,
            all_neighbor_bytes_extents_relocations_pools_and_guard_fingerprints_exact=True)
    def test_06_effective_fresh_semantic_and_cached_access_controls(self):
        saturation=tuple(range(1,256))
        controls=(
            ('start','s32 identity = 1','s32 identity = 2',fixture((0,)),None),
            ('restart','            i = 0;','            i = -1;',fixture((2,1,0)),None),
            ('skip-one','            i = 0;','            i = 1;',fixture((0,2,1)),None),
            ('comparison','== identity','!= identity',fixture((2,)),None),
            ('byte-candidate','s32 identity','u8 identity',fixture(saturation),None),
            ('cap-bound','identity >= 0x100','identity > 0x100',fixture(saturation),None),
            ('cap-value','identity = 0xFF','identity = 0xFE',fixture(saturation),None),
            ('count-sign','extern u8 D_800D2100','extern s8 D_800D2100',fixture((1,2),count=128),'DECLARATIONS'),
            ('field','padding[0x28]','padding[0x27]',fixture((1,)), 'RECORD'),
            ('stride','tail[7]','tail[11]',fixture((0,1),full=True),'RECORD'),
            ('cached-count','extern u8 D_800D2100','extern volatile u8 D_800D2100',fixture((2,1,0)),'DECLARATIONS'),
            ('cached-pointer','*D_800D20FC','*volatile D_800D20FC',fixture((2,1,0)),'DECLARATIONS'))
        for name,old,new,memory,target in controls:
            if target:
                value=getattr(screen,target).replace(old,new)
                if name=='field': value=value.replace('tail[7]','tail[8]')
                with patch.object(screen,target,value): _,words=screen.compile_candidate(self.root,self.out,'negative-'+name)
            else: _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            self.assertNotEqual(words,self.raw)
            correct=SelectorOracle(self.raw,memory).run(); wrong=SelectorOracle(words,memory).run()
            if name.startswith('cached-'): self.assertNotEqual(correct.events,wrong.events,name)
            else: self.assertNotEqual(correct.r[2],wrong.r[2],name)
        self.receipt('negative',fresh_IDO_controls=len(controls),effective_result_controls=10,
            effective_cached_access_controls=2,all_effective=True)
    def test_07_native32_exhaustive_pairs_and_effective_restart_negative(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.RECORD+NATIVE_TABLE+
                screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,[66560,0,0]))
        bad=screen.SELECTED.replace('            i = 0;','            i = -1;')
        result,_=self.run_native('native-negative',NATIVE_PREFIX+screen.RECORD+NATIVE_TABLE+bad+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=66560,executions=133120,profiles=['O2','O0'],
            exhaustive_pairs_every_count_patterns_restart_cap_and_widths=True,
            complete_record_pool_and_globals_unchanged=True,effective_restart_negative=1)
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
        self.assertEqual(struct.unpack_from('>3I',self.before,elf_slot_offset(self.before,screen.ENTRY,12)),
            (0x00001025,0x03E00008,0))
        struct.pack_into('>27I',expected,elf_slot_offset(self.before,screen.ENTRY,108),*self.retail)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12); struct.pack_into('>I',expected,extent,108)
        actual=(self.root/self.paths['elf']).read_bytes(); self.assertEqual(bytes(expected),actual)
        for name in self.paths:
            if name not in ('source','elf'):
                self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            only_target_slot_and_extent_change=True,all_other_ELF_bytes_metadata_exact=True,
            guards_layout_symbol_auto_assignments_and_census_unchanged=True,protected_data=audit)
    def test_09_complete_retail_caller_identity_publication(self):
        entry,rom,length=0x150169A0,0x43E50,477
        outer=list(struct.unpack_from('>477I',self.rom,rom))
        self.assertNotEqual(list(struct.unpack_from('>477I',self.before,elf_slot_offset(self.before,entry,length*4))),outer)
        callbacks={0x15004F30:1,0x1502B9B4:2,0x10003C40:4,0x10004514:4,
            0x1502B8E0:5,0x15017114:1,0x100226F0:2,0x15016850:0,0x1508295C:3,0x15172CA8:1}
        class Connected(SelectorOracle):
            def __init__(model,memory,inner,count,scene,phase):
                super().__init__(outer,memory,phase=phase,entry=entry)
                model.r[4]=0; model.code.update({screen.ENTRY+i*4:w for i,w in enumerate(inner)})
                model.count,model.allocations=count,0
            def record_call(model,target):
                assert target==screen.ENTRY or target in callbacks,hex(target)
                size=0 if target==screen.ENTRY else callbacks[target]
                args=tuple(model.r[4:4+min(size,4)])
                if size==5: args+=(read(model.memory,model.r[29]+16,4),)
                model.calls.append((target,*args)); model.events.append(('CALL',target,args))
            def hook(model,target):
                result=0
                if target in (0x1502B9B4,0x1502B8E0): result=(model.count-5)*48
                if target==0x10003C40:
                    result=(RECORDS,0x30000,0x31000)[model.allocations]; model.allocations+=1
                if target==0x100226F0:
                    for i in range(model.r[5]): model.put(model.r[4]+i,0,1)
                for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]; model.r[2]=result
        cases=0; invocations=0
        for count,pattern,scene,phase in itertools.product((5,8,16,128,255),range(3),(0,1,2),(0,8)):
            values=[0]*count if pattern==0 else [1]*count if pattern==1 else [(i%3)+1 for i in range(count)]
            if pattern==0 and count>16:
                values=[1]*count; values[-2:]=[0,0]
            if pattern==2: values[count//2]=0
            memory=fixture(values,full=True)
            for start,size in ((0x30000,512),(0x31000,1024),(0x800D2101,32),(0x800D1548,4),
                    (0x8008FD8C,1),(0x800D2340,2)):
                for i in range(size): memory[start+i]=0
            put(memory,0x8008FD8C,scene,1)
            filled=values.copy()
            for i in range(count):
                if not filled[i]:
                    wanted=reference(fixture(filled))[2]; filled[i]=wanted
            models=[Connected(memory,w,count,scene,phase).run() for w in (self.retail,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
            self.assertEqual([models[0].memory[RECORDS+i*48+40] for i in range(count)],filled)
            expected_calls=sum(not identity for identity in values)
            self.assertEqual(sum(c[0]==screen.ENTRY for c in models[0].calls),expected_calls)
            self.assertEqual([c for c in models[0].calls if c[0]==0x1508295C],
                [(0x1508295C,0,1,1),(0x1508295C,0,1,0)])
            invocations+=expected_calls; cases+=1
        self.receipt('connected',complete_retail_caller_words=477,cases=cases,executions=cases*2,
            selector_invocations_per_form=invocations,returned_identities_stored_only_into_zero_ID_records=True,
            complete_caller_C_still_unrecovered=True,resource_copy_allocate_reset_callbacks_bounded=True,
            category_zero_and_scene_presence_mask_zero_path_scope=True,deep_scene_update_path_unqualified=True,
            full_empty_tables_through_16_max_counts_use_at_most_two_zero_ID_records=True)


NATIVE_PREFIX=r'''
#include <stddef.h>
typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4)?1:-1];
u8 D_800D2100;
'''
NATIVE_TABLE=r'''
IndexRecord15083E0C *D_800D20FC;
typedef char record_width[(sizeof(IndexRecord15083E0C)==48)?1:-1];
static IndexRecord15083E0C records[256],expected[256];
static u32 results[3];
s32 func_15083DA0(void);
static int check(void) {
    int cursor=0,id=1,got; unsigned i;
    if(D_800D2100) while(cursor<D_800D2100) {
        if(records[cursor].identity==id) { id++; cursor=1; } else cursor++;
    }
    if(id>255) id=255;
    for(i=0;i<sizeof(records);i++) ((u8*)expected)[i]=((u8*)records)[i];
    got=func_15083DA0();
    if(got!=id || D_800D20FC!=records) return 1;
    for(i=0;i<sizeof(records);i++) if(((u8*)expected)[i]!=((u8*)records)[i]) return 2;
    return 0;
}
'''
NATIVE_RUNNER=r'''
static int run(void) {
    unsigned first,second,count,path,i,cases=0; int status;
    D_800D20FC=records;
    for(i=0;i<sizeof(records);i++) ((u8*)records)[i]=(u8)(i*17+0x35);
    for(first=0;first<256;first++) for(second=0;second<256;second++) {
        D_800D2100=2; records[0].identity=(u8)first; records[1].identity=(u8)second;
        status=check(); if(status || D_800D2100!=2) return status?status:3; cases++;
    }
    for(count=0;count<256;count++) for(path=0;path<4;path++) {
        D_800D2100=(u8)count;
        for(i=0;i<256;i++) records[i].identity=path==0?0:path==1?(u8)(i+1):path==2?(u8)(255-i):(u8)(i%3+1);
        status=check(); if(status || D_800D2100!=count) return status?status:3; cases++;
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
