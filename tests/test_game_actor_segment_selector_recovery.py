"""Complete segment-selector C, callback mutations, banked override and layout gates."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_actor_segment_selector_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_random_curve_record as native
from tools.tests import test_game_slot_byte_update_match as updater
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

ACTORS, MODE_TABLE, ROW_TABLE, OVERRIDE = tuple(screen.SYMBOLS.values())
STACK = updater.STACK
OUTPUT, MODES, OTHER_MODES, ROWS, OTHER_ROWS, PAIR, ANIMATION = (
    0x20000, 0x30008, 0x31008, 0x50000, 0x52000, 0x54000, 0x55000)
ANIMATION_HELPER = 0x150849A0
LINKS = ((screen.ENTRY, ACTORS, MODE_TABLE, ROW_TABLE, OVERRIDE),
    (0x15207FF0,0x80107FFC,0x80118004,0x80127FF0,0x15228004),
    (0x15308004,0x80117FFC,0x80128004,0x80137FF0,0x15327FFC),
    (0x15417FFC,0x80207FF0,0x80218004,0x80227FFC,0x15438004))


def fixture(first=1, second=2, selector=1, slot=0, identity=7, output=True,
        pair=(2,3), symbols=LINKS[0]):
    _, actors, mode_table, row_table, _ = symbols
    memory = {STACK+i:0xA5 for i in range(-0x600,0x100)}
    actor = actors+slot*0x32C
    for base, size in ((actor,0x32C),(mode_table,1024),(row_table,1024),
            (MODES-8,40),(OTHER_MODES-8,40),(ROWS,3072),(OTHER_ROWS,3072),
            (OUTPUT,96),(PAIR,2560),(ANIMATION,256)):
        memory.update({base+i:0xA5 for i in range(size)})
    for index in range(256):
        put(memory, mode_table+index*4, MODES)
        put(memory, row_table+index*4, ROWS if output else 0)
        put(memory, ROWS+index*12, 0x80100000+index*16)
        put(memory, OTHER_ROWS+index*12, 0xA5200000+index*20)
        put(memory, ANIMATION+index, 9, 1)
    for offset,value in ((4,identity),(0x68,4),(0x69,5),(0x6C,first),(0x6D,second),
            (0x6F,selector),(0x1C9,0)):
        put(memory,actor+offset,value,1)
    put(memory,actor+0x2C4,ANIMATION)
    for base, salt in ((MODES,0),(OTHER_MODES,80)):
        for index in range(24): put(memory,base+index,(index+salt)&255,1)
        put(memory,base-8,PAIR)
    for index in range(256):
        put(memory,PAIR+index*10,pair[0],1)
        put(memory,PAIR+index*10+1,pair[1],1)
    return memory


def reference(memory, slot=0, output=OUTPUT, returns=(PAIR,PAIR), actions=None,
        symbols=LINKS[0], real=False):
    result,events,calls = memory.copy(),[],[]
    _,base,mode_table,row_table,override = symbols
    actor = base+slot*0x32C
    actions = actions or {}
    def get(address,size=1):
        value = read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(address,value,size=4):
        put(result,address,value,size)
        events.append(('W',address,size,value&((1<<(size*8))-1)))
    identity,pair,selected = get(actor+4),0,[]
    for index in range(2):
        mode = get(actor+0x6C+index)
        if mode>=10:
            selected.append(mode-10)
            continue
        table = get(mode_table+identity*4,4)
        selector = get(actor+0x6F)
        selected.append(get(table+index*3+mode+8))
        if selector and not pair:
            calls.append((override,actor,selector))
            events.append(('CALL',override,(actor,selector)))
            if real:
                calls.append((ANIMATION_HELPER,actor))
                events.append(('CALL',ANIMATION_HELPER,(actor,)))
                count = get(actor+0x1C9)
                animation = get(actor+0x2C4,4)
                animation_id = get(animation+(count-1 if count else 0))
                table = get(mode_table+animation_id*4,4)
                pair = get(table-8,4) if table else 0
                if pair: pair += selector*10
            else:
                number = len(calls)-1
                for address,value,size in actions.get(number,()): store(address,value,size)
                pair = returns[number]
        if pair:
            values = [get(pair),get(pair+1)]
            table = get(mode_table+identity*4,4)
            if values[index]==get(table+index*3+10) or get(actor+0x6C+index)==0:
                selected[index] = values[index]
    rows = get(row_table+get(actor+4)*4,4)
    if rows:
        for index,command in enumerate((0xDB060018,0xDB06001C,0xDB060028,0xDB06002C)):
            store(output,command)
            selection = selected[index] if index<2 else get(actor+0x68+index-2)
            store(output+4,get(rows+selection*12,4))
            output+=8
    return result,events,calls,output


class SegmentOracle(TriangleOracle):
    def __init__(self,words,memory,slot=0,output=OUTPUT,returns=(PAIR,PAIR),actions=None,
            symbols=LINKS[0],phase=0,connected=None,entry=None,arguments=None):
        super().__init__(words,memory,entry=entry or symbols[0],phase=phase,connected=connected,
            arguments=arguments or (output,slot))
        self.override,self.results,self.actions = symbols[-1],returns,actions or {}
        self.fault=None
        self.accesses=0
    def gate(self,address):
        if STACK-0x600<=address<STACK+0x100: return
        if self.fault==self.accesses: raise AccessFault(self.accesses)
        self.accesses+=1
    def get(self,address,size):
        self.gate(address)
        assert all(address+i in self.memory for i in range(size)),('unmapped read',address,size)
        return super().get(address,size)
    def put(self,address,value,size):
        if self.recording:
            self.gate(address)
            assert all(address+i in self.memory for i in range(size)),('unmapped write',address,size)
        super().put(address,value,size)
    def record_call(self,target):
        assert target in (self.override,ANIMATION_HELPER)
        args = self.arguments(2 if target==self.override else 1)
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))
    def hook(self,target):
        assert target==self.override
        number = len(self.calls)-1
        for address,value,size in self.actions.get(number,()): self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.results[number]


class AccessFault(Exception):
    pass


def public(events):
    return [e for e in events if e[0]=='CALL' or not STACK-0x600<=e[1]<STACK+0x100]


def public_memory(memory):
    return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x100}


class GameActorSegmentSelectorRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-segment-selector-recovery-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>146I',cls.rom,screen.ROM))
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
        elf=(cls.root/cls.paths['elf']).read_bytes()
        cls.helpers={}
        for entry,rom,size in ((OVERRIDE,0xABDB8,96),(ANIMATION_HELPER,0xB1E50,44)):
            words=list(struct.unpack_from('>%dI'%(size//4),elf,elf_slot_offset(elf,entry,size)))
            assert words==list(struct.unpack_from('>%dI'%(size//4),cls.rom,rom))
            cls.helpers.update({entry+i*4:w for i,w in enumerate(words)})
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        sdk='#include <PR/mbi.h>\n#include <PR/gbi.h>\n'
        cls.fixture=sdk+'\n#define NULL ((void *)0)\n'+screen.TYPES+'''
static u8 D_800CC2D0[26*0x32C];
static u8 modes[256][24], *D_800D1C90[256], pair[2];
static ActorSegmentRow58F80 rows[256], otherRows[256], *D_800C5338[256];
static Gfx output[8];
static s32 wantedSlot, calls, mutation, failFirst, error;
u8 *func_1507E908(u8 *actor,s32 selector) {
    if(actor!=D_800CC2D0+wantedSlot*0x32C || selector!=1) error=1;
    calls++;
    if(mutation) { actor[4]=8; actor[0x6C]=0; D_800C5338[8]=otherRows; }
    return failFirst && calls==1 ? NULL : pair;
}
'''+screen.SELECTED+'\n'
        cls.fixture=subprocess.run(['cc','-m32','-E','-P','-D_LANGUAGE_C','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',
            '-I',str(cls.root/'conker/include/2.0L'),'-xc','-'],input=cls.fixture,
            capture_output=True,text=True,check=True).stdout

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,slot=0,output=OUTPUT,returns=(PAIR,PAIR),actions=None,
            symbols=LINKS[0],phase=0,words=None,real=False):
        expected,events,calls,result=reference(memory,slot,output,returns,actions,symbols,real)
        models=[]
        for body in (words or self.words,self.retail):
            model=SegmentOracle(body,memory,slot,output,returns,actions,symbols,phase,
                connected=self.helpers if real else None).run()
            self.assertEqual(public_memory(model.memory),public_memory(expected))
            self.assertEqual(public(model.events),events)
            self.assertEqual(model.calls,calls)
            self.assertEqual(model.r[2],result)
            models.append(model)
        return models

    def test_01_profiles_extent_and_original_frame_gate(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes']), (149,144,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(self.words[0],0x27BDFF70)
        self.assertEqual(self.retail[0],0x27BDFF78)
        with self.assertRaisesRegex(ValueError,'retail span'):
            emit_padded_assembly(self.objects[1],self.root/'conker/asm/58F80.s',
                word_patches_path=self.root/self.paths['guards'],filename='generated_58F80')
        self.receipt('shape',words=149,retail_words=146,frame=144,retail_frame=136,
            differences=self.meta['differences'],pool_bytes=0,installation_rejected=True)

    def test_02_all_bytes_nulls_and_mutating_callbacks(self):
        cases=0
        inputs=[]
        for first,second,selector,enabled in itertools.product((0,1,2,9,10,11,15,255),
                (0,1,2,9,10,11,15,255),(0,1,255),(False,True)):
            inputs.append((fixture(first,second,selector,output=enabled),0,OUTPUT,(PAIR,PAIR),None))
        for value in range(256):
            inputs.append((fixture(value,1,pair=(value,255-value)),0,OUTPUT,(PAIR,PAIR),None))
            inputs.append((fixture(1,value,pair=(255-value,value)),0,OUTPUT,(PAIR,PAIR),None))
        for slot,first,second in itertools.product((0,12,25),(0,1,9),(0,1,9)):
            actor=ACTORS+slot*0x32C
            for result in ((0,0),(0,PAIR),(PAIR,0)):
                actions={0:((actor+4,8,1),(actor+0x6C,0,1),(actor+0x6D,0,1),
                    (MODE_TABLE+7*4,OTHER_MODES,4),(ROW_TABLE+8*4,OTHER_ROWS,4))}
                inputs.append((fixture(first,second,slot=slot),slot,OUTPUT,result,actions))
        for first,second,selector,returns in itertools.product((0,1,9),(0,1,9),(0,255),((0,PAIR),(PAIR,PAIR))):
            actions={0:((ACTORS+0x6F,selector,1),(PAIR,10,1),(PAIR+1,13,1))}
            inputs.append((fixture(first,second),0,OUTPUT,returns,actions))
        coverage=set()
        for memory,slot,output,returns,actions in inputs:
            models=self.compare(memory,slot,output,returns,actions,phase=(cases%2)*8)
            coverage.update(models[1].visits)
            cases+=1
        self.receipt('guest',cases=cases,executions=cases*2,retail_words_reached=len(coverage),
            public_memory_accesses_calls_and_cursor_exact=True,complete_private_frame_not_yet_exact=True)

    def test_03_output_aliases_and_pair_aliases(self):
        cases=0
        for first,second,alias in itertools.product((0,1,9,10,255),(0,2,9,10),
                (OUTPUT,ACTORS+0x68,ACTORS+0x60,ROWS,ROWS+4,ROWS+12,MODES-8)):
            for pair in (PAIR,ACTORS+0x68,OUTPUT):
                self.compare(fixture(first,second),output=alias,returns=(pair,pair))
                cases+=1
        self.receipt('aliases',cases=cases,executions=cases*2,ordered_output_table_and_actor_reads=True)

    def test_04_real_banked_override_and_animation_reader(self):
        cases=0
        for slot,count,selector,mode,kind in itertools.product((0,25),(0,1,2,255),
                (0,1,2,255),(0,1,9,10),(0,1,2)):
            memory=fixture(mode,1,selector,slot,pair=(10,13))
            put(memory,ACTORS+slot*0x32C+0x1C9,count,1)
            if kind==1: put(memory,MODE_TABLE+9*4,0)
            if kind==2: put(memory,MODES-8,0)
            self.compare(memory,slot=slot,real=True)
            cases+=1
        self.receipt('callees',cases=cases,executions=cases*2,override_words=24,animation_words=11,
            actual_banked_callees=True,no_opaque_callback_substitution=True)

    def test_05_independent_links_signed_low_carries(self):
        cases=0
        original_obj=self.out/'original.o'
        assembly=(self.root/'conker/asm/58F80.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        original_asm=self.out/'original.s'
        original_asm.write_text('.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n'+
            screen.FUNCTION+':\n'+assembly+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(original_obj),str(original_asm)],
            check=True,capture_output=True)
        for symbols in LINKS:
            linked=[]
            for name,obj,count in (('raw',self.out/'selected.o',149),('original',original_obj,146)):
                script=self.out/('link-%s-%X.ld'%(name,symbols[0]))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%symbols[0])
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%(key,value) for key,value in zip(screen.SYMBOLS,symbols[1:])],
                    '-o',str(elf),str(obj)],check=True,capture_output=True)
                linked.append(list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1])))
            for first,second in itertools.product((0,1,9,10),(0,2,10)):
                memory=fixture(first,second,symbols=symbols)
                expected,events,calls,result=reference(memory,symbols=symbols)
                for words in linked:
                    model=SegmentOracle(words,memory,symbols=symbols).run()
                    self.assertEqual(public_memory(model.memory),public_memory(expected))
                    self.assertEqual(public(model.events),events)
                    self.assertEqual((model.calls,model.r[2]),(calls,result))
                cases+=1
        self.receipt('rebases',links=8,symbol_sets=4,cases=cases,signed_low_carry=True)

    def test_06_copied_owner_and_unchanged_production(self):
        self.assertEqual(self.diagnostics,[[],[]])
        old,of,orels=parse_object(self.objects[0])
        new,nf,nrels=parse_object(self.objects[1])
        neighbors=set(of)-{screen.FUNCTION}
        self.assertEqual(of.keys(),nf.keys())
        relative=lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name in neighbors:
            a,b=of[name],nf[name]
            self.assertEqual((a['size'],old[a['value']:a['value']+a['size']],relative(orels,a)),
                (b['size'],new[b['value']:b['value']+b['size']],relative(nrels,b)),name)
        self.assertEqual(normalized_pools(self.objects[0]),normalized_pools(self.objects[1]))
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name],name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(data['exact'])
        self.receipt('owner',neighbors=len(neighbors),zero_diagnostics=True,pools_unchanged=True,
            production_source_ELF_guards_conversion_rows_unchanged=True,protected_data=data)

    def test_07_actual_native32_with_SDK_macro(self):
        self.run_host('''
int slot,a,b,m,f,i,j; u32 expected[8]; u8 *actor; Gfx *end;
for(i=0;i<256;i++) {
    D_800D1C90[i]=modes[i]; D_800C5338[i]=rows;
    rows[i].address=0x80100000+i*16; otherRows[i].address=0xA5200000+i*20;
    for(j=0;j<24;j++) modes[i][j]=j;
}
for(slot=0;slot<26;slot++) for(a=0;a<256;a++) for(b=0;b<256;b+=17)
for(m=0;m<2;m++) for(f=0;f<2;f++) {
    wantedSlot=slot; actor=D_800CC2D0+slot*0x32C;
    actor[4]=7; actor[0x6C]=a; actor[0x6D]=b; actor[0x6F]=1;
    actor[0x68]=4; actor[0x69]=5;
    calls=error=0; mutation=m; failFirst=f; pair[0]=10; pair[1]=13;
    for(i=0;i<8;i++) output[i].words.w0=output[i].words.w1=0xA5A5A5A5;
    { int first=a, second=b, called=0, pairReady=0, id=7, selections[2];
      for(i=0;i<2;i++) {
        int mode=i?second:first;
        if(mode>=10) selections[i]=mode-10;
        else {
          selections[i]=i*3+mode+8;
          if(!pairReady) {called++; if(m) {id=8;first=0;} pairReady=!(f&&called==1);}
          if(pairReady && ((i?13:10)==i*3+10 || (i?second:first)==0)) selections[i]=i?13:10;
        }
      }
      for(i=0;i<4;i++) {int selection=i<2?selections[i]:i+2;
        expected[i*2]=(u32[]){0xDB060018,0xDB06001C,0xDB060028,0xDB06002C}[i];
        expected[i*2+1]=id==8 ? otherRows[selection].address : rows[selection].address;}
      end=func_1502F01C(output,slot);
      if(end!=output+4 || calls!=called || error) return 1;
    }
    for(i=0;i<4;i++) if(output[i].words.w0!=expected[i*2] || output[i].words.w1!=expected[i*2+1]) return 2;
    for(i=4;i<8;i++) if(output[i].words.w0!=0xA5A5A5A5 || output[i].words.w1!=0xA5A5A5A5) return 3;
}
''')
        self.receipt('native',cases=26*256*16*4,actual_complete_C=True,actual_SDK_segment_macro=True,
            all_bounded_slots=True,callback_mutations_and_NULL_retry=True)

    def test_08_fresh_effective_complete_negative_controls(self):
        checks=(('negative-cached-final-id',fixture(),{0:((ACTORS+4,8,1),(ROW_TABLE+8*4,OTHER_ROWS,4))},(PAIR,PAIR)),
            ('negative-reloaded-loop-id',fixture(1,1),{0:((ACTORS+4,8,1),(MODE_TABLE+8*4,OTHER_MODES,4))},(PAIR,PAIR)),
            ('negative-second-call',fixture(1,0),None,(0,PAIR)),
            ('negative-no-zero-override',fixture(1,1),{0:((ACTORS+0x6C,0,1),)},(PAIR,PAIR)),
            ('negative-first-pair-only',fixture(1,1,pair=(10,13)),None,(PAIR,PAIR)),
            ('negative-segment',fixture(),None,(PAIR,PAIR)),
            ('negative-one-iteration',fixture(1,11),None,(PAIR,PAIR)))
        bodies=dict(screen.candidates())
        for name,memory,actions,returns in checks:
            _,words=screen.compile_candidate(self.root,self.out,name,bodies[name])
            expected,events,calls,result=reference(memory,actions=actions,returns=returns)
            actual=SegmentOracle(words,memory,actions=actions,returns=returns).run()
            self.assertNotEqual((public_memory(actual.memory),public(actual.events),actual.calls,actual.r[2]),
                (public_memory(expected),events,calls,result),name)
            self.compare(memory,actions=actions,returns=returns)
        self.receipt('negatives',fresh_complete_compiled=len(checks),effective=len(checks))

    def test_09_verified_public_fault_prefixes(self):
        cases=0
        for first,second,returns in itertools.product((0,9,10),(0,9,10),((0,PAIR),(PAIR,PAIR))):
            memory=fixture(first,second)
            complete=SegmentOracle(self.retail,memory,returns=returns).run()
            events=public(complete.events)
            for index,event in enumerate(events):
                if event[0]=='CALL': continue
                fault=sum(e[0]!='CALL' for e in events[:index])
                expected=public_memory(memory)
                for prior in events[:index]:
                    if prior[0]=='W': put(expected,prior[1],prior[3],prior[2])
                for words in (self.retail,self.words):
                    model=SegmentOracle(words,memory,returns=returns)
                    model.fault=fault
                    with self.assertRaises(AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args,(fault,))
                    self.assertEqual(public(model.events),events[:index])
                    self.assertEqual(public_memory(model.memory),expected)
                cases+=1
        self.receipt('faults',prefixes=cases,executions=cases*2,gates_verified=True,
            complete_public_memory_and_access_prefix=True,private_stack_not_yet_certified=True)


if __name__=='__main__':
    unittest.main()
