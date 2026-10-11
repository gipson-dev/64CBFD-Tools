"""Full alternate loader: live attachment/count, NULL-free gates and nested SDK ABI."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_node_alternate_loader_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_node_resource_loader_match as default
from tools.tests import test_game_node_resource_initializer_match as initializer
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout

STACK,MASK=default.STACK,0xFFFFFFFF
ALLOCATE,ZERO,DEFAULT,FREE,ACTION=screen.recovery.SYMBOLS.values()
NODE,NODE2,FIRST,SECOND,OUTPUT=0x60000,0x61000,0x62000,0x63000,0x64000
DISPATCH=0x1505E0C4
COUNTS=(0,1,2,127,128,255,256,0x3FFFFFF,0x4000000,0x80000001,MASK)
STATUSES=(0,1,2,127,0x80000000,MASK)


def arguments(kind=133,selector=128):
    return (kind,selector,OUTPUT,OUTPUT+4,OUTPUT+8,OUTPUT+12,OUTPUT+16)


def homes(memory,args,phase=0):
    for i,value in enumerate(args[4:]):put(memory,STACK+phase+16+i*4,value)
    return memory


def fixture(phase=0):
    memory={}
    for start,size in ((STACK-0x600,0x700),(NODE,0x3F8),(NODE2,0x3F8),(FIRST,256),(SECOND,256),(OUTPUT,64)):
        memory.update({start+i:(i*17+35)&255 for i in range(size)})
    for node in (NODE,NODE2):
        put(memory,node+0x3E8,FIRST);put(memory,node+0x3EC,SECOND)
    return homes(memory,arguments(),phase)


def changes(role,ordinal,plan,attached,frame):
    if role=='allocate' and ordinal==0 and plan==1:return (
        (frame+0x58,OUTPUT+24,4),(frame+0x44,0x8000007F,4))
    if role=='zero' and plan==2:return ((attached,NODE2,4),)
    if role=='default' and plan==3:return ((attached,NODE2,4),(frame+0x44,0xFFFF0080,4))
    if role=='allocate' and ordinal==1 and plan==4:return (
        (frame+0x3C,0x80000001,4),(attached,NODE2,4))
    if role=='allocate' and ordinal==2 and plan==5:return ((attached,NODE2,4),(NODE2+0x3E8,0,4))
    if role=='free' and ordinal==0 and plan==6:return ((attached,NODE2,4),(NODE2+0x3EC,0,4))
    if role=='action' and plan==7:return ((attached,NODE2,4),)
    return ()


def reference(memory,args=None,phase=0,allocation=NODE,first=FIRST,second=SECOND,
        count=2,status=0,plan=0,symbols=None,**unused):
    args=args or arguments();allocate,zero,loader,free,action=(symbols or screen.recovery.SYMBOLS).values()
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x40;attached=args[6]
    def get(address,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped read',address,size)
        value=read(state,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped write',address,size)
        value&=(1<<(size*8))-1;put(state,address,value,size);events.append(('W',address,size,value))
    def call(target,packet,role,ordinal=0):
        events.append(('CALL',target,packet));calls.append((target,*packet))
        if role=='zero':
            for i in range(packet[1]):store(packet[0]+i,0,1)
        elif role=='default':
            _,records,meta,source,transform,extra,amount=packet
            for address,value,size in ((records,default.ARRAY,4),(meta,3,1),(source,default.HEADER+24,4),
                    (transform,0x81548004,4),(extra,0x81238004,4),(amount,count,4)):
                if address:store(address,value,size)
        for address,value,size in changes(role,ordinal,plan,attached,frame):store(address,value,size)
        return (allocation,first,second)[ordinal] if role=='allocate' else status if role=='default' else 0xBEEF1234
    def finish(result):
        for offset in (0x2C,0x24,0x28):get(frame+offset)
        return state,events,calls,result
    store(frame+0x24,0x5A000010);store(frame+0x2C,0xDEAD0000);store(frame+0x28,0x5A000011)
    for offset,value in zip((0x44,0x48,0x4C),args[1:4]):store(frame+offset,value)
    value=call(allocate,(0x3F8,1,2,2),'allocate');attached=get(frame+0x58);store(attached,value)
    if not value:return finish(1)
    call(zero,(get(attached),0x40),'zero');store(get(attached)+0x215,1,1);store(get(attached)+0x45,1,1)
    transform=get(frame+0x54);source=get(frame+0x50);meta=get(frame+0x4C);store(frame+0x10,transform)
    node=get(attached);store(frame+0x18,frame+0x3C);records=get(frame+0x48);store(frame+0x14,node+0x3F0)
    call(loader,(args[0]&MASK,records,meta,source,transform,node+0x3F0,frame+0x3C),'default')
    value=get(frame+0x3C);store(get(attached)+0x3F4,value,1)
    node=get(attached);selector=get(frame+0x44);store(node+0x3F5,selector,1);store(get(attached)+0x3F6,0,1)
    value=call(allocate,((get(frame+0x3C)<<6)&MASK,1,2,2),'allocate',1);store(get(attached)+0x3E8,value)
    value=call(allocate,((get(frame+0x3C)<<6)&MASK,1,2,2),'allocate',2);store(get(attached)+0x3EC,value)
    node=get(attached);first_value=get(node+0x3E8)
    if first_value and get(node+0x3EC):
        store(frame+0x14,0);store(frame+0x10,0);call(action,(node,1,0,0x3F800000,0,0),'action')
        return finish(0)
    ordinal=0
    if not first_value:
        call(free,(first_value,),'free',ordinal);ordinal+=1;node=get(attached)
    second_value=get(node+0x3EC)
    if not second_value:
        call(free,(second_value,),'free',ordinal);ordinal+=1;node=get(attached)
    call(free,(node,),'free',ordinal);return finish(1)


class AlternateOracle(reset.ResetOracle):
    def __init__(self,words,memory,args=None,phase=0,allocation=NODE,first=FIRST,second=SECOND,
            count=2,status=0,plan=0,symbols=None,entry=screen.ENTRY,connected=None,real=False,loader_result=default.HEADER):
        args=args or arguments()
        guest.AttachmentOracle.__init__(self,words,memory,arguments=args,phase=phase,entry=entry,connected=connected)
        self.symbols=symbols or screen.recovery.SYMBOLS
        self.roles=dict(zip(self.symbols.values(),('allocate','zero','default','free','action')))
        self.counts=dict(zip(self.symbols.values(),(4,2,7,1,6)))
        self.counts.update({default.LOAD:6,default.RETAIN:5,default.RELOCATE:2,DISPATCH:12})
        self.args,self.frame,self.attached=args,STACK+phase-0x40,args[6]
        self.results=(allocation,first,second);self.count,self.status,self.plan=count,status,plan
        self.ordinals={};self.real,self.loader_result=real,loader_result;self.snapshots=[]
    def record_call(self,target):
        if target==DEFAULT:
            self.snapshots.append((self.memory.copy(),self.r[29],tuple(self.arguments(7)),len(self.events),
                {i:self.r[i] for i in range(16,23)},self.r[31]))
        super().record_call(target)
    def hook(self,target):
        packet=self.calls[-1][1:];role=self.roles.get(target,'deep')
        key=target if role=='deep' else role
        ordinal=self.ordinals.get(key,0);self.ordinals[key]=ordinal+1
        if role=='zero':
            for i in range(packet[1]):self.put(packet[0]+i,0,1)
        elif role=='default':
            _,records,meta,source,transform,extra,amount=packet
            for address,value,size in ((records,default.ARRAY,4),(meta,3,1),(source,default.HEADER+24,4),
                    (transform,0x81548004,4),(extra,0x81238004,4),(amount,self.count,4)):
                if address:self.put(address,value,size)
        elif target==default.RETAIN:self.put(packet[4],0x60000+ordinal*4,4)
        for address,value,size in changes(role,ordinal,self.plan,self.attached,self.frame):self.put(address,value,size)
        if role=='allocate' and ordinal==0:self.attached=read(self.memory,self.frame+0x58)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=(self.results[ordinal] if role=='allocate' else self.status if role=='default'
            else self.loader_result if target==default.LOAD else 0xBEEF1234)&MASK


class InitializerOracle(initializer.ResourceOracle):
    def __init__(self,*args,attachment_first=FIRST,attachment_second=SECOND,**kwargs):
        super().__init__(*args,**kwargs)
        self.counts.update({ZERO:2,DEFAULT:7,ACTION:6,default.LOAD:6,default.RETAIN:5,
            default.RELOCATE:2,DISPATCH:12})
        self.attachment_results=(NODE,attachment_first,attachment_second);self.attachment_allocations=0
        self.alt_frame=None;self.deep_ordinals={}
    def record_call(self,target):
        if target==screen.ENTRY:self.alt_frame=self.r[29]-0x40
        super().record_call(target)
    def hook(self,target):
        packet=self.calls[-1][1:]
        if target==ALLOCATE and self.r[29]==self.alt_frame:
            result=self.attachment_results[self.attachment_allocations];self.attachment_allocations+=1
        elif target==ZERO:
            for i in range(packet[1]):self.put(packet[0]+i,0,1)
            result=0xBEEF1234
        elif target in (default.LOAD,default.RETAIN,default.RELOCATE,DISPATCH) or target==FREE and self.r[29]==self.alt_frame:
            if target==default.RETAIN:
                ordinal=self.deep_ordinals.get(target,0);self.deep_ordinals[target]=ordinal+1
                self.put(packet[4],0x60000+ordinal*4,4)
            result=default.HEADER if target==default.LOAD else 0xBEEF1234
        else:
            super().hook(target);return
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&MASK


class GameNodeAlternateLoaderMatchTests(unittest.TestCase):
    maxDiff=1800
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-node-alternate-loader-test'
        cls.out.mkdir(exist_ok=True);cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.recovery.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>99I',cls.rom,screen.ROM))
        cls.before=(cls.out/'before-elf').read_bytes();cls.rows=screen.guard_rows(cls.out/'selected.o')
        cls.fields=next(csv.reader((cls.out/'before-guards').read_text().splitlines()))
        cls.write_rows(cls.out/'target-guards.csv',cls.rows)
        cls.full_guards=cls.out/'full-guards.csv';cls.full_guards.write_bytes((cls.out/'before-guards').read_bytes())
        screen.append_guards(cls.full_guards,cls.full_guards.read_bytes(),cls.out/'selected.o')
        body=(cls.root/'conker/asm/6C960.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_6C960',
            word_patches_path=cls.out/'target-guards.csv'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.original
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        script=cls.out/(name+'-link.ld');elf=cls.out/(name+'-link.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%v for v in (symbols or screen.recovery.SYMBOLS).items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>99I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,args=None,forms=None,**settings):
        args=args or arguments();memory=homes(memory.copy(),args,settings.get('phase',0))
        expected=reference(memory,args,**settings);models=[]
        for index,code in enumerate(forms or (self.original,self.raw,self.fitted)):
            model=AlternateOracle(code,memory,args=args,**settings).run();models.append(model)
            events=model.events.copy()
            # Raw IDO saves S1/RA/S0; retail saves S0/RA/S1. Only complete runs normalize this private prefix.
            if index==1:events[0],events[2]=events[2],events[0]
            self.assertEqual((model.memory,events,model.calls,model.r[2]),expected)
        return models
    def test_01_shape_closed_transfer_and_stale_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes'],
            self.meta['diagnostics']),(99,64,24,0,''))
        self.assertEqual(len(self.rows),24);self.assertEqual(len(self.meta['relocations']),9)
        text,functions,relocations=parse_object(self.out/'selected.o');start=functions[screen.FUNCTION]['value']
        for i in range(99):
            changed=list(screen.RAW);changed[i]^=1
            with self.assertRaisesRegex(ValueError,'stale complete'):screen.recipe(changed)
        for offset in screen.RELOCATIONS:
            changed={k:list(v) for k,v in relocations.items()};changed[start+offset]=[('R_MIPS_26','wrong_target')]
            with patch.object(screen,'parse_object',return_value=(text,functions,changed)):
                with self.assertRaisesRegex(ValueError,'stale alternate.*relocations'):screen.guard_rows(self.out/'selected.o')
        with self.assertRaisesRegex(ValueError,'stale alternate.*manifest'):
            screen.append_guards(self.full_guards,b'wrong\n',self.out/'selected.o')
        with self.assertRaisesRegex(ValueError,'already published'):
            screen.append_guards(self.full_guards,self.full_guards.read_bytes(),self.out/'selected.o')
        self.assertTrue(all(r['insert_after']=='' and r['omit']=='false' and r['expected_relocations']=='-' for r in self.rows))
        self.receipt('shape',words=99,frame=64,raw_differences=24,guards=24,relocation_sites=9,
            stale_word_controls=99,stale_relocation_controls=9,insertions_omissions=0,diagnostic_bytes=0,pool_bytes=0)
    def test_02_all_kind_selector_bytes_count_words_statuses_and_NULL_gates(self):
        cases=0;coverage=set()
        for axis,value,phase in itertools.product(('kind','selector'),range(256),(0,8)):
            args=arguments(kind=value) if axis=='kind' else arguments(selector=value)
            models=self.compare(fixture(phase),args,phase=phase);cases+=1;coverage.update(models[0].visits)
        for count,status,first,second,phase in itertools.product(COUNTS,STATUSES,(0,FIRST),(0,SECOND),(0,8)):
            models=self.compare(fixture(phase),phase=phase,count=count,status=status,first=first,second=second)
            cases+=1;coverage.update(models[0].visits)
        for phase,selector in itertools.product((0,8),(0,255,0x80000000,MASK)):
            models=self.compare(fixture(phase),arguments(0x80000000,selector),phase=phase,allocation=0)
            cases+=1;coverage.update(models[0].visits)
        self.assertEqual(set(range(screen.ENTRY,screen.ENTRY+396,4))-coverage,set())
        self.receipt('guest',cases=cases,executions=cases*3,all_99_words_reached=True,
            ignored_full_word_status=True,unsigned_count_shift_wrapping=True,inverted_NULL_free_gates=True,
            first_64_bytes_only_zeroed=True,caller_GP_FPR_clobbered=True,
            raw_complete_state_calls_and_accesses_except_private_save_order=True,
            fitted_complete_ordered_reference=True)
    def test_03_live_mutations_aliases_and_fired_fault_pairs(self):
        cases=prefixes=0
        for plan,first,second,phase in itertools.product(range(8),(0,FIRST),(0,SECOND),(0,8)):
            memory=fixture(phase);models=self.compare(memory,phase=phase,plan=plan,first=first,second=second);cases+=1
            if phase==0:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for code in (self.original,self.fitted):
                        model=AlternateOracle(code,memory,plan=plan,first=first,second=second);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls,failed[0].f),
                        (failed[1].memory,failed[1].events,failed[1].calls,failed[1].f));prefixes+=1
        for which,address in ((2,NODE),(3,NODE+0x3F4),(4,OUTPUT),(5,OUTPUT+8),
                (4,STACK-0xC0),(6,STACK-0x80)):
            args=list(arguments());args[which]=address;self.compare(fixture(),tuple(args));cases+=1
        args=list(arguments());args[6]=OUTPUT;memory=homes(fixture(),args);failed=[]
        for code in (self.original,self.fitted):
            model=AlternateOracle(code,memory,args=args)
            with self.assertRaises(AssertionError):model.run()
            failed.append(model)
        self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls),
            (failed[1].memory,failed[1].events,failed[1].calls));cases+=1
        for allocation in (0,NODE):
            args=list(arguments());args[6]=0;memory=homes(fixture(),args)
            for code in (self.original,self.raw,self.fitted):
                with self.assertRaises(AssertionError):AlternateOracle(code,memory,args=args,allocation=allocation).run()
            cases+=1
        self.receipt('aliases',cases=cases,fired_retail_fitted_fault_pairs=prefixes,failed_executions=prefixes*2,
            raw_private_fault_order_not_claimed=True,live_attached_output_private_homes_count_and_selector=True,
            NULL_free_reloads_and_captured_node=True,required_NULL_attachment_guest_faults=True)
    def test_04_independent_five_callbacks_and_all_nine_JAL_rebases(self):
        cases=0
        for j in range(3):
            symbols={name:0x15410004+j*0x10004+i*0x100 for i,name in enumerate(screen.recovery.SYMBOLS)}
            entry=0x15217FFC+j*0x10004;forms=tuple(self.link(n,entry,symbols) for n in ('original','selected','fitted'))
            for kind,selector,first,second,plan in itertools.product((0,255,MASK),(0,128,MASK),(0,FIRST),(0,SECOND),(0,3,6)):
                self.compare(fixture(),arguments(kind,selector),forms=forms,entry=entry,symbols=symbols,
                    first=first,second=second,plan=plan);cases+=1
        self.receipt('rebases',links=9,cases=cases,executions=cases*3,all_nine_JAL_sites=True,five_independent_callbacks=True)
    def test_05_copied_owner_real_padder_and_three_unchanged_neighbors(self):
        objects=[];padded=[];diagnostics=[];before=(self.out/'before-source').read_text()
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,detail=compile_owner(self.root,self.out,source,name);objects.append(obj);diagnostics.append(detail)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            asm=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_6C960',str(asm),'--word-patches',str(self.full_guards if name=='owner-after' else self.out/'before-guards')],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(asm.with_suffix('.o')))
        self.assertEqual(diagnostics,[[],[]]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        a,b=padded;start=b[1][screen.FUNCTION]['value'];expected=bytearray(a[0]);raw,funcs,_=parse_object(objects[1])
        selected=struct.unpack_from('>99I',raw,funcs[screen.FUNCTION]['value'])
        struct.pack_into('>99I',expected,start,*screen.recipe(selected));self.assertEqual(bytes(expected),b[0])
        for name in a[1]:
            if name!=screen.FUNCTION:self.assertEqual(a[1][name],b[1][name])
        self.assertEqual(a[2],{k:v for k,v in b[2].items() if not start<=k<start+396})
        self.receipt('owner',untouched_neighbors=len(a[1])-1,neighbor_bytes_extents_relocations_exact=True,
            pools_exact=True,diagnostic_bytes=0,actual_padder=True)
    def test_06_effective_fresh_IDO_negative_controls(self):
        controls=(('wrong-clear',screen.SELECTED.replace('bzero(*attached, 0x40)','bzero(*attached, 0x3F8)'),{}),
            ('wrong-flag',screen.SELECTED.replace('[0x215] = 1','[0x215] = 2'),{}),
            ('wrong-size',screen.SELECTED.replace('recordCount << 6','recordCount << 5'),{}),
            ('wrong-count-byte',screen.SELECTED.replace('[0x3F4] = recordCount','[0x3F4] = 0'),{}),
            ('wrong-free-gate',screen.SELECTED.replace('if (*(u8 **)(node + 0x3E8) == 0)',
                'if (*(u8 **)(node + 0x3E8) != 0)'),dict(first=0)),
            ('wrong-action',screen.SELECTED.replace('node, 1, 0, 1.0f','node, 2, 0, 1.0f'),{}),
            ('status-propagated',screen.SELECTED.replace('    func_1502FE10(kind, records, count, source, transform,',
                '    if (func_1502FE10(kind, records, count, source, transform,').replace(
                '(u8 **)(*attached + 0x3F0), &recordCount);','(u8 **)(*attached + 0x3F0), &recordCount)) return 1;'),dict(status=1)))
        for name,body,settings in controls:
            _,words=screen.compile_candidate(self.root,self.out,name,body)
            expected=AlternateOracle(self.original,fixture(),**settings).run();actual=AlternateOracle(words,fixture(),**settings).run()
            self.assertNotEqual((initializer.public(actual.memory),actual.calls,actual.r[2]),
                (initializer.public(expected.memory),expected.calls,expected.r[2]),name)
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))
    def test_07_native32_valid_written_outputs_and_ignored_status(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        body=screen.SELECTED.replace('recordCount << 6','recordCount << 5')
        result,_=self.run_native('native-wrong-size',NATIVE_PREFIX+body+NATIVE_RUNNER);self.assertNotEqual(result,0)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=2048,executions=4096,
            all_selector_bytes_four_NULL_buffer_masks_ignored_nonzero_status=True,effective_negative_controls=1,
            always_written_count=True,unwritten_local_case_excluded=True,bounded_callbacks=True,
            assignment_destination_callback_mutations_guest_only=True)
    def test_08_actual_default_loader_and_action_helper(self):
        loader=list(struct.unpack_from('>114I',self.before,elf_slot_offset(self.before,DEFAULT,456)))
        helper=list(struct.unpack_from('>29I',self.before,elf_slot_offset(self.before,ACTION,116)))
        self.assertEqual(loader,list(struct.unpack_from('>114I',self.rom,default.screen.ROM)))
        self.assertEqual(helper,list(struct.unpack_from('>29I',self.rom,0x6CA68)))
        connected={DEFAULT+i*4:w for i,w in enumerate(loader)}
        connected.update({ACTION+i*4:w for i,w in enumerate(helper)})
        cases=prefixes=0
        for refs,record_count,result,first,second,phase in itertools.product((0,1,255),(0,1,255,0x8000000),
                (0,default.HEADER),(0,FIRST),(0,SECOND),(0,8)):
            memory=fixture(phase);extra=default.fixture(refs=refs,count=2,phase=phase)
            memory.update({a:v for a,v in extra.items() if not STACK-0x600<=a<STACK+0x100})
            homes(memory,arguments(),phase);put(memory,default.HEADER+12,record_count<<4)
            residue=0x80000001;put(memory,STACK+phase-4,residue)
            models=[AlternateOracle(code,memory,phase=phase,connected=connected,real=True,
                loader_result=result,first=first,second=second).run() for code in (self.original,self.fitted)]
            a,b=models;self.assertEqual((a.memory,a.events,a.calls,a.r[2]),(b.memory,b.events,b.calls,b.r[2]))
            snapshot,stack,args,event_index,saved,ra=a.snapshots[0]
            expected=default.reference(snapshot,args,phase=stack-STACK,result=result,saved=saved,return_address=ra)
            start=event_index+1;self.assertEqual(a.events[start:start+len(expected[1])],expected[1])
            written=bool(refs or result);live_count=record_count if written else residue
            self.assertEqual(read(a.memory,NODE+0x3F4,1),live_count&255)
            allocation_calls=[c for c in a.calls if c[0]==ALLOCATE]
            self.assertEqual([c[1] for c in allocation_calls],[0x3F8,(live_count<<6)&MASK,(live_count<<6)&MASK])
            dispatch=[c for c in a.calls if c[0]==DISPATCH]
            self.assertEqual(dispatch,[(DISPATCH,0,0,NODE,0,1,0,128,0x3F800000,0,0,0,0)] if first and second else [])
            if phase==0 and refs==0 and record_count==1 and first and second:
                for ordinal in range(a.accesses):
                    failed=[]
                    for code in (self.original,self.fitted):
                        model=AlternateOracle(code,memory,connected=connected,real=True,loader_result=result);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));failed.append(model)
                    self.assertEqual((failed[0].memory,failed[0].events,failed[0].calls),
                        (failed[1].memory,failed[1].events,failed[1].calls));prefixes+=1
            cases+=1
        self.receipt('connected',cases=cases,executions=cases*2,actual_default_words=114,actual_action_helper_words=29,
            independent_nested_default_ordered_reference=True,full_12_word_dispatch_float_packet=True,
            ignored_real_default_failure_and_guest_stack_residue=True,private_count_never_initialized=True,
            fired_fault_pairs=prefixes,SDK_resource_allocator_and_dispatch_callbacks_bounded=True)
    def test_09_whole_ELF_single_slot_and_protected_inputs(self):
        source=(self.root/screen.SOURCE).read_text();before=self.before
        self.assertEqual(source,(self.out/'before-source').read_text() if screen.recovery.ORIGINAL in source
            else screen.install((self.out/'before-source').read_text()))
        if screen.recovery.ORIGINAL in source:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(before)
        struct.pack_into('>99I',expected,elf_slot_offset(before,screen.ENTRY,396),*self.fitted)
        old,new=metadata(before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:])
        symbols=old[4];changed=0
        for offset in range(symbols[4],symbols[4]+symbols[5],symbols[9]):
            a,b=SYMBOL.unpack_from(before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:]);self.assertEqual((a[2],b[2]),(12,396))
                struct.pack_into('>I',expected,offset+8,b[2]);changed+=1
        self.assertEqual(changed,1);self.assertEqual(bytes(expected),actual)
        self.assertEqual((self.root/self.paths['guards']).read_bytes(),self.full_guards.read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        for name in ('progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        self.receipt('linked',installed=True,changed_function_count=1,changed_symbol_extents=1,all_other_ELF_bytes_exact=True,
            ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),appended_guards=24,old_guard_prefix_exact=True,
            data_audit=audit,conversion_rows_unchanged=True)
    def test_10_actual_initializer_consumes_alternate_loader_outputs(self):
        entry=initializer.screen.ENTRY
        parent=list(struct.unpack_from('>96I',self.before,elf_slot_offset(self.before,entry,384)))
        self.assertEqual(parent,list(struct.unpack_from('>96I',self.rom,initializer.screen.recovery.ROM)))
        loader=list(struct.unpack_from('>114I',self.before,elf_slot_offset(self.before,DEFAULT,456)))
        helper=list(struct.unpack_from('>29I',self.before,elf_slot_offset(self.before,ACTION,116)))
        cases=0
        for refs,selector,flags,actor_flags,first,second,attachment_first,attachment_second,phase in itertools.product(
                (0,1,255),(0,127,128,254),(0,16),(0,8),(0,initializer.DEST1),(0,initializer.DEST2),
                (0,FIRST),(0,SECOND),(0,8)):
            memory=initializer.fixture(selector=selector,flags=flags,actor_flags=actor_flags,phase=phase)
            for addition in (fixture(phase),default.fixture(refs=refs,count=2,phase=phase)):
                memory.update({a:v for a,v in addition.items() if not STACK-0x600<=a<STACK+0x100})
            put(memory,default.HEADER+12,2<<4)
            models=[]
            for body in (self.original,self.fitted):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(body)}
                connected.update({DEFAULT+i*4:w for i,w in enumerate(loader)})
                connected.update({ACTION+i*4:w for i,w in enumerate(helper)})
                models.append(InitializerOracle(parent,memory,phase=phase,connected=connected,first=first,second=second,
                    attachment_first=attachment_first,attachment_second=attachment_second,
                    source=default.HEADER+24,length=16).run())
            a,b=models;self.assertEqual((a.memory,a.events,a.calls,a.r[2]),(b.memory,b.events,b.calls,b.r[2]))
            attachment_failed=not attachment_first or not attachment_second
            copied=not flags&16 and actor_flags==8
            self.assertEqual(a.r[2],int(attachment_failed or copied and (not first or not second)))
            self.assertEqual(read(a.memory,initializer.NODE+0x48),NODE)
            self.assertEqual(read(a.memory,initializer.NODE+0x24),default.ARRAY)
            self.assertEqual(read(a.memory,initializer.NODE+0x14,1),2)
            self.assertEqual(read(a.memory,default.REFS+133,1),(refs+1)&255)
            if a.r[2]==0:
                self.assertEqual(read(a.memory,initializer.NODE+9,1),1)
                for offset,dest in ((0x28,first),(0x2C,second)):
                    self.assertEqual(read(a.memory,initializer.NODE+offset),dest if copied else default.HEADER+24)
                    if copied:self.assertEqual(bytes(a.memory[dest+i] for i in range(16)),
                        bytes(a.memory[default.HEADER+24+i] for i in range(16)))
            cases+=1
        self.receipt('initializer',cases=cases,executions=cases*2,actual_words=[96,99,114,29],
            real_parent_records_count_source_transform_attachment_and_copy_outputs=True,
            signed_selector_bytes_and_cached_reference_rollover=True,
            attachment_buffer_parent_buffer_failure_paths=True,bounded_deeper_callbacks=True)


NATIVE_PREFIX=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
static u32 storage[254],alternate[254],outputs[8],firstBuffer[64],secondBuffer[64];
static s32 allocationIndex,missingFirst,missingSecond,nonzeroStatus,plan,callCount;
static u32 amount;static u8 **attachedHome;static u32 *countHome;
struct Call {u32 target,args[7];};static struct Call calls[8],expectedCalls[8];
static u32 expectedStorage[254],expectedAlternate[254],expectedOutputs[8];static s32 expectedCount;
static s32 report(u32 a,u32 b,u32 c){
    u32 data[3]={a,b,c};s32 result;
    __asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");
    return 1;
}
static void record(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g){
    struct Call *call=&calls[callCount++];call->target=target;call->args[0]=a;call->args[1]=b;
    call->args[2]=c;call->args[3]=d;call->args[4]=e;call->args[5]=f;call->args[6]=g;
}
static void *allocate_memory(s32 size,s32 a,s32 b,s32 c){
    s32 ordinal=allocationIndex++;record(1,(u32)size,(u32)a,(u32)b,(u32)c,0,0,0);
    if(ordinal==0)return storage;
    if(ordinal==1&&plan==1)*countHome=0x80000001u;
    return ordinal==1?(missingFirst?0:firstBuffer):(missingSecond?0:secondBuffer);
}
static void bzero(void *p,u32 size){u32 i;record(2,(u32)p,size,0,0,0,0,0);for(i=0;i<size;i++)((u8 *)p)[i]=0;}
static s32 func_1502FE10(s32 k,u8 **r,u8 *c,u8 **s,u8 **t,u8 **e,u32 *n){
    record(3,(u32)k,(u32)r,(u32)c,(u32)s,(u32)t,(u32)e,0);
    *r=(u8 *)0x50028;*c=3;*s=(u8 *)0x50018;*t=(u8 *)0x81548004u;
    *e=(u8 *)0x81238004u;*n=amount;countHome=n;return nonzeroStatus?-1:0;
}
static void func_10004074(void *p){record(4,(u32)p,0,0,0,0,0,0);}
static s32 func_1503F5B8(u8 *p,s32 a,s32 b,f32 c,f32 d,s32 e){
    union {f32 f;u32 u;} x,y;x.f=c;y.f=d;record(5,(u32)p,(u32)a,(u32)b,x.u,y.u,(u32)e,0);return -1;
}
'''
NATIVE_RUNNER=r'''
static s32 independent(s32 kind,s32 selector,u8 **records,u8 *count,u8 **source,u8 **transform,u8 **attached){
    u32 recordCount;u8 *node,*a,*b;
    *attached=allocate_memory(1016,1,2,2);if(!*attached)return 1;
    bzero(*attached,64);(*attached)[533]=1;(*attached)[69]=1;
    func_1502FE10(kind,records,count,source,transform,(u8 **)(*attached+1008),&recordCount);
    (*attached)[1012]=(u8)recordCount;(*attached)[1013]=(u8)selector;(*attached)[1014]=0;
    a=allocate_memory(recordCount*64u,1,2,2);*(u8 **)(*attached+1000)=a;
    b=allocate_memory(recordCount*64u,1,2,2);*(u8 **)(*attached+1004)=b;node=*attached;
    if(*(u8 **)(node+1000)&&*(u8 **)(node+1004)){func_1503F5B8(node,1,0,1.0f,0.0f,0);return 0;}
    if(!*(u8 **)(node+1000)){func_10004074(0);node=*attached;}
    if(!*(u8 **)(node+1004)){func_10004074(0);node=*attached;}
    func_10004074(node);return 1;
}
static void setup(s32 selector,s32 missing,s32 status,s32 scenario){
    s32 i;allocationIndex=callCount=0;missingFirst=missing&1;missingSecond=missing&2;
    nonzeroStatus=status;plan=scenario;amount=selector&1?0x80000001u:257;
    for(i=0;i<254;i++)storage[i]=alternate[i]=0xA5A5A5A5u;
    storage[250]=alternate[250]=(u32)firstBuffer;storage[251]=alternate[251]=(u32)secondBuffer;
    for(i=0;i<8;i++)outputs[i]=0xA5A5A5A5u;
    attachedHome=(u8 **)&outputs[4];
}
int run(void){
    s32 selector,missing,status,scenario,a,b,i,j;
    for(selector=0;selector<256;selector++)for(missing=0;missing<4;missing++)for(status=0;status<2;status++){
        scenario=selector&1;setup(selector,missing,status,scenario);
        a=independent(133,selector,(u8 **)&outputs[0],(u8 *)&outputs[1],(u8 **)&outputs[2],(u8 **)&outputs[3],attachedHome);
        expectedCount=callCount;for(i=0;i<callCount;i++)expectedCalls[i]=calls[i];
        for(i=0;i<254;i++){expectedStorage[i]=storage[i];expectedAlternate[i]=alternate[i];}
        for(i=0;i<8;i++)expectedOutputs[i]=outputs[i];
        setup(selector,missing,status,scenario);
        b=func_1503F62C(133,selector,(u8 **)&outputs[0],(u8 *)&outputs[1],(u8 **)&outputs[2],(u8 **)&outputs[3],attachedHome);
        if(a!=b||expectedCount!=callCount)return report((u32)selector,(u32)a,(u32)b);
        for(i=0;i<callCount;i++){if(expectedCalls[i].target!=calls[i].target)return 2;
            for(j=0;j<7;j++)if(expectedCalls[i].args[j]!=calls[i].args[j])return 3;}
        for(i=0;i<254;i++)if(expectedStorage[i]!=storage[i]||expectedAlternate[i]!=alternate[i])return 4;
        for(i=0;i<8;i++)if(expectedOutputs[i]!=outputs[i])return 5;
    }
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
