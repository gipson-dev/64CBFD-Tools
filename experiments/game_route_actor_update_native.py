"""Execute the full route-update C and five real C helpers in bounded native32."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import struct
import subprocess

from tools.experiments import game_route_actor_update_extent as source
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests import test_game_route_actor_update as guest
from tools.tests.test_game_projected_packet_draw import native_command

BUILD = 'conker/build/game-route-actor-update-native'
CASES = 553
HELPER_SHA = {
    'func_150888A8': '34028478c854adccbc1666f16f11b90d42dd7899a1efaca152be1890572d911f',
    'func_15088A08': 'f77a29c36de2adbd52edecc35c393e42ad67a2872c874968c81aecfd13bcc0ab',
    'func_15088F30': 'e953823fda06675fcefe173a3d8aaef88a318eba6141cac2de9888e63ff9b99a',
    'func_150497E0': '27759ba0cb99958e7bc308312c14ee0f6ccf93ed9830ca7a20f64deb9ae7d619',
    'func_150498A4': '18f07d3b76d36ea088b044d1bdc66ec12d97205acc2795ccca2d0b5e2707e1a3',
}
# The mappings preserve public aliases, including actor+0x40 / D_800CC310.
REGIONS = ((guest.RECORDS, 32 * 132, 0x1000), (guest.ACTORS - 0x32C, 6 * 0x32C, 0x3000),
           (guest.OBJECTS, 0x200, 0x5000), (guest.ROUTES, 4096, 0x6000),
           (0x800D2000, 0x500, 0x8000), (0x8009D9D0, 0x40, 0x9000),
           (0x800E0B00, 0x200, 0x9100), (guest.TABLE, 4, 0x9400),
           (guest.TICKS, 4, 0x9410), (guest.MASK, 2, 0x9420),
           (0x8008FD90, 1, 0x9430), (0x800BE616, 1, 0x9440))
HELPERS = (('generated_B3020', 'func_150888A8', 'actual_neighbor'),
           ('generated_B3020', 'func_15088A08', 'actual_advance'),
           ('generated_B3020', 'func_15088F30', 'actual_vector'),
           ('generated_76C90', 'func_150497E0', 'actual_cubic'),
           ('generated_76C90', 'func_150498A4', 'actual_derivative'))

HEADER = r'''#include <ultra64.h>
typedef union {u64 align;u8 bytes[0x10000];} Arena;
static Arena arena,wanted;
typedef struct {u32 address,length,offset;} Region;
static const Region regions[]={REGIONS};
static u32 failure,callCount,wantedCount,effect,fired,everFired;
static u8 *activeRecord;static f32 *axes[3];static u32 calls[2048];
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 value(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u8 *address(u32 at,int expected){u32 i;
 if(!at)return 0;
 for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
  if(at>=regions[i].address&&at-regions[i].address<regions[i].length)
   return (expected?wanted.bytes:arena.bytes)+regions[i].offset+at-regions[i].address;
 failure=90;return arena.bytes;
}
static u32 guestAddress(u8 *p){u32 i;
 for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
  if((u32)p>=(u32)arena.bytes+regions[i].offset&&(u32)p<(u32)arena.bytes+regions[i].offset+regions[i].length)
   return regions[i].address+(u32)p-(u32)arena.bytes-regions[i].offset;
 failure=91;return 0;
}
static void logCall(u32 id,u32 a,u32 b,u32 c,u32 d){u32 *p;
 if(callCount>=400){failure=92;return;}p=calls+callCount*5;
 p[0]=id;p[1]=a;p[2]=b;p[3]=c;p[4]=d;callCount++;
}
#define D_800872A0 (*(u8 **)address(0x800872A0U,0))
#define D_800CC2D0 (address(0x800CC2D0U,0))
#define D_800D2350 (*(u8 **)address(0x800D2350U,0))
#define D_800D2104 (*(u8 ***)address(0x800D2104U,0))
#define D_800D2398 (*(s8 *)address(0x800D2398U,0))
#define D_800D2390 (*(s8 *)address(0x800D2390U,0))
#define D_800D23A9 (*(s8 *)address(0x800D23A9U,0))
#define D_800D23A8 (*(s8 *)address(0x800D23A8U,0))
#define D_800BE9E4 (*(s32 *)address(0x800BE9E4U,0))
#define D_800D18A0 (*(u16 *)address(0x800D18A0U,0))
#define D_8008FD90 (*(s8 *)address(0x8008FD90U,0))
#define D_800E0BE7 (*(s8 *)address(0x800E0BE7U,0))
#define D_800BE616 (*(u8 *)address(0x800BE616U,0))
#define D_800E0C10 ((s16 *)address(0x800E0C10U,0))
#define D_800E0C18 ((s32 *)address(0x800E0C18U,0))
#define D_8009D9E0 (*(f32 *)address(0x8009D9E0U,0))
#define D_8009D9E4 (*(f32 *)address(0x8009D9E4U,0))
#define D_8009D9E8 (*(f32 *)address(0x8009D9E8U,0))
#define D_8009D9F0 (*(f64 *)address(0x8009D9F0U,0))
#define D_8009D9F8 (*(f32 *)address(0x8009D9F8U,0))
#define D_8009D9FC (*(f32 *)address(0x8009D9FCU,0))
#define D_800D239C (*(f32 *)address(0x800D239CU,0))
#define D_800D23A0 (*(f32 *)address(0x800D23A0U,0))
#define D_800D23A4 (*(f32 *)address(0x800D23A4U,0))
#define D_800CC310 (*(f32 *)address(0x800CC310U,0))
s32 func_150888A8(u8,u8,s8);
f32 sqrtf(f32 x){f32 r;__asm__ volatile("sqrtss %1,%0":"=x"(r):"x"(x));return r;}
'''

WRAPPERS = r'''
s32 func_150888A8(u8 excluded,u8 id,s8 mode){
 logCall(0x150888A8U,excluded,id,(u32)(s32)mode,0);return actual_neighbor(excluded,id,mode);
}
s32 func_15088A08(u8 *p,f32 delta){
 logCall(0x15088A08U,p==activeRecord?0:1,bits(delta),0,0);return actual_advance(p,delta);
}
void func_15088F30(u8 *p,f32 *x,f32 *y,f32 *z){
 logCall(0x15088F30U,p==activeRecord?0:1,*(u32 *)p,*(u32 *)(p+8),0);
 axes[0]=x;axes[1]=y;axes[2]=z;actual_vector(p,x,y,z);
}
static u32 axis(f32 *p){u32 i;for(i=0;i<3;i++)if(p==axes[i])return i;failure=93;return 0;}
f32 func_150497E0(f32 *p,s32 i,f32 t){logCall(0x150497E0U,axis(p),(u32)i,bits(t),0);return actual_cubic(p,i,t);}
f32 func_150498A4(f32 *p,s32 i,f32 t,f32 *d){logCall(0x150498A4U,axis(p),(u32)i,bits(t),0);return actual_derivative(p,i,t,d);}
void func_15042D78(s32 command){
 logCall(0x15042D78U,(u32)command,0,0,0);if(effect)fired|=1U<<effect;
 if(effect>=1&&effect<=3)D_800D2390=(s8)effect;
 if(effect==4){activeRecord[0x30]=2;address(0x601C4U,0)[0]=0;}
 if(effect==5){D_800BE9E4=7;activeRecord[0x33]=251;}
}
void bcopy(const void *a,void *b,int size){int i;const u8 *p=a;u8 *q=b;
 logCall(0x10023A10U,(u32)size,0,0,0);for(i=0;i<size;i++)q[i]=p[i];}
void func_1508802C(u8 *r,u8 *a,s32 command){logCall(0x1508802CU,guestAddress(r),guestAddress(a),(u32)command,0);}
f32 sinf(f32 angle){logCall(0x15047D60U,bits(angle),0,0,0);return trig(bits(angle),0);}
f32 cosf(f32 angle){logCall(0x15047C00U,bits(angle),0,0,0);return trig(bits(angle),1);}
'''

RUNNER = r'''
typedef struct {u32 at,width,pointer;u64 value;} Patch;
typedef struct {u32 first,count,wanted,wantedCount,callFirst,callCount,index,active,look,effect;} Case;
static const Patch patches[]={PATCHES};
static const u32 expectedCalls[]={CALLS};
static const Case cases[]={CASES};
static void apply(u32 first,u32 count,int expected){u32 i;u8 *p;u64 v;
 for(i=first;i<first+count;i++){
  p=address(patches[i].at,expected);v=patches[i].value;
  if(patches[i].pointer)v=(u32)address((u32)v,0);
  if(patches[i].width==1)*p=(u8)v;
  else if(patches[i].width==2)*(u16 *)p=(u16)v;
  else if(patches[i].width==4)*(u32 *)p=(u32)v;
  else if(patches[i].width==8)*(u64 *)p=v;
  else failure=94;
 }
}
void _start(void){u32 i,j;const Case *c;int result=0;
 if(sizeof(void *)!=4||sizeof(f32)!=4)result=70;
 for(i=0;!result&&i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases+i;for(j=0;j<sizeof(arena.bytes);j++){arena.bytes[j]=165;wanted.bytes[j]=165;}
  failure=0;callCount=0;wantedCount=c->callCount;effect=c->effect;fired=0;
  apply(c->first,c->count,0);apply(c->wanted,c->wantedCount,1);
  activeRecord=D_800872A0?(u8 *)((u32)D_800872A0+c->index*132U):0;
  func_15087350((s32)c->index,(s32)c->active,value(c->look));
  if(failure)result=(int)failure;
  else if(callCount!=wantedCount)result=22;
  else {for(j=0;j<wantedCount*5;j++)if(calls[j]!=expectedCalls[c->callFirst+j]){result=23;break;}}
  if(!result)for(j=0;j<sizeof(arena.bytes);j++)if(arena.bytes[j]!=wanted.bytes[j]){result=21;break;}
  if(!result&&effect&&!(fired&(1U<<effect)))result=24;everFired|=fired;
 }
 if(!result&&REQUIRE_EFFECTS&&(everFired&62)!=62)result=24;
 __asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();
}
'''


def cases():
    rows = []
    for index, mode, active, position in itertools.product((0, 1, 3), (0, 1, 2, 128),
            (0, 1, 256), ((20., 10.), (-300., 100.), (1600., -250.))):
        rows.append(dict(index=index, mode=mode, active=active, position=position))
    rows += [dict(effect=e, mode=m, active=a) for e, m, a in itertools.product(range(1, 6), (0, 1, 2, 255), (0, 1))]
    rows += [dict(mode=1, lap=lap) for lap in range(256)]
    rows += [dict(mode=1, count=n, mask=m, pattern=p) for n, m, p in
             itertools.product((-128, -1, 0, 1, 2, 16, 17), (0, 1, 7), range(3))]
    rows += [dict(active=a, tick=t, mode=m) for a, t, m in itertools.product(
        (0, 1, 128, 255, 256, 0x10001, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF), (1, 127, 128, 255), (0, 1))]
    rows += [dict(mode=1, active=0, position=(v, -v), wide=v) for v in (32768., -32769., 65535., -65535., 16777216., -16777216.)]
    rows += [dict(null=True, index=i, active=0xFFFFFFFF) for i in (0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)]
    rows += [dict(mode=1, modular=i) for i in (0x40000000, 0x80000000, 0xC0000000)]
    return rows


def fixture(row, constants=None):
    memory, args = guest.fixture(real=True, **{k: row[k] for k in ('index', 'mode', 'active', 'count', 'position') if k in row})
    if constants is not None:
        memory.update(constants)
    if 'lap' in row:
        guest.put(memory, guest.RECORDS + 132 + 0x2A, row['lap'], 1)
    if 'mask' in row:
        guest.put(memory, guest.MASK, row['mask'], 2)
        for i in range(17):
            guest.put(memory, guest.RECORDS + i * 132 + 8, guest.bits(.2 if row['pattern'] == 0 else ((i * 7) % 17) * .03125))
            guest.put(memory, guest.RECORDS + i * 132 + 0x24, (-32768, 0, 32767)[(i if row['pattern'] == 2 else 1) % 3], 2)
    if 'tick' in row:
        guest.put(memory, guest.RECORDS + 0x33, row['tick'], 1)
        guest.put(memory, guest.RECORDS + 0x1C, 0x7FFFFFFE)
    if 'wide' in row:
        guest.put(memory, guest.ACTORS + 0x18, guest.bits(row['wide']))
    if row.get('null'):
        guest.put(memory, guest.TABLE, 0)
    if 'modular' in row:
        args = (row['modular'], *args[1:])
    return memory, args


def schema(index):
    values = []
    for i in range(32):
        values.extend((guest.RECORDS + i * 132 + off, 4, False) for off in range(0, 0x24, 4))
        values.append((guest.RECORDS + i * 132 + 0x24, 2, False))
    actor = guest.ACTORS + index % 3 * 0x32C
    values.extend((actor + off, 4, False) for off in (0x14, 0x18, 0x1C, 0x20, 0x2C, 0x34, 0x44))
    values.extend(((actor + 0x31C, 4, True), (0x800CC310, 4, False),
        (guest.OBJECTS, 4, True), (guest.OBJECTS + 0x108, 2, False),
        (guest.OBJECTS + 0x10A, 2, False), (guest.OBJECTS + 0x10C, 2, False),
        (guest.TABLE, 4, True), (0x800D2104, 4, True), (0x800D2350, 4, True),
        (guest.MASK, 2, False), (guest.TICKS, 4, False), (0x8009D9F0, 8, False)))
    values.extend((at, 4, False) for at in (0x8009D9E0, 0x8009D9E4, 0x8009D9E8,
        0x8009D9F8, 0x8009D9FC, 0x800D239C, 0x800D23A0, 0x800D23A4))
    values.extend((guest.ROUTES + i * 16 + j * 2, 2, False) for i in range(256) for j in range(3))
    values.extend((guest.lap.ANCHORS['D_800E0C10'] + i * 2, 2, False) for i in range(4))
    values.extend((guest.lap.ANCHORS['D_800E0C18'] + i * 4, 4, False) for i in range(4))
    return values


def patches(memory, index):
    memory = guest.public(memory)
    covered, result = set(), []
    for at, width, pointer in schema(index):
        if not all(at + i in memory for i in range(width)):
            continue
        if any(at + i in covered for i in range(width)):
            raise ValueError('Overlapping native field schema')
        covered.update(range(at, at + width))
        value = guest.read(memory, at, width)
        if value != int.from_bytes(bytes([165]) * width, 'big'):
            result.append((at, width, int(pointer), value))
    result.extend((at, 1, 0, v) for at, v in sorted(memory.items()) if at not in covered and v != 165)
    for at, width, pointer, value in result:
        if not any(start <= at and at + width <= start + length for start, length, _ in REGIONS):
            raise ValueError('Unmapped native public address: ' + hex(at))
        if pointer and value and not any(start <= value < start + length for start, length, _ in REGIONS):
            raise ValueError('Unmapped native pointer: ' + hex(value))
    return result


def call_words(calls):
    result = []
    for call in calls:
        target, *args = call
        if target in (guest.VECTOR, guest.ADVANCE):
            args[0] = int(args[0] != 'record')
        elif target in (guest.NEIGHBOR, guest.SELECT, guest.FINALIZE):
            args = list(args[0])
        result.extend([target] + [int(v) & 0xFFFFFFFF for v in args] + [0] * (4 - len(args)))
    return result


def strip_externs(body):
    return re.sub(r'(?m)^    extern [^\n(]+;\n', '', body)


def static_constants(root):
    image = (root / 'conker/build/conker.us.elf').read_bytes()
    result = {}
    for at, n in ((0x8009D9E0, 4), (0x8009D9E4, 4), (0x8009D9E8, 4),
                  (0x8009D9F0, 8), (0x8009D9F8, 4), (0x8009D9FC, 4)):
        offset = source.source.prior.elf_slot_offset(image, at, n)
        result.update({at + i: image[offset + i] for i in range(n)})
    return result


def translation_unit(root, body=None, rows=None):
    rows = cases() if rows is None else rows
    body = source.selected() if body is None else body
    helpers, fingerprints = [], {}
    for owner, name, alias in HELPERS:
        text = (root / ('conker/src/game/' + owner + '.c')).read_text()
        a, b = function_span(text, name)
        span = text[a:b]
        fingerprints[name] = hashlib.sha256(span.encode()).hexdigest()
        helpers.append('#define %s %s\n%s\n#undef %s\n' % (name, alias, strip_externs(span), name))
    if fingerprints != HELPER_SHA:
        raise ValueError('Changed native real-helper source')
    constants = static_constants(root)
    all_patches, all_calls, encoded, trig = [], [], [], {}
    for row in rows:
        initial, args = fixture(row, constants)
        expected, calls = guest.reference(initial, args, row.get('effect', 0))
        first = len(all_patches)
        before = patches(initial, row.get('index', 0))
        after = patches(expected, row.get('index', 0))
        all_patches.extend(before + after)
        call_first = len(all_calls)
        all_calls.extend(call_words(calls))
        encoded.append((first, len(before), first + len(before), len(after), call_first,
            len(calls), *args, row.get('effect', 0)))
        for call in calls:
            if call[0] in (guest.SIN, guest.COS):
                x = guest.floating(call[1])
                trig[call[1]] = guest.bits(math.sin(x)), guest.bits(math.cos(x))
    provider = 'static f32 trig(u32 angle,int cosine){switch(angle){\n' + ''.join(
        'case 0x%XU:return value(cosine?0x%XU:0x%XU);\n' % (k, b, a) for k, (a, b) in sorted(trig.items())) +\
        'default:failure=95;return 0.0f;}}\n'
    header = HEADER.replace('REGIONS', ','.join('{0x%XU,0x%XU,0x%XU}' % r for r in REGIONS))
    runner = RUNNER.replace('PATCHES', ',\n'.join('{0x%XU,%d,%d,0x%XULL}' % p for p in all_patches))
    runner = runner.replace('CALLS', ','.join('0x%XU' % v for v in all_calls))
    runner = runner.replace('CASES', ',\n'.join('{' + ','.join('0x%XU' % (v & 0xFFFFFFFF) for v in row) + '}' for row in encoded))
    runner = runner.replace('REQUIRE_EFFECTS', str(int({r.get('effect', 0) for r in rows} >= set(range(1, 6)))))
    return header + provider + '\n'.join(helpers) + WRAPPERS + strip_externs(body) + runner, fingerprints


def controls():
    body = source.selected()
    return dict(half_lookahead=body.replace('lookAhead + lookAhead', 'lookAhead'),
        unsigned_tick=body.replace('(f32)(s8)record[0x32]', '(f32)record[0x32]'),
        byte_active=body.replace('if (active == 0)', 'if ((u8)active == 0)'),
        unsigned_lap=body.replace('(f32)(s8)cursor[0x2A]', '(f32)cursor[0x2A]'),
        ascending=body.replace('valueX < *(f32 *)(cursor + 4)', 'valueX > *(f32 *)(cursor + 4)'))


def qualify(root, out, smoke=False):
    source.source.freeze(root, out)
    source.checked(root / source.BUILD / 'qualified-cursor.o')
    rows = cases()
    if len(rows) != CASES:
        raise ValueError('Changed native route-update corpus size')
    if smoke:
        rows = [rows[0], dict(mode=1, active=0), dict(mode=1, lap=255), dict(null=True)]
    unit, helpers = translation_unit(root, rows=rows)
    a, b = function_span(unit, source.source.FUNCTION)
    results = {}
    profiles = [('O0', None, '-O0', False), ('O2', None, '-O2', False), ('O2-UBSAN', None, '-O2', True)]
    if not smoke:
        profiles += [(name, body, '-O2', True) for name, body in controls().items()]
        profiles.append(('invalid-cast-domain', source.selected().replace('(s32)D_800D239C',
            '(s32)(D_800D239C + 1.0e30f)'), '-O2', True))
    for name, body, opt, sanitize in profiles:
        path = out / ('native-' + name + ('-smoke' if smoke else '') + '.c')
        if body is not None:
            if body == source.selected():
                raise ValueError('Ineffective native control: ' + name)
            replacement = strip_externs(body)
            lo, hi = function_span(replacement, source.source.FUNCTION)
            text = unit[:a] + replacement[lo:hi] + unit[b:]
        else:
            text = unit
        path.write_text(text)
        exe = path.with_suffix('')
        command = [*native_command(opt, sanitize), *(['-fsanitize=float-cast-overflow'] if sanitize else []),
            '-mstackrealign', '-fno-strict-aliasing', str(path), '-o', str(exe)]
        p = subprocess.run(command, cwd=root, capture_output=True, text=True)
        path.with_suffix('.compile.json').write_text(json.dumps(dict(command=command, exit=p.returncode,
            diagnostics=p.stdout + p.stderr), indent=2) + '\n')
        if p.returncode or p.stdout or p.stderr:
            raise ValueError('Native build failed: ' + name + '\n' + p.stdout + p.stderr)
        p = subprocess.run([str(exe)], cwd=root, capture_output=True, timeout=120)
        results[name] = p.returncode
        accepted = p.returncode == -4 if name == 'invalid-cast-domain' else (
            p.returncode == 0 if body is None else p.returncode in (21, 22, 23))
        if p.stdout or p.stderr or not accepted:
            raise ValueError('Native result failed: %s exit %d' % (name, p.returncode))
        print(json.dumps(dict(profile=name, cases=len(rows), exit=p.returncode, smoke=smoke)), flush=True)
    receipt = dict(cases_per_positive_build=len(rows), profiles=['O0', 'O2', 'O2+UBSAN'],
        effective_controls=0 if smoke else len(controls()), exits=results, helper_source_SHA256=helpers,
        float_cast_overflow_checked=True, outside_cast_domain_sanitizer_control_exit=results.get('invalid-cast-domain'),
        raw_target_SHA256=source.RAW_SHA, full_mapped_public_arena_and_canonical_calls_equal=True,
        constants_loaded_from_frozen_ELF=True,
        public_aliases_preserved=True, aligned_host_endian_memory=True, five_real_helpers=True,
        finite_float_conversion_and_nonzero_divisor_domain=True, ordered_scores_and_maximum_17_ranked_records=True,
        trig_and_event_and_finalize_and_copy_providers_bounded=True, all_five_effect_gates_required=not smoke,
        native_private_stack_and_unmapped_aliases_and_invalid_pointers_excluded=True, smoke_only=smoke)
    (out / ('native32-smoke.json' if smoke else 'native32.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    source.source.freeze(root, out)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD, args.smoke), indent=2))
