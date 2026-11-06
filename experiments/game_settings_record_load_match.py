"""Settings loader: selected no-unroll body, guarded layout and literal ELF."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_settings_record_load_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=280,candidate.BUILD
OBJECT='conker/build/src/game_33990.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/nonmatchings/game_33990/func_15007440.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='dfda98f2d79107f1c65b55b101831d491bf9530fcb15566fd4342b1c144592e6'
GUARD_SHA='015f773de9b6c97c9f3b12ee69cd3d20d758f8f3e9a7319ce93a23f2cfcf5466'
RODATA_SYMBOL='jtbl_80095A00_game'
sha=lambda b:hashlib.sha256(b).hexdigest()
RAW_SHA='a85a19a8cd877a8610630df46f9c96f7b0d3814df993187d7286af399bff430c'
TRUTH_SHA='736e27ae8db3f7f1fa4a7f8bba6c14de36bb5494a50be1973762d9873b621282'
BINDINGS={8: [('R_MIPS_HI16', 'D_800BE900')], 20: [('R_MIPS_LO16', 'D_800BE900')], 12: [('R_MIPS_HI16', 'D_800BE358')], 16: [('R_MIPS_LO16', 'D_800BE358')], 28: [('R_MIPS_26', 'func_151DD3A0')], 36: [('R_MIPS_HI16', 'D_800BE358')], 44: [('R_MIPS_LO16', 'D_800BE358')], 40: [('R_MIPS_HI16', 'D_800BE35A')], 52: [('R_MIPS_LO16', 'D_800BE35A')], 104: [('R_MIPS_HI16', 'D_800E0BE0')], 108: [('R_MIPS_LO16', 'D_800E0BE0')], 120: [('R_MIPS_HI16', 'D_800E0BFC')], 128: [('R_MIPS_LO16', 'D_800E0BFC')], 168: [('R_MIPS_HI16', 'D_800E0BFC')], 180: [('R_MIPS_LO16', 'D_800E0BFC')], 232: [('R_MIPS_HI16', 'D_800E0BE0')], 240: [('R_MIPS_LO16', 'D_800E0BE0')], 236: [('R_MIPS_26', 'func_151DD9E4')], 244: [('R_MIPS_26', 'func_151E7EF8')], 256: [('R_MIPS_HI16', 'D_8008FE30')], 260: [('R_MIPS_LO16', 'D_8008FE30')]}
RETAIL_BINDINGS={12: [('R_MIPS_HI16', 'D_800BE358')], 16: [('R_MIPS_LO16', 'D_800BE358')], 8: [('R_MIPS_HI16', 'D_800BE900')], 20: [('R_MIPS_LO16', 'D_800BE900')], 28: [('R_MIPS_26', 'func_151DD3A0')], 36: [('R_MIPS_HI16', 'D_800BE35A')], 44: [('R_MIPS_LO16', 'D_800BE35A')], 92: [('R_MIPS_HI16', 'D_800BE358')], 96: [('R_MIPS_LO16', 'D_800BE358')], 100: [('R_MIPS_HI16', 'D_800E0BE0')], 104: [('R_MIPS_LO16', 'D_800E0BE0')], 120: [('R_MIPS_HI16', 'D_800E0BFC')], 124: [('R_MIPS_LO16', 'D_800E0BFC')], 116: [('R_MIPS_HI16', 'D_800E0BE0')], 128: [('R_MIPS_LO16', 'D_800E0BE0')], 176: [('R_MIPS_HI16', 'D_800E0BFC')], 180: [('R_MIPS_LO16', 'D_800E0BFC')], 172: [('R_MIPS_HI16', 'D_800E0BE0')], 184: [('R_MIPS_LO16', 'D_800E0BE0')], 168: [('R_MIPS_HI16', 'D_800BE358')], 188: [('R_MIPS_LO16', 'D_800BE358')], 236: [('R_MIPS_26', 'func_151DD9E4')], 244: [('R_MIPS_26', 'func_151E7EF8')], 256: [('R_MIPS_HI16', 'D_8008FE30')], 260: [('R_MIPS_LO16', 'D_8008FE30')]}
PATCHES=(
    (0x24,0x3C060000,0x3C030000,[('R_MIPS_HI16', 'D_800BE358')],[('R_MIPS_HI16', 'D_800BE35A')]),
    (0x28,0x3C030000,0x240200CC,[('R_MIPS_HI16', 'D_800BE35A')],[]),
    (0x2C,0x24C60000,0x24630000,[('R_MIPS_LO16', 'D_800BE358')],[('R_MIPS_LO16', 'D_800BE35A')]),
    (0x30,0x240400CC,0x24040002,[],[]),
    (0x34,0x24630000,0x906E0000,[('R_MIPS_LO16', 'D_800BE35A')],[]),
    (0x38,0x24020002,0x308F0003,[],[]),
    (0x3C,0x2405001E,0x24840001,[],[]),
    (0x40,0x906E0000,0x01EEC004,[],[]),
    (0x44,0x304F0003,0x00581021,[],[]),
    (0x48,0x24420001,0x3059FFFF,[],[]),
    (0x4C,0x01EEC004,0x2881001E,[],[]),
    (0x50,0x00982021,0x03201025,[],[]),
    (0x54,0x3099FFFF,0x1420FFF7,[],[]),
    (0x58,0x03202025,0x24630001,[],[]),
    (0x5C,0x1445FFF8,0x3C080000,[],[('R_MIPS_HI16', 'D_800BE358')]),
    (0x60,0x24630001,0x95080000,[],[('R_MIPS_LO16', 'D_800BE358')]),
    (0x64,0x94CA0000,0x3C060000,[],[('R_MIPS_HI16', 'D_800E0BE0')]),
    (0x68,0x3C050000,0x24C60000,[('R_MIPS_HI16', 'D_800E0BE0')],[('R_MIPS_LO16', 'D_800E0BE0')]),
    (0x6C,0x24A50000,0x1328000E,[('R_MIPS_LO16', 'D_800E0BE0')],[]),
    (0x70,0x132A000D,0x80C50010,[],[]),
    (0x74,0x80A90010,0x3C020000,[],[('R_MIPS_HI16', 'D_800E0BE0')]),
    (0x78,0x3C080000,0x3C040000,[('R_MIPS_HI16', 'D_800E0BFC')],[('R_MIPS_HI16', 'D_800E0BFC')]),
    (0x7C,0x00A01025,0x24840000,[],[('R_MIPS_LO16', 'D_800E0BFC')]),
    (0x80,0x25080000,0x24420000,[('R_MIPS_LO16', 'D_800E0BFC')],[('R_MIPS_LO16', 'D_800E0BE0')]),
    (0x98,0x1448FFFB,0x1444FFFB,[],[]),
    (0xA0,0x10000011,0x10000012,[],[]),
    (0xA8,0x3C080000,0x3C030000,[('R_MIPS_HI16', 'D_800E0BFC')],[('R_MIPS_HI16', 'D_800BE358')]),
    (0xAC,0x00A01025,0x3C020000,[],[('R_MIPS_HI16', 'D_800E0BE0')]),
    (0xB0,0x00C01825,0x3C040000,[],[('R_MIPS_HI16', 'D_800E0BFC')]),
    (0xB4,0x25080000,0x24840000,[('R_MIPS_LO16', 'D_800E0BFC')],[('R_MIPS_LO16', 'D_800E0BFC')]),
    (0xB8,0x90640002,0x24420000,[],[('R_MIPS_LO16', 'D_800E0BE0')]),
    (0xBC,0x90650003,0x24630000,[],[('R_MIPS_LO16', 'D_800BE358')]),
    (0xC0,0x90660004,0x90690002,[],[]),
    (0xC4,0x90670005,0x906A0003,[],[]),
    (0xC8,0x24420004,0x906B0004,[],[]),
    (0xCC,0x24630004,0x906C0005,[],[]),
    (0xD0,0xA044FFFC,0x24420004,[],[]),
    (0xD4,0xA045FFFD,0x24630004,[],[]),
    (0xD8,0xA046FFFE,0xA049FFFC,[],[]),
    (0xDC,0xA047FFFF,0xA04AFFFD,[],[]),
    (0xE0,0x5448FFF6,0xA04BFFFE,[],[]),
    (0xE4,0x90640002,0x1444FFF6,[],[]),
    (0xE8,0x3C010000,0xA04CFFFF,[('R_MIPS_HI16', 'D_800E0BE0')],[]),
    (0xF0,0xA0290010,0xA0C50010,[('R_MIPS_LO16', 'D_800E0BE0')],[]),
    (0xFC,0x240B0001,0x240D0001,[],[]),
    (0x104,0xA02B0000,0xA02D0000,[('R_MIPS_LO16', 'D_8008FE30')],[('R_MIPS_LO16', 'D_8008FE30')]),
)
MAKE_RULE="# Keep normal-profile neighbors; select the settings loader's scalar checksum\n# and explicit four-byte groups from its no-unroll object.\n$(BUILD_DIR)/$(SRC_DIR)/game_33990.c.o: \\\n        $(SRC_DIR)/game_33990.c $(RETAIL_LAYOUT) ../tools/pad_c_object.py ../tools/pad_generated_object.py retail_word_patches.us.csv Makefile\n\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) $(MIPSBIT) -o $@.compact $<\n\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) -Wo,-loopunroll,0 $(MIPSBIT) -o $@.nounroll.compact $<\n\t$(PYTHON) ../tools/pad_c_object.py $@.compact $(RETAIL_LAYOUT) game_33990 $@.padded.s \\\n\t\t--function-object func_15007440=$@.nounroll.compact --word-patches retail_word_patches.us.csv --rodata-symbol $(RETAIL_RODATA_SYMBOL)\n\t$(AS) $(ASFLAGS) -o $@ $@.padded.s\n\trm -f $@.compact $@.nounroll.compact $@.padded.s\n\n"
EXCLUDE_OLD='$(BUILD_DIR)/$(SRC_DIR)/init_EB00.c.o $(BUILD_DIR)/$(SRC_DIR)/game_221290.c.o $(BUILD_DIR)/$(SRC_DIR)/game_476D0.c.o, \\\n'
EXCLUDE_NEW='$(BUILD_DIR)/$(SRC_DIR)/init_EB00.c.o $(BUILD_DIR)/$(SRC_DIR)/game_221290.c.o $(BUILD_DIR)/$(SRC_DIR)/game_476D0.c.o $(BUILD_DIR)/$(SRC_DIR)/game_33990.c.o, \\\n'

def make_states(live):
    anchor='# Only the two-row graphics initializer uses the retail no-unroll profile.\n'
    if live.count(MAKE_RULE)==1 and live.count(EXCLUDE_NEW)==1:return live.replace(MAKE_RULE,'',1).replace(EXCLUDE_NEW,EXCLUDE_OLD,1),live,True
    if MAKE_RULE not in live and live.count(EXCLUDE_OLD)==1 and live.count(anchor)==1:return live,live.replace(EXCLUDE_OLD,EXCLUDE_NEW,1).replace(anchor,MAKE_RULE+anchor,1),False
    raise ValueError('Settings loader Make profile state changed')

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(rom)-3,4):
        w=struct.unpack_from('>I',rom,at)[0]
        if w==ENTRY:pointers.append(at)
        if w>>26 in(2,3)and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if w>>26!=3:raise ValueError('Settings loader tail call changed')
            calls.append(at)
    if pointers or calls!=[0x49B84]:raise ValueError('Settings loader caller census changed')
    return calls

def freeze(root,out):
    manifest=out/'input-sha256.json'
    if not manifest.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze settings loader at predecessor ELF first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game/generated_48FD0.c','conker/asm/48FD0.s','conker/build/src/game/generated_48FD0.c.o','conker/src/game/generated_20AE20.c','conker/asm/20AE20.s','conker/build/src/game/generated_20AE20.c.o']
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/asm/nonmatchings/game_33990').glob('*.s')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        manifest.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(manifest.read_text());changed={SOURCE,OBJECT,ELF,GUARDS,MAKE,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Settings loader frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Settings loader protected input changed: '+name)
    return len(values)

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Settings loader raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Settings loader original body changed')
    result=bytearray(raw);out_bindings={at:r[:]for at,r in bindings.items()}
    for at,old,new,ob,nb in PATCHES:
        if struct.unpack_from('>I',result,at)[0]!=old or out_bindings.get(at,[])!=ob:raise ValueError('Settings loader expected word/relocation changed')
        struct.pack_into('>I',result,at,new)
        if nb:out_bindings[at]=nb[:]
        else:out_bindings.pop(at,None)
    expected=bytearray(truth)
    for at,rows in RETAIL_BINDINGS.items():struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&(0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000))
    if result!=expected or out_bindings!=RETAIL_BINDINGS:raise ValueError('Settings loader normalized words/bindings differ')
    return bytes(result)

def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Settings loader inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Settings loader already guarded')
    rows=[]
    for at,old,new,ob,nb in PATCHES:
        phase='checksum and address lifetime'if at<116 else'fill pointer allocation'if at<168 else'copy snapshot and delay schedule'if at<244 else'completion register allocation'
        reloc=lambda r:';'.join(k+':'+n for k,n in r)or'-'
        rows.append(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations=reloc(ob),replacement_relocations=reloc(nb),note='Normalize settings loader '+phase,insert_after='',insert_after_relocations='',omit='false'))
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(rows);return before+out.getvalue().encode()

def assemble_owner(root,out,obj,manifest,label,override=None):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/(FILENAME+'.c.s');result=p/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',FILENAME,rodata_symbol=RODATA_SYMBOL,word_patches_path=guards,function_objects={FUNCTION:override}if override else None))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Settings loader strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Settings loader predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Settings loader literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:35])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Settings loader named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text());bm,nm,mi=make_states((root/MAKE).read_text())
    if mi!=installed:raise ValueError('Partial settings loader profile installation')
    old_guards=(out/'frozen'/GUARDS).read_bytes();new_guards=guard_manifest(old_guards)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial settings loader guard installation')
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-normal');alt,ad=candidate.compile_owner(root,out,ns,'qualified-nounroll',True)
    if od or nd or ad:raise ValueError('Settings loader compiler diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];fitted=normalized(*function_blob(alt),truth);raw_neighbors=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Settings loader normal owner pools changed')
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner');new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner',alt)
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Settings loader live owner differs')
    if function_blob(new_owner)!=(fitted,RETAIL_BINDINGS):raise ValueError('Settings loader padded body/bindings differ')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Settings loader padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,old_owner,'predecessor-image');ne=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Settings loader live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>70I',truth)):raise ValueError('Settings loader body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Settings loader protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=70,frame=24,guards=len(PATCHES),bindings=len(BINDINGS),retail_bindings=len(RETAIL_BINDINGS),raw_neighbors=raw_neighbors,neighbors=neighbors,qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(new_guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=census(root),profile='target-only O2/g3/no-unroll')
    (out/'proposed-owner.c').write_text(ns);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=alt,qualified_normal=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
