"""Direct child cleanup match, live descriptors, callbacks and linked audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from tools.experiments import game_animation_child_cleanup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed

S = screen.SYMBOLS
STACK, RECORDS, ALTERNATE, CHILD = guest.STACK, 0x24000, 0x26000, 0x28000
COUNTS = dict(func_150302F0=2, func_1505F0AC=1, func_15060F28=2)


def descriptor(animation, symbols=S):
    return (symbols['D_80086CC4'] + (((animation-1)&0xFFFFFFFF)<<3))&0xFFFFFFFF


def quotient(actor, symbols=S):
    delta = signed((actor-symbols['D_800CC2D0'])&0xFFFFFFFF)
    return abs(delta)//812 * (-1 if delta<0 else 1)


def fixture(animation=1, count=3, kind=0, parent=1, records=RECORDS, symbols=S):
    memory = {}
    for start, length in ((STACK-0x500, 0x700), (records, 4096), (ALTERNATE, 4096), (CHILD, 812)):
        for i in range(length): memory.setdefault(start+i, (i*17+35)&255)
    address = descriptor(animation, symbols)
    for i in range(8): memory[address+i] = 0xA5
    put(memory, address, records); put(memory, address+4, count, 1)
    for i in range(256):
        put(memory, records+i*16, i, 1); put(memory, records+i*16+3, kind, 1)
    put(memory, CHILD+0x65, parent, 1)
    return memory


def reference(memory, animation=1, actor=None, lookup=CHILD, symbols=S, phase=0, mutations=None):
    memory = memory.copy(); events, calls = [], []; frame = STACK+phase-48
    actor = symbols['D_800CC2D0'] if actor is None else actor
    occurrence = {name:0 for name in COUNTS}
    def get(where, size=4):
        assert all(where+i in memory for i in range(size)), ('reference unmapped read', where, size)
        value = read(memory, where, size); events.append(('R', where, size, value)); return value
    def store(where, value, size=4):
        assert all(where+i in memory for i in range(size)), ('reference unmapped write', where, size)
        value &= (1<<(size*8))-1; put(memory, where, value, size); events.append(('W', where, size, value))
    def call(name, args):
        target = symbols[name]; calls.append((target, *args)); events.append(('CALL', target, args))
        index = occurrence[name]; occurrence[name] += 1
        for where, value, size in (mutations or {}).get((name,index), ()):
            store(where, value, size)
    for register, offset in ((21,40),(16,20),(31,44),(20,36),(19,32),(18,28),(17,24)):
        store(frame+offset, 0xDEAD0000 if register==31 else 0x5A000000+register)
    call('func_150302F0', (actor&0xFFFFFFFF, animation&0xFFFFFFFF))
    address = descriptor(animation, symbols)
    count = get(address+4, 1); record = get(address); i = 0
    if count:
        while True:
            if get(record+3, 1)==0:
                identity = get(record, 1); call('func_1505F0AC', (identity,))
                child = lookup.get(identity, 0) if isinstance(lookup, dict) else lookup
                if child and quotient(actor, symbols)+1 == get(child+0x65, 1):
                    call('func_15060F28', (child, 0))
            count = get(address+4, 1); i += 1; record = (record+16)&0xFFFFFFFF
            if i>=count: break
            assert i<256, 'unbounded descriptor fixture'
    for offset in (44,20,24,28,32,36,40): get(frame+offset)
    return memory, events, calls


class CleanupOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, animation=1, actor=None, lookup=CHILD,
            symbols=S, phase=0, mutations=None, entry=screen.ENTRY):
        actor = symbols['D_800CC2D0'] if actor is None else actor
        super().__init__(words, memory, arguments=(actor, animation), phase=phase, entry=entry)
        self.lookup, self.symbols, self.mutations = lookup, symbols, mutations or {}
        self.occurrence = {name:0 for name in COUNTS}
    def execute(self, word):
        if word>>26==0 and word&63==27:
            left,right=self.r[word>>21&31],self.r[word>>16&31]
            assert right, 'unsigned negative-control divisor is zero'
            self.lo=left//right
        else:
            super().execute(word)
    def record_call(self, target):
        name = next(n for n in COUNTS if self.symbols[n]==target)
        args = tuple(self.r[4:4+COUNTS[name]])
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
    def hook(self, target):
        name = next(n for n in COUNTS if self.symbols[n]==target)
        index = self.occurrence[name]; self.occurrence[name] += 1
        identity = self.r[4]
        for where, value, size in self.mutations.get((name,index), ()):
            self.put(where, value, size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        if name=='func_1505F0AC':
            self.r[2] = self.lookup.get(identity,0) if isinstance(self.lookup,dict) else self.lookup


class GameAnimationChildCleanupTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-animation-child-cleanup-test'; cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt')
        if not (cls.out/'baseline.json').exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text(); hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes(); (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline = json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.raw = screen.compile_candidate(cls.root,cls.out,'selected')
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.retail = list(struct.unpack_from('>66I',(cls.root/'conker/conker.us.bin').read_bytes(),screen.ROM))
        body = (cls.root/'conker/asm/AEB40.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        slot = cls.out/'slot.s'; slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded',emit_padded_assembly(cls.out/'selected.o',slot,filename='generated_AEB40'))
    @classmethod
    def link(cls,name,symbols=S,entry=screen.ENTRY):
        script = cls.out/('%s-%X.ld'%(name,entry)); elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        return list(struct.unpack_from('>66I',sections(elf)['.text'][1]))
    def receipt(self,name,**values):
        if name=='baseline': raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,forms=None,**settings):
        expected = reference(memory,**{k:v for k,v in settings.items() if k!='entry'})
        models = [CleanupOracle(w,memory,**settings).run() for w in (forms or (self.retail,self.raw))]
        for model in models: self.assertEqual((model.memory,model.events,model.calls),expected)
        self.assertEqual((models[0].r,models[0].f),(models[1].r,models[1].f))
        return models
    def test_01_complete_direct_shape_and_relocations(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(66,48,0,0,''))
        self.assertEqual(self.raw,self.retail)
        for name in ('original','selected','padded'): self.assertEqual(self.link(name),self.retail)
        _,functions,relocations = parse_object(self.out/'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'],264); self.assertEqual(len(relocations),7)
        self.receipt('shape',words=66,frame=48,direct_match=True,new_guards=0,relocations=7,
            independently_assembled_and_actual_padding_exact=True)
    def test_02_independent_domains_signed_slots_and_reachable_words(self):
        cases=0; coverage=set()
        for parent,kind,lookup,phase in itertools.product(range(256),(0,1,2,255),(0,CHILD),(0,8)):
            actor = S['D_800CC2D0']+(parent-1)*812
            memory = fixture(count=2,kind=kind,parent=parent)
            models=self.compare(memory,actor=actor,lookup=lookup,phase=phase)
            coverage.update(models[0].visits); cases+=1
        for delta in (0,1,-1,811,-811,812,-812,813,-813,206220,207032,0x7FFFFFFF,-0x80000000):
            for parent in (0,1,2,254,255):
                actor=(S['D_800CC2D0']+delta)&0xFFFFFFFF
                models=self.compare(fixture(count=1,parent=parent),actor=actor)
                coverage.update(models[0].visits); cases+=1
        for animation,count in itertools.product((0,1,2,255,256,0x80000000,0xFFFFFFFF,0x20000001),(0,1,2,128,255)):
            models=self.compare(fixture(animation,count),animation=animation)
            coverage.update(models[0].visits); cases+=1
        # The constant positive divisor makes only these trap-scaffold words unreachable.
        unreachable={screen.ENTRY+x for x in (0xA0,0xB0,0xB4,0xB8)}
        self.assertEqual(coverage,set(range(screen.ENTRY,screen.ENTRY+264,4))-unreachable)
        self.receipt('guest',cases=cases,executions=cases*2,reached_words=len(coverage),
            unreachable_trap_offsets=sorted(a-screen.ENTRY for a in unreachable),
            all_parent_bytes_types_nulls_full_animation_words_signed_slots=True,
            live_GP_FPR_clobbers_and_saved_registers_checked=True)
    def test_03_mutable_descriptors_record_aliases_and_full_fired_faults(self):
        cases=[]; d=descriptor(1)
        def add(memory,**settings): cases.append((memory,settings))
        add(fixture(count=0))
        for kind,lookup,parent in itertools.product((0,255),(0,CHILD),(0,1)):
            add(fixture(count=3,kind=kind,parent=parent),lookup=lookup)
        add(fixture(count=0),mutations={('func_150302F0',0):((d+4,3,1),)})
        add(fixture(count=3),mutations={('func_150302F0',0):((d+4,0,1),)})
        add(fixture(count=3),mutations={('func_1505F0AC',0):((d+4,0,1),)})
        add(fixture(count=1),mutations={('func_15060F28',0):((d+4,4,1),)})
        add(fixture(count=3),mutations={('func_1505F0AC',0):((CHILD+0x65,0,1),)})
        add(fixture(count=3),mutations={('func_15060F28',0):((d,ALTERNATE,4),(RECORDS+16+3,255,1))})
        memory=fixture(count=3,records=STACK+0x40)
        add(memory,mutations={('func_1505F0AC',0):((STACK+0x40+16,255,1),)})
        # Child parent byte aliases the live descriptor count, then cleanup reduces it.
        memory=fixture(count=2); alias=d+4-0x65
        add(memory,actor=S['D_800CC2D0']+812,lookup=alias,
            mutations={('func_15060F28',0):((d+4,0,1),)})
        memory=fixture(count=0)
        for address in list(memory):
            if RECORDS<=address<RECORDS+4096: del memory[address]
        add(memory)
        faults=0
        for phase in (0,8):
            for memory,settings in cases:
                models=self.compare(memory,phase=phase,**settings)
                for index in range(models[0].accesses):
                    pair=[CleanupOracle(w,memory,phase=phase,**settings) for w in (self.retail,self.raw)]
                    for model in pair:
                        model.fault=index
                        with self.assertRaises(guest.AccessFault): model.run()
                        self.assertEqual(model.accesses,index)
                    self.assertEqual((pair[0].memory,pair[0].events,pair[0].calls),
                        (pair[1].memory,pair[1].events,pair[1].calls)); faults+=1
        self.receipt('aliases',cases=len(cases)*2,executions=len(cases)*4,fired_fault_pairs=faults,
            callback_count_growth_shrink_cached_records_unsigned_parent_private_aliases=True,
            zero_count_skips_unmapped_records=True,bounded_callbacks_not_real_lifetime_acceptance=True)
    def test_04_rebased_tables_JAL_and_signed_low_carries(self):
        cases=0
        for entry,table,actors,reset,lookup,cleanup in (
                (0x15207FF0,0x80117FFC,0x80128004,0x15237FFC,0x15248004,0x15258004),
                (0x15308004,0x80218004,0x80227FFC,0x15348004,0x15357FFC,0x15368004),
                (0x15417FFC,0x80327FFC,0x80338004,0x15457FF0,0x15467FFC,0x15478004)):
            symbols=dict(zip(S,(table,actors,reset,lookup,cleanup)))
            forms=tuple(self.link(n,symbols,entry) for n in ('original','selected','padded'))
            self.assertEqual(forms[0],forms[1]); self.assertEqual(forms[0],forms[2])
            for count,kind,found in ((0,0,CHILD),(3,255,CHILD),(3,0,0),(3,0,CHILD)):
                self.compare(fixture(count=count,kind=kind,symbols=symbols),forms=forms,
                    lookup=found,symbols=symbols,entry=entry); cases+=1
        self.receipt('links',symbol_sets=3,links=9,cases=cases,executions=cases*3,
            two_address_pairs_three_JAL_sites_independently_rebased=True)
    def test_05_actual_copied_owner_and_both_production_padding_routes(self):
        before=(self.out/'before-source').read_text(); objects=[]; warnings=[]
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            obj,diagnostics=compile_owner(self.root,self.out,source,name); warnings.append(diagnostics)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj)
        self.assertEqual(warnings,[[],[]]); parsed=[parse_object(o) for o in objects]
        def fingerprint(data,name):
            text,functions,relocations=data; f=functions[name]; start,end=f['value'],f['value']+f['size']
            return f['size'],text[start:end],{o-start:v for o,v in relocations.items() if start<=o<end}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION: self.assertEqual(fingerprint(parsed[0],name),fingerprint(parsed[1],name),name)
        self.assertEqual(fingerprint(parsed[1],screen.FUNCTION),fingerprint(parse_object(self.out/'selected.o'),screen.FUNCTION))
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for route in ('layout','generated'):
            padded=[]
            for i,obj in enumerate(objects):
                asm=self.out/('owner-%s-%d.s'%(route,i))
                if route=='layout':
                    args=['pad_c_object.py',str(obj),str(self.root/'conker/retail_layout.us.txt'),'generated_AEB40',str(asm)]
                else:
                    args=['pad_generated_object.py',str(obj),str(self.root/'conker/asm/AEB40.s'),str(asm),
                        '--filename','generated_AEB40','--rodata-symbol','jtbl_8009CC40_game']
                subprocess.run(['python3',str(self.root/'tools'/args[0]),*args[1:],
                    '--word-patches',str(self.out/'before-guards')],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                padded.append(parse_object(asm.with_suffix('.o')))
            start=padded[1][1][screen.FUNCTION]['value']; expected=bytearray(padded[0][0])
            expected[start:start+264]=padded[1][0][start:start+264]; self.assertEqual(bytes(expected),padded[1][0])
            self.assertEqual({o:v for o,v in padded[0][2].items() if not start<=o<start+264},
                {o:v for o,v in padded[1][2].items() if not start<=o<start+264})
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,padding_routes=2,
            all_neighbor_bytes_extents_relocations_pools_guard_fingerprints_exact=True)
    def test_06_effective_fresh_compiler_semantic_controls(self):
        d=descriptor(1)
        controls=(
            ('animation','animation--;','animation -= 2;',fixture(),{}),
            ('type','record[3] == 0','record[3] != 0',fixture(),{}),
            ('identity','record[0]','record[1]',fixture(count=1),{'lookup':{0:CHILD}}),
            ('parent','child[0x65]','child[0x64]',fixture(count=1),{}),
            ('slot','/ 0x32C + 1','/ 0x32C + 2',fixture(count=1),{}),
            ('mode','func_15060F28(child, 0)','func_15060F28(child, 1)',fixture(count=1),{}),
            ('stride','record += 16','record += 32',fixture(count=3),{}),
            ('count','i < descriptor->count','i < 1',fixture(count=3),{}),
            ('unsigned','(s32)((u32)actor','(u32)((u32)actor',fixture(count=1,parent=0),
                {'actor':S['D_800CC2D0']-812}))
        def public(memory): return {a:v for a,v in memory.items() if not STACK-0x500<=a<STACK+0x200}
        for name,old,new,memory,settings in controls:
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            self.assertNotEqual(words,self.raw)
            correct=CleanupOracle(self.raw,memory,**settings).run(); wrong=CleanupOracle(words,memory,**settings)
            if name=='animation':
                with self.assertRaisesRegex(AssertionError,'unmapped read'): wrong.run()
            else:
                wrong.run(); self.assertNotEqual((public(correct.memory),correct.calls),(public(wrong.memory),wrong.calls),name)
        dynamic=(
            ('cached-count',screen.SELECTED.replace('    s32 i;','    s32 i;\n    s32 cachedCount;').replace(
                '    i = 0;','    i = 0;\n    cachedCount = descriptor->count;').replace(
                'i < descriptor->count','i < cachedCount'),fixture(count=1),
                {('func_15060F28',0):((d+4,4,1),)}),
            ('reloaded-records',screen.SELECTED.replace('record += 16','record = descriptor->records + (i << 4)'),
                fixture(count=3),{('func_15060F28',0):((d,ALTERNATE,4),)}))
        for name,body,memory,mutations in dynamic:
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            self.assertNotEqual(words,self.raw)
            correct=CleanupOracle(self.raw,memory,mutations=mutations).run()
            wrong=CleanupOracle(words,memory,mutations=mutations).run()
            self.assertNotEqual(correct.calls,wrong.calls,name)
        self.receipt('negative',fresh_IDO_controls=len(controls)+len(dynamic),all_effective=True,
            live_count_and_cached_records_controls_effective=True)
    def test_07_native32_live_counts_cached_records_and_signed_parent(self):
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:],NATIVE_PREFIX+screen.RECORD+NATIVE_TABLE+
                screen.SELECTED+NATIVE_RUNNER,profile)
            self.assertEqual((result,detail),(0,[4096,0,0]))
        bad=screen.SELECTED.replace('child[0x65]','child[0x64]')
        result,_=self.run_native('native-negative',NATIVE_PREFIX+screen.RECORD+NATIVE_TABLE+bad+NATIVE_RUNNER)
        self.assertNotEqual(result,0)
        self.receipt('native',cases_per_profile=4096,executions=8192,profiles=['O2','O0'],
            pointer_integer_descriptor_widths_checked=True,effective_negative=1,
            wrapped_animation_addresses_and_private_faults_guest_only=True)
    def test_08_immutable_baselines_and_whole_linked_installation(self):
        with self.assertRaisesRegex(ValueError,'immutable'): self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name])
            self.receipt('linked',installed=False); return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        expected=bytearray(self.before)
        struct.pack_into('>66I',expected,elf_slot_offset(self.before,screen.ENTRY,264),*self.retail)
        extent=installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12); struct.pack_into('>I',expected,extent,264)
        actual=(self.root/self.paths['elf']).read_bytes(); self.assertEqual(bytes(expected),actual)
        for name in ('guards','progress','rodata','symbols','undefined'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked',installed=True,ELF_bytes=len(actual),ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            only_target_slot_and_12_to_264_symbol_extent_change=True,all_other_ELF_bytes_metadata_exact=True,
            guards_and_conversion_rows_unchanged=True,protected_data=audit)
    def test_09_complete_actual_two_call_actor_reset_caller(self):
        outer_entry,outer_rom,length=0x150634E4,0x90994,35
        rom=(self.root/'conker/conker.us.bin').read_bytes()
        outer=list(struct.unpack_from('>35I',rom,outer_rom))
        self.assertEqual(list(struct.unpack_from('>35I',self.before,
            elf_slot_offset(self.before,outer_entry,length*4))),outer)
        class Connected(CleanupOracle):
            def __init__(model,memory,inner,actor,lookup,phase,mutations):
                super().__init__(outer,memory,actor=actor,lookup=lookup,phase=phase,
                    mutations=mutations,entry=outer_entry)
                model.code.update({screen.ENTRY+i*4:w for i,w in enumerate(inner)})
            def record_call(model,target):
                if target==screen.ENTRY:
                    args=tuple(model.r[4:6]); model.calls.append((target,*args))
                    model.events.append(('CALL',target,args))
                else: super().record_call(target)
        cases=invocations=0
        for slot,path,phase in itertools.product((0,1,127,254),range(4),(0,8)):
            actor=S['D_800CC2D0']+slot*812; state=0x2E000
            memory=fixture(animation=29,count=0 if path==0 else 3,kind=255 if path==1 else 0,parent=slot+1)
            other=descriptor(30)
            for i in range(8): memory[other+i]=0xA5
            put(memory,other,RECORDS); put(memory,other+4,2,1)
            for start,size in ((actor,812),(state,512)):
                for i in range(size): memory[start+i]=0xA5
            put(memory,actor+0x31C,state)
            lookup=0 if path==2 else CHILD
            mutations={('func_15060F28',0):((descriptor(29)+4,1,1),(other+4,3,1))}
            models=[Connected(memory,w,actor,lookup,phase,mutations).run() for w in (self.retail,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r,models[0].f),
                (models[1].memory,models[1].events,models[1].calls,models[1].r,models[1].f))
            self.assertEqual([c[1:] for c in models[0].calls if c[0]==screen.ENTRY],[(actor,29),(actor,30)])
            for offset in (0x78,0x11A): self.assertEqual(read(models[0].memory,state+offset,1),0)
            for offset in (0x8A,0x89,0x83): self.assertEqual(read(models[0].memory,actor+offset,1),0)
            invocations+=2; cases+=1
        self.receipt('connected',complete_actual_caller_words=35,cases=cases,executions=cases*2,
            helper_invocations_per_form=invocations,ordered_two_calls_and_final_actor_state_checked=True,
            deep_reset_lookup_cleanup_callbacks_bounded=True)


NATIVE_PREFIX=r'''
#include <stddef.h>
typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
typedef char widths[(sizeof(void*)==4 && sizeof(s32)==4)?1:-1];
u8 D_800CC2D0[0x40000];
static u8 children[2][812], records[4096], alternate[4096];
static unsigned calls[3], digest, behavior, which;
void func_150302F0(u8 *actor,s32 animation);
u8 *func_1505F0AC(u8 identity);
void func_15060F28(u8 *child,s32 mode);
'''
NATIVE_TABLE=r'''
AnimationDescriptor15083568 D_80086CC4[8];
typedef char descriptor_width[(sizeof(AnimationDescriptor15083568)==8)?1:-1];
void func_150302F0(u8 *actor,s32 animation) {
    calls[0]++; digest=digest*33+(u32)actor+(u32)animation;
    if(behavior==1) D_80086CC4[animation-1].count=3;
}
u8 *func_1505F0AC(u8 identity) {
    calls[1]++; digest=digest*33+identity;
    if(behavior==2) D_80086CC4[0].count=0;
    if(behavior==3) { D_80086CC4[0].records=alternate; records[19]=255; }
    return (identity&1)?NULL:children[which];
}
void func_15060F28(u8 *child,s32 mode) {
    calls[2]++; digest=digest*33+child[101]+(u32)mode;
    if(behavior==4) D_80086CC4[0].count=4;
    if(behavior==5) D_80086CC4[0].count=0;
}
'''
NATIVE_RUNNER=r'''
static void expected(u8 *actor,s32 animation) {
    AnimationDescriptor15083568 *d; u8 *r,*child; unsigned i=0;
    func_150302F0(actor,animation); d=D_80086CC4+animation-1; r=d->records;
    if(!d->count) return;
    do {
        if(!r[3]) {
            child=func_1505F0AC(r[0]);
            if(child && (s32)((u32)actor-(u32)D_800CC2D0)/812+1==child[101]) func_15060F28(child,0);
        }
        ++i; r+=16;
    } while(i<d->count);
}
static u32 results[3];
static int run(void) {
    unsigned slot,path,type,form,i,cases=0; u32 got[2][6];
    for(slot=0;slot<256;slot++) for(path=0;path<8;path++) for(type=0;type<2;type++) {
        u8 *actor=D_800CC2D0+(slot?slot-1:0)*812;
        if(!slot) actor=(u8*)((u32)D_800CC2D0-812);
        for(form=0;form<2;form++) {
            for(i=0;i<4096;i++) records[i]=alternate[i]=(u8)(i*17+35);
            for(i=0;i<256;i++) { records[i*16]=(u8)i; records[i*16+3]=(u8)(type?255:0); }
            for(i=0;i<812;i++) children[form][i]=(u8)(i*31);
            children[form][101]=(u8)slot; which=form;
            D_80086CC4[0].records=records; D_80086CC4[0].count=(u8)(path==0?0:path==6?255:2);
            behavior=path; digest=0; calls[0]=calls[1]=calls[2]=0;
            if(form) expected(actor,1); else func_150836CC(actor,1);
            for(i=0;i<3;i++) got[form][i]=calls[i];
            got[form][3]=digest; got[form][4]=D_80086CC4[0].count; got[form][5]=records[19];
        }
        for(i=0;i<6;i++) if(got[0][i]!=got[1][i]) return 1;
        cases++;
    }
    results[0]=cases; return 0;
}
void _start(void) {
    int result=run();
    __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(results),"d"(12):"memory");
    __asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");
    __builtin_unreachable();
}
'''


if __name__=='__main__': unittest.main()
