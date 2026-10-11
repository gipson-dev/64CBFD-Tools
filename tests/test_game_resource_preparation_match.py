"""Complete resource preparation, live extras callbacks and direct linked audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_resource_preparation_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_resource_buffers as buffers
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools

S, STACK = screen.SYMBOLS, guest.STACK
ACTOR, CONFIG, DESCRIPTOR, LIST, OTHER_LIST = 0x20000, 0x22000, 0x26000, 0x27000, 0x28000
ROLES = dict(load='func_1503CF20', auxiliary='func_150028BC',
    extras='func_1503DC3C', entry='func_1510CE60', buffers='func_15084044')
ARITIES = dict(load=5, auxiliary=1, extras=1, entry=5, buffers=2)


def address(symbols, table, identity, stride=4):
    return (symbols[table] + identity * stride) & 0xFFFFFFFF


def fixture(identity=7, present=True, config=True, flags=0, actor_flags=0,
        cached=False, descriptor=0, extra_count=1, count=2, symbols=S):
    memory = {STACK+i:0xA5 for i in range(-0x600, 0xC0)}
    for base, length in ((ACTOR, 0x340), (CONFIG, 0x40), (DESCRIPTOR, 0x20),
            (LIST, 0x40), (OTHER_LIST, 0x40)):
        memory.update({base+i:(i*19+0x35)&255 for i in range(length)})
    put(memory, ACTOR+0x144, CONFIG if config else 0)
    put(memory, ACTOR+0xAC, actor_flags, 1)
    put(memory, CONFIG+0x18, flags)
    for table, value, stride in (('D_800D19A0', buffers.SOURCE if present else 0, 4),
            ('D_800C5C08', 0x29000 if cached else 0, 4),
            ('D_800C5628', extra_count, 2), ('D_800C5338', DESCRIPTOR, 4),
            ('D_800C4778', count, 2), ('D_800C4488', LIST, 4)):
        base = address(symbols, table, identity, stride)
        memory.update({base+i:0xA5 for i in range(stride)})
        put(memory, base, value, stride)
    put(memory, DESCRIPTOR, descriptor)
    for i in range(16):
        put(memory, LIST+i*4, 0x11000000+i)
        put(memory, OTHER_LIST+i*4, 0x91000000+i)
    return memory


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x600 <= a < STACK+0xC0}


def events(values):
    return [v for v in values if v[0]=='CALL' or not STACK-0x600 <= v[1] < STACK+0xC0]


def helper(model, role):
    number = model.numbers.get(role, 0)
    model.numbers[role] = number + 1
    for location, value, size in model.actions.get((role, number), ()):
        model.put(location, value, size)
    result = model.results.get(role, 0)
    return (result[min(number, len(result)-1)] if isinstance(result, tuple) else result) & 0xFFFFFFFF


class PreparationOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, identity=7, channel=0, extras=1, phase=0,
            symbols=S, entry=screen.ENTRY, actions=None, results=None, connected=None):
        super().__init__(words, memory, arguments=(ACTOR, identity & 0xFFFFFFFF,
            channel & 0xFFFFFFFF, extras & 0xFFFFFFFF), phase=phase, entry=entry, connected=connected)
        self.symbols, self.actions, self.results = symbols, actions or {}, results or {}
        self.numbers = {}
        self.allocations = self.copies = self.frees = 0
        self.buffer_results = (buffers.PRIVATE,buffers.ALTERNATE)
        self.record_only = False
    def execute(self, word):
        if word >> 26==32:
            buffers.CopyOracle.execute(self,word)
        else:
            super().execute(word)
    def record_call(self, target):
        role = next((r for r,n in ROLES.items() if self.symbols[n]==target), None)
        if role is None:
            return buffers.BufferOracle.record_call(self, target)
        count = ARITIES[role]
        args = tuple(self.r[4:4+min(count,4)])
        if count==5:
            args += (read(self.memory, self.r[29]+16, 4),)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))
    def hook(self, target):
        role = next((r for r,n in ROLES.items() if self.symbols[n]==target), None)
        if role is None:
            saved = self.results
            try:
                self.results = self.buffer_results
                return buffers.BufferOracle.hook(self, target)
            finally:
                self.results = saved
        result = helper(self, role)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = result


class Reference:
    def __init__(self, memory, symbols=S, actions=None, results=None):
        self.memory, self.symbols = memory.copy(), symbols
        self.events, self.calls, self.numbers = [], [], {}
        self.actions, self.results = actions or {}, results or {}
    def get(self, location, size=4):
        assert all(location+i in self.memory for i in range(size))
        value = read(self.memory, location, size)
        self.events.append(('R', location, size, value))
        return value
    def put(self, location, value, size=4):
        assert all(location+i in self.memory for i in range(size))
        put(self.memory, location, value, size)
        self.events.append(('W', location, size, value & ((1 << (size*8))-1)))
    def call(self, role, *args):
        target = self.symbols[ROLES[role]]
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
        return helper(self, role)
    def run(self, identity=7, channel=0, extras=1):
        present = self.get(address(self.symbols, 'D_800D19A0', identity))
        config = self.get(ACTOR+0x144)
        if not present:
            result = self.call('load', identity & 0xFFFFFFFF, 0, config,
                extras & 0xFFFFFFFF, self.get(ACTOR+0xAC, 1))
        else:
            result = 0
            auxiliary = bool(config and self.get(config+0x18) & 0x4000)
            if not auxiliary:
                auxiliary = bool(self.get(ACTOR+0xAC, 1) & 1)
            if auxiliary and not self.get(address(self.symbols, 'D_800C5C08', identity)):
                self.call('auxiliary', identity & 0xFFFFFFFF)
            if extras and self.get(address(self.symbols, 'D_800C5628', identity, 2), 2):
                pointer = self.get(address(self.symbols, 'D_800C5338', identity))
                if self.get(pointer) < 0x10000000:
                    result = self.call('extras', identity & 0xFFFFFFFF)
                    count = address(self.symbols, 'D_800C4778', identity, 2)
                    index = 0
                    while index < self.get(count, 2):
                        base = self.get(address(self.symbols, 'D_800C4488', identity))
                        self.call('entry', self.get(base+index*4), 0, 0, 0x3E, 0)
                        index += 1
                        assert index <= 16, 'unbounded reference fixture'
        if result==0:
            result = self.call('buffers', ACTOR, channel & 0xFFFFFFFF)
        return result


class GameResourcePreparationMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-resource-preparation-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>104I', cls.rom, screen.ROM))
        assembly = (cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+assembly+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', cls.slot, filename='generated_6A3D0'))
        cls.before = (cls.out/'before-elf').read_bytes()
    def receipt(self, name, **values):
        assert name!='baseline'
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')
    @classmethod
    def link(cls, name, symbols=S, entry=screen.ENTRY):
        script = cls.out/('%s-%X.ld' % (name,entry)); elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(cls.out/(name+'.o'))],
            check=True, capture_output=True)
        return list(struct.unpack_from('>104I', sections(elf)['.text'][1]))
    def compare(self, memory, forms=None, **settings):
        reference = Reference(memory, settings.get('symbols',S), settings.get('actions'), settings.get('results'))
        result = reference.run(settings.get('identity',7), settings.get('channel',0), settings.get('extras',1))
        expected = public(reference.memory), events(reference.events), reference.calls, result
        models = [PreparationOracle(words, memory, **settings).run() for words in (forms or (self.retail,self.raw))]
        for model in models:
            self.assertEqual((public(model.memory), events(model.events), model.calls, model.r[2]), expected)
        self.assertEqual(models[0].memory, models[1].memory)
        self.assertEqual(models[0].events, models[1].events)
        return models
    def test_01_direct_shape(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (104,0x48,0,0,''))
        self.assertEqual(self.raw, self.retail)
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.link('padded'), self.retail)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse(any(r['function']==screen.FUNCTION for r in csv.DictReader(stream)))
        self.receipt('shape', words=104, frame=72, raw_differences=0, guards=0, direct_match=True)
    def test_02_complete_branch_boundary_product(self):
        reached = set(); cases = 0
        for present, config, flags, actor_flags, cached, extras, descriptor, extra_count, phase in itertools.product(
                (False,True), (False,True), (0,0x4000,0xFFFFFFFF), (0,1,0xFE,0xFF),
                (False,True), (0,1,0xFFFFFFFF), (0,0x0FFFFFFF,0x10000000,0xFFFFFFFF), (0,1), (0,8)):
            models = self.compare(fixture(present=present,config=config,flags=flags,actor_flags=actor_flags,
                cached=cached,descriptor=descriptor,extra_count=extra_count), extras=extras, phase=phase,
                results=dict(load=0 if phase==0 else 0x80000001,
                    extras=0 if actor_flags&1 else 0x10, buffers=0xFFFFFFFF))
            reached.update(models[0].visits); cases += 1
        self.assertEqual(reached, set(range(screen.ENTRY,screen.ENTRY+416,4)))
        self.receipt('guest', cases=cases, executions=cases*2, reached_words=len(reached),
            independent_complete_memory_access_order_and_call_reference=True)
    def test_03_word_ABI_unsigned_counts_and_live_callback_mutations(self):
        cases = 0
        count_address = address(S,'D_800C4778',7,2)
        list_address = address(S,'D_800C4488',7)
        for identity, channel, extras, present, phase in itertools.product(
                (-1,0,1,128,186,255,0x40000007,0x80000001), (-1,0,3,0x80000001),
                (0,1,0x80000000,0xFFFFFFFF), (False,True), (0,8)):
            self.compare(fixture(identity=identity),identity=identity,channel=channel,extras=extras,phase=phase)
            self.compare(fixture(identity=identity,present=present,actor_flags=0xFF),identity=identity,
                channel=channel,extras=extras,phase=phase,results=dict(load=0xFFFFFFFF,buffers=0x80000000))
            cases += 2
        for count, extra_count, phase in itertools.product((0,1,2,15,0x7FFF,0x8000,0xFFFF),
                (0,1,0x7FFF,0x8000,0xFFFF),(0,8)):
            self.compare(fixture(count=count,extra_count=extra_count),phase=phase,
                actions={('entry',0):((count_address,1,2),)})
            cases += 1
        for phase, result, initial in itertools.product((0,8),(0,0x10,0x80000000),(0,1,3)):
            actions = {('extras',0):((count_address,3,2),(list_address,OTHER_LIST,4)),
                ('entry',0):((count_address,5,2),(list_address,LIST,4)),
                ('entry',1):((count_address,3,2),(list_address,OTHER_LIST,4))}
            self.compare(fixture(count=initial),phase=phase,results=dict(extras=result),actions=actions)
            cases += 1
        for phase in (0,8):
            actions = {('auxiliary',0):((address(S,'D_800C5628',7,2),0xFFFF,2),
                (DESCRIPTOR,0x10000000,4),(ACTOR+0x144,0,4),(ACTOR+0xAC,0,1))}
            self.compare(fixture(flags=0x4000,extra_count=0),phase=phase,actions=actions)
            cases += 1
        self.receipt('mutations', cases=cases, executions=cases*2,
            word_ABI_high_bits_unsigned_halfword_counts_dynamic_growth_shrink_and_list_reloads=True,
            guest_index_wrap_not_portable_C_array_domain=True)
    def test_04_short_circuit_unmapped_memory_and_aliases(self):
        cases = 0
        for config, flags, extras, descriptor in ((False,0,0,0),(True,0x4000,0,0),
                (True,0,1,0x10000000),(True,0,1,0)):
            memory = fixture(config=config,flags=flags,descriptor=descriptor,count=0,extra_count=0)
            if not config:
                for i in range(0x40): del memory[CONFIG+i]
            if flags&0x4000:
                del memory[ACTOR+0xAC]
            for table,stride in (('D_800C5338',4),('D_800C4488',4),('D_800C4778',2)):
                for i in range(stride): del memory[address(S,table,7,stride)+i]
            if not extras:
                for i in range(2): del memory[address(S,'D_800C5628',7,2)+i]
            self.compare(memory,extras=extras); cases += 1
        for table, location in (('D_800C5338',ACTOR+0x144),('D_800C4778',LIST+4),
                ('D_800C4488',DESCRIPTOR)):
            symbols = dict(S); stride = 2 if table=='D_800C4778' else 4
            symbols[table] = location-7*stride
            forms = [self.link(name,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms,[forms[0]]*3)
            memory = fixture(symbols=symbols,count=2)
            if table=='D_800C5338': put(memory,ACTOR+0x144,DESCRIPTOR); put(memory,DESCRIPTOR+24,0)
            if table=='D_800C4488': put(memory,DESCRIPTOR,LIST)
            self.compare(memory,forms=forms,symbols=symbols,
                actions={('entry',0):((address(symbols,'D_800C4778',7,2),1,2),)})
            cases += 1
        self.receipt('aliases', cases=cases, short_circuit_missing_inputs_and_cross_role_aliases=True)
    def test_05_independent_relocations_and_fired_fault_prefixes(self):
        cases = faults = links = 0
        for entry, delta in ((screen.ENTRY,0),(0x15207FF0,0x47FFC),(0x15308004,0x88004)):
            symbols = {n:v+delta if n.startswith('D_') else v for n,v in S.items()}
            forms = [self.link(name,symbols,entry) for name in ('original','selected','padded')]; links += 3
            self.assertEqual(forms,[forms[0]]*3)
            for present, extras, flags, phase in itertools.product((False,True),(0,1),(0,0x4000),(0,8)):
                self.compare(fixture(symbols=symbols,present=present,flags=flags),forms=forms,
                    symbols=symbols,entry=entry,extras=extras,phase=phase); cases += 1
        for present, config, flags, extras, descriptor, result, phase in itertools.product(
                (False,True),(False,True),(0,0x4000),(0,1),
                (0,0x10000000),(0,0x80000001),(0,8)):
            memory = fixture(present=present,config=config,flags=flags,descriptor=descriptor)
            settings = dict(extras=extras,phase=phase,results=dict(load=result,extras=result))
            complete = PreparationOracle(self.retail,memory,**settings).run()
            for index in range(complete.accesses):
                models = []
                for words in (self.retail,self.raw):
                    model = PreparationOracle(words,memory,**settings); model.fault=index
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,index); models.append(model)
                self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                    (models[1].memory,models[1].events,models[1].calls)); faults += 1
        self.receipt('links-faults', links=links, rebase_cases=cases, fired_fault_pairs=faults,
            complete_partial_memory_accesses_calls_equal=True)
    def test_06_effective_fresh_semantic_controls(self):
        controls = (
            ('wrong-loader-extra', 'extras, actor[0xAC]', '0, actor[0xAC]', fixture(present=False), {}),
            ('wrong-actor-byte', 'actor[0xAC]);', '(s8)actor[0xAC]);', fixture(present=False,actor_flags=255), {}),
            ('wrong-aux-flag', '& 0x4000', '& 0x2000', fixture(flags=0x4000), {}),
            ('signed-threshold', '*(*(u32 **)((u8 *)D_800C5338 + tableOffset)) < 0x10000000U',
                '(s32)*(*(u32 **)((u8 *)D_800C5338 + tableOffset)) < 0x10000000',
                fixture(descriptor=0xFFFFFFFF), {}),
            ('wrong-entry-command', ', 0, 0, 0x3E, 0)', ', 0, 0, 0x3F, 0)', fixture(), {}),
            ('wrong-fifth-arg', ', 0, 0, 0x3E, 0)', ', 0, 0, 0x3E, 1)', fixture(), {}),
            ('discard-extras-error', 'result = func_1503DC3C(identity);',
                'func_1503DC3C(identity);', fixture(), dict(results=dict(extras=0x10))),
            ('wrong-helper-channel', 'func_15084044(actor, channel)', 'func_15084044(actor, 0)',
                fixture(), dict(channel=3)),
            ('snapshot-count', screen.QUALIFIED, screen.QUALIFIED.replace(
                '    s32 tableOffset;', '    s32 tableOffset;\n    s32 limit;').replace(
                '                for (index = 0;', '                limit = D_800C4778[identity];\n                for (index = 0;').replace(
                'index < D_800C4778[identity]', 'index < limit'), fixture(),
                dict(actions={('entry',0):((address(S,'D_800C4778',7,2),1,2),)})),
            ('snapshot-list', screen.QUALIFIED, screen.QUALIFIED.replace(
                '    s32 tableOffset;', '    s32 tableOffset;\n    u32 *entries;').replace(
                '                for (index = 0;',
                '                entries = (*(u32 **)((u8 *)D_800C4488 + tableOffset));\n                for (index = 0;').replace(
                '(*(u32 **)((u8 *)D_800C4488 + tableOffset))[index]', 'entries[index]'), fixture(),
                dict(actions={('entry',0):((address(S,'D_800C4488',7),OTHER_LIST,4),)})),
        )
        for name, before, after, memory, settings in controls:
            with self.subTest(control=name):
                self.assertEqual(screen.QUALIFIED.count(before),1)
                with patch.object(screen,'ENTRY',0x15400000):
                    meta, words = screen.compile_candidate(self.root,self.out,name,screen.QUALIFIED.replace(before,after))
                self.assertGreater(meta['differences'],0)
                correct = PreparationOracle(self.raw,memory,**settings).run()
                wrong = PreparationOracle(words,memory,entry=0x15400000,**settings).run()
                self.assertNotEqual((events(correct.events),correct.calls,correct.r[2]),
                    (events(wrong.events),wrong.calls,wrong.r[2]))
        self.receipt('controls', freshly_compiled_effective_controls=len(controls))
    def test_07_copied_owner_both_actual_padders(self):
        before = (self.out/'before-source').read_text(); objects = []
        real_run = subprocess.run
        def run(command, *args, **kwargs):
            if str(command[0]).endswith('/cc'):
                command = list(command)+['-Wo,-loopunroll,0']
            return real_run(command,*args,**kwargs)
        for name, source in (('owner-before',before),('owner-after',screen.install(before))):
            with patch('subprocess.run',side_effect=run):
                obj, diagnostics = compile_owner(self.root,self.out,source,name)
            self.assertEqual(diagnostics,[])
            objects.append(obj)
        parsed = [parse_object(obj) for obj in objects]
        def fingerprint(data,name):
            text, functions, relocations = data; info = functions[name]; start = info['value']
            return info['size'],text[start:start+info['size']],{
                o-start:v for o,v in relocations.items() if start<=o<start+info['size']}
        self.assertEqual(set(parsed[0][1]),set(parsed[1][1]))
        for name in parsed[0][1]:
            if name!=screen.FUNCTION:
                self.assertEqual(fingerprint(parsed[0],name),fingerprint(parsed[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for route in ('pad_c_object.py','pad_generated_object.py'):
            padded = []
            for i,obj in enumerate(objects):
                asm = self.out/('owner-%s-%d.s' % (route,i))
                args = [str(obj),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
                args += ['--word-patches',str(self.out/'before-guards')]
                subprocess.run(['python3',str(self.root/'tools'/route),*args],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                padded.append(parse_object(asm.with_suffix('.o')))
            start = padded[1][1][screen.FUNCTION]['value']; end = start+416
            expected = bytearray(padded[0][0]); expected[start:end]=padded[1][0][start:end]
            self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<end},
                {o:v for o,v in padded[1][2].items() if not start<=o<end})
            self.assertEqual(fingerprint(parsed[1],screen.FUNCTION),
                fingerprint(parse_object(self.out/'selected.o'),screen.FUNCTION))
        self.receipt('owner', neighbors=len(parsed[0][1])-1, diagnostics=0,
            exact_isolated_complete_owner_body=True, padding_routes=2,
            all_neighbor_bytes_extents_relocations_and_pools_unchanged=True)
    def test_08_linked_installation_audit(self):
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source = (self.root/screen.SOURCE).read_text()
        if source==(self.out/'before-source').read_text():
            for name,path in self.paths.items():
                self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
            self.receipt('linked',installed=False,immutable_baseline_verified=True); return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        struct.pack_into('>104I',expected,elf_slot_offset(self.before,screen.ENTRY,416),*self.retail)
        extent = installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        struct.pack_into('>I',expected,extent,416)
        previous, current = metadata(self.before), metadata(actual)
        self.assertEqual(previous[:2],current[:2]); self.assertEqual(previous[3],current[3])
        symbols = previous[2].copy()
        target = next(s for s in symbols if s[0]==screen.FUNCTION.encode() and s[1]==screen.ENTRY)
        self.assertEqual(target[2],12); symbols[target]-=1
        symbols[(target[0],target[1],416,*target[3:])]+=1
        self.assertEqual(+symbols,current[2])
        changed_metadata = 0
        for table in current[4:]:
            start,end = table[4],table[4]+table[5]
            changed_metadata += sum(a!=b for a,b in zip(self.before[start:end],actual[start:end]))
            expected[start:end]=actual[start:end]
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name not in ('source','elf'):
                self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit = audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,target_all_104_words_direct_exact=True,
            ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),changed_metadata_bytes=changed_metadata,
            only_target_slot_extent_and_existing_metadata_order_change=True,
            all_other_ELF_bytes_names_values_data_layout_guards_conversion_rows_exact=True,
            protected_data=audit)
    def test_09_native32_actual_complete_body(self):
        for profile in ('-O2','-O0'):
            code, detail = self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''))
        code, _ = self.run_native('native-negative',NATIVE+screen.QUALIFIED.replace(
            ', 0, 0, 0x3E, 0)', ', 0, 0, 0x3F, 0)')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native',cases_per_profile=18432,profiles=['O2','O0'],
            complete_actual_C_independent_reference_trace_mutations_and_memory_equal=True,
            effective_wrong_command_control=True)
    def test_10_actual_matched_buffer_callee_all_resource_paths(self):
        inner = list(struct.unpack_from('>194I',self.before,
            elf_slot_offset(self.before,buffers.screen.ENTRY,776)))
        self.assertEqual(inner,list(struct.unpack_from('>194I',self.rom,buffers.screen.ROM)))
        connected = {buffers.screen.ENTRY+i*4:w for i,w in enumerate(inner)}
        cases = 0; reached = set(); callee_reached = set()
        for mode,channel,present,extras,flags,loaded_result,phase,bounds,allocation_results in itertools.product(
                range(4),(0,1,3),(False,True),(0,1),(0,0x4000),(0,0x10),(0,8),
                ((1,0,3),(0,0,3),(1,0x10000000,3),(1,0,0)),
                ((buffers.PRIVATE,buffers.ALTERNATE),(0,buffers.ALTERNATE),(buffers.PRIVATE,0))):
            extra_count,descriptor,count = bounds
            memory = fixture(present=present,flags=flags,count=count,actor_flags=0,
                extra_count=extra_count,descriptor=descriptor)
            memory.update(buffers.fixture(mode,channel=channel,source=buffers.SOURCE if present else 0))
            put(memory,ACTOR+0xAC,0,1); put(memory,CONFIG+24,flags)
            count_address = address(S,'D_800C4778',7,2)
            actions = {('load',0):((address(S,'D_800D19A0',7),buffers.SOURCE,4),),
                ('entry',0):((address(S,'D_800C4488',7),OTHER_LIST,4),),
                ('entry',1):((count_address,3,2),)}
            settings = dict(channel=channel,extras=extras,phase=phase,actions=actions,
                results=dict(load=loaded_result,extras=loaded_result))
            models = []
            for words in (self.retail,self.raw):
                model = PreparationOracle(words,memory,connected=connected,**settings)
                model.buffer_results = allocation_results
                models.append(model.run())
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].r[2]))
            reference = Reference(memory,actions=actions,results=settings['results'])
            outer_result = reference.run(channel=channel,extras=extras)
            forwarded = [c for c in reference.calls if c[0]==S['func_15084044']]
            self.assertEqual([c for c in models[0].calls if c[0] in S.values()],reference.calls)
            if forwarded:
                expected_inner = buffers.Reference(reference.memory,allocation_results,actions)
                expected_result = expected_inner.run(channel=channel)
                self.assertEqual(public(models[0].memory),public(expected_inner.memory))
                self.assertEqual(events(models[0].events),events(reference.events)+events(expected_inner.events))
                self.assertEqual(models[0].r[2],expected_result)
            else:
                self.assertEqual(public(models[0].memory),public(reference.memory))
                self.assertEqual(models[0].r[2],outer_result)
            reached.update(models[0].visits & set(range(screen.ENTRY,screen.ENTRY+416,4)))
            callee_reached.update(models[0].visits & set(connected)); cases += 1
        self.assertEqual(len(reached),104)
        self.receipt('connected',cases=cases,executions=cases*2,complete_caller_words=104,
            reached_caller_words=len(reached),complete_actual_callee_words=194,
            reached_callee_words=len(callee_reached),independent_connected_result_calls_memory_access_reference=True,
            deeper_resource_loaders_and_allocator_callbacks_remain_bounded=True)


NATIVE = r'''
#define NULL ((void *)0)
typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef int s32;
static u8 actor[0x340],config[0x40];
u8 *D_800D19A0[187],*D_800C5C08[187];
u16 D_800C5628[187],D_800C4778[187];
u32 *D_800C5338[187],*D_800C4488[187];
static u32 descriptor[8],list[16],other[16],trace[32][6],saved[32][6];
static s32 n,action; static u32 loadResult,extraResult,bufferResult;
static void record(u32 role,u32 a,u32 b,u32 c,u32 d,u32 e) {
    trace[n][0]=role;trace[n][1]=a;trace[n][2]=b;
    trace[n][3]=c;trace[n][4]=d;trace[n][5]=e;n++;
}
s32 func_1503CF20(s32 id,s32 zero,u8 *cfg,s32 extra,s32 flags) {
    record(1,id,zero,(u32)cfg,extra,flags);
    if(action==2) D_800D19A0[id]=actor;
    return loadResult;
}
void func_150028BC(s32 id) {
    record(2,id,0,0,0,0);
    if(action==1) { D_800C5628[id]=1;descriptor[0]=0; }
}
s32 func_1503DC3C(s32 id) {
    record(3,id,0,0,0,0);
    if(action==1) { D_800C4778[id]=3;D_800C4488[id]=other; }
    return extraResult;
}
static s32 liveId,entries;
void func_1510CE60(u32 entry,s32 a,s32 b,s32 command,s32 fifth) {
    record(4,entry,a,b,command,fifth);
    if(action==2) {
        if(entries==0) { D_800C4778[liveId]=5;D_800C4488[liveId]=other; }
        else if(entries==1) { D_800C4778[liveId]=3;D_800C4488[liveId]=list; }
    }
    entries++;
}
s32 func_15084044(u8 *value,s32 channel) {
    record(5,(u32)value,channel,0,0,0);return bufferResult;
}
static s32 reference(s32 id,s32 channel,s32 extra) {
    u8 *cfg=*(u8 **)(actor+0x144);u32 result=0; s32 i;
    if(!D_800D19A0[id]) result=func_1503CF20(id,0,cfg,extra,actor[0xAC]);
    else {
        if((cfg && (*(u32 *)(cfg+24)&0x4000)) || (actor[0xAC]&1))
            if(!D_800C5C08[id]) func_150028BC(id);
        if(extra && D_800C5628[id] && D_800C5338[id][0]<0x10000000U) {
            result=func_1503DC3C(id);i=0;
            while(i<D_800C4778[id]) {
                func_1510CE60(D_800C4488[id][i],0,0,0x3E,0);i++;
            }
        }
    }
    return result?result:(u32)func_15084044(actor,channel);
}
static void reset(s32 id,s32 present,s32 cfg,s32 flag,s32 cached,s32 extraCount,
        s32 threshold,s32 count,s32 act,s32 fail) {
    s32 i; n=0;entries=0;liveId=id;action=act;
    loadResult=fail==1?0x80000001U:0;extraResult=fail==2?0x10:0;
    bufferResult=fail==3?0xFFFFFFFFU:0;
    for(i=0;i<0x340;i++) actor[i]=(u8)(i*19+0x35);
    for(i=0;i<0x40;i++) config[i]=(u8)(i*19+0x35);
    *(u8 **)(actor+0x144)=cfg?config:NULL;actor[0xAC]=count==1?0xFF:0;
    *(u32 *)(config+24)=flag?0x4000:0;
    for(i=0;i<187;i++) {
        D_800D19A0[i]=D_800C5C08[i]=NULL;D_800C5338[i]=D_800C4488[i]=NULL;
        D_800C5628[i]=D_800C4778[i]=0;
    }
    for(i=0;i<8;i++) descriptor[i]=0xA5A50000U+i;
    for(i=0;i<16;i++) { list[i]=0x11000000U+i;other[i]=0x91000000U+i; }
    D_800D19A0[id]=present?actor:NULL;D_800C5C08[id]=cached?actor:NULL;
    D_800C5628[id]=extraCount;D_800C4778[id]=count;
    D_800C5338[id]=descriptor;D_800C4488[id]=list;
    descriptor[0]=threshold?0xFFFFFFFFU:0;
}
static u8 savedMemory[sizeof(actor)+sizeof(config)+sizeof(descriptor)+sizeof(list)+sizeof(other)
    +sizeof(D_800D19A0)+sizeof(D_800C5C08)+sizeof(D_800C5628)+sizeof(D_800C4778)
    +sizeof(D_800C5338)+sizeof(D_800C4488)];
static s32 bytes(const void *data,s32 size,s32 *offset,s32 save) {
    const u8 *p=data;s32 i;
    for(i=0;i<size;i++) {
        if(save) savedMemory[*offset+i]=p[i];
        else if(savedMemory[*offset+i]!=p[i]) return 0;
    }
    *offset+=size;return 1;
}
static s32 memory(s32 save) {
    s32 offset=0;
#define CHECK(x) if(!bytes(x,sizeof(x),&offset,save)) return 0
    CHECK(actor);CHECK(config);CHECK(descriptor);CHECK(list);CHECK(other);
    CHECK(D_800D19A0);CHECK(D_800C5C08);CHECK(D_800C5628);
    CHECK(D_800C4778);CHECK(D_800C5338);CHECK(D_800C4488);
#undef CHECK
    return offset==(s32)sizeof(savedMemory);
}
'''
NATIVE_MAIN = r'''
static s32 main(void) {
    s32 p,c,f,a,e,t,x,k,m,b,id,i,j,expectedN,cases=0;
    u32 expectedResult;static const s32 ids[]={0,7,128,186};
    if(sizeof(void *)!=4 || sizeof(s32)!=4) return 9;
    for(id=0;id<4;id++) for(p=0;p<2;p++) for(c=0;c<2;c++)
    for(f=0;f<2;f++) for(a=0;a<2;a++) for(e=0;e<2;e++)
    for(t=0;t<2;t++) for(x=0;x<2;x++) for(k=0;k<3;k++)
    for(m=0;m<3;m++) for(b=0;b<4;b++) {
        reset(ids[id],p,c,f,a,x,t,k,m,b);
        expectedResult=reference(ids[id],0x80000003U,e?0x80000000U:0);
        expectedN=n;if(!memory(1)) return 4;
        for(i=0;i<n;i++) for(j=0;j<6;j++) saved[i][j]=trace[i][j];
        reset(ids[id],p,c,f,a,x,t,k,m,b);
        if((u32)func_1503DA9C(actor,ids[id],0x80000003U,e?0x80000000U:0)!=expectedResult
            || n!=expectedN || !memory(0)) return 1;
        for(i=0;i<n;i++) for(j=0;j<6;j++) if(trace[i][j]!=saved[i][j]) return 2;
        cases++;
    }
    return cases==18432?0:3;
}
void _start(void) {
    s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");
    __builtin_unreachable();
}
'''


if __name__=='__main__':
    unittest.main()
