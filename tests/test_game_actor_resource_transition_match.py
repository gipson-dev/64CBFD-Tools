"""Complete resource transition, ordered guest/ABI references and linked-only audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_actor_resource_transition_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_actor_animation_selector_match as selector
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_row_destination_fill import START
from tools.check_game_data_layout import audit_layout

S=screen.recovery.SYMBOLS
STACK,DEFINITION,ALTERNATE=guest.STACK,0x26000,0x27000
COUNTS={'func_15062BDC':3,'func_15084D00':1,'func_1502B020':4}
FLOATS=(0,0x80000000,0x3F800000,0xC0200000,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,1)


def actor_address(slot=0,symbols=S):return (symbols['D_800CC2D0']+slot*812)&0xFFFFFFFF


def fixture(slot=0,identity=7,height=-32768,result=8,count=1,symbols=S,xz=0x3F800000,y=0xC0200000):
    actor=actor_address(slot,symbols);entry=(symbols['D_800D1C90']+identity*4)&0xFFFFFFFF
    memory={}
    for start,length in ((STACK-0x500,0x600),(actor,812),(symbols['D_800D1C90'],1024),
            (entry,4),(symbols['D_800C5A90'],512),(DEFINITION,64),(ALTERNATE,64)):
        memory.update({(start+i)&0xFFFFFFFF:0xA5 for i in range(length)})
    put(memory,entry,DEFINITION)
    put(memory,DEFINITION+6,height,2);put(memory,DEFINITION+0x12,91,1)
    put(memory,ALTERNATE+6,32767,2);put(memory,ALTERNATE+0x12,173,1)
    put(memory,actor+0x14C,xz);put(memory,actor+0x150,y)
    put(memory,symbols['D_800C5A90']+(result&255)*2,count,2)
    return memory


def reference(memory,slot=0,identity=7,unused=0,symbols=S,phase=0,
        result=8,address=0x28000,mutations=None):
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x30
    actor=actor_address(slot,symbols);identity&=0xFFFFFFFF
    def get(where,size=1):
        assert all(where+i in state for i in range(size)),('reference unmapped read',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size=1):
        assert all(where+i in state for i in range(size)),('reference unmapped write',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    def call(name,args):
        target=symbols[name];calls.append((target,*args));events.append(('CALL',target,args))
        for where,value,size in (mutations or {}).get(target,()):store(where,value,size)
    store(frame+0x1C,0xDEAD0000,4);store(frame+0x18,0x5A000010,4);store(frame+0x38,unused,4)
    store(actor+4,identity)
    if identity==255:
        for offset,value in ((0xE4,0),(0xE6,0),(0xE8,0),(0xD2,70),(0xD4,70),(0xD6,0),(0x160,0)):
            store(actor+offset,value,2)
        store(actor+0xC8,0,4)
    else:
        entry=(symbols['D_800D1C90']+(identity<<2))&0xFFFFFFFF
        resource=get(entry,4);xz=get(actor+0x14C,4);height=get(resource+6,2)
        store(frame+0x20,entry,4);y=get(actor+0x150,4)
        store(actor+0xC8,bits(float(height if height<32768 else height-65536)),4)
        call('func_15062BDC',(actor,xz,y))
        entry=get(frame+0x20,4);resource=get(entry,4)
        store(actor+5,get(resource+0x12))
    call('func_15084D00',(actor,))
    canonical=result&255;store(actor+6,result)
    if get(symbols['D_800C5A90']+canonical*2,2):
        call('func_1502B020',(0,2,2,canonical));store(actor+0x58,address,4)
    get(frame+0x1C,4);get(frame+0x18,4)
    return state,events,calls


class TransitionOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,slot=0,identity=7,unused=0,symbols=S,phase=0,result=8,
            address=0x28000,mutations=None,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,arguments=(slot,identity,unused),phase=phase,entry=entry,connected=connected)
        self.symbols,self.result,self.address=symbols,result,address
        self.mutations=mutations or {}
    def record_call(self,target):
        name=next(name for name in COUNTS if self.symbols[name]==target)
        args=self.arguments(COUNTS[name]);self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target in (self.symbols[name] for name in COUNTS)
        for where,value,size in self.mutations.get(target,()):self.put(where,value,size)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        if target==self.symbols['func_15084D00']:self.r[2]=self.result&0xFFFFFFFF
        if target==self.symbols['func_1502B020']:self.r[2]=self.address&0xFFFFFFFF


class GameActorResourceTransitionMatchTests(unittest.TestCase):
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-resource-transition-test';cls.out.mkdir(exist_ok=True)
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
        cls.write_rows(cls.out/'isolated.csv',cls.rows);cls.write_rows(cls.out/'qualified.csv',cls.old_rows+cls.rows)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>70I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot=cls.out/'slot.s';cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+\
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+\
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_AEB40'))
        cls.fitted=cls.link('fitted',S)
        assert cls.fitted==cls.original

    @classmethod
    def link(cls,name,symbols,entry=screen.ENTRY):
        script=cls.out/('link-%s-%X.ld'%(name,entry));elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>70I',sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,forms=None,**settings):
        state,events,calls=reference(memory,**{k:v for k,v in settings.items() if k!='entry'})
        models=[TransitionOracle(words,memory,**settings).run() for words in (forms or (self.original,self.fitted,self.raw))]
        for index,model in enumerate(models):
            self.assertEqual(model.memory,state,('memory',index))
            self.assertEqual(model.events,events,('events',index));self.assertEqual(model.calls,calls,('calls',index))
        return models

    def test_01_complete_shape_provenance_and_all_word_stale_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(70,48,0,15,''))
        self.assertEqual(len(self.rows),15)
        self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in self.rows))
        for index in range(70):
            stale=list(screen.RAW);stale[index]^=0x10000
            with self.assertRaisesRegex(ValueError,'stale complete'):screen.recipe(stale)
        for offset in screen.RELOCATIONS:
            text,functions,relocs=parse_object(self.out/'selected.o');relocs[offset]=[('R_MIPS_26','stale')]
            with unittest.mock.patch.object(screen,'parse_object',return_value=(text,functions,relocs)):
                with self.assertRaisesRegex(ValueError,'stale.*relocations'):screen.guard_rows(self.out/'selected.o')
        self.receipt('shape',words=70,frame=48,guards=15,complete_semantic_C=True,
            closed_register_renames=True,alternative_RA_loads_merged_at_common_epilogue=True,
            emitted_a2_constant_moved_and_move_copied=True,not_a_pure_word_permutation=True,
            stale_word_controls=70,stale_relocation_controls=len(screen.RELOCATIONS))

    def test_02_independent_guest_references_and_full_width_arguments(self):
        cases=0;coverage=set()
        for identity,slot,result,count in itertools.product(range(256),(0,25),(0,255,0x123480FF),(0,1,65535)):
            memory=fixture(slot,identity,result=result,count=count,height=(identity*257)&65535,
                xz=FLOATS[identity%len(FLOATS)],y=FLOATS[(identity+3)%len(FLOATS)])
            models=self.compare(memory,slot=slot,identity=identity,result=result,unused=0xFEDCBA98)
            coverage.update(models[0].visits);cases+=1
        for identity,slot,height,phase,address in itertools.product((0x100,0x1FF,0xFFFF,0x7FFFFFFF,0xFFFFFFFF),
                (-1,0x7FFFFFFF,-0x80000000),(-32768,-1,0,32767),(0,8),(0,0xFFFFFFFF)):
            memory=fixture(slot,identity,height=height)
            self.compare(memory,slot=slot,identity=identity,phase=phase,address=address,unused=0xA5A5A5A5);cases+=1
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+280,4)))
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=70,
            full_private_public_order_and_mixed_float_O32_arguments=True,all_identity_bytes=True,
            full_word_sentinel_not_truncated=True,all_caller_GP_FPR_clobbered=True,
            signed_height_and_unsigned_count=True,lowword_actor_and_table_indices=True,
            full_word_callback_return_narrowing=True,void_return_not_compared=True)

    def test_03_live_table_private_aliases_and_fired_fault_prefixes(self):
        cases=prefixes=0
        for identity,phase,plan in itertools.product((7,255),(0,8),range(5)):
            memory=fixture(identity=identity,count=0 if plan==0 else 1)
            actor=actor_address();frame=STACK+phase-0x30
            mutations={S['func_15062BDC']:((S['D_800D1C90']+identity*4,ALTERNATE,4),
                (actor+0x14C,0xDEADBEEF,4),(actor+4,19,1)),
                S['func_15084D00']:((S['D_800C5A90']+16,plan%2,2),(actor+6,77,1)),
                S['func_1502B020']:((actor+0x58,0x13572468,4),)}
            if plan==2:
                put(memory,S['D_800D1C90']+19*4,ALTERNATE)
                mutations[S['func_15062BDC']]+=((frame+0x20,S['D_800D1C90']+19*4,4),)
            if plan==3:
                put(memory,S['D_800D1C90']+identity*4,actor+0xE0)
                put(memory,actor+0xE6,-13,2);put(memory,actor+0xF2,211,1)
            if plan==4:
                put(memory,S['D_800D1C90']+identity*4,frame+0x10)
                put(memory,frame+0x16,-17,2);put(memory,frame+0x22,219,1)
            models=self.compare(memory,identity=identity,phase=phase,mutations=mutations,
                result=0x87654308,address=0)
            for ordinal in range(models[0].accesses):
                failed=[]
                for words in (self.original,self.fitted,self.raw):
                    model=TransitionOracle(words,memory,identity=identity,phase=phase,mutations=mutations,
                        result=0x87654308,address=0);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal)
                    failed.append(model)
                for other in failed[1:]:
                    for name in ('memory','events','calls'):self.assertEqual(getattr(failed[0],name),getattr(other,name))
                prefixes+=1
            cases+=1
        for key,address in (('D_800C5A90',actor_address()+0xD2-16),
                ('D_800D1C90',STACK-0x30+0x38-7*4)):
            symbols=dict(S);symbols[key]=address
            forms=tuple(self.link(name,symbols) for name in ('original','fitted','selected'))
            memory=fixture(symbols=symbols)
            unused=DEFINITION if key=='D_800D1C90' else 0xA5A5A5A5
            self.compare(memory,symbols=symbols,forms=forms,unused=unused);cases+=1
        self.receipt('aliases-faults',cases=cases,fired_prefix_triplets=prefixes,
            failed_executions=prefixes*3,original_raw_fitted_full_private_order_exact=True,
            live_table_reloads_and_private_entry_home_mutation=True,actor_resource_and_argument_home_aliases=True,
            absent_fault_is_failure=True,not_portable_C_fault_acceptance=True)

    def test_04_independent_symbol_rebases_and_signed_carries(self):
        cases=0
        for entry,symbols in ((screen.ENTRY,S),(0x15207FF0,dict(zip(S,(0x80107FFC,0x80118004,0x80127FFC,
                0x15218004,0x15227FFC,0x15238004)))),(0x15308004,dict(zip(S,(0x80118004,0x80127FFC,
                0x80138004,0x15327FFC,0x15338004,0x15347FFC))))):
            forms=tuple(self.link(name,symbols,entry) for name in ('original','fitted','selected'))
            self.assertEqual(forms[0],forms[1])
            for identity,count,phase in itertools.product((0,7,255,0x1FF),(0,65535),(0,8)):
                memory=fixture(identity=identity,count=count,symbols=symbols)
                self.compare(memory,forms=forms,identity=identity,symbols=symbols,phase=phase,entry=entry);cases+=1
        self.receipt('rebases',independent_links=9,cases=cases,executions=cases*3,
            signed_HI_LO_carries_and_distinct_JAL_entries=True)

    def test_05_copied_owner_neighbors_profiles_and_actual_padding(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj)
        self.assertEqual(warnings[0],warnings[1])
        parsed=[parse_object(obj) for obj in objects]
        def body(data,name):
            text,functions,relocs=data;target=functions[name];start,size=target['value'],target['size']
            return size,text[start:start+size],{a-start:v for a,v in relocs.items() if start<=a<start+size}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION:self.assertEqual(body(parsed[0],name),body(parsed[1],name),name)
        self.assertEqual(screen.guard_rows(objects[1]),self.rows)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_AEB40',str(assembly),
                '--word-patches',str(self.out/('before-guards' if index==0 else 'qualified.csv'))],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True)
        padded=[parse_object(self.out/('padded-owner-%d.o'%i)) for i in (0,1)]
        base=padded[1][1][screen.FUNCTION]['value'];expected=bytearray(padded[0][0])
        expected[base:base+280]=padded[1][0][base:base+280];self.assertEqual(bytes(expected),padded[1][0])
        self.assertEqual({a:v for a,v in padded[0][2].items() if not base<=a<base+280},
            {a:v for a,v in padded[1][2].items() if not base<=a<base+280})
        self.assertEqual({a-base:v for a,v in padded[1][2].items() if base<=a<base+280},screen.RELOCATIONS)
        self.receipt('owner',neighbors=len(parsed[0][1])-1,preexisting_warning_count=len(warnings[0]),
            no_new_diagnostics=True,only_280_byte_target_changes=True,all_other_bodies_extents_pools_relocations_exact=True)

    def test_06_fresh_complete_semantic_negative_controls(self):
        controls=(('sentinel','identity == 255','(u8)identity == 255',dict(identity=0x1FF)),
            ('height','(s16 *)(*resource + 6)','(u16 *)(*resource + 6)',dict(height=-1)),
            ('dimensions','actor + 0x14C','actor + 0x150',{}),
            ('resource-byte','(*resource)[0x12]','(*resource)[0x13]',{}),
            ('canonical','identity &= 255','identity &= 127',dict(result=255)),
            ('count','!= 0','> 1',dict(count=1)),
            ('depth','NULL, 2, 2, identity','NULL, 1, 2, identity',{}),
            ('output-field','*(u32 *)(actor + 0x58) = func_1502B020','*(u32 *)(actor + 0x5C) = func_1502B020',{}))
        for name,old,new,case in controls:
            self.assertIn(old,screen.SELECTED)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            memory=fixture(**case);settings={k:v for k,v in case.items() if k in ('identity','result')}
            expected=TransitionOracle(self.raw,memory,**settings).run()
            wrong=TransitionOracle(words,memory,**settings).run()
            public=lambda m:{a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x100}
            trace=lambda es:[e for e in es if e[0]=='CALL' or not STACK-0x500<=e[1]<STACK+0x100]
            self.assertNotEqual((public(wrong.memory),trace(wrong.events),wrong.calls),
                (public(expected.memory),trace(expected.events),expected.calls),name)
        cached=screen.SELECTED.replace('    u8 **resource;', '    u8 **resource;\n    u8 *cached;').replace(
            '        resource = &D_800D1C90[identity];',
            '        resource = &D_800D1C90[identity];\n        cached = *resource;').replace(
            '(s16 *)(*resource + 6)', '(s16 *)(cached + 6)').replace('(*resource)[0x12]', 'cached[0x12]')
        _,words=screen.compile_candidate(self.root,self.out,'negative-cached-definition',cached)
        memory=fixture();mutations={S['func_15062BDC']:((S['D_800D1C90']+28,ALTERNATE,4),)}
        expected=TransitionOracle(self.raw,memory,mutations=mutations).run()
        wrong=TransitionOracle(words,memory,mutations=mutations).run()
        self.assertNotEqual(read(wrong.memory,actor_address()+5,1),read(expected.memory,actor_address()+5,1))
        self.receipt('negatives',fresh_IDO_controls=len(controls)+1,all_effective=True)

    def test_07_actual_banked_selector_connection(self):
        before=(self.out/'before-elf').read_bytes()
        caller=list(struct.unpack_from('>98I',before,elf_slot_offset(before,selector.screen.ENTRY,392)))
        self.assertEqual(caller,list(struct.unpack_from('>98I',self.rom,selector.screen.ROM)))
        class Connected(TransitionOracle):
            def record_call(model,target):
                if target in (selector.S[name] for name in selector.CALL_COUNTS):
                    name=next(n for n in selector.CALL_COUNTS if selector.S[n]==target)
                    args=model.arguments(selector.CALL_COUNTS[name]);model.calls.append((target,*args))
                    model.events.append(('CALL',target,args))
                else:super().record_call(target)
            def hook(model,target):
                assert target!=screen.ENTRY,'transition must execute actual instructions'
                if target in (S[name] for name in COUNTS):return super().hook(target)
                for register in (1,2,3,*range(4,16),24,25):model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]
        cases=0
        for slot,pending,animation,count,phase in itertools.product((0,25),(0,2,255),(7,255),(0,65535),(0,8)):
            memory=fixture(slot,animation,result=8,count=count)
            memory.update(selector.fixture(distance=slot*812,pending=pending,identity=19,animation=animation))
            put(memory,S['D_800D1C90']+animation*4,DEFINITION)
            put(memory,S['D_800C5A90']+16,count,2)
            models=[]
            for body in (self.original,self.fitted,self.raw):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(body)}
                model=Connected(caller,memory,slot=slot,phase=phase,entry=selector.screen.ENTRY,connected=connected)
                model.r[4]=model.before[4]=actor_address(slot);model.run();models.append(model)
                self.assertEqual(screen.ENTRY in model.visits,bool(pending))
            for other in models[1:]:
                for name in ('memory','events','calls','accesses'):self.assertEqual(getattr(models[0],name),getattr(other,name))
            cases+=1
        self.receipt('caller',cases=cases,executions=cases*3,actual_banked_selector_words=98,
            actual_transition_words=70,full_private_traces_and_ABI_exact=True,other_callbacks_bounded=True)

    def test_08_native32_complete_C_signed_heights_and_float_ABI(self):
        source=NATIVE+screen.SELECTED+'\n'+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-height','(s16 *)(*resource + 6)','(u16 *)(*resource + 6)'),
                ('native-count','!= 0','> 1'),('native-ABI','actor + 0x14C','actor + 0x150')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertNotEqual(result,0,(name,detail))
        self.receipt('native',profiles=2,cases_per_profile=26*256*3*2+65536,
            all_signed_height_halfwords=True,all_valid_actor_slots_and_identity_bytes=True,
            complete_C_and_real_mixed_float_ABI=True,live_table_mutating_callbacks=True,
            native_semantic_negatives=3,guest_wrapped_indices_not_native_acceptance=True)

    def test_09_immutable_snapshots_and_whole_linked_installation(self):
        with self.assertRaisesRegex(ValueError,'immutable'):self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text();before_source=(self.out/'before-source').read_text()
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
        struct.pack_into('>70I',expected,elf_slot_offset(before,screen.ENTRY,280),*self.original)
        struct.pack_into('>I',expected,installed.symbol_size_offset(before,screen.FUNCTION,screen.ENTRY),280)
        actual=(self.root/self.paths['elf']).read_bytes();em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5];expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_one_280_byte_slot_and_symbol_extent_change=True,
            guards_added=15,guard_history_prefix_exact=True,conversion_progress_rodata_exact=True,
            all_other_linked_bytes_addresses_extents_exact=True,protected_data=audit)


NATIVE=r'''
#include <stddef.h>
typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
u8 D_800CC2D0[26*812] __attribute__((aligned(16)));
u8 *D_800D1C90[256];u16 D_800C5A90[256];
static u8 definition[64],alternate[64],expected[812],*currentActor;
static u32 plan,error,resultValue,returnAddress,calls[3][5],wanted[3][5],callCount,wantedCount,currentIdentity;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(f32)==4)?1:-1];
static u32 floatBits(float f){union {float f;u32 u;} x;x.f=f;return x.u;}
static void logCall(u32 *out,u32 kind,u32 a,u32 b,u32 c,u32 d) {
    out[0]=kind;out[1]=a;out[2]=b;out[3]=c;out[4]=d;
}
void func_15062BDC(u8 *actor,float xz,float y) {
    if(actor!=currentActor || callCount>=3)error=1;
    logCall(calls[callCount++],0,(u32)actor,floatBits(xz),floatBits(y),0);
    if(plan) {D_800D1C90[currentIdentity]=alternate;actor[4]=19;*(u32 *)(actor+0x14C)=0xDEADBEEF;}
}
s32 func_15084D00(u8 *actor) {
    if(actor!=currentActor || callCount>=3)error=2;
    logCall(calls[callCount++],1,(u32)actor,0,0,0);
    if(plan==2)D_800C5A90[resultValue&255]=0;
    return resultValue;
}
u32 func_1502B020(u32 *size,u32 depth,...) {
    __builtin_va_list ap;u32 category,index;
    __builtin_va_start(ap,depth);category=__builtin_va_arg(ap,u32);index=__builtin_va_arg(ap,u32);__builtin_va_end(ap);
    if(callCount>=3)error=3;
    logCall(calls[callCount++],2,(u32)size,depth,category,index);
    *(u32 *)(currentActor+0x58)=0x13572468;
    return returnAddress;
}
'''
NATIVE_RUNNER=r'''
static int qualify(int slot,int identity,int height,int count,int mutation) {
    int i,j;u32 xz=identity&1?0x7F812345:0x80000000,y=identity&2?0xFF800000:0x3F800000;
    u8 *actor=D_800CC2D0+slot*812;
    currentActor=actor;currentIdentity=identity;callCount=wantedCount=error=0;plan=mutation;
    resultValue=identity&1?0x987654FF:8;returnAddress=identity&2?0:0xFEDCBA98;
    for(i=0;i<812;i++)actor[i]=0xA5;
    for(i=0;i<64;i++)definition[i]=alternate[i]=0xA5;
    for(i=0;i<256;i++){D_800D1C90[i]=definition;D_800C5A90[i]=(u16)count;}
    *(s16 *)(definition+6)=(s16)height;definition[18]=91;alternate[18]=173;
    *(u32 *)(actor+0x14C)=xz;*(u32 *)(actor+0x150)=y;
    for(i=0;i<812;i++)expected[i]=actor[i];
    expected[4]=(u8)identity;
    if(identity==255) {
        static const int offsets[]={0xE4,0xE6,0xE8,0xD2,0xD4,0xD6,0x160};
        for(i=0;i<7;i++)*(u16 *)(expected+offsets[i])=(u16)(i==3 || i==4?70:0);
        *(u32 *)(expected+0xC8)=0;
    } else {
        *(float *)(expected+0xC8)=(float)(height>=32768?height-65536:height);
        logCall(wanted[wantedCount++],0,(u32)actor,xz,y,0);
        if(plan){expected[4]=19;*(u32 *)(expected+0x14C)=0xDEADBEEF;}
        expected[5]=plan?173:91;
    }
    logCall(wanted[wantedCount++],1,(u32)actor,0,0,0);expected[6]=(u8)resultValue;
    if(count && plan!=2) {
        logCall(wanted[wantedCount++],2,0,2,2,resultValue&255);
        *(u32 *)(expected+0x58)=returnAddress;
    }
    func_150837D4(slot,identity,0xFEDCBA98);
    if(error || callCount!=wantedCount)return 1;
    for(i=0;i<812;i++)if(actor[i]!=expected[i])return 2;
    for(i=0;i<(int)callCount;i++)for(j=0;j<5;j++)if(calls[i][j]!=wanted[i][j])return 3;
    if(D_800D1C90[identity]!=(plan && identity!=255?alternate:definition))return 4;
    return 0;
}
int run(void) {
    int slot,id,plan,count,height,r;
    for(slot=0;slot<26;slot++)for(id=0;id<256;id++)for(plan=0;plan<3;plan++)for(count=0;count<2;count++) {
        r=qualify(slot,id,(id*257)&65535,count,plan);if(r)return r;
    }
    for(height=0;height<65536;height++){r=qualify(0,7,height,1,1);if(r)return r;}
    return 0;
}
'''


if __name__=='__main__':unittest.main()
