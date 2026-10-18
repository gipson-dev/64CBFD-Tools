"""Recover both route spline payload modes against the complete retail routine."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_dispatcher_match as prior
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-route-spline-payload-recovery'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_150896EC',0x150896EC,0xB6B9C,305
INPUTS=dict(prior.INPUTS,**prior.AFTER)
INPUTS.update({
    'conker/src/game/generated_76C90.c':'8e9c9885e7772fbd356120a036307a2ba8202d04fc72de82a3027dba7f750dde',
    'conker/asm/76C90.s':'45f439d3beb500a34a1ac6a681b270d878681313347b6e095d0fdc6ee517d27e',
    'conker/build/alternative-source-byte-audit-20261014/snapshot/conker/src/game/game_B3020.c':'985829462ef793d967dfbd0e9d0375baa86ad522555bbfb990b3baec5d32eda9',
})
SELECTED='''/* Queue a route stop or interpolate its six-channel spline payload. */
void func_150896EC(u8 *record, u8 *actor, s32 stop) {
    extern s8 D_800D23A8;
    extern s32 D_800BE9E4;
    extern f32 D_8009DA0C;
    extern f32 D_8009DA10;
    extern f64 D_8009DA18;
    extern void func_1512D560(u8 *, s32, void *);
    extern f32 func_150497E0(f32 *, s32, f32);
    f32 x[4];
    f32 y[4];
    f32 z[4];
    f32 targetX[4];
    f32 targetY[4];
    f32 targetZ[4];
    f32 *xCursor;
    f32 *yCursor;
    f32 *zCursor;
    f32 *targetXCursor;
    f32 *targetYCursor;
    f32 *targetZCursor;
    f32 phase;
    f32 angle;
    f32 previousX;
    f32 previousY;
    f32 previousZ;
    f32 previousTargetX;
    f32 previousTargetY;
    f32 previousTargetZ;
    f64 angleScale;
    s32 previousValid;
    s32 i;
    u8 routeClass;
    u8 id;
    u8 next;
    u8 old;
    u8 *node;
    u8 *recordCursor;
    u8 *payload;
    u8 *object;

    object = *(u8 **)(actor + 0x318);
    if (object != 0) {
        if (stop != 0) {
            payload = record + 0x4C;
            *(s32 *)(payload + 0x10) = 120;
            *(f32 *)(payload + 0x0C) = D_8009DA0C;
            func_1512D560(*(u8 **)(actor + 0x318), 10, payload);
            func_1512D560(*(u8 **)(actor + 0x318), 6, (void *)(u32)object[0x23D]);
            record[0x49] = 0;
        } else {
            if (*(s8 *)(record + 0x49) == 0) {
                routeClass = D_800D23A8 + 1;
                for (i = 0; i < D_80087290; i++) {
                    node = D_800D2350 + i * 16;
                    if (node[14] == 6 && node[15] == routeClass) {
                        record[0x44] = i;
                        i = D_80087290;
                    }
                }
                id = func_1508907C(record[0x44], 6, 255, 0);
                record[0x45] = id;
                next = func_1508907C(id, 6, record[0x44], 0);
                record[0x46] = next;
                record[0x47] = func_1508907C(next, 6, record[0x45], 0);
                *(f32 *)(record + 0x38) = *(f32 *)(actor + 0x14);
                *(f32 *)(record + 0x3C) = *(f32 *)(actor + 0x18);
                *(f32 *)(record + 0x40) = *(f32 *)(actor + 0x1C);
                *(f32 *)(record + 0x34) = 0.0f;
                func_1512D560(*(u8 **)(actor + 0x318), 5, (void *)(u32)object[0x23D]);
                record[0x49] = 1;
            }
            *(f32 *)(record + 0x34) += D_8009DA10 * (f32)D_800BE9E4;
            phase = *(f32 *)(record + 0x34);
            if (phase >= 1.0f) {
                id = record[0x46];
                if (id == 255) {
                    *(f32 *)(record + 0x34) = 1.0f;
                } else {
                    next = record[0x47];
                    old = record[0x45];
                    record[0x45] = id;
                    *(f32 *)(record + 0x34) = phase - 1.0f;
                    record[0x46] = next;
                    record[0x44] = old;
                    record[0x47] = func_1508907C(next, 6, id, 0);
                }
            }
            previousValid = 0;
            angleScale = D_8009DA18;
            recordCursor = record;
            xCursor = x;
            yCursor = y;
            zCursor = z;
            targetXCursor = targetX;
            targetYCursor = targetY;
            targetZCursor = targetZ;
            do {
                id = recordCursor[0x44];
                if (id != 255) {
                    previousValid = 1;
                    func_15086CBC(id, xCursor, yCursor, zCursor);
                    func_15086CBC(func_1508907C(recordCursor[0x44], 4, 255, 0),
                        targetXCursor, targetYCursor, targetZCursor);
                } else if (previousValid == 1) {
                    previousValid = 0;
                    angle = (f32)((f64)*(f32 *)(actor + 0x40) * angleScale);
                    *xCursor = *(f32 *)(record + 0x38) - sinf(angle) * 500.0f;
                    *yCursor = *(f32 *)(record + 0x3C) + 180.0f;
                    *zCursor = *(f32 *)(record + 0x40) - cosf(angle) * 500.0f;
                    *targetXCursor = *(f32 *)(record + 0x38);
                    *targetYCursor = *(f32 *)(record + 0x3C) + 120.0f;
                    *targetZCursor = *(f32 *)(record + 0x40);
                } else {
                    previousX = xCursor[-1];
                    previousY = yCursor[-1];
                    previousZ = zCursor[-1];
                    previousTargetX = targetXCursor[-1];
                    previousTargetY = targetYCursor[-1];
                    previousTargetZ = targetZCursor[-1];
                    *xCursor = (previousX - xCursor[-2]) + previousX;
                    *yCursor = (previousY - yCursor[-2]) + previousY;
                    *zCursor = (previousZ - zCursor[-2]) + previousZ;
                    *targetXCursor = (previousTargetX - targetXCursor[-2]) + previousTargetX;
                    *targetYCursor = (previousTargetY - targetYCursor[-2]) + previousTargetY;
                    *targetZCursor = (previousTargetZ - targetZCursor[-2]) + previousTargetZ;
                }
                targetZCursor++;
                recordCursor++;
                xCursor++;
                yCursor++;
                zCursor++;
                targetXCursor++;
                targetYCursor++;
            } while (targetZCursor != targetZ + 4);
            phase = *(f32 *)(record + 0x34);
            payload = record + 0x4C;
            *(f32 *)(payload + 0x14) = func_150497E0(x, 0, phase);
            *(f32 *)(payload + 0x18) = func_150497E0(y, 0, phase);
            *(f32 *)(payload + 0x1C) = func_150497E0(z, 0, phase);
            *(f32 *)(payload + 0x20) = func_150497E0(targetX, 0, phase);
            *(f32 *)(payload + 0x24) = func_150497E0(targetY, 0, phase);
            *(f32 *)(payload + 0x28) = func_150497E0(targetZ, 0, phase);
            *(u32 *)(payload + 0) = 0;
            *(u32 *)(payload + 4) = 0;
            *(f32 *)(payload + 0x30) = 30.0f;
            *(f32 *)(payload + 0x34) = 30.0f;
            *(f32 *)(payload + 0x2C) = 0.0f;
            func_1512D560(*(u8 **)(actor + 0x318), 7, payload);
        }
    }
}
'''
RAW_SHA='6437f38581ccce8cb4f0c13fc162c3b6ae8e65162ab327540b57c8463dbcd98f'
FRONT_SHA='47f168f182b09c3ba6e1a0046652a1aa36701b29e80ed890e8aeb2c8832ffb0c'
BINDINGS={at:[('R_MIPS_26',name)] for at,name in (
    (116,'func_1512D560'),(136,'func_1512D560'),(288,'func_1508907C'),(312,'func_1508907C'),
    (336,'func_1508907C'),(392,'func_1512D560'),(528,'func_1508907C'),(612,'func_15086CBC'),
    (632,'func_1508907C'),(652,'func_15086CBC'),(700,'sinf'),(744,'cosf'),
    (980,'func_150497E0'),(1004,'func_150497E0'),(1024,'func_150497E0'),(1044,'func_150497E0'),
    (1064,'func_150497E0'),(1084,'func_150497E0'),(1140,'func_1512D560'))}
for hi,lo,name in ((92,96,'D_8009DA0C'),(156,160,'D_80087290'),(168,172,'D_800D23A8'),
        (200,204,'D_800D2350'),(408,412,'D_800BE9E4'),(428,432,'D_8009DA10'),(540,544,'D_8009DA18')):
    BINDINGS[hi]=[('R_MIPS_HI16',name)];BINDINGS[lo]=[('R_MIPS_LO16',name)]


def checked(obj,front=False):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in relocations.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=1208 or hashlib.sha256(raw).hexdigest()!=(FRONT_SHA if front else RAW_SHA) or bindings!=BINDINGS:
        raise ValueError('Unknown complete spline payload source or bindings')
    return raw,bindings


def freeze(root,out):
    values={}
    for path,digest in INPUTS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Changed spline payload input: '+path)
        values[path]=data
    out.mkdir(parents=True,exist_ok=True)
    for index,data in enumerate(values.values()):
        path=out/('before-%02d'%index)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed spline payload snapshot')
        if not path.exists():path.write_bytes(data)
    return values


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150896EC() {\n    return 0;\n}':raise ValueError('Unknown spline payload stub')
    result=before[:lo]+body.rstrip()+before[hi:]
    old='    extern s32 func_150896EC();'
    if result.count(old)!=1:raise ValueError('Unknown spline payload caller declaration')
    return result.replace(old,'    extern void func_150896EC(u8 *, u8 *, s32);')


def measure(root,out,label='initial',body=SELECTED,normal=False):
    values=freeze(root,out);before=values['conker/src/game/generated_B3020.c'].decode()
    obj,diag=prior.prior.compile_profile(root,out,recovered_owner(before,body),label,normal)
    if diag:raise ValueError(diag)
    data,functions=prior.prior.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>305I',values['conker/conker.us.bin'],ROM))
    text,defs,rel=parse_object(obj);f=defs[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    row=dict(words=len(words),frame=(-words[0])&65535,differences=sum(i>=len(words) or i>=WORDS or words[i]!=truth[i]
        for i in range(max(len(words),WORDS))),raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings,
        production_installed=False,matching_credit=0)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def indexed(body):
    result=body
    names=('x','y','z','targetX','targetY','targetZ')
    for name in names:
        cursor=name+'Cursor'
        for text in ('    f32 *'+cursor+';\n','            '+cursor+' = '+name+';\n','                '+cursor+'++;\n'):
            if result.count(text)!=1:raise ValueError('Unknown spline cursor: '+text)
            result=result.replace(text,'')
        result=result.replace(cursor+'[-1]',name+'[i - 1]').replace(cursor+'[-2]',name+'[i - 2]')
        result=result.replace('*'+cursor,name+'[i]')
        result=re.sub(r'\b'+cursor+r'\b','('+name+' + i)',result)
    for text in ('    u8 *recordCursor;\n','            recordCursor = record;\n','                recordCursor++;\n'):
        if result.count(text)!=1:raise ValueError('Unknown spline record cursor')
        result=result.replace(text,'')
    return result.replace('recordCursor[0x44]','record[i + 0x44]').replace(
        '            do {','            for (i = 0; i < 4; i++) {').replace(
        '            } while ((targetZ + i) != targetZ + 4);','            }')


def fields(body):
    result=body.replace('    u8 *node;\n','').replace('                    node = D_800D2350 + i * 16;\n','')
    return result.replace('node[14]','(D_800D2350 + i * 16)[14]').replace('node[15]','(D_800D2350 + i * 16)[15]')


def expressions(body):
    old='''                id = func_1508907C(record[0x44], 6, 255, 0);
                record[0x45] = id;
                next = func_1508907C(id, 6, record[0x44], 0);
                record[0x46] = next;
                record[0x47] = func_1508907C(next, 6, record[0x45], 0);'''
    new='''                record[0x45] = func_1508907C(record[0x44], 6, 255, 0);
                record[0x46] = func_1508907C(record[0x45], 6, record[0x44], 0);
                record[0x47] = func_1508907C(record[0x46], 6, record[0x45], 0);'''
    if body.count(old)!=1:raise ValueError('Unknown spline selector chain')
    result=body.replace(old,new)
    old='''                    next = record[0x47];
                    old = record[0x45];
                    record[0x45] = id;
                    *(f32 *)(record + 0x34) = phase - 1.0f;
                    record[0x46] = next;
                    record[0x44] = old;
                    record[0x47] = func_1508907C(next, 6, id, 0);'''
    new='''                    i = record[0x45];
                    record[0x45] = id;
                    *(f32 *)(record + 0x34) = phase - 1.0f;
                    record[0x46] = record[0x47];
                    record[0x44] = i;
                    record[0x47] = func_1508907C(record[0x46], 6, id, 0);'''
    if result.count(old)!=1:raise ValueError('Unknown spline shift')
    return result.replace(old,new).replace('    u8 next;\n','').replace('    u8 old;\n','')


def front_floats(body):
    declarations=''.join('    f32 '+name+';\n' for name in ('phase','previousX','previousY','previousZ',
        'previousTargetX','previousTargetY','previousTargetZ'))
    result=body
    for text in declarations.splitlines(True):
        if result.count(text)!=1:raise ValueError('Unknown spline float declaration')
        result=result.replace(text,'')
    return result.replace('    f32 x[4];',declarations+'    f32 x[4];')


def forms():
    result={'indexed':indexed(SELECTED),'fields':fields(SELECTED),'expressions':expressions(SELECTED),
        'front-floats':front_floats(SELECTED)}
    for name,body in (('indexed-fields',fields(indexed(SELECTED))),
        ('indexed-expressions',expressions(indexed(SELECTED))),
        ('indexed-fields-expressions',expressions(fields(indexed(SELECTED))))):
        result[name]=body;result[name+'-front']=front_floats(body)
    return result


def direct_phase(body):
    old='''            phase = *(f32 *)(record + 0x34);
            if (phase >= 1.0f) {'''
    if body.count(old)!=1:raise ValueError('Unknown early spline phase')
    return body.replace(old,'            if (*(f32 *)(record + 0x34) >= 1.0f) {').replace(
        '*(f32 *)(record + 0x34) = phase - 1.0f;','*(f32 *)(record + 0x34) -= 1.0f;')


def inline_previous(body):
    result=body
    for name,cursor in zip(('previousX','previousY','previousZ','previousTargetX','previousTargetY','previousTargetZ'),
            ('xCursor','yCursor','zCursor','targetXCursor','targetYCursor','targetZCursor')):
        result=result.replace('    f32 '+name+';\n','').replace('                    '+name+' = '+cursor+'[-1];\n','')
        result=re.sub(r'\b'+name+r'\b',cursor+'[-1]',result)
    return result


def refinements():
    base=direct_phase(SELECTED);small=inline_previous(base)
    result={'direct-phase':base,'inline-previous':inline_previous(SELECTED),'phase-inline-previous':small,
        'phase-inline-fields':fields(small),'phase-inline-indexed':indexed(small)}
    for name,body in (('phase-object-first',base),('phase-inline-object-first',small)):
        result[name]=body.replace('    u8 *object;\n','').replace('    f32 x[4];','    u8 *object;\n    f32 x[4];')
    for name,body in (('phase-split-payload',base),('phase-inline-split-payload',small)):
        text='''            payload = record + 0x4C;
            *(s32 *)(payload + 0x10) = 120;
            *(f32 *)(payload + 0x0C) = D_8009DA0C;
            func_1512D560(*(u8 **)(actor + 0x318), 10, payload);'''
        replacement=text.replace('payload','stopPayload')
        result[name]=body.replace('    u8 *payload;','    u8 *payload;\n    u8 *stopPayload;').replace(text,replacement)
    return result


def compact_forms():
    base=inline_previous(SELECTED)
    scale=base.replace('    f64 angleScale;\n','').replace('            angleScale = D_8009DA18;\n','').replace(
        ' * angleScale',' * D_8009DA18')
    cls=base.replace('    u8 routeClass;\n','').replace('                routeClass = D_800D23A8 + 1;\n','').replace(
        'node[15] == routeClass','node[15] == (u8)(D_800D23A8 + 1)')
    combined=scale.replace('    u8 routeClass;\n','').replace('                routeClass = D_800D23A8 + 1;\n','').replace(
        'node[15] == routeClass','node[15] == (u8)(D_800D23A8 + 1)')
    result={'compact-expressions':expressions(base),'compact-scale':scale,'compact-class':cls,
        'compact-scale-class':combined,'compact-scale-expressions':expressions(scale),
        'compact-all':expressions(combined),'compact-const-scale':scale.replace('extern f64 D_8009DA18','extern const f64 D_8009DA18')}
    return {name:direct_phase(body) for name,body in result.items()}


def scoped_loop(body):
    names=('xCursor','yCursor','zCursor','targetXCursor','targetYCursor','targetZCursor')
    declarations=''.join('    f32 *'+name+';\n' for name in names)+'    f64 angleScale;\n    s32 previousValid;\n    u8 *recordCursor;\n'
    result=body
    for line in declarations.splitlines(True):
        if result.count(line)!=1:raise ValueError('Unknown spline scope declaration')
        result=result.replace(line,'')
    first=result.index('            previousValid = 0;')
    last=result.index('            phase = *(f32 *)(record + 0x34);',first)
    inner=''.join('    '+line for line in result[first:last].splitlines(True))
    decl=''.join('            '+line for line in declarations.splitlines(True))
    return result[:first]+'            {\n'+decl+inner+'            }\n'+result[last:]


def scope_forms():
    base=direct_phase(SELECTED)
    return {'scoped-loop':scoped_loop(base),'scoped-loop-inline':scoped_loop(inline_previous(base)),
        'scoped-loop-fields':scoped_loop(fields(base)),'scoped-loop-inline-fields':scoped_loop(fields(inline_previous(base)))}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument('--normal',action='store_true');group.add_argument('--screen',action='store_true')
    group.add_argument('--front',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.screen:
        for label,body in dict(forms(),**refinements(),**compact_forms(),**scope_forms()).items():
            row=measure(root,out,label,body)[2]
            print(json.dumps({k:row[k] for k in ('words','frame','differences','raw_sha256')}|dict(label=label)),flush=True)
    elif args.front:
        obj,_,row=measure(root,out,'front-qualified',front_floats(SELECTED));checked(obj,True)
        print(json.dumps(row,indent=2))
    else:print(json.dumps(measure(root,out,'normal' if args.normal else 'initial',normal=args.normal)[2],indent=2))
