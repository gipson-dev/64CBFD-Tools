"""Direct recovery of the type-19 minimum-height particle constructor."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
NAME='func_15174FA4';ENTRY=0x15174FA4;ROM=0x1A2454;SIZE=1004
SOURCE='conker/src/game/generated_1A20A0.c';BUILD='conker/build/game-height-particle-constructor-15174fa4-screen'
RAW_SHA256='f075622b60e5cbcdf8a0271f520e1d7e2c939db7f32c301379e27c16046121c2'
EXTRA='typedef struct {\n    u8 retained00[0x90];\n    u8 slot, state91;\n    s16 flags;\n    void *model;\n    f32 position[3];\n    s16 lifetime, mode;\n    f32 tilt, heading, fieldB0, fieldB4, fieldB8, fieldBC, scale;\n    u32 retainedC4;\n    f32 groundHeight, fieldCC;\n    s16 fieldD0, retainedD2, fieldD4, fieldD6;\n    u32 retainedD8;\n    s16 fieldDC;\n    u16 retainedDE;\n    f32 fieldE0, fieldE4;\n    u32 surfaceFlags;\n    u8 surfaceKind, variant;\n    u16 retainedEE;\n    u8 stateF0, stateF1, retainedF2[6];\n} Particle15174FA4;\ntypedef struct { s32 fixedHeight; u32 retained04[3]; } Height15174FA4;\nextern Height15174FA4 D_800D3300[];\nextern void *D_800DDF14;\nvoid func_1510F800(s32 context);\ns32 func_150A3A70(s32 x, s32 z);\nvoid func_1516979C(struct102 *record);\n'
SELECTED='/* Create type-19 particles using the lowest returned fixed-point height. */\nvoid func_15174FA4(s32 count, s32 slot, s32 x, s32 y, s32 z, s32 width,\n                   s32 unusedView, s32 elevated, f32 baseScale, f32 scaleRange) {\n    s32 centerX = x;\n    s32 centerY = y;\n    s32 i;\n    s32 spawnX;\n    s32 spawnZ;\n    s32 halfWidth;\n    s32 hits;\n    s32 lowest;\n    s32 j;\n    Particle15174FA4 *particle;\n\n    if (elevated == 0) {\n        func_1510F800(0);\n    }\n    i = 0;\n    if (count > 0) {\n        do {\n            particle = func_15167A68(19, 0, 0xF8, 1, 0xFF, 1);\n            if (particle == NULL) {\n                break;\n            }\n            halfWidth = width >> 1;\n            spawnX = (u32)centerX + func_150ADA20() % (u32)width - halfWidth;\n            spawnZ = (u32)z + func_150ADA20() % (u32)width - halfWidth;\n            particle->slot = slot;\n            particle->position[0] = (f32)spawnX;\n            particle->position[1] = (f32)centerY;\n            particle->position[2] = (f32)spawnZ;\n            particle->lifetime = func_150ADA20() % 3U + 4;\n            particle->mode = 0;\n            particle->tilt = (f32)((s32)(func_150ADA20() & 31) - 15);\n            particle->heading = (f32)(func_150ADA20() % 360U);\n            particle->fieldB0 = (f32)((s32)(func_150ADA20() & 31) - 15);\n            particle->fieldB4 = 0.0f;\n            particle->fieldBC = 0.0f;\n            particle->fieldB8 = 3.0f;\n            particle->scale = ((f32)(s32)(func_150ADA20() & 65535) * 0.000030517578125f * scaleRange) + baseScale;\n            particle->model = D_800DDF14;\n            particle->variant = 7;\n            hits = func_150A3A70(spawnX, spawnZ);\n            if (hits == 0) {\n                func_1516979C((struct102 *)particle);\n            } else {\n                lowest = D_800D3300[0].fixedHeight;\n                for (j = 1; j < hits; j++) {\n                    if (D_800D3300[j].fixedHeight < lowest) {\n                        lowest = D_800D3300[j].fixedHeight;\n                    }\n                }\n                lowest >>= 8;\n                particle->groundHeight = (f32)lowest;\n                if (elevated == 0) {\n                    particle->state91 = 0;\n                    particle->position[1] = (f32)(lowest + 10);\n                    particle->flags = 1;\n                } else {\n                    particle->state91 = 2;\n                    particle->flags = 4;\n                    particle->fieldE4 = (f32)(s32)((func_150ADA20() & 127) + (u32)lowest + 300);\n                    particle->position[1] = (f32)(s32)((func_150ADA20() & 127) + (u32)lowest + 300);\n                }\n                particle->fieldCC = 0;\n                particle->fieldD0 = centerX;\n                particle->fieldD4 = z;\n                particle->fieldD6 = halfWidth;\n                particle->fieldE0 = 0;\n                particle->fieldDC = 0;\n                particle->surfaceFlags = 0;\n                particle->surfaceKind = 0;\n                particle->stateF0 = 0;\n                particle->stateF1 = 0;\n            }\n            i++;\n        } while (i != count);\n    }\n}'
RAW_REFS={84: [('R_MIPS_26', 'func_1510F800')], 152: [('R_MIPS_26', 'func_15167A68')], 176: [('R_MIPS_26', 'func_150ADA20')], 212: [('R_MIPS_26', 'func_150ADA20')], 284: [('R_MIPS_26', 'func_150ADA20')], 312: [('R_MIPS_26', 'func_150ADA20')], 340: [('R_MIPS_26', 'func_150ADA20')], 388: [('R_MIPS_26', 'func_150ADA20')], 432: [('R_MIPS_26', 'func_150ADA20')], 468: [('R_MIPS_HI16', 'D_800DDF14')], 500: [('R_MIPS_LO16', 'D_800DDF14')], 508: [('R_MIPS_26', 'func_150A3A70')], 524: [('R_MIPS_26', 'func_1516979C')], 540: [('R_MIPS_HI16', 'D_800D3300')], 548: [('R_MIPS_LO16', 'D_800D3300')], 576: [('R_MIPS_HI16', 'D_800D3300')], 580: [('R_MIPS_LO16', 'D_800D3300')], 628: [('R_MIPS_HI16', 'D_800D3300')], 632: [('R_MIPS_LO16', 'D_800D3300')], 820: [('R_MIPS_26', 'func_150ADA20')], 852: [('R_MIPS_26', 'func_150ADA20')]}

def validate(raw,refs):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:
        raise ValueError('Height-particle constructor raw body or named bindings changed')
    return raw,refs

def proposed(before):
    assert body(before,NAME)=='s32 func_15174FA4() {\n    return 0;\n}'
    return before.replace(body(before,NAME),SELECTED).replace('/* Recovered routine',EXTRA+'\n/* Recovered routine',1)

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
    live=(root/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(out/'production-baseline'/SOURCE).read_text() if installed else live
    source=proposed(before);assert not installed or source==live
    old,diags=compile_owner(root,out,before,'baseline');obj,diag2=compile_owner(root,out,source,'selected');assert diags==diag2==''
    raw,refs=validate(*payload(obj,NAME));rom=(root/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>251I',rom,ROM));assert bound_blob(raw,refs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.rodata':None,'.data':None}
    controls=0
    for i in range(251):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:validate(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw word accepted')
    for pc in refs:
        bad={**refs,pc:[(kind,name+'_changed') for kind,name in refs[pc]]}
        try:validate(raw,bad)
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    guards=(root/'conker/retail_word_patches.us.csv').read_bytes();assert not [r for r in csv.DictReader(io.StringIO(guards.decode())) if r['function']==NAME]
    (out/'proposed-guards.csv').write_bytes(guards)
    asm=(root/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (out/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (out/'guarded.s').write_text(pg.emit_padded_assembly(obj,root/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=out/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'.o')),str(out/(label+'.s'))],cwd=root/'conker',capture_output=True,check=True)
        assert bound_blob(*payload(out/(label+'.o'),NAME))==truth
    ws=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff);calls=[i*4 for i,w in enumerate(ws) if w==jal]
    assert calls==[0x1b09f8,0x1b0a58] and ENTRY not in ws
    report=dict(words=251,frame=96,new_guards=0,neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,direct_callers=calls,raw_sha256=hashlib.sha256(raw).hexdigest())
    (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
