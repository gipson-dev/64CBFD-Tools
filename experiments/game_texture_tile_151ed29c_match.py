"""Fail-closed qualification of the texture-tile display-list builder."""
import csv,hashlib,io,json,os,re,shutil,struct,subprocess,sys
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
OUT=ROOT/'conker/build/game-texture-tile-151ed29c-durable';NAME='func_151ED29C';OWNER='generated_215960'
MANIFEST=json.loads(Path(__file__).with_name('game_texture_tile_151ed29c_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def apply(text,changes,reverse=False):
    lines=text.splitlines(keepends=True)
    for item in reversed(changes):
        old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
        if lines[at:at+len(expected)]!=expected:raise ValueError('Texture tile source context changed')
        lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
    return ''.join(lines)
def sources():
    s,g=MANIFEST['source'],MANIFEST['guards'];current=(ROOT/s['path']).read_text()
    if sha(current)==s['before_sha256']:before,installed=current,False
    elif sha(current)==s['after_sha256']:before,installed=apply(current,s['changes'],True),True
    else:raise ValueError('Unknown texture tile source state')
    after=apply(before,s['changes'])
    if sha(before)!=s['before_sha256'] or sha(after)!=s['after_sha256']:raise ValueError('Texture tile source hash changed')
    current,suffix=(ROOT/g['path']).read_text(),g['append']
    if installed:
        if not current.endswith(suffix):raise ValueError('Texture tile guard suffix missing')
        old,new=current[:-len(suffix)],current
    else:old,new=current,current+suffix
    if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Texture tile guard state changed')
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
    (OUT/'guard-rows.json').write_text(json.dumps(MANIFEST['guard_rows'],indent=2)+'\n');(OUT/'flow-alignment.json').write_text(json.dumps(MANIFEST['flow_alignment'],indent=2)+'\n')
    before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'coords-02')
    if same_functions(before,after,(NAME,))!=26 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors, pools or diagnostics changed')
    full=(ROOT/'conker/asm/215960.s').read_text();match=re.search(r'^glabel '+NAME+r'\n.*?^endlabel '+NAME+r'\s*$',full,re.M|re.S)
    if not match:raise ValueError('Original texture tile assembly missing')
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+NAME+',.-'+NAME+'\n','retail')
    raw,refs=payload(after,NAME);orig,trefs=payload(retail,NAME);w=list(struct.unpack('>102I',raw));truth=list(struct.unpack('>101I',orig))
    flow=MANIFEST['flow_alignment'];origins=flow['origins']
    if flow['unmatched'] or flow['unselected']!=[12] or len(set(origins))!=101 or set(range(102))-set(origins)!={12}:raise ValueError('Texture tile instruction alignment changed')
    if w[12]>>26!=12 or w[12]&65535!=31 or 48 in refs:raise ValueError('Shift mask preimage changed')
    for at,origin in enumerate(origins):
        value,wanted=w[origin],truth[at];op=value>>26
        if op==0:
            if (value&0x7ff)!=(wanted&0x7ff):raise ValueError('R opcode changed')
            fields=(21,16,11)
        elif op in (2,3):fields=()
        else:
            if value>>26!=wanted>>26 or value&65535!=wanted&65535:raise ValueError('Opcode or immediate changed')
            fields=(21,16)
        for shift in fields:
            a,b=value>>shift&31,wanted>>shift&31
            if a!=b:
                if not a or not b:raise ValueError('Unexplained zero register edit')
                value=(value&~(31<<shift))|(b<<shift)
        if value!=wanted or refs.get(origin*4,[])!=[x for x in trefs.get(at*4,[]) if x[0]!='R_MIPS_PC16']:raise ValueError('Instruction or binding derivation changed')
    old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
    if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=88:raise ValueError('Texture tile guard history changed')
    symbols={r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())};truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x21a74c:0x21a8e0]
    for kind in ('generated','c'):
        if kind=='generated':text=pg.emit_padded_assembly(after,ROOT/'conker/asm/215960.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv')
        else:text=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')
        padded=assemble(text,kind+'-guarded')
        if struct.pack('>101I',*bound_blob(*payload(padded,NAME),symbols))!=truth or same_functions(ROOT/'conker/build/src/game/generated_215960.c.o',padded,(NAME,))!=26:raise ValueError('Padded texture tile owner differs')
    shutil.copyfile(OUT/'generated-guarded.o',OUT/'guarded.o')
    print('Texture tile: 101 retail words, 88 checked guards, 26 unchanged neighbors; installed='+str(installed),flush=True)
    return texts,installed
if __name__=='__main__':prepare()
