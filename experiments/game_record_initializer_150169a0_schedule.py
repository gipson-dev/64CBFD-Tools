"""Pinned initializer scheduling projection, with a separate relational proof.

This diagnostic has no installer and emits no production guard rows.
The proof engine independently checks the proposed register colors and public
effects. This pure projection does not install a body or claim match credit.
"""
import hashlib,json,struct
from tools.experiments import game_record_initializer_150169a0_candidates as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
RAW_SHA256='0028b0d4e468e23a1d1bd253c8286eca1bb2572ae5a2b659c83f467fdd8eb4ec'
RAW_REFS={16: [('R_MIPS_26', 'func_15004F30')], 44: [('R_MIPS_HI16', '.rodata')], 52: [('R_MIPS_LO16', '.rodata')], 64: [('R_MIPS_HI16', 'D_1A34E0')], 68: [('R_MIPS_LO16', 'D_1A34E0')], 72: [('R_MIPS_HI16', 'D_1A37E0')], 84: [('R_MIPS_LO16', 'D_1A37E0')], 88: [('R_MIPS_HI16', 'D_1A33F0')], 92: [('R_MIPS_LO16', 'D_1A33F0')], 96: [('R_MIPS_HI16', 'D_1A34E0')], 104: [('R_MIPS_LO16', 'D_1A34E0')], 112: [('R_MIPS_26', 'func_1502B9B4')], 144: [('R_MIPS_26', 'allocate_memory')], 152: [('R_MIPS_HI16', 'D_800D20FC')], 156: [('R_MIPS_LO16', 'D_800D20FC')], 176: [('R_MIPS_26', 'func_10004514')], 192: [('R_MIPS_HI16', 'D_800D2100')], 208: [('R_MIPS_LO16', 'D_800D2100')], 216: [('R_MIPS_HI16', 'D_800D2101')], 220: [('R_MIPS_LO16', 'D_800D2101')], 264: [('R_MIPS_26', 'func_1502B8E0')], 280: [('R_MIPS_HI16', 'D_800D2100')], 284: [('R_MIPS_LO16', 'D_800D2100')], 304: [('R_MIPS_26', 'func_15017114')], 312: [('R_MIPS_HI16', 'D_800D2100')], 316: [('R_MIPS_LO16', 'D_800D2100')], 332: [('R_MIPS_26', 'allocate_memory')], 344: [('R_MIPS_HI16', 'D_800D210C')], 348: [('R_MIPS_LO16', 'D_800D210C')], 372: [('R_MIPS_26', 'allocate_memory')], 380: [('R_MIPS_HI16', 'D_800D2110')], 388: [('R_MIPS_LO16', 'D_800D2110')], 384: [('R_MIPS_HI16', 'D_800D210C')], 392: [('R_MIPS_LO16', 'D_800D210C')], 396: [('R_MIPS_26', 'bzero')], 404: [('R_MIPS_HI16', 'D_800D2110')], 408: [('R_MIPS_LO16', 'D_800D2110')], 412: [('R_MIPS_26', 'bzero')], 428: [('R_MIPS_HI16', 'D_800D1548')], 432: [('R_MIPS_LO16', 'D_800D1548')], 420: [('R_MIPS_HI16', 'D_8008FD8C')], 424: [('R_MIPS_LO16', 'D_8008FD8C')], 452: [('R_MIPS_HI16', 'D_800D2340')], 456: [('R_MIPS_LO16', 'D_800D2340')], 512: [('R_MIPS_HI16', 'D_800CC2D0')], 516: [('R_MIPS_LO16', 'D_800CC2D0')], 548: [('R_MIPS_26', 'func_150859AC')], 588: [('R_MIPS_HI16', 'D_800BE9F0')], 608: [('R_MIPS_LO16', 'D_800BE9F0')], 592: [('R_MIPS_HI16', 'D_8008FD90')], 604: [('R_MIPS_LO16', 'D_8008FD90')], 556: [('R_MIPS_HI16', '.rodata')], 568: [('R_MIPS_LO16', '.rodata')], 572: [('R_MIPS_HI16', '.rodata')], 576: [('R_MIPS_LO16', '.rodata')], 644: [('R_MIPS_HI16', '.rodata')], 652: [('R_MIPS_LO16', '.rodata')], 1728: [('R_MIPS_HI16', 'D_8008FD8C')], 1732: [('R_MIPS_LO16', 'D_8008FD8C')], 1756: [('R_MIPS_26', 'func_15016850')], 1764: [('R_MIPS_HI16', 'D_800D2100')], 1768: [('R_MIPS_LO16', 'D_800D2100')], 1812: [('R_MIPS_26', 'func_15083DA0')], 1832: [('R_MIPS_HI16', 'D_800D2100')], 1844: [('R_MIPS_LO16', 'D_800D2100')], 1872: [('R_MIPS_26', 'func_1508295C')], 1880: [('R_MIPS_26', 'func_15172CA8')], 1896: [('R_MIPS_26', 'func_1508295C')]}
COLORS=(62717952, 62849024, 61865984, 61079552, 0, 0, 61210624, 13500416, 29425664, 2097152, 946176, 65536, 3016704, 3014656, 29360128, 0, 983040, 32440320, 1048576, 61800448, 0, 34603008, 1572864, 51904512, 1048576, 62390272, 34603008, 262144, 0, 327680, 62455808, 327680, 393216, 35198976, 4399104, 61014016, 0, 14336, 1048576, 34603008, 33685504, 61079552, 4204544, 61210624, 0, 458752, 61734912, 196608, 65536, 29556736, 30720, 31588352, 3080192, 4390912, 65536, 2228224, 35192832, 61734912, 6291456, 0, 0, 49152, 10240, 393216, 458752, 51978240, 0, 61734912, 65536, 4259840, 196608, 6488064, 7274496, 49152, 61079552, 33081344, 0, 7929856, 262144, 8650752, 327680, 12288, 14336, 0, 61079552, 61014016, 65536, 2228224, 204800, 8394752, 61079552, 327680, 12288, 0, 14336, 65536, 262144, 2228224, 8650752, 0, 61145088, 262144, 8650752, 0, 61145088, 65536, 2097152, 983040, 32440320, 12288, 6144, 31457280, 458752, 917504, 30277632, 1572864, 14206976, 53377024, 31457280, 401408, 311296, 50339840, 327680, 61014016, 0, 61210624, 65536, 61014016, 35192832, 2097152, 65536, 2097152, 61210624, 524288, 720896, 4259840, 52654080, 23789568, 17301504, 458752, 589824, 655360, 786432, 851968, 2031616, 2097152, 29360128, 161792, 65536, 3082240, 3080192, 31457280, 0, 16908288, 65536, 4259840, 65536, 4259840, 65536, 4259840, 34471936, 35127296, 50579456, 0, 53018624, 34471936, 29587456, 0, 31457280, 35127296, 50579456, 0, 53018624, 34537472, 917504, 31703040, 0, 51249152, 34537472, 1638400, 31682560, 0, 30998528, 34537472, 1572864, 31705088, 0, 54001664, 34537472, 917504, 31703040, 0, 51249152, 34537472, 1638400, 31682560, 30998528, 35127296, 50558976, 31457280, 35192832, 52629504, 4194304, 0, 4194304, 35127296, 917504, 50558976, 32374784, 35192832, 52674560, 50331648, 34471936, 29560832, 4194304, 0, 4194304, 35192832, 983040, 52674560, 0, 51314688, 35192832, 917504, 52656128, 0, 32374784, 35192832, 1572864, 52654080, 0, 30932992, 35192832, 983040, 52674560, 0, 51314688, 35192832, 917504, 52656128, 0, 32374784, 35192832, 1572864, 52654080, 30932992, 34537472, 31705088, 0, 53084160, 34471936, 1572864, 29587456, 33030144, 35192832, 52654080, 0, 30015488, 34537472, 1572864, 31705088, 0, 54001664, 34537472, 917504, 31703040, 0, 51249152, 34537472, 1638400, 31682560, 30998528, 24641536, 14157824, 2097152, 35127296, 34537472, 31705088, 0, 52887552, 35127296, 917504, 50558976, 32374784, 35192832, 983040, 52629504, 5767168, 51249152, 5111808, 35192832, 52674560, 0, 51314688, 34471936, 983040, 29607936, 53215232, 35127296, 1638400, 50556928, 30343168, 35127296, 50558976, 33095680, 23986176, 13502464, 2097152, 34537472, 35127296, 50579456, 0, 54460416, 34537472, 31682560, 29818880, 35127296, 65536, 50532352, 5832704, 52525056, 5177344, 34471936, 29560832, 5767168, 51970048, 0, 5832704, 34537472, 1572864, 65536, 31682560, 30146560, 35192832, 52656128, 33030144, 34471936, 29607936, 53280768, 35127296, 50558976, 33488896, 34471936, 29560832, 5832704, 52543488, 0, 5767168, 34471936, 983040, 1572864, 29607936, 53411840, 34471936, 29587456, 33030144, 35192832, 1572864, 52654080, 30212096, 34537472, 31705088, 54001664, 34471936, 29587456, 31457280, 35127296, 50579456, 52428800, 34471936, 29560832, 5177344, 33030144, 5767168, 16908288, 65536, 442368, 4259840, 50774016, 65536, 4259840, 1622016, 35192832, 65536, 52629504, 5111808, 29456384, 5177344, 1622016, 50774016, 1622016, 50774016, 1622016, 50774016, 1638400, 54067200, 1622016, 51974144, 4194304, 35127296, 0, 50579456, 983040, 0, 53411840, 4194304, 34537472, 0, 31705088, 1572864, 0, 54001664, 4194304, 35127296, 0, 50579456, 983040, 0, 53411840, 34537472, 5111808, 31705088, 966656, 0, 54001664, 34471936, 29587456, 31916032, 1572864, 51904512, 12976128, 6488064, 14157824, 2097152, 0, 0, 0, 262144, 8650752, 10240, 6144, 8388608, 61079552, 35192832, 52654080, 30343168, 31457280, 10813440, 61014016, 0, 61145088, 61014016, 35127296, 61145088, 262144, 50579456, 52559872, 8650752, 10813440, 10749952, 2097152, 6488064, 61079552, 327680, 0, 393216, 0, 8192, 61079552, 327680, 0, 12288, 62849024, 61865984, 62717952, 65011712, 0)
r=lambda start,end:list(range(start,end,4))
order=r(0,0x1a4)+[0x1ac,0x1b0,0x1a4,0x1a8,0x1b8,0x1bc,0x1b4,0x1c0]+r(0x1c4,0x1e0)+[0x210,0x214,0x21c,0x220,0x224,0x228]+r(0x22c,0x248)+r(0x24c,0x278)+[0x50c,0x278,0x27c]+r(0x280,0x50c)+r(0x510,0x57c)+r(0x580,0x61c)+[0x1e0,0x61c,0x1e4,0x620,0x624,0x1e8]+r(0x62c,0x644)+[0x1e8]+r(0x1ec,0x210)+[0x644]+r(0x648,0x6a8)+[0x6ac,0x6a8]+r(0x6b4,0x784)
assert len(order)==477
omitted=sorted(set(range(0,1924,4))-set(order));assert omitted==[0x218,0x248,0x57c,0x628,0x6b0]
inverse={pc:i*4 for i,pc in reversed(list(enumerate(order)))}
def mask(w):
    op,fn=w>>26,w&63
    if op==0:
        if fn in(0,2,3):return 31<<16|31<<11
        if fn in(4,6,7,33,35,36,37,42,43):return 31<<21|31<<16|31<<11
        if fn==8:return 31<<21
        if fn in(16,18):return 31<<11
        if fn in(24,25,26,27):return 31<<21|31<<16
        if not w or fn==13:return 0
        raise AssertionError(hex(w))
    if op==17:return 31<<16 if w>>21&31 in(0,4)else 0
    if op in(3,):return 0
    if op in(6,7,22,23,49,57):return 31<<21
    if op==15:return 31<<16
    assert op in(4,5,9,10,11,12,13,20,21,32,33,35,36,37,40,41,43),hex(w)
    return 31<<21|31<<16

def private_projection(raw,refs):
    if len(raw)!=1924 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or refs!=RAW_REFS:raise ValueError('Initializer source instructions or bindings changed')
    words=list(struct.unpack('>481I',raw));result=[];bindings={};paired={};pending=[]
    names={0:'jtbl_80096760_game',0xa0:'D_80096800',0xa4:'D_80096804',0xa8:'jtbl_80096808_game'}
    for pc,rows in sorted(refs.items()):
        if rows==[('R_MIPS_HI16','.rodata')]:pending.append(pc)
        elif rows==[('R_MIPS_LO16','.rodata')]:
            name=names[words[pc//4]&65535];paired[pc]=name
            for hi in pending:paired[hi]=name
            pending=[]
    assert not pending and len(paired)==8
    for i,pc in enumerate(order):
        w=words[pc//4];m=mask(w);color=COLORS[i];assert color&~m==0
        value=(w&~m)|color
        if w>>26 in(1,4,5,6,7,20,21,22,23):
            target=pc+4+4*(((w&65535)^32768)-32768)
            if pc==0x624:target=0x1ec
            assert target in inverse
            delta=inverse[target]-(i*4+4);assert delta%4==0
            value=(value&0xffff0000)|((delta//4)&65535)
        if pc in refs:
            rows=refs[pc]
            if pc in paired:
                rows=[(kind,paired[pc])for kind,name in rows]
                if refs[pc][0][0]=='R_MIPS_LO16':value&=0xffff0000
            bindings[i*4]=rows
        result.append(value)
    return struct.pack('>477I',*result),bindings

def main():
    raw,refs=payload(g.OUT/'selected.o',g.NAME);normal,nrefs=private_projection(raw,refs)
    rom=(g.ROOT/'conker/conker.us.bin').read_bytes();truth=struct.unpack_from('>477I',rom,g.ROM)
    assert bound_blob(normal,nrefs,g.symbols())==list(truth)
    pool,targets=normalized_pools(g.OUT/'selected.o')['.rodata'];pool=bytearray(pool)
    for at,owner,pc in targets:
        assert owner==g.NAME and pc in inverse
        struct.pack_into('>I',pool,at,g.ENTRY+inverse[pc])
    assert bytes(pool)==rom[g.POOL_ROM:g.POOL_ROM+336]
    controls=0
    for i in range(481):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:private_projection(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw instruction accepted')
    for pc,rows in refs.items():
        try:private_projection(raw,{**refs,pc:[(kind,name+'_changed')for kind,name in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    from tools.tests.game_record_initializer_150169a0_proof import prove
    retail,source=g.programs();proof=prove(source,(bound_blob(normal,nrefs,g.symbols()),retail[1],retail[2]))
    report=dict(raw_words=481,projected_words=477,omitted=[hex(pc)for pc in omitted],duplicated=['0x1e8'],table_entries=79,table_pool_exact=True,corruption_controls=controls,independent_equivalence_proof_pending=False,proof_paths=proof['symbolic_paths'],production_installation=False,uncredited=True)
    (g.OUT/'projection-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
