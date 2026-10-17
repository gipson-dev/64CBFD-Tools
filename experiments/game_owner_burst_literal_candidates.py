"""Bind the burst scale's real literal section and screen complete source forms."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_owner_burst_emitter as source
from tools.experiments import game_owner_burst_storage_candidates as storage
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.alternative_source_draft_word_screen import nm_anchors

BUILD='conker/build/game-owner-burst-literal-candidates'
POOL_ADDRESS=0x800A196C
POOL_ROM=0x24642C


def forms():
    _,body,types=next(storage.forms())
    body=body.replace('    f32 multiplier;\n','').replace('                multiplier = D_800A196C;\n','').replace(
        'payload.multiplier = multiplier;','payload.multiplier = 58.14f;')
    yield 'literal-scale',body,types
    reused=body.replace('    u8 *created;\n','').replace('created','actor').replace(
        '                    data->mode = (s8)data->mode - 1;',
        '                    actor = (u8 *)data - 0x28;\n                    data->mode = (s8)data->mode - 1;')
    yield 'literal-reuse-parameter',reused,types
    yield 'literal-owner',*storage.inline_owner(body,types)
    yield 'literal-copy',*storage.copy_phase(body,types)
    def direct(body,types):
        return body.replace('    Generated11FF10Payload *data;\n','').replace(
            '    data = (Generated11FF10Payload *)(actor + 0x28);\n    savedData = data;',
            '    savedData = (Generated11FF10Payload *)(actor + 0x28);').replace(
            'data->','((Generated11FF10Payload *)(actor + 0x28))->'),types
    yield 'literal-data',*direct(body,types)
    both=storage.copy_phase(*storage.inline_owner(body,types))
    yield 'literal-owner-copy',*both
    yield 'literal-no-scalar-homes',*direct(*both)
    yield 'literal-owner-state-first',body.replace('data->state != owner[0x222]',
        'owner[0x222] != data->state'),types
    merged=body.replace('    Generated11FF10Payload *data;\n','').replace(
        '    data = (Generated11FF10Payload *)(actor + 0x28);\n    savedData = data;',
        '    savedData = (Generated11FF10Payload *)(actor + 0x28);').replace('data->','savedData->')
    yield 'literal-merged-data',merged,types
    yield 'literal-merged-data-copy',*storage.copy_phase(merged,types)
    for first,second in (('created','owner'),('owner','created')):
        packed=merged.replace('    u8 *created;\n','').replace('    u8 *owner;\n','')
        packed=packed.replace('    BurstDescriptor2D14 request;',
            '    u8 *'+first+';\n    BurstDescriptor2D14 request;').replace(
            '    BurstInputPair2D14 inputs;','    u8 *'+second+';\n    BurstInputPair2D14 inputs;')
        yield 'literal-gap-'+first,packed,types


def pool_binding(root,out,obj):
    sections=source.projection.sections(obj)
    pool=sections.get('.rodata',(0,b''))[1]
    retail=(out/'before-retail_rom').read_bytes()[POOL_ROM:POOL_ROM+4]
    if pool!=retail+b'\0'*12 or retail.hex()!='42688f5c':raise ValueError('Changed burst scale pool')
    if nm_anchors(root/'conker/build/conker.us.elf').get('D_800A196C')!=POOL_ADDRESS:
        raise ValueError('Changed installed scale anchor')
    data,functions,relocations=source.parse_object(obj);function=functions[source.FUNCTION]
    references=[(offset,values) for offset,values in relocations.items() if any(s=='.rodata' for _,s in values)]
    references.sort()
    if (len(references)!=2 or [v for _,v in references]!=[
            [('R_MIPS_HI16','.rodata')],[('R_MIPS_LO16','.rodata')]]
            or not all(function['value']<=o<function['value']+function['size'] for o,_ in references)):
        raise ValueError('Ambiguous scale pool ownership')
    hi,lo=[struct.unpack_from('>I',data,o)[0] for o,_ in references]
    if (hi>>26!=15 or lo>>26!=49 or hi&65535 or lo&65535
            or (hi>>16&31)!=(lo>>21&31)):
        raise ValueError('Changed burst scale relocation addends/base')
    return pool,dict(address=POOL_ADDRESS,rom=POOL_ROM,value_hex=retail.hex(),
        target_relocations=[o-function['value'] for o,_ in references],live_bytes=4,
        compiler_terminal_alignment_bytes=12,addends=[0,0],existing_absolute_anchor=True)


def linked(root,out,obj,label,entry=source.ENTRY,symbols=None,pool_address=POOL_ADDRESS):
    pool,binding=pool_binding(root,out,obj)
    data,functions,relocations=source.parse_object(obj)
    anchors=source.SYMBOLS if symbols is None else symbols
    if pool_address!=anchors.get('D_800A196C') or pool_address%4:
        raise ValueError('Literal section must use the qualified scale binding')
    assembly,unknown=source.emit_function(data,functions[source.FUNCTION],relocations,source.FUNCTION,anchors)
    if unknown!=['.rodata']:raise ValueError('Unexpected burst literal binding '+repr(unknown))
    # Keep the actual section relocation and bytes; do not rewrite instruction words.
    assembly+='\n.section .rodata, "a"\n.balign 4\n.byte '+','.join(str(b) for b in pool)+'\n'
    stem=out/label;asm=stem.with_suffix('.s');compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
    asm.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(entry,pool_address))
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
        *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
    sections=source.projection.sections(elf)
    if sections['.rodata']!=(pool_address,pool):raise ValueError('Linked scale pool moved/changed')
    count=functions[source.FUNCTION]['size']//4
    return list(struct.unpack_from('>%dI'%count,sections['.text'][1])),binding


def measure(root,out,label,body,types):
    source.freeze(root,out);before=(out/'before-record_gate_owner').read_text()
    from unittest.mock import patch
    with patch.object(source,'TYPE',types):
        content=source.recovered_owner(before,body)
    obj,diagnostics=source.compile_owner(root,out,content,label)
    if diagnostics:raise ValueError('Burst literal compiler diagnostics '+repr(diagnostics))
    words,binding=linked(root,out,obj,label+'-linked')
    raw,bindings=source.parts(obj);truth=struct.unpack_from('>288I',(out/'before-retail_rom').read_bytes(),source.ROM)
    old,diagnostics=source.compile_owner(root,out,before,'owner-before')
    if diagnostics:raise ValueError('Changed burst owner baseline')
    neighbors=same_functions(old,obj,(source.FUNCTION,))
    row=dict(words=len(words),frame=(-words[0])&65535,differences=sum(a!=b for a,b in zip(words,truth)),
        extent_gap=len(words)-288,raw_sha=hashlib.sha256(raw).hexdigest(),literal_binding=binding,
        unchanged_raw_neighbors=neighbors,bindings=bindings,installed=False,matching_credit=0)
    (out/(label+'-audit.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def padded_object(root,out,obj,label,guards=None):
    pool_binding(root,out,obj)
    text=source.emit_padded_assembly(obj,out/'before-record_gate_original',filename=source.OWNER,
        word_patches_path=guards or out/'before-guards',rodata_symbol='D_800A196C')
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    label,body,types=next(forms());obj,words,row=measure(root,out,label,body,types)
    if (row['words'],row['frame'],row['differences'],row['raw_sha'])!=(288,352,75,
            'f472f48ab8ad06b0109311a5bc6c55fbe0c78907913b3e2329982db2179d794f'):
        raise ValueError('Changed burst literal candidate')
    padded=padded_object(root,out,obj,label)
    data,functions=source.build.link_owner(root,out,padded,source.OWNER)
    candidate=list(struct.unpack_from('>288I',data,functions[source.FUNCTION]['value']))
    if candidate!=words:raise ValueError('Literal pool padding changes target words')
    old,diagnostics=source.compile_owner(root,out,(out/'before-record_gate_owner').read_text(),'owner-before')
    if diagnostics:raise ValueError('Changed burst before owner')
    old_padded=source.padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(source.FUNCTION,))!=11:raise ValueError('Changed burst padded neighbors')
    before_pools=storage.normalized_pools(old);after_pools=storage.normalized_pools(obj)
    if before_pools['.rodata'] is not None or after_pools['.rodata']!=(bytes.fromhex('42688f5c')+b'\0'*12,()):
        raise ValueError('Unexpected new burst literal pool ownership')
    if before_pools['.data']!=after_pools['.data']:raise ValueError('Changed burst nonliteral pool')
    before_sections=source.projection.sections(old);after_sections=source.projection.sections(obj)
    for name in before_sections.keys()|after_sections.keys():
        if name not in ('.rodata','.data') and name.startswith(('.rdata','.sdata','.lit','.bss','.sbss')):
            if before_sections.get(name)!=after_sections.get(name):raise ValueError('Changed burst auxiliary pool '+name)
    row.update(unchanged_padded_neighbors=11,raw_padded_words_identical=True,new_guards=0,
        literal_only_pool_delta=True,installed=False,matching_credit=0)
    (out/'qualified-literal-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,[words,candidate],row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];out=root/BUILD;rows=[]
    for label,body,types in forms():
        row=measure(root,out,label,body,types)[-1];rows.append(dict(label=label,**row))
        print(label,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
    (out/'measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
