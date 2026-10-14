"""Frame dispatch ABI, metadata byte loop, public aliases and strict slot match."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_codec_frame_dispatch_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_burst_packet_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import signed
from tools.check_game_data_layout import audit_layout
from tools.tests import codec_frame_dispatch_checkpoint as checkpoint

ENTRY, CONTEXT, OUT = 0x151F86B0, 0x21000, 0x31000
HEADER, DECODE, DECODE2, READ, READ2, NOTIFY, NOTIFY2, STRLEN = 0x151F8088, 0x18001000, 0x18002000, 0x18003000, 0x18004000, 0x18005000, 0x18006000, 0x10022EEC
STATUS, NOTIFIER = 0x800E0E04, 0x800E0E00
PAYLOADS = (b'\0', b'\xFF\0', b'ab\x80\0', b'\xA5' * 255 + b'\0')


def fixture(index, metadata, notify, alias, seek=0x87654321):
    memory = {machine.STACK + i: 0xA5 for i in range(-0x600, 0x180)}
    memory.update({CONTEXT + i: (i * 13 + 0xA5) & 255 for i in range(-16, 0x84A0)})
    memory.update({OUT + i: 0xA5 for i in range(-16, 32)})
    for offset, value in ((0, 0x12345678), (4, READ), (0x3BA0, index),
            (0x3BC8, metadata), (0x3F8C, 2), (0x8474, seek), (0x8478, DECODE)):
        put(memory, CONTEXT + offset, value)
    put(memory, STATUS, 0x76543210)
    put(memory, NOTIFIER, NOTIFY if notify else 0)
    outputs = ((OUT, OUT + 4), (OUT, OUT), (CONTEXT + 0x3F8C, OUT + 4),
        (OUT, CONTEXT + 0x3BC8), (CONTEXT + 0x3BA0, OUT + 4))[alias]
    return memory, (CONTEXT, *outputs)


def effects(memory, target, mode, reads=0):
    if target == HEADER and mode == 1:
        for offset, value in ((0x3BA0, 4), (0x8474, 3), (0, 0x87654321)):
            put(memory, CONTEXT + offset, value)
    if target == HEADER and mode == 2:
        put(memory, CONTEXT + 0x8478, DECODE2)
    if target in (DECODE, DECODE2) and mode == 2:
        put(memory, CONTEXT + 0x3F8C, 2)
        put(memory, CONTEXT + 0x3BC8, 1)
    if target in (DECODE, DECODE2) and mode == 5:
        put(memory, CONTEXT + 0x3F8C, 0)
        put(memory, CONTEXT + 0x3BC8, 0)
    if target in (READ, READ2) and mode == 3 and reads == 1:
        put(memory, CONTEXT, 0xFEDCBA98)
        put(memory, CONTEXT + 4, READ2)
        put(memory, NOTIFIER, NOTIFY2)
    if target == STRLEN and mode == 4:
        # Deliberate external-mutation probe, not a claimed strlen side effect.
        put(memory, NOTIFIER, NOTIFY2)


def reference(memory, arguments, header, decoded, payload, fail_at, mode, phase):
    result, calls = dict(memory), []
    _, output, count = arguments
    current = (read(result, CONTEXT + 0x3BA0) + 1) & 0xFFFFFFFF
    put(result, CONTEXT + 0x3BA0, 0 if signed(current) >= 6 else current)
    calls.append((HEADER, (CONTEXT, read(result, CONTEXT + 0x8474)), None))
    effects(result, HEADER, mode)
    if header == 0:
        put(result, STATUS, 3)
        return result, calls, 0
    put(result, CONTEXT + 0x8474, 0xFFFFFFFF)
    target = read(result, CONTEXT + 0x8478)
    calls.append((target, (CONTEXT,), None))
    effects(result, target, mode)
    if decoded == 0:
        return result, calls, 0
    position = read(result, CONTEXT + 0x3BA0)
    put(result, output, CONTEXT + position * 1160 + 0x2070)
    put(result, count, read(result, CONTEXT + 0x3F8C))
    if read(result, CONTEXT + 0x3BC8):
        buffer = machine.STACK + phase - 0x130 + 0x28
        data = bytearray()
        for index in range(256):
            callback, handle = read(result, CONTEXT + 4), read(result, CONTEXT)
            calls.append((callback, (handle, buffer + index, 1, 0xFFFFFFFF), None))
            byte = 0 if fail_at == index else payload[index]
            data.append(byte)
            effects(result, callback, mode, index + 1)
            if fail_at == index or byte == 0:
                break
        else:
            raise AssertionError('Fixture metadata must terminate within 256 bytes')
        callback = read(result, NOTIFIER)
        if callback:
            calls.append((STRLEN, (buffer,), bytes(data)))
            effects(result, STRLEN, mode)
            calls.append((read(result, NOTIFIER), (0, buffer, len(data)), bytes(data)))
    return result, calls, decoded & 0xFFFFFFFF


class DispatchOracle(machine.BurstOracle):
    def __init__(self, words, memory, arguments, header=1, decoded=1, payload=b'\0', fail_at=None,
            mode=0, phase=0, fault=None):
        super().__init__(words, memory, actor=CONTEXT, phase=phase, mode=mode,
            entry=ENTRY, arguments=arguments, symbols={'unused': 0})
        self.header, self.decoded, self.payload, self.fail_at = header, decoded, payload, fail_at
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.byte_reads, self.seek_at_decode = 0, []
        self.code = faults.TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction and ENTRY <= self.current_pc < ENTRY + 436:
            if self.accesses == self.root_fault:
                raise faults.AccessBoundary
            self.accesses += 1

    def string(self, address):
        data = bytearray()
        for i in range(256):
            byte = self.get(address + i, 1)
            data.append(byte)
            if byte == 0:
                return bytes(data)
        raise AssertionError('Unterminated fixture metadata')

    def record_call(self, target):
        sizes = {HEADER: 2, DECODE: 1, DECODE2: 1, READ: 4, READ2: 4, NOTIFY: 3, NOTIFY2: 3, STRLEN: 1}
        assert target in sizes, hex(target)
        args = tuple(self.arguments(sizes[target]))
        payload = self.string(args[0]) if target == STRLEN else bytes(self.get(args[1] + i, 1) for i in range(args[2])) if target in (NOTIFY, NOTIFY2) else None
        self.calls.append((target, args, payload))
        self.events.append(('CALL', target, args))
        if target in (DECODE, DECODE2):
            self.seek_at_decode.append(read(self.memory, CONTEXT + 0x8474))

    def hook(self, target):
        args = self.calls[-1][1]
        returned = self.header if target == HEADER else self.decoded if target in (DECODE, DECODE2) else 0x11223344
        if target in (READ, READ2):
            byte = 0 if self.fail_at == self.byte_reads else self.payload[self.byte_reads]
            self.put(args[1], byte, 1)
            returned = 0 if self.fail_at == self.byte_reads else 1
            self.byte_reads += 1
        if target == STRLEN:
            returned = len(self.calls[-1][2]) - 1
        effects(self.memory, target, self.mode, self.byte_reads)
        for i in range(4):
            self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = returned & 0xFFFFFFFF


class CodecFrameDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>112I', cls.rom, 0x225B60))
        cls.original = cls.root / 'conker/asm/nonmatchings/game_221290/func_151F86B0.s'

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)], capture_output=True, text=True, check=True)
        return obj

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_complete_owners_static_guard_closure_and_both_padders(self):
        before = (self.out / 'before-owner').read_text()
        objects, neighbors = {}, {}
        for label, flags in (('O2', ('-O2', '-g3')), ('g', ('-g',))):
            old, w0 = build.compile_owner(self.root, self.out, before, 'owner-before-' + label, flags)
            new, w1 = build.compile_owner(self.root, self.out, source.recover(before), 'owner-after-' + label, flags)
            t0, f0, r0 = parse_object(old)
            t1, f1, r1 = parse_object(new)
            self.assertEqual(set(f0), set(f1))
            for name in set(f0) - {source.FUNCTION}:
                a, b = f0[name], f1[name]
                self.assertEqual(a['size'], b['size'], name)
                self.assertEqual(t0[a['value']:a['value'] + a['size']], t1[b['value']:b['value'] + b['size']], name)
                relative = lambda table, info: {at - info['value']: value for at, value in table.items() if info['value'] <= at < info['value'] + info['size']}
                self.assertEqual(relative(r0, a), relative(r1, b), name)
            self.assertEqual(normalized_pools(old), normalized_pools(new), label)
            self.assertLessEqual(w1.count('cfe: Warning'), w0.count('cfe: Warning'))
            objects[label], neighbors[label] = new, len(f0) - 1
        raw, functions = build.link_owner(self.root, self.out, objects['g'], source.OWNER)
        info = functions[source.FUNCTION]
        self.assertEqual(info['size'], 436)
        words = list(struct.unpack_from('>109I', raw, info['value']))
        self.assertEqual([i for i, (a, b) in enumerate(zip(words, self.retail)) if a != b], [55, 67, 68, 70, 73, 75])
        for i in range(67, 76):
            word = words[i]
            self.assertIn(word >> 26, (0, 9, 35))
            for shift in ((21, 16, 11) if word >> 26 == 0 else (21, 16)):
                register = word >> shift & 31
                replacement = {8: 10, 10: 8}.get(register, register)
                word = word & ~(31 << shift) | replacement << shift
            self.assertEqual(word, self.retail[i], i)
        self.assertEqual(words[55] & ~(31 << 21 | 31 << 16), self.retail[55] & ~(31 << 21 | 31 << 16))
        self.assertEqual((words[55] >> 21 & 31, words[55] >> 16 & 31), (self.retail[55] >> 16 & 31, self.retail[55] >> 21 & 31))
        self.assertEqual(self.retail[109:], [0, 0, 0])
        guards = self.out / 'guards.csv'
        guards.write_bytes((self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        makefile = source.recover_makefile((self.out / 'before-makefile').read_text())
        start = makefile.index('CODEC_RETAIL_G_FUNCTIONS :=')
        selected = makefile[start:makefile.index('\n$(BUILD_DIR)', start)].split(':=', 1)[1].replace('\\', '').split()
        self.assertEqual(len(selected), 9)
        self.assertIn(source.FUNCTION, selected)
        primary = pad_c_object.emit_padded_assembly(objects['O2'], self.root / 'conker/retail_layout.us.txt', source.OWNER,
            function_objects={name: objects['g'] for name in selected}, word_patches_path=guards)
        primary_obj = self.assemble(primary, 'primary-padded')
        text, f, r = parse_object(objects['g'])
        extracted, unresolved = emit_function(text, f[source.FUNCTION], r, source.FUNCTION, nm_anchors(self.root / 'conker/build/conker.us.elf'))
        self.assertFalse(unresolved)
        compact = self.assemble(extracted, 'selected-compact')
        selected_guards = self.out / 'selected-guards.csv'
        selected_guards.write_text(guards.read_text().splitlines()[0] + '\n' + source.GUARD_ROWS)
        generated = emit_padded_assembly(compact, self.original, filename=source.OWNER, word_patches_path=selected_guards)
        generated_obj = self.assemble(generated, 'generated-padded')
        for artifact in (primary_obj, generated_obj):
            data, f = build.link_owner(self.root, self.out, artifact, source.OWNER)
            self.assertEqual(data[f[source.FUNCTION]['value']:f[source.FUNCTION]['value'] + 448], self.rom[0x225B60:0x225D20])
        self.receipt('owners', profiles=neighbors, body_words=109, slot_words=112, alignment_nops=3,
            guards=6, one_commutative_add_and_closed_five_word_register_cycle=True,
            all_neighbors_relocations_and_pools_fixed=True, both_padders_and_nine_function_mix=True)

    def qualified_words(self):
        text, f = build.link_owner(self.root, self.out, self.out / 'generated-padded.o', source.OWNER)
        return list(struct.unpack_from('>112I', text, f[source.FUNCTION]['value']))

    def test_02_original_and_rebased_independent_links(self):
        original = self.assemble(self.original.read_text() + '\n.type ' + source.FUNCTION + ',@function\n.size ' + source.FUNCTION + ',436\n', 'original-retail')
        anchors = nm_anchors(self.root / 'conker/build/conker.us.elf')
        anchors.update(build.load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt')))
        for phase, base in enumerate((ENTRY, 0x16108000)):
            spans = []
            for index, artifact in enumerate((original, self.out / 'primary-padded.o', self.out / 'generated-padded.o')):
                text, f, r = parse_object(artifact)
                info = dict(f[source.FUNCTION], size=448)
                asm, unresolved = emit_function(text, info, r, source.FUNCTION, anchors)
                self.assertFalse(unresolved)
                single = self.assemble(asm, 'rebase-input-%d-%d' % (phase, index))
                symbols = {symbol for at, entries in r.items() if info['value'] <= at < info['value'] + 448 for _, symbol in entries}
                values = {symbol: (0x17008000 + i * 4 if symbol.startswith('func_') or symbol == 'strlen' else 0x90007FFC + i * 4) for i, symbol in enumerate(sorted(symbols))} if phase else {symbol: anchors[symbol] for symbol in symbols}
                script = single.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                elf = single.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in values.items()], '-o', str(elf), str(single)], capture_output=True, text=True, check=True)
                spans.append(sections(elf)['.text'][1][:448])
            self.assertEqual(spans[0], spans[1])
            self.assertEqual(spans[0], spans[2])

    def test_03_mips_statuses_output_aliases_metadata_and_live_callbacks(self):
        words, cases, seen = self.qualified_words(), 0, set()
        for ordinal, (index, header, decoded, mode, alias, phase) in enumerate(itertools.product(
                (0xFFFFFFFE, 0, 4, 5, 0x7FFFFFFF), (0, 1), (0, 1, 0x80000000), range(6), range(5), (0, 8))):
            payload = PAYLOADS[(ordinal + mode + alias) % len(PAYLOADS)]
            fail_at = (len(payload) - 1) // 2 if mode == 2 else None
            memory, arguments = fixture(index, ordinal & 1, ordinal % 3 != 0, alias)
            expected, calls, returned = reference(memory, arguments, header, decoded, payload, fail_at, mode, phase)
            models = [DispatchOracle(body, memory, arguments, header, decoded, payload, fail_at, mode, phase).run() for body in (self.retail, words)]
            for model in models:
                self.assertEqual(model.calls, calls)
                self.assertEqual(model.r[2], returned)
                self.assertEqual(model.seek_at_decode, [0xFFFFFFFF] if header else [])
                self.assertEqual({a: v for a, v in model.memory.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180},
                    {a: v for a, v in expected.items() if not machine.STACK - 0x600 <= a < machine.STACK + 0x180})
            self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(ENTRY, ENTRY + 436, 4)) - {ENTRY + 102 * 4, ENTRY + 103 * 4})
        self.receipt('mips', cases=cases, reached_words=len(seen), unreachable_words=[102, 103],
            padding_nops_not_executed=3, full32_statuses_and_signed_counter_wrap=True,
            five_output_alias_layouts=True, metadata_lengths_through_256=True,
            fresh_reader_handle_decode_and_notifier_lookups=True, full_instruction_state_equal=True,
            EOF_fixture_writes_zero_for_defined_strlen=True, helpers_are_bounded_contract_hooks=True)

    def test_04_every_fired_root_memory_prefix(self):
        words, cuts = self.qualified_words(), 0
        for index, header, decoded, mode, alias, payload in ((5, 0, 1, 0, 0, b'\0'),
                (0, 1, 0, 0, 0, b'\0'), (4, 1, 1, 3, 2, b'\xFFa\0'),
                (0, 1, 1, 4, 3, b'\x80\0'), (0x7FFFFFFF, 1, 0x80000000, 2, 4, b'x\0')):
            memory, arguments = fixture(index, 1, 1, alias)
            finished = DispatchOracle(self.retail, memory, arguments, header, decoded, payload, None, mode).run()
            for cut in range(finished.accesses):
                models = [DispatchOracle(body, memory, arguments, header, decoded, payload, None, mode, fault=cut) for body in (self.retail, words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                    self.assertEqual(model.accesses, cut)
                self.assertEqual(machine.complete_state(models[0]), machine.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of), (models[1].current_pc, models[1].delay_of))
                cuts += 1
        self.receipt('faults', fired_prefixes=cuts, actual_root_memory_instructions=True,
            helpers_atomic_and_bounded=True, no_portable_C_or_arbitrary_helper_fault_claim=True)

    def test_05_effective_compiled_and_expected_word_relocation_controls(self):
        before = (self.out / 'before-owner').read_text()
        for label, body in (('wrap', source.BODY.replace('>= 6', '>= 5')),
                ('command', source.BODY.replace('&metadata[index], 1, -1', '&metadata[index], 1, 0'))):
            self.assertNotEqual(body, source.BODY)
            obj, _ = build.compile_owner(self.root, self.out, source.recover(before, body), 'negative-' + label, ('-g',))
            raw, f = build.link_owner(self.root, self.out, obj, source.OWNER)
            words = list(struct.unpack_from('>109I', raw, f[source.FUNCTION]['value']))
            self.assertNotEqual(words, self.retail[:109])
            memory, arguments = fixture(4, 1, 1, 0)
            model = DispatchOracle(words, memory, arguments, 1, 1, b'\xFF\0').run()
            expected, calls, _ = reference(memory, arguments, 1, 1, b'\xFF\0', None, 0, 0)
            if label == 'command':
                self.assertNotEqual(model.calls, calls)
            else:
                self.assertNotEqual(read(model.memory, CONTEXT + 0x3BA0), read(expected, CONTEXT + 0x3BA0))
        for old, new in (('0x01485821,0x010A5821', '0x01485820,0x010A5821'),
                (',-,-,Normalize', ',R_MIPS_LO16:D_800E0E00,-,Normalize')):
            bad = self.out / 'negative-guards.csv'
            rows = source.GUARD_ROWS.replace(old, new)
            self.assertNotEqual(rows, source.GUARD_ROWS)
            bad.write_text((self.out / 'selected-guards.csv').read_text().splitlines()[0] + '\n' + rows)
            with self.assertRaises(ValueError):
                emit_padded_assembly(self.out / 'selected-compact.o', self.original, filename=source.OWNER, word_patches_path=bad)

    def test_06_native32_aliases_metadata_and_callback_controls(self):
        native = r'''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef s32 (*func_151F6FD0_ReadFunc)(s32,void *,s32,s32);
static u8 storage[0x84C0],expected[0x84C0];static u8 *context;
static u32 output[2],expectedOutput[2],expectedStatus,expectedNotify;
s32 D_800E0E04,D_800E0E00;
static s32 headerResult,decodeResult,mode,error,events,total,byteReads,kind,failAt;
static u8 *metadataBase;static u32 wanted[270][5];static u8 wantedText[256];static int wantedSize;
static u32 get(u8 *p,int offset){return *(u32 *)(p+offset);}
static void set(u8 *p,int offset,u32 value){*(u32 *)(p+offset)=value;}
static s32 decodeA(void *);static s32 decodeB(void *);
static s32 readerA(s32,void *,s32,s32);static s32 readerB(s32,void *,s32,s32);
static void notifyA(s32,char *,s32);static void notifyB(s32,char *,s32);
static u8 byteAt(int i){if(kind==0)return 0;if(kind==1)return i?0:0xFF;
 if(kind==2)return i==0?'a':i==1?'b':i==2?0x80:0;return i<255?0xA5:0;}
static void effects(u8 *p,u32 *notify,int role,int reads){
 if(role==0&&mode==1){set(p,0x3BA0,4);set(p,0x8474,3);set(p,0,0x87654321);}
 if(role==0&&mode==2)set(p,0x8478,(u32)decodeB);
 if((role==1||role==2)&&mode==2){set(p,0x3F8C,2);set(p,0x3BC8,1);}
 if((role==1||role==2)&&mode==5){set(p,0x3F8C,0);set(p,0x3BC8,0);}
 if((role==3||role==4)&&mode==3&&reads==1){set(p,0,0xFEDCBA98);set(p,4,(u32)readerB);*notify=(u32)notifyB;}
 if(role==5&&mode==4)*notify=(u32)notifyB;}
static void want(u32 role,u32 a,u32 b,u32 c,u32 d){
 wanted[total][0]=role;wanted[total][1]=a;wanted[total][2]=b;wanted[total][3]=c;wanted[total][4]=d;total++;}
static void event(u32 role,u32 a,u32 b,u32 c,u32 d){u32 row[5]={role,a,b,c,d};int i;
 if(events>=total){error=1;return;}for(i=0;i<5;i++)if(row[i]!=wanted[events][i])error=1;events++;}
s32 func_151F8088(void *p,s32 seek){if(p!=context)error=1;event(0,(u32)seek,get(context,0x3BA0),0,0);
 effects(context,(u32 *)&D_800E0E00,0,0);return headerResult;}
static s32 decode(void *p,int role){if(p!=context)error=1;event((u32)role,get(context,0x8474),0,0,0);
 effects(context,(u32 *)&D_800E0E00,role,0);return decodeResult;}
static s32 decodeA(void *p){return decode(p,1);}static s32 decodeB(void *p){return decode(p,2);}
static s32 reading(s32 handle,void *p,s32 size,s32 command,int role){u8 byte;
 if(!metadataBase)metadataBase=p;event((u32)role,(u32)handle,(u32)((u8 *)p-metadataBase),(u32)size,(u32)command);
 byte=byteReads==failAt?0:byteAt(byteReads);*(u8 *)p=byte;
 effects(context,(u32 *)&D_800E0E00,role,byteReads+1);return byteReads++==failAt?0:1;}
static s32 readerA(s32 a,void *b,s32 c,s32 d){return reading(a,b,c,d,3);}
static s32 readerB(s32 a,void *b,s32 c,s32 d){return reading(a,b,c,d,4);}
u32 strlen(const char *p){int i;if((const u8 *)p!=metadataBase)error=1;event(5,0,0,0,0);
 for(i=0;i<256;i++)if(!p[i]){effects(context,(u32 *)&D_800E0E00,5,0);return (u32)i;}error=1;return 255;}
static void notifying(s32 command,char *p,s32 count,int role){int i;
 if((u8 *)p!=metadataBase)error=1;event((u32)role,(u32)command,(u32)count,0,0);
 if(count!=wantedSize){error=1;return;}for(i=0;i<count;i++)if((u8)p[i]!=wantedText[i])error=1;}
static void notifyA(s32 a,char *b,s32 c){notifying(a,b,c,6);}
static void notifyB(s32 a,char *b,s32 c){notifying(a,b,c,7);}
''' + source.BODY + r'''
static void refStore(u8 *p,int which,int alias,u32 value){
 if(which==0&&alias==2)set(p,0x3F8C,value);else if(which==0&&alias==4)set(p,0x3BA0,value);
 else if(which==1&&alias==3)set(p,0x3BC8,value);else expectedOutput[which==1&&alias==1?0:which]=value;}
static u32 ref(u8 *p,int alias){u32 cursor,value,role;int i;
 value=get(p,0x3BA0)+1;set(p,0x3BA0,(s32)value>=6?0:value);
 want(0,get(p,0x8474),get(p,0x3BA0),0,0);effects(p,&expectedNotify,0,0);
 if(!headerResult){expectedStatus=3;return 0;}set(p,0x8474,0xFFFFFFFF);
 role=get(p,0x8478)==(u32)decodeB?2:1;want(role,get(p,0x8474),0,0,0);effects(p,&expectedNotify,(int)role,0);
 if(!decodeResult)return 0;cursor=get(p,0x3BA0);
 refStore(p,0,alias,(u32)context+cursor*1160+0x2070);refStore(p,1,alias,get(p,0x3F8C));
 if(get(p,0x3BC8)){for(i=0;i<256;i++){
  role=get(p,4)==(u32)readerB?4:3;want(role,get(p,0),(u32)i,1,0xFFFFFFFF);
  wantedText[i]=i==failAt?0:byteAt(i);effects(p,&expectedNotify,(int)role,i+1);
  if(i==failAt||!wantedText[i])break;}
  wantedSize=i+1;if(expectedNotify){want(5,0,0,0,0);effects(p,&expectedNotify,5,0);
   want(expectedNotify==(u32)notifyB?7:6,0,(u32)wantedSize,0,0);}}
 return (u32)decodeResult;}
static int run(void){u32 indices[5]={0xFFFFFFFE,0,4,5,0x7FFFFFFF};
 int ni,h,d,alias,phase,i,ordinal=0,cases=0;u32 returned,wantedReturn;u8 *p;void **out;s32 *count;
 if(sizeof(void *)!=4||sizeof(s32)!=4)return 80;
 for(ni=0;ni<5;ni++)for(h=0;h<2;h++)for(d=0;d<3;d++)for(mode=0;mode<6;mode++)for(alias=0;alias<5;alias++)for(phase=0;phase<2;phase++,ordinal++){
  /* The strlen-time external mutation is a MIPS scheduling probe, not a libc contract. */
  if(mode==4)continue;cases++;
  context=storage+16+phase*4;p=expected+16+phase*4;kind=(ordinal+mode+alias)%4;
  failAt=mode==2?(kind==0?0:kind==1?0:kind==2?1:127):-1;
  headerResult=h;decodeResult=d==0?0:d==1?1:(s32)0x80000000;
  for(i=0;i<(int)sizeof(storage);i++)storage[i]=(u8)(i*13+0xA5);
  set(context,0,0x12345678);set(context,4,(u32)readerA);set(context,0x3BA0,indices[ni]);
  set(context,0x3BC8,(u32)(ordinal&1));set(context,0x3F8C,2);set(context,0x8474,0x87654321);set(context,0x8478,(u32)decodeA);
  for(i=0;i<(int)sizeof(storage);i++)expected[i]=storage[i];
  output[0]=output[1]=expectedOutput[0]=expectedOutput[1]=0xA5A5A5A5;
  D_800E0E04=(s32)(expectedStatus=0x76543210);D_800E0E00=(s32)(expectedNotify=ordinal%3?(u32)notifyA:0);
  error=events=total=byteReads=wantedSize=0;metadataBase=0;wantedReturn=ref(p,alias);
  out=(void **)(alias==2?context+0x3F8C:alias==4?context+0x3BA0:(u8 *)&output[0]);
  count=(s32 *)(alias==3?context+0x3BC8:alias==1?(u8 *)&output[0]:(u8 *)&output[1]);
  returned=(u32)func_151F86B0(context,out,count);
  if(error||events!=total||returned!=wantedReturn||(u32)D_800E0E04!=expectedStatus||(u32)D_800E0E00!=expectedNotify)return 1;
  if(output[0]!=expectedOutput[0]||output[1]!=expectedOutput[1])return 2;
  for(i=0;i<(int)sizeof(storage);i++)if(storage[i]!=expected[i])return 2;
 }return cases==1500?0:81;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for label, profile, body, status in (('O2', '-O2', source.BODY, 0), ('O0', '-O0', source.BODY, 0),
                ('negative-command', '-O2', source.BODY.replace('&metadata[index], 1, -1', '&metadata[index], 1, 0'), 1),
                ('negative-wrap', '-O2', source.BODY.replace('>= 6', '>= 5'), 1)):
            path = self.out / ('native-' + label + '.c')
            path.write_text(native.replace(source.BODY, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-fwrapv', '-fno-builtin',
                '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra',
                '-Werror', '-Wno-misleading-indentation', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, status, label)
        self.receipt('native', cases_per_profile=1500, profiles=['O2', 'O0'], native32_required=True,
            five_public_output_alias_layouts=True, callback_arguments_and_metadata_bytes_compared=True,
            full_context_and_output_memory_compared=True, signed_arithmetic_wrap_profile=True,
            EOF_fixtures_define_string_bytes_without_changing_production=True,
            strlen_time_external_mutation_kept_in_MIPS_only=True,
            wrong_wrap_and_command_controls_fired=True, no_audio_runtime_or_guest_endian_claim=True)

    def test_07_installed_source_profile_guards_and_closed_image(self):
        source.freeze(self.root, self.out)
        self.assertEqual((self.root / 'conker/src/game_221290.c').read_text(), source.recover((self.out / 'before-owner').read_text()))
        self.assertEqual((self.root / 'conker/Makefile').read_text(), source.recover_makefile((self.out / 'before-makefile').read_text()))
        self.assertEqual((self.root / 'conker/retail_word_patches.us.csv').read_bytes(), (self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), (self.out / 'before-progress').read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        current = (self.root / 'conker/build/conker.us.elf').read_bytes()
        expected = bytearray(before)
        at = image.elf_slot_offset(before, ENTRY, 448)
        expected[at:at + 448] = self.rom[0x225B60:0x225D20]
        with patch.object(image.screen, 'ENTRY', ENTRY):
            size = image.elf_symbol_size_offset(before, source.FUNCTION)
        self.assertEqual(struct.unpack_from('>I', before, size)[0], 12)
        struct.pack_into('>I', expected, size, 436)
        self.assertEqual(current, bytes(expected), 'Only the dispatcher slot and its code extent may change')
        symbols = canonical_symbols(before)
        old = next(row for row in symbols if row[0] == source.FUNCTION)
        symbols[old] -= 1
        symbols[(old[0], old[1], 436, *old[3:])] += 1
        self.assertEqual(+symbols, canonical_symbols(current))
        data = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        self.receipt('image', ELF_sha256=hashlib.sha256(current).hexdigest(),
            changed_slot_bytes=sum(a != b for a, b in zip(before[at:at + 448], expected[at:at + 448])),
            body_words=109, slot_words=112, retained_alignment_nops=3,
            only_one_public_extent_change=True, every_other_ELF_byte_fixed=True,
            new_guards=6, unchanged_progress=True, one_new_g_profile_selection=True, protected_data=data)

    def test_08_effective_current_source_image_and_immutable_input_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        for filename in ('conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv', 'conker/progress.csv'):
            path = self.root / filename
            bad = rb(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_profile_guards_and_closed_image()
        for filename in ('conker/src/game_221290.c', 'conker/Makefile'):
            path = self.root / filename
            bad = rt(path) + '\n'
            with patch.object(Path, 'read_text', lambda p, *a, value=bad, **k: value if p == path else rt(p, *a, **k)):
                with self.assertRaises(AssertionError):
                    self.test_07_installed_source_profile_guards_and_closed_image()
        path = self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: b'changed baseline' if p == path else rb(p)):
            with self.assertRaisesRegex(ValueError, 'immutable frame-dispatch input'):
                self.test_07_installed_source_profile_guards_and_closed_image()

    def test_09_pinned_inverse_and_unknown_input_controls(self):
        self.test_07_installed_source_profile_guards_and_closed_image()
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, path, self.root), checkpoint.fixture(self.root, 'before', key))
            bad = data + b'\n'
            self.assertEqual(checkpoint.previous_input(bad, path, self.root), bad)


if __name__ == '__main__':
    unittest.main()
