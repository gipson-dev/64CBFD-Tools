"""Native SDK32 execution against independently generated guest expectations."""
import json
import subprocess
import struct
from tools.experiments import game_map_trail_update_1510608c_recovery as source
from tools.tests import game_map_trail_update_1510608c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def state(m):
    offsets = ((0x10, 2), (0x12, 1), (0x68, 2), (0x54, 2), (0x56, 2))
    rows = [g.read(m, g.RECORD+a, n) for a, n in offsets] + [g.read(m, g.TICKS)]
    for offset in (0x6C, 0x70):
        rows.append({0: 0, g.CHILD0: 1, g.CHILD1: 2}[g.read(m, g.RECORD+offset)])
    rows += [g.read(m, g.RECORD+a) for a in (0x14, 0x18, 0x1C, 0x38, 0x3C, 0x40)]
    rows += [g.read(m, child+0x40+4*i) for child in (g.CHILD0, g.CHILD1) for i in range(3)]
    assert len(rows) == 20
    return rows


def harness(body=source.BODY):
    before, _ = source.source()
    types = before.split('#include "game/map_trail.h"', 1)[1].split('extern MapTrailPoint133190 D_800A5480;', 1)[0]
    rows = []
    ids = {**{a: i+1 for i, a in enumerate(g.CALLBACKS)}, g.REMOVE: 3, g.CURVE: 4, g.SAMPLES: 5, g.RNG: 6}
    count = 0
    for c in g.cases():
        if c.phase:
            continue
        initial = g.fixture(c)
        expected, calls = g.reference(initial, c)
        trace = 0
        for target, _ in calls:
            trace = trace*8 + ids[target]
        values = (c.flag, c.null, c.returned, c.changed, c.seed, c.mode, trace)
        literal = lambda values: ','.join('0x%Xu' % (v & 0xFFFFFFFF) for v in values)
        rows.append('{ {%s}, {%s}, {%s} }' % (literal(values), literal(state(initial)), literal(state(expected))))
        count += 1
    prefix = '#include <ultra64.h>\n#include "structs.h"\n#include "game/map_trail.h"\n' + types + source.PREAMBLE
    text = prefix + r'''
struct Case { u32 parameters[7], initial[20], expected[20]; };
static const struct Case cases[] = { ROWS };
static const struct Case *current;
static MapTrailRecord133190 record, expected;
static MapTrailChild133190 children[2], expectedChildren[2];
static u8 *retained;
static u32 trace, error;
static void diagnostic(const void *p,u32 n){__asm__ volatile(".byte 0xcd,0x80"::"a"(4),"b"(2),"c"(p),"d"(n):"memory");}
s32 D_800BE9E4;
static f32 real(u32 word) { union { u32 w; f32 f; } v; v.w=word; return v.f; }
static int equal(const void *a,const void *b,u32 n) { const u8*x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1; }
static void fill(void *a,u32 n) { u8*x=a;u32 i;for(i=0;i<n;i++)x[i]=0xA5; }
static void apply(MapTrailRecord133190 *r,MapTrailChild133190 *ch,const u32 *v) {
 u32 i,j;
 r->packet.duration=(s16)v[0];r->packet.enabled=(u8)v[1];r->timer=(s16)v[2];
 r->packet.minimum=(s16)v[3];r->packet.maximum=(s16)v[4];
 for(i=0;i<2;i++)r->children[i]=v[6+i]?&children[v[6+i]-1]:0;
 for(i=0;i<2;i++){MapTrailPoint133190*p=&r->packet.points[i?3:0];
  p->x=real(v[8+i*3]);p->y=real(v[9+i*3]);p->z=real(v[10+i*3]);}
 for(j=0;j<2;j++){ch[j].position.x=real(v[14+j*3]);ch[j].position.y=real(v[15+j*3]);ch[j].position.z=real(v[16+j*3]);}
}
static void effect(u32 id) {
 u32 mode=current->parameters[5];trace=trace*8+id;
 if(id<3){*retained=(u8)current->parameters[3];if(mode&1){record.packet.enabled^=1;D_800BE9E4=3;record.packet.duration=2;record.packet.points[3].x=real(0x7FC0ABCD);}}
 else if(id==3&&(mode&2)){if(retained)*retained^=0x81;D_800BE9E4=-1;record.timer=-2;}
 else if(id==4&&(mode&1)){D_800BE9E4=65537;record.packet.points[0].x=real(0xDEADBEEF);}
 else if(id==5&&(mode&2)){record.packet.minimum=123;record.packet.maximum=7;}
 else if(id==6&&(mode&1)){record.packet.minimum=-123;record.packet.maximum=-32768;record.children[0]=&children[1];}
}
static s32 callback0(u8*r,u8*changed){if(r!=(u8*)&record||!changed)error=1;retained=changed;effect(1);return(s32)current->parameters[2];}
static s32 callback1(u8*r,u8*changed){if(r!=(u8*)&record||!changed)error=2;retained=changed;effect(2);return(s32)current->parameters[2];}
s32 (*D_80088C10[2])(u8*,u8*);
void func_1516972C(struct102*r){if(r!=(struct102*)&record)error=3;effect(3);}
void func_15106214(MapTrailRecord133190*r){if(r!=&record)error=4;effect(4);}
void func_15106610(MapTrailRecord133190*r){if(r!=&record)error=5;effect(5);}
s32 func_150ADA20(void){static const u32 v[]={0,1,0xFFFFFFFF,0x80000000,7,0x87654321,32767,0xFFFFFFFE};effect(6);return(s32)v[current->parameters[4]];}
BODY
static int run(void) {
 u32 i;
 if(sizeof(void*)!=4||sizeof(MapTrailRecord133190)!=0x88||sizeof(MapTrailPacket133190)!=80||
    __builtin_offsetof(MapTrailChild133190,position)!=0x40)return 10;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];fill(&record,sizeof(record));fill(children,sizeof(children));
  record.packet.flag=(s8)current->parameters[0];apply(&record,children,current->initial);
  expected=record;expectedChildren[0]=children[0];expectedChildren[1]=children[1];
  apply(&expected,expectedChildren,current->expected);
  D_800BE9E4=(s32)current->initial[5];trace=error=0;retained=0;
  D_80088C10[0]=current->parameters[1]?0:callback0;D_80088C10[1]=current->parameters[1]?0:callback1;
  func_1510608C((struct102*)&record);
  if(error||trace!=current->parameters[6])return 11;
  if((u32)D_800BE9E4!=current->expected[5])return 12;
  if(!equal(&record,&expected,sizeof(record))){diagnostic(current->parameters,28);diagnostic(&record,sizeof(record));diagnostic(&expected,sizeof(expected));return 13;}
  if(!equal(children,expectedChildren,sizeof(children)))return 14;
 }
 return 0;
}
'''
    return text.replace('ROWS', ',\n'.join(rows)).replace('BODY', body) + START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)'), count


def run():
    out = source.OUT/'native'
    out.mkdir(exist_ok=True)
    text, count = harness()
    path = out/'target.c'
    path.write_text(text)
    reports = []
    for opt in ('-O0', '-O2', '-O3'):
        executable = out/opt[1:]
        command = native_command(opt) + [str(path), '-o', str(executable)]
        compiled = subprocess.run(command, cwd=source.ROOT, capture_output=True, text=True)
        assert compiled.returncode == 0, compiled.stdout+compiled.stderr
        result = subprocess.run([str(executable)], timeout=15, capture_output=True)
        if result.returncode == 13 and len(result.stderr) == 300:
            params = struct.unpack('<7I', result.stderr[:28])
            a, b = result.stderr[28:164], result.stderr[164:]
            raise AssertionError((opt, params, [(i,x,y)for i,(x,y)in enumerate(zip(a,b))if x!=y]))
        assert result.returncode == 0, (opt, result.returncode)
        reports.append(dict(optimization=opt, cases=count, UBSan=True, strict_aliasing=True))
    controls = {
        'zero-expires': source.BODY.replace('->timer < 0', '->timer <= 0'),
        'changed-inverted': source.BODY.replace('if (changed != 0)', 'if (changed == 0)'),
        'wrong-enabled-bit': source.BODY.replace('->packet.enabled & 1', '->packet.enabled & 2'),
        'callback-return-inverted': source.BODY.replace('update((u8 *)node, &changed) == 0', 'update((u8 *)node, &changed) != 0'),
        'wrong-endpoint': source.BODY.replace('->packet.points[3]', '->packet.points[2]'),
    }
    rejected = []
    for label, body in controls.items():
        assert body != source.BODY
        mutated, _ = harness(body)
        path = out/(label+'.c')
        path.write_text(mutated)
        executable = out/label
        compiled = subprocess.run(native_command('-O2')+[str(path), '-o', str(executable)], cwd=source.ROOT, capture_output=True, text=True)
        assert compiled.returncode == 0, compiled.stdout+compiled.stderr
        result = subprocess.run([str(executable)], timeout=15, capture_output=True)
        assert result.returncode in (11, 12, 13, 14), (label, result.returncode)
        rejected.append(label)
    (out/'negative-controls.json').write_text(json.dumps(rejected)+'\n')
    (out/'receipt.json').write_text(json.dumps(reports, indent=2)+'\n')
    return reports
