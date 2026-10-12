"""Ordered ground collision, live callback state and complete guarded owner audit."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_ground_collision_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly, ELF_HEADER, SECTION_HEADER, SYMBOL
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_transform_setup_match as setup
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, BUFFER, OTHER, TYPES = guest.STACK, 0x24000, 0x34000, 0x50000
CONTEXT, HEIGHT, DELEGATE, CALLER, STOP = 0x1510F800, 0x1510F8D8, 0x150A49F4, 0x1503EEC0, 0x15060F28
rounded = setup.rounded


def swapped_constant_symbol(data):
    header=ELF_HEADER.unpack_from(data)
    headers=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
    tables=[s for s in headers if s[1]==2]; assert len(tables)==1
    table=tables[0]; strings=headers[table[6]]; names=data[strings[4]:strings[4]+strings[5]]
    found=[o for o in range(table[4],table[4]+table[5],table[9])
        if names[SYMBOL.unpack_from(data,o)[0]:].split(b'\0',1)[0]==b'D_80098928']
    assert len(found)==1 and table[9]==16
    symbol_start=found[0]; first=SYMBOL.unpack_from(data,symbol_start); second=SYMBOL.unpack_from(data,symbol_start+16)
    assert first[1:]==(0x80098928,0,16,0,0xFFF1)
    assert second[1:]==(0x150DEC90,44,18,0,5) and second[0]==first[0]+11
    string_start=strings[4]+first[0]
    assert data[string_start:string_start+25]==b'D_80098928\0func_150DEC90\0'
    result=bytearray(data)
    SYMBOL.pack_into(result,symbol_start,first[0],*second[1:])
    SYMBOL.pack_into(result,symbol_start+16,first[0]+14,*first[1:])
    result[string_start:string_start+25]=b'func_150DEC90\0D_80098928\0'
    return result,symbol_start,string_start


def address(base, index, size):
    return (base+(index & 0xFFFFFFFF)*size) & 0xFFFFFFFF


def public(memory):
    return {a: v for a, v in memory.items() if not STACK-0x800 <= a < STACK+0x140}


def fixture(count=3, kinds=(-1,), flag=1, acceleration=bits(-0.3), velocity=-8.0,
        y=0.0, slot=7, group=2, symbols=screen.SYMBOLS, buffer=BUFFER):
    memory = {STACK+i: 0xA5 for i in range(-0x800, 0x140)}
    control = address(symbols['D_800C6660'], slot, 16)
    for base, length in ((control-16, 48), (buffer-16, count*104+32), (OTHER-16, count*104+32)):
        memory.update({(base+i)&0xFFFFFFFF: 0x35 for i in range(length)})
    for base in {buffer, OTHER}:
        for index in range(count):
            for i, value in ((9, 1.75+index), (10, y), (11, -3.75-index), (18, 1.25),
                    (19, velocity), (20, -2.5), (21, 3.0), (22, -4.0), (23, 5.0)):
                put(memory, base+index*104+i*4, bits(value))
            put(memory, base+index*104+96, acceleration); put(memory, base+index*104+100, flag, 1)
    for g in {0,1,2,group,255}:
        put(memory, symbols['D_80098914']+g, count, 1)
        put(memory, symbols['D_80084454']+g*4, TYPES+g*512)
        for index in range(count): put(memory, TYPES+g*512+index, kinds[index % len(kinds)], 1)
    put(memory, control, buffer); put(memory, control+14, group, 1)
    put(memory, symbols['D_80098928'], 0x3ECCCCCD); put(memory, symbols['D_8009892C'], 0x3F4CCCCD)
    return memory


class Reference:
    def __init__(self, memory, slot=7, heights=(0,), symbols=screen.SYMBOLS, actions=None):
        self.memory, self.slot, self.heights, self.symbols = memory.copy(), slot, heights, symbols
        self.actions, self.calls, self.queried, self.bounced, self.settled = actions or {}, [], [], [], []
    def mutate(self, role):
        for a, v, size in self.actions.get(role, ()): put(self.memory, a, v, size)
    def run(self):
        s = self.symbols; self.calls.append((s['func_1510F800'], 0)); self.mutate('context')
        control = address(s['D_800C6660'], self.slot, 16)
        count = read(self.memory, s['D_80098914']+read(self.memory, control+14, 1), 1)
        if count:
            angular = floating(read(self.memory, s['D_80098928']))
            linear = floating(read(self.memory, s['D_8009892C']))
        for index in range(count):
            element = address(read(self.memory, control), index, 104)
            if not read(self.memory, element+100, 1): continue
            table = read(self.memory, s['D_80084454']+read(self.memory, control+14, 1)*4)
            if read(self.memory, table+index, 1) != 255: continue
            if floating(read(self.memory, element+96)) == 0.0: continue
            args = tuple(int(floating(read(self.memory, element+i*4))) & 0xFFFFFFFF for i in (9,10,11))+(0,)
            self.calls.append((s['func_1510F8D8'], *args))
            number = len(self.queried); self.queried.append(index); self.mutate(('height', number))
            floor = rounded(float(signed((self.heights[number % len(self.heights)]+5) & 0xFFFFFFFF)))
            if not floating(read(self.memory, element+40)) < floor: continue
            velocity = floating(read(self.memory, element+76))
            put(self.memory, element+40, bits(floor))
            if velocity < -4.0:
                for i, multiplier in ((18,linear),(19,-0.5),(20,linear),(21,-1.0),(22,angular),(23,-1.0)):
                    put(self.memory, element+i*4, bits(rounded(floating(read(self.memory, element+i*4))*multiplier)))
                self.bounced.append(index)
            else:
                for i in (23,22,21,24,20,19,18): put(self.memory, element+i*4, 0)
                self.settled.append(index)
        return self


class CollisionOracle(state.StateOracle):
    def __init__(self, words, memory, slot=7, heights=(0,), phase=0, symbols=screen.SYMBOLS,
            start=screen.ENTRY, actions=None, connected=None):
        guest.AttachmentOracle.__init__(self, words, memory, phase=phase, entry=start, arguments=(slot,), connected=connected)
        self.heights, self.symbols, self.actions, self.number = heights, symbols, actions or {}, 0
        self.entry_calls = []
    def record_call(self, target):
        if target == screen.ENTRY:
            self.entry_calls.append((target, self.r[4])); return
        width = 4 if target == self.symbols['func_1510F8D8'] else 2 if target == STOP else 1
        assert target in (self.symbols['func_1510F800'], self.symbols['func_1510F8D8'], DELEGATE, STOP), hex(target)
        self.calls.append((target, *self.arguments(width))); self.events.append(('CALL', target, *self.arguments(width)))
    def hook(self, target):
        if target in (self.symbols['func_1510F800'], DELEGATE): role, value = 'context', 0x81234567
        elif target == self.symbols['func_1510F8D8']:
            role, value = ('height', self.number), self.heights[self.number % len(self.heights)]
            self.number += 1
        else: assert target == STOP; role, value = 'stop', 0x81234567
        for a, v, size in self.actions.get(role, ()): self.put(a, v, size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register] = 0xA5000000+register
        self.r[2] = value & 0xFFFFFFFF
        self.f[:20] = [0xA5000000+i for i in range(20)]


class GameRecordGroundCollisionMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-ground-collision-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == '9367a1516def9e328ede83dc1c82584a6c6ae6e485ac32ff45bf57e29a9b0fde'
        assert cls.baseline['elf'] == '9ae3dd99b1c097f66414e7a23f5ad8d847b39e09b7112437687f9f173046f355'
        assert cls.baseline['guards'] == '2887c379208a8ddadbded3ee593396db2e7c7920261ee9f05443f0af412e7911'
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>134I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        body = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split('endlabel '+screen.FUNCTION, 1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.guards = cls.out/'successor-guards'; cls.guards.write_bytes(screen.guard_successor((cls.out/'before-guards').read_bytes()))
        cls.isolated = cls.out/'isolated-guards'
        with cls.isolated.open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(next(csv.reader(io.StringIO(cls.guards.read_text())))); writer.writerows(screen.GUARD_ROWS)
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot, word_patches_path=cls.isolated, filename='generated_6B320'))

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def link(self, name, start=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld'); script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))], check=True, capture_output=True)
        return list(struct.unpack_from('>134I', sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self), '_padded'): type(self)._padded = self.link('padded')
        return type(self)._padded

    def compare(self, memory, slot=7, heights=(0,), phase=0, actions=None,
            symbols=screen.SYMBOLS, start=screen.ENTRY, forms=None):
        expected = Reference(memory, slot, heights, symbols, actions).run()
        models = [CollisionOracle(w, memory, slot, heights, phase, symbols, start, actions).run()
            for w in forms or (self.retail,self.raw,self.padded)]
        for model in models: self.assertEqual((public(model.memory), model.calls), (public(expected.memory), expected.calls))
        for model in models[1:]:
            self.assertEqual((model.memory,model.events,model.r[2:],model.f),
                (models[0].memory,models[0].events,models[0].r[2:],models[0].f))
        self.assertEqual(models[0].r,models[2].r)
        return models

    def test_01_shape_complete_dead_store_and_profiles(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']), (134,104,15,0))
        self.assertEqual(self.padded,self.retail); self.assertEqual(self.link('original'),self.retail)
        self.assertEqual([i*4 for i,(a,b) in enumerate(zip(self.raw,self.retail)) if a!=b],
            [int(row[2],16) for row in screen.GUARD_ROWS])
        self.assertEqual(self.raw[108],0xE614005C)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'],536)
        for profile in ('compact','o1g3','o1'):
            _,words=screen.compile_candidate(self.root,self.out,profile,profile=profile)
            if profile=='compact': self.assertEqual(words,self.raw)
            else: self.assertNotEqual(words,self.raw)
        self.receipt('shape',words=134,frame=104,unchanged_words=119,guards=15,pool_bytes=0,
            duplicate_unreachable_zero_store_direct=True,no_drops_insertions=True,not_full_direct_exact=True)

    def test_02_counts_gates_collision_branches_and_reachable_words(self):
        cases,reached=0,set()
        for count,kinds,flag,acceleration,velocity in itertools.product((0,1,3,4,27,45,128,255),
                ((-1,),(-2,),(-128,-2,0,1,-1)),(0,255),(0,0x80000000,bits(-0.3)),(-8.0,-4.0)):
            models=self.compare(fixture(count,kinds,flag,acceleration,velocity))
            reached.update(models[0].visits); cases+=1
        for y,velocity,height,phase in itertools.product((-5.75,5.0,5.000001,12.5),
                (-4.000000476837158,-4.0,-3.999999761581421,-0.0),(-20,0,0xFFFFFFFC,0x1000000),(0,8)):
            models=self.compare(fixture(1,velocity=velocity,y=y),heights=(height,),phase=phase)
            reached.update(models[0].visits); cases+=1
        for slot,group in itertools.product((0,25,-1,0x80000000),(0,255)):
            self.compare(fixture(1,slot=slot,group=group),slot); cases+=1
        self.assertEqual(len(reached & set(range(screen.ENTRY,screen.ENTRY+536,4))),133)
        self.assertNotIn(screen.ENTRY+432,reached)
        self.receipt('guest',cases=cases,forms=3,reachable_words=133,dead_store_not_executed=True,
            unsigned_count_full_range_and_signed_type=True,exact_zero_acceleration_and_strict_floor_threshold=True,
            paired_F20_through_F31_saved=True,invalid_slots_mapped_guest_only=True)

    def test_03_context_and_height_callback_lifetimes(self):
        s=screen.SYMBOLS; control=s['D_800C6660']+7*16; cases=0
        for phase in (0,8):
            actions={'context':((s['D_80098914']+2,1,1),(s['D_80098928'],bits(0.25),4),(s['D_8009892C'],bits(0.5),4))}
            self.compare(fixture(),phase=phase,actions=actions); cases+=1
            for index in range(3):
                actions={('height',index):((BUFFER+index*104+40,bits(12),4),
                    (BUFFER+index*104+76,bits(-1),4),(BUFFER+index*104+96,0,4))}
                self.compare(fixture(),phase=phase,actions=actions); cases+=1
                actions={('height',index):((BUFFER+index*104+76,bits(-1),4),
                    (s['D_80098928'],bits(9),4),(s['D_8009892C'],bits(9),4))}
                self.compare(fixture(),phase=phase,actions=actions); cases+=1
            actions={('height',0):((control,OTHER,4),(s['D_80098914']+2,0,1))}
            models=self.compare(fixture(),phase=phase,actions=actions)
            self.assertEqual(models[0].number,3); cases+=1
            memory=fixture(); put(memory,TYPES+512+1,-2,1)
            actions={('height',0):((control+14,1,1),)}
            models=self.compare(memory,phase=phase,actions=actions)
            self.assertEqual(models[0].number,2); cases+=1
        self.receipt('callbacks',cases=cases,post_context_count_damping=True,
            cached_count_damping_current_element=True,live_next_buffer_group_type=True,
            post_query_Y_and_velocity=True,acceleration_gate_not_rechecked=True,all_effective=True)

    def test_04_self_alias_cached_damping_and_live_buffer_group(self):
        s=screen.SYMBOLS; control=s['D_800C6660']+7*16; cases=0
        for phase in (0,8):
            self.compare(fixture(buffer=s['D_8009892C']-72),phase=phase); cases+=1
            memory=fixture(2,buffer=control-40)
            extra=fixture(2,buffer=bits(5.0))
            memory.update({a:v for a,v in extra.items() if bits(5.0)-16<=a<bits(5.0)+240})
            models=self.compare(memory,phase=phase); self.assertEqual(read(models[0].memory,control),bits(5)); cases+=1
            memory=fixture(3,buffer=control-28); put(memory,TYPES+1,-2,1)
            models=self.compare(memory,phase=phase); self.assertEqual(read(models[0].memory,control+14,1),0)
            self.assertEqual(models[0].number,2); cases+=1
        self.receipt('aliases',cases=cases,effective_buffer_group_and_damping_aliases=True,
            mapped_guest_only_not_portable_C_alias_claim=True)

    def test_05_empty_and_skipped_unmapped_payloads(self):
        s=screen.SYMBOLS
        memory=fixture(0)
        for name in ('D_80098928','D_8009892C'):
            for i in range(4): del memory[s[name]+i]
        for a in list(memory):
            if s['D_80084454']<=a<s['D_80084454']+1024 or TYPES<=a<TYPES+131072: del memory[a]
        models=self.compare(memory); self.assertEqual(models[0].calls,[(CONTEXT,0)])
        for kinds,flag,acceleration in (((-1,),0,bits(-0.3)),((-2,),1,bits(-0.3)),((-1,),1,0)):
            memory=fixture(1,kinds,flag,acceleration)
            for i in range(36,48): del memory[BUFFER+i]
            if not flag:
                for a in list(memory):
                    if s['D_80084454']<=a<s['D_80084454']+1024 or TYPES<=a<TYPES+131072: del memory[a]
            self.compare(memory)
        cases=4
        for acceleration,velocity in itertools.product((1,0x80000001,0x7FC12345,0x7F800000),
                (0x80000000,0xFF800000,0x7FC12345,bits(-4.000000476837158))):
            memory=fixture(1,acceleration=acceleration); put(memory,BUFFER+76,velocity)
            self.compare(memory); cases+=1
        self.receipt('unmapped-floats',cases=cases,count_zero_constants_unmapped=True,
            skipped_coordinates_unmapped=True,subnormal_infinity_NaN_models_only=True,no_hardware_FCSR_claim=True)

    def test_06_independent_rebases_and_fired_faults(self):
        cases=0
        for j,start in enumerate((0x15207FFC,0x15308004)):
            symbols={name:(0x15100000+i*0x100 if name.startswith('func_') else
                (0x80107FFC if i%2==j else 0x80218004)+i*0x10000) for i,name in enumerate(screen.SYMBOLS)}
            forms=tuple(self.link(name,start,symbols) for name in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[2])
            for count,velocity,phase in itertools.product((0,3),(-8,-4),(0,8)):
                self.compare(fixture(count,velocity=velocity,symbols=symbols),phase=phase,symbols=symbols,start=start,forms=forms); cases+=1
        faults=0
        for count,kinds,flag,acceleration,velocity in ((0,(-1,),1,bits(-0.3),-8),
                (1,(-1,),0,bits(-0.3),-8),(1,(-2,),1,bits(-0.3),-8),(1,(-1,),1,0,-8),
                (1,(-1,),1,bits(-0.3),-8),(1,(-1,),1,bits(-0.3),-4)):
            memory=fixture(count,kinds,flag,acceleration,velocity)
            complete=CollisionOracle(self.retail,memory).run()
            for fault in range(complete.accesses):
                models=[CollisionOracle(w,memory) for w in (self.retail,self.raw,self.padded)]
                for model in models:
                    model.fault=fault
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,fault)
                for model in models[1:]: self.assertEqual((model.memory,model.events),(models[0].memory,models[0].events))
                self.assertEqual((models[0].r,models[0].f),(models[2].r,models[2].f)); faults+=1
        self.receipt('rebases-faults',symbols=7,links=2,cases=cases,fired_fault_triplets=faults,
            memory_events_exact=True,guarded_all_state_exact=True,raw_initialization_FPR_lifetime_different=True,
            no_portable_C_fault_hardware_claim=True)

    def test_07_effective_semantic_and_guard_controls(self):
        controls=(('wrong-type',screen.SELECTED.replace('[index] == -1','[index] == -2')),
            ('wrong-flag',screen.SELECTED.replace('unk64 != 0','unk64 == 0')),
            ('threshold',screen.SELECTED.replace('< -4.0f','< -9.0f')),
            ('no-offset',screen.SELECTED.replace('0) + 5','0) + 0')),
            ('wrong-damping',screen.SELECTED.replace('[18] *= linearDamping','[18] *= 0.0f')),
            ('live-damping',screen.SELECTED.replace('[18] *= linearDamping','[18] *= D_8009892C')))
        actions={('height',0):((screen.SYMBOLS['D_8009892C'],bits(9),4),)}
        for name,body in controls:
            self.assertNotEqual(body,screen.SELECTED); _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            model=CollisionOracle(words,fixture(),actions=actions).run()
            expected=Reference(fixture(),actions=actions).run()
            self.assertNotEqual((public(model.memory),model.calls),(public(expected.memory),expected.calls),name)
        wrong=self.out/'wrong-guards'; wrong.write_bytes(self.isolated.read_bytes().replace(b'0x46185402',b'0x46185403'))
        with self.assertRaises(ValueError): emit_padded_assembly(self.out/'selected.o',self.out/'slot.s',word_patches_path=wrong,filename='generated_6B320')
        self.receipt('controls',fresh_semantic=6,all_effective=True,stale_expected_word_rejected=True)

    def test_08_complete_owner_neighbors_and_both_padders(self):
        before=(self.out/'before-source').read_text(); objects=[]
        for stage,source in (('before',before),('after',screen.install(before))):
            obj,warnings=compile_owner(self.root,self.out,source,'owner-'+stage)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            self.assertEqual(warnings,[]); objects.append(obj)
        def fingerprint(obj,name):
            text,functions,relocations=parse_object(obj); item=functions[name]; a,b=item['value'],item['value']+item['size']
            return item['size'],text[a:b],{o-a:r for o,r in relocations.items() if a<=o<b}
        names=set(parse_object(objects[0])[1]); self.assertEqual(names,set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}: self.assertEqual(fingerprint(objects[0],name),fingerprint(objects[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes=[]
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed=[]
            for stage,obj in zip(('before','after'),objects):
                asm=self.out/(route+'-'+stage+'.s'); guards=self.out/'before-guards' if stage=='before' else self.guards
                args=[str(obj),str(self.out/'before-layout'),'generated_6B320',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6B320.s'),str(asm),'--filename','generated_6B320']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(guards)],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value']; expected=bytearray(parsed[0][0])
            expected[start:start+536]=parsed[1][0][start:start+536]; self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start<=o<start+536},
                {o:r for o,r in parsed[1][2].items() if not start<=o<start+536})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1]); self.receipt('owner',unchanged_neighbors=len(names)-1,
            both_padders=True,pools_exact=True,timer_caller35_and_impulse74_unchanged=True)

    def test_09_literal_source_ELF_guards_and_six_inputs(self):
        before_source=(self.out/'before-source').read_text(); current=(self.root/screen.SOURCE).read_text(); now=current!=before_source
        self.assertEqual(current,screen.install(before_source) if now else before_source)
        actual=(self.root/self.paths['elf']).read_bytes(); expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,536); extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if now:
            struct.pack_into('>134I',expected,start,*self.retail); struct.pack_into('>I',expected,extent,536)
            expected,_,_=swapped_constant_symbol(expected)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
            if name=='guards': self.assertEqual((self.root/path).read_bytes(),
                screen.guard_successor((self.out/'before-guards').read_bytes()) if now else (self.out/'before-guards').read_bytes())
            elif name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=now,ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+536],actual[start:start+536])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(),explicit_two_entry_symbol_string_swap=True,
            metadata_bytes=sum(a!=b for a,b in zip(self.before,actual))-
                sum(a!=b for a,b in zip(self.before[start:start+536],actual[start:start+536]))-
                sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            literal_every_other_byte_exact_no_generic_exception=True,
            guard_prefix_plus15_rows=True,six_other_inputs_exact=True,protected_data=data)

    def test_10_effective_stale_install_and_literal_integrity_controls(self):
        before=(self.out/'before-source').read_text()
        for stale in (screen.install(before),before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(stale)
        with self.assertRaises(AssertionError): screen.guard_successor(self.guards.read_bytes())
        rt,rb=Path.read_text,Path.read_bytes; source=self.root/screen.SOURCE; actual=source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k: actual+'\n' if p==source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_guards_and_six_inputs()
        elf=self.root/self.paths['elf']; actual=elf.read_bytes(); start=elf_slot_offset(actual,screen.ENTRY,536)
        _,symbol_start,string_start=swapped_constant_symbol(self.before)
        for offset in (start+4,start+432,start+536,installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)+3,
                symbol_start+4,symbol_start+15,string_start+8,string_start+25):
            wrong=bytearray(actual); wrong[offset]^=1
            with patch.object(Path,'read_bytes',lambda p: bytes(wrong) if p==elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_guards_and_six_inputs()
        guards=self.root/self.paths['guards']; wrong=guards.read_bytes()+b'\n'
        with patch.object(Path,'read_bytes',lambda p: wrong if p==guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_09_literal_source_ELF_guards_and_six_inputs()
        self.receipt('integrity-controls',stale_installs=2,duplicate_guards=1,source=1,ELF=8,guards=1,all_effective=True)

    def test_11_actual_timer_caller_and_context_wrapper(self):
        bodies={}
        for entry,rom,n in ((CALLER,0x6C370,35),(CONTEXT,0x13CCB0,8)):
            words=list(struct.unpack_from('>%dI'%n,self.before,elf_slot_offset(self.before,entry,n*4)))
            self.assertEqual(words,list(struct.unpack_from('>%dI'%n,self.rom,rom))); bodies[entry]=words
        cases=0; s=screen.SYMBOLS
        for count,velocity,phase,duration,step in itertools.product((0,1,3),(-8,-4),(0,8),(-1,1,9),(-1,1,5)):
            memory=fixture(count,velocity=velocity); control=s['D_800C6660']+7*16
            put(memory,control+12,duration,2); put(memory,0x800BE9E4,step)
            expected=Reference(memory).run(); result=signed((duration-step)&0xFFFFFFFF)
            put(expected.memory,control+12,result,2)
            calls=[(CONTEXT,0),(DELEGATE,0),*expected.calls[1:]]
            if result<=0: calls.append((STOP,0x800CC2D0+7*812,1))
            models=[]
            for words in (self.retail,self.raw,self.padded):
                connected={a+i*4:w for a,body in bodies.items() if a!=CALLER for i,w in enumerate(body)}
                connected.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
                model=CollisionOracle(bodies[CALLER],memory,phase=phase,start=CALLER,connected=connected).run(); models.append(model)
                self.assertEqual((public(model.memory),model.calls),(public(expected.memory),calls))
                self.assertEqual(model.entry_calls,[(screen.ENTRY,7)])
            for model in models[1:]: self.assertEqual((model.memory,model.events,model.r[2:],model.f),
                (models[0].memory,models[0].events,models[0].r[2:],models[0].f))
            self.assertEqual(models[0].r,models[2].r)
            cases+=1
        self.receipt('connected-caller',cases=cases,actual_timer35_collision134_context8=True,
            terrain215_and_context_delegate_and_stop_callbacks_modeled=True,not_full_gameplay_acceptance=True)

    def test_12_native32_full_count_domain_and_effective_controls(self):
        prefix=r'''
typedef unsigned char u8; typedef signed char s8; typedef unsigned u32; typedef int s32; typedef float f32;
typedef struct { u32 words[25]; u8 unk64,pad[3]; } struct04;
typedef struct { s32 unk0,unk4,unk8; u8 tail[4]; } struct106;
typedef char widths[(sizeof(void *)==4 && sizeof(struct04)==104 && sizeof(struct106)==16)?1:-1];
struct106 D_800C6660[26]; u8 D_80098914[3]; f32 D_80098928,D_8009892C;
static s8 rows[3][256]; s8 *D_80084454[3]={rows[0],rows[1],rows[2]};
static struct04 records[256],expected[256]; static int context_calls,height_calls,mutate,slot;
void func_1510F800(s32 mode) { if(mode) __builtin_trap(); context_calls++; }
s32 func_1510F8D8(s32 x,s32 y,s32 z,s32 mode) {
    if(mode || x<1 || z>-3) __builtin_trap();
    (void)y; height_calls++;
    if(mutate) { int i=x-1; if(height_calls==1) ((f32 *)&records[i])[19]=-1.0f;
        D_80098928=9.0f; D_8009892C=9.0f; }
    return 0;
}
static void initialize(int count,int pattern,int flag,int velocity,int location,int selected,int action) {
    slot=selected; mutate=action; context_calls=height_calls=0; D_80098928=0.4f; D_8009892C=0.8f;
    D_800C6660[slot].unk0=count?(s32)records:0; ((u8 *)&D_800C6660[slot])[14]=slot%3;
    for(int g=0;g<3;g++) { D_80098914[g]=count; for(int i=0;i<256;i++) rows[g][i]=pattern==0?-1:pattern==1?-2:(i%3==0?-1:i%3==1?-2:0); }
    for(int i=0;i<256;i++) {
        for(int j=0;j<25;j++) records[i].words[j]=0x35353535;
        records[i].unk64=flag; for(int j=0;j<3;j++) records[i].pad[j]=0x35;
        f32 *p=(f32 *)&records[i]; p[9]=i+1.75f; p[10]=location?8.0f:0.0f; p[11]=-3.75f-i;
        p[18]=1.25f; p[19]=velocity==0?-8.0f:velocity==1?-4.0f:-1.0f; p[20]=-2.5f;
        p[21]=3.0f; p[22]=-4.0f; p[23]=5.0f; p[24]=i%3==0?-0.3f:i%3==1?0.0f:-0.0f;
    }
}
static void reference(int selected) {
    func_1510F800(0); int group=((u8 *)&D_800C6660[selected])[14],count=D_80098914[group];
    f32 angular=D_80098928,linear=D_8009892C;
    for(int i=0;i<count;i++) {
        f32 *p=(f32 *)&records[i];
        if(!records[i].unk64 || rows[group][i]!=-1 || p[24]==0.0f) continue;
        int query=func_1510F8D8((int)p[9],(int)p[10],(int)p[11],0); f32 floor=(f32)(query+5);
        if(!(p[10]<floor)) continue;
        p[10]=floor;
        if(p[19]<-4.0f) { p[18]=p[18]*linear; p[19]=p[19]*-0.5f; p[20]=p[20]*linear;
            p[21]=p[21]*-1.0f; p[22]=p[22]*angular; p[23]=p[23]*-1.0f; }
        else { p[23]=p[22]=p[21]=p[24]=p[20]=p[19]=p[18]=0.0f; }
    }
}
'''
        suffix=r'''
static int run(u32 *failure) {
    int slots[3]={0,7,25}; unsigned cases=0;
    for(int count=0;count<256;count++) for(int pattern=0;pattern<3;pattern++) for(int flag=0;flag<2;flag++)
    for(int velocity=0;velocity<3;velocity++) for(int location=0;location<2;location++) for(int selected=0;selected<3;selected++) {
        int action=(count%2); initialize(count,pattern,flag,velocity,location,slots[selected],action); reference(slots[selected]);
        int calls=height_calls;
        for(int i=0;i<256*26;i++) ((u32 *)expected)[i]=((u32 *)records)[i];
        initialize(count,pattern,flag,velocity,location,slots[selected],action); func_1503ECA0(slots[selected]); cases++;
        for(int i=0;i<256*26;i++) if(((u32 *)records)[i]!=((u32 *)expected)[i]) {
            failure[0]=cases; failure[1]=i; failure[2]=((u32 *)records)[i]; return 1;
        }
        if(context_calls!=1 || height_calls!=calls) return 3;
    }
    return cases==27648?0:2;
}
void _start(void) { u32 failure[3]; int result=run(failure);
    if(result==1) __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory"); __builtin_unreachable(); }
'''
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],prefix+screen.SELECTED+suffix,profile),(0,''))
        for name,body in (('type',screen.SELECTED.replace('[index] == -1','[index] == -2')),
                ('threshold',screen.SELECTED.replace('< -4.0f','< -9.0f')),
                ('offset',screen.SELECTED.replace('0) + 5','0) + 0')),
                ('live-damping',screen.SELECTED.replace('[18] *= linearDamping','[18] *= D_8009892C'))):
            result,detail=self.run_native('native-negative-'+name,prefix+body+suffix)
            self.assertEqual(result,1); self.assertEqual(len(detail),3)
        self.receipt('native',cases_per_profile=27648,profiles=['O2','O0'],counts_all_0_through255=True,
            all_26_words_of_256_records=True,three_slots_types_flags_threshold_and_floor_cases=True,
            post_query_velocity_and_cached_damping=True,effective_controls=4,
            no_private_alias_signed_overflow_FCSR_claim=True)


if __name__ == '__main__':
    unittest.main()
