"""Byte-exact dispatch, full selector domain, native32 and current quad connection."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_rectangle_preset_dispatch as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests import game_rectangle_preset_oracle as guest
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import test_game_quad_edge_path_recovery as quad
from tools.tests.game_table_debris_native import TYPES


def controls():
    b = source.SELECTED
    return {
        'halfword-selector': b.replace('actor[0x72]', '*(u16 *)(actor + 0x72)'),
        'signed-selector': b.replace('actor[0x72]', '*(signed char *)(actor + 0x72)'),
        'null-actor': b.replace('func_151717FC(actor,', 'func_151717FC((u8 *)0,'),
        'baked-offset': b.replace('D_800A6FC0', '-1270.0f'),
        'wrong-offset': b.replace('D_800A6FC4', 'D_800A6FC0'),
        'swapped-counts': b.replace('2, 5, 4, 10,', '2, 5, 10, 4,'),
        'wrong-last-kind': b.replace('1, 5, 4, 4,', '2, 5, 4, 4,'),
        'wrong-flags': b.replace('flags, context);', '(u8)(flags >> 1), context);'),
        'narrow-context': b.replace('flags, context);', 'flags, (u8)context);'),
    }


def native_fixture(rom):
    rows = []
    for selector, pattern in itertools.product(range(256), range(3)):
        flags, context = (selector*1097+pattern*37) & 0xFFFFFFFF, (selector*0x1234567+pattern+0x80000000) & 0xFFFFFFFF
        m, a = guest.fixture(rom, selector, flags, context, pattern)
        calls = guest.reference(m, a)
        values = calls[0][2:] if calls else (0,)*12
        row = (selector, flags, context, guest.read(m, 0x800A6FC0), guest.read(m, 0x800A6FC4), len(calls))
        rows.append('{' + ','.join('0x%Xu' % n for n in row) + ',{' + ','.join('0x%Xu' % n for n in values) + '}}')
    return TYPES + r'''
f32 D_800A6FC0,D_800A6FC4;
struct Case{u32 selector,flags,context,c0,c4,called,words[12];};
static const struct Case cases[]={ROWS};
static const struct Case*c;static u32 calls,error;
static union{u32 alignment;u8 bytes[128];}actor;
static f32 number(u32 n){union{u32 n;f32 f;}v;v.n=n;return v.f;}
static u32 word(f32 f){union{u32 n;f32 f;}v;v.f=f;return v.n;}
void func_151717FC(u8*p,f32 w,f32 d,f32 x,f32 y,f32 z,s32 kind,s32 preset,s32 nx,s32 nz,f32 scale,u8 flags,s32 context){
 u32 actual[12]={word(w),word(d),word(x),word(y),word(z),(u32)kind,(u32)preset,(u32)nx,(u32)nz,word(scale),flags,(u32)context};u32 i;
 calls++;if(p!=actor.bytes||calls>1){error=20;return;}for(i=0;i<12;i++)if(actual[i]!=c->words[i])error=21;
 p[0x72]=0x5A;D_800A6FC0=D_800A6FC4=0.0f;}
void func_15171600(u8*,u8,s32);
static void(*volatile invoke)(u8*,u8,s32)=func_15171600;
static int run(void){u32 n,i;if(sizeof(void*)!=4)return 24;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
 for(i=0;i<128;i++)actor.bytes[i]=0xA5;actor.bytes[0x72]=(u8)c->selector;D_800A6FC0=number(c->c0);D_800A6FC4=number(c->c4);calls=error=0;
 invoke(actor.bytes,(u8)c->flags,(s32)c->context);if(error)return (int)error;if(calls!=c->called)return 22;
 if(actor.bytes[0x72]!=(u8)(calls?0x5A:c->selector))return 23;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows))


class RectangleDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>127I', cls.rom, source.ROM))

    def receipt(self, name, **data):
        (self.out / (name+'.json')).write_text(json.dumps(data, indent=2)+'\n')

    def test_01_exact_shape_neighbors_bindings_and_unchanged_pool(self):
        self.assertEqual(self.words, self.truth)
        obj, diag = source.build.compile_owner(self.root, self.out, (self.out / 'before-edge_wrapper_owner').read_text(), 'neighbor-baseline')
        self.assertFalse(diag)
        old, new = parse_object(obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value']+f['size']], new[0][g['value']:g['value']+g['size']], name)
            relative = lambda o, f: {a-f['value']: v for a, v in o[2].items() if f['value'] <= a < f['value']+f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(sections(obj)['.rodata'][1], source.POOL)
        self.assertEqual(sections(self.obj)['.rodata'][1], source.POOL)
        self.assertNotIn((','+source.FUNCTION+',').encode(), (self.out / 'before-guards').read_bytes())
        self.receipt('shape', words=127, frame=64, neighbors=8, target_guards=0, pool_unchanged=True, compiler_diagnostics='')

    def test_02_all_selector_bytes_word_widths_live_constants_and_effectful_callee(self):
        visits, count = set(), 0
        for selector, phase, pattern, mode in itertools.product(range(256), (0, 8), range(4), (0, 1)):
            memory, args = guest.fixture(self.rom, selector, pattern=pattern)
            models = [guest.DispatchOracle(w, memory, args, phase=phase, mode=mode).run() for w in (self.truth, self.words)]
            for m in models:
                self.assertEqual(m.calls, guest.reference(memory, args, phase))
                if selector not in guest.PRESETS:
                    reads = {e[1] for e in m.events if e[0] == 'R'}
                    self.assertTrue(reads.isdisjoint({0x800A6FC0, 0x800A6FC4}))
            self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
            visits.update(models[0].visits)
            count += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY+508, 4)))
        self.receipt('selectors', paired_cases=count, all_256_selectors=True, all_127_words_visited=True,
            effectful_callee_and_default_no_offset_reads=True, raw_float_bitpatterns=True)

    def test_03_native32_O2_O0_UBSan_and_effective_negatives(self):
        harness = self.out / 'native-harness.c'
        harness.write_text(native_fixture(self.rom))
        exits = {}
        for name, body, opt, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-'+n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-'+name+'.c')
            path.write_text(TYPES+source.DECLARATIONS+body)
            command = ['cc', '-m32', opt, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            else:
                command += ['-Wno-switch-outside-range']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 24)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=768, separate_units=True, selected_UBSan=True, exits=exits)

    def test_04_effective_compiled_guest_negatives(self):
        rejected = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            obj, _, _ = source.measure(self.root, self.out, 'negative-'+name, body)
            data, funcs = source.build.link_owner(self.root, self.out, obj, source.OWNER)
            f = funcs[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (f['size']//4), data, f['value']))
            address, pool = sections(obj.with_suffix('.elf'))['.rodata']
            for selector in guest.PRESETS:
                memory, args = guest.fixture(self.rom, selector, pattern=1)
                memory.update({address+i: b for i, b in enumerate(pool)})
                model = guest.DispatchOracle(words, memory, args).run()
                if model.calls != guest.reference(memory, args):
                    rejected.append(name)
                    break
            else:
                self.fail('Ineffective compiled negative: '+name)
        self.receipt('negatives', compiled_effective=rejected, own_raw_pool_not_production_alias=True)

    def test_05_all_raw_word_binding_and_pool_corruptions(self):
        text, funcs, rel = parse_object(self.obj)
        f = funcs[source.FUNCTION]
        for i in range(127):
            bad = bytearray(text)
            bad[f['value']+i*4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), funcs, rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad = dict(rel)
            bad[f['value']+at] = [(rel[f['value']+at][0][0], 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, funcs, bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        pools = sections(self.obj)
        for i in range(32):
            bad = bytearray(source.POOL)
            bad[i] ^= 1
            with patch.object(source, 'sections', return_value=dict(pools, **{'.rodata': (0, bytes(bad))})):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        self.receipt('corruptions', raw_words=127, bindings=8, inherited_pool_bytes=32)

    def test_06_fired_fault_prefixes_and_guest_home_aliases(self):
        faults, aliases = 0, 0
        for phase, selector in itertools.product((0, 8), (*guest.PRESETS, 0)):
            memory, args = guest.fixture(self.rom, selector)
            done = guest.DispatchOracle(self.truth, memory, args, phase=phase).run()
            for fault in range(done.accesses):
                models = []
                for words in (self.truth, self.words):
                    model = guest.DispatchOracle(words, memory, args, phase=phase, fault=fault)
                    with self.assertRaises(guest.edge.AccessFault):
                        model.run()
                    models.append(model)
                self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
                faults += 1
        for phase, home, selector in itertools.product((0, 8), (4, 8), guest.PRESETS):
            memory, args = guest.fixture(self.rom, selector)
            actor = guest.STACK+phase+home-0x72
            args = (actor, selector << 24 | 0x123481, selector << 24 | 0x567812)
            models = [guest.DispatchOracle(w, memory, args, phase=phase).run() for w in (self.truth, self.words)]
            self.assertEqual(models[0].calls, guest.reference(memory, args, phase))
            self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
            aliases += 1
        self.receipt('faults', fired_prefix_pairs=faults, guest_home_aliases=aliases, not_native_fault_alias_or_FP_proof=True)

    def test_07_original_caller_capture_and_current_stub_limit(self):
        class Stop(guest.DispatchOracle):
            def record_call(self, target):
                if target == source.ENTRY:
                    self.forwarded = self.arguments(3)
                    raise guest.edge.CallBoundary
                return super().record_call(target)
        entry, rom, size = 0x15029914, 0x56DC4, 32
        data = self.rom[rom:rom+size]
        image = (self.out / 'before-elf').read_bytes()
        self.assertEqual(image[elf_slot_offset(image, entry, size):][:size], bytes(size))
        caller = (self.out / 'before-dual_caller_owner').read_text()
        lo, hi = source.build.function_span(caller, 'func_150265CC')
        self.assertEqual(caller[lo:hi], 's32 func_150265CC() {\n    return 0;\n}')
        cases = 0
        for phase, flags in itertools.product((0, 8), (0, 0x81, 0xFF)):
            memory, _ = guest.fixture(self.rom)
            guest.put(memory, guest.STACK+phase+0x768, guest.ACTOR)
            guest.put(memory, guest.STACK+phase+0x764, 0xDEADBEEF)
            guest.put(memory, guest.STACK+phase+0x773, flags, 1)
            model = Stop(list(struct.unpack('>8I', data)), memory, (0, 0, 0), phase=phase, entry=entry)
            model.r[2] = 0x28
            with self.assertRaises(guest.edge.CallBoundary):
                model.run()
            self.assertEqual(model.forwarded, (guest.ACTOR, flags, 0))
            cases += 1
        self.receipt('caller', original_captures=cases, current_caller='func_150265CC',
            current_placeholder_and_zero_call_window=True, no_current_caller_or_gameplay_claim=True)

    def test_08_current_rectangle_emitter_thirteen_inputs_and_quad(self):
        image = (self.out / 'before-elf').read_bytes()
        data = image[elf_slot_offset(image, source.CALLEE, 244):][:244]
        self.assertEqual(data, self.rom[0x19ECAC:0x19ECAC+244])
        code = dict(zip(range(source.CALLEE, source.CALLEE+244, 4), struct.unpack('>61I', data)))
        class Chain(guest.DispatchOracle):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self.quads = []
            def record_call(self, target):
                if target == 0x151700D8:
                    args = self.arguments(10)
                    self.quads.append((args, tuple(guest.read(self.memory, args[0]+i*4) for i in range(12))))
                    return
                return super().record_call(target)
            def hook(self, target):
                self.asserted_target = target
                assert target == 0x151700D8
                return quad.WrapperOracle.hook(self, target)
        cases = 0
        for selector, phase, coords in itertools.product(guest.PRESETS, (0, 8), ((-32768, -1, 32767), (123, -456, 789))):
            memory, args = guest.fixture(self.rom, selector)
            for i, v in enumerate(coords):
                guest.put(memory, guest.ACTOR+0x10+i*2, v, 2)
            forwarded = guest.reference(memory, args, phase)[0][1:]
            expected, vertices = quad.packet_reference(memory, forwarded, phase-64)
            models = [Chain(w, memory, args, phase=phase, connected=code).run() for w in (self.truth, self.words)]
            for model in models:
                self.assertEqual(model.calls, [(source.CALLEE, *forwarded)])
                self.assertEqual(model.quads, [(expected, vertices)])
            self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
            cases += 1
        self.receipt('chain', current_rectangle_words=61, paired_cases=cases, all_quad_words_and_ten_forwarded_inputs=True,
            four_edge_emitter_is_opaque_not_gameplay_acceptance=True)

    def test_09_full_preinstall_prediction_all_frozen_inputs_and_corruptions(self):
        row = source.prelink_prediction(self.root, self.out)
        self.assertEqual(row['additional_serialization_bytes'], 53)
        expected = source.expected_inputs(self.root, self.out)
        hashes = {k: hashlib.sha256(v).hexdigest() for k, v in expected.items()}
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), hashes)
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **hashes)))
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            target = self.out / ('before-'+key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        target = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == target else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        rejected = (self.out / 'slot-only-rejected.elf').read_bytes()
        self.assertNotEqual(rejected, expected['elf'])
        self.assertEqual(source.serialize_symbols(rejected), expected['elf'])
        bad = bytearray(rejected)
        bad[100] ^= 1
        with self.assertRaises(ValueError):
            source.serialize_symbols(bad)
        self.receipt('scope', inputs=len(source.PATHS), predictions=hashes, rejected_slot_prediction_preserved=True,
            complete_metadata_accounting_bytes=53, metadata_exclusions=0)

    def test_10_independently_assembled_original_rebases(self):
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel '+source.FUNCTION+'\n', 1)[1].split('endlabel '+source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "'+str(self.root / 'conker/include/asm_processor_prelude.inc')+'"\n.type '+source.FUNCTION+
            ', @function\nglabel '+source.FUNCTION+'\n'+original+'\n.size '+source.FUNCTION+', . - '+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        text, funcs, rel = parse_object(path.with_suffix('.o'))
        f = funcs[source.FUNCTION]
        original_raw = text[f['value']:f['value']+f['size']]
        original_rel = {a-f['value']: v for a, v in rel.items() if f['value'] <= a < f['value']+f['size']}
        raw, bindings = source.checked_object(self.obj)
        cases = 0
        for entry, delta, call_delta in ((0x15201000, 0x1000, 0x2000), (0x15302000, 0x1040, 0x4000), (0x15403000, 0x2100, 0x6000)):
            links = {'func_151717FC': source.CALLEE+call_delta, 'D_800A6FC0': 0x800A6FC0+delta, 'D_800A6FC4': 0x800A6FC4+delta}
            streams = []
            for i, (data, rows) in enumerate(((raw, bindings), (original_raw, original_rel))):
                asm, missing = emit_function(data, dict(value=0, size=len(data)), rows, source.FUNCTION, links)
                self.assertFalse(missing)
                file = self.out / ('rebase-%X-%d.s' % (entry, i))
                file.write_text(asm)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(file.with_suffix('.o')), str(file)], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(file.with_suffix('.ld')), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in links.items()], '-o', str(file.with_suffix('.elf')), str(file.with_suffix('.o'))], check=True, capture_output=True)
                streams.append(list(struct.unpack_from('>127I', sections(file.with_suffix('.elf'))['.text'][1])))
            self.assertEqual(streams[0], streams[1])
            for selector, phase, pattern in itertools.product((*guest.PRESETS, 0), (0, 8), range(3)):
                initial, args = guest.fixture(self.rom, selector, pattern=pattern)
                memory = {a+delta if 0x800A6FC0 <= a < 0x800A6FC8 else a: b for a, b in initial.items()}
                models = [guest.DispatchOracle(w, memory, args, phase=phase, entry=entry,
                    bindings={source.CALLEE+call_delta: source.CALLEE}).run() for w in streams]
                self.assertEqual(models[0].calls, guest.reference(initial, args, phase))
                self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
                cases += 1
        self.receipt('rebases', independent_original_sets=3, paired_cases=cases, all_calls_globals_and_signed_low_carry=True)


if __name__ == '__main__':
    unittest.main()
