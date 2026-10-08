"""Complete timer truncation, callback lifetime, live player state and free ordering."""

import csv
import itertools
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_record_state_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_attachment_progress_match import ProgressReference
from tools.tests.test_game_point_transform_match import put, read

RECORD, CALLBACK = 0x20000, 0x15100010
WRAPPER, DISTANCE = 0x151D8BE0, 0x151D8C00
MAP, STATE = 0x80084060, 0x800BE93C
SOURCE = 'conker/src/game/generated_205C90.c'
DELTAS = (0,1,2,32767,32768,65535,-1,-32768,0x7FFFFFFF,-0x80000000)


def public(memory):
    return {a:v for a,v in memory.items() if not prior.STACK-0x600<=a<prior.STACK+0x140}


def public_events(model):
    return [e for e in model.events if e[0]=='CALL' or not prior.STACK-0x600<=e[1]<prior.STACK+0x140]


def fixture(timer=0,step=1,flags=1,selector=255,level=7,mirror=7,mask=15,
            record=RECORD,symbols=None,callback=CALLBACK):
    symbols=symbols or screen.SYMBOLS
    memory={prior.STACK+i:0xA5 for i in range(-0x100,0x100)}
    memory.update({record+i:0xA5 for i in range(-16,80)})
    put(memory,record+0xE,flags,1)
    put(memory,record+0x10,timer,2)
    put(memory,record+0x12,level,1)
    put(memory,record+0x13,mask,1)
    put(memory,record+0x14,selector,1)
    put(memory,record+0x16,mirror,1)
    put(memory,symbols['D_800BE9E4'],step,4)
    for i in range(-128,256):
        put(memory,(symbols['D_8008FCC0']+i*4)&0xFFFFFFFF,callback+(4 if i>=128 else 0),4)
    return memory


def effects(mode,role,player,record):
    if role=='callback':
        if mode==1:
            return ((record+0x12,9,1),(record+0x13,0xF5,1),(record+0x10,32767,2))
        if mode==4:
            return ((record+0x12,7,1),(record+0x16,7,1),(record+0x13,15,1))
        if mode==5:
            return ((record+0xE,0,1),(record+0x10,32767,2),(record+0x12,0,1))
    if role=='clear' and mode==2:
        return ((record+0x12,player*17+3,1),(record+0x13,255^(1<<player),1))
    if role=='register' and mode==3:
        return ((record+0x12,player*31+4,1),(record+0x13,(0xA5>>player)|8,1))
    if role=='free' and mode==7:
        return ((record+0x12,0xEE,1),(record+0x16,0xDD,1))
    return ()


class StateReference(ProgressReference):
    def put(self,address,value,size=1):
        address&=0xFFFFFFFF
        value&=(1<<(size*8))-1
        self.events.append(('W',address,size,value))
        assert all(address+i in self.memory for i in range(size)),('unmapped store',address,size)
        put(self.memory,address,value,size)

    def call(self,role,args,target,mode,record):
        self.events.append(('CALL',role,args,target))
        self.calls.append((role,args,target))
        for address,value,size in effects(mode,role,args[0] if role in ('clear','register') else 0,record):
            self.put(address,value,size)

    def run(self,record=RECORD,mode=0,symbols=None,connected=False,real_clear=False):
        symbols=symbols or screen.SYMBOLS
        expired=False
        if self.get(record+0xE,1)&1:
            timer=self.get(record+0x10,2)
            step=self.get(symbols['D_800BE9E4'])
            self.put(record+0x10,(timer-step)&65535,2)
            expired=self.get(record+0x10,2)>=32768
        selector=self.get(record+0x14,1)
        if selector!=255:
            selector=selector if selector<128 else selector-256
            target=self.get((symbols['D_8008FCC0']+selector*4)&0xFFFFFFFF)
            self.call('callback',(record,),target,0 if connected else mode,record)
            if connected:
                self.call('distance',(record,record+0x18),DISTANCE,0,record)
                for address,value,size in effects(mode,'callback',0,record):
                    self.put(address,value,size)
        level=self.get(record+0x12,1)
        mirror=self.get(record+0x16,1)
        if level!=mirror:
            for player in range(4):
                if self.get(record+0x13,1)&(1<<player):
                    self.call('clear',(player,),symbols['func_1501C17C'],0 if real_clear else mode,record)
                    if real_clear:
                        index=self.get(MAP+player,1)
                        if index<4:
                            self.put(STATE+index,0,1)
                    level=self.get(record+0x12,1)
                    self.call('register',(player,level),symbols['func_1501C010'],mode,record)
            self.put(record+0x16,self.get(record+0x12,1),1)
        if expired:
            self.call('free',(record,),symbols['func_1516972C'],mode,record)
        return self


class StateOracle(TriangleOracle):
    def __init__(self,words,memory,record=RECORD,phase=0,mode=0,symbols=None,entry=screen.ENTRY,
                 callback=CALLBACK,connected=None,connected_callback=False,fail_after=None,unmap_free=False):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(record,),connected=connected)
        self.record,self.mode,self.symbols=record,mode,symbols or screen.SYMBOLS
        self.callback,self.connected_callback=callback,connected_callback
        self.fail_after,self.unmap_free=fail_after,unmap_free
        self.fault_injected=False

    def execute(self,word):
        if word>>26==32:
            CopyOracle.execute(self,word)
        else:
            super().execute(word)

    def role(self,target):
        if target in (self.callback,self.callback+4):
            return 'callback'
        if target==DISTANCE and self.connected_callback:
            return 'distance'
        return {self.symbols['func_1501C17C']:'clear',self.symbols['func_1501C010']:'register',
                self.symbols['func_1516972C']:'free'}[target]

    def record_call(self,target):
        role=self.role(target)
        args=tuple(self.r[4:6 if role in ('register','distance') else 5])
        self.calls.append((role,args,target))
        self.events.append(('CALL',role,args,target))

    def hook(self,target):
        role=self.role(target)
        for address,value,size in effects(self.mode,'callback' if role=='distance' else role,self.r[4],self.record):
            self.put(address,value,size)
        if self.mode==6 and role in ('callback','clear','register'):
            self.put(prior.STACK+(self.before[29]-prior.STACK),RECORD+0x400,4)
        if self.fail_after and self.fail_after[0]==role and not self.fault_injected:
            del self.memory[self.fail_after[1]]
            self.fault_injected=True
        if role=='free' and self.unmap_free:
            for i in range(0x40):
                del self.memory[self.record+i]
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=0x81234567


class GameRecordStateUpdateTests(unittest.TestCase):
    run_host=prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-record-state-update-test'
        cls.out.mkdir(exist_ok=True)
        cls.record,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.words=screen.normalize(cls.raw)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>64I',cls.rom,screen.ROM))
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)

    def receipt(self,name,data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory=None,record=RECORD,phase=0,mode=0,words=None,symbols=None,entry=screen.ENTRY,
                callback=CALLBACK,connected=None,real_clear=False,connected_callback=False):
        memory=memory or fixture()
        ref=StateReference(memory,phase).run(record,mode,symbols,connected_callback,real_clear)
        inputs=[words if words is not None else self.words]
        if symbols is None and entry==screen.ENTRY:
            inputs.append(self.retail)
        models=[StateOracle(w,memory,record,phase,mode,symbols,entry,callback,connected,connected_callback).run()
                for w in inputs]
        for model in models:
            self.assertEqual((model.calls,public_events(model),public(model.memory)),
                             (ref.calls,ref.events,public(ref.memory)))
        if len(models)==2:
            self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                             (models[1].r,models[1].f,models[1].events,models[1].memory))
        return models

    def test_01_complete_slot_and_closed_private_byte_guards(self):
        self.assertEqual((self.record['body_words'],self.record['frame'],self.record['differences']),(64,0x28,4))
        self.assertEqual(self.words,self.retail)
        self.assertEqual((self.record['diagnostics'],self.record['pool_bytes']),('',0))
        self.assertEqual(sum(map(len,self.record['relocations'].values())),7)
        for index in (0,5,19,35,54):
            stale=self.raw.copy()
            stale[index]^=1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        self.receipt('slot',dict(words=64,bytes=256,frame=40,raw_differences=4,normalized_differences=0,
                                private_byte_guards=4,relocations=7,stale_rejections=5,pools_diagnostics=0))

    def test_02_timer_mask_selector_bytes_and_reachable_words(self):
        cases,seen=0,set()
        for timer,phase in itertools.product(range(65536),(0,8)):
            memory=fixture(timer,DELTAS[timer%len(DELTAS)],1,255,7,7,15)
            for model in self.compare(memory,phase=phase):
                seen.update(model.visits)
            cases+=1
        for selector,flags,mask,phase in itertools.product(range(256),(0,1),(0,1,5,15,255),(0,8)):
            for model in self.compare(fixture(0x8000,1,flags,selector,selector,selector^255,mask),phase=phase):
                seen.update(model.visits)
            cases+=1
        for flags,mask,phase in itertools.product(range(256),range(256),(0,8)):
            self.compare(fixture(0,0,flags,255,mask,mask^1,mask),phase=phase)
            cases+=1
        for timer,step,phase in itertools.product((0,1,32767,32768,65535),DELTAS,(0,8)):
            self.compare(fixture(timer,step,1,0,0,255,255),phase=phase)
            cases+=1
        self.assertEqual(seen,set(range(screen.ENTRY,screen.ENTRY+256,4)))
        self.receipt('guest',dict(cases=cases,all_timer_u16_patterns=True,all_signed_selector_bytes=True,
            all_flag_mask_byte_pairs=True,all_64_words_reached=True,SP_phases=2,
            negative_table_indices_are_guest_instruction_evidence_not_portable_C=True))

    def test_03_lazy_fields_and_required_fault_prefixes(self):
        memory=fixture(flags=0,selector=255)
        for address in (RECORD+0x10,RECORD+0x11,screen.SYMBOLS['D_800BE9E4'],RECORD+0x13):
            del memory[address]
        for address in list(memory):
            if screen.SYMBOLS['D_8008FCC0']-512<=address<screen.SYMBOLS['D_8008FCC0']+1024:
                del memory[address]
        self.compare(memory)
        cases=0
        for phase in (0,8):
            sp=prior.STACK+phase-0x28
            addresses=(sp+0x18,sp+0x1C,sp+0x14,sp+0x23,RECORD+0xE,RECORD+0x10,
                       RECORD+0x11,screen.SYMBOLS['D_800BE9E4'],RECORD+0x14,
                       screen.SYMBOLS['D_8008FCC0'],RECORD+0x12,RECORD+0x16,RECORD+0x13)
            for address in addresses:
                memory=fixture(timer=0,selector=0,level=7,mirror=0)
                del memory[address]
                models=[StateOracle(w,memory,phase=phase) for w in (self.words,self.retail)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                self.assertEqual((models[0].r,models[0].f,models[0].events,models[0].memory),
                                 (models[1].r,models[1].f,models[1].events,models[1].memory))
                cases+=1
            for role,address in (('callback',RECORD+0x12),('clear',RECORD+0x12),
                                  ('register',RECORD+0x13),('register',RECORD+0x16),
                                  ('register',sp+0x23),('free',sp+0x1C)):
                models=[StateOracle(w,fixture(0,1,1,0,7,0,15),phase=phase,fail_after=(role,address))
                        for w in (self.words,self.retail)]
                for model in models:
                    with self.assertRaises(AssertionError):
                        model.run()
                self.assertEqual((models[0].events,models[0].memory),(models[1].events,models[1].memory))
                cases+=1
        self.receipt('faults',dict(lazy_skip_case=True,required_fault_prefixes=cases,
            full_normalized_retail_prefixes_equal=True,CP0_fault_metadata_hardware_not_modeled=True))

    def test_04_mutations_captured_expiry_and_complete_raw_schedule(self):
        cases=0
        for mode,mask,timer,selector,phase in itertools.product(range(8),(0,1,5,15,255),
                                                              (0,1,32767,32768),(0,255),(0,8)):
            memory=fixture(timer,1,1,selector,7,0,mask)
            self.compare(memory,phase=phase,mode=mode)
            raw=StateOracle(self.raw,memory,phase=phase,mode=mode).run()
            exact=StateOracle(self.retail,memory,phase=phase,mode=mode).run()
            self.assertEqual((raw.r,raw.f,public_events(raw),public(raw.memory)),
                             (exact.r,exact.f,public_events(exact),public(exact.memory)))
            # The complete raw slot differs only at the private expiry byte.
            old=prior.STACK+phase-0x28+(self.raw[5]&65535)
            new=prior.STACK+phase-0x28+(self.retail[5]&65535)
            self.assertEqual({a:v for a,v in raw.memory.items() if a not in (old,new)},
                             {a:v for a,v in exact.memory.items() if a not in (old,new)})
            translated=[(e[0],new,*e[2:]) if e[0] in ('R','W') and e[1]==old else e for e in raw.events]
            self.assertEqual(translated,exact.events)
            cases+=1
        for phase in (0,8):
            models=[StateOracle(w,fixture(0,1,1,0,7,0,15),phase=phase,unmap_free=True).run()
                    for w in (self.words,self.retail)]
            self.assertEqual(models[0].events,models[1].events)
        self.receipt('mutations',dict(cases=cases,modes=8,expiry_captured_before_callback=True,
            private_home_owner_remains_captured=True,raw_private_delta_only_two_byte_locations=True,
            no_record_read_after_free=True,private_stack_alias_C_contract_not_claimed=True))

    def test_05_native32_actual_C_mutations_and_canaries(self):
        self.fixture=NATIVE_PREFIX+screen.SELECTED+'\n'+NATIVE_REFERENCE
        self.run_host(NATIVE_RUN)
        self.receipt('native',dict(cases=1607424,all_u16_timer_patterns_ten_signed_steps=True,
            all_flag_mask_byte_pairs=True,all_level_selector_bytes=True,modes=7,pointer_int_bytes=4,
            complete_C_through_volatile_pointer=True,canary_bytes=96,
            defined_aligned_objects_and_nonnegative_callback_indices_only=True))

    def test_06_profiles_and_effective_compiled_negatives(self):
        records,ordinary,negatives=[],0,0
        forms=[(n,b,'o2g3') for n,b in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p!='o2g3']
        settings=((32768,1,1,0,7,0,15,0),(32767,-1,1,128,9,0,15,0),
                  (0,1,2,0,7,0,15,1),(0,1,1,255,7,0,15,2),
                  (0,1,1,0,7,0,15,3),(0,1,1,0,7,7,15,1),
                  (0,1,1,0,7,0,15,5),(65535,0x7FFFFFFF,1,255,7,0,255,0))
        for name,body,profile in forms:
            meta,words=screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(meta)
            equal=[]
            for timer,step,flags,selector,level,mirror,mask,mode in settings:
                memory=fixture(timer,step,flags,selector,level,mirror,mask)
                ref=StateReference(memory).run(mode=mode)
                model=StateOracle(words,memory,mode=mode).run()
                # Other profiles may reread fields; compare public flow and results.
                equal.append((model.calls,public(model.memory))==(ref.calls,public(ref.memory)))
            if name.startswith('negative-'):
                self.assertFalse(all(equal),name)
                negatives+=1
            else:
                self.assertTrue(all(equal),name)
                ordinary+=len(settings)
        self.receipt('controls',dict(forms=len(records),ordinary_executions=ordinary,
            effective_negatives=negatives,all_controls_execute_without_exceptions=True,measurements=records))

    def test_07_copied_owner_real_padder_and_independent_links(self):
        source=(self.root/SOURCE).read_text().replace(screen.SELECTED,screen.ORIGINAL)
        self.assertEqual(source.count(screen.ORIGINAL),1)
        candidate=source.replace(screen.ORIGINAL,screen.SELECTED)
        if screen.DECLARATIONS not in candidate:
            candidate=candidate.replace('void func_1501C17C',screen.DECLARATIONS+'void func_1501C17C',1)
        objects=[]
        for name,body in (('baseline',source),('selected',candidate)):
            obj,warnings=compile_owner(self.root,self.out,body,'owner-'+name)
            self.assertEqual(warnings,[])
            processed=self.out/('owner-'+name+'-processed.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable,str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(processed.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(processed)
        old,previous,old_rel=parse_object(objects[0])
        text,current,rel=parse_object(objects[1])
        self.assertEqual(current.keys(),previous.keys())
        for name,fn in current.items():
            if name==screen.FUNCTION:
                continue
            before=previous[name]
            self.assertEqual(text[fn['value']:fn['value']+fn['size']],old[before['value']:before['value']+before['size']],name)
            self.assertEqual({o-fn['value']:r for o,r in rel.items() if fn['value']<=o<fn['value']+fn['size']},
                             {o-before['value']:r for o,r in old_rel.items() if before['value']<=o<before['value']+before['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        target=current[screen.FUNCTION]
        isolated,_,isolated_rel=parse_object(self.out/'selected.o')
        self.assertEqual(text[target['value']:target['value']+256],isolated[:256])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value']<=o<target['value']+256},isolated_rel)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            reader=csv.DictReader(stream)
            fields,guards=reader.fieldnames,list(reader)
        assert_guard_history(self,guards[:11148])
        assert_guard_history(self,guards)
        if len(guards)==11148:
            guards+=screen.owner_guards()
        else:
            self.assertEqual(guards[11148:11152],screen.owner_guards())
        manifest=self.out/'qualification-guards.csv'
        with manifest.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader()
            writer.writerows(guards)
        assembly=emit_padded_assembly(objects[1],self.root/'conker/asm/205C90.s',word_patches_path=manifest,filename='generated_205C90')
        start=assembly.index('.type %s, @function'%screen.FUNCTION)
        end=assembly.index('.size %s, . - %s'%(screen.FUNCTION,screen.FUNCTION),start)
        end=assembly.index('\n',end)+1
        self.assertNotIn('.space',assembly[end:assembly.find('.type ',end)])
        asm,obj=self.out/'padded.s',self.out/'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n'%screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        _,functions,relocations=parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'],256)
        self.assertEqual(relocations,isolated_rel)
        self.assertNotIn('.rodata',sections(obj))
        cases=0
        for index in range(6):
            entry=screen.ENTRY+(0x1000004 if index==1 else 0)
            symbols=screen.SYMBOLS.copy()
            if index>=2:
                for n,name in enumerate(symbols):
                    symbols[name]=((0x80007FFC,0xFFFF7FF8,0x7FFF8000,0x81018004)[index-2]+n*0x100
                                   if name.startswith('D_') else symbols[name]+index*0x100004)
            script,elf=self.out/'padded.ld',self.out/('rebased-%d.elf'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            words=list(struct.unpack_from('>64I',sections(elf)['.text'][1]))
            expected=self.retail.copy()
            for offset,rows in relocations.items():
                self.assertEqual(len(rows),1)
                kind,name=rows[0]
                value=symbols[name]
                word=expected[offset//4]
                if kind=='R_MIPS_26':
                    expected[offset//4]=word&0xFC000000|value>>2&0x3FFFFFF
                else:
                    value=(value+0x8000)>>16 if kind=='R_MIPS_HI16' else value
                    expected[offset//4]=word&0xFFFF0000|value&65535
            self.assertEqual(words,expected)
            for timer,mask,mode,phase in itertools.product((0,32768),(0,15,255),(0,2,3),(0,8)):
                memory=fixture(timer=timer,selector=0,mirror=0,mask=mask,symbols=symbols)
                # Rebased retail instructions must also be rebased; use the selected independent link.
                self.compare(memory,phase=phase,mode=mode,words=words,symbols=symbols,entry=entry)
                cases+=1
        self.receipt('owner-padder',dict(neighbors=len(current)-1,pools_relative_relocations_unchanged=True,
            strict_diagnostics=0,padded_bytes=256,guards=4,independent_links=6,rebased_executions=cases,relocations=7))

    def test_08_actual_wrapper_clearer_table_and_guard_history(self):
        wrapper=list(struct.unpack_from('>8I',self.rom,0x206090))
        clearer=list(struct.unpack_from('>13I',self.rom,0x4962C))
        connected=dict(zip(range(WRAPPER,WRAPPER+32,4),wrapper))
        connected.update(zip(range(screen.SYMBOLS['func_1501C17C'],screen.SYMBOLS['func_1501C17C']+52,4),clearer))
        cases=0
        for timer,mask,mapping,mode,phase in itertools.product((0,1,32768),range(16),
                ((0,1,2,3),(255,0,1,2),(3,2,1,0)),(0,1,3,5),(0,8)):
            memory=fixture(timer,1,1,0,7,0,mask,callback=WRAPPER)
            for i,value in enumerate(mapping):
                put(memory,MAP+i,value,1)
            for i in range(4):
                put(memory,STATE+i,0x5A+i,1)
            self.compare(memory,phase=phase,mode=mode,callback=WRAPPER,connected=connected,
                         connected_callback=True,real_clear=True)
            cases+=1
        functions,_,addresses=load_elf_functions(str(self.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION],functions[screen.FUNCTION]),(screen.ENTRY,self.retail))
        self.assertEqual(functions['func_151D8BE0'],wrapper)
        address,data=sections(self.root/'conker/build/conker.us.elf')['.game_data']
        self.assertEqual(list(struct.unpack_from('>4I',data,0x8008FCC0-address)),[WRAPPER,0,0,0])
        self.assertEqual(struct.unpack_from('>I',data,0x8008C174-address)[0],screen.ENTRY)
        source=(self.root/SOURCE).read_text()
        installed=screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL),1)
        with (self.root/'conker/retail_word_patches.us.csv').open() as stream:
            guards=list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertEqual(guards[11148:11152],screen.owner_guards() if installed else [])
        before=guards[:11148]
        proposed=before+screen.owner_guards()
        assert_guard_history(self,proposed)
        self.assertEqual(len(proposed),11152)
        for i in range(4):
            bad=[dict(row) for row in proposed]
            bad[11148+i]['replacement']='0x00000000'
            with self.assertRaises(AssertionError):
                assert_guard_history(self,bad)
        for bad in (proposed[:-1],proposed+[dict(proposed[-1])],before+list(reversed(screen.owner_guards()))):
            with self.assertRaises(AssertionError):
                assert_guard_history(self,bad)
        self.receipt('connected',dict(cases=cases,actual_wrapper_words=8,actual_clearer_words=13,
            real_tables_and_complete_target_match_retail=True,guards=4,prior_rows=11148,
            controlled_distance_registration_free_not_full_gameplay_hardware=True))


NATIVE_PREFIX=r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;
s32 D_800BE9E4;
void (*D_8008FCC0[128])(u8 *);
static u8 storage[96] __attribute__((aligned(4)));
static u8 expected[96] __attribute__((aligned(4)));
static u32 log[16][3],wanted[16][3],calls,wants;
static int mode,error;
static u8 *owner=storage+16;
static void mutate(u8 *p,int role,int player) {
 if(role==0&&mode==1){p[18]=9;p[19]=0xF5;*(s16 *)(p+16)=32767;}
 if(role==0&&mode==4){p[18]=7;p[22]=7;p[19]=15;}
 if(role==0&&mode==5){p[14]=0;*(s16 *)(p+16)=32767;p[18]=0;}
 if(role==1&&mode==2){p[18]=player*17+3;p[19]=255^(1<<player);}
 if(role==2&&mode==3){p[18]=player*31+4;p[19]=(0xA5>>player)|8;}
 if(role==3&&mode==7){p[18]=0xEE;p[22]=0xDD;}
}
static void call(int role,u32 a,u32 b) {
 if(calls>=16){error=1;return;}
 log[calls][0]=role;log[calls][1]=a;log[calls][2]=b;calls++;
 mutate(owner,role,(int)a);
}
static void callback(u8 *p){if(p!=owner)error=1;call(0,0,0);}
void func_1501C17C(u8 player){call(1,player,0);}
void func_1501C010(u8 player,u8 level){call(2,player,level);}
void func_1516972C(u8 *p){if(p!=owner)error=1;call(3,0,0);}
'''

NATIVE_REFERENCE=r'''
static void want(int role,u32 a,u32 b,u8 *p) {
 wanted[wants][0]=role;wanted[wants][1]=a;wanted[wants][2]=b;wants++;
 mutate(p,role,(int)a);
}
static int check(u32 timer,s32 step,int flags,int selector,int level,int mirror,int mask,int action) {
 u8 *p=expected+16;u32 i;int expired=0;u32 difference;
 void (*volatile invoke)(u8 *)=func_151D8A24;
 mode=action;calls=wants=error=0;D_800BE9E4=step;
 for(i=0;i<96;i++)storage[i]=expected[i]=0xA5;
 p[14]=owner[14]=flags;*(s16 *)(p+16)=*(s16 *)(owner+16)=timer;
 p[18]=owner[18]=level;p[19]=owner[19]=mask;p[20]=owner[20]=selector;p[22]=owner[22]=mirror;
 if(flags&1){
   difference=(u32)(s32)*(s16 *)(p+16)-(u32)step;
   *(s16 *)(p+16)=(s16)difference;
   expired=(*(s16 *)(p+16)<0);
 }
 if(selector!=255)want(0,0,0,p);
 if(p[18]!=p[22]){
   for(i=0;i<4;i++){
     if(p[19]&(1U<<i)){want(1,i,0,p);want(2,i,p[18],p);}
   }
   p[22]=p[18];
 }
 if(expired)want(3,0,0,p);
 invoke(owner);
 if(error||calls!=wants||D_800BE9E4!=step)return 1;
 for(i=0;i<96;i++)if(storage[i]!=expected[i])return 2;
 for(i=0;i<calls;i++){
   if(log[i][0]!=wanted[i][0]||log[i][1]!=wanted[i][1]||log[i][2]!=wanted[i][2])return 3;
 }
 return 0;
}
'''

NATIVE_RUN=r'''
u32 timer,i,flags,mask,selector,level,count=0;int action;
static s32 steps[]={0,1,2,32767,32768,65535,-1,-32768,2147483647,(-2147483647-1)};
if(sizeof(void *)!=4||sizeof(int)!=4||sizeof(short)!=2)return 10;
for(i=0;i<128;i++)D_8008FCC0[i]=callback;
for(timer=0;timer<65536;timer++)for(i=0;i<10;i++)for(flags=0;flags<2;flags++){
 if(check(timer,steps[i],flags,255,7,7,15,0))return 11;
 count++;
}
for(flags=0;flags<256;flags++)for(mask=0;mask<256;mask++){
 if(check(32768,1,flags,255,mask,mask^1,mask,3))return 12;
 count++;
}
for(selector=0;selector<129;selector++)for(level=0;level<256;level++)for(action=0;action<8;action++){
 if(action==6)continue;
 if(check(level*257,steps[level%10],1,selector==128?255:selector,level,level^1,level,action))return 13;
 count++;
}
if(count!=1607424)return 14;
'''
