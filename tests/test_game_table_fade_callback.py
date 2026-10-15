"""Typed table snapshots and full-word semantics; the 0x60/0x68 frame gap stays open."""
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_table_fade_callback as source
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_actor_mask_scan_match import MaskOracle, AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_counter_preset_match as previous
from tools.check_game_data_layout import audit_layout

RECORD = 0x20000
TABLE = bytes.fromhex('fafaebebfafadcd2d2dcd200100707071408282828141400ffffffffbeaa78c83c78c80008020a01080aff0a02ff0a00')


def fixture(index=0, value=127, active=1, step=1, record=RECORD, width=-32768):
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-1024, 512)}
    memory.update({record + i: (i * 13 + 0xC5) & 255 for i in range(80)})
    memory.update({source.TABLES + i: v for i, v in enumerate(TABLE)})
    put(memory, source.STEP, step)
    for offset, v in ((0x1F, value), (0x24, active), (0x2C, index)):
        put(memory, record + offset, v, 1)
    put(memory, record + 0x14, width, 2)
    return memory


def effects(memory, target, record, mode):
    if target == source.MOVE:
        if mode in (1, 3):
            put(memory, record + 0x14, 0x8123 if mode == 1 else 32767, 2)
            put(memory, record + 0x2C, 10, 1)
            put(memory, record + 0x24, 0, 1)
        if mode:
            put(memory, source.STEP, 0xFFFFFFFD if mode == 1 else 2 if mode == 2 else 7)
        if mode in (2, 3):
            memory.update({source.TABLES + i: (61 + i * 23) & 255 for i in range(48)})
    elif mode == 2:
        put(memory, record + 0x22, 0xBEEF, 2)
    elif mode == 3:
        put(memory, record + 0x14, 0xA55A, 2)


def reference(original, record=RECORD, mode=0):
    memory = dict(original)
    tables = [[read(memory, source.TABLES + i * 12 + j, 1) for j in range(11)] for i in range(4)]
    index, value = read(memory, record + 0x2C, 1), read(memory, record + 0x1F, 1)
    assert index < 11, 'native/bounded semantic table domain'
    if read(memory, record + 0x24, 1):
        limit = tables[2][index]
        if value != limit:
            value = min(signed((value + read(memory, source.STEP) * 16) & 0xFFFFFFFF), limit)
            put(memory, record + 0x1F, value, 1)
    elif value:
        value = max(signed((value - read(memory, source.STEP) * tables[3][index]) & 0xFFFFFFFF), 0)
        put(memory, record + 0x1F, value, 1)
    if not read(memory, record + 0x24, 1) and value == 0:
        return memory, 1, []
    effects(memory, source.MOVE, record, mode)
    old = read(memory, record + 0x14, 2)
    extent = old - (65536 if old & 32768 else 0) + read(memory, source.STEP) * tables[1][index]
    put(memory, record + 0x16, extent, 2)
    put(memory, record + 0x14, extent, 2)
    if index == 3:
        put(memory, record + 0x18, 100, 2)
    effects(memory, source.SCALE, record, mode)
    return memory, 0, [(source.MOVE, record), (source.SCALE, record, tables[0][index])]


class TableFadeOracle(MaskOracle):
    def __init__(self, words, memory, record=RECORD, mode=0, phase=0, fault=None, connected=None):
        super().__init__(words, memory, entry=source.ENTRY, arguments=(record,), mode=mode, phase=phase,
            fault=fault, connected=connected)
        self.record = record

    def execute(self, word):
        op, rt = word >> 26, word >> 16 & 31
        if op in (38, 46):
            rs, imm = word >> 21 & 31, word & 65535
            at = (self.r[rs] + (imm if imm < 32768 else imm - 65536)) & 0xFFFFFFFF
            lane, base = at & 3, at & ~3
            mask = (1 << ((lane + 1) * 8)) - 1
            self.dispatched_word, self.own_instruction = word, True
            try:
                if op == 38:
                    value = (self.r[rt] & ~mask) | (self.get(base, 4) >> ((3 - lane) * 8))
                    if rt:
                        self.r[rt] = value & 0xFFFFFFFF
                else:
                    self.put(base, self.r[rt] & mask, lane + 1)
                    self.writes.append((base, lane + 1))
            finally:
                self.own_instruction = False
            self.r[0] = 0
        elif op == 32:
            super().execute(word | 0x10000000)
            if rt:
                self.r[rt] = ((self.r[rt] ^ 128) - 128) & 0xFFFFFFFF
        else:
            super().execute(word)

    def record_call(self, target):
        assert target in (source.MOVE, source.SCALE, 0x1516F8EC, 0x1516F91C), hex(target)
        args = self.arguments(1 if target == source.MOVE else 2)
        self.calls.append((target, *args))
        self.events.append(('CALL', target, args))

    def hook(self, target):
        assert target in (source.MOVE, source.SCALE)
        effects(self.memory, target, self.record, self.mode)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]


def external(memory):
    return {a: v for a, v in memory.items() if not STACK - 1024 <= a < STACK + 512}


def controls():
    return {
        'wide-active': source.SELECTED.replace('record[0x24]', '*(u32 *)(record + 0x24)'),
        'wrong-rise': source.SELECTED.replace('<< 4', '<< 5'),
        'early-byte': source.SELECTED.replace('    if (record[0x24] == 0 && value == 0)', '    value = (u8)value;\n    if (record[0x24] == 0 && value == 0)'),
        'wrong-fade': source.SELECTED.replace('fades.values[index]', 'growth.values[index]'),
        'wrong-growth': source.SELECTED.replace('* growth.values[index]', '* fades.values[index]'),
        'wrong-special': source.SELECTED.replace('index == 3', 'index == 4'),
        'live-growth': source.SELECTED.replace('* growth.values[index]', '* D_8008CBD0.values[index]'),
        'live-scale': source.SELECTED.replace('record, scales.values[index]', 'record, D_8008CBC4.values[index]'),
    }


class TableFadeCandidateTests(unittest.TestCase):
    def test_scope_recipes_and_strict_direct_match_gate(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(len(set(source.PATHS.values())), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        before = 'extern s32 D_800BE9E4;\ns32 func_1516F024() {\n    return 0;\n}\nvoid other(void) { }\n'
        for body in (*source.candidates().values(), *source.layouts().values()):
            self.assertNotIn('volatile', body)
            self.assertTrue(source.recovered_owner(before, body).endswith('void other(void) { }\n'))
        with self.assertRaises(ValueError):
            source.recovered_owner(source.recovered_owner(before))
        for count, differences, diagnostics in ((103, 19, ''), (102, 0, ''), (103, 0, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, differences=differences, diagnostics=diagnostics))):
                with self.assertRaisesRegex(ValueError, 'not a direct match'):
                    source.qualify(Path('.'), Path('.'))


class TableFadeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.recover(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>103I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = previous.CounterMatchTests.test_08_all_original_801_archive_fingerprints

    def test_01_raw_frame_real_padder_neighbors_and_original_data(self):
        self.assertEqual((len(self.words), self.row['differences'], self.row['frame']), (103, 19, 96))
        self.assertFalse(self.row['installable'])
        old_obj, diag = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diag, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(self.obj))
        path = self.out / 'recovered-padded.s'
        path.write_text(emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER, word_patches_path=self.out / 'before-guards'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        data, fs = source.build.link_owner(self.root, self.out, path.with_suffix('.o'), source.OWNER)
        f = fs[source.FUNCTION]
        self.assertEqual(list(struct.unpack_from('>103I', data, f['value'])), self.words)
        image = (self.out / 'before-elf').read_bytes()
        self.assertEqual(image[elf_slot_offset(image, source.TABLES, 48):][:48], TABLE)
        self.assertEqual(self.rom[source.TABLE_ROM:source.TABLE_ROM + 48], TABLE)
        self.assertEqual(struct.unpack_from('>I', self.rom, source.TABLE_ROM - 28)[0], source.ENTRY)
        self.assertEqual(sum(w >> 26 == 38 for w in self.words), 4)
        self.assertEqual(sum(w >> 26 == 46 for w in self.words), 4)
        self.receipt('owner', raw_and_padded_words=103, differences=19, candidate_frame=96, retail_frame=104,
            four_11_byte_table_copies=True, exact_48_byte_source_data=True, actual_callback_table_index=2,
            unchanged_neighbors=29, pools_and_relative_relocations_fixed=True, guards_added=0, installable=False)

    def test_02_partial_word_merge_and_untouched_copy_padding(self):
        cases = 0
        for lane in range(4):
            for i in range(256):
                old, word = (i * 1664525 + 1013904223) & 0xFFFFFFFF, (i * 65539 + 0x87654321) & 0xFFFFFFFF
                model = TableFadeOracle(self.truth, fixture())
                put(model.memory, 0x30000, word)
                model.r[8], model.r[9] = 0x30000, old
                model.execute((38 << 26) | (8 << 21) | (9 << 16) | lane)
                shift, mask = (3 - lane) * 8, (0xFFFFFF00, 0xFFFF0000, 0xFF000000, 0)[lane]
                self.assertEqual(model.r[9], (old & mask) | (word >> shift))
                model.r[9] = old
                model.execute((46 << 26) | (8 << 21) | (9 << 16) | lane)
                self.assertEqual(read(model.memory, 0x30000), (word & (0x00FFFFFF, 0x0000FFFF, 0x000000FF, 0)[lane]) | ((old << shift) & 0xFFFFFFFF))
                cases += 1
        for words, frame in ((self.words, 96), (self.truth, 104)):
            model = TableFadeOracle(words, fixture(value=0, active=0)).run()
            for index, offset in enumerate((0x48, 0x3C, 0x30, 0x24)):
                at = STACK - frame + offset
                self.assertEqual(bytes(model.memory[at + j] for j in range(11)), TABLE[index * 12:index * 12 + 11])
                self.assertEqual(model.memory[at + 11], ((at + 11 - STACK) * 17 + 0xA5) & 255)
        self.receipt('partial-words', merge_cases=cases, all_four_lanes=True, four_three_byte_tails_preserve_padding=True,
            LWR_reads_aligned_word_SWR_records_selected_byte_writes=True,
            project64_interpreter_reference='https://github.com/project64/project64/blob/develop/Source/Project64-core/N64System/Interpreter/InterpreterOps.cpp',
            low_word_BE_model_not_full_bus_TLB_or_64bit_CPU=True)

    def test_03_bounded_guest_semantics_snapshots_and_live_helpers(self):
        count, visits, private_differences = 0, set(), 0
        for index in range(11):
            limit = TABLE[24 + index]
            values = sorted({v for v in (0, 1, 127, 128, 254, 255, limit - 1, limit, limit + 1) if 0 <= v <= 255})
            for value in values:
                for active in (0, 1, 255):
                    for step in (0, 1, 0xFFFFFFFF, 16, 0xFFFFFFE0, 0x80000000, 0x7FFFFFFF, 65536):
                        for mode in range(4):
                            memory = fixture(index, value, active, step)
                            expected, result, calls = reference(memory, mode=mode)
                            pair = [TableFadeOracle(w, memory, mode=mode).run() for w in (self.words, self.truth)]
                            for model in pair:
                                self.assertEqual((external(model.memory), model.r[2], model.calls), (external(expected), result, calls))
                            private_differences += pair[0].memory != pair[1].memory or pair[0].r != pair[1].r
                            visits |= pair[1].visits
                            count += 1
        self.assertGreater(private_differences, 0)
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 412, 4)) - {source.ENTRY + 0x130})
        self.receipt('semantics', paired_cases=count, full_record_and_external_memory_equal=True, private_state_differences=private_differences,
            visited_retail_words=len(visits), retained_unreachable_store_offset=304,
            snapshots_survive_provider_table_writes=True, index_snapshot_but_live_step_and_width=True,
            full_word_clamp_and_completion_before_byte_truncation=True, domain_indices=[0, 10], not_matching_qualification=True)

    def test_04_every_compiled_semantic_control_is_effective(self):
        probes = [(0, 127, 1, 1, 0), (3, 1, 0, 1, 0), (6, 1, 0, 0xFFFFFFFF, 0), (0, 1, 1, 1, 2), (3, 255, 1, 16, 3), (0, 0, 0, 1, 0)]
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            _, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            count = 0
            for index, value, active, step, mode in probes:
                memory = fixture(index, value, active, step)
                expected, result, calls = reference(memory, mode=mode)
                model = TableFadeOracle(words, memory, mode=mode).run()
                count += (external(model.memory), model.r[2], model.calls) != (external(expected), result, calls)
            self.assertGreater(count, 0, name)
        self.receipt('controls', effective_compiled_guest_negatives=len(controls()), no_guards_or_profiles_used=True)

    def test_05_native32_all_intensity_modes_and_live_provider_boundaries(self):
        defaults = ','.join(str(v) for v in TABLE)
        harness = '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
''' + source.DECLARATIONS + '''
ByteTable11_19A8B0 D_8008CBC4,D_8008CBD0,D_8008CBDC,D_8008CBE8;s32 D_800BE9E4;
static u8 original[48]={''' + defaults + '''};
static u8 record[80] __attribute__((aligned(16))),expected[80] __attribute__((aligned(16)));
static u32 mode,calls,scale,sequence_error;
static u32 half(u8 *p){union{u16 n;u8 b[2];}v;v.b[0]=p[0];v.b[1]=p[1];return v.n;}
static void sethalf(u8 *p,u32 n){union{u16 n;u8 b[2];}v;v.n=(u16)n;p[0]=v.b[0];p[1]=v.b[1];}
static s32 signedhalf(u8 *p){u32 n=half(p);return n>=32768?(s32)n-65536:(s32)n;}
static void effect(u8 *p,u32 *step,u8 tables[48],u32 move){u32 i;
 if(move){
  if(mode==1||mode==3){sethalf(p+0x14,mode==1?0x8123:32767);p[0x2C]=10;p[0x24]=0;}
  if(mode)*step=mode==1?0xFFFFFFFDu:mode==2?2u:7u;
  if(mode==2||mode==3)for(i=0;i<48;i++)tables[i]=(u8)(61+i*23);
 }else if(mode==2)sethalf(p+0x22,0xBEEF);else if(mode==3)sethalf(p+0x14,0xA55A);
}
static void readtables(u8 t[48]){u32 i,j;ByteTable11_19A8B0 *p[4]={&D_8008CBC4,&D_8008CBD0,&D_8008CBDC,&D_8008CBE8};
 for(i=0;i<4;i++)for(j=0;j<11;j++)t[i*12+j]=p[i]->values[j];}
static void writetables(u8 t[48]){u32 i,j;ByteTable11_19A8B0 *p[4]={&D_8008CBC4,&D_8008CBD0,&D_8008CBDC,&D_8008CBE8};
 for(i=0;i<4;i++)for(j=0;j<11;j++)p[i]->values[j]=t[i*12+j];}
__attribute__((noinline,noclone)) void func_1516F864(u8 *p){u8 t[48];u32 step=(u32)D_800BE9E4;
 if(calls||p!=record)sequence_error=1;calls++;readtables(t);effect(p,&step,t,1);writetables(t);D_800BE9E4=(s32)step;}
__attribute__((noinline,noclone)) void func_1516F94C(u8 *p,u32 s){u8 t[48];u32 step=(u32)D_800BE9E4;
 if(calls!=1||p!=record)sequence_error=1;calls++;scale=s;readtables(t);effect(p,&step,t,0);writetables(t);D_800BE9E4=(s32)step;}
''' + source.SELECTED + '''
static s32 (*volatile invoke)(u8 *)=func_1516F024;
static u32 model(u8 *p,u32 *step,u8 t[48],u32 *want_scale,u32 *want_calls){u8 snap[48];u32 i,index=p[0x2C],v=p[0x1F],limit,n;
 for(i=0;i<48;i++)snap[i]=t[i];
 if(p[0x24]){limit=snap[24+index];if(v!=limit){v+=*step*16u;if((s32)v>(s32)limit)v=limit;p[0x1F]=(u8)v;}}
 else if(v){v-=*step*snap[36+index];if((s32)v<0)v=0;p[0x1F]=(u8)v;}
 if(!p[0x24]&&!v){*want_calls=0;return 1;}
 effect(p,step,t,1);n=(u32)signedhalf(p+0x14)+*step*snap[12+index];
 sethalf(p+0x16,n);sethalf(p+0x14,n);if(index==3)sethalf(p+0x18,100);
 *want_scale=snap[index];*want_calls=2;effect(p,step,t,0);return 0;}
static int run(void){u32 index,v,a,d,j,k,n=0,want_calls,want_scale,want_result,want_step,result;u8 t[48],actual[48];
 u32 steps[8]={0,1,0xFFFFFFFFu,16,0xFFFFFFE0u,0x80000000u,0x7FFFFFFFu,65536};u8 active[3]={0,1,255};
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(ByteTable11_19A8B0)!=11)return 10;
 for(index=0;index<11;index++)for(v=0;v<256;v++)for(a=0;a<3;a++)for(d=0;d<8;d++)for(mode=0;mode<4;mode++){
  for(j=0;j<80;j++)record[j]=expected[j]=(u8)(j*13+n*17+0xC5);
  record[0x2C]=expected[0x2C]=(u8)index;record[0x1F]=expected[0x1F]=(u8)v;record[0x24]=expected[0x24]=active[a];
  sethalf(record+0x14,n*257);sethalf(expected+0x14,n*257);n++;
  for(j=0;j<48;j++)t[j]=original[j];writetables(t);D_800BE9E4=(s32)steps[d];want_step=steps[d];
  calls=scale=sequence_error=want_calls=want_scale=0;want_result=model(expected,&want_step,t,&want_scale,&want_calls);
  result=(u32)invoke(record);if(result!=want_result||calls!=want_calls||sequence_error)return 11;
  if(calls&&scale!=want_scale)return 12;if((u32)D_800BE9E4!=want_step)return 13;
  for(j=0;j<80;j++)if(record[j]!=expected[j])return 14;
  readtables(actual);for(j=0;j<4;j++)for(k=0;k<11;k++)if(actual[j*12+k]!=t[j*12+k])return 15;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        variants = [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)]
        variants += [('negative-' + name, body, '-O2', False) for name, body in controls().items()]
        for name, body, profile, expected in variants:
            path = self.out / ('native-' + name + '.c')
            path.write_text(harness.replace(source.SELECTED, body))
            result = subprocess.run(['cc', '-m32', profile, '-std=c11', '-ffreestanding', '-fno-strict-aliasing', '-fno-stack-protector',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
                '-Wno-unused-parameter', *(['-Wno-unused-variable'] if not expected else []),
                str(path), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(path.with_suffix(''))], timeout=30)
            self.assertEqual(result.returncode == 0, expected, (name, result.returncode))
        self.receipt('native', cases_per_O2_O0=270336, all_256_values_11_indices_eight_steps_three_flags_four_providers=True,
            exact_11_byte_struct_size=True, eight_effective_controls=True,
            native_byte_and_halfword_ABI_not_BE_memory_or_arbitrary_index_claim=True)

    def test_06_current_real_movement_and_velocity_helpers(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        connected = {}
        for entry, rom, count in ((source.MOVE, 0x19CD14, 34), (source.SCALE, 0x19CDFC, 14), (0x1516F8EC, 0x19CD9C, 12), (0x1516F91C, 0x19CDCC, 12)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        count = 0
        for index in range(11):
            for value in (0, 1, 128, 255):
                for active in (0, 1):
                    for step in (1, 0xFFFFFFFF, 0x80000000):
                        memory = fixture(index, value, active, step)
                        pair = [TableFadeOracle(w, memory, connected=connected).run() for w in (self.words, self.truth)]
                        self.assertEqual((external(pair[0].memory), pair[0].r[2], pair[0].calls), (external(pair[1].memory), pair[1].r[2], pair[1].calls))
                        count += 1
        self.receipt('chain', paired_cases=count, actual_current_helper_words=[34, 14, 12, 12],
            all_helper_calls_connected_not_opaque=True, no_full_gameplay_or_hardware_claim=True)

    def test_07_fired_fault_prefixes_keep_private_frame_failure_visible(self):
        count = differences = 0
        for memory in (fixture(0, 0, 0), fixture(3, 128, 1), fixture(6, 1, 0, 0xFFFFFFFF)):
            whole = [TableFadeOracle(w, memory).run() for w in (self.words, self.truth)]
            for fault in range(min(m.accesses for m in whole)):
                pair = [TableFadeOracle(w, memory, fault=fault) for w in (self.words, self.truth)]
                for model in pair:
                    with self.assertRaises(AccessFault):
                        model.run()
                differences += (pair[0].r, pair[0].memory, pair[0].events) != (pair[1].r, pair[1].memory, pair[1].events)
                count += 1
        self.assertEqual(differences, count)
        self.receipt('prefixes', paired_fired_guest_faults=count, literal_private_failures=differences,
            first_frame_and_RA_store_diverge=True, no_affine_private_acceptance_or_portable_C_fault_claim=True)

    def test_09_all_52_live_inputs_and_immutable_capture_controls(self):
        source.freeze(self.root, self.out)
        def unchanged():
            for key, relative in source.PATHS.items():
                self.assertEqual((self.root / relative).read_bytes(), (self.out / ('before-' + key)).read_bytes(), key)
        unchanged()
        layout = audit_layout(self.root / source.PATHS['elf'], self.root / 'conker')
        self.assertEqual((layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']), (True, 189088, 720, 0))
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        for relative in source.PATHS.values():
            path = self.root / relative
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    unchanged()
        self.receipt('unchanged-inputs', all_52_live_inputs_fixed=True, all_52_live_and_before_capture_flips_rejected=True,
            protected_data=layout, no_production_source_guard_profile_ELF_or_progress_change=True)


if __name__ == '__main__':
    unittest.main()
