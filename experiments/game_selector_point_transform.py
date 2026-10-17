"""Recover the byte-selector point transform against its preserved retail table."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_fixed_sine_update as previous
from tools.tests import fixed_sine_update_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-selector-point-transform'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11F780','func_150F22D0',0x150F22D0,0x11F780,172
TABLE,TABLE_SYMBOL,VECTOR=0x800A192C,'jtbl_800A192C',0x800A1920
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE)
changed={previous.PATHS[k]:v for k,v in checkpoint.AFTER.items()}
for key,path in PATHS.items():
    if path in changed:BASELINE[key]=changed[path]
for key,path,sha in (
    ('selector_data','conker/asm/data/2463E0.rodata.s','887a53cf3e58dc7d731ed4fba066686f1c28013da06c23d51de6f2317a63193a'),
    ('selector_helper','conker/asm/nonmatchings/game_16EE20/func_15143134.s','6279833e1ee189fdaabd7b639d051c5301b6ba953bcf4185ad91769fd573390a'),
    ('selector_math_tests','tools/tests/test_game_point_transform_match.py','19773668004893fc2af398a3f529f0268f3f0cb52adc42a320f30acce5663d45'),
    ('fixed_checkpoint','tools/tests/fixed_sine_update_checkpoint.py','87762c4875ec20acb12285eb4e9b62d19ff0256f43bea3079ad3a1faffb8f7ee'),
    ('fixed_tests','tools/tests/test_game_fixed_sine_update.py','39321df77e1c65398dcc5d89b4b6185526be32d594b40ae9f37ce398e3d02dad')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='extern f32 D_800A1920[3];\nvoid func_15143134(f32 *point, f32 *output, u8 *matrix);\n'
SELECTED='''/* Transform the selector's indexed actor record into the output point. */
s32 func_150F22D0(struct17 *output, u8 *actor, u8 selector) {
    s32 index;

    switch (selector) {
        case 3: index = 0x29; break;
        case 4: index = 0x2D; break;
        case 5: index = 0x31; break;
        case 6: index = 0x35; break;
        case 7: index = 0x39; break;
        case 8: index = 0x3D; break;
        default: return 0;
    }
    func_15143134(D_800A1920, (f32 *)output,
                 *(u8 **)(actor + 0x1D4) + (index << 6));
    return 1;
}'''
RAW_SHA='b7973680cb92b0e72b3306628475d4d27ac3b933da49d59d6a26952e9231c379'
BINDINGS={44:[('R_MIPS_HI16','.rodata')],52:[('R_MIPS_LO16','.rodata')],
    124:[('R_MIPS_HI16','D_800A1920')],136:[('R_MIPS_LO16','D_800A1920')],
    144:[('R_MIPS_26','func_15143134')]}
TABLE_OFFSETS=tuple(range(0x40,0x69,8))


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import selector_point_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed selector-point live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed selector-point frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION);anchor='extern u8 D_800BE9C0;'
    if before[lo:hi]!='s32 func_150F22D0() {\n    return 0;\n}' or before.count(anchor)!=1:
        raise ValueError('Unknown selector-point predecessor')
    return (before[:lo]+body+before[hi:]).replace(anchor,anchor+'\n'+TYPE,1)


def recovered_makefile(before):
    anchor='$(BUILD_DIR)/$(SRC_DIR)/game/generated_1AC2F0.c.o: RETAIL_RODATA_SYMBOL := D_800A7280\n'
    if before.count(anchor)!=1 or 'generated_11F780.c.o: RETAIL_RODATA_SYMBOL' in before:
        raise ValueError('Unknown selector-point rodata predecessor')
    return before.replace(anchor,anchor+
        '# Selector point transform uses its preserved six-way retail jump table.\n'
        '$(BUILD_DIR)/$(SRC_DIR)/game/generated_11F780.c.o: RETAIL_RODATA_SYMBOL := jtbl_800A192C\n'
        '$(BUILD_DIR)/$(SRC_DIR)/game/generated_11F780.c.o: Makefile\n',1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete selector-point words/bindings')


def checked_pool(obj):
    wanted=(bytes(32),tuple((i*4,FUNCTION,at) for i,at in enumerate(TABLE_OFFSETS)))
    if normalized_pools(obj)['.rodata']!=wanted:raise ValueError('Changed selector-point jump table/padding/relocations')


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-phase_original',word_patches_path=out/'before-guards',
        filename=OWNER,rodata_symbol=TABLE_SYMBOL)
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def raw_object(root,out,obj,label):
    data,fs,rs=parse_object(obj)
    rs={at:[(kind,TABLE_SYMBOL if name=='.rodata' else name) for kind,name in rows] for at,rows in rs.items()}
    text,unknown=emit_function(data,fs[FUNCTION],rs,FUNCTION,
        {TABLE_SYMBOL:TABLE,'D_800A1920':VECTOR,'func_15143134':0x15143134})
    if unknown:raise ValueError('Unknown selector-point raw binding '+repr(unknown))
    asm=out/(label+'-raw.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-fixed_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Selector-point compiler diagnostics')
    checked_parts(*parts(obj));checked_pool(obj)
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items()
        if n.startswith(('.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj) or '.rodata' in projection.sections(old):
        raise ValueError('Unexpected selector-point owner pool predecessor')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Selector-point padded neighbors changed')
    rom=(out/'before-retail_rom').read_bytes()
    if rom[0x2463EC:0x246410]!=struct.pack('>9I',*(ENTRY+at for at in TABLE_OFFSETS),0,0,0):
        raise ValueError('Changed preserved selector-point retail table')
    if rom[0x2463E0:0x2463EC]!=struct.pack('>3I',0,0xC2340000,0):
        raise ValueError('Changed selector-point template')
    images=[]
    for path in (raw_object(root,out,obj,'candidate'),padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>43I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>43I',rom,ROM))
    if images!=[truth,truth]:raise ValueError('Incomplete direct selector-point match')
    row=dict(words=43,frame=24,bindings=5,new_guards=0,raw_differences=0,
        unchanged_raw_padded_neighbors=neighbors,compact_pool_bytes=32,retail_table_bytes=36,
        table_entries=6,preserved_table_binding=TABLE_SYMBOL,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
