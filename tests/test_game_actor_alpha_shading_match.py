"""Complete shading match with real matrix bodies, private aliases and linked audit."""
import csv
import hashlib
import itertools
import json
import math
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_alpha_shading_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as attachment
from tools.tests import test_game_actor_render_dispatch_recovery as dispatch
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating

STACK, ACTOR, OUTPUT = attachment.STACK, 0x25000, 0x26000
S = screen.recovery.SYMBOLS
MATRIX, WRAPPER, CONTINUATION, RGB = 0x150A7960, 0x150A7A00, 0x150A7A14, 0x1502D54C
LINKS = (S, {name: (value + (0x47FFC if name != 'func_150A7A00' else 0)) & 0xFFFFFFFF
    for name, value in S.items()}, {name: (value + (0x58004 if name != 'func_150A7A00' else 0)) & 0xFFFFFFFF
    for name, value in S.items()})
VALUES = (-math.inf, -1000.0, -1.0, -0.0, 0.0, 0.001, 0.1, 1.0, 10.0, 1000.0, math.inf, math.nan)


def rounded(value):
    return floating(bits(value))


def divide(left, right):
    if right == 0.0:
        return math.nan if left == 0.0 or math.isnan(left) else math.copysign(math.inf, left * math.copysign(1.0, right))
    return rounded(left / right)


def truncate(value):
    if not math.isfinite(value): return 0x80000000
    result = math.trunc(value)
    return result & 0xFFFFFFFF if -0x80000000 <= result <= 0x7FFFFFFF else 0x80000000


def fixture(first=1.0, second=10.0, start=0, end=1000, w=2.0, view=0,
        position=(1.0, 2.0, 3.0), symbols=S, matrix=None):
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x100)}
    selected = (symbols['D_800D2CA8'] + (view & 0xFFFFFFFF) * 64) & 0xFFFFFFFF
    for address, length in ((ACTOR, 0x40), (OUTPUT, 32), (selected, 64)):
        memory.update({address + i: (i * 17 + 53) & 255 for i in range(length)})
    for name, value, size in (('D_800D9B1C', bits(first), 4), ('D_800D9B20', bits(second), 4),
            ('D_800DD2E8', start, 2), ('D_800DD2EC', end, 2),
            *((name, 0x3A83126F, 4) for name in ('D_80096DE8', 'D_80096DEC', 'D_80096DF0', 'D_80096DF4'))):
        attachment.put(memory, symbols[name], value, size)
    for i, value in enumerate(position): attachment.put(memory, ACTOR + 0x14 + i * 4, bits(value))
    if matrix is None:
        matrix = [0.0] * 16
        matrix[0], matrix[5], matrix[10], matrix[15] = 1.0, 1.0, 1.0, w
    for i, value in enumerate(matrix): attachment.put(memory, selected + i * 4, bits(value))
    return memory


def semantic_alpha(memory, actor=ACTOR, view=0, symbols=S):
    get = lambda address: floating(attachment.read(memory, address, 4))
    first, second = get(symbols['D_800D9B1C']), get(symbols['D_800D9B20'])
    first = divide(1.0, first) if first != 0.0 else get(symbols['D_80096DE8'])
    second = divide(1.0, second) if second != 0.0 else get(symbols['D_80096DEC'])
    step = rounded(rounded(first - second) * get(symbols['D_80096DF0']))
    start = rounded(rounded(attachment.read(memory, symbols['D_800DD2E8'], 2) * step) + second)
    end = rounded(rounded(attachment.read(memory, symbols['D_800DD2EC'], 2) * step) + second)
    matrix = (symbols['D_800D2CA8'] + (view & 0xFFFFFFFF) * 64) & 0xFFFFFFFF
    x, y, z = (get(actor + offset) for offset in (0x14, 0x18, 0x1C))
    point = []
    for axis in range(4):
        a = rounded(rounded(get(matrix + axis * 4) * x) + rounded(get(matrix + 16 + axis * 4) * y))
        b = rounded(rounded(get(matrix + 32 + axis * 4) * z) + get(matrix + 48 + axis * 4))
        point.append(rounded(a + b))
    w = divide(1.0, point[3]) if point[3] != 0.0 else get(symbols['D_80096DF4'])
    if w < 0.0 or end <= w: factor = 0.0
    elif w <= start: factor = 1.0
    else: factor = divide(rounded(w - end), rounded(start - end))
    return truncate(rounded(rounded(1.0 - factor) * 255.0)), tuple(bits(value) for value in point)


class ShadingOracle(attachment.AttachmentOracle):
    def __init__(self, words, memory, actor=ACTOR, output=OUTPUT, view=0, phase=0,
            helpers=None, entry=screen.ENTRY):
        super().__init__(words, memory, entry=entry, arguments=(actor, output, view),
            phase=phase, connected=helpers)

    def record_call(self, target):
        assert target == WRAPPER
        event = ('CALL', target, self.arguments(8))
        self.calls.append(event)
        self.events.append(event)

    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 13:
            self.f[word >> 6 & 31] = truncate(floating(self.f[word >> 11 & 31]))
        else:
            super().execute(word)


class ConnectedDispatch(dispatch.DispatchOracle):
    def execute(self, word):
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 == 13:
            self.f[word >> 6 & 31] = truncate(floating(self.f[word >> 11 & 31]))
        else:
            super().execute(word)

    def record_call(self, target):
        if target == WRAPPER:
            return ShadingOracle.record_call(self, target)
        return super().record_call(target)

    def hook(self, target):
        assert target not in (WRAPPER, screen.ENTRY, RGB), 'complete RGB/shading/matrix must execute'
        return super().hook(target)


class GameActorAlphaShadingMatchTests(unittest.TestCase):
    assemble = classmethod(attachment.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows = classmethod(attachment.GameActorAttachmentUpdateMatchTests.write_rows.__func__)
    run_host = attachment.GameActorAttachmentUpdateMatchTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-alpha-shading-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(dispatch.PATHS)
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        with (cls.out / 'before-guards').open(newline='') as stream:
            reader = csv.DictReader(stream)
            cls.fields, cls.old_rows = reader.fieldnames, list(reader)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>125I', cls.rom, screen.ROM))
        assembly = (cls.root / 'conker/asm/58F80.s').read_text().split(
            'glabel ' + screen.FUNCTION, 1)[1].split('endlabel ' + screen.FUNCTION, 1)[0]
        cls.slot_asm = cls.out / 'slot.s'
        cls.slot_asm.write_text('glabel ' + screen.FUNCTION + assembly + 'endlabel ' + screen.FUNCTION + '\n')
        cls.rows = screen.guard_rows(cls.out / 'selected.o')
        cls.write_rows(cls.out / 'isolated.csv', cls.rows)
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl ' + screen.FUNCTION +
            '\n.type ' + screen.FUNCTION + ',@function\n' + screen.FUNCTION + ':\n' + assembly +
            '\n.size ' + screen.FUNCTION + ',.-' + screen.FUNCTION + '\n')
        cls.assemble('fitted', emit_padded_assembly(cls.out / 'selected.o', cls.slot_asm,
            word_patches_path=cls.out / 'isolated.csv', filename='generated_58F80'))
        cls.fitted = cls.link('fitted', S)
        cls.current = cls.fitted
        cls.elf = (cls.root / cls.paths['elf']).read_bytes()
        if screen.recovery.ORIGINAL not in (cls.root / screen.SOURCE).read_text():
            cls.current = list(struct.unpack_from('>125I', cls.elf,
                elf_slot_offset(cls.elf, screen.ENTRY, 500)))
        cls.helpers = {}
        for entry, rom, size in ((MATRIX, 0xD4E10, 160), (WRAPPER, 0xD4EB0, 20), (CONTINUATION, 0xD4EC4, 52)):
            body = list(struct.unpack_from('>%dI' % (size // 4), cls.elf,
                elf_slot_offset(cls.elf, entry, size)))
            assert body == list(struct.unpack_from('>%dI' % (size // 4), cls.rom, rom))
            cls.helpers.update({entry + i * 4: word for i, word in enumerate(body)})
        cls.caller = list(struct.unpack_from('>176I', cls.elf,
            elf_slot_offset(cls.elf, dispatch.screen.ENTRY, 704)))
        assert cls.caller == list(struct.unpack_from('>176I', cls.rom, dispatch.screen.ROM))
        cls.rgb = list(struct.unpack_from('>57I', cls.elf, elf_slot_offset(cls.elf, RGB, 228)))
        assert cls.rgb == list(struct.unpack_from('>57I', cls.rom, 0x5A9FC))
        cls.objects, cls.diagnostics = [], []
        before = (cls.out / 'before-source').read_text()
        for name, body in (('owner-before', before), ('owner-after', screen.install(before))):
            obj, diagnostics = compile_owner(cls.root, cls.out, body, name)
            subprocess.run(['python3', str(cls.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((cls.out / (name + '.c')).relative_to(cls.root / 'conker')), '--post-process',
                str(obj.relative_to(cls.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=cls.root / 'conker',
                check=True, capture_output=True)
            cls.objects.append(obj)
            cls.diagnostics.append(diagnostics)
        cls.guards = cls.out / 'qualified-guards.csv'
        cls.write_rows(cls.guards, cls.old_rows + cls.rows)
        cls.coverage = set()
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        cls.fixture = '''typedef unsigned char u8;typedef unsigned short u16;
typedef unsigned int u32;typedef int s32;typedef float f32;
static f32 D_800D9B1C,D_800D9B20,D_800D2CA8[4][16];
static u16 D_800DD2E8,D_800DD2EC;
static f32 D_80096DE8=0.001f,D_80096DEC=0.001f,D_80096DF0=0.001f,D_80096DF4=0.001f;
static int calls;static f32 last[4];
void func_150A7A00(f32 *matrix,f32 x,f32 y,f32 z,f32 *outX,f32 *outY,f32 *outZ,f32 *outW) {
    int i; calls++;
    for(i=0;i<4;i++) {
        f32 a=matrix[i]*x,b=matrix[4+i]*y,c=matrix[8+i]*z,d=matrix[12+i];
        last[i]=(a+b)+(c+d);
    }
    *outX=last[0];*outY=last[1];*outZ=last[2];*outW=last[3];
}
''' + screen.SELECTED + '''
static s32 expected(f32 first,f32 second,u16 a,u16 b,f32 w) {
    f32 low,high,step,p,q,factor,one=1.0f,zero=0.0f;
    low=first!=zero ? one/first : 0.001f;
    high=second!=zero ? one/second : 0.001f;
    step=(low-high)*0.001f;p=(f32)a*step+high;q=(f32)b*step+high;
    w=w!=zero ? one/w : 0.001f;
    if(w<zero || q<=w) factor=zero;
    else if(w<=p) factor=one;
    else factor=(w-q)/(p-q);
    return (s32)((one-factor)*255.0f);
}
'''

    @classmethod
    def link(cls, name, symbols):
        script = cls.out / ('link-%s-%X.ld' % (name, symbols['D_800D2CA8']))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % screen.ENTRY)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf),
            str(cls.out / (name + '.o'))], check=True, capture_output=True)
        size = parse_object(cls.out / (name + '.o'))[1][screen.FUNCTION]['size'] // 4
        return list(struct.unpack_from('>%dI' % size, sections(elf)['.text'][1]))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, actor=ACTOR, output=OUTPUT, view=0, phase=0, bodies=None, semantic=True):
        models = [ShadingOracle(body, memory, actor, output, view, phase, self.helpers).run()
            for body in bodies or (self.retail, self.raw, self.current)]
        for model in models[1:]:
            self.assertEqual((model.memory, model.events), (models[0].memory, models[0].events))
        if semantic:
            alpha, point = semantic_alpha(memory, actor, view)
            self.assertEqual(attachment.read(models[0].memory, output + 12, 4), alpha)
            frame = STACK + phase - 0x58
            self.assertEqual(tuple(attachment.read(models[0].memory, frame + o, 4) for o in (0x40, 0x3C, 0x38)), point[:3])
            self.assertEqual(models[0].calls[0][2][:4],
                ((S['D_800D2CA8'] + (view & 0xFFFFFFFF) * 64) & 0xFFFFFFFF,
                 *(attachment.read(memory, actor + o, 4) for o in (0x14, 0x18, 0x1C))))
        self.coverage.update(models[0].visits)
        return models

    def test_01_full_guest_reciprocals_clamps_rounding_and_unsigned_cuts(self):
        cases = 0
        for first, second, start, end, w in itertools.product((0.0, -0.0, 1.0, 10.0, -1.0),
                (0.0, 1.0, 10.0), (0, 1000, 65535), (0, 1000, 65535), (-2.0, 0.0, 1.0, 2.0, 10.0)):
            self.compare(fixture(first, second, start, end, w), phase=8 if cases % 2 else 0)
            cases += 1
        for view, word in itertools.product((-1, 0, 3, 0x12340002),
                (0, 0x80000000, 0x3F7FFFFF, 0x3F800000, 0x3F800001, 0x41200000, 0x41200001)):
            self.compare(fixture(w=floating(word), view=view), view=view)
            cases += 1
        self.receipt('guest', cases=cases, executions=cases * 3, original_raw_fitted_complete_memory_order=True,
            signed_fullwidth_view=True, zero_and_signed_zero_fallbacks=True,
            inclusive_clamps_and_neighbor_float_bits=True, saved_GPR_FPR_RA_SP_checked=True)

    def test_02_nonfinite_edges_with_explicit_bounded_FP_model(self):
        cases = 0
        for first, second, w in itertools.product(VALUES, VALUES, VALUES):
            self.compare(fixture(first, second, 32768, 65535, w))
            cases += 1
        self.receipt('FP-edges', cases=cases, original_raw_fitted_memory_order_exact=True,
            bounded_integer_indefinite=0x80000000, actual_FCSR_flags_traps_NaN_payloads_not_claimed=True)

    def test_03_real_matrix_association_and_private_aliases_faults(self):
        aliases = faults = 0
        for phase, offset in itertools.product((0, 8), (0x30, 0x34, 0x38, 0x3C, 0x40, 0x50, 0x54)):
            output = STACK + phase - 0x58 + offset - 12
            self.compare(fixture(), output=output, phase=phase, semantic=False)
            aliases += 1
        for phase, offset in itertools.product((0, 8), (0x20, 0x24, 0x28, 0x30, 0x34)):
            actor = STACK + phase - 0x58 + offset - 0x14
            self.compare(fixture(), actor=actor, phase=phase, semantic=False)
            aliases += 1
        matrix = [1.0, 2.0, 3.0, 0.5, -1.0, 0.25, -4.0, 0.75,
            1e20, -1e20, 0.5, 0.125, -1e20, 1e20, -0.0, 0.25]
        self.compare(fixture(matrix=matrix, position=(1.0, 1.0, 1.0)))
        inputs = [(fixture(w=0.0), 0, ACTOR, OUTPUT), (fixture(w=-2.0), 8, ACTOR, OUTPUT),
            (fixture(w=2.0), 0, ACTOR, OUTPUT)]
        for phase in (0, 8):
            frame = STACK + phase - 0x58
            inputs.append((fixture(), phase, ACTOR, frame + 0x34 - 12))
            inputs.append((fixture(), phase, frame + 0x24 - 0x14, OUTPUT))
        for memory, phase, actor, output in inputs:
            original = self.compare(memory, actor=actor, output=output, phase=phase, semantic=actor == ACTOR and output == OUTPUT)[0]
            for index, event in enumerate(original.events):
                if event[0] == 'CALL': continue
                ordinal = sum(e[0] != 'CALL' for e in original.events[:index])
                expected = memory.copy()
                for prior in original.events[:index]:
                    if prior[0] == 'W': attachment.put(expected, prior[1], prior[3], prior[2])
                for body in (self.retail, self.raw, self.current):
                    model = ShadingOracle(body, memory, actor=actor, output=output, phase=phase, helpers=self.helpers)
                    model.fault = ordinal
                    with self.assertRaises(attachment.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args, (ordinal,))
                    self.assertEqual((model.memory, model.events), (expected, original.events[:index]))
                faults += 1
        self.receipt('private', alias_cases=aliases, full_fired_fault_prefixes=faults,
            fault_executions=faults * 3, all_gates_fired=True, actual_58word_matrix_chain_executes=True,
            pairwise_matrix_sum_association=True, complete_private_memory_order_exact=True)

    def test_04_copied_owner_neighbors_and_only_target_padding(self):
        self.assertEqual(self.diagnostics, [[], []])
        first, second = [parse_object(obj) for obj in self.objects]
        relative = lambda data, f: {o - f['value']: uses for o, uses in data[2].items()
            if f['value'] <= o < f['value'] + f['size']}
        self.assertEqual(first[1].keys(), second[1].keys())
        for name, a in first[1].items():
            if name == screen.FUNCTION: continue
            b = second[1][name]
            self.assertEqual((a['size'], first[0][a['value']:a['value'] + a['size']], relative(first, a)),
                (b['size'], second[0][b['value']:b['value'] + b['size']], relative(second, b)), name)
        self.assertEqual(normalized_pools(self.objects[0]), normalized_pools(self.objects[1]))
        self.assertEqual(screen.guard_rows(self.objects[1]), self.rows)
        padded = []
        for i, obj in enumerate(self.objects):
            name = 'padded-owner-%d' % i
            self.assemble(name, emit_padded_assembly(obj, self.root / 'conker/asm/58F80.s',
                word_patches_path=self.out / 'before-guards' if i == 0 else self.guards,
                filename='generated_58F80', rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out / (name + '.o')))
        start = padded[1][1][screen.FUNCTION]['value']
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'], 500)
        self.assertEqual(padded[0][0][:start], padded[1][0][:start])
        self.assertEqual(padded[0][0][start + 500:], padded[1][0][start + 500:])
        self.receipt('owner', neighbors=len(first[1]) - 1, diagnostics=0, copied_equals_isolated=True,
            caller_RGB_body_relocations_pools_exact=True, only_target_500byte_slot_changes=True)

    def test_05_independent_links_and_every_stale_dependency(self):
        cases = 0
        for symbols in LINKS:
            bodies = [self.link(name, symbols) for name in ('original', 'fitted', 'selected')]
            self.assertEqual(bodies[0], bodies[1])
            for view, first, w in itertools.product((0, 3, -1), (0.0, 1.0), (0.0, 2.0, 10.0)):
                memory = fixture(first=first, w=w, view=view, symbols=symbols)
                models = [ShadingOracle(body, memory, view=view, helpers=self.helpers).run() for body in bodies]
                for model in models[1:]:
                    self.assertEqual((model.memory, model.events), (models[0].memory, models[0].events))
                self.assertEqual(attachment.read(models[0].memory, OUTPUT + 12, 4), semantic_alpha(memory, view=view, symbols=symbols)[0])
                cases += 1
        raw = (self.out / 'selected.o').read_bytes()
        header = ELF_HEADER.unpack_from(raw)
        headers = [SECTION_HEADER.unpack_from(raw, header[6] + i * header[11]) for i in range(header[12])]
        text = next(section for section in headers if section[2] & 4)
        for i in range(121):
            words = list(screen.RAW); words[i] ^= 0x10000
            with self.assertRaisesRegex(ValueError, 'stale complete shading'): screen.recipe(words)
            damaged = bytearray(raw)
            struct.pack_into('>I', damaged, text[4] + i * 4, words[i])
            path = self.out / 'stale.o'; path.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError, 'stale word patch'):
                emit_padded_assembly(path, self.slot_asm, word_patches_path=self.out / 'isolated.csv', filename='generated_58F80')
        for offset in screen.RELOCATIONS:
            rows = [dict(row) for row in self.rows]
            rows[offset // 4]['expected_relocations'] = '-'
            path = self.out / 'stale-relocations.csv'; self.write_rows(path, rows)
            with self.assertRaisesRegex(ValueError, 'stale relocations'):
                emit_padded_assembly(self.out / 'selected.o', self.slot_asm, word_patches_path=path, filename='generated_58F80')
        self.receipt('links-and-stale', independent_links=9, cases=cases, signed_LO16_carries=True,
            actual_word_rejections=121, actual_relocation_rejections=len(screen.RELOCATIONS), full_memory_order_exact=True)

    def test_06_actual_native32_complete_C(self):
        self.run_host('''
static f32 values[]={-1000.0f,-1.0f,-0.0f,0.0f,0.001f,0.1f,1.0f,10.0f,1000.0f};
static u16 cuts[]={0,1,1000,32768,65535};
f32 actor[16];s32 parameters[4];int a,b,c,d,e,view,i;u32 cut;
actor[5]=1;actor[6]=2;actor[7]=3;
for(a=0;a<9;a++) for(b=0;b<9;b++) for(c=0;c<5;c++) for(d=0;d<5;d++)
for(e=0;e<9;e++) for(view=0;view<4;view++) {
    D_800D9B1C=values[a];D_800D9B20=values[b];D_800DD2E8=cuts[c];D_800DD2EC=cuts[d];
    for(i=0;i<16;i++) D_800D2CA8[view][i]=0;
    D_800D2CA8[view][0]=D_800D2CA8[view][5]=D_800D2CA8[view][10]=1;
    D_800D2CA8[view][15]=values[e];
    parameters[0]=11;parameters[1]=22;parameters[2]=33;calls=0;
    func_1502D630((u8 *)actor,parameters,view);
    if(calls!=1 || parameters[0]!=11 || parameters[1]!=22 || parameters[2]!=33) return 1;
    if(parameters[3]!=expected(values[a],values[b],cuts[c],cuts[d],values[e])) return 2;
}
D_800D9B1C=1;D_800D9B20=10;D_800D2CA8[0][15]=2;
for(cut=0;cut<65536;cut++) for(i=0;i<2;i++) {
    D_800DD2E8=i ? 0 : cut;D_800DD2EC=i ? cut : 1000;
    func_1502D630((u8 *)actor,parameters,0);
    if(parameters[3]!=expected(1,10,D_800DD2E8,D_800DD2EC,2)) return 3;
}
''')
        self.receipt('native32', cases=9 * 9 * 5 * 5 * 9 * 4 + 2 * 65536,
            actual_complete_C=True, both_all_65536_unsigned_cuts=True, bounded_matrix_model=True,
            valid_disjoint_finite_inputs_only=True, RGB_sentinels_unchanged=True)

    def test_07_fresh_effective_compiled_negative_controls(self):
        controls = (
            ('wrong-end-gate', 'end <= w', 'w <= end', fixture()),
            ('wrong-start-gate', 'w <= start', 'start <= w', fixture(w=64.0)),
            ('wrong-halfword-width', '(f32)(u32)D_800DD2E8', '(f32)(s16)D_800DD2E8', fixture(start=65535)),
            ('wrong-alpha-slot', 'parameters[3] =', 'parameters[2] =', fixture()),
            ('wrong-blend-sign', '(w - end)', '(end - w)', fixture()),
            ('wrong-fallback', 'w = D_80096DF4;', 'w = 1.0f;', fixture(w=0.0)),
            ('wrong-position', 'actor + 0x1C', 'actor + 0x18', fixture(matrix=[0.0] * 11 + [1.0] + [0.0] * 4)),
        )
        for name, old, new, memory in controls:
            _, words = screen.compile_candidate(self.root, self.out, name, screen.SELECTED.replace(old, new))
            wrong = ShadingOracle(words, memory, helpers=self.helpers).run()
            self.assertNotEqual(attachment.read(wrong.memory, OUTPUT + 12, 4), semantic_alpha(memory)[0], name)
        self.receipt('negatives', fresh_effective_complete_compiled_controls=len(controls), public_alpha_distinguished=True)

    def test_08_complete_banked_dispatch_shading_matrix_connection(self):
        cases = 0
        for slot, view, mode, phase, w in itertools.product((0, 25), (0, 3), range(7), (0, 8), (0.0, 2.0, 10.0)):
            memory = dispatch.fixture(slot, view, enabled=1)
            actor = dispatch.S['D_800CC2D0'] + slot * 0x32C
            shading = fixture(w=w, view=view)
            memory.update(shading)
            for offset in (0x14, 0x18, 0x1C):
                attachment.put(memory, actor + offset, attachment.read(shading, ACTOR + offset, 4))
            memory[actor + 0x66] = 4 if cases % 2 else 0
            colors = tuple((cases + i * 37) & 255 for i in range(6))
            for i, value in enumerate(colors): memory[actor + 0x1DD + i] = value
            expected_rgb = tuple(255 - (colors[i] + colors[i + 3]) // 2 for i in range(3)) if cases % 2 else (255,) * 3
            models = []
            for body in (self.retail, self.raw, self.current):
                connected = dict(self.helpers)
                connected.update({RGB + i * 4: word for i, word in enumerate(self.rgb)})
                connected.update({screen.ENTRY + i * 4: word for i, word in enumerate(body)})
                model = ConnectedDispatch(self.caller, memory, slot, view, mode, phase=phase,
                    plan=dispatch.Plan(second=254), connected=connected).run()
                self.assertIn(screen.ENTRY, model.visits)
                self.assertIn(RGB, model.visits)
                self.assertTrue(set(self.helpers).issubset(model.visits))
                render = [event for event in model.calls if event[1] == 'func_1502CCFC']
                self.assertEqual(len(render), 1)
                self.assertEqual(render[0][2][5], (*expected_rgb, semantic_alpha(memory, actor, view)[0]))
                models.append(model)
            for model in models[1:]:
                self.assertEqual((model.r[2], model.memory, model.events), (models[0].r[2], models[0].memory, models[0].events))
            cases += 1
        self.receipt('caller', cases=cases, banked_dispatch_words=176, complete_shading_words=125,
            actual_RGB_words=57, actual_58word_matrix_chain_executes=True, other_callbacks_explicitly_bounded=True,
            whole_game_acceptance=False)

    def test_09_shape_and_whole_linked_installation(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['pool_bytes'],
            self.meta['diagnostics']), (121, 0x58, 0, ''))
        self.assertEqual(self.fitted, self.retail)
        self.assertEqual(self.current, self.retail)
        self.assertEqual(len(self.rows), 121)
        self.assertEqual(sum(bool(row['insert_after']) for row in self.rows), 4)
        self.assertFalse(any(row['omit'] == 'true' for row in self.rows))
        missing = [i for i in range(125) if screen.ENTRY + i * 4 not in self.coverage]
        self.assertEqual(missing, [46, 47, 48, 57, 58, 59, 96, 103, 110])
        self.receipt('shape', raw_words=121, matched_words=125, frame=0x58, guards=121,
            changed_rows=sum(r['expected'] != r['replacement'] for r in self.rows), insertions=4,
            omissions=0, padding=0, relocations=len(screen.RELOCATIONS),
            missing_reachable_words=missing,
            recipe_never_reads_ROM=True)
        source = (self.root / screen.SOURCE).read_text()
        if screen.recovery.ORIGINAL in source:
            self.assertEqual({name: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                for name, path in self.paths.items()}, self.baseline)
            self.receipt('installation', installed=False, baseline_unchanged=True)
            return
        self.assertEqual(source, screen.install((self.out / 'before-source').read_text()))
        with (self.root / self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)), self.old_rows + self.rows)
        self.assertTrue((self.root / self.paths['guards']).read_bytes().startswith((self.out / 'before-guards').read_bytes()))
        for name in ('progress', 'rodata'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>125I', expected, elf_slot_offset(before, screen.ENTRY, 500), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 500)
        actual = (self.root / self.paths['elf']).read_bytes()
        em, am = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(em[:4], am[:4])
        for section in em[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('installation', installed=True, only_target_500_bytes_and_extent_changed=True,
            guards_exact_prefix_conversion_rodata_exact=True, protected_data=audit)


if __name__ == '__main__':
    unittest.main()
