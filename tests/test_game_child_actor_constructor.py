"""Full child constructor recovery, live O32 homes and bounded integration."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_child_actor_constructor_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_actor_animation_constructor_match as caller
from tools.tests import test_game_actor_resource_transition_match as transition
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset, SYMBOL
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.check_game_data_layout import audit_layout

STACK, MASK, S = guest.STACK, 0xFFFFFFFF, screen.SYMBOLS
RESOURCE, OTHER_RESOURCE = 0x26000, 0x27000
COUNTS = dict(func_1503D774=2, func_1503D660=2, func_1505ED34=0,
    func_150615DC=1, func_1515D480=1, func_1515D440=0,
    func_150839B8=3, func_150837D4=3, func_150838EC=4)
FLOATS = (0, 0x80000000, 0x3F800000, 0xC0200000, 1,
    0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345)


def private(address): return STACK - 0x800 <= address < STACK + 0x100
def public(memory): return {a: v for a, v in memory.items() if not private(a)}
def public_events(events): return [e for e in events if e[0] == 'CALL' or not private(e[1])]
def index(address, base): return (abs(signed(address - base)) // 812) * (-1 if signed(address - base) < 0 else 1)


def fixture(flags=3, inherit=1, identity=7, count=2, active=1, parent=1,
        child=3, magnitude=11, pattern=0, scale=0x3F800000, symbols=S):
    base = symbols['D_800CC2D0']; actor = (base + parent * 812) & MASK
    created = (base + child * 812) & MASK
    memory = {}
    for start, length in ((STACK-0x800, 0x900), (actor, 0x400), (created, 0x400),
            (RESOURCE, 64), (OTHER_RESOURCE, 64), (symbols['D_800D1C90'], 1024),
            (symbols['D_80082FA0'], 4), (symbols['D_800C35EA'], 1), (symbols['D_800C3638'], 1)):
        memory.update({(start+i)&MASK: (i*17+35)&255 for i in range(length)})
    for n in range(256): put(memory, symbols['D_800D1C90']+n*4, RESOURCE)
    put(memory, RESOURCE+14, magnitude, 2); put(memory, OTHER_RESOURCE+14, 65535, 2)
    for i, offset in enumerate((0x14C, 0x150, 0x154, 0x158)):
        put(memory, actor+offset, FLOATS[(pattern+i)%len(FLOATS)])
    put(memory, created+0x300, 0 if pattern&1 else 0xA5812345)
    put(memory, symbols['D_80082FA0'], count)
    put(memory, symbols['D_800C35EA'], active, 1); put(memory, symbols['D_800C3638'], 173, 1)
    return memory, (actor, 0xF1234567, identity&MASK, 0x81820304,
        0x76543210, flags&MASK, inherit&MASK, 0xFFEEDDCC, scale), created


def mutations(name, ordinal, plan, created, stack, symbols):
    if plan == 1 and name == 'func_1503D774' and ordinal == 0:
        return ((stack+8, 9, 4), (stack+0x10, 0xDEADBEEF, 4),
            (stack+0x14, 3, 4), (stack+0x18, 1, 4))
    if plan == 2 and name == 'func_1503D774' and ordinal == 1:
        return ((stack+8, 11, 4), (stack+0x14, 0, 4), (created+0x14C, bits(2.5), 4),
            (symbols['D_800D1C90']+11*4, OTHER_RESOURCE, 4))
    if plan == 3 and name == 'func_1515D480' and ordinal == 0:
        return ((symbols['D_80082FA0'], 0, 4),)
    if plan == 4 and name == 'func_1515D480' and ordinal == 0:
        return ((symbols['D_80082FA0'], 3, 4),)
    if plan == 5 and name == 'func_150839B8':
        return ((stack+8, 255, 4), (symbols['D_800C35EA'], 0, 1),
            (symbols['D_800C3638'], 99, 1))
    if plan == 6 and name == 'func_150837D4':
        return ((stack+0x1C, 0x13579BDF, 4), (stack+0x20, 0x7F812345, 4),
            (symbols['D_800C35EA'], 1, 1), (symbols['D_800C3638'], 201, 1))
    return ()


def reference(memory, arguments, created, plan=0, symbols=S, stack=STACK):
    state, events, calls, ordinals = memory.copy(), [], [], {}
    actor, attachment, identity, kind, value, flags, inherit, mode, scale = arguments
    put(state, stack+8, identity)
    for i, value in enumerate(arguments[4:], 4): put(state, stack+i*4, value)
    def get(where, size=4):
        where &= MASK
        assert all(where+i in state for i in range(size)), ('reference read', where, size)
        value = read(state, where, size); events.append(('R', where, size, value)); return value
    def store(where, value, size=1):
        where &= MASK
        assert all(where+i in state for i in range(size)), ('reference write', where, size)
        value &= (1 << (size*8))-1; put(state, where, value, size); events.append(('W', where, size, value))
    def call(name, args):
        target = symbols[name]; calls.append((target, *args)); events.append(('CALL', target, args))
        ordinal = ordinals.get(name, 0); ordinals[name] = ordinal+1
        for where, value, size in mutations(name, ordinal, plan, created, stack, symbols): store(where, value, size)
        if name == 'func_1505ED34': return created
        if name == 'func_1515D480': return 0 if ordinal&1 else 0x31000+ordinal*16
        if name == 'func_1515D440': return 0xF1238004
        return 0xDEADBEEF
    call('func_1503D774', (get(stack+8), 0)); call('func_1503D660', (get(stack+8), 0))
    call('func_1505ED34', ())
    store(created+0x3B, 255-index(created, symbols['D_800CC2D0']))
    store(created+0xAB, kind); store(created, get(stack+0x10), 4)
    call('func_150615DC', (created,)); identity = get(stack+8)
    for offset, value in ((0x232, 1), (0x1CA, 1), (0x125, 255),
            (0x65, index(actor, symbols['D_800CC2D0'])+1)): store(created+offset, value)
    store(created+0x5C, attachment, 4); store(created+0x123, 1); store(created+4, identity)
    flags_byte = get(actor+0x66, 1)
    store(created+0x66, flags_byte); store(created+0x66, flags_byte&239); store(created+0x66, flags_byte&239)
    for source, destination in ((0x1DD, 0x1DD), (0x1DE, 0x1DE), (0x1DE, 0x1DF),
            (0x1E0, 0x1E0), (0x1E1, 0x1E1), (0x1E2, 0x1E2)):
        store(created+destination, get(actor+source, 1))
    inherit = get(stack+0x18)
    for offset in (0x14C, 0x150, 0x154, 0x158):
        store(created+offset, get(actor+offset) if inherit else bits(1.0), 4)
    flags = get(stack+0x14); store(created+0x101, inherit); store(created+0xAC, flags)
    call('func_1503D774', (identity, 0))
    if flags&1:
        store(created+0xF8, get(created+0xF8)|0x4000, 4)
        identity = get(stack+8); resource = get((symbols['D_800D1C90']+identity*4)&MASK)
        magnitude = get(resource+14, 2); size = floating(get(created+0x14C))
        store(created+0x270, bits(float(magnitude)*size), 4)
    mode = int(bool(flags&2)); i = 0
    count = signed(get(symbols['D_80082FA0']))
    if count >= 0:
        while True:
            result = call('func_1515D480', (1,)); store(created+0x304+i*4, result, 4)
            count = signed(get(symbols['D_80082FA0'])); i += 1
            if i > count: break
            assert i < 8, 'unbounded fixture allocation limit'
    if get(created+0x300+i*4): store(created+0x301, 1)
    store(created+0x314, call('func_1515D440', ()), 4)
    active = get(symbols['D_800C35EA'], 1) == 1
    if active: store(symbols['D_800C3638'], 0)
    call('func_150839B8', (created, get(stack+8), 0))
    call('func_150837D4', (index(created, symbols['D_800CC2D0'])&MASK, get(stack+8), 1))
    call('func_150838EC', (created, get(stack+0x1C), mode, get(stack+0x20)))
    if active: store(symbols['D_800C3638'], 1)
    return public(state), public_events(events), calls, created


class ChildOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, arguments, created, plan=0, phase=0,
            symbols=S, entry=screen.ENTRY, connected=None):
        super().__init__(words, memory, arguments=arguments, phase=phase, entry=entry, connected=connected)
        self.symbols, self.created, self.plan = symbols, created, plan
        self.roles = {symbols[name]: name for name in COUNTS}; self.counts = {symbols[n]: c for n, c in COUNTS.items()}
        self.ordinals = {}; self.top_stack = STACK+phase; self.public_fault = None; self.public_accesses = 0
    def public_gate(self, where):
        if private(where): return
        if self.public_accesses == self.public_fault: raise guest.AccessFault(self.public_accesses)
        self.public_accesses += 1
    def get(self, where, size):
        self.public_gate(where); return super().get(where, size)
    def put(self, where, value, size):
        if self.recording: self.public_gate(where)
        super().put(where, value, size)
    def record_call(self, target):
        args = self.arguments(self.counts[target]); self.calls.append((target, *args)); self.events.append(('CALL', target, args))
    def hook(self, target):
        name = self.roles[target]; ordinal = self.ordinals.get(name, 0); self.ordinals[name] = ordinal+1
        for where, value, size in mutations(name, ordinal, self.plan, self.created, self.top_stack, self.symbols):
            self.put(where, value, size)
        result = (self.created if name == 'func_1505ED34' else
            (0 if ordinal&1 else 0x31000+ordinal*16) if name == 'func_1515D480' else
            0xF1238004 if name == 'func_1515D440' else 0xDEADBEEF)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]; self.r[2] = result


class GameChildActorConstructorTests(unittest.TestCase):
    maxDiff = 1000
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = native.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root/'conker/build/game-child-actor-constructor-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv', rodata='conker/asm/data/23B8A0.rodata.s',
            symbols='conker/symbol_addrs.us.txt', undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text(); hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths: assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>182I', cls.rom, screen.ROM)); cls.before = (cls.out/'before-elf').read_bytes()
        body = (cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split('endlabel '+screen.FUNCTION, 1)[0]
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
    def receipt(self, name, **values): (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')
    def compare(self, memory, arguments, created, forms=None, **settings):
        expected = reference(memory, arguments, created, plan=settings.get('plan', 0),
            symbols=settings.get('symbols', S), stack=STACK+settings.get('phase', 0))
        models = [ChildOracle(code, memory, arguments, created, **settings).run() for code in (forms or (self.retail, self.raw))]
        for model in models: self.assertEqual((public(model.memory), public_events(model.events), model.calls, model.r[2]), expected)
        return models
    def test_01_full_shape_and_not_byte_exact(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (182, 80, 125, 0, ''))
        self.assertNotEqual(self.raw, self.retail)
        self.assertEqual(sum(uses == [('R_MIPS_26', name)] for uses in self.meta['relocations'].values() for name in COUNTS), 10)
        with self.assertRaises(ValueError): screen.install(screen.SELECTED)
        self.receipt('shape', raw_words=182, retail_words=182, raw_frame=80, retail_frame=56,
            differences=125, new_guards=0, matching_credit_added=0, private_frame_fault_equivalence_not_claimed=True)
    def test_02_domains_boundaries_live_arguments_and_aliases(self):
        cases = 0; coverage = set()
        values = [dict(flags=i, identity=i, pattern=i%len(FLOATS), inherit=i) for i in range(256)]
        values += [dict(flags=f, inherit=v, count=n, active=a, parent=p, child=c, magnitude=m, pattern=t, scale=b)
            for f, v, n, a, p, c, m, t, b in itertools.product((0,1,2,3,0xFFFFFFFF), (0,1,2,0xFFFFFFFF),
                (-1,0,2), (0,1,2,255), (1,), (1,3), (0,65535), (3,), (0x80000000,0x7F812345))]
        values += [dict(parent=p, child=c, flags=3, inherit=1) for p,c in ((-2,-1),(0,255),(255,0))]
        for values in values:
            memory, args, created = fixture(**values); models = self.compare(memory, args, created)
            coverage.update(models[0].visits); cases += 1
        for plan, phase, active in itertools.product(range(7), (0,8), (0,1,2)):
            memory, args, created = fixture(active=active); self.compare(memory, args, created, plan=plan, phase=phase); cases += 1
        for delta in (4, 0x100, -4):
            memory,args,created=fixture(); parent=created+delta
            memory.update({parent+i:memory.get(parent+i,(i*17+35)&255) for i in range(0x400)})
            args=(parent,*args[1:]);self.compare(memory,args,created);cases+=1
        self.receipt('guest', cases=cases, executions=cases*2, reached_retail_words=len(coverage),
            complete_routine=True, all_flag_identity_inherit_bytes=True, adversarial_GP_FPR_clobbers=True,
            live_identity_value_flags_inherit_state_scale_homes=True, allocation_limit_bounded_to_three=True,
            independent_ordered_public_reference=True, private_frame_equivalence_not_claimed=True)
    def test_03_fired_public_faults_and_unconditional_NULL_access(self):
        pairs=0
        for plan in range(7):
            memory,args,created=fixture(); models=self.compare(memory,args,created,plan=plan)
            for cut in range(models[0].public_accesses):
                failed=[]
                for code in (self.retail,self.raw):
                    model=ChildOracle(code,memory,args,created,plan=plan);model.public_fault=cut
                    with self.assertRaises(guest.AccessFault) as caught:model.run()
                    self.assertEqual(caught.exception.args,(cut,));self.assertEqual(model.public_accesses,cut);failed.append(model)
                self.assertEqual((public(failed[0].memory),public_events(failed[0].events),failed[0].calls),
                    (public(failed[1].memory),public_events(failed[1].events),failed[1].calls));pairs+=1
        memory,args,_=fixture();failed=[]
        for code in (self.retail,self.raw):
            model=ChildOracle(code,memory,args,0)
            with self.assertRaisesRegex(AssertionError,'unmapped write'):model.run()
            self.assertEqual(len(model.calls),3);failed.append(model)
        self.assertEqual(public_events(failed[0].events),public_events(failed[1].events))
        self.receipt('faults',fired_public_fault_pairs=pairs,executions=pairs*2,NULL_fault_executions=2,
            private_frame_fault_order_not_claimed=True,no_synthetic_allocation_NULL_guard=True)
    def test_04_effective_fresh_IDO_controls(self):
        controls=(('wrong-parent-index',screen.SELECTED.replace('/ 0x32C + 1','/ 0x32C + 2'),{}),
            ('wrong-mask',screen.SELECTED.replace('bits & ~0x10','bits & ~0x20'),{}),
            ('wrong-copy',screen.SELECTED.replace('created[0x1DF] = actor[0x1DE]','created[0x1DF] = actor[0x1DF]'),{}),
            ('wrong-scale-gate',screen.SELECTED.replace('inheritScale == 0','inheritScale == 1'),{}),
            ('wrong-limit',screen.SELECTED.replace('i <= D_80082FA0','i < D_80082FA0'),{}),
            ('wrong-toggle',screen.SELECTED.replace('D_800C3638 = 1','D_800C3638 = 2'),{}),
            ('wrong-float-word',screen.SELECTED.replace('*(u32 *)&scale','(u32)scale'),dict(scale=bits(2.5))))
        for name,body,values in controls:
            _,code=screen.compile_candidate(self.root,self.out,name,body);memory,args,created=fixture(**values)
            with self.assertRaises(AssertionError):self.compare(memory,args,created,forms=(code,))
        self.receipt('negative',effective_fresh_IDO_controls=len(controls))
    def test_05_independent_relocations(self):
        cases=0
        for ordinal in range(3):
            entry=0x15217FFC+ordinal*0x10004
            symbols={n:(0x80117FFC+ordinal*0x20004+i*0x1000 if n.startswith('D_') else
                0x15407FFC+ordinal*0x10004+i*0x100) for i,n in enumerate(S)}
            forms=[]
            for name in ('original','selected'):
                script=self.out/('link-%s-%d.ld'%(name,ordinal));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(self.out/(name+'.o'))],check=True,capture_output=True)
                forms.append(list(struct.unpack_from('>182I',sections(elf)['.text'][1])))
            for plan in range(7):
                memory,args,created=fixture(symbols=symbols);self.compare(memory,args,created,forms=forms,
                    symbols=symbols,entry=entry,plan=plan);cases+=1
        self.receipt('rebases',links=6,cases=cases,executions=cases*2,all_five_globals_and_nine_helpers_independent=True)
    def test_06_copied_owner_and_all_unchanged_neighbors(self):
        objects=[];padded=[];diagnostics=[];before=(self.out/'before-source').read_text()
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,warnings=compile_owner(self.root,self.out,source,name);objects.append(obj);diagnostics.append(warnings)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            asm=self.out/(name+'-padded.s')
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(self.root/'conker/retail_layout.us.txt'),
                'generated_AEB40',str(asm),'--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
            padded.append(parse_object(asm.with_suffix('.o')))
        self.assertEqual(diagnostics,[[],[]]);self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        a,b=padded;start=a[1][screen.FUNCTION]['value'];end=start+728
        self.assertEqual(a[0][:start]+a[0][end:],b[0][:start]+b[0][end:])
        for name in a[1]:
            if name!=screen.FUNCTION:self.assertEqual(a[1][name],b[1][name])
        self.assertEqual({o:v for o,v in a[2].items() if not start<=o<end},{o:v for o,v in b[2].items() if not start<=o<end})
        text,functions,_=parse_object(objects[1]);target=functions[screen.FUNCTION]
        raw_text,raw_functions,_=parse_object(self.out/'selected.o');target_raw=raw_functions[screen.FUNCTION]
        self.assertEqual(text[target['value']:target['value']+target['size']],raw_text[target_raw['value']:target_raw['value']+target_raw['size']])
        self.receipt('owner',untouched_neighbors=len(a[1])-1,all_bytes_extents_relocations_pools_exact=True,
            adjacent_helper_placeholders_unchanged=True,diagnostics=0)
    def test_07_whole_linked_installation(self):
        source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:self.receipt('linked',installed=False);return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        actual=(self.root/self.paths['elf']).read_bytes();expected=bytearray(self.before)
        struct.pack_into('>182I',expected,elf_slot_offset(self.before,screen.ENTRY,728),*self.raw)
        old,new=metadata(self.before),metadata(actual);self.assertEqual(old[:2],new[:2]);self.assertEqual(old[3:],new[3:]);changed=0
        section=old[4]
        for offset in range(section[4],section[4]+section[5],section[9]):
            a,b=SYMBOL.unpack_from(self.before,offset),SYMBOL.unpack_from(actual,offset)
            if a!=b:
                self.assertEqual(a[1],screen.ENTRY);self.assertEqual(a[:2]+a[3:],b[:2]+b[3:]);self.assertEqual((a[2],b[2]),(28,728))
                struct.pack_into('>I',expected,offset+8,b[2]);changed+=1
        self.assertEqual(changed,1);self.assertEqual(bytes(expected),actual)
        for name in ('guards','progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'])
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),all_other_ELF_bytes_exact=True,
            conversion_rows_unchanged=True,matching_credit_added=0,new_guards=0,data_audit=audit)
    def test_08_actual_descriptor_caller_and_resource_transition(self):
        outer=list(struct.unpack_from('>89I',self.rom,caller.screen.ROM))
        helper=list(struct.unpack_from('>70I',self.rom,transition.screen.ROM))
        for entry,words in ((caller.screen.ENTRY,outer),(transition.screen.ENTRY,helper)):
            self.assertEqual(words,list(struct.unpack_from('>%dI'%len(words),self.before,
                elf_slot_offset(self.before,entry,len(words)*4))))
        class Connected(ChildOracle):
            def __init__(self,memory,args,created,inner):
                code={screen.ENTRY+i*4:w for i,w in enumerate(inner)}
                code.update({transition.screen.ENTRY+i*4:w for i,w in enumerate(helper)})
                super().__init__(outer,memory,args,created,entry=caller.screen.ENTRY,connected=code)
                self.counts.update({screen.ENTRY:9,caller.OTHER:13,
                    **{transition.S[n]:c for n,c in transition.COUNTS.items()}})
            def hook(self,target):
                if target in self.roles:return super().hook(target)
                self.assert_bounded(target)
                for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
                self.f[:20]=[0xA5000000+i for i in range(20)]
                self.r[2]=8 if target==transition.S['func_15084D00'] else 0x33000 if target==transition.S['func_1502B020'] else 0
            def assert_bounded(self,target):
                assert target in (caller.OTHER,*(transition.S[n] for n in transition.COUNTS))
        cases=type0_calls=0
        for animation,active,count in itertools.product((2,15,17,46,54,79,85,5),(0,1),(-1,2)):
            memory,args,created=fixture(active=active,count=count)
            address=caller.descriptor_address(animation);offset=elf_slot_offset(self.before,address,8)
            descriptor=self.before[offset:offset+8];records=struct.unpack_from('>I',descriptor)[0];n=descriptor[4]
            data=self.before[elf_slot_offset(self.before,records,n*16):][:n*16]
            memory.update({address+i:v for i,v in enumerate(descriptor)})
            memory.update({records+i:v for i,v in enumerate(data)})
            memory.update({transition.S['D_800C5A90']+i:0 for i in range(512)})
            put(memory,transition.S['D_800C5A90']+16,1,2)
            put(memory,RESOURCE+6,-2,2);put(memory,RESOURCE+0x12,91,1)
            models=[Connected(memory,(args[0],animation,0x7F812345,0xFEEDC0DE),created,inner).run()
                for inner in (self.retail,self.raw)]
            self.assertEqual((public(models[0].memory),public_events(models[0].events),models[0].calls,models[0].r[2]),
                (public(models[1].memory),public_events(models[1].events),models[1].calls,models[1].r[2]))
            type0_calls+=sum(c[0]==screen.ENTRY for c in models[0].calls);cases+=1
        self.assertGreater(type0_calls,0)
        self.receipt('connected',cases=cases,executions=cases*2,type0_calls_per_form=type0_calls,
            actual_89_word_caller_and_70_word_helper=True,retail_linked_bodies_exact=True,
            eight_linked_descriptors=True,deep_allocators_initializers_and_alternative_constructor_bounded=True)
    def test_09_native32_profiles_and_effective_negative(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,''))
        result,_=self.run_native('native-negative',NATIVE_PREFIX+screen.SELECTED.replace('bits & ~0x10','bits & ~0x20')+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',profiles=['O2','O0'],cases_per_profile=18432,executions=36864,
            effective_negative_controls=1,same_parent_child_and_offset_aliases=True,
            finite_scale_arithmetic_only=True,all_forwarded_scale_bits_including_signaling_NaN=True,
            strict_aliasing_disabled_for_decomp_raw_word_accesses=True,deep_callbacks_bounded=True)


NATIVE_PREFIX=r'''
#define NULL ((void *)0)
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 D_800CC2D0[8*812] __attribute__((aligned(16)));
static u8 definitions[256][32] __attribute__((aligned(16)));
static u8 *D_800D1C90[256];static s32 D_80082FA0;
static u8 D_800C35EA,D_800C3638;static u8 *result;
static u32 logWords[16][5],expectedLog[16][5];static u8 expected[8*812];
static s32 logCount,allocations,phase;
static void log_call(u32 role,u32 a,u32 b,u32 c,u32 d){
    u32 *p=logWords[logCount++];p[0]=role;p[1]=a;p[2]=b;p[3]=c;p[4]=d;
}
static void func_1503D774(s32 a,s32 b){log_call(1,(u32)a,(u32)b,0,0);}
static void func_1503D660(s32 a,s32 b){log_call(2,(u32)a,(u32)b,0,0);}
static u8 *func_1505ED34(void){log_call(3,0,0,0,0);return result;}
static void func_150615DC(u8 *p){log_call(4,(u32)p,0,0,0);}
static u32 func_1515D480(s32 a){
    u32 value=allocations%2?0:0x31000u+(u32)allocations*16u;log_call(5,(u32)a,0,0,0);
    if(allocations++==0 && phase)D_80082FA0=phase==1?0:3;
    return value;
}
static u32 func_1515D440(void){log_call(6,0,0,0,0);return 0xF1238004u;}
static s32 func_150839B8(u8 *p,s32 id,s32 v){log_call(7,(u32)p,(u32)id,(u32)v,0);D_800C3638=99;return -1;}
static void func_150837D4(s32 a,s32 b,s32 c){log_call(8,(u32)a,(u32)b,(u32)c,0);}
static s32 func_150838EC(u8 *p,s32 state,s32 mode,u32 scale){
    log_call(9,(u32)p,(u32)state,(u32)mode,scale);D_800C35EA=0;return -1;
}
'''
NATIVE_RUNNER=r'''
static void store(u8 *p,u32 value){*(u32 *)p=value;}
static u32 word(u8 *p){return *(u32 *)p;}
static u8 *independent(u8 *parent,s32 attachment,s32 id,s32 kind,s32 value,
        s32 flags,s32 inherit,s32 state,u32 scale){
    u8 *p;u32 inherited,masked;int i,active;
    func_1503D774(id,0);func_1503D660(id,0);p=func_1505ED34();
    p[59]=(u8)(255-((s32)((u32)p-(u32)D_800CC2D0)/812));p[171]=(u8)kind;
    store(p,(u32)value);func_150615DC(p);
    p[562]=p[458]=1;p[293]=255;p[101]=(u8)(((s32)((u32)parent-(u32)D_800CC2D0)/812)+1);
    store(p+92,(u32)attachment);p[291]=1;p[4]=(u8)id;
    inherited=parent[102];p[102]=(u8)inherited;masked=inherited&239;p[102]=(u8)masked;p[102]=(u8)masked;
    p[477]=parent[477];p[478]=parent[478];p[479]=parent[478];
    for(i=480;i<=482;i++)p[i]=parent[i];
    for(i=332;i<=344;i+=4)store(p+i,inherit?word(parent+i):0x3F800000u);
    p[257]=(u8)inherit;p[172]=(u8)flags;func_1503D774(id,0);
    if(flags&1){store(p+248,word(p+248)|16384u);
        *(f32 *)(p+624)=(f32)*(u16 *)(D_800D1C90[id]+14)**(f32 *)(p+332);}
    i=0;if(D_80082FA0>=0){do{store(p+772+i*4,func_1515D480(1));i++;}while(i<=D_80082FA0);}
    if(word(p+768+i*4))p[769]=1;
    store(p+788,func_1515D440());active=D_800C35EA==1;
    if(active)D_800C3638=0;
    func_150839B8(p,id,0);
    func_150837D4((s32)((u32)p-(u32)D_800CC2D0)/812,id,1);
    func_150838EC(p,state,(flags&2)?1:0,scale);if(active)D_800C3638=1;return p;
}
static void setup(int flags,int inherit,int count,int active,int alias,int scale){
    int i;u8 *parent;for(i=0;i<8*812;i++)D_800CC2D0[i]=(u8)(i*17+35);
    for(i=0;i<256;i++){D_800D1C90[i]=definitions[i];*(u16 *)(definitions[i]+14)=(u16)(i*257);}
    result=D_800CC2D0+3*812;store(result+768,flags%2?0:0xA5812345u);
    parent=alias?result+(alias==2?4:0):D_800CC2D0+812;
    for(i=0;i<4;i++)*(f32 *)(parent+332+i*4)=i%2?-2.5f:1.25f;
    D_80082FA0=count;D_800C35EA=(u8)active;D_800C3638=173;logCount=allocations=0;phase=flags%3;
    (void)inherit;(void)alias;(void)scale;
}
static int qualify(int flags,int inherit,int count,int active,int alias,int scale){
    union{u32 u;f32 f;} value;u8 *parent;u32 bits=scale?0x7F812345u:0x80000000u;
    int i,j,n;u8 toggle,mode;u8 *returned;
    setup(flags,inherit,count,active,alias,scale);parent=alias?result+(alias==2?4:0):D_800CC2D0+812;
    independent(parent,(s32)0xF1234567u,flags,(s32)0x81820304u,(s32)0x76543210u,flags,inherit,(s32)0xFFEEDDCCu,bits);
    n=logCount;toggle=D_800C3638;mode=D_800C35EA;
    for(i=0;i<8*812;i++)expected[i]=D_800CC2D0[i];
    for(i=0;i<n;i++)for(j=0;j<5;j++)expectedLog[i][j]=logWords[i][j];
    setup(flags,inherit,count,active,alias,scale);parent=alias?result+(alias==2?4:0):D_800CC2D0+812;
    value.u=bits;returned=func_15083AC8(parent,(s32)0xF1234567u,flags,(s32)0x81820304u,
        (s32)0x76543210u,flags,inherit,(s32)0xFFEEDDCCu,value.f);
    if(returned!=result || logCount!=n || D_800C3638!=toggle || D_800C35EA!=mode)return 1;
    for(i=0;i<n;i++)for(j=0;j<5;j++)if(logWords[i][j]!=expectedLog[i][j])return 2;
    for(i=0;i<8*812;i++)if(D_800CC2D0[i]!=expected[i])return 3;
    return 0;
}
int run(void){
    int f,v,n,a,l,s,r;for(f=0;f<256;f++)for(v=0;v<2;v++)for(n=-1;n<=2;n+=n==0?2:1)
        for(a=0;a<2;a++)for(l=0;l<3;l++)for(s=0;s<2;s++){
            r=qualify(f,v,n,a,l,s);if(r)return r;
        }
    return 0;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
