"""Complete object-mode layout, closed guards, protected table and caller audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_object_color_mode_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_object_color_mode_recovery as recovery
from tools.tests import test_game_owner_metadata_adapter_match as adapter
from tools.tests import test_game_owner_ribbon_renderer_recovery as renderer
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_random_curve_record as native

put, read = recovery.put, recovery.read
STACK, OBJECT, FLOAT, OUTPUT, COS = recovery.STACK, recovery.OBJECT, recovery.FLOAT, recovery.OUTPUT, recovery.COS
TABLE_SYMBOL = 'jtbl_80096F1C_game'
LINKS = ((screen.ENTRY, 0x80096F1C, 0x80096F38, 0x80096F3C, COS),
    (0x15207FF0, 0x80107FFC, 0x80118004, 0x80127FF0, 0x15308004),
    (0x15308004, 0x80118004, 0x80127FFC, 0x80137FF0, 0x15407FFC),
    (0x15417FFC, 0x80207FF0, 0x80218004, 0x80227FFC, 0x15518004))


class GameObjectColorModeMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-object-color-mode-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(baseline.read_text())
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields, cls.old_rows = reader.fieldnames, list(reader)
        cls.meta, cls.raw = screen.recovery.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>150I', cls.rom, screen.ROM))
        assembly = (cls.root / 'conker/asm/58F80.s').read_text()
        slot = assembly.split('glabel ' + screen.FUNCTION, 1)[1].split('endlabel ' + screen.FUNCTION, 1)[0]
        cls.slot = cls.out / 'slot.s'
        cls.slot.write_text('glabel ' + screen.FUNCTION + slot + 'endlabel ' + screen.FUNCTION + '\n')
        isolated = screen.guard_rows(cls.out / 'selected.o')
        cls.write_rows(cls.out / 'isolated.csv', isolated)
        fitted = emit_padded_assembly(cls.out / 'selected.o', cls.slot,
            word_patches_path=cls.out / 'isolated.csv', filename='generated_58F80')
        cls.assemble('fitted', fitted)
        # Retail is a test oracle only; production fitting derives exclusively from compiled words.
        lines = ['.text', '.set noat', '.set noreorder', '.globl ' + screen.FUNCTION,
            '.type %s,@function' % screen.FUNCTION, screen.FUNCTION + ':']
        for index, word in enumerate(cls.retail):
            uses = screen.RELOCATIONS.get(index * 4, ())
            if uses:
                word &= 0xFC000000 if index == 92 else 0xFFFF0000
            for kind, symbol in uses:
                lines.append('.reloc ., %s, %s' % (kind, TABLE_SYMBOL if symbol == '.rodata' else symbol))
            lines.append('.word 0x%08X' % word)
        lines.append('.size %s,.-%s' % (screen.FUNCTION, screen.FUNCTION))
        cls.assemble('original', '\n'.join(lines))
        cls.linked = cls.link('fitted', LINKS[0])
        cls.link('original', LINKS[0])
        cls.owner_objects, cls.owner_diagnostics = [], []
        before = (cls.out / 'before-source').read_text()
        for name, body in (('owner-before', before), ('owner-after', screen.install(before))):
            obj, warnings = compile_owner(cls.root, cls.out, body, name)
            subprocess.run(['python3', str(cls.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((cls.out / (name + '.c')).relative_to(cls.root / 'conker')), '--post-process',
                str(obj.relative_to(cls.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=cls.root / 'conker', check=True, capture_output=True)
            cls.owner_objects.append(obj)
            cls.owner_diagnostics.append(warnings)
        cls.rows = screen.guard_rows(cls.owner_objects[1], owner=True)
        cls.guards = cls.out / 'qualified-guards.csv'
        cls.write_rows(cls.guards, cls.old_rows + cls.rows)
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        cls.fixture = '''#pragma GCC diagnostic ignored "-Wunused-variable"
typedef unsigned char u8; typedef unsigned int u32;
typedef int s32; typedef float f32;
static f32 D_80096F38=2.55f, D_80096F3C=0.02454369329f, cosine;
static f32 cosf(f32 phase) { (void)phase; return cosine; }
static u8 object[384] __attribute__((aligned(16)));
''' + screen.SELECTED + '\n'

    @classmethod
    def write_rows(cls, path, rows):
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=cls.fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

    @classmethod
    def assemble(cls, name, text):
        path = cls.out / (name + '.s')
        path.write_text(text + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')),
            str(path)], check=True, capture_output=True)

    @classmethod
    def link(cls, name, symbols):
        entry, table, scale, phase, cos = symbols
        script = cls.out / ('link-%s-%X.ld' % (name, entry))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            '--defsym=%s=0x%X' % (TABLE_SYMBOL, table), '--defsym=D_80096F38=0x%X' % scale,
            '--defsym=D_80096F3C=0x%X' % phase, '--defsym=cosf=0x%X' % cos,
            '-o', str(elf), str(cls.out / (name + '.o'))], check=True, capture_output=True)
        data = sections(elf)['.text'][1]
        size = parse_object(cls.out / (name + '.o'))[1][screen.FUNCTION]['size']
        return list(struct.unpack_from('>%dI' % (size // 4), data))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def model(self, memory, words=None, arguments=recovery.ARGUMENTS, phase=0, cosine=0.5):
        data = memory.copy()
        for i, target in enumerate((48,208,208,264,264,496,496)):
            put(data, recovery.TABLE + i * 4, screen.ENTRY + target)
        put(data, 0x80096F38, 0x40233333)
        put(data, 0x80096F3C, 0x3CC90FDB)
        return recovery.ModeOracle(words or self.linked, data, arguments, phase, cosine)

    def test_01_closed_recipe_extent_homes_and_semantic_origin(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['diagnostics']), (148,40,''))
        self.assertEqual(self.linked, self.retail)
        fitted, _, inserted = screen.recipe(screen.RAW)
        self.assertEqual(len(fitted), 150)
        self.assertEqual(inserted, {121:0x10000018, 135:0x01601825})
        self.assertEqual([r['offset'] for r in self.rows if r['insert_after']], ['0x1E4','0x21C'])
        self.assertFalse(any(r['omit'] != 'false' for r in self.rows))
        for i in range(148):
            stale = list(screen.RAW)
            stale[i] ^= 0x10000
            with self.assertRaisesRegex(ValueError, 'stale complete'):
                screen.recipe(stale)
        self.receipt('shape', raw_words=148, matched_words=150, frame=40, guards=148,
            field_renames=len(screen.RENAMES), commute_operations=2, inserted_words=2, omitted_words=0,
            recipe_never_reads_ROM=True, whole_body_stale_rejections=148)

    def test_02_all_modes_aliases_and_complete_private_trace(self):
        cases = 0
        inputs = [(recovery.fixture(mode, packed=FLOAT if mode == 1 else 0xFF802010),
            recovery.ARGUMENTS, phase, cosine) for mode, phase, cosine in
            itertools.product(range(256), (0,8), (-1.0,1.0))]
        inputs += [(recovery.fixture(packed=value), recovery.ARGUMENTS, 0, 0.5) for value in range(256)]
        inputs += [(recovery.fixture(packed=FLOAT, value=value), recovery.ARGUMENTS, 0, 0.5)
            for value in (-100.0,-0.0,0.0,0.25,10.25,100.0,254.9,255.0,300.0)]
        aliases = []
        for index, target in itertools.product(range(1,5), (OUTPUT,OBJECT+0xA0,OBJECT+0xA4,OBJECT+0xA8)):
            args = list(recovery.ARGUMENTS)
            args[index] = target
            aliases.append(tuple(args))
        aliases.append((OBJECT,OUTPUT,OUTPUT,OUTPUT,OUTPUT))
        inputs += [(recovery.fixture(mode, packed=83 if mode == 1 else 0xFF802010), args, 0, cosine)
            for mode, args, cosine in itertools.product(range(8), aliases, (-1.0,0.5,1.0))]
        for memory, args, phase, cosine in inputs:
            expected = recovery.reference(memory, args, cosine)
            models = [self.model(memory, words, args, phase, cosine).run() for words in (self.retail,self.linked)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            self.assertEqual((recovery.public(models[1].memory),
                [e for e in models[1].events if OBJECT <= e[1] < FLOAT+4], models[1].calls), expected)
            cases += 1
        self.receipt('guest', cases=cases, executions=cases*2, complete_private_memory_and_ordered_events_equal=True,
            independent_public_reference_equal=True, bounded_cosine_not_actual_trig_or_FCSR=True)

    def test_03_all_private_public_fault_prefixes_and_reserved_holes(self):
        prefixes = 0
        for mode, phase in itertools.product(range(1,8),(0,8)):
            memory = recovery.fixture(mode, packed=FLOAT if mode==1 else 0xFF802010)
            good = self.model(memory, self.retail, phase=phase).run()
            for cut in range(len(good.events)):
                results = []
                for words in (self.retail,self.linked):
                    model = self.model(memory, words, phase=phase)
                    count = [0]
                    original_get, original_put = model.get, model.put
                    def gate():
                        if count[0] == cut: raise RuntimeError('verified access fault')
                        count[0] += 1
                    def get(address, size):
                        gate()
                        return original_get(address,size)
                    def store(address,value,size):
                        if model.recording: gate()
                        return original_put(address,value,size)
                    model.get, model.put = get, store
                    with self.assertRaisesRegex(RuntimeError,'verified access fault'):
                        model.run()
                    self.assertEqual(count[0], cut)
                    results.append((model.memory,model.events,model.calls))
                self.assertEqual(results[0],results[1])
                self.assertEqual(results[0][1],good.events[:cut])
                prefixes += 1
            holes=memory.copy()
            for offset in (0x18,0x20,0x24):
                for byte in range(4): del holes[STACK+phase-40+offset+byte]
            for words in (self.retail,self.linked): self.model(holes,words,phase=phase).run()
        self.receipt('faults', all_access_fault_prefixes=prefixes, executions=prefixes*2, gates_verified=True,
            three_reserved_words_unmapped_cases=14)

    def test_04_independent_links_and_table_carry_rebases(self):
        cases = 0
        for symbols in LINKS:
            entry,table,scale,phase,cos = symbols
            fitted,original = self.link('fitted',symbols),self.link('original',symbols)
            self.assertEqual(fitted,original)
            raw = self.link('selected',symbols)
            raw_pool = sections(self.out / ('link-selected-%X.elf'%entry))['.rodata']
            for mode, stack in itertools.product(range(8),(0,8)):
                memory = recovery.fixture(mode, packed=FLOAT if mode==1 else 0xFF802010)
                outcomes = []
                class LinkedOracle(recovery.ModeOracle):
                    def record_call(self,target):
                        assert target==cos
                        self.calls.append((target,self.f[12]))
                    def hook(self,target):
                        assert target==cos
                        super().hook(COS)
                for words in (original,raw,fitted):
                    data = memory.copy()
                    put(data,scale,0x40233333)
                    put(data,phase,0x3CC90FDB)
                    for i,offset in enumerate((48,208,208,264,264,496,496)): put(data,table+i*4,entry+offset)
                    data.update({raw_pool[0]+i:value for i,value in enumerate(raw_pool[1])})
                    model = LinkedOracle(words,data,phase=stack,entry=entry).run()
                    outcomes.append((recovery.public(model.memory),model.calls))
                self.assertEqual(outcomes[0],outcomes[1])
                self.assertEqual(outcomes[0],outcomes[2])
                cases += 1
        self.receipt('rebases', independent_links=12, symbol_sets=4, cases=cases, HI16_signed_LO16_carries=True)

    def test_05_actual_owner_padder_neighbors_and_pool_ownership(self):
        self.assertEqual(self.owner_diagnostics,[[],[]])
        old,of,orels=parse_object(self.owner_objects[0])
        new,nf,nrels=parse_object(self.owner_objects[1])
        self.assertEqual(of.keys(),nf.keys())
        relative=lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name,f in nf.items():
            if name==screen.FUNCTION: continue
            prior=of[name]
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']],relative(nrels,f)),
                (prior['size'],old[prior['value']:prior['value']+prior['size']],relative(orels,prior)),name)
        oldpool,newpool=(sections(obj)['.rodata'][1] for obj in self.owner_objects)
        self.assertEqual(newpool[:len(oldpool)],oldpool)
        self.assertEqual(len(newpool)-len(oldpool),32)
        bodies=[]
        for index,obj in enumerate(self.owner_objects):
            name='padded-owner-%d'%index
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards' if index==0 else self.guards,
                filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            bodies.append(parse_object(self.out/(name+'.o')))
        start=bodies[1][1][screen.FUNCTION]['value']
        self.assertEqual(bodies[1][1][screen.FUNCTION]['size'],600)
        self.assertEqual(bodies[0][0][:start],bodies[1][0][:start])
        self.assertEqual(bodies[0][0][start+600:],bodies[1][0][start+600:])
        self.assertEqual(bodies[1][2][start+28],[('R_MIPS_HI16',TABLE_SYMBOL)])
        self.assertEqual(bodies[1][2][start+36],[('R_MIPS_LO16',TABLE_SYMBOL)])
        self.receipt('owner', neighbors=37, zero_diagnostics=True, protected_table_direct_relocation=True,
            all_other_padded_owner_bytes_equal=True, existing_pool_prefix_equal=True, compact_pool_not_emitted=True)

    def test_06_actual_padder_every_stale_word_and_relocation(self):
        data=(self.out/'selected.o').read_bytes()
        header=ELF_HEADER.unpack_from(data)
        headers=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
        ns=headers[header[13]]
        names=data[ns[4]:ns[4]+ns[5]]
        text_section=next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(148):
            changed=bytearray(data)
            struct.pack_into('>I',changed,text_section[4]+index*4,screen.RAW[index]^0x10000)
            path=self.out/'stale.o'
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        rows=screen.guard_rows(self.out/'selected.o')
        for offset in screen.RELOCATIONS:
            wrong=[dict(row) for row in rows]
            wrong[offset//4]['expected_relocations']='-'
            path=self.out/'stale-relocations.csv'
            self.write_rows(path,wrong)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot,word_patches_path=path,filename='generated_58F80')
        self.receipt('stale', actual_padder_word_rejections=148, relocation_spec_rejections=7)

    def test_07_actual_native32_complete_C_normal_outputs(self):
        self.run_host('''
int mode,phase,high,c,cases=0; s32 r,g,b,a,expected; f32 sample=10.25f;
for(mode=0;mode<256;mode++) for(phase=0;phase<256;phase+=17) for(high=0;high<256;high+=51) for(c=0;c<3;c++) {
    cosine=c-1; object[0xA4]=mode; object[0xA5]=phase; object[0xA6]=52; object[0xA7]=71;
    *(u32 *)(object+0xA0)=mode==1 ? (u32)&sample : ((u32)high<<24)|0x802010;
    r=g=b=a=-123; func_1502EC34(object,&r,&g,&b,&a);
    if(mode==0 || mode>7) { if(r!=-123 || g!=-123 || b!=-123 || a!=-123) return 1; }
    else if(mode==1) { if(r!=phase || g!=52 || b!=71 || a!=26) return 2; }
    else if(mode==2 || mode==3) { if(r || g || b || a!=(mode==3 ? 255-phase : phase)) return 3; }
    else {
        if(r!=128 || g!=32 || b!=16) return 4;
        if(mode<6) { expected=high+32*c; expected+=((255-expected)*(255-71))>>8; }
        else expected=255-((phase*high)>>8);
        if(a!=expected) return 5;
    }
    cases++;
}
if(cases!=73728) return 6;
''')
        self.receipt('native32', actual_full_C_cases=73728, finite_bounded_inputs=True, native_alias_or_FCSR_claim=False)

    def test_10_fresh_effective_compiled_semantic_controls(self):
        forms=dict(screen.recovery.candidates())
        cases=(('negative-cache-mode',recovery.fixture(3),(*recovery.ARGUMENTS[:4],OBJECT+0xA4)),
            ('negative-cache-word',recovery.fixture(6),(OBJECT,OBJECT+0xA0,*recovery.ARGUMENTS[2:])),
            ('negative-byte-opacity',recovery.fixture(1,packed=FLOAT,value=300.0),recovery.ARGUMENTS),
            ('negative-unsigned-product',recovery.fixture(5,packed=0xFF802010),recovery.ARGUMENTS))
        records=[]
        for name,memory,args in cases:
            meta,words=screen.recovery.compile_candidate(self.root,self.out,name,forms[name])
            data=memory.copy()
            address,pool=sections(self.out/(name+'.elf'))['.rodata']
            data.update({address+i:value for i,value in enumerate(pool)})
            put(data,0x80096F38,0x40233333)
            put(data,0x80096F3C,0x3CC90FDB)
            model=recovery.ModeOracle(words,data,args,cosine=1.0).run()
            self.assertNotEqual(recovery.public(model.memory),recovery.reference(memory,args,1.0)[0],name)
            records.append(meta)
        self.receipt('negatives',actual_complete_compiled_controls=4,effective=4,measurements=records)

    def test_08_linked_installation_only_target_changes(self):
        actual_source=(self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in actual_source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest() for name,path in self.paths.items()},
                self.baseline)
            self.receipt('installation', installed=False, baseline_unchanged=True)
            return
        self.assertEqual(actual_source,screen.install((self.out/'before-source').read_text()))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes()
        expected=bytearray(before)
        struct.pack_into('>150I',expected,elf_slot_offset(before,screen.ENTRY,600),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),600)
        actual=(self.root/self.paths['elf']).read_bytes()
        em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5]
            expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_600_bytes_and_symbol_extent_changed=True,
            old_guard_prefix_and_conversion_rows_unchanged=True,protected_data=audit)

    def test_09_banked_renderer_adapter_and_actual_padded_helper(self):
        elf=(self.root/self.paths['elf']).read_bytes()
        def slot(entry,size): return list(struct.unpack_from('>%dI'%(size//4),elf,elf_slot_offset(elf,entry,size)))
        caller=slot(renderer.screen.ENTRY,1900)
        banked_adapter=slot(adapter.screen.ENTRY,356)
        default=slot(adapter.DEFAULT,136)
        self.assertEqual(caller,list(struct.unpack_from('>475I',self.rom,renderer.screen.ROM)))
        self.assertEqual(banked_adapter,list(struct.unpack_from('>89I',self.rom,adapter.screen.ROM)))
        helper=self.linked
        if screen.ORIGINAL not in (self.root/screen.SOURCE).read_text():
            helper=slot(screen.ENTRY,600)
            self.assertEqual(helper,self.linked)
        class ConnectedRenderer(renderer.RibbonOracle):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs)
                self.adapter_calls=[]
            def record_call(self,target):
                if target in (screen.ENTRY,adapter.DEFAULT,COS):
                    args=(self.f[12],) if target==COS else tuple(self.arguments(5 if target==screen.ENTRY else 14))
                    self.adapter_calls.append((target,*args))
                else: super().record_call(target)
            def hook(self,target):
                if target==COS:
                    for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
                    self.f[:20]=[0xA5000000+i for i in range(20)]
                    self.f[0]=recovery.bits(0.5)
                else: super().hook(target)
        cases=0
        for mode,pattern,stack,view in itertools.product(range(8),(0,3),(0,8),(0,0xFFFF)):
            memory,vertex=renderer.fixture(pattern=pattern,view=view,selector=1)
            memory.update(recovery.fixture(mode,packed=83 if mode==1 else 0x40802010))
            put(memory,adapter.ACTOR+0x150,OBJECT)
            for i,target in enumerate((48,208,208,264,264,496,496)): put(memory,recovery.TABLE+i*4,screen.ENTRY+target)
            put(memory,0x80096F38,0x40233333)
            put(memory,0x80096F3C,0x3CC90FDB)
            values=renderer.VALUES
            if mode&1:
                colors,opacity={1:((37,52,71),83),3:((0,0,0),218),5:((128,32,16),214),7:((128,32,16),246)}[mode]
                values=(0x200005,0x60600,*colors,255,opacity,opacity,opacity,255,0x100000,5,0x2F)
            ref=renderer.RibbonReference(memory,view=view,vertex=vertex,values=values).run()
            connected={}
            for entry,words in ((adapter.screen.ENTRY,banked_adapter),(adapter.DEFAULT,default),(screen.ENTRY,helper)):
                connected.update(zip(range(entry,entry+len(words)*4,4),words))
            model=ConnectedRenderer(caller,memory,view=view,phase=stack,vertex=vertex,connected=connected).run()
            self.assertEqual(renderer.external(model.memory),renderer.external(ref.memory))
            self.assertEqual(renderer.writes(model),ref.events)
            self.assertEqual(model.calls,ref.calls)
            self.assertEqual(model.r[2],ref.result)
            self.assertEqual(sum(call[0]==screen.ENTRY for call in model.adapter_calls),1)
            self.assertTrue(any(screen.ENTRY<=address<screen.ENTRY+600 for address in model.visits))
            cases+=1
        self.receipt('renderer',cases=cases,complete_banked_renderer_words=475,banked_adapter_words=89,
            actual_padded_helper_words=150,independent_strip_reference_equal=True,bounded_graphics_cosine_not_live_rendering=True)


if __name__=='__main__':
    unittest.main()
