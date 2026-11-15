"""Private original-role particle candidate and checked scheduling/CFG normalization.

This derives words from the pinned semantic C object. It never reads retail
words while transforming an object and is not a production adoption receipt.
"""
from pathlib import Path
import json,os
from tools.experiments.game_configurable_particle_15175390_recovery import NAME,ENTRY,ROM,SIZE,SOURCE,EXTRA,BASELINE_SOURCE_SHA256,BASELINE_ELF_SHA256
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
BUILD='conker/build/game-configurable-particle-constructor-15175390-normalization'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
OUT=ROOT/BUILD
SELECTED='void func_15175390(s32 count, s32 slot, s32 x, s32 y, s32 z,\n                   s32 outerRadius, s32 view, s32 verticalRange, s32 innerRadius,\n                   s32 flags, s32 baseType, s32 typeRange, s32 baseModel,\n                   s32 modelMask, s32 state, f32 baseScale, f32 scaleRange,\n                   s32 groundFlags) {\n    s32 i;\n    s32 variant;\n    s32 tilted;\n    s32 grounded;\n    s32 sampleZ; /* Divisor until the second remainder, then the world Z sample. */\n    s32 value; /* Signed samples, heading, then raw surface bits. */\n    s32 heading;\n    s32 spawnX;\n    s32 spawnY;\n    struct17 relative;\n    Particle15175390 *particle;\n    u8 *surface; /* A failed query can leave the retail word untouched. */\n    s32 towardView;\n\n    if ((flags & 0x40) && verticalRange <= 0) {\n        return;\n    }\n    towardView = flags & 0x10000;\n    if (towardView) {\n        relative.unk0 = (f32)x - *(f32 *)(D_800DBFF0 + (u32)view * 0x9A0 + 0x2F8);\n        relative.unk4 = (f32)y - *(f32 *)(D_800DBFF0 + (u32)view * 0x9A0 + 0x2FC);\n        relative.unk8 = (f32)z - *(f32 *)(D_800DBFF0 + (u32)view * 0x9A0 + 0x300);\n        heading = (s32)func_15048FC8(&relative);\n    }\n    i = 0;\n    if (count > 0) {\n        do {\n            if (typeRange != 0) {\n                variant = (u32)func_150ADA20() % (u32)typeRange;\n            } else {\n                variant = 0;\n            }\n            particle = func_15167A68((u32)baseType + variant, 0, 0xF8, 1, 0xFF, 1);\n            if (particle == NULL) {\n                break;\n            }\n            tilted = flags & 0x20000;\n            grounded = groundFlags & 1;\n            spawnY = y;\n            sampleZ = (u32)outerRadius - innerRadius;\n            value = func_150ADA20() % sampleZ;\n            spawnX = (u32)value + innerRadius;\n            if (value < 0) {\n                spawnX = (u32)value - innerRadius;\n            }\n            spawnX = (u32)spawnX + x;\n            value = func_150ADA20() % sampleZ;\n            if (value < 0) {\n                sampleZ = (u32)value - innerRadius;\n            } else {\n                sampleZ = (u32)value + innerRadius;\n            }\n            sampleZ = (u32)sampleZ + z;\n            if (state == 0 || grounded != 0) {\n                particle->groundHeight = (f32)func_1510F8D8(spawnX, y, sampleZ, &surface);\n            }\n            if (state == 0) {\n                spawnY = (s32)particle->groundHeight;\n            } else if (verticalRange != 0) {\n                spawnY = (u32)y + (u32)func_150ADA20() % (u32)verticalRange;\n            }\n            particle->slot = slot;\n            particle->flags = flags;\n            particle->state91 = state;\n            particle->position[0] = (f32)spawnX;\n            particle->position[1] = (f32)spawnY;\n            particle->position[2] = (f32)sampleZ;\n            particle->lifetime = (u32)func_150ADA20() % 15U + 10;\n            particle->mode = 0;\n            if (towardView) {\n                value = (func_150ADA20() & 31) + (u32)heading - 15;\n                if (value < 0) {\n                    value = value + 360;\n                } else if (value >= 360) {\n                    value = value - 360;\n                }\n            } else {\n                value = (u32)func_150ADA20() % 360U;\n            }\n            if (tilted) {\n                particle->tilt = (f32)((func_150ADA20() & 31) - 15);\n                particle->fieldB4 = -1.0f;\n            } else {\n                particle->tilt = 0.0f;\n                particle->fieldB4 = 0.0f;\n            }\n            particle->fieldB0 = 0.0f;\n            particle->heading = (f32)value;\n            particle->angularRate = (f32)((func_150ADA20() & 255) - 128) * D_800A7178;\n            particle->fieldBC = 0.0f;\n            particle->scale = ((f32)(s32)(func_150ADA20() & 65535) * 0.000030517578125f * scaleRange) + baseScale;\n            if (modelMask != -1) {\n                variant = 0;\n                if (modelMask != 0) {\n                    variant = func_150ADA20() & modelMask;\n                }\n            }\n            variant = (u32)variant + baseModel;\n            particle->model = D_800DDE88[variant].model;\n            particle->variant = variant;\n            particle->sourceX = x;\n            particle->sourceY = y;\n            particle->sourceZ = z;\n            particle->outerRadius = outerRadius;\n            particle->innerRadius = innerRadius;\n            particle->verticalRange = verticalRange;\n            particle->fieldDC = 0;\n            particle->fieldDE = 0;\n            particle->surfaceFlags = 0;\n            particle->fieldE0 = 0;\n            if (i == 0) {\n                if (baseType == 10) {\n                    particle->sound = func_10010E78(0, 0xA2, 0x7D00, 0, 0, 0, spawnX, spawnY, sampleZ, 1000, 4000);\n                }\n            } else {\n                particle->sound = 0;\n            }\n            if (grounded) {\n                particle->flags |= 0x80;\n                value = 0;\n                if (surface != NULL) {\n                    value = D_800DBE5C[(s32)((u32)surface - (u32)D_800DBE3C) / 12];\n                }\n                particle->surfaceFlags = value;\n                particle->surfaceKind = D_800A7170[((u32)value >> 5) & 3];\n            } else {\n                particle->surfaceKind = 0;\n            }\n            particle->stateF0 = 0;\n            particle->stateF1 = 0;\n            i++;\n        } while (i != count);\n    }\n}'
import hashlib,struct
from collections import Counter
RAW_SHA256='8055bc014c509dfc595ad13ad0ac1045b6136aa2e094a2d3e3decb6b427f8aec'
RAW_REFS={112: [('R_MIPS_HI16', 'D_800DBFF0')], 136: [('R_MIPS_LO16', 'D_800DBFF0')], 220: [('R_MIPS_26', 'func_15048FC8')], 280: [('R_MIPS_26', 'func_150ADA20')], 356: [('R_MIPS_26', 'func_15167A68')], 408: [('R_MIPS_26', 'func_150ADA20')], 480: [('R_MIPS_26', 'func_150ADA20')], 588: [('R_MIPS_26', 'func_1510F8D8')], 656: [('R_MIPS_26', 'func_150ADA20')], 752: [('R_MIPS_26', 'func_150ADA20')], 796: [('R_MIPS_26', 'func_150ADA20')], 856: [('R_MIPS_26', 'func_150ADA20')], 892: [('R_MIPS_26', 'func_150ADA20')], 960: [('R_MIPS_26', 'func_150ADA20')], 980: [('R_MIPS_HI16', 'D_800A7178')], 984: [('R_MIPS_LO16', 'D_800A7178')], 1000: [('R_MIPS_26', 'func_150ADA20')], 1080: [('R_MIPS_26', 'func_150ADA20')], 1100: [('R_MIPS_HI16', 'D_800DDE88')], 1128: [('R_MIPS_LO16', 'D_800DDE88')], 1264: [('R_MIPS_26', 'func_10010E78')], 1300: [('R_MIPS_HI16', 'D_800DBE3C')], 1332: [('R_MIPS_LO16', 'D_800DBE3C')], 1336: [('R_MIPS_HI16', 'D_800DBE5C')], 1340: [('R_MIPS_LO16', 'D_800DBE5C')], 1376: [('R_MIPS_HI16', 'D_800A7170')], 1388: [('R_MIPS_LO16', 'D_800A7170')]}
ORDER=(0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 148, 152, 156, 160, 164, 168, 172, 176, 180, 184, 188, 192, 196, 200, 204, 208, 212, 216, 220, 224, 228, 232, 236, 240, 244, 248, 252, 256, 260, 264, 268, 272, 276, 280, 284, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324, 328, 332, 336, 340, 344, 348, 352, 356, 360, 364, 368, 376, 372, 380, 384, 392, 388, 404, 400, 396, 408, 412, 416, 420, 424, 428, 432, 436, 440, 444, 448, 452, 456, 460, 464, 468, 472, 496, 476, 480, 484, 488, 492, 544, 500, 504, 508, 512, 516, 520, 524, 528, 532, 536, 540, 560, 548, 552, 556, 580, 564, 568, 572, 584, 588, 592, 596, 600, 604, 608, 612, 616, 620, 624, 628, 632, 636, 640, 644, 648, 652, 656, 660, 664, 668, 672, 676, 680, 684, 688, 692, 696, 700, 704, 708, 712, 716, 720, 724, 728, 732, 736, 740, 744, 748, 752, 756, 760, 764, 768, 772, 776, 780, 784, 788, 792, 796, 800, 804, 808, 812, 816, 820, 824, 828, 832, 836, 840, 844, 848, 852, 856, 860, 864, 868, 872, 876, 880, 884, 888, 892, 896, 900, 904, 908, 912, 916, 920, 924, 928, 932, 936, 940, 944, 948, 952, 956, 960, 964, 968, 972, 976, 980, 984, 988, 992, 996, 1000, 1004, 1008, 1012, 1016, 1020, 1024, 1028, 1032, 1036, 1040, 1044, 1048, 1052, 1056, 1060, 1064, 1068, 1072, 1076, 1080, 1084, 1088, 576, 1092, 1096, 1100, 1104, 1108, 1112, 1116, 1120, 1124, 1128, 1132, 1136, 1140, 1144, 1148, 1152, 1156, 1160, 1164, 1168, 1172, 1176, 1180, 1184, 1188, 1192, 1196, 1200, 1204, 1208, 1212, 1216, 1220, 1224, 1228, 1232, 1236, 1240, 1244, 1248, 1252, 1256, 1260, 1264, 1268, 1272, 1276, 1280, 1284, 1288, 1292, 1300, 1320, 1304, 1308, 1312, 1296, 1376, 1324, 1328, 1332, 1336, 1340, 1344, 1348, 1352, 1356, 1360, 1316, 1364, 1368, 1372, 1380, 1384, 1388, 1392, 1396, 1400, 1404, 1408, 1412, 1416, 1420, 1424, 1428, 1432, 1436, 1440, 1444, 1448, 1452, 1456, 1460, 1464, 1468, 1472, 1476)
FIELDS={104: {16: (9, 10)}, 112: {16: (11, 9)}, 116: {16: (9, 10), 11: (10, 11)}, 120: {21: (10, 11), 16: (9, 10), 11: (10, 11)}, 128: {16: (10, 11), 11: (10, 11)}, 132: {21: (10, 11), 16: (9, 10), 11: (10, 11)}, 136: {21: (11, 9), 16: (11, 9)}, 140: {16: (10, 11), 11: (10, 11)}, 148: {21: (10, 11), 16: (9, 10), 11: (10, 11)}, 152: {16: (10, 11), 11: (10, 11)}, 160: {21: (10, 9)}, 288: {16: (9, 10)}, 292: {16: (9, 10)}, 300: {21: (9, 10)}, 316: {16: (10, 9)}, 324: {16: (10, 9)}, 360: {21: (10, 9)}, 380: {16: (15, 13)}, 388: {11: (13, 15)}, 404: {21: (13, 15)}, 412: {21: (15, 13)}, 536: {21: (4, 3)}, 612: {16: (9, 10)}, 620: {21: (9, 10)}, 664: {16: (12, 13)}, 668: {16: (14, 12)}, 672: {16: (12, 13)}, 676: {11: (13, 14)}, 680: {21: (13, 12)}, 684: {21: (12, 13)}, 772: {16: (9, 10)}, 776: {16: (9, 10)}, 784: {16: (10, 9)}, 788: {21: (10, 9)}, 804: {16: (12, 13)}, 812: {16: (12, 13)}, 900: {16: (13, 12)}, 904: {21: (13, 12)}, 1088: {16: (9, 10)}, 1092: {16: (9, 10)}, 1096: {16: (10, 9)}, 1100: {16: (12, 13)}, 1108: {16: (10, 9)}, 1124: {21: (12, 13), 11: (12, 13)}, 1128: {21: (12, 13), 16: (12, 13)}, 1136: {16: (12, 13)}, 1140: {16: (13, 12)}, 1144: {16: (13, 12)}, 1224: {16: (9, 10)}, 1228: {16: (10, 9)}, 1232: {16: (10, 9)}, 1236: {16: (9, 10)}, 1300: {16: (15, 14)}, 1304: {16: (12, 13)}, 1308: {16: (12, 13)}, 1312: {16: (13, 12)}, 1296: {11: (4, 3)}, 1376: {16: (13, 11)}, 1324: {21: (13, 12)}, 1332: {21: (15, 14), 16: (15, 14)}, 1336: {16: (9, 24)}, 1340: {21: (9, 24), 16: (9, 24)}, 1344: {21: (14, 12), 16: (15, 14), 11: (24, 2)}, 1348: {21: (24, 2)}, 1352: {11: (25, 15)}, 1356: {16: (25, 15), 11: (8, 25)}, 1360: {21: (9, 24), 16: (8, 25), 11: (10, 8)}, 1364: {21: (10, 8), 16: (4, 3)}, 1368: {16: (4, 3), 11: (11, 10)}, 1372: {21: (11, 10), 16: (12, 9)}, 1380: {16: (4, 3)}, 1384: {21: (13, 11), 16: (12, 9), 11: (13, 11)}, 1388: {21: (13, 11), 16: (13, 11)}, 1396: {16: (13, 11)}, 1412: {16: (14, 13)}, 1420: {16: (14, 13)}}
OPCODES={572: (20, 4), 1324: (20, 4)}
EDGE_OVERRIDES={564: 580, 572: 608, 1324: 1372}
SPECIALS={0x1F0:(0x00602025,0x1DC,0x1E4),0x240:(0x8FA900F0,0x440,0x448),0x524:(0x8FAE0080,0x554,0x55C),0x530:(0x00045942,0x530,None)}
TEMP_REGS=set(range(1,16))|{24,25}
def normalize(raw,refs):
    if len(raw)!=1480 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Configurable particle source or named bindings changed')
    words=list(struct.unpack('>370I',raw));adjusted=words[:];assert sorted(ORDER)==list(range(0,1480,4));inverse={src:dst*4 for dst,src in enumerate(ORDER)}
    for pc,changes in FIELDS.items():
        word=adjusted[pc//4]
        for shift,(old,new) in changes.items():
            assert old in TEMP_REGS and new in TEMP_REGS and word>>shift&31==old
            word=(word&~(31<<shift))|(new<<shift)
        adjusted[pc//4]=word
    for pc,(old,new) in OPCODES.items():
        assert adjusted[pc//4]>>26==old and (old,new)==(20,4)
        adjusted[pc//4]=adjusted[pc//4]&0x03FFFFFF|new<<26
    result=[];bindings={}
    for dst,src in enumerate(ORDER):
        if src in SPECIALS:
            expected,at,target=SPECIALS[src];assert words[src//4]==expected and dst*4==at and src not in refs
            word=0 if target is None else (4<<26)|((target-at-4)//4&65535)
        else:
            word=adjusted[src//4];op=words[src//4]>>26
            if op in(1,4,5,6,7,20,21,22,23):
                old_target=src+4+4*(((words[src//4]&65535)^32768)-32768)
                target=EDGE_OVERRIDES.get(src,inverse[old_target]);word=word&0xFFFF0000|((target-dst*4-4)//4&65535)
        result.append(word)
        if src in refs:bindings[dst*4]=refs[src]
    assert Counter(r for rows in refs.values() for r in rows)==Counter(r for rows in bindings.values() for r in rows)
    return struct.pack('>370I',*result),bindings


def proposed(before):
    assert body(before,NAME)=='s32 func_15175390() {\n    return 0;\n}' and before.count('u32 func_150ADA20(void);')==1
    return before.replace(body(before,NAME),SELECTED).replace('/* Recovered routine',EXTRA+'\n/* Recovered routine',1).replace('u32 func_150ADA20(void);','s32 func_150ADA20(void);')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=(ROOT/SOURCE).read_bytes()
    assert hashlib.sha256(before).hexdigest()==BASELINE_SOURCE_SHA256
    assert hashlib.sha256((ROOT/'conker/build/conker.us.elf').read_bytes()).hexdigest()==BASELINE_ELF_SHA256
    old,diag=compile_owner(ROOT,OUT,before.decode(),'baseline')
    obj,diag2=compile_owner(ROOT,OUT,proposed(before.decode()),'selected')
    assert diag==diag2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs)
    a,b=bound_blob(raw,refs),bound_blob(normal,nrefs)
    truth=list(struct.unpack_from('>370I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    assert len(a)==len(b)==370 and sum(x!=y for x,y in zip(a,truth))==219 and b==truth
    assert (-a[0])&65535==(-b[0])&65535==184
    assert same_functions(old,obj,(NAME,))==8
    assert normalized_pools(old)==normalized_pools(obj)=={'.rodata':None,'.data':None}
    controls=0
    for i in range(370):
        bad=bytearray(raw);bad[4*i+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed source word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(kind,name+'_changed') for kind,name in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed named binding accepted')
    from tools.tests.game_configurable_particle_15175390_normalization_proof import qualify
    proof=qualify(a,b)
    (OUT/'normalized.bin').write_bytes(normal)
    (OUT/'normalized-bindings.json').write_text(json.dumps(nrefs,indent=2)+'\n')
    assert (ROOT/SOURCE).read_bytes()==before
    report=dict(words=370,frame=184,raw_differences=219,normalized_differences=0,raw_sha256=RAW_SHA256,neighbors=8,named_bindings=sum(map(len,refs.values())),corruption_controls=controls,permuted_words=sum(i*4!=p for i,p in enumerate(ORDER)),register_words=len(FIELDS),proof=proof,installed=False,c_match_credit=0,new_guards=0)
    (OUT/'normalization-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
