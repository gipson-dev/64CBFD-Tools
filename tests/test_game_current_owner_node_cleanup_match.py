"""Current-owner cleanup: live nested iterators, canonical nodes and literal ABI."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest
from unittest.mock import patch
from tools.experiments import game_current_owner_node_cleanup_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
SYMBOLS = dict(D_800DD190=0x800DD190, D_800DCE94=0x800DCE94,
    D_800DD198=0x800DD198, D_800C3E78=0x800C3E78, func_1516972C=0x1516972C)
NODES = tuple(0x30000 + i * 0x400 for i in range(6)) + (0x38000, 0x38400)
PARENT, PARENT_ROM, MODE, TABLE = 0x1506DE84, 0x9B334, 0x800D1580, 0x80099D54
SCAN, DEFAULT, FREE, PROVIDER, FLAG = 0x151696DC, 0x15169804, 0x15168B10, 0x15600000, 0x15604000


def signed_byte(value):
    return ((value & 255) ^ 128) - 128


def slot(memory, symbols=SYMBOLS):
    return (symbols['D_800DD198'] + 4 * signed_byte(memory[symbols['D_800DD190']])) & 0xFFFFFFFF


@dataclass(frozen=True)
class Case:
    depth: int = -1
    current: int = 0
    pattern: int = 0
    mode: int = 0
    empty: bool = False


def owners(case):
    if case.pattern == 0:
        return [case.current] * 8
    if case.pattern == 1:
        return [case.current if i % 2 == 0 else case.current ^ 128 for i in range(8)]
    if case.pattern == 2:
        return [case.current ^ 1] * 8
    return [case.current if i == 0 else (case.current + 37 * i) & 255 for i in range(8)]


def fixture(case, symbols=SYMBOLS):
    m = {STACK + i: (i * 17 + 0xA5) & 255 for i in range(-2048, 512)}
    for i in range(-128, 128):
        put(m, (symbols['D_800DD198'] + 4 * i) & 0xFFFFFFFF, 0)
    for i, node in enumerate(NODES):
        m.update({node + j: (i * 31 + j * 13 + 7) & 255 for j in range(0x1D8)})
        m[node] = 1
        put(m, node + 8, NODES[i + 1] if i not in (5, 7) else 0)
        m[node + 0x3F] = owners(case)[i]
    m[symbols['D_800DD190']] = case.depth & 255
    m[symbols['D_800C3E78']] = case.current
    put(m, symbols['D_800DCE94'], 0 if case.empty else NODES[0])
    m[FLAG] = 0
    return m


def effects(memory, case, node, state, symbols=SYMBOLS, recurse=None):
    if state['fired'] or state['inside']:
        return
    state['fired'] = True
    saved = read(memory, slot(memory, symbols))
    if case.mode & 1:
        put(memory, node + 8, NODES[6])
    if case.mode & 2:
        memory[symbols['D_800C3E78']] ^= 128
        if saved:
            memory[saved + 0x3F] = memory[symbols['D_800C3E78']]
    if case.mode & 4:
        put(memory, slot(memory, symbols), read(memory, saved + 8) if saved else 0)
    if case.mode & 8:
        value = read(memory, slot(memory, symbols))
        memory[symbols['D_800DD190']] = (memory[symbols['D_800DD190']] + 1) & 255
        put(memory, slot(memory, symbols), value)
    if case.mode & 16:
        assert recurse is not None
        put(memory, symbols['D_800DCE94'], NODES[6])
        state['inside'] = True
        recurse()
        state['inside'] = False


def reference(initial, case, symbols=SYMBOLS):
    m, calls, observations = dict(initial), [], []
    state = dict(fired=False, inside=False)
    def walk():
        # Preserve retail's early head read and cached slot for guest aliases.
        depth = m[symbols['D_800DD190']]
        node = read(m, symbols['D_800DCE94'])
        m[symbols['D_800DD190']] = (depth + 1) & 255
        cursor = slot(m, symbols)
        steps = 0
        while node:
            steps += 1
            assert steps <= 16, 'Unbounded fixture list'
            following = read(m, node + 8)
            current = m[symbols['D_800C3E78']]
            put(m, cursor, following)
            if current == m[node + 0x3F]:
                calls.append((symbols['func_1516972C'], (node,)))
                observations.append((node, m[symbols['D_800DD190']], current))
                effects(m, case, node, state, symbols, walk)
                cursor = slot(m, symbols)
            node = read(m, cursor)
        m[symbols['D_800DD190']] = (m[symbols['D_800DD190']] - 1) & 255
    walk()
    return m, calls, observations


def public(memory):
    return {a: b for a, b in memory.items() if not STACK - 2048 <= a < STACK + 512}


class WalkOracle(RayOracle):
    def __init__(self, words, memory, case=Case(), phase=0, symbols=SYMBOLS,
                 entry=source.ENTRY, connected=None, fault=None, chain=False):
        TimingOracle.__init__(self, words, memory, phase=phase, entry=entry,
            arguments=(0x89ABCDEF, 0x76543210, 0xA1B2C3D4, 0x12345678), connected=connected)
        self.case, self.symbols, self.chain = case, symbols, chain
        self.provider_state = dict(fired=False, inside=False)
        self.observations = []
        self.root_fault = fault

    def record_call(self, target):
        count = 0 if target == source.ENTRY else 2 if target == FREE else 1
        args = self.arguments(count)
        self.calls.append((target, args))
        self.events.append(('CALL', target, args))
        if target == self.symbols['func_1516972C']:
            self.observations.append((args[0], self.memory[self.symbols['D_800DD190']],
                self.memory[self.symbols['D_800C3E78']]))

    def hook(self, target):
        if target == self.symbols['func_1516972C'] and not self.chain:
            effects(self.memory, self.case, self.calls[-1][1][0], self.provider_state, self.symbols)
        else:
            assert self.chain and target in (FREE, PROVIDER), ('Unknown cleanup provider', hex(target))
        for i in range(4):
            self.put(self.r[29] + 4 * i, 0xB5000000 + i, 4)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.hi, self.lo, self.r[2] = 0x87654321, 0x12345678, 0xB5000002


def controls():
    b = source.SELECTED
    return dict(wrong_owner=b.replace('D_800C3E78 == node->pad3E[1]', 'D_800C3E78 != node->pad3E[1]'),
        signed_owner=b.replace('node->pad3E[1]', '(s8)node->pad3E[1]'),
        missing_filter=b.replace('D_800C3E78 == node->pad3E[1]', '1'),
        missing_unwind=b.replace('    D_800DD190--;', ''),
        late_next=b.replace('node = D_800DD198[D_800DD190];', 'node = (struct102 *)node->unk8;'),
        cached_owner=b.replace('    struct102 *node;', '    struct102 *node;\n    u8 owner = D_800C3E78;')
            .replace('D_800C3E78 == node->pad3E[1]', 'owner == node->pad3E[1]'))


def native_cases():
    result = [Case(depth, current, pattern, mode) for depth, current, pattern, mode in itertools.product(
        (-1, 0, 2), (0, 127, 128, 255), range(4), range(32))]
    result += [Case(-1, current, 0, mode) for current, mode in itertools.product(range(256), (0, 2, 15))]
    result += [Case(depth, 255, empty=True) for depth in range(256)]
    return result


def native_rows():
    node_id = lambda p: -1 if not p else NODES.index(p)
    rows = []
    for case in native_cases():
        m, calls, observations = reference(fixture(case), case)
        traces = list(observations) + [(0, 0, 0)] * (16 - len(observations))
        assert len(traces) == 16
        trace = ','.join('{%d,%d,%d}' % (node_id(p), depth, current) for p, depth, current in traces)
        nexts = ','.join(str(node_id(read(m, p + 8))) for p in NODES)
        flags = ','.join(str(m[p + 0x3F]) for p in NODES)
        slots = ','.join(str(node_id(read(m, SYMBOLS['D_800DD198'] + 4 * i))) for i in range(6))
        rows.append('{%d,%d,%d,%d,%d,%d,{%s},%d,%d,%d,{%s},{%s},{%s}}' %
            (case.depth, case.current, case.pattern, case.mode, case.empty, len(calls), trace,
             m[SYMBOLS['D_800DD190']], m[SYMBOLS['D_800C3E78']], node_id(read(m, SYMBOLS['D_800DCE94'])),
             nexts, flags, slots))
    return ',\n'.join(rows)


def native_harness(body, rows):
    return '#include <ultra64.h>\n' + source.DECLARATIONS + '''
void func_150AFDB0(void);
s8 D_800DD190;u8 D_800C3E78;struct102 *D_800DCE94;void *D_800DD198[6];
static struct {u32 left[4];struct102 nodes[8];u32 right[4];} storage;
struct Trace{s32 node;u32 depth,current;};
struct Case{s32 depth;u32 current,pattern,mode,empty,count;struct Trace trace[16];
 u32 finalDepth,finalCurrent;s32 head,next[8];u8 owner[8];s32 slots[6];};
static const struct Case cases[]={ROWS};static const struct Case *c;
static u32 calls,error,fired,inside;
typedef char ABI[(sizeof(void*)==4 && sizeof(struct102)==0x1D8 &&
 __builtin_offsetof(struct102,unk8)==8 && __builtin_offsetof(struct102,pad3E)+1==0x3F)?1:-1];
static struct102 *node(s32 id){return id<0?(struct102*)0:&storage.nodes[id];}
static s32 id(struct102 *p){u32 i;if(!p)return -1;for(i=0;i<8;i++)if(p==node((s32)i))return (s32)i;return -99;}
__attribute__((noinline,noclone)) void func_1516972C(struct102 *p){
 struct102 *saved;u32 level;
 if(calls>=c->count || id(p)!=c->trace[calls].node || (u8)D_800DD190!=c->trace[calls].depth ||
  D_800C3E78!=c->trace[calls].current)error=1;
 calls++;
 if(fired||inside)return;fired=1;
 level=(u8)D_800DD190;if(level>=6){error=1;return;}saved=(struct102*)D_800DD198[level];
 if(c->mode&1)p->unk8=(s32)node(6);
 if(c->mode&2){D_800C3E78^=128;if(saved)saved->pad3E[1]=D_800C3E78;}
 if(c->mode&4)D_800DD198[level]=saved?(struct102*)saved->unk8:(struct102*)0;
 if(c->mode&8){D_800DD190++;D_800DD198[(u8)D_800DD190]=D_800DD198[level];}
 if(c->mode&16){D_800DCE94=node(6);inside=1;func_150AFDB0();inside=0;}
}
''' .replace('ROWS', rows) + body + '''
static u8 owner(u32 i){
 if(c->pattern==0)return (u8)c->current;
 if(c->pattern==1)return (u8)(i%2?c->current^128:c->current);
 if(c->pattern==2)return (u8)(c->current^1);
 return (u8)(i?c->current+37*i:c->current);
}
int run(void){
 u32 k,i,j;u8 *p;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
  c=&cases[k];calls=error=fired=inside=0;
  for(i=0;i<4;i++)storage.left[i]=storage.right[i]=0xA5A5A5A5u;
  for(i=0;i<8;i++){
   p=(u8*)node((s32)i);for(j=0;j<sizeof(struct102);j++)p[j]=(u8)(i*31+j*13+7);
   p[0]=1;node((s32)i)->unk8=(s32)node(i==5||i==7?-1:(s32)i+1);node((s32)i)->pad3E[1]=owner(i);
  }
  for(i=0;i<6;i++)D_800DD198[i]=(void*)0;
  D_800DD190=(s8)c->depth;D_800C3E78=(u8)c->current;D_800DCE94=node(c->empty?-1:0);
  func_150AFDB0();
  if(error||calls!=c->count||(u8)D_800DD190!=c->finalDepth||D_800C3E78!=c->finalCurrent||id(D_800DCE94)!=c->head)return 23;
  for(i=0;i<6;i++)if(id((struct102*)D_800DD198[i])!=c->slots[i])return 23;
  for(i=0;i<8;i++){
   if(id((struct102*)node((s32)i)->unk8)!=c->next[i]||node((s32)i)->pad3E[1]!=c->owner[i])return 23;
   p=(u8*)node((s32)i);for(j=0;j<sizeof(struct102);j++)
    if(!(j>=8&&j<12)&&j!=0x3F&&p[j]!=(j==0?1:(u8)(i*31+j*13+7)))return 23;
  }
  for(i=0;i<4;i++)if(storage.left[i]!=0xA5A5A5A5u||storage.right[i]!=0xA5A5A5A5u)return 23;
 }
 return 0;
}
''' + START


class CurrentOwnerNodeCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD
        cls.values = source.snapshot(cls.output)
        cls.installed = (ROOT / source.SOURCE).read_bytes() != cls.values[source.SOURCE]
        source.audit_inputs(ROOT, cls.output) if cls.installed else source.freeze(ROOT, cls.output)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.truth = list(struct.unpack_from('>45I', cls.rom, source.ROM))
        linked, functions = source.link_owner(ROOT, cls.output, cls.output / 'after-owner.o', source.OWNER)
        cls.words = list(struct.unpack_from('>45I', linked, functions[source.FUNCTION]['value']))
        cls.receipt = {}

    def test_01_direct_owner_Make_and_complete_word_binding_guards(self):
        raw, bindings = source.payload(self.output / 'after-owner.o')
        source.checked_payload(raw, bindings)
        self.assertEqual(self.words, self.truth)
        q = json.loads((self.output / 'qualification.json').read_text())
        self.assertEqual((q['words'], q['frame'], q['relocations'], q['new_guards'], q['preserved_neighbors']),
            (45, 32, 19, 0, 17))
        self.assertEqual(json.loads((self.output / 'make-shadow.json').read_text())['actual_Make_commands'], 5)
        self.assertEqual(self.truth[:3], [0x27BDFFE0, 0xAFBF001C, 0xAFB00018])
        for i in range(45):
            wrong = bytearray(raw)
            wrong[4 * i] ^= 1
            with self.assertRaises(ValueError):
                source.checked_payload(bytes(wrong), bindings)
        for at in bindings:
            wrong = dict(bindings)
            wrong[at] = [('R_MIPS_26', 'unknown')]
            with self.assertRaises(ValueError):
                source.checked_payload(raw, wrong)
        self.receipt.update(words=45, frame=32, bindings=19, new_guards=0, preserved_neighbors=17,
            GLOBAL_ASM_neighbors_preserved=1, canonical_helper_declaration_and_neighbor_cast=True,
            word_controls=45, binding_controls=19, inherited_owner_warnings=2)

    def test_02_guest_live_owner_iterator_depth_mutations_and_signed_empty_axis(self):
        cases = [Case(depth, current, pattern, mode) for depth, current, pattern, mode in itertools.product(
            (-1, 0, 2, 126, 127, 128), (0, 128, 255), range(4), range(16))]
        cases += [Case(-1, current, 0, mode) for current, mode in itertools.product(range(256), (0, 2))]
        cases += [Case(depth, 255, empty=True) for depth in range(256)]
        visits, phases = set(), 0
        for case in cases:
            m = fixture(case)
            wanted, calls, observations = reference(m, case)
            models = [WalkOracle(w, m, case, phase=(phases & 1) * 8).run() for w in (self.truth, self.words)]
            for model in models:
                self.assertEqual((public(model.memory), model.calls, model.observations),
                    (public(wanted), calls, observations), case)
                visits.update(model.visits)
            self.assertEqual(complete(models[0]), complete(models[1]))
            phases += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + source.SIZE, 4)))
        self.receipt.update(guest_phases=phases, all_45_words_visited=True, signed_empty_depth_values=256,
            current_owner_values=256, live_owner_next_slot_and_depth_mutations=True,
            complete_literal_GPR_FPR_RAM_events=True, native_out_of_range_iterators_not_claimed=True)

    def test_03_native32_canonical_records_all_byte_axes_and_reentrant_provider(self):
        rows = native_rows()
        exits = {}
        for label, opt, body, valid in [('O0', '-O0', source.SELECTED, True),
                ('O2', '-O2', source.SELECTED, True), ('O3', '-O3', source.SELECTED, True)] + [
                (name, '-O2', body, False) for name, body in controls().items()]:
            unit = self.output / ('native-' + label + '.c')
            unit.write_text(native_harness(body, rows))
            exe = unit.with_suffix('')
            p = subprocess.run([*native_command(opt, valid), str(unit), '-o', str(exe)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            p = subprocess.run([str(exe)], timeout=60)
            self.assertEqual(p.returncode, 0 if valid else 23, label)
            exits[label] = p.returncode
        self.receipt.update(native32=exits, native_cases_per_profile=len(native_cases()),
            selected_trap_UBSan=True, canonical_struct102_size=0x1D8, six_valid_iterator_slots=True,
            all_256_empty_depth_and_owner_axes=True, actual_C_reentry=True,
            whole_node_bytes_and_boundary_guards_preserved=True, portable_native_aliases_claimed=False)

    def parent_table(self):
        original = self.output / 'before-conker_build_conker.us.elf'
        for address, data in sections(original).values():
            if address <= TABLE and TABLE + 56 <= address + len(data):
                return struct.unpack_from('>14I', data, TABLE - address)
        raise AssertionError('Original cleanup caller table is not mapped')

    def test_04_real_original_caller_and_current_release_iterator_repair_chain(self):
        parent = list(struct.unpack_from('>154I', self.rom, PARENT_ROM))
        table = self.parent_table()
        self.assertEqual(table.count(0x1506E0D4), 1)
        selected_mode = table.index(0x1506E0D4)
        phases = 0
        for depth, current, pattern, mode, phase, command in itertools.product(
                (-1, 0), (0, 128, 255), range(4), (0, 2, 4, 8), (0, 8), (selected_mode, 14, 0xFFFFFFFF)):
            case = Case(depth, current, pattern, mode)
            m = fixture(case)
            put(m, MODE, command)
            for i, address in enumerate(table):
                put(m, TABLE + 4 * i, address)
            wanted, calls, _ = reference(m, case) if command == selected_mode else (dict(m), [], [])
            expected_calls = [(source.ENTRY, ()), *calls] if command == selected_mode else []
            models = [WalkOracle(parent, m, case, phase=phase, entry=PARENT,
                connected=dict(zip(range(source.ENTRY, source.ENTRY + source.SIZE, 4), w))).run()
                for w in (self.truth, self.words)]
            for model in models:
                self.assertEqual((public(model.memory), model.calls), (public(wanted), expected_calls))
            self.assertEqual(complete(models[0]), complete(models[1]))
            phases += 1
        connected = {}
        old = self.values['conker/build/conker.us.elf']
        for entry, size in ((SYMBOLS['func_1516972C'], 112), (SCAN, 80), (DEFAULT, 32)):
            rom = entry - 0x15000000 + 0x2D4B0
            truth = self.rom[rom:rom + size]
            at = source.elf_slot_offset(old, entry, size)
            self.assertEqual(old[at:at + size], truth)
            connected.update(zip(range(entry, entry + size, 4), struct.unpack('>%dI' % (size // 4), truth)))
        helper_phases, visits = 0, set()
        for depth, kind, callback, pattern, phase in itertools.product(
                (-1, 0, 2), (0, 1, 2, 7, 255), (0, 1), (0, 1), (0, 8)):
            case = Case(depth, 128, pattern)
            m = fixture(case)
            for node in NODES:
                m[node] = kind
            for i in range(depth + 1):
                put(m, SYMBOLS['D_800DD198'] + 4 * i, NODES[0] if i % 2 == 0 else NODES[6])
            put(m, 0x8008B4D0 + 52 * kind, PROVIDER if callback else 0)
            wanted, root_calls, _ = reference(m, case)
            calls = []
            for _, args in root_calls:
                node = args[0]
                calls.extend(((SYMBOLS['func_1516972C'], args), (SCAN, args)))
                for i in range(depth + 1):
                    address = SYMBOLS['D_800DD198'] + 4 * i
                    if read(wanted, address) == node:
                        put(wanted, address, read(m, node + 8))
                if kind >= 2:
                    calls.extend(((PROVIDER, args),) if callback else ((DEFAULT, args), (FREE, (node, 1))))
            models = [WalkOracle(w, m, case, phase=phase, connected=connected, chain=True).run()
                for w in (self.truth, self.words)]
            for model in models:
                self.assertEqual((public(model.memory), model.calls), (public(wanted), calls))
                visits.update(model.visits)
            self.assertEqual(complete(models[0]), complete(models[1]))
            helper_phases += 1
        self.assertTrue(set(connected) <= visits)
        for name in ('conker/src/game_981E0.c', 'conker/build/src/game_981E0.c.o',
                'conker/src/game_1944C0.c', 'conker/build/src/game_1944C0.c.o'):
            self.assertEqual((ROOT / name).read_bytes(), self.values[name])
        self.receipt.update(original_caller_words=154, original_caller_mode=selected_mode,
            original_caller_phases=phases, retained_caller_stub_uncredited=True,
            actual_release_chain_phases=helper_phases, actual_release_chain_words=len(connected),
            all_56_chain_words_visited=True, original_helper_and_caller_objects_unchanged=True,
            callback_heap_and_gameplay_providers_bounded=True)

    def rebased(self, obj, entry, symbols, label):
        text, functions, bindings = source.parse_object(obj)
        assembly, unknown = emit_function(text, functions[source.FUNCTION], bindings, source.FUNCTION, symbols)
        self.assertFalse(unknown)
        p = self.output / label
        p.with_suffix('.s').write_text(assembly)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(p.with_suffix('.o')),
            str(p.with_suffix('.s'))], check=True, capture_output=True)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(p.with_suffix('.ld')),
            '-e', source.FUNCTION, *['--defsym=%s=0x%X' % row for row in symbols.items()],
            '-o', str(p.with_suffix('.elf')), str(p.with_suffix('.o'))], check=True, capture_output=True)
        return list(struct.unpack_from('>45I', sections(p.with_suffix('.elf'))['.text'][1]))

    def test_05_independent_GNU_links_aliases_and_fired_fault_prefixes(self):
        objects = (source.original(ROOT, self.output), self.output / 'qualified-padded.o',
            self.output / 'make-shadow/src/game/generated_DC6B0.c.o')
        phases = 0
        for i, entry in enumerate((source.ENTRY, 0x18017FFC, 0x1A028000)):
            symbols = SYMBOLS if not i else dict(D_800DD190=0x81007FFC + i * 0x10000,
                D_800DCE94=0x82008000 + i * 0x10000, D_800DD198=0x8300FFFC + i * 0x10000,
                D_800C3E78=0x84008004 + i * 0x10000, func_1516972C=entry + 0x10000)
            images = [self.rebased(obj, entry, symbols, 'rebase-%d-%d' % (i, j)) for j, obj in enumerate(objects)]
            self.assertEqual(images[0], images[1])
            self.assertEqual(images[0], images[2])
            for depth, pattern, mode in itertools.product((-1, 0, 2), (0, 1, 2), (0, 2, 12)):
                case = Case(depth, 255, pattern, mode)
                m = fixture(case, symbols)
                wanted, calls, observations = reference(m, case, symbols)
                models = [WalkOracle(w, m, case, symbols=symbols, entry=entry).run() for w in images[:2]]
                self.assertEqual(complete(models[0]), complete(models[1]))
                self.assertEqual((public(models[0].memory), models[0].calls, models[0].observations),
                    (public(wanted), calls, observations))
                phases += 1
        aliases = 0
        for i, (name, address) in enumerate((('D_800DD198', STACK - 32), ('D_800DD198', NODES[0] + 0x3C),
                ('D_800C3E78', SYMBOLS['D_800DD198']), ('D_800DD190', STACK - 0x100))):
            symbols = dict(SYMBOLS)
            symbols[name] = address
            case = Case(-1, 0, 2)
            m = fixture(case, symbols)
            images = [self.rebased(obj, source.ENTRY, symbols, 'alias-%d-%d' % (i, j))
                for j, obj in enumerate(objects[:2])]
            self.assertEqual(images[0], images[1])
            models = [WalkOracle(w, m, case, symbols=symbols).run() for w in images]
            self.assertEqual(complete(models[0]), complete(models[1]))
            aliases += 1
        cuts = 0
        for case, phase in itertools.product((Case(empty=True), Case(pattern=2), Case(mode=15)), (0, 8)):
            m = fixture(case)
            accesses = WalkOracle(self.truth, m, case, phase=phase).run().root_accesses
            for cut in range(accesses):
                models = [WalkOracle(w, m, case, phase=phase, fault=cut) for w in (self.truth, self.words)]
                for model in models:
                    with self.assertRaises(faults.AccessBoundary):
                        model.run()
                self.assertEqual(complete(models[0]), complete(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of, models[0].dispatched_word),
                    (models[1].current_pc, models[1].delay_of, models[1].dispatched_word))
                cuts += 1
        self.receipt.update(GNU_links=17, rebased_phases=phases, guest_alias_layouts=aliases,
            fired_target_fault_prefixes=cuts, literal_complete_guest_state=True,
            portable_C_alias_fault_or_hardware_acceptance_claimed=False)

    def test_06_strict_image_symbol_permutation_and_frozen_input_controls(self):
        values = source.snapshot(self.output)
        before = values['conker/build/conker.us.elf']
        truth = values['conker/conker.us.bin'][source.ROM:source.ROM + source.SIZE]
        actual = (self.output / 'first-linked.elf').read_bytes()
        source.check_image(before, actual, truth)
        at = source.elf_slot_offset(before, source.ENTRY, source.SIZE)
        rows = list(source.symbol_rows(actual))
        touched = [row for row in rows if row[1] in ('D_80095BC0', 'D_8009EFC0')]
        offsets = (0, at, at + source.SIZE - 1, at + source.SIZE, len(actual) - 1,
            touched[0][0] + 4, touched[0][3], touched[1][3])
        for offset in offsets:
            wrong = bytearray(actual)
            wrong[offset] ^= 1
            with self.assertRaises(ValueError):
                source.check_image(before, bytes(wrong), truth)
        with self.assertRaises(ValueError):
            source.check_image(before, actual + b'\0', truth)
        with self.assertRaises(ValueError):
            source.checked_payload(*source.payload(self.output / 'before-padded.o'))
        for name in (source.SOURCE, source.OBJECT, 'conker/include/structs.h',
                'conker/retail_word_patches.us.csv', 'conker/asm/DC6B0.s',
                'conker/src/game_1944C0.c'):
            target = self.output / ('before-' + name.replace('/', '_'))
            original = Path.read_bytes
            def changed(path):
                data = original(path)
                return bytes([data[0] ^ 1]) + data[1:] if path == target else data
            with patch.object(Path, 'read_bytes', changed), self.assertRaises(ValueError):
                source.snapshot(self.output)
        with patch.object(source, 'SERIALIZATION', ((('D_80095BC0', 'D_8009EFC0'), (1, 0),
                ((0x80095BC0, 1, 16, 0, 65521), (0x8009EFC0, 0, 16, 0, 6))),)):
            with self.assertRaises(AssertionError):
                source.predicted_image(before, truth)
        self.receipt.update(strict_image_controls=9, frozen_input_controls=6, old_stub_rejected=True,
            closed_symbol_string_permutations=1, exact_named_definition_preconditions=True,
            wrong_symbol_definition_rejected=True, metadata_exclusions=0)
