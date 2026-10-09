"""Bounded three-request recovery; explicitly not a matching-installation suite."""
import hashlib
import itertools
import json
import re
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_owner_link_setup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_queued_segment_writer import STACK

ACTOR, FIRST, SECOND = 0x20000, 0x22000, 0x24000
RESULTS = (0x26000, 0x28000, 0x2A000)
PACKET_HOLES = (6, 7, 26, 27, 45, 46, 47)
REQUEST_HOLES = (1, 31, 37, 38, 39, 53, 54, 55)


def read(memory, address, size=4):
    return int.from_bytes(bytes(memory[address+i] for i in range(size)), 'big')


def payload(memory, address, length, holes):
    return tuple(memory[address+i] for i in range(length) if i not in holes)


def fixture(seed, layout):
    first = ACTOR if layout == 2 else FIRST
    second = first if layout == 1 else ACTOR if layout == 3 else SECOND
    memory = {STACK+i: (i*17+seed*13+0xA5)&255 for i in range(-0x300, 0x140)}
    for base in (ACTOR, first, second, *RESULTS):
        memory.update({base+i: (i*11+seed*7+0x5A)&255 for i in range(-16, 0x200)})
    for base in (first, second):
        put(memory, base+0x3B, (base//256+seed)&255, 1)
        for i in range(3):
            put(memory, base+0x14+i*4, 0x3F800000+seed*0x1000+i*0x800000)
    put(memory, ACTOR+0x28, first)
    put(memory, ACTOR+0x30, second)
    for name, address in screen.SYMBOLS.items():
        if not name.startswith('D_'):
            continue
        for i in range(3 if address < 0x800AA380 else 1):
            put(memory, address+4*i, 0x41200000+(address&255)*256+i*4096+seed)
    return memory, first, second


def mutate(memory, first, second, index, enabled):
    if not enabled:
        return
    for base in (first, second):
        put(memory, base+0x3B, 0xE0+index, 1)
        put(memory, base+0x14, 0xC1200000+index*0x100000)
    # Later calls must retain endpoint identities captured before the first call.
    put(memory, ACTOR+0x28, 0)
    put(memory, ACTOR+0x30, 0)


def expected(initial, first, second, mask, enabled):
    memory = initial.copy()
    request, packet = {}, {}
    for offset, value, size in ((0,0,1),(2,1000,2),(28,1,1),(29,1,1),(30,0,1),
            (32,0x40A00000,4),(36,3,1),(40,0x42A00000,4),
            (44,read(memory,0x800AA380),4),(48,read(memory,0x800AA384),4),(52,0,1)):
        put(request, offset, value, size)
    records = []
    for index, (a, b, kind, va, vb) in enumerate((
            (second,second,10,0x800AA350,0x800AA35C),
            (first,second,5,0x800AA320,0x800AA338),
            (first,second,10,0x800AA32C,0x800AA344))):
        for offset, value, size in ((0,a,4),(4,read(memory,a+0x3B,1),1),(5,5,1),
                (20,b,4),(24,read(memory,b+0x3B,1),1),(25,kind,1),(40,ACTOR,4),(44,2-index,1)):
            put(packet, offset, value, size)
        for i in range(3):
            put(packet, 8+4*i, read(memory,va+4*i))
            put(packet, 28+4*i, read(memory,vb+4*i))
            put(request, 4+4*i, read(memory,a+0x14+4*i))
            put(request, 16+4*i, read(memory,b+0x14+4*i))
        if index == 1:
            put(request,40,0x432A0000)
        put(request,30,0,1)
        records.append(('allocate', payload(request,0,56,REQUEST_HOLES),0x3AC49BA6,48,255,0))
        mutate(memory,first,second,index,enabled)
        result = RESULTS[index] if mask & (1 << index) else 0
        put(memory,ACTOR+0x40-index*4,result)
        if result:
            records.append(('copy',result+0x150,48,payload(packet,0,48,PACKET_HOLES)))
            for i in range(48):
                if i not in PACKET_HOLES:
                    memory[result+0x150+i]=packet[i]
    return public(memory), records


def public(memory):
    return {a:v for a,v in memory.items()
            if not STACK-0x300 <= a < STACK+0x140
            and not any(a == base+0x150+i for base in RESULTS for i in PACKET_HOLES)}


class SetupOracle(TriangleOracle):
    def __init__(self, words, memory, first, second, mask, enabled, phase):
        super().__init__(words,memory,phase=phase,entry=screen.ENTRY,arguments=(ACTOR,))
        self.initial=memory.copy()
        self.first,self.second,self.mask,self.enabled=first,second,mask,enabled
        self.records=[]
        self.allocations=0
        self.pending=None

    def record_call(self,target):
        if target == screen.SYMBOLS['func_151B30B0']:
            args=(*self.r[4:8],self.get(self.r[29]+16,4))
            self.records.append(('allocate',payload(self.memory,args[0],56,REQUEST_HOLES),*args[1:]))
            for i in REQUEST_HOLES:
                assert self.memory[args[0]+i] == self.initial[args[0]+i], ('request-hole',i)
            self.pending=('allocate',args)
        else:
            assert target == screen.SYMBOLS['memcpy'], ('unexpected-call',target)
            destination,source,length=self.r[4:7]
            self.records.append(('copy',destination,length,payload(self.memory,source,48,PACKET_HOLES)))
            for i in PACKET_HOLES:
                assert self.memory[source+i] == self.initial[source+i], ('packet-hole',i)
            self.pending=('copy',(destination,source,length))

    def hook(self,target):
        role,args=self.pending
        if role == 'allocate':
            index=self.allocations
            assert index < 3
            result=RESULTS[index] if self.mask & (1 << index) else 0
            mutate(self.memory,self.first,self.second,index,self.enabled)
            self.allocations+=1
        else:
            destination,source,length=args
            assert 0 <= length <= 48
            for i in range(length):
                self.put(destination+i,self.get(source+i,1),1)
            result=destination
        for i in range(4):
            self.put(self.r[29]+i*4,0xA5000100+i,4)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result


class GameOwnerLinkSetupRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-link-setup-test'
        cls.out.mkdir(exist_ok=True)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>210I',cls.rom,screen.ROM))
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.before={p:hashlib.sha256((cls.root/p).read_bytes()).hexdigest() for p in
            (screen.SOURCE,'conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/progress.csv')}

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,words,seed=0,layout=0,mask=7,enabled=True,phase=0):
        memory,first,second=fixture(seed,layout)
        model=SetupOracle(words,memory,first,second,mask,enabled,phase).run()
        self.assertEqual((public(model.memory),model.records),expected(memory,first,second,mask,enabled))
        self.assertEqual(model.allocations,3)
        return model

    def test_01_shape_catalog_keeps_nonmatching_status(self):
        rows=[]
        expected_shapes={'selected':(212,176,200),'grouped-actor-home':(211,168,192),
            'grouped-reuse-actor':(208,168,209)}
        for name,body in screen.candidates():
            meta,words=screen.compile_candidate(self.root,self.out,name,body)
            rows.append(meta)
            self.assertNotEqual(words,self.retail)
            self.assertEqual(meta['diagnostics'],'')
            self.assertEqual(meta['pool_bytes'],0)
            if name in expected_shapes:
                self.assertEqual(tuple(meta[k] for k in ('body_words','frame','differences')),expected_shapes[name])
            # All measured forms are rejected as a byte-exact installation.
            self.assertFalse(len(words)==210 and words==self.retail)
        self.assertEqual(len(rows),17)
        self.receipt('shapes',rows)

    def test_02_guest_defined_fields_failures_aliases_mutations(self):
        cases=0
        coverage=set()
        for seed,layout,mask,enabled,phase in itertools.product(range(3),range(4),range(8),(False,True),(0,8)):
            for words in (self.retail,self.words):
                model=self.compare(words,seed,layout,mask,enabled,phase)
                if words is self.retail:
                    coverage.update(model.visits)
            cases+=1
        self.receipt('guest',dict(cases=cases,executions=cases*2,retail_words_reached=len(coverage),
            defined_fields_only=True,raw_private_stack_parity=False,allocator_is_bounded=True))

    def test_03_compiled_effective_negative_controls(self):
        controls={
            'wrong-route':screen.SELECTED.replace('packet.route = 1;','packet.route = 2;'),
            'wrong-distance':screen.SELECTED.replace('request.distance = 170.0f;','request.distance = 80.0f;'),
            'late-first':screen.SELECTED.replace('    u8 *first = *(u8 **)(actor + 0x28);',
                '    u8 *first;').replace('    packet.route = 1;', '    first = *(u8 **)(actor + 0x28);\n    packet.route = 1;'),
            'omit-failed-store':screen.SELECTED.replace('    *(u8 **)(pair + 0x18) = created;',
                '    if (created != NULL) *(u8 **)(pair + 0x18) = created;'),
            'short-copy':screen.SELECTED.replace('memcpy(created + 0x150, &packet, 48);',
                'memcpy(created + 0x150, &packet, 44);')}
        results={}
        for name,body in controls.items():
            meta,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            rejected=False
            for mask in (0,7):
                try:
                    self.compare(words,mask=mask)
                except (AssertionError,KeyError):
                    rejected=True
                    break
            self.assertTrue(rejected,name)
            results[name]=dict(rejected=True,words=meta['body_words'])
        self.receipt('negatives',results)

    def test_04_native_32_layout(self):
        source=self.out/'layout.c'
        source.write_text('typedef unsigned char u8;typedef short s16;typedef int s32;'
            'typedef unsigned int u32;typedef float f32;\n'+screen.TYPES+
            '#define OFF(t,f) __builtin_offsetof(t,f)\n'
            '_Static_assert(sizeof(OwnerLinkEndpoint2348)==20,"endpoint");\n'
            '_Static_assert(sizeof(OwnerLinkPacket2348)==48,"packet");\n'
            '_Static_assert(sizeof(OwnerLinkRequest2348)==56,"request");\n'
            '_Static_assert(OFF(OwnerLinkPacket2348,second)==20,"second");\n'
            '_Static_assert(OFF(OwnerLinkPacket2348,actor)==40,"actor");\n'
            '_Static_assert(OFF(OwnerLinkPacket2348,route)==44,"route");\n'
            '_Static_assert(OFF(OwnerLinkRequest2348,distance)==40,"distance");\n'
            '_Static_assert(OFF(OwnerLinkRequest2348,tail)==52,"tail");\n')
        subprocess.run(['gcc','-m32','-std=c11','-Wall','-Wextra','-Werror','-c',
            str(source),'-o',str(self.out/'layout.o')],check=True,capture_output=True)
        self.receipt('layout',dict(pointer_bits=32,endpoint=20,packet=48,request=56,
            compile_time_only=True,native_semantic_execution=False))

    def test_05_original_assembly_and_production_unchanged(self):
        fragment=(self.root/'conker/asm/nonmatchings/generated_1DF510/func_151B2348.s').read_text()
        words=[int(x,16) for x in re.findall(r'/\* [0-9A-F]{6} [0-9A-F]{8} ([0-9A-F]{8}) \*/',fragment)]
        self.assertEqual(words,self.retail)
        self.assertIn(screen.ORIGINAL,(self.root/screen.SOURCE).read_text())
        pools=sections(self.root/'conker/build/conker.us.elf')
        start,data=pools['.game']
        self.assertEqual(list(struct.unpack_from('>210I',data,screen.ENTRY-start)),self.retail)
        after={p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in self.before}
        self.assertEqual(after,self.before)
        self.receipt('unchanged',after)


if __name__ == '__main__':
    unittest.main()
