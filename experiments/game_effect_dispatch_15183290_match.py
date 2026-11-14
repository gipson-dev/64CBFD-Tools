"""Recover four-slot effect dispatch, packet ABI and closed temporary roles."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_effect_dispatch_15183290_proof import REGIONS,qualify
from tools import pad_generated_object as pg
NAME='func_15183290';ENTRY=0x15183290;ROM=0x1B0740;SIZE=1568
SOURCE='conker/src/game/generated_1B0740.c';BUILD='conker/build/game-effect-dispatch-15183290-screen'
RAW_SHA256='65fe4e9c404d408350a1fdb2ade08db32f805d8211e17775c941ce1b6f6e4279'
EXTRA='extern u8 D_800DDF5C[4];\nextern u8 *D_800DBFF0;\nextern u8 D_800CC2E4[];\nextern f32 D_800A7320, D_800A7324, D_800A7328, D_800A732C;\nextern f32 D_800A7330, D_800A7334, D_800A7338, D_800A733C, D_800A7340;\nvoid func_15177F90(s32, void *, s32, s32, s32, s32, s32, s32, s32, s32, s32);\nvoid func_15175390(s32, s32, s32, s32, s32, s32, s32, s32, s32,\n                   s32, s32, s32, s32, s32, s32, f32, f32, s32);\nvoid func_15174BF0(s32, s32, s32, s32, s32, s32, f32, f32, s32);\nvoid func_15174FA4(s32, s32, s32, s32, s32, s32, s32, s32, f32, f32);\nvoid func_151838B0(s32);\nvoid func_15183974(s32);\nvoid func_151839F0(s32, s32);\ns32 func_15184118(u8 *);\nvoid func_1517AA20(f32, s32, s32, s32, s32);\n'
SELECTED='/* Dispatch an effect through the first free slot; burst requests do not reserve it. */\ns32 func_15183290(s32 x, s32 y, s32 z, s32 value, s32 kind, s32 unused,\n                   s32 view, s32 param0, s32 param1, s32 param2, s32 flags) {\n    s32 slot;\n    u8 *selected;\n    u8 *actor;\n\n    for (slot = 0, selected = D_800DDF5C; slot != 4; slot++, selected++) {\n        if (*selected == 0) {\n            break;\n        }\n    }\n    if (slot == 4) {\n        return -1;\n    }\n    /* These are wrapping word shifts, including for negative event parameters. */\n    param0 = (u32)param0 << 4;\n    param1 = (u32)param1 << 4;\n    param2 = (u32)param2 << 4;\n    actor = *(u8 **)(D_800DBFF0 + (u32)view * 0x9A0 + 0x3D0);\n    switch (kind) {\n    case 0:\n        func_15177F90((u8)value, 0, 0xFE, x, y, z, 0, 0x7FFF, 0xFF, 1, 0);\n        break;\n    case 1:\n        func_15177F90((u8)value, D_800CC2E4, 0xFE, x, y, z, 0, 0x7FFF, 0xFF, 1, 0);\n        break;\n    case 2:\n        func_151838B0(0);\n        func_15175390(value, slot, x, y, z, 63, view, 30, 0, 0x30003,\n                       10, 0, 0, 1, 2, D_800A7320, 0.5f, flags);\n        break;\n    case 3:\n        if (func_15184118(actor)) {\n            func_15174BF0(value, slot, x, y, z, view, D_800A7324, 0.5f, flags);\n        } else {\n            return -1;\n        }\n        break;\n    case 8:\n        return -1;\n    case 4:\n        func_151839F0(7, 10);\n        func_15174FA4(value, slot, x, y, z, (u32)param0 << 2, view, 0,\n                       D_800A7328, 0.5f);\n        break;\n    case 10:\n        func_15183ACC(7);\n        func_15174FA4(value, slot, x, y, z, (u32)param0 << 2, view, 1,\n                       D_800A732C, 0.5f);\n        break;\n    case 11:\n        func_15183ACC(2);\n        func_15183ACC(3);\n        func_15183ACC(4);\n        func_15183ACC(5);\n        func_15175390(value, slot, x, y, z, param0, view, param1, param2,\n                       0x4D, 0x15, 3, 2, -1, 0, D_800A7330, 0.5f, flags);\n        break;\n    case 5:\n        func_15183ACC(2);\n        func_15183ACC(3);\n        func_15183ACC(4);\n        func_15183ACC(5);\n        func_15175390(value, slot, x, y, z, param0, view, param1, param2,\n                       0x4D, 0x15, 3, 2, -1, 2, D_800A7334, 0.5f, flags);\n        break;\n    case 6:\n        func_15183974(8);\n        func_15175390(value, slot, x, y, z, param0, view, param1, param2,\n                       0x7D, 0x44, 2, 8, -1, 2, D_800A7338, 0.5f, flags);\n        break;\n    case 7:\n        func_15183ACC(6);\n        func_15175390(value, slot, x, y, z, param0, view, param1, param2,\n                       0x4D, 0x14, 0, 6, 0, 2, D_800A733C, D_800A7340, flags);\n        break;\n    case 9:\n        func_1517AA20(*(f32 *)(actor + 0x3C), (s32)*(f32 *)(actor + 0x14),\n                       (s32)*(f32 *)(actor + 0x18), (s32)*(f32 *)(actor + 0x1C), value);\n        break;\n    }\n    /* Unsupported kinds also claim the captured slot in the retail routine. */\n    if (kind != 9) {\n        *selected = 1;\n    }\n    return slot;\n}'
RAW_REFS={32: [('R_MIPS_HI16', 'D_800DDF5C')], 36: [('R_MIPS_LO16', 'D_800DDF5C')], 112: [('R_MIPS_HI16', 'D_800DBFF0')], 120: [('R_MIPS_LO16', 'D_800DBFF0')], 188: [('R_MIPS_HI16', '.rodata')], 196: [('R_MIPS_LO16', '.rodata')], 268: [('R_MIPS_26', 'func_15177F90')], 292: [('R_MIPS_HI16', 'D_800CC2E4')], 320: [('R_MIPS_LO16', 'D_800CC2E4')], 348: [('R_MIPS_26', 'func_15177F90')], 364: [('R_MIPS_26', 'func_151838B0')], 372: [('R_MIPS_HI16', 'D_800A7320')], 376: [('R_MIPS_LO16', 'D_800A7320')], 496: [('R_MIPS_26', 'func_15175390')], 512: [('R_MIPS_26', 'func_15184118')], 528: [('R_MIPS_HI16', 'D_800A7324')], 532: [('R_MIPS_LO16', 'D_800A7324')], 584: [('R_MIPS_26', 'func_15174BF0')], 620: [('R_MIPS_26', 'func_151839F0')], 628: [('R_MIPS_HI16', 'D_800A7328')], 632: [('R_MIPS_LO16', 'D_800A7328')], 696: [('R_MIPS_26', 'func_15174FA4')], 712: [('R_MIPS_26', 'func_15183ACC')], 720: [('R_MIPS_HI16', 'D_800A732C')], 724: [('R_MIPS_LO16', 'D_800A732C')], 792: [('R_MIPS_26', 'func_15174FA4')], 808: [('R_MIPS_26', 'func_15183ACC')], 816: [('R_MIPS_26', 'func_15183ACC')], 824: [('R_MIPS_26', 'func_15183ACC')], 832: [('R_MIPS_26', 'func_15183ACC')], 844: [('R_MIPS_HI16', 'D_800A7330')], 848: [('R_MIPS_LO16', 'D_800A7330')], 968: [('R_MIPS_26', 'func_15175390')], 984: [('R_MIPS_26', 'func_15183ACC')], 992: [('R_MIPS_26', 'func_15183ACC')], 1000: [('R_MIPS_26', 'func_15183ACC')], 1008: [('R_MIPS_26', 'func_15183ACC')], 1024: [('R_MIPS_HI16', 'D_800A7334')], 1028: [('R_MIPS_LO16', 'D_800A7334')], 1148: [('R_MIPS_26', 'func_15175390')], 1164: [('R_MIPS_26', 'func_15183974')], 1180: [('R_MIPS_HI16', 'D_800A7338')], 1184: [('R_MIPS_LO16', 'D_800A7338')], 1304: [('R_MIPS_26', 'func_15175390')], 1320: [('R_MIPS_26', 'func_15183ACC')], 1328: [('R_MIPS_HI16', 'D_800A733C')], 1332: [('R_MIPS_LO16', 'D_800A733C')], 1336: [('R_MIPS_HI16', 'D_800A7340')], 1340: [('R_MIPS_LO16', 'D_800A7340')], 1452: [('R_MIPS_26', 'func_15175390')], 1516: [('R_MIPS_26', 'func_1517AA20')]}

def bound(raw,refs):
    s={n:0x800a72f0 if n in ('.rodata','jtbl_800A72F0') else int(n.split('_')[1],16) for rs in refs.values() for _,n in rs}
    return bound_blob(raw,refs,s)

def normalize(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:
        raise ValueError('Effect dispatch raw body or named bindings changed')
    words=list(struct.unpack('>392I',raw))
    for start,end in REGIONS:
        mapping={11:12,12:13,13:11} if start==0x58 else {11:12,12:11}
        for i in range(start//4,end//4):
            w=words[i];op=w>>26
            fields=(21,16,11) if op==0 else () if op==3 else (21,) if op in (49,57) else (16,) if op==17 else (21,16)
            for shift in fields:
                reg=w>>shift&31
                if reg in mapping:w=(w&~(31<<shift))|(mapping[reg]<<shift)
            words[i]=w
    assert words[0xa4//4]==0x01ab7021
    w=words[0xa4//4];words[0xa4//4]=(w&~((31<<21)|(31<<16)))|((w>>21&31)<<16)|((w>>16&31)<<21)
    result=struct.pack('>392I',*words);qualify(bound(raw,refs),bound(result,refs))
    return result,refs

def proposed(before):
    assert body(before,NAME)=='s32 func_15183290() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Non-matching placeholders',EXTRA+'\n/* Non-matching placeholders',1).replace('/* Non-matching placeholders for the text-only asm slice asm/1B0740.s. */','/* Recovered routines for the text-only asm slice asm/1B0740.s. */')

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='s32 '+NAME+'(s32 x' in live
    before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    proposal=proposed(before);assert not installed or proposal==live
    old,diags=compile_owner(root,out,before,'baseline');obj,diags2=compile_owner(root,out,proposal,'selected');assert diags==diags2==''
    (out/'selected-body.c').write_text(body(proposal,NAME)+'\n');(out/'extra.c').write_text(EXTRA)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);assert bound(normal,nrefs)==list(struct.unpack_from('>392I',(root/'conker/conker.us.bin').read_bytes(),ROM))
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)=={'.rodata':None,'.data':None}
    pools=normalized_pools(obj);pool,identities=pools['.rodata'];assert pool==bytes(48) and pools['.data'] is None
    table=struct.unpack_from('>12I',(root/'conker/conker.us.bin').read_bytes(),0x24bdb0)
    assert identities==tuple((i*4,NAME,t-ENTRY) for i,t in enumerate(table))
    for i in range(392):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:pass
        else:raise AssertionError('Changed raw word accepted')
    try:normalize(raw,{**refs,0x10c:[('R_MIPS_26','func_15177F94')]})
    except ValueError:pass
    else:raise AssertionError('Changed helper binding accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    rel=lambda rs:';'.join(k+':'+n for k,n in rs) or '-'
    for i,(a,b) in enumerate(zip(struct.unpack('>392I',raw),struct.unpack('>392I',normal))):
        if a!=b:rows.append(dict(filename='generated_1B0740',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(refs.get(i*4,[])),note='Normalize closed effect dispatcher temporary roles and commutative address operands',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==44;existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    asm=(root/'conker/asm/1B0740.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pg.emit_padded_assembly(obj,root/'conker/asm/1B0740.s',filename='generated_1B0740',word_patches_path=out/'proposed-guards.csv',rodata_symbol='jtbl_800A72F0'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True)
        assert bound(*payload(out/(label+'.o'),NAME))==bound(normal,nrefs)
    rom=(root/'conker/conker.us.bin').read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff)
    calls=[i*4 for i,w in enumerate(ws) if w==jal];assert calls==[0xcfa0c] and ENTRY not in ws
    report=dict(words=392,frame=104,guards=44,neighbors=8,owner_functions=9,table_bytes=48,installed=installed,corruption_controls=393,proof=qualify(bound(raw,refs),bound(normal,nrefs)),direct_callers=calls,raw_sha256=hashlib.sha256(raw).hexdigest())
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
