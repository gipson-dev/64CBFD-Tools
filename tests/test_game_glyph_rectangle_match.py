"""Signed glyph math, typed caller/lookup/draw chain and guarded linked audit."""
import csv
import hashlib
import io
import itertools
import json
import re
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_glyph_rectangle_candidates as screen
from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import signed

STACK, OUTPUT, TEXT, TABLE = guest.STACK, 0x30000, 0x50000, 0x800848D0
LOOKUP, LOOKUP_ROM = 0x15041480, 0x6E930
OWNER = 0x150412C0
MASK = 0xFFFFFFFF
GLYPHS = (-2147483648,-2147483647,-129,-80,-17,-16,-9,-8,-7,-1,
    0,1,7,8,9,63,64,79,80,255,2147483646,2147483647)
COORDS = (-2147483648,-1025,-1,0,1,1023,1024,2147483647)
OUTPUTS = (OUTPUT,0x80010000,0xFFFFFFF0)


def quotient(value):
    return (abs(value)//8)*(1 if value >= 0 else -1)


def glyph_commands(x,y,index):
    q = quotient(index); remainder = index-q*8
    x,y = x&MASK,y&MASK
    return ((0xE4000000 | ((((x+8)<<2)&4095)<<12) | (((y+12)<<2)&4095),
        (((x<<2)&4095)<<12) | ((y<<2)&4095)),
        (0xE1000000,((remainder*256)&65535)<<16 | ((q*384)&65535)),
        (0xF1000000,0x04000400))


def fixture(output=OUTPUT,pattern=0,table=None,text=b'aZ?\x00',alias=0,table_address=TABLE):
    memory = {STACK+i:0xA5 for i in range(-256,192)}
    memory.update({(output+i)&MASK:(i*17+53+pattern*19)&255 for i in range(-16,1552)})
    if table is not None:
        memory.update({table_address+i:table[i] if i < 80 else 0xA5 for i in range(256)})
    text_address = output if alias == 1 else TEXT
    if alias == 2:
        output = table_address
    memory.update({text_address+i:text[i] if i < len(text) else 0 for i in range(128)})
    return memory,output,text_address


class Reference:
    def __init__(self,memory,lookup=LOOKUP,leaf=screen.ENTRY,table=TABLE):
        self.memory,self.events,self.calls = memory.copy(),[],[]
        self.lookup,self.leaf,self.table = lookup,leaf,table
    def get(self,address):
        address &= MASK
        assert address in self.memory,('reference unmapped byte',address)
        value = read(self.memory,address,1)
        self.events.append(('R',address,1,value))
        return value
    def store(self,address,value):
        address &= MASK
        assert all(address+i in self.memory for i in range(4)),('reference unmapped write',address)
        put(self.memory,address,value)
        self.events.append(('W',address,4,value&MASK))
    def draw(self,output,x,y,index):
        for i,pair in enumerate(glyph_commands(x,y,index)):
            for j in ((1,0) if i == 0 else (0,1)):
                self.store(output+i*8+j*4,pair[j])
        return (output+24)&MASK
    def find(self,code):
        for i in range(80):
            if self.get(self.table+i) == code:
                return i
        return 80
    def call(self,target,args):
        self.calls.append((target,*args)); self.events.append(('CALL',target,tuple(args)))
    def string(self,output,x,y,text):
        code = self.get(text)
        for _ in range(64):
            if not code:
                return output
            self.call(self.lookup,(code,))
            index = self.find(code)
            self.call(self.leaf,(output,x&MASK,y&MASK,index))
            output = self.draw(output,x,y,index)
            code = self.get(text+1)
            text += 1; x = (x+8)&MASK
        raise AssertionError('bounded fixture lacks a terminator')


class ChainOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,args,connected,entry=screen.CALLER_ENTRY,phase=0,
            lookup=LOOKUP,leaf=screen.ENTRY):
        super().__init__(words,memory,arguments=args,connected=connected,entry=entry,phase=phase)
        self.lookup,self.leaf = lookup,leaf
    def record_call(self,target):
        assert target in (self.lookup,self.leaf),hex(target)
        args = self.arguments(1 if target == self.lookup else 4)
        self.calls.append((target,*args)); self.events.append(('CALL',target,tuple(args)))


class GameGlyphRectangleMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-glyph-rectangle-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt',
            makefile='conker/Makefile',assembly='conker/asm/6E770.s',
            texture_data='conker/asm/data/2275E0.data.s',
            sdk_gbi='conker/include/2.0L/PR/gbi.h',sdk_mbi='conker/include/2.0L/PR/mbi.h')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            before = (cls.root/screen.SOURCE).read_text()
            assert screen.ORIGINAL in before and screen.CALLER_ORIGINAL in before
            hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'e13af74be9feec1ad02bd96e0cc20855754b7ee6b362a676b704d4888798e563'
        assert cls.baseline['elf'] == '978ccf41d42999cf6a9ceb3b21792ea37451b23e8cd09f9c9cf9bae3acf22118'
        assert cls.baseline['guards'] == '0c28956baf37afeaa5129ad33cb532639375cfbee4fa8a8a6d479d8220adaf52'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>54I',cls.rom,screen.ROM))
        cls.meta,cls.raw = screen.compile_candidate(cls.root,cls.out,'selected')
        cls.caller_meta,cls.caller_raw = screen.compile_candidate(cls.root,cls.out,'caller-after',screen.CALLER_SELECTED,caller=True)
        _,cls.caller_old_raw = screen.compile_candidate(cls.root,cls.out,'caller-before',screen.CALLER_ORIGINAL,caller=True)
        cls.old_source = (cls.out/'before-source').read_text()
        cls.lookup_source = re.search(r's32 func_15041480\(u8 arg0\) \{\n.*?\n\}',cls.old_source,re.S).group(0)
        cls.table = cls.before[elf_slot_offset(cls.before,TABLE,80):][:80]
        cls.asm = (cls.out/'before-assembly').read_text()
        cls.guards = screen.guard_successor((cls.out/'before-guards').read_bytes())
        (cls.out/'guards.csv').write_bytes(cls.guards)
        header = (cls.out/'before-guards').read_bytes().splitlines(keepends=True)[0]
        (cls.out/'leaf-guards.csv').write_bytes(screen.guard_successor(header))
        old_rows = list(csv.DictReader(io.StringIO((cls.out/'before-guards').read_text())))
        caller_rows = [r for r in old_rows if r['filename'] == 'generated_6E770' and r['function'] == screen.CALLER_FUNCTION]
        assert len(caller_rows) == 9
        stream = io.StringIO(newline='')
        csv.DictWriter(stream,fieldnames=list(old_rows[0])).writerows(caller_rows)
        (cls.out/'caller-guards.csv').write_bytes(header+stream.getvalue().encode('ascii'))
        for name,function,obj,guards in (
                ('leaf',screen.FUNCTION,'selected.o','leaf-guards.csv'),
                ('caller',screen.CALLER_FUNCTION,'caller-after.o','caller-guards.csv')):
            body = cls.asm.split('glabel '+function,1)[1].split('endlabel '+function,1)[0]
            slot = cls.out/(name+'-slot.s'); slot.write_text('glabel '+function+body+'endlabel '+function+'\n')
            cls.assemble('original-'+name,cls.asm_function(function,body))
            cls.assemble('fitted-'+name,emit_padded_assembly(cls.out/obj,slot,
                word_patches_path=cls.out/guards,filename='generated_6E770'))
        parts = []
        for function in (screen.CALLER_FUNCTION,'func_15041480',screen.FUNCTION):
            body = cls.asm.split('glabel '+function,1)[1].split('endlabel '+function,1)[0]
            parts.append(cls.asm_function(function,body))
        cls.assemble('original-chain',''.join(parts))
        cls.owners = []
        run = subprocess.run
        def compact(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for stage,source in (('before',cls.old_source),('after',screen.install(cls.old_source))):
            with patch('subprocess.run',side_effect=compact):
                obj,warnings = compile_owner(cls.root,cls.out,source,'owner-'+stage)
            assert not warnings,warnings
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/('owner-'+stage+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=cls.root/'conker',check=True,capture_output=True)
            cls.owners.append(obj)
            cls.assemble('padded-owner-'+stage,emit_padded_assembly(obj,cls.root/'conker/asm/6E770.s',
                word_patches_path=cls.out/('before-guards' if stage == 'before' else 'guards.csv'),filename='generated_6E770'))

    @staticmethod
    def asm_function(function,body):
        return '.text\n.set noat\n.set noreorder\n.globl '+function+'\n.type '+function+',@function\n'+function+':\n'+body+'\n.size '+function+',.-'+function+'\n'

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def link(self,name,entry,function,table=TABLE):
        script = self.out/(name+'-%X-%X.ld'%(entry,table))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        defined = parse_object(self.out/(name+'.o'))[1]
        symbols = dict(D_800848D0=table,D_80084930=table+96,
            func_15041480=LOOKUP,func_15041508=screen.ENTRY)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',function,
            *['--defsym=%s=0x%X'%(key,value) for key,value in symbols.items() if key not in defined],
            '-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
        return sections(elf)['.text'][1]

    def leaf(self,name,entry=screen.ENTRY):
        return list(struct.unpack_from('>54I',self.link(name,entry,screen.FUNCTION)))

    def chain(self,name,base=screen.CALLER_ENTRY,table=TABLE):
        owner = name.startswith('padded-owner')
        entry = base-(screen.CALLER_ENTRY-OWNER) if owner else base
        data = self.link(name,entry,screen.CALLER_FUNCTION,table)
        offset = screen.CALLER_ENTRY-OWNER if owner else 0
        # Internal JAL targets are defined by the object, not fixed rebasing values.
        code = {base+i*4:w for i,w in enumerate(struct.unpack_from('>121I',data,offset))}
        return code

    def compare_leaf(self,x,y,index,output=OUTPUT,phase=0,forms=None,entry=screen.ENTRY):
        memory,_,_ = fixture(output)
        ref = Reference(memory); result = ref.draw(output,x,y,index)
        models = [guest.AttachmentOracle(w,memory,arguments=(output,x,y,index),entry=entry,phase=phase).run()
            for w in forms or self.leaf_forms]
        for m in models:
            self.assertEqual((m.memory,m.events,m.r[2]),(ref.memory,ref.events,result))
            self.assertEqual((m.calls,m.accesses),([],6))
        self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
            (models[-1].memory,models[-1].events,models[-1].r,models[-1].f))
        return models

    @property
    def leaf_forms(self):
        if not hasattr(type(self),'_leaf_forms'):
            type(self)._leaf_forms = (self.retail,self.raw,self.leaf('fitted-leaf'))
        return type(self)._leaf_forms

    def compare_chain(self,memory,output,x,y,text,phase=0,base=screen.CALLER_ENTRY,table=TABLE,codes=None):
        lookup,leaf = base+132,base+268
        ref = Reference(memory,lookup,leaf,table); result = ref.string(output,x,y,text)
        if codes is None:
            codes = (self.chain('original-chain'),self.chain('padded-owner-after'))
        models = [ChainOracle([code[base+i*4] for i in range(33)],memory,(output,x,y,text),
            code,base,phase,lookup,leaf).run() for code in codes]
        for m in models:
            public = {a:v for a,v in m.memory.items() if not STACK-256 <= a < STACK+192}
            expected = {a:v for a,v in ref.memory.items() if not STACK-256 <= a < STACK+192}
            events = [e for e in m.events if e[0] == 'CALL' or not STACK-256 <= e[1] < STACK+192]
            self.assertEqual((public,events,m.calls,m.r[2]),(expected,ref.events,ref.calls,result))
        self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
            (models[-1].memory,models[-1].events,models[-1].r,models[-1].f))
        return models

    def test_01_full_signed_leaf_and_guarded_state(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(54,0,11,0))
        self.assertEqual(self.leaf('original-leaf'),self.retail)
        self.assertEqual(self.leaf_forms[-1],self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[2],{})
        reached,cases = set(),0
        for x,y,index,phase in itertools.product(COORDS,COORDS,GLYPHS,(0,8)):
            models = self.compare_leaf(x,y,index,phase=phase)
            reached.update(models[0].visits); cases += 1
        for output in OUTPUTS:
            self.compare_leaf(-1,1024,-9,output)
        self.assertEqual(reached,set(range(screen.ENTRY,screen.ENTRY+216,4)))
        self.receipt('leaf',cases=cases,extra_buffers=3,reached=54,guards=11,
            unsigned_shift_and_multiply_full_width=True,raw_public_and_guarded_complete_state_exact=True,
            no_frame_reads_calls_or_pool=True)

    def test_02_typed_caller_unchanged_and_actual_lookup_draw_chain(self):
        self.assertEqual(self.caller_raw,self.caller_old_raw)
        self.assertEqual(parse_object(self.out/'caller-after.o'),parse_object(self.out/'caller-before.o'))
        self.assertEqual((self.caller_meta['body_words'],self.caller_meta['frame'],self.caller_meta['differences']),(33,40,9))
        codes = (self.chain('original-chain'),self.chain('padded-owner-after'))
        self.assertEqual(codes[0],codes[1])
        for entry,count,rom in ((screen.CALLER_ENTRY,33,screen.CALLER_ROM),(LOOKUP,34,LOOKUP_ROM)):
            self.assertEqual([codes[0][entry+i*4] for i in range(count)],
                list(struct.unpack_from('>%dI'%count,self.rom,rom)))
        cases = 0
        for byte,phase in itertools.product(range(256),(0,8)):
            memory,out,text = fixture(table=self.table,text=bytes((byte,0)))
            self.compare_chain(memory,out,-1,1024,text,phase,codes=codes); cases += 1
        for text_bytes,x,y,phase in itertools.product((b'\x00',b'aZ?',b'_\xffa_\x00',b'0123456789\x00'),
                (-2147483648,-1,2147483647),(-1,0,1024),(0,8)):
            memory,out,text = fixture(table=self.table,text=text_bytes)
            self.compare_chain(memory,out,x,y,text,phase,codes=codes); cases += 1
        for alias,phase in itertools.product((1,2),(0,8)):
            memory,out,text = fixture(table=self.table,text=b'aZ?\x00',alias=alias)
            self.compare_chain(memory,out,0,0,text,phase,codes=codes); cases += 1
        self.receipt('chain',cases=cases,actual_caller33_lookup34_leaf54=True,
            all_256_first_bytes_empty_missing_duplicate_and_aliases=True,existing_caller_guards9_unchanged=True,
            typed_scalar_coordinate_and_Gfx_returns=True,no_helper_hooks=True)

    def test_03_independent_chain_rebases_and_all_fired_faults(self):
        cases,faults = 0,0
        for base,table in ((0x15207FFC,0x80107FFC),(0x15308004,0x80218004)):
            codes = (self.chain('original-chain',base,table),self.chain('padded-owner-after',base,table))
            self.assertEqual(codes[0],codes[1])
            for phase,x in itertools.product((0,8),(-1,0,1024)):
                memory,out,text = fixture(table=self.table,table_address=table)
                self.compare_chain(memory,out,x,-1,text,phase,base,table,codes); cases += 1
        for index,phase in itertools.product((-9,-8,-1,0,7,8),(0,8)):
            memory,_,_ = fixture()
            full = guest.AttachmentOracle(self.retail,memory,arguments=(OUTPUT,-1,1024,index),entry=screen.ENTRY,phase=phase).run()
            for fault in range(full.accesses):
                models = [guest.AttachmentOracle(w,memory,arguments=(OUTPUT,-1,1024,index),entry=screen.ENTRY,phase=phase)
                    for w in (self.retail,self.leaf_forms[-1])]
                for m in models:
                    m.fault = fault
                    with self.assertRaises(guest.AccessFault): m.run()
                    self.assertEqual(m.accesses,fault)
                self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                    (models[1].memory,models[1].events,models[1].r,models[1].f)); faults += 1
        codes = (self.chain('original-chain'),self.chain('padded-owner-after'))
        for text_bytes,alias in ((b'\x00',0),(b'a\x00',0),(b'\xff\x00',0),(b'aZ?\x00',1),(b'aZ?\x00',2)):
            memory,out,text = fixture(table=self.table,text=text_bytes,alias=alias)
            full = self.compare_chain(memory,out,-1,0,text,codes=codes)[0]
            for fault in range(full.accesses):
                models = [ChainOracle([c[screen.CALLER_ENTRY+i*4] for i in range(33)],memory,(out,-1,0,text),c) for c in codes]
                for m in models:
                    m.fault = fault
                    with self.assertRaises(guest.AccessFault): m.run()
                    self.assertEqual(m.accesses,fault)
                self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                    (models[1].memory,models[1].events,models[1].r,models[1].f)); faults += 1
        self.receipt('rebases-faults',rebase_cases=cases,links=2,actual_three_functions_and_HI_LO_table=True,
            fired_pairs=faults,all_complete_partial_state_exact=True,raw_private_fault_order_not_claimed=True,
            no_portable_C_fault_or_hardware_claim=True)

    @staticmethod
    def negatives():
        return (
            ('mask-remainder',screen.SELECTED.replace('glyph % 8','glyph & 7')),
            ('direct-row-shift',screen.SELECTED.replace('(glyph - (glyph % 8)) / 8','glyph >> 3')),
            ('width',screen.SELECTED.replace('(u32)x + 8','(u32)x + 9')),
            ('height',screen.SELECTED.replace('(u32)y + 12','(u32)y + 11')),
            ('wrong-step',screen.SELECTED.replace('0x400, 0x400','0x200, 0x400')),
            ('wrong-return',screen.SELECTED.replace('return displayList;','return displayList-1;')),
        )

    def test_04_fresh_semantic_guard_and_caller_controls(self):
        for name,body in self.negatives():
            self.assertNotEqual(body,screen.SELECTED)
            _,words = screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            memory,_,_ = fixture()
            ref = Reference(memory); result = ref.draw(OUTPUT,-1,1024,-9)
            model = guest.AttachmentOracle(words,memory,arguments=(OUTPUT,-1,1024,-9),entry=screen.ENTRY).run()
            self.assertNotEqual((model.memory,model.events,model.r[2]),(ref.memory,ref.events,result),name)
        header = (self.out/'before-guards').read_bytes().splitlines(keepends=True)[0]
        stream = io.StringIO(); rows = [list(r) for r in screen.GUARD_ROWS]; rows[0][3]='0x00000000'
        csv.writer(stream).writerows(rows)
        stale = self.out/'stale-guards.csv'; stale.write_bytes(header+stream.getvalue().encode())
        with self.assertRaisesRegex(ValueError,'stale word patch'):
            emit_padded_assembly(self.out/'selected.o',self.out/'leaf-slot.s',
                word_patches_path=stale,filename='generated_6E770')
        partial = self.out/'partial-guards.csv'
        stream = io.StringIO(); csv.writer(stream).writerows(screen.GUARD_ROWS[1:])
        partial.write_bytes(header+stream.getvalue().encode())
        self.assemble('partial-leaf',emit_padded_assembly(self.out/'selected.o',self.out/'leaf-slot.s',
            word_patches_path=partial,filename='generated_6E770'))
        with self.assertRaises(AssertionError):
            self.compare_leaf(1,2,-9,forms=(self.retail,self.leaf('partial-leaf')))
        self.receipt('controls',compiled_semantic=6,stale_guard_and_missing_cycle_guard_effective=True)

    def test_05_complete_owner_neighbors_and_both_actual_padders(self):
        def fingerprint(obj,name):
            text,functions,relocs = parse_object(obj); item=functions[name]
            a,b = item['value'],item['value']+item['size']
            return item['size'],text[a:b],{o-a:r for o,r in relocs.items() if a <= o < b}
        names = set(parse_object(self.owners[0])[1])
        self.assertEqual(names,set(parse_object(self.owners[1])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(self.owners[0],name),fingerprint(self.owners[1],name),name)
        self.assertEqual(normalized_pools(self.owners[0]),normalized_pools(self.owners[1]))
        self.assertEqual(fingerprint(self.owners[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed = []
            for stage,obj in zip(('before','after'),self.owners):
                asm = self.out/(route+'-'+stage+'.s')
                args = [str(obj),str(self.out/'before-layout'),'generated_6E770',str(asm)] if route == 'pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6E770.s'),str(asm),'--filename','generated_6E770']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',
                    str(self.out/('before-guards' if stage == 'before' else 'guards.csv'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            a = parsed[1][1][screen.FUNCTION]['value']; expected=bytearray(parsed[0][0])
            expected[a:a+216] = parsed[1][0][a:a+216]
            self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not a <= o < a+216},
                {o:r for o,r in parsed[1][2].items() if not a <= o < a+216})
            for name in names-{screen.FUNCTION}:
                self.assertEqual(parsed[0][1][name],parsed[1][1][name])
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors=7,typed_caller_raw_bytes_and_relocations_identical=True,
            original_caller_guards_unchanged=True,actual_no_unroll_GLOBAL_ASM_both_padders=True,
            other_extents_relocations_pools_exact=True)

    def native_source(self,leaf=screen.SELECTED,caller=screen.CALLER_SELECTED):
        table = 'static const u8 initialTable[80]={'+','.join(map(str,self.table))+'};\n'
        source = '#include <PR/mbi.h>\n#include <PR/gbi.h>\n'+NATIVE+table+NATIVE_REFERENCE+\
            self.lookup_source+'\n'+leaf+'\n'+caller+'\n'+NATIVE_MAIN
        return subprocess.run(['cc','-m32','-E','-P','-D_LANGUAGE_C','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',
            '-I',str(self.root/'conker/include/2.0L'),'-xc','-'],
            input=source,check=True,capture_output=True,text=True).stdout

    def test_06_actual_SDK_native32_leaf_and_typed_chain(self):
        source = self.native_source()
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],source,profile),(0,''))
        for name,body in self.negatives():
            code,detail = self.run_native('native-negative-'+name,self.native_source(leaf=body))
            self.assertEqual(code,1,name); self.assertEqual(len(detail),3,name)
        for name,caller in (('caller-stride',screen.CALLER_SELECTED.replace('xCursor += 8','xCursor += 4')),
                ('caller-return',screen.CALLER_SELECTED.replace('return result;','return displayList;')),
                ('caller-unsigned-char',screen.CALLER_SELECTED.replace('func_15041480(*commands)','func_15041480(0)'))):
            code,detail = self.run_native('native-negative-'+name,self.native_source(caller=caller))
            self.assertEqual(code,1,name); self.assertEqual(len(detail),3,name)
        self.receipt('native',profiles=['O2','O0'],leaf_cases_per_profile=1408,
            chain_cases_per_profile=1024,actual_full_SDK_lookup_and_typed_caller_source=True,
            all_input_output_table_canaries_and_aliases=True,pointer_bytes4_Gfx_bytes8=True,
            effective_leaf_controls6_caller_controls3=True,no_64bit_host_hardware_claim=True)

    def test_07_literal_source_whole_ELF_guard_prefix_and_ten_inputs(self):
        current = (self.root/screen.SOURCE).read_text(); changed = current != self.old_source
        self.assertEqual(current,screen.install(self.old_source) if changed else self.old_source)
        actual=(self.root/self.paths['elf']).read_bytes(); expected=bytearray(self.before)
        start=elf_slot_offset(self.before,screen.ENTRY,216)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],28)
        if changed:
            struct.pack_into('>54I',expected,start,*self.retail); struct.pack_into('>I',expected,extent,216)
        self.assertEqual(actual,bytes(expected))
        for name,path in self.paths.items():
            old=(self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(),self.baseline[name])
            if name not in ('source','elf'):
                self.assertEqual((self.root/path).read_bytes(),self.guards if changed and name == 'guards' else old,name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=changed,ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+216],actual[start:start+216])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            old_guard_prefix_plus11_rows_only=True,ten_other_inputs_exact=True,
            literal_no_projection_or_metadata_exception=True,protected_data=data)

    def test_08_effective_frozen_baseline_and_integrity_controls(self):
        for source in (screen.install(self.old_source),self.old_source+'\n'+screen.ORIGINAL,
                self.old_source.replace(screen.PROTOTYPE,''),self.old_source.replace(screen.CALLER_ORIGINAL,'')):
            with self.assertRaises(AssertionError): screen.install(source)
        with self.assertRaises(AssertionError): screen.guard_successor(self.guards)
        rt,rb=Path.read_text,Path.read_bytes
        source=self.root/screen.SOURCE; current=source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:current+'\n' if p == source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_guard_prefix_and_ten_inputs()
        elf=self.root/self.paths['elf']; actual=elf.read_bytes()
        start=elf_slot_offset(actual,screen.ENTRY,216); extent=installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,start+216,extent+3):
            wrong=bytearray(actual); wrong[offset]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_guard_prefix_and_ten_inputs()
        guard=self.root/self.paths['guards']; wrong=bytearray(guard.read_bytes()); wrong[0]^=1
        with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p == guard else rb(p)):
            with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_guard_prefix_and_ten_inputs()
        self.receipt('integrity-controls',source1_ELF3_guard1_stale_source4_duplicate_guard1=True,all_effective=True)


NATIVE = r'''
static u8 D_800848D0[2048] __attribute__((aligned(8))),wantedTable[2048];
static u8 text[256],wantedText[256];static Gfx output[200],wantedOutput[200];
static int report(u32 a,u32 b,u32 c){u32 data[3]={a,b,c};int r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
static s32 q8(s32 v){return v/8;}
static void draw_ref(Gfx *p,s32 x,s32 y,s32 glyph){
    s32 q=q8(glyph),rem=glyph-q*8;u32 xx=(u32)x,yy=(u32)y;
    p[0].words.w0=0xE4000000u|((((xx+8)*4)&4095)<<12)|(((yy+12)*4)&4095);
    p[0].words.w1=((xx*4)&4095)<<12|((yy*4)&4095);
    p[1].words.w0=0xE1000000u;p[1].words.w1=((u32)rem*256&65535)<<16|((u32)q*384&65535);
    p[2].words.w0=0xF1000000u;p[2].words.w1=0x04000400u;
}
'''
NATIVE_REFERENCE = r'''
static void reset(u32 pattern,u32 byte){
    for(u32 i=0;i<2048;i++)D_800848D0[i]=wantedTable[i]=(u8)(i*17+53+pattern*19);
    for(u32 i=0;i<80;i++)D_800848D0[i]=wantedTable[i]=initialTable[i];
    for(u32 i=0;i<sizeof(output);i++)((u8 *)output)[i]=((u8 *)wantedOutput)[i]=(u8)(i*13+71+pattern*23);
    for(u32 i=0;i<256;i++)text[i]=wantedText[i]=0;
    text[0]=wantedText[0]=(u8)byte;text[1]=wantedText[1]='_';text[2]=wantedText[2]=255;text[3]=wantedText[3]='a';
}
static Gfx *string_ref(Gfx *p,s32 x,s32 y,u8 *s){
    u32 xx=(u32)x,n=0;while(*s){s32 i=0;
        while(i<80&&wantedTable[i]!=*s)i++;
        draw_ref(p,(s32)xx,y,i);p+=3;s++;xx+=8;
        if(++n>=64)__builtin_trap();
    }return p;
}
static int compare_all(u32 caseNumber){
    for(u32 i=0;i<sizeof(output);i++)if(((u8 *)output)[i]!=((u8 *)wantedOutput)[i])return report(caseNumber,1,i);
    for(u32 i=0;i<2048;i++)if(D_800848D0[i]!=wantedTable[i])return report(caseNumber,2,i);
    for(u32 i=0;i<256;i++)if(text[i]!=wantedText[i])return report(caseNumber,3,i);
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void){
    static const s32 coords[8]={(-2147483647-1),-1025,-1,0,1,1023,1024,2147483647};
    static const s32 glyphs[22]={(-2147483647-1),-2147483647,-129,-80,-17,-16,-9,-8,-7,-1,0,1,7,8,9,63,64,79,80,255,2147483646,2147483647};
    u32 cases=0;
    if(sizeof(void *)!=4||sizeof(Gfx)!=8||sizeof(s32)!=4||sizeof(u32)!=4)return 2;
    for(u32 a=0;a<8;a++)for(u32 b=0;b<8;b++)for(u32 g=0;g<22;g++,cases++){
        reset(g,0);draw_ref(wantedOutput+1,coords[a],coords[b],glyphs[g]);
        Gfx *r=func_15041508(output+1,coords[a],coords[b],glyphs[g]);
        if(r!=output+4)return report(cases,0,0);
        int error=compare_all(cases);if(error)return error;
    }
    if(cases!=1408)return 3;
    u32 chainCases=0;
    for(u32 byte=0;byte<256;byte++)for(u32 a=0;a<4;a++,chainCases++){
        reset(a,byte);s32 x=coords[a==3?7:a];Gfx *start=output+1,*want=wantedOutput+1;
        u8 *s=text,*ws=wantedText;
        if(a==1){start=(Gfx *)D_800848D0;want=(Gfx *)wantedTable;}
        if(a==2){s=(u8 *)(output+1);ws=(u8 *)(wantedOutput+1);
            for(u32 i=0;i<256;i++){s[i]=ws[i]=0;}
            s[0]=ws[0]=(u8)byte;}
        Gfx *wr=string_ref(want,x,0,ws),*r=func_150413FC(start,x,0,s);
        if((u32)r-(u32)start!=(u32)wr-(u32)want)return report(chainCases,0,1);
        int error=compare_all(chainCases);if(error)return error;
    }
    return chainCases==1024?0:4;
}
void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
