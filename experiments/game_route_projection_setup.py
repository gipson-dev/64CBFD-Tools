"""Non-installable route projection recovery with real neighbor/event helpers."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_neighbor_preference as neighbor
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint

BUILD='conker/build/game-route-projection-setup'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_150891E8',0x150891E8,0xB6698,321
INPUTS=dict(neighbor.INPUTS,**neighbor.AFTER)
INPUTS.update({
    'conker/asm/15AA10.s':'7353e92717ffd91feb69dbcaffda8a6b0f06613810c4155165a984c752857db5',
    'conker/asm/data/2424A0.rodata.s':'78d0ff41de7bab3a0f2121db2cdaac4d69c4576706dc3671ebf66003a1e51c19',
})
SELECTED='''/* Select the nearer route node and queue a clamped projection payload. */
void func_150891E8(u8 *record, u8 *actor) {
    extern u16 D_8008FDBC;
    extern s8 D_800D23A8;
    extern f32 D_8009DA08;
    extern f32 sqrtf(f32);
    extern void func_1512D560(u8 *, s32, void *);
    u8 *object;
    u8 *node;
    u8 *previousNode;
    u8 *currentNode;
    u8 *table;
    u8 *payload;
    s32 i;
    s32 j;
    s32 nodeX;
    s32 nodeZ;
    s32 previousX;
    s32 previousZ;
    s32 nodeY;
    s8 mode;
    u8 preferred;
    u8 candidate;
    u8 current;
    u8 previous;
    u8 first;
    u8 next;
    f32 actorX;
    f32 actorZ;
    f32 dx;
    f32 dy;
    f32 dz;
    f32 previousDx;
    f32 previousDz;
    f32 distance;
    f32 currentDistance;
    f32 best;
    f32 length;
    f32 targetZ;

    object = *(u8 **)(actor + 0x318);
    if (object != 0) {
        if (D_8008FDBC & 0x40) {
            preferred = 1;
        } else {
            preferred = 0;
        }
        if (*(s8 *)(record + 0x30) == 2) {
            for (i = 0; i < D_80087290; i++) {
                node = D_800D2350 + i * 0x10;
                if (node[0xE] == 5 && node[0xF] == 2) {
                    record[0x4A] = i;
                    record[0x4B] = i;
                    for (j = 0; j < 5; j++) {
                        candidate = node[j + 9];
                        if (candidate != 0xFF) {
                            mode = D_800D23A8;
                            if ((mode == 0 && D_800D2350[candidate * 0x10 + 0xF] == 3) ||
                                (mode != 0 && D_800D2350[candidate * 0x10 + 0xF] != 3)) {
                                record[0x4B] = candidate;
                            }
                        }
                    }
                    i = D_80087290;
                }
            }
            current = record[0x4B];
            previous = record[0x4A];
            first = current;
            best = D_8009DA08;
            do {
                node = D_800D2350 + current * 0x10;
                next = func_1508907C(current, 0xFF, previous, preferred);
                nodeX = *(s16 *)(node + 0);
                nodeZ = *(s16 *)(node + 4);
                actorX = *(f32 *)(actor + 0x14);
                actorZ = *(f32 *)(actor + 0x1C);
                previous = current;
                current = next;
                dx = actorX - (f32)nodeX;
                dz = actorZ - (f32)nodeZ;
                distance = dx * dx + dz * dz;
                if (distance < best) {
                    best = distance;
                    record[0x4A] = previous;
                    record[0x4B] = next;
                }
            } while (first != current);
            func_1512D560(*(u8 **)(actor + 0x318), 5, 0);
            record[0x30] = 3;
        }
        current = record[0x4B];
        table = D_800D2350;
        actorX = *(f32 *)(actor + 0x14);
        currentNode = table + current * 0x10;
        nodeX = *(s16 *)(currentNode + 0);
        nodeZ = *(s16 *)(currentNode + 4);
        actorZ = *(f32 *)(actor + 0x1C);
        previous = record[0x4A];
        previousNode = table + previous * 0x10;
        dx = actorX - (f32)nodeX;
        dz = actorZ - (f32)nodeZ;
        currentDistance = dx * dx + dz * dz;
        previousX = *(s16 *)(previousNode + 0);
        previousZ = *(s16 *)(previousNode + 4);
        previousDx = actorX - (f32)previousX;
        previousDz = actorZ - (f32)previousZ;
        distance = previousDx * previousDx + previousDz * previousDz;
        if (currentDistance < distance) {
            record[0x4A] = current;
            record[0x4B] = func_1508907C(current, 0xFF, previous, preferred);
            previousNode = currentNode;
            actorX = *(f32 *)(actor + 0x14);
            nodeX = *(s16 *)(previousNode + 0);
            nodeZ = *(s16 *)(previousNode + 4);
            actorZ = *(f32 *)(actor + 0x1C);
            dx = actorX - (f32)nodeX;
            dz = actorZ - (f32)nodeZ;
            distance = currentDistance;
        } else {
            dx = previousDx;
            dz = previousDz;
        }
        nodeY = *(s16 *)(previousNode + 2);
        dy = *(f32 *)(actor + 0x18) - (f32)nodeY;
        length = sqrtf(dy * dy + distance);
        dx /= length;
        dy /= length;
        dz /= length;
        if (length > 1000.0f) {
            length = 1000.0f;
        }
        payload = record + 0x4C;
        *(u32 *)(payload + 0) = 0;
        *(f32 *)(payload + 0x20) = *(f32 *)(actor + 0x14);
        *(f32 *)(payload + 0x24) = *(f32 *)(actor + 0x18);
        *(f32 *)(payload + 0x28) = *(f32 *)(actor + 0x1C);
        *(f32 *)(payload + 0x14) = *(f32 *)(actor + 0x14) - dx * length;
        *(f32 *)(payload + 0x18) = *(f32 *)(actor + 0x18) - dy * length;
        targetZ = *(f32 *)(actor + 0x1C) - dz * length;
        *(u32 *)(payload + 4) = 0;
        *(f32 *)(payload + 0x30) = 30.0f;
        *(f32 *)(payload + 0x34) = 30.0f;
        *(f32 *)(payload + 0x2C) = 0.0f;
        *(f32 *)(payload + 0x1C) = targetZ;
        func_1512D560(*(u8 **)(actor + 0x318), 7, payload);
        *(f32 *)(object + 0x19C) = 30.0f;
        *(f32 *)(object + 0x1A4) = 30.0f;
        *(f32 *)(object + 0x1A0) = 30.0f;
        *(f32 *)(object + 0x1A8) = 30.0f;
    }
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text


def compact_body():
    body=SELECTED
    for declaration in ('    u8 *table;\n','    s32 nodeX;\n','    s32 nodeZ;\n','    s32 previousX;\n',
            '    s32 previousZ;\n','    s32 nodeY;\n','    f32 actorX;\n','    f32 actorZ;\n',
            '    f32 previousDx;\n','    f32 previousDz;\n','    f32 length;\n'):
        body=body.replace(declaration,'')
    body=body.replace('''                nodeX = *(s16 *)(node + 0);
                nodeZ = *(s16 *)(node + 4);
                actorX = *(f32 *)(actor + 0x14);
                actorZ = *(f32 *)(actor + 0x1C);
                previous = current;
                current = next;
                dx = actorX - (f32)nodeX;
                dz = actorZ - (f32)nodeZ;''','''                previous = current;
                current = next;
                dx = *(f32 *)(actor + 0x14) - (f32)*(s16 *)(node + 0);
                dz = *(f32 *)(actor + 0x1C) - (f32)*(s16 *)(node + 4);''')
    lo=body.index('        table = D_800D2350;');hi=body.index('        length = sqrtf',lo)
    body=body[:lo]+'''        currentNode = D_800D2350 + current * 0x10;
        previous = record[0x4A];
        previousNode = D_800D2350 + previous * 0x10;
        dx = *(f32 *)(actor + 0x14) - (f32)*(s16 *)(currentNode + 0);
        dz = *(f32 *)(actor + 0x1C) - (f32)*(s16 *)(currentNode + 4);
        currentDistance = dx * dx + dz * dz;
        dx = *(f32 *)(actor + 0x14) - (f32)*(s16 *)(previousNode + 0);
        dz = *(f32 *)(actor + 0x1C) - (f32)*(s16 *)(previousNode + 4);
        distance = dx * dx + dz * dz;
        if (currentDistance < distance) {
            record[0x4A] = current;
            record[0x4B] = func_1508907C(current, 0xFF, previous, preferred);
            previousNode = currentNode;
            dx = *(f32 *)(actor + 0x14) - (f32)*(s16 *)(previousNode + 0);
            dz = *(f32 *)(actor + 0x1C) - (f32)*(s16 *)(previousNode + 4);
            distance = currentDistance;
        }
        dy = *(f32 *)(actor + 0x18) - (f32)*(s16 *)(previousNode + 2);
'''+body[hi:]
    return body.replace('length','best')


MODEL=compact_body()
MODEL_SHA='1825510015d392e2f819acaa88ea5372de3aa21771025fe060b0b8d2ae5af269'
MODEL_BINDINGS={
    44:[('R_MIPS_HI16','D_8008FDBC')],56:[('R_MIPS_LO16','D_8008FDBC')],
    60:[('R_MIPS_HI16','D_80087290')],76:[('R_MIPS_LO16','D_80087290')],
    128:[('R_MIPS_HI16','D_800D2350')],144:[('R_MIPS_LO16','D_800D2350')],
    132:[('R_MIPS_HI16','D_800D23A8')],136:[('R_MIPS_LO16','D_800D23A8')],
    536:[('R_MIPS_HI16','D_800D2350')],544:[('R_MIPS_LO16','D_800D2350')],
    540:[('R_MIPS_HI16','D_8009DA08')],552:[('R_MIPS_LO16','D_8009DA08')],
    596:[('R_MIPS_26','func_1508907C')],716:[('R_MIPS_26','func_1512D560')],
    736:[('R_MIPS_HI16','D_800D2350')],744:[('R_MIPS_LO16','D_800D2350')],
    908:[('R_MIPS_26','func_1508907C')],1156:[('R_MIPS_26','func_1512D560')],
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=neighbor.baseline.model.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150891E8() {\n    return 0;\n}':raise ValueError('Unknown route projection placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='initial',body=SELECTED,normal=False):
    values=freeze(root,out)
    compiler=neighbor.baseline.model.compile_owner
    if normal:
        from tools.experiments.game_remaining_donor_candidates import compile_owner as compiler
    obj,diagnostics=compiler(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=neighbor.baseline.model.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    text,functions,rel=neighbor.parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    truth=list(struct.unpack_from('>321I',values['conker/conker.us.bin'],ROM))
    row=dict(words=len(words),frame=(-words[0])&65535,differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-321),
        diagnostics=diagnostics,raw_sha256=hashlib.sha256(raw).hexdigest(),
        saved=[(w>>16&31,w&65535) for w in words if w>>26==43 and w>>21&31==29],
        bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def require_retail_contract(words):
    # Necessary extent/entry gates, not a sufficient whole-function match proof.
    if len(words)!=321 or words[0]!=0x27BDFF88 or words[10]!=0x8EA20318 or words[12]>>26!=20 or words[13]!=0x8FBF002C:
        raise ValueError('Projection model is not installable: retail extent and conditional object lifetime differ')


def checked_model(obj):
    text,functions,rel=neighbor.parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=1228 or hashlib.sha256(raw).hexdigest()!=MODEL_SHA or bindings!=MODEL_BINDINGS:
        raise ValueError('Unknown projection semantic model or bindings')
    return raw,bindings


def qualify_model(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified-model',MODEL,True)
    checked_model(obj)
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    # Compare like-for-like normal-profile objects; production remains no-unroll.
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=neighbor.same_functions(before,obj,(FUNCTION,))
    if diagnostics or row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['neighbors'])!=(307,120,309,72) or \
            neighbor.normalized_pools(before)!=neighbor.normalized_pools(obj):raise ValueError('Changed projection model/owner evidence')
    try:require_retail_contract(words)
    except ValueError:row['installable']=False
    else:raise ValueError('Recorded projection model unexpectedly passed the retail gate')
    (out/'model-audit.json').write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal',action='store_true');parser.add_argument('--compact',action='store_true')
    parser.add_argument('--qualify',action='store_true');args=parser.parse_args()
    print(json.dumps(qualify_model(root,root/BUILD)[2] if args.qualify else measure(root,root/BUILD,
        ('compact-' if args.compact else '')+('normal' if args.normal else 'initial'),
        compact_body() if args.compact else SELECTED,normal=args.normal)[2],indent=2))
