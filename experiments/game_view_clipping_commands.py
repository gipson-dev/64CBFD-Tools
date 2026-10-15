"""Recover adjacent clipping-plane command and queue in a private owner."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_view_pending_queue as previous

BUILD, OWNER = 'conker/build/game-view-clipping-commands', previous.OWNER
COMMAND, QUEUE = 'func_1510B458', 'func_1510B51C'
TARGETS = ((COMMAND, 0x1510B458, 0x138908, 49), (QUEUE, 0x1510B51C, 0x1389CC, 55))
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, elf='307dae852b172a633730646ad73f4b406274b853a1ca86a7487b2ccfdc1721b7',
    owner='659475afe8ecfb244117e32317c4414964d3015db90794f62eff9d9b6682101c',
    guards='6e4e9e1850ceec25de5a319001682796fe19da44f494eb070bbbe08cad793576')
COMMAND_BODY = '''/* Rebuild one view with defaulted clip planes and remember the request. */
void func_1510B458(s32 index, f32 nearPlane, f32 farPlane) {
    if (nearPlane == 0.0f) {
        nearPlane = D_800D9B20;
    }
    if (farPlane == 0.0f) {
        farPlane = D_800D9B1C;
    }
    func_1510B5F8(index, (u16 *)(D_800BE628 + index * 0x180 + 0xB8),
        PROJECTION_VIEWS_138520[index].fovY, PROJECTION_VIEWS_138520[index].fovX,
        nearPlane, farPlane, PROJECTION_VIEWS_138520[index].matrixScale);
    D_800D9AF8[index][0] = nearPlane;
    D_800D9AF8[index][1] = farPlane;
    D_800D9B18 = 1;
}
'''
QUEUE_BODY = '''/* Consume pending clip planes using each view's current projection. */
void func_1510B51C(void) {
    f32 *pending = D_800D9AF8[0];
    s32 index;

    for (index = 0; index <= D_80082FA0; index++, pending += 2) {
        if (pending[0] != -1.0f) {
            func_1510B5F8(index, (u16 *)(D_800BE628 + index * 0x180 + 0xB8),
                PROJECTION_VIEWS_138520[index].fovY, PROJECTION_VIEWS_138520[index].fovX,
                pending[0], pending[1], PROJECTION_VIEWS_138520[index].matrixScale);
            pending[0] = -1.0f;
        }
    }
    D_800D9B18 = 0;
}
'''
BASE_QUEUE_BODY = QUEUE_BODY
QUEUE_BODY = QUEUE_BODY.replace('    s32 index;', '    f32 farPlane;\n    s32 index;').replace(
    '            func_1510B5F8(', '            farPlane = pending[1];\n            func_1510B5F8(').replace(
    'pending[0], pending[1],', 'pending[0], farPlane,')
GUARDS = ((0x48,0xC6020000,0xC6000000),(0x4C,0x4602A032,0x4600A032),
    (0x64,0xC6000004,0xC6040004),(0x7C,0xE7A20010,0xE7A00010),
    (0x80,0xE7A00014,0xE7A40014),(0x84,0xC4440084,0xC4460084),
    (0x94,0xE7A40018,0xE7A60018))
GUARD_ROWS = ''.join('%s,%s,0x%X,0x%08X,0x%08X,-,-,Preserve complete clipping-queue float temporary roles,,,false\n' %
    ((OWNER,QUEUE)+row) for row in GUARDS)


def guard_manifest(before):
    assert before.endswith(b'\n') and (','+QUEUE+',').encode() not in before
    return before+GUARD_ROWS.encode()


def recover(before, command=COMMAND_BODY, queue=QUEUE_BODY):
    for name, body in ((COMMAND, command), (QUEUE, queue)):
        lo, hi = build.function_span(before, name)
        before = before[:lo]+body.rstrip()+before[hi:]
    before = before.replace('    u8 padding84[0xFC];', '    f32 matrixScale;\n    u8 padding88[0xF8];')
    return before.replace('extern u8 D_800D9AF0;\n', 'extern u8 D_800D9AF0;\nextern f32 D_800D9AF8[][2];\nextern u8 D_800D9B18;\n', 1)


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out/'baseline.json'
    if not manifest.exists():
        data = {key:(root/path).read_bytes() for key,path in PATHS.items()}
        if {key:hashlib.sha256(value).hexdigest() for key,value in data.items()} != BASELINE:
            raise ValueError('Changed clipping command baseline')
        for key,value in data.items():
            (out/('before-'+key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE,indent=2)+'\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified clipping command manifest')
    for key,digest in BASELINE.items():
        if hashlib.sha256((out/('before-'+key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable clipping command input: '+key)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/BUILD
    freeze(root,out)
    rom = (root/'conker/conker.us.bin').read_bytes()
    records=[]
    for label,queue in variants():
        obj,diagnostics = build.compile_owner(root,out,recover((out/'before-owner').read_text(),queue=queue),label)
        data,functions = build.link_owner(root,out,obj,OWNER)
        for name,_,offset,count in TARGETS:
            info = functions[name]
            words = list(struct.unpack_from('>%dI' % (info['size']//4),data,info['value']))
            truth = struct.unpack_from('>%dI' % count,rom,offset)
            row=dict(label=label,function=name,bytes=info['size'],frame=-words[0]&65535,
                diagnostics=diagnostics,word_length_difference=len(words)-count,
                differences=[(i,hex(a),hex(b)) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
            records.append(row)
            print(label,name,info['size'],row['frame'],len(row['differences']),diagnostics,flush=True)
    (out/'screens.json').write_text(json.dumps(records,indent=2)+'\n')


def variants():
    captured=None
    for far in (False, True):
        for near in (False, True):
            for view in (False, True):
                body=BASE_QUEUE_BODY
                if far:
                    body=body.replace('    s32 index;', '    f32 farPlane;\n    s32 index;').replace(
                        '            func_1510B5F8(', '            farPlane = pending[1];\n            func_1510B5F8(').replace(
                        'pending[0], pending[1],', 'pending[0], farPlane,')
                if near:
                    body=body.replace('    s32 index;', '    f32 nearPlane;\n    s32 index;').replace(
                        'if (pending[0] != -1.0f)', 'if (-1.0f != (nearPlane = pending[0]))').replace(
                        '                pending[0],', '                nearPlane,')
                if view:
                    body=body.replace('    s32 index;', '    ViewProjection138520 *view;\n    s32 index;').replace(
                        '            func_1510B5F8(', '            view = &PROJECTION_VIEWS_138520[index];\n            func_1510B5F8(').replace(
                        '(u16 *)(D_800BE628 + index * 0x180 + 0xB8)', '(u16 *)((u8 *)view + 0xB8)').replace(
                        'PROJECTION_VIEWS_138520[index].', 'view->')
                yield 'far%d-near%d-view%d' % (far,near,view),body
                if far and near and not view:
                    captured=body
    for compare in (False,True):
        for scale in (False,True):
            body=captured.replace('    f32 farPlane;\n    f32 nearPlane;', '    f32 nearPlane;\n    f32 farPlane;')
            if compare:
                body=body.replace('if (-1.0f != (nearPlane = pending[0]))', 'if ((nearPlane = pending[0]) != -1.0f)')
            if scale:
                body=body.replace('    s32 index;', '    f32 scale;\n    s32 index;').replace(
                    '            func_1510B5F8(', '            scale = PROJECTION_VIEWS_138520[index].matrixScale;\n            func_1510B5F8(').replace(
                    'farPlane, PROJECTION_VIEWS_138520[index].matrixScale)', 'farPlane, scale)')
            yield 'near-first-compare%d-scale%d' % (compare,scale),body


if __name__ == '__main__':
    main()
