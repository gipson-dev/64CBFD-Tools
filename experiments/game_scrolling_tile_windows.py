"""Recover the paired scrolling tile-size commands directly from SDK C."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_overlay_fade_packet as previous
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-scrolling-tile-windows'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_FC5F0', 'func_150CF5E8', 0x150CF5E8, 0xFCA98, 38
SIZE = WORDS*4
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE)
EXTRA = {
    'tile_owner':('conker/src/game/generated_FC5F0.c','82ee02770b155e52b703516ce79fad035fd24d14ad3478068a8d39d85f679c5f'),
    'tile_original':('conker/asm/FC5F0.s','dc18e10eb1b01e036532701be7ba18b21c811da6c6d49cfe926b83931004e2a9'),
    'tile_caller_a':('conker/asm/138520.s','ad0efe574a623e2a2a9ef2446c7536d7ccf35a12d90388c7cf60aa947e519761'),
    'tile_caller_b':('conker/asm/13D350.s','aae655875cae186bc7377f14463dc61e80cb55f511b1931a0ed03d1308333a2c'),
    'tile_caller_a_C':('conker/src/game/generated_138520.c','4296bc1df7c67483fc8cdb6dab3704b722b25cc395e7a2bffd990a1d4d4b47c1'),
    'tile_caller_b_C':('conker/src/game/generated_13D350.c','68d7d45a9b71049426ee12b4af3af36c7c7d455fb42bac2979e857eacc71fd89'),
}
for key,(path,sha) in EXTRA.items():
    PATHS[key],BASELINE[key] = path,sha
build,compile_owner,projection = previous.build,previous.compile_owner,previous.projection
SELECTED = '''/* Publish the two scrolling texture-tile windows. */
Gfx *func_150CF5E8(Gfx *commands) {
    gDPSetTileSize(commands++, 0, D_80088890 >> 7, D_80088894 >> 7, 0x47E, 0x47E);
    gDPSetTileSize(commands++, 1, D_80088898 >> 7, D_8008889C >> 7, 0x47E, 0x47E);
    return commands;
}'''
RAW_SHA = '5e376248f17483071efebaf43bfbc4ceb287b94da2fe4aace524549da1005da0'
BINDINGS = {at:[(kind,name)] for name,hi,lo in (
    ('D_80088890',4,8),('D_80088894',12,16),('D_80088898',72,76),('D_8008889C',80,84))
    for at,kind in ((hi,'R_MIPS_HI16'),(lo,'R_MIPS_LO16'))}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data = (root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import scrolling_tile_checkpoint as installed
            data = installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            raise ValueError('Unknown scrolling tile input: '+key)
        target = out/('before-'+key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes()!=data:
            raise ValueError('Changed scrolling tile fixture: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi = build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150CF5E8() {\n    return 0;\n}' or before.count('extern s32 D_80088898;\n')!=1:
        raise ValueError('Unknown scrolling tile placeholder')
    return (before[:lo]+body+before[hi:]).replace('extern s32 D_80088898;\n',
        'extern s32 D_80088898;\nextern s32 D_8008889C;\n',1)


def parts(obj):
    data,functions,relocations = parse_object(obj)
    f = functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete scrolling tile words/bindings')


def padded_object(root,out,obj,label):
    text = emit_padded_assembly(obj,out/'before-tile_original',word_patches_path=out/'before-guards',filename=OWNER)
    path = out/(label+'-padded.s'); path.write_text(text)
    target = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out)
    before = (out/'before-tile_owner').read_text()
    obj,diag = compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag = compile_owner(root,out,before,'owner-before')
    if diag or old_diag:
        raise ValueError('Scrolling tile compiler diagnostics')
    checked_parts(*parts(obj))
    pools = lambda p:{n:d for n,(_,d) in projection.sections(p).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):
        raise ValueError('Scrolling tile owner pools changed')
    neighbors = same_functions(old,obj,(FUNCTION,))
    padded,old_padded = padded_object(root,out,obj,'candidate'),padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:
        raise ValueError('Scrolling tile padded neighbors changed')
    images = []
    truth = list(struct.unpack_from('>38I',(out/'before-retail_rom').read_bytes(),ROM))
    for p in (obj,padded):
        data,functions = build.link_owner(root,out,p,OWNER); f=functions[FUNCTION]
        words = list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
        if words!=truth:
            raise ValueError('Scrolling tile does not emit all 38 original words')
        images.append(words)
    row = dict(words=38,frame=0,bindings=8,new_guards=0,unchanged_raw_padded_neighbors=neighbors)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
