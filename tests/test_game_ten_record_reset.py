"""Ten-record reset: complete semantic loop, caller ABI and checked address folds."""
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_ten_record_reset as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
BASE, PARENT, PARENT_ROM = 0x800D3010, 0x150177F8, 0x44CA8
PREPARE, BZERO = 0x1509BA04, 0x100226F0


def fixture(seed=0, phase=0, base=BASE):
    memory = {STACK+phase+i: (seed+i*17+0xA5)&255 for i in range(-256, 256)}
    memory.update({base+i: (seed+i*29)&255 for i in range(-16, 136)})
    return memory


def reference(memory, base=BASE):
    result = dict(memory)
    for i in range(10):
        at = base+i*12
        result[at] &= 127
        for j in range(4, 12):
            result[at+j] = 0
    return result


class ResetOracle(TimingOracle):
    def __init__(self, words, memory, phase=0, entry=source.ENTRY, connected=None, seed=0):
        self.visits = set()
        self.seed = seed
        super().__init__(words, memory, phase=phase, entry=entry,
                         arguments=(0xFFFFFFFF, 0x80000000, 0x12345678, seed), connected=connected)

    def record_call(self, target):
        n = {PREPARE: 1, BZERO: 2, source.ENTRY: 0}[target]
        args = self.arguments(n)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        if target == PREPARE:
            assert self.calls[-1][1] == (1,)
            for i in range(120):
                self.memory[BASE+i] = (self.seed+i*29+0xA5)&255
        elif target == BZERO:
            assert self.calls[-1][1] == (0x800D2F48, 12)
            for i in range(12):
                self.memory[0x800D2F48+i] = 0
        else:
            raise AssertionError(('Unbounded reset helper', target))
        for i in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[i] = 0xA5000000+i
        self.f[:20] = [0xB5000000+i for i in range(20)]
        self.lo, self.hi = 0xABCD0010, 0xABCD0011


def controls():
    body = source.SELECTED
    return dict(selected=body,
        wrong_bit=body.replace('~0x80', '~0x40'),
        nine=body.replace('index < 10', 'index < 9'),
        eight=body.replace('index < 10', 'index < 8'),
        first_only=body.replace('[index]', '[0]'),
        keep_value=body.replace('D_800D3010[index].value = 0;', ''),
        keep_timer=body.replace('D_800D3010[index].unk8 = 0;', ''),
        wipe_status=body.replace('&= (u16)~0x80', '= 0'),
        toggle=body.replace('&= (u16)~0x80', '^= 0x80'),
        partial_value=body.replace('.value = 0;', '.value &= 0xFF;'),
        clear_padding=body.replace('.value = 0;', '.value = 0; D_800D3010[index].pad1[0] = 0;'))


def native_harness(caller):
    result = '#include <ultra64.h>\n' + source.DECLARATIONS + '''
typedef char record_size[sizeof(GeneratedCD5A0Record)==12?1:-1];
typedef char value_offset[__builtin_offsetof(GeneratedCD5A0Record,value)==4?1:-1];
typedef char timer_offset[__builtin_offsetof(GeneratedCD5A0Record,unk8)==8?1:-1];
static struct {u32 left[4];GeneratedCD5A0Record records[10];u32 right[4];} actual,expected;
#define D_800D3010 actual.records
'''
    for name, body in controls().items():
        result += body.replace(source.FUNCTION, name) + '\n'
    result += '''typedef void (*Reset)(void);
static int variant(Reset fn) {
 u32 seed,pattern,i,j,repeat;u8 *p=(u8*)&actual,*q=(u8*)&expected;
 for(seed=0;seed<256;seed++)for(pattern=0;pattern<8;pattern++) {
  for(i=0;i<sizeof(actual);i++)p[i]=q[i]=(u8)(seed+i*29+pattern*37);
  for(repeat=0;repeat<2;repeat++) {
   for(i=0;i<10;i++) {
    q[16+i*12]&=127;
    for(j=4;j<12;j++)q[16+i*12+j]=0;
   }
   fn();
   for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 23;
  }
 }
 return 0;
}
static u8 D_800D2F48[12],D_800D2E41,D_800D2E42,D_800D2E44;
static s32 D_800D3858;
static f32 D_800D2DB0,D_800968C0;
static u32 native_seed,steps;
static void reset_prepare(s32 mode) {
 u32 i,j;u8 *p=(u8*)&actual,*q=(u8*)&expected;
 if(mode!=1||steps!=0){steps=99;return;}steps=1;
 for(i=0;i<120;i++)((u8*)actual.records)[i]=(u8)(native_seed+i*29+0xA5);
 for(i=0;i<sizeof(actual);i++)q[i]=p[i];
 for(i=0;i<10;i++){q[16+i*12]&=127;for(j=4;j<12;j++)q[16+i*12+j]=0;}
}
static void reset_bzero(void *address,s32 size) {
 u32 i;u8*p=(u8*)address;
 if(address!=D_800D2F48||size!=12||steps!=1){steps=99;return;}steps=2;
 for(i=0;i<12;i++)p[i]=0;
}
#define func_1509BA04 reset_prepare
#define bzero reset_bzero
#define func_150A00F0 selected
'''
    result += caller + '\n'
    result += 'int run(void) {\n'
    for i, name in enumerate(controls()):
        result += ' if(variant(%s)!=%d)return %d;\n' % (name, 0 if name == 'selected' else 23, i+1)
    result += ''' {
 u32 seed,i;u8 *p=(u8*)&actual,*q=(u8*)&expected;
 for(seed=0;seed<256;seed++) {
  native_seed=seed;steps=0;
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(seed+i*17);
  for(i=0;i<12;i++)D_800D2F48[i]=0xA5;
  D_800968C0=17.25f;D_800D2DB0=-91.5f;
  D_800D2E41=255;D_800D2E42=254;D_800D2E44=253;D_800D3858=-1;
  func_150177F8();
  if(steps!=2||D_800D2DB0!=D_800968C0||D_800D2E41!=10||D_800D2E42!=6||D_800D2E44||D_800D3858)return 40;
  for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 41;
  for(i=0;i<12;i++)if(D_800D2F48[i])return 42;
 }
 }
 return 0;
}
'''
    return result + START


class TenRecordResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = ROOT / source.BUILD
        cls.values = source.snapshot(cls.out)
        cls.installed = (ROOT/source.SOURCE).read_bytes() != cls.values[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.out)
        else:
            source.qualify(ROOT, cls.out)
            source.make_shadow(ROOT, cls.out)
            source.predict(ROOT, cls.out)
        cls.raw_object, diag = source.compile_owner(ROOT, cls.out,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED, 'fresh-selected')
        if diag:
            raise ValueError(diag)
        cls.padded = cls.out/'qualified-padded.o'
        data, functions = source.link_owner(ROOT, cls.out, cls.padded, source.OWNER)
        cls.words = list(struct.unpack_from('>43I', data, functions[source.FUNCTION]['value']))
        data, functions = source.link_owner(ROOT, cls.out, cls.raw_object, source.OWNER)
        cls.raw_words = list(struct.unpack_from('>46I', data, functions[source.FUNCTION]['value']))
        cls.rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>43I', cls.rom, source.ROM))
        cls.receipt = dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt, indent=2)+'\n')
        print(cls.receipt)

    def compare(self, seed=0, phase=0, base=BASE, entry=source.ENTRY, images=None):
        initial = fixture(seed,phase,base)
        models = [ResetOracle(words,initial,phase,entry).run() for words in images or (self.truth,self.words)]
        for model in models:
            self.assertEqual(model.memory,reference(initial,base))
            self.assertEqual(model.calls,[])
        self.assertEqual(complete(models[0]),complete(models[1]))
        return models

    def test_01_complete_words_owner_Make_and_stub_negative(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.normalized(*source.payload(self.raw_object)),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text())
        m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['raw_words'],q['frame'],q['new_guards'],q['preserved_neighbors']),(43,46,0,20,4))
        self.assertEqual(m['actual_Make_commands'],3)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,172)
        stale=ResetOracle(struct.unpack_from('>43I',old,at),fixture(255)).run()
        self.assertNotEqual(stale.memory,self.compare(255)[0].memory)
        self.receipt.update(words=43,raw_words=46,frame=0,new_guards=20,omitted_high_loads=3,
            inserted_words=0,compiler_only=False,neighbors=4,actual_Make_commands=3,old_stub_rejected=True,
            whole_typed_caller_object_unchanged=True)

    def test_02_all_flags_counters_padding_fences_and_repeat(self):
        visits=set();count=0
        for seed,phase in itertools.product(range(256),(0,8)):
            models=self.compare(seed,phase);visits.update(models[0].visits);count+=1
            for words in (self.truth,self.words,self.raw_words):
                memory=fixture(seed,phase)
                for repeat in range(2):
                    model=ResetOracle(words,memory,phase).run()
                    self.assertEqual(model.memory,reference(memory));memory=dict(model.memory)
                    count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+172,4)))
        self.receipt.update(guest_phases=count,all43_words_visited=True,
            raw_C_ordinary_memory_outcomes=True,raw_literal_GPR_or_fault_equivalence_claimed=False)

    def test_03_native32_three_optimizations_ten_wrong_C_and_actual_C_caller(self):
        old=self.values[source.CALLER_SOURCE].decode()
        lo,hi=source.function_span(old,'func_150177F8')
        harness=native_harness(old[lo:hi])
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(harness)
            process=subprocess.run([*native_command(opt),str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stdout+process.stderr)
            process=subprocess.run([str(p)],capture_output=True,timeout=60)
            self.assertEqual(process.returncode,0,(opt,process.stdout,process.stderr))
        self.receipt.update(native_cases_per_optimization=4096,native_actual_caller_cases_per_optimization=256,
            native_optimizations=['O0','O2','O3'],defined_wrong_C_controls=10,trap_UBSan=True,
            native_disjoint_typed_storage=True)

    def linked(self,obj,entry,base,label):
        aliases={0:4,8:12,16:20}
        for a,b in aliases.items():
            self.assertEqual(((base+a+0x8000)>>16)&65535,((base+b+0x8000)>>16)&65535)
        symbols={'D_%08X'%(BASE+i):(base+i)&0xFFFFFFFF for i in(0,4,8,12,16,20,24,120)}
        data,functions,bindings=source.parse_object(obj)
        asm,unknown=emit_function(data,functions[source.FUNCTION],bindings,source.FUNCTION,symbols)
        self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
            *['--defsym=%s=0x%X'%pair for pair in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1])

    def test_04_relocations_rebases_and_all_fired_access_prefixes(self):
        phases=cuts=0
        for i,(entry,base) in enumerate(((source.ENTRY,BASE),(0x18017FFC,0x80347FE0),(0x1A028000,0x80458000))):
            objects=(source.original(ROOT,self.out),self.padded,self.out/'make-shadow/src/game/generated_CD5A0.c.o')
            images=[self.linked(obj,entry,base,'rebase-test-%d-%d'%(i,j)) for j,obj in enumerate(objects)]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for seed,phase in itertools.product((0,1,127,128,255),(0,8)):
                self.compare(seed,phase,base,entry,images[:2]);phases+=1
        for seed,phase in itertools.product((0,127,128,255),(0,8)):
            initial=fixture(seed,phase);good=ResetOracle(self.truth,initial,phase).run()
            self.assertEqual(good.root_accesses,40)
            for cut in range(good.root_accesses):
                models=[ResetOracle(words,initial,phase) for words in(self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        with self.assertRaises(AssertionError):self.linked(self.padded,source.ENTRY,0x80347FFC,'invalid-fold-layout')
        self.receipt.update(independent_GNU_links=9,rebase_phases=phases,fired_root_access_prefixes=cuts,
            fixed_array_alias_relationships_preserved=True,arbitrary_incompatible_layout_rejected=True,
            portable_C_fault_semantics_claimed=False)

    def test_05_complete_actual_caller_frame_and_late_reset(self):
        parent=list(struct.unpack_from('>28I',self.rom,PARENT_ROM))
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,PARENT,112)
        self.assertEqual(before[at:at+112],struct.pack('>28I',*parent))
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4) if self.rom[i:i+4]==jal],[0x44CC8])
        visits=set();count=0
        for seed,phase in itertools.product(range(32),(0,8)):
            initial=fixture(seed,phase)
            for address,size in((0x800D2F48,12),(0x800968C0,4),(0x800D2DB0,4),(0x800D2E41,4),(0x800D3858,4)):
                for i in range(size):initial[address+i]=(seed+i*13+0xA5)&255
            put(initial,0x800968C0,(0,0x3FA00000,0xC1900000,0x477FFF00)[seed%4])
            expected=dict(initial)
            for i in range(120):expected[BASE+i]=(seed+i*29+0xA5)&255
            expected=reference(expected)
            for i in range(12):expected[0x800D2F48+i]=0
            put(expected,0x800D2DB0,read(expected,0x800968C0));put(expected,0x800D3858,0)
            expected.update({0x800D2E41:10,0x800D2E42:6,0x800D2E44:0})
            models=[]
            for words in(self.truth,self.words):
                connected={source.ENTRY+i*4:word for i,word in enumerate(words)}
                model=ResetOracle(parent,initial,phase,PARENT,connected,seed).run()
                self.assertEqual(model.calls,[(PREPARE,(1,)),(BZERO,(0x800D2F48,12)),(source.ENTRY,())])
                self.assertEqual({a:b for a,b in model.memory.items() if not STACK-256<=a<STACK+256},
                                 {a:b for a,b in expected.items() if not STACK-256<=a<STACK+256})
                self.assertEqual(model.r[29],STACK+phase);visits.update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(PARENT,PARENT+112,4))<=visits)
        self.receipt.update(actual_full_caller_words=28,caller_frame=24,actual_caller_phases=count,
            all_caller_words_visited=True,actual_C_caller_native=True,
            prepare_and_bzero_helpers_bounded=True,full_helper_implementation_claimed=False)

    def test_06_guest_stack_overlap_and_nonzero_incoming_registers(self):
        base=STACK-64;entry=0x18000000
        images=[self.linked(obj,entry,base,'stack-overlap-%d'%j) for j,obj in enumerate((source.original(ROOT,self.out),self.padded))]
        count=0
        for seed,phase in itertools.product(range(0,256,17),(0,8)):
            self.compare(seed,phase,base,entry,images);count+=1
        self.receipt.update(guest_stack_overlap_phases=count,guest_stack_overlap_not_native_C_claim=True)

    def test_07_expected_word_binding_and_schedule_controls(self):
        raw,bindings=source.payload(self.raw_object)
        for i in range(46):
            bad=bytearray(raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad.pop(at)
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old)
        self.assertTrue(new.startswith(old))
        fields=csv.DictReader(io.StringIO(old.decode())).fieldnames
        rows=list(csv.DictReader(io.StringIO(new[len(old):].decode()),fieldnames=fields))
        self.assertEqual(len(rows),20);self.assertEqual(sum(x['omit']=='true' for x in rows),3)
        self.assertTrue(all(not x['insert_after'] for x in rows))
        self.receipt.update(raw_word_negatives=46,raw_binding_negatives=len(bindings),new_guard_rows=20,
            source_schedule_is_closed=True,guarded_not_compiler_only=True)

    def test_08_installed_history_and_strict_full_image_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172]
        predicted=source.predicted_image(before,truth);source.check_image(before,predicted,truth)
        at=source.elf_slot_offset(before,source.ENTRY,172)
        for position in(0,at-1,at,at+168,at+172,len(before)-1):
            bad=bytearray(predicted);bad[position]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,predicted[:-1],truth)
        symbols={name:(offset,string_at) for offset,name,_,string_at in source.symbol_rows(before)}
        for old_order,_ in source.SYMBOL_ORDERS:
            for position in symbols[old_order[0]]:
                bad=bytearray(predicted);bad[position]^=1
                with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for name,old in self.values.items():
            expected=old
            if self.installed:
                if name==source.SOURCE:expected=source.recovered_owner(old.decode()).encode()
                elif name==source.CALLER_SOURCE:expected=source.recovered_caller(old.decode()).encode()
                elif name=='conker/retail_word_patches.us.csv':expected=source.guard_bytes(old)
                elif name=='conker/build/conker.us.elf':expected=predicted
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.receipt.update(pinned_inputs=len(source.INPUTS),old_guard_prefix_preserved=True,strict_image_negatives=19,
            closed_symbol_and_string_cycles=6,metadata_exclusions=0)
