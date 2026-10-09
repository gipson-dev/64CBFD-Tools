"""Direct constructor match, defined native fields, real callees and linked audit."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_ribbon_effect_constructor_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, emit_padded_assembly, parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_record_ring_shaping_recovery import ShapingOracle
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
INSERT = screen.TYPES.split('\n', 1)[1] + 'f32 func_151423D8(u8);\n\n'
CREATED, PAYLOAD, TABLE = 0x20000, 0x21000, 0x8009A220
PATTERNS = (0, 0x80000000, 1, 0x80000001, 0x3F800000, 0x41400000,
    0x7F7FFFFF, 0xFF7FFFFF, 0x7F800000, 0xFF800000, 0x7FC12345, 0x7F812345)
WIDTHS = (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0xFFFF0001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def source_shapes(root):
    source = (root / SOURCE).read_text()
    old = source.replace(screen.SELECTED, screen.ORIGINAL).replace(INSERT, '')
    assert old.count(screen.ORIGINAL) == 1
    new = old.replace('/* Non-matching placeholders', INSERT + '/* Non-matching placeholders', 1)
    return old, new.replace(screen.ORIGINAL, screen.SELECTED)


def symbol_size_offset(data):
    header = ELF_HEADER.unpack_from(data)
    headers = [SECTION_HEADER.unpack_from(data, header[6] + i * header[11]) for i in range(header[12])]
    offsets = []
    for section in headers:
        if section[1] != 2:
            continue
        strings = headers[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for offset in range(section[4], section[4] + section[5], section[9]):
            symbol = SYMBOL.unpack_from(data, offset)
            if names[symbol[0]:].split(b'\0', 1)[0].decode() == screen.FUNCTION:
                assert symbol[1] == screen.ENTRY and symbol[3] & 15 == 2
                offsets.append(offset + 8)
    assert len(offsets) == 1
    return offsets[0]


def fixture(table, seed=0):
    memory = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x160)}
    for base in (CREATED, PAYLOAD):
        memory.update({base + i: (i * 13 + seed * 11 + 0xA5) & 255 for i in range(-16, 0x300)})
    put(memory, CREATED + 0x98, PAYLOAD)
    for i, value in enumerate(table):
        put(memory, TABLE + i * 4, value)
    return memory


def lookup(angle, table):
    angle &= 255
    index = 64 - (angle & 63) if angle & 64 else angle & 63
    return table[index] ^ (0 if angle & 192 in (0, 192) else 0x80000000)


def expected(memory, args, table, phase=0):
    kind, x, y, z, count, yaw, pitch, speed, duration, gravity, threshold, channel = args
    frame = STACK + phase - 184
    request = bytearray(memory[frame + 0x9C + i] for i in range(28))
    payload = bytearray(memory[frame + 0x7C + i] for i in range(32))
    render = bytearray(memory[frame + 0x4C + i] for i in range(32))
    struct.pack_into('>3IHHI', request, 0, x, y, z, duration & 65535, 1, 1)
    request[21] = (count + 3) & 255
    pitch_value, pitch_quarter, yaw_value, yaw_quarter = [lookup(a, table)
        for a in (pitch, pitch - 64, yaw, yaw - 64)]
    lateral = bits(floating(speed) * floating(pitch_value))
    vx = bits(floating(lateral) * floating(yaw_quarter))
    vy = bits(floating(speed ^ 0x80000000) * floating(pitch_quarter))
    vz = bits(floating(lateral) * floating(yaw_value))
    struct.pack_into('>5I', payload, 0, gravity, vx, vy, vz, threshold)
    payload[24:28] = bytes((40 if kind & 255 == 10 else 8, kind & 255, 255, 255))
    struct.pack_into('>7I', render, 0, 0, 1, 0x160600, 3, 16, 128, 32)
    render[28:30] = bytes((0, 9))
    call = ('create', bytes(request), bytes(payload), (0, 1, 0, 0, 0, 0, 0, 0, 0),
        bytes(render), (0, channel & 255, 1))
    return [('angle', a & 255) for a in (pitch, pitch - 64, yaw, yaw - 64)] + [call]


def cases():
    for byte in range(256):
        width = WIDTHS[byte % len(WIDTHS)]
        pattern = PATTERNS[byte % len(PATTERNS)]
        yield (0x81234500 | byte, pattern, pattern ^ 0x80000000, pattern,
            width, 0xFFFF0000 | byte, (byte * 73 + 11) | 0x80000000,
            pattern, width, pattern, pattern ^ 0x80000000, byte | 0xABCDE000)
    for values in itertools.product((9, 10, 11, 255), WIDTHS, PATTERNS):
        kind, width, pattern = values
        yield (kind, pattern, bits(3.25), bits(-2.5), width, width, width ^ 0x80000000,
            pattern, width, pattern, pattern, width)


class ConstructorOracle(ShapingOracle):
    def __init__(self, words, memory, args, table, result=CREATED, phase=0, clobber=False,
            entry=screen.ENTRY, symbols=None, connected=None):
        TriangleOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=args, connected=connected)
        self.fcsr = self.initial_fcsr = 0
        self.table, self.result, self.clobber = table, result, clobber
        self.symbols, self.raw_calls = symbols or screen.SYMBOLS, []

    def packet(self, address, size):
        return bytes(self.get(address + i, 1) for i in range(size))

    def record_call(self, target):
        if target == self.symbols['func_151423D8']:
            self.raw_calls.append(('angle', self.r[4]))
            self.calls.append(('angle', self.r[4]))
        elif target == self.symbols['func_15147DA0']:
            args = self.arguments(15)
            self.raw_calls.append(('create', args))
            self.calls.append(('create', self.packet(args[0], 28), self.packet(args[1], 32),
                args[2:11], self.packet(args[11], 32), args[12:]))
        elif target == 0x15147A80:
            self.raw_calls.append(('allocate', self.arguments(11)))
        else:
            assert target == 0x10022EC0, hex(target)
            self.raw_calls.append(('copy', self.arguments(3)))

    def hook(self, target):
        role, args = self.raw_calls[-1]
        result = self.result
        if role == 'copy':
            destination, source, size = args
            assert size == 32
            for i in range(size):
                self.put(destination + i, self.get(source + i, 1), 1)
            result = destination
        if self.clobber:
            for i in range(4 if role == 'angle' else 15 if role == 'create' else 4):
                self.put(self.r[29] + i * 4, 0x76540000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        if role == 'angle':
            self.f[0] = lookup(args, self.table)
        else:
            self.r[2] = result & 0xFFFFFFFF


class GameRibbonEffectConstructorTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-ribbon-effect-constructor-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>107I', rom, screen.ROM))
        cls.lookup_words = list(struct.unpack_from('>27I', rom, 0x16F888))
        cls.creator_words = list(struct.unpack_from('>70I', rom, 0x175250))
        elf = sections(cls.root / 'conker/build/conker.us.elf')
        chunks = [data[TABLE - address:TABLE - address + 260] for address, data in elf.values()
            if address <= TABLE and TABLE + 260 <= address + len(data)]
        assert len(chunks) == 1
        cls.table = list(struct.unpack('>65I', chunks[0]))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            assert screen.ORIGINAL in (cls.root / SOURCE).read_text()
            paths = {'source': SOURCE, 'elf': 'conker/build/conker.us.elf',
                'guards': 'conker/retail_word_patches.us.csv', 'progress': 'conker/progress.csv'}
            hashes = {}
            for name, path in paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')

    def receipt(self, name, value):
        (self.out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def test_01_full_direct_match_and_abi_shape(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
            (107, 184, 0, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertEqual(sum(map(len, self.meta['relocations'].values())), 5)
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            guards = list(csv.DictReader(stream))
        self.assertFalse(any(row['function'] == screen.FUNCTION for row in guards))
        self.receipt('shape', dict(self.meta, source_sha256=hashlib.sha256(screen.SELECTED.encode()).hexdigest(),
            target_guards=0, raw_byte_exact=True))

    def test_02_guest_mixed_abi_all_bytes_and_untouched_holes(self):
        coverage, count = set(), 0
        for args, phase, clobber, result in itertools.product(cases(), (0, 8), (False, True), (0, CREATED)):
            memory = fixture(self.table, count % 3)
            reference = expected(memory, args, self.table, phase)
            for words in (self.words, self.retail):
                model = ConstructorOracle(words, memory, args, self.table, result, phase, clobber).run()
                self.assertEqual(model.calls, reference)
                self.assertEqual(model.r[2], result)
                self.assertEqual(bytes(model.memory[CREATED + i] for i in range(0x100)),
                    bytes(memory[CREATED + i] for i in range(0x100)))
                coverage.update(model.visits)
            count += 1
        self.assertEqual(len(coverage), 107)
        self.receipt('guest', dict(cases=count, executions=count * 2, covered_words=107,
            raw_private_packets_including_holes=True, all_kind_yaw_pitch_channel_bytes=True,
            scratch_gpr_fp_and_argument_home_clobbers=True, hardware_FCSR_proven=False))

    def test_03_real_lookup_and_creator_connected(self):
        connected = dict(zip(range(0x151423D8, 0x15142444, 4), self.lookup_words))
        connected.update(zip(range(0x15147DA0, 0x15147EB8, 4), self.creator_words))
        count = 0
        for byte, result in itertools.product(range(256), (0, CREATED)):
            args = (byte, bits(1.25), bits(-2.5), bits(3.75), byte, byte, byte * 73,
                bits(12.), byte | 0x8000, bits(-1.), bits(4.), byte)
            memory = fixture(self.table, byte % 3)
            reference = expected(memory, args, self.table)
            model = ConstructorOracle(self.words, memory, args, self.table, result=result,
                connected=connected).run()
            self.assertEqual(model.calls, reference)
            self.assertEqual(model.r[2], result)
            if result:
                self.assertEqual(model.packet(PAYLOAD, 32), reference[-1][2])
                self.assertEqual(model.packet(PAYLOAD + 0x28, 32), reference[-1][4])
                self.assertEqual(model.packet(PAYLOAD + 0x20, 6), bytes((1, 0, 0, 0, 0, 0)))
            else:
                self.assertEqual(model.packet(PAYLOAD, 0x100), bytes(memory[PAYLOAD + i] for i in range(0x100)))
            count += 1
        self.receipt('connected', dict(cases=count, actual_lookup_words=27, actual_creator_words=70,
            table_from_current_guest_ELF=True, allocation_and_memcpy_bounded_hooks=True,
            whole_script_caller_or_hardware_proven=False))

    def test_04_copied_owner_and_actual_padder(self):
        old, new = source_shapes(self.root)
        objects = []
        for name, source in (('before', old), ('after', new)):
            obj, diagnostics = compile_owner(self.root, self.out, source, name)
            self.assertEqual(diagnostics, [])
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((self.out / (name + '.c')).relative_to(self.root / 'conker')),
                '--post-process', str(obj.relative_to(self.root / 'conker')),
                '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
        before, old_fn, old_rel = parse_object(objects[0])
        after, new_fn, new_rel = parse_object(objects[1])
        self.assertEqual(old_fn.keys(), new_fn.keys())
        for name, function in new_fn.items():
            if name == screen.FUNCTION:
                continue
            prior = old_fn[name]
            self.assertEqual((function['size'], after[function['value']:function['value'] + function['size']]),
                (prior['size'], before[prior['value']:prior['value'] + prior['size']]), name)
            self.assertEqual({o - function['value']: r for o, r in new_rel.items()
                if function['value'] <= o < function['value'] + function['size']},
                {o - prior['value']: r for o, r in old_rel.items()
                if prior['value'] <= o < prior['value'] + prior['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
        self.assertTrue(assembly)
        self.receipt('owner', dict(neighbors=len(new_fn) - 1, unchanged_pools_and_relative_relocations=True,
            diagnostics=0, actual_padder_accepts=True))

    def test_05_effective_compiled_negatives(self):
        args = next(cases())
        args = (10, *args[1:5], 35, 17, bits(12.), *args[8:])
        memory = fixture(self.table)
        reference = expected(memory, args, self.table)
        controls = {'angle-order': screen.SELECTED.replace('func_151423D8(pitch)', 'func_151423D8(yaw)', 1),
            'missing-special-flag': screen.SELECTED.replace('payload.flags = 0x28;', 'payload.flags = 8;'),
            'wrong-count': screen.SELECTED.replace('(u32)count + 3', '(u32)count + 2'),
            'wrong-speed-sign': screen.SELECTED.replace('-speed * pitchQuarter', 'speed * pitchQuarter'),
            'wrong-channel': screen.SELECTED.replace('&render, 0, channel, 1', '&render, 0, 0, 1')}
        args = (*args[:-1], 129)
        reference = expected(memory, args, self.table)
        for name, body in controls.items():
            _, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            model = ConstructorOracle(words, memory, args, self.table).run()
            self.assertNotEqual(model.calls, reference, name)
        self.receipt('negatives', dict(effective=list(controls)))

    def test_06_whole_ELF_and_progress_installation_audit(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        self.assertEqual(hashlib.sha256((self.root / 'conker/retail_word_patches.us.csv').read_bytes()).hexdigest(),
            baseline['guards'])
        current = (self.root / 'conker/build/conker.us.elf').read_bytes()
        before = (self.out / 'before-elf').read_bytes()
        if screen.SELECTED not in (self.root / SOURCE).read_text():
            self.assertEqual(current, before)
            self.receipt('audit', dict(installed=False, production_unchanged=True))
            return
        expected_elf = bytearray(before)
        offset = elf_slot_offset(before, screen.ENTRY, 428)
        expected_elf[offset:offset + 428] = struct.pack('>107I', *self.retail)
        size = symbol_size_offset(before)
        self.assertEqual(symbol_size_offset(current), size)
        self.assertEqual(struct.unpack_from('>I', before, size)[0], 12)
        self.assertEqual(struct.unpack_from('>I', current, size)[0], 428)
        struct.pack_into('>I', expected_elf, size, 428)
        self.assertEqual(current, bytes(expected_elf), 'unexpected ELF change outside target slot/size field')
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), (self.out / 'before-progress').read_bytes())
        audit = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('audit', dict(installed=True, whole_ELF_only_target_slot_and_symbol_size_changed=True,
            target_symbol_size_before=12, target_symbol_size_after=428,
            target_words=107, guards_unchanged=True, conversion_rows_unchanged=True,
            source_sha256=hashlib.sha256((self.root / SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest(), protected_data_layout=audit))

    def test_07_actual_native32_typed_callback_and_defined_packets(self):
        table = ','.join('0x%08Xu' % value for value in self.table)
        self.fixture = '''typedef unsigned char u8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
#define NULL ((void *)0)
''' + screen.TYPES + screen.DECLARATIONS + '''
static u32 input[12], wanted[5];
static unsigned char arena[256];
static int calls, error, success;
static f32 fromBits(u32 word) { union { u32 word; f32 value; } x; x.word=word; return x.value; }
static u32 toBits(f32 value) { union { u32 word; f32 value; } x; x.value=value; return x.word; }
static int equalFloat(f32 value,u32 word) {
    u32 actual=toBits(value);
    return actual==word || ((actual&0x7fffffff)>0x7f800000 && (word&0x7fffffff)>0x7f800000);
}
static u32 table[65]={''' + table + '''};
f32 func_151423D8(u8 angle) {
    u32 expectedAngle, word; int index;
    expectedAngle=input[calls<2?6:5]-(calls&1?64u:0u);
    if(calls>=4 || angle!=(u8)expectedAngle) error=1;
    calls++;
    index=angle&64?64-(angle&63):angle&63;
    word=table[index];
    if((angle&192)!=0 && (angle&192)!=192)word^=0x80000000u;
    return fromBits(word);
}
u8 *func_15147DA0(void *r,void *p,s32 a2,s32 a3,s32 a4,s32 a5,s32 a6,s32 a7,s32 a8,
    s32 a9,s32 a10,void *g,s32 a12,u8 channel,s32 context) {
    RibbonRequest15148F1C *request=r;
    RibbonPayload15148F1C *payload=p;
    RenderRecord15147DA0 *render=g;
    static u32 words[7]={0,1,0x160600,3,16,128,32};
    int i;
    if(calls!=4 || a2 || a3!=1 || a4 || a5 || a6 || a7 || a8 || a9 || a10 || a12 ||
        channel!=(u8)input[11] || context!=1) error=1;
    if(toBits(request->x)!=input[1] || toBits(request->y)!=input[2] || toBits(request->z)!=input[3] ||
        request->duration!=(s16)input[8] || request->mode!=1 || request->active!=1 ||
        request->count!=(u8)(input[4]+3u)) error=1;
    if(toBits(payload->gravity)!=input[9] || toBits(payload->threshold)!=input[10] ||
        !equalFloat(payload->velocityX,wanted[1]) || !equalFloat(payload->velocityY,wanted[2]) ||
        !equalFloat(payload->velocityZ,wanted[3]) || payload->flags!=((u8)input[0]==10?40:8) ||
        payload->kind!=(u8)input[0] || payload->channel!=255 || payload->alpha!=255) error=1;
    for(i=0;i<7;i++)if((u32)render->words[i]!=words[i])error=1;
    if(((u8 *)render)[28]!=0 || ((u8 *)render)[29]!=9)error=1;
    return success?arena+16:NULL;
}
typedef char RequestSize[(sizeof(RibbonRequest15148F1C)==28)?1:-1];
typedef char PayloadSize[(sizeof(RibbonPayload15148F1C)==32)?1:-1];
''' + screen.SELECTED + '''
static u8 *(*factory)(u8,f32,f32,f32,s32,s32,s32,f32,s16,f32,f32,u8)=func_15148F1C;
'''
        invocations, count = [], 0
        for args in cases():
            packet = expected(fixture(self.table), args, self.table)[-1][2]
            values = struct.unpack_from('>5I', packet)
            invocations.append('{u32 a[12]={%s},v[5]={%s};int i;u8 *result;\n'
                'for(i=0;i<12;i++){input[i]=a[i];}\nfor(i=0;i<5;i++){wanted[i]=v[i];}\n'
                'for(i=0;i<256;i++){arena[i]=0xa5;}\ncalls=error=0;success=%d;\n'
                'result=factory((u8)a[0],fromBits(a[1]),fromBits(a[2]),fromBits(a[3]),(s32)a[4],'
                '(s32)a[5],(s32)a[6],fromBits(a[7]),(s16)a[8],fromBits(a[9]),fromBits(a[10]),(u8)a[11]);\n'
                'if(error || calls!=4 || result!=(success?arena+16:NULL))return 1;\n'
                'for(i=0;i<256;i++)if(arena[i]!=0xa5)return 2;}\n' %
                (','.join('0x%08Xu' % a for a in args), ','.join('0x%08Xu' % a for a in values), count % 2))
            count += 1
        self.run_host(''.join(invocations))
        self.receipt('native', dict(cases=count, actual_native32=True, exact_typed_factory_assignment=True,
            defined_request_payload_render_fields=True, full_public_canaries=True,
            uninitialized_padding_not_compared=True, NaN_geometry_compared_by_classification=True))

    def test_08_independent_original_candidate_rebases(self):
        assembly = (self.root / 'conker/asm/175250.s').read_text().split('glabel ' + screen.FUNCTION, 1)[1]
        assembly = 'glabel ' + screen.FUNCTION + assembly.split('endlabel ' + screen.FUNCTION, 1)[0]
        path, original = self.out / 'original.s', self.out / 'original.o'
        path.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n.type ' +
            screen.FUNCTION + ', @function\n' + assembly + '\n.size ' + screen.FUNCTION +
            ', . - ' + screen.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(original), str(path)],
            cwd=self.root, check=True, capture_output=True)
        _, _, relocations = parse_object(original)
        _, _, candidate_rel = parse_object(self.out / 'selected.o')
        self.assertEqual(relocations, candidate_rel)
        records = []
        for variant, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = {name: (entry & 0xF0000000) + 0x100800 + i * 0x100
                for i, name in enumerate(screen.SYMBOLS)} if variant else screen.SYMBOLS
            script = self.out / ('rebase-%d.ld' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, obj in (('original', original), ('candidate', self.out / 'selected.o')):
                elf = self.out / ('rebase-%d-%s.elf' % (variant, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
                    '-e', screen.FUNCTION, *['--defsym=%s=0x%X' % item for item in symbols.items()],
                    '-o', str(elf), str(obj)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>107I', sections(elf)['.text'][1])))
            self.assertEqual(bodies[0], bodies[1])
            count = 0
            for args, phase, clobber, result in itertools.product(list(cases())[:16],
                    (0, 8), (False, True), (0, CREATED)):
                memory = fixture(self.table)
                reference = expected(memory, args, self.table, phase)
                for words in bodies:
                    model = ConstructorOracle(words, memory, args, self.table, result, phase, clobber,
                        entry=entry, symbols=symbols).run()
                    self.assertEqual(model.calls, reference)
                    self.assertEqual(model.r[2], result)
                count += 1
            records.append(dict(entry=entry, symbols=symbols, cases=count))
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, relocation_uses=5,
            cases=sum(r['cases'] for r in records), records=records, exact_at_each_link=True))


if __name__ == '__main__':
    unittest.main()
