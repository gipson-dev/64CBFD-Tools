"""Lazy endpoint gates, byte transitions, callee mutation and scoped restoration."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_state_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly, ELF_HEADER, SECTION_HEADER, SYMBOL
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_descriptor_match import size_field
from tools.tests import test_game_random_curve_record as native

ACTOR, FIRST, SECOND, TABLE, RELEASE = 0x20000, 0x22000, 0x24000, 0x800CC2D0, 0x1516972C
HELPERS = ((0x151B2348, 0x1DF7F8, 210), (0x151B2690, 0x1DFB40, 176))
INSERT = screen.DECLARATIONS + '\n'
RETURNS = (0, 1, 2, 3, 255, 0xFFFFFFFF, 0x102)
MUTATIONS = ((None,None), (1,0), (2,255), (0,1), (1,2), (255,255))


def restoration(function):
    return '#pragma GLOBAL_ASM("asm/nonmatchings/generated_1DF510/%s.s")' % function


def sources(source):
    before = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '')
    for entry, _, _ in HELPERS:
        function = 'func_%08X' % entry
        before = before.replace(restoration(function), 's32 %s() {\n    return 0;\n}' % function)
    assert before.count(screen.ORIGINAL) == 1
    after = before.replace('/* Non-matching placeholders', INSERT + '/* Non-matching placeholders', 1).replace(
        screen.ORIGINAL, screen.SELECTED)
    for entry, _, _ in HELPERS:
        function = 'func_%08X' % entry
        after = after.replace('s32 %s() {\n    return 0;\n}' % function, restoration(function))
    return before, after


def fixture(previous=0, gate=0, layout=0, seed=0, connected=False):
    first = TABLE + 3 * 0x32C if connected else ACTOR if layout == 2 else FIRST
    second = first if layout == 1 else ACTOR if layout == 3 else SECOND
    memory = {STACK+i:(i*17+seed*13+0xA5)&255 for i in range(-0x300,0x140)}
    for base in (ACTOR, first, second):
        memory.update({base+i:(i*11+seed*7+0x5A)&255 for i in range(-16,0x120)})
    for base in (first,second):
        put(memory,base,0x80000001);put(memory,base+4,7,1);put(memory,base+0x3B,0xA7,1)
    put(memory,ACTOR+0x28,first);put(memory,ACTOR+0x30,second)
    put(memory,ACTOR+0x2C,0xA7,1);put(memory,ACTOR+0x34,0xA7,1)
    put(memory,ACTOR+0x35,previous,1);put(memory,ACTOR+0xE,0x7BCD,2)
    if gate==1:put(memory,first,0)
    elif gate==2:put(memory,first+4,255,1)
    elif gate==3:put(memory,ACTOR+0x2C,0xA6,1)
    elif gate==4:put(memory,second,0)
    elif gate==5:put(memory,second+4,255,1)
    elif gate==6:put(memory,ACTOR+0x34,0xA6,1)
    return memory


def read(memory,address,size=4):
    return int.from_bytes(bytes(memory[address+i] for i in range(size)), 'big')


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x140}


def metadata(data):
    header=ELF_HEADER.unpack_from(data)
    sections=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
    table=[s for s in sections if s[1]==2]
    assert len(table)==1
    table=table[0];strings=sections[table[6]]
    names=data[strings[4]:strings[4]+strings[5]]
    symbols=[]
    for offset in range(table[4],table[4]+table[5],table[9]):
        value=SYMBOL.unpack_from(data,offset)
        name=names[value[0]:].split(b'\0',1)[0]
        symbols.append((name,*value[1:]))
    return header,sections,Counter(symbols),Counter(names.split(b'\0')),table,strings


def reference(memory,result,cleanup=None,setup=None,mutate=True):
    memory=public(memory)
    first,second=read(memory,ACTOR+0x28),read(memory,ACTOR+0x30)
    calls=[]
    if (read(memory,first)==0 or read(memory,first+4,1)==255 or
            read(memory,ACTOR+0x2C,1)!=read(memory,first+0x3B,1) or
            read(memory,second)==0 or read(memory,second+4,1)==255 or
            read(memory,ACTOR+0x34,1)!=read(memory,second+0x3B,1)):
        put(memory,ACTOR+0xE,0xFFFF,2)
        return memory,calls
    old=read(memory,ACTOR+0x35,1)
    calls.append(('classify',ACTOR))
    if mutate:
        put(memory,ACTOR+0x35,0x77,1);put(memory,ACTOR+0x28,0);put(memory,ACTOR+0x30,0)
    put(memory,ACTOR+0x35,result&255,1)
    if old!=(result&255):
        calls.append(('cleanup',ACTOR))
        if cleanup is not None:put(memory,ACTOR+0x35,cleanup,1)
        if read(memory,ACTOR+0x35,1)==1:
            calls.append(('setup',ACTOR))
            if setup is not None:put(memory,ACTOR+0x35,setup,1)
        if read(memory,ACTOR+0x35,1) in (0,2):calls.append(('alternate',ACTOR))
    return memory,calls


class StateOracle(TriangleOracle):
    def __init__(self,words,memory,result=2,cleanup=None,setup=None,mutate=True,
            phase=0,entry=screen.ENTRY,symbols=None,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(ACTOR,),connected=connected)
        self.result,self.cleanup,self.setup,self.mutate=result,cleanup,setup,mutate
        self.symbols=symbols or screen.SYMBOLS
        self.records=[]

    def execute(self,word):
        if word>>26==32:
            rs,rt,imm=word>>21&31,word>>16&31,word&65535
            address=(self.r[rs]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
            value=self.get(address,1)
            self.r[rt]=(value if value<128 else value-256)&0xFFFFFFFF
            self.r[0]=0
        else:super().execute(word)

    def get(self,address,size):
        if address%size:raise KeyError(('unaligned-read',address,size))
        if any(address+i not in self.memory for i in range(size)):raise KeyError(('read',address,size))
        return super().get(address,size)

    def put(self,address,value,size):
        if self.recording and (address%size or any(address+i not in self.memory for i in range(size))):
            raise KeyError(('write',address,size))
        super().put(address,value,size)

    def record_call(self,target):
        roles=('classify','cleanup','setup','alternate')
        role=next((role for role,(_,address) in zip(roles,self.symbols.items()) if address==target),None)
        if target==RELEASE:role='release'
        if target==screen.ENTRY:role='callback'
        assert role is not None, ('unexpected-call',hex(target))
        if role!='release':assert self.r[4]==ACTOR, ('actor-argument',self.r[4])
        self.records.append((role,self.r[4]))

    def hook(self,target):
        role=self.records[-1][0]
        result=0xDEADBEEF
        if role=='classify':
            if self.mutate:
                self.put(ACTOR+0x35,0x77,1);self.put(ACTOR+0x28,0,4);self.put(ACTOR+0x30,0,4)
            result=self.result
        elif role=='cleanup' and self.cleanup is not None:self.put(ACTOR+0x35,self.cleanup,1)
        elif role=='setup' and self.setup is not None:self.put(ACTOR+0x35,self.setup,1)
        elif role=='release':
            # A freed record may rewrite the next attachment: the cleanup loop must reread it.
            if self.r[4]==0x26000:self.put(ACTOR+0x3C,0x29000,4)
        for i in range(4):self.put(self.r[29]+i*4,0xA5000100+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result


class GameOwnerStateTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-state-test'
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>67I',cls.rom,screen.ROM))
        cls.directory=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        if not (cls.out/'baseline.json').exists() and screen.ORIGINAL in (cls.root/screen.SOURCE).read_text():
            hashes={}
            for name,path in dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
                    guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,memory,result=2,cleanup=None,setup=None,phase=0,words=None,entry=screen.ENTRY,symbols=None):
        expected=reference(memory,result,cleanup,setup)
        outcomes=[]
        for body in (self.retail if entry==screen.ENTRY else words, words or self.words):
            model=StateOracle(body,memory,result,cleanup,setup,phase=phase,entry=entry,symbols=symbols).run()
            self.assertEqual((public(model.memory),model.records),expected)
            outcomes.append((model.memory,model.events,model.records));last=model
        self.assertEqual(outcomes[0],outcomes[1])
        return last

    def test_01_direct_shape_profiles_and_restoration_extents(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences','pool_bytes')), (67,56,0,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(sum(map(len,self.meta['relocations'].values())),4)
        targets={screen.FUNCTION,'func_151B2348','func_151B2690'}
        with (self.root/'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(row['function'] in targets for row in csv.DictReader(stream)))
        profiles=[]
        for profile in ('o2g3','o2','o1g3','o1'):
            meta,_=screen.compile_candidate(self.root,self.out,'profile-'+profile,profile=profile);profiles.append(meta)
        from unittest.mock import patch
        with patch.object(screen,'DECLARATIONS',screen.DECLARATIONS.replace('void func_151B2348(u8 *);',
                's32 func_151B2348();').replace('void func_151B2690(u8 *);','s32 func_151B2690();')):
            false_contract,_=screen.compile_candidate(self.root,self.out,'false-return-contract')
        self.assertEqual((false_contract['body_words'],false_contract['frame'],false_contract['differences']),(67,56,21))
        for entry,_,_ in HELPERS:
            name='func_%08X'%entry
            assembly=(self.root/'conker/asm/1DF510.s').read_text().split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]
            fragment=(self.root/('conker/asm/nonmatchings/generated_1DF510/'+name+'.s')).read_text()
            self.assertEqual(fragment.strip(),('glabel '+name+'\n'+assembly).strip())
        self.receipt('shape',dict(words=67,frame=56,guards=0,profiles=profiles,false_return_contract=false_contract,
            restored_helper_words=[210,176]))

    def test_02_all_previous_bytes_return_width_mutation_and_aliases(self):
        seen,count=set(),0
        for previous,result,mutation,phase in itertools.product(range(256),RETURNS,MUTATIONS,(0,8)):
            memory=fixture(previous,layout=count%4,seed=count%3)
            model=self.compare(memory,result,*mutation,phase=phase)
            seen.update(model.visits);count+=1
        for gate,layout,phase in itertools.product(range(1,7),range(4),(0,8)):
            model=self.compare(fixture(0xFE,gate,layout),0x101,1,0,phase)
            seen.update(model.visits);count+=1
        # The duplicate old-state load at +0x80 is unreachable after the unconditional invalid branch.
        self.assertEqual(set(range(screen.ENTRY,screen.ENTRY+268,4))-seen,{screen.ENTRY+0x80})
        self.receipt('guest',dict(cases=count,executions=count*2,reached_words=len(seen),unreachable_word=hex(screen.ENTRY+0x80),
            all_previous_bytes=True,truncated_returns=list(RETURNS),aliases=4,callee_mutation=True,scratch_and_argument_home_clobbers=True))

    def test_03_actual_classifier_and_cleanup_live_attachment_chain(self):
        classifier=list(struct.unpack_from('>21I',self.rom,0x1DF7A4))
        cleanup=list(struct.unpack_from('>28I',self.rom,0x1DF6DC))
        connected={entry+i*4:word for entry,body in ((0x151B22F4,classifier),(0x151B222C,cleanup)) for i,word in enumerate(body)}
        count=0
        for old,index,active,setup,phase in itertools.product((0,1,2,255),(3,4),(0,1),(None,0,2),(0,8)):
            memory=fixture(old,connected=True)
            put(memory,SECOND+0x65,index+1,1);put(memory,SECOND+0x5C,active)
            attachments=(0x26000,0x27000,0,0x28000)
            for i,value in enumerate(attachments):put(memory,ACTOR+0x38+i*4,value)
            result=1 if index==3 and active==1 else 2
            expected=public(memory);calls=[('classify',ACTOR)]
            put(expected,ACTOR+0x35,result,1)
            if old!=result:
                calls += [('cleanup',ACTOR),('release',0x26000),('release',0x29000),('release',0x28000)]
                put(expected,ACTOR+0x3C,0x29000)
                if result==1:
                    calls.append(('setup',ACTOR))
                    if setup is not None:put(expected,ACTOR+0x35,setup,1)
                if read(expected,ACTOR+0x35,1) in (0,2):calls.append(('alternate',ACTOR))
            outcomes=[]
            for body in (self.retail,self.words):
                model=StateOracle(body,memory,setup=setup,mutate=False,phase=phase,connected=connected).run()
                self.assertEqual((public(model.memory),model.records),(expected,calls))
                outcomes.append((model.memory,model.events,model.records))
            self.assertEqual(outcomes[0],outcomes[1]);count+=1
        self.receipt('connected',dict(cases=count,actual_classifier_words=21,actual_cleanup_words=28,
            live_later_attachment_rewrite=True,release_setup_alternate_bounded_hooks=True))

    def test_04_actual_native32_typed_callback(self):
        self.fixture='''typedef unsigned char u8;typedef short s16;typedef int s32;
typedef unsigned int u32;
static union { u32 alignment;u8 bytes[512]; } actorStore, firstStore, secondStore;
static u8 *actor=actorStore.bytes+16,*first,*second;
static s32 resultWord;static int cleanupState,setupState,error,count;static u8 sequence[4];
s32 func_151B22F4(u8 *a) {
    if(a!=actor || count)error=1;
    sequence[count++]=1;
    a[0x35]=0x77;*(u8 **)(a+0x28)=0;*(u8 **)(a+0x30)=0;return resultWord;
}
void func_151B222C(u8 *a) {
    if(a!=actor)error=2;
    sequence[count++]=2;
    if(cleanupState>=0)a[0x35]=(u8)cleanupState;
}
void func_151B2348(u8 *a) {
    if(a!=actor)error=3;
    sequence[count++]=3;
    if(setupState>=0)a[0x35]=(u8)setupState;
}
void func_151B2690(u8 *a) { if(a!=actor)error=4;sequence[count++]=4; }
'''+screen.SELECTED+'''
static void (*callback)(u8 *)=func_151B2100;
'''
        self.run_host('''
static u32 values[]={0,1,2,3,255,0xffffffffu,0x102};
union { u32 alignment;u8 bytes[512]; } expectedStore;
u32 old,r,gate,layout,mode,i;u8 *expected=expectedStore.bytes;
u8 firstExpected[512],secondExpected[512],events[4],state;int n,valid;
for(old=0;old<256;old++)for(r=0;r<7;r++)for(gate=0;gate<7;gate++)
for(layout=0;layout<4;layout++)for(mode=0;mode<3;mode++) {
    for(i=0;i<512;i++){actorStore.bytes[i]=0x5a;firstStore.bytes[i]=0xa5;secondStore.bytes[i]=0xa5;}
    first=layout==2?actor:firstStore.bytes+16;
    second=layout==1?first:layout==3?actor:secondStore.bytes+16;
    *(s32 *)first=*(s32 *)second=1;first[4]=second[4]=7;first[0x3b]=second[0x3b]=0xa7;
    *(u8 **)(actor+0x28)=first;*(u8 **)(actor+0x30)=second;
    actor[0x2c]=actor[0x34]=0xa7;actor[0x35]=(u8)old;*(s16 *)(actor+0xe)=0x7bcd;
    if(gate==1)*(s32 *)first=0;else if(gate==2)first[4]=255;
    else if(gate==3)actor[0x2c]=0xa6;else if(gate==4)*(s32 *)second=0;
    else if(gate==5)second[4]=255;else if(gate==6)actor[0x34]=0xa6;
    for(i=0;i<512;i++) {
        expected[i]=actorStore.bytes[i];firstExpected[i]=firstStore.bytes[i];secondExpected[i]=secondStore.bytes[i];
    }
    valid=*(s32 *)first && first[4]!=255 && actor[0x2c]==first[0x3b] &&
        *(s32 *)second && second[4]!=255 && actor[0x34]==second[0x3b];
    resultWord=(s32)values[r];cleanupState=mode==0?-1:mode==1?1:0;setupState=mode==1?2:-1;
    n=0;
    if(!valid)*(s16 *)(expected+16+0xe)=-1;
    else {
        events[n++]=1;*(u8 **)(expected+16+0x28)=0;*(u8 **)(expected+16+0x30)=0;
        state=(u8)resultWord;
        if(old!=state) {
            events[n++]=2;if(cleanupState>=0)state=(u8)cleanupState;
            if(state==1){events[n++]=3;if(setupState>=0)state=(u8)setupState;}
            if(state==0 || state==2)events[n++]=4;
        }
        expected[16+0x35]=state;
    }
    count=error=0;callback(actor);
    if(error || count!=n)return 1;
    for(i=0;i<(u32)n;i++)if(sequence[i]!=events[i])return 2;
    for(i=0;i<512;i++)if(actorStore.bytes[i]!=expected[i])return 3;
    for(i=0;i<512;i++) {
        if(firstStore.bytes[i]!=firstExpected[i] || secondStore.bytes[i]!=secondExpected[i])return 4;
    }
}
''')
        self.receipt('native',dict(cases=256*7*7*4*3,actual_native32=True,typed_void_callback=True,
            full_actor_canaries=True,all_previous_bytes=True,aliases=4,bounded_helpers=True))

    def test_05_copied_owner_padder_and_only_declared_restorations(self):
        before,after=sources((self.root/screen.SOURCE).read_text())
        objects,warnings=[],[]
        for name,text in (('before',before),('after',after)):
            obj,diagnostics=compile_owner(self.root,self.out,text,name)
            if name=='after':
                subprocess.run([sys.executable,str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                    str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj),
                    '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                    cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj);warnings.append(diagnostics)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(len(warnings[0]),4)
        old,old_fn,old_rel=parse_object(objects[0]);new,new_fn,new_rel=parse_object(objects[1])
        changed={screen.FUNCTION,'func_151B2348','func_151B2690'}
        self.assertEqual(old_fn.keys(),new_fn.keys())
        for name,function in new_fn.items():
            if name in changed:continue
            prior=old_fn[name]
            self.assertEqual((function['size'],new[function['value']:function['value']+function['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-function['value']:r for o,r in new_rel.items() if function['value']<=o<function['value']+function['size']},
                {o-prior['value']:r for o,r in old_rel.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertTrue(emit_padded_assembly(objects[1],self.root/'conker/asm/1DF510.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_1DF510'))
        self.receipt('owner',dict(unchanged_neighbors=len(new_fn)-3,unchanged_pools_relative_relocations=True,
            existing_diagnostics=4,new_diagnostics=0,padder_accepts=True,only_target_and_two_asm_restorations=True))

    def test_06_compiled_effective_negative_controls(self):
        negatives={
            'wrong-first-sentinel':screen.SELECTED.replace('first[4] == 255','first[4] == 254'),
            'wrong-code':screen.SELECTED.replace('pair[12] != second[0x3B]','pair[12] != second[0x3A]'),
            'early-classify':screen.SELECTED.replace('        previous = pair[13];\n        pair[13] = func_151B22F4(actor);',
                '        s32 state = func_151B22F4(actor);\n        previous = pair[13];\n        pair[13] = state;'),
            'no-cleanup':screen.SELECTED.replace('            func_151B222C(actor);\n',''),
            'else-if-alternate':screen.SELECTED.replace('            if (pair[13] == 2','            else if (pair[13] == 2'),
            'wrong-invalidation':screen.SELECTED.replace('*(s16 *)(actor + 0xE) = -1','*(s16 *)(actor + 0xE) = 0')}
        rejected=[]
        for name,body in negatives.items():
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            mismatch=False
            for memory,result,cleanup,setup in ((fixture(0,2),2,None,None),(fixture(0),1,None,2),
                    (fixture(0x77),1,2,None),(fixture(0),0x77,None,None),
                    (fixture(0,6),2,None,None),(fixture(0,1),2,None,None)):
                model=StateOracle(words,memory,result,cleanup,setup).run()
                if (public(model.memory),model.records)!=reference(memory,result,cleanup,setup):mismatch=True
            self.assertTrue(mismatch,name);rejected.append(name)
        self.receipt('negatives',dict(compiled_effective=rejected,no_arbitrary_oracle_assertions_accepted=True))

    def test_07_lazy_invalid_gates_and_fault_prefixes(self):
        count=0
        for gate in range(1,7):
            memory=fixture(0xFF,gate)
            # Delete fields that only later validation steps would read.
            cut=(FIRST+4,FIRST+0x3B,SECOND,SECOND+4,SECOND+0x3B,ACTOR+0x35)[gate-1]
            for i in range(4 if gate==3 else 1):memory.pop(cut+i,None)
            self.compare(memory);count+=1
        pairs=0
        for layout in range(4):
            memory=fixture(0xFF,layout=layout)
            addresses=[ACTOR+0x28,ACTOR+0x30,read(memory,ACTOR+0x28),read(memory,ACTOR+0x28)+4,
                ACTOR+0x2C,read(memory,ACTOR+0x28)+0x3B,read(memory,ACTOR+0x30),
                read(memory,ACTOR+0x30)+4,ACTOR+0x34,read(memory,ACTOR+0x30)+0x3B,ACTOR+0x35]
            for address in addresses:
                broken=memory.copy();del broken[address];outcomes=[]
                for body in (self.words,self.retail):
                    model=StateOracle(body,broken)
                    with self.assertRaises(KeyError):model.run()
                    outcomes.append((model.memory,model.events,model.records))
                self.assertEqual(outcomes[0],outcomes[1]);pairs+=1
        self.receipt('faults',dict(lazy_invalid_cases=count,missing_byte_pairs=pairs,
            guest_order_only_not_portable_C_or_hardware_fault_proof=True))

    def test_08_independent_relocations_and_links(self):
        assembly=(self.root/'conker/asm/1DF510.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        path=self.out/'original.s';obj=self.out/'original.o'
        path.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\nglabel '+screen.FUNCTION+'\n'+assembly)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],cwd=self.root,check=True,capture_output=True)
        self.assertEqual(parse_object(obj)[2],parse_object(self.out/'selected.o')[2])
        count=0
        for variant,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if variant==0 else {name:(entry&0xF0000000)+0x100800+i*0x100 for i,name in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,object_path in (('original',obj),('candidate',self.out/'selected.o')):
                elf=self.out/('rebase-%d-%s.elf'%(variant,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(object_path)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>67I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[1])
            for previous,result,phase in itertools.product((0,1,2,255),(0,1,2,0x101,0xFFFFFFFF),(0,8)):
                expected=reference(fixture(previous),result,1,2)
                outcomes=[]
                for body in bodies:
                    model=StateOracle(body,fixture(previous),result,1,2,phase=phase,entry=entry,symbols=symbols).run()
                    self.assertEqual((public(model.memory),model.records),expected)
                    outcomes.append((model.memory,model.events,model.records))
                self.assertEqual(outcomes[0],outcomes[1]);count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=8,relocation_uses=4,cases=count,executions=count*2))

    def test_09_whole_ELF_only_target_and_two_restored_helpers(self):
        current=(self.root/'conker/build/conker.us.elf').read_bytes()
        if not (self.out/'baseline.json').exists():self.skipTest('immutable pre-install baseline absent')
        baseline=json.loads((self.out/'baseline.json').read_text());before=(self.out/'before-elf').read_bytes()
        for name,digest in baseline.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),digest)
        installed=screen.SELECTED in (self.root/screen.SOURCE).read_text()
        expected=bytearray(before);allowed=[]
        if installed:
            from unittest.mock import patch
            for entry,rom,words in ((screen.ENTRY,screen.ROM,67),*HELPERS):
                length=words*4;offset=elf_slot_offset(before,entry,length)
                expected[offset:offset+length]=self.rom[rom:rom+length]
                with patch('tools.tests.test_game_owner_descriptor_match.screen.FUNCTION','func_%08X'%entry), \
                        patch('tools.tests.test_game_owner_descriptor_match.screen.ENTRY',entry):
                    field=size_field(before);self.assertEqual(size_field(current),field)
                self.assertEqual(struct.unpack_from('>I',before,field)[0],12)
                self.assertEqual(struct.unpack_from('>I',current,field)[0],length)
                struct.pack_into('>I',expected,field,length);allowed.append(hex(entry))
        old_metadata,new_metadata=metadata(before),metadata(current)
        self.assertEqual(old_metadata[:2],new_metadata[:2])
        expected_symbols=old_metadata[2].copy()
        if installed:
            for entry,_,words in ((screen.ENTRY,screen.ROM,67),*HELPERS):
                found=[symbol for symbol in expected_symbols if symbol[0]==('func_%08X'%entry).encode()]
                self.assertEqual(len(found),1)
                symbol=found[0];self.assertEqual(expected_symbols[symbol],1)
                self.assertEqual((symbol[1],symbol[2]),(entry,12))
                del expected_symbols[symbol]
                expected_symbols[(symbol[0],symbol[1],words*4,*symbol[3:])]=1
        self.assertEqual(new_metadata[2],expected_symbols)
        self.assertEqual(old_metadata[3],new_metadata[3])
        self.assertEqual(old_metadata[4:],new_metadata[4:])
        # New assembly references reorder GNU ld's symbol/string tables, not their meaning.
        # Prove every record/string first, then permit only these non-loadable order changes.
        for section in new_metadata[4:]:
            offset,length=section[4:6]
            expected[offset:offset+length]=current[offset:offset+length]
        self.assertEqual(current,bytes(expected))
        guards=(self.root/'conker/retail_word_patches.us.csv').read_bytes()
        self.assertEqual(guards,(self.out/'before-guards').read_bytes())
        def rows(data):return list(csv.DictReader(data.decode().splitlines()))
        old=rows((self.out/'before-progress').read_bytes());new=rows((self.root/'conker/progress.csv').read_bytes())
        self.assertEqual(len(old),len(new));changed=[]
        for prior,after in zip(old,new):
            if prior!=after:
                self.assertTrue(installed);self.assertIn(prior['function'],('func_151B2348','func_151B2690'))
                self.assertEqual(prior['language'],'c');self.assertEqual(after['language'],'asm')
                self.assertEqual({k:v for k,v in prior.items() if k!='language'},{k:v for k,v in after.items() if k!='language'})
                changed.append(prior['function'])
        self.assertEqual(changed,['func_151B2348','func_151B2690'] if installed else [])
        audit=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('audit',dict(installed=installed,allowed_code_slots=allowed,guards_identical=True,
            restored_false_C_rows=changed,protected_data_layout=audit,baseline=baseline,
            source_sha256=hashlib.sha256((self.root/screen.SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest(),symbol_records=len(list(new_metadata[2].elements())),
            unchanged_symbol_meaning_except_three_sizes=True,symbol_string_order_only=True,
            no_other_ELF_or_progress_differences=True))

    def test_10_actual_registered_dispatcher_timer_and_release(self):
        dispatcher=list(struct.unpack_from('>45I',self.rom,0x176714))
        pools=sections(self.root/'conker/build/conker.us.elf')
        def linked(entry,length):
            matches=[data[entry-address:entry-address+length] for address,data in pools.values()
                if address<=entry and entry+length<=address+len(data)]
            self.assertEqual(len(matches),1)
            return matches[0]
        self.assertEqual(linked(0x15149264,180),struct.pack('>45I',*dispatcher))
        self.assertEqual(struct.unpack('>I',linked(0x8008A4E8+22*4,4))[0],screen.ENTRY)
        count=0
        for selector,flags,delta,old,gate,phase in itertools.product((-1,22),(0,1),(0,3,12),
                (0,1,2,255),range(7),(0,8)):
            memory=fixture(old,gate)
            put(memory,ACTOR+0xD,flags,1);put(memory,ACTOR+0xE,10,2)
            put(memory,ACTOR+0x10,255,1);put(memory,ACTOR+0x11,selector&255,1)
            put(memory,0x800BE9E4,delta);put(memory,0x8008A540,screen.ENTRY)
            expected=public(memory);calls=[]
            if flags&1:put(expected,ACTOR+0xE,(10-delta)&65535,2)
            if selector==22:
                expected,inner=reference(expected,old%4,1,2)
                calls=[('callback',ACTOR),*inner]
            if read(expected,ACTOR+0xE,2)&0x8000:calls.append(('release',ACTOR))
            outcomes=[]
            for callback in (self.retail,self.words):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(callback)}
                model=StateOracle(dispatcher,memory,old%4,1,2,phase=phase,entry=0x15149264,connected=connected).run()
                self.assertEqual((public(model.memory),model.records),(expected,calls))
                outcomes.append((model.memory,model.events,model.records))
            self.assertEqual(outcomes[0],outcomes[1]);count+=1
        self.receipt('dispatcher',dict(cases=count,executions=count*2,actual_words=45,
            linked_caller_byte_exact=True,actual_table_selector=22,callback_pointer=hex(screen.ENTRY),
            disabled_selector_timer_and_invalidation_release=True,other_slots_and_helpers_bounded=True))


if __name__=='__main__':
    unittest.main()
