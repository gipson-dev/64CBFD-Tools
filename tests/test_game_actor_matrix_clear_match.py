"""Live-mask matrix clear, closed register guards and full linked isolation."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_matrix_clear_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests import test_game_actor_renderer_install_match as native
from tools.check_game_data_layout import audit_layout

ACTOR, BUFFER, ALT, PROVIDER, CALLER = 0x22000, 0x30000, 0x31000, 0x1502DB20, 0x150347E8
COUNTS = (-0x80000000, -4, -1, 0, 1, 2, 3, 31, 32, 33, 0x7FFFFFFF)
MASKS = (0, 1, 2, 0x80000000, 0x80000001, 0xFFFFFFFF, 0xA5A5A5A5, 0x8000)
TYPES = (0, 4, 59, 117, 130, 176, 255)
SPECIAL = (59, 117, 130, 136, 144, 150, 152, 156, 157, 159, 160, 177, 178, 180)
ACTORS, DISABLED, COUNT_TABLE, JUMP_TABLE = 0x800CC2D0, 0x800BEAC0, 0x800C4ED0, 0x80096DF8


def signed(value):
    value &= 0xFFFFFFFF
    return value if value < 0x80000000 else value-0x100000000


def fixture(kind=0, count=2, mask=1, buffer=BUFFER):
    memory = {STACK+i: (i*17+165)&255 for i in range(-0x200, 0x80)}
    for base, size in ((ACTOR-2048, 0x32C+2048), (BUFFER-16, 2080), (ALT-16, 2080)):
        memory.update({base+i: (i*13+165)&255 for i in range(size)})
    put(memory, ACTOR+4, kind, 1)
    put(memory, ACTOR+0x9C, mask)
    put(memory, ACTOR+0x1D4, buffer)
    return memory


def reference(memory, count, mutation=0, actor=ACTOR):
    memory = memory.copy()
    calls, writes = [], []
    if read(memory, actor+0x1D4) and read(memory, actor+0x9C):
        calls.append((PROVIDER, (read(memory, actor+4, 1),)))
        changes = ()
        if mutation == 1:
            changes = ((actor+0x1D4, ALT), (actor+0x9C, read(memory, actor+0x9C)^0xFFFFFFFF))
        elif mutation == 2:
            changes = ((actor+0x1D4, 0), (actor+0x9C, 0))
        for address, value in changes:
            put(memory, address, value)
            writes.append(('W', address, 4, value))
        buffer = read(memory, actor+0x1D4)
        last = min(signed((count & 0xFFFFFFFF)-1), 31)
        for bone in range(last, -1, -1):
            if read(memory, actor+0x9C) & (1 << bone):
                for row, offset in itertools.product(range(3), (0, 4, 8)):
                    address = (buffer+(bone<<6)+(row<<4)+offset)&0xFFFFFFFF
                    put(memory, address, 0)
                    writes.append(('W', address, 4, 0))
    return memory, calls, writes


class AccessFault(Exception):
    pass


class ClearOracle(TriangleOracle):
    def __init__(self, words, memory, count=2, mutation=0, phase=0, actor=ACTOR,
                 entry=screen.ENTRY, connected=None):
        self.fault, self.accesses, self.in_hook = None, 0, False
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(actor,), connected=connected)
        self.count, self.mutation, self.actor, self.after_provider = count, mutation, actor, False

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault == self.accesses:
                raise AccessFault()
            self.accesses += 1

    def get(self, address, size):
        self.gate()
        return super().get(address, size)

    def put(self, address, value, size):
        self.gate()
        return super().put(address, value, size)

    def record_call(self, target):
        assert target in (PROVIDER, screen.ENTRY)
        args = (self.r[4],)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target == PROVIDER
        self.in_hook = True
        try:
            if self.mutation == 1:
                self.put(self.actor+0x1D4, ALT, 4)
                self.put(self.actor+0x9C, self.get(self.actor+0x9C, 4)^0xFFFFFFFF, 4)
            elif self.mutation == 2:
                self.put(self.actor+0x1D4, 0, 4)
                self.put(self.actor+0x9C, 0, 4)
            for register in (1, 2, 3, *range(4, 16), 24, 25):
                self.r[register] = 0xA5000000 if 6 <= register <= 15 else 0xA5000000+register
            self.r[2] = self.count & 0xFFFFFFFF
            self.f[:20] = [0xA5000000+i for i in range(20)]
            self.after_provider = True
        finally:
            self.in_hook = False


def registers(model, raw=False):
    result = model.r.copy()
    if raw and model.after_provider:
        for register in range(6, 16):
            result[register+1 if register<15 else 6] = model.r[register]
    return result


def external(memory):
    return {a:v for a,v in memory.items() if not STACK-0x200 <= a < STACK+0x80}


class GameActorMatrixClearMatchTests(unittest.TestCase):
    run_native = native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-actor-matrix-clear-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.owner_before = (cls.out/'before-source').read_text()
        cls.owner_after = screen.recovered_owner(cls.owner_before)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>48I', cls.rom, screen.ROM))
        cls.guard_before = (cls.out/'before-guards').read_bytes()
        cls.guard_after = screen.guard_bytes(cls.guard_before)
        (cls.out/'qualified-guards.csv').write_bytes(cls.guard_after)
        cls.helper = list(struct.unpack_from('>25I', cls.rom, 0x5AFD0))
        cls.caller = list(struct.unpack_from('>27I', cls.rom, 0x61C98))
        cls.helper_source = re.search(r's32 func_1502DB20\([^{}]+\) \{\n.*?\n\}',
            (cls.root/'conker/src/game/generated_58F80.c').read_text(), re.S).group(0)
        cls.caller_source = re.search(r'void func_150347E8\(void\) \{\n.*?\n\}',cls.owner_before,re.S).group(0)
        table_offset = elf_slot_offset(cls.before,JUMP_TABLE,256)
        cls.jump_table = cls.before[table_offset:table_offset+256]

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def test_01_complete_body_closed_guard_derivation_and_effective_guard_controls(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['diagnostics'], self.meta['pool_bytes']), (48, 32, 18, '', 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.meta['relocations'], {0x28:[('R_MIPS_26', 'func_1502DB20')]})
        self.assertEqual(len(screen.owner_guards()), 18)
        for offset, expected in screen.GUARD_INPUTS:
            bad = self.raw.copy()
            bad[offset//4] ^= 1
            with self.assertRaisesRegex(AssertionError, 'stale matrix-clear allocation'):
                screen.normalize(bad)
            actual = self.raw[offset//4]
            fitted = screen.renamed_word(actual, offset)
            self.assertEqual(actual>>26, fitted>>26)
            if actual>>26 == 0:
                self.assertEqual(actual & 0x7FF, fitted & 0x7FF)
            else:
                self.assertEqual(actual & 65535, fitted & 65535)
        self.assertEqual(self.raw[:12], self.retail[:12])
        for address, rom, size in ((PROVIDER, 0x5AFD0, 100), (CALLER, 0x61C98, 108)):
            offset = elf_slot_offset(self.before, address, size)
            self.assertEqual(self.before[offset:offset+size], self.rom[rom:rom+size])
        with self.assertRaisesRegex(ValueError, 'already installed'):
            screen.guard_bytes(self.guard_after)

    def compare_case(self, memory, count, mutation=0, phase=0):
        expected, calls, writes = reference(memory, count, mutation)
        models = [ClearOracle(words, memory, count, mutation, phase).run() for words in (self.retail, self.raw, self.words)]
        for index, model in enumerate(models):
            self.assertEqual(external(model.memory), external(expected))
            self.assertEqual(model.calls, calls)
            self.assertEqual([e for e in model.events if e[0]=='W' and not STACK-0x200<=e[1]<STACK+0x80], writes)
            self.assertEqual((model.memory, model.events, model.calls, model.f, model.visits, registers(model,index==1)),
                (models[0].memory, models[0].events, models[0].calls, models[0].f, models[0].visits, models[0].r))
        return models[0].visits

    def test_02_guest_signed_clamp_all_types_mutations_aliases_and_full_storage(self):
        cases, coverage = 0, set()
        for kind,count,mask,mutation,phase in itertools.product(TYPES, COUNTS, MASKS, range(3), (0,8)):
            coverage.update(self.compare_case(fixture(kind,count,mask), count, mutation, phase))
            cases += 1
        for kind,count in itertools.product(range(256), (1,32)):
            coverage.update(self.compare_case(fixture(kind,count,0x80000001),count))
            cases += 1
        for kind,mask,phase in itertools.product(TYPES,MASKS,(0,8)):
            coverage.update(self.compare_case(fixture(kind,2,mask,0),2,phase=phase))
            cases += 1
        aliases = 0
        for count,mask,phase in itertools.product((1,2,31,32), (1,0x80000000,0xFFFFFFFF),(0,8)):
            memory = fixture(count=count,mask=mask)
            put(memory,ACTOR+0x1D4, ACTOR+0x9C-(min(count-1,31)<<6))
            self.compare_case(memory,count,phase=phase)
            aliases += 1
        self.assertEqual(cases, 4320)
        self.assertEqual(aliases,24)
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+192,4)))
        self.receipt('guest',cases=cases,alias_cases=aliases,covered_words=48,
            raw_fitted_original=True,raw_register_cycle_canonicalized=True,complete_public_storage_and_write_order=True)

    def test_03_fired_own_access_faults_and_minimal_gates(self):
        cases = [fixture(count=32,mask=0xFFFFFFFF),fixture(count=2,mask=1),fixture(count=0,mask=1),fixture(mask=0)]
        counts = (32,2,0,2)
        cuts = 0
        for memory,count in zip(cases,counts):
            complete = ClearOracle(self.words,memory,count).run()
            for cut in range(complete.accesses):
                pair = []
                for words in (self.retail,self.raw,self.words):
                    model = ClearOracle(words,memory,count)
                    model.fault = cut
                    with self.assertRaises(AccessFault):
                        model.run()
                    self.assertEqual(model.accesses,cut)
                    pair.append(model)
                for index,model in enumerate(pair):
                    self.assertEqual((model.memory,model.events,model.calls,model.f,registers(model,index==1)),
                        (pair[0].memory,pair[0].events,pair[0].calls,pair[0].f,pair[0].r))
                cuts += 1
        minimal = fixture(buffer=0)
        for address in (ACTOR+4,*range(ACTOR+0x9C,ACTOR+0xA0)):
            del minimal[address]
        for words in (self.retail,self.raw,self.words):
            self.assertEqual(ClearOracle(words,minimal).run().calls,[])
            broken = fixture()
            del broken[ACTOR+4]
            with self.assertRaisesRegex(AssertionError,'unmapped read'):
                ClearOracle(words,broken).run()
        self.receipt('faults',fired_cut_triples=cuts,provider_accesses_excluded=True,completed_controls=True)

    def native_source(self, body):
        return '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
u8 actor[0x32C] __attribute__((aligned(4))),matrices[2][2048] __attribute__((aligned(4)));
u8 wantedActor[0x32C],wantedMatrices[2][2048];
int countValue,mutation,calls,error,wantedType;
s32 func_1502DB20(s32 type){if(type!=wantedType)error=1;calls++;
 if(mutation){*(u32*)(actor+0x1D4)=(u32)matrices[1];*(u32*)(actor+0x9C)^=0xFFFFFFFFU;}
 return countValue;
}
''' + body + '''
int check(void){int kind,c,m,x,i,j,k,row,offset,callExpected,last;
 int counts[]={0,1,2,31,32,33,(-2147483647-1),-4};
 u32 masks[]={0,1,0x80000000U,0xFFFFFFFFU};
 if(sizeof(void*)!=4 || sizeof(f32)!=4)return 9;
 for(kind=0;kind<256;kind++)for(c=0;c<8;c++)for(x=0;x<4;x++)for(m=0;m<2;m++){
  for(i=0;i<0x32C;i++)actor[i]=(u8)(i*13+165);
  for(j=0;j<2;j++)for(i=0;i<2048;i++)matrices[j][i]=wantedMatrices[j][i]=(u8)(i*17+165);
  actor[4]=(u8)kind;*(u32*)(actor+0x1D4)=(u32)matrices[0];*(u32*)(actor+0x9C)=masks[x];
  for(i=0;i<0x32C;i++)wantedActor[i]=actor[i];
  countValue=counts[c];mutation=m;calls=error=0;wantedType=kind;callExpected=masks[x]!=0;
  if(callExpected && m){*(u32*)(wantedActor+0x1D4)=(u32)matrices[1];*(u32*)(wantedActor+0x9C)^=0xFFFFFFFFU;}
  last=(s32)((u32)countValue-1);if(last>31)last=31;
  if(callExpected)for(k=last;k>=0;k--)if(*(u32*)(wantedActor+0x9C)&(1U<<k))
   for(row=0;row<3;row++)for(offset=0;offset<12;offset++)wantedMatrices[m][k*64+row*16+offset]=0;
  func_15034728(actor);
  if(error || calls!=callExpected)return 1;
  for(i=0;i<0x32C;i++)if(actor[i]!=wantedActor[i])return 2;
  for(j=0;j<2;j++)for(i=0;i<2048;i++)if(matrices[j][i]!=wantedMatrices[j][i])return 3;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''

    def test_04_actual_native32_source_and_effective_semantic_negatives(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(screen.SELECTED),profile),(0,''))
        negatives = {'fourth-row':screen.SELECTED.replace('row < 3','row < 4'),
            'fourth-component':screen.SELECTED.replace('offset < 12','offset < 16'),
            'cached-buffer':screen.SELECTED.replace('    last = (s32)((u32)func_1502DB20(actor[4]) - 1);\n    buffer = *(u32 *)(actor + 0x1D4);',
                '    buffer = *(u32 *)(actor + 0x1D4);\n    last = (s32)((u32)func_1502DB20(actor[4]) - 1);'),
            'wrong-clamp':screen.SELECTED.replace('bone = 31','bone = 30').replace('last < 31','last < 30'),
            'byte-mask':screen.SELECTED.replace('*(u32 *)(actor + 0x9C)','*(u8 *)(actor + 0x9C)')}
        for name,body in negatives.items():
            self.assertNotEqual(body,screen.SELECTED)
            self.assertIn(self.run_native('negative-'+name,self.native_source(body))[0],(1,2,3))
        self.receipt('native',cases_per_profile=16384,profiles=['O2','O0'],effective_negatives=5,
            full_record_and_both_matrix_buffers=True)

    def test_05_copied_owner_pools_neighbors_and_both_full_padders(self):
        objects = [screen.compile_owner(self.root,self.out,source,name) for source,name in
            ((self.owner_before,'owner-before'),(self.owner_after,'owner-after'))]
        self.assertEqual([warnings for _,warnings in objects],[[],[]])
        before,after = [parse_object(obj) for obj,_ in objects]
        self.assertEqual(before[1].keys(),after[1].keys())
        for name in before[1]:
            a,b = before[1][name],after[1][name]
            if name != screen.FUNCTION:
                self.assertEqual(before[0][a['value']:a['value']+a['size']],after[0][b['value']:b['value']+b['size']],name)
                self.assertEqual({o-a['value']:r for o,r in before[2].items() if a['value']<=o<a['value']+a['size']},
                    {o-b['value']:r for o,r in after[2].items() if b['value']<=o<b['value']+b['size']},name)
        self.assertEqual(normalized_pools(objects[0][0]),normalized_pools(objects[1][0]))
        isolated = parse_object(self.out/'selected.o')
        target = after[1][screen.FUNCTION]
        self.assertEqual(after[0][target['value']:target['value']+192],isolated[0][:192])
        self.assertEqual({o-target['value']:r for o,r in after[2].items() if target['value']<=o<target['value']+192},isolated[2])
        padded = []
        for script in ('pad_c_object.py','pad_generated_object.py'):
            asm = self.out/(script+'.s')
            args = [str(objects[1][0]),str(self.root/'conker/retail_layout.us.txt'),'generated_61490',str(asm)] if script=='pad_c_object.py' else [
                str(objects[1][0]),str(self.root/'conker/asm/61490.s'),str(asm),'--filename','generated_61490']
            result = subprocess.run([sys.executable,str(self.root/'tools'/script),*args,
                '--word-patches',str(self.out/'qualified-guards.csv'),'--rodata-symbol','jtbl_80097D20_game'],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(self.root/'conker'),'-o',str(obj),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0],padded[1])
        self.assertEqual(padded[0][1][screen.FUNCTION]['size'],192)
        self.receipt('owner',neighbors=len(after[1])-1,both_full_padders_identical=True,normalized_pools_equal=True)

    def test_06_independent_original_and_fitted_symbol_rebases(self):
        original = (self.root/'conker/asm/61490.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        original = 'glabel '+screen.FUNCTION+'\n'+original.split('endlabel '+screen.FUNCTION,1)[0]+'endlabel '+screen.FUNCTION+'\n'
        asm = self.out/'original.s'
        asm.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+original)
        obj = asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        for i,entry,provider in ((0,screen.ENTRY,PROVIDER),(1,0x15234728,0x1512DB20),(2,0x15334728,0x1522DB20)):
            with patch.multiple(screen,ENTRY=entry,SYMBOLS={'func_1502DB20':provider}):
                _,raw = screen.compile_candidate(self.root,self.out,'rebase-'+str(i))
            fitted = screen.normalize(raw)
            ld = self.out/('original-'+str(i)+'.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf = ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',screen.FUNCTION,
                '--defsym=func_1502DB20=0x%X'%provider,'-o',str(elf),str(obj)],check=True,capture_output=True)
            self.assertEqual(fitted,list(struct.unpack_from('>48I',sections(elf)['.text'][1])))

    def test_07_literal_whole_image_guard_prefix_protected_inputs_and_history(self):
        current = (self.root/self.paths['elf']).read_bytes()
        source = (self.root/screen.SOURCE).read_text()
        expected = bytearray(self.before)
        offset = elf_slot_offset(self.before,screen.ENTRY,192)
        self.assertEqual(offset,elf_slot_offset(current,screen.ENTRY,192))
        installed = source==self.owner_after
        if installed:
            expected[offset:offset+192] = struct.pack('>48I',*self.retail)
            with patch.multiple(descriptor.screen,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
                size_offset = descriptor.size_field(self.before)
            struct.pack_into('>I',expected,size_offset,192)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        guard_bytes = (self.root/self.paths['guards']).read_bytes()
        self.assertEqual(guard_bytes,self.guard_after if installed else self.guard_before)
        self.assertTrue(self.guard_after.startswith(self.guard_before))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(hashlib.sha256(self.guard_before).hexdigest(),
            '3f12cf872b84100963934734de2e67f5f07073ce3112ccbd2e5c4cb8af84666e')
        old_rows = list(csv.DictReader(self.guard_before.decode().splitlines()))
        self.assertEqual(len(old_rows),14623)
        self.assertEqual(rows, old_rows+screen.owner_guards() if installed else old_rows)
        for name in ('progress','layout','makefile'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        data = audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,literal_whole_image=True,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data)

    def connected_fixture(self,disabled,mode):
        memory = {STACK+i:165 for i in range(-0x200,0x80)}
        for base,size in ((ACTORS-2048,2048+25*0x32C),(BUFFER-16,2080),(COUNT_TABLE,512)):
            memory.update({base+i:(i*13+165)&255 for i in range(size)})
        memory.update({JUMP_TABLE+i:v for i,v in enumerate(self.jump_table)})
        memory[DISABLED] = disabled
        for kind in range(256):
            count = {0:1,59:4,117:36,130:37,255:2}.get(kind,5)
            put(memory,COUNT_TABLE+kind*2,count,2)
        for i in range(25):
            actor = ACTORS+i*0x32C
            put(memory,actor,int(i%3!=0))
            put(memory,actor+4,(0,59,117,130,255)[i%5],1)
            put(memory,actor+0x9C,MASKS[(i+mode)%8])
            buffer = 0 if mode==2 and i%3==1 else BUFFER
            if mode==4:
                buffer = ACTORS+2*0x32C+0x9C-(31<<6)
                put(memory,actor+0x9C,0xFFFFFFFF)
            put(memory,actor+0x1D4,buffer)
        return memory

    def connected_reference(self,memory):
        memory = memory.copy()
        calls = []
        if memory[DISABLED]==0:
            for i in range(25):
                actor = ACTORS+i*0x32C
                if read(memory,actor) and read(memory,actor+0x9C):
                    calls.append((screen.ENTRY,(actor,)))
                    kind = read(memory,actor+4,1)
                    count = read(memory,COUNT_TABLE+kind*2,2)-(4 if kind in SPECIAL else 0)
                    memory,inner,_ = reference(memory,count,actor=actor)
                    calls.extend(inner)
        return memory,calls

    def native_connected(self,body=screen.SELECTED):
        prefix = r'''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
u8 backing[2048+20300] __attribute__((aligned(4))),wanted[2048+20300];
u8 matrix[2048] __attribute__((aligned(4))),wantedMatrix[2048],D_800BEAC0;
u16 D_800C4ED0[256];extern u8 D_800CC2D0[];extern s32 D_800D121C;
__asm__(".globl D_800CC2D0\n.set D_800CC2D0,backing+2048\n.globl D_800D121C\n.set D_800D121C,D_800CC2D0+20300");
'''
        check = r'''
int special(int t){int types[]={59,117,130,136,144,150,152,156,157,159,160,177,178,180};int i;
 for(i=0;i<14;i++){if(t==types[i])return 1;}
 return 0;
}
int check(void){int disable,mode,i,t,k,r,x,last;u8 *a;u32 b,address;
 if(sizeof(void*)!=4)return 9;
 for(disable=0;disable<2;disable++)for(mode=0;mode<6;mode++){
  for(i=0;i<2048+20300;i++)backing[i]=(u8)(i*13+165);
  for(i=0;i<2048;i++)matrix[i]=wantedMatrix[i]=(u8)(i*17+165);
  for(i=0;i<256;i++)D_800C4ED0[i]=5;
  D_800C4ED0[0]=1;D_800C4ED0[59]=4;D_800C4ED0[117]=36;D_800C4ED0[130]=37;D_800C4ED0[255]=2;
  D_800BEAC0=(u8)disable;
  for(i=0;i<25;i++){
   int types[]={0,59,117,130,255};u32 masks[]={0,1,2,0x80000000U,0x80000001U,0xFFFFFFFFU,0xA5A5A5A5U,0x8000};
   a=D_800CC2D0+i*0x32C;*(u32*)a=(u32)(i%3!=0);a[4]=(u8)types[i%5];*(u32*)(a+0x9C)=masks[(i+mode)%8];
   b=(mode==2 && i%3==1)?0:(u32)matrix;
   if(mode==4){b=(u32)D_800CC2D0+2*0x32C+0x9C-(31U<<6);*(u32*)(a+0x9C)=0xFFFFFFFFU;}
   *(u32*)(a+0x1D4)=b;
  }
  for(i=0;i<2048+20300;i++)wanted[i]=backing[i];
  if(!disable)for(i=0;i<25;i++){
   a=wanted+2048+i*0x32C;
   if(!*(u32*)a || !*(u32*)(a+0x9C) || !*(u32*)(a+0x1D4))continue;
   t=a[4];last=D_800C4ED0[t]-(special(t)?4:0)-1;if(last>31)last=31;b=*(u32*)(a+0x1D4);
   for(k=last;k>=0;k--)if(*(u32*)(a+0x9C)&(1U<<k))for(r=0;r<3;r++)for(x=0;x<12;x++){
    address=b+(u32)k*64+(u32)r*16+(u32)x;
    if(address>=(u32)backing && address<(u32)backing+sizeof(backing))wanted[address-(u32)backing]=0;
    else if(address>=(u32)matrix && address<(u32)matrix+2048)wantedMatrix[address-(u32)matrix]=0;
    else return 8;
   }
  }
  func_150347E8();
  for(i=0;i<2048+20300;i++)if(backing[i]!=wanted[i])return 1;
  for(i=0;i<2048;i++)if(matrix[i]!=wantedMatrix[i])return 2;
 }
 return 0;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''
        return prefix+self.helper_source+'\n'+body+'\n'+self.caller_source+'\n'+check

    def test_08_actual_connected_caller_helper_table_and_native_C_chain(self):
        cases = 0
        for disabled,mode,phase in itertools.product((0,1,255),range(6),(0,8)):
            memory = self.connected_fixture(disabled,mode)
            expected,calls = self.connected_reference(memory)
            models = []
            for words in (self.retail,self.raw,self.words):
                connected = dict(zip(range(screen.ENTRY,screen.ENTRY+192,4),words))
                connected.update(zip(range(PROVIDER,PROVIDER+100,4),self.helper))
                model = ClearOracle(self.caller,memory,phase=phase,entry=CALLER,connected=connected).run()
                self.assertEqual(external(model.memory),external(expected))
                self.assertEqual(model.calls,calls)
                models.append(model)
            for model in models[1:]:
                self.assertEqual((model.memory,model.events,model.calls,model.f),
                    (models[0].memory,models[0].events,models[0].calls,models[0].f))
            self.assertEqual(models[2].r,models[0].r)
            cases += 1
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-connected-'+profile[1:],self.native_connected(),profile),(0,''))
        self.receipt('connected',guest_cases=cases,caller_words=27,helper_words=25,actor_count=25,
            actual_instructions_and_table=True,native_cases_per_profile=12,native_profiles=['O2','O0'],
            raw_public_effects_fitted_full_machine_state=True,live_future_actor_alias=True)


if __name__=='__main__':
    unittest.main()
