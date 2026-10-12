"""Full unsigned-rate initialization, live buffers and retained 64-bit RNG."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_vertical_rate_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_random_selector_outputs_match as rng
from tools.tests import test_game_random_reload_timer_match as division
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, BUFFER, OTHER, RANDOM, SEED = guest.STACK, 0x24000, 0x34000, 0x150ADA20, rng.SEED
VALUES = (0,1,4,5,19,20,21,39,40,0x7FFFFFFF,0x80000000,0xFFFFFFFE,0xFFFFFFFF)
address = state.address


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x800 <= a < STACK+0x140}


def fixture(count=3,slot=7,group=0,symbols=screen.SYMBOLS,buffer=BUFFER,seed=1):
    control=address(symbols['D_800C6660'],slot,16)
    memory={STACK+i:0xA5 for i in range(-0x800,0x140)}
    for start,length in ((control-16,48),(buffer-16,max(count,120)*104+32),(OTHER-16,max(count,120)*104+32)):
        memory.update({(start+i)&0xFFFFFFFF:(i*17+0x35)&255 for i in range(length)})
    put(memory,SEED,seed,8)
    for g in {0,1,2,group,255}: put(memory,symbols['D_80098914']+g,count,1)
    put(memory,control,buffer); put(memory,control+12,0xA535,2); put(memory,control+14,group,1)
    return memory


class Reference:
    def __init__(self,memory,slot=7,randoms=VALUES,symbols=screen.SYMBOLS,actions=None,actual=False):
        self.memory,self.slot,self.randoms,self.symbols=memory.copy(),slot,randoms,symbols
        self.actions,self.actual,self.calls=actions or {},actual,[]
    def run(self):
        control=address(self.symbols['D_800C6660'],self.slot,16)
        group=read(self.memory,control+14,1)
        put(self.memory,control+12,120,2)
        self.count=read(self.memory,self.symbols['D_80098914']+group,1)
        for index in range(self.count):
            self.calls.append((self.symbols['func_150ADA20'],))
            for a,v,size in self.actions.get(index,()): put(self.memory,a,v,size)
            if self.actual:
                seed=rng.next_seed(read(self.memory,SEED,8)); put(self.memory,SEED,seed,8); value=seed&0xFFFFFFFF
            else: value=self.randoms[index%len(self.randoms)]&0xFFFFFFFF
            element=address(read(self.memory,control),index,104)
            put(self.memory,element+76,bits(float(value%20-5)))
        return self


class RateOracle(rng.RandomOutputsOracle,division.TimerOracle,state.StateOracle):
    def __init__(self,words,memory,slot=7,randoms=VALUES,phase=0,symbols=screen.SYMBOLS,
            start=screen.ENTRY,actions=None,connected=None,actual=False):
        guest.AttachmentOracle.__init__(self,words,memory,phase=phase,entry=start,arguments=(slot,),connected=connected)
        self.randoms,self.symbols,self.actions,self.actual=randoms,symbols,actions or {},actual
        self.number,self.hi,self.lo=0,0,0
    def execute(self,word):
        op,fn=word>>26,word&63
        if op==0 and fn==27:
            # DIVU consumes low words even after the real RNG returns sign-extended V0.
            registers={word>>21&31,word>>16&31}; saved={i:self.r[i] for i in registers}
            for i in registers: self.r[i]&=0xFFFFFFFF
            try: division.TimerOracle.execute(self,word)
            finally:
                for i,v in saved.items(): self.r[i]=v
        elif op==0 and fn==16:
            division.TimerOracle.execute(self,word)
        else: rng.RandomOutputsOracle.execute(self,word)
    def record_call(self,target):
        assert target==self.symbols['func_150ADA20'],hex(target)
        self.calls.append((target,)); self.events.append(('CALL',target))
        for a,v,size in self.actions.get(self.number,()): self.put(a,v,size)
        self.number+=1
    def hook(self,target):
        assert target==self.symbols['func_150ADA20'] and not self.actual
        value=self.randoms[(self.number-1)%len(self.randoms)]
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.r[2]=value&0xFFFFFFFF
        self.f[:20]=[0xA5000000+i for i in range(20)]


class GameRecordVerticalRateMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-vertical-rate-match-test'; cls.out.mkdir(exist_ok=True)
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
        assert cls.baseline['source']=='b29637289176da1db3720c86e43270c377e81d3567bbf32e2ebfbb32cdabc4c9'
        assert cls.baseline['elf']=='ced34e5fd81c32b7c4c62d437c33f43894c705559633292fbc567e904d221c75'
        assert cls.baseline['guards']=='92f39fbf0bf509614ecff961e3a654e01d30c98666c3c65f224884f57102206e'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.before=(cls.out/'before-elf').read_bytes(); cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>45I',cls.rom,screen.ROM))
        cls.random=list(struct.unpack_from('>18I',cls.rom,0xDAED0))
        assert cls.random==list(struct.unpack_from('>18I',cls.before,elf_slot_offset(cls.before,RANDOM,72)))
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
        return list(struct.unpack_from('>45I',sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self),'_padded'): type(self)._padded=self.link('padded')
        return type(self)._padded

    def compare(self,memory,slot=7,randoms=VALUES,phase=0,actions=None,actual=False,
            symbols=screen.SYMBOLS,start=screen.ENTRY,forms=None):
        expected=Reference(memory,slot,randoms,symbols,actions,actual).run()
        code={symbols['func_150ADA20']+i*4:w for i,w in enumerate(self.random)} if actual else {}
        models=[RateOracle(w,memory,slot,randoms,phase,symbols,start,actions,code,actual).run()
            for w in forms or (self.retail,self.raw,self.padded)]
        for model in models:
            self.assertEqual((public(model.memory),model.calls),(public(expected.memory),expected.calls))
            self.assertEqual(model.number,expected.count)
        for model in models[1:]: self.assertEqual((model.memory,model.events,model.r,model.f,model.hi,model.lo),
            (models[0].memory,models[0].events,models[0].r,models[0].f,models[0].hi,models[0].lo))
        return models

    def test_01_all_words_direct_profiles_and_dead_break(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(45,48,0,0))
        self.assertEqual(self.raw,self.retail); self.assertEqual(self.padded,self.retail); self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'],180)
        self.assertEqual(self.raw[32],0x0007000D)
        for profile in ('compact','o1g3','o1'):
            _,words=screen.compile_candidate(self.root,self.out,profile,profile=profile)
            if profile=='compact': self.assertEqual(words,self.raw)
            else: self.assertNotEqual(words,self.raw)
        self.receipt('shape',words=45,direct=True,frame=48,guards=0,pools=0,unreachable_divisor_check_emitted=True)

    def test_02_counts_full_unsigned_numerators_and_reachable_words(self):
        cases,reached=0,set()
        for count,phase,pattern in itertools.product((0,1,3,4,5,27,45,128,255),(0,8),(0,1,2)):
            values=VALUES[pattern:]+VALUES[:pattern]
            models=self.compare(fixture(count),randoms=values,phase=phase); reached.update(models[0].visits); cases+=1
        for value,phase in itertools.product(tuple(range(40))+VALUES[9:],(0,8)):
            self.compare(fixture(1),randoms=(value,),phase=phase); cases+=1
        for slot,group in itertools.product((0,25,-1,0x80000000),(0,255)):
            self.compare(fixture(1,slot,group),slot); cases+=1
        self.assertEqual(len(reached & set(range(screen.ENTRY,screen.ENTRY+180,4))),44)
        self.assertNotIn(screen.ENTRY+128,reached)
        self.receipt('guest',cases=cases,forms=3,reachable_words=44,dead_break_not_executed=True,
            timer120_even_count_zero=True,unsigned32_remainder_then_signed_float=True,invalid_slots_mapped_guest_only=True)

    def test_03_live_buffer_cached_group_count_and_post_call_store(self):
        s=screen.SYMBOLS; control=s['D_800C6660']+7*16; cases=0
        for phase,index in itertools.product((0,8),range(3)):
            actions={index:((control,OTHER,4),(s['D_80098914'],0,1),(control+14,255,1),
                (OTHER+index*104+76,bits(123),4))}
            models=self.compare(fixture(),phase=phase,actions=actions)
            self.assertEqual(models[0].number,3)
            self.assertNotEqual(read(models[0].memory,OTHER+index*104+76),bits(123)); cases+=1
        for phase in (0,8):
            actions={i:((control,OTHER if i%2==0 else BUFFER,4),) for i in range(5)}
            self.compare(fixture(5),phase=phase,actions=actions); cases+=1
        self.receipt('lifetimes',cases=cases,live_buffer_after_every_RNG=True,cached_count_group=True,
            all_fields_written_regardless_flags_types=True,all_effective=True)

    def test_04_timer_count_and_control_buffer_aliases(self):
        cases=0
        for group,phase in itertools.product((0,1),(0,8)):
            symbols=dict(screen.SYMBOLS,D_800C6660=screen.SYMBOLS['D_80098914']-12)
            forms=tuple(self.link(n,screen.ENTRY,symbols) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            memory=fixture(3,slot=0,group=group,symbols=symbols)
            put(memory,symbols['D_800C6660']+14,group,1)
            models=self.compare(memory,slot=0,phase=phase,symbols=symbols,forms=forms)
            self.assertEqual(models[0].number,0 if group==0 else 120); cases+=1
        self.receipt('aliases',cases=cases,timer_store_precedes_count_read=True,
            count_high_zero_low120=True,mapped_guest_only_not_portable_alias_proof=True)

    def test_05_retained_actual64_rng_and_seed_alias(self):
        cases,reached=0,set()
        for seed,count,phase,alias in itertools.product(rng.SEEDS,(0,1,5),(0,8),(False,True)):
            buffer=SEED-76 if alias else BUFFER
            models=self.compare(fixture(count,buffer=buffer,seed=seed),phase=phase,actual=True)
            reached.update(models[0].visits); cases+=1
        self.assertEqual(len(reached & set(range(RANDOM,RANDOM+72,4))),18)
        self.receipt('actual-rng',cases=cases,instructions=18,full_seed64=True,
            low_word_DIVU_sign_extended_V0=True,effective_seed_high_word_alias=True,RNG_unconverted=True)

    def test_06_rebases_and_fired_fault_prefixes(self):
        cases=0
        for j,start in enumerate((0x15207FFC,0x15308004)):
            symbols={name:(0x151ADA20+j*0x10000 if name.startswith('func_') else
                (0x80107FFC if i%2==j else 0x80218004)+i*0x10000) for i,name in enumerate(screen.SYMBOLS)}
            forms=tuple(self.link(n,start,symbols) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for count,phase in itertools.product((0,3),(0,8)):
                self.compare(fixture(count,symbols=symbols),phase=phase,symbols=symbols,start=start,forms=forms); cases+=1
        faults=0
        for count in (0,1,3):
            memory=fixture(count); complete=RateOracle(self.retail,memory).run()
            for fault in range(complete.accesses):
                models=[RateOracle(w,memory) for w in (self.retail,self.raw,self.padded)]
                for model in models:
                    model.fault=fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,fault)
                for model in models[1:]: self.assertEqual((model.memory,model.events,model.r,model.f,model.hi,model.lo),
                    (models[0].memory,models[0].events,models[0].r,models[0].f,models[0].hi,models[0].lo))
                faults+=1
        self.receipt('rebases-faults',symbols=3,links=2,cases=cases,fired_fault_triplets=faults,all_state_exact=True,
            no_portable_C_fault_or_FCSR_claim=True)

    def test_07_effective_semantic_and_fired_dead_break_controls(self):
        controls=(('timer',screen.SELECTED.replace('= 120','= 0')),
            ('range',screen.SELECTED.replace('% 20','% 16')),
            ('lost-sign',screen.SELECTED.replace('(s32)((u32)func_150ADA20() % 20) - 5','((u32)func_150ADA20() % 20) - 5U')),
            ('cached-buffer',screen.SELECTED.replace('    s32 count;','    struct04 *buffer = (struct04 *)control->unk0;\n    s32 count;').replace(
                '(struct04 *)control->unk0 + index','buffer + index')))
        actions={0:((screen.SYMBOLS['D_800C6660']+7*16,OTHER,4),)}
        for name,body in controls:
            self.assertNotEqual(body,screen.SELECTED); _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            values=(19,20,0xFFFFFFFF)
            model=RateOracle(words,fixture(),randoms=values,actions=actions).run()
            expected=Reference(fixture(),randoms=values,actions=actions).run()
            self.assertTrue((public(model.memory),model.calls)!=(public(expected.memory),expected.calls),name)
        for words in (self.retail,self.raw,self.padded):
            wrong=words.copy(); self.assertEqual(wrong[20],0x24140014); wrong[20]=0x24140000
            model=RateOracle(wrong,fixture(1))
            with self.assertRaises(division.DivideZeroTrap): model.run()
            self.assertIn(screen.ENTRY+128,model.visits)
        self.receipt('controls',fresh_semantic=4,all_effective=True,fired_zero_divisor_break_triplets=1,
            machine_mutation_only_not_defined_C_zero_division=True)

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
            expected[start:start+180]=parsed[1][0][start:start+180]; self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start<=o<start+180},
                {o:r for o,r in parsed[1][2].items() if not start<=o<start+180})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1]); self.receipt('owner',unchanged_neighbors=len(names)-1,
            both_padders=True,pools_exact=True,dispatcher171_collision134_impulse74_unchanged=True)

    def test_09_literal_source_ELF_and_seven_inputs(self):
        before_source=(self.out/'before-source').read_text(); current=(self.root/screen.SOURCE).read_text(); now=current!=before_source
        self.assertEqual(current,screen.install(before_source) if now else before_source)
        actual=(self.root/self.paths['elf']).read_bytes(); expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,180); extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if now: struct.pack_into('>45I',expected,start,*self.retail); struct.pack_into('>I',expected,extent,180)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=now,ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+180],actual[start:start+180])),
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
        elf=self.root/self.paths['elf']; actual=elf.read_bytes(); start=elf_slot_offset(actual,screen.ENTRY,180)
        for offset in (start+4,start+128,start+180,installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)+3):
            wrong=bytearray(actual); wrong[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p==elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_and_seven_inputs()
        guards=self.root/self.paths['guards']; wrong=guards.read_bytes()+b'\n'
        with patch.object(Path,'read_bytes',lambda p:wrong if p==guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_and_seven_inputs()
        self.receipt('integrity-controls',stale_installs=2,source=1,ELF=4,guards=1,all_effective=True)

    def test_11_actual_dispatcher_predicate_finish_and_rng(self):
        bodies={}
        for entry,rom,n in ((state.screen.ENTRY,state.screen.ROM,171),(state.HELPER,state.screen.ROM+684,27)):
            words=list(struct.unpack_from('>%dI'%n,self.before,elf_slot_offset(self.before,entry,n*4)))
            self.assertEqual(words,list(struct.unpack_from('>%dI'%n,self.rom,rom))); bodies[entry]=words
        table=self.rom[0x2275E0+0x8008443C-0x80082B20:0x2275E0+0x8008443C-0x80082B20+12]
        self.assertEqual(struct.unpack('>3I',table),(screen.ENTRY,0x1503F108,0x1503F16C))
        symbols=dict(state.screen.SYMBOLS,**screen.SYMBOLS)
        class ChainOracle(RateOracle):
            def __init__(model,memory,phase,code):
                state.StateOracle.__init__(model,bodies[state.screen.ENTRY],memory,symbols=symbols,phase=phase,
                    start=state.screen.ENTRY,connected=code)
                model.randoms,model.actual,model.number,model.hi,model.lo=VALUES,True,0,0,0
            def record_call(model,target):
                if target==RANDOM: return RateOracle.record_call(model,target)
                return state.StateOracle.record_call(model,target)
            def hook(model,target): return state.StateOracle.hook(model,target)
        class ChainReference(state.Reference):
            def call(ref,target,args):
                result=super().call(target,args)
                if target==screen.ENTRY:
                    rate=Reference(ref.memory,args[0],symbols=symbols,actual=True).run()
                    ref.memory=rate.memory; ref.calls.extend(rate.calls)
                return result
        cases=0
        with patch.dict(state.LABELS,{screen.ENTRY:'finish'}):
            for count,phase,seed,status in itertools.product((0,1,3,5),(0,8),rng.SEEDS[:6],(2,3)):
                memory=state.fixture(state=status,count=count,group=0,types=(255,),existing=True,flag=1,symbols=symbols)
                memory.update({STACK+i:0xA5 for i in range(-0x800,0x140)})
                put(memory,SEED,seed,8); put(memory,symbols['D_8008443C'],screen.ENTRY)
                expected=ChainReference(memory,symbols=symbols).run(); models=[]
                for words in (self.retail,self.raw,self.padded):
                    code={state.HELPER+i*4:w for i,w in enumerate(bodies[state.HELPER])}
                    code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                    code.update({RANDOM+i*4:w for i,w in enumerate(self.random)})
                    model=ChainOracle(memory,phase,code).run(); models.append(model)
                    self.assertEqual((public(model.memory),model.calls),(public(expected.memory),expected.calls))
                    self.assertEqual(model.number,count)
                for model in models[1:]: self.assertEqual((model.memory,model.events,model.r,model.f,model.hi,model.lo),
                    (models[0].memory,models[0].events,models[0].r,models[0].f,models[0].hi,models[0].lo))
                cases+=1
        self.receipt('connected-caller',cases=cases,actual_dispatcher171_predicate27_finish45_rng18=True,
            original_group0_finish_table=True,other_callbacks_and_tails_modeled=True,not_full_gameplay_acceptance=True)

    def test_12_native32_full_counts_unsigned_boundaries_and_live_buffers(self):
        prefix=r'''
typedef unsigned char u8; typedef short s16; typedef unsigned u32; typedef int s32; typedef float f32;
typedef struct { u32 words[26]; } struct04;
typedef struct { s32 unk0,unk4,unk8; u8 tail[4]; } struct106;
typedef char widths[(sizeof(void *)==4 && sizeof(struct04)==104 && sizeof(struct106)==16)?1:-1];
struct106 D_800C6660[26]; u8 D_80098914[3];
static struct04 banks[2][256],expected[2][256]; static int number,pattern,mutate,selected;
static const u32 draws[8]={0,1,19,20,21,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
s32 func_150ADA20(void) {
    int i=number++;
    if(mutate) { D_800C6660[selected].unk0=(s32)banks[i%2]; D_80098914[selected%3]=0; }
    return (s32)draws[(i+pattern)%8];
}
static void initialize(int count,int p,int slot,int action) {
    number=0; pattern=p; selected=slot; mutate=action;
    for(int g=0;g<3;g++) D_80098914[g]=count;
    for(int i=0;i<4;i++) ((u32 *)&D_800C6660[slot])[i]=0x35353535;
    D_800C6660[slot].unk0=count?(s32)banks[0]:0; ((u8 *)&D_800C6660[slot])[14]=slot%3;
    for(int b=0;b<2;b++) for(int i=0;i<256;i++) for(int j=0;j<26;j++) banks[b][i].words[j]=0x35353535+i+j+b;
}
static void reference(int slot) {
    struct106 *control=&D_800C6660[slot]; int group=((u8 *)control)[14];
    *(s16 *)((u8 *)control+12)=120; int count=D_80098914[group];
    for(int i=0;i<count;i++) { u32 value=(u32)func_150ADA20();
        f32 rate=(f32)((s32)(value%20u)-5); f32 *record=(f32 *)((struct04 *)control->unk0+i); record[19]=rate; }
}
'''
        suffix=r'''
static int run(u32 *failure) {
    int slots[3]={0,7,25}; unsigned cases=0;
    for(int count=0;count<256;count++) for(int p=0;p<8;p++) for(int s=0;s<3;s++) for(int action=0;action<2;action++) {
        initialize(count,p,slots[s],action); reference(slots[s]);
        u32 control[4]; for(int j=0;j<4;j++) control[j]=((u32 *)&D_800C6660[slots[s]])[j];
        for(int i=0;i<2*256*26;i++) ((u32 *)expected)[i]=((u32 *)banks)[i];
        initialize(count,p,slots[s],action); func_1503EFC4(slots[s]); cases++;
        for(int i=0;i<2*256*26;i++) if(((u32 *)banks)[i]!=((u32 *)expected)[i]) {
            failure[0]=cases; failure[1]=i; failure[2]=((u32 *)banks)[i]; return 1;
        }
        for(int j=0;j<4;j++) if(((u32 *)&D_800C6660[slots[s]])[j]!=control[j]) {
            failure[0]=cases; failure[1]=0x10000+j; failure[2]=((u32 *)&D_800C6660[slots[s]])[j]; return 1;
        }
        if(number!=count) return 3;
    }
    return cases==12288?0:2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result==1) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],prefix+screen.SELECTED+suffix,profile),(0,''))
        controls=(('timer',screen.SELECTED.replace('= 120','= 0')),
            ('signed-remainder',screen.SELECTED.replace('(u32)func_150ADA20() % 20','func_150ADA20() % 20')),
            ('lost-sign',screen.SELECTED.replace('(s32)((u32)func_150ADA20() % 20) - 5','((u32)func_150ADA20() % 20) - 5U')),
            ('cached-buffer',screen.SELECTED.replace('    s32 count;','    struct04 *buffer = (struct04 *)control->unk0;\n    s32 count;').replace(
                '(struct04 *)control->unk0 + index','buffer + index')))
        for name,body in controls:
            self.assertNotEqual(body,screen.SELECTED); result,detail=self.run_native('native-negative-'+name,prefix+body+suffix)
            self.assertEqual(result,1); self.assertEqual(len(detail),3)
        self.receipt('native',cases_per_profile=12288,profiles=['O2','O0'],counts_all_0_through255=True,
            unsigned_high_bit_and_negative_rates=True,live_alternating_buffers_cached_count=True,
            all_words_of_two_256_record_banks_and_control=True,effective_controls=4,
            no_private_alias_hardware_FCSR_claim=True)


if __name__=='__main__':
    unittest.main()
