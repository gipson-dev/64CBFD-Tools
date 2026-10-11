"""Qualify the complete allocated vertex-coordinate pair copy and owner split."""
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

from tools.experiments import game_record_pair_copy_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_command_weight_counter_match as counter
from tools.tests import test_game_main_resource_loader as main
from tools.tests import test_game_resource_preparation_match as preparation
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools


STACK, SOURCE, TABLE, ALTERNATE, OUTPUT = guest.STACK, 0x70000, 0x72000, 0x74000, 0x76000
LINKS = [(entry, {name:address for name,address in zip(screen.SYMBOLS,
    (0x80107FFC+carry, 0x80118004-carry, 0x80207FF0+carry, 0x10018004+carry))})
    for entry, carry in itertools.product((screen.ENTRY, 0x15207FFC, 0x15318004), (0, 8, 0x10000))]
LINKS[0] = (screen.ENTRY, screen.SYMBOLS)


def slot(symbols, name, identity):
    return (symbols[name]+(identity&0xFFFFFFFF)*4)&0xFFFFFFFF


def fixture(identity=36, present=False, offset=0, symbols=screen.SYMBOLS, pattern=0, destination=OUTPUT):
    memory = {STACK+i:0xA5 for i in range(-0x600, 0x100)}
    for base, length in ((SOURCE, 0x1000), (ALTERNATE, 0x1000), (OUTPUT, 0x800), (TABLE, 32)):
        memory.update({base+i:(i*137+pattern*31+19)&255 for i in range(length)})
    for name in ('D_800C6360', 'D_800D19A0', 'D_800C4020'):
        address = slot(symbols, name, identity)
        memory.update({address+i:0xA5 for i in range(0x180)})
    if destination not in (0, OUTPUT):
        for i in range(384): memory.setdefault((destination+i)&0xFFFFFFFF, 0xA5)
    put(memory, slot(symbols, 'D_800C6360', identity), OUTPUT if present else 0)
    put(memory, slot(symbols, 'D_800D19A0', identity), SOURCE+0x100)
    put(memory, slot(symbols, 'D_800C4020', identity), TABLE)
    put(memory, TABLE, offset)
    return memory


class PairOracle(guest.AttachmentOracle):
    def __init__(self, words, memory, identity=36, result=OUTPUT, actions=(),
            phase=0, entry=screen.ENTRY, symbols=screen.SYMBOLS, unused=(0, 0, 0)):
        super().__init__(words, memory, arguments=(identity&0xFFFFFFFF, *unused), phase=phase, entry=entry)
        self.result, self.actions, self.symbols = result, actions, symbols
    def record_call(self, target):
        assert target == self.symbols['allocate_memory']
        args = tuple(self.r[4:8])
        self.calls.append((target, *args)); self.events.append(('CALL', target, args))
    def hook(self, target):
        assert target == self.symbols['allocate_memory']
        for address, value, size in self.actions: self.put(address, value, size)
        main.extras_module.clobber(self, self.result)


class Reference:
    def __init__(self, memory, symbols=screen.SYMBOLS, result=OUTPUT, actions=()):
        self.memory, self.events, self.calls = memory.copy(), [], []
        self.symbols, self.result, self.actions = symbols, result, actions
    def get(self, address, size=4):
        assert all((address+i)&0xFFFFFFFF in self.memory for i in range(size))
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value)); return value
    def put(self, address, value, size=4):
        assert all((address+i)&0xFFFFFFFF in self.memory for i in range(size))
        put(self.memory, address, value, size)
        self.events.append(('W', address, size, value&((1<<(size*8))-1)))
    def run(self, identity=36):
        if identity&0xFFFFFFFF != 36: return 0
        target = slot(self.symbols, 'D_800C6360', identity)
        if self.get(target): return 0
        base = self.get(slot(self.symbols, 'D_800D19A0', identity))
        table = self.get(slot(self.symbols, 'D_800C4020', identity))
        source = (base+(self.get(table)<<4))&0xFFFFFFFF
        allocate = self.symbols['allocate_memory']
        self.calls.append((allocate, 376, 1, 0, 2)); self.events.append(('CALL', allocate, (376, 1, 0, 2)))
        for address, value, size in self.actions: self.put(address, value, size)
        self.put(target, self.result)
        if not self.result: return 1
        destination = self.get(target)
        for index in range(94):
            for component in (0, 1):
                value = self.get((source+index*16+8+component*2)&0xFFFFFFFF, 2)
                self.put((destination+index*4+component*2)&0xFFFFFFFF, value, 2)
        return 0


class GameRecordPairCopyMatchTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-record-pair-copy-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt', makefile='conker/Makefile')
        manifest = cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2)+'\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['source'] == screen.COUNTER_SOURCE_SHA
        assert cls.baseline['elf'] == 'b714ed2f171bce3917539e59a91ae6ee1f1571f2e9665dc495f7ec579133a01b'
        assert cls.baseline['guards'] == screen.COUNTER_GUARDS_SHA
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest() == cls.baseline[name]
        cls.before = (cls.out/'before-elf').read_bytes()
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>96I', cls.rom, screen.ROM))
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        _, funcs, rel = parse_object(cls.out/'selected.o')
        start = funcs[screen.FUNCTION]['value']
        for offset in screen.PAIRS: assert not rel.get(start+offset)
        cls.guards = cls.out/'qualified-guards.csv'
        cls.guards.write_bytes((cls.out/'before-guards').read_bytes()+screen.guard_suffix())
        cls.only = cls.out/'only-guards.csv'
        cls.only.write_text((cls.out/'before-guards').read_text().splitlines()[0]+'\n'+screen.guard_suffix().decode('ascii'))
        body = (cls.root/'conker/asm/6A3D0.s').read_text().split('glabel '+screen.FUNCTION, 1)[1].split(
            'endlabel '+screen.FUNCTION, 1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+screen.FUNCTION+body+'endlabel '+screen.FUNCTION+'\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+
            '\n.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+body+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.assemble('padded', emit_padded_assembly(cls.out/'selected.o', cls.slot,
            word_patches_path=cls.only, filename='generated_6A3D0'))

    def receipt(self, name, **values):
        (self.out/(name+'.json')).write_text(json.dumps(values, indent=2)+'\n')
    def link(self, name, entry=screen.ENTRY, symbols=screen.SYMBOLS):
        script = self.out/'rebase.ld'
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        words = parse_object(self.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%words, sections(elf)['.text'][1]))
    @property
    def padded(self):
        if not hasattr(type(self), '_padded_words'): type(self)._padded_words = self.link('padded')
        return type(self)._padded_words
    def compare(self, memory, symbols=screen.SYMBOLS, identity=36, forms=None, result=OUTPUT, actions=(), **settings):
        reference = Reference(memory, symbols, result, actions)
        value = reference.run(identity)
        expected = preparation.public(reference.memory), preparation.events(reference.events), reference.calls, value
        models = [PairOracle(words, memory, identity=identity, symbols=symbols, result=result,
            actions=actions, **settings).run() for words in (forms or (self.retail, self.raw, self.padded))]
        for model in models:
            self.assertEqual((preparation.public(model.memory), preparation.events(model.events), model.calls, model.r[2]), expected)
        return models

    def test_01_complete_guarded_slot_and_closed_spill_shape(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (96, 64, 4))
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual(screen.normalized(self.raw, self.retail), self.retail)
        self.assertEqual(self.link('original'), self.retail)
        self.assertEqual(self.padded, self.retail)
        self.assertEqual(self.retail[0], 0x27BDFFC8)
        self.assertEqual(tuple(i*4 for i,(a,b) in enumerate(zip(self.raw,self.retail)) if a != b), tuple(screen.PAIRS))
        self.receipt('shape', words=96, raw_frame=64, retail_frame=56, directly_exact_words=92,
            expected_word_empty_relocation_guards=4, all_control_flow_load_store_widths_and_unroll_exact=True,
            guarded_not_direct_C_match=True)

    def test_02_identity_gate_present_failure_and_payloads(self):
        cases, reached = 0, set()
        for identity, present, failed, pattern, phase in itertools.product(
                (0, 35, 36, 37, 186, 187, 255, -1, 256, 0x80000000, 0x7FFFFFFF),
                (False, True), (False, True), range(4), (0, 8)):
            memory = fixture(identity, present, pattern=pattern)
            models = self.compare(memory, identity=identity, result=0 if failed else OUTPUT, phase=phase)
            for model in models:
                reached.update(model.visits)
                if identity != 36: self.assertEqual(preparation.events(model.events), [])
                if identity == 36 and present: self.assertEqual(model.calls, [])
            cases += 1
        self.receipt('guest', cases=cases, forms=3, reached_words=len(reached&set(range(screen.ENTRY,screen.ENTRY+384,4))),
            only_identity_36_reads_tables=True, present_no_allocator_and_failure_publishes_null=True,
            full_public_memory_access_call_order_and_status_reference=True,
            dead_kind_minus_one_and_variable_count_paths_not_claimed_reachable=True)

    def test_03_cached_inputs_live_callback_data_and_alias_order(self):
        cases = 0
        destinations = (OUTPUT, SOURCE+0x100, SOURCE+0x108, SOURCE+0x10A, SOURCE+0x110,
            slot(screen.SYMBOLS,'D_800C6360',36), slot(screen.SYMBOLS,'D_800D19A0',36), TABLE)
        for destination, offset, phase in itertools.product(destinations, (0, 1, 7, 0xFFFFFFFF, 0x80000000), (0, 8)):
            memory = fixture(offset=offset, destination=destination)
            self.compare(memory, result=destination, phase=phase); cases += 1
        for phase in (0, 8):
            memory = fixture(offset=1)
            actions = ((slot(screen.SYMBOLS,'D_800D19A0',36), ALTERNATE, 4),
                (slot(screen.SYMBOLS,'D_800C4020',36), TABLE+4, 4), (TABLE, 9, 4),
                (slot(screen.SYMBOLS,'D_800C6360',36), ALTERNATE, 4),
                (SOURCE+0x118, 0x8001, 2), (SOURCE+0x11A, 0xFFFF, 2))
            self.compare(memory, actions=actions, phase=phase); cases += 1
        self.receipt('aliases', cases=cases, signed_half_pairs_and_16_4_byte_strides=True,
            cached_source_and_index_live_payloads_and_overwritten_publication=True,
            source_table_and_publication_aliases_preserve_sequential_read_store_order=True,
            wrapped_offsets_are_mapped_guest_fixtures_not_portable_C_acceptance=True)

    def test_04_independent_HI_LO_and_call_rebases(self):
        cases = 0
        for entry, symbols in LINKS:
            forms = [self.link(name,entry,symbols) for name in ('original','selected','padded')]
            self.assertEqual(forms[0], forms[2])
            self.assertEqual(screen.normalized(forms[1],forms[0]), forms[0])
            for identity, failed, unused, phase in itertools.product((7,36), (False,True),
                    ((0,0,0),(0xDEADBEEF,0x80000000,0xFFFFFFFF)), (0,8)):
                self.compare(fixture(identity=identity,symbols=symbols), symbols, identity, forms,
                    result=0 if failed else OUTPUT, entry=entry, unused=unused, phase=phase); cases += 1
        self.receipt('rebases', links=len(LINKS), cases=cases, three_independent_globals_and_allocator=True,
            HI16_LO16_carries_and_JAL_target_rebases=True, unused_A1_A2_A3_ignored=True)

    def test_05_every_private_and_public_fault_prefix(self):
        pairs = 0
        for identity, present, result, phase in ((7,False,OUTPUT,0), (36,True,OUTPUT,8),
                (36,False,0,0), (36,False,OUTPUT,0), (36,False,SOURCE+0x10A,8)):
            memory = fixture(identity,present,destination=result)
            complete = PairOracle(self.retail,memory,identity=identity,result=result,phase=phase).run()
            for ordinal in range(complete.accesses):
                models = [PairOracle(words,memory,identity=identity,result=result,phase=phase)
                    for words in (self.retail,self.padded)]
                for model in models:
                    model.fault = ordinal
                    with self.assertRaises(guest.AccessFault): model.run()
                    self.assertEqual(model.accesses,ordinal)
                self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r),
                    (models[1].memory,models[1].events,models[1].calls,models[1].r)); pairs += 1
        self.receipt('faults', fired_original_padded_pairs=pairs,
            every_private_and_public_access_partial_memory_calls_registers_exact=True,
            raw_C_private_faults_not_claimed=True, guest_model_not_hardware=True)

    def test_06_effective_compiled_semantics_and_stale_install_controls(self):
        controls = (('identity','identity == 0x24','identity == 0x25',36,OUTPUT),
            ('count','count = 94','count = 93',36,OUTPUT),
            ('kind','kind = 0','kind = 1',36,OUTPUT),
            ('allocation','count * 4, 1, 0, 2','count * 4, 1, 1, 2',36,OUTPUT),
            ('source-first','v.tc[0]','v.ob[0]',36,OUTPUT),
            ('source-second','v.tc[1]','v.ob[1]',36,OUTPUT),
            ('output-first','output[index].s','output[index].t',36,OUTPUT),
            ('failure','return 1;','return 2;',36,0))
        for name,before,after,identity,result in controls:
            body = screen.QUALIFIED.replace(before,after)
            self.assertNotEqual(body,screen.QUALIFIED)
            _,words = screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            with self.assertRaises(AssertionError): self.compare(fixture(),identity=identity,result=result,forms=(words,))
        before = (self.out/'before-source').read_text()
        for wrong in (before.replace(screen.ORIGINAL,''),before+screen.ORIGINAL,
                before.replace('s32 func_1503D804();','s32 func_1503D804(s32);')):
            with self.assertRaises(ValueError): screen.install(wrong)
        with self.assertRaises(ValueError): screen.install_makefile(screen.install_makefile((self.out/'before-makefile').read_text()))
        self.receipt('controls', effective_compiled_semantic_mutations=len(controls), stale_source_rejections=3,
            duplicate_recipe_rejected=True)

    def test_07_complete_owner_both_padders_and_mixed_profile_selection(self):
        before = (self.out/'before-source').read_text()
        run, objects = subprocess.run, []
        def compile_run(command,*args,**kwargs):
            if str(command[0]).endswith('/cc'): command = list(command)+['-Wo,-loopunroll,0']
            return run(command,*args,**kwargs)
        for name,source in (('owner-before',before),('owner-after',screen.install(before))):
            with patch('subprocess.run',side_effect=compile_run): obj,diagnostics = compile_owner(self.root,self.out,source,name)
            self.assertEqual(diagnostics,[]); objects.append(obj)
        alternate,diagnostics = compile_owner(self.root,self.out,screen.install(before),'owner-unrolled')
        self.assertEqual(diagnostics,[])
        def fingerprint(obj,name):
            text,functions,relocations = parse_object(obj); info = functions[name]
            start,end = info['value'],info['value']+info['size']
            return info['size'],text[start:end],{o-start:v for o,v in relocations.items() if start<=o<end}
        names = set(parse_object(objects[0])[1]); self.assertEqual(names,set(parse_object(objects[1])[1]))
        for name in names-{screen.FUNCTION}: self.assertEqual(fingerprint(objects[0],name),fingerprint(objects[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(alternate))
        self.assertEqual(fingerprint(alternate,screen.FUNCTION),fingerprint(self.out/'selected.o',screen.FUNCTION))
        routes = []
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed = []
            for index,obj in enumerate(objects):
                asm = self.out/('owner-'+route+'-'+str(index)+'.s')
                args = [str(obj),str(self.out/'before-layout'),'generated_6A3D0',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.root/'conker/asm/6A3D0.s'),str(asm),'--filename','generated_6A3D0']
                args += ['--word-patches',str(self.guards if index else self.out/'before-guards')]
                if index: args += ['--function-object',screen.FUNCTION+'='+str(alternate)]
                subprocess.run(['python3',str(self.root/'tools'/route),*args],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
                if index:
                    wrong = subprocess.run(['python3',str(self.root/'tools'/route),*args[:-2]],capture_output=True,text=True)
                    self.assertNotEqual(wrong.returncode,0)
            start = parsed[1][1][screen.FUNCTION]['value']; expected = bytearray(parsed[0][0])
            expected[start:start+384] = parsed[1][0][start:start+384]; self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:v for o,v in parsed[0][2].items() if not start<=o<start+384},
                {o:v for o,v in parsed[1][2].items() if not start<=o<start+384})
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        makefile = self.out/'mixed-profile.mk'
        makefile.write_text(screen.install_makefile((self.out/'before-makefile').read_text()))
        dry = subprocess.run(['make','-C','conker','-f',str(makefile),'-n','-B',
            'build/src/game/generated_6A3D0.c.o'],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(dry.returncode,0,dry.stdout+dry.stderr)
        compiles = [line for line in dry.stdout.splitlines() if ' -c -32 ' in line]
        self.assertEqual(len(compiles),2)
        self.assertIn('-Wo,-loopunroll,0',compiles[0]); self.assertNotIn('-Wo,-loopunroll,0',compiles[1])
        self.assertIn('--function-object func_1503D804=',dry.stdout)
        self.assertNotIn('generated_6A3D0.c.o\' given more than once',dry.stderr)
        self.receipt('owner', neighbors=len(names)-1, actual_padders=2, diagnostics=0,
            other_bytes_extents_relocations_pools_and_typed_parent_unchanged=True,
            only_target_selected_from_unrolled_owner=True, omitted_selector_rejected_by_both_routes=True)

    def test_08_immutable_whole_ELF_guard_and_recipe_installation_audit(self):
        for name in self.paths: self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        before_source = (self.out/'before-source').read_text(); source = (self.root/screen.SOURCE).read_text()
        installed_now = source != before_source
        self.assertEqual(source,screen.install(before_source) if installed_now else before_source)
        actual = (self.root/self.paths['elf']).read_bytes(); expected = bytearray(self.before)
        start = elf_slot_offset(self.before,screen.ENTRY,384)
        extent = installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I',self.before,extent)[0],12)
        if installed_now:
            struct.pack_into('>96I',expected,start,*self.retail); struct.pack_into('>I',expected,extent,384)
        self.assertEqual(bytes(expected),actual)
        for name,path in self.paths.items():
            if name in ('source','elf'): continue
            data = (self.out/('before-'+name)).read_bytes()
            if installed_now and name == 'guards': data += screen.guard_suffix()
            if installed_now and name == 'makefile': data = screen.install_makefile(data.decode('ascii')).encode('ascii')
            self.assertEqual((self.root/path).read_bytes(),data,name)
        audit = audit_layout(self.root/self.paths['elf'],self.root/'conker'); self.assertTrue(audit['exact'],audit)
        self.receipt('linked', installed=installed_now, ELF_sha256=hashlib.sha256(actual).hexdigest(),
            changed_ELF_bytes=sum(a!=b for a,b in zip(self.before,actual)),
            changed_target_bytes=sum(a!=b for a,b in zip(self.before[start:start+384],actual[start:start+384])),
            changed_extent_bytes=sum(a!=b for a,b in zip(self.before[extent:extent+4],actual[extent:extent+4])),
            all_other_ELF_bytes_metadata_data_and_conversion_inputs_exact=True,
            guard_prefix_exact_only_four_rows_and_exact_mixed_recipe_change=True, protected_data=audit)

    def test_09_native32_complete_C_aliases_callbacks_and_all_halfword_values(self):
        for profile in ('-O2','-O0'):
            code,detail = self.run_native('native-'+profile[1:],NATIVE+screen.QUALIFIED+NATIVE_MAIN,profile)
            self.assertEqual((code,detail),(0,''),(profile,code,detail))
        code,_ = self.run_native('native-negative',NATIVE+screen.QUALIFIED.replace('v.tc[1]','v.ob[1]')+NATIVE_MAIN)
        self.assertNotEqual(code,0)
        self.receipt('native', profiles=['O2','O0'], cases_per_profile=66896,
            all_65536_halfword_values_and_256_valid_identities=True,
            cached_inputs_callback_mutations_overlap_order_full_arrays_and_slots=True,
            effective_second_coordinate_control=True, native32_no_strict_aliasing_not_64_bit_host=True)

    def test_10_all_guard_word_and_relocation_corruptions_fail_closed(self):
        rows = list(csv.DictReader(io.StringIO(self.guards.read_text())))
        fields = list(rows[0]); prefix = len(rows)-4; attempts = 0
        for index in range(prefix,len(rows)):
            for field,value,message in (('expected','0x%08X'%(int(rows[index]['expected'],0)^1),'stale word patch'),
                    ('expected_relocations','R_MIPS_HI16:D_800D19A0','stale relocations')):
                altered = [dict(row) for row in rows]; altered[index][field] = value
                stale = self.out/'stale-guards.csv'
                with stale.open('w',newline='') as stream:
                    writer = csv.DictWriter(stream,fieldnames=fields,lineterminator='\n'); writer.writeheader(); writer.writerows(altered)
                with self.assertRaisesRegex(ValueError,message): emit_padded_assembly(self.out/'selected.o',self.slot,
                    word_patches_path=stale,filename='generated_6A3D0')
                result = subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(self.out/'owner-after.o'),
                    str(self.out/'before-layout'),'generated_6A3D0',str(self.out/'stale.s'),
                    '--function-object',screen.FUNCTION+'='+str(self.out/'owner-unrolled.o'),
                    '--word-patches',str(stale)],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0); self.assertIn(message,result.stdout+result.stderr); attempts += 2
        self.receipt('stale-guards', guards=4, actual_padders=2, fired_rejections=attempts,
            every_expected_word_and_relocation_changed_and_rejected=True)

    def test_11_exact_historical_projection_with_effective_source_word_extent_and_guard_rejections(self):
        before_source = (self.out/'before-source').read_text(); qualified = screen.install(before_source)
        source_path,elf_path,guard_path = (self.root/self.paths[name] for name in ('source','elf','guards'))
        read_text,read_bytes = Path.read_text,Path.read_bytes
        start = elf_slot_offset(self.before,screen.ENTRY,384)
        extent = installed.symbol_size_offset(self.before,screen.FUNCTION,screen.ENTRY)
        current = bytearray(self.before); struct.pack_into('>96I',current,start,*self.retail); struct.pack_into('>I',current,extent,384)
        def sources(body): return patch.object(Path,'read_text',lambda p,*a,**kw: body if p==source_path else read_text(p,*a,**kw))
        def binaries(data,guards=None):
            return patch.object(Path,'read_bytes',lambda p: bytes(data) if p==elf_path else
                self.guards.read_bytes() if p==guard_path and guards is None else guards if p==guard_path else read_bytes(p))
        with sources(qualified),binaries(current):
            self.assertEqual(screen.counter_source(self.root),before_source)
            self.assertEqual(screen.counter_elf(self.root,self.before),self.before)
            self.assertEqual(screen.counter_guards(self.root),(self.out/'before-guards').read_bytes())
        for wrong in (qualified.replace('count = 94','count = 93'),qualified.replace('s32 func_1503D804(s32);','s32 func_1503D804();'),
                qualified.replace('s32 allocate_memory(s32, s32, s32, s32);','void *allocate_memory(s32, s32, s32, s32);'),qualified+'\n'):
            with sources(wrong),self.assertRaises(AssertionError): screen.counter_source(self.root)
        for offset in (start+4,extent+3):
            wrong = current.copy(); wrong[offset] ^= 1
            with sources(qualified),binaries(wrong),self.assertRaises(AssertionError): screen.counter_elf(self.root,self.before)
        for wrong in (self.guards.read_bytes()+b'\n',self.guards.read_bytes()[:-1],
                self.guards.read_bytes().replace(b'0x27BDFFC0',b'0x27BDFFC1',1)):
            with sources(qualified),binaries(current,wrong),self.assertRaises(AssertionError): screen.counter_guards(self.root)
        wrong,expected = current.copy(),bytearray(self.before); wrong[start+384] ^= 1; expected[start+384] ^= 1
        with sources(qualified),binaries(wrong): self.assertEqual(screen.counter_elf(self.root,self.before),bytes(expected))
        self.receipt('historical', source_rejections=4, word_extent_rejections=2, guard_rejections=3,
            exact_body_prototype_declaration_slot_extent_suffix_only=True,
            unrelated_ELF_bytes_preserved_for_whole_ELF_rejection=True, immutable_baselines_not_refreshed=True)

    def test_12_actual_eight_body_loader_chain_noop_copy_and_failure(self):
        buffers = main.extras_module.buffers
        old_oracle,old_reference,old_fixture,old_buffers,old_helper = (
            main.MainOracle,main.Reference,main.fixture,buffers.fixture,buffers.helper)
        old_outer_run = preparation.Reference.run
        pair_words,reached = self.padded,set()
        class WithPairs(old_oracle):
            def __init__(model,*args,**kwargs):
                connected = dict(kwargs.get('connected') or {})
                connected.update({screen.ENTRY+i*4:w for i,w in enumerate(pair_words)})
                kwargs['connected'] = connected
                model.pair_failed = bool((kwargs.get('results') or {}).get('secondary'))
                super().__init__(*args,**kwargs)
            def run(model):
                if model.entry == preparation.screen.ENTRY: model.r[5] = identity
                value = super().run(); reached.update(model.visits&set(range(screen.ENTRY,screen.ENTRY+384,4)))
                return value
        class WithReference(old_reference):
            def call(model,role,*args):
                if role != 'secondary': return super().call(role,*args)
                target = main.S[main.ROLES[role]]
                model.calls.append((target,*args)); model.events.append(('CALL',target,args))
                child = Reference(model.memory,result=0 if model.results.get('secondary') else OUTPUT)
                value = child.run(args[0]); model.memory = child.memory
                model.events.extend(child.events); model.calls.extend(child.calls); return value
        def with_allocator(model,target,args):
            if target == buffers.ALLOCATE and args == (376,1,0,2):
                return 0 if model.pair_failed else OUTPUT
            return old_helper(model,target,args)
        saved = self.retail,self.raw
        self.retail = self.raw = list(struct.unpack_from('>46I',self.rom,counter.screen.ROM))
        try:
            for identity in (7,36):
                def with_outer_identity(model,*args,**kwargs):
                    kwargs.setdefault('identity',identity)
                    return old_outer_run(model,*args,**kwargs)
                def with_inputs(*args,**kwargs):
                    kwargs.setdefault('identity',identity)
                    return old_buffers(*args,**kwargs)
                def with_records(*args,**kwargs):
                    kwargs.setdefault('identity',identity)
                    memory = old_fixture(*args,**kwargs)
                    for base,size in ((main.BLOCK+0x38,0x900),(OUTPUT,400)):
                        memory.update({base+i:(i*137+19)&255 for i in range(size)})
                    put(memory,main.BLOCK+0x78,1); put(memory,main.BLOCK+0xB8,1)
                    put(memory,main.address('D_800C6360',identity),0)
                    count_slot = counter.slot(counter.screen.SYMBOLS,'D_800C5918',identity)
                    memory.update({count_slot+i:0xA5 for i in range(2)})
                    return memory
                with patch.object(main,'MainOracle',WithPairs),patch.object(main,'Reference',WithReference), \
                        patch.object(main,'fixture',with_records),patch.object(buffers,'fixture',with_inputs), \
                        patch.object(buffers,'helper',with_allocator),patch.object(preparation.Reference,'run',with_outer_identity):
                    counter.GameCommandWeightCounterMatchTests.test_10_actual_seven_body_loader_chain_with_counter(self)
        finally:
            self.retail,self.raw = saved
        self.assertGreater(len(reached),80)
        self.receipt('pair-chain', cases=1536, identities=[7,36], reached_pair_words=len(reached),
            actual_104_274_52_46_96_56_9_194_word_bodies=True,
            secondary_hook_replaced_by_actual_guarded_body=True,
            secondary_failure_flag_now_drives_real_allocator_null_and_return_one=True,
            deeper_allocator_copy_free_auxiliary_hardware_runtime_still_bounded=True)


NATIVE = r'''#define NULL ((void *)0)
typedef unsigned char u8;typedef short s16;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
typedef struct {s16 ob[3];u16 flag;s16 tc[2];u8 cn[4];} Vtx_t;
typedef union {Vtx_t v;long long force_structure_alignment;} Vtx;
u8 *D_800C6360[256],*D_800D19A0[256];u32 D_800C4020[256];
static u32 source[512] __attribute__((aligned(16))),other[512] __attribute__((aligned(16))),destination[256],table[8];
static u32 es[512],eo[512],ed[256],et[8];
static int identity,mode,fail,alias,offset,calls,error;static u32 returned;
s32 func_1503D804(s32);
s32 allocate_memory(s32 size,s32 align,s32 pool,s32 kind) {
    calls++;if(size!=376 || align!=1 || pool!=0 || kind!=2) error=1;
    if(mode==1) D_800D19A0[36]=(u8 *)other;
    if(mode==2) {D_800C4020[36]=(u32)(table+1);table[0]=11;}
    if(mode==3) {D_800C6360[36]=(u8 *)other;((u16 *)source)[offset*8+4]=0x8001;((u16 *)source)[offset*8+5]=0xFFFF;}
    return fail?0:(s32)returned;
}
static int check(int id,int present,int failed,int record,int action,int overlap,u32 pattern) {
    int i,c;u32 value;u8 *target;u8 *expected;int active=id==36 && !present;
    identity=id;mode=action;fail=failed;alias=overlap;offset=record;calls=error=0;
    for(i=0;i<512;i++) source[i]=es[i]=(u32)i*0x12345U+pattern*0x314159U+0xA180FF01U;
    for(i=0;i<512;i++) other[i]=eo[i]=(u32)i*0x54321U+pattern*17U+0xDEADBEEFU;
    for(i=0;i<256;i++) destination[i]=ed[i]=0xA5000000U+(u32)i;
    for(i=0;i<8;i++) table[i]=et[i]=(u32)record+(u32)i;
    ((u16 *)source)[record*8+4]=((u16 *)es)[record*8+4]=(u16)pattern;
    ((u16 *)source)[record*8+5]=((u16 *)es)[record*8+5]=(u16)(pattern^0x8000U);
    for(i=0;i<256;i++) {D_800C6360[i]=NULL;D_800D19A0[i]=(u8 *)source;D_800C4020[i]=(u32)table;}
    if(id>=0 && id<256) D_800C6360[id]=present?(u8 *)destination:NULL;
    target=overlap?(u8 *)source+record*16+(overlap==1?0:overlap==2?8:overlap==3?10:16):(u8 *)destination;
    returned=(u32)target;
    value=(u32)func_1503D804(id);
    if(value!=(active && failed?1U:0U) || calls!=active || error) return 1;
    if(active && mode==2) et[0]=11;
    if(active && mode==3) {((u16 *)es)[record*8+4]=0x8001;((u16 *)es)[record*8+5]=0xFFFF;}
    expected=overlap?(u8 *)es+record*16+(overlap==1?0:overlap==2?8:overlap==3?10:16):(u8 *)ed;
    if(active && !failed) for(i=0;i<94;i++) for(c=0;c<2;c++)
        *(u16 *)(expected+i*4+c*2)=*(u16 *)((u8 *)es+record*16+i*16+8+c*2);
    for(i=0;i<256;i++) {
        u8 *published=i==id && present?(u8 *)destination:NULL;
        if(i==36 && active) published=failed?NULL:target;
        if(D_800C6360[i]!=published || D_800D19A0[i]!=(active && i==36 && mode==1?(u8 *)other:(u8 *)source) ||
            D_800C4020[i]!=(u32)(active && i==36 && mode==2?table+1:table)) return 2;
    }
    for(i=0;i<512;i++) if(source[i]!=es[i] || other[i]!=eo[i]) return 3;
    for(i=0;i<256;i++) if(destination[i]!=ed[i]) return 4;
    for(i=0;i<8;i++) if(table[i]!=et[i]) return 5;
    return 0;
}
'''
NATIVE_MAIN = r'''
static int run(void) {
    static int invalid[]={-1,256,0x7FFFFFFF,(int)0x80000000U};
    int id,p,f,o,m,a,r;u32 value;
    if(sizeof(Vtx)!=16 || (u32)&((Vtx *)0)->v.tc[0]!=8 || (u32)&((Vtx *)0)->v.tc[1]!=10) return 9;
    for(value=0;value<65536U;value++) {r=check(36,0,0,0,0,0,value);if(r)return r;}
    for(id=0;id<256;id++) for(p=0;p<2;p++) for(f=0;f<2;f++) {r=check(id,p,f,1,3,0,(u32)id);if(r)return r;}
    for(p=0;p<2;p++) for(f=0;f<2;f++) for(o=0;o<4;o++) for(m=0;m<4;m++) for(a=0;a<5;a++)
        {r=check(36,p,f,o,m,a,0x80FFU+(u32)o);if(r)return r;}
    for(id=0;id<4;id++) for(p=0;p<2;p++) for(f=0;f<2;f++)
        {r=check(invalid[id],p,f,0,3,0,0xFFFF);if(r)return r;}
    return 0;
}
void _start(void) {int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''


if __name__ == '__main__':
    unittest.main()
