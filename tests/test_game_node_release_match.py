"""Complete lifetime release: ordered semantic proof, actual callers and linked-only audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_node_release_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_channel_reset_match as reset
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_node_cleanup_match as cleanup
from tools.tests import test_game_node_resource_initializer_match as resource
from tools.tests import test_game_animation_node_constructor_match as factory
from tools.tests import test_game_node_action_match as action
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.patch_generated_slice_ld import load_game_data_layout

STACK,NODE,ACTOR,MASK=factory.STACK,factory.NODE,factory.ACTOR,0xFFFFFFFF
HEAD,DISPATCH,FREE,QUEUE,ATTACH,RESOURCE=screen.recovery.SYMBOLS.values()
PREVIOUS,NEXT,ALT_PREVIOUS,ALT_NEXT,BUFFER,ALT_BUFFER=0x32000,0x33000,0x44000,0x45000,0x46000,0x47000
POINTERS=(0x28,0x2C,0x34,0x44,0x48,0x4C,0x50)
LIMITS=(0,1,2,256,0x80000000,0xFFFF0000,MASK)


def fixture(initialized=1,copied=1,kind=133,pointers=127,listing=1,phase=0,head=HEAD,node=NODE):
    memory=resource.fixture(phase=phase)
    for start,size in ((node,0x60),(PREVIOUS,0x60),(NEXT,0x60),(ALT_PREVIOUS,0x60),(ALT_NEXT,0x60)):
        for i in range(size):memory.setdefault(start+i,(i*17+35)&255)
    for i in range(4):memory.setdefault(head+i,0xA5)
    for address,value,size in ((node+9,initialized,1),(node+8,copied,1),(node+1,kind,1),(node+6,0,1),
            (node+0x54,NEXT if listing in (1,2) else 0,4),
            (node+0x58,PREVIOUS if listing in (2,3) else 0,4),(head,node if listing in (0,1) else PREVIOUS,4)):
        put(memory,address,value,size)
    for i,offset in enumerate(POINTERS):put(memory,node+offset,BUFFER+i*0x100 if pointers>>i&1 else 0)
    return memory


def changes(role,ordinal,plan,node,frame,head):
    if role=='dispatch' and plan==1:return ((node+9,0,1),(node+8,0,1),(node+0x34,ALT_BUFFER,4))
    if role in ('free','queue') and ordinal==0 and plan==2:return ((node+0x2C,ALT_BUFFER,4),)
    if role=='attach' and plan==3:return ((node+1,255,1),)
    if role=='resource' and plan==4:return ((node+0x34,ALT_BUFFER,4),(node+0x44,0,4),
        (node+0x54,ALT_NEXT,4),(node+0x58,ALT_PREVIOUS,4),(head,NEXT,4))
    if role in ('free','queue') and ordinal==0 and plan==5:return ((frame+0x24,0,4),(node+0x2C,0,4))
    if role=='dispatch' and plan==6:return ((frame+0x24,0x80000000,4),(node+9,1,1),(node+8,1,1))
    return ()


def reference(memory,node=NODE,immediate=1,phase=0,plan=0,entry=screen.ENTRY,symbols=None,
        saved_s0=0x5A000010,return_address=0xDEAD0000):
    state,events,calls=memory.copy(),[],[];frame=STACK+phase-0x20
    head,dispatch,free,queue,attach,resource=(symbols or screen.recovery.SYMBOLS).values();counts={}
    def get(address,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped read',address,size)
        value=read(state,address,size);events.append(('R',address,size,value));return value
    def store(address,value,size=4):
        address&=MASK;assert all(address+i in state for i in range(size)),('reference unmapped write',address,size)
        value&=(1<<(size*8))-1;put(state,address,value,size);events.append(('W',address,size,value))
    def call(target,args,role):
        ordinal=counts.get(role,0);counts[role]=ordinal+1
        events.append(('CALL',target,args));calls.append((target,*args))
        for address,value,size in changes(role,ordinal,plan,node,frame,head):store(address,value,size)
        return (0xBEEF0000+len(calls))&MASK
    store(frame+0x18,saved_s0);store(frame+0x1C,return_address);store(frame+0x24,immediate)
    if not get(frame+0x24):call(dispatch,(node,),'dispatch')
    initialized=get(node+9,1)
    if initialized:
        copied=get(node+8,1);live_immediate=get(frame+0x24)
        if copied:
            target,role=(free,'free') if live_immediate else (queue,'queue')
            for offset in (0x28,0x2C):
                pointer=get(node+offset);call(target,(pointer,) if live_immediate else (pointer,4),role)
        pointer=get(node+0x48)
        if pointer:call(attach,(pointer,),'attach')
        call(resource,(get(node+1,1),),'resource')
    pointer=get(node+0x34);live_immediate=get(frame+0x24)
    if pointer:call(free if live_immediate else queue,(pointer,) if live_immediate else (pointer,4),
        'free' if live_immediate else 'queue')
    pointer=get(node+0x44)
    if pointer:call(free,(pointer,),'free')
    for offset in (0x4C,0x50):
        pointer=get(node+offset);live_immediate=get(frame+0x24)
        if pointer:call(free if live_immediate else queue,(pointer,) if live_immediate else (pointer,4),
            'free' if live_immediate else 'queue')
    if node==get(head):store(head,get(node+0x54))
    previous=get(node+0x58)
    if previous:store(previous+0x54,get(node+0x54))
    following=get(node+0x54)
    if following:store(following+0x58,get(node+0x58))
    result=call(free,(node,),'free');get(frame+0x1C);get(frame+0x18)
    return state,events,calls,result


class ReleaseOracle(reset.ResetOracle):
    def __init__(self,words,memory,node=NODE,immediate=1,phase=0,plan=0,entry=screen.ENTRY,symbols=None,
            connected=None,resolved=ACTOR,cleanup_mode=0):
        guest.AttachmentOracle.__init__(self,words,memory,arguments=(node,immediate),phase=phase,entry=entry,connected=connected)
        self.head,*targets=(symbols or screen.recovery.SYMBOLS).values()
        self.targets=dict(zip(targets,('dispatch','free','queue','attach','resource')))
        self.counts={target:2 if role=='queue' else 1 for target,role in self.targets.items()}
        self.counts.update(cleanup.WIDTHS)
        self.node,self.frame,self.plan=node,STACK+phase-0x20,plan;self.ordinals={}
        self.resolved,self.cleanup_mode=resolved,cleanup_mode;self.dispatch_stack=None;self.snapshots=[]
        self.capture=bool(connected)
    def record_call(self,target):
        if self.capture and target in self.targets and len(self.snapshots)<2:
            self.snapshots.append((self.memory.copy(),self.r[29],target,len(self.calls)))
        if target==DISPATCH:self.dispatch_stack=self.r[29]
        if target in cleanup.PACKETS:
            args=self.arguments(self.counts[target]);packet=args[cleanup.PACKETS[target]]
            contents=(self.get(packet,4),self.get(packet+4,1))
            self.calls.append((target,*args,*contents));self.events.append(('CALL',target,(*args,*contents)))
        else:super().record_call(target)
    def hook(self,target):
        if target in self.targets:
            role=self.targets[target];ordinal=self.ordinals.get(role,0);self.ordinals[role]=ordinal+1
            for address,value,size in changes(role,ordinal,self.plan,self.node,self.frame,self.head):self.put(address,value,size)
            result=0xBEEF0000+len(self.calls)
        else:
            for address,value,size in cleanup.mutations(self.cleanup_mode,target,self.dispatch_stack):self.put(address,value,size)
            result=self.resolved if target==cleanup.LOOKUP else 0xBEEF0000+len(self.calls)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&MASK


class FactoryReleaseOracle(resource.ConnectedOracle):
    def __init__(self,*args,scenario=0,**kwargs):
        super().__init__(*args,resource_first=0 if scenario==3 else resource.DEST1,
            resource_second=0 if scenario==4 else resource.DEST2,
            resource_status=0x80000000 if scenario==2 else 0,**kwargs)
        self.scenario=scenario;self.in_release=False;self.release_snapshots=[];self.release_base=0
        self.counts.update({DISPATCH:1,QUEUE:2,ATTACH:1,RESOURCE:1,**cleanup.WIDTHS})
    def record_call(self,target):
        if target==screen.ENTRY:
            self.node,self.actor=self.r[4:6];self.frame=self.r[29]-0x20
            self.release_snapshots.append((self.memory.copy(),self.r[29],tuple(self.r[4:6]),
                len(self.calls),self.r[16],self.r[31]))
            self.release_base=len(self.calls)+1;self.in_release=True
        super().record_call(target)
    def hook(self,target):
        if self.in_release and target in (FREE,QUEUE,ATTACH,RESOURCE):
            result=0xBEEF0000+len(self.calls)-self.release_base
        elif target==resource.ALLOCATE and not self.loading and (
                self.scenario==5 and self.calls[-1][1]==0x5C or self.scenario==1 and self.calls[-1][1]==0x80):
            result=0
        else:
            super().hook(target);return
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&MASK


class GameNodeReleaseMatchTests(unittest.TestCase):
    maxDiff=1800
    assemble=classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(guest.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_native=native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-node-release-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.recovery.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        with (cls.out/'before-guards').open(newline='') as f:reader=csv.DictReader(f);cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected');cls.rows=screen.guard_rows(cls.out/'selected.o')
        cls.write_rows(cls.out/'qualified-guards.csv',cls.old_rows+cls.rows);cls.write_rows(cls.out/'isolated.csv',cls.rows)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.original=list(struct.unpack_from('>102I',cls.rom,screen.ROM))
        body=(cls.root/'conker/asm/5D2C0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        slot=cls.out/'slot.s';slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_5D2C0'))
        cls.fitted=cls.link('fitted');assert cls.fitted==cls.original
        cls.before=(cls.out/'before-elf').read_bytes();assert audit_layout(cls.out/'before-elf',cls.root/'conker')['exact']
    @classmethod
    def link(cls,name,entry=screen.ENTRY,symbols=None):
        script=cls.out/(name+'-link.ld');elf=cls.out/(name+'-link.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in (symbols or screen.recovery.SYMBOLS).items()],
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>102I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,**settings):
        expected=reference(memory,**settings);models=[]
        for words in forms or (self.original,self.raw,self.fitted):
            model=ReleaseOracle(words,memory,**settings).run();models.append(model)
            self.assertEqual({a:(v,expected[0].get(a)) for a,v in model.memory.items() if v!=expected[0].get(a)}, {})
            self.assertEqual((model.events,model.calls,model.r[2]),expected[1:])
        return models

    def test_01_complete_transfer_stale_object_and_prefix_publication(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['differences'],
            self.meta['diagnostics']),(102,32,0,5,''));self.assertEqual(self.meta['relocations'],screen.RELOCATIONS)
        for index in range(102):
            stale=list(screen.RAW);stale[index]^=1
            with self.assertRaises(ValueError):screen.recipe(stale)
        text,functions,relocations=parse_object(self.out/'selected.o')
        for offset in screen.RELOCATIONS:
            wrong=dict(relocations);wrong[offset]=[(relocations[offset][0][0],'stale_symbol')]
            with patch.object(screen,'parse_object',return_value=(text,functions,wrong)):
                with self.assertRaises(ValueError):screen.guard_rows(self.out/'selected.o')
        self.assertTrue(all(r['omit']=='false' and not r['insert_after'] and
            r['expected_relocations']==r['replacement_relocations']=='-' for r in self.rows))
        before=(self.out/'before-guards').read_bytes();path=self.out/'publish-test.csv';path.write_bytes(before)
        screen.append_guards(path,before,self.out/'selected.o');self.assertTrue(path.read_bytes().startswith(before))
        with path.open(newline='') as f:self.assertEqual(list(csv.DictReader(f)),self.old_rows+self.rows)
        with self.assertRaises(ValueError):screen.append_guards(path,before,self.out/'selected.o')
        with self.assertRaises(ValueError):screen.append_guards(path,path.read_bytes(),self.out/'selected.o')
        self.receipt('shape',words=102,frame=32,guards=5,insertions=0,omissions=0,pools=0,
            stale_words_rejected=102,stale_relocations_rejected=17,memory_order_unchanged=True)

    def test_02_all_bytes_full_word_modes_nullable_fields_lists_and_coverage(self):
        cases=0;coverage=set()
        for value,axis,immediate,phase in itertools.product(range(256),('initialized','copied','kind'),
                (0,1,256,0x80000000,MASK),(0,8)):
            memory=fixture(**{axis:value},phase=phase)
            models=self.compare(memory,immediate=immediate,phase=phase);coverage.update(models[0].visits);cases+=1
        for pointers,initialized,copied,immediate,listing in itertools.product(range(128),(0,1),(0,1),(0,256),range(4)):
            models=self.compare(fixture(initialized,copied,pointers=pointers,listing=listing),immediate=immediate)
            coverage.update(models[0].visits);cases+=1
        missing=sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY,screen.ENTRY+408,4))-coverage)
        self.assertEqual(missing,[])
        self.receipt('guest',cases=cases,executions=cases*3,raw_retail_fitted_full_order=True,
            all_flag_kind_bytes=True,full_word_nonzero_immediate=True,all_seven_pointer_NULL_masks=True,
            isolated_head_middle_tail_list_shapes=True,all_102_words_reached=True,caller_saved_registers_FPRs_clobbered=True)

    def test_03_live_mutations_private_aliases_and_fired_fault_prefixes(self):
        cases=prefixes=0
        for phase,plan,immediate,initialized,copied in itertools.product((0,8),range(7),(0,1),(0,1),(0,1)):
            memory=fixture(initialized,copied,phase=phase,listing=2)
            models=self.compare(memory,phase=phase,plan=plan,immediate=immediate);cases+=1
            if phase==0 and initialized and copied:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for words in (self.original,self.raw,self.fitted):
                        model=ReleaseOracle(words,memory,plan=plan,immediate=immediate);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    for model in failed[1:]:
                        self.assertEqual((model.memory,model.events,model.calls,model.f),
                            (failed[0].memory,failed[0].events,failed[0].calls,failed[0].f))
                    prefixes+=1
        for head,node,listing in itertools.product((HEAD,NODE+0x54,NODE+0x58),(NODE,STACK-0x80),range(4)):
            symbols=dict(screen.recovery.SYMBOLS);symbols['D_800C3EE0']=head
            forms=tuple(self.link(name,screen.ENTRY,symbols) for name in ('original','selected','fitted'))
            self.compare(fixture(node=node,head=head,listing=listing),forms=forms,node=node,symbols=symbols);cases+=1
        for words in (self.original,self.raw,self.fitted):
            model=ReleaseOracle(words,fixture(),node=0)
            with self.assertRaises(AssertionError) as caught:model.run()
            self.assertEqual(caught.exception.args,(('unmapped read',9,1),))
        self.receipt('aliases',cases=cases,fired_fault_triples=prefixes,failed_executions=prefixes*3,
            live_flags_pair_second_pointer_attachment_kind_auxiliaries_head_links=True,
            immediate_private_home_reloads=True,overlapping_head_node_links_and_private_node=True,
            NULL_node_required_read=True,guest_faults_not_portable_C_or_actual_free_lifetime=True)

    def test_04_independent_head_signed_LO_and_all_five_callback_rebases(self):
        cases=0
        for entry,addresses in ((screen.ENTRY,tuple(screen.recovery.SYMBOLS.values())),
                (0x15207FFC,(0x80117FFC,0x15218004,0x10017FFC,0x10028004,0x15228004,0x15237FFC)),
                (0x15308004,(0x80118004,0x15317FFC,0x10028004,0x10037FFC,0x15328004,0x15338004))):
            symbols=dict(zip(screen.recovery.SYMBOLS,addresses));head=addresses[0]
            forms=tuple(self.link(name,entry,symbols) for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[2])
            for immediate,initialized,copied,listing,pointers in itertools.product(LIMITS,(0,1),(0,1),range(4),(0,127)):
                self.compare(fixture(initialized,copied,pointers=pointers,listing=listing,head=head),forms=forms,
                    immediate=immediate,entry=entry,symbols=symbols);cases+=1
        self.receipt('rebases',links=9,cases=cases,executions=cases*3,head_HI_LO_signed_carries=True,
            all_five_callbacks_fifteen_JAL_sites=True)

    def test_05_copied_owner_real_padding_pools_and_unchanged_neighbors(self):
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
        expected[start:start+408]=struct.pack('>102I',*screen.recipe(screen.RAW));self.assertEqual(bytes(expected),new[0])
        for name in old[1]:
            if name!=screen.FUNCTION:self.assertEqual(old[1][name],new[1][name])
        self.assertEqual(old[2],{k:v for k,v in new[2].items() if not start<=k<start+408})
        self.receipt('owner',untouched_neighbors=len(old[1])-1,neighbor_bytes_extents_relocations_exact=True,
            pools_exact=True,diagnostics_equal=True,diagnostic_bytes=len(warnings[1]),actual_padder=True,
            void_return_matches_ignored_caller_contract=True)

    def test_06_effective_fresh_IDO_semantic_negative_controls(self):
        controls=(('narrow-immediate',screen.SELECTED.replace('s32 immediate','u8 immediate'),{},dict(immediate=256)),
            ('only-one-immediate',screen.SELECTED.replace('immediate != 0','immediate == 1'),{},dict(immediate=0x80000000)),
            ('signed-kind',screen.SELECTED.replace('func_1518CA04(node[1])','func_1518CA04((s8)node[1])'),dict(kind=255),{}),
            ('skip-dispatch',screen.SELECTED.replace('        func_15031C14(node);\n',''),{},dict(immediate=0)),
            ('wrong-queue',screen.SELECTED.replace(', 4)',', 3)'),{},dict(immediate=0)),
            ('wrong-pair',screen.SELECTED.replace('func_10004074(*(u8 **)(node + 0x2C))','func_10004074(*(u8 **)(node + 0x28))'),{},{}),
            ('wrong-aux-mode',screen.SELECTED.replace('''    if (*(u8 **)(node + 0x44) != 0) {
        func_10004074(*(u8 **)(node + 0x44));''','''    if (*(u8 **)(node + 0x44) != 0) {
        func_100043B4(*(u8 **)(node + 0x44), 4);'''),{},dict(immediate=0)),
            ('skip-node-free',screen.SELECTED.replace('    func_10004074(node);\n',''),{},{}),
            ('wrong-prev-link',screen.SELECTED.replace('node + 0x58) + 0x54','node + 0x58) + 0x58'),dict(listing=2),{}),
            ('wrong-next-link',screen.SELECTED.replace('node + 0x54) + 0x58','node + 0x54) + 0x54'),dict(listing=2),{}))
        for name,body,inputs,settings in controls:
            meta,words=screen.compile_candidate(self.root,self.out,name,body);self.assertGreater(meta['differences'],0)
            memory=fixture(**inputs);actual=ReleaseOracle(words,memory,**settings).run()
            expected=ReleaseOracle(self.original,memory,**settings).run()
            self.assertNotEqual((factory.public(actual.memory),actual.calls),
                (factory.public(expected.memory),expected.calls),name)
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))

    def test_07_native32_optimized_unoptimized_complete_public_contract(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        for name,body in (('native-narrow',screen.SELECTED.replace('s32 immediate','u8 immediate')),
                ('native-wrong-queue',screen.SELECTED.replace(', 4)',', 3)')),
                ('native-skip-node',screen.SELECTED.replace('    func_10004074(node);\n',''))):
            result,_=self.run_native(name,NATIVE_PREFIX+body+NATIVE_RUNNER);self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=48640,executions=97280,profiles=['O2','O0'],
            effective_native_negative_controls=3,all_flag_kind_bytes_and_pointer_masks=True,
            full_word_immediate_modes=True,independent_release_reference_and_complete_nodes_head_call_packets=True,
            live_callback_mutations=True,bounded_release_receipts_not_real_allocator_lifetimes=True)

    def test_08_actual_cleanup_dispatcher_all_kinds_keys_and_owned_table(self):
        before=self.before
        words=list(struct.unpack_from('>134I',before,elf_slot_offset(before,DISPATCH,536)))
        self.assertEqual(words,list(struct.unpack_from('>134I',self.rom,cleanup.screen.ROM)))
        table=cleanup.screen.TABLE;pool=before[elf_slot_offset(before,table,192):][:192]
        start,base,_,_=load_game_data_layout(self.root/'conker')
        self.assertEqual(pool,self.rom[start+table-base:][:192])
        connected={DISPATCH+i*4:w for i,w in enumerate(words)};cases=prefixes=0
        for kind,key,counter,resolved in itertools.product(range(256),cleanup.KEYS,(None,0xAA,0xFFFF),(0,ACTOR)):
            memory=fixture(kind=kind,pointers=0);put(memory,NODE+6,key,1)
            memory.update({table+i:value for i,value in enumerate(pool)})
            for address,size in ((ACTOR,0x340),(cleanup.ALT_ACTOR,0x340),(cleanup.STATE,0x1C0)):
                for i in range(size):memory.setdefault(address+i,0xA5)
            put(memory,ACTOR+0x31C,0 if counter is None else cleanup.STATE)
            put(memory,cleanup.STATE+0x1A6,counter or 0,2);put(memory,ACTOR+0x9C,MASK)
            models=[]
            for code in (self.original,self.raw,self.fitted):
                model=ReleaseOracle(code,memory,immediate=0,connected=connected,resolved=resolved).run();models.append(model)
                snapshot,stack,_,_=model.snapshots[0]
                expected=cleanup.CleanupReference(snapshot);expected.stack=stack;expected.run(NODE,resolved)
                after=next((s,index) for s,_,target,index in model.snapshots[1:] if target in (FREE,QUEUE,ATTACH,RESOURCE))
                self.assertEqual(factory.public(after[0]),factory.public(expected.memory))
                self.assertEqual(model.calls[1:after[1]],expected.calls)
            for model in models[1:]:
                self.assertEqual((model.memory,model.events,model.calls,model.f,model.r[2]),
                    (models[0].memory,models[0].events,models[0].calls,models[0].f,models[0].r[2]))
            if kind in (0x37,0x49,0x5A,0x5D,0x90) and key==0x89 and counter==0xFFFF and resolved:
                for ordinal in range(models[0].accesses):
                    failed=[]
                    for code in (self.original,self.raw,self.fitted):
                        model=ReleaseOracle(code,memory,immediate=0,connected=connected);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed.append(model)
                    for model in failed[1:]:
                        self.assertEqual((model.memory,model.events,model.calls,model.f),
                            (failed[0].memory,failed[0].events,failed[0].calls,failed[0].f))
                    prefixes+=1
            cases+=1
        self.receipt('dispatcher',cases=cases,executions=cases*3,actual_134_word_dispatcher=True,
            original_48_entry_table_ROM_verified=True,all_256_kinds_cleanup_keys_nullable_actor_and_counter_states=True,
            independent_cleanup_public_memory_calls=True,fired_fault_triples=prefixes,failed_executions=prefixes*3,
            external_dispatcher_release_callbacks_bounded=True)

    def test_10_actual_factory_full_initializer_allocation_and_loader_failure_chain(self):
        before=self.before
        def words(address,count):return list(struct.unpack_from('>%dI'%count,before,elf_slot_offset(before,address,count*4)))
        factory_words=words(factory.screen.ENTRY,152);initializer=words(resource.screen.ENTRY,96)
        setup=words(factory.SETUP,113)
        self.assertEqual(factory_words,list(struct.unpack_from('>152I',self.rom,factory.screen.ROM)))
        self.assertEqual(initializer,list(struct.unpack_from('>96I',self.rom,resource.screen.ROM)))
        self.assertEqual(setup,list(struct.unpack_from('>113I',self.rom,action.screen.ROM)))
        setup_data={}
        for address,size in ((action.screen.TABLE,220),(action.LOW,8)):
            data=before[elf_slot_offset(before,address,size):][:size]
            setup_data.update({address+i:v for i,v in enumerate(data)})
        cases=prefixes=0
        for flags,selector,phase,scenario in itertools.product((8,12),(128,255),(0,8),range(6)):
            args=factory.arguments(flags=flags);args=(*args[:10],selector,*args[11:])
            memory=resource.fixture(phase=phase);memory.update(setup_data)
            put(memory,ACTOR+0x3B,7,1);put(memory,ACTOR+0x66,8,1);put(memory,HEAD,0)
            memory.update({address+i:0xA5 for address,size in ((0x51000,0x80),(0x61000,0x80),(action.STATE,0x1C0))
                for i in range(size)});put(memory,ACTOR+0x31C,action.STATE)
            def make(code):
                connected={}
                for entry,body in ((screen.ENTRY,code),(resource.screen.ENTRY,initializer),(factory.SETUP,setup)):
                    connected.update({entry+i*4:w for i,w in enumerate(body)})
                return FactoryReleaseOracle(factory_words,memory,args=args,phase=phase,entry=factory.screen.ENTRY,
                    connected=connected,scenario=scenario)
            models=[make(code).run() for code in (self.original,self.raw,self.fitted)]
            for model in models[1:]:
                self.assertEqual((model.memory,model.events,model.calls,model.f,model.r[2]),
                    (models[0].memory,models[0].events,models[0].calls,models[0].f,models[0].r[2]))
            failed=scenario in (2,3,4,5) or scenario==1 and flags&4
            for model in models:
                self.assertEqual(model.r[2],0 if failed else 0x51000)
                self.assertEqual(read(model.memory,HEAD),0 if failed else 0x51000)
                if failed and scenario!=5:
                    self.assertEqual(len(model.release_snapshots),1)
                    snapshot,stack,packet,ordinal,saved_s0,ra=model.release_snapshots[0]
                    expected=reference(snapshot,*packet,phase=stack-STACK,saved_s0=saved_s0,return_address=ra)
                    self.assertEqual(model.memory,expected[0]);self.assertEqual(model.calls[ordinal+1:],expected[2])
                    self.assertEqual(model.calls[-1],(FREE,0x51000))
                else:self.assertFalse(model.release_snapshots)
            if phase==0 and selector==255 and flags==12 and scenario in (1,2,3,4):
                for ordinal in range(models[0].accesses):
                    failed_models=[]
                    for code in (self.original,self.raw,self.fitted):
                        model=make(code);model.fault=ordinal
                        with self.assertRaises(guest.AccessFault) as caught:model.run()
                        self.assertEqual(caught.exception.args,(ordinal,));self.assertEqual(model.accesses,ordinal);failed_models.append(model)
                    for model in failed_models[1:]:
                        self.assertEqual((model.memory,model.events,model.calls,model.f),
                            (failed_models[0].memory,failed_models[0].events,failed_models[0].calls,failed_models[0].f))
                    prefixes+=1
            cases+=1
        self.receipt('factory',cases=cases,executions=cases*3,actual_152_word_factory_96_word_initializer_102_word_release=True,
            node_allocation_matrix_allocation_full_status_first_second_buffer_failure_gates=True,
            independent_complete_cleanup_memory_and_calls=True,unlinked_before_final_node_free=True,
            actual_success_action_consumer_113_words=True,fired_fault_triples=prefixes,failed_executions=prefixes*3,
            deeper_loaders_allocator_free_copy_action_callbacks_bounded=True)

    def test_09_whole_ELF_single_slot_extent_guards_and_protected_inputs(self):
        source=(self.root/screen.SOURCE).read_text();before=self.before
        self.assertEqual(source,(self.out/'before-source').read_text() if screen.recovery.ORIGINAL in source
            else screen.install((self.out/'before-source').read_text()))
        if screen.recovery.ORIGINAL in source:self.receipt('linked',installed=False);return
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(before)
        struct.pack_into('>102I',expected,elf_slot_offset(before,screen.ENTRY,408),*self.fitted)
        old,new=metadata(before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:])
        symbol_table=old[4];changes=0
        for offset in range(symbol_table[4],symbol_table[4]+symbol_table[5],symbol_table[9]):
            a,b=SYMBOL.unpack_from(before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:])
                self.assertEqual((a[2],b[2]),(12,408));struct.pack_into('>I',expected,offset+8,b[2]);changes+=1
        self.assertEqual(changes,1);self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        with (self.root/self.paths['guards']).open(newline='') as f:self.assertEqual(list(csv.DictReader(f)),self.old_rows+self.rows)
        for name in ('progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        self.receipt('linked',installed=True,changed_function_count=1,changed_symbol_extents=1,
            all_other_ELF_bytes_exact=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),guard_prefix_exact=True,appended_rows=5,
            data_audit=audit,conversion_rows_unchanged=True)


NATIVE_PREFIX=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
static u32 nodes[5][24],expectedNodes[5][24];static u8 *D_800C3EE0,*expectedHead;
struct Call {u32 role,pointer,mode;};static struct Call calls[64],expectedCalls[64];
static s32 callCount,expectedCount,plan,ordinals[6];
static u8 *node(void){return (u8 *)nodes[0];}
static u8 *pointer(u8 *p,s32 offset){return *(u8 **)(p+offset);}
static void set(u8 *p,s32 offset,u8 *value){*(u8 **)(p+offset)=value;}
static void call(s32 role,u8 *p,s32 mode){
    s32 n=ordinals[role]++;u8 *v=node();
    calls[callCount].role=role;calls[callCount].pointer=(u32)p;calls[callCount].mode=mode;callCount++;
    if(role==1&&plan==1){v[9]=v[8]=0;set(v,0x34,(u8 *)0x47000);}
    if((role==2||role==3)&&!n&&plan==2)set(v,0x2C,(u8 *)0x47000);
    if(role==4&&plan==3)v[1]=255;
    if(role==5&&plan==4){set(v,0x34,(u8 *)0x47000);set(v,0x44,0);
        set(v,0x54,(u8 *)nodes[4]);set(v,0x58,(u8 *)nodes[3]);D_800C3EE0=(u8 *)nodes[2];}
}
static void func_15031C14(u8 *p){call(1,p,0);}
static void func_10004074(void *p){call(2,(u8 *)p,0);}
static void func_100043B4(void *p,s32 mode){call(3,(u8 *)p,mode);}
static void func_1503F7B8(void *p){call(4,(u8 *)p,0);}
static void func_1518CA04(s32 kind){call(5,(u8 *)(u32)kind,0);}
'''
NATIVE_RUNNER=r'''
static void referenceRelease(u8 *n,s32 immediate){
    static const s32 offsets[4]={0x34,0x44,0x4C,0x50};s32 i;u8 *p;
    if(!immediate)call(1,n,0);
    if(n[9]){
        if(n[8])for(i=0;i<2;i++){
            p=pointer(n,0x28+i*4);call(immediate?2:3,p,immediate?0:4);
        }
        p=pointer(n,0x48);if(p)call(4,p,0);
        call(5,(u8 *)(u32)n[1],0);
    }
    for(i=0;i<4;i++){
        p=pointer(n,offsets[i]);if(p)call(i==1||immediate?2:3,p,i==1||immediate?0:4);
    }
    if(D_800C3EE0==n)D_800C3EE0=pointer(n,0x54);
    p=pointer(n,0x58);if(p)set(p,0x54,pointer(n,0x54));
    p=pointer(n,0x54);if(p)set(p,0x58,pointer(n,0x58));
    call(2,n,0);
}
static void setup(s32 initialized,s32 copied,s32 kind,s32 mask,s32 listing,s32 scenario){
    static const s32 offsets[7]={0x28,0x2C,0x34,0x44,0x48,0x4C,0x50};
    s32 i,j;u8 *n=node();plan=scenario;callCount=0;
    for(i=0;i<6;i++)ordinals[i]=0;
    for(i=0;i<5;i++)for(j=0;j<24;j++)nodes[i][j]=0xA5A5A5A5u;
    n[1]=(u8)kind;n[8]=(u8)copied;n[9]=(u8)initialized;
    for(i=0;i<7;i++)set(n,offsets[i],mask>>i&1?(u8 *)(u32)(0x46000+i*0x100):0);
    set(n,0x54,listing==1||listing==2?(u8 *)nodes[2]:0);
    set(n,0x58,listing==2||listing==3?(u8 *)nodes[1]:0);
    D_800C3EE0=listing<2?n:(u8 *)nodes[1];
}
static s32 qualify(s32 initialized,s32 copied,s32 kind,s32 mask,s32 listing,s32 immediate,s32 scenario){
    s32 i,j;
    setup(initialized,copied,kind,mask,listing,scenario);referenceRelease(node(),immediate);
    expectedHead=D_800C3EE0;expectedCount=callCount;
    for(i=0;i<callCount;i++)expectedCalls[i]=calls[i];
    for(i=0;i<5;i++)for(j=0;j<24;j++)expectedNodes[i][j]=nodes[i][j];
    setup(initialized,copied,kind,mask,listing,scenario);func_15030158(node(),immediate);
    if(D_800C3EE0!=expectedHead||callCount!=expectedCount)return 1;
    for(i=0;i<callCount;i++)if(calls[i].role!=expectedCalls[i].role||calls[i].pointer!=expectedCalls[i].pointer||
        calls[i].mode!=expectedCalls[i].mode)return 2;
    for(i=0;i<5;i++)for(j=0;j<24;j++)if(nodes[i][j]!=expectedNodes[i][j])return 3;
    return 0;
}
int run(void){
    static const s32 modes[5]={0,1,256,(s32)0x80000000u,-1};
    s32 axis,value,mask,mode,scenario,initialized,copied,listing,r;
    for(axis=0;axis<3;axis++)for(value=0;value<256;value++)for(mask=0;mask<2;mask++)
        for(mode=0;mode<5;mode++)for(scenario=0;scenario<5;scenario++){
            r=qualify(axis==0?value:1,axis==1?value:1,axis==2?value:133,mask?127:0,value%4,modes[mode],scenario);
            if(r)return r;
        }
    for(mask=0;mask<128;mask++)for(initialized=0;initialized<2;initialized++)for(copied=0;copied<2;copied++)
        for(mode=0;mode<5;mode++)for(listing=0;listing<4;listing++){
            r=qualify(initialized,copied,255,mask,listing,modes[mode],0);if(r)return r;
        }
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
