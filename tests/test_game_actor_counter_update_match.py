"""Direct signed counter recovery, private traces, actual classifier and owner audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_counter_update_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as attachment
from tools.tests import test_game_actor_update_dispatch_match as dispatch
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put,read

STACK=attachment.STACK
CONFIG=0x24000
CLASSIFIER=0x1502C3BC
LINKS=(screen.SYMBOLS,
    dict(D_800BEAC0=0x80107FFC,D_800CC2D0=0x80118004,D_8008CA4C=0x80128004,func_1502C3BC=0x15207FF0),
    dict(D_800BEAC0=0x80218004,D_800CC2D0=0x80227FFC,D_8008CA4C=0x80237FFC,func_1502C3BC=0x15308004))


def half(value):
    return ((value&65535)^32768)-32768


def fixture(slot=0,value=0,step=1,period=1,enabled=1,disabled=0,identity=11,symbols=LINKS[0],phase=0):
    actor=symbols['D_800CC2D0']+slot*0x32C
    memory={STACK+phase+i:0xA5 for i in range(-0x100,0x80)}
    memory.update({actor+i:(i*17+0x35)&255 for i in range(0x32C)})
    for address,length in ((symbols['D_8008CA4C'],1024),(CONFIG,16)):
        memory.update({address+i:0xA5 for i in range(length)})
    for address,data,size in ((symbols['D_800BEAC0'],disabled,1),(actor+7,enabled,1),
            (actor+0x60,value,2),(actor+0x62,step,2),(actor+0x136,identity,1),
            (symbols['D_8008CA4C']+identity*4,CONFIG,4),(CONFIG+4,period,1)):
        put(memory,address,data,size)
    # Retail never touches the reserved word between argument homes and saved RA.
    for i in range(4): del memory[STACK+phase-0x28+0x10+i]
    return memory


def reference(memory,slot=0,symbols=LINKS[0],phase=0,identity=11,actions=(),actual=False):
    result,events=memory.copy(),[]
    frame=STACK+phase-0x28
    actor=(symbols['D_800CC2D0']+(slot&0xFFFFFFFF)*0x32C)&0xFFFFFFFF
    def get(address,size):
        assert all(address+i in result for i in range(size))
        value=read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(address,value,size):
        assert all(address+i in result for i in range(size))
        put(result,address,value,size)
        events.append(('W',address,size,value&((1<<(size*8))-1)))
    store(frame+0x14,0xDEAD0000,4)
    if get(symbols['D_800BEAC0'],1)==0:
        enabled=get(actor+7,1)
        value,step=half(get(actor+0x60,2)),half(get(actor+0x62,2))
        if enabled:
            store(frame+0x22,value,2)
            store(frame+0x18,actor,4)
            store(frame+0x20,step,2)
            events.append(('CALL',symbols['func_1502C3BC'],(slot&0xFFFFFFFF,)))
            if actual:
                identity=get(actor+0x136,1)
                if identity>=70: identity=11
            for address,data,size in actions: store(address,data,size)
            configuration=get(symbols['D_8008CA4C']+identity*4,4)
            value,step=half(get(frame+0x22,2)),half(get(frame+0x20,2))
            period=get(configuration+4,1)<<8
            actor=get(frame+0x18,4)
            value=half(value+step)
            if value>=period: value=half(value-period)
            elif value<0: value=half(value+period)
            store(actor+0x60,value,2)
    get(frame+0x14,4)
    return result,events


class CounterOracle(attachment.AttachmentOracle):
    def __init__(self,words,memory,slot=0,symbols=LINKS[0],phase=0,identity=11,actions=(),**kwargs):
        super().__init__(words,memory,slot,(screen.ENTRY,0,0),phase,**kwargs)
        self.symbols,self.identity,self.actions=symbols,identity,actions
    def record_call(self,target):
        assert target==self.symbols['func_1502C3BC']
        args=self.arguments(1)
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.symbols['func_1502C3BC']
        for address,value,size in self.actions: self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.identity


class GameActorCounterUpdateMatchTests(unittest.TestCase):
    run_host=attachment.GameActorAttachmentUpdateMatchTests.run_host
    assemble=classmethod(attachment.GameActorAttachmentUpdateMatchTests.assemble.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-counter-update-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>56I',cls.rom,screen.ROM))
        cls.elf=(cls.root/cls.paths['elf']).read_bytes()
        cls.current=cls.raw
        if screen.ORIGINAL not in (cls.root/screen.SOURCE).read_text():
            cls.current=list(struct.unpack_from('>56I',cls.elf,elf_slot_offset(cls.elf,screen.ENTRY,224)))
        cls.banked={}
        for entry,rom,words in ((CLASSIFIER,0x5986C,19),(dispatch.ENTRY,0x59234,88)):
            body=list(struct.unpack_from('>%dI'%words,cls.elf,elf_slot_offset(cls.elf,entry,words*4)))
            assert body==list(struct.unpack_from('>%dI'%words,cls.rom,rom))
            cls.banked.update({entry+i*4:word for i,word in enumerate(body)})
        cls.objects,cls.diagnostics=[],[]
        before=(cls.out/'before-source').read_text()
        for name,body in (('owner-before',before),('owner-after',screen.install(before))):
            obj,warnings=compile_owner(cls.root,cls.out,body,name)
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/(name+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=cls.root/'conker',check=True,capture_output=True)
            cls.objects.append(obj)
            cls.diagnostics.append(warnings)
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        cls.fixture='''typedef unsigned char u8; typedef unsigned short u16; typedef short s16;
typedef unsigned int u32; typedef int s32;
static u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16))),D_800BEAC0;
static u8 configurations[70][8],alternate[8],*D_8008CA4C[70];
static s32 calls,lastSlot,mutate;
static s32 narrow(s32 x) { return (s32)((u32)x&65535u)-((x&32768)?65536:0); }
s32 func_1502C3BC(s32 slot) {
    u8 *actor=D_800CC2D0+(u32)slot*0x32C; s32 identity=actor[0x136];
    if(identity>=70) identity=11;
    calls++;lastSlot=slot;
    if(mutate) { *(s16 *)(actor+0x60)=123;*(s16 *)(actor+0x62)=-321;D_8008CA4C[identity]=alternate; }
    return identity;
}
''' + screen.SELECTED+'\n'

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    @classmethod
    def link(cls,name,symbols):
        script=cls.out/('link-%s-%X.ld'%(name,symbols['D_800CC2D0']))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%screen.ENTRY)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        size=parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%size,sections(elf)['.text'][1]))

    def compare(self,memory,slot=0,symbols=LINKS[0],phase=0,identity=11,actions=(),actual=False,bodies=None):
        expected,events=reference(memory,slot,symbols,phase,identity,actions,actual)
        models=[]
        for body in bodies or (self.retail,self.raw,self.current):
            model=CounterOracle(body,memory,slot,symbols,phase,identity,actions,
                connected=self.banked if actual else None).run()
            self.assertEqual((model.memory,model.events),(expected,events))
            models.append(model)
        return models

    def test_01_complete_direct_words_and_frame(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['differences']),
            (56,0x28,0,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(self.raw,self.retail)
        self.assertEqual(self.current,self.retail)
        self.assertEqual(len(self.meta['relocations']),7)
        self.receipt('shape',words=56,frame=40,guards=0,insertions=0,omissions=0,padding=0,
            direct_exact=True,relocations=7,zero_diagnostics=True)

    def test_02_signed_wrap_all_period_bytes_and_bounded_slots(self):
        cases,coverage=0,set()
        for period,value,step in itertools.product(range(256),(-32768,-1,0,32767),(-32768,-1,0,32767)):
            model=self.compare(fixture(value=value,step=step,period=period))[0]
            coverage.update(model.visits)
            cases+=1
        for slot,enabled,disabled in itertools.product(range(26),(0,1,255),(0,1,255)):
            coverage.update(self.compare(fixture(slot,-32768,32767,255,enabled,disabled),slot,phase=0)[0].visits)
            cases+=1
        self.assertEqual(len(coverage),56)
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=len(coverage),
            all_period_bytes=True,all_bounded_slots=True,full_private_and_public_traces_exact=True,
            reserved_stack_word_unmapped=True)

    def test_03_actual_classifier_and_mutating_opaque_callback(self):
        cases=0
        for identity,phase,slot in itertools.product(range(256),(0,8),(0,25)):
            memory=fixture(slot,-30000,30001,period=127,identity=identity,phase=phase)
            if identity>=70: put(memory,screen.SYMBOLS['D_8008CA4C']+11*4,CONFIG)
            self.compare(memory,slot,phase=phase,actual=True)
            cases+=1
        for identity,phase,slot in itertools.product((0,11,69,255),(0,8),(0,25)):
            actor=screen.SYMBOLS['D_800CC2D0']+slot*0x32C
            memory=fixture(slot,32760,30,period=1,identity=identity,phase=phase)
            actions=((actor+0x60,1,2),(actor+0x62,2,2),
                (screen.SYMBOLS['D_8008CA4C']+identity*4,CONFIG+8,4),(CONFIG+12,255,1))
            self.compare(memory,slot,phase=phase,identity=identity,actions=actions)
            cases+=1
        self.receipt('callee',cases=cases,actual_banked_classifier_words=19,all_identity_bytes=True,
            opaque_mutations_cannot_reload_captures=True,fresh_configuration_read=True)

    def test_04_private_aliases_and_independent_links(self):
        cases=0
        for phase,offset in itertools.product((0,8),(0x14,0x18,0x19,0x1A,0x1B,0x20,0x21,0x22,0x23)):
            memory=fixture(value=-32768,step=32767,phase=phase)
            put(memory,screen.SYMBOLS['D_8008CA4C']+11*4,STACK+phase-0x28+offset-4)
            self.compare(memory,phase=phase)
            cases+=1
        for symbols in LINKS:
            words=self.link('selected',symbols)
            for slot,phase in itertools.product((0,25),(0,8)):
                self.compare(fixture(slot,-12345,-23456,255,symbols=symbols,phase=phase),slot,
                    symbols,phase,bodies=(words,))
                cases+=1
        for phase in (0,8):
            symbols=dict(screen.SYMBOLS,D_8008CA4C=STACK+phase-0x28+0x18-11*4)
            words=self.link('selected',symbols)
            memory=fixture(value=32760,step=20,symbols=symbols,phase=phase)
            self.compare(memory,symbols=symbols,phase=phase,bodies=(words,))
            cases+=1
        self.receipt('aliases',cases=cases,private_saved_RA_actor_and_halves_configuration_aliases=True,
            table_cell_aliases_private_actor_home=True,independent_links=5,signed_LO16_carries=True)

    def test_05_every_verified_fault_prefix(self):
        prefixes=0
        for enabled,disabled,value,phase in itertools.product((0,1),(0,1),(-32768,0,32767),(0,8)):
            memory=fixture(value=value,enabled=enabled,disabled=disabled,phase=phase)
            _,events=reference(memory,phase=phase)
            ordinal=0
            for index,event in enumerate(events):
                if event[0]=='CALL': continue
                expected=memory.copy()
                for prior in events[:index]:
                    if prior[0]=='W': put(expected,prior[1],prior[3],prior[2])
                for body in (self.retail,self.raw,self.current):
                    model=CounterOracle(body,memory,phase=phase)
                    model.fault=ordinal
                    with self.assertRaises(attachment.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args,(ordinal,))
                    self.assertEqual((model.memory,model.events),(expected,events[:index]))
                ordinal+=1
                prefixes+=1
        self.receipt('faults',prefixes=prefixes,executions=prefixes*3,actual_fault_gate_verified=True,
            complete_private_and_public_prefixes_exact=True)

    def test_06_copied_owner_and_actual_padder(self):
        self.assertEqual(self.diagnostics,[[],[]])
        old,of,orels=parse_object(self.objects[0])
        new,nf,nrels=parse_object(self.objects[1])
        self.assertEqual(of.keys(),nf.keys())
        relative=lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name in of:
            if name==screen.FUNCTION: continue
            a,b=of[name],nf[name]
            self.assertEqual((a['size'],old[a['value']:a['value']+a['size']],relative(orels,a)),
                (b['size'],new[b['value']:b['value']+b['size']],relative(nrels,b)),name)
        self.assertEqual(normalized_pools(self.objects[0]),normalized_pools(self.objects[1]))
        padded=[]
        for index,obj in enumerate(self.objects):
            name='padded-owner-%d'%index
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards',filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out/(name+'.o')))
        start=padded[1][1][screen.FUNCTION]['value']
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'],224)
        self.assertEqual(padded[0][0][:start],padded[1][0][:start])
        self.assertEqual(padded[0][0][start+224:],padded[1][0][start+224:])
        self.receipt('owner',neighbors=len(nf)-1,relative_relocations_and_pools_unchanged=True,
            only_target_padded_slot_changes=True,caller_prototype_no_neighbor_change=True)

    def test_07_actual_native32_exhaustive_signed_inputs(self):
        self.run_host('''s32 i,j,k,slot,value,step,period,want,beforeCalls;
static s32 steps[]={-32768,-257,-1,0,1,32767},periods[]={0,1,127,128,255};
for(i=0;i<70;i++) { D_8008CA4C[i]=configurations[i];configurations[i][4]=1; }
for(i=0;i<65536;i++) for(j=0;j<6;j++) for(k=0;k<5;k++) {
    value=narrow(i);step=steps[j];period=periods[k]<<8;
    *(s16 *)(D_800CC2D0+0x60)=(s16)value;*(s16 *)(D_800CC2D0+0x62)=(s16)step;
    D_800CC2D0[7]=1;configurations[0][4]=(u8)periods[k];
    want=narrow(value+step);if(want>=period) want=narrow(want-period);else if(want<0) want=narrow(want+period);
    beforeCalls=calls;func_1502C608(0);
    if(*(s16 *)(D_800CC2D0+0x60)!=want || *(s16 *)(D_800CC2D0+0x62)!=step || calls!=beforeCalls+1 || lastSlot!=0) return 1;
}
for(slot=0;slot<26;slot++) for(i=0;i<256;i++) for(j=0;j<2;j++) for(k=0;k<2;k++) {
    u8 *actor=D_800CC2D0+slot*0x32C;
    actor[7]=(u8)j;actor[0x136]=(u8)i;D_800BEAC0=(u8)k;
    *(s16 *)(actor+0x60)=32760;*(s16 *)(actor+0x62)=30;alternate[4]=255;mutate=1;
    want=narrow(32760+30);want=narrow(want+(255<<8));beforeCalls=calls;
    func_1502C608(slot);
    if(*(s16 *)(actor+0x60)!=(j&&!k?want:32760) || calls!=beforeCalls+(j&&!k) ||
        *(s16 *)(actor+0x62)!=(j&&!k?-321:30) || (j&&!k&&lastSlot!=slot)) return 2;
}''')
        self.receipt('native',cases=65536*6*5+26*256*2*2,actual_complete_C=True,
            exhaustive_value_bits=True,all_identity_bytes_and_slots=True,mutating_callback=True)

    def test_08_fresh_effective_negative_controls(self):
        count=0
        for name,body in screen.candidates():
            if not name.startswith('negative-'): continue
            _,words=screen.compile_candidate(self.root,self.out,name,body)
            memory=fixture(value=-300,step=1,period=1)
            actions=((screen.SYMBOLS['D_800CC2D0']+0x60,123,2),) if name=='negative-reload-captures' else ()
            expected,events=reference(memory,actions=actions)
            wrong=CounterOracle(words,memory,actions=actions).run()
            public=lambda m:{a:v for a,v in m.items() if not STACK-0x100<=a<STACK+0x80}
            trace=lambda es:[e for e in es if e[0]=='CALL' or not STACK-0x100<=e[1]<STACK+0x80]
            self.assertNotEqual((public(wrong.memory),trace(wrong.events)),(public(expected),trace(events)),name)
            count+=1
        self.assertEqual(count,6)
        self.receipt('negatives',fresh_effective_compiled_controls=count)

    def test_09_actual_banked_dispatcher_connection(self):
        class Connected(CounterOracle):
            def record_call(model,target):
                count=1 if target==CLASSIFIER else dispatch.COUNTS[target]
                args=model.arguments(count)
                model.calls.append((target,*args))
                model.events.append(('CALL',target,args))
            def hook(model,target):
                assert target not in (screen.ENTRY,CLASSIFIER)
                for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]
        cases=0
        caller=[self.banked[dispatch.ENTRY+i*4] for i in range(88)]
        for slot,active,disabled,enabled,identity,phase,actor_id in itertools.product((0,25),(0,1),(0,1),
                (0,1),(0,69,70,255),(0,8),(0,255)):
            memory=fixture(slot,32760,30,255,enabled,disabled,identity,phase=phase)
            actor=screen.SYMBOLS['D_800CC2D0']+slot*0x32C
            for offset,value,size in ((0,active,4),(4,actor_id,1),(5,2,1),(0x1C9,0,1),(0x1D4,0x12345678,4)):
                put(memory,actor+offset,value,size)
            if identity>=70: put(memory,screen.SYMBOLS['D_8008CA4C']+11*4,CONFIG)
            models=[]
            for body in (self.retail,self.current):
                connected=dict(self.banked)
                connected.update({screen.ENTRY+i*4:word for i,word in enumerate(body)})
                model=Connected(caller,memory,slot,phase=phase,entry=dispatch.ENTRY,
                    arguments=(actor,slot),connected=connected).run()
                self.assertEqual((screen.ENTRY,slot) in model.calls,actor_id!=255)
                self.assertEqual((CLASSIFIER,slot) in model.calls,bool(actor_id!=255 and not disabled and enabled))
                models.append(model)
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            cases+=1
        self.receipt('caller',cases=cases,actual_banked_dispatcher_words=88,actual_banked_classifier_words=19,
            actual_counter_words=56,complete_connected_traces_and_ABI_exact=True,other_callbacks_bounded_opaque=True)

    def test_10_whole_linked_installation(self):
        source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
                for name,path in self.paths.items()},self.baseline)
            self.receipt('installation',installed=False,baseline_unchanged=True)
            return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        for name in ('guards','progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes()
        expected=bytearray(before)
        struct.pack_into('>56I',expected,elf_slot_offset(before,screen.ENTRY,224),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),224)
        actual=(self.root/self.paths['elf']).read_bytes()
        em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5]
            expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_224_bytes_and_symbol_extent_changed=True,
            old_guards_and_conversion_unchanged=True,protected_data=audit)


if __name__=='__main__':
    unittest.main()
