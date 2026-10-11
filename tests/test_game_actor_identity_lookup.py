"""Complete 26-slot lookup, private access order and linked caller contracts."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_identity_lookup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_index_query as records
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.game_owner_pool import normalized_pools

STACK, STRIDE, COUNT = guest.STACK, 812, 26
BASE = screen.SYMBOLS['D_800CC2D0']
UNREACHABLE = {0x78, 0x9C, 0xC0, 0xE4}


def symbols(base):
    return dict(D_800CC2D0=base, D_800CC30B=base+59, D_800CC5FC=base+812)


def fixture(selector=7, position=1, presence=1, duplicate=False, inactive=False,
            empty=False, holes=False, base=BASE, full=False):
    memory={STACK+i:0xA5 for i in range(-0x100,0x100)}
    if full: memory.update({base+i:0 for i in range(28*STRIDE)})
    for i in range(28):
        actor=base+i*STRIDE
        put(memory,actor,0 if empty or (holes and i%4==0) else presence)
        put(memory,actor+59,(selector+1)&255,1)
        memory[actor+58]=0
    if position>=0:
        put(memory,base+position*STRIDE+59,selector&255,1)
        put(memory,base+position*STRIDE,0 if inactive or empty else presence)
        if duplicate and position<25:
            put(memory,base+25*STRIDE+59,selector&255,1)
            put(memory,base+25*STRIDE,presence)
    return memory


def reference(memory,selector=7,phase=0,base=BASE):
    memory=memory.copy(); events=[]
    value=selector&0xFFFFFFFF
    put(memory,STACK+phase,value); events.append(('W',STACK+phase,4,value))
    selector=value&255; result=0
    def get(address,size):
        assert all(address+i in memory for i in range(size)),('reference unmapped read',address,size)
        value=read(memory,address,size); events.append(('R',address,size,value)); return value
    if selector:
        for i in range(COUNT):
            actor=base+i*STRIDE
            if get(actor,4) and get(actor+59,1)==selector:
                result=actor; break
    return memory,events,result


class LookupOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,selector=7,phase=0,base=BASE,entry=screen.ENTRY):
        super().__init__(words,memory,arguments=(selector,),phase=phase,entry=entry)
    def execute(self,word):
        if word>>26==32: CopyOracle.execute(self,word)
        else: super().execute(word)
    def hook(self,target): raise AssertionError(('unexpected leaf lookup call',target))


class GameActorIdentityLookupTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-identity-lookup-test'; cls.out.mkdir(exist_ok=True)
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
        cls.retail=list(struct.unpack_from('>72I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        slot=cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_AEB40'))
    @classmethod
    def link(cls,name,base=BASE,entry=screen.ENTRY):
        script=cls.out/('%s-%X-%X.ld'%(name,entry,base)); elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols(base).items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>72I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):
        if name=='baseline': raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**{k:v for k,v in settings.items() if k!='entry'})
        models=[LookupOracle(w,memory,**settings).run() for w in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((model.memory,model.events,model.r[2]),expected); self.assertEqual(model.calls,[])
        self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
        return models
    def test_01_complete_direct_shape_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(72,0,0,0,''))
        self.assertEqual(self.raw,self.retail); self.assertEqual(self.raw[0],0xAFA40000)
        for name in ('original','selected','padded'): self.assertEqual(self.link(name),self.retail)
        _,functions,relocations=parse_object(self.out/'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'],288); self.assertEqual(len(relocations),8)
        self.receipt('shape',words=72,frame=0,direct_match=True,new_guards=0,relocations=8,
            original_full_argument_home_and_complete_26_slot_loop_exact=True)
    def test_02_independent_selectors_slots_presence_and_first_duplicate(self):
        cases=0; coverage=set()
        for selector,position,phase in itertools.product(range(256),range(-1,27),(0,8)):
            models=self.compare(fixture(selector,position,duplicate=True,holes=True),selector=selector,phase=phase)
            coverage.update(models[0].visits); cases+=1
        for selector,upper in itertools.product(range(256),(0x100,0xFFFF0000,0x80000000,0x7FFFFF00)):
            self.compare(fixture(selector,25),selector=upper|selector); cases+=1
        for position,presence,inactive,phase in itertools.product(range(26),
                (1,2,0x80000000,0xFFFFFFFF),(False,True),(0,8)):
            models=self.compare(fixture(255,position,presence,inactive=inactive),selector=255,phase=phase)
            coverage.update(models[0].visits); cases+=1
        for position in range(26):
            self.compare(fixture(7,position,empty=True)); cases+=1
        expected=set(range(screen.ENTRY,screen.ENTRY+288,4))-{screen.ENTRY+o for o in UNREACHABLE}
        self.assertEqual(coverage,expected)
        self.receipt('guest',cases=cases,executions=cases*2,reached_words=len(coverage),
            unreachable_redundant_unroll_offsets=sorted(UNREACHABLE),
            every_selector_and_slot_25_included_slot_26_excluded=True,
            full_presence_words_inactive_identity_duplicate_and_upper_arguments=True,
            complete_memory_order_return_and_GP_FPR_preservation=True)
    def test_03_short_circuits_argument_home_aliases_and_fired_faults(self):
        cases=[]
        memory={STACK+i:0xA5 for i in range(-0x100,0x100)}
        cases.append((memory,dict(selector=0)))
        for position in (0,1,2,4,5,25):
            memory=fixture(position=position)
            memory={a:v for a,v in memory.items() if a<BASE+(position+1)*STRIDE or a<BASE}
            cases.append((memory,{}))
        memory=fixture(empty=True)
        for i in range(28): del memory[BASE+i*STRIDE+59]
        cases.append((memory,{}))
        memory=fixture(position=2)
        put(memory,BASE,0); del memory[BASE+59]
        cases.append((memory,{}))
        memory=fixture(position=26)
        for i in range(28):
            if i>=26:
                for address in (BASE+i*STRIDE+58,BASE+i*STRIDE+59,*range(BASE+i*STRIDE,BASE+i*STRIDE+4)):
                    del memory[address]
        cases.append((memory,{}))
        faults=0; count=0
        for phase in (0,8):
            home=STACK+phase
            varied=list(cases)
            for offset in (0,56,812,868):
                base=home-offset
                varied.append((fixture(selector=7,position=2,base=base),dict(base=base,selector=0x107)))
            for memory,settings in varied:
                base=settings.get('base',BASE)
                forms=tuple(self.link(n,base) for n in ('original','selected')) if base!=BASE else (self.retail,self.raw)
                models=self.compare(memory,forms=forms,phase=phase,**settings); count+=1
                for index in range(models[0].accesses):
                    pair=[LookupOracle(w,memory,phase=phase,**settings) for w in forms]
                    for model in pair:
                        model.fault=index
                        with self.assertRaises(guest.AccessFault): model.run()
                        self.assertEqual(model.accesses,index)
                    self.assertEqual((pair[0].memory,pair[0].events,pair[0].calls,pair[0].r,pair[0].f),
                        (pair[1].memory,pair[1].events,pair[1].calls,pair[1].r,pair[1].f)); faults+=1
        self.receipt('aliases',cases=count,executions=count*2,fired_fault_pairs=faults,
            private_presence_identity_home_aliases=True,
            zero_selector_inactive_id_first_match_and_outside_slot_reads_gated=True)
    def test_04_consistent_pool_alias_rebases_and_low_half_carries(self):
        cases=0
        for entry,base in ((0x15207FF0,0x80117FFC),(0x15308004,0x80218004),(0x15417FFC,0x8031FE00)):
            forms=tuple(self.link(n,base,entry) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for selector,position,presence in ((0,0,1),(7,-1,1),(7,0,1),(255,1,0x80000000),
                    (7,25,0xFFFFFFFF),(7,26,1)):
                self.compare(fixture(selector,position,presence,base=base),forms=forms,
                    selector=selector,base=base,entry=entry); cases+=1
        self.receipt('links',symbol_sets=3,links=9,cases=cases,executions=cases*3,
            one_actor_pool_with_consistent_base_identity_and_second_slot_aliases=True,
            HI_LO_signed_carry_boundaries_checked=True)
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
            expected[start:start+288]=padded[1][0][start:start+288]; self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<start+288},
                {o:v for o,v in padded[1][2].items() if not start<=o<start+288})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            all_neighbor_bytes_extents_relocations_pools_guard_fingerprints_exact=True)
    def test_06_effective_fresh_IDO_semantic_controls(self):
        controls=(
            ('selector','u8 selector','u32 selector',fixture(),dict(selector=0x107)),
            ('last-slot','i < 26','i < 25',fixture(position=25),{}),
            ('outside-slot','i < 26','i < 27',fixture(position=26),{}),
            ('presence','!= 0','== 0',fixture(position=0),{}),
            ('presence-byte','*(s32 *)actor','*(u8 *)actor',fixture(position=0,presence=1),{}),
            ('identity','actor[0x3B]','actor[0x3A]',fixture(position=0),{}),
            ('signed-identity','actor[0x3B]','*(s8 *)(actor + 0x3B)',fixture(255,0),dict(selector=255)),
            ('comparison','== selector','!= selector',fixture(position=1),{}),
            ('stride','actor += 0x32C','actor += 0x330',fixture(position=1,full=True),{}),
            ('zero-gate','    if (selector == 0) {\n        return NULL;\n    }\n','',fixture(0,0),dict(selector=0)))
        for name,old,new,memory,settings in controls:
            self.assertIn(old,screen.SELECTED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            self.assertNotEqual(words,self.raw)
            correct=LookupOracle(self.raw,memory,**settings).run(); wrong=LookupOracle(words,memory,**settings).run()
            self.assertNotEqual(correct.r[2],wrong.r[2],name)
        self.receipt('negative',fresh_IDO_controls=len(controls),all_effective=True,
            last_slot_25_required_outside_slot_26_forbidden=True)
    def test_07_native32_domains_and_effective_last_slot_negative(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,[21504,0,0]))
        bad=screen.SELECTED.replace('i < 26','i < 25')
        result,_=self.run_native('native-negative',NATIVE_PREFIX+bad+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=21504,executions=43008,profiles=['O2','O0'],
            pointer_integer_widths_checked=True,effective_last_slot_negative=1,
            complete_pool_bytes_unchanged=True,private_home_faults_guest_only=True)
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
        self.assertEqual(struct.unpack_from('>4I',self.before,elf_slot_offset(self.before,screen.ENTRY,16)),
            (0xAFA40000,0x00001025,0x03E00008,0))
        struct.pack_into('>72I',expected,elf_slot_offset(self.before,screen.ENTRY,288),*self.retail)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],16); struct.pack_into('>I',expected,extent,288)
        actual=(self.root/self.paths['elf']).read_bytes(); self.assertEqual(bytes(expected),actual)
        for name in self.paths:
            if name not in ('source','elf'):
                self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            only_target_slot_and_extent_change=True,all_other_ELF_bytes_metadata_exact=True,
            guards_layout_symbol_auto_assignments_and_census_unchanged=True,protected_data=audit)
    def test_09_actual_linked_index_wrapper_and_two_lookup_caller(self):
        cases=0; invocations=0
        for entry,rom,size in ((0x15083FB0,0xB1460,20),(0x15008A10,0x35EC0,20)):
            outer=list(struct.unpack_from('>20I',self.before,elf_slot_offset(self.before,entry,size*4)))
            self.assertEqual(outer,list(struct.unpack_from('>20I',self.rom,rom)))
            class Connected(LookupOracle):
                def __init__(model,memory,inner,selector,phase):
                    super().__init__(outer,memory,selector=selector,phase=phase,entry=entry)
                    model.code.update({screen.ENTRY+i*4:w for i,w in enumerate(inner)})
                def record_call(model,target):
                    assert target==screen.ENTRY
                    model.calls.append((target,model.r[4])); model.events.append(('CALL',target,(model.r[4],)))
            for selector,position,inactive,phase in itertools.product(
                    (0,1,0x101,255),(-1,0,1,25,26),(False,True),(0,8)):
                identity=selector&255 if entry==0x15083FB0 else 1
                memory=fixture(identity,position,inactive=inactive)
                for address in range(0x80088720,0x80088734): memory[address]=0xA5
                models=[Connected(memory,w,selector,phase).run() for w in (self.retail,self.raw)]
                self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                    (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
                found=identity!=0 and 0<=position<26 and not inactive
                if entry==0x15083FB0:
                    self.assertEqual(models[0].r[2],position if found else 0xFFFFFFFF)
                else:
                    wanted=BASE+position*STRIDE if found else 0
                    for address in (0x80088720,0x80088730): self.assertEqual(read(models[0].memory,address,4),wanted)
                    for address in (0x80088724,0x80088728,0x8008872C): self.assertEqual(read(models[0].memory,address,4),0)
                    self.assertEqual(models[0].calls,[(screen.ENTRY,1),(screen.ENTRY,1)])
                invocations+=len(models[0].calls); cases+=1
        self.receipt('connected',current_linked_byte_exact_callers=2,complete_caller_words=[20,20],
            cases=cases,executions=cases*2,lookup_invocations_per_form=invocations,
            index_sentinel_two_stores_and_three_float_zero_stores_checked=True,no_callback_models=True)
    def test_10_complete_retail_caller_with_banked_record_query(self):
        entry,rom,length=0x15097910,0xC4DC0,47
        outer=list(struct.unpack_from('>47I',self.rom,rom))
        self.assertNotEqual(list(struct.unpack_from('>47I',self.before,elf_slot_offset(self.before,entry,188))),outer)
        record_words=list(struct.unpack_from('>33I',self.before,elf_slot_offset(self.before,records.screen.ENTRY,132)))
        self.assertEqual(record_words,list(struct.unpack_from('>33I',self.rom,records.screen.ROM)))
        initialize=0x15082A44
        class Connected(LookupOracle):
            def __init__(model,memory,inner,selector,result,remove,phase):
                super().__init__(outer,memory,selector=selector,phase=phase,entry=entry)
                model.code.update({screen.ENTRY+i*4:w for i,w in enumerate(inner)})
                model.code.update({records.screen.ENTRY+i*4:w for i,w in enumerate(record_words)})
                model.result,model.remove=result,remove
            def record_call(model,target):
                assert target in (screen.ENTRY,records.screen.ENTRY,initialize)
                args=tuple(model.r[4:5] if target!=initialize else model.r[4:8])
                if target==initialize: args+=(read(model.memory,model.r[29]+16,4),)
                model.calls.append((target,*args)); model.events.append(('CALL',target,args))
            def hook(model,target):
                assert target==initialize
                if model.remove:
                    for i in range(3): model.put(records.RECORDS+i*48+40,8,1)
                for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]; model.r[2]=model.result
        cases=0; invocations=0
        for selector,index,position,flag,result,remove,phase in itertools.product(
                (0,7,0x107),(-1,0,2),(-1,0,25,26),(0,5,255),(0,1),(False,True),(0,8)):
            memory=fixture(selector&255,position)
            memory.update(records.fixture(selector&255,3,index))
            for i in range(28): memory[BASE+i*STRIDE+0x13F]=flag
            models=[Connected(memory,w,selector,result,remove,phase).run() for w in (self.retail,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
            if not selector&255 or index<0: expected=0xFFFFFFFF
            elif 0<=position<26: expected=flag|(0x2000 if flag else 0)
            elif not result or remove: expected=0xFFFFFFFF
            else: expected=index|(0x2000 if index else 0)
            self.assertEqual(models[0].r[2],expected)
            invocations+=sum(c[0]==screen.ENTRY for c in models[0].calls); cases+=1
        self.receipt('retail-connected',complete_retail_caller_words=47,cases=cases,executions=cases*2,
            lookup_invocations_per_form=invocations,record_query_is_current_linked_byte_exact=True,
            actor_lookup_and_record_query_execute_not_callbacks=True,
            caller_current_C_still_unrecovered=True,only_initializer_is_bounded_callback=True,
            sentinel_index_zero_actor_flag_and_requery_result_checked=True)


NATIVE_PREFIX=r'''
#include <stddef.h>
#define NULL ((void *)0)
typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4)?1:-1];
static u8 D_800CC2D0[28*812] __attribute__((aligned(4)));
static u8 expected[28*812];
static u32 results[3];
'''
NATIVE_RUNNER=r'''
static int run(void) {
    unsigned selector,path,i,cases=0; int position,found;
    const u32 presence[3]={1,0x80000000u,0xFFFFFFFFu};
    for(selector=0;selector<256;selector++) for(position=-1;position<27;position++) for(path=0;path<3;path++) {
        for(i=0;i<sizeof(D_800CC2D0);i++) D_800CC2D0[i]=(u8)(i*17+0x35);
        for(i=0;i<28;i++) {
            *(u32*)(D_800CC2D0+i*812)=presence[path];
            D_800CC2D0[i*812+59]=(u8)(selector+1);
        }
        if(position>=0) {
            D_800CC2D0[position*812+59]=(u8)selector;
            if(path==2) *(u32*)(D_800CC2D0+position*812)=0;
            if(path==1 && position<25) D_800CC2D0[25*812+59]=(u8)selector;
        }
        found=-1;
        if(selector) for(i=0;i<26;i++) if(*(u32*)(D_800CC2D0+i*812) && D_800CC2D0[i*812+59]==selector) { found=(int)i; break; }
        for(i=0;i<sizeof(expected);i++) expected[i]=D_800CC2D0[i];
        if(func_15083E90((u8)selector)!=(found<0?NULL:D_800CC2D0+found*812)) return 1;
        for(i=0;i<sizeof(expected);i++) if(expected[i]!=D_800CC2D0[i]) return 2;
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
