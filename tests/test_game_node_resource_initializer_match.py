"""Full resource initializer: loader outputs, paired buffers, rollback and actual callers."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_node_resource_initializer_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_animation_node_constructor_match as factory
from tools.tests import test_game_actor_animation_constructor_match as constructor
from tools.tests import test_game_node_action_match as action
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.patch_generated_slice_ld import load_game_data_layout

STACK,ACTOR,NODE,MASK=factory.STACK,factory.ACTOR,factory.NODE,0xFFFFFFFF
DEFAULT,SELECTED,ALLOCATE,FREE,COPY=screen.recovery.SYMBOLS.values()
SOURCE,ALTERNATE,DEST1,DEST2,DEST3,ACTOR2=0x39000,0x3B000,0x3D000,0x3F000,0x41000,0x43000


def fixture(selector=255,kind=133,flags=0,actor_flags=8,cached=0,phase=0,length=16,transform=1):
    memory=factory.fixture(phase=phase)
    for start,size in ((SOURCE,256),(ALTERNATE,256),(DEST1,256),(DEST2,256),(DEST3,256),(ACTOR2,0x340)):
        memory.update({start+i:(i*37+(start>>12))&255 for i in range(size)})
    for address,value,size in ((NODE+1,kind,1),(NODE+4,flags,1),(NODE+0x17,selector,1),
            (NODE+0x24,cached,4),(ACTOR+0x66,actor_flags,1),(ACTOR2+0x66,0,1)):
        put(memory,address,value,size)
    return memory


def changes(role,ordinal,plan,node,actor,source_home,frame):
    if role=='load' and plan==1:return ((node+4,0x10,1),(actor+0x66,12,1),(source_home,ALTERNATE,4),
        (node+0x24,ALTERNATE+16,4))
    if role=='load' and plan==4:return ((frame+0x44,ACTOR2,4),)
    if role=='allocate' and ordinal==1 and plan==2:return ((node+0x28,DEST3,4),)
    if role=='copy' and ordinal==0 and plan==2:return ((source_home,ALTERNATE,4),(node+0x2C,DEST1,4))
    if role=='copy' and ordinal==0 and plan==6:return ((node+8,77,1),(node+9,99,1))
    if role=='free' and plan==3:return ((node+0x28,0x12345678,4),(node+8,133,1))
    return ()


def reference(memory,node=NODE,actor=ACTOR,phase=0,status=0,first=DEST1,second=DEST2,
        length=16,transform=1,source=SOURCE,plan=0,entry=screen.ENTRY,symbols=None):
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x40
    default,selected,allocate,free,copy=(symbols or screen.recovery.SYMBOLS).values()
    def get(address,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped read',address,size)
        value=read(state,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped write',address,size)
        value&=(1<<(size*8))-1;put(state,address,value,size);events.append(('W',address,size,value))
    def call(target,packet,role,ordinal=0):
        events.append(('CALL',target,packet));calls.append((target,*packet))
        if role=='load':
            if target==default:_,end,meta,home,matrix,_,_=packet;attached=0
            else:_,_,end,meta,home,matrix,attached=packet
            store(end,source+length);store(meta,0x7B,1);store(home,source);store(matrix,transform)
            if attached:store(attached,0xF1238004)
        elif role=='copy':
            src,dest,size=packet;assert size<=256,('unbounded copy fixture',size)
            data=[get(src+i,1) for i in range(size)]
            for i,value in enumerate(data):store(dest+i,value,1)
        for address,value,size in changes(role,ordinal,plan,node,actor,frame+0x3C,frame):store(address,value,size)
        return status&MASK if role=='load' else (first if ordinal==0 else second)&MASK if role=='allocate' else 0xBEEF1234
    def finish(result):
        get(frame+0x2C);get(frame+0x28);return state,events,calls,result
    store(frame+0x28,0x5A000010);store(frame+0x2C,0xDEAD0000);store(frame+0x44,actor)
    if get(node+0x24):return finish(0)
    selector=get(node+0x17,1);selector=selector if selector<128 else selector-256
    kind=get(node+1,1)
    if selector==-1:
        store(frame+0x10,node+0x30);store(frame+0x18,0);store(frame+0x14,0)
        packet=(kind,node+0x24,node+0x14,frame+0x3C,read(state,frame+0x10),read(state,frame+0x14),read(state,frame+0x18))
        target=default
    else:
        store(frame+0x18,node+0x48);store(frame+0x14,node+0x30);store(frame+0x10,frame+0x3C)
        packet=(kind,selector&MASK,node+0x24,node+0x14,read(state,frame+0x10),read(state,frame+0x14),read(state,frame+0x18))
        target=selected
    if call(target,packet,'load'):return finish(1)
    live_actor=get(frame+0x44);flags=get(node+4,1);end=get(node+0x24);start=get(frame+0x3C)
    actor_flags=get(live_actor+0x66,1);size=(end-start)&MASK
    if flags&16 or actor_flags&12!=8 or not get(node+0x30):
        store(node+0x28,get(frame+0x3C));store(node+0x2C,get(frame+0x3C))
    else:
        store(frame+0x34,size);result=call(allocate,(size,1,2,2),'allocate');store(node+0x28,result)
        if not result:return finish(1)
        size=get(frame+0x34);result=call(allocate,(size,1,2,2),'allocate',1);store(node+0x2C,result)
        if not result:
            call(free,(get(node+0x28),),'free');store(node+0x28,0);return finish(1)
        for ordinal,offset in enumerate((0x28,0x2C)):
            packet=(get(frame+0x3C),get(node+offset),get(frame+0x34));call(copy,packet,'copy',ordinal)
        store(node+8,1,1)
    store(node+9,1,1);return finish(0)


class ResourceOracle(reset.ResetOracle):
    def __init__(self,words,memory,node=NODE,actor=ACTOR,phase=0,status=0,first=DEST1,second=DEST2,
            length=16,transform=1,source=SOURCE,plan=0,entry=screen.ENTRY,symbols=None,connected=None):
        guest.AttachmentOracle.__init__(self,words,memory,arguments=(node,actor),phase=phase,entry=entry,connected=connected)
        self.targets=dict(zip((symbols or screen.recovery.SYMBOLS).values(),('default','selected','allocate','free','copy')))
        self.counts={target:7 if role in ('default','selected') else 4 if role=='allocate' else 3 if role=='copy' else 1
            for target,role in self.targets.items()}
        self.node,self.actor,self.frame=node,actor,STACK+phase-0x40
        self.status,self.first,self.second=status,first,second
        self.length,self.transform,self.source,self.plan=length,transform,source,plan
        self.allocations=self.copies=0;self.source_home=None
    def hook(self,target):
        role=self.targets[target];packet=self.calls[-1][1:];ordinal=0
        if role in ('default','selected'):
            if role=='default':_,end,meta,home,matrix,_,_=packet;attached=0
            else:_,_,end,meta,home,matrix,attached=packet
            self.source_home=home
            self.put(end,(self.source+self.length)&MASK,4);self.put(meta,0x7B,1)
            self.put(home,self.source,4);self.put(matrix,self.transform,4)
            if attached:self.put(attached,0xF1238004,4)
            role='load';result=self.status
        elif role=='allocate':
            ordinal=self.allocations;result=self.first if ordinal==0 else self.second;self.allocations+=1
        elif role=='copy':
            ordinal=self.copies;self.copies+=1;src,dest,size=packet
            assert size<=256,('unbounded copy fixture',size)
            data=[self.get(src+i,1) for i in range(size)]
            for i,value in enumerate(data):self.put(dest+i,value,1)
            result=0xBEEF1234
        else:result=0xBEEF1234
        for address,value,size in changes(role,ordinal,self.plan,self.node,self.actor,self.source_home,self.frame):
            self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&MASK


class ConnectedOracle(factory.NodeOracle):
    def __init__(self,*args,resource_first=DEST1,resource_second=DEST2,resource_status=0,resource_plan=0,**kwargs):
        super().__init__(*args,**kwargs)
        self.counts.update({DEFAULT:7,SELECTED:7,FREE:1,COPY:3})
        self.resource_targets=dict(zip(screen.recovery.SYMBOLS.values(),('default','selected','allocate','free','copy')))
        self.resource_first,self.resource_second=resource_first,resource_second
        self.resource_status,self.resource_plan=resource_status,resource_plan
        self.length,self.transform,self.source=16,1,SOURCE
        self.allocations=self.copies=0;self.source_home=None;self.initializer_snapshots=[]
        self.loading=False
        self.factory_allocations=0;self.call_snapshots=[]
    def record_call(self,target):
        self.call_snapshots.append((self.memory.copy(),self.r[29],target,len(self.calls)))
        if target in (factory.screen.ENTRY,factory.CLEANUP,factory.SETUP):self.loading=False
        if target==screen.ENTRY:
            self.node,self.actor=self.r[4:6];self.frame=self.r[29]-0x40
            self.allocations=self.copies=0
            first=self.resource_first+(self.factory_allocations-1)*0x400 if self.resource_first else 0
            second=self.resource_second+(self.factory_allocations-1)*0x400 if self.resource_second else 0
            self.current_first,self.current_second=first,second
            self.initializer_snapshots.append((self.memory.copy(),self.r[29],tuple(self.r[4:6]),len(self.calls),first,second))
        super().record_call(target)
    def hook(self,target):
        if target in (DEFAULT,SELECTED):self.loading=True
        if target in (DEFAULT,SELECTED,FREE,COPY) or target==ALLOCATE and self.loading:
            old=(self.targets,self.first,self.second,self.status,self.plan)
            self.targets,self.first,self.second,self.status,self.plan=(self.resource_targets,self.current_first,
                self.current_second,self.resource_status,self.resource_plan)
            ResourceOracle.hook(self,target)
            self.targets,self.first,self.second,self.status,self.plan=old
        elif target==ALLOCATE:
            size,a,b,c=self.calls[-1][1:]
            assert (size,a,b,c) in ((0x5C,1,0,2),(0x80,1,2,2))
            if size==0x5C:
                result=0x51000+self.factory_allocations*0x80;self.factory_allocations+=1
            else:result=0x61000+(self.factory_allocations-1)*0x80
            for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result
        else:super().hook(target)


def public(memory):return factory.public(memory)


class GameNodeResourceInitializerMatchTests(unittest.TestCase):
    maxDiff=1800
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-node-resource-initializer-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.recovery.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        with (cls.out/'before-guards').open(newline='') as f:cls.fields=csv.DictReader(f).fieldnames
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rows=screen.guard_rows(cls.out/'selected.o');cls.write_rows(cls.out/'qualified-guards.csv',cls.read_rows()+cls.rows)
        cls.write_rows(cls.out/'isolated.csv',cls.rows);cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>96I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/5D2C0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_5D2C0'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.original
        cls.before=(cls.out/'before-elf').read_bytes();assert audit_layout(cls.out/'before-elf',cls.root/'conker')['exact']
    @classmethod
    def read_rows(cls):
        with (cls.out/'before-guards').open(newline='') as f:return list(csv.DictReader(f))
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        script=cls.out/(name+'-link.ld');elf=cls.out/(name+'-link.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in (symbols or screen.recovery.SYMBOLS).items()],
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>96I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,raw=True,**settings):
        expected=reference(memory,**settings);models=[]
        for words in forms or (self.original,self.fitted):
            model=ResourceOracle(words,memory,**settings).run();models.append(model)
            self.assertEqual({a:(v,expected[0].get(a)) for a,v in model.memory.items() if v!=expected[0].get(a)}, {})
            self.assertEqual((model.events,model.calls,model.r[2]),expected[1:])
        if raw:
            model=ResourceOracle(self.raw,memory,**settings).run()
            self.assertEqual((public(model.memory),model.calls,model.r[2]),(public(expected[0]),expected[2],expected[3]))
        return models

    def test_01_complete_shape_stale_words_relocations_and_publication(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['differences'],
            self.meta['diagnostics']),(96,64,0,12,''));self.assertEqual(self.meta['relocations'],screen.RELOCATIONS)
        for index in range(96):
            stale=list(screen.RAW);stale[index]^=1
            with self.assertRaises(ValueError):screen.recipe(stale)
        text,functions,relocations=parse_object(self.out/'selected.o')
        for offset in screen.RELOCATIONS:
            wrong=dict(relocations);wrong[offset]=[('R_MIPS_26','stale_helper')]
            with patch.object(screen,'parse_object',return_value=(text,functions,wrong)):
                with self.assertRaises(ValueError):screen.guard_rows(self.out/'selected.o')
        self.assertTrue(all(r['omit']=='false' and not r['insert_after'] and
            r['expected_relocations']==r['replacement_relocations']=='-' for r in self.rows))
        before=(self.out/'before-guards').read_bytes();path=self.out/'publish-test.csv';path.write_bytes(before)
        screen.append_guards(path,before,self.out/'selected.o');published=path.read_bytes();self.assertTrue(published.startswith(before))
        with path.open(newline='') as f:self.assertEqual(list(csv.DictReader(f)),self.read_rows()+self.rows)
        with self.assertRaises(ValueError):screen.append_guards(path,before,self.out/'selected.o')
        with self.assertRaises(ValueError):screen.append_guards(path,published,self.out/'selected.o')
        self.receipt('shape',words=96,frame=64,guards=12,insertions=0,omissions=0,pools=0,
            stale_word_rejections=96,stale_relocation_rejections=7,raw_private_read_order_not_claimed=True)

    def test_02_all_selector_kind_flag_bytes_outputs_and_failures(self):
        cases=0;coverage=set()
        for value,axis,status,phase in itertools.product(range(256),('selector','kind','flags','actor_flags'),
                (0,1,0x80000000,MASK),(0,8)):
            values={axis:value};memory=fixture(**values,phase=phase)
            models=self.compare(memory,status=status,phase=phase);coverage.update(models[0].visits);cases+=1
        for selector,flags,actor_flags,transform,cached,first,second,length in itertools.product(
                (0,127,128,254,255),(0,16),(0,8,12),(0,1),(0,SOURCE),(0,DEST1),(0,DEST2),(0,1,16,127)):
            memory=fixture(selector,flags=flags,actor_flags=actor_flags,transform=transform,cached=cached)
            models=self.compare(memory,transform=transform,first=first,second=second,length=length)
            coverage.update(models[0].visits);cases+=1
        missing=sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY,screen.ENTRY+384,4))-coverage)
        self.assertEqual(missing,[38])
        self.receipt('guest',cases=cases,executions=cases*3,raw_public_cases=cases,
            all_selector_kind_node_actor_flag_bytes=True,full_nonzero_status_normalized_to_one=True,
            paired_allocation_failure_and_rollback=True,zero_and_variable_copy_lengths=True,
            retail_words_reached=95,unreachable_duplicate_actor_home_load=38,GP_FPR_clobbered=True,
            independent_full_private_order_on_retail_and_fitted=True)

    def test_03_live_callback_outputs_aliases_NULL_and_fired_fault_prefixes(self):
        cases=prefixes=0
        for phase,selector,plan,first,second in itertools.product((0,8),(0,255),(0,1,2,3,4,6),(0,DEST1),(0,DEST2)):
            memory=fixture(selector,phase=phase);models=self.compare(memory,phase=phase,plan=plan,first=first,second=second)
            cases+=1
            if phase==0 and first==DEST1:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.fitted):
                        model=ResourceOracle(words,memory,phase=phase,plan=plan,first=first,second=second);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls,failed[0].f),
                        (failed[1].memory,failed[1].events,failed[1].calls,failed[1].f));prefixes+=1
        for phase,source in itertools.product((0,8),(NODE+0x28,ACTOR+0x60,STACK-0x40+0x10)):
            self.compare(fixture(flags=16,phase=phase),phase=phase,source=source,length=0,raw=False);cases+=1
        for status,cached in ((MASK,0),(0,SOURCE)):
            self.compare(fixture(cached=cached),actor=0,status=status);cases+=1
        for flags,transform in ((0,1),(16,0)):
            memory=fixture(flags=flags);failed=[]
            for words in (self.original,self.fitted):
                model=ResourceOracle(words,memory,actor=0,transform=transform)
                with self.assertRaises(AssertionError) as caught:model.run()
                self.assertEqual(caught.exception.args,(('unmapped read',0x66,1),));failed.append(model)
            self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls),
                (failed[1].memory,failed[1].events,failed[1].calls))
        for size in (0x7FFFFFFF,0x80000000,MASK):
            self.compare(fixture(flags=16),length=size,raw=False);cases+=1
        self.receipt('aliases',cases=cases,fired_fault_pairs=prefixes,failed_executions=prefixes*2,
            live_source_output_reloaded_after_first_copy=True,live_node_destinations_and_free_before_clear=True,
            NULL_actor_short_circuit_only_cached_or_loader_failure=True,actor_read_even_bypass=True,
            private_home_aliases_and_wrapping_noncopy_span_guest_only=True,raw_private_order_not_claimed=True)

    def test_04_independent_all_five_callback_rebases(self):
        cases=0
        for entry,addresses in ((screen.ENTRY,tuple(screen.recovery.SYMBOLS.values())),
                (0x15207FFC,(0x15218004,0x15227FFC,0x10017FFC,0x10028004,0x10038004)),
                (0x15308004,(0x15317FFC,0x15328004,0x10027FFC,0x10038004,0x10047FFC))):
            symbols=dict(zip(screen.recovery.SYMBOLS,addresses))
            forms=tuple(self.link(name,entry,symbols) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[2])
            for selector,status,flags,first,second in itertools.product((128,255),(0,MASK),(0,16),(0,DEST1),(0,DEST2)):
                memory=fixture(selector,flags=flags)
                settings=dict(entry=entry,symbols=symbols,status=status,first=first,second=second)
                models=self.compare(memory,forms=(forms[0],forms[2]),raw=False,**settings)
                raw=ResourceOracle(forms[1],memory,**settings).run()
                self.assertEqual((public(raw.memory),raw.calls,raw.r[2]),
                    (public(models[0].memory),models[0].calls,models[0].r[2]));cases+=1
        self.receipt('rebases',links=9,cases=cases,executions=cases*3,five_callbacks_seven_JAL_sites=True,
            signed_seven_argument_loader_packet=True)

    def test_05_copied_owner_real_postprocess_padding_pools_and_neighbors(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[];padded=[]
        for i,(name,source) in enumerate((('owner-before',before),('owner-after',screen.install(before)))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);objects.append(obj);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            assembly=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_5D2C0',str(assembly),'--word-patches',str(self.out/('before-guards' if i==0 else 'qualified-guards.csv'))],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),str(assembly)],
                check=True,capture_output=True);padded.append(parse_object(assembly.with_suffix('.o')))
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(screen.guard_rows(objects[1]),self.rows)
        old,new=padded;start=new[1][screen.FUNCTION]['value'];expected=bytearray(old[0])
        expected[start:start+384]=struct.pack('>96I',*screen.recipe(screen.RAW));self.assertEqual(bytes(expected),new[0])
        for name in old[1]:
            if name!=screen.FUNCTION:self.assertEqual(old[1][name],new[1][name])
        self.assertEqual(old[2],{k:v for k,v in new[2].items() if not start<=k<start+384})
        self.receipt('owner',untouched_neighbors=len(old[1])-1,neighbor_extents_bytes_relocations_exact=True,
            pools_exact=True,diagnostics_equal=True,diagnostic_bytes=len(warnings[1]),actual_padder=True,
            deeper_loader_and_cleanup_stubs_unchanged=True)

    def test_06_effective_fresh_IDO_negative_controls(self):
        controls=(('unsigned-selector',screen.SELECTED.replace('*(s8 *)','*(u8 *)'),{},{}),
            ('narrow-status',screen.SELECTED.replace('if (func_1502FE10','if ((u8)func_1502FE10'),{},dict(status=0x80000000)),
            ('wrong-mask',screen.SELECTED.replace('actorFlags & 0xC','actorFlags & 8'),dict(actor_flags=12),{}),
            ('wrong-mode',screen.SELECTED.replace('allocate_memory(size, 1, 2, 2)','allocate_memory(size, 1, 0, 2)'),{},{}),
            ('wrong-size',screen.SELECTED.replace('allocate_memory(size, 1, 2, 2)','allocate_memory(size + 1, 1, 2, 2)'),{},{}),
            ('skip-free',screen.SELECTED.replace('                func_10004074(*(u8 **)(node + 0x28));\n',''),{},dict(second=0)),
            ('skip-clear',screen.SELECTED.replace('                *(u8 **)(node + 0x28) = 0;\n',''),{},dict(second=0)),
            ('wrong-copy',screen.SELECTED.replace('bcopy(source, *(u8 **)(node + 0x2C), size);','bcopy(source, *(u8 **)(node + 0x28), size);'),{},{}),
            ('cached-source',screen.SELECTED.replace('''            bcopy(source, *(u8 **)(node + 0x28), size);
            bcopy(source, *(u8 **)(node + 0x2C), size);''','''            {
                u8 *cachedSource = source;
                bcopy(cachedSource, *(u8 **)(node + 0x28), size);
                bcopy(cachedSource, *(u8 **)(node + 0x2C), size);
            }'''),{},dict(plan=2)),
            ('early-success',screen.SELECTED.replace('return 1;','return 0;'),{},dict(first=0)))
        for name,body,inputs,settings in controls:
            meta,words=screen.compile_candidate(self.root,self.out,name,body);self.assertGreater(meta['differences'],0)
            memory=fixture(**inputs);actual=ResourceOracle(words,memory,**settings).run()
            expected=ResourceOracle(self.original,memory,**settings).run()
            self.assertNotEqual((public(actual.memory),actual.calls,actual.r[2]),
                (public(expected.memory),expected.calls,expected.r[2]),name)
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))

    def test_07_native32_optimized_unoptimized_valid_output_contract(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        for name,body in (('native-wrong-mask',screen.SELECTED.replace('actorFlags & 0xC','actorFlags & 8')),
                ('native-skip-clear',screen.SELECTED.replace('                *(u8 **)(node + 0x28) = 0;\n',''))):
            result,_=self.run_native(name,NATIVE_PREFIX+body+NATIVE_RUNNER);self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=12802,executions=25604,profiles=['O2','O0'],
            native_negative_controls=2,typed_seven_argument_loader_packets=True,
            complete_node_gaps_buffers_actor_compared=True,source_output_escapes_and_live_second_copy=True,
            successful_loaders_write_outputs=True,disjoint_fresh_allocations=True)

    def test_08_actual_factory_initializer_action_caller_and_ROM_descriptors(self):
        before=self.before;rom_start,vram,rom_end,_=load_game_data_layout(self.root/'conker')
        def words(address,count):return list(struct.unpack_from('>%dI'%count,before,elf_slot_offset(before,address,count*4)))
        factory_words=words(factory.screen.ENTRY,152);setup=words(factory.SETUP,113)
        caller=words(constructor.screen.ENTRY,89);cleanup=words(factory.CLEANUP,3)
        self.assertEqual(factory_words,list(struct.unpack_from('>152I',self.rom,factory.screen.ROM)))
        self.assertEqual(setup,list(struct.unpack_from('>113I',self.rom,action.screen.ROM)))
        self.assertEqual(caller,list(struct.unpack_from('>89I',self.rom,constructor.screen.ROM)))
        self.assertEqual(cleanup,[0x00001025,0x03E00008,0])
        self.assertEqual(words(DEFAULT,3),[0x00001025,0x03E00008,0])
        self.assertEqual(words(SELECTED,3),[0x00001025,0x03E00008,0])
        setup_data={}
        for address,size in ((action.screen.TABLE,220),(action.LOW,8)):
            data=before[elf_slot_offset(before,address,size):][:size]
            setup_data.update({address+i:value for i,value in enumerate(data)})
        assets={}
        for animation in (5,6,7,10,11,0x17,0x23,0x44):
            address=constructor.descriptor_address(animation);descriptor=before[elf_slot_offset(before,address,8):][:8]
            records=struct.unpack_from('>I',descriptor)[0];count=descriptor[4]
            data=before[elf_slot_offset(before,records,count*16):][:count*16]
            self.assertEqual(descriptor,self.rom[rom_start+address-vram:][:8])
            self.assertTrue(vram<=records and rom_start+records-vram+len(data)<=rom_end)
            self.assertEqual(data,self.rom[rom_start+records-vram:][:len(data)])
            self.assertTrue(all(data[i*16+3] in (1,2) for i in range(count)))
            assets[animation]=(address,descriptor,records,data)
        cases=prefixes=0
        for animation,phase,status,second in itertools.product(assets,(0,8),(0,0x80000000),(0,DEST2)):
            address,descriptor,records,data=assets[animation]
            memory=fixture(phase=phase);memory.update(setup_data)
            count=descriptor[4]
            for start,size in ((0x51000,count*0x80),(0x61000,count*0x80),(DEST1,count*0x400),(DEST2,count*0x400)):
                for i in range(size):memory.setdefault(start+i,(i*17+35)&255)
            memory.update({action.STATE+i:0xA5 for i in range(0x1C0)});put(memory,ACTOR+0x31C,action.STATE)
            memory.update({address+i:value for i,value in enumerate(descriptor)})
            memory.update({records+i:value for i,value in enumerate(data)})
            models=[]
            def model_for(initializer):
                connected={}
                for entry,code in ((factory.screen.ENTRY,factory_words),(screen.ENTRY,initializer),
                        (factory.SETUP,setup),(factory.CLEANUP,cleanup)):
                    connected.update({entry+i*4:w for i,w in enumerate(code)})
                return ConnectedOracle(caller,memory,args=(ACTOR,animation,0x7F812345,0),phase=phase,
                    entry=constructor.screen.ENTRY,connected=connected,resource_status=status,resource_second=second)
            for initializer in (self.original,self.fitted):models.append(model_for(initializer).run())
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].f,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].f,models[1].r[2]))
            self.assertTrue(any(c[0]==factory.screen.ENTRY and len(c)==14 for c in models[0].calls))
            self.assertTrue(models[0].initializer_snapshots)
            for model in models:
                for snapshot,stack,packet,ordinal,first_buffer,second_buffer in model.initializer_snapshots:
                    expected=reference(snapshot,*packet,phase=stack-STACK,status=status,first=first_buffer,second=second_buffer)
                    after=[c for c in model.calls[ordinal+1:] if c[0] in (DEFAULT,SELECTED,ALLOCATE,FREE,COPY)]
                    self.assertEqual(after[:len(expected[2])],expected[2])
                    after_snapshot=next(s for s,_,target,index in model.call_snapshots if index>ordinal and target in (factory.SETUP,factory.CLEANUP))
                    self.assertEqual(public(after_snapshot),public(expected[0]))
                for snapshot,stack,packet,ordinal in model.setup_snapshots:
                    expected=action.ActionReference(snapshot);expected.stack=stack;expected.run(*packet,99)
                    later=next(((s,index) for s,_,target,index in model.call_snapshots
                        if index>ordinal and target==factory.screen.ENTRY),(model.memory,len(model.calls)))
                    self.assertEqual(public(later[0]),public(expected.memory))
                    self.assertEqual(model.calls[ordinal+1:later[1]],expected.calls)
            if phase==0 and status==0 and second==DEST2:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for initializer in (self.original,self.fitted):
                        model=model_for(initializer);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls,failed[0].f),
                        (failed[1].memory,failed[1].events,failed[1].calls,failed[1].f));prefixes+=1
            cases+=1
        self.receipt('connected',cases=cases,executions=cases*2,ROM_verified_descriptors=8,
            actual_152_word_factory_96_word_initializer_113_word_action_89_word_caller=True,
            owned_jump_tables=True,independent_initializer_and_action_public_effects=True,
            actual_cleanup_zero_stub=True,deeper_loader_zero_stubs_present_but_bounded_outputs_for_qualification=True,
            fired_fault_pairs=prefixes,failed_executions=prefixes*2,not_complete_resource_or_gameplay_acceptance=True)

    def test_10_actual_zero_loader_stub_exposes_unwritten_output_guest_only(self):
        cases=0
        for selector,phase,seed in itertools.product((128,255),(0,8),(SOURCE,ALTERNATE)):
            memory=fixture(selector,flags=16,phase=phase);home=STACK+phase-4;put(memory,home,seed)
            connected={}
            for target in (DEFAULT,SELECTED):
                code=list(struct.unpack_from('>3I',self.before,elf_slot_offset(self.before,target,12)))
                self.assertEqual(code,[0x00001025,0x03E00008,0])
                connected.update({target+i*4:w for i,w in enumerate(code)})
            models=[ResourceOracle(words,memory,phase=phase,connected=connected).run()
                for words in (self.original,self.fitted)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].r[2]))
            self.assertEqual(models[0].r[2],0);self.assertEqual(read(models[0].memory,NODE+0x24),0)
            self.assertEqual(read(models[0].memory,NODE+0x28),seed);self.assertEqual(read(models[0].memory,NODE+0x2C),seed)
            self.assertTrue(any(e==('R',home,4,seed) for e in models[0].events))
            self.assertFalse(any(e[0]=='W' and e[1]==home for e in models[0].events));cases+=1
        self.receipt('deeper-stub-boundary',cases=cases,executions=cases*2,actual_zero_loader_bodies=True,
            required_success_output_unwritten=True,private_residue_seeded_for_guest_proof_only=True,
            not_portable_C_or_complete_resources=True)

    def test_09_whole_ELF_single_slot_extent_guards_and_protected_inputs(self):
        source=(self.root/screen.SOURCE).read_text();before=self.before
        self.assertEqual(source,(self.out/'before-source').read_text() if screen.recovery.ORIGINAL in source
            else screen.install((self.out/'before-source').read_text()))
        if screen.recovery.ORIGINAL in source:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(before)
        struct.pack_into('>96I',expected,elf_slot_offset(before,screen.ENTRY,384),*self.fitted)
        old,new=metadata(before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:])
        symbol_table=old[4];changes=0
        for offset in range(symbol_table[4],symbol_table[4]+symbol_table[5],symbol_table[9]):
            a,b=SYMBOL.unpack_from(before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:])
                self.assertEqual((a[2],b[2]),(12,384));struct.pack_into('>I',expected,offset+8,b[2]);changes+=1
        self.assertEqual(changes,1);self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        guards=(self.root/self.paths['guards']).read_bytes();prefix=(self.out/'before-guards').read_bytes()
        self.assertTrue(guards.startswith(prefix))
        with (self.root/self.paths['guards']).open(newline='') as f:self.assertEqual(list(csv.DictReader(f)),self.read_rows()+self.rows)
        for name in ('progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        self.receipt('linked',installed=True,changed_function_count=1,changed_symbol_extents=1,
            all_other_ELF_bytes_exact=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),guard_prefix_exact=True,appended_rows=12,
            data_audit=audit,conversion_rows_unchanged=True)


NATIVE_PREFIX=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
static u32 nodeWords[24],expectedWords[24],actorWords[208];
static u8 sourceBytes[128],alternateBytes[128],buffers[2][128],expectedBuffers[2][128];
static s32 scenario,allocations,copies,loads,frees,errors,selectorValue,kindValue,lengthValue;
static u8 **escaped;static u32 statusValue;static u8 flagsValue,actorFlagsValue;static s32 transformValue;
static __attribute__((noinline)) s32 loader(s32 selected,s32 kind,s32 selector,u8 **end,u8 *meta,u8 **source,u8 **matrix,u8 **attached){
    if(selected!=(selectorValue!=255)||kind!=kindValue||
        (selected&&selector!=(s8)selectorValue)||end!=(u8 **)((u8 *)nodeWords+0x24)||
        meta!=(u8 *)nodeWords+0x14||matrix!=(u8 **)((u8 *)nodeWords+0x30)||
        attached!=(selected?(u8 **)((u8 *)nodeWords+0x48):0))errors++;
    loads++;escaped=source;*source=sourceBytes;*end=sourceBytes+lengthValue;*meta=0x7B;*matrix=(u8 *)transformValue;
    if(attached)*attached=(u8 *)0xF1238004u;
    return (s32)statusValue;
}
static s32 func_1502FE10(s32 kind,u8 **end,u8 *meta,u8 **source,u8 **matrix,s32 a,s32 b){
    if(a||b)errors++;
    return loader(0,kind,-1,end,meta,source,matrix,0);
}
static s32 func_1503F62C(s32 kind,s32 selector,u8 **end,u8 *meta,u8 **source,u8 **matrix,u8 **attached){
    return loader(1,kind,selector,end,meta,source,matrix,attached);
}
static void *allocate_memory(s32 size,s32 a,s32 b,s32 c){
    s32 n=allocations++;if(size!=lengthValue||a!=1||b!=2||c!=2||n>1)errors++;
    return scenario==n+1?0:buffers[n];
}
static void func_10004074(void *p){
    frees++;if(p!=buffers[0]||*(u8 **)((u8 *)nodeWords+0x28)!=p)errors++;
}
static void bcopy(const void *src,void *dst,s32 size){
    s32 i,n=copies++;const u8 *s=(const u8 *)src;u8 *d=(u8 *)dst;
    if(size!=lengthValue||dst!=buffers[n]||src!=(n&&scenario==4?alternateBytes:sourceBytes))errors++;
    for(i=0;i<size;i++)d[i]=s[i];
    if(!n&&scenario==4)*escaped=alternateBytes;
}
'''
NATIVE_RUNNER=r'''
static void pointer(u8 *p,u8 *v){*(u8 **)p=v;}
static s32 qualify(s32 axis,s32 value,s32 plan,s32 status){
    u8 *n=(u8 *)nodeWords,*e=(u8 *)expectedWords; s32 i,j,copying,result,wanted;
    selectorValue=axis==0?value:255;kindValue=axis==1?value:133;
    flagsValue=axis==2?(u8)value:0;actorFlagsValue=axis==3?(u8)value:8;
    transformValue=axis==4?(value&1):1;
    scenario=plan;statusValue=status?(u32)0x80000000u:0;lengthValue=(value%33);
    errors=loads=allocations=copies=frees=0;
    for(i=0;i<24;i++)nodeWords[i]=expectedWords[i]=0xA5A5A5A5u;
    for(i=0;i<208;i++)actorWords[i]=0xA5A5A5A5u;
    for(i=0;i<128;i++){
        sourceBytes[i]=(u8)(i*37+1);alternateBytes[i]=(u8)(i*53+9);
        for(j=0;j<2;j++)buffers[j][i]=expectedBuffers[j][i]=(u8)(i*17+j);
    }
    n[1]=e[1]=(u8)kindValue;n[4]=e[4]=flagsValue;n[0x17]=e[0x17]=(u8)selectorValue;
    pointer(n+0x24,0);pointer(e+0x24,0);((u8 *)actorWords)[0x66]=actorFlagsValue;
    result=func_1502FFD8(n,(u8 *)actorWords);escaped=0;copying=!(flagsValue&16)&&(actorFlagsValue&12)==8&&transformValue;
    wanted=status|| (copying&&(plan==1||plan==2));
    pointer(e+0x24,sourceBytes+lengthValue);e[0x14]=0x7B;pointer(e+0x30,(u8 *)transformValue);
    if(selectorValue!=255)pointer(e+0x48,(u8 *)0xF1238004u);
    if(!status){
        if(copying){
            pointer(e+0x28,plan==1?0:buffers[0]);
            if(plan!=1){pointer(e+0x2C,plan==2?0:buffers[1]);if(plan==2)pointer(e+0x28,0);}
            if(plan!=1&&plan!=2){e[8]=1;
                for(i=0;i<lengthValue;i++){
                    expectedBuffers[0][i]=sourceBytes[i];expectedBuffers[1][i]=plan==4?alternateBytes[i]:sourceBytes[i];
                }
            }
        }else{pointer(e+0x28,sourceBytes);pointer(e+0x2C,sourceBytes);}
        if(!wanted)e[9]=1;
    }
    if(result!=wanted||errors||loads!=1)return 1;
    if(allocations!=(status||!copying?0:plan==1?1:2)||
        copies!=(status||!copying||plan==1||plan==2?0:2)||frees!=(!status&&copying&&plan==2))return 2;
    for(i=0;i<24;i++)if(nodeWords[i]!=expectedWords[i])return 3;
    for(i=0;i<128;i++)for(j=0;j<2;j++)if(buffers[j][i]!=expectedBuffers[j][i])return 4;
    for(i=0;i<208*4;i++)if(((u8 *)actorWords)[i]!=(i==0x66?actorFlagsValue:0xA5))return 5;
    return 0;
}
int run(void){s32 axis,value,plan,status,r;
    for(axis=0;axis<5;axis++)for(value=0;value<256;value++)for(plan=0;plan<5;plan++)for(status=0;status<2;status++){
        r=qualify(axis,value,plan,status);if(r)return r;
    }
    loads=allocations=copies=frees=errors=0;
    if(func_1502FFD8((u8 *)nodeWords,0)||loads||allocations||copies||frees||errors)return 6;
    pointer((u8 *)nodeWords+0x24,0);statusValue=0x80000000u;
    if(func_1502FFD8((u8 *)nodeWords,0)!=1||loads!=1||allocations||copies||frees||errors)return 7;
    escaped=0;
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
