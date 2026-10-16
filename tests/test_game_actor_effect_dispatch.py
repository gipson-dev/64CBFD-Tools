"""All selectors, effect order, real caller, native32 and full-owner completion."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_effect_dispatch as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object, parse_retail_slice
from tools.tests import game_actor_effect_oracle as guest
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_table_debris_native import TYPES


def controls():
    b = source.SELECTED
    calls = '            func_150AEEB0(actor, flags);\n            func_10010154(0x69, actor, 0x7D00, 200, 2000);'
    return {
        'halfword-kind': b.replace('actor[4]', '*(u16 *)(actor+4)'),
        'wrong-kind-offset': b.replace('actor[4]', 'actor[5]'),
        'missing-second-kind': b.replace('        case 0x23:\n', ''),
        'wrong-effect-helper': b.replace('func_150BD740(actor,', 'func_150CDBB0(actor,'),
        'lost-flag-high-bit': b.replace('(actor, flags', '(actor, (u8)(flags & 127)'),
        'wrong-mode': b.replace('(actor, flags, 1)', '(actor, flags, 0)'),
        'wrong-sound-id': b.replace('func_10010154(0x69,', 'func_10010154(0x68,'),
        'swapped-distances': b.replace('0x7D00, 200, 2000', '0x7D00, 2000, 200'),
        'missing-sound': b.replace('            func_10010154(0x69, actor, 0x7D00, 200, 2000);\n', ''),
        'reversed-effect-sound': b.replace(calls, '\n'.join(reversed(calls.splitlines()))),
    }


def native_fixture():
    rows = []
    roles = {source.FIRST: 1, source.SECOND: 2, source.THIRD: 3, source.SOUND: 4}
    for kind, flags, mode in itertools.product(range(256), (0, 0x81, 0xFFFFFFFF), (0, 1)):
        memory, args = guest.fixture(kind, flags)
        calls = guest.reference(memory, args)
        order = [roles[c[0]] for c in calls]
        rows.append('{%d,0x%Xu,%d,%d,{%s}}' % (kind, flags, mode, len(order), ','.join(map(str, order)) if order else '0'))
    return TYPES + r'''
struct Case{u32 kind,flags,mode,count,order[2];};static const struct Case cases[]={ROWS};
static const struct Case*c;static u32 calls,error;static union{u32 alignment;u8 bytes[128];}actor;
static void check(u32 role,u8*p,u8 flags,s32 mode){
 if(calls>=c->count||c->order[calls]!=role||p!=actor.bytes){error=20;return;}
 if(flags!=(u8)c->flags||((role==2||role==3)&&mode!=1))error=21;calls++;
 if(c->mode)p[4]=0x54;}
void func_150AEEB0(u8*p,u8 flags){check(1,p,flags,0);}
void func_150BD740(u8*p,u8 flags,s32 mode){check(2,p,flags,mode);}
void func_150CDBB0(u8*p,u8 flags,s32 mode){check(3,p,flags,mode);}
s32 func_10010154(u16 sound,void*p,u16 volume,s16 minimum,u16 maximum){
 if(calls>=c->count||c->order[calls]!=4||p!=actor.bytes){error=22;return 0;}
 if(sound!=0x69||volume!=0x7D00||minimum!=200||maximum!=2000)error=23;calls++;return (s32)0x87654321u;}
void func_15171BF4(u8*,u8);static void(*volatile invoke)(u8*,u8)=func_15171BF4;
static int run(void){u32 n,i;if(sizeof(void*)!=4)return 25;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
 for(i=0;i<128;i++)actor.bytes[i]=0xA5;actor.bytes[4]=(u8)c->kind;calls=error=0;
 invoke(actor.bytes,(u8)c->flags);if(error)return (int)error;if(calls!=c->count)return 24;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows))


class ActorEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>43I', cls.rom, source.ROM))

    def receipt(self, name, **data):
        (self.out / (name+'.json')).write_text(json.dumps(data, indent=2)+'\n')

    def test_01_exact_body_terminal_padding_neighbors_and_pool(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['body_words'], self.row['words'], self.row['frame'], self.row['terminal_padding_words']), (42, 43, 40, 1))
        raw, _ = source.checked_object(self.obj)
        self.assertEqual(len(raw), 168)
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
        self.receipt('shape', body_words=42, slot_words=43, frame=40, terminal_padding=1, neighbors=8,
            target_guards=0, pool_and_prior_guards_fixed=True, body_instructions_not_inserted_or_omitted=True)

    def test_02_all_selectors_flags_callee_mutations_and_call_order(self):
        visits, count = set(), 0
        for kind, flags, phase, mode in itertools.product(range(256), (0, 0xABCDEF81, 0xFFFFFFFF), (0, 8), (0, 1)):
            memory, args = guest.fixture(kind, flags)
            models = [guest.EffectOracle(w, memory, args, phase=phase, mode=mode).run() for w in (self.truth, self.words)]
            for model in models:
                self.assertEqual(model.calls, guest.reference(memory, args, phase))
            self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
            visits.update(models[0].visits)
            count += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY+168, 4)))
        self.receipt('selectors', paired_cases=count, all_256_kinds=True, all_42_body_words_visited=True,
            terminal_padding_not_executed=True, effectful_clobbering_helpers_and_sound_order=True)

    def test_03_native32_separate_units_O2_O0_UBSan_and_negatives(self):
        harness = self.out / 'native-harness.c'
        harness.write_text(native_fixture())
        exits = {}
        for name, body, opt, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-'+n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-'+name+'.c')
            path.write_text(TYPES+source.DECLARATIONS+body)
            command = ['cc', '-m32', opt, '-std=c11', '-fno-strict-aliasing', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            if valid:
                command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error']
            result = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 25)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=1536, separate_units=True, selected_UBSan=True, exits=exits)

    def test_04_effective_compiled_guest_negatives(self):
        rejected = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            obj, _, _ = source.measure(self.root, self.out, 'negative-'+name, body)
            data, funcs = source.build.link_owner(self.root, self.out, obj, source.OWNER)
            f = funcs[source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % (f['size']//4), data, f['value']))
            for kind in (0x13, 0x23, 0x1E, 0x54):
                memory, args = guest.fixture(kind)
                model = guest.EffectOracle(words, memory, args, mode=1).run()
                if model.calls != guest.reference(memory, args):
                    rejected.append(name)
                    break
            else:
                self.fail('Ineffective compiled negative: '+name)
        self.receipt('negatives', compiled_effective=rejected)

    def test_05_raw_word_binding_pool_corruptions_and_wrong_padding(self):
        text, funcs, rel = parse_object(self.obj)
        f = funcs[source.FUNCTION]
        for i in range(42):
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
        bad_rom = bytearray(self.rom)
        bad_rom[source.ROM+168] ^= 1
        rb, path = Path.read_bytes, self.out / 'before-retail_rom'
        measured = (self.obj, self.truth[:42], dict(self.row, words=42, differences=1))
        with patch.object(source, 'measure', return_value=measured), patch.object(Path, 'read_bytes', lambda p: bytes(bad_rom) if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'terminal padding'):
                source.qualify(self.root, self.out)
        self.receipt('corruptions', raw_words=42, bindings=4, inherited_pool_bytes=32, terminal_padding_flip_rejected=True)

    def test_06_fired_fault_prefixes_and_guest_argument_home_aliases(self):
        faults, aliases = 0, 0
        for phase, kind in itertools.product((0, 8), (0x13, 0x23, 0x1E, 0x54, 0)):
            memory, args = guest.fixture(kind)
            complete = guest.EffectOracle(self.words, memory, args, phase=phase).run()
            for fault in range(complete.accesses):
                models = []
                for w in (self.truth, self.words):
                    model = guest.EffectOracle(w, memory, args, phase=phase, fault=fault)
                    with self.assertRaises(guest.edge.AccessFault):
                        model.run()
                    models.append(model)
                self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
                faults += 1
        for phase, kind in itertools.product((0, 8), (0x13, 0x23, 0x1E, 0x54)):
            memory, _ = guest.fixture(kind)
            args = (guest.STACK+phase, kind << 24 | 0x123481)
            models = [guest.EffectOracle(w, memory, args, phase=phase).run() for w in (self.truth, self.words)]
            self.assertEqual(models[0].calls, guest.reference(memory, args, phase))
            self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
            aliases += 1
        self.receipt('faults', fired_prefix_pairs=faults, guest_home_aliases=aliases, not_portable_native_fault_or_alias_proof=True)

    def test_07_original_caller_and_current_placeholder_limit(self):
        class Stop(guest.EffectOracle):
            def record_call(self, target):
                if target == source.ENTRY:
                    self.forwarded = self.arguments(2)
                    raise guest.edge.CallBoundary
                return super().record_call(target)
        entry, rom, size = 0x1502993C, 0x56DEC, 16
        data, image = self.rom[rom:rom+size], (self.out / 'before-elf').read_bytes()
        self.assertEqual(image[elf_slot_offset(image, entry, size):][:size], bytes(size))
        caller = (self.out / 'before-dual_caller_owner').read_text()
        lo, hi = source.build.function_span(caller, 'func_150265CC')
        self.assertEqual(caller[lo:hi], 's32 func_150265CC() {\n    return 0;\n}')
        count = 0
        for phase, flags in itertools.product((0, 8), (0, 0x81, 255)):
            memory, _ = guest.fixture()
            guest.put(memory, guest.STACK+phase+0x773, flags, 1)
            model = Stop(list(struct.unpack('>4I', data)), memory, (0, 0), phase=phase, entry=entry)
            model.r[25] = guest.ACTOR
            with self.assertRaises(guest.edge.CallBoundary):
                model.run()
            self.assertEqual(model.forwarded, (guest.ACTOR, flags))
            count += 1
        self.receipt('caller', original_captures=count, actor_from_t9_and_byte_flags=True,
            current_caller_placeholder_and_zero_window=True, no_current_caller_or_gameplay_claim=True)

    def test_08_current_sound_wrapper_muted_guard_after_effect(self):
        image = (self.out / 'before-elf').read_bytes()
        data = image[elf_slot_offset(image, source.SOUND, 496):][:496]
        self.assertEqual(data, self.rom[0x10154:0x10344])
        code = dict(zip(range(source.SOUND, source.SOUND+496, 4), struct.unpack('>124I', data)))
        count = 0
        for phase, kind, mode in itertools.product((0, 8), (0x13, 0x23), (2, 3)):
            memory, args = guest.fixture(kind)
            models = [guest.EffectOracle(w, memory, args, phase=phase, mode=mode, connected=code).run() for w in (self.truth, self.words)]
            self.assertEqual(models[0].calls, guest.reference(memory, args, phase))
            self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
            self.assertEqual(guest.read(models[0].memory, guest.ACTOR), 5 if mode == 3 else 0)
            count += 1
        self.receipt('sound-connection', current_sound_words=124, paired_cases=count,
            only_state_0_and_5_early_return_paths=True, effects_opaque_and_no_audible_sound_or_gameplay_claim=True)

    def test_09_preinstall_prediction_all_frozen_inputs_and_complete_owner(self):
        row = source.prelink_prediction(self.root, self.out)
        self.assertEqual((row['slot_changes'], row['additional_serialization_bytes']), (127, 0))
        expected = source.expected_inputs(self.root, self.out)
        hashes = {k: hashlib.sha256(v).hexdigest() for k, v in expected.items()}
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), hashes)
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **hashes)))
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            path = self.out / ('before-'+key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        path = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == path else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        lo, hi, funcs, _ = parse_retail_slice(self.root / source.PATHS['edge_wrapper_original'])
        at = elf_slot_offset(expected['elf'], lo, hi-lo)
        self.assertEqual(expected['elf'][at:at+hi-lo], self.rom[0x19E040:0x19E040+hi-lo])
        owner = expected['edge_wrapper_owner'].decode()
        self.assertNotIn('return 0;', owner)
        self.assertNotIn('Non-matching placeholders', owner)
        self.receipt('scope', inputs=len(source.PATHS), predictions=hashes, complete_owner_functions=len(funcs),
            complete_owner_bytes=hi-lo, all_owner_slots_byte_exact=True, no_owner_zero_return_placeholders=True, metadata_exclusions=0)

    def test_10_independently_assembled_original_call_rebases(self):
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel '+source.FUNCTION+'\n', 1)[1].split('endlabel '+source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "'+str(self.root / 'conker/include/asm_processor_prelude.inc')+'"\n.type '+source.FUNCTION+
            ', @function\nglabel '+source.FUNCTION+'\n'+original+'\n.size '+source.FUNCTION+', . - '+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        text, funcs, rel = parse_object(path.with_suffix('.o'))
        f = funcs[source.FUNCTION]
        old = text[f['value']:f['value']+f['size']]
        old_rel = {a-f['value']: v for a, v in rel.items() if f['value'] <= a < f['value']+f['size']}
        raw, bindings = source.checked_object(self.obj)
        names = ('func_150AEEB0', 'func_150BD740', 'func_150CDBB0', 'func_10010154')
        targets = (source.FIRST, source.SECOND, source.THIRD, source.SOUND)
        count = 0
        for entry, delta in ((0x15201000, 0x2000), (0x15302000, 0x4000), (0x15403000, 0x6000)):
            links = {n: a+delta for n, a in zip(names, targets)}
            streams = []
            for i, (data, rows) in enumerate(((raw, bindings), (old, old_rel))):
                asm, missing = emit_function(data, dict(value=0, size=len(data)), rows, source.FUNCTION, links)
                self.assertFalse(missing)
                file = self.out / ('rebase-%X-%d.s' % (entry, i))
                file.write_text(asm)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(file.with_suffix('.o')), str(file)], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(file.with_suffix('.ld')), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % v for v in links.items()], '-o', str(file.with_suffix('.elf')), str(file.with_suffix('.o'))], check=True, capture_output=True)
                streams.append(list(struct.unpack_from('>42I', sections(file.with_suffix('.elf'))['.text'][1]))+[0])
            self.assertEqual(streams[0], streams[1])
            for kind, phase, flags, mode in itertools.product((0x13, 0x23, 0x1E, 0x54, 0), (0, 8), (0, 0xABCDEF81), (0, 1)):
                memory, args = guest.fixture(kind, flags)
                models = [guest.EffectOracle(w, memory, args, phase=phase, mode=mode, entry=entry,
                    bindings={a+delta: a for a in targets}).run() for w in streams]
                self.assertEqual(models[0].calls, guest.reference(memory, args, phase))
                self.assertEqual(guest.edge.state(models[0]), guest.edge.state(models[1]))
                count += 1
        self.receipt('rebases', independent_original_sets=3, paired_cases=count, all_four_call_bindings_changed=True)
