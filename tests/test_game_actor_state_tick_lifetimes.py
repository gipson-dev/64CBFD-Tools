"""Full-source lifetime screen; byte/private/fault installation gates stay open."""

import itertools
import json
import struct
import subprocess
import unittest
from collections import Counter
from pathlib import Path

from tools.experiments import game_actor_state_tick_lifetimes as source
from tools.tests import test_game_actor_state_tick_candidates as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


ROOT = Path(__file__).resolve().parents[2]
# The kernel enters _start without a C caller's pushed return address.
NATIVE_START = START.replace('void _start(void)',
    '__attribute__((force_align_arg_pointer)) void _start(void)')


def native_cases():
    rows = []
    for category, action, seed, count in itertools.product((0xB7, 0xB8, 0xB9), (0, 5), range(4), (4, 16)):
        rows.append((guest.fixture(count=count, category=category, action=action, seed=seed,
                                   delta=seed % 3), dict(status=seed % 2, steering=seed // 2)))
    for category, count in itertools.product((0xB7, 0xB8, 0xB9), (-1, 0, 1)):
        rows.append((guest.fixture(count=count, category=category, delta=0), {}))
    return rows


def native_harness():
    """Serialize typed guest cells; no N64 byte order is assumed for native C."""
    fixtures = native_cases()
    memory = fixtures[0][0]
    addresses = sorted(a for a in memory if not guest.private(a))
    regions, offset = [], 0
    for address in addresses:
        if not regions or address != regions[-1][0] + regions[-1][1]:
            offset = (offset + 15) & ~15
            regions.append([address, 0, offset])
        regions[-1][1] += 1
        offset += 1
    extent = (offset + 15) & ~15

    def physical(address):
        matches = [o + address - a for a, n, o in regions if a <= address < a + n]
        if len(matches) != 1:
            raise ValueError('Unmapped native fixture address: %X' % address)
        return matches[0]

    widths = {}
    for base in (guest.STATE, guest.ALT_STATE):
        for at in range(0, 0x1900, 4):
            if 0x1700 <= at < 0x1748:
                continue
            if at == 0x16BC:
                widths[base + at], widths[base + at + 2] = 2, 2
            else:
                widths[base + at] = 4
    pointers = {guest.GLOBAL, guest.VIEWPORTS}
    for slot in range(16):
        for at in (0x14, 0x18, 0x1C, 0x31C):
            widths[guest.ACTORS + slot * 0x32C + at] = 4
        widths[guest.ACTORS + slot * 0x32C + 0x22C] = 2
        pointers.add(guest.ACTORS + slot * 0x32C + 0x31C)
    for at in range(16 * 0x180 // 4):
        widths[guest.VIEWS + at * 4] = 4
    for address in (guest.GLOBAL, guest.DELTA, guest.VIEWPORTS, guest.LAST_PLAYER):
        widths[address] = 4
    for i in range(4):
        widths[guest.LIMIT + i * 2] = 2
        widths[guest.SCALE + i * 4] = 4
    schema, i = [], 0
    while i < len(addresses):
        address = addresses[i]
        size = widths.get(address, 1)
        if addresses[i:i + size] != list(range(address, address + size)):
            raise ValueError('Native cell crosses a fixture hole')
        schema.append((address, physical(address), size, int(address in pointers)))
        i += size

    cells, calls, cases = [], [], []

    def serialize(values):
        start = len(cells)
        for address, at, size, pointer in schema:
            value = guest.read(values, address, size)
            if value != int.from_bytes(b'\xA5' * size, 'big'):
                cells.append('{%d,0x%Xu,%d,%d}' % (at, value, size, pointer))
        return start, len(cells) - start

    for memory, options in fixtures:
        expected, trace, _, result = guest.reference(memory, **options)
        initial_at, initial_n = serialize(memory)
        expected_at, expected_n = serialize(expected)
        call_at = len(calls)
        for call in trace:
            target, args = call[0], call[1:]
            calls.append('{0x%Xu,%d,{%s}}' % (target, len(args),
                ','.join('0x%Xu' % (a & 0xFFFFFFFF) for a in (*args, *((0,) * (6 - len(args)))))))
        cases.append('{%s}' % ','.join(str(x) for x in (initial_at, initial_n, expected_at, expected_n,
            call_at, len(trace), result, options.get('status', 1), options.get('steering', 0))))

    types = {'D_800D23B0': ('s32', guest.GLOBAL), 'D_800CC2D0': ('u8 *', guest.ACTORS),
        'D_800E0BB8': ('u8 *', guest.EVENT_BYTES), 'D_800BE9E4': ('s32', guest.DELTA),
        'D_800E0BD0': ('s8', guest.DIFFICULTY), 'D_800872C4': ('s16 *', guest.LIMIT),
        'D_800872D0': ('s8 *', guest.PERIOD), 'D_800872E0': ('s8 *', guest.IDLE_PERIOD),
        'D_800872E8': ('s8 *', guest.CHANCE), 'D_800872F8': ('f32 *', guest.SCALE),
        'D_800BE628': ('u8 **', guest.VIEWPORTS), 'D_80082FA0': ('s32', guest.LAST_PLAYER)}
    definitions = []
    for name, (kind, address) in types.items():
        base = '(actual+%d)' % physical(address)
        if name == 'D_800BE628':
            expression = '(*(u8 **)' + base + ')'
        elif '*' in kind:
            expression = '((' + kind + ')' + base + ')'
        else:
            expression = '(*(' + kind + ' *)' + base + ')'
        definitions.append('#define ' + name + ' ' + expression)
    definitions.append('#define D_8009DA20 format')
    body = r'''
#include <ultra64.h>
struct Region{u32 address,size,offset;};
struct Cell{u32 offset,value;u8 size,pointer;};
struct Call{u32 target,n,args[6];};
struct Case{u32 initial,ninitial,expected,nexpected,call,ncall,result,status,steering;};
static const struct Region regions[]={REGIONS};
static const struct Cell cells[]={CELLS};
static const struct Call calls[]={CALLS};
static const struct Case cases[]={CASES};
static u8 actual[EXTENT] __attribute__((aligned(16)));
static u8 expected[EXTENT] __attribute__((aligned(16)));
static u8 format[4];static u32 error,callIndex,randomIndex;static const struct Case*c;
DEFINITIONS
static u32 pointer(u32 address){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(address>=regions[i].address&&address-regions[i].address<regions[i].size)
 return (u32)(actual+regions[i].offset+address-regions[i].address);error=31;return 0;}
static void apply(u8*out,u32 start,u32 count){u32 i,v;const struct Cell*p;
 for(i=0;i<count;i++){p=&cells[start+i];v=p->pointer?pointer(p->value):p->value;
 if(p->size==1)out[p->offset]=(u8)v;else if(p->size==2)*(u16*)(out+p->offset)=(u16)v;
 else *(u32*)(out+p->offset)=v;}}
static void record(u32 target,u32 n,const u32*args){u32 i,v;const struct Call*p;
 if(callIndex>=c->ncall){error=32;return;}p=&calls[c->call+callIndex++];
 if(p->target!=target||p->n!=n){error=33;return;}for(i=0;i<n;i++){
 v=p->args[i];if(target==0x15042D94u&&i==3)v=(u32)format;if(args[i]!=v)error=34;}}
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
s32 func_150859AC(s16 a,s32 b){u32 args[]={(u32)(s32)a,(u32)b};record(0x150859AC,2,args);return c->status;}
s32 func_15085DA8(f32 a){u32 args[]={word(a)};record(0x15085DA8,1,args);return 3;}
void func_1508EC5C(s32 a,s32 b){u32 args[]={(u32)a,(u32)b};record(0x1508EC5C,2,args);}
s32 func_1508DAEC(s32 a,s32 b){u32 args[]={(u32)a,(u32)b};record(0x1508DAEC,2,args);return 0x12345678;}
void func_1508EBF8(s32 a,s32 b){u32 args[]={(u32)a,(u32)b};record(0x1508EBF8,2,args);}
s32 func_1508CAD8(s32 a,s32 b,s32 d,s32 e,s32 f,s32 g){u32 args[]={(u32)a,(u32)b,(u32)d,(u32)e,(u32)f,(u32)g};
 record(0x1508CAD8,6,args);return c->steering;}
f32 func_150ADA68(void){static const u32 values[]={0,0x3E800000,0x3F000000,0x3F400000,0x3F800000};
 record(0x150ADA68,0,0);return real(values[randomIndex++%5]);}
void func_1508B3F8(void){record(0x1508B3F8,0,0);}
void func_1504332C(s32 a,s32 b,s32 d,s32 e){u32 args[]={(u32)a,(u32)b,(u32)d,(u32)e};record(0x1504332C,4,args);}
s32 func_15042D94(s32 a,s32 b,s32 d,void*f,...){__builtin_va_list ap;u32 args[5];
 __builtin_va_start(ap,f);args[0]=a;args[1]=b;args[2]=d;args[3]=(u32)f;args[4]=__builtin_va_arg(ap,s32);
 __builtin_va_end(ap);record(0x15042D94,5,args);return 0x12345678;}
SOURCE
int run(void){u32 i,j,result;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){c=&cases[i];
 error=callIndex=randomIndex=0;for(j=0;j<sizeof(actual);j++)actual[j]=expected[j]=0xA5;
 apply(actual,c->initial,c->ninitial);apply(expected,c->expected,c->nexpected);
 result=(u32)func_1508A6FC();if(error)return error;if(result!=c->result)return 35;
 if(callIndex!=c->ncall)return 36;for(j=0;j<sizeof(actual);j++)if(actual[j]!=expected[j])return 37;}return 0;}
'''
    replacements = {'REGIONS': ','.join('{%d,%d,%d}' % tuple(r) for r in regions),
                    'CELLS': ',\n'.join(cells), 'CALLS': ',\n'.join(calls), 'CASES': ',\n'.join(cases),
                    'EXTENT': str(extent), 'DEFINITIONS': '\n'.join(definitions), 'SOURCE': source.SELECTED}
    for marker, value in replacements.items():
        body = body.replace(marker, value)
    return body + '\n' + NATIVE_START, len(fixtures)


class ActorStateTickLifetimeTests(unittest.TestCase):
    compare = guest.ActorStateTickCandidateTests.compare
    test_empty_inactive_first_seen_and_all_sixteen_slots = guest.ActorStateTickCandidateTests.test_empty_inactive_first_seen_and_all_sixteen_slots
    test_categories_timer_signs_states_actions_and_probability = guest.ActorStateTickCandidateTests.test_categories_timer_signs_states_actions_and_probability
    test_opaque_helpers_can_replace_global_and_mutate_captured_inputs = guest.ActorStateTickCandidateTests.test_opaque_helpers_can_replace_global_and_mutate_captured_inputs

    @classmethod
    def setUpClass(cls):
        cls.root, cls.output = ROOT, ROOT / source.BUILD / 'test'
        source.prior.freeze(cls.root, cls.output)
        cls.record, cls.words = source.compile_candidate(cls.root, cls.output, 'selected', source.SELECTED)
        cls.retail = struct.unpack_from('>678I', (cls.root / 'conker/conker.us.bin').read_bytes(), guest.screen.ROM)
        cls.coverage, cls.completed, cls.public_reads, cls.native_count = set(), 0, 0, 0

    @classmethod
    def tearDownClass(cls):
        receipt = dict(completed_fixtures=cls.completed, retail_words_visited=len(cls.coverage),
            words=cls.record['body_words'], frame=cls.record['frame'],
            public_read_footprint_pairs=cls.public_reads, native_fixtures=cls.native_count,
            installed=False, matching_credit=0, private_and_fault_equivalence=False)
        (cls.output / 'qualification.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('actor-state lifetime qualification:', receipt)

    def test_complete_shape_captures_and_no_false_matching_credit(self):
        self.assertEqual((self.record['body_words'], self.record['frame']), (678, 288))
        self.assertEqual(self.record['diagnostics'], '')
        self.assertEqual(self.record['raw_sha256'], source.RAW_SHA256)
        self.assertEqual(len(self.record['opening']['eager_table_homes']), 11)
        self.assertEqual(len({h['table_offset'] for h in self.record['opening']['eager_table_homes']}), 11)
        self.assertEqual(self.record['aligned_differences'], 607)
        self.assertFalse(self.record['installed'])
        self.assertNotEqual(self.words, self.retail)

    def test_timer_reload_has_effective_literal_public_read_control(self):
        body = dict(source.forms())['eager-reused-cursors']
        _, old_words = source.compile_candidate(self.root, self.output, 'omitted-reload-control', body)
        for category, seed, phase in itertools.product((0xB7, 0xB8, 0xB9), range(4), (0, 8)):
            memory = guest.fixture(count=16, category=category, seed=seed, action=5)
            models = [guest.TickOracle(w, memory, phase).run() for w in (self.retail, self.words)]
            reads = [Counter(r for r in m.reads if not guest.private(r[0])) for m in models]
            self.assertEqual(reads[0], reads[1])
            type(self).public_reads += 1
        memory = guest.fixture(count=16, category=0xB9, seed=1, action=5)
        retail = guest.TickOracle(self.retail, memory).run()
        old = guest.TickOracle(old_words, memory).run()
        wanted = Counter(r for r in retail.reads if not guest.private(r[0]))
        omitted = wanted - Counter(r for r in old.reads if not guest.private(r[0]))
        self.assertEqual(sum(omitted.values()), 7)
        self.assertTrue(all(size == 4 and value == 0 and guest.STATE + 0x29C <= address < guest.STATE + 0x2DC
                            for address, size, value in omitted))

    def test_both_owner_profiles_and_production_preservation(self):
        rows = source.qualify_owner(self.root, self.output / 'owner')
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['preserved_neighbors'] == 72 and r['words'] == 678 and r['frame'] == 288 for r in rows))

    def test_remaining_register_and_read_order_boundary_is_not_hidden(self):
        class Capture(guest.TickOracle):
            def record_call(self, target):
                super().record_call(target)
                if target == guest.STATUS and self.r[4] == 1:
                    self.capture = self.r[16:24] + [self.r[30]]

        memory = guest.fixture(count=16, category=0xB9, action=5, seed=1)
        retail, candidate = (Capture(w, memory).run() for w in (self.retail, self.words))
        a, b = retail.capture, candidate.capture
        self.assertEqual(a, [4, guest.GLOBAL, 1, guest.ACTORS + 0x32C, 0, 1,
                             guest.STATE + 0x360, guest.STATE + 0x220, 2])
        self.assertEqual(b, [1, guest.GLOBAL, guest.ACTORS + 0x32C, 4, 0, 1,
                             guest.STATE + 0x220, guest.STATE + 0x360, 2])
        left = [r for r in retail.reads if not guest.private(r[0])]
        right = [r for r in candidate.reads if not guest.private(r[0])]
        self.assertEqual(Counter(left), Counter(right))
        self.assertNotEqual(left, right)
        differences = [(i, x, y) for i, (x, y) in enumerate(zip(left, right)) if x != y]
        self.assertEqual(len(differences), 14)
        (self.output / 'remaining-layout-boundary.json').write_text(json.dumps(dict(
            retail_status_slot1_gprs=a, candidate_status_slot1_gprs=b,
            ordered_public_reads_equal=False, first_read_differences=differences[:2]), indent=2) + '\n')

    def test_complete_native32_source_at_three_optimizations_with_ubsan(self):
        body, count = native_harness()
        path = self.output / 'native.c'
        path.write_text(body)
        for opt in ('-O0', '-O2', '-O3'):
            exe = self.output / ('native' + opt)
            build = subprocess.run([*native_command(opt), '-fno-strict-aliasing', str(path), '-o', str(exe)],
                                   cwd=self.root, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, timeout=10)
            self.assertEqual(run.returncode, 0, (opt, run.stdout, run.stderr))
        type(self).native_count = count
        controls = (
            ('wide-flag', source.SELECTED.replace('actor[0x2FD] != 0', '*(u32 *)(actor + 0x2FC) != 0')),
            ('four-word-stride', source.SELECTED.replace('            band++;', '            band += 4;')),
            ('inclusive-random', source.SELECTED.replace('func_150ADA68() > 0.5f', 'func_150ADA68() >= 0.5f')),
        )
        self.assertEqual(body.count(source.SELECTED), 1)
        for name, bad in controls:
            self.assertNotEqual(bad, source.SELECTED)
            path = self.output / ('native-negative-' + name + '.c')
            path.write_text(body.replace(source.SELECTED, bad))
            exe = path.with_suffix('')
            build = subprocess.run([*native_command('-O2'), '-fno-strict-aliasing', str(path), '-o', str(exe)],
                                   cwd=self.root, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertIn(subprocess.run([str(exe)], capture_output=True, timeout=10).returncode,
                          (32, 33, 34, 35, 36, 37), name)
        overflow = self.output / 'overflow.c'
        overflow.write_text('int run(void){volatile int value=0x7FFFFFFF;return value+1;}\n' + NATIVE_START)
        exe = self.output / 'overflow'
        build = subprocess.run([*native_command('-O2'), str(overflow), '-o', str(exe)],
                               cwd=self.root, capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(subprocess.run([str(exe)], capture_output=True, timeout=5).returncode, -4)


if __name__ == '__main__':
    unittest.main()
