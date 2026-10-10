"""Full slot updater, callback mutations, physical homes and linked-only audit."""
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

from tools.experiments import game_slot_byte_update_matching as screen
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
from tools.tests.game_owner_pool import normalized_pools

ACTORS, CLASSIFIER, FINAL, STACK = 0x800CC2D0,0x1502EE8C,0x1507E3C0,color.STACK
LINKS = ((screen.ENTRY,ACTORS,CLASSIFIER,FINAL),
    (0x15207FF0,0x80107FFC,0x15218004,0x15227FF0),
    (0x15308004,0x80118004,0x15327FFC,0x15337FF0),
    (0x15417FFC,0x80207FF0,0x15428004,0x15437FFC))
RETURNS = (0,1,2,3,0x100,0x101,0x102,0xFFFFFFFF,0x80000001)


def fixture(slot=0,first=1,second=9,identity=15,values=(0,3),base=ACTORS):
    memory = {STACK+i:0xA5 for i in range(-0x100,0x80)}
    actor = base+slot*0x32C
    memory.update({actor+i:(i*17+0x35)&255 for i in range(-16,0x33C)})
    for offset,value in ((4,identity),(0x6A,values[0]),(0x6B,values[1]),(0x6C,first),(0x6D,second)):
        put(memory,actor+offset,value,1)
    put(memory,actor+0x94,0xA5A51080)
    return memory


def reference(memory,slot=0,results=(0,1),actions=None,symbols=LINKS[0],real=False):
    result,events,calls = memory.copy(),[],[]
    _,base,classifier,final = symbols
    actor = base+slot*0x32C
    actions = actions or {}
    def get(address,size=1):
        value = read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(address,value,size=1):
        put(result,address,value,size)
        events.append(('W',address,size,value&((1<<(size*8))-1)))
    for index in range(2):
        address = actor+0x6C+index
        if get(address)<10:
            calls.append((classifier,slot,index))
            events.append(('CALL',classifier,(slot,index)))
            if real:
                value = get(actor+0x6A+index)
                state = value if value<2 else value-2 if value<4 else 2
            else:
                for offset,value,size in actions.get(index,()): store(actor+offset,value,size)
                state = results[index]&255
            if state==0:
                value = get(address)
                if value>0: store(address,value-1)
            elif state==1:
                value = get(address)
                if value<2: store(address,value+1)
            else:
                store(address,1)
    calls.append((final,actor))
    events.append(('CALL',final,(actor,)))
    if real:
        if get(actor+4) in (15,70,76):
            values = []
            for index in range(2):
                value = get(actor+0x6C+index)
                values.append((0 if value==15 else 1 if value==11 else 2) if value>=10
                    else value+1 if value<2 else value)
            flags = get(actor+0x94,4)|0x7E
            store(actor+0x94,flags,4)
            flags &= ~(8 if values[0]==0 else 16 if values[0]==1 else 4)
            store(actor+0x94,flags,4)
            flags &= ~(32 if values[1]==0 else 64 if values[1]==1 else 2)
            store(actor+0x94,flags,4)
    else:
        for offset,value,size in actions.get(2,()): store(actor+offset,value,size)
    return result,events,calls


class SlotOracle(TriangleOracle):
    def __init__(self,words,memory,slot=0,results=(0,1),actions=None,phase=0,symbols=LINKS[0],connected=None,
            entry=None,arguments=None):
        entry_address,base,self.classifier,self.final = symbols
        super().__init__(words,memory,entry=entry or entry_address,phase=phase,connected=connected,
            arguments=(slot,) if arguments is None else arguments)
        self.slot,self.actor,self.results,self.actions = slot,base+slot*0x32C,results,actions or {}
    def get(self,address,size):
        assert all(address+i in self.memory for i in range(size)),('unmapped read',address,size)
        return super().get(address,size)
    def put(self,address,value,size):
        if self.recording:
            assert all(address+i in self.memory for i in range(size)),('unmapped write',address,size)
        super().put(address,value,size)
    def record_call(self,target):
        assert target in (self.classifier,self.final)
        args = self.arguments(2 if target==self.classifier else 1)
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))
    def hook(self,target):
        index = self.r[5] if target==self.classifier else 2
        address = self.actor if target==self.classifier else self.r[4]
        for offset,value,size in self.actions.get(index,()): self.put(address+offset,value,size)
        value = self.results[index] if target==self.classifier else 0xA5000002
        for register in (1,2,3,*range(4,16),24,25): self.r[register] = 0xA5000000+register
        self.f[:20] = [0xA5000000+i for i in range(20)]
        self.r[2] = value&0xFFFFFFFF


class GameSlotByteUpdateMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host
    write_rows = classmethod(color.GameObjectColorModeMatchTests.write_rows.__func__)
    assemble = classmethod(color.GameObjectColorModeMatchTests.assemble.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-slot-byte-update-match-test'
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
        cls.retail = list(struct.unpack_from('>74I',cls.rom,screen.ROM))
        assembly = (cls.root/'conker/asm/58F80.s').read_text()
        slot = assembly.split('glabel '+screen.FUNCTION,1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        cls.slot_asm = cls.out/'slot.s'
        cls.slot_asm.write_text('glabel '+screen.FUNCTION+slot+'endlabel '+screen.FUNCTION+'\n')
        cls.write_rows(cls.out/'isolated.csv',screen.guard_rows(cls.out/'selected.o'))
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot_asm,
            word_patches_path=cls.out/'isolated.csv',filename='generated_58F80'))
        lines = ['.text','.set noat','.set noreorder','.globl '+screen.FUNCTION,
            '.type %s,@function'%screen.FUNCTION,screen.FUNCTION+':']
        for index,word in enumerate(cls.retail):
            uses = screen.RELOCATIONS.get(index*4,())
            if uses: word &= 0xFC000000 if uses[0][0]=='R_MIPS_26' else 0xFFFF0000
            for kind,symbol in uses: lines.append('.reloc ., %s, %s'%(kind,symbol))
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
        cls.rows = screen.guard_rows(cls.owner_objects[1])
        cls.guards = cls.out/'qualified-guards.csv'
        cls.write_rows(cls.guards,cls.old_rows+cls.rows)
        cls.elf = (cls.root/cls.paths['elf']).read_bytes()
        def slot(entry,size): return list(struct.unpack_from('>%dI'%(size//4),cls.elf,elf_slot_offset(cls.elf,entry,size)))
        cls.classifier,cls.final,cls.dispatcher = slot(CLASSIFIER,104),slot(FINAL,320),slot(dispatch.ENTRY,352)
        cls.assert_callees = ((cls.classifier,0x5C33C,26),(cls.final,0xAB870,80),(cls.dispatcher,0x59234,88))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        cls.fixture = '''typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
static u8 D_800CC2D0[26*0x32C+16];
static s32 results[2],mutations[2],wantedSlot; static int calls[2],finalCalls,error;
s32 func_1502EE8C(s32 slot,s32 index) {
    if(slot!=wantedSlot || index<0 || index>1) {error=1; return 0;}
    calls[index]++;
    if(mutations[index]>=0) D_800CC2D0[slot*0x32C+0x6C+index]=mutations[index];
    return results[index];
}
void func_1507E3C0(u8 *actor) {
    if(actor!=D_800CC2D0+wantedSlot*0x32C) error=2;
    finalCalls++; actor[0x94]^=0x5A;
}
''' + screen.SELECTED+'\n'

    @classmethod
    def link(cls,name,symbols):
        entry,base,classifier,final = symbols
        script = cls.out/('link-%s-%X.ld'%(name,entry))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=D_800CC2D0=0x%X'%base,'--defsym=func_1502EE8C=0x%X'%classifier,
            '--defsym=func_1507E3C0=0x%X'%final,'-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        data = sections(elf)['.text'][1]
        size = parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']
        return list(struct.unpack_from('>%dI'%(size//4),data))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_closed_shape_homes_and_every_stale_word(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['diagnostics']),
            (74,48,0,''))
        self.assertEqual(self.linked,self.retail)
        fitted = screen.recipe(screen.RAW)
        self.assertEqual(len(fitted),74)
        self.assertFalse(any(row['insert_after'] or row['omit']!='false' for row in self.rows))
        self.assertEqual({self.retail[i]&65535 for i in (1,3,4,5,6,7,8)},set(range(0x14,0x30,4)))
        for index in range(74):
            stale = list(screen.RAW); stale[index] ^= 0x10000
            with self.assertRaisesRegex(ValueError,'stale complete'): screen.recipe(stale)
        self.receipt('shape',words=74,frame=48,guards=74,changed_words=sum(a!=b for a,b in zip(screen.RAW,fitted)),
            inserted_words=0,omissions=0,pool_bytes=0,physical_saved_homes=list(range(0x14,0x30,4)))

    def test_02_byte_gates_wide_returns_mutations_and_order(self):
        cases,coverage = 0,set()
        inputs = [(fixture(slot,first,second),slot,(a,b),{}) for slot,first,second,a,b in itertools.product(
            (0,1,12,24,25),(0,1,2,9,10,11,15,255),(0,1,2,9,10,11,15,255),(0,1,2,0x100),(0,1,2,0x101))]
        inputs += [(fixture(0,value,255-value),0,(ret,ret),{}) for value,ret in itertools.product(range(256),RETURNS)]
        inputs += [(fixture(slot,1,9),slot,(a,b),{0:((0x6C,value,1),(0x6D,second,1)),1:((0x6D,value,1),),
            2:((0x94,0x12345678,4),)}) for slot,a,b,value,second in itertools.product(
                (0,25),(0,1,2,0xFFFFFFFF),(0,1,2),(0,1,2,9,255),(0,10))]
        for memory,slot,results,actions in inputs:
            expected,events,calls = reference(memory,slot,results,actions)
            models = [SlotOracle(words,memory,slot,results,actions).run() for words in (self.retail,self.linked,self.raw)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            for model in models:
                public = {a:b for a,b in memory.items() if not STACK-0x100<=a<STACK+0x80}
                self.assertEqual({a:model.memory[a] for a in public},{a:expected[a] for a in public})
                self.assertEqual([e for e in model.events if e[0]=='CALL' or e[1] in public],events)
                self.assertEqual(model.calls,calls)
            coverage.update(models[0].visits)
            cases += 1
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=len(coverage),
            unreachable_retail_store_word=48,wide_returns_low_byte_masked=True,post_callback_byte_reload_order=True,
            original_fitted_complete_private_trace_equal=True,raw_C_public_reference_equal=True)

    def test_03_all_verified_fault_prefixes_and_reserved_hole(self):
        prefixes = 0
        for first,results,phase in itertools.product((0,1,9,10),( (0,1),(1,2),(0xFFFFFFFF,0x100)),(0,8)):
            memory = fixture(25,first,1)
            good = SlotOracle(self.retail,memory,25,results,phase=phase).run()
            accesses = [e for e in good.events if e[0]!='CALL']
            for cut in range(len(accesses)):
                outcomes = []
                for words in (self.retail,self.linked):
                    model = SlotOracle(words,memory,25,results,phase=phase)
                    count = [0]; get,store = model.get,model.put
                    def gate():
                        if count[0]==cut: raise RuntimeError('verified access fault')
                        count[0] += 1
                    def read_gate(address,size):
                        gate(); return get(address,size)
                    def write_gate(address,value,size):
                        if model.recording: gate()
                        return store(address,value,size)
                    model.get,model.put = read_gate,write_gate
                    with self.assertRaisesRegex(RuntimeError,'verified access fault'): model.run()
                    self.assertEqual(count[0],cut)
                    outcomes.append((model.memory,model.events,model.calls))
                self.assertEqual(outcomes[0],outcomes[1])
                self.assertEqual([e for e in outcomes[0][1] if e[0]!='CALL'],accesses[:cut])
                prefixes += 1
            holes = memory.copy()
            for byte in range(4): del holes[STACK+phase-48+0x10+byte]
            for words in (self.retail,self.linked): SlotOracle(words,holes,25,results,phase=phase).run()
        self.receipt('faults',prefixes=prefixes,executions=prefixes*2,gates_verified=True,
            reserved_hole_unmapped_cases=24,portable_C_fault_claim=False)

    def test_04_independent_links_and_base_carry_rebases(self):
        cases = 0
        for symbols in LINKS:
            fitted,original = self.link('fitted',symbols),self.link('original',symbols)
            self.assertEqual(fitted,original)
            raw = self.link('selected',symbols)
            for slot,first,phase in itertools.product((0,25),(0,1,9,10,255),(0,8)):
                memory = fixture(slot,first,1,base=symbols[1])
                expected,events,calls = reference(memory,slot,(0,1),symbols=symbols)
                for words in (original,fitted,raw):
                    model = SlotOracle(words,memory,slot,phase=phase,symbols=symbols).run()
                    public = {a for a in memory if not STACK-0x100<=a<STACK+0x80}
                    self.assertEqual({a:model.memory[a] for a in public},{a:expected[a] for a in public})
                    self.assertEqual([e for e in model.events if e[0]=='CALL' or e[1] in public],events)
                    self.assertEqual(model.calls,calls)
                cases += 1
        self.receipt('rebases',independent_links=12,symbol_sets=4,cases=cases,signed_LO16_carries=True)

    def test_05_copied_owner_neighbors_and_unchanged_pools(self):
        self.assertEqual(self.owner_diagnostics,[[],[]])
        old,of,orels = parse_object(self.owner_objects[0])
        new,nf,nrels = parse_object(self.owner_objects[1])
        self.assertEqual(of.keys(),nf.keys())
        relative = lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name,f in nf.items():
            if name==screen.FUNCTION: continue
            prior = of[name]
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']],relative(nrels,f)),
                (prior['size'],old[prior['value']:prior['value']+prior['size']],relative(orels,prior)),name)
        self.assertEqual(normalized_pools(self.owner_objects[0]),normalized_pools(self.owner_objects[1]))
        bodies = []
        for i,obj in enumerate(self.owner_objects):
            name = 'padded-owner-%d'%i
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards' if i==0 else self.guards,
                filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            bodies.append(parse_object(self.out/(name+'.o')))
        start = bodies[1][1][screen.FUNCTION]['value']
        self.assertEqual(bodies[1][1][screen.FUNCTION]['size'],296)
        self.assertEqual(bodies[0][0][:start],bodies[1][0][:start])
        self.assertEqual(bodies[0][0][start+296:],bodies[1][0][start+296:])
        self.receipt('owner',neighbors=len(nf)-1,zero_diagnostics=True,prior_pools_and_relative_relocations_equal=True,
            all_other_padded_owner_bytes_equal=True,existing_color_and_phase_guards_unchanged=True)

    def test_06_actual_padder_stale_words_and_relocations(self):
        data = (self.out/'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(data)
        headers = [SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
        ns = headers[header[13]]; names = data[ns[4]:ns[4]+ns[5]]
        ts = next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(74):
            changed = bytearray(data)
            struct.pack_into('>I',changed,ts[4]+index*4,screen.RAW[index]^0x10000)
            path = self.out/'stale.o'; path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        rows = screen.guard_rows(self.out/'selected.o')
        for offset in screen.RELOCATIONS:
            wrong = [dict(row) for row in rows]; wrong[offset//4]['expected_relocations'] = '-'
            path = self.out/'stale-relocations.csv'; self.write_rows(path,wrong)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot_asm,word_patches_path=path,filename='generated_58F80')
        self.receipt('stale',actual_word_rejections=74,relocation_rejections=6)

    def test_07_actual_native32_complete_C(self):
        self.run_host('''
static u32 returns[]={0,1,2,3,0x100,0x101,0x102,0xFFFFFFFF,0x80000001};
static int changes[]={-1,0,1,255};
int slot,value,r,m,index,cases=0; u8 initial[2],expected[2],*actor;
for(slot=0;slot<26;slot++) for(value=0;value<256;value++) for(r=0;r<9;r++) for(m=0;m<4;m++) {
    wantedSlot=slot;actor=D_800CC2D0+slot*0x32C;
    actor[0x6B]=0xA5; actor[0x6E]=0xA5; actor[0x94]=0xA5;
    actor[0x6C]=initial[0]=expected[0]=value;
    actor[0x6D]=initial[1]=expected[1]=(value*13)&255;
    results[0]=returns[r]; results[1]=returns[(r+4)%9];
    mutations[0]=mutations[1]=changes[m];calls[0]=calls[1]=finalCalls=error=0;
    for(index=0;index<2;index++) if(initial[index]<10) {
        u8 state=results[index];
        if(mutations[index]>=0) expected[index]=mutations[index];
        if(state==0) {if(expected[index]>0) expected[index]--;}
        else if(state==1) {if(expected[index]<2) expected[index]++;}
        else expected[index]=1;
    }
    func_1502EEF4(slot);
    if(error || finalCalls!=1 || calls[0]!=(initial[0]<10) || calls[1]!=(initial[1]<10)
        || actor[0x6C]!=expected[0] || actor[0x6D]!=expected[1]
        || actor[0x6B]!=0xA5 || actor[0x6E]!=0xA5 || actor[0x94]!=0xFF) return 1;
    cases++;
}
if(cases!=239616) return 2;
''')
        self.receipt('native32',actual_complete_C_cases=239616,all_26_bounded_slots=True,
            callbacks_mutate_checked_byte=True,arbitrary_low_byte_returns=True)

    def test_08_fresh_effective_complete_compiled_controls(self):
        forms = dict(screen.recovery.candidates())
        cases = (('negative-cache-byte',fixture(first=9),(0,1),{0:((0x6C,0,1),)}),
            ('negative-no-byte-mask',fixture(first=9),(0x100,1),{}),
            ('negative-gate',fixture(first=10),(2,1),{}),
            ('negative-one-iteration',fixture(second=1),(0,0),{}),
            ('negative-final-pointer',fixture(),(0,1),{2:((0x94,0x12345678,4),)}))
        records = []
        for name,memory,results,actions in cases:
            meta,words = screen.recovery.compile_candidate(self.root,self.out,name,forms[name])
            model = SlotOracle(words,memory,results=results,actions=actions).run()
            expected,_,calls = reference(memory,results=results,actions=actions)
            public = {a for a in memory if not STACK-0x100<=a<STACK+0x80}
            self.assertTrue(model.calls!=calls or any(model.memory[a]!=expected[a] for a in public),name)
            records.append(meta)
        self.receipt('negatives',complete_compiled_controls=5,effective=5,measurements=records)

    def test_09_actual_banked_classifier_and_final_actor_flags(self):
        for words,rom,count in self.assert_callees:
            self.assertEqual(words,list(struct.unpack_from('>%dI'%count,self.rom,rom)))
        connected = {}
        for entry,words in ((CLASSIFIER,self.classifier),(FINAL,self.final)):
            connected.update(zip(range(entry,entry+len(words)*4,4),words))
        helper = self.linked
        if screen.ORIGINAL not in (self.root/screen.SOURCE).read_text():
            elf = (self.root/self.paths['elf']).read_bytes()
            helper = list(struct.unpack_from('>74I',elf,elf_slot_offset(elf,screen.ENTRY,296)))
            self.assertEqual(helper,self.linked)
        cases = 0
        for slot,first,second,identity,value in itertools.product((0,25),(0,1,2,9,10,11,15,255),
                (0,1,2,9,10,11,15,255),(0,15,70,76,255),(0,1,2,3,4,255)):
            memory = fixture(slot,first,second,identity,(value,255-value))
            expected,events,calls = reference(memory,slot,real=True)
            models = [SlotOracle(words,memory,slot,connected=connected).run() for words in (self.retail,helper)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            public = {a for a in memory if not STACK-0x100<=a<STACK+0x80}
            self.assertEqual({a:models[1].memory[a] for a in public},{a:expected[a] for a in public})
            self.assertEqual(models[1].calls,calls)
            self.assertEqual([e for e in models[1].events if e[0]=='W' and e[1] in public],
                [e for e in events if e[0]=='W'])
            cases += 1
        self.receipt('callees',cases=cases,banked_classifier_words=26,banked_final_callback_words=80,
            actual_padded_helper_words=74,independent_flag_reference_equal=True,no_opaque_callee_hooks=True)

    def test_10_linked_installation_only_target_changes(self):
        source = (self.root/screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
                for name,path in self.paths.items()},self.baseline)
            self.receipt('installation',installed=False,baseline_unchanged=True)
            return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before = (self.out/'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>74I',expected,elf_slot_offset(before,screen.ENTRY,296),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),296)
        actual = (self.root/self.paths['elf']).read_bytes()
        em,am = metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length = section[4],section[5]
            expected[offset:offset+length] = actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit = audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_296_bytes_and_symbol_extent_changed=True,
            old_guards_exact_byte_prefix=True,conversion_rows_unchanged=True,protected_data=audit)

    def test_11_actual_dispatcher_slot_forwarding_and_call_gates(self):
        helper = self.linked
        if screen.ORIGINAL not in (self.root/screen.SOURCE).read_text():
            elf = (self.root/self.paths['elf']).read_bytes()
            helper = list(struct.unpack_from('>74I',elf,elf_slot_offset(elf,screen.ENTRY,296)))
            self.assertEqual(helper,self.linked)
        class Connected(SlotOracle):
            def record_call(self,target):
                count = 2 if target==CLASSIFIER else 1 if target==FINAL else dispatch.COUNTS[target]
                args = self.arguments(count)
                self.calls.append((target,*args))
                self.events.append(('CALL',target,args))
            def hook(self,target):
                assert target in dispatch.COUNTS and target!=screen.ENTRY
                if target==0x1503A08C: self.put(self.actor+0x1D4,0,4)
                if target==0x1503DF48 and self.disable: self.put(self.actor,0,4)
                for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        cases,hits = 0,0
        for slot,identity,active,state,disable in itertools.product((0,25),(0,15,70,76,255),(0,1),(0,2,3,5),(False,True)):
            memory = fixture(slot,9,1,identity,(0,3))
            actor = ACTORS+slot*0x32C
            for offset,value,size in ((0,active,4),(5,state,1),(0xA4,0,1),(0xF8,0,4),(0x1C9,0,1),
                    (0x1D4,0xDEADBEEF,4),(0x260,0,4)):
                put(memory,actor+offset,value,size)
            put(memory,dispatch.FLAGS+slot*16,int(disable),1)
            expected,_,calls = reference(memory,slot,real=True)
            models = []
            for words in (self.retail,helper):
                connected = {}
                for entry,body in ((screen.ENTRY,words),(CLASSIFIER,self.classifier),(FINAL,self.final)):
                    connected.update(zip(range(entry,entry+len(body)*4,4),body))
                model = Connected(self.dispatcher,memory,slot,connected=connected,entry=dispatch.ENTRY,arguments=(actor,slot))
                model.disable = disable
                models.append(model.run())
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            wanted = bool(active and identity!=255 and state==0 and not disable)
            entries = [call for call in models[1].calls if call[0]==screen.ENTRY]
            self.assertEqual(entries,[(screen.ENTRY,slot)] if wanted else [])
            self.assertEqual(any(screen.ENTRY<=pc<screen.ENTRY+296 for pc in models[1].visits),wanted)
            nested = [call for call in models[1].calls if call[0] in (CLASSIFIER,FINAL)]
            self.assertEqual(nested,calls if wanted else [])
            for offset,size in ((0x6C,1),(0x6D,1),(0x94,4)):
                self.assertEqual(read(models[1].memory,actor+offset,size),read(expected if wanted else memory,actor+offset,size))
            hits += int(wanted)
            cases += 1
        self.receipt('dispatcher',cases=cases,verified_slot_updater_entries=hits,banked_caller_words=88,
            real_classifier_and_flag_callback=True,hostile_other_callbacks=True,pre_gate_active_mutation=True,
            hardware_or_gameplay_claim=False)


if __name__=='__main__':
    unittest.main()
