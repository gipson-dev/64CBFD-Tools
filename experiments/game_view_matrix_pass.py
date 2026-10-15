"""Recover the per-view matrix pass under its existing compiler profile."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_view_clipping_commands as previous

BUILD,OWNER='conker/build/game-view-matrix-pass',previous.OWNER
FUNCTION,ENTRY,ROM,WORDS='func_1510B690',0x1510B690,0x138B40,73
PATHS=dict(previous.PATHS,sdk='conker/src/libultra/gu/mtxutil2.c',
    multiply_owner='conker/src/game/generated_D4E10.c',multiply_original='conker/asm/D4E10.s',
    frustum_owner='conker/src/game_476D0.c',frustum_original='conker/asm/nonmatchings/game_476D0/func_1501B22C.s')
BASELINE=dict(previous.BASELINE,
    elf='6c21a585574499c927f22707b735110ff34323dfb3bba084e75ba3bc66f1e340',
    owner='7f3d9a7a4fb00d58842ddee5e232fa13a62e89574ddaebad17fd80805f4927cc',
    guards='8bfcaa60e5503ffa4f80436b7b9f3251003c0389cfcc41351cfe8372dd61eb37',
    sdk='45ad70401c273ef3d4ddf922da65e09ec1a1da82d93d4f0fb352a06d82597fc3',
    multiply_owner='6d96778399dd72ee597cde11ee8fcda6d207a5053c8209f743dbf1308e529ea6',
    multiply_original='f47bd76b4bbd945213021c4ddece59c396b1805872d66461343f6e0688ff5302',
    frustum_owner='eb3b52178dea347045168a4d261d95b830cad348dae3afa7f298500eed4dfc0c',
    frustum_original='7bb5a42cff83525d209676e0ad4c89684bf121f9b9968a06c70c83e3353925cb')
DECLARATIONS='''extern f32 D_800D9D10[][4][4];
void func_150A7A48(f32 left[4][4], f32 right[4][4], f32 product[4][4]);
void func_1501B22C(s32 index);
'''
BODY='''/* Combine each view's live fixed matrix pair and refresh its side planes. */
void func_1510B690(void) {
    f32 projection[4][4];
    s16 index;

    for (index = 0; index <= D_80082FA0; index++) {
        guMtxL2F(projection, (Mtx *)(D_800BE628 + index * 0x180 +
            D_800BE9C0 * 0x40 + 0x100));
        guMtxL2F((f32 (*)[4])(D_800D9C10 + index * 0x40),
            (Mtx *)(D_800DC2A0[D_800BE9C0] + index * 0x40));
        func_150A7A48((f32 (*)[4])(D_800D9C10 + index * 0x40),
            projection, D_800D9D10[index]);
        func_1501B22C(index);
    }
}
'''
BASE_BODY=BODY
BODY=BODY.replace('    f32 projection[4][4];','    f32 (*products)[4][4] = D_800D9D10;\n    f32 projection[4][4];').replace(
    'D_800D9D10[index]','products[index]').replace('index * 0x180','(index * 4 - index) * 0x80').replace(
    '(Mtx *)(D_800DC2A0[D_800BE9C0] + index * 0x40)','((Mtx *)D_800DC2A0[D_800BE9C0]) + index')
GUARDS=((0x68,0x8EA80000,0x8EAF0000),(0x6C,0x928A0000,0x92880000),
    (0x70,0x00107880,0x0010C080),(0x74,0x01F0C023,0x0310C023),
    (0x78,0x0018C9C0,0x0018C1C0),(0x7C,0x03284821,0x01F8C821),
    (0x80,0x000A5980,0x00084980),(0x84,0x012B2821,0x03292821),
    (0x94,0x928C0000,0x928A0000),(0xA0,0x000C6880,0x000A5880),
    (0xA4,0x02ED7021,0x02EB6021),(0xA8,0x8DCF0000,0x8D8D0000),
    (0xAC,0x0010C180,0x00107180),(0xB8,0x01F82821,0x01AE2821),
    (0xD4,0x3C0A0000,0x3C080000),(0xD8,0x8D4A0000,0x8D080000),
    (0xE0,0x0010CC00,0x00107C00),(0xE4,0x00198403,0x000F8403),
    (0xE8,0x0150082A,0x0110082A),(0xF0,0x8EA80000,0x8EAF0000))
GUARD_ROWS=''.join('%s,%s,0x%X,0x%08X,0x%08X,%s,%s,Preserve closed per-view matrix-pass temporary allocation,,,false\n'%
    (OWNER,FUNCTION,offset,expected,replacement,
     'R_MIPS_HI16:D_80082FA0' if offset==0xD4 else 'R_MIPS_LO16:D_80082FA0' if offset==0xD8 else '-',
     'R_MIPS_HI16:D_80082FA0' if offset==0xD4 else 'R_MIPS_LO16:D_80082FA0' if offset==0xD8 else '-')
    for offset,expected,replacement in GUARDS)
MULTIPLY, MULTIPLY_ENTRY, MULTIPLY_ROM, MULTIPLY_WORDS='func_150A7A48',0x150A7A48,0xD4EF8,78
ASSEMBLY='conker/asm/nonmatchings/generated_D4E10/func_150A7A48.s'


def guard_manifest(before):
    assert before.endswith(b'\n') and (','+FUNCTION+',').encode() not in before
    return before+GUARD_ROWS.encode()


def restored_multiply_owner(before):
    lo,hi=build.function_span(before,MULTIPLY)
    return before[:lo]+'/* Original four-row product kernel, caching the complete right operand. */\n'+\
        '#pragma GLOBAL_ASM("'+ASSEMBLY.removeprefix('conker/')+'")'+before[hi:]


def restored_multiply_assembly(original):
    block=original.split('glabel '+MULTIPLY,1)[1]
    body,tail=block.split('endlabel '+MULTIPLY,1)
    padding=[line for line in tail.splitlines() if line.strip()]
    assert len(padding)==2 and all('00000000' in line and 'nop' in line for line in padding)
    return '/* Original cached-right-operand matrix product; preserve row-wise read/write order. */\n'+\
        'glabel '+MULTIPLY+body+'\n'.join(padding)+'\nendlabel '+MULTIPLY+'\n'


def expected_progress(before):
    wanted=['us','game','generated_D4E10',MULTIPLY,'353008200','312','c']
    lines=before.splitlines(keepends=True)
    reader=csv.reader(io.StringIO(before.decode(),newline=''))
    chunks,cursor,changed=[],0,0
    for row in reader:
        end=reader.line_num
        record=b''.join(lines[cursor:end])
        if row[:4]==wanted[:4]:
            if row!=wanted:
                raise ValueError('Unexpected matrix product progress row')
            ending='\r\n' if record.endswith(b'\r\n') else '\n' if record.endswith(b'\n') else ''
            output=io.StringIO(newline='')
            csv.writer(output,lineterminator=ending).writerow(row[:-1]+['asm'])
            record,changed=output.getvalue().encode(),changed+1
        chunks.append(record)
        cursor=end
    if changed!=1 or cursor!=len(lines):
        raise ValueError('Unexpected matrix product progress row')
    return b''.join(chunks)


def recover(before,body=BODY):
    lo,hi=build.function_span(before,FUNCTION)
    result=before[:lo]+body.rstrip()+before[hi:]
    return result.replace('extern u8 D_800D9B90[], D_800D9BD0[], D_800D9C10[];\n',
        'extern u8 D_800D9B90[], D_800D9BD0[], D_800D9C10[];\n'+DECLARATIONS,1)


def freeze(root,out):
    out.mkdir(exist_ok=True)
    manifest=out/'baseline.json'
    if not manifest.exists():
        data={key:(root/path).read_bytes() for key,path in PATHS.items()}
        if {key:hashlib.sha256(value).hexdigest() for key,value in data.items()}!=BASELINE:
            raise ValueError('Changed view matrix pass baseline')
        for key,value in data.items():
            (out/('before-'+key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE,indent=2)+'\n')
    if json.loads(manifest.read_text())!=BASELINE:
        raise ValueError('Modified view matrix pass manifest')
    for key,digest in BASELINE.items():
        if hashlib.sha256((out/('before-'+key)).read_bytes()).hexdigest()!=digest:
            raise ValueError('Modified immutable view matrix pass input: '+key)


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    freeze(root,out)
    retail=struct.unpack_from('>73I',(root/'conker/conker.us.bin').read_bytes(),ROM)
    records=[]
    for label,body in variants():
        obj,diagnostics=build.compile_owner(root,out,recover((out/'before-owner').read_text(),body),label)
        data,functions=build.link_owner(root,out,obj,OWNER)
        info=functions[FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        row=dict(label=label,bytes=info['size'],frame=-words[0]&65535,diagnostics=diagnostics,
            word_length_difference=len(words)-73,
            differences=[(i,hex(a),hex(b)) for i,(a,b) in enumerate(zip(words,retail)) if a!=b])
        records.append(row)
        print(label,row['bytes'],row['frame'],len(row['differences']),diagnostics,flush=True)
    (out/'screens.json').write_text(json.dumps(records,indent=2)+'\n')


def variants():
    yield 'direct',BASE_BODY
    for base in ('typed','bytes'):
        for before in (False,True):
            for stride in (False,True):
                for captured in (False,True):
                    declaration='    f32 (*products)[4][4] = D_800D9D10;\n' if base=='typed' else '    u8 *products = (u8 *)D_800D9D10;\n'
                    body=BASE_BODY.replace('    f32 projection[4][4];',declaration+'    f32 projection[4][4];' if before else '    f32 projection[4][4];\n'+declaration.rstrip())
                    body=body.replace('D_800D9D10[index]', 'products[index]' if base=='typed' else '(f32 (*)[4])(products + index * 0x40)')
                    if stride:
                        body=body.replace('index * 0x180','(index * 4 - index) * 0x80')
                    if captured:
                        body=body.replace('    s16 index;','    s16 index;\n    s32 offset;').replace(
                            '        guMtxL2F((f32', '        offset = index * 0x40;\n        guMtxL2F((f32').replace('index * 0x40','offset')
                        body=body.replace('offset = offset;','offset = index * 0x40;')
                    yield '%s-first%d-stride%d-offset%d'%(base,before,stride,captured),body
    base=BASE_BODY.replace('    f32 projection[4][4];','    f32 (*products)[4][4] = D_800D9D10;\n    f32 projection[4][4];').replace(
        'D_800D9D10[index]','products[index]').replace('index * 0x180','(index * 4 - index) * 0x80')
    for fixed in ('array','pointer'):
        for temporary in ('first','last'):
            for convert in ('s16','s32'):
                body=base
                if fixed=='array':
                    body=body.replace('(Mtx *)(D_800DC2A0[D_800BE9C0] + index * 0x40)', '((Mtx *)D_800DC2A0[D_800BE9C0]) + index')
                if temporary=='last':
                    body=body.replace('    f32 projection[4][4];\n    s16 index;','    s16 index;\n    f32 projection[4][4];')
                if convert=='s32':
                    body=body.replace('((Mtx *)D_800DC2A0[D_800BE9C0]) + index','((Mtx *)D_800DC2A0[D_800BE9C0]) + (s32)index')
                yield 'typed-fixed-%s-temporary-%s-%s'%(fixed,temporary,convert),body


if __name__=='__main__':
    main()
