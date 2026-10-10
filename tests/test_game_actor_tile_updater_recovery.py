"""Complete actor tile updater recovery; no installation or hardware claim."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_tile_updater_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests.test_game_dual_matrix_emitter import sdk_macro
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_renderer_install_match as install
from tools.experiments import game_actor_renderer_connected as chain
from tools.tests.test_game_record_constructor_match import elf_slot_offset

STACK, OUTPUT, RECORDS = guest.STACK, 0x20000, 0x22000
ACTORS, TABLE, SPECIAL = screen.SYMBOLS.values()
SLOTS = (0, 25, -1, 0x7FFFFFFF, -0x80000000, 0x12345678)
KINDS = (0, 1, 2, 3, 4, 5, 0x28, 0x89, 0x96, 0xBA, 255)
SELECTORS = {0:14, 1:5, 2:5, 3:5, 4:5, 0x28:4, 0x96:7}


def actor_address(slot):
    return (ACTORS + (slot & 0xFFFFFFFF) * 0x32C) & 0xFFFFFFFF


def public(address):
    return not STACK - 0x200 <= address < STACK + 0x100


def fixture(kind=0, present=True, slot=0, pattern=0):
    actor = actor_address(slot)
    memory = {STACK+i:0xA5 for i in range(-0x200,0x100)}
    for base, length in ((actor-16, 0x350), (OUTPUT, 64), (RECORDS, 0x200), (TABLE-16, 0x420)):
        memory.update({(base+i)&0xFFFFFFFF:(i*17+53)&255 for i in range(length)})
    memory[actor+4] = kind
    guest.put(memory,TABLE+kind*4,RECORDS if present else 0)
    coordinates = ((0,1,2,3), (0x7FFE,0x7FFF,0x8000,0x8001),
        (0xFFFE,0xFFFF,0,0xFFF), (0x1000,0x1FFF,0xABCD,0x4321))[pattern]
    for i,value in enumerate(coordinates): guest.put(memory,actor+0x27A+i*2,value,2)
    dimensions = ((0,1),(0xFFFF,0x8000),(0x4000,0x7FFF),(0x1234,0xABCD))[pattern]
    for row in range(15):
        guest.put(memory,RECORDS+row*12+8,dimensions[0]+row*37,2)
        guest.put(memory,RECORDS+row*12+10,dimensions[1]+row*29,2)
    return memory


def reference(memory, commands=OUTPUT, slot=0, delta=16, actions=()):
    state, events, calls = memory.copy(), [], []
    actor = actor_address(slot)
    def get(address,size=4):
        value = guest.read(state,address&0xFFFFFFFF,size)
        events.append(('R',address&0xFFFFFFFF,size,value))
        return value
    def store(address,value,size=4):
        address &= 0xFFFFFFFF
        guest.put(state,address,value,size)
        events.append(('W',address,size,value&((1<<(size*8))-1)))
    kind = get(actor+4,1)
    if kind in (0x89,0xBA):
        call = ('CALL',SPECIAL,(commands,actor))
        calls.append(call);events.append(call)
        store(commands,0xCAFE0001);store(commands+4,0x12345678)
        for address,value,size in actions: store(address,value,size)
        return (commands+delta)&0xFFFFFFFF,state,events,calls
    header = TABLE+kind*4
    if get(header):
        selected = SELECTORS.get(kind,0)
        for part in range(2):
            root = get(header)
            left = get(actor+0x27A+part*2,2)
            top = get(actor+0x27E+part*2,2)
            width = get(root+selected*12+8,2)
            height = get(root+selected*12+10,2)
            first = 0xF2000000 | ((left+2)&0xFFF)<<12 | ((top+2)&0xFFF)
            second = (5-part)<<24 | ((width*4-2)&0xFFF)<<12 | ((height*4-2)&0xFFF)
            store(commands,first);store(commands+4,second)
            commands = (commands+8)&0xFFFFFFFF
    return commands,state,events,calls


class TileOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,slot=0,commands=OUTPUT,phase=0,delta=16,actions=()):
        super().__init__(words,memory,entry=screen.ENTRY,arguments=(commands,slot),phase=phase)
        self.delta,self.actions = delta,actions

    def record_call(self,target):
        assert target == SPECIAL, ('unexpected tile callback',target)
        call = ('CALL',target,self.arguments(2))
        self.calls.append(call);self.events.append(call)

    def hook(self,target):
        assert target == SPECIAL
        commands,_ = self.arguments(2)
        self.put(commands,0xCAFE0001,4);self.put(commands+4,0x12345678,4)
        for address,value,size in self.actions: self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.r[2]=(commands+self.delta)&0xFFFFFFFF


class TileConnected(chain.ConnectedOracle):
    def __init__(self,*args,**kwargs):
        self.tile_active=None;self.tile_started=False;self.tile_records=[]
        super().__init__(*args,**kwargs)

    def record_call(self,target):
        if target==screen.ENTRY:
            self.tile_active=(self.memory.copy(),self.arguments(2),self.r[29],self.r[31])
            self.tile_started=False
        if target==SPECIAL:
            return TileOracle.record_call(self,target)
        return super().record_call(target)

    def hook(self,target):
        assert target!=screen.ENTRY, 'complete tile updater cannot be a hook'
        if target==SPECIAL:
            self.delta,self.actions=16,()
            return TileOracle.hook(self,target)
        return super().hook(target)

    def execute(self,word):
        super().execute(word)
        if self.tile_active is not None:
            before,args,stack,returned=self.tile_active
            self.tile_started |= self.r[29]!=stack
            if self.tile_started and self.r[29]==stack and self.r[31]==returned:
                self.tile_records.append((before,args,self.memory.copy(),self.r[2]))
                self.tile_active=None


class GameActorTileUpdaterRecoveryTests(unittest.TestCase):
    assemble = classmethod(guest.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_native = install.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-tile-updater-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        assert set(cls.baseline)==set(cls.paths), 'invalid immutable baseline manifest'
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>123I',cls.rom,screen.ROM))

    def receipt(self,name,**values):
        if name=='baseline':
            raise ValueError('immutable baseline manifest is not a receipt')
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,slot=0,commands=OUTPUT,phase=0,delta=16,actions=()):
        expected,state,events,calls=reference(memory,commands,slot,delta,actions)
        models=[TileOracle(words,memory,slot,commands,phase,delta,actions).run()
            for words in (self.retail,self.raw)]
        for model in models:
            self.assertEqual(model.r[2],expected)
            self.assertEqual({a:v for a,v in model.memory.items() if public(a)},
                {a:v for a,v in state.items() if public(a)})
            self.assertEqual([e for e in model.events if e[0]=='CALL' or public(e[1])],
                [e for e in events if e[0]=='CALL' or public(e[1])])
            self.assertEqual(bytes(model.memory[commands+i] for i in range(16)),
                bytes(state[commands+i] for i in range(16)))
            self.assertEqual(model.calls,calls)
        self.assertEqual(models[0].memory,models[1].memory)
        self.assertEqual(models[0].events,models[1].events)
        self.assertEqual(models[0].accesses,models[1].accesses)
        return models

    def test_01_complete_body_shape_and_original_all_words(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],
            self.meta['differences'],self.meta['diagnostics']),(111,0x20,0,118,''))
        self.assertNotEqual(self.raw,self.retail)
        coverage=[set(),set()]
        cases=0
        for kind,present,phase in itertools.product(range(256),(False,True),(0,8)):
            for i,model in enumerate(self.compare(fixture(kind,present),phase=phase)):
                coverage[i].update(model.visits)
            cases+=1
        self.assertEqual(coverage,[set(range(screen.ENTRY,screen.ENTRY+n*4,4)) for n in (123,111)])
        self.receipt('guest',cases=cases,executions=cases*2,all_256_ids=True,
            original_compiled_all_words=[123,111],full_private_public_memory_events_calls_exact=True,
            independent_ordered_public_reference=True,original_frame_exact=True,not_byte_matching=True)

    def test_02_signed_wrapped_slots_coordinate_dimensions_and_callback_results(self):
        cases=0
        for slot,kind,pattern,phase in itertools.product(SLOTS,KINDS,range(4),(0,8)):
            self.compare(fixture(kind,slot=slot,pattern=pattern),slot=slot,phase=phase)
            cases+=1
        for kind,delta,phase in itertools.product((0x89,0xBA),(-OUTPUT,0,8,16,32),(0,8)):
            actions=((actor_address(0)+4,0,1),(TABLE+kind*4,0,4))
            self.compare(fixture(kind),delta=delta,phase=phase,actions=actions)
            cases+=1
        self.receipt('boundaries',cases=cases,executions=cases*2,signed_fullwidth_slots=True,
            coordinate_dimension_wrap=True,special_mutations_and_cursor_return_preserved=True)

    def test_03_live_output_aliases_and_private_fired_fault_prefixes(self):
        cases,pairs=0,0
        samples=[]
        for kind,pattern in itertools.product((0,1,0x96,0x28,255),range(4)):
            for output in (actor_address(0)+0x278,actor_address(0)+0x27C,
                    RECORDS+SELECTORS.get(kind,0)*12+8,OUTPUT+8):
                memory=fixture(kind,pattern=pattern)
                self.compare(memory,commands=output)
                samples.append((memory,output))
                cases+=1
        # A command can replace its live table root; map the resulting guest
        # root explicitly rather than let the second iteration read a stale one.
        for kind in (0,1,0x96):
            memory=fixture(kind)
            output=TABLE+kind*4
            first=0xF2000000|2<<12|4
            selected=SELECTORS[kind]
            for i in range(32): memory[first+selected*12+i]=0x19+i
            self.compare(memory,commands=output)
            samples.append((memory,output));cases+=1
        samples += [(fixture(0x89),OUTPUT),(fixture(255,False),OUTPUT)]
        for phase in (0,8):
            memory=fixture(0)
            self.compare(memory,commands=STACK+phase-0x20,phase=phase)
            cases+=1
        for phase in (0,8):
            for memory,output in samples[::7]+samples[-2:]:
                positive=self.compare(memory,commands=output,phase=phase)
                for ordinal in range(positive[0].accesses):
                    models=[]
                    for words in (self.retail,self.raw):
                        model=TileOracle(words,memory,commands=output,phase=phase)
                        model.fault=ordinal
                        with self.assertRaises(guest.AccessFault): model.run()
                        self.assertEqual(model.accesses,ordinal)
                        models.append(model)
                    self.assertEqual(models[0].memory,models[1].memory)
                    self.assertEqual(models[0].events,models[1].events)
                    self.assertEqual(models[0].calls,models[1].calls)
                    pairs+=1
        self.receipt('aliases',cases=cases,executions=cases*2,
            live_actor_record_and_table_root_aliases=True,full_fired_fault_prefix_pairs=pairs,
            failed_executions=pairs*2,private_public_prefix_memory_events_calls_exact=True,
            absence_of_fault_is_failure=True)

    def test_04_fresh_effective_complete_C_negatives(self):
        negatives=(
            ('wrong-row','selected = 14;','selected = 13;',0),
            ('wrong-type','kind == 0xBA','kind == 0xBB',0xBA),
            ('wrong-inset','left += 2;','left += 1;',0),
            ('wrong-width','right * 4 - 2','right * 4 - 1',0),
            ('wrong-tile','5 - part','4 - part',0),
            ('wrong-count','part != 2','part != 1',0),
            ('wrong-null-gate','D_800C5338[kind] != NULL','D_800C5338[kind] == NULL',0))
        for name,old,new,kind in negatives:
            memory=fixture(kind)
            self.compare(memory)
            _,words=screen.compile_candidate(self.root,self.out,name,screen.SELECTED.replace(old,new))
            model=TileOracle(words,memory).run()
            expected,state,_,_=reference(memory)
            self.assertTrue((model.r[2],{a:v for a,v in model.memory.items() if public(a)}) !=
                (expected,{a:v for a,v in state.items() if public(a)}),name)
        self.receipt('negatives',fresh_complete_compiled_controls=len(negatives),
            effective=True,unmodified_positives_checked_first=True)

    def test_05_copied_owner_neighbors_pools_relocations_and_actual_padding(self):
        before=(self.out/'before-source').read_text()
        objects=[]
        for name,source in (('owner-before',before),('owner-after',screen.copied_owner(before))):
            obj,warnings=compile_owner(self.root,self.out,source,name)
            self.assertEqual(warnings,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',
                check=True,capture_output=True)
            objects.append(obj)
        parsed=[parse_object(obj) for obj in objects]
        def body(data,name):
            text,functions,relocations=data
            record=functions[name];base,size=record['value'],record['size']
            return size,text[base:base+size],{a-base:v for a,v in relocations.items() if base<=a<base+size}
        self.assertEqual(parsed[0][1].keys(),parsed[1][1].keys())
        for name in parsed[0][1]:
            if name!=screen.FUNCTION:self.assertEqual(body(parsed[0],name),body(parsed[1],name),name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        self.assertEqual(body(parsed[1],screen.FUNCTION),body(parse_object(self.out/'selected.o'),screen.FUNCTION))
        padded=[]
        for i,obj in enumerate(objects):
            name='padded-owner-%d'%i
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards',filename='generated_58F80',
                rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out/(name+'.o')))
        expected=bytearray(padded[0][0])
        target=padded[1][1][screen.FUNCTION];base,size=target['value'],target['size']
        self.assertEqual(size,444)
        next_target=padded[1][1]['func_1502FBE8']['value']
        self.assertEqual(next_target-base,492)
        self.assertEqual(padded[1][0][base+444:next_target],bytes(48))
        expected[base:next_target]=padded[1][0][base:next_target]
        self.assertEqual(bytes(expected),padded[1][0])
        self.assertNotEqual(padded[1][0][base:next_target],struct.pack('>123I',*self.retail))
        self.receipt('owner',neighbors=len(parsed[0][1])-1,diagnostics=0,
            other_bodies_extents_relative_relocations_pools_exact=True,
            isolated_owner_target_equal=True,actual_padded_slot_bytes=492,
            copied_symbol_bytes=444,only_copied_target_changes=True,padding_words=12,padding_not_matching=True)

    def test_06_actual_native32_C_sdk_all_types_boundaries_aliases_and_negatives(self):
        mbi=(self.root/'conker/include/2.0L/PR/mbi.h').read_text()
        gbi=(self.root/'conker/include/2.0L/PR/gbi.h').read_text()
        macros=sdk_macro(mbi,'_SHIFTL')+''.join(sdk_macro(gbi,n) for n in
            ('G_SETTILESIZE','gDPLoadTileGeneric','gDPSetTileSize'))
        lookup=','.join(str(SELECTORS.get(k,0)) for k in range(256))
        source=NATIVE_TYPES+macros+screen.DECLARATIONS+NATIVE_FIXTURE+screen.SELECTED+(
            '\nstatic const u8 selections[256]={'+lookup+'};\n')+NATIVE_RUNNER+START
        for profile in ('-O2','-O0'):
            result,detail=self.run_native('native-'+profile[1:].lower(),source,profile)
            self.assertEqual(result,0,(profile,detail))
        controls=[]
        for name,old,new in (('native-wrong-row','selected = 14;','selected = 13;'),
                ('native-wrong-inset','left += 2;','left += 1;'),
                ('native-wrong-tile','5 - part','4 - part')):
            negative=source.replace(screen.SELECTED,screen.SELECTED.replace(old,new))
            result,detail=self.run_native(name,negative)
            self.assertIn(result,(1,2,3,4,5),(name,result,detail));controls.append((name,result,detail))
        self.receipt('native',cases=256*2*2*4*5,profiles=2,executions=256*2*2*4*5*2,
            actual_complete_C_sdk=True,all_256_types=True,
            native_valid_slots_only=[0,25],actor_record_output_aliases=True,
            independent_little_endian_reference=True,guest_table_pointer_aliases_not_native=True,
            fresh_effective_complete_controls=controls,special_helper_bounded=True)

    def test_07_measured_forms_profiles_and_physical_layout_refusal(self):
        records=[]
        for name,body in screen.candidates():
            for profile in ('o2g3','o1g3'):
                meta,words=screen.compile_candidate(self.root,self.out,name+'-'+profile,body,profile)
                self.assertEqual(meta['diagnostics'],'')
                self.assertNotEqual(words,self.retail)
                records.append(meta)
        self.receipt('shapes',forms=len(records),records=records,
            original_words=123,selected_words=111,selected_frame=32,
            no_byte_exact_form=True,no_production_installation=True)

    def test_08_immutable_production_and_stale_owner_rejections(self):
        with self.assertRaisesRegex(ValueError,'immutable baseline'):
            self.receipt('baseline',replacement=True)
        for name,path in self.paths.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),self.baseline[name],name)
            self.assertEqual(hashlib.sha256((self.out/('before-'+name)).read_bytes()).hexdigest(),self.baseline[name],name)
        before=(self.out/'before-source').read_text()
        with self.assertRaisesRegex(ValueError,'stale'):screen.copied_owner(screen.copied_owner(before))
        with self.assertRaisesRegex(ValueError,'stale'):
            screen.copied_owner(before.replace('Gfx *func_1502F9FC();','Gfx *func_1502F9FC(Gfx *, s32);'))
        self.receipt('unchanged-production',all_five_production_artifacts_unchanged=True,no_matching_credit=True)

    def test_09_complete_banked_renderer_actual_helper_and_tile_call_boundaries(self):
        elf=(self.root/self.paths['elf']).read_bytes()
        render_words=list(struct.unpack_from('>532I',self.rom,0x5A1AC))
        offset=elf_slot_offset(elf,chain.renderer.screen.ENTRY,2128)
        self.assertEqual(list(struct.unpack_from('>532I',elf,offset)),render_words)
        bodies,data=chain.load_helpers(self.root)
        offset=elf_slot_offset(elf,chain.COLOR,200)
        self.assertEqual(list(struct.unpack_from('>50I',elf,offset)),bodies[chain.COLOR])
        cases=0
        for kind,present,mode,phase in itertools.product(KINDS,(False,True),(0,3),(0,8)):
            memory=chain.fixture(count=2,kind=0,enabled=cases&1)
            tile=fixture(kind,present,pattern=cases%4)
            actor=ACTORS
            for start,length in ((actor+0x27A,8),(TABLE+kind*4,4),(RECORDS,0x200)):
                memory.update({start+i:tile[start+i] for i in range(length)})
            memory[actor+4]=kind
            for name,size in (('D_800C4778',2),('D_800C4488',4),('D_800C48F0',4)):
                base=chain.renderer.S[name]
                guest.put(memory,base+kind*size,guest.read(memory,base+7*size,size),size)
            args=(chain.renderer.OUTPUT,0,0,mode,0)
            models=[]
            for words in (self.retail,self.raw):
                connected=dict(bodies);connected[screen.ENTRY]=words
                model=TileConnected(render_words,memory,args,connected,data,phase=phase,caller=True).run()
                self.assertEqual(len(model.tile_records),1)
                captured,tile_args,after,returned=model.tile_records[0]
                expected,state,_,_=reference(captured,*tile_args)
                self.assertEqual(returned,expected)
                self.assertEqual({a:v for a,v in after.items() if public(a)},
                    {a:v for a,v in state.items() if public(a)})
                self.assertIn(screen.ENTRY,model.visits)
                self.assertIn(chain.COLOR,model.visits)
                self.assertIn(chain.RGB,model.visits)
                if cases&1:self.assertIn(chain.SHADING,model.visits)
                if mode==0:self.assertIn(chain.IDENTITY,model.visits)
                models.append(model)
            for name in ('memory','events','calls','accesses'):
                self.assertEqual(getattr(models[0],name),getattr(models[1],name),name)
            self.assertEqual(models[0].r[2],models[1].r[2])
            cases+=1
        with self.assertRaisesRegex(AssertionError,'complete tile updater'):
            model=TileConnected(render_words,memory,args,bodies,data,caller=True)
            model.run()
        self.receipt('connected',cases=cases,executions=cases*2,
            complete_banked_dispatcher_renderer_color_RGB_shading_and_matrix_bodies_execute=True,
            full_original_compiled_private_memory_events_calls_exact=True,
            independent_tile_call_boundary_public_reference=True,
            modeled_tile_substitute_rejected=True,special_and_other_callbacks_bounded=True)


NATIVE_TYPES=r'''
typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;
typedef struct { struct { u32 w0,w1; } words; } Gfx;
#define NULL ((void *)0)
'''
NATIVE_FIXTURE=r'''
ActorDisplay58F80 D_800CC2D0[26];ActorSegmentRow58F80 *D_800C5338[256];
static u8 records[192] __attribute__((aligned(16))),output[64] __attribute__((aligned(16)));
static u8 expectedActor[0x32C],expectedRecords[192],expectedOutput[64];
static int calls;static u32 callActor,callOutput;
static void copy(u8 *to,const u8 *from,u32 size) { u32 i;for(i=0;i<size;i++)to[i]=from[i]; }
static void put16(u8 *to,u32 value) { to[0]=value;to[1]=value>>8; }
static u32 read16(const u8 *from) { return from[0]|(u32)from[1]<<8; }
static void put32(u8 *to,u32 value) { u32 i;for(i=0;i<4;i++)to[i]=value>>(8*i); }
Gfx *func_150C3160(Gfx *commands,u8 *actor) {
    calls++;callActor=(u32)actor;callOutput=(u32)commands;
    commands[0].words.w0=0xCAFE0001;commands[0].words.w1=0x12345678;
    return commands+2;
}
'''
NATIVE_RUNNER=r'''
static int report(u32 code,u32 c,u32 i) {
    u32 data[3]={code,c,i};s32 result;
    __asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");
    return (s32)code;
}
static u16 coords[4][4]={{0,1,2,3},{0x7FFE,0x7FFF,0x8000,0x8001},
    {0xFFFE,0xFFFF,0,0xFFF},{0x1000,0x1FFF,0xABCD,0x4321}};
static u16 dims[4][2]={{0,1},{0xFFFF,0x8000},{0x4000,0x7FFF},{0x1234,0xABCD}};
typedef char widths[(sizeof(void *)==4 && sizeof(ActorDisplay58F80)==0x32C)?1:-1];
int run(void) {
    u32 k,p,slot,pattern,alias,i,part,n=0,first,second,selected,offset;
    u8 *actor,*commands,*expected,*row;Gfx *result;
    for(k=0;k<256;k++)for(p=0;p<2;p++)for(slot=0;slot<26;slot+=25)
    for(pattern=0;pattern<4;pattern++)for(alias=0;alias<5;alias++) {
        actor=(u8 *)&D_800CC2D0[slot];
        for(i=0;i<0x32C;i++)actor[i]=(u8)(i*17+53);
        for(i=0;i<192;i++)records[i]=(u8)(i*29+71);
        for(i=0;i<64;i++)output[i]=0xA5;
        actor[4]=k;
        for(i=0;i<4;i++)put16(actor+0x27A+i*2,coords[pattern][i]);
        for(i=0;i<15;i++) { put16(records+i*12+8,dims[pattern][0]+i*37);put16(records+i*12+10,dims[pattern][1]+i*29); }
        selected=selections[k];D_800C5338[k]=p?(ActorSegmentRow58F80 *)records:NULL;
        copy(expectedActor,actor,0x32C);copy(expectedRecords,records,192);copy(expectedOutput,output,64);
        commands=alias==1?actor+0x278:alias==2?actor+0x27C:
            alias==3?records+selected*12+8:alias==4?records+selected*12+4:output;
        expected=alias==1?expectedActor+0x278:alias==2?expectedActor+0x27C:
            alias==3?expectedRecords+selected*12+8:alias==4?expectedRecords+selected*12+4:expectedOutput;
        offset=0;
        if(k==0x89 || k==0xBA) {
            put32(expected,0xCAFE0001);put32(expected+4,0x12345678);offset=16;
        } else if(p) {
            for(part=0;part<2;part++) {
                row=expectedRecords+selected*12;
                first=0xF2000000U|((read16(expectedActor+0x27A+part*2)+2)&4095)<<12
                    |((read16(expectedActor + 0x27E + part*2)+2)&4095);
                second=(5-part)<<24|((read16(row+8)*4-2)&4095)<<12|((read16(row+10)*4-2)&4095);
                put32(expected+offset,first);put32(expected+offset+4,second);offset+=8;
            }
        }
        calls=0;result=func_1502F9FC((Gfx *)commands,(s32)slot);
        if((u8 *)result!=commands+offset)return report(1,n,0);
        if(calls!=(int)(k==0x89 || k==0xBA))return report(2,n,0);
        if(calls && (callActor!=(u32)actor || callOutput!=(u32)commands))return report(3,n,0);
        for(i=0;i<0x32C;i++)if(actor[i]!=expectedActor[i])return report(4,n,i);
        for(i=0;i<192;i++)if(records[i]!=expectedRecords[i])return report(5,n,i);
        for(i=0;i<64;i++)if(output[i]!=expectedOutput[i])return report(5,n,i+192);
        n++;
    }
    return n==20480?0:report(1,n,0);
}
'''


if __name__=='__main__':
    unittest.main()

