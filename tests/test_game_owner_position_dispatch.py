"""Retail position capture, selected-actor indexing, byte ABI and overflow removal."""

import csv
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_position_dispatch as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_actor_triangle_transform_match import put
from tools.tests.test_game_owner_actor_update_match import read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete


ROOT = Path(__file__).resolve().parents[2]
POINTS = ((0, 0x80000000, 0x3F800000), (0xBF800000, 0x41280000, 0xC3400000),
          (0x7F7FFFFF, 0xFF7FFFFF, 0x00800000), (1, 0x80000001, 0x3EAAAAAB),
          (0x7F800000, 0xFF800000, 0x7FC12345), (0x7FA12345, 0xFFC12345, 1))
ACTOR = 0x28000
STRIDE = 0x32C


def corpus():
    for index in range(256):
        yield index, (index * 0x1234567) & 0xFFFFFFFF, POINTS[index % len(POINTS)], index & 1
    for mode in range(256):
        yield mode % 27, mode, POINTS[mode % len(POINTS)], mode & 1
    for index, mode, point, mutation in itertools.product((0, 1, 5, 26), (0, 128, 255, 0xDEADBEEF), POINTS, (0, 1)):
        yield index, mode, point, mutation


def fixture(case, delta=0, alias=False):
    index, mode, point, _ = case
    actor = source.ACTORS + delta + 4 * STRIDE if alias else ACTOR + delta
    memory = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-0x200, 0x100)}
    memory.update({actor + i: 0xA5 for i in range(STRIDE)})
    put(memory, source.CURRENT + delta, actor)
    put(memory, actor + 0x124, index, 1)
    for i, value in enumerate(point):
        put(memory, actor + 0x14 + 4 * i, value)
    return memory, actor


class DispatchOracle(TimingOracle):
    def __init__(self, words, case, phase=0, delta=0, alias=False, entry=source.ENTRY, connected=None):
        memory, self.actor = fixture(case, delta, alias)
        self.case, self.delta, self.captures = case, delta, []
        super().__init__(words, memory, phase=phase, entry=entry, arguments=(case[1],), connected=connected)

    def record_call(self, target):
        if target == source.ENTRY:
            self.calls.append(('ENTER', self.arguments(1)))
            return
        assert target == source.DISPATCH + self.delta, hex(target)
        args = self.arguments(7)
        position = tuple(read(self.memory, args[2] + i * 4) for i in range(3))
        self.captures.append((args, position))
        self.calls.append(('DISPATCH', args))

    def hook(self, target):
        assert target == source.DISPATCH + self.delta
        if self.case[3]:
            # The provider can change the live actor/global without changing its snapshot.
            self.put(source.CURRENT + self.delta, 0x27000 + self.delta, 4)
            for i in range(3):
                self.put(self.actor + 0x14 + i * 4, 0x3F800000 + i, 4)
            self.put(self.actor + 0x124, 0xFE, 1)
        args, position = self.captures[-1]
        assert position == tuple(read(self.memory, args[2] + i * 4) for i in range(3))
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo = 0x87654321, 0x12345678


def native_harness(body, cases):
    rows = ['{' + ','.join('0x%Xu' % v for v in (c[0], c[1], *c[2], c[3])) + '}' for c in cases]
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef float f32;
typedef struct {f32 unk0,unk4,unk8;} struct17;
typedef struct {u8 p0[0x14];f32 x_position,y_position,z_position;u8 p1[0x104];u8 unk124;u8 tail[0x207];} struct127;
typedef char actor_stride[sizeof(struct127)==0x32C?1:-1];
typedef char selector_offset[__builtin_offsetof(struct127,unk124)==0x124?1:-1];
struct127 D_800CC2D0[26],*D_800D154C;
void func_15103E40(struct127 *,struct127 *,struct17 *,u8,s32,s32,s32);
''' + body + '''
typedef struct {u32 index,mode,x,y,z,mutation;} Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;static struct127 actor;static int calls,error;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
void func_15103E40(struct127 *selected,struct127 *current,struct17 *point,u8 mode,s32 a,s32 b,s32 c){
    struct127 *expected=item->index?&D_800CC2D0[item->index-1]:&actor;
    if(calls++ || selected!=expected || current!=&actor || mode!=(u8)item->mode ||
       a!=0 || b!=255 || c!=0 || word(point->unk0)!=item->x ||
       word(point->unk4)!=item->y || word(point->unk8)!=item->z)error=1;
    if(item->mutation){actor.x_position=8.0f;actor.y_position=9.0f;actor.z_position=10.0f;actor.unk124=254;D_800D154C=0;}
    if(word(point->unk0)!=item->x || word(point->unk4)!=item->y || word(point->unk8)!=item->z)error=1;
}
static int test_all(void){
    u32 n,i;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;
        for(i=0;i<sizeof(actor);i++)((u8 *)&actor)[i]=0xA5;
        D_800D154C=&actor;actor.unk124=(u8)item->index;
        actor.x_position=real(item->x);actor.y_position=real(item->y);actor.z_position=real(item->z);
        func_15070C40((u8)item->mode);
        if(error || calls!=1)return 23;
        for(i=0;i<sizeof(actor);i++){
            if((i>=0x14&&i<0x20)||i==0x124)continue;
            if(((u8 *)&actor)[i]!=0xA5)return 24;
        }
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class OwnerPositionDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.installed = source.digest((ROOT / source.SOURCE).read_bytes()) != source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT, cls.output)
        else:
            source.freeze(ROOT, cls.output)
            if not (cls.output / 'first-link.json').exists():
                source.qualify(ROOT, cls.output)
                source.make_shadow(ROOT, cls.output)
                source.predict(ROOT, cls.output)
        cls.values = source.snapshot(cls.output)
        cls.obj, diagnostic = source.compile_owner(ROOT, cls.output, source.DECLARATIONS + source.SELECTED, 'fresh-selected')
        if diagnostic:
            raise ValueError(diagnostic)
        image, funcs = source.link_owner(ROOT, cls.output, cls.obj, source.OWNER)
        cls.words = list(struct.unpack_from('>39I', image, funcs[source.FUNCTION]['value']))
        cls.truth = list(struct.unpack_from('>39I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.cases = list(corpus())
        cls.native_cases = [c for c in cls.cases if c[0] <= 26 and c[2] in POINTS[:4]]
        cls.receipt = dict(installed=cls.installed, cases=len(cls.cases), native_cases=len(cls.native_cases),
                           guards=0, matching_credit=int(cls.installed))

    @classmethod
    def tearDownClass(cls):
        (cls.output / 'test-receipt.json').write_text(json.dumps(cls.receipt, indent=2) + '\n')
        print('position dispatch qualification:', cls.receipt)

    def test_01_exact_C_GNU_original_and_canonical_layout(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual(source.payload(self.obj), source.payload(source.original(ROOT, self.output)))
        check = source.DECLARATIONS + '''
typedef char actor_size[sizeof(struct127)==0x32C?1:-1];
typedef char xyz_offset[(u32)&((struct127 *)0)->x_position==0x14?1:-1];
typedef char y_offset[(u32)&((struct127 *)0)->y_position==0x18?1:-1];
typedef char z_offset[(u32)&((struct127 *)0)->z_position==0x1C?1:-1];
typedef char index_byte[sizeof(((struct127 *)0)->unk124)==1?1:-1];
typedef char index_offset[(u32)&((struct127 *)0)->unk124==0x124?1:-1];
typedef char vector_size[sizeof(struct17)==12?1:-1];
''' + source.SELECTED
        obj, diagnostic = source.compile_owner(ROOT, self.output, check, 'canonical-layout')
        self.assertEqual(diagnostic, '')
        self.assertEqual(source.payload(obj), source.payload(self.obj))

    def test_02_complete_guest_cases_call_ABI_snapshot_and_aliases(self):
        visits = set()
        for case, phase, alias in itertools.product(self.cases, (0, 8), (False, True)):
            a = DispatchOracle(self.truth, case, phase, alias=alias).run()
            b = DispatchOracle(self.words, case, phase, alias=alias).run()
            self.assertEqual(complete(a), complete(b))
            self.assertEqual(a.captures, b.captures)
            args, position = b.captures[0]
            selected = source.ACTORS + (case[0] - 1) * STRIDE if case[0] else b.actor
            self.assertEqual(args, (selected, b.actor, STACK + phase - 12, case[1] & 255, 0, 255, 0))
            self.assertEqual(position, case[2])
            self.assertEqual(len(b.captures), 1)
            for reg in (*range(16, 24), 28, 29, 30, 31):
                self.assertEqual(b.r[reg], b.before[reg])
            visits.update(b.visits)
        self.assertTrue(set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)) <= visits)
        self.receipt.update(complete_model_cases=len(self.cases)*4, all39_words_visited=True,
                            all256_indices_guest_only_outside_0_to_26=True, all256_modes=True,
                            current_equals_selected_aliases=True, hardware_FCSR_MMU_claimed=False)

    def test_03_native32_UBSan_three_optimizations_and_effective_negatives(self):
        def run(body, label, optimization):
            unit = self.output / (label + '.c')
            unit.write_text(native_harness(body, self.native_cases))
            binary = self.output / (label + optimization)
            args = ['gcc', '-m32', optimization, '-std=c99', '-fno-strict-aliasing', '-ffreestanding',
                    '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-msse2',
                    '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off', '-fsanitize=undefined',
                    '-fsanitize-undefined-trap-on-error', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(unit), '-o', str(binary)]
            p = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            return subprocess.run([str(binary)], capture_output=True, timeout=30).returncode
        for optimization in ('-O0', '-O2', '-O3'):
            self.assertEqual(run(source.SELECTED, 'native', optimization), 0)
        negatives = {
            'current-only': source.SELECTED.replace('actor->unk124 != 0', '0'),
            'next-row': source.SELECTED.replace('actor->unk124 - 1', 'actor->unk124'),
            'wrong-x': source.SELECTED.replace('position.unk0 = actor->x_position', 'position.unk0 = actor->y_position'),
            'wrong-y': source.SELECTED.replace('position.unk4 = actor->y_position', 'position.unk4 = actor->z_position'),
            'wrong-z': source.SELECTED.replace('position.unk8 = actor->z_position', 'position.unk8 = actor->x_position'),
            'wrong-mode': source.SELECTED.replace('&position, mode,', '&position, mode ^ 1,'),
            'wrong-flag': source.SELECTED.replace('mode, 0, 0xFF, 0', 'mode, 1, 0xFF, 0'),
            'wrong-sentinel': source.SELECTED.replace('mode, 0, 0xFF, 0', 'mode, 0, 0xFE, 0'),
        }
        for name, body in negatives.items():
            self.assertNotEqual(body, source.SELECTED)
            self.assertEqual(run(body, name, '-O2'), 23, name)
        self.receipt.update(native_optimizations=3, trap_UBSan=True, native_defined_index_range=[0,26],
                            compiled_semantic_negatives=len(negatives))

    def test_04_two_complete_original_wrappers_and_direct_call_inventory(self):
        symbols = load_symbol_addrs(str(ROOT / 'conker/symbol_addrs.us.txt'))
        rows = list(csv.DictReader((ROOT / 'conker/progress.csv').open()))
        add_retail_lengths(rows, 'us', DEFAULT_SEGMENTS['us'], symbols)
        rom = self.values['conker/conker.us.bin']
        opcode = 0x0C000000 | (source.ENTRY >> 2 & 0x3FFFFFF)
        found = []
        for row in rows:
            if row['version'] != 'us' or row['section'] not in DEFAULT_SEGMENTS['us']:
                continue
            base, start = DEFAULT_SEGMENTS['us'][row['section']]
            entry = function_vram(row, symbols)
            words = struct.unpack_from('>%dI' % row['_retail_nwords'], rom, entry-base+start)
            found.extend((row['function'], entry+i*4) for i,w in enumerate(words) if w == opcode)
        self.assertEqual(found, [('func_15070CDC',0x15070CE8), ('func_15070D00',0x15070D0C)])
        count = 0
        for entry, mode in ((0x15070CDC,1),(0x15070D00,0)):
            wrapper = list(struct.unpack_from('>9I', rom, entry-0x15000000+0x2D4B0))
            for case in self.cases[::13]:
                connected = dict(zip(range(source.ENTRY,source.ENTRY+156,4),self.words))
                model = DispatchOracle(wrapper, case, entry=entry, connected=connected).run()
                self.assertEqual(model.captures[0][0][3], mode)
                self.assertEqual(len(model.captures), 1)
                for reg in (*range(16,24),28,29,30,31):
                    self.assertEqual(model.r[reg], model.before[reg])
                count += 1
        self.receipt.update(all_direct_retail_call_sites=found, complete_original_wrapper_cases=count,
                            underlying_dispatch_provider_bounded=True)

    def test_05_independent_global_HI_LO_carry_rebases(self):
        obj = source.original(ROOT, self.output)
        paths = (self.obj, obj)
        count = 0
        for delta in (0x10000,0x13AC0,0x1BD30):
            images = []
            for j,path in enumerate(paths):
                elf, script = self.output / ('rebase-%d-%d.elf'%(delta,j)), self.output / 'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                args = ['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                        '--defsym=D_800D154C=0x%X'%(source.CURRENT+delta),
                        '--defsym=D_800CC2D0=0x%X'%(source.ACTORS+delta),
                        '--defsym=func_15103E40=0x%X'%(source.DISPATCH+delta),
                        '-o',str(elf),str(path)]
                subprocess.run(args,capture_output=True,check=True)
                images.append(list(struct.unpack_from('>39I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case in self.cases[::17]:
                model = DispatchOracle(images[0],case,delta=delta).run()
                args,position = model.captures[0]
                self.assertEqual(args[0],source.ACTORS+delta+(case[0]-1)*STRIDE if case[0] else ACTOR+delta)
                self.assertEqual(position,case[2]);count+=1
        self.receipt.update(independent_symbol_rebase_phases=count, rebase_sets=3)

    def test_06_target_only_closed_overflow_and_protected_image(self):
        report = json.loads((self.output/'first-link.json').read_text())
        self.assertEqual(report['moved_overflow_bodies'],6)
        self.assertEqual(len(report['relocated_trampolines']),4)
        self.assertEqual(report['removed_overflow_bytes'],160)
        self.assertTrue(report['protected_sections_equal'])
        truth = self.values['conker/conker.us.bin'][source.ROM:source.ROM+source.SIZE]
        baseline = self.output/'before-conker_build_conker.us.elf'
        linked = self.output/'first-linked.elf'
        fresh = source.inspect_image(baseline, linked, truth, ROOT/'conker')
        self.assertTrue(fresh['complete_ELF_byte_prediction'])
        self.assertEqual(fresh['metadata_exclusions'],0)
        for label, address in (('other-code',0x15001000),('data',0x80082B20),('overflow',0x15F00000)):
            image = bytearray(linked.read_bytes())
            at = source.elf_slot_offset(image,address,4)
            image[at] ^= 1
            mutant = self.output/('negative-image-'+label+'.elf')
            mutant.write_bytes(image)
            with self.assertRaises(ValueError):
                source.inspect_image(baseline,mutant,truth,ROOT/'conker')
        image = bytearray(linked.read_bytes())
        image[20] ^= 1
        mutant = self.output/'negative-image-header.elf'
        mutant.write_bytes(image)
        with self.assertRaises(ValueError):
            source.inspect_image(baseline,mutant,truth,ROOT/'conker')
        self.receipt.update(complete_ELF_byte_prediction=True,image_negative_controls=4)
