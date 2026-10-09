"""Direct owner-link allocator, finite float semantics, real setup chain and audit."""
import csv
import hashlib
import itertools
import json
import math
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_link_allocator_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_link_setup_recovery as setup
from tools.tests import test_game_random_curve_record as native

CREATED, REQUEST = 0x30000, 0x32000
INSERT=screen.DECLARATIONS+'\n'
DISTANCES=(-0.0,-1.0,0.5,80.0,170.0,-170.0,32767.0,-32768.0,0.0001)
PARAMETERS=(0.0,0.0015,-0.0015,0.5)
SIZES=(0,48,65535,0xFFFFFEB0,0xFFFFFFFF,0x7FFFFEAF,0x80000000)


def derived(distance, parameter, divisor):
    square=bits(floating(distance)*floating(distance))
    quotient=bits(floating(square)/floating(divisor))
    doubled=bits(floating(quotient)+floating(quotient))
    product=bits(floating(distance)*floating(parameter))
    scaled=bits(floating(product)*4096.0)
    value=floating(scaled)
    assert math.isfinite(value) and -2147483648 <= math.trunc(value) <= 2147483647
    return doubled,math.trunc(value)&0xFFFFFFFF


def external(memory):
    return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x140}


def fixture(distance,divisor,seed=0,symbols=None):
    symbols=symbols or screen.SYMBOLS
    memory={STACK+i:(i*17+seed*13+0xA5)&255 for i in range(-0x300,0x140)}
    for base in (CREATED,REQUEST):
        memory.update({base+i:(i*11+seed*7+0x5A)&255 for i in range(-16,0x200)})
    put(memory,REQUEST+40,distance)
    put(memory,symbols['D_800AA390'],divisor)
    return memory


def mutate_request(memory,request,enabled):
    if enabled:
        memory[request]^=0xA0
        put(memory,request+40,bits(170.0))


def mutate_created(memory,created,enabled):
    if enabled:
        memory[created+16]^=0x80
        put(memory,created+0x38,bits(-80.0))


def expected(initial,args,result,mutation,symbols=None):
    symbols=symbols or screen.SYMBOLS
    memory=external(initial)
    request,parameter,extra,slot,context=args
    records=[('allocate',(0x33,context,(extra+0x150)&0xFFFFFFFF,1,slot&255,1))]
    if not result:
        return memory,records
    mutate_request(memory,request,mutation)
    records.append(('copy',(result+16,request,56)))
    for i in range(56):
        memory[result+16+i]=memory[request+i]
    mutate_created(memory,result,mutation)
    distance=setup.read(memory,result+0x38)
    memory[result+16]|=14
    doubled,scaled=derived(distance,parameter,setup.read(memory,symbols['D_800AA390']))
    put(memory,result+0x138,doubled)
    put(memory,result+0x13C,scaled)
    records.append(('zero',(result+0x140,16)))
    for i in range(16):
        memory[result+0x140+i]=0
    return memory,records


class AllocatorOracle(TriangleOracle):
    def __init__(self,words,memory,args,result=CREATED,mutation=False,phase=0,
            entry=screen.ENTRY,symbols=None):
        super().__init__(words,memory,entry=entry,arguments=args,phase=phase)
        self.result,self.mutation,self.request=result,mutation,args[0]
        self.symbols=symbols or screen.SYMBOLS
        self.records=[]

    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            source,destination=word>>11&31,word>>6&31
            value=floating(self.f[source])
            assert math.isfinite(value) and -2147483648<=math.trunc(value)<=2147483647
            self.f[destination]=math.trunc(value)&0xFFFFFFFF
        else:
            TriangleOracle.execute(self,word)

    def record_call(self,target):
        if target==self.symbols['func_15167A68']:
            self.records.append(('allocate',self.arguments(6)))
        elif target==self.symbols['memcpy']:
            self.records.append(('copy',self.arguments(3)))
        else:
            assert target==self.symbols['bzero'],('unexpected-call',target)
            self.records.append(('zero',self.arguments(2)))

    def hook(self,target):
        role,args=self.records[-1]
        if role=='allocate':
            if self.result:
                mutate_request(self.memory,self.request,self.mutation)
            result=self.result
        elif role=='copy':
            destination,source,length=args
            assert length<=56
            for i in range(length):
                self.put(destination+i,self.get(source+i,1),1)
            mutate_created(self.memory,self.result,self.mutation)
            result=destination
        else:
            destination,length=args
            assert length==16
            for i in range(length):
                self.put(destination+i,0,1)
            result=0xDEADC0DE
        for i in range(6 if role=='allocate' else 4):
            self.put(self.r[29]+i*4,0xA5000100+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result


class ChainOracle(setup.SetupOracle):
    execute=AllocatorOracle.execute

    def __init__(self,wrapper,memory,first,second,mask,enabled,phase,setup_words):
        super().__init__(setup_words,memory,first,second,mask,enabled,phase)
        self.code.update({screen.ENTRY+i*4:w for i,w in enumerate(wrapper)})
        self.common_calls=[]
        self.request_copies=[]

    def record_call(self,target):
        if target==screen.ENTRY:
            super().record_call(target)
        elif target==screen.SYMBOLS['func_15167A68']:
            args=self.arguments(6)
            self.common_calls.append(args)
            self.pending=('common',args)
        elif target==screen.SYMBOLS['memcpy']:
            if self.r[6]==56:
                args=self.arguments(3)
                self.request_copies.append(args)
                self.pending=('request-copy',args)
            else:
                super().record_call(target)
        else:
            assert target==screen.SYMBOLS['bzero']
            self.pending=('zero',self.arguments(2))

    def hook(self,target):
        role,args=self.pending
        if role=='copy':
            return super().hook(target)
        if role=='common':
            index=self.allocations
            assert index<3 and args==(0x33,0,0x180,1,255,1)
            setup.mutate(self.memory,self.first,self.second,index,self.enabled)
            result=setup.RESULTS[index] if self.mask&(1<<index) else 0
            self.allocations+=1
        elif role=='request-copy':
            destination,source,length=args
            for i in range(length):
                self.put(destination+i,self.get(source+i,1),1)
            result=destination
        else:
            assert role=='zero' and args[1]==16
            for i in range(16):
                self.put(args[0]+i,0,1)
            result=0xDEADC0DE
        for i in range(6 if role=='common' else 4):
            self.put(self.r[29]+i*4,0xA5000100+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result


class GameOwnerLinkAllocatorTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-link-allocator-test'
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>53I',cls.rom,screen.ROM))
        cls.setup_words=list(struct.unpack_from('>210I',cls.rom,setup.screen.ROM))
        directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path=Path(directory.name)
        if not (cls.out/'baseline.json').exists() and screen.ORIGINAL in (cls.root/screen.SOURCE).read_text():
            hashes={}
            for name,path in dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
                    guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,words,memory,args,result=CREATED,mutation=False,phase=0,
            entry=screen.ENTRY,symbols=None):
        model=AllocatorOracle(words,memory,args,result,mutation,phase,entry,symbols).run()
        self.assertEqual((external(model.memory),model.records),expected(memory,args,result,mutation,symbols))
        self.assertEqual(model.r[2],result)
        return model

    def test_01_direct_shape_and_profiles(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences','pool_bytes')),(53,40,0,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(sum(map(len,self.meta['relocations'].values())),5)
        rows=[]
        for profile in screen.compiler.PROFILES:
            meta,_=screen.compile_candidate(self.root,self.out,'profile-'+profile,profile=profile)
            rows.append(meta)
        with (self.root/'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(r['function']==screen.FUNCTION for r in csv.DictReader(stream)))
        self.receipt('shape',dict(selected=self.meta,profiles=rows,guards=0))

    def test_02_guest_all_slot_bytes_failure_and_mutation(self):
        count=0
        coverage=set()
        for byte,extra,result,phase in itertools.product(range(256),SIZES,(0,CREATED),(0,8)):
            distance=bits(DISTANCES[byte%len(DISTANCES)])
            parameter=bits(PARAMETERS[byte%len(PARAMETERS)])
            divisor=bits((1.0,32.0,0.25)[byte%3])
            memory=fixture(distance,divisor,byte%3)
            request=REQUEST if result or byte%2 else 0
            args=(request,parameter,extra,0xA5F00000|byte,0xABCDEF00|byte)
            outcomes=[]
            for words in (self.retail,self.words):
                model=self.compare(words,memory,args,result,bool(byte&1),phase)
                coverage.update(model.visits)
                outcomes.append((model.memory,model.records,model.events,model.r))
            self.assertEqual(outcomes[0],outcomes[1])
            count+=1
        self.receipt('guest',dict(cases=count,executions=count*2,retail_words_reached=len(coverage),
            finite_in_range_conversion_only=True,argument_homes_and_scratch_clobbered=True))

    def test_03_native32_actual_body(self):
        rows=[]
        for d,p,div in itertools.product(DISTANCES,PARAMETERS,(1.0,32.0,0.25)):
            values=derived(bits(d),bits(p),bits(div))
            rows.append('{%s}'%','.join('0x%X'%v for v in (bits(d),bits(p),bits(div),*values)))
        self.fixture='''typedef unsigned char u8;typedef int s32;typedef unsigned int u32;
typedef float f32;
#define NULL ((void *)0)
static union { u32 align; u8 bytes[0x240]; } resultStorage,requestStorage;
static u8 *created=resultStorage.bytes+16,*request=requestStorage.bytes+16;
static s32 extra,context;static u8 slot;static int fail,mutation,calls,error;
static u32 row[5];
f32 D_800AA390;
static f32 number(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
void *func_15167A68(s32 kind,s32 ctx,s32 size,s32 flags,u8 channel,u8 pool){
    if(calls++!=0||kind!=0x33||ctx!=context||size!=extra+0x150||flags!=1||channel!=slot||pool!=1)error=1;
    if(fail)return NULL;
    if(mutation){request[0]^=0xA0;*(f32 *)(request+40)=80.0f;}
    return created;
}
void *memcpy(void *dst,const void *src,u32 size){
    u8 *d=dst;const u8 *s=src;u32 i;
    if(calls++!=1||d!=created+16||s!=request||size!=56)error=2;
    for(i=0;i<size;i++)d[i]=s[i];
    if(mutation){created[16]^=0x80;*(f32 *)(created+0x38)=number(row[0]);}
    return dst;
}
void bzero(void *dst,int size){
    u8 *d=dst;int i;
    if(calls++!=2||d!=created+0x140||size!=16)error=3;
    for(i=0;i<size;i++)d[i]=0;
}
'''+screen.SELECTED+'\n'
        self.run_host('''static u32 table[][5]={'''+','.join(rows)+'''};
static s32 sizes[]={0,48,65535,-336,-1,2147483311,(-2147483647-1)};
int r,b,s,m,f,i;u8 *ret;
for(r=0;r<108;r++)for(b=0;b<256;b++)for(s=0;s<7;s++)for(m=0;m<2;m++)for(f=0;f<2;f++){
    for(i=0;i<0x240;i++){resultStorage.bytes[i]=0xA5;requestStorage.bytes[i]=(u8)(i*11+b);}
    for(i=0;i<5;i++)row[i]=table[r][i];
    *(f32 *)(request+40)=number(row[0]);D_800AA390=number(row[2]);
    extra=sizes[s];slot=(u8)b;context=(s32)0xABCDEF01;fail=f;mutation=m;calls=error=0;
    ret=func_151B30B0(f?NULL:request,number(row[1]),extra,slot,context);
    if(error||ret!=(f?NULL:created)||calls!=(f?1:3))return 1;
    if(!f){
        if(word(*(f32 *)(created+0x138))!=row[3]||*(u32 *)(created+0x13C)!=row[4])return 2;
        for(i=0;i<56;i++){
            u8 v=request[i];
            if(i==0)v=(u8)((v^(m?0x80:0))|14);
            if(m&&i>=40&&i<44)v=((u8 *)&row[0])[i-40];
            if(created[16+i]!=v)return 3;
        }
    }
    for(i=0;i<0x240;i++){
        u8 *a=resultStorage.bytes+i;
        if(!f&&a>=created+16&&a<created+72)continue;
        if(!f&&a>=created+0x138&&a<created+0x140)continue;
        if(!f&&a>=created+0x140&&a<created+0x150){if(*a)return 4;continue;}
        if(*a!=0xA5)return 5;
    }
}
''')
        self.receipt('native',dict(cases=108*256*7*2*2,pointer_bits=32,
            signed_addition_in_range=True,float_conversion_finite_in_range=True,
            expected_float_words_from_independent_python=True))

    def test_04_copied_owner_and_padder(self):
        source=(self.root/screen.SOURCE).read_text()
        before=source.replace(screen.SELECTED,screen.ORIGINAL).replace(INSERT,'')
        self.assertEqual(before.count(screen.ORIGINAL),1)
        after=before.replace('/* Non-matching placeholders',INSERT+'/* Non-matching placeholders',1).replace(
            screen.ORIGINAL,screen.SELECTED)
        objects,diagnostics=[],[]
        for name,text in (('before',before),('after',after)):
            obj,warnings=compile_owner(self.root,self.out,text,name)
            objects.append(obj);diagnostics.append(warnings)
        self.assertEqual(diagnostics[0],diagnostics[1])
        old,old_fn,old_rel=parse_object(objects[0])
        new,new_fn,new_rel=parse_object(objects[1])
        self.assertEqual(old_fn.keys(),new_fn.keys())
        for name,fn in new_fn.items():
            if name==screen.FUNCTION:
                continue
            prior=old_fn[name]
            self.assertEqual((fn['size'],new[fn['value']:fn['value']+fn['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-fn['value']:r for o,r in new_rel.items() if fn['value']<=o<fn['value']+fn['size']},
                {o-prior['value']:r for o,r in old_rel.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertTrue(emit_padded_assembly(objects[1],self.root/'conker/asm/1E0560.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_1E0560'))
        self.receipt('owner',dict(neighbors=len(new_fn)-1,diagnostics=diagnostics[0],
            unchanged_pools_and_relative_relocations=True,padder_accepted=True))

    def test_05_compiled_effective_negatives(self):
        records={}
        for name,body in screen.candidates():
            if not name.startswith('negative-'):
                continue
            meta,words=screen.compile_candidate(self.root,self.out,name,body)
            memory=fixture(bits(170.0),bits(32.0))
            # Keep the wrong returned-copy pointer's float read inside the oracle domain.
            put(memory,CREATED+0x48,bits(1.0))
            args=(REQUEST,bits(0.0015),48,255,0)
            model=AllocatorOracle(words,memory,args).run()
            expected_memory,expected_calls=expected(memory,args,CREATED,False)
            self.assertNotEqual((external(model.memory),model.records,model.r[2]),
                (expected_memory,expected_calls,CREATED),name)
            records[name]=dict(rejected=True,public_output_or_call_mismatch=True,words=meta['body_words'])
        self.receipt('negatives',records)

    def test_06_independent_original_candidate_rebases(self):
        assembly=(self.root/'conker/asm/1E0560.s').read_text().split('glabel '+screen.FUNCTION,1)[1]
        assembly='glabel '+screen.FUNCTION+assembly.split('endlabel '+screen.FUNCTION,1)[0]
        raw=self.out/'original.s';obj=self.out/'original.o'
        raw.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n'+assembly)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(raw)],
            cwd=self.root,check=True,capture_output=True)
        self.assertEqual(parse_object(obj)[2],parse_object(self.out/'selected.o')[2])
        count=0
        for variant,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if variant==0 else {n:(entry&0xF0000000)+0x100800+i*0x100
                for i,n in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,path in (('original',obj),('candidate',self.out/'selected.o')):
                elf=self.out/('rebase-%d-%s.elf'%(variant,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>53I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[1])
            for result,mutation,phase in itertools.product((0,CREATED),(False,True),(0,8)):
                memory=fixture(bits(80.0),bits(32.0),symbols=symbols)
                args=(REQUEST,bits(0.0015),48,0xFFFF01FF,0x80000001)
                outcomes=[]
                for words in bodies:
                    model=self.compare(words,memory,args,result,mutation,phase,entry,symbols)
                    outcomes.append((model.memory,model.events,model.records))
                self.assertEqual(outcomes[0],outcomes[1])
                count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=8,cases=count,executions=count*2))

    def test_07_actual_setup_chain(self):
        count=0
        for layout,mask,enabled,phase in itertools.product(range(4),range(8),(False,True),(0,8)):
            memory,first,second=setup.fixture(count%3,layout)
            put(memory,screen.SYMBOLS['D_800AA390'],bits(32.0))
            public,records=setup.expected(memory,first,second,mask,enabled)
            frame=STACK+phase-168
            request_seed=bytearray(memory[frame+0x64+i] for i in range(56))
            allocations=[r for r in records if r[0]=='allocate']
            for index,record in enumerate(allocations):
                if not mask&(1<<index):
                    continue
                raw=request_seed.copy()
                for offset,value in zip((i for i in range(56) if i not in setup.REQUEST_HOLES),record[1]):
                    raw[offset]=value
                result=setup.RESULTS[index]
                for i,v in enumerate(raw):
                    public[result+16+i]=v
                public[result+16]|=14
                doubled,scaled=derived(int.from_bytes(raw[40:44],'big'),0x3AC49BA6,bits(32.0))
                put(public,result+0x138,doubled);put(public,result+0x13C,scaled)
                for i in range(16):
                    public[result+0x140+i]=0
            outcomes=[]
            for wrapper in (self.retail,self.words):
                model=ChainOracle(wrapper,memory,first,second,mask,enabled,phase,self.setup_words).run()
                self.assertEqual((setup.public(model.memory),model.records),(public,records))
                self.assertEqual(model.common_calls,[(0x33,0,0x180,1,255,1)]*3)
                self.assertEqual(len(model.request_copies),mask.bit_count())
                for index,result in enumerate(setup.RESULTS):
                    if mask&(1<<index):
                        for i in setup.PACKET_HOLES:
                            self.assertEqual(model.memory[result+0x150+i],memory[frame+0x34+i])
                outcomes.append((model.memory,model.events,model.records))
            self.assertEqual(outcomes[0],outcomes[1])
            count+=1
        self.receipt('chain',dict(cases=count,executions=count*2,actual_setup_words=210,
            actual_wrapper_words=53,common_allocator_and_sdk_bounded=True,
            original_setup_raw_packet_holes=True,unmatched_setup_C_not_installed=True))

    def test_08_whole_elf_installation_audit(self):
        current=(self.root/'conker/build/conker.us.elf').read_bytes()
        if not (self.out/'baseline.json').exists():
            self.skipTest('immutable pre-install baseline absent')
        before=(self.out/'before-elf').read_bytes()
        installed=screen.SELECTED in (self.root/screen.SOURCE).read_text()
        if installed:
            expected_bytes=bytearray(before)
            offset=elf_slot_offset(before,screen.ENTRY,212)
            expected_bytes[offset:offset+212]=struct.pack('>53I',*self.retail)
            with patch.object(descriptor.screen,'FUNCTION',screen.FUNCTION), patch.object(descriptor.screen,'ENTRY',screen.ENTRY):
                size=descriptor.size_field(before)
                self.assertEqual(descriptor.size_field(current),size)
            self.assertEqual(struct.unpack_from('>I',before,size)[0],12)
            self.assertEqual(struct.unpack_from('>I',current,size)[0],212)
            struct.pack_into('>I',expected_bytes,size,212)
            old_meta,new_meta=metadata(bytes(expected_bytes)),metadata(current)
            self.assertEqual(old_meta,new_meta)
            # GNU ld may reorder symbol records after a newly referenced global.
            for section in old_meta[4:]:
                start,length=section[4],section[5]
                expected_bytes[start:start+length]=current[start:start+length]
            self.assertEqual(current,bytes(expected_bytes))
        else:
            self.assertEqual(current,before)
        for name,path in dict(guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
            self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('audit',dict(installed=installed,only_target_loadable_code_change=installed,
            only_target_symbol_size_meaning_change=installed,symbol_string_order_normalized=installed,
            guards_progress_identical=True,protected_data_layout=audit,
            source_sha256=hashlib.sha256((self.root/screen.SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest()))


if __name__=='__main__':
    unittest.main()
