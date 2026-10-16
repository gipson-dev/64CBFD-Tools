"""Restore the frame-step divider, phase byte and ten-sample timing history."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_overlay_match as previous
from tools.tests import view_overlay_match_checkpoint as checkpoint
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-frame-timing-update'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_45B80','func_15019F20',0x15019F20,0x473D0,192
PATHS=dict(previous.PATHS,timing_assembly='conker/asm/nonmatchings/game_45B80/func_15019F20.s',
    timing_constant_assembly='conker/asm/data/23B390.rodata.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    timing_assembly='1e6578219eb40f8e7c8281fe2ebc37f1592da2a195d05e9a99e10a45acd9f13d',
    timing_constant_assembly='650cf91f08b5a6ec5ed518eccab844bb7a9859a858943c69e4d825dbff925adf')
build=previous.build
DECLARATIONS='''/* Frame-step history, counters and the existing retail mean-factor label. */
extern u8 D_800BEA0C, D_800BE619, D_800BE61A;
extern u32 D_800BE610;
extern s32 D_800BE9AC, D_800BE9B0;
extern f32 D_800BE5E8[], D_800BE9B8, D_800BE9BC;
extern const f32 D_800968D0;

'''
INITIAL='''/* Update frame steps, alternating phase and the ten-sample timing mean. */
void func_15019F20(void) {
    u32 divisor;
    u32 total;
    f32 sum;
    s32 i;

    divisor = D_800BEA0C;
    D_800BEA08 = D_800BE9E4;
    if (divisor != 0) {
        if (divisor == 1) {
            D_800BE9E4 = 0;
            D_800BE5E0 = 0;
            D_800BE9A4 = 0.0f;
        } else {
            total = D_800BE610 + (u32)D_800BE9E4;
            D_800BE9A4 = (f32)D_800BE9E4 / (f32)divisor;
            D_800BE9E4 = (s32)D_800BE9A4;
            D_800BE9A4 *= 0.5f;
            if (total >= divisor) {
                D_800BE9E4 = total / divisor;
                /* Retail multiplies by total here, not by the divisor. */
                D_800BE610 = total - ((u32)D_800BE9E4 * total);
            } else {
                D_800BE610 = total;
                D_800BE9E4 = 0;
            }
        }
    } else {
        D_800BE9A4 = (f32)D_800BE9E4 * 0.5f;
    }
    D_800BE5E0 &= 1;
    D_800BE5E0 += D_800BE9E4;
    D_800BE9A0 = D_800BE5E0 >> 1;
    if (D_800BE9A4 != 0.0f) {
        D_800BE9A8 = 1.0f / D_800BE9A4;
    } else {
        D_800BE9A4 = 0.0f;
        D_800BE9A8 = 0.0f;
    }
    D_800BE9AC = (s32)((u32)D_800BE9AC + (u32)D_800BE9E4);
    D_800BE9B0 = D_800BE9AC % 30;
    D_800BE5E8[D_800BE619] = D_800BE9A4;
    D_800BE619++;
    if (D_800BE619 == 10) {
        D_800BE619 = 0;
    }
    if (D_800BE61A < 10) {
        D_800BE61A++;
        D_800BE9B8 = D_800BE9A4;
        D_800BE9BC = D_800BE9A8;
    } else {
        sum = 0.0f;
        for (i = 0; i < 10; i++) {
            sum += D_800BE5E8[i];
        }
        D_800BE9B8 = sum * D_800968D0;
        if (D_800BE9B8 != 0.0f) {
            D_800BE9BC = 1.0f / D_800BE9B8;
        } else {
            D_800BE9BC = 0.0f;
        }
    }
    func_150A019C();
}'''


def forms():
    cached=INITIAL.replace('    u32 divisor;','    u8 historyIndex;\n    u32 divisor;').replace(
        '    D_800BE5E8[D_800BE619] = D_800BE9A4;\n    D_800BE619++;',
        '    historyIndex = D_800BE619;\n    D_800BE5E8[historyIndex] = D_800BE9A4;\n    D_800BE619 = historyIndex + 1;')
    for label,body in (('cached-ring',cached),('initial',INITIAL)):
        yield label,body,DECLARATIONS
        unsigned=body.replace('D_800BE9B0 = D_800BE9AC % 30;','D_800BE9B0 = (s32)D_800BE9AC % 30;').replace(
            'D_800BE9AC = (s32)((u32)D_800BE9AC + (u32)D_800BE9E4);','D_800BE9AC += D_800BE9E4;')
        decl=DECLARATIONS.replace('extern s32 D_800BE9AC, D_800BE9B0;','extern u32 D_800BE9AC;\nextern s32 D_800BE9B0;')
        yield label+'-word-counter',unsigned,decl
        yield label+'-bounded-history',unsigned,decl.replace('D_800BE5E8[]','D_800BE5E8[256]')
        global_divisor=unsigned.replace('    u32 divisor;\n','').replace('    divisor = D_800BEA0C;\n','')
        global_divisor=global_divisor.replace('divisor != 0','D_800BEA0C != 0').replace(
            'divisor == 1','D_800BEA0C == 1').replace('(f32)divisor','(f32)(u32)D_800BEA0C').replace(
            'total >= divisor','total >= (u32)D_800BEA0C').replace('total / divisor','total / (u32)D_800BEA0C')
        yield label+'-live-divisor',global_divisor,decl


def arithmetic_forms():
    body=dict((n,(b,d)) for n,b,d in forms())['cached-ring-word-counter'][0]
    decl=dict((n,(b,d)) for n,b,d in forms())['cached-ring-word-counter'][1]
    for unsigned in (False,True):
        candidate=body.replace('D_800BE5E0 += D_800BE9E4;','D_800BE5E0 += (u32)D_800BE9E4;') if unsigned else body
        for comparison in ('integer-zero','truth'):
            if comparison=='integer-zero':changed=candidate.replace('!= 0.0f','!= 0')
            else:changed=candidate.replace('D_800BE9A4 != 0.0f','D_800BE9A4').replace('D_800BE9B8 != 0.0f','D_800BE9B8')
            yield ('unsigned-phase-' if unsigned else 'signed-phase-')+comparison,changed,decl


def lifetime_forms():
    cached=dict((n,(b,d)) for n,b,d in forms())['cached-ring'][0]
    signed=cached.replace('D_800BE9AC = (s32)((u32)D_800BE9AC + (u32)D_800BE9E4);','D_800BE9AC += D_800BE9E4;').replace('!= 0.0f','!= 0')
    for name,body in (('signed-counter',signed),('signed-total',signed.replace('    u32 total;','    s32 total;').replace(
            'total = D_800BE610 + (u32)D_800BE9E4;','total = (s32)(D_800BE610 + (u32)D_800BE9E4);').replace(
            'total >= divisor','(u32)total >= divisor').replace('total / divisor','(u32)total / divisor').replace(
            'total - ((u32)D_800BE9E4 * total)','(u32)total - ((u32)D_800BE9E4 * (u32)total)'))):
        yield name,body,DECLARATIONS
        direct=body.replace('    u32 divisor;\n','').replace('    divisor = D_800BEA0C;\n','').replace(
            'divisor != 0','D_800BEA0C != 0').replace('divisor == 1','D_800BEA0C == 1').replace(
            '(f32)divisor','(f32)(u32)D_800BEA0C').replace('>= divisor','>= (u32)D_800BEA0C').replace('/ divisor','/ (u32)D_800BEA0C')
        yield name+'-global-divisor',direct,DECLARATIONS
        for label,base in (('local-divisor',body),('global-divisor',direct)):
            local=base.replace('    u32 total;','    s32 ticks;\n    u32 total;').replace('    s32 total;','    s32 ticks;\n    s32 total;')
            local=local.replace('    D_800BEA08 = D_800BE9E4;','    ticks = D_800BE9E4;\n    D_800BEA08 = ticks;')
            local=local.replace('D_800BE9E4 = 0;','D_800BE9E4 = ticks = 0;').replace('D_800BE9E4 = (s32)D_800BE9A4;','D_800BE9E4 = ticks = (s32)D_800BE9A4;')
            local=local.replace('D_800BE9E4 = total /','D_800BE9E4 = ticks = total /').replace('D_800BE9E4 = (u32)total /','D_800BE9E4 = ticks = (u32)total /')
            for old,new in (('(u32)D_800BE9E4','(u32)ticks'),('(f32)D_800BE9E4','(f32)ticks'),('+= D_800BE9E4;','+= ticks;')):local=local.replace(old,new)
            yield name+'-cached-ticks-'+label,local,DECLARATIONS


def divisor_forms():
    body=dict((n,(b,d)) for n,b,d in lifetime_forms())['signed-counter'][0]
    for ty in ('s32','u8','s16','int'):
        candidate=body.replace('u32 divisor;',ty+' divisor;').replace('(f32)divisor','(f32)(u32)divisor')
        for signed in (False,True):
            decl=DECLARATIONS.replace('extern u32 D_800BE610;','extern s32 D_800BE610;') if signed else DECLARATIONS
            yield 'divisor-'+ty+('-signed-remainder' if signed else ''),candidate,decl


def byte_divisor_forms():
    body,decl=dict((n,(b,d)) for n,b,d in arithmetic_forms())['unsigned-phase-integer-zero']
    for ty in ('u8','s16'):
        candidate=body.replace('u32 divisor;',ty+' divisor;').replace('(f32)divisor','(f32)(u32)divisor')
        yield 'wrapped-byte-divisor-'+ty,candidate,decl


SELECTED,SELECTED_DECLARATIONS=dict((n,(b,d)) for n,b,d in byte_divisor_forms())['wrapped-byte-divisor-u8']


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    with patch.multiple(previous.previous.engine,PATHS=PATHS,BASELINE=BASELINE):previous.previous.engine.freeze(root,out)


def recovered_owner(before,body=None,declarations=None):
    body=SELECTED if body is None else body
    declarations=SELECTED_DECLARATIONS if declarations is None else declarations
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15019F20() {\n    return 0;\n}':raise ValueError('Unknown frame-timing predecessor')
    result=before[:lo]+body+before[hi:]
    for old,new in (('/* Non-matching C placeholders for asm/nonmatchings/game_45B80/func_15019F20.s. */\n',''),
            ('s32 func_15019F20();','void func_15019F20(void);'),
            ('/* Generated placeholder declarations. */',declarations+'/* Generated placeholder declarations. */')):
        if result.count(old)!=1:raise ValueError('Unknown frame-timing interface/declarations')
        result=result.replace(old,new,1)
    return result


def measure(root,out,label='selected',body=None,declarations=None,flags=('-O2','-g3')):
    freeze(root,out);content=recovered_owner((out/'before-dispatch_owner').read_text(),body,declarations)
    obj,diag=build.compile_owner(root,out,content,label,flags)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    data,placed=build.link_owner(root,out,obj,OWNER)
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth=struct.unpack_from('>192I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-192),diagnostics=diag,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in previous.previous.sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


RAW_SHA256='63fa053a2cb82cc69b8870e51fdf741b7816b2568aac8ea9cab272649282e67a'
BINDING_SHA256='38cd139a2af2f0f712ba1d90160dc9002248c08a61e94fb6d52255345d7aa0c7'
STRUCTURAL_SHA256='fa48acc7665ba6d768f591f5c1a8a4823a0351665cda2517f8c6cc9fd4f65657'
SERIALIZATION=(
    (('D_800BE9BC','D_800BE5EC','D_800A2FD8'),(1,2,0),
        ((0x800BE9BC,0,16,0,65521),(0x800BE5EC,0,16,0,65521),(0x800A2FD8,0,16,0,65521))),
    (('D_800BE619','.L15098F6C_game_data','func_151279A0'),(1,2,0),
        ((0x800BE619,0,16,0,65521),(0x15098F6C,0,16,0,5),(0x151279A0,1304,18,0,5))),
    (('D_800BE9B0','D_800BE5E0'),(1,0),((0x800BE9B0,0,16,0,65521),(0x800BE5E0,0,16,0,65521))),
    (('D_800DBE30','D_80089730'),(1,0),((0x800DBE30,0,16,0,65521),(0x80089730,0,16,0,6))),
    (('osPiGetCmdQueue','D_800AA98C','D_800895B0'),(2,0,1),
        ((0x100275F0,40,18,0,3),(0x800AA98C,0,16,0,65521),(0x800895B0,0,16,0,65521))),
    (('D_800C3D60','D_8003C900'),(1,0),((0x800C3D60,0,16,0,65521),(0x8003C900,0,16,0,65521))))


def serialize_metadata(data):
    from tools.tests import test_game_actor_burst_packet_match as symbols
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols
    if hashlib.sha256(data).hexdigest()!=STRUCTURAL_SHA256:raise ValueError('Unknown frame-timing structural prediction')
    result=bytearray(data)
    with patch.object(symbols,'SERIALIZATION',SERIALIZATION):symbols.apply_burst_symbol_serialization(result)
    if canonical_symbols(result)!=canonical_symbols(data) or sum(a!=b for a,b in zip(data,result))!=173:
        raise ValueError('Changed frame-timing metadata serialization')
    return bytes(result)


def checked_object(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']}
    binding_hash=hashlib.sha256(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    pools={n:d for n,(_,d) in previous.previous.sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=764 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or len(bindings)!=59 or binding_hash!=BINDING_SHA256 or pools:
        raise ValueError('Unknown frame-timing object/bindings/pools')
    return list(struct.unpack('>191I',raw)),bindings


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified');checked_object(obj)
    before=(out/'before-dispatch_owner').read_text()
    baseline,diag=build.compile_owner(root,out,before,'neighbor-before')
    if previous.previous.warning_sites(before,diag)!=previous.previous.warning_sites(recovered_owner(before),row['diagnostics']):
        raise ValueError('Changed frame-timing diagnostics')
    old,new=parse_object(baseline),parse_object(obj)
    bindings=lambda p,f:{a-f['value']:v for a,v in p[2].items() if f['value']<=a<f['value']+f['size']}
    if set(old[1])!=set(new[1]):raise ValueError('Changed frame-timing owner function set')
    for name,f in old[1].items():
        if name==FUNCTION:continue
        g=new[1][name]
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or bindings(old,f)!=bindings(new,g):
            raise ValueError('Changed frame-timing neighbor: '+name)
    path=out/'qualified-padded.s'
    path.write_text(previous.previous.pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,
        word_patches_path=out/'before-guards'))
    padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    slot=data[f['value']:f['value']+768]
    if f['size']!=764 or slot!=struct.pack('>191I',*words)+bytes(4):raise ValueError('Unexpected frame-timing padding/extent')
    truth=(out/'before-retail_rom').read_bytes()[ROM:ROM+768]
    row=dict(row,slot_words=192,body_words=191,byte_exact=slot==truth,
        real_word_differences=sum(slot[i:i+4]!=truth[i:i+4] for i in range(0,768,4)),
        slot_sha256=hashlib.sha256(slot).hexdigest(),new_guards=0,unchanged_neighbors=15)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,words,row


def expected_inputs(root,out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before=(out/'before-elf').read_bytes();slot=(out/'predicted-slot.bin').read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf'] or len(slot)!=768:raise ValueError('Changed frame-timing prediction')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12):raise ValueError('Unknown frame-timing predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,ENTRY,768);data[at:at+768]=slot
    struct.pack_into('>I',data,row[0]+8,764)
    return dict(elf=serialize_metadata(bytes(data)),dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text()).encode())


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out);capture=out/'link-inputs.json'
    live=lambda:{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}
    if not capture.exists():
        if live()!=BASELINE:raise ValueError('Frame-timing link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'),('before-owner.o','conker/build/src/'+OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed frame-timing link capture')
    link=(out/'before-linkscript').read_text();needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Unknown frame-timing link selector')
    for name,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=out/(name+'.ld');script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result=subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+name+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():raise ValueError('Frame-timing predecessor not reproduced')
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+768];target=out/'predicted-slot.bin'
    if not target.exists():target.write_bytes(slot)
    if target.read_bytes()!=slot:raise ValueError('Changed first frame-timing slot')
    expected=expected_inputs(root,out);predicted=(out/'prelink-prediction.elf').read_bytes()
    if predicted!=expected['elf']:raise ValueError('Frame-timing link differs outside slot/extent')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()};initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=BASELINE:raise ValueError('Frame-timing prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first frame-timing prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),predicted)),
        body_bytes=764,slot_bytes=768,new_guards=0,metadata_exclusions=0,metadata_serialization_bytes=173)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true');parser.add_argument('--arithmetic',action='store_true');parser.add_argument('--lifetimes',action='store_true');parser.add_argument('--divisors',action='store_true');parser.add_argument('--byte-divisors',action='store_true');parser.add_argument('--prelink',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.prelink:print(json.dumps(prelink_prediction(root,root/BUILD),indent=2));raise SystemExit(0)
    for label,body,decl in (byte_divisor_forms() if args.byte_divisors else divisor_forms() if args.divisors else lifetime_forms() if args.lifetimes else arithmetic_forms() if args.arithmetic else forms() if args.screens else [('selected',SELECTED,SELECTED_DECLARATIONS)]):
        row=measure(root,root/BUILD,label,body,decl)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256','pools')}),flush=True)
