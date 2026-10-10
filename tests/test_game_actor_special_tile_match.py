"""Actual special helper, complete updater connections, native C and two-slot linked audit."""
import csv
import hashlib
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_special_tile_candidates as screen
from tools.experiments import game_actor_tile_updater_matching as tile
from tools.experiments import game_actor_renderer_connected as chain
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_tile_updater_recovery as proof
from tools.tests import test_game_actor_tile_updater_match as schedule
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.tests import test_game_actor_alpha_shading_match as floating
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_dual_matrix_emitter import sdk_macro
from tools.tests.test_game_row_destination_fill import START

PAIRS = ((0,0),(1,1),(0,1),(1,0),(-1,3),(31,10),(-77,-23),
    (16777217,16777216),(-2147483648,-2147483648),(2147483647,2147483647))
PREVIOUS = (-1024,-1,0,2,3,66,1024)


def fixture(kind=0x89, numerator=31, denominator=10, previous=66, slot=0):
    memory = proof.fixture(kind,slot=slot)
    actor = proof.actor_address(slot)
    for offset,value in ((0x2E4,numerator),(0x2E8,denominator),(0x2EC,previous)):
        proof.guest.put(memory,actor+offset,value)
    return memory


def helper_reference(memory, commands, actor):
    state,events = memory.copy(),[]
    def get(address):
        value=proof.guest.read(state,address,4)
        events.append(('R',address,4,value));return value
    def put(address,value):
        value &= 0xFFFFFFFF
        proof.guest.put(state,address,value)
        events.append(('W',address,4,value))
    denominator=signed(get(actor+0x2E8))
    ratio=floating.divide(floating.rounded(float(signed(get(actor+0x2E4)))),
        floating.rounded(float(denominator))) if denominator else 1.0
    value=floating.rounded(floating.rounded(500.0*floating.rounded(1.0-ratio))+2.0)
    if not math.isfinite(value) or not -2147483648 <= math.trunc(value) <= 2147483647:
        raise ValueError('unqualified float conversion')
    coordinate=math.trunc(value)
    previous=signed((2-get(actor+0x2EC))&0xFFFFFFFF)
    quotient=(abs(coordinate)//3)*(-1 if coordinate<0 else 1)
    put(actor+0x2EC,quotient)
    if previous<0:previous+=((-previous+63)//64)*64
    put(commands,0xF2000000|((coordinate&4095)<<12)|(previous&4095))
    put(commands+4,0x041FE03E)
    return (commands+8)&0xFFFFFFFF,state,events


def reference(memory,commands=proof.OUTPUT,slot=0):
    actor=proof.actor_address(slot);kind=proof.guest.read(memory,actor+4,1)
    if kind not in (0x89,0xBA):return proof.reference(memory,commands,slot)
    returned,state,events=helper_reference(memory,commands,actor)
    call=('CALL',screen.ENTRY,(commands,actor))
    return returned,state,[('R',actor+4,1,kind),call,*events],[call]


class SpecialInstructions:
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            value=floating.floating(self.f[word>>11&31])
            assert math.isfinite(value) and -2147483648<=math.trunc(value)<=2147483647,\
                'unqualified float conversion'
            self.f[word>>6&31]=math.trunc(value)&0xFFFFFFFF
        else:super().execute(word)


class HelperOracle(SpecialInstructions,proof.guest.AttachmentOracle):
    def __init__(self,words,memory,commands,actor,phase=0,entry=screen.ENTRY):
        super().__init__(words,memory,entry=entry,arguments=(commands,actor),phase=phase)


class ActualTileOracle(SpecialInstructions,proof.TileOracle):
    def __init__(self,words,memory,helper,slot=0,commands=proof.OUTPUT,phase=0,
            entry=tile.ENTRY,special=screen.ENTRY):
        connected={special+i*4:word for i,word in enumerate(helper)}
        proof.guest.AttachmentOracle.__init__(self,words,memory,entry=entry,
            arguments=(commands,slot),phase=phase,connected=connected)

    def hook(self,target):
        raise AssertionError(('actual special helper cannot be modeled',target))


class ActualConnected(SpecialInstructions,proof.TileConnected):
    def hook(self,target):
        assert target!=screen.ENTRY,'actual special helper cannot be modeled'
        return super().hook(target)


class GameActorSpecialTileMatchTests(unittest.TestCase):
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-special-tile-test';cls.out.mkdir(exist_ok=True)
        cls.previous=cls.root/'conker/build/game-actor-tile-updater-test'
        cls.paths=dict(source=tile.SOURCE,special=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            old=json.loads((cls.previous/'baseline.json').read_text())
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                if name!='special':
                    assert hashlib.sha256(data).hexdigest()==old[name],name
                    assert data==(cls.previous/('before-'+name)).read_bytes(),name
                else:assert screen.ORIGINAL in data.decode()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        for name in cls.paths:
            assert hashlib.sha256((cls.out/('before-'+name)).read_bytes()).hexdigest()==cls.baseline[name]
        cls.meta,cls.helper=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.original=list(struct.unpack_from('>52I',cls.rom,screen.ROM))
        schedule.GameActorTileUpdaterMatchTests.setUpClass()
        cls.tile_forms=schedule.GameActorTileUpdaterMatchTests.forms
        cls.rows=schedule.GameActorTileUpdaterMatchTests.rows

    def receipt(self,name,**values):
        if name=='baseline':raise ValueError('immutable baseline is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,slot=0,commands=proof.OUTPUT,phase=0):
        returned,state,events,calls=reference(memory,commands,slot)
        models=[ActualTileOracle(words,memory,self.helper,slot,commands,phase).run()
            for words in self.tile_forms]
        for model in models:
            self.assertEqual(model.r[2],returned)
            self.assertEqual({a:v for a,v in model.memory.items() if proof.public(a)},
                {a:v for a,v in state.items() if proof.public(a)})
            self.assertEqual([e for e in model.events if e[0]=='CALL' or proof.public(e[1])],
                [e for e in events if e[0]=='CALL' or proof.public(e[1])])
            self.assertEqual(model.calls,calls)
            self.assertEqual(bytes(model.memory[commands+i] for i in range(16)),
                bytes(state[commands+i] for i in range(16)))
        for model in models[1:]:
            for name in ('memory','events','calls','accesses'):
                self.assertEqual(getattr(models[0],name),getattr(model,name),name)
        return models

    def test_01_direct_C_and_complete_actual_special_paths(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(52,0,0,0,''))
        self.assertEqual(self.helper,self.original)
        coverage=set();cases=0
        for kind,slot,pair,previous,phase in itertools.product((0x89,0xBA),proof.SLOTS,
                PAIRS,PREVIOUS,(0,8)):
            models=self.compare(fixture(kind,*pair,previous,slot),slot=slot,phase=phase)
            coverage.update(models[0].visits);cases+=1
        # Retail's standalone MTC1 at index 12 is unreachable from either branch.
        self.assertEqual(coverage&set(range(screen.ENTRY,screen.ENTRY+208,4)),
            set(range(screen.ENTRY,screen.ENTRY+208,4))-{screen.ENTRY+12*4})
        self.receipt('guest',cases=cases,executions=cases*3,actual_helper_words=52,
            directly_compiled_exact=True,reachable_helper_words=51,unreachable_word=12,
            independent_single_precision_and_order_reference=True,
            full_private_public_memory_events_calls_exact=True)

    def test_02_actual_aliases_and_all_fired_fault_prefixes(self):
        cases=prefixes=0
        for kind,pair,phase in itertools.product((0x89,0xBA),PAIRS,(0,8)):
            actor=proof.actor_address(0)
            for commands in (proof.OUTPUT,actor+0x2E0,actor+0x2E4,actor+0x2E8,
                    actor+0x2EC,proof.STACK+phase-0x20):
                memory=fixture(kind,*pair)
                positive=self.compare(memory,commands=commands,phase=phase);cases+=1
                for ordinal in range(positive[0].accesses):
                    models=[]
                    for words in self.tile_forms:
                        model=ActualTileOracle(words,memory,self.helper,commands=commands,phase=phase)
                        model.fault=ordinal
                        with self.assertRaises(proof.guest.AccessFault):model.run()
                        self.assertEqual(model.accesses,ordinal);models.append(model)
                    for model in models[1:]:
                        for name in ('memory','events','calls'):
                            self.assertEqual(getattr(models[0],name),getattr(model,name))
                    prefixes+=1
        with self.assertRaisesRegex(AssertionError,'actual special helper'):
            ActualTileOracle(self.tile_forms[0],fixture(),[]).run()
        with self.assertRaisesRegex(ValueError,'unqualified float conversion'):
            self.compare(fixture(numerator=2147483647,denominator=1))
        with self.assertRaisesRegex(AssertionError,'unqualified float conversion'):
            ActualTileOracle(self.tile_forms[0],fixture(numerator=2147483647,denominator=1),
                self.helper).run()
        self.receipt('aliases-faults',cases=cases,executions=cases*3,
            fired_prefixes=prefixes,failed_executions=prefixes*3,
            actor_field_and_private_output_aliases=True,full_private_order_exact=True,
            missing_fault_or_helper_substitute_fails=True,
            nonfinite_out_of_range_FCSR_traps_and_extreme_long_loops_not_acceptance=True)

    def test_03_copied_special_owner_actual_padding_and_neighbors(self):
        before=(self.out/'before-special').read_text();objects=[]
        for name,body in (('owner-before',before),('owner-after',screen.copied_owner(before))):
            obj,warnings=compile_owner(self.root,self.out,body,name)
            self.assertEqual(warnings,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',
                check=True,capture_output=True)
            objects.append(obj)
        parsed=[parse_object(obj) for obj in objects]
        def body(data,name):
            text,functions,relocs=data;target=functions[name];start,size=target['value'],target['size']
            return size,text[start:start+size],{a-start:v for a,v in relocs.items() if start<=a<start+size}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION:self.assertEqual(body(parsed[0],name),body(parsed[1],name),name)
        self.assertEqual(body(parsed[1],screen.FUNCTION),body(parse_object(self.out/'selected.o'),screen.FUNCTION))
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        for index,obj in enumerate(objects):
            assembly=self.out/('padded-owner-%d.s'%index)
            subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),
                str(self.root/'conker/retail_layout.us.txt'),'game_EF410',str(assembly),
                '--word-patches',str(self.out/'before-guards')],
                check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(assembly.with_suffix('.o')),
                str(assembly)],check=True,capture_output=True)
        padded=[parse_object(self.out/('padded-owner-%d.o'%index)) for index in (0,1)]
        base=padded[1][1][screen.FUNCTION]['value'];expected=bytearray(padded[0][0])
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'],208)
        self.assertEqual(padded[1][0][base:base+208],struct.pack('>52I',*self.original))
        expected[base:base+208]=padded[1][0][base:base+208]
        self.assertEqual(bytes(expected),padded[1][0]);self.assertEqual(padded[0][2],padded[1][2])
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,
            actual_padded_target_bytes=208,only_target_changes=True,guards=0,
            other_bodies_extents_relocations_pools_exact=True)

    def test_04_fresh_effective_complete_C_negatives(self):
        controls=(('scale','500.0f','499.0f'),('inset','+ 2.0f','+ 1.0f'),
            ('state-divide','coordinate / 3','coordinate / 4'),('wrap','previous += 64','previous += 63'),
            ('tile','commands++, 4','commands++, 5'),('zero-gate','!= 0','== 0'))
        for name,old,new in controls:
            memory=fixture();self.compare(memory)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,screen.SELECTED.replace(old,new))
            for section,(base,data) in sections(self.out/('negative-'+name+'.elf')).items():
                if section in ('.rodata','.data'):
                    memory.update({base+i:value for i,value in enumerate(data)})
            model=HelperOracle(words,memory,proof.OUTPUT,proof.actor_address(0)).run()
            returned,state,_=helper_reference(memory,proof.OUTPUT,proof.actor_address(0))
            self.assertNotEqual((model.r[2],model.memory),(returned,state),name)
            self.assertNotEqual(words,self.original)
        with self.assertRaisesRegex(ValueError,'stale'):
            screen.copied_owner(screen.copied_owner((self.out/'before-special').read_text()))
        self.receipt('negatives',fresh_complete_IDO_controls=len(controls),effective=True)

    def test_05_actual_banked_renderer_with_real_special_helper(self):
        render=list(struct.unpack_from('>532I',self.rom,0x5A1AC))
        bodies,data=chain.load_helpers(self.root);bodies[screen.ENTRY]=self.helper
        cases=0
        for kind,pair,mode,phase in itertools.product((0x89,0xBA),PAIRS,(0,3),(0,8)):
            memory=chain.fixture(count=2,kind=0,enabled=cases&1)
            actor=proof.actor_address(0);helper=fixture(kind,*pair,PREVIOUS[cases%len(PREVIOUS)])
            for start,length in ((actor+0x27A,8),(actor+0x2E4,12),
                    (proof.TABLE+kind*4,4),(proof.RECORDS,0x200)):
                memory.update({start+i:helper[start+i] for i in range(length)})
            memory[actor+4]=kind
            for name,size in (('D_800C4778',2),('D_800C4488',4),('D_800C48F0',4)):
                base=chain.renderer.S[name]
                proof.guest.put(memory,base+kind*size,proof.guest.read(memory,base+7*size,size),size)
            args=(chain.renderer.OUTPUT,0,0,mode,0);models=[]
            for words in self.tile_forms:
                connected=dict(bodies);connected[tile.ENTRY]=words
                model=ActualConnected(render,memory,args,connected,data,phase=phase,caller=True).run()
                self.assertEqual(len(model.tile_records),1)
                captured,call_args,after,returned=model.tile_records[0]
                expected,state,_,_=reference(captured,*call_args)
                self.assertEqual(returned,expected)
                self.assertEqual({a:v for a,v in after.items() if proof.public(a)},
                    {a:v for a,v in state.items() if proof.public(a)})
                self.assertIn(screen.ENTRY,model.visits);models.append(model)
            for model in models[1:]:
                for name in ('memory','events','calls','accesses'):
                    self.assertEqual(getattr(models[0],name),getattr(model,name))
            cases+=1
        self.receipt('connected',cases=cases,executions=cases*3,
            actual_special_renderer_dispatch_color_RGB_shading_matrix_bodies=True,
            independent_tile_call_boundary=True,no_saved_PC_adjustment=True,other_callbacks_bounded=True)

    def test_06_native_complete_C_helper_and_updater_with_actual_SDK(self):
        cases=[]
        for kind,present in itertools.product(range(256),(False,True)):
            memory=fixture(kind,*PAIRS[kind%len(PAIRS)],PREVIOUS[kind%len(PREVIOUS)])
            proof.guest.put(memory,proof.TABLE+kind*4,proof.RECORDS if present else 0)
            cases.append((memory,0,proof.OUTPUT,0))
        for kind,pair,previous,alias in itertools.product((0x89,0xBA),PAIRS,
                (0,3,66),range(5)):
            commands=proof.OUTPUT if alias==0 else proof.actor_address(25)+0x2E0+(alias-1)*4
            cases.append((fixture(kind,*pair,previous,25),25,commands,alias))
        serialized=[]
        ranges=((proof.actor_address,0x32C),(lambda slot:proof.RECORDS,0x200),(lambda slot:proof.OUTPUT,64))
        # Transform numeric half/word inputs to little endian, then use the same
        # independent arithmetic/order reference with little-endian memory APIs.
        from tools.experiments import game_actor_renderer_native32 as native
        for memory,slot,commands,alias in cases:
            little=memory.copy();actor=proof.actor_address(slot);kind=memory[actor+4]
            for address,size in [(actor+0x27A+i*2,2) for i in range(4)]+\
                    [(actor+0x2E4+i*4,4) for i in range(3)]+\
                    [(proof.RECORDS+i*12+j,2) for i in range(15) for j in (8,10)]+\
                    [(proof.TABLE+kind*4,4)]:
                native.little_put(little,address,proof.guest.read(memory,address,size),size)
            present=int(proof.guest.read(memory,proof.TABLE+kind*4,4)!=0)
            with patch.multiple(proof.guest,read=native.little_read,put=native.little_put):
                returned,state,_,_=reference(little,commands,slot)
            fields=[]
            for base,length in ranges:
                fields.extend(native.image(values,base(slot),length) for values in (little,state))
            fields.extend(str(value) for value in (slot,kind,present,alias,returned-commands))
            serialized.append('{'+','.join(fields)+'}')
        mbi=(self.root/'conker/include/2.0L/PR/mbi.h').read_text()
        gbi=(self.root/'conker/include/2.0L/PR/gbi.h').read_text()
        macros=sdk_macro(mbi,'_SHIFTL')+''.join(sdk_macro(gbi,name) for name in
            ('G_SETTILESIZE','gDPLoadTileGeneric','gDPSetTileSize'))
        source=NATIVE_TYPES+macros+tile.recovery.DECLARATIONS+NATIVE_FIXTURE+screen.SELECTED+\
            '\n'+tile.SELECTED+'\nstatic const Case cases[]={\n'+',\n'.join(serialized)+'\n};\n'+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        for name,old,new in (('native-scale','500.0f','499.0f'),
                ('native-state','coordinate / 3','coordinate / 4'),('native-tile','commands++, 4','commands++, 5')):
            result,detail=self.run_native(name,source.replace(screen.SELECTED,screen.SELECTED.replace(old,new)))
            self.assertIn(result,(1,2,3),(name,result,detail))
        self.receipt('native',cases=len(cases),executions=len(cases)*2,profiles=2,
            complete_actual_helper_and_updater_C_SDK=True,all_256_types=True,
            signed_conversion_wrap_and_actor_aliases=True,native_valid_slots_only=[0,25],
            independent_little_endian_reference=True,fresh_effective_native_negatives=3)

    def test_05_independent_rebased_links_with_actual_special_helper(self):
        cases=0
        settings=((tile.ENTRY,proof.ACTORS,proof.TABLE,screen.ENTRY),
            (0x15207FF0,0x80107FFC,0x80218004,0x15218004),
            (0x15308004,0x80118004,0x80227FFC,0x15327FFC),
            (0x15417FFC,0x80207FF0,0x80318004,0x15407FF0))
        for entry,actors,table,special in settings:
            symbols=dict(D_800CC2D0=actors,D_800C5338=table,func_150C3160=special)
            forms=tuple(schedule.GameActorTileUpdaterMatchTests.link(name,entry,symbols)
                for name in ('original','selected','fitted'))
            self.assertEqual(forms[0],forms[2])
            with patch.multiple(proof,ACTORS=actors,TABLE=table,SPECIAL=special),\
                    patch.object(screen,'ENTRY',special):
                for kind,slot,pair,phase in itertools.product((0x89,0xBA),(0,25,-1),PAIRS,(0,8)):
                    memory=fixture(kind,*pair,66,slot)
                    returned,state,events,calls=reference(memory,proof.OUTPUT,slot)
                    models=[ActualTileOracle(words,memory,self.helper,slot,phase=phase,
                        entry=entry,special=special).run() for words in forms]
                    for model in models:
                        self.assertEqual(model.r[2],returned)
                        self.assertEqual({a:v for a,v in model.memory.items() if proof.public(a)},
                            {a:v for a,v in state.items() if proof.public(a)})
                        self.assertEqual([e for e in model.events if e[0]=='CALL' or proof.public(e[1])],events)
                        self.assertEqual(model.calls,calls)
                    for model in models[1:]:
                        for name in ('memory','events','calls','accesses'):
                            self.assertEqual(getattr(models[0],name),getattr(model,name))
                    cases+=1
        self.receipt('actual-rebases',independent_links=12,symbol_sets=4,cases=cases,
            executions=cases*3,actual_relocated_special_entry=True,
            helper_no_absolute_dependencies=True,full_private_memory_order_exact=True)

    def test_07_immutable_baseline_and_whole_linked_installation(self):
        with self.assertRaisesRegex(ValueError,'immutable baseline'):self.receipt('baseline')
        for name in self.paths:
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name])
        before_source=(self.out/'before-source').read_text()
        source=(self.root/tile.SOURCE).read_text()
        if tile.recovery.ORIGINAL in source:
            for name,path in self.paths.items():
                self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name],name)
            self.receipt('installation',installed=False,six_artifacts_and_snapshots_exact=True)
            return
        self.assertEqual(source,tile.recovery.copied_owner(before_source,tile.SELECTED))
        self.assertEqual((self.root/screen.SOURCE).read_text(),
            screen.copied_owner((self.out/'before-special').read_text()))
        with (self.out/'before-guards').open(newline='') as stream:old=list(csv.DictReader(stream))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),old+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes();expected=bytearray(before)
        for function,entry,words in ((tile.FUNCTION,tile.ENTRY,self.tile_forms[0]),
                (screen.FUNCTION,screen.ENTRY,self.original)):
            struct.pack_into('>%dI'%len(words),expected,elf_slot_offset(before,entry,len(words)*4),*words)
            struct.pack_into('>I',expected,installed.symbol_size_offset(before,function,entry),len(words)*4)
        actual=(self.root/self.paths['elf']).read_bytes();em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5];expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_two_target_slots_and_extents_change=True,
            bytes=700,added_tile_guards=120,special_guards=0,guard_prefix_exact=True,
            all_other_linked_bytes_addresses_extents_exact=True,progress_rodata_exact=True,protected_data=audit)


NATIVE_TYPES=proof.NATIVE_TYPES+'\ntypedef float f32;\n'
NATIVE_FIXTURE=r'''
ActorDisplay58F80 D_800CC2D0[26];ActorSegmentRow58F80 *D_800C5338[256];
static u8 records[512] __attribute__((aligned(16))),output[64] __attribute__((aligned(16)));
typedef struct {u8 actor[0x32C],expectedActor[0x32C],records[512],expectedRecords[512],
    output[64],expectedOutput[64];u32 slot,kind,present,alias,advance;} Case;
static void copy(u8 *to,const u8 *from,u32 length) {u32 i;for(i=0;i<length;i++)to[i]=from[i];}
typedef char widths[(sizeof(void *)==4 && sizeof(ActorDisplay58F80)==0x32C)?1:-1];
'''
NATIVE_RUNNER=r'''
int run(void) {
    u32 n,i;const Case *c;u8 *actor,*commands;Gfx *result;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++) {
        c=cases+n;actor=(u8 *)&D_800CC2D0[c->slot];copy(actor,c->actor,0x32C);
        copy(records,c->records,512);copy(output,c->output,64);
        D_800C5338[c->kind]=c->present?(ActorSegmentRow58F80 *)records:NULL;
        commands=c->alias?actor+0x2E0+(c->alias-1)*4:output;
        result=func_1502F9FC((Gfx *)commands,c->slot);
        if((u8 *)result!=commands+c->advance)return 1;
        for(i=0;i<0x32C;i++)if(actor[i]!=c->expectedActor[i])return 2;
        for(i=0;i<512;i++)if(records[i]!=c->expectedRecords[i])return 3;
        for(i=0;i<64;i++)if(output[i]!=c->expectedOutput[i])return 3;
    }
    return 0;
}
'''


if __name__=='__main__':
    unittest.main()
