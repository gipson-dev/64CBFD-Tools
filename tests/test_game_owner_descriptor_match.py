"""Raw descriptor holes, mutation/ABI order, connected caller and linked audit."""
import csv
import hashlib
import itertools
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_descriptor_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_random_curve_record as native

OWNER, CREATED, GATE, CALLER, CORE = 0x20000, 0x21000, 0x800BE9F0, 0x1514DB64, 0x15149130
RESOURCES = (0, 1, 0x80000000, 0xFFFFFFFF, 0x28000)
ALLOC_ARGS = (300, 0xFFFFFFFF, 22, 0, 18, 32, 255, 1)
INSERT = screen.TYPES + screen.DECLARATIONS + '\n'


def fixture(byte, seed=0):
    memory = {STACK+i:(i*17+seed*31+0xA5)&255 for i in range(-0x300,0x140)}
    for base in (OWNER, CREATED):
        memory.update({base+i:(i*13+seed*19+0x5A)&255 for i in range(-16,0x120)})
    put(memory, OWNER+0x3B, byte, 1)
    put(memory, GATE, 20)
    return memory


def packet(memory, address, owner, resource):
    data = bytearray(memory[address+i] for i in range(32))
    struct.pack_into('>I', data, 0, owner)
    data[4] = memory[owner+0x3B]
    struct.pack_into('>I', data, 8, resource)
    data[12:14] = bytes((1,0))
    data[16:] = bytes(16)
    return bytes(data)


def external(memory):
    return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x140}


class DescriptorOracle(TriangleOracle):
    def __init__(self, words, memory, owner=OWNER, resource=1, created=CREATED,
            mutate=False, clobber=False, phase=0, symbols=None, entry=screen.ENTRY,
            connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(owner,),connected=connected)
        self.owner, self.resource, self.created = owner, resource, created
        self.mutate, self.clobber, self.symbols = mutate, clobber, symbols or screen.SYMBOLS
        self.descriptor, self.records = None, []

    def get(self,address,size):
        if any(address+i not in self.memory for i in range(size)):
            raise KeyError(('read',address,size))
        return super().get(address,size)

    def put(self,address,value,size):
        if self.recording and any(address+i not in self.memory for i in range(size)):
            raise KeyError(('write',address,size))
        super().put(address,value,size)

    def raw(self,address,size):
        return bytes(self.memory[address+i] for i in range(size))

    def record_call(self,target):
        if target == screen.ENTRY:
            self.records.append(('caller',self.arguments(1)))
            return
        role = next((name for name,address in self.symbols.items() if address==target),None)
        if target == CORE:
            role = 'core'
        assert role is not None, hex(target)
        count = dict(func_15083E90=1,bzero=2,func_151491F4=8,memcpy=3,core=9)[role]
        args = self.arguments(count)
        if role == 'func_15083E90':
            self.descriptor = self.r[29]+0x2C
        if role == 'func_151491F4':
            self.records.append(('descriptor',self.raw(self.descriptor,32)))
        self.records.append((role,args))

    def hook(self,target):
        role,args = self.records[-1]
        if role == 'func_15083E90':
            assert args == (1,), ('resource-arguments',args)
            self.assert_capture()
            if self.mutate:
                self.put(self.owner+0x3B,self.memory[self.owner+0x3B]^255,1)
                self.put(GATE,19,4)
            result = self.resource
        elif role == 'bzero':
            address,length = args
            assert (address,length)==(self.descriptor+16,12), ('clear-arguments',args)
            for i in range(length):
                self.put(address+i,0,1)
            result = 0x87654321
        elif role in ('func_151491F4','core'):
            assert args == (ALLOC_ARGS if role=='func_151491F4' else
                (300,0xFFFFFFFF,22,0xFFFFFFFF,0,18,32,255,1)), ('allocate-arguments',args)
            result = self.created
        else:
            assert role == 'memcpy'
            address,source,length = args
            assert source==self.descriptor and length==32 and address==self.created+0x28, ('copy-arguments',args)
            values = self.raw(source,length)
            for i,value in enumerate(values):
                self.put(address+i,value,1)
            result = 0xDEADBEEF
        if self.clobber:
            for i in range(8 if role=='func_151491F4' else 9 if role=='core' else 4):
                self.put(self.r[29]+i*4,0x76540000+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result

    def assert_capture(self):
        assert int.from_bytes(self.raw(self.descriptor,4),'big')==self.owner, ('owner-capture',self.owner)
        assert self.memory[self.descriptor+4]==self.memory[self.owner+0x3B], ('owner-byte-capture',self.owner)


def size_field(data):
    h=ELF_HEADER.unpack_from(data)
    headers=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
    offsets=[]
    for section in headers:
        if section[1]!=2: continue
        strings=headers[section[6]]
        names=data[strings[4]:strings[4]+strings[5]]
        for offset in range(section[4],section[4]+section[5],section[9]):
            symbol=SYMBOL.unpack_from(data,offset)
            if names[symbol[0]:].split(b'\0',1)[0].decode()==screen.FUNCTION:
                assert symbol[1]==screen.ENTRY and symbol[3]&15==2
                offsets.append(offset+8)
    assert len(offsets)==1
    return offsets[0]


class GameOwnerDescriptorTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-descriptor-test'
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>40I',rom,screen.ROM))
        cls.wrapper=list(struct.unpack_from('>28I',rom,0x1766A4))
        cls.caller=list(struct.unpack_from('>13I',rom,0x17B014))
        directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path=Path(directory.name)
        baseline=cls.out/'baseline.json'
        if not baseline.exists() and screen.ORIGINAL in (cls.root/screen.SOURCE).read_text():
            hashes={}
            for name,path in dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
                    guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes,indent=2)+'\n')

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def expected(self,memory,owner,resource,created,mutate,phase=0,caller=False):
        expected=external(memory)
        if not owner: return expected,None
        address=STACK+phase-80-(24 if caller else 0)+0x2C
        raw=packet(memory,address,owner,resource)
        if mutate:
            expected[owner+0x3B]^=255
            put(expected,GATE,19)
        if created:
            expected.update({created+0x28+i:value for i,value in enumerate(raw)})
        return expected,raw

    def test_01_full_direct_match_and_profile(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences','pool_bytes')),
            (40,80,0,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(sum(map(len,self.meta['relocations'].values())),4)
        with (self.root/'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(row['function']==screen.FUNCTION for row in csv.DictReader(stream)))
        profiles=[]
        for profile in ('o2g3','o2','o1g3','o1'):
            meta,_=screen.compile_candidate(self.root,self.out,'profile-'+profile,profile=profile)
            profiles.append(meta)
        self.receipt('shape',dict(records=profiles,target_guards=0,raw_byte_exact=True))

    def test_02_guest_bytes_mutations_aliases_holes_and_scratch(self):
        coverage,count=set(),0
        for byte,created,mutate,phase,clobber in itertools.product(range(256),(0,CREATED,OWNER),(False,True),(0,8),(False,True)):
            resource=RESOURCES[byte%len(RESOURCES)]
            memory=fixture(byte,count%3)
            expected,raw=self.expected(memory,OWNER,resource,created,mutate,phase)
            models=[]
            for words in (self.words,self.retail):
                model=DescriptorOracle(words,memory,resource=resource,created=created,
                    mutate=mutate,clobber=clobber,phase=phase).run()
                self.assertEqual(external(model.memory),expected)
                self.assertIn(('descriptor',raw),model.records)
                self.assertEqual([record[0] for record in model.records],
                    ['func_15083E90','bzero','descriptor','func_151491F4']+(['memcpy'] if created else []))
                models.append((model.memory,model.events,model.records))
                coverage.update(model.visits)
            self.assertEqual(models[0],models[1])
            count+=1
        for phase in (0,8):
            memory=fixture(0xFF)
            for words in (self.words,self.retail):
                model=DescriptorOracle(words,memory,owner=0,phase=phase).run()
                self.assertEqual(external(model.memory),external(memory))
                self.assertEqual(model.records,[])
                coverage.update(model.visits)
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+160,4)))
        self.receipt('guest',dict(cases=count+2,executions=(count+2)*2,covered_words=40,
            raw32_byte_descriptor_including_five_holes=True,owner_alias_results=True,
            pre_helper_owner_capture=True,scratch_gpr_fp_and_argument_home_clobbers=True))

    def test_03_actual_allocator_wrapper_and_context_caller(self):
        count=0
        for context,owner,created,phase in itertools.product((0,19,20,21,0xFFFFFFFF),(0,OWNER),(0,CREATED,OWNER),(0,8)):
            memory=fixture(count&255)
            put(memory,GATE,context)
            connected=dict(zip(range(screen.ENTRY,screen.ENTRY+160,4),self.words))
            connected.update(zip(range(0x151491F4,0x15149264,4),self.wrapper))
            model=DescriptorOracle(self.caller,memory,owner=owner,resource=RESOURCES[count%5],
                created=created,mutate=True,clobber=True,phase=phase,entry=CALLER,connected=connected).run()
            routed=context==20
            self.assertEqual(sum(record[0]=='caller' for record in model.records),int(routed))
            if routed and owner:
                self.assertIn(('core',(300,0xFFFFFFFF,22,0xFFFFFFFF,0,18,32,255,1)),model.records)
                expected,raw=self.expected(memory,owner,RESOURCES[count%5],created,True,phase,caller=True)
                self.assertIn(('descriptor',raw),model.records)
            else:
                expected=external(memory)
            self.assertEqual(external(model.memory),expected)
            count+=1
        self.receipt('connected',dict(cases=count,actual_context_caller_words=13,actual_allocator_wrapper_words=28,
            common_allocator_resource_zero_copy_bounded_hooks=True,whole_allocator_hardware_proven=False))

    def test_04_native32_typed_constructor_and_real_caller_source(self):
        source=(self.root/'conker/src/game/generated_179F30.c').read_text()
        caller=re.search(r'void func_1514DB64\([^;{}]+\) \{\n.*?\n\}',source,re.S).group(0)
        self.fixture='''typedef unsigned char u8; typedef signed char s8; typedef short s16;
typedef int s32; typedef unsigned int u32;
#define NULL ((void *)0)
void bzero(void *,int);
''' + screen.TYPES+screen.DECLARATIONS+'''
static union { u32 align; u8 bytes[256]; } owners,allocated;
static u8 *owner=owners.bytes+16,*created;
static u32 resourceWord;static int mutation,calls,error;
static u8 originalByte;
s32 D_800BE9F0;
u8 *func_15083E90(s32 kind) {
    if(kind!=1 || calls!=0)error=1;
    calls++;
    if(mutation) { owner[0x3b]^=255;D_800BE9F0=19; }
    return (u8 *)resourceWord;
}
void bzero(void *destination,int length) {
    int i;
    if(length!=12 || calls!=1)error=2;
    calls++;
    for(i=0;i<length;i++)((u8 *)destination)[i]=0;
}
u8 *func_151491F4(s16 duration,s8 a,s8 kind,u8 mode,u8 type,s32 size,u8 channel,s32 context) {
    if(calls!=2 || duration!=300 || a!=-1 || kind!=22 || mode || type!=18 ||
        size!=32 || channel!=255 || context!=1)error=3;
    calls++;
    return created;
}
void *memcpy(void *destination,const void *source,u32 size) {
    const OwnerDescriptor151B2060 *descriptor=source;
    int i;
    if(calls!=3 || !created || destination!=created+0x28 || size!=32 ||
        descriptor->owner!=owner || descriptor->ownerCode!=originalByte ||
        (u32)descriptor->resource!=resourceWord || descriptor->active!=1 ||
        descriptor->state || descriptor->value)error=4;
    for(i=0;i<12;i++)if(descriptor->cleared[i])error=5;
    calls++;
    for(i=0;i<32;i++)((u8 *)destination)[i]=((const u8 *)source)[i];
    return NULL;
}
typedef char DescriptorSize[(sizeof(OwnerDescriptor151B2060)==32)?1:-1];
typedef char DescriptorCode[(__builtin_offsetof(OwnerDescriptor151B2060,ownerCode)==4)?1:-1];
typedef char DescriptorResource[(__builtin_offsetof(OwnerDescriptor151B2060,resource)==8)?1:-1];
typedef char DescriptorClear[(__builtin_offsetof(OwnerDescriptor151B2060,cleared)==16)?1:-1];
''' +screen.SELECTED+'\n'+caller+'''
static void (*constructor)(u8 *)=func_151B2060;
'''
        self.run_host(r'''
u32 byte,result,mutate,mode,i;u8 *output;
for(byte=0;byte<256;byte++)for(result=0;result<3;result++)for(mutate=0;mutate<2;mutate++)for(mode=0;mode<5;mode++) {
    int routed=mode<=1,hasOwner=mode!=4;
    for(i=0;i<256;i++) { owners.bytes[i]=0xa5;allocated.bytes[i]=0x5a; }
    owner=owners.bytes+16;owner[0x3b]=(u8)byte;originalByte=(u8)byte;
    created=result==0?NULL:result==1?allocated.bytes+16:owner;
    resourceWord=byte%5==0?0:byte%5==1?1:byte%5==2?0x80000000u:byte%5==3?0xffffffffu:0x28000u;
    mutation=(int)mutate;calls=error=0;D_800BE9F0=mode==2?19:mode==3?-1:20;
    if(mode==0)constructor(owner);
    else func_1514DB64(hasOwner?owner:NULL);
    if(error || calls!=(routed?(created?4:3):0))return 1;
    output=routed&&created?created+0x28:NULL;
    for(i=0;i<256;i++) {
        u8 *a=owners.bytes+i,*b=allocated.bytes+i;
        if(output!=owner+0x28 || a<output || a>=output+32) {
            u8 expected=a==owner+0x3b?(u8)(byte^(routed&&mutation?255:0)):0xa5;
            if(*a!=expected)return 2;
        }
        if((output!=allocated.bytes+16+0x28 || b<output || b>=output+32) && *b!=0x5a)return 3;
    }
}
''')
        self.receipt('native',dict(cases=256*3*2*5,actual_native32=True,typed_constructor=True,
            real_caller_source=True,defined_fields_and_all_external_canaries=True,
            private_holes_not_compared=True,resource_and_allocator_bounded_hooks=True))

    def test_05_owner_neighbors_padder_and_negative_controls(self):
        source=(self.root/screen.SOURCE).read_text()
        before=source.replace(screen.SELECTED,screen.ORIGINAL).replace(INSERT,'')
        self.assertEqual(before.count(screen.ORIGINAL),1)
        after=before.replace('/* Non-matching placeholders',INSERT+'/* Non-matching placeholders',1).replace(screen.ORIGINAL,screen.SELECTED)
        objects,diagnostics=[],[]
        for name,text in (('before',before),('after',after)):
            obj,warning=compile_owner(self.root,self.out,text,name)
            objects.append(obj);diagnostics.append(warning)
        self.assertEqual(diagnostics[0],diagnostics[1])
        self.assertEqual(len(diagnostics[0]),4)
        self.assertTrue(all(code=='712' and line.strip() in ('func_151B220C(arg0);','func_151B2FD0(arg0);')
            for code,line,_ in diagnostics[0]))
        old,old_fn,old_rel=parse_object(objects[0]);new,new_fn,new_rel=parse_object(objects[1])
        self.assertEqual(old_fn.keys(),new_fn.keys())
        for name,function in new_fn.items():
            if name==screen.FUNCTION:continue
            prior=old_fn[name]
            self.assertEqual((function['size'],new[function['value']:function['value']+function['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-function['value']:r for o,r in new_rel.items() if function['value']<=o<function['value']+function['size']},
                {o-prior['value']:r for o,r in old_rel.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertTrue(emit_padded_assembly(objects[1],self.root/'conker/asm/1DF510.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_1DF510'))
        negatives={'late-owner-byte':screen.SELECTED.replace('        descriptor.ownerCode = owner[0x3B];\n','').replace(
                '        descriptor.resource = func_15083E90(1);','        descriptor.resource = func_15083E90(1);\n        descriptor.ownerCode = owner[0x3B];'),
            'wrong-resource':screen.SELECTED.replace('func_15083E90(1)','func_15083E90(2)'),
            'short-clear':screen.SELECTED.replace('descriptor.cleared, 12','descriptor.cleared, 8'),
            'wrong-kind':screen.SELECTED.replace('300, -1, 0x16','300, -1, 0x17'),
            'short-copy':screen.SELECTED.replace('&descriptor, 32','&descriptor, 28')}
        rejection_reasons={}
        for name,body in negatives.items():
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            model=DescriptorOracle(words,fixture(0x81),mutate=True)
            try:
                model.run()
                expected,raw=self.expected(fixture(0x81),OWNER,1,CREATED,True)
                rejected=external(model.memory)!=expected or ('descriptor',raw) not in model.records
                rejection_reasons[name]='output-or-packet'
            except AssertionError as error:
                self.assertTrue(error.args and isinstance(error.args[0],tuple) and error.args[0][0] in (
                    'resource-arguments','clear-arguments','allocate-arguments','copy-arguments',
                    'owner-capture','owner-byte-capture'),(name,error.args))
                rejection_reasons[name]=error.args[0][0]
                rejected=True
            self.assertTrue(rejected,name)
        self.receipt('owner',dict(neighbors=len(new_fn)-1,unchanged_pools_relative_relocations=True,
            existing_diagnostics=4,new_diagnostics=0,actual_padder_accepts=True,negatives=list(negatives),
            specific_negative_rejection_reasons=rejection_reasons))

    def test_06_independent_original_candidate_rebases(self):
        assembly=(self.root/'conker/asm/1DF510.s').read_text().split('glabel '+screen.FUNCTION,1)[1]
        assembly='glabel '+screen.FUNCTION+assembly.split('endlabel '+screen.FUNCTION,1)[0]
        path=self.out/'original.s';obj=self.out/'original.o'
        path.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n'+assembly)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],cwd=self.root,check=True,capture_output=True)
        self.assertEqual(parse_object(obj)[2],parse_object(self.out/'selected.o')[2])
        count=0
        for variant,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if variant==0 else {name:(entry&0xF0000000)+0x100800+i*0x100
                for i,name in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,path in (('original',obj),('candidate',self.out/'selected.o')):
                elf=self.out/('rebase-%d-%s.elf'%(variant,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>40I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[1])
            for owner,created,mutate,phase in itertools.product((0,OWNER),(0,CREATED,OWNER),(False,True),(0,8)):
                memory=fixture(0xFE,count%3);expected,raw=self.expected(memory,owner,0xFFFFFFFF,created,mutate,phase)
                outcomes=[]
                for words in bodies:
                    model=DescriptorOracle(words,memory,owner=owner,resource=0xFFFFFFFF,created=created,
                        mutate=mutate,phase=phase,clobber=True,entry=entry,symbols=symbols).run()
                    self.assertEqual(external(model.memory),expected)
                    outcomes.append((model.memory,model.events,model.records))
                self.assertEqual(outcomes[0],outcomes[1]);count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=8,relocation_uses=4,cases=count,executions=count*2))

    def test_07_missing_owner_byte_fault_prefix(self):
        memory=fixture(0xFF);del memory[OWNER+0x3B]
        outcomes=[]
        for words in (self.words,self.retail):
            model=DescriptorOracle(words,memory)
            with self.assertRaises(KeyError):model.run()
            self.assertEqual(model.records,[])
            outcomes.append((model.memory,model.events))
        self.assertEqual(outcomes[0],outcomes[1])
        self.receipt('faults',dict(missing_owner_byte_pairs=1,before_any_helper=True,guest_order_not_C_hardware_fault_guarantee=True))

    def test_08_whole_ELF_installation_and_connected_bodies(self):
        elf=self.root/'conker/build/conker.us.elf';current=elf.read_bytes();data=sections(elf)
        for entry,words in ((CALLER,self.caller),(0x151491F4,self.wrapper)):
            actual=[chunk[entry-base:entry-base+len(words)*4] for base,chunk in data.values() if base<=entry and entry+len(words)*4<=base+len(chunk)]
            self.assertEqual(actual,[struct.pack('>%dI'%len(words),*words)])
        if not (self.out/'baseline.json').exists():
            self.skipTest('immutable pre-install baseline absent; connected bodies checked')
        baseline=json.loads((self.out/'baseline.json').read_text());before=(self.out/'before-elf').read_bytes()
        installed=screen.SELECTED in (self.root/screen.SOURCE).read_text()
        if installed:
            expected=bytearray(before);offset=elf_slot_offset(before,screen.ENTRY,160)
            expected[offset:offset+160]=struct.pack('>40I',*self.retail)
            size=size_field(before);self.assertEqual(size_field(current),size)
            self.assertEqual(struct.unpack_from('>I',before,size)[0],12)
            self.assertEqual(struct.unpack_from('>I',current,size)[0],160)
            struct.pack_into('>I',expected,size,160);self.assertEqual(current,bytes(expected))
        else:self.assertEqual(current,before)
        for name,path in dict(guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
            value=(self.root/path).read_bytes();self.assertEqual(value,(self.out/('before-'+name)).read_bytes())
            self.assertEqual(hashlib.sha256(value).hexdigest(),baseline[name])
        audit=audit_layout(elf,self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('audit',dict(installed=installed,only_target_slot_and_size_change=installed,
            guards_progress_identical=True,protected_data_layout=audit,
            source_sha256=hashlib.sha256((self.root/screen.SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest(),actual_connected_bodies_exact=True))


if __name__=='__main__':
    unittest.main()
