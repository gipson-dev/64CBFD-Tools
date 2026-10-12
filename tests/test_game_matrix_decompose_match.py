"""Full decomposer semantics with actual vector helpers and guarded layout."""
import hashlib
import csv
import io
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_matrix_decompose_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_matrix_forward_match as forward
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits, floating

STACK, INPUT, OUTPUT, OTHER = guest.STACK, 0x50000, 0x60000, 0x70000
SYMBOLS = screen.SYMBOLS
NAMES = dict(bcopy='copy',func_150AD930='length',func_15049148='scale',
    func_150AD8B0='cross',func_150AD900='dot',func_150487E0='asin',
    func_150AD780='cos',func_150484A0='atan')
COUNTS = dict(copy=3,length=1,scale=3,cross=3,dot=2)
f32 = lambda x: floating(bits(x))


def fdiv(a,b):
    return f32(a/b) if b else f32(math.nan if not a else math.copysign(math.inf,a*math.copysign(1.0,b)))


def public(memory,phase=0):
    return {a:v for a,v in memory.items() if not STACK-0x800 <= a < STACK+phase}


def fixture(pattern=0,alias=0,phase=0,symbols=SYMBOLS):
    memory = {STACK+i:0xA5 for i in range(-0x800,0x240)}
    for base in (INPUT-16,OUTPUT-16,OTHER-16):
        memory.update({base+i:(i*17+53)&255 for i in range(128)})
    patterns = (
        (1,0,0,0, 0,1,0,0, 0,0,1,0, 11,22,33,1),
        (-2,0,0,9, 0,3,0,8, 0,0,4,7, -11,22,-33,1),
        (0,0,0,0, 0,0,0,0, 0,0,0,0, 1,2,3,1),
        (1,2,3,4, 3,2,1,4, -2,4,1,4, 5,6,7,1),
        (0,1,0,0, 0,0,1,0, 1,0,0,0, 10,20,30,1),
        (1e-8,0,0,0, 0,-1e-8,0,0, 0,0,1e-8,0, 0,-0.0,0,1),
    )
    for i,v in enumerate(patterns[pattern]): put(memory,INPUT+i*4,bits(v))
    put(memory,symbols['D_80098918'],0x38D1B717)
    put(memory,symbols['D_8009891C'],0x42652EE0)
    outputs = [OUTPUT+i*4 for i in range(9)]
    if alias == 1: outputs = [OUTPUT+(i%3)*4 for i in range(9)]
    if alias == 2: outputs = [OUTPUT]*9
    if alias == 3: outputs = [INPUT+i*4 for i in range(9)]
    if alias == 4: outputs[0] = symbols['D_80098918']
    if alias == 5: outputs[3] = symbols['D_8009891C']
    return memory,(INPUT,*outputs)


class Reference:
    def __init__(self,memory,args,phase=0,symbols=SYMBOLS,actions=None,cosine=0.5,pitch=0.25,home=None):
        self.memory,self.args,self.home = memory.copy(),args,STACK+phase if home is None else home
        self.symbols,self.actions,self.cosine,self.pitch = symbols,actions or {},cosine,pitch
        self.calls,self.events,self.occurrences = [],[],{}
        for i,v in enumerate(args[4:],4): put(self.memory,self.home+i*4,v)
    def getf(self,a):
        return floating(read(self.memory,a))
    def putf(self,a,v):
        put(self.memory,a,bits(v)); self.events.append(('W',a,4,bits(v)))
    def mutate(self,label):
        n = self.occurrences.get(label,0); self.occurrences[label] = n+1
        for a,v,size in self.actions.get((label,n),()): put(self.memory,a,v,size)
    def call(self,label,args=()):
        target = self.symbols[next(n for n,v in NAMES.items() if v == label)]
        self.calls.append((target,*args)); self.mutate(label)
        if label == 'copy':
            source,dest,size = args
            data = [read(self.memory,source+i,1) for i in range(size)]
            for i,v in enumerate(data): put(self.memory,dest+i,v,1)
        elif label == 'length':
            x,y,z = [self.getf(args[0]+i*4) for i in range(3)]
            total = f32(f32(f32(x*x)+f32(y*y))+f32(z*z))
            return f32(math.sqrt(total)) if total >= 0 else math.nan
        elif label == 'scale':
            source,scalar,dest = args; scalar = floating(scalar)
            for i in range(3): self.putf(dest+i*4,f32(self.getf(source+i*4)*scalar))
        elif label == 'cross':
            a,b,dest = args
            left,right = [[self.getf(base+i*4) for i in range(3)] for base in (a,b)]
            values = [f32(f32(left[1]*right[2])-f32(left[2]*right[1])),
                f32(f32(left[2]*right[0])-f32(left[0]*right[2])),
                f32(f32(left[0]*right[1])-f32(left[1]*right[0]))]
            for i in (2,0,1): self.putf(dest+i*4,values[i])
        elif label == 'dot':
            a,b = args
            products = [f32(self.getf(a+i*4)*self.getf(b+i*4)) for i in range(3)]
            return f32(f32(products[0]+products[1])+products[2])
        elif label == 'asin': return self.pitch
        elif label == 'cos': return self.cosine
        elif label == 'atan':
            return f32(f32(floating(args[0])*0.25)+f32(floating(args[1])*0.125))
    def run(self):
        home,s = self.home,self.symbols
        matrix,cross = home-0x40,home-0x50
        self.call('copy',(self.args[0],matrix,64))
        for ptr,i in zip(self.args[1:4],(12,13,14)): self.putf(ptr,self.getf(matrix+i*4))
        fallback = self.getf(s['D_80098918'])
        scales = [read(self.memory,home+i*4) for i in (7,8,9)]
        for i in range(3):
            row = matrix+i*16; length = self.call('length',(row,))
            if length == 0: length = fallback
            self.putf(scales[i],length)
            self.call('scale',(row,bits(fdiv(1.0,length)),row))
        self.call('cross',(matrix+16,matrix+32,cross))
        if self.call('dot',(matrix,cross)) < 0:
            for ptr in scales: self.putf(ptr,-self.getf(ptr))
            for i in range(3):
                values = [self.getf(matrix+i*16+j*4) for j in range(3)]
                for j,v in enumerate(values): self.putf(matrix+i*16+j*4,-v)
        angleY = self.call('asin',(bits(-self.getf(matrix+8)),))
        cosine = self.call('cos',(bits(angleY),))
        if cosine != 0:
            angleX = self.call('atan',(bits(self.getf(matrix+24)),bits(self.getf(matrix+40))))
            angleZ = self.call('atan',(bits(self.getf(matrix+4)),bits(self.getf(matrix))))
        else:
            angleX = self.call('atan',(bits(self.getf(matrix+16)),bits(self.getf(matrix+20))))
            angleZ = 0.0
        factor = self.getf(s['D_8009891C'])
        for i,v in zip((4,5,6),(angleX,angleY,angleZ)):
            self.putf(read(self.memory,home+i*4),f32(v*factor))
        return self


class DecomposeOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,args,phase=0,symbols=SYMBOLS,actions=None,cosine=0.5,pitch=0.25,
            connected=None,start=screen.ENTRY):
        super().__init__(words,memory,phase=phase,entry=start,arguments=args,connected=connected)
        self.symbols,self.actions,self.cosine,self.pitch = symbols,actions or {},cosine,pitch
        self.occurrences = {}
    def execute(self,word):
        op,rs,rt,rd,fd,fn = word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op == 17 and rs == 16 and fn == 4:
            value = floating(self.f[rd]); self.f[fd] = bits(math.sqrt(value) if value >= 0 else math.nan)
        elif op == 17 and rs == 16 and fn == 7:
            self.f[fd] = self.f[rd]^0x80000000
        else: super().execute(word)
    def label(self,target):
        return next(label for name,label in NAMES.items() if self.symbols[name] == target)
    def record_call(self,target):
        label = self.label(target)
        args = (self.f[12],self.f[14]) if label == 'atan' else (self.f[12],) if label in ('asin','cos') else self.arguments(COUNTS[label])
        self.calls.append((target,*args)); self.events.append(('CALL',target,args))
        n = self.occurrences.get(label,0); self.occurrences[label] = n+1
        for a,v,size in self.actions.get((label,n),()): self.put(a,v,size)
    def hook(self,target):
        label = self.label(target)
        if label == 'copy':
            source,dest,size = self.arguments(3)
            assert size == 64
            data = [self.get(source+i,1) for i in range(size)]
            for i,v in enumerate(data): self.put(dest+i,v,1)
            result = 0.0
        else:
            assert label in ('asin','cos','atan'),label
            result = self.pitch if label == 'asin' else self.cosine if label == 'cos' else f32(
                f32(floating(self.f[12])*0.25)+f32(floating(self.f[14])*0.125))
        for reg in (1,2,3,*range(4,16),24,25): self.r[reg] = 0xA5000000+reg
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.f[0] = bits(result)


class GameMatrixDecomposeMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-matrix-decompose-match-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s',symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt',layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            assembly='conker/asm/nonmatchings/generated_6B320/func_1503E5F8.s')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == '48adc4b96517a4d4efe101817e092d6b343dbfa5aa462d2d639ddd85c17960c5'
        assert cls.baseline['elf'] == '4b4bece866646b9f453b958c1dccdd2f37e31f65dc2abaaa810b71f72a5d4071'
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes(); cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>141I',cls.rom,screen.ROM))
        cls.meta,cls.raw = screen.compile_candidate(cls.root,cls.out,'selected')
        cls.guards = screen.guard_successor((cls.out/'before-guards').read_bytes())
        (cls.out/'guards.csv').write_bytes(cls.guards)
        (cls.out/'isolated-guards.csv').write_bytes(screen.guard_successor((cls.out/'before-guards').read_bytes().splitlines(keepends=True)[0]))
        body = (cls.out/'before-assembly').read_text()
        slot = cls.out/'slot.s'; slot.write_text(body)
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+
            ',@function\n'+screen.FUNCTION+':\n'+body.split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('guarded',emit_padded_assembly(cls.out/'selected.o',slot,word_patches_path=cls.out/'isolated-guards.csv',filename='generated_6B320'))
        cls.connected = {}
        for entry,count in ((SYMBOLS['func_150AD8B0'],19),(SYMBOLS['func_150AD900'],12),(SYMBOLS['func_150AD930'],11),(SYMBOLS['func_15049148'],13)):
            words = list(struct.unpack_from('>%dI'%count,cls.before,elf_slot_offset(cls.before,entry,count*4)))
            assert words == list(struct.unpack_from('>%dI'%count,cls.rom,entry-0x15000000+0x2D4B0))
            cls.connected.update({entry+i*4:w for i,w in enumerate(words)})
    def link(self,name,start=screen.ENTRY,symbols=SYMBOLS):
        script = self.out/(name+'.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%start)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
        return list(struct.unpack_from('>141I',sections(elf)['.text'][1]))
    @property
    def guarded(self):
        if not hasattr(type(self),'_guarded'): type(self)._guarded = self.link('guarded')
        return type(self)._guarded
    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,args,phase=0,actions=None,cosine=0.5,pitch=0.25,
            forms=None,symbols=SYMBOLS,start=screen.ENTRY,connected=None):
        expected = Reference(memory,args,phase,symbols,actions,cosine,pitch).run()
        models = [DecomposeOracle(w,memory,args,phase,symbols,actions,cosine,pitch,
            self.connected if connected is None else connected,start).run()
            for w in forms or (self.retail,self.raw,self.guarded)]
        for m in models:
            self.assertEqual((public(m.memory,phase),m.calls),(public(expected.memory,phase),expected.calls))
        self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
            (models[-1].memory,models[-1].events,models[-1].r,models[-1].f))
        return models
    def test_01_shape_guarded_and_full_semantic_matrix(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(141,192,63,0))
        self.assertEqual(self.link('guarded'),self.retail)
        self.assertEqual(self.link('original'),self.retail)
        reached,cases = set(),0
        for pattern,alias,phase,cosine,pitch in itertools.product(range(6),range(6),(0,8),(0.0,0.5),(0.25,-0.25)):
            memory,args = fixture(pattern,alias,phase)
            models = self.compare(memory,args,phase,cosine=cosine,pitch=pitch)
            reached.update(models[0].visits); cases += 1
        self.assertEqual(len(reached & set(range(screen.ENTRY,screen.ENTRY+564,4))),140)
        self.assertNotIn(screen.ENTRY+0xCC,reached)
        (self.out/'semantic.json').write_text(json.dumps(dict(cases=cases,reached=140,guards=63,
            raw_public_semantics_and_guarded_complete_state=True,actual_four_vector_helpers=True,bcopy_trig_bounded=True),indent=2)+'\n')

    def test_02_effective_global_pointer_and_alias_lifetimes(self):
        cases = 0
        for phase in (0,8):
            home = STACK+phase; matrix = home-64
            choices = [
                {('copy',0):((home+4,OTHER,4),)},
                *({('copy',0):((home+i*4,OTHER,4),)} for i in (7,8,9)),
                {('length',0):((SYMBOLS['D_80098918'],bits(1.0),4),)},
                {('length',0):((home+28,OTHER,4),)},
                {('length',0):((matrix,bits(4.0),4),)},
                {('scale',0):((matrix+16,bits(-2.0),4),)},
                {('dot',0):((OUTPUT+24,bits(7.0),4),)},
                *({('cos',0):((home+i*4,OTHER,4),)} for i in (4,5,6)),
                {('atan',1):((SYMBOLS['D_8009891C'],bits(90.0),4),)},
            ]
            for i,actions in enumerate(choices):
                pattern = 2 if i == 4 else 1
                memory,args = fixture(pattern,phase=phase)
                models = self.compare(memory,args,phase,actions)
                base = self.compare(memory,args,phase)
                if i not in (0,5):
                    self.assertTrue(public(models[0].memory,phase) != public(base[0].memory,phase))
                cases += 1
        self.receipt('lifetimes',cases=cases,initial_positions_cached_before_copy=True,
            scale_pointers_loaded_after_copy_then_cached=True,angle_pointers_loaded_after_trig=True,
            fallback_once_and_coefficient_once=True,actual_vector_call_mutations=True,private_home_aliases_guest_only=True)

    def test_03_rebases_fired_faults_and_expected_word_controls(self):
        cases,faults = 0,0
        for j,start in enumerate((0x15207FFC,0x15308004)):
            symbols = {name:((0x80107FFC if i%2 == j else 0x80218004)+i*0x10000
                if name.startswith('D_') else 0x15400000+j*0x10000+i*0x1000)
                for i,name in enumerate(SYMBOLS)}
            forms = tuple(self.link(n,start,symbols) for n in ('original','selected','guarded'))
            self.assertEqual(forms[0],forms[2])
            code = {symbols[name]+i*4:self.connected[SYMBOLS[name]+i*4]
                for name,count in (('func_150AD8B0',19),('func_150AD900',12),('func_150AD930',11),('func_15049148',13))
                for i in range(count)}
            for pattern,alias,phase,cosine in itertools.product((0,1,2),(0,2,5),(0,8),(0.0,0.5)):
                memory,args = fixture(pattern,alias,phase,symbols)
                self.compare(memory,args,phase,cosine=cosine,forms=forms,symbols=symbols,start=start,connected=code); cases += 1
        for pattern,cosine in itertools.product((0,1,2),(0.0,0.5)):
            memory,args = fixture(pattern)
            full = DecomposeOracle(self.retail,memory,args,cosine=cosine,connected=self.connected).run()
            for fault in range(full.accesses):
                models = [DecomposeOracle(w,memory,args,cosine=cosine,connected=self.connected)
                    for w in (self.retail,self.guarded)]
                for m in models:
                    m.fault = fault
                    with self.assertRaises(guest.AccessFault): m.run()
                    self.assertEqual(m.accesses,fault)
                self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                    (models[1].memory,models[1].events,models[1].r,models[1].f)); faults += 1
        rows = screen.GUARD_ROWS
        stale = self.out/'stale.csv'; changed = [list(r) for r in rows]; changed[0][3] = '0x00000000'
        import csv,io
        text = io.StringIO(); csv.writer(text).writerows(changed)
        stale.write_bytes((self.out/'before-guards').read_bytes().splitlines(keepends=True)[0]+text.getvalue().encode())
        with self.assertRaisesRegex(ValueError,'stale word patch'):
            emit_padded_assembly(self.out/'selected.o',self.out/'slot.s',word_patches_path=stale,filename='generated_6B320')
        self.receipt('rebases-faults',cases=cases,symbols=10,links=2,fired_fault_pairs=faults,
            guarded_all_state_exact=True,raw_private_fault_order_not_claimed=True,stale_guard_effective=True,
            no_portable_C_fault_hardware_FCSR_claim=True)

    def test_04_effective_compiled_semantic_controls(self):
        controls = (
            ('fallback',screen.SELECTED.replace('length = fallback','length = 1.0f'),2,0,0.5),
            ('handedness',screen.SELECTED.replace(' < 0.0f',' > 0.0f'),1,0,0.5),
            ('pitch-sign',screen.SELECTED.replace('(-matrix[0][2])','(matrix[0][2])'),3,0,0.5),
            ('gimbal',screen.SELECTED.replace(' != 0.0f',' == 0.0f'),3,0,0.0),
            ('live-factor',screen.SELECTED.replace('angleY * factor','angleY * D_8009891C'),1,5,0.5),
            ('first-position',screen.SELECTED.replace('*x = matrix[3][0]','*x = matrix[0][0]'),0,0,0.5),
        )
        for name,source,pattern,alias,cosine in controls:
            _,words = screen.compile_candidate(self.root,self.out,'negative-'+name,source)
            memory,args = fixture(pattern,alias)
            model = DecomposeOracle(words,memory,args,cosine=cosine,connected=self.connected).run()
            expected = Reference(memory,args,cosine=cosine).run()
            if name == 'pitch-sign': self.assertNotEqual(model.calls,expected.calls)
            else: self.assertTrue(public(model.memory) != public(expected.memory),name)
        self.receipt('controls',semantic=6,all_effective=True,full_source_compiled_no_guard_reuse_for_negatives=True)

    def test_05_complete_owner_and_both_actual_padders(self):
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
        results = []
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed = []
            for stage,obj in zip(('before','after'),objects):
                asm = self.out/(route+'-'+stage+'.s')
                args = [str(obj),str(self.out/'before-layout'),'generated_6B320',str(asm)] if route == 'pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6B320.s'),str(asm),'--filename','generated_6B320']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',
                    str(self.out/('before-guards' if stage == 'before' else 'guards.csv'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
            self.assertEqual(parsed[0],parsed[1]); results.append(parsed[1])
        self.assertEqual(results[0],results[1])
        self.receipt('owner',neighbors=len(names)-1,pools_and_other_relocations_exact=True,
            both_production_padders_entire_objects_exact=True,target_extent564_unchanged=True)

    def test_06_native32_complete_c_body_and_effective_controls(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],NATIVE+screen.SELECTED+NATIVE_MAIN,profile),(0,''))
        for name,source in (
                ('fallback',screen.SELECTED.replace('length = fallback','length = 1.0f').replace(
                    'fallback = D_80098918;','fallback = D_80098918; (void)fallback;')),
                ('handedness',screen.SELECTED.replace(' < 0.0f',' > 0.0f')),
                ('gimbal',screen.SELECTED.replace(' != 0.0f',' == 0.0f')),
                ('coefficient',screen.SELECTED.replace('angleY * factor','angleY * D_8009891C')),
                ('translation',screen.SELECTED.replace('*x = matrix[3][0]','*x = matrix[0][0]'))):
            result,detail = self.run_native('native-negative-'+name,NATIVE+source+NATIVE_MAIN)
            self.assertEqual(result,1); self.assertEqual(len(detail),3)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=432,
            all_matrix_rows_input_output_aliases_fallback_factor_mutations=True,source_semantics_not_guard_projection=True,
            actual_C_vector_math_and_SSE_sqrt=True,trig_controlled_not_retail_trig_or_hardware_FCSR=True,effective_controls=5)

    def test_07_actual_wrapper_sdk_decomposer_vector_chain(self):
        wrapper_entry = forward.screen.ENTRY
        wrapper = list(struct.unpack_from('>40I',self.before,elf_slot_offset(self.before,wrapper_entry,160)))
        self.assertEqual(wrapper,list(struct.unpack_from('>40I',self.rom,forward.screen.ROM)))
        helpers = dict(self.connected)
        for entry,count in ((forward.COPY,11),(forward.CONVERT,46)):
            words = list(struct.unpack_from('>%dI'%count,self.before,elf_slot_offset(self.before,entry,count*4)))
            helpers.update({entry+i*4:w for i,w in enumerate(words)})
        class Pipeline(DecomposeOracle):
            def record_call(model,target):
                if target in (screen.ENTRY,forward.COPY,forward.CONVERT):
                    n = 10 if target == screen.ENTRY else 3 if target == forward.COPY else 2
                    args = model.arguments(n); model.calls.append((target,*args)); model.events.append(('CALL',target,args))
                else: super().record_call(target)
        cases = 0
        for flag,pattern,alias,phase,cosine in itertools.product((0,1,255),(0,1,2),(0,2),(0,8),(0.0,0.5)):
            memory,args = forward.fixture(flag,pattern,alias,phase)
            put(memory,SYMBOLS['D_80098918'],0x38D1B717); put(memory,SYMBOLS['D_8009891C'],0x42652EE0)
            want = memory.copy(); home = STACK+phase; private = home-64
            for i,v in enumerate(args): put(want,home+i*4,v)
            words = [read(want,args[0]+i*4) for i in range(16)]
            if flag: words = forward.converted(words)
            for i,v in enumerate(words): put(want,private+i*4,v)
            subargs = (private,*args[1:])
            expected = Reference(want,subargs,phase,cosine=cosine,home=home-0x70).run(); models = []
            for code in (self.retail,self.raw,self.guarded):
                connected = dict(helpers)
                connected.update({screen.ENTRY+i*4:w for i,w in enumerate(code)})
                model = Pipeline(wrapper,memory,args,phase,cosine=cosine,connected=connected,start=wrapper_entry).run()
                self.assertEqual(public(model.memory,phase),public(expected.memory,phase))
                self.assertEqual(model.calls[1],(screen.ENTRY,*subargs))
                self.assertEqual(model.calls[2:],expected.calls); models.append(model)
            self.assertEqual((models[0].memory,models[0].events,models[0].r,models[0].f),
                (models[2].memory,models[2].events,models[2].r,models[2].f)); cases += 1
        self.receipt('wrapper-chain',cases=cases,actual_wrapper40_sdk45_copy11_decomposer141_four_vector_helpers=True,
            no_projection_decomposer_hook=True,bcopy_trig_bounded_not_full_gameplay_FCSR=True)

    def expected_progress(self):
        data = (self.out/'before-progress').read_bytes()
        rows = list(csv.reader(io.StringIO(data.decode('ascii'))))
        matching = [r for r in rows if r[3] == screen.FUNCTION]
        self.assertEqual(len(matching),1); self.assertEqual(matching[0][6],'asm')
        matching[0][6] = 'c'
        stream = io.StringIO(newline='')
        csv.writer(stream,lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(rows)
        return stream.getvalue().encode('ascii')

    def test_08_literal_source_entire_elf_guard_append_and_inputs(self):
        before = (self.out/'before-source').read_text(); current = (self.root/screen.SOURCE).read_text()
        changed = current != before
        self.assertEqual(current,screen.install(before) if changed else before)
        self.assertEqual((self.root/'conker/build/conker.us.elf').read_bytes(),self.before)
        for name,path in self.paths.items():
            old = (self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(old).hexdigest(),self.baseline[name])
            if name not in ('source','elf'):
                expected = self.guards if changed and name == 'guards' else self.expected_progress() if changed and name == 'progress' else old
                self.assertEqual((self.root/path).read_bytes(),expected,name)
        data = audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertTrue(data['exact'],data)
        self.receipt('linked',installed=changed,literal_elf_identical=True,metadata_and_extent564_identical=True,
            guard_prefix_exact63_rows_only=True,progress_only_one_asm_to_c_cell=True,protected_data=data)

    def test_09_effective_frozen_baseline_and_integrity_controls(self):
        before = (self.out/'before-source').read_text()
        for source in (screen.install(before),before+'\n'+screen.ORIGINAL):
            with self.assertRaises(AssertionError): screen.install(source)
        with self.assertRaises(AssertionError): screen.guard_successor(self.guards)
        rt,rb = Path.read_text,Path.read_bytes
        source = self.root/screen.SOURCE; current = source.read_text()
        with patch.object(Path,'read_text',lambda p,*a,**k:current+'\n' if p == source else rt(p,*a,**k)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_entire_elf_guard_append_and_inputs()
        elf = self.root/'conker/build/conker.us.elf'; data = elf.read_bytes()
        start = elf_slot_offset(data,screen.ENTRY,564)
        extent = installed.symbol_size_offset(data,screen.FUNCTION,screen.ENTRY)
        for offset in (start+4,start+564,extent+3):
            bad = bytearray(data); bad[offset] ^= 1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p == elf else rb(p)):
                with self.assertRaises(AssertionError): self.test_08_literal_source_entire_elf_guard_append_and_inputs()
        guard = self.root/'conker/retail_word_patches.us.csv'; bad = bytearray(guard.read_bytes()); bad[0] ^= 1
        with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p == guard else rb(p)):
            with self.assertRaises(AssertionError): self.test_08_literal_source_entire_elf_guard_append_and_inputs()
        self.receipt('integrity-controls',source=1,elf=3,guard_prefix=1,stale_source=2,duplicate_guard=1,all_effective=True)


NATIVE = r'''
typedef unsigned int u32;typedef int s32;typedef float f32;typedef unsigned char u8;
typedef struct {f32 unk0,unk4,unk8;} struct17;
static f32 D_80098918,D_8009891C,cosine,pitch;
static f32 input[4][4],initial[4][4],output[12],wantInput[4][4],wantOutput[12],wantFallback,wantFactor;
static f32 *pointers[9];static int mode,lengthCalls,atanCalls,copied,scaled,crossed,dotted,error;
static int trace[16],wantTrace[16],count,wantCount;static u32 params[16][3],wantParams[16][3];
static u32 word(f32 v){union{f32 f;u32 u;}x;x.f=v;return x.u;}
static void record(int label,u32 a,u32 b,u32 c){if(count>=16){error=1;return;}trace[count]=label;
    params[count][0]=a;params[count][1]=b;params[count++][2]=c;}
void bcopy(const void *a,void *b,unsigned int n){copied++;record(1,n,0,0);
    for(u32 i=0;i<n;i++)((u8 *)b)[i]=((const u8 *)a)[i];}
f32 func_150AD930(f32 *v){f32 sum=(v[0]*v[0]+v[1]*v[1])+v[2]*v[2],result;
    record(2,word(v[0]),word(v[1]),word(v[2]));
    if(lengthCalls++==0 && mode==1)D_80098918=1.0f;
    __asm__ volatile("sqrtss %1,%0":"=x"(result):"x"(sum));return result;}
void func_15049148(struct17 *v,f32 k,struct17 *out){scaled++;record(3,word(k),0,0);
    out->unk0=v->unk0*k;out->unk4=v->unk4*k;out->unk8=v->unk8*k;}
void func_150AD8B0(f32 *a,f32 *b,f32 *v){f32 x=a[1]*b[2]-a[2]*b[1],y=a[2]*b[0]-a[0]*b[2],z=a[0]*b[1]-a[1]*b[0];
    crossed++;record(4,word(x),word(y),word(z));v[2]=z;v[0]=x;v[1]=y;}
f32 func_150AD900(f32 *a,f32 *b){f32 v=(a[0]*b[0]+a[1]*b[1])+a[2]*b[2];
    dotted++;record(5,word(v),0,0);return v;}
f32 func_150487E0(f32 v){record(6,word(v),0,0);return pitch;}
f32 func_150AD780(f32 v){record(7,word(v),0,0);return cosine;}
f32 func_150484A0(f32 x,f32 y){record(8,word(x),word(y),0);
    if(atanCalls++==0 && mode==2)D_8009891C=90.0f;
    return x*0.25f+y*0.125f;}
static void reference(void){f32 m[4][4],v[3],fallback,len,x,y,z,factor;
    bcopy(input,m,64);*pointers[0]=m[3][0];*pointers[1]=m[3][1];*pointers[2]=m[3][2];fallback=D_80098918;
    for(int i=0;i<3;i++){len=func_150AD930(m[i]);if(len==0.0f)len=fallback;
        *pointers[i+6]=len;func_15049148((struct17 *)m[i],1.0f/len,(struct17 *)m[i]);}
    func_150AD8B0(m[1],m[2],v);
    if(func_150AD900(m[0],v)<0.0f){for(int i=6;i<9;i++)*pointers[i]=-*pointers[i];
        for(int i=0;i<3;i++)for(int j=0;j<3;j++)m[i][j]=-m[i][j];}
    y=func_150487E0(-m[0][2]);
    if(func_150AD780(y)==0.0f){x=func_150484A0(m[1][0],m[1][1]);z=0.0f;}
    else {x=func_150484A0(m[1][2],m[2][2]);z=func_150484A0(m[0][1],m[0][0]);}
    factor=D_8009891C;*pointers[3]=x*factor;*pointers[4]=y*factor;*pointers[5]=z*factor;}
static void reset(int pattern,int alias,int c,int p,int mutation){
    static const f32 rows[6][16]={
        {1,0,0,0,0,1,0,0,0,0,1,0,11,22,33,1},
        {-2,0,0,9,0,3,0,8,0,0,4,7,-11,22,-33,1},
        {0,0,0,0,0,0,0,0,0,0,0,0,1,2,3,1},
        {1,2,3,4,3,2,1,4,-2,4,1,4,5,6,7,1},
        {0,1,0,0,0,0,1,0,1,0,0,0,10,20,30,1},
        {0.00000001f,0,0,0,0,-0.00000001f,0,0,0,0,0.00000001f,0,0,-0.0f,0,1}};
    for(int i=0;i<16;i++)((f32 *)input)[i]=rows[pattern][i];
    for(int i=0;i<12;i++)output[i]=1234.5f;
    for(int i=0;i<9;i++)pointers[i]=output+1+(alias==1?i%3:alias==2?0:i);
    if(alias==3)for(int i=0;i<9;i++)pointers[i]=(f32 *)input+i;
    D_80098918=0.0001f;D_8009891C=57.2957763671875f;
    if(alias==4)pointers[0]=&D_80098918;
    if(alias==5)pointers[3]=&D_8009891C;
    cosine=c?0.5f:0.0f;pitch=p?0.25f:-0.25f;mode=mutation;
    copied=scaled=crossed=dotted=lengthCalls=atanCalls=error=count=0;}
static int report(u32 a,u32 b,u32 c){u32 data[3]={a,b,c};s32 r;
    __asm__ volatile("int $0x80":"=a"(r):"a"(4),"b"(2),"c"(data),"d"(12):"memory");return 1;}
'''

NATIVE_MAIN = r'''
static int run(void){u32 cases=0;
    if(sizeof(void *)!=4 || sizeof(struct17)!=12)return 2;
    for(int pat=0;pat<6;pat++)for(int a=0;a<6;a++)for(int c=0;c<2;c++)for(int p=0;p<2;p++)for(int m=0;m<3;m++,cases++){
        reset(pat,a,c,p,m);reference();wantCount=count;wantFallback=D_80098918;wantFactor=D_8009891C;
        for(int i=0;i<16;i++)((f32 *)wantInput)[i]=((f32 *)input)[i];
        for(int i=0;i<12;i++)wantOutput[i]=output[i];
        for(int i=0;i<count;i++){wantTrace[i]=trace[i];for(int j=0;j<3;j++)wantParams[i][j]=params[i][j];}
        reset(pat,a,c,p,m);
        func_1503E5F8(input,pointers[0],pointers[1],pointers[2],pointers[3],pointers[4],pointers[5],pointers[6],pointers[7],pointers[8]);
        if(error || count!=wantCount || copied!=1 || scaled!=3 || crossed!=1 || dotted!=1)return report(cases,0,count);
        for(int i=0;i<16;i++)if(word(((f32 *)input)[i])!=word(((f32 *)wantInput)[i]))return report(cases,1,i);
        for(int i=0;i<12;i++)if(word(output[i])!=word(wantOutput[i]))return report(cases,2,i);
        if(word(D_80098918)!=word(wantFallback)||word(D_8009891C)!=word(wantFactor))return report(cases,3,0);
        for(int i=0;i<count;i++){if(trace[i]!=wantTrace[i])return report(cases,4,i);
            for(int j=0;j<3;j++)if(params[i][j]!=wantParams[i][j])return report(cases,5,i*3+j);}
    }
    return cases==432?0:3;}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
