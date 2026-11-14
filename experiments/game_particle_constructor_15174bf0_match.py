"""Recover jittered particle fields, private homes, roles and surface phi."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_particle_constructor_15174bf0_proof import qualify
from tools import pad_generated_object as pg
NAME='func_15174BF0';ENTRY=0x15174BF0;ROM=0x1A20A0;SIZE=948
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-ground-particle-constructor-15174bf0-screen'
RAW_SHA256='ada7251ec22b14da6b1e59b38bfdafdbb22010d86bb67bd65e553118d9d8ca0f'
EXTRA='#include "structs.h"\ntypedef struct {\n    u8 retained00[0x90];\n    u8 slot, retained91;\n    s16 flags;\n    void *model;\n    f32 position[3];\n    s16 lifetime, mode;\n    f32 tilt, heading, fieldB0, fieldB4, angularRate, fieldBC, scale;\n    u32 retainedC4;\n    f32 groundHeight;\n    u8 retainedCC[0x1C];\n    u32 surfaceFlags;\n    u8 surfaceKind, variant;\n    u16 sound;\n    u8 stateF0, stateF1, retainedF2[6];\n} Particle15174BF0;\ntypedef struct { void *model; u32 retained04[4]; } Model15174BF0;\nextern u8 *D_800DBFF0;\nextern u8 *D_800DBE3C;\nextern u32 *D_800DBE5C;\nextern Model15174BF0 D_800DDE88[];\nextern u8 D_800A7170[];\nextern f32 D_800A7174;\nf32 func_15048FC8(struct17 *relative);\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\nu32 func_150ADA20(void);\nu16 func_10010E78(s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32); /* Full call-site words; narrowing occurs in the callee. */\ns32 func_1510F8D8(s32, s32, s32, u8 **);\n'
SELECTED='/* Create jittered particles with one initial sound and optional ground classification. */\nvoid func_15174BF0(s32 count, s32 slot, s32 x, s32 y, s32 z, s32 view,\n                   f32 baseScale, f32 scaleRange, s32 flags) {\n    struct17 relative;\n    u8 *surface; /* An early query failure leaves the retail stack word untouched. */\n    f32 rateScale;\n    s32 heading;\n    s32 spawnX;\n    s32 spawnZ;\n    s32 turn;\n    s32 angle;\n    s32 i;\n    s32 grounded;\n    u32 material;\n    s32 variant;\n    Particle15174BF0 *particle;\n\n    relative.unk0 = (f32)x - *(f32 *)(D_800DBFF0 + (u32)view * 0x9A0 + 0x2F8);\n    relative.unk4 = (f32)y - *(f32 *)(D_800DBFF0 + (u32)view * 0x9A0 + 0x2FC);\n    relative.unk8 = (f32)z - *(f32 *)(D_800DBFF0 + (u32)view * 0x9A0 + 0x300);\n    heading = (s32)func_15048FC8(&relative);\n    i = 0;\n    if (count > 0) {\n        rateScale = D_800A7174;\nagain:\n        particle = func_15167A68(10, 0, 0xF8, 1, 0xFF, 1);\n        if (particle != NULL) {\n            grounded = flags & 1;\n            spawnX = (u32)x + (func_150ADA20() & 0x7F) - 0x3F;\n            spawnZ = (u32)z + (func_150ADA20() & 0x7F) - 0x3F;\n            particle->flags = 3;\n            particle->position[1] = (f32)y;\n            particle->position[0] = (f32)spawnX;\n            particle->slot = slot;\n            particle->position[2] = (f32)spawnZ;\n            particle->lifetime = (func_150ADA20() % 15U) + 10;\n            particle->mode = 1;\n            turn = (u32)heading + (func_150ADA20() & 0x1F) - 15;\n            angle = turn;\n            if (turn < 0) {\n                angle = turn + 360;\n            } else if (turn >= 360) {\n                angle = turn - 360;\n            }\n            particle->tilt = (f32)((s32)(func_150ADA20() & 0x1F) - 15);\n            particle->fieldB0 = 0.0f;\n            particle->fieldB4 = -1.0f;\n            particle->heading = (f32)angle;\n            particle->angularRate = (f32)((s32)(func_150ADA20() & 0xFF) - 128) * rateScale;\n            particle->fieldBC = 0.0f;\n            particle->scale = ((f32)(s32)(func_150ADA20() & 0xFFFF) * 0.000030517578125f * scaleRange) + baseScale;\n            variant = func_150ADA20() & 1;\n            particle->variant = variant;\n            particle->model = D_800DDE88[variant].model;\n            if (i == 0) {\n                particle->sound = func_10010E78(0, 0xA2, 0x7D00, 0, 0, 0, spawnX, y, spawnZ, 1000, 4000);\n            } else {\n                particle->sound = 0;\n            }\n            particle->surfaceFlags = 0;\n            if (grounded) {\n                particle->flags |= 0x80;\n                particle->groundHeight = (f32)func_1510F8D8(spawnX, y, spawnZ, &surface);\n                material = 0;\n                if (surface != NULL) {\n                    material = D_800DBE5C[(s32)((u32)surface - (u32)D_800DBE3C) / 12];\n                }\n                particle->surfaceFlags = material;\n                particle->surfaceKind = D_800A7170[(material >> 5) & 3];\n            } else {\n                particle->surfaceKind = 0;\n            }\n            particle->stateF0 = 0;\n            particle->stateF1 = 0;\n            i++;\n            if (i != count) {\n                goto again;\n            }\n        }\n    }\n}'
RAW_REFS={92: [('R_MIPS_HI16', 'D_800DBFF0')], 112: [('R_MIPS_LO16', 'D_800DBFF0')], 192: [('R_MIPS_26', 'func_15048FC8')], 212: [('R_MIPS_HI16', 'D_800A7174')], 228: [('R_MIPS_LO16', 'D_800A7174')], 276: [('R_MIPS_26', 'func_15167A68')], 300: [('R_MIPS_26', 'func_150ADA20')], 316: [('R_MIPS_26', 'func_150ADA20')], 380: [('R_MIPS_26', 'func_150ADA20')], 412: [('R_MIPS_26', 'func_150ADA20')], 464: [('R_MIPS_26', 'func_150ADA20')], 508: [('R_MIPS_26', 'func_150ADA20')], 540: [('R_MIPS_26', 'func_150ADA20')], 584: [('R_MIPS_26', 'func_150ADA20')], 608: [('R_MIPS_HI16', 'D_800DDE88')], 620: [('R_MIPS_LO16', 'D_800DDE88')], 680: [('R_MIPS_26', 'func_10010E78')], 736: [('R_MIPS_26', 'func_1510F8D8')], 748: [('R_MIPS_HI16', 'D_800DBE3C')], 780: [('R_MIPS_LO16', 'D_800DBE3C')], 784: [('R_MIPS_HI16', 'D_800DBE5C')], 788: [('R_MIPS_LO16', 'D_800DBE5C')], 824: [('R_MIPS_HI16', 'D_800A7170')], 836: [('R_MIPS_LO16', 'D_800A7170')]}
def initial(raw,refs):
    words=list(struct.unpack('>237I',raw));result=words[:]
    for i,w in enumerate(words):
        pc=i*4;op,rs,rt=w>>26,w>>21&31,w>>16&31
        if rs==29 and (op in (35,43,49,57) or op==9 and rt in (4,7)):
            off=w&65535;private={0xc8:0x9c,0xcc:0xa4,0xd0:0xa8,0xd4:0xac}
            if off in private:w=w&0xffff0000|private[off]
        if 0x54<=pc<0x88:
            mapping={14:15,15:24,24:14}
            fields=(21,16,11) if op==0 else (21,16)
            for shift in fields:
                r=w>>shift&31
                if r in mapping:w=w&~(31<<shift)|mapping[r]<<shift
        if pc==0x84:
            assert w==0x030e1021;w=0x01d81021
        if 0xe0<=pc<0x36c:
            mapping={24:30,26:24,28:26,30:28}
            fields=(16,) if op in (49,57) else (11,) if op==17 and rs in (0,4) else (16,11,6) if op==17 and rs==16 else (11,6) if op==17 and rs==20 else ()
            for shift in fields:
                r=w>>shift&31
                if r in mapping:w=w&~(31<<shift)|mapping[r]<<shift
        result[i]=w
    return struct.pack('>237I',*result),refs

def complete(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:
        raise ValueError('Particle constructor raw body or named bindings changed')
    adjusted,_=initial(raw,refs);ws=list(struct.unpack('>237I',adjusted));order=list(range(237))
    def permutation(start,values):
        order[start//4:start//4+len(values)]=[v//4 for v in values]
    permutation(0x144,[0x144,0x14c,0x148,0x150,0x158,0x15c,0x154,0x174,0x160,0x164,0x16c,0x168,0x170,0x180,0x17c,0x178])
    permutation(0x264,[0x268,0x26c,0x264,0x274,0x278,0x27c,0x280,0x284,0x288,0x270])
    permutation(0x2dc,[0x2e0,0x2dc,0x2e8,0x2ec,0x2f0,0x2f4,0x2e4,0x338,0x2f8,0x2fc,0x304,0x300,0x30c,0x310,0x314,0x318,0x31c,0x320,0x324,0x328,0x308,0x32c,0x330,0x334,0x33c,0x340,0x344,0x348,0x34c])
    assert sorted(order)==list(range(237));inverse={old:new for new,old in enumerate(order)}
    fields={0x2e4:{'rd':3},0x338:{'rt':11},0x310:{'rt':24},0x314:{'rs':24,'rt':24},
            0x318:{'rs':13,'rd':2},0x31c:{'rs':2},0x320:{'rd':14},0x324:{'rt':14,'rd':25},
            0x328:{'rs':24,'rt':25,'rd':8},0x32c:{'rs':8,'rt':3},0x330:{'rt':3,'rd':9},
            0x334:{'rs':9,'rt':10},0x33c:{'rt':3},0x340:{'rs':11,'rt':10,'rd':11},
            0x344:{'rs':11,'rt':11},0x34c:{'rt':11}}
    for pc in range(0x144,0x184,4):
        w=ws[pc//4];op=w>>26;mapping={14:15,15:14,24:25,25:24}
        shifts=(21,16,11) if op==0 else (16,) if op==17 and w>>21&31==4 else (21,) if op in (49,57) else () if op==3 else (21,16)
        for shift in shifts:
            reg=w>>shift&31
            if reg in mapping:w=w&~(31<<shift)|mapping[reg]<<shift
        ws[pc//4]=w
    for pc in (0x204,0x208,0x20c):
        w=ws[pc//4];op=w>>26;shifts=(16,) if op==17 else (21,16)
        for shift in shifts:
            reg=w>>shift&31
            if reg in (14,15):w=w&~(31<<shift)|({14:15,15:14}[reg]<<shift)
        ws[pc//4]=w
    for pc,roles in fields.items():
        w=ws[pc//4]
        for field,reg in roles.items():
            shift={'rs':21,'rt':16,'rd':11}[field];w=w&~(31<<shift)|reg<<shift
        ws[pc//4]=w
    for pc in (0x35c,0x364):
        w=ws[pc//4];assert w>>16&31==14;ws[pc//4]=w&~(31<<16)|12<<16
    result=[ws[i] for i in order];nrefs={j*4:refs[i*4] for j,i in enumerate(order) if i*4 in refs}
    for j,i in enumerate(order):
        w=ws[i];op=w>>26
        if op in (4,5,20,21) and j*4 not in (0x304,0x32c):
            imm=((w&65535)^32768)-32768;target=i+1+imm
            assert target in inverse;result[j]=w&0xffff0000|((inverse[target]-j-1)&65535)
    # A repeated ordinary local load is redundant. The two mutually-exclusive
    # right shifts merge at their common successor, whose material phi is V3.
    # Moving the zero after the helper preserves its caller-clobbered lifetime.
    assert result[0x308//4]==0x8fae009c and result[0x304//4]==0x51a0000b
    result[0x308//4]=0;result[0x304//4]=0x11a0000b
    assert result[0x32c//4]==0x00115942
    result[0x32c//4]=(4<<26)|((0x334-(0x32c+4))//4)
    return struct.pack('>237I',*result),nrefs


def normalize(raw,refs):
    normal,nrefs=complete(raw,refs);adjusted,arefs=initial(raw,refs)
    qualify(bound_blob(adjusted,arefs),bound_blob(normal,nrefs))
    assert Counter(r for rs in refs.values() for r in rs)==Counter(r for rs in nrefs.values() for r in rs)
    return normal,nrefs
def proposed(before):
    assert body(before,NAME)=='s32 func_15174BF0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Non-matching placeholders',EXTRA+'\n/* Non-matching placeholders',1).replace('/* Non-matching placeholders for the text-only asm slice asm/1A20A0.s. */','/* Recovered routine and remaining placeholders for asm/1A20A0.s. */')
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    source=proposed(before);assert not installed or source==live
    old,diags=compile_owner(root,out,before,'baseline');obj,diag2=compile_owner(root,out,source,'selected');assert diags==diag2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs)
    rom=(root/'conker/conker.us.bin').read_bytes();assert bound_blob(normal,nrefs)==list(struct.unpack_from('>237I',rom,ROM))
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.rodata':None,'.data':None}
    for i in range(237):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:pass
        else:raise AssertionError('Changed raw word accepted')
    try:normalize(raw,{**refs,0xc0:[('R_MIPS_26','func_15048FCC')]})
    except ValueError:pass
    else:raise AssertionError('Changed heading binding accepted')
    original=(root/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[];rel=lambda rs:';'.join(k+':'+n for k,n in rs) or '-'
    for i,(a,b) in enumerate(zip(struct.unpack('>237I',raw),struct.unpack('>237I',normal))):
        if a!=b or refs.get(i*4,[])!=nrefs.get(i*4,[]):
            rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(nrefs.get(i*4,[])),note='Restore particle private homes closed temporary roles and surface classification scheduling',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==79;existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (out/'proposed-guards.csv').write_bytes(guards)
    asm=(root/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pg.emit_padded_assembly(obj,root/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True)
        assert bound_blob(*payload(out/(label+'.o'),NAME))==bound_blob(normal,nrefs)
    ws=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff)
    calls=[i*4 for i,w in enumerate(ws) if w==jal];assert calls==[0x1b0988] and ENTRY not in ws
    report=dict(words=237,frame=216,guards=79,neighbors=8,owner_functions=9,installed=installed,corruption_controls=238,proof=qualify(bound_blob(*initial(raw,refs)),bound_blob(normal,nrefs)),direct_callers=calls,raw_sha256=hashlib.sha256(raw).hexdigest())
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
