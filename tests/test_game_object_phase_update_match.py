"""Full wrapping leaf, alias/order, owner-pool and installation qualification."""
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

from tools.experiments import game_object_phase_update_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_object_color_mode_match as color
from tools.tests import test_game_actor_update_dispatch_match as dispatch
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests import test_game_random_curve_record as native
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.game_owner_pool import normalized_pools

OBJECT, TICK, TABLE, STACK = 0x22000, 0x800BE9E4, 0x80096F04, color.STACK
TICKS = (0,1,2,25,26,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x10000001)
LINKS = ((screen.ENTRY,TABLE,TICK), (0x15207FF0,0x80107FFC,0x80118004),
    (0x15308004,0x80118004,0x80127FFC), (0x15417FFC,0x80207FF0,0x80218004))


def fixture(mode=5, phase=37, rate=52, blend=71, tick=1, object_address=OBJECT, tick_address=TICK):
    memory = {STACK+i:0xA5 for i in range(-0x100,0x80)}
    memory.update({object_address+i:(i*17+0x35)&255 for i in range(-16,0x180)})
    put(memory,tick_address,tick)
    for offset,value in ((0xA4,mode),(0xA5,phase),(0xA6,rate),(0xA7,blend)):
        put(memory,object_address+offset,value,1)
    return memory


def reference(memory, object_address=OBJECT, tick_address=TICK):
    result, events = memory.copy(), []
    def get(address,size=4):
        value = read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(offset,value):
        put(result,object_address+offset,value,1)
        events.append(('W',object_address+offset,1,value&255))
    def product():
        tick = get(tick_address)
        rate = get(object_address+0xA6,1)
        phase = get(object_address+0xA5,1)
        return signed(tick*rate&0xFFFFFFFF),phase
    mode = get(object_address+0xA4,1)
    if mode in (2,3):
        delta,phase = product()
        store(0xA5,phase-delta if delta<phase else 0)
    elif mode in (4,5):
        if mode==5:
            tick = get(tick_address)
            blend = get(object_address+0xA7,1)
            delta = signed(tick*10&0xFFFFFFFF)
            store(0xA7,blend-delta) if delta<blend else store(0xA4,0)
        delta,phase = product()
        store(0xA5,phase+delta)
    elif mode==6:
        delta,phase = product()
        store(0xA5,phase+delta if phase<signed((255-delta)&0xFFFFFFFF) else 255)
        store(0xA4,7)
    elif mode==7:
        delta,phase = product()
        store(0xA5,phase-delta) if delta<phase else store(0xA4,0)
    return result,events


class PhaseOracle(TriangleOracle):
    def __init__(self,words,memory,object_address=OBJECT,entry=screen.ENTRY,phase=0,connected=None,arguments=None):
        super().__init__(words,memory,entry=entry,phase=phase,connected=connected,
            arguments=(object_address,) if arguments is None else arguments)
    def get(self,address,size):
        assert all(address+i in self.memory for i in range(size)), ('unmapped read',address,size)
        return super().get(address,size)
    def put(self,address,value,size):
        if self.recording:
            assert all(address+i in self.memory for i in range(size)), ('unmapped store',address,size)
        super().put(address,value,size)
    def record_call(self,target):
        raise AssertionError(('unexpected leaf call',target))


class GameObjectPhaseUpdateMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host
    write_rows = classmethod(color.GameObjectColorModeMatchTests.write_rows.__func__)
    assemble = classmethod(color.GameObjectColorModeMatchTests.assemble.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-object-phase-update-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        baseline = cls.out/'baseline.json'
        if not baseline.exists():
            hashes = {}
            for name,path in cls.paths.items():
                data = (cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline = json.loads(baseline.read_text())
        with (cls.out/'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields,cls.old_rows = reader.fieldnames,list(reader)
        cls.meta,cls.raw = screen.recovery.compile_candidate(cls.root,cls.out,'selected')
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>78I',cls.rom,screen.ROM))
        cls.table = struct.unpack_from('>6I',cls.rom,0x23B9C4)
        assembly = (cls.root/'conker/asm/58F80.s').read_text()
        slot = assembly.split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.slot = cls.out/'slot.s'
        cls.slot.write_text('glabel '+screen.FUNCTION+slot+'endlabel '+screen.FUNCTION+'\n')
        cls.write_rows(cls.out/'isolated.csv',screen.guard_rows(cls.out/'selected.o'))
        fitted = emit_padded_assembly(cls.out/'selected.o',cls.slot,
            word_patches_path=cls.out/'isolated.csv',filename='generated_58F80')
        cls.assemble('fitted',fitted)
        # The retail body is used only as an independent test oracle.
        relocs,shift = {},0
        for index in range(75):
            if index*4 in screen.RELOCATIONS:
                relocs[(index+shift)*4] = screen.RELOCATIONS[index*4]
            if index in (22,49,60): shift += 1
        lines = ['.text','.set noat','.set noreorder','.globl '+screen.FUNCTION,
            '.type %s,@function'%screen.FUNCTION,screen.FUNCTION+':']
        for index,word in enumerate(cls.retail):
            uses = relocs.get(index*4,())
            if uses: word &= 0xFFFF0000
            for kind,symbol in uses:
                lines.append('.reloc ., %s, %s'%(kind,screen.TABLE if symbol=='.rodata' else symbol))
            lines.append('.word 0x%08X'%word)
        lines.append('.size %s,.-%s'%(screen.FUNCTION,screen.FUNCTION))
        cls.assemble('original','\n'.join(lines))
        cls.linked = cls.link('fitted',LINKS[0])
        cls.owner_objects,cls.owner_diagnostics = [],[]
        before = (cls.out/'before-source').read_text()
        for name,body in (('owner-before',before),('owner-after',screen.install(before))):
            obj,warnings = compile_owner(cls.root,cls.out,body,name)
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/(name+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=cls.root/'conker',check=True,capture_output=True)
            cls.owner_objects.append(obj)
            cls.owner_diagnostics.append(warnings)
        cls.rows = screen.guard_rows(cls.owner_objects[1],owner=True)
        cls.qualified_rows = screen.requalify_color(cls.owner_objects[1],cls.old_rows)+cls.rows
        cls.guards = cls.out/'qualified-guards.csv'
        cls.write_rows(cls.guards,cls.qualified_rows)
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        cls.fixture = ('typedef unsigned char u8; typedef unsigned int u32; typedef int s32;\n'
            'static s32 D_800BE9E4; static u8 object[384];\n'+screen.SELECTED+'\n')

    @classmethod
    def link(cls,name,symbols):
        entry,table,tick = symbols
        script = cls.out/('link-%s-%X.ld'%(name,entry))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=%s=0x%X'%(screen.TABLE,table),'--defsym=D_800BE9E4=0x%X'%tick,
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        data = sections(elf)['.text'][1]
        size = parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']
        return list(struct.unpack_from('>%dI'%(size//4),data))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def model(self,memory,words=None,object_address=OBJECT,phase=0,entry=screen.ENTRY,table=TABLE,pool=None):
        data = memory.copy()
        for i,offset in enumerate((40,40,144,96,180,256)): put(data,table+i*4,entry+offset)
        if pool:
            address,body = pool
            data.update({address+i:value for i,value in enumerate(body)})
        return PhaseOracle(words or self.linked,data,object_address,entry,phase)

    def compare(self,memory,object_address=OBJECT):
        expected,events = reference(memory,object_address)
        models = [self.model(memory,words,object_address).run() for words in (self.retail,self.linked)]
        self.assertEqual((models[0].memory,models[0].events),(models[1].memory,models[1].events))
        pool = sections(self.out/'selected.elf')['.rodata']
        models.append(self.model(memory,self.raw,object_address,pool=pool).run())
        for model in models:
            self.assertEqual({a:model.memory[a] for a in memory},expected)
            self.assertEqual([e for e in model.events if e[1] in memory],events)
        return models

    def test_01_closed_shape_words_and_stale_producers(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['diagnostics']),(75,0,''))
        self.assertEqual(self.linked,self.retail)
        self.assertEqual(tuple(t-screen.ENTRY for t in self.table),(40,40,144,96,180,256))
        fitted,replacements,inserted = screen.recipe(screen.RAW)
        self.assertEqual((len(fitted),inserted),(78,{22:0,49:0x240B00FF,60:0}))
        self.assertFalse(any(row['omit']!='false' for row in self.rows))
        for index in range(75):
            stale = list(screen.RAW)
            stale[index] ^= 0x10000
            with self.assertRaisesRegex(ValueError,'stale complete'): screen.recipe(stale)
        self.receipt('shape',raw_words=75,matched_words=78,frame=0,guards=75,insertions=3,omissions=0,
            changed_words=sum(a!=b for a,b in zip(screen.RAW,replacements)),ROM_not_read_by_recipe=True)

    def test_02_modes_wrapping_signed_products_aliases_and_order(self):
        cases,coverage = 0,set()
        inputs = [(fixture(mode,tick=tick),OBJECT) for mode,tick in itertools.product(range(256),TICKS)]
        inputs += [(fixture(mode,phase,rate,tick=tick),OBJECT)
            for mode,phase,rate,tick in itertools.product(range(2,8),(0,1,37,254,255),(0,1,10,52,255),TICKS)]
        inputs += [(fixture(mode,phase,rate,blend,tick,object_address=TICK-offset),TICK-offset)
            for mode,phase,rate,blend,tick,offset in itertools.product(range(2,8),(0,37,255),(0,52,255),
                (0,71,255),(1,256,0xFFFFFFFF),(0xA1,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7))]
        for memory,address in inputs:
            models = self.compare(memory,address)
            coverage.update(models[0].visits)
            cases += 1
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=len(coverage),
            signed_low32_product=True,fresh_tick_alias_order=True,raw_C_public_accesses_equal=True,
            fitted_complete_memory_and_access_order_equal=True)

    def test_03_all_verified_access_fault_prefixes(self):
        prefixes = 0
        for mode,tick in itertools.product(range(8),(0,1,26,0xFFFFFFFF)):
            memory = fixture(mode,tick=tick)
            good = self.model(memory,self.retail).run()
            for cut in range(len(good.events)):
                results = []
                for words in (self.retail,self.linked):
                    model = self.model(memory,words)
                    count = [0]
                    get,store = model.get,model.put
                    def gate():
                        if count[0]==cut: raise RuntimeError('verified access fault')
                        count[0] += 1
                    def read_gate(address,size):
                        gate()
                        return get(address,size)
                    def write_gate(address,value,size):
                        if model.recording: gate()
                        return store(address,value,size)
                    model.get,model.put = read_gate,write_gate
                    with self.assertRaisesRegex(RuntimeError,'verified access fault'): model.run()
                    self.assertEqual(count[0],cut)
                    results.append((model.memory,model.events))
                self.assertEqual(results[0],results[1])
                self.assertEqual(results[0][1],good.events[:cut])
                prefixes += 1
        self.receipt('faults',prefixes=prefixes,executions=prefixes*2,gates_verified=True,portable_C_fault_claim=False)

    def test_04_relocation_carry_rebases(self):
        cases = 0
        for symbols in LINKS:
            entry,table,tick = symbols
            fitted,original = self.link('fitted',symbols),self.link('original',symbols)
            self.assertEqual(fitted,original)
            raw = self.link('selected',symbols)
            pool = sections(self.out/('link-selected-%X.elf'%entry))['.rodata']
            for mode,phase in itertools.product(range(8),(0,8)):
                memory = fixture(mode,tick=0xFFFFFFFF,tick_address=tick)
                expected,events = reference(memory,tick_address=tick)
                for words,p in ((original,None),(fitted,None),(raw,pool)):
                    model = self.model(memory,words,phase=phase,entry=entry,table=table,pool=p).run()
                    self.assertEqual({a:model.memory[a] for a in memory},expected)
                    self.assertEqual([e for e in model.events if e[1] in memory],events)
                cases += 1
        self.receipt('rebases',links=12,symbol_sets=4,cases=cases,signed_LO16_carries=True)

    def test_05_copied_owner_only_phase_and_one_color_addend(self):
        self.assertEqual(self.owner_diagnostics,[[],[]])
        old,of,orels = parse_object(self.owner_objects[0])
        new,nf,nrels = parse_object(self.owner_objects[1])
        self.assertEqual(of.keys(),nf.keys())
        relative = lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name,f in nf.items():
            if name==screen.FUNCTION: continue
            prior = of[name]
            expected = bytearray(old[prior['value']:prior['value']+prior['size']])
            if name==screen.color.FUNCTION:
                self.assertEqual(struct.unpack_from('>I',expected,36)[0],0x8C2F0100)
                struct.pack_into('>I',expected,36,0x8C2F0118)
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']],relative(nrels,f)),
                (prior['size'],bytes(expected),relative(orels,prior)),name)
        before,after = (normalized_pools(obj) for obj in self.owner_objects)
        self.assertEqual(before['.data'],after['.data'])
        ob,oi = before['.rodata']; nb,ni = after['.rodata']
        self.assertEqual(len(nb)-len(ob),32)
        self.assertEqual(nb[:256],ob[:256])
        self.assertEqual(nb[280:308],ob[256:284])
        self.assertEqual(nb[308:],bytes(12))
        self.assertEqual(ob[284:],bytes(4))
        preserved = tuple((offset-24 if offset>=280 else offset,name,rel)
            for offset,name,rel in ni if name!=screen.FUNCTION)
        self.assertEqual(preserved,oi)
        self.assertEqual(len([entry for entry in ni if entry[1]==screen.FUNCTION]),6)
        bodies = []
        for i,obj in enumerate(self.owner_objects):
            name = 'padded-owner-%d'%i
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards' if i==0 else self.guards,
                filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            bodies.append(parse_object(self.out/(name+'.o')))
        start = bodies[1][1][screen.FUNCTION]['value']
        self.assertEqual(bodies[1][1][screen.FUNCTION]['size'],312)
        self.assertEqual(bodies[0][0][:start],bodies[1][0][:start])
        self.assertEqual(bodies[0][0][start+312:],bodies[1][0][start+312:])
        self.assertEqual(bodies[1][2][start+20],[('R_MIPS_HI16',screen.TABLE)])
        self.assertEqual(bodies[1][2][start+28],[('R_MIPS_LO16',screen.TABLE)])
        differences = [(a,b) for a,b in zip(self.old_rows,self.qualified_rows) if a!=b]
        self.assertEqual(len(differences),1)
        a,b = differences[0]
        self.assertEqual({k:v for k,v in a.items() if k!='expected'},
            {k:v for k,v in b.items() if k!='expected'})
        self.receipt('owner',neighbors=len(nf)-1,compiler_diagnostics=0,color_only_expected_addend_change=True,
            all_other_padded_bytes_equal=True,prior_pools_preserved_by_relocation_ownership=True,new_pool_bytes=32)

    def test_06_actual_padder_stale_words_and_relocations(self):
        data = (self.out/'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(data)
        headers = [SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
        ns = headers[header[13]]; names = data[ns[4]:ns[4]+ns[5]]
        ts = next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for i in range(75):
            changed = bytearray(data)
            struct.pack_into('>I',changed,ts[4]+i*4,screen.RAW[i]^0x10000)
            path = self.out/'stale.o'; path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        rows = screen.guard_rows(self.out/'selected.o')
        for offset in screen.RELOCATIONS:
            wrong = [dict(row) for row in rows]
            wrong[offset//4]['expected_relocations'] = '-'
            path = self.out/'stale-relocations.csv'; self.write_rows(path,wrong)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot,word_patches_path=path,filename='generated_58F80')
        self.receipt('stale',actual_padder_word_rejections=75,relocation_rejections=12)

    def test_07_actual_native32_complete_C(self):
        self.run_host('''
static u32 ticks[]={0,1,2,25,26,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x10000001};
int mode,phase,rate,t,cases=0; u8 wantedMode,wantedPhase,wantedBlend; s32 delta;
for(mode=0;mode<256;mode++) for(phase=0;phase<256;phase+=17) for(rate=0;rate<256;rate+=17) for(t=0;t<11;t++) {
    object[0xA4]=wantedMode=mode; object[0xA5]=wantedPhase=phase;
    object[0xA6]=rate; object[0xA7]=wantedBlend=71; D_800BE9E4=ticks[t];
    delta=(u32)rate*ticks[t];
    if(mode==2 || mode==3) wantedPhase=delta<phase ? (u32)phase-(u32)delta : 0;
    else if(mode==4) wantedPhase=(u32)phase+(u32)delta;
    else if(mode==5) {
        s32 fade=ticks[t]*10u;
        if(fade<71) wantedBlend=71u-(u32)fade; else wantedMode=0;
        wantedPhase=(u32)phase+(u32)delta;
    } else if(mode==6) {
        wantedPhase=phase<(s32)(255u-(u32)delta) ? (u32)phase+(u32)delta : 255;
        wantedMode=7;
    } else if(mode==7) {
        if(delta<phase) wantedPhase=(u32)phase-(u32)delta; else wantedMode=0;
    }
    func_1502EAFC(object);
    if(object[0xA4]!=wantedMode || object[0xA5]!=wantedPhase || object[0xA6]!=rate || object[0xA7]!=wantedBlend) return 1;
    cases++;
}
if(cases!=720896) return 2;
''')
        self.receipt('native32',complete_C_cases=720896,wrapping_products=True,native_big_endian_alias_claim=False)

    def test_08_fresh_effective_compiled_negative_controls(self):
        forms = dict(screen.recovery.candidates())
        cases = (('negative-cache-tick',fixture(5,tick=256,object_address=TICK-0xA1),TICK-0xA1),
            ('negative-unsigned-compare',fixture(2,tick=0xFFFFFFFF),OBJECT),
            ('negative-clear-phase',fixture(7,tick=26),OBJECT),
            ('negative-no-fallthrough',fixture(5),OBJECT),
            ('negative-mode6-gate',fixture(6,phase=253,rate=1),OBJECT))
        records = []
        for name,memory,address in cases:
            meta,words = screen.recovery.compile_candidate(self.root,self.out,name,forms[name])
            pool = sections(self.out/(name+'.elf'))['.rodata']
            model = self.model(memory,words,address,pool=pool).run()
            self.assertTrue(any(model.memory[a]!=value for a,value in reference(memory,address)[0].items()),name)
            records.append(meta)
        self.receipt('negatives',compiled_complete_controls=5,effective=5,measurements=records)

    def test_09_actual_dispatcher_gate_and_connected_leaf(self):
        elf = (self.root/self.paths['elf']).read_bytes()
        caller = list(struct.unpack_from('>88I',elf,elf_slot_offset(elf,dispatch.ENTRY,352)))
        self.assertEqual(caller,list(struct.unpack_from('>88I',self.rom,0x59234)))
        helper = self.linked
        if screen.ORIGINAL not in (self.root/screen.SOURCE).read_text():
            helper = list(struct.unpack_from('>78I',elf,elf_slot_offset(elf,screen.ENTRY,312)))
            self.assertEqual(helper,self.linked)
        class Connected(PhaseOracle):
            def record_call(self,target):
                args = self.arguments(dispatch.COUNTS[target])
                self.calls.append((target,*args))
                self.events.append(('CALL',target,args))
            def hook(self,target):
                dispatch.DispatchOracle.hook(self,target)
        cases,hits = 0,0
        for mode,active,state,tick in itertools.product(range(8),(0,1),(0,5),(1,0xFFFFFFFF)):
            memory = dispatch.memory_case(state=state,active=active,signal=mode)
            put(memory,TICK,tick)
            for offset,value in ((0xA5,37),(0xA6,52),(0xA7,71)):
                put(memory,dispatch.ACTOR+offset,value,1)
            for i,offset in enumerate((40,40,144,96,180,256)): put(memory,TABLE+i*4,screen.ENTRY+offset)
            models = []
            for words in (self.retail,helper):
                connected = dict(zip(range(screen.ENTRY,screen.ENTRY+312,4),words))
                model = Connected(caller,memory,entry=dispatch.ENTRY,arguments=(dispatch.ACTOR,0),connected=connected)
                model.work,model.actions = 0,{}
                models.append(model.run())
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            calls = [call for call in models[1].calls if call[0]==screen.ENTRY]
            self.assertEqual(len(calls),int(bool(active and mode and state!=5)))
            self.assertEqual(any(screen.ENTRY<=pc<screen.ENTRY+312 for pc in models[1].visits),bool(calls))
            if calls:
                self.assertEqual(calls,[(screen.ENTRY,dispatch.ACTOR)])
                expected,_ = reference(memory,dispatch.ACTOR)
                for offset in (0xA4,0xA5,0xA6,0xA7):
                    self.assertEqual(models[1].memory[dispatch.ACTOR+offset],expected[dispatch.ACTOR+offset])
                hits += 1
            cases += 1
        self.receipt('connected',cases=cases,leaf_gate_hits=hits,banked_dispatcher_words=88,actual_leaf_words=78,
            bounded_other_callbacks_not_gameplay_acceptance=True)

    def test_10_linked_installation_only_target_changes(self):
        source = (self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
                for name,path in self.paths.items()},self.baseline)
            self.receipt('installation',installed=False,baseline_unchanged=True)
            return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.qualified_rows)
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before = (self.out/'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>78I',expected,elf_slot_offset(before,screen.ENTRY,312),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),312)
        actual = (self.root/self.paths['elf']).read_bytes()
        em,am = metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length = section[4],section[5]
            expected[offset:offset+length] = actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit = audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_312_bytes_and_symbol_extent_changed=True,
            old_guard_one_expected_field_requalified=True,conversion_rows_unchanged=True,protected_data=audit)


if __name__=='__main__':
    unittest.main()
