"""Fail-closed qualification of the actor coordinate-packet routine."""
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
OUT=ROOT/'conker/build/game-actor-coordinate-packet-150f1b48-durable';NAME='func_150F1B48';OWNER='generated_11C2B0'
MANIFEST=json.loads(Path(__file__).with_name('game_actor_coordinate_packet_150f1b48_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def apply(text,changes,reverse=False):
    lines=text.splitlines(keepends=True)
    for item in reversed(changes):
        old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
        if lines[at:at+len(expected)]!=expected:raise ValueError('Coordinate packet source context changed')
        lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
    return ''.join(lines)
def sources():
    texts={};states=[]
    for name in ('source','caller','actor_declaration','variables'):
        s=MANIFEST[name];current=(ROOT/s['path']).read_text()
        if sha(current)==s['before_sha256']:before,installed=current,False
        elif sha(current)==s['after_sha256']:before,installed=apply(current,s['changes'],True),True
        else:raise ValueError('Unknown coordinate packet '+name+' state')
        after=apply(before,s['changes'])
        if sha(before)!=s['before_sha256'] or sha(after)!=s['after_sha256']:raise ValueError('Coordinate packet '+name+' hash changed')
        texts[name]=(before,after);states.append(installed)
    if len(set(states))!=1:raise ValueError('Coordinate packet source, caller or declarations differ')
    installed=states[0];g=MANIFEST['guards'];current=(ROOT/g['path']).read_text();suffix=g['append']
    if installed:
        if not current.endswith(suffix):raise ValueError('Coordinate packet guard suffix missing')
        old,new=current[:-len(suffix)],current
    else:old,new=current,current+suffix
    if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Coordinate packet guard state changed')
    texts['guards']=(old,new);return texts,installed
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
    (OUT/'formatted.c').write_text(texts['source'][1]);(OUT/'caller-after.c').write_text(texts['caller'][1]);(OUT/'actor-declaration-after.c').write_text(texts['actor_declaration'][1]);(OUT/'variables-after.h').write_text(texts['variables'][1]);(OUT/'private-guards.csv').write_text(texts['guards'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
    (OUT/'guard-rows.json').write_text(json.dumps(MANIFEST['guard_rows'],indent=2)+'\n')
    before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'formatted')
    if same_functions(before,after,(NAME,))!=43 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Target neighbors, pools or diagnostics changed')
    ca,cd=compile_owner(ROOT,OUT,texts['caller'][0],'caller-before');cb,ce=compile_owner(ROOT,OUT,texts['caller'][1],'caller-after')
    if same_functions(ca,cb)!=10 or normalized_pools(ca)!=normalized_pools(cb) or diagnostic_rows(cd)!=diagnostic_rows(ce):raise ValueError('Caller object function, pool or diagnostics changed')
    full=(ROOT/'conker/asm/11C2B0.s').read_text();match=re.search(r'^glabel '+NAME+r'\n.*?^endlabel '+NAME+r'\s*$',full,re.M|re.S)
    if not match:raise ValueError('Original coordinate packet assembly missing')
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+NAME+',.-'+NAME+'\n','retail')
    raw,refs=payload(after,NAME);orig,trefs=payload(retail,NAME);w=list(struct.unpack('>87I',raw));original=list(struct.unpack('>90I',orig))
    linked=bound_blob(raw,refs);truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x11eff8:0x11f160];rom=list(struct.unpack('>90I',truth))
    if [i for i,(a,b) in enumerate(zip(linked[:62],rom[:62])) if a!=b]!=[21]:raise ValueError('Coordinate packet prefix changed')
    if [original[i] for i in (63,65,68,69)]!=[0x24020002,0x00021880,0x00621823,0x00031840] or [w[i]&65535 for i in (67,71,75,79)]!=[190,196,202,208]:raise ValueError('Peeled loop derivation changed')
    old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
    if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=23:raise ValueError('Coordinate packet guard history changed')
    symbols={r[1]:r[2][1] for r in symbol_rows((OUT/'frozen/conker/build/conker.us.elf').read_bytes())}
    for kind in ('generated','c'):
        if kind=='generated':text=pg.emit_padded_assembly(after,ROOT/'conker/asm/11C2B0.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv')
        else:text=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')
        padded=assemble(text,kind+'-guarded')
        if struct.pack('>90I',*bound_blob(*payload(padded,NAME),symbols))!=truth or same_functions(ROOT/'conker/build/src/game/generated_11C2B0.c.o',padded,(NAME,))!=43:raise ValueError('Padded coordinate packet owner differs')
    print('Coordinate packet: 90 retail words, 23 checked guards, 43 unchanged neighbors and 10 unchanged caller functions; installed='+str(installed),flush=True)
    return texts,installed
if __name__=='__main__':prepare()
