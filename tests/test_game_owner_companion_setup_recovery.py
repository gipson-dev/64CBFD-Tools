"""Qualified companion recovery; original assembly remains installed."""
import hashlib
import itertools
import json
import re
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_companion_setup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests import test_game_owner_link_setup_recovery as setup
from tools.tests import test_game_owner_link_allocator_match as wrapper
from tools.tests import test_game_random_curve_record as native

ACTOR, ENDPOINT = 0x20000, 0x22000
RESULTS = (0x26000, 0x28000, 0x2A000)
FACTORY_ARGS = (300, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0, 19, 40, 255, 1)
INSERT = screen.EXTRA_TYPES + screen.EXTRA_DECLARATIONS + '\n'


def fixture(seed, alias, symbols=None):
    symbols = symbols or screen.SYMBOLS
    endpoint = ACTOR if alias else ENDPOINT
    memory = {STACK+i:(i*17+seed*13+0xA5)&255 for i in range(-0x400,0x140)}
    for base in (ACTOR, ENDPOINT, *RESULTS):
        memory.update({base+i:(i*11+seed*7+0x5A)&255 for i in range(-16,0x220)})
    put(memory, ACTOR+0x28, endpoint)
    put(memory, endpoint+0x3B, (seed*79+7)&255, 1)
    for i in range(3):
        put(memory, endpoint+0x14+i*4, 0x3F800000+seed*0x1000+i*0x800000)
    for name, address in symbols.items():
        if name.startswith('D_'):
            for i in range(3 if name in ('D_800AA320','D_800AA32C','D_800AA368','D_800AA374') else 1):
                put(memory,address+i*4,0x41200000+(address&255)*256+i*4096+seed)
    put(memory,wrapper.screen.SYMBOLS['D_800AA390'],wrapper.bits(100.0))
    return memory,endpoint


def mutate(memory, endpoint, index, enabled, symbols):
    if not enabled:
        return
    put(memory,endpoint+0x3B,0xE0+index,1)
    put(memory,endpoint+0x14,0xC1200000+index*0x100000)
    put(memory,ACTOR+0x28,0)
    for name,address in symbols.items():
        if name.startswith('D_'):
            count=3 if name in ('D_800AA320','D_800AA32C','D_800AA368','D_800AA374') else 1
            for i in range(count):
                put(memory,address+i*4,0xC1200000+index*0x10000+i*4096)


def expected(initial, endpoint, mask, enabled, results=RESULTS, symbols=None, phase=0, connected=False):
    symbols = symbols or screen.SYMBOLS
    memory = initial.copy()
    request, packet, effect = {}, {}, {}
    read = setup.read
    for offset,value,size in ((0,0,1),(2,100,2),(28,1,1),(29,1,1),(30,1,1),
            (32,0x40A00000,4),(36,3,1),(40,0x43340000,4),
            (44,read(memory,symbols['D_800AA388']),4),(48,read(memory,symbols['D_800AA38C']),4),(52,0,1)):
        put(request,offset,value,size)
    for offset,value,size in ((0,endpoint,4),(4,read(memory,endpoint+0x3B,1),1),(5,5,1),
            (20,endpoint,4),(24,read(memory,endpoint+0x3B,1),1),(25,2,1),(40,ACTOR,4)):
        put(packet,offset,value,size)
    for i in range(3):
        put(request,4+i*4,read(memory,endpoint+0x14+i*4))
        put(request,16+i*4,read(memory,endpoint+0x14+i*4))
    records=[]
    frame=STACK+phase-216
    for index,(va,vb) in enumerate((('D_800AA320','D_800AA368'),('D_800AA32C','D_800AA374'))):
        put(packet,44,1-index,1)
        for i in range(3):
            put(packet,8+i*4,read(memory,symbols[va]+i*4))
            put(packet,28+i*4,read(memory,symbols[vb]+i*4))
        records.append(('link',setup.payload(request,0,56,setup.REQUEST_HOLES),0x3AC49BA6,48,255,0))
        mutate(memory,endpoint,index,enabled,symbols)
        result=results[index] if mask&(1<<index) else 0
        if result and connected:
            for i in range(56):
                memory[result+16+i]=initial[frame+0x98+i] if i in setup.REQUEST_HOLES else request[i]
            memory[result+16]|=14
            doubled,scaled=wrapper.derived(read(memory,result+0x38),0x3AC49BA6,
                read(memory,wrapper.screen.SYMBOLS['D_800AA390']))
            put(memory,result+0x138,doubled);put(memory,result+0x13C,scaled)
            for i in range(16):memory[result+0x140+i]=0
        put(memory,ACTOR+0x3C-index*4,result)
        if result:
            records.append(('copy',result+0x150,48,setup.payload(packet,0,48,setup.PACKET_HOLES)))
            for i in range(48):
                memory[result+0x150+i]=initial[frame+0x68+i] if i in setup.PACKET_HOLES else packet[i]
    for offset,value,size in ((0,endpoint,4),(4,read(memory,endpoint+0x3B,1),1),(5,2,1),
            (32,0x40A00000,4),(36,ACTOR,4)):
        put(effect,offset,value,size)
    for i in range(3):
        put(effect,8+i*4,read(memory,symbols['D_800AA368']+i*4))
        put(effect,20+i*4,read(memory,symbols['D_800AA374']+i*4))
    records.append(('factory',FACTORY_ARGS))
    mutate(memory,endpoint,2,enabled,symbols)
    result=results[2] if mask&4 else 0
    put(memory,ACTOR+0x44,result)
    if result:
        records.append(('copy',result+0x28,40,setup.payload(effect,0,40,(6,7))))
        for i in range(40):
            memory[result+0x28+i]=initial[frame+0x40+i] if i in (6,7) else effect[i]
    return public(memory),records


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x140}


class CompanionOracle(TriangleOracle):
    execute=wrapper.AllocatorOracle.execute

    def __init__(self,words,memory,endpoint,mask,enabled,phase,results=RESULTS,
            symbols=None,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(ACTOR,))
        self.initial=memory.copy()
        self.endpoint,self.mask,self.enabled,self.results=endpoint,mask,enabled,results
        self.symbols=symbols or screen.SYMBOLS
        self.records=[];self.allocations=0;self.pending=None;self.common_calls=[]
        if connected is not None:
            self.code.update({wrapper.screen.ENTRY+i*4:w for i,w in enumerate(connected)})

    def get(self,address,size):
        if any(address+i not in self.memory for i in range(size)):
            raise KeyError(('read',address,size))
        return super().get(address,size)

    def record_call(self,target):
        if target==self.symbols['func_151B30B0']:
            args=self.arguments(5)
            self.records.append(('link',setup.payload(self.memory,args[0],56,setup.REQUEST_HOLES),*args[1:]))
            for i in setup.REQUEST_HOLES:
                assert self.memory[args[0]+i]==self.initial[args[0]+i]
            self.pending=('link',args)
        elif target==self.symbols['func_15149130']:
            args=self.arguments(9)
            self.records.append(('factory',args));self.pending=('factory',args)
        elif target==wrapper.screen.SYMBOLS['func_15167A68']:
            args=self.arguments(6);self.common_calls.append(args);self.pending=('common',args)
        elif target==wrapper.screen.SYMBOLS['bzero']:
            self.pending=('zero',self.arguments(2))
        else:
            assert target==self.symbols['memcpy']
            args=self.arguments(3);destination,source,length=args
            if length==56:
                self.pending=('request-copy',args)
                return
            holes=setup.PACKET_HOLES if length in (44,48) else (6,7)
            self.records.append(('copy',destination,length,setup.payload(self.memory,source,length,holes)))
            for i in holes:
                assert self.memory[source+i]==self.initial[source+i]
            self.pending=('copy',args)

    def hook(self,target):
        role,args=self.pending
        if role in ('link','factory','common'):
            index=self.allocations
            assert index<3
            mutate(self.memory,self.endpoint,index,self.enabled,self.symbols)
            result=self.results[index] if self.mask&(1<<index) else 0
            self.allocations+=1
        elif role=='zero':
            destination,length=args
            assert length==16
            for i in range(length):self.put(destination+i,0,1)
            result=0xDEADC0DE
        else:
            destination,source,length=args
            assert 0<=length<=56
            for i in range(length):self.put(destination+i,self.get(source+i,1),1)
            result=destination
        for i in range(9 if role=='factory' else 6 if role=='common' else 4):
            self.put(self.r[29]+i*4,0xA5000100+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result


class GameOwnerCompanionSetupRecoveryTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-companion-setup-test'
        cls.out.mkdir(exist_ok=True)
        directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path=Path(directory.name)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>176I',cls.rom,screen.ROM))
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.before={p:hashlib.sha256((cls.root/p).read_bytes()).hexdigest() for p in
            (screen.SOURCE,'conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/progress.csv')}

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,words,memory,endpoint,mask,enabled,phase,results=RESULTS,symbols=None,entry=screen.ENTRY,connected=None):
        model=CompanionOracle(words,memory,endpoint,mask,enabled,phase,results,symbols,entry,connected).run()
        self.assertEqual((public(model.memory),model.records),
            expected(memory,endpoint,mask,enabled,results,symbols,phase,connected is not None))
        self.assertEqual(model.allocations,3)
        return model

    def test_01_complete_catalog_explicitly_rejects_matching(self):
        rows=[]
        for name,body in screen.candidates():
            for profile in screen.setup.compiler.PROFILES if name=='selected' else ('o2g3',):
                meta,words=screen.compile_candidate(self.root,self.out,name+'-'+profile,body,profile)
                self.assertEqual(meta['diagnostics'],'');self.assertEqual(meta['pool_bytes'],0)
                self.assertNotEqual(words,self.retail)
                rows.append(meta)
        self.assertEqual(len(rows),56)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences')),(176,216,122))
        self.receipt('shapes',rows)

    def test_02_guest_reuse_late_capture_aliases_and_raw_holes(self):
        count=0;coverage=set()
        for seed,alias,mask,enabled,phase,result_alias in itertools.product(range(3),(False,True),range(8),(False,True),(0,8),(False,True)):
            memory,endpoint=fixture(seed,alias)
            results=(ACTOR,endpoint,endpoint) if result_alias else RESULTS
            models=[self.compare(words,memory,endpoint,mask,enabled,phase,results) for words in (self.retail,self.words)]
            coverage.update(models[0].visits)
            self.assertEqual(models[0].memory,models[1].memory)
            self.assertEqual(models[0].records,models[1].records)
            count+=1
        self.assertEqual(len(coverage),176)
        self.receipt('guest',dict(cases=count,executions=count*2,retail_words_reached=176,
            complete_memory_and_raw_packet_holes_equal=True,access_traces_not_equal_or_claimed=True,
            two_links_retain_codes_coordinates_limits=True,final_effect_late_capture=True))

    def test_03_native32_actual_body_and_layout(self):
        self.fixture='''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
#define NULL ((void *)0)
'''+screen.TYPES+'''
_Static_assert(sizeof(OwnerLinkEndpoint2348)==20,"endpoint");
_Static_assert(sizeof(OwnerLinkPacket2348)==48,"packet");
_Static_assert(sizeof(OwnerLinkRequest2348)==56,"request");
_Static_assert(sizeof(OwnerEffectPacket2690)==40,"effect");
_Static_assert(__builtin_offsetof(OwnerEffectPacket2690,actor)==36,"effect actor");
static union{u32 align;u8 bytes[0x240];} aStore,eStore,rStore[3];
static u8 *actor=aStore.bytes+16,*endpoint,*results[3],*returned;
static int mask,mutation,calls,copies,index,error;
static u8 retainedCode,copyCode;
static u32 retainedPosition[3],retainedLimits[2],copyA[3],copyB[3];
OwnerLinkVector2348 D_800AA320,D_800AA32C,D_800AA368,D_800AA374;
OwnerLinkVector2348 D_800AA350,D_800AA35C,D_800AA338,D_800AA344;
f32 D_800AA388,D_800AA38C,D_800AA380,D_800AA384;
static u32 word(f32 value){union{u32 u;f32 f;}v;v.f=value;return v.u;}
static void capture(int which){
    int i;OwnerLinkVector2348 *a=which==0?&D_800AA320:which==1?&D_800AA32C:&D_800AA368;
    OwnerLinkVector2348 *b=which==0?&D_800AA368:&D_800AA374;
    for(i=0;i<3;i++){copyA[i]=((u32 *)a)[i];copyB[i]=((u32 *)b)[i];}
}
static void change(void){
    int i;if(!mutation)return;
    endpoint[0x3b]=(u8)(0xe0+index);*(u32 *)(endpoint+0x14)=0xc1200000+index*0x100000;
    *(u8 **)(actor+0x28)=NULL;
    D_800AA388=-1.0f;D_800AA38C=-2.0f;
    for(i=0;i<3;i++){((u32 *)&D_800AA320)[i]=0xc1200000+index*0x10000+i*4096;
        ((u32 *)&D_800AA32C)[i]=((u32 *)&D_800AA368)[i]=((u32 *)&D_800AA374)[i]=((u32 *)&D_800AA320)[i];}
}
u8 *func_151B30B0(void *ptr,f32 parameter,s32 bytes,u8 slot,s32 context){
    OwnerLinkRequest2348 *request=ptr;int i;
    index=calls++;if(index>1){error=1;return NULL;}
    if(index==0){retainedCode=endpoint[0x3b];for(i=0;i<3;i++)retainedPosition[i]=*(u32 *)(endpoint+0x14+i*4);
        retainedLimits[0]=word(D_800AA388);retainedLimits[1]=word(D_800AA38C);}
    capture(index);copyCode=retainedCode;
    if(word(parameter)!=0x3ac49ba6||bytes!=48||slot!=255||context)error=2;
    if(request->flags||request->duration!=100||request->active!=1||request->enabled!=1||
        request->extra!=1||request->kind!=3||word(request->width)!=0x40a00000||
        word(request->distance)!=0x43340000||word(request->limitA)!=retainedLimits[0]||
        word(request->limitB)!=retainedLimits[1]||request->tail)error=3;
    for(i=0;i<3;i++)if(((u32 *)&request->start)[i]!=retainedPosition[i]||
        ((u32 *)&request->end)[i]!=retainedPosition[i])error=4;
    returned=mask&(1<<index)?results[index]:NULL;change();return returned;
}
void *func_15149130(s16 duration,s8 a,s8 b,s8 c,u8 active,u8 mode,s32 bytes,u8 slot,s32 context){
    index=calls++;if(index!=2)error=5;
    if(duration!=300||a!=-1||b!=-1||c||active||mode!=19||bytes!=40||slot!=255||context!=1)error=6;
    capture(index);copyCode=endpoint[0x3b];
    returned=mask&4?results[2]:NULL;change();return returned;
}
void *memcpy(void *destination,const void *source,u32 length){
    u8 *d=destination;const u8 *s=source;u32 i;copies++;
    if(index<2){
        const OwnerLinkPacket2348 *p=source;
        if(d!=returned+0x150||length!=48||p->first.owner!=endpoint||p->second.owner!=endpoint||
            p->first.code!=copyCode||p->second.code!=copyCode||p->first.kind!=5||p->second.kind!=2||
            p->actor!=actor||p->route!=1-index)error=7;
        for(i=0;i<3;i++)if(((u32 *)&p->first.offset)[i]!=copyA[i]||((u32 *)&p->second.offset)[i]!=copyB[i])error=8;
        if(*(u8 **)(actor+0x3c-index*4)!=returned)error=9;
    }else{
        const OwnerEffectPacket2690 *p=source;
        if(d!=returned+0x28||length!=40||p->endpoint.owner!=endpoint||p->endpoint.code!=copyCode||
            p->endpoint.kind!=2||p->actor!=actor||word(p->width)!=0x40a00000)error=10;
        for(i=0;i<3;i++)if(((u32 *)&p->endpoint.offset)[i]!=copyA[i]||((u32 *)&p->end)[i]!=copyB[i])error=11;
        if(*(u8 **)(actor+0x44)!=returned)error=12;
    }
    for(i=0;i<length;i++)d[i]=s[i];
    return destination;
}
'''+screen.SELECTED+'\n'
        self.run_host('''int byte,alias,m,f,resultAlias,i,j;
for(byte=0;byte<256;byte++)for(alias=0;alias<2;alias++)for(m=0;m<2;m++)for(f=0;f<8;f++)for(resultAlias=0;resultAlias<2;resultAlias++){
    for(i=0;i<0x240;i++){aStore.bytes[i]=0xa5;eStore.bytes[i]=0x5a;for(j=0;j<3;j++)rStore[j].bytes[i]=0x7e;}
    endpoint=alias?actor:eStore.bytes+16;
    for(i=0;i<3;i++){*(u32 *)(endpoint+0x14+i*4)=0x3f800000+byte*4096+i*0x800000;
        ((u32 *)&D_800AA320)[i]=0x41200000+i*4096;((u32 *)&D_800AA32C)[i]=0x42200000+i*4096;
        ((u32 *)&D_800AA368)[i]=0xc1200000+i*4096;((u32 *)&D_800AA374)[i]=0xc2200000+i*4096;}
    endpoint[0x3b]=(u8)byte;*(u8 **)(actor+0x28)=endpoint;
    for(i=0;i<3;i++)results[i]=resultAlias?(i==0?actor:endpoint):rStore[i].bytes+16;
    D_800AA388=100.0f;D_800AA38C=200.0f;mask=f;mutation=m;calls=copies=error=0;
    func_151B2690(actor);
    if(error||calls!=3||copies!=((f&1)!=0)+((f&2)!=0)+((f&4)!=0))return 1;
    for(i=0;i<16;i++){if(aStore.bytes[i]!=0xa5||eStore.bytes[i]!=0x5a)return 2;
        for(j=0;j<3;j++)if(rStore[j].bytes[i]!=0x7e)return 3;}
    for(i=0x200;i<0x240;i++)for(j=0;j<3;j++)if(rStore[j].bytes[i]!=0x7e)return 4;
}
''')
        self.receipt('native',dict(cases=16384,pointer_bits=32,actual_body=True,
            layout_assertions=True,defined_fields_only=True,no_native_padding_parity_claim=True))

    def test_04_compiled_effective_negatives(self):
        controls={
            'wrong-duration':screen.SELECTED.replace('duration = 100;','duration = 1000;'),
            'recaptured-code':screen.SELECTED.replace('    work.packet.route = 0;',
                '    work.packet.route = 0;\n    work.packet.first.code = endpoint[0x3B];'),
            'recaptured-coordinate':screen.SELECTED.replace('    work.packet.route = 0;',
                '    work.packet.route = 0;\n    work.request.start.x = *(f32 *)(endpoint + 0x14);'),
            'wrong-factory-mode':screen.SELECTED.replace('0, 0, 19, 40','0, 0, 18, 40'),
            'omitted-failed-store':screen.SELECTED.replace('    *(u8 **)(pair + 0x14) = created;',
                '    if (created != NULL) *(u8 **)(pair + 0x14) = created;'),
            'short-effect-copy':screen.SELECTED.replace('&work.effect, 40);','&work.effect, 36);')}
        outcomes={}
        for name,body in controls.items():
            meta,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            mismatch=False
            for mask in (0,7):
                memory,endpoint=fixture(0,False)
                model=CompanionOracle(words,memory,endpoint,mask,True,0).run()
                mismatch|=(public(model.memory),model.records)!=expected(memory,endpoint,mask,True)
            self.assertTrue(mismatch,name)
            outcomes[name]=dict(public_output_or_calls_mismatch=True,words=meta['body_words'])
        self.receipt('negatives',outcomes)

    def test_05_independent_original_candidate_rebases(self):
        fragment=(self.root/'conker/asm/nonmatchings/generated_1DF510/func_151B2690.s').read_text()
        raw=self.out/'original.s';obj=self.out/'original.o'
        raw.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n'+fragment)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(raw)],
            cwd=self.root,check=True,capture_output=True)
        original_relocations=parse_object(obj)[2]
        candidate_relocations=parse_object(self.out/'selected.o')[2]
        self.assertEqual(sum(map(len,original_relocations.values())),22)
        # One early home load shifts the prefix; the omitted late home store closes it.
        self.assertEqual({offset+(4 if offset<0x118 else 0):uses
            for offset,uses in original_relocations.items()},candidate_relocations)
        count=0
        for variant,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if variant==0 else {n:(entry&0xF0000000)+0x108008+i*0x100 for i,n in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,path in (('original',obj),('candidate',self.out/'selected.o')):
                elf=self.out/('rebase-%d-%s.elf'%(variant,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>176I',sections(elf)['.text'][1])))
            for mask,phase in itertools.product(range(8),(0,8)):
                memory,endpoint=fixture(count%3,bool(count%2))
                for name,address in screen.SYMBOLS.items():
                    if name.startswith('D_'):
                        for i in range(12 if address&255<0x80 else 4):
                            memory[symbols[name]+i]=memory[address+i]
                models=[self.compare(words,memory,endpoint,mask,True,phase,symbols=symbols,entry=entry) for words in bodies]
                self.assertEqual(models[0].memory,models[1].memory)
                count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=8,cases=count,executions=count*2,
            relocation_uses=sum(map(len,self.meta['relocations'].values())),semantic_memory_equal=True,byte_matching=False))

    def test_06_copied_owner_postprocess_neighbor_and_padder(self):
        before=(self.root/screen.SOURCE).read_text()
        after=before.replace('/* Non-matching placeholders',INSERT+'/* Non-matching placeholders',1).replace(screen.ORIGINAL,screen.SELECTED)
        objects=[];warnings=[]
        for name,body in (('owner-before',before),('owner-after',after)):
            obj,diagnostics=compile_owner(self.root,self.out,body,name)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj);warnings.append(diagnostics)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(len(warnings[0]),4)
        old,of,orels=parse_object(objects[0]);new,nf,nrels=parse_object(objects[1])
        self.assertEqual(of.keys(),nf.keys())
        for name,f in nf.items():
            if name==screen.FUNCTION:continue
            prior=of[name]
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-f['value']:r for o,r in nrels.items() if f['value']<=o<f['value']+f['size']},
                {o-prior['value']:r for o,r in orels.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertTrue(emit_padded_assembly(objects[1],self.root/'conker/asm/1DF510.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_1DF510'))
        self.receipt('owner',dict(neighbors=len(nf)-1,existing_diagnostics=4,new_diagnostics=0,
            pools_and_relative_relocations_unchanged=True,actual_postprocess_and_padder_accept=True,
            production_installation=False,matching_acceptance=False))

    def test_07_real_exact_wrapper_chain(self):
        words=list(struct.unpack_from('>53I',self.rom,wrapper.screen.ROM))
        count=0
        for alias,mask,enabled,phase in itertools.product((False,True),range(8),(False,True),(0,8)):
            memory,endpoint=fixture(count%3,alias)
            models=[self.compare(body,memory,endpoint,mask,enabled,phase,connected=words)
                for body in (self.retail,self.words)]
            self.assertEqual(models[0].memory,models[1].memory)
            self.assertEqual(models[0].common_calls,[(0x33,0,0x180,1,255,1)]*2)
            count+=1
        self.receipt('connected',dict(cases=count,executions=count*2,actual_setup_words=176,
            actual_wrapper_words=53,common_allocator_factory_and_sdk_bounded=True))

    def test_08_missing_byte_public_prefixes(self):
        count=0
        for alias in (False,True):
            memory,endpoint=fixture(0,alias)
            for address in (ACTOR+0x28,endpoint+0x3B,endpoint+0x14,0x800AA320,0x800AA368,0x800AA388):
                broken=memory.copy();del broken[address];models=[]
                for words in (self.retail,self.words):
                    model=CompanionOracle(words,broken,endpoint,7,False,0)
                    with self.assertRaises(KeyError):model.run()
                    models.append(model)
                self.assertEqual((public(models[0].memory),models[0].records),(public(models[1].memory),models[1].records))
                count+=1
        self.receipt('faults',dict(cases=count,executions=count*2,public_prefix_only=True,
            private_stack_and_access_trace_parity_not_claimed=True,hardware_faults_not_proven=True))

    def test_09_original_assembly_and_production_unchanged(self):
        fragment=(self.root/'conker/asm/nonmatchings/generated_1DF510/func_151B2690.s').read_text()
        words=[int(x,16) for x in re.findall(r'/\* [0-9A-F]{6} [0-9A-F]{8} ([0-9A-F]{8}) \*/',fragment)]
        self.assertEqual(words,self.retail);self.assertIn(screen.ORIGINAL,(self.root/screen.SOURCE).read_text())
        start,data=sections(self.root/'conker/build/conker.us.elf')['.game']
        self.assertEqual(list(struct.unpack_from('>176I',data,screen.ENTRY-start)),self.retail)
        self.assertEqual({p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in self.before},self.before)
        audit=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('unchanged',dict(hashes=self.before,protected_data_layout=audit,
            original_asm_retained=True,new_conversion_or_matching_credit=0))


if __name__=='__main__':
    unittest.main()
