"""Timer-300 finish, ordered flag stores and actual paired-mask queries."""
import hashlib
import itertools
import json
import re
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_mask_finish_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK,PAIRS,QUERY=guest.STACK,0x55000,0x1503EF4C
QUERY_SYMBOLS=dict(D_8008446C=0x8008446C,D_800C6664=0x800C6664,D_800C6668=0x800C6668)
SYMBOLS=dict(screen.SYMBOLS,**QUERY_SYMBOLS)
FLAGS=(0,0xFFFFFFFF,0x80000000,0x12345678,0x740)
address=state.address


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x800<=a<STACK+0x140}


def fixture(slot=7,flags=0xFFFFFFFF,masks=(0xFFFFFFFF,0xFFFFFFFF),
        pairs=((1,0),(0,2),(0,0)),symbols=SYMBOLS,table=PAIRS):
    timer=address(symbols['D_800C666C'],slot,16)
    actor=address(symbols['D_800CC2D0'],slot,812)
    first=address(symbols['D_800C6664'],slot,16); second=address(symbols['D_800C6668'],slot,16)
    memory={STACK+i:0xA5 for i in range(-0x800,0x140)}
    for base,length in ((timer-12,32),(actor-16,844),(first-4,20),(table-16,56)):
        memory.update({(base+i)&0xFFFFFFFF:(i*17+0x35)&255 for i in range(length)})
    put(memory,actor+148,flags); put(memory,timer,0xA535,2)
    put(memory,first,masks[0]); put(memory,second,masks[1])
    put(memory,symbols['D_8008446C']+8,table)
    for i,(a,b) in enumerate(pairs): put(memory,table+i*8,a); put(memory,table+i*8+4,b)
    return memory


def paired_mask(memory,index,slot,symbols=SYMBOLS):
    table=read(memory,symbols['D_8008446C']+8)
    first=read(memory,table+index*8)
    if first and not first&read(memory,address(symbols['D_800C6664'],slot,16)): return 0
    second=read(memory,table+index*8+4)
    return int(not second or bool(second&read(memory,address(symbols['D_800C6668'],slot,16))))


class Reference:
    def __init__(self,memory,slot=7,results=(1,1,1),symbols=SYMBOLS,actions=None,actual=False):
        self.memory,self.slot,self.results,self.symbols=memory.copy(),slot,results,symbols
        self.actions,self.actual,self.calls,self.writes=actions or {},actual,[],[]
    def run(self):
        actor=address(self.symbols['D_800CC2D0'],self.slot,812)
        timer=address(self.symbols['D_800C666C'],self.slot,16)
        put(self.memory,timer,300,2)
        for i in range(3):
            self.calls.append((self.symbols['func_1503EF4C'],2,i,self.slot&0xFFFFFFFF))
            for a,v,size in self.actions.get(i,()): put(self.memory,a,v,size)
            result=paired_mask(self.memory,i,self.slot,self.symbols) if self.actual else self.results[i]
            if not result: continue
            offset=actor+148; value=read(self.memory,offset)
            if i<2:
                value|=0x40<<i; put(self.memory,offset,value); self.writes.append(value&0xFFFFFFFF)
                value&=~(0x200>>i)
            else: value&=~0x400
            put(self.memory,offset,value); self.writes.append(value&0xFFFFFFFF)
        return self


class FinishOracle(state.StateOracle):
    def __init__(self,words,memory,slot=7,results=(1,1,1),phase=0,symbols=SYMBOLS,
            start=screen.ENTRY,actions=None,connected=None,actual=False):
        guest.AttachmentOracle.__init__(self,words,memory,phase=phase,entry=start,arguments=(slot,),connected=connected)
        self.results,self.symbols,self.actions,self.actual=results,symbols,actions or {},actual
        self.number=0
    def record_call(self,target):
        assert target==self.symbols['func_1503EF4C'],hex(target)
        args=self.arguments(3); self.calls.append((target,*args)); self.events.append(('CALL',target,*args))
        self.assert_call=args[:2]==(2,self.number)
        assert self.assert_call,args
        for a,v,size in self.actions.get(self.number,()): self.put(a,v,size)
        self.number+=1
    def hook(self,target):
        assert target==self.symbols['func_1503EF4C'] and not self.actual
        value=self.results[self.number-1]
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.r[2]=value&0xFFFFFFFF
        self.f[:20]=[0xA5000000+i for i in range(20)]


class GameRecordMaskFinishMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-mask-finish-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt',makefile='conker/Makefile')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='5516cd7c1641d54e312dcc5e6bbf0496f6b6dead96e22390a015c7213c1dbf36'
        assert cls.baseline['elf']=='2eba14a881b78db16bee6505b484a7484720777acf4ba8599ae6ef1f085002d1'
        assert cls.baseline['guards']=='92f39fbf0bf509614ecff961e3a654e01d30c98666c3c65f224884f57102206e'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes(); cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>81I',cls.rom,screen.ROM))
        cls.query=list(struct.unpack_from('>30I',cls.before,elf_slot_offset(cls.before,QUERY,120)))
        assert cls.query==list(struct.unpack_from('>30I',cls.rom,0x6C3FC))
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        body=(cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        slot=cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_6B320'))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def link(self,name,start=screen.ENTRY,symbols=screen.SYMBOLS):
        script=self.out/('link-'+name+'.ld'); script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%start)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>81I',sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self),'_padded'): type(self)._padded=self.link('padded')
        return type(self)._padded

    def compare(self,memory,slot=7,results=(1,1,1),phase=0,actions=None,actual=False,
            symbols=SYMBOLS,start=screen.ENTRY,forms=None):
        expected=Reference(memory,slot,results,symbols,actions,actual).run()
        code={symbols['func_1503EF4C']+i*4:w for i,w in enumerate(self.query)} if actual else {}
        models=[FinishOracle(w,memory,slot,results,phase,symbols,start,actions,code,actual).run()
            for w in forms or (self.retail,self.raw,self.padded)]
        flag=address(symbols['D_800CC2D0'],slot,812)+148
        for model in models:
            self.assertEqual((public(model.memory),model.calls),(public(expected.memory),expected.calls))
            self.assertEqual(model.number,3)
            writes=[e[3] for e in model.events if e[0]=='W' and e[1]==flag]
            callback=[v&0xFFFFFFFF for entries in (actions or {}).values() for a,v,n in entries if a==flag and n==4]
            self.assertEqual(len(writes),len(expected.writes)+len(callback))
            if not callback: self.assertEqual(writes,expected.writes)
        for model in models[1:]: self.assertEqual((model.memory,model.events,model.r,model.f),
            (models[0].memory,models[0].events,models[0].r,models[0].f))
        return models

    def test_01_all_words_direct_and_profiles(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(81,32,0,0))
        self.assertEqual(self.raw,self.retail); self.assertEqual(self.padded,self.retail); self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'],324)
        for profile in ('compact','o1g3','o1'):
            _,words=screen.compile_candidate(self.root,self.out,profile,profile=profile)
            if profile=='compact': self.assertEqual(words,self.raw)
            else: self.assertNotEqual(words,self.raw)
        self.receipt('shape',words=81,frame=32,direct=True,guards=0,pools=0,all_five_ordered_flag_stores_direct=True)

    def test_02_all_results_relevant_bits_and_full_words(self):
        cases,reached=0,set()
        for flags,results,phase in itertools.product(FLAGS,tuple(itertools.product((0,1,-1,0x80000000),repeat=3)),(0,8)):
            models=self.compare(fixture(flags=flags),results=results,phase=phase); reached.update(models[0].visits); cases+=1
        for mask in range(32):
            flags=0x80000001|sum((1<<(6+i)) for i in range(5) if mask&(1<<i))
            for results in itertools.product((0,1),repeat=3): self.compare(fixture(flags=flags),results=results); cases+=1
        for slot in (0,25,-1,0x80000000): self.compare(fixture(slot),slot); cases+=1
        self.assertEqual(len(reached & set(range(screen.ENTRY,screen.ENTRY+324,4))),81)
        self.receipt('guest',cases=cases,forms=3,all_words=81,nonzero_result_full32=True,
            all_relevant_bits_and_preserved_high_bits=True,ordered_intermediate_stores=True,invalid_slots_mapped_guest_only=True)

    def test_03_call_time_mutations_live_flags_and_timer(self):
        cases=0; actor=screen.SYMBOLS['D_800CC2D0']+7*812; timer=screen.SYMBOLS['D_800C666C']+7*16
        for index,phase,result in itertools.product(range(3),(0,8),(0,1,0x80000000)):
            actions={index:((actor+148,0x80000701,4),(timer,0x4567,2))}
            models=self.compare(fixture(flags=0),results=(1,result,1) if index==1 else
                (result,1,1) if index==0 else (1,1,result),phase=phase,actions=actions)
            self.assertEqual(read(models[0].memory,timer,2),0x4567); cases+=1
        self.receipt('callbacks',cases=cases,flags_reread_after_each_call=True,timer_written_only_before_calls=True,all_effective=True)

    def test_04_actual_query_masks_short_circuit_and_coverage(self):
        cases,reached=0,set()
        choices=(((0,0),(0,0),(0,0)),((1,0),(0,2),(0x80000000,0x80000000)),
            ((1,2),(0x80000000,4),(4,0x80000000)),((0xFFFFFFFF,0xFFFFFFFF),)*3)
        for pairs,masks,phase in itertools.product(choices,tuple(itertools.product((0,1,2,0x80000000,0xFFFFFFFF),repeat=2)),(0,8)):
            models=self.compare(fixture(masks=masks,pairs=pairs),phase=phase,actual=True)
            reached.update(models[0].visits); cases+=1
        self.assertEqual(len(reached & set(range(QUERY,QUERY+120,4))),29)
        self.assertNotIn(QUERY+108,reached)
        self.receipt('actual-query',cases=cases,full_query30=True,reachable_words=29,retail_dead_zero_direct_preserved=True,
            zero_pair_wildcards_and_two_mask_domains=True)

    def test_05_effective_actual_query_aliases(self):
        cases=0
        for phase in (0,8):
            actor=screen.SYMBOLS['D_800CC2D0']+7*812
            memory=fixture(flags=0x200,masks=(0x40,0),table=actor+148-8,pairs=((0,0),(0x200,0),(0,0)))
            put(memory,actor+148,0x200)
            models=self.compare(memory,phase=phase,actual=True)
            self.assertEqual(read(models[0].memory,actor+148),0xC0); cases+=1
            symbols=dict(SYMBOLS,D_800CC2D0=QUERY_SYMBOLS['D_800C6664']-148)
            forms=tuple(self.link(n,screen.ENTRY,symbols) for n in ('original','selected','padded'))
            memory=fixture(slot=0,flags=0x200,masks=(0x200,0),symbols=symbols,pairs=((0,0),(0x40,0),(0x80,0)))
            self.compare(memory,slot=0,phase=phase,actual=True,symbols=symbols,forms=forms); cases+=1
        self.receipt('aliases',cases=cases,flag_pair_and_control_mask_feedback=True,all_effective=True,
            mapped_guest_only_not_portable_C_or_real_allocation_proof=True)

    def test_06_independent_rebases_and_fired_fault_prefixes(self):
        cases=0
        for j,start in enumerate((0x15207FFC,0x15308004)):
            symbols={name:(0x1512EF4C+j*0x10000 if name.startswith('func_') else
                (0x80107FFC if i%2==j else 0x80218004)+i*0x10000) for i,name in enumerate(screen.SYMBOLS)}
            forms=tuple(self.link(n,start,symbols) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for results,phase in itertools.product(tuple(itertools.product((0,1),repeat=3)),(0,8)):
                self.compare(fixture(symbols=dict(SYMBOLS,**symbols)),results=results,phase=phase,
                    symbols=dict(SYMBOLS,**symbols),start=start,forms=forms); cases+=1
        faults=0
        for results,actual in itertools.product(((0,0,0),(1,0,1),(1,1,1)),(False,True)):
            memory=fixture(); code={QUERY+i*4:w for i,w in enumerate(self.query)} if actual else {}
            complete=FinishOracle(self.retail,memory,results=results,connected=code,actual=actual).run()
            for fault in range(complete.accesses):
                models=[FinishOracle(w,memory,results=results,connected=code,actual=actual) for w in (self.retail,self.raw,self.padded)]
                for model in models:
                    model.fault=fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,fault)
                for model in models[1:]: self.assertEqual((model.memory,model.events,model.r,model.f),
                    (models[0].memory,models[0].events,models[0].r,models[0].f))
                faults+=1
        self.receipt('rebases-faults',symbols=3,links=2,cases=cases,fired_fault_triplets=faults,
            actual_query_in_fault_domain=True,all_state_exact=True,no_portable_C_fault_or_FCSR_claim=True)

    def test_07_effective_semantic_controls(self):
        controls=(('timer',screen.SELECTED.replace('= 300','= 0')),
            ('selector',screen.SELECTED.replace('func_1503EF4C(2,','func_1503EF4C(1,')),
            ('first-mask',screen.SELECTED.replace('~0x200','~0x400')),
            ('nonzero',screen.SELECTED.replace(' != 0',' == 1')),
            ('third',screen.SELECTED.replace(' &= ~0x400',' |= 0x400')))
        for name,body in controls:
            self.assertNotEqual(body,screen.SELECTED); _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            if name=='selector':
                model=FinishOracle(words,fixture())
                with self.assertRaises(AssertionError): model.run()
            else:
                results=(0x80000000,1,1); model=FinishOracle(words,fixture(),results=results).run()
                expected=Reference(fixture(),results=results).run()
                self.assertTrue((public(model.memory),model.calls)!=(public(expected.memory),expected.calls),name)
        collapsed=screen.SELECTED.replace('D_800CC2D0[slot].unk94 |= 0x40;\n        D_800CC2D0[slot].unk94 &= ~0x200;',
            'D_800CC2D0[slot].unk94 = (D_800CC2D0[slot].unk94 | 0x40) & ~0x200;')
        _,words=screen.compile_candidate(self.root,self.out,'negative-collapsed',collapsed)
        model=FinishOracle(words,fixture()).run()
        reference=FinishOracle(self.retail,fixture()).run()
        self.assertEqual(public(model.memory),public(reference.memory)); self.assertNotEqual(model.events,reference.events)
        self.receipt('controls',fresh_semantic=5,all_effective=True,collapsed_store_trace_control=True)

    def test_08_complete_owner_and_both_padders(self):
        before=(self.out/'before-source').read_text(); objects=[]
        for stage,source in (('before',before),('after',screen.install(before))):
            obj,warnings=compile_owner(self.root,self.out,source,'owner-'+stage)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            self.assertEqual(warnings,[]); objects.append(obj)
        def fingerprint(obj,name):
            text,functions,relocations=parse_object(obj); item=functions[name]; a,b=item['value'],item['value']+item['size']
            return item['size'],text[a:b],{o-a:r for o,r in relocations.items() if a<=o<b}
        names=set(parse_object(objects[0])[1]); self.assertEqual(names,set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}: self.assertEqual(fingerprint(objects[0],name),fingerprint(objects[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes=[]
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed=[]
            for stage,obj in zip(('before','after'),objects):
                asm=self.out/(route+'-'+stage+'.s')
                args=[str(obj),str(self.out/'before-layout'),'generated_6B320',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6B320.s'),str(asm),'--filename','generated_6B320']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value']; expected=bytearray(parsed[0][0])
            expected[start:start+324]=parsed[1][0][start:start+324]; self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start<=o<start+324},
                {o:r for o,r in parsed[1][2].items() if not start<=o<start+324})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1]); self.receipt('owner',unchanged_neighbors=len(names)-1,
            both_padders=True,pools_exact=True,dispatcher171_query30_rate45_collision134_unchanged=True)

    def test_09_literal_source_ELF_and_seven_inputs(self):
        before_source=(self.out/'before-source').read_text(); current=(self.root/screen.SOURCE).read_text(); now=current!=before_source
        self.assertEqual(current,screen.install(before_source) if now else before_source)
        actual=(self.root/self.paths['elf']).read_bytes(); expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,324); extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if now: struct.pack_into('>81I',expected,start,*self.retail); struct.pack_into('>I',expected,extent,324)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=now,ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+324],actual[start:start+324])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(),literal_no_projection_or_metadata_exception=True,
            guards_and_seven_inputs_exact=True,protected_data=data)

    def test_10_effective_stale_install_and_literal_integrity_controls(self):
        before=(self.out/'before-source').read_text()
        for stale in (screen.install(before),before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        rt,rb=Path.read_text,Path.read_bytes; source=self.root/screen.SOURCE; actual=source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:actual+'\n' if p==source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_and_seven_inputs()
        elf=self.root/self.paths['elf']; actual=elf.read_bytes(); start=elf_slot_offset(actual,screen.ENTRY,324)
        for offset in (start+4,start+324,installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)+3):
            wrong=bytearray(actual); wrong[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p==elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_and_seven_inputs()
        guards=self.root/self.paths['guards']; wrong=guards.read_bytes()+b'\n'
        with patch.object(Path,'read_bytes',lambda p:wrong if p==guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_and_seven_inputs()
        self.receipt('integrity-controls',stale_installs=2,source=1,ELF=3,guards=1,all_effective=True)

    def test_11_actual_dispatcher_predicate_finish_query_chain(self):
        bodies={}
        for entry,rom,n in ((state.screen.ENTRY,state.screen.ROM,171),(state.HELPER,state.screen.ROM+684,27)):
            body=list(struct.unpack_from('>%dI'%n,self.before,elf_slot_offset(self.before,entry,n*4)))
            self.assertEqual(body,list(struct.unpack_from('>%dI'%n,self.rom,rom))); bodies[entry]=body
        table=self.rom[0x2275E0+0x8008443C-0x80082B20:0x2275E0+0x8008443C-0x80082B20+12]
        self.assertEqual(struct.unpack('>3I',table),(0x1503EFC4,0x1503F108,screen.ENTRY))
        symbols=dict(state.screen.SYMBOLS,**SYMBOLS)
        class ChainOracle(FinishOracle):
            def __init__(model,memory,phase,code):
                state.StateOracle.__init__(model,bodies[state.screen.ENTRY],memory,symbols=symbols,phase=phase,
                    start=state.screen.ENTRY,connected=code)
                model.number,model.actual,model.results=0,True,(1,1,1)
            def record_call(model,target):
                if target==QUERY: return FinishOracle.record_call(model,target)
                return state.StateOracle.record_call(model,target)
            def hook(model,target): return state.StateOracle.hook(model,target)
        class ChainReference(state.Reference):
            def call(ref,target,args):
                result=super().call(target,args)
                if target==screen.ENTRY:
                    finish=Reference(ref.memory,args[0],symbols=symbols,actual=True).run()
                    ref.memory=finish.memory; ref.calls.extend(finish.calls)
                return result
        cases=0
        with patch.dict(state.LABELS,{screen.ENTRY:'finish'}):
            for count,phase,masks,status in itertools.product((0,1,3,5),(0,8),((0,0),(1,2),(0xFFFFFFFF,0xFFFFFFFF)),(2,3)):
                memory=state.fixture(state=status,count=count,group=2,types=(255,),existing=True,flag=1,symbols=symbols,masks=masks)
                memory.update({STACK+i:0xA5 for i in range(-0x800,0x140)})
                put(memory,symbols['D_8008443C']+8,screen.ENTRY)
                extra=fixture(masks=masks,symbols=symbols)
                memory.update({a:v for a,v in extra.items() if PAIRS-16<=a<PAIRS+40})
                put(memory,symbols['D_8008446C']+8,PAIRS)
                expected=ChainReference(memory,symbols=symbols).run(); models=[]
                for words in (self.retail,self.raw,self.padded):
                    code={state.HELPER+i*4:w for i,w in enumerate(bodies[state.HELPER])}
                    code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                    code.update({QUERY+i*4:w for i,w in enumerate(self.query)})
                    model=ChainOracle(memory,phase,code).run(); models.append(model)
                    self.assertEqual((public(model.memory),model.calls),(public(expected.memory),expected.calls))
                    self.assertEqual(model.number,3)
                for model in models[1:]: self.assertEqual((model.memory,model.events,model.r,model.f),
                    (models[0].memory,models[0].events,models[0].r,models[0].f))
                cases+=1
        self.receipt('connected-caller',cases=cases,actual_dispatcher171_predicate27_finish81_query30=True,
            original_group2_table=True,remaining_active_callbacks_tails_modeled=True,not_full_gameplay_acceptance=True)

    def test_12_native32_full_masks_and_actual_helper(self):
        prefix=r'''
typedef unsigned char u8; typedef short s16; typedef int s32; typedef unsigned u32;
typedef struct { u8 pad[0x94]; s32 unk94; u8 tail[0x294]; } struct127;
typedef struct { s32 unk0,unk4,unk8; u8 tail[4]; } struct106;
typedef char sizes[(sizeof(void *)==4 && sizeof(struct127)==812 && sizeof(struct106)==16)?1:-1];
struct127 D_800CC2D0[26]; struct106 D_800C6660[26];
#define D_800C666C ((u8 *)D_800C6660+12)
#define D_800C6664 ((u8 *)D_800C6660+4)
#define D_800C6668 ((u8 *)D_800C6660+8)
static s32 pairs[6]; s32 *D_8008446C[3]={pairs,pairs,pairs};
static struct127 expected; static u32 control[4];
static s32 results[3]; static int number,mutate,selected;
s32 func_1503EF4C(s32 group,s32 index,s32 slot) {
    if(group!=2 || index!=number || slot!=selected) __builtin_trap();
    number++; if(mutate) D_800CC2D0[slot].unk94=(s32)(0x80000701u+index);
    return results[index];
}
static void initialize(u32 flags,int slot,int pattern,int action) {
    selected=slot; mutate=action; number=0;
    for(int i=0;i<812;i++) ((u8 *)&D_800CC2D0[slot])[i]=(u8)(i*17+0x35);
    D_800CC2D0[slot].unk94=(s32)flags;
    for(int j=0;j<4;j++) ((u32 *)&D_800C6660[slot])[j]=0x35353535;
    for(int j=0;j<3;j++) results[j]=pattern&(1<<j)?(s32)0x80000000u:0;
}
static void reference(int slot) {
    *(s16 *)(D_800C666C+slot*16)=300;
    for(int i=0;i<3;i++) {
        if(!func_1503EF4C(2,i,slot)) continue;
        if(i<2) { D_800CC2D0[slot].unk94|=0x40<<i; D_800CC2D0[slot].unk94&=~(0x200>>i); }
        else D_800CC2D0[slot].unk94&=~0x400;
    }
}
'''
        suffix=r'''
static int run(u32 *failure) {
    const u32 high[4]={0,0xFFFFFFFFu,0x80000000u,0x12345678u}; int slots[3]={0,7,25}; unsigned cases=0;
    for(int bits=0;bits<32;bits++) for(int h=0;h<4;h++) for(int pattern=0;pattern<8;pattern++)
    for(int action=0;action<2;action++) for(int s=0;s<3;s++) {
        u32 flags=(high[h]&~0x7C0u)|((u32)bits<<6);
        initialize(flags,slots[s],pattern,action); reference(slots[s]);
        for(int j=0;j<812/4;j++) ((u32 *)&expected)[j]=((u32 *)&D_800CC2D0[slots[s]])[j];
        for(int j=0;j<4;j++) control[j]=((u32 *)&D_800C6660[slots[s]])[j];
        initialize(flags,slots[s],pattern,action); func_1503F16C(slots[s]); cases++;
        for(int j=0;j<812/4;j++) if(((u32 *)&expected)[j]!=((u32 *)&D_800CC2D0[slots[s]])[j]) {
            failure[0]=cases; failure[1]=j; failure[2]=((u32 *)&D_800CC2D0[slots[s]])[j]; return 1;
        }
        for(int j=0;j<4;j++) if(control[j]!=((u32 *)&D_800C6660[slots[s]])[j]) {
            failure[0]=cases; failure[1]=0x1000+j; failure[2]=((u32 *)&D_800C6660[slots[s]])[j]; return 1;
        }
        if(number!=3) return 3;
    }
    return cases==6144?0:2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result==1) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],prefix+screen.SELECTED+suffix,profile),(0,''))
        for name,body in (('timer',screen.SELECTED.replace('= 300','= 0')),
                ('nonzero',screen.SELECTED.replace(' != 0',' == 1')),
                ('mask',screen.SELECTED.replace('~0x200','~0x400'))):
            result,detail=self.run_native('native-negative-'+name,prefix+body+suffix)
            self.assertEqual(result,1); self.assertEqual(len(detail),3)
        helper=re.findall(r'^s32 func_1503EF4C\([^;{}]+\) \{.*?^\}',(self.out/'before-source').read_text(),re.M|re.S)
        self.assertEqual(len(helper),1)
        renamed=helper[0].replace('func_1503EF4C','actual_mask_query')
        actual_prefix=prefix+renamed
        actual_suffix=r'''
static int run(u32 *failure) {
    u32 masks[5]={0,1,2,0x80000000u,0xFFFFFFFFu}; int slots[3]={0,7,25}; unsigned cases=0;
    for(int a=0;a<5;a++) for(int b=0;b<5;b++) for(int p=0;p<4;p++) for(int s=0;s<3;s++) {
        initialize(0xFFFFFFFFu,slots[s],0,0); D_800C6660[slots[s]].unk4=(s32)masks[a]; D_800C6660[slots[s]].unk8=(s32)masks[b];
        for(int i=0;i<6;i++) pairs[i]=p==0?0:p==1?(1<<(i%3)):p==2?(s32)0x80000000u:-1;
        for(int i=0;i<3;i++) results[i]=actual_mask_query(2,i,slots[s]);
        reference(slots[s]); u32 expected_flags=(u32)D_800CC2D0[slots[s]].unk94;
        D_800CC2D0[slots[s]].unk94=-1; func_1503F16C(slots[s]); cases++;
        if((u32)D_800CC2D0[slots[s]].unk94!=expected_flags) {
            failure[0]=cases; failure[1]=0; failure[2]=(u32)D_800CC2D0[slots[s]].unk94; return 1;
        }
    }
    return cases==300?0:2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result==1) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        source=screen.SELECTED.replace('func_1503EF4C(','actual_mask_query(')
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-actual-'+profile[1:],actual_prefix+source+actual_suffix,profile),(0,''))
        self.receipt('native',cases_per_profile=6144,actual_helper_cases_per_profile=300,profiles=['O2','O0'],
            all_actor_and_control_words=True,all_relevant_bits_full_nonzero_and_callback_mutations=True,
            effective_controls=3,no_native_intermediate_store_or_private_alias_FCSR_claim=True)


if __name__=='__main__':
    unittest.main()
