"""Bounded register-role, setup-schedule and literal-pool guard proofs."""
import json,os,struct,subprocess,sys
from tools.experiments import game_motion_effect_150c2c00_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools import check_motion_effect_150c2c00_pool as production
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, SYMBOL, RELOCATION, parse_object, read_c_string

def gpr_fields(w):
    op,fmt=w>>26,w>>21&31
    if op==0:return (21,16,11)
    if op in (2,3):return ()
    if op==17:return (16,) if fmt in (0,4) else ()
    if op in (49,53,57,61):return (21,)
    if op==15:return (16,)
    return (21,16)

def fpr_fields(w):
    op,fmt,fn=w>>26,w>>21&31,w&63
    if op in (49,53,57,61):return (16,)
    if op!=17:return ()
    if fmt in (0,4):return (11,)
    if fmt==8:return ()
    if fmt in (16,17,20):return (11,16) if fn>=48 else (11,6) if fn in (6,7,32,36) else (11,16,6)
    raise AssertionError(hex(w))

def rename(w,fields,mapping):
    for at in fields:
        value=w>>at&31;w=(w&~(31<<at))|(mapping.get(value,value)<<at)
    return w

def fp_access(w):
    op,fmt,fn=w>>26,w>>21&31,w&63
    if op in (49,53):return set(),{w>>16&31}
    if op in (57,61):return {w>>16&31},set()
    if op!=17 or fmt==8:return set(),set()
    fs,ft,fd=w>>11&31,w>>16&31,w>>6&31
    if fmt==4:return set(),{fs}
    if fmt==0:return {fs},set()
    if fn>=48:return {fs,ft},set()
    return ({fs} if fn in (6,7,32,36) else {fs,ft}),{fd}

def main():
    raw,refs=payload(s.OUT/'recovered.o',s.NAME);fixed,fr=s.normalize(raw,refs)
    a=list(struct.unpack('>243I',raw));b=list(struct.unpack('>243I',fixed))
    assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}==set(s.PATCHES)
    # Only the initialized owner/motion roles are permuted. Initial register
    # saves keep their own original homes; their independent order changes.
    changed=[]
    for i in range(2,227):
        if i==8:continue
        w=rename(a[i],gpr_fields(a[i]),{18:19,19:18})
        if w!=a[i]:assert w==b[i];changed.append(i)
    assert changed==[2,30,51,106,108,191,196]
    assert a[1]==b[8]==0xafb20054 and a[8]==b[1]==0xafb30058
    assert a[233:]==b[233:] and a[0]==b[0]==0x27bdff18
    assert not any(19 in {a[i]>>n&31 for n in gpr_fields(a[i])} for i in range(9,51))
    # Z's initial F20 value dies after the square. Its next use is a fresh
    # first-scale definition. The renamed scratch is never a hidden FP arg.
    changed=[i for i in range(47,53) if rename(a[i],fpr_fields(a[i]),{20:2})!=a[i]]
    assert changed==[47,52]
    assert all(rename(a[i],fpr_fields(a[i]),{20:2})==b[i] for i in changed)
    touches=[(i,fp_access(a[i])) for i in range(53,227) if 20 in set.union(*fp_access(a[i]))]
    assert touches[0][0]==136 and 20 not in touches[0][1][0] and 20 in touches[0][1][1]
    assert rename(a[59],fpr_fields(a[59]),{0:12})==b[59]
    assert rename(a[63],fpr_fields(a[63]),{0:12})==b[63]
    assert not any({0,12}&set.union(*fp_access(a[i])) for i in range(64,101))
    assert a[101]>>26==3 and (a[101]&0x3ffffff)<<2==0
    assert refs[404]==[('R_MIPS_26','func_150ADA68')]
    # Packet setup uses one closed scratch cycle, followed by a no-argument
    # float-returning call which overwrites/clobbers the caller-saved FPRs.
    changed=[]
    for i in range(71,101):
        w=rename(a[i],fpr_fields(a[i]),{10:16,16:18,18:10})
        if w!=a[i]:assert w==b[i];changed.append(i)
    assert changed==[71,73,78,98,99,100]
    for reg in (10,16,18):
        first=next(fp_access(a[i]) for i in range(71,101) if reg in set.union(*fp_access(a[i])))
        assert reg not in first[0] and reg in first[1]
    # Three distinct constant destinations commute, with no intervening use.
    def setup(words):
        registers={i:('entry',i) for i in range(32)};registers[0]=0
        for w in words:
            op,rs,rt,imm=w>>26,w>>21&31,w>>16&31,w&65535
            assert rs==0 and op in (9,15)
            registers[rt]=(imm<<16) if op==15 else (imm^32768)-32768
        return registers
    assert setup(a[53:56])==setup(b[53:56])
    assert b[53:56]==a[54:56]+a[53:54]
    rejected=0
    for i in s.PATCHES:
        bad=bytearray(raw);bad[i*4+3]^=1
        try:s.normalize(bytes(bad),refs)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt expected word accepted')
    for offset in refs:
        bad=dict(refs);bad[offset]=[('R_MIPS_26','func_150C2C00')]
        try:s.normalize(raw,bad)
        except AssertionError:rejected+=1
        else:raise AssertionError('Corrupt relocation accepted')
    pool=(s.ROOT/'conker/conker.us.bin').read_bytes()[0x244d80:0x244dd0];pool_controls=0
    for i in range(20):
        bad=bytearray(pool);bad[4*i]^=1
        try:s.pool_guard(bytes(bad))
        except AssertionError:pool_controls+=1
        else:raise AssertionError('Corrupt literal pool accepted')
    obj=s.OUT/'recovered.o';assert production.verify(obj)['verified']
    cli=subprocess.run([sys.executable,'-m','tools.check_motion_effect_150c2c00_pool',str(obj)],cwd=s.ROOT,capture_output=True,text=True)
    assert cli.returncode==0 and json.loads(cli.stdout)['verified'] and not cli.stderr
    blob=obj.read_bytes();header=ELF_HEADER.unpack_from(blob);headers=[SECTION_HEADER.unpack_from(blob,header[6]+i*header[11]) for i in range(header[12])]
    names=headers[header[13]];strings=blob[names[4]:names[4]+names[5]];indices={read_c_string(strings,h[0]):i for i,h in enumerate(headers)}
    pool_header=headers[indices['.rodata']];text_header=headers[indices['.text']];fn=parse_object(obj)[1][s.NAME]
    bad_path=s.OUT/'corrupt-production-pool.o';production_controls=0
    def reject(data):
        nonlocal production_controls
        bad_path.write_bytes(data)
        try:production.verify(bad_path)
        except ValueError:production_controls+=1
        else:raise AssertionError('Production pool checker accepted corrupted object')
    for i in range(20):
        bad=bytearray(blob);bad[pool_header[4]+4*i]^=1;reject(bad)
    bad=bytearray(blob);bad[text_header[4]+fn['value']+3]^=1;reject(bad)
    bad=bytearray(blob);struct.pack_into('>I',bad,header[6]+indices['.rodata']*header[11]+8,pool_header[2]|1);reject(bad)
    symbol_header=next(h for h in headers if h[1]==2)
    symbols=[SYMBOL.unpack_from(blob,at) for at in range(symbol_header[4],symbol_header[4]+symbol_header[5],symbol_header[9] or SYMBOL.size)]
    pool_symbol=next(i for i,symbol in enumerate(symbols) if symbol[5]==indices['.rodata'] and symbol[3]&15==3)
    rel_header=next(h for h in headers if h[1]==9 and h[7]==indices['.text'])
    rels=[(at,*RELOCATION.unpack_from(blob,at)) for at in range(rel_header[4],rel_header[4]+rel_header[5],rel_header[9] or RELOCATION.size)]
    at,location,info=next(row for row in rels if not fn['value']<=row[1]<fn['value']+fn['size'])
    bad=bytearray(blob);struct.pack_into('>I',bad,at+4,(pool_symbol<<8)|(info&255));reject(bad)
    at,location,info=next(row for row in rels if fn['value']<=row[1]<fn['value']+fn['size'])
    bad=bytearray(blob);struct.pack_into('>I',bad,at+4,(info&~255)|(6 if info&255!=6 else 5));reject(bad)
    assert production_controls==24
    report=dict(groups=4,guards=22,frame_and_saves_unchanged=True,role_words=9,motion_scratch_words=4,setup_words=3,packet_scratch_words=6,corrupt_words_and_relocations_rejected=rejected,corrupt_pool_words_rejected=pool_controls,production_checker_controls=production_controls,readonly_pool_bytes=80)
    (s.OUT/'guard-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
