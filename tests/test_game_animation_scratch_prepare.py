"""Full semantic restoration; byte matching and private fault order remain open."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_animation_scratch_prepare_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_node_transform_submit_match as submit
from tools.tests.test_game_record_constructor_match import elf_slot_offset,SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout

STACK,MASK=submit.STACK,0xFFFFFFFF
NODE,ACTOR,ALT,SCRATCH=0x20000,0x22000,0x24000,0x28000
REFRESH,SMALL,DMA=screen.SYMBOLS.values()
BZERO=0x100226F0


def private(address):return STACK-0x600<=address<STACK+0x100
def public(memory):return {a:v for a,v in memory.items() if not private(a)}
def events_public(events):return [e for e in events if e[0]=='CALL' or not private(e[1])]
def f32(value):return floating(bits(value))


def fixture(length=7,stride=0,frame=2.25,end=8.0,flag=0,actor=False,sentinel=0,
        source=0x12345001,alignment=3,second=11,node=NODE):
    memory={}
    for base,size in ((STACK-0x600,0x700),(node,0x500),(ALT,0x500),(ACTOR,0x32C),(SCRATCH,0x800)):
        memory.update({base+i:(i*17+35)&255 for i in range(size)})
    for base in (node,ALT):
        put(memory,base+0x3C,flag,2)
        for i in range(2):
            for offset,value,size in ((8+i*4,bits(frame),4),(0x18+i*4,bits(end),4),
                    (0x28+i*4,(source+i*0x1000)&MASK,4),(0x45+i*0x1D0,length if i==0 else second,1),
                    (0x48+i*0x1D0,stride,1)):
                put(memory,base+offset,value,size)
    put(memory,ACTOR+0x84,sentinel,2);put(memory,ACTOR+0x2D0,node)
    return memory,(node,ACTOR if actor else 0,SCRATCH+alignment)


def mutation(target,ordinal,node,plan):
    if target==REFRESH and plan==1:return ((ACTOR+0x2D0,ALT,4),)
    if target==REFRESH and plan==4:return ((ACTOR+0x2D0,0,4),)
    if target in (SMALL,DMA) and ordinal==0 and plan==2:
        return ((node+0x28,0x76543003,4),(node+0x30,SCRATCH+0x400,4))
    if target in (SMALL,DMA) and ordinal==0 and plan==3:
        return ((node+0x3C,0,2),(node+0x215,199,1),(node+0xC,bits(7.5),4))
    return ()


def reference(memory,arguments,plan=0,symbols=None):
    refresh,small,dma=(symbols or screen.SYMBOLS).values();state=memory.copy();events=[];calls=[];copies=0
    node,actor,scratch=arguments
    def get(where,size=4):
        assert all(where+i in state for i in range(size)),('unmapped reference read',where,size)
        value=read(state,where,size);events.append(('R',where,size,value));return value
    def store(where,value,size=1):
        assert all(where+i in state for i in range(size)),('unmapped reference write',where,size)
        value&=(1<<(size*8))-1;put(state,where,value,size);events.append(('W',where,size,value))
    def call(target,packet):
        nonlocal copies
        events.append(('CALL',target,packet));calls.append((target,*packet))
        if target in (small,dma):
            source,destination,size=packet[:3]
            for i in range(size):store((destination+i)&MASK,(source+i*13)&255)
            ordinal=copies;copies+=1;role=SMALL if target==small else DMA
        else:ordinal=0;role=REFRESH
        for where,value,size in mutation(role,ordinal,node,plan):store(where,value,size)
    banks=1
    if actor:
        if get(actor+0x84,2)==65535:call(refresh,(actor,))
        node=get(actor+0x2D0)
    if not node:return public(state),events,calls
    if signed(get(node+0x3C,2)<<16)>0:banks=2
    for bank in range(banks):
        fields=node+bank*4;length=get(node+bank*0x1D0+0x45,1)
        if not length:store(node+0x38+bank,0);continue
        source=get(fields+0x28)
        if not source:continue
        frame=floating(get(fields+8));end=floating(get(fields+0x18));scratch=(scratch+15)&MASK&~15
        index=math.trunc(frame)
        if end<=f32(index):index=math.trunc(f32(end-1.0))
        stride=get(node+bank*0x1D0+0x48,1)+1
        if stride>=2:
            last=f32(end-1.0)
            index=math.trunc(f32(f32(last+f32(stride-1))/f32(stride))) if last<=f32(index) else (abs(index)//stride)*(-1 if index<0 else 1)
        address=(source+length*index)&MASK;skip=address&3;address=(address-skip)&MASK
        wrap=end<=f32(frame+1.0);amount=length if wrap else length*2
        if not wrap:store(node+0x38+bank,length)
        amount+=skip;store(fields+0x30,(scratch+skip)&MASK,4)
        call(small if amount<200 else dma,(address,scratch,amount) if amount<200 else (address,scratch,(amount+15)&~15,1))
        scratch=(scratch+amount)&MASK
        if wrap:
            address=get(fields+0x28);scratch=(scratch+15)&MASK&~15;skip=address&1;amount=skip+length
            address=(address-skip)&MASK
            call(small if amount<200 else dma,(address,scratch,amount) if amount<200 else (address,scratch,(amount+15)&~15,1))
            pointer=get(fields+0x30);store(node+0x38+bank,scratch+skip-pointer);scratch=(scratch+amount)&MASK
    return public(state),events,calls


class PrepareOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,arguments,phase=0,entry=screen.ENTRY,symbols=None,plan=0,connected=None):
        super().__init__(words,memory,arguments=arguments,phase=phase,entry=entry,connected=connected)
        refresh,small,dma=(symbols or screen.SYMBOLS).values();self.roles={refresh:REFRESH,small:SMALL,dma:DMA,BZERO:BZERO}
        self.counts={refresh:1,small:3,dma:4,BZERO:2};self.plan=plan;self.node=arguments[0];self.copies=0
        self.public_fault=None;self.public_accesses=0
    def get(self,address,size):
        self.public_gate(address);return super().get(address,size)
    def put(self,address,value,size):
        if self.recording:self.public_gate(address)
        super().put(address,value,size)
    def public_gate(self,address):
        if private(address):return
        if self.public_fault==self.public_accesses:raise guest.AccessFault(self.public_accesses)
        self.public_accesses+=1
    def record_call(self,target):
        args=self.arguments(self.counts[target]);self.calls.append((target,*args));self.events.append(('CALL',target,args))
    def hook(self,target):
        role=self.roles[target];packet=self.calls[-1][1:]
        if role in (SMALL,DMA):
            source,destination,size=packet[:3]
            if role==DMA:assert size%16==0 and packet[3]==1
            for i in range(size):self.put((destination+i)&MASK,(source+i*13)&255,1)
            ordinal=self.copies;self.copies+=1
        elif role==BZERO:
            destination,size=packet
            for i in range(size):self.put(destination+i,0,1)
            ordinal=0
        else:ordinal=0
        for where,value,size in mutation(role,ordinal,self.node,self.plan):self.put(where,value,size)
        if role==REFRESH:self.node=read(self.memory,ACTOR+0x2D0)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]


class GameAnimationScratchPrepareTests(unittest.TestCase):
    maxDiff=1500
    run_native=native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/'conker/build/game-animation-scratch-prepare-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,caller='conker/src/game/generated_6C960.c',elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',
            symbols='conker/symbol_addrs.us.txt',undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text();hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes();cls.retail=list(struct.unpack_from('>191I',cls.rom,screen.ROM))
        cls.before=(cls.out/'before-elf').read_bytes();cls.guard_bytes=screen.retire_superseded_submit_guards((cls.out/'before-guards').read_bytes())
        (cls.out/'qualified-guards.csv').write_bytes(cls.guard_bytes)
        cls.refresh=list(struct.unpack_from('>33I',cls.rom,0x8B48C))
        assert cls.refresh==list(struct.unpack_from('>33I',cls.before,elf_slot_offset(cls.before,REFRESH,132)))
    def receipt(self,name,**values):(self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,args,forms=None,**settings):
        expected=reference(memory,args,plan=settings.get('plan',0),symbols=settings.get('symbols'))
        models=[PrepareOracle(code,memory,args,**settings).run() for code in (forms or (self.retail,self.raw))]
        for model in models:self.assertEqual((public(model.memory),events_public(model.events),model.calls),expected)
        return models
    def test_01_full_semantic_body_not_claimed_byte_exact(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['diagnostics'],self.meta['pool_bytes']),(188,80,162,'',0))
        self.assertNotEqual(self.raw,self.retail)
        self.assertEqual(len(self.meta['relocations']),5)
        before=(self.out/'before-guards').read_bytes()
        with self.assertRaisesRegex(ValueError,'stale transform'):
            screen.retire_superseded_submit_guards(before.replace(b'0x020A1821',b'0x020A1820'))
        line=next(line for line in before.splitlines(keepends=True) if b'func_1503F4B0,0x6C,' in line)
        with self.assertRaisesRegex(ValueError,'duplicate superseded'):
            screen.retire_superseded_submit_guards(before+line)
        self.receipt('shape',raw_words=188,retail_words=191,raw_frame=80,retail_frame=104,isolated_word_differences=162,
            guards_for_new_function=0,matching_not_achieved=True,compiler_diagnostics=0,pool_bytes=0)
    def test_02_byte_domains_frame_boundaries_alignments_and_NULL_gates(self):
        cases=0;coverage=set()
        settings=[{axis:i} for axis in ('length','stride') for i in range(256)]
        settings += [dict(length=n,frame=f,end=e,flag=flag,alignment=a,source=s) for n,f,e,flag,a,s in
            itertools.product((0,1,99,100,197,198,199,200,254,255),(-2.5,0.0,6.25,7.0,8.0),(1.0,8.0),
                (0,1),(0,15),(0,0xFFFFFFFD))]
        settings += [dict(actor=True,sentinel=value,flag=flag) for value,flag in itertools.product((0,65534,65535),(0,32767,32768,65535))]
        for values in settings:
            memory,args=fixture(**values);models=self.compare(memory,args);coverage.update(models[0].visits);cases+=1
        for phase,node in itertools.product((0,8),(0,NODE)):
            memory,args=fixture();self.compare(memory,(node,0,args[2]),phase=phase);cases+=1
        for alignment in range(16):
            memory,args=fixture(alignment=alignment,flag=1,frame=7.5,length=255);self.compare(memory,args);cases+=1
        self.receipt('guest',cases=cases,executions=cases*2,retail_words_reached=len(coverage),full_routine_executed=True,
            all_length_stride_bytes=True,alignment_positions=16,finite_float_only=True,independent_ordered_public_reference=True,
            private_frame_equivalence_not_claimed=True,PI_callbacks_bounded_not_actual_ROM_reads=True)
    def test_03_mutations_aliases_and_fired_public_fault_pairs(self):
        cases=pairs=0
        for plan in range(5):
            memory,args=fixture(length=7,flag=1,frame=7.5,actor=True,sentinel=65535)
            models=self.compare(memory,args,plan=plan);cases+=1
            for cut in range(models[0].public_accesses):
                failed=[]
                for code in (self.retail,self.raw):
                    model=PrepareOracle(code,memory,args,plan=plan);model.public_fault=cut
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(cut,));self.assertEqual(model.public_accesses,cut);failed.append(model)
                self.assertEqual((public(failed[0].memory),events_public(failed[0].events),failed[0].calls),
                    (public(failed[1].memory),events_public(failed[1].events),failed[1].calls));pairs+=1
        for alias in (NODE+0x40,NODE+0x30):
            memory,args=fixture(length=3,frame=7.5,flag=1);self.compare(memory,(args[0],args[1],alias));cases+=1
        self.receipt('aliases',cases=cases,fired_public_fault_pairs=pairs,failed_executions=pairs*2,
            private_fault_order_not_claimed=True,live_actor_node_source_output_second_bank_reads=True)
    def test_04_independently_rebased_five_JAL_sites(self):
        cases=0
        for i in range(3):
            entry=0x15217FFC+i*0x10004;symbols={name:0x15417FFC+i*0x10004+j*0x100 for j,name in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%i);elf=script.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/'selected.o')],check=True,capture_output=True)
            raw=list(struct.unpack_from('>188I',sections(elf)['.text'][1]));retail=list(self.retail)
            for n,w in enumerate(retail):
                if w>>26==3:
                    target=((screen.ENTRY+4)&0xF0000000)|((w&0x3FFFFFF)<<2)
                    name=next(name for name,va in screen.SYMBOLS.items() if va==target);retail[n]=0x0C000000|((symbols[name]>>2)&0x3FFFFFF)
            for length,frame,plan in itertools.product((0,7,255),(2.25,7.5),(0,2,3)):
                memory,args=fixture(length=length,frame=frame,flag=1);self.compare(memory,args,forms=(retail,raw),entry=entry,symbols=symbols,plan=plan);cases+=1
        self.receipt('rebases',links=3,cases=cases,executions=cases*2,all_five_JAL_sites=True,three_independent_callbacks=True)
    def test_05_actual_33_word_actor_refresh_connection(self):
        connected={REFRESH+i*4:w for i,w in enumerate(self.refresh)};cases=0
        for flag,node in itertools.product((0,1),(0,NODE)):
            memory,args=fixture(flag=flag,actor=True,sentinel=65535);put(memory,ACTOR+4,3,1);put(memory,ACTOR+0x2D0,node)
            for i in range(8):memory[0x800C4ED0+i]=0
            put(memory,0x800C4ED0+6,5,2)
            models=[PrepareOracle(code,memory,args,connected=connected).run() for code in (self.retail,self.raw)]
            self.assertEqual((public(models[0].memory),events_public(models[0].events),models[0].calls),
                (public(models[1].memory),events_public(models[1].events),models[1].calls))
            self.assertEqual(read(models[0].memory,ACTOR+0x84,2),65535)
            if node:self.assertEqual(read(models[0].memory,node+0x28),0);self.assertEqual(read(models[0].memory,node+0x38,1),0)
            self.assertFalse(any(call[0] in (SMALL,DMA) for call in models[0].calls));cases+=1
        self.receipt('refresh',cases=cases,executions=cases*2,actual_33_word_retail_and_linked_helper_exact=True,bzero_bounded=True)
    def test_06_effective_IDO_negative_controls(self):
        controls=(('wrong-length',screen.SELECTED.replace('length * 2','length * 3'),dict(frame=2.25,length=7)),
            ('wrong-bank-sign',screen.SELECTED.replace('*(s16 *)(node + 0x3C)','*(u16 *)(node + 0x3C)'),dict(flag=32768)),
            ('wrong-alignment',screen.SELECTED.replace('+ 15) >> 4 << 4','+ 7) >> 3 << 3'),dict(alignment=7)),
            ('wrong-threshold',screen.SELECTED.replace('0xC8U','0xC7U'),dict(length=199,frame=7.5,source=0x12345000)),
            ('wrong-stride',screen.SELECTED.replace('state[0x48] + 1','state[0x48] + 2'),dict(stride=1,frame=5.5)),
            ('wrong-wrap-mask',screen.SELECTED.replace('address & 1','address & 3'),dict(source=0x12345003,frame=7.5)),
            ('wrong-offset',screen.SELECTED.replace('scratch + offset) - (u32)*(u8 **)(fields + 0x30)','scratch) - (u32)*(u8 **)(fields + 0x30)'),dict(source=0x12345001,frame=7.5)))
        for name,body,values in controls:
            _,words=screen.compile_candidate(self.root,self.out,name,body);memory,args=fixture(**values)
            with self.assertRaises(AssertionError):self.compare(memory,args,forms=(words,))
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))
    def test_07_copied_owner_and_submit_contract_requalification(self):
        objects=[];padded=[];diagnostics=[];before=(self.out/'before-source').read_text()
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,detail=compile_owner(self.root,self.out,source,name);objects.append(obj);diagnostics.append(detail)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            asm=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_58F80',str(asm),'--word-patches',str(self.out/'qualified-guards.csv')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(asm.with_suffix('.o')))
        self.assertEqual(diagnostics,[[],[]]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        a,b=padded;start=a[1][screen.FUNCTION]['value'];end=start+191*4
        self.assertEqual(a[0][:start]+a[0][end:],b[0][:start]+b[0][end:])
        for name in a[1]:
            if name!=screen.FUNCTION:self.assertEqual(a[1][name],b[1][name])
        self.assertEqual({o:v for o,v in a[2].items() if not start<=o<end},{o:v for o,v in b[2].items() if not start<=o<end})
        with self.assertRaises(ValueError):screen.retire_superseded_submit_guards(self.guard_bytes)
        submit.GameNodeTransformSubmitMatchTests.setUpClass()
        self.assertEqual(submit.GameNodeTransformSubmitMatchTests.fitted,submit.GameNodeTransformSubmitMatchTests.original)
        self.receipt('owner',untouched_neighbors=len(a[1])-1,bytes_extents_relocations_pools_exact=True,diagnostics=0,
            current_66_word_submit_stays_exact=True,three_superseded_base_guards_retired=True,two_placement_guards_retained=True)
    def test_08_whole_ELF_only_preparation_slot_and_size_change(self):
        source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:self.receipt('linked',installed=False);return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        caller=(self.out/'before-caller').read_text().replace('s32 func_1502D824();','void func_1502D824(u8 *, u8 *, u8 *);')
        self.assertEqual((self.root/self.paths['caller']).read_text(),caller)
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        struct.pack_into('>188I',expected,elf_slot_offset(self.before,screen.ENTRY,764),*self.raw)
        old,new=metadata(self.before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:]);changed=0
        section=old[4]
        for offset in range(section[4],section[4]+section[5],section[9]):
            a,b=SYMBOL.unpack_from(self.before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:]);self.assertEqual((a[2],b[2]),(12,752))
                struct.pack_into('>I',expected,offset+8,b[2]);changed+=1
        self.assertEqual(changed,1);self.assertEqual(bytes(expected),actual)
        self.assertEqual((self.root/self.paths['guards']).read_bytes(),self.guard_bytes)
        for name in ('progress','rodata','symbols','undefined'):self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),all_other_ELF_bytes_exact=True,data_audit=audit,
            conversion_rows_unchanged=True,matching_credit_added=0,new_function_guards=0,retired_submit_guards=3)

    def test_09_complete_66_word_transform_caller_connection(self):
        class Connected(submit.SubmitOracle):
            def __init__(self,outer,memory,code,temporary):
                super().__init__(outer,memory,node=NODE,temporary=temporary,connected={screen.ENTRY+i*4:w for i,w in enumerate(code)})
                self.roles.update({REFRESH:REFRESH,SMALL:SMALL,DMA:DMA});self.counts.update({REFRESH:1,SMALL:3,DMA:4})
                self.node=NODE;self.copies=0
            def hook(self,target):
                if target in (REFRESH,SMALL,DMA):PrepareOracle.hook(self,target)
                else:super().hook(target)
        outer=list(struct.unpack_from('>66I',self.rom,submit.screen.ROM));cases=0
        for length,frame,flag,gate,temporary in itertools.product((0,7,100),(2.25,7.5),(0,1),(False,True),(0,SCRATCH)):
            if temporary==0 and length!=0 and gate:continue
            memory,args=fixture(length=length,frame=frame,flag=flag,second=0 if temporary==0 else 11)
            for offset,value,size in ((0x3E0,0x30000 if gate else 0,4),(0x3E8,0x31000,4),(0x3F0,0x32000,4),(0x3F4,2,1)):
                put(memory,NODE+offset,value,size)
            memory[submit.SELECTOR]=0
            for i in range(4):memory[submit.STEP+i]=0
            put(memory,submit.STEP,bits(1.0))
            models=[Connected(outer,memory,code,temporary).run() for code in (self.retail,self.raw)]
            self.assertEqual((public(models[0].memory),events_public(models[0].events),models[0].calls),
                (public(models[1].memory),events_public(models[1].events),models[1].calls));cases+=1
        self.receipt('caller',cases=cases,executions=cases*2,actual_complete_66_word_caller=True,
            complete_retail_and_current_preparation=True,gate_and_safe_NULL_temporary_paths=True,
            emission_submission_timeline_allocator_free_bounded=True)

    def test_10_native32_optimized_unoptimized_and_effective_negative(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        result,_=self.run_native('native-negative',NATIVE_PREFIX+screen.SELECTED.replace('length * 2','length * 3')+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=12288,executions=24576,
            effective_negative_controls=1,finite_in_range_conversions_only=True,private_fault_order_not_claimed=True,
            bounded_PI_packets_and_generated_copy_bytes=True)


NATIVE_PREFIX=r'''
#define NULL ((void *)0)
typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u32 nodeWords[320],actorWords[204],scratchWords[512];
static u8 *node=(u8 *)nodeWords,*actor=(u8 *)actorWords,*storage=(u8 *)scratchWords;
static u32 log[8][5],expectedLog[8][5],expectedNode[320],expectedActor[204],expectedStorage[512];
static s32 calls,scenario,copies;
static void record(u32 role,u32 a,u32 b,u32 c,u32 d){
    u32 *p=log[calls++];p[0]=role;p[1]=a;p[2]=b;p[3]=c;p[4]=d;
}
static void func_1505DFDC(u8 *p){
    record(1,(u32)p,0,0,0);if(scenario==4)*(u32 *)(p+720)=0;
}
static void copied(u32 source,u8 *destination,u32 size){
    u32 i;for(i=0;i<size;i++)destination[i]=(u8)(source+i*13);
    if(copies++==0 && scenario==2){*(u32 *)(node+40)=0x76543003u;*(u32 *)(node+48)=(u32)storage+1024;}
    if(copies==1 && scenario==3){*(s16 *)(node+60)=0;node[533]=199;*(f32 *)(node+12)=7.5f;}
}
static void func_1000480C(s32 source,void *destination,u32 size){
    record(2,(u32)source,(u32)destination,size,0);copied((u32)source,destination,size);
}
static s32 func_10004514(s32 source,void *destination,u32 size,s32 mode){
    record(3,(u32)source,(u32)destination,size,(u32)mode);copied((u32)source,destination,size);return -1;
}
'''
NATIVE_RUNNER=r'''
static void independent(u8 *p,u8 *a,u8 *scratch){
    s32 banks,i;u32 n,base,address,skip,amount,step;f32 frame,end,last;int k;
    if(a){if(*(u16 *)(a+132)==65535)func_1505DFDC(a);p=(u8 *)*(u32 *)(a+720);}
    if(!p)return;
    banks=*(s16 *)(p+60)>0?2:1;
    for(i=0;i<banks;i++){
        u8 *fields=p+i*4;n=p[i*464+69];
        if(!n){p[56+i]=0;continue;}base=*(u32 *)(fields+40);if(!base)continue;
        frame=*(f32 *)(fields+8);end=*(f32 *)(fields+24);scratch=(u8 *)(((u32)scratch+15)&~15u);
        k=(int)frame;if(end<=(f32)k)k=(int)(end-1.0f);step=(u32)p[i*464+72]+1;
        if(step>1){last=end-1.0f;if(last<=(f32)k)k=(int)((last+(f32)(step-1))/(f32)step);else k/=(int)step;}
        address=base+n*(u32)k;skip=address%4;amount=(end<=frame+1.0f?n:2*n)+skip;
        if(end>frame+1.0f)p[56+i]=(u8)n;
        *(u32 *)(fields+48)=(u32)scratch+skip;
        if(amount>=200)func_10004514((s32)(address-skip),scratch,(amount+15)&~15u,1);
        else func_1000480C((s32)(address-skip),scratch,amount);
        scratch+=amount;
        if(end<=frame+1.0f){
            base=*(u32 *)(fields+40);skip=base%2;scratch=(u8 *)(((u32)scratch+15)&~15u);amount=n+skip;
            if(amount>=200)func_10004514((s32)(base-skip),scratch,(amount+15)&~15u,1);
            else func_1000480C((s32)(base-skip),scratch,amount);
            p[56+i]=(u8)((u32)scratch+skip-*(u32 *)(fields+48));scratch+=amount;
        }
    }
}
static void setup(int length,int stride,int flag,int alignment,int phase,int plan){
    int i;for(i=0;i<320;i++)nodeWords[i]=0xA5A5A5A5u;
    for(i=0;i<204;i++)actorWords[i]=0xA5A5A5A5u;
    for(i=0;i<512;i++)scratchWords[i]=0xA5A5A5A5u;
    for(i=0;i<2;i++){
        *(f32 *)(node+8+i*4)=phase?7.5f:2.25f;*(f32 *)(node+24+i*4)=8.0f;
        *(u32 *)(node+40+i*4)=0x12345001u+(u32)i*4096u;
        node[i*464+69]=(u8)length;node[i*464+72]=(u8)stride;
    }
    *(s16 *)(node+60)=(s16)flag;*(u16 *)(actor+132)=65535;*(u32 *)(actor+720)=(u32)node;
    calls=copies=0;scenario=plan;(void)alignment;
}
static int qualify(int length,int stride,int flag,int alignment,int phase,int plan){
    int i,j,count;setup(length,stride,flag,alignment,phase,plan);
    independent(node,actor,storage+alignment);count=calls;
    for(i=0;i<calls;i++)for(j=0;j<5;j++)expectedLog[i][j]=log[i][j];
    for(i=0;i<320;i++)expectedNode[i]=nodeWords[i];
    for(i=0;i<204;i++)expectedActor[i]=actorWords[i];
    for(i=0;i<512;i++)expectedStorage[i]=scratchWords[i];
    setup(length,stride,flag,alignment,phase,plan);func_1502D824(node,actor,storage+alignment);
    if(calls!=count)return 1;
    for(i=0;i<calls;i++)for(j=0;j<5;j++)if(expectedLog[i][j]!=log[i][j])return 2;
    for(i=0;i<320;i++)if(expectedNode[i]!=nodeWords[i])return 3;
    for(i=0;i<204;i++)if(expectedActor[i]!=actorWords[i])return 4;
    for(i=0;i<512;i++)if(expectedStorage[i]!=scratchWords[i])return 5;
    return 0;
}
int run(void){
    static const int strides[]={0,1,127,255},alignments[]={0,7,15};
    int length,stride,flag,alignment,phase,r;
    for(length=0;length<256;length++)for(stride=0;stride<4;stride++)for(flag=0;flag<2;flag++)
        for(alignment=0;alignment<3;alignment++)for(phase=0;phase<2;phase++){
            r=qualify(length,strides[stride],flag,alignments[alignment],phase,length%5);if(r)return r;
        }
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
