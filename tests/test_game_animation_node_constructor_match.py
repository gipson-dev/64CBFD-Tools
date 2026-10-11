"""Full node factory: ordered retail oracle, semantic C, actual caller and linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_animation_node_constructor_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_animation_constructor_match as constructor
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_node_action_match as action
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.patch_generated_slice_ld import load_game_data_layout

STACK,ACTOR,MASK=constructor.STACK,constructor.ACTOR,0xFFFFFFFF
HEAD,ALLOCATE,INITIALIZE,CLEANUP,SETUP=screen.recovery.SYMBOLS.values()
NODE,OLD,SECOND,MATRIX,VALUES=0x31000,0x32000,0x33000,0x35000,0x37000
LIMITS=(0,1,4,8,12,127,128,255,256,260,0xFFFF,0x80000004,MASK)


def arguments(kind=0x37,index=255,flags=0,mode=0,key=9,duration=0,values=VALUES,actor=ACTOR,seed=0):
    return (actor,kind&MASK,index&MASK,flags&MASK,0x12340000+seed,mode&MASK,duration&MASK,
        key&MASK,(0xABCDEF80+seed)&MASK,values,0xFFFFFFFF,(0x12348000+seed)&MASK,0xFFFF0001+seed)


def fixture(args=None,group=7,listing=0,seed=0,phase=0,head=HEAD):
    args=args or arguments(seed=seed)
    memory={STACK+i:0xA5 for i in range(-0x400,0x100)}
    for start,length in ((ACTOR,0x340),(NODE,0x60),(OLD,0x60),(SECOND,0x60),(MATRIX,0x80),(VALUES,8)):
        memory.update({start+i:(i*17+35+seed)&255 for i in range(length)})
    memory.update({head+i:0xA5 for i in range(4)})
    if args[9] and args[9] not in (VALUES,):
        for i in range(6):memory.setdefault(args[9]+i,(i*67+seed)&255)
    put(memory,ACTOR+0x3B,group,1)
    put(memory,head,OLD if listing else 0)
    for address,kind,key,link in ((OLD,0xFF if listing==2 else args[1],args[7],SECOND if listing==2 else 0),
            (SECOND,args[1],args[7],0)):
        put(memory,address,group,1);put(memory,address+1,kind,1);put(memory,address+6,key,1)
        put(memory,address+0x54,link);put(memory,address+0x58,0xF1238004)
    for i,value in enumerate(args[4:]):put(memory,STACK+phase+0x10+i*4,value)
    return memory


def actions(target,ordinal,plan,stack,head,args):
    if target==ALLOCATE and ordinal==0:
        if plan==1:return ((head,SECOND,4),(ACTOR+0x3B,129,1))
        if plan==2:return ((stack+12,12,4),(stack+0x1C,0xABCDEF44,4),(ACTOR+0x3B,255,1))
        if plan==3:return ((args[9],0xF123,2),(args[9]+2,0x8001,2),(args[9]+4,0xFFFF,2))
    if target==INITIALIZE and plan==4:
        return ((NODE+0x24,0xBEEF1234,4),(NODE+0x13,133,1),(ACTOR+0x6F,255,1))
    if target==SETUP and plan==4:return ((NODE+0x3C,0x80000000,4),)
    if target==CLEANUP and plan==4:return ((head,0,4),(NODE+0x48,0x80018004,4))
    return ()


def reference(memory,args,phase=0,head=HEAD,allocate=ALLOCATE,initialize=INITIALIZE,cleanup=CLEANUP,
        setup=SETUP,first=NODE,second=MATRIX,status=0,plan=0,stack=None,return_address=0xDEAD0000):
    state,events,calls=memory.copy(),[],[]
    stack=STACK+phase if stack is None else stack;frame=stack-0x30
    for i,value in enumerate(args[4:]):put(state,stack+0x10+i*4,value)
    def get(where,size=4):
        where&=MASK;assert all(where+i in state for i in range(size)),('reference unmapped read',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size=4):
        where&=MASK;assert all(where+i in state for i in range(size)),('reference unmapped write',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    allocation=0
    def call(target,packet):
        nonlocal allocation
        events.append(('CALL',target,packet));calls.append((target,*packet))
        base={allocate:ALLOCATE,initialize:INITIALIZE,cleanup:CLEANUP,setup:SETUP}[target]
        ordinal=allocation if target==allocate else 0
        for where,value,size in actions(base,ordinal,plan,stack,head,args):store(where,value,size)
        if target==allocate:
            result=first if allocation==0 else second;allocation+=1;return result&MASK
        return status&MASK if target==initialize else 0xBEEF1234
    def finish(result):
        get(frame+0x1C);get(frame+0x14);get(frame+0x18)
        return state,events,calls,result
    store(frame+0x18,0x5A000011);store(frame+0x1C,return_address);store(frame+0x14,0x5A000010)
    for offset,value in ((0x30,args[0]),(0x38,args[2]),(0x3C,args[3])):store(frame+offset,value)
    actor=get(frame+0x30);flags=get(frame+0x3C);group=get(actor+0x3B,1)
    if not group:return finish(0)
    if not flags&8:
        node=get(head);key=get(frame+0x4C)
        while node:
            node_group=get(node,1);next_node=get(node+0x54)
            if group==node_group and key==get(node+6,1) and args[1]==get(node+1,1):return finish(0)
            node=next_node
    node=call(allocate,(0x5C,1,0,2));flags=get(frame+0x3C);key=get(frame+0x4C)
    if not node:return finish(0)
    previous=get(head);failed=0
    if previous:store(previous+0x58,node);previous=get(head)
    store(node+0x54,previous);store(node+0x58,0)
    actor=get(frame+0x30);store(head,node);group=get(actor+0x3B,1)
    store(node+1,args[1],1);store(node,group,1);index=get(frame+0x38)
    for offset in (0x24,0x28,0x2C,0x30):store(node+offset,0)
    store(node+3,255,1);store(node+0x44,0);store(node+4,flags,1);store(node+6,key,1)
    store(node+0x40,0x3F800000);store(node+2,index,1)
    values=get(frame+0x54);mode=get(frame+0x44);extra=get(frame+0x50)
    store(node+0x38,0);store(node+0x3C,0);store(node+8,0,1);store(node+9,0,1)
    store(node+0x18,0,2);store(node+0x1A,0,2);store(node+7,extra,1)
    for offset in (0,2,4):store(node+0xA+offset,get(values+offset,2),2)
    selector=get(frame+0x58);store(node+0x48,0);store(node+0x17,selector,1)
    slot=get(frame+0x40);store(node+0x16,mode,1);store(node+0x15,slot,1)
    parent=get(frame+0x5C);store(node+0x1E,parent,2);joint=get(frame+0x60)
    store(node+0x13,0,1);store(node+0x4C,0);store(node+0x50,0);store(node+5,0,1)
    store(node+0x22,0,2);store(node+0x20,joint,2)
    if mode==4 or flags&4:
        store(frame+0x24,failed);matrix=call(allocate,(0x80,1,2,2));failed=get(frame+0x24)
        store(node+0x34,matrix)
        if matrix==0:failed=1
    else:store(node+0x34,0)
    duration=get(frame+0x48);store(node+0x1C,duration if duration else 65535,2)
    actor=get(frame+0x30)
    if failed==0:
        store(frame+0x24,failed);value=call(initialize,(node,actor));failed=get(frame+0x24)|value
    if failed:
        call(cleanup,(node,1));return finish(0)
    call(setup,(node,get(frame+0x30)));return finish(node)


class NodeOracle(reset.ResetOracle):
    def __init__(self,words,memory,args=None,phase=0,entry=screen.ENTRY,head=HEAD,
            allocate=ALLOCATE,initialize=INITIALIZE,cleanup=CLEANUP,setup=SETUP,
            first=NODE,second=MATRIX,status=0,plan=0,connected=None,random=99):
        args=args or arguments()
        guest.AttachmentOracle.__init__(self,words,memory,arguments=args,phase=phase,entry=entry,connected=connected)
        self.counts={allocate:4,initialize:2,cleanup:2,setup:2,constructor.screen.ENTRY:4,
            constructor.TYPE0:9,screen.ENTRY:13,**action.WIDTHS}
        self.targets=dict(zip((allocate,initialize,cleanup,setup),(ALLOCATE,INITIALIZE,CLEANUP,SETUP)))
        self.head,self.initial_stack,self.args=head,STACK+phase,args
        self.first,self.second,self.status,self.plan=first,second,status,plan
        self.allocate,self.initialize=allocate,initialize;self.ordinal=0
        self.random=random;self.setup_snapshots=[]
    def record_call(self,target):
        if target==SETUP:self.setup_snapshots.append((self.memory.copy(),self.r[29],tuple(self.r[4:6]),len(self.calls)))
        super().record_call(target)
    def hook(self,target):
        if target==constructor.TYPE0:result=0
        elif target in action.WIDTHS:result=self.random if target==action.RANDOM else 0xBEEF0000+len(self.calls)
        else:
            for where,value,size in actions(self.targets[target],self.ordinal,self.plan,self.initial_stack,self.head,self.args):
                self.put(where,value,size)
            if target==self.allocate:
                result=self.first if self.ordinal==0 else self.second;self.ordinal+=1
            else:result=self.status if target==self.initialize else 0xBEEF1234
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&MASK


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x100}


class GameAnimationNodeConstructorMatchTests(unittest.TestCase):
    maxDiff=None
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-animation-node-constructor-test'
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
        with (cls.out/'before-guards').open(newline='') as f:
            reader=csv.DictReader(f);cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rows=screen.guard_rows(cls.out/'selected.o');cls.guards=cls.out/'qualified-guards.csv'
        cls.write_rows(cls.guards,cls.old_rows+cls.rows);cls.write_rows(cls.out/'isolated.csv',cls.rows)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>152I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/5D2C0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_5D2C0'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.original
        before=(cls.out/'before-elf').read_bytes();assert audit_layout(cls.out/'before-elf',cls.root/'conker')['exact']
        cls.setup=list(struct.unpack_from('>113I',before,elf_slot_offset(before,SETUP,452)))
        assert cls.setup==list(struct.unpack_from('>113I',cls.rom,action.screen.ROM))
        cls.setup_data={}
        for address,size in ((action.screen.TABLE,220),(action.LOW,8)):
            data=before[elf_slot_offset(before,address,size):][:size]
            cls.setup_data.update({address+i:v for i,v in enumerate(data)})
        cls.caller=list(struct.unpack_from('>89I',before,elf_slot_offset(before,constructor.screen.ENTRY,356)))
        assert cls.caller==list(struct.unpack_from('>89I',cls.rom,constructor.screen.ROM))
        cls.stubs={}
        for address in (INITIALIZE,CLEANUP):
            code=list(struct.unpack_from('>3I',before,elf_slot_offset(before,address,12)))
            assert code==[0x00001025,0x03E00008,0];cls.stubs[address]=code
        cls.assets={};rom_start,vram,rom_end,_=load_game_data_layout(cls.root/'conker')
        for animation in (5,6,7,10,11,0x17,0x23,0x44):
            address=constructor.descriptor_address(animation)
            descriptor=before[elf_slot_offset(before,address,8):][:8]
            records=struct.unpack_from('>I',descriptor)[0];count=descriptor[4]
            data=before[elf_slot_offset(before,records,count*16):][:count*16]
            assert descriptor==cls.rom[rom_start+address-vram:][:8]
            assert vram<=records and rom_start+records-vram+len(data)<=rom_end
            assert data==cls.rom[rom_start+records-vram:][:len(data)]
            assert all(data[i*16+3] in (1,2) for i in range(count))
            cls.assets[animation]=(address,descriptor,records,data)
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        symbols=symbols or screen.recovery.SYMBOLS
        script=cls.out/(name+'-link.ld');elf=cls.out/(name+'-link.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>152I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,args=None,forms=None,**settings):
        args=args or arguments();forms=forms or (self.original,self.fitted)
        expected=reference(memory,args,**{k:v for k,v in settings.items() if k!='entry'})
        models=[NodeOracle(w,memory,args,**settings).run() for w in forms]
        for model in models:self.assertEqual((model.memory,model.events,model.calls,model.r[2]),expected)
        return models

    def test_01_complete_checked_recipe_and_publication(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['differences'],
            self.meta['diagnostics']),(152,48,0,47,''))
        self.assertEqual(self.meta['relocations'],screen.RELOCATIONS)
        for index in range(152):
            stale=list(screen.RAW);stale[index]^=1
            with self.assertRaises(ValueError):screen.recipe(stale)
        self.assertTrue(all(r['omit']=='false' and not r['insert_after'] and
            r['expected_relocations']==r['replacement_relocations']=='-' for r in self.rows))
        before=(self.out/'before-guards').read_bytes();path=self.out/'publish-test.csv';path.write_bytes(before)
        screen.append_guards(path,before,self.out/'selected.o');published=path.read_bytes()
        self.assertTrue(published.startswith(before))
        with path.open(newline='') as f:self.assertEqual(list(csv.DictReader(f)),self.old_rows+self.rows)
        with self.assertRaises(ValueError):screen.append_guards(path,before,self.out/'selected.o')
        with self.assertRaises(ValueError):screen.append_guards(path,published,self.out/'selected.o')
        self.receipt('shape',words=152,frame=48,guards=47,insertions=0,omissions=0,pools=0,stale_rejections=152,
            initialization_schedule_not_raw_private_order=True,relocations_untouched=13)

    def test_02_widths_lists_allocations_rollback_and_callback_mutations(self):
        cases=0;coverage=set();raw_cases=0
        for value,axis,listing,phase,plan in itertools.product(range(256),('flags','mode','kind','key','group'),
                (0,1,2),(0,8),(0,1)):
            fields={axis:value} if axis!='group' else {}
            args=arguments(**fields,seed=value);group=value if axis=='group' else 7
            memory=fixture(args,group,listing,value,phase)
            options=dict(phase=phase,plan=plan,first=0 if value%17==0 else NODE,
                second=0 if value%7==0 else MATRIX,status=(0,1,0x80000000,MASK)[value%4])
            models=self.compare(memory,args,**options);coverage.update(models[0].visits);cases+=1
            if listing==0 and phase==0 and plan==0:
                raw=NodeOracle(self.raw,memory,args,**options).run();retail=models[0]
                self.assertEqual((public(raw.memory),raw.calls,raw.r[2]),(public(retail.memory),retail.calls,retail.r[2]))
                raw_cases+=1
        for flags,mode,key,kind,duration,plan in itertools.product(LIMITS,(4,260,0x80000004),
                (9,0x12340009),(0x37,0x12340037),(0,1,0x80000000,0xFFFF0000),range(5)):
            args=arguments(kind=kind,flags=flags,mode=mode,key=key,duration=duration)
            models=self.compare(fixture(args,listing=1),args,plan=plan,status=0)
            coverage.update(models[0].visits);cases+=1
        missing=sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY,screen.ENTRY+608,4))-coverage)
        self.assertEqual(missing,[130])
        self.receipt('guest',cases=cases,executions=cases*2,raw_public_semantic_cases=raw_cases,
            all_flag_mode_kind_key_group_bytes=True,full_word_mode_and_duplicate_comparisons=True,
            first_and_second_allocation_NULL=True,nonzero_status_including_sign_bit=True,
            post_allocate_actor_head_flags_key_payload_changes=True,callback_GP_FPR_clobbered=True,
            retail_words_reached=151,unreachable_compiler_duplicate_store=130,
            independent_full_private_order_on_retail_and_fitted=True)

    def test_03_private_aliases_fired_faults_and_NULL_boundaries(self):
        cases=prefixes=0
        for phase,alias in itertools.product((0,8),range(6)):
            stack=STACK+phase;frame=stack-0x30
            values=(VALUES,NODE+0xA,ACTOR+0x3A,OLD+6,frame+0x24,stack+0x10)[alias]
            args=arguments(flags=12,mode=4,values=values,duration=0xFFFFFFFF)
            memory=fixture(args,listing=1,phase=phase)
            models=self.compare(memory,args,phase=phase,plan=4);cases+=1
            if alias in (2,3):
                raw=NodeOracle(self.raw,memory,args,phase=phase,plan=4).run()
                self.assertEqual((public(raw.memory),raw.calls,raw.r[2]),
                    (public(models[0].memory),models[0].calls,models[0].r[2]))
            for ordinal in range(models[0].accesses):
                failed=[]
                for words in (self.original,self.fitted):
                    model=NodeOracle(words,memory,args,phase=phase,plan=4);model.fault=ordinal
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                for name in ('memory','events','calls','f'):
                    self.assertEqual(getattr(failed[0],name),getattr(failed[1],name))
                prefixes+=1
        args=arguments(values=0)
        for group,listing,first in ((0,0,NODE),(7,1,NODE),(7,0,0)):
            self.compare(fixture(args,group,listing),args,first=first);cases+=1
        for args,expected in ((arguments(actor=0),('unmapped read',0x3B,1)),
                (arguments(values=0),('unmapped read',0,2))):
            failed=[]
            for words in (self.original,self.fitted):
                model=NodeOracle(words,fixture(args),args)
                with self.assertRaises(AssertionError) as caught:model.run()
                self.assertEqual(caught.exception.args,(expected,));failed.append(model)
            self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls),
                (failed[1].memory,failed[1].events,failed[1].calls))
        self.receipt('aliases',cases=cases,executions=cases*2,fired_fault_pairs=prefixes,
            failed_executions=prefixes*2,caller_homes_failure_spill_live_actor_list_and_node_payload=True,
            NULL_payload_short_circuit=True,guest_fault_not_portable_C=True,raw_private_schedule_not_claimed=True)

    def test_04_independent_HI_LO_and_all_four_callback_rebases(self):
        cases=0
        for entry,head,allocate,initialize,cleanup,setup in ((screen.ENTRY,HEAD,ALLOCATE,INITIALIZE,CLEANUP,SETUP),
                (0x15207FFC,0x80117FFC,0x10017FFC,0x15218004,0x15228004,0x15237FFC),
                (0x15308004,0x80118004,0x10028004,0x15317FFC,0x15327FFC,0x15338004)):
            symbols=dict(zip(screen.recovery.SYMBOLS,(head,allocate,initialize,cleanup,setup)))
            forms=tuple(self.link(name,entry,symbols) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[2])
            for flags,mode,listing,status,phase in itertools.product((0,4,8,12),(4,260),(0,1,2),(0,MASK),(0,8)):
                args=arguments(flags=flags,mode=mode)
                settings=dict(entry=entry,head=head,allocate=allocate,initialize=initialize,cleanup=cleanup,setup=setup,
                    status=status,phase=phase)
                models=self.compare(fixture(args,listing=listing,phase=phase,head=head),args,forms=(forms[0],forms[2]),**settings)
                raw=NodeOracle(forms[1],fixture(args,listing=listing,phase=phase,head=head),args,**settings).run()
                self.assertEqual((public(raw.memory),raw.calls,raw.r[2]),
                    (public(models[0].memory),models[0].calls,models[0].r[2]));cases+=1
        self.receipt('rebases',independent_links=9,cases=cases,executions=cases*3,
            signed_LO_carries=True,all_four_callbacks_independent=True,thirteen_argument_ABI=True)

    def test_05_copied_owner_actual_padding_and_unchanged_neighbors(self):
        before=(self.out/'before-source').read_text();objects=[];warnings=[];padded=[]
        for i,(name,source) in enumerate((('owner-before',before),('owner-after',screen.install(before)))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name);objects.append(obj);warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            assembly=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'generated_5D2C0',str(assembly),
                '--word-patches',str(self.out/('before-guards' if i==0 else 'qualified-guards.csv'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),str(assembly)],
                check=True,capture_output=True);padded.append(parse_object(assembly.with_suffix('.o')))
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(screen.guard_rows(objects[1]),self.rows)
        old,new=padded;start=new[1][screen.FUNCTION]['value'];expected=bytearray(old[0])
        expected[start:start+608]=struct.pack('>152I',*screen.recipe(screen.RAW));self.assertEqual(bytes(expected),new[0])
        for name in old[1]:
            if name!=screen.FUNCTION:self.assertEqual(old[1][name],new[1][name])
        self.assertEqual(old[2],{k:v for k,v in new[2].items() if not start<=k<start+608})
        self.receipt('owner',untouched_neighbors=len(old[1])-1,neighbor_extents_bytes_relocations_exact=True,
            pools_exact=True,diagnostics_equal=True,diagnostic_bytes=len(warnings[1]),generated_padding_full_body=True,
            changed_functions=[screen.FUNCTION],helper_stubs_unchanged=True)

    def test_06_effective_semantic_negative_controls(self):
        controls=(('narrow-mode',screen.SELECTED.replace('mode == 4','(u8)mode == 4'),arguments(mode=260),0,0),
            ('narrow-key',screen.SELECTED.replace('key == node[6]','(u8)key == node[6]'),arguments(key=0x12340009),1,0),
            ('narrow-kind',screen.SELECTED.replace('kind == node[1]','(u8)kind == node[1]'),arguments(kind=0x12340037),1,0),
            ('zero-duration',screen.SELECTED.replace('= 0xFFFF;', '= 0;'),arguments(duration=0),0,0),
            ('wrong-payload',screen.SELECTED.replace('= *(u16 *)(values + 4);','= *(u16 *)(values + 2);'),arguments(),0,0),
            ('skip-cleanup',screen.SELECTED.replace('        func_15030158(node, 1);\n',''),arguments(),0,1),
            ('positive-status',screen.SELECTED.replace('if (failed != 0)','if (failed > 0)'),arguments(),0,0x80000000),
            ('wrong-allocation',screen.SELECTED.replace('allocate_memory(0x5C,','allocate_memory(0x58,'),arguments(),0,0))
        for name,body,args,listing,status in controls:
            meta,words=screen.compile_candidate(self.root,self.out,name,body)
            self.assertGreater(meta['differences'],0)
            memory=fixture(args,listing=listing)
            actual=NodeOracle(words,memory,args,status=status).run();expected=NodeOracle(self.original,memory,args,status=status).run()
            self.assertNotEqual((public(actual.memory),actual.calls,actual.r[2]),
                (public(expected.memory),expected.calls,expected.r[2]),name)
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))

    def test_07_native32_optimized_unoptimized_semantic_contract(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        for name,body in (('native-zero-duration',screen.SELECTED.replace('= 0xFFFF;','= 0;')),
                ('native-narrow-mode',screen.SELECTED.replace('mode == 4','(u8)mode == 4'))):
            result,_=self.run_native(name,NATIVE_PREFIX+body+NATIVE_RUNNER)
            self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=264192,executions=528384,profiles=['O2','O0'],
            typed_thirteen_arguments=True,full_node_untouched_gaps_and_live_head_actor_payload=True,
            second_allocation_and_cleanup_gates=True,native_negative_controls=2,disjoint_fresh_allocation_contract=True)

    def test_08_actual_complete_constructor_and_ROM_descriptors(self):
        cases=prefixes=0
        for animation,phase,status,second in itertools.product(self.assets,(0,8),(0,0x80000000),(0,MATRIX)):
            address,descriptor,records,data=self.assets[animation]
            memory=fixture(group=7,phase=phase)
            memory.update(self.setup_data)
            memory.update({action.STATE+i:0xA5 for i in range(0x1C0)});put(memory,ACTOR+0x31C,action.STATE)
            memory.update({address+i:v for i,v in enumerate(descriptor)})
            memory.update({records+i:v for i,v in enumerate(data)})
            models=[]
            for words in (self.original,self.fitted):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({SETUP+i*4:w for i,w in enumerate(self.setup)})
                for target,code in self.stubs.items():connected.update({target+i*4:w for i,w in enumerate(code)})
                model=NodeOracle(self.caller,memory,args=(ACTOR,animation,0x7F812345,0),phase=phase,
                    entry=constructor.screen.ENTRY,connected=connected,status=status,second=second).run();models.append(model)
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].f,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].f,models[1].r[2]))
            self.assertTrue(any(call[0]==screen.ENTRY and len(call)==14 for call in models[0].calls));cases+=1
            if phase==0 and status==0 and second==MATRIX:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.fitted):
                        connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                        connected.update({SETUP+i*4:w for i,w in enumerate(self.setup)})
                        for target,code in self.stubs.items():connected.update({target+i*4:w for i,w in enumerate(code)})
                        model=NodeOracle(self.caller,memory,args=(ACTOR,animation,0x7F812345,0),
                            entry=constructor.screen.ENTRY,connected=connected);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));failed.append(model)
                    self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls,failed[0].f),
                        (failed[1].memory,failed[1].events,failed[1].calls,failed[1].f));prefixes+=1
        self.receipt('connected',ROM_verified_descriptors=8,cases=cases,executions=cases*2,
            actual_89_word_caller=True,actual_113_word_setup_and_owned_jump_tables=True,
            actual_initialize_cleanup_zero_stubs=True,external_action_callbacks_bounded=True,
            fired_fault_pairs=prefixes,failed_executions=prefixes*2,not_complete_deeper_helper_or_gameplay_acceptance=True)

    def test_10_actual_action_consumer_all_kinds_and_independent_public_effects(self):
        cases=0
        for kind,phase,random,counter in itertools.product(range(256),(0,8),(99,0x80000000),(None,0xFFFF)):
            args=arguments(kind=kind,flags=8);memory=fixture(args,phase=phase)
            memory.update(self.setup_data)
            memory.update({action.STATE+i:0xA5 for i in range(0x1C0)})
            put(memory,ACTOR+0x31C,0 if counter is None else action.STATE)
            put(memory,action.STATE+0x1A6,counter or 0,2);put(memory,ACTOR+0x9C,0x80000001)
            models=[]
            for words in (self.original,self.fitted):
                connected={SETUP+i*4:w for i,w in enumerate(self.setup)}
                for target,code in self.stubs.items():connected.update({target+i*4:w for i,w in enumerate(code)})
                model=NodeOracle(words,memory,args,phase=phase,connected=connected,random=random).run();models.append(model)
                self.assertEqual(model.r[2],NODE);self.assertEqual(len(model.setup_snapshots),1)
                snapshot,stack,packet,ordinal=model.setup_snapshots[0]
                expected=action.ActionReference(snapshot);expected.stack=stack;expected.run(*packet,random)
                self.assertEqual(public(model.memory),public(expected.memory))
                self.assertEqual(model.calls[ordinal+1:],expected.calls)
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].f));cases+=1
        self.receipt('action-consumer',cases=cases,executions=cases*2,all_256_action_bytes=True,
            actual_113_word_consumer=True,independent_action_reference=True,owned_jump_tables=True,
            nullable_state_counter_wrap_actor_flag_masks_signed_random=True,external_callbacks_bounded=True)

    def test_09_entire_linked_single_slot_metadata_and_protected_inputs(self):
        source=(self.root/screen.SOURCE).read_text();before=(self.out/'before-elf').read_bytes()
        self.assertEqual(source,(self.out/'before-source').read_text() if screen.recovery.ORIGINAL in source
            else screen.install((self.out/'before-source').read_text()))
        if screen.recovery.ORIGINAL in source:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(before)
        struct.pack_into('>152I',expected,elf_slot_offset(before,screen.ENTRY,608),*self.fitted)
        old,new=metadata(before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:])
        symbol_table=old[4];changes=0
        for offset in range(symbol_table[4],symbol_table[4]+symbol_table[5],symbol_table[9]):
            a,b=SYMBOL.unpack_from(before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:])
                self.assertEqual((a[2],b[2]),(12,608));struct.pack_into('>I',expected,offset+8,b[2]);changes+=1
        self.assertEqual(changes,1);self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        self.assertEqual((self.root/self.paths['guards']).read_bytes()[:len((self.out/'before-guards').read_bytes())],
            (self.out/'before-guards').read_bytes())
        with (self.root/self.paths['guards']).open(newline='') as f:self.assertEqual(list(csv.DictReader(f)),self.old_rows+self.rows)
        for name in ('progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        self.receipt('linked',installed=True,changed_function_count=1,changed_symbol_extents=1,
            all_other_ELF_bytes_exact=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),guard_prefix_exact=True,appended_rows=47,
            data_audit=audit,conversion_rows_unchanged=True)


NATIVE_PREFIX=r'''
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;
typedef short s16;typedef int s32;typedef float f32;
static u32 actorWords[208],nodes[3][24],matrixWords[32];static u16 values[3];
static u8 *D_800C3EE0;
static s32 scenario,ordinal,errors,initCalls,cleanupCalls,setupCalls;
static s32 flagsValue,modeValue,keyValue,kindValue,durationValue;
static u8 groupValue;static u32 expected[24];
static void *allocate_memory(s32 size,s32 a,s32 b,s32 c){
    s32 n=ordinal++;
    if(size!=(n?0x80:0x5C)||a!=1||b!=(n?2:0)||c!=2)errors++;
    if(!n){D_800C3EE0=(u8 *)nodes[2];((u8 *)actorWords)[0x3B]^=128;
        values[0]^=0xFFFF;values[1]^=0x8000;values[2]^=0x1234;
        return scenario==1?0:nodes[0];}
    return scenario==2?0:matrixWords;
}
static s32 func_1502FFD8(u8 *node,u8 *actor){
    initCalls++;if(node!=(u8 *)nodes[0]||actor!=(u8 *)actorWords)errors++;
    *(u32 *)(node+0x24)=0xBEEF1234;
    return scenario==3?(s32)0x80000000u:0;
}
static s32 func_15030158(u8 *node,s32 rollback){
    cleanupCalls++;if(node!=(u8 *)nodes[0]||rollback!=1)errors++;
    node[0x13]=133;return (s32)0xFFFFFFFFu;
}
static void func_15031A50(u8 *node,u8 *actor){
    setupCalls++;if(node!=(u8 *)nodes[0]||actor!=(u8 *)actorWords)errors++;
    *(u32 *)(node+0x3C)=0x80000000u;
}
'''
NATIVE_RUNNER=r'''
static void word(u8 *p,u32 v){*(u32 *)p=v;}
static void half(u8 *p,u16 v){*(u16 *)p=v;}
static s32 qualify(s32 flags,s32 mode,s32 plan){
    s32 i,j,duplicate,matrix,failed;u8 *result,*e=(u8 *)expected,*n=(u8 *)nodes[0];
    scenario=plan;ordinal=errors=initCalls=cleanupCalls=setupCalls=0;
    flagsValue=flags;modeValue=mode;keyValue=(flags&1)?0x12340009:9;
    kindValue=(mode&1)?0x12340037:0x37;durationValue=(mode&2)?(s32)0xFFFF0000u:mode;
    groupValue=(u8)(flags+mode);for(i=0;i<208;i++)actorWords[i]=0xA5A5A5A5u;
    ((u8 *)actorWords)[0x3B]=groupValue;
    for(i=0;i<3;i++)for(j=0;j<24;j++)nodes[i][j]=0xA5A5A5A5u;
    for(j=0;j<24;j++)expected[j]=nodes[0][j];
    D_800C3EE0=(u8 *)nodes[1];((u8 *)nodes[1])[0]=groupValue;
    ((u8 *)nodes[1])[1]=0x37;((u8 *)nodes[1])[6]=9;nodes[1][0x54/4]=0;
    values[0]=0xF123;values[1]=0x8001;values[2]=0xFFFF;
    duplicate=groupValue && !(flags&8) && keyValue==9 && kindValue==0x37;
    matrix=modeValue==4 || (flags&4);failed=(matrix && plan==2)||plan==3;
    result=func_15030AF4((u8 *)actorWords,kindValue,0x123400FF,flags,0x12345678,modeValue,
        durationValue,keyValue,0xABCDEF80,(u8 *)values,-1,0xFFFF8000,0xFFFF0001);
    if(errors)return 1;
    if(!groupValue||duplicate){
        if(result||ordinal||initCalls||cleanupCalls||setupCalls||D_800C3EE0!=(u8 *)nodes[1])return 2;
    }else if(plan==1){
        if(result||ordinal!=1||initCalls||cleanupCalls||setupCalls||D_800C3EE0!=(u8 *)nodes[2])return 3;
    }else{
        if(ordinal!=1+!!matrix||cleanupCalls!=!!failed||setupCalls==!!failed||
            initCalls!=(matrix&&plan==2?0:1)||result!=(failed?0:n)||D_800C3EE0!=n)return 4;
        if(nodes[2][0x58/4]!=(u32)n)return 5;
        e[0]=(u8)(groupValue^128);e[1]=(u8)kindValue;e[2]=255;e[3]=255;e[4]=(u8)flags;
        e[5]=0;e[6]=(u8)keyValue;e[7]=128;e[8]=e[9]=0;
        half(e+0xA,(u16)(0xF123^0xFFFF));half(e+0xC,(u16)(0x8001^0x8000));half(e+0xE,(u16)(0xFFFF^0x1234));
        e[0x13]=failed?133:0;e[0x15]=0x78;e[0x16]=(u8)mode;e[0x17]=255;
        half(e+0x18,0);half(e+0x1A,0);half(e+0x1C,(u16)(durationValue?durationValue:0xFFFF));
        half(e+0x1E,0x8000);half(e+0x20,1);half(e+0x22,0);
        for(i=0x24;i<=0x30;i+=4)word(e+i,0);
        word(e+0x34,matrix?(plan==2?0:(u32)matrixWords):0);word(e+0x38,0);word(e+0x3C,failed?0:0x80000000u);
        word(e+0x40,0x3F800000u);word(e+0x44,0);word(e+0x48,0);word(e+0x4C,0);word(e+0x50,0);
        word(e+0x54,(u32)nodes[2]);word(e+0x58,0);
        if(!(matrix&&plan==2))word(e+0x24,0xBEEF1234);
    }
    for(i=0;i<24;i++)if(nodes[0][i]!=expected[i])return 6;
    if(((u8 *)actorWords)[0x3B]!=(u8)(!groupValue||duplicate?groupValue:groupValue^128))return 7;
    return 0;
}
int run(void){s32 flags,mode,plan,r;
    for(flags=0;flags<256;flags++)for(mode=0;mode<256;mode++)for(plan=0;plan<4;plan++){
        r=qualify(flags,mode==4?260:mode,plan);if(r)return r;}
    for(flags=0;flags<256;flags++)for(plan=0;plan<4;plan++){
        r=qualify(flags,4,plan);if(r)return r;
        r=qualify(flags,(s32)0x80000004u,plan);if(r)return r;}
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
