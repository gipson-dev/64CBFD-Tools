"""Resource-cache match with proved split-bound scheduling and three derived words."""
import csv,hashlib,io,json,struct,subprocess
from tools.experiments import game_resource_cache_15016850_candidates as draft
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_particle_display_151770c8_match import bound
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
ROOT,OUT,NAME,ENTRY,ROM,SIZE,SOURCE,BUILD=draft.ROOT,draft.OUT,draft.NAME,draft.ENTRY,draft.ROM,draft.SIZE,draft.SOURCE,draft.BUILD
SDK=set()
RAW_SHA256='d3f5abc8fb11e70af7d7c262f461082ef89a68b723d542eb746eab77262b2c8c'
RAW_REFS={8: [('R_MIPS_HI16', 'D_800BE590')], 12: [('R_MIPS_LO16', 'D_800BE590')], 48: [('R_MIPS_HI16', 'D_800D2100')], 52: [('R_MIPS_LO16', 'D_800D2100')], 68: [('R_MIPS_HI16', 'D_800BE598')], 88: [('R_MIPS_LO16', 'D_800BE598')], 72: [('R_MIPS_HI16', 'D_800BE5A8')], 84: [('R_MIPS_LO16', 'D_800BE5A8')], 76: [('R_MIPS_HI16', 'D_800D20FC')], 80: [('R_MIPS_LO16', 'D_800D20FC')], 124: [('R_MIPS_HI16', 'D_800BE598')], 128: [('R_MIPS_LO16', 'D_800BE598')], 192: [('R_MIPS_26', 'func_1502B7F0')], 200: [('R_MIPS_HI16', 'D_800D2100')], 204: [('R_MIPS_LO16', 'D_800D2100')]}
ORDER=(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 148, 152, 156, 160, 164, 168, 172, 216, 260, None, 264, 176, 180, 184, 188, 192, 196, 200, 204, 208, 256, None, 212, None, 220, 224, 228, 232, 236, 240, 244, 248, 252, 268, 272, 276, 280, 284, 288, 292, 296, 300, 304, 308, 312, 316, 320)

def normalize(raw,refs):
    if len(raw)!=324 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Resource-cache source instructions or bindings changed')
    a=list(struct.unpack('>81I',raw));order=ORDER
    assert len(order)==84 and sorted(p for p in order if p is not None)==list(range(0,324,4))
    inverse={p:i*4 for i,p in enumerate(order)if p is not None};result=[];bindings={};fields={}
    def scaled(w,which):
        if which=='first':assert w==0x00061080;return w&~(31<<11)|3<<11
        if which=='middle':assert w==0x00461023;return w&~(31<<21|31<<11)|3<<21|3<<11
        assert which=='last'and w==0x00026900;return w&~(31<<16|31<<11)|3<<16|3<<11
    for i,src in enumerate(order):
        pc=i*4
        if src is None:
            if pc==0xb8:w=0x10000000|((0x118-pc-4)//4&65535)
            elif pc==0xe8:w=scaled(a[0x104//4],'middle')
            else:assert pc==0xf0;w=scaled(a[0x108//4],'last')
            result.append(w);continue
        w=a[src//4]
        if src==0x6c:
            assert w==0x01d17821
        if src in(0xd8,0x100):w=scaled(w,'first')
        if src==0x104:w=scaled(w,'middle')
        if src==0x108:w=scaled(w,'last')
        if src==0x110:assert w==0x022d082a;w=w&~(31<<16)|3<<16
        op=w>>26
        if op in(1,4,5,6,7,20,21,22,23):
            target=src+4+4*(((a[src//4]&65535)^32768)-32768)
            if src==0xa8:assert op==5 and target==0x100;w=w&~(63<<26)|4<<26;dest=0xc0
            elif src==0xd4:assert op==20 and target==0x104;w=w&~(63<<26)|4<<26;dest=0x118
            else:dest=inverse[target]
            w=w&0xffff0000|((dest-pc-4)//4&65535)
        result.append(w)
        if src in refs:bindings[pc]=refs[src]
    blob=struct.pack('>84I',*result)
    from tools.tests.game_resource_cache_15016850_proof import prove
    prove(bound(raw,refs),bound(blob,bindings))
    return blob,bindings

def proposed(before):
    assert body(before,NAME)=='s32 func_15016850() {\n    return 0;\n}'
    return before.replace(body(before,NAME),draft.SELECTED)

def main():
    before=(OUT/'production-baseline'/SOURCE).read_text();candidate=proposed(before);live=(ROOT/SOURCE).read_text();installed='void '+NAME+'('in live
    assert live==(candidate if installed else before)
    old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'selected')
    assert d==d2==''and same_functions(old,obj,(NAME,))==2 and normalized_pools(old)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);truth=struct.unpack_from('>84I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM);assert bound(normal,nrefs)==list(truth)
    controls=0
    for i in range(81):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(k,n+'_changed')for k,n in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));ws=struct.unpack('>84I',normal);oldwords=struct.unpack('>81I',raw);rows=[];dest=0
    rel=lambda rows:';'.join(k+':'+n for k,n in rows)or'-'
    for i,expected in enumerate(oldwords):
        at=dest;replacement=ws[dest];dest+=1;insert=dest<len(ws)and ORDER[dest]is None
        extra=ws[dest]if insert else None
        if insert:dest+=1
        er,rr=refs.get(i*4,[]),nrefs.get(at*4,[])
        if expected!=replacement or er!=rr or insert:rows.append(dict(filename='generated_43D00',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations=rel(er),replacement_relocations=rel(rr),note='Restore proved split resource-cache bound and original conditional join',insert_after='0x%08X'%extra if insert else'',insert_after_relocations='',omit='false'))
    assert dest==84 and sum(bool(r['insert_after'])for r in rows)==3
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/43D00.s').read_text();a=asm.index('glabel '+NAME+'\n');b=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:b]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/43D00.s',filename='generated_43D00',word_patches_path=OUT/'proposed-guards.csv'))
    for label in('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True);assert bound(*payload(OUT/(label+'.o'),NAME))==list(truth)
    assert same_functions(OUT/'production-baseline/conker/build/src/game/generated_43D00.c.o',OUT/'guarded.o',(NAME,))==2
    report=dict(raw_words=81,words=84,frame=96,guards=len(rows),inserted_derived_words=3,neighbors=2,corruption_controls=controls,installed=installed,raw_sha256=RAW_SHA256)
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
