"""Fail-closed qualification of the 23-byte settings validator."""
import csv,hashlib,io,json,os,shutil,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-settings-validator-151dd9e4-durable';NAME='func_151DD9E4';OWNER='generated_20AE20'
MANIFEST=json.loads(Path(__file__).with_name('game_settings_validator_151dd9e4_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()

def apply(text,changes,reverse=False):
    lines=text.splitlines(keepends=True)
    for item in reversed(changes):
        old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
        if lines[at:at+len(expected)]!=expected:raise ValueError('Settings validator source context changed')
        lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
    return ''.join(lines)

def sources():
    s,g=MANIFEST['source'],MANIFEST['guards'];current=(ROOT/s['path']).read_text()
    if sha(current)==s['before_sha256']:before,installed=current,False
    elif sha(current)==s['after_sha256']:before,installed=apply(current,s['changes'],True),True
    else:raise ValueError('Unknown settings validator source state')
    after=apply(before,s['changes'])
    if sha(before)!=s['before_sha256'] or sha(after)!=s['after_sha256']:raise ValueError('Settings validator source hash changed')
    current,suffix=(ROOT/g['path']).read_text(),g['append']
    if installed:
        if not current.endswith(suffix):raise ValueError('Settings validator guard suffix missing')
        old,new=current[:-len(suffix)],current
    else:old,new=current,current+suffix
    if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Settings validator guard state changed')
    return {'source':(before,after),'guards':(old,new)},installed

def assemble(text,label):
    asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
    args=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(ROOT/'conker')),str(asm.relative_to(ROOT/'conker'))]
    p=subprocess.run(args,cwd=ROOT/'conker',capture_output=True,text=True)
    if p.returncode:raise ValueError(p.stderr)
    return obj

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    for path,digest in MANIFEST['inputs'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('Input changed: '+path)
    texts,installed=sources()
    for path,digest in MANIFEST['baseline'].items():
        dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            if installed:raise ValueError('Retained pre-install baseline required: '+path)
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('Baseline changed: '+path)
            shutil.copyfile(ROOT/path,dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:raise ValueError('Frozen baseline changed: '+path)
    (OUT/'formatted.c').write_text(texts['source'][1]);(OUT/'private-guards.csv').write_text(texts['guards'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
    (OUT/'guard-row.json').write_text(json.dumps(MANIFEST['guard_rows'],indent=2)+'\n')
    before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'return-00')
    if same_functions(before,after,(NAME,))!=59 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors, pools or diagnostics changed')
    raw,refs=payload(after,NAME);words=bound_blob(raw,refs)
    truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x20ae94:0x20b044];retail=list(struct.unpack('>108I',truth))
    if len(words)!=109 or words[:106]!=retail[:106] or words[106:]!=[0x24020017,0x03e00008,0] or retail[106:]!=[0x03e00008,0] or 424 in refs:raise ValueError('Unpadded derivation changed')
    old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
    if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=3:raise ValueError('Settings validator guard history changed')
    symbols={r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())}
    for kind in ('generated','c'):
        if kind=='generated':text=pg.emit_padded_assembly(after,ROOT/'conker/asm/20AE20.s',filename=OWNER,rodata_symbol='jtbl_800AB994',word_patches_path=OUT/'proposed-guards.csv')
        else:text=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,rodata_symbol='jtbl_800AB994',word_patches_path=OUT/'proposed-guards.csv')
        padded=assemble(text,kind+'-guarded')
        if struct.pack('>108I',*bound_blob(*payload(padded,NAME),symbols))!=truth or same_functions(ROOT/'conker/build/src/game/generated_20AE20.c.o',padded,(NAME,))!=59:raise ValueError('Padded settings validator owner differs')
    print('Settings validator: 108 retail words, three checked guards, 59 unchanged neighbors; installed='+str(installed),flush=True)
    return texts,installed
if __name__=='__main__':prepare()
