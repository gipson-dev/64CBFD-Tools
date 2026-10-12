"""Complete matrix wrapper, O32 homes and original zero-tail preservation."""
import hashlib
import itertools
import json
import re
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_matrix_forward_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_record_state_dispatch_match as state
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits, floating, signed

STACK, INPUT, OUTPUT, OTHER = guest.STACK, 0x50000, 0x60000, 0x70000
COPY, CONVERT, FORWARD = (screen.SYMBOLS[n] for n in ('memcpy', 'guMtxL2F', 'func_1503E5F8'))
SELECTOR = screen.SYMBOLS['D_800C3E90']
PROJECTION = (12, 13, 14, 0, 1, 2, 4, 5, 6)


def converted(words):
    result = []
    for i in range(8):
        first = (words[i] & 0xFFFF0000) | ((words[i+8] >> 16) & 65535)
        second = ((words[i] << 16) & 0xFFFF0000) | (words[i+8] & 65535)
        result.extend(bits(floating(bits(float(signed(v))))/65536.0) for v in (first, second))
    return result


def matrix_words(pattern, fixed):
    if fixed:
        values = [(0x10000 if i in (0, 5, 10, 15) else 0) if pattern == 0 else
            (0x80000000, 0x7FFFFFFF, 0xFFFF8000, 0x18000, 0, 0xFFFF0000, 0x8001, 0x12345678)[(i+pattern) % 8]
            for i in range(16)]
        return [((values[i*2] & 0xFFFF0000) | ((values[i*2+1] >> 16) & 65535)) for i in range(8)]+[
            (((values[i*2] << 16) & 0xFFFF0000) | (values[i*2+1] & 65535)) for i in range(8)]
    if pattern == 7:
        return [0x7FC01234, 0x7F800000, 0xFF800000, 0x80000000]*4
    return [bits(float(i-pattern*3)/4.0) for i in range(16)]


def fixture(flag=1, pattern=1, alias=0, phase=0, input_address=INPUT, symbols=screen.SYMBOLS):
    memory = {STACK+i:0xA5 for i in range(-0x800, 0x240)}
    for base in (input_address-16, OUTPUT-16, OTHER-16):
        memory.update({base+i:(i*17+53)&255 for i in range(128)})
    put(memory, symbols['D_800C3E90'], flag, 1)
    for i, value in enumerate(matrix_words(pattern, flag != 0)):
        put(memory, input_address+i*4, value)
    outputs = tuple(OUTPUT+i*4 if alias == 0 else OUTPUT+(i % 3)*4 if alias == 1 else OUTPUT for i in range(9))
    return memory, (input_address, *outputs)


def public(memory, phase=0):
    return {a:v for a,v in memory.items() if not STACK-0x800 <= a < STACK+phase}


class Reference:
    def __init__(self, memory, args, phase=0, symbols=screen.SYMBOLS, actions=()):
        self.memory, self.args, self.home = memory.copy(), args, STACK+phase
        self.symbols, self.actions, self.calls, self.payloads = symbols, actions, [], []
    def run(self):
        for i, value in enumerate(self.args):
            put(self.memory, self.home+i*4, value)
        private = self.home-0x40
        flag = read(self.memory, self.symbols['D_800C3E90'], 1)
        source = self.args[0]
        target = self.symbols['guMtxL2F'] if flag else self.symbols['memcpy']
        self.calls.append((target, private, source, *(() if flag else (64,))))
        for a,v,n in self.actions:
            put(self.memory, a, v, n)
        words = [read(self.memory, source+i*4) for i in range(16)]
        if flag:
            words = converted(words)
        for i,v in enumerate(words):
            put(self.memory, private+i*4, v)
        outputs = tuple(read(self.memory, self.home+i*4) for i in range(1, 10))
        self.calls.append((self.symbols['func_1503E5F8'], private, *outputs))
        self.payloads.append(words)
        for pointer, index in zip(outputs, PROJECTION):
            put(self.memory, pointer, words[index])
        return self


class ForwardOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, args, phase=0, symbols=screen.SYMBOLS,
            start=screen.ENTRY, actions=(), connected=None):
        super().__init__(words, memory, phase=phase, entry=start, arguments=args, connected=connected)
        self.symbols, self.actions, self.payloads = symbols, actions, []
    def record_call(self, target):
        s = self.symbols
        assert target in (s['memcpy'], s['guMtxL2F'], s['func_1503E5F8']), hex(target)
        args = self.arguments(10 if target == s['func_1503E5F8'] else 3 if target == s['memcpy'] else 2)
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        if target != s['func_1503E5F8']:
            for a,v,n in self.actions:
                self.put(a,v,n)
    def hook(self, target):
        s = self.symbols
        if target == s['func_1503E5F8']:
            args = self.arguments(10)
            words = [self.get(args[0]+i*4, 4) for i in range(16)]
            self.payloads.append(words)
            for pointer, index in zip(args[1:], PROJECTION):
                self.put(pointer, words[index], 4)
        else:
            args = self.arguments(3 if target == s['memcpy'] else 2)
            words = [self.get(args[1]+i*4, 4) for i in range(16)]
            if target == s['guMtxL2F']:
                words = converted(words)
            else:
                assert args[2] == 64, args
            for i,value in enumerate(words):
                self.put(args[0]+i*4, value, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]


class GameMatrixForwardMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-matrix-forward-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt', makefile='conker/Makefile',
            sdk='conker/src/libultra/gu/mtxutil2.c')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == 'aa141c65ad29d29a1ff7d7b52e96d8115df088fa27b52244e610d1bfb34d69f8'
        assert cls.baseline['elf'] == '407aad745988d43056465c75d3cf2ac866787e70ab431e8d316d82fdc2a5f1cc'
        assert cls.baseline['guards'] == '92f39fbf0bf509614ecff961e3a654e01d30c98666c3c65f224884f57102206e'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.slot = list(struct.unpack_from('>43I', cls.rom, screen.ROM)); cls.retail = cls.slot[:40]
        assert cls.slot[40:] == [0,0,0]
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        body = (cls.root/'conker/asm/6B320.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', slot, filename='generated_6B320'))
        cls.connected = {}
        for entry,rom,count in ((COPY,0x22EC0,11),(CONVERT,0x21D368,46)):
            words = list(struct.unpack_from('>%dI'%count,cls.before,elf_slot_offset(cls.before,entry,count*4)))
            assert words == list(struct.unpack_from('>%dI'%count,cls.rom,rom))
            cls.connected.update({entry+i*4:w for i,w in enumerate(words)})

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def link(self,name,start=screen.ENTRY,symbols=screen.SYMBOLS):
        script = self.out/('link-'+name+'.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>40I',sections(elf)['.text'][1]))

    @property
    def padded(self):
        if not hasattr(type(self),'_padded'):
            type(self)._padded = self.link('padded')
        return type(self)._padded

    def compare(self,memory,args,phase=0,actions=(),actual=True,
            symbols=screen.SYMBOLS,start=screen.ENTRY,forms=None):
        expected = Reference(memory,args,phase,symbols,actions).run()
        models = [ForwardOracle(words,memory,args,phase,symbols,start,actions,self.connected if actual else None).run()
            for words in forms or (self.retail,self.raw,self.padded)]
        for model in models:
            self.assertEqual((public(model.memory,phase),model.calls,model.payloads),
                (public(expected.memory,phase),expected.calls,expected.payloads))
        for model in models[1:]:
            self.assertEqual((model.memory,model.events,model.r,model.f,model.lo),
                (models[0].memory,models[0].events,models[0].r,models[0].f,models[0].lo))
        return models

    def test_01_all40_direct_three_original_tail_words(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(40,112,0,0))
        self.assertEqual(self.raw,self.retail); self.assertEqual(self.padded,self.retail)
        self.assertEqual(self.link('original'),self.retail)
        self.assertEqual(parse_object(self.out/'selected.o')[1][screen.FUNCTION]['size'],160)
        for profile in ('compact','o1g3','o1'):
            meta,words = screen.compile_candidate(self.root,self.out,profile,profile=profile)
            if profile == 'compact': self.assertEqual(words,self.retail)
            else: self.assertEqual((meta['body_words'],meta['differences']),((40,9) if profile == 'o1g3' else (39,38)))
        self.receipt('shape',body_words=40,slot_words=43,original_zero_tail_words=3,frame=112,direct=True,guards=0,pools=0)

    def test_02_all_selector_bytes_patterns_aliases_and_actual_sdk(self):
        cases,reached = 0,set()
        for flag,phase in itertools.product(range(256),(0,8)):
            memory,args = fixture(flag,phase=phase)
            models = self.compare(memory,args,phase)
            reached.update(models[0].visits); cases += 1
        for flag,pattern,alias,phase in itertools.product((0,1,2,127,128,255),range(8),range(3),(0,8)):
            memory,args = fixture(flag,pattern,alias,phase)
            self.compare(memory,args,phase); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY,screen.ENTRY+160,4))),40)
        self.assertEqual(len(reached & set(range(CONVERT,CONVERT+184,4))),45)
        self.assertEqual(len(reached & set(range(COPY,COPY+44,4))),11)
        self.receipt('matrix',cases=cases,all256_unsigned_selector_bytes=True,
            active_words_reached=40,actual_conversion_words_reached=45,actual_copy_words_reached=11,
            projection_forward_leaf_bounded_not_decomposition_or_FCSR_proof=True)

    def test_03_effective_home_mutations_live_inputs_and_partial_storage(self):
        cases = 0
        for flag,phase in itertools.product((0,1),(0,8)):
            memory,args = fixture(flag,phase=phase); home = STACK+phase
            base = self.compare(memory,args,phase)[0]
            choices = [((home+i*4,OTHER+i*4,4),) for i in range(1,10)]
            choices += [((home,OTHER,4),),((SELECTOR,1-flag,1),),((INPUT,0x80010002,4),)]
            for actions in choices:
                models = self.compare(memory,args,phase,actions=actions)
                if actions[0][0] not in (home,SELECTOR):
                    self.assertTrue((public(models[0].memory,phase),models[0].calls,models[0].payloads) !=
                        (public(base.memory,phase),base.calls,base.payloads))
                else:
                    self.assertEqual(models[0].calls,base.calls)
                cases += 1
        for phase in (0,8):
            memory,args = fixture(0,phase=phase,input_address=INPUT+1)
            self.compare(memory,args,phase); cases += 1
        for flag in (0,1):
            memory,args = fixture(flag); del memory[INPUT+63]
            for words in (self.retail,self.raw,self.padded):
                with self.assertRaises(AssertionError):
                    ForwardOracle(words,memory,args,connected=self.connected).run()
        self.receipt('lifetimes',cases=cases,nine_late_pointer_homes_live=True,
            source_pointer_cached_before_first_call=True,selector_not_retested=True,
            actual_unaligned_byte_copy_guest_only=True,missing_required_source_byte_rejected=True,
            no_portable_private_home_alias_claim=True)

    def test_04_rebases_and_all_fired_fault_prefixes(self):
        cases,faults = 0,0
        for j,start in enumerate((0x15207FFC,0x15308004)):
            symbols = {name:(0x15140000+i*0x100+j*0x10000 if name != 'D_800C3E90' else
                (0x80107FFC if j == 0 else 0x80218004)) for i,name in enumerate(screen.SYMBOLS)}
            forms = tuple(self.link(n,start,symbols) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for flag,alias,phase in itertools.product((0,1,255),range(3),(0,8)):
                memory,args = fixture(flag,alias=alias,phase=phase,symbols=symbols)
                self.compare(memory,args,phase,actual=False,symbols=symbols,start=start,forms=forms); cases += 1
        for flag,actual in itertools.product((0,1),(False,True)):
            memory,args = fixture(flag); code = self.connected if actual else None
            full = ForwardOracle(self.retail,memory,args,connected=code).run()
            for fault in range(full.accesses):
                models = [ForwardOracle(w,memory,args,connected=code) for w in (self.retail,self.raw,self.padded)]
                for m in models:
                    m.fault = fault
                    with self.assertRaises(guest.AccessFault): m.run()
                    self.assertEqual(m.accesses,fault)
                for m in models[1:]:
                    self.assertEqual((m.memory,m.events,m.r,m.f),(models[0].memory,models[0].events,models[0].r,models[0].f))
                faults += 1
        self.receipt('rebases-faults',links=2,symbols=4,cases=cases,fired_fault_triplets=faults,
            actual_sdk_and_bounded_projection_accesses=True,no_portable_C_fault_hardware_FCSR_claim=True)

    def test_05_effective_compiled_semantic_controls(self):
        controls = (
            ('gate',screen.SELECTED.replace(' != 0',' == 0')),
            ('one-only',screen.SELECTED.replace(' != 0',' == 1')),
            ('short-copy',screen.SELECTED.replace('sizeof(matrix)','60')),
            ('swap',screen.SELECTED.replace('matrix, x, y, z','matrix, y, x, z')),
            ('last-pointer',screen.SELECTED.replace('sx, sy, sz);','sx, sy, sy);')),
            ('original-input',screen.SELECTED.replace('func_1503E5F8(matrix,','func_1503E5F8((f32 (*)[4])input,')),
        )
        for name,body in controls:
            self.assertNotEqual(body,screen.SELECTED)
            _,words = screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            detected = False
            for flag in (0,2):
                memory,args = fixture(flag)
                model = ForwardOracle(words,memory,args,connected=self.connected).run()
                expected = Reference(memory,args).run()
                if (public(model.memory),model.calls,model.payloads) != (public(expected.memory),expected.calls,expected.payloads):
                    detected = True
            self.assertTrue(detected,name)
        self.receipt('controls',semantic=6,all_effective=True)

    def test_06_complete_owner_and_both_padders(self):
        before = (self.out/'before-source').read_text(); objects = []
        for stage,source in (('before',before),('after',screen.install(before))):
            obj,warnings = compile_owner(self.root,self.out,source,'owner-'+stage)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/('owner-'+stage+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            self.assertEqual(warnings,[]); objects.append(obj)
        def fingerprint(obj,name):
            text,functions,relocs = parse_object(obj); item = functions[name]; a,b = item['value'],item['value']+item['size']
            return item['size'],text[a:b],{o-a:r for o,r in relocs.items() if a <= o < b}
        names = set(parse_object(objects[0])[1]); self.assertEqual(names,set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(objects[0],name),fingerprint(objects[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(fingerprint(objects[1],screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed = []
            for stage,obj in zip(('before','after'),objects):
                asm = self.out/(route+'-'+stage+'.s')
                args = [str(obj),str(self.out/'before-layout'),'generated_6B320',str(asm)] if route == 'pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6B320.s'),str(asm),'--filename','generated_6B320']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+172] = parsed[1][0][start:start+172]
            self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual(parsed[1][0][start:start+160],fingerprint(self.out/'selected.o',screen.FUNCTION)[1])
            self.assertEqual({o-start:r for o,r in parsed[1][2].items() if start <= o < start+160},
                fingerprint(self.out/'selected.o',screen.FUNCTION)[2])
            self.assertEqual(struct.unpack_from('>3I',parsed[1][0],start+160),(0,0,0))
            self.assertEqual(parsed[1][1][screen.FUNCTION]['size'],160)
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start <= o < start+172},
                {o:r for o,r in parsed[1][2].items() if not start <= o < start+172})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt('owner',neighbors=len(names)-1,pools_exact=True,both_production_padders=True,
            GLOBAL_ASM_processed=True,target_size160_slot172_tail_exact=True)

    def test_07_literal_source_whole_ELF_and_eight_inputs(self):
        source = (self.out/'before-source').read_text(); now = (self.root/screen.SOURCE).read_text(); changed = now != source
        self.assertEqual(now,screen.install(source) if changed else source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before,screen.ENTRY,172)
        extent = installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if changed:
            struct.pack_into('>43I',expected,start,*self.slot); struct.pack_into('>I',expected,extent,160)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            old = (self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(),self.baseline[name])
            if name not in ('source','elf'): self.assertEqual((self.root/path).read_bytes(),old,name)
        data = audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=changed,changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            target_bytes=sum(a!=b for a,b in zip(self.before[start:start+172],actual[start:start+172])),
            extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            ELF_sha256=hashlib.sha256(actual).hexdigest(),eight_inputs_exact=True,
            literal_no_projection_or_metadata_exception=True,protected_data=data)

    def test_08_effective_stale_and_literal_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for source in (screen.install(before),before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(source)
        rt,rb = Path.read_text,Path.read_bytes
        source = self.root/screen.SOURCE; actual = source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:actual+'\n' if p == source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_and_eight_inputs()
        elf = self.root/self.paths['elf']; actual = elf.read_bytes()
        start = elf_slot_offset(actual,screen.ENTRY,172); extent = installed.symbol_size_offset(actual,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,start+160,start+172,extent+3):
            wrong = bytearray(actual); wrong[offset] ^= 1
            with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_and_eight_inputs()
        guards = self.root/self.paths['guards']; wrong = bytearray(guards.read_bytes()); wrong[0] ^= 1
        with patch.object(Path,'read_bytes',lambda p:bytes(wrong) if p == guards else rb(p)):
            with self.assertRaises(AssertionError): self.test_07_literal_source_whole_ELF_and_eight_inputs()
        self.receipt('integrity-controls',stale=2,source=1,ELF=4,guards=1,all_effective=True,original_tail_corruption_detected=True)

    def test_09_original_caller152_with_actual_sdk_and_effective_control(self):
        entry = 0x151D4408
        caller = list(struct.unpack_from('>152I',self.before,elf_slot_offset(self.before,entry,608)))
        self.assertEqual(caller,list(struct.unpack_from('>152I',self.rom,0x2018B8)))
        parent = self
        class CallerOracle(ForwardOracle):
            def record_call(model,target):
                if target == screen.ENTRY:
                    args = model.arguments(10)
                    home = STACK+model.phase-0xD0
                    parent.assertEqual(args,(INPUT,home+0x44,home+0x48,home+0x4C,
                        home+0x64,home+0x68,home+0x6C,home+0x38,home+0x3C,home+0x40))
                    model.calls.append((target,*args)); model.events.append(('CALL',target,args))
                elif target in (0x150ADA68,0x150ADA20,0x15132A4C):
                    args = model.arguments(6) if target == 0x15132A4C else ()
                    model.calls.append((target,*args)); model.events.append(('CALL',target,args))
                    if target == 0x15132A4C:
                        parent.assertEqual(args[1:4],(3,255,0))
                        model.packets.append((args,[read(model.memory,args[0]+i*4) for i in range(30)]))
                else:
                    super().record_call(target)
            def hook(model,target):
                if target in (0x150ADA68,0x150ADA20,0x15132A4C):
                    for reg in (1,2,3,*range(4,16),24,25):
                        model.r[reg] = 0xA5000000+reg
                    model.f[:20] = [0xA5000000+i for i in range(20)]
                    model.f[0] = bits(0.25); model.r[2] = 5
                else:
                    super().hook(target)
        def execute(words,flag,pattern,phase):
            memory,_ = fixture(flag,pattern,phase=phase)
            for base in (0x74000,0x75000,0x76000):
                memory.update({base+i:0xA5 for i in range(128)})
            for base in (0x74000,0x75000):
                for i in range(3):
                    put(memory,base+i*4,bits(float(i+1)))
            for a in range(0x800AB1D4,0x800AB1FC,4):
                value = struct.unpack_from('>I',parent.before,elf_slot_offset(parent.before,a,4))[0]
                put(memory,a,value)
            put(memory,0x76000+0x3B,37,1)
            code = dict(parent.connected)
            code.update({screen.ENTRY+i*4:w for i,w in enumerate(words)})
            args = (0x74000,0x75000,INPUT,0x76000,bits(4.0),0x12345678,0x9ABCDEF0)
            model = CallerOracle(caller,memory,args,phase,start=entry,connected=code)
            model.phase = phase; model.packets = []
            model.run()
            parent.assertEqual(len(model.packets),1)
            parent.assertEqual(model.packets[0][0][4:],(0x78,0x9ABCDEF0))
            return model
        cases,reached = 0,set()
        for flag,pattern,phase in itertools.product((0,1,255),(0,1,2),(0,8)):
            models = [execute(w,flag,pattern,phase) for w in (self.retail,self.raw,self.padded)]
            for model in models[1:]:
                self.assertEqual((model.memory,model.events,model.r,model.f,model.packets),
                    (models[0].memory,models[0].events,models[0].r,models[0].f,models[0].packets))
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(entry,entry+608,4))),152)
        wrong = screen.SELECTED.replace('matrix, x, y, z, rx, ry, rz','matrix, x, y, z, ry, rx, rz')
        _,words = screen.compile_candidate(self.root,self.out,'negative-caller-rotation-order',wrong)
        self.assertNotEqual(execute(words,1,1,0).packets,execute(self.retail,1,1,0).packets)
        self.receipt('original-caller',cases=cases,caller_words_reached=152,wrapper40_and_sdk_conversion45_copy11_actual=True,
            complete_ten_argument_call_and_export_packet_checked=True,effective_packet_rotation_control=True,
            decomposer_random_and_export_leaves_bounded_not_gameplay_FCSR_acceptance=True)

    def test_10_native32_actual_conversion_and_all_ten_pointer_arguments(self):
        sdk = (self.out/'before-sdk').read_text().split('void guMtxL2F',1)[1]
        prefix = NATIVE+'void actual_conversion'+sdk+NATIVE_HELPERS
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],prefix+screen.SELECTED+NATIVE_MAIN,profile),(0,''))
        for name,body in (
                ('gate',screen.SELECTED.replace(' != 0',' == 0')),
                ('one-only',screen.SELECTED.replace(' != 0',' == 1')),
                ('copy',screen.SELECTED.replace('sizeof(matrix)','60')),
                ('pointer',screen.SELECTED.replace('matrix, x, y, z','matrix, y, x, z')),
                ('input',screen.SELECTED.replace('func_1503E5F8(matrix,','func_1503E5F8((f32 (*)[4])input,'))):
            result,detail = self.run_native('native-negative-'+name,prefix+body+NATIVE_MAIN)
            self.assertEqual(result,1); self.assertEqual(len(detail),3)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=12288,
            actual_recovered_sdk_conversion_C=True,all256_bytes_eight_patterns_three_output_aliases_two_modes=True,
            full_source_and_output_canaries_protocol_and_payloads=True,effective_controls=5,
            no_private_home_alias_hardware_FCSR_or_decomposer_acceptance_claim=True)


NATIVE = r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
typedef union {s32 m[4][4];double align;u32 words[16];} Mtx;
static Mtx source,initial;static u32 out[12],want[12],expectedMatrix[16];static f32 *pointers[9];
static u8 D_800C3E90;static int originalFlag,mode,prepared,forwarded,error;
static u32 floatword(f32 v){union{f32 f;u32 u;}x;x.f=v;return x.u;}
static void prepare(int kind){if(prepared++ || kind!=(originalFlag!=0))error=1;
    if(mode)D_800C3E90=(u8)(originalFlag?0:255);}
static int report(u32 a,u32 b,u32 c){u32 data[3]={a,b,c};s32 r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
'''

NATIVE_HELPERS = r'''
void guMtxL2F(f32 matrix[4][4],Mtx *input){
    if(input!=&source)error=2;
    actual_conversion(matrix,input);prepare(1);}
void *memcpy(void *destination,const void *input,unsigned int size){
    if(input!=&source || size!=64)error=3;
    for(u32 i=0;i<size;i++)((u8 *)destination)[i]=((const u8 *)input)[i];
    prepare(0);return destination;
}
void func_1503E5F8(f32 matrix[4][4],f32 *x,f32 *y,f32 *z,f32 *rx,f32 *ry,f32 *rz,f32 *sx,f32 *sy,f32 *sz){
    static int indices[9]={12,13,14,0,1,2,4,5,6};f32 *actual[9]={x,y,z,rx,ry,rz,sx,sy,sz};
    if(prepared!=1 || forwarded++ || (void *)matrix==(void *)&source)error=4;
    for(int i=0;i<9;i++)if(actual[i]!=pointers[i])error=5;
    for(int i=0;i<16;i++)if(floatword(((f32 *)matrix)[i])!=expectedMatrix[i])error=6;
    for(int i=0;i<9;i++)*(u32 *)actual[i]=floatword(((f32 *)matrix)[indices[i]]);
}
static void initialize(int flag,int pattern,int alias,int mutation){
    static u32 integers[8]={0x80000000U,0x7FFFFFFFU,0xFFFF8000U,0x18000U,0,0xFFFF0000U,0x8001U,0x12345678U};
    u32 values[16];
    originalFlag=flag;D_800C3E90=(u8)flag;mode=mutation;prepared=forwarded=error=0;
    for(int i=0;i<12;i++)out[i]=want[i]=0xA5A5A5A5U;
    for(int i=0;i<9;i++)pointers[i]=(f32 *)(out+1+(alias==0?i:alias==1?i%3:0));
    for(int i=0;i<16;i++){
        if(flag)values[i]=pattern==0?(i==0||i==5||i==10||i==15?0x10000U:0):integers[(i+pattern)%8];
        else values[i]=floatword((f32)(i-pattern*3)/4.0f);
    }
    if(!flag && pattern==7){for(int i=0;i<16;i++)values[i]=(u32[]){0x7FC01234U,0x7F800000U,0xFF800000U,0x80000000U}[i%4];}
    for(int i=0;i<16;i++)source.words[i]=values[i];
    if(flag)for(int i=0;i<8;i++){
        source.words[i]=(values[i*2]&0xFFFF0000U)|(values[i*2+1]>>16);
        source.words[i+8]=(values[i*2]<<16)|(values[i*2+1]&65535U);
    }
    initial=source;
    for(int i=0;i<16;i++)expectedMatrix[i]=flag?floatword((f32)(s32)values[i]/65536.0f):values[i];
    for(int i=0;i<9;i++)want[1+(alias==0?i:alias==1?i%3:0)]=expectedMatrix[(int[]){12,13,14,0,1,2,4,5,6}[i]];
}
'''

NATIVE_MAIN = r'''
static int run(void){u32 c=0;
    if(sizeof(void *)!=4 || sizeof(Mtx)!=64)return 2;
    for(int flag=0;flag<256;flag++)for(int pattern=0;pattern<8;pattern++)for(int alias=0;alias<3;alias++)for(int m=0;m<2;m++,c++){
        initialize(flag,pattern,alias,m);
        func_1503F404(&source,pointers[0],pointers[1],pointers[2],pointers[3],pointers[4],pointers[5],pointers[6],pointers[7],pointers[8]);
        if(error || prepared!=1 || forwarded!=1)return report(c,0,error);
        if(D_800C3E90!=(u8)(m?(flag?0:255):flag))return report(c,1,D_800C3E90);
        for(int i=0;i<12;i++)if(out[i]!=want[i])return report(c,2,i);
        for(int i=0;i<16;i++)if(source.words[i]!=initial.words[i])return report(c,3,i);
    }
    return c==12288?0:3;}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
