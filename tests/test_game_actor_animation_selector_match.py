"""Complete selector transition, independent ordered references, native ABI and linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_animation_selector_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_update_dispatch_match as dispatch
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

S=screen.recovery.SYMBOLS
STACK,SELECTORS=guest.STACK,0x24000
CALL_COUNTS={'func_150837D4':3,'func_1505E650':7,'func_1507EABC':1}
DISTANCES=(0,812*25,-812,813,-813,0x7FFFFFFF,-0x80000000)


def public(address):return not STACK-0x400<=address<STACK+0x100


def actor_address(distance=0,symbols=S):
    return (symbols['D_800CC2D0']+distance)&0xFFFFFFFF


def fixture(pending=2,count=3,current=0,identity=7,animation=8,frame=2,length=3,
        mode=1,equal=False,distance=0,symbols=S,selectors=SELECTORS):
    actor=actor_address(distance,symbols)
    memory={STACK+i:0xA5 for i in range(-0x400,0x100)}
    for start,size in ((actor,0x32C),(SELECTORS,256),(symbols['D_800D1588'],1024),
            (symbols['D_800C5A90'],512)):
        memory.update({(start+i)&0xFFFFFFFF:0xA5 for i in range(size)})
    for i in range(256):
        put(memory,symbols['D_800D1588']+i*4,0xAB000000+i*17)
        put(memory,symbols['D_800C5A90']+i*2,length,2)
        put(memory,SELECTORS+i,animation,1)
    for offset,value,size in ((4,identity,1),(0x1C9,pending,1),(0x1C8,current,1),
            (0x2C9,count,1),(0x84,frame,2),(0x2C4,selectors,4)):
        put(memory,actor+offset,value,size)
    if equal:put(memory,symbols['D_800D1588']+animation*4,read(memory,symbols['D_800D1588']+identity*4,4))
    put(memory,symbols['D_800C35EA'],mode,1);put(memory,symbols['D_800C3638'],0xA5,1)
    return memory


def actions(memory,actor,animation,plan,symbols=S,frame=None):
    first=[];second=[]
    if plan in (1,2):
        first=[(actor+4,254,1),(actor+0x1C9,99,1),(actor+0x2C9,0,1),
            (actor+0x1C8,201,1),(actor+0x2C4,SELECTORS+128,4),
            (SELECTORS+(read(memory,actor+0x1C9,1)-1 if read(memory,actor+0x1C9,1)!=255 else 0),255,1),
            (symbols['D_800D1588']+read(memory,actor+4,1)*4,0x12345678,4),
            (actor+0x84,65534 if plan==1 else 1,2),(symbols['D_800C35EA'],1 if plan==1 else 255,1)]
        second=[(symbols['D_800C35EA'],0 if plan==1 else 1,1),(actor+0x84,321,2)]
    elif plan==3:
        first=[(symbols['D_800D1588']+animation*4,
            read(memory,symbols['D_800D1588']+read(memory,actor+4,1)*4,4),4),
            (symbols['D_800C35EA'],1,1)]
    elif plan==4:
        first=[(symbols['D_800C35EA'],0,1)]
        second=[(symbols['D_800C35EA'],1,1)]
    elif plan==5:
        assert frame is not None
        first=[(frame+0x3C,0xFE,4),(frame+0x34,255,4),(frame+0x38,0xAB000000+255*17,4)]
    return {symbols['func_150837D4']:tuple(first),symbols['func_1505E650']:tuple(second)}


def reference(memory,actor,symbols=S,phase=0,mutations=None,raw=False):
    state,events,calls=memory.copy(),[],[]
    frame=STACK+phase-0x40
    animation_home,resource_home=(0x30,0x34) if raw else (0x34,0x38)
    def get(address,size=1):
        assert all(address+i in state for i in range(size)),('unmapped reference read',address,size)
        value=read(state,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size=1):
        assert all(address+i in state for i in range(size)),('unmapped reference write',address,size)
        value&=(1<<(size*8))-1;put(state,address,value,size);events.append(('W',address,size,value))
    def call(name,args):
        target=symbols[name]
        if len(args)==7:
            args=(*args[:4],*(read(state,frame+i,4) for i in (0x10,0x14,0x18)))
        events.append(('CALL',target,args));calls.append((target,*args))
        for address,value,size in (mutations or {}).get(target,()):store(address,value,size)
    store(frame+0x28,0x5A000010,4);store(frame+0x2C,0xDEAD0000,4)
    pending=get(actor+0x1C9)
    if pending:
        original=get(symbols['D_800D1588']+get(actor+4)*4,4)
        if pending==255:
            store(actor+0x1C9,0);index=0
        else:
            count=get(actor+0x2C9);index=pending-1
            if index>=count:
                get(frame+0x2C,4);get(frame+0x28,4);return state,events,calls
            if index==get(actor+0x1C8):
                get(frame+0x2C,4);get(frame+0x28,4);return state,events,calls
        animation=get(get(actor+0x2C4,4)+index)
        distance=signed((actor-symbols['D_800CC2D0'])&0xFFFFFFFF)
        slot=(abs(distance)//812)*(-1 if distance<0 else 1)
        store(frame+resource_home,original,4);store(frame+0x3C,index,4)
        store(frame+animation_home,animation,4)
        call('func_150837D4',(slot&0xFFFFFFFF,animation,0))
        index=get(frame+0x3C,4);animation=get(frame+animation_home,4);original=get(frame+resource_home,4)
        store(actor+0x1C8,index)
        mode=get(symbols['D_800C35EA'])
        if mode==1:store(symbols['D_800C3638'],0)
        if original!=get(symbols['D_800D1588']+animation*4,4):
            current=get(actor+0x84,2);limit=get(symbols['D_800C5A90']+animation*2,2)
            store(actor+0x84,65535,2)
            store(frame+0x18,0,4);store(frame+0x14,0,4);store(frame+0x10,0,4)
            call('func_1505E650',(actor,0 if current>=limit else current,0x3F800000,0,0,0,0))
            mode=get(symbols['D_800C35EA'])
        if mode==1:store(symbols['D_800C3638'],1)
        call('func_1507EABC',(actor,))
    get(frame+0x2C,4);get(frame+0x28,4)
    return state,events,calls


class SelectorOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,actor,symbols=S,phase=0,mutations=None,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,arguments=(actor,),phase=phase,entry=entry,connected=connected)
        self.symbols,self.mutations=symbols,mutations or {}
    def record_call(self,target):
        name=next(name for name in CALL_COUNTS if self.symbols[name]==target)
        args=self.arguments(CALL_COUNTS[name]);self.calls.append((target,*args))
        self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in (self.symbols[name] for name in CALL_COUNTS)
        for address,value,size in self.mutations.get(target,()):self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]


class GameActorAnimationSelectorMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-animation-selector-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            assert screen.recovery.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        with (cls.out/'before-guards').open(newline='') as stream:
            reader=csv.DictReader(stream);cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rows=screen.guard_rows(cls.out/'selected.o')
        cls.write_rows(cls.out/'isolated.csv',cls.rows)
        cls.write_rows(cls.out/'qualified.csv',cls.old_rows+cls.rows)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>98I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/58F80.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot=cls.out/'slot.s';cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_58F80'))
        cls.fitted=cls.link('fitted',S)
        assert cls.fitted==cls.original

    @classmethod
    def link(cls,name,symbols,entry=screen.ENTRY):
        script=cls.out/('link-%s-%X.ld'%(name,entry));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>98I',sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,distance=0,symbols=S,phase=0,mutations=None,forms=None,entry=screen.ENTRY,
            include_raw=True):
        actor=actor_address(distance,symbols);forms=forms or (self.original,self.fitted,self.raw)
        models=[]
        for index,body in enumerate(forms if include_raw else forms[:2]):
            state,events,calls=reference(memory,actor,symbols,phase,mutations,raw=index==2)
            model=SelectorOracle(body,memory,actor,symbols,phase,mutations,entry).run()
            self.assertEqual(model.memory,state,('memory',index))
            self.assertEqual(model.events,events,('events',index))
            self.assertEqual(model.calls,calls,('calls',index));models.append(model)
        for name in ('memory','events','calls','accesses'):
            self.assertEqual(getattr(models[0],name),getattr(models[1],name),name)
        return models

    def test_01_complete_shape_closed_provenance_and_stale_rejection(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(98,64,0,14,''))
        self.assertEqual(len(self.rows),14)
        self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in self.rows))
        for index in range(98):
            stale=list(screen.RAW);stale[index]^=0x10000
            with self.assertRaisesRegex(ValueError,'stale complete'):screen.recipe(stale)
        self.receipt('shape',words=98,bytes=392,frame=64,guards=14,insertions=0,omissions=0,
            missing_body_padding=0,all_producers_emitted=True,closed_register_lives=2,
            spill_words=4,independent_schedule_words=3,whole_body_stale_rejections=98)

    def test_02_selector_unsigned_boundaries_callback_mutations_and_private_traces(self):
        cases=0;coverage=set()
        inputs=[]
        for pending,phase in itertools.product(range(256),(0,8)):
            inputs.append((dict(pending=pending,count=(0,1,254,255)[pending%4],
                current=(0,1,253,254)[pending%4],identity=pending,animation=255-pending,
                mode=(0,1,2,255)[pending%4],frame=(0,1,32768,65535)[pending%4],length=32768),0,phase))
        for identity in range(256):
            inputs.append((dict(pending=255,identity=identity,animation=255-identity,
                frame=65534,length=65535),identity%5,0))
        for frame,length,equal,mode in itertools.product((0,1,32767,32768,65534,65535),
                (0,1,32768,65535),(False,True),(0,1,255)):
            inputs.append((dict(frame=frame,length=length,equal=equal,mode=mode),0,0))
        for distance,plan,phase in itertools.product(DISTANCES,range(5),(0,8)):
            inputs.append((dict(distance=distance,animation=255,length=65535),plan,phase))
        for case,plan,phase in inputs:
            memory=fixture(**case);distance=case.get('distance',0);actor=actor_address(distance)
            animation=case.get('animation',8)
            mutation=actions(memory,actor,animation,plan)
            models=self.compare(memory,distance,phase=phase,mutations=mutation)
            coverage.update(models[0].visits);cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+392,4)))
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=98,
            independent_ordered_full_private_public_references=True,actual_seven_argument_O32_ABI=True,
            all_pending_ID_selector_bytes=True,unsigned_phase_length=True,signed_lowword_distance=True,
            callbacks_clobber_all_caller_GP_FPR=True,retained_callback_captures_and_mode_reads=True,
            void_return_not_false_zero_acceptance=True,raw_spill_layout_distinct_and_explicit=True)

    def test_03_live_aliases_private_mutations_and_all_fired_fault_prefixes(self):
        cases=prefixes=0
        for alias,phase,plan in itertools.product((SELECTORS,S['D_800CC2D0']+0x1C8,
                S['D_800C3638'],STACK-0x40+0x34),(0,8),(0,4)):
            memory=fixture(pending=255,selectors=alias);actor=actor_address()
            memory.setdefault(alias,8)
            animation=read(memory,alias,1)
            mutation=actions(memory,actor,animation,plan)
            positive=self.compare(memory,phase=phase,mutations=mutation);cases+=1
            for ordinal in range(positive[0].accesses):
                models=[]
                for words in (self.original,self.fitted):
                    model=SelectorOracle(words,memory,actor,phase=phase,mutations=mutation)
                    model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal)
                    models.append(model)
                for name in ('memory','events','calls'):
                    self.assertEqual(getattr(models[0],name),getattr(models[1],name))
                prefixes+=1
        for phase in (0,8):
            memory=fixture(animation=8)
            mutation=actions(memory,actor_address(),8,5,frame=STACK+phase-0x40)
            self.compare(memory,phase=phase,mutations=mutation,include_raw=False);cases+=1
        live_aliases=0
        for key,address in (('D_800C35EA',actor_address()+0x1C8),
                ('D_800C3638',S['D_800D1588']+8*4+3)):
            symbols=dict(S);symbols[key]=address
            forms=tuple(self.link(name,symbols) for name in ('original','fitted','selected'))
            for pending,plan in itertools.product((2,255),range(5)):
                memory=fixture(pending=pending,mode=0 if key=='D_800C35EA' else 1,
                    equal=True,symbols=symbols)
                if key=='D_800C3638':
                    put(memory,S['D_800D1588']+8*4,read(memory,S['D_800D1588']+7*4,4))
                mutation=actions(memory,actor_address(),8,plan,symbols)
                self.compare(memory,symbols=symbols,mutations=mutation,forms=forms);live_aliases+=1
        self.receipt('aliases-faults',cases=cases,executions=cases*3-2,
            full_fired_fault_prefix_pairs=prefixes,failed_executions=prefixes*2,
            private_selector_and_retained_spill_mutation_cases=True,original_fitted_private_order_exact=True,
            raw_distinct_spill_layout_reference=True,missing_fault_is_failure=True,
            live_mode_current_and_flag_resource_alias_cases=live_aliases,additional_independent_links=6)

    def test_04_independent_symbol_rebases_and_signed_carries(self):
        cases=0
        settings=((screen.ENTRY,S),(0x15207FF0,dict(zip(S,(0x80107FFC,0x80118004,0x80127FFC,
            0x80208004,0x80217FFC,0x15218004,0x15227FFC,0x15238004)))),
            (0x15308004,dict(zip(S,(0x80118004,0x80127FFC,0x80138004,
            0x80217FFC,0x80228004,0x15327FFC,0x15338004,0x15347FFC)))))
        for entry,symbols in settings:
            forms=tuple(self.link(name,symbols,entry) for name in ('original','fitted','selected'))
            self.assertEqual(forms[0],forms[1])
            for distance,pending,plan in itertools.product((0,-813,812*25),(0,2,255),range(5)):
                memory=fixture(distance=distance,pending=pending,animation=255,symbols=symbols)
                mutation=actions(memory,actor_address(distance,symbols),255,plan,symbols)
                self.compare(memory,distance,symbols,mutations=mutation,forms=forms,entry=entry);cases+=1
        self.receipt('rebases',independent_links=9,symbol_sets=3,cases=cases,executions=cases*3,
            independently_linked_original_raw_fitted=True,signed_HI_LO_carries_and_JAL_entries=True)

    def test_05_copied_owner_actual_padding_and_37_neighbors(self):
        before=(self.out/'before-source').read_text();objects=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,warnings=compile_owner(self.root,self.out,source,name);self.assertEqual(warnings,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj)
        parsed=[parse_object(obj) for obj in objects]
        def body(data,name):
            text,functions,relocs=data;target=functions[name];start,size=target['value'],target['size']
            return size,text[start:start+size],{a-start:v for a,v in relocs.items() if start<=a<start+size}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION:self.assertEqual(body(parsed[0],name),body(parsed[1],name),name)
        # Isolated IDO rounds the text section to sixteen bytes; owner extent is exactly 392.
        _,functions,relocs=parse_object(objects[1]);target=functions[screen.FUNCTION]
        self.assertEqual(target['size'],392)
        self.assertEqual(screen.guard_rows(objects[1]),self.rows)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_58F80',str(assembly),
                '--word-patches',str(self.out/('before-guards' if index==0 else 'qualified.csv'))],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True)
        padded=[parse_object(self.out/('padded-owner-%d.o'%i)) for i in (0,1)]
        base=padded[1][1][screen.FUNCTION]['value'];expected=bytearray(padded[0][0])
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'],392)
        expected[base:base+392]=padded[1][0][base:base+392]
        self.assertEqual(bytes(expected),padded[1][0])
        self.assertEqual({a:v for a,v in padded[0][2].items() if not base<=a<base+392},
            {a:v for a,v in padded[1][2].items() if not base<=a<base+392})
        self.assertEqual({a-base:v for a,v in padded[1][2].items() if base<=a<base+392},screen.RELOCATIONS)
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,actual_padded_bytes=392,
            only_target_changes=True,typed_direct_caller_cast_instruction_neutral=True,
            all_other_bodies_extents_relative_relocations_pools_exact=True)

    def test_06_fresh_complete_semantic_negative_controls(self):
        controls=(('reset','index == 255','index == 254',dict(pending=255),0),
            ('bounds','index >= actor[0x2C9]','index > actor[0x2C9]',dict(pending=2,count=1),0),
            ('captured-index','actor[0x1C8] = index','actor[0x1C8] = actor[0x1C9] - 1',{},1),
            ('phase','frame >= D_800C5A90[animation]','frame > D_800C5A90[animation]',dict(frame=3,length=3),0),
            ('reload-mode','mode = D_800C35EA;\n            }','mode = 1;\n            }',{},1),
            ('float-ABI','1.0f, 0.0f','2.0f, 0.0f',{},0),
            ('unsigned-phase','*(u16 *)(actor + 0x84)','*(short *)(actor + 0x84)',dict(frame=65535,length=32768),0))
        for name,old,new,case,plan in controls:
            self.assertIn(old,screen.SELECTED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            memory=fixture(**case);mutation=actions(memory,actor_address(),8,plan)
            state,events,calls=reference(memory,actor_address(),mutations=mutation)
            wrong=SelectorOracle(words,memory,actor_address(),mutations=mutation).run()
            pub=lambda m:{a:v for a,v in m.items() if public(a)}
            trace=lambda es:[e for e in es if e[0]=='CALL' or public(e[1])]
            self.assertNotEqual((pub(wrong.memory),trace(wrong.events),wrong.calls),
                (pub(state),trace(events),calls),name)
        self.receipt('negatives',fresh_complete_IDO_controls=len(controls),effective=True)

    def test_07_actual_banked_dispatcher_connection(self):
        before=(self.out/'before-elf').read_bytes()
        caller=list(struct.unpack_from('>88I',before,elf_slot_offset(before,dispatch.ENTRY,352)))
        self.assertEqual(caller,list(struct.unpack_from('>88I',self.rom,0x59234)))
        class Connected(SelectorOracle):
            def record_call(model,target):
                if target in dispatch.COUNTS:
                    args=model.arguments(dispatch.COUNTS[target])
                    model.calls.append((target,*args));model.events.append(('CALL',target,args))
                else:super().record_call(target)
            def hook(model,target):
                assert target!=screen.ENTRY,'selector must execute actual instructions'
                if target in (S[name] for name in CALL_COUNTS):return super().hook(target)
                for register in (1,2,3,*range(4,16),24,25):model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]
        cases=0
        for slot,pending,kind,state,phase in itertools.product((0,25),(0,2,255),(7,255),(0,2,3,5),(0,8)):
            memory=fixture(distance=slot*812,pending=pending,identity=kind);actor=actor_address(slot*812)
            memory.update({dispatch.FLAGS+i:0 for i in range(26*16)})
            for offset,value,size in ((0,0,4),(5,state,1),(0xA4,0,1),(0xF8,0,4),(0x260,0,4)):
                put(memory,actor+offset,value,size)
            models=[]
            for body in (self.original,self.fitted):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(body)}
                model=Connected(caller,memory,actor,phase=phase,entry=dispatch.ENTRY,connected=connected)
                model.r[5]=model.before[5]=slot
                model.run();models.append(model)
                self.assertEqual(screen.ENTRY in model.visits,bool(pending and kind!=255 and state==0))
            for name in ('memory','events','calls','accesses'):
                self.assertEqual(getattr(models[0],name),getattr(models[1],name))
            cases+=1
        self.receipt('caller',cases=cases,executions=cases*2,actual_banked_dispatcher_words=88,
            actual_complete_selector_words=98,full_private_traces_and_ABI_exact=True,other_callbacks_bounded=True)

    def test_08_native32_complete_C_and_real_float_ABI(self):
        source=NATIVE+screen.SELECTED+'\n'+NATIVE_REFERENCE+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-phase','frame >= D_800C5A90[animation]','frame > D_800C5A90[animation]'),
                ('native-reset','index == 255','index == 254'),('native-ABI','1.0f, 0.0f','2.0f, 0.0f')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=26*256*5+2*6*4*5*3*2+2*3*5,
            all_valid_slots_pending_ID_selector_bytes=True,actual_complete_C_seven_arg_float_ABI=True,
            separate_little_endian_reference_and_mutating_callbacks=True,fresh_effective_native_negatives=3,
            live_selector_actor_phase_and_flag_alias_cases=30,
            invalid_wrapped_guest_distances_not_native_acceptance=True)

    def test_09_immutable_snapshots_and_whole_linked_installation(self):
        with self.assertRaisesRegex(ValueError,'immutable'):self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        before_source=(self.out/'before-source').read_text();source=(self.root/screen.SOURCE).read_text()
        if screen.recovery.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('installation',installed=False,five_current_baselines_unchanged=True);return
        self.assertEqual(source,screen.install(before_source))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes();expected=bytearray(before)
        struct.pack_into('>98I',expected,elf_slot_offset(before,screen.ENTRY,392),*self.original)
        struct.pack_into('>I',expected,installed.symbol_size_offset(before,screen.FUNCTION,screen.ENTRY),392)
        actual=(self.root/self.paths['elf']).read_bytes();em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5];expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_one_392_byte_slot_and_symbol_extent_change=True,
            added_guards=14,guard_prefix_exact=True,conversion_progress_rodata_exact=True,
            all_other_linked_bytes_addresses_extents_exact=True,protected_data=audit)


NATIVE=r'''
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
u8 D_800CC2D0[26*812] __attribute__((aligned(16))),D_800C35EA,D_800C3638;
u32 D_800D1588[256];u16 D_800C5A90[256];
static u8 selectors[256],wantedSelectors[256],expected[812];static u32 resources[256];
static u8 wantMode,wantFlag;static u32 plan,error,selectedIndex,callCount,wantedCount,alias;
static u32 calls[3][8],wanted[3][8];static u8 *currentActor;static u32 expectedSlot;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(f32)==4)?1:-1];
static void mutation(u8 *actor,u32 *table,u8 *mode,int animation,int callback) {
    if(callback==0 && (plan==1 || plan==2)) {
        table[actor[4]]=0x12345678;actor[4]=254;actor[0x1C9]=99;actor[0x2C9]=0;
        actor[0x1C8]=201;*(u8 **)(actor+0x2C4)=selectors+128;
        if(actor==currentActor)selectors[selectedIndex]=255;else wantedSelectors[selectedIndex]=255;
        *(u16 *)(actor+0x84)=plan==1?65534:1;*mode=plan==1?1:255;
    } else if(callback==0 && plan==3) {
        table[animation]=table[actor[4]];*mode=1;
    } else if(callback==0 && plan==4) {*mode=0;}
    if(callback==1) {
        if(plan==1 || plan==2) {*mode=plan==1?0:1;*(u16 *)(actor+0x84)=321;}
        if(plan==4)*mode=1;
    }
}
static void logCall(u32 *out,int kind,u8 *actor,u32 a,u32 b,u32 c) {
    int i;for(i=0;i<8;i++)out[i]=0;out[0]=kind;
    out[1]=kind==0?expectedSlot:0xABCDEF01;
    out[2]=a;out[3]=b;out[4]=c;
}
void func_150837D4(s32 slot,s32 animation,s32 zero) {
    if((u32)slot!=expectedSlot || zero!=0 || callCount>=3)error=1;
    logCall(calls[callCount++],0,currentActor,animation,zero,0);
    mutation(currentActor,D_800D1588,&D_800C35EA,animation,0);
}
void func_1505E650(u8 *actor,u16 phase,f32 rate,f32 x,f32 y,f32 z,s32 zero) {
    if(actor!=currentActor || callCount>=3 || rate!=1.0f || x!=0.0f || y!=0.0f || z!=0.0f || zero)error=2;
    logCall(calls[callCount++],1,actor,phase,0x3F800000,0);
    mutation(actor,D_800D1588,&D_800C35EA,0,1);
}
void func_1507EABC(u8 *actor) {
    if(actor!=currentActor || callCount>=3)error=3;
    logCall(calls[callCount++],2,actor,0,0,0);
}
'''
NATIVE_REFERENCE=r'''
static void expectedTransition(u8 *actor) {
    u32 resource,animation,phase,index,mode,pending=actor[0x1C9];
    if(!pending)return;
    resource=resources[actor[4]];
    if(pending==255) {actor[0x1C9]=0;index=0;}
    else {index=pending-1;if(index>=actor[0x2C9] || index==actor[0x1C8])return;}
    animation=alias==1?actor[0x1C8+index]:alias==2?wantFlag:alias==3?actor[0x84+index]:wantedSelectors[index];
    logCall(wanted[wantedCount++],0,actor,animation,0,0);
    mutation(actor,resources,&wantMode,animation,0);
    actor[0x1C8]=(u8)index;mode=wantMode;if(mode==1)wantFlag=0;
    if(resource!=resources[animation]) {
        phase=*(u16 *)(actor+0x84);if(phase>=D_800C5A90[animation])phase=0;
        *(u16 *)(actor+0x84)=65535;
        logCall(wanted[wantedCount++],1,actor,phase,0x3F800000,0);
        mutation(actor,resources,&wantMode,0,1);mode=wantMode;
    }
    if(mode==1)wantFlag=1;
    logCall(wanted[wantedCount++],2,actor,0,0,0);
}
'''
NATIVE_RUNNER=r'''
static int qualify(int slot,int pending,int frame,int length,int mode,int equal,int id,int animation,int mutationPlan) {
    int i,j;u8 *actor=D_800CC2D0+slot*812;
    currentActor=actor;expectedSlot=slot;plan=mutationPlan;callCount=wantedCount=error=0;
    selectedIndex=pending==255?0:(u32)(pending-1);
    for(i=0;i<812;i++)actor[i]=0xA5;
    for(i=0;i<256;i++) {D_800D1588[i]=resources[i]=0xAB000000+(u32)i*17;
        D_800C5A90[i]=(u16)length;selectors[i]=wantedSelectors[i]=(u8)animation;}
    actor[4]=(u8)id;actor[0x1C9]=(u8)pending;actor[0x2C9]=255;actor[0x1C8]=0;
    *(u8 **)(actor+0x2C4)=selectors;*(u16 *)(actor+0x84)=(u16)frame;
    D_800C35EA=wantMode=(u8)mode;D_800C3638=wantFlag=0xA5;
    if(alias) *(u8 **)(actor+0x2C4)=alias==1?actor+0x1C8:alias==2?&D_800C3638:actor+0x84;
    if(equal)D_800D1588[animation]=resources[animation]=resources[id];
    for(i=0;i<812;i++)expected[i]=actor[i];
    expectedTransition(expected);func_1502FBE8(actor);
    if(error || callCount!=wantedCount || D_800C35EA!=wantMode || D_800C3638!=wantFlag)return 1;
    for(i=0;i<812;i++)if(actor[i]!=expected[i])return 2;
    for(i=0;i<256;i++)if(D_800D1588[i]!=resources[i] || selectors[i]!=wantedSelectors[i])return 3;
    for(i=0;i<(int)callCount;i++)for(j=0;j<8;j++)if(calls[i][j]!=wanted[i][j])return 4;
    return 0;
}
int run(void) {
    static const int phases[]={0,1,32767,32768,65534,65535},lengths[]={0,1,32768,65535};
    int slot,pending,frame,length,mode,equal,p,result;
    alias=0;
    for(slot=0;slot<26;slot++)for(pending=0;pending<256;pending++)for(p=0;p<5;p++) {
        result=qualify(slot,pending,phases[pending%6],lengths[pending%4],pending%3,
            pending%2,pending,255-pending,p);if(result)return result;
    }
    for(slot=0;slot<=25;slot+=25)for(frame=0;frame<6;frame++)for(length=0;length<4;length++)
        for(p=0;p<5;p++)for(mode=0;mode<3;mode++)for(equal=0;equal<2;equal++) {
            result=qualify(slot,2,phases[frame],lengths[length],mode,equal,7,255,p);if(result)return result;
        }
    for(slot=0;slot<=25;slot+=25)for(alias=1;alias<=3;alias++)for(p=0;p<5;p++) {
        result=qualify(slot,255,65535,32768,1,0,7,255,p);if(result)return result;
    }
    return 0;
}
'''


if __name__=='__main__':unittest.main()
