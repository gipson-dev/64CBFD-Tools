"""Fail-closed qualification for the selected menu-record loader."""
import csv,hashlib,io,json,os,runpy,shutil,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-menu-load-151e22bc-durable';NAME='func_151E22BC';OWNER='generated_20AE20'
MANIFEST=json.loads(Path(__file__).with_name('game_menu_load_151e22bc_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()

def apply(text,changes,reverse=False):
    lines=text.splitlines(keepends=True)
    for item in reversed(changes):
        old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
        if lines[at:at+len(expected)]!=expected:raise ValueError('Menu loader source context changed')
        lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
    return ''.join(lines)

def sources():
    s=MANIFEST['source'];current=(ROOT/s['path']).read_text();h=sha(current)
    if h==s['before_sha256']:before,installed=current,False
    elif h==s['after_sha256']:before,installed=apply(current,s['changes'],True),True
    else:raise ValueError('Unknown menu loader source state')
    after=apply(before,s['changes']);assert sha(before)==s['before_sha256'] and sha(after)==s['after_sha256']
    g=MANIFEST['guards'];current=(ROOT/g['path']).read_text();suffix=g['append']
    if installed:
        if not current.endswith(suffix):raise ValueError('Menu loader guard suffix missing')
        old=current[:-len(suffix)];new=current
    else:old=current;new=current+suffix
    if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Menu loader guards changed')
    m=MANIFEST['make'];current=(ROOT/m['path']).read_text()
    if installed:
        if sha(current)!=m['after_sha256'] or current.count(m['new'])!=1:raise ValueError('Menu loader Make profile changed')
        mb=current.replace(m['new'],m['old'])
    else:
        if sha(current)!=m['before_sha256'] or current.count(m['old'])!=1:raise ValueError('Menu loader Make profile changed')
        mb=current
    ma=mb.replace(m['old'],m['new'])
    if sha(mb)!=m['before_sha256'] or sha(ma)!=m['after_sha256']:raise ValueError('Menu loader Make history changed')
    return {'source':(before,after),'guards':(old,new),'make':(mb,ma)},installed

def assemble(text,label):
    asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
    argv=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(ROOT/'conker')),str(asm.relative_to(ROOT/'conker'))]
    p=subprocess.run(argv,cwd=ROOT/'conker',capture_output=True,text=True)
    if p.returncode:raise ValueError(p.stderr)
    return obj

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    for path,h in MANIFEST['inputs'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Menu loader input changed: '+path)
    texts,installed=sources()
    for path,h in MANIFEST['baseline'].items():
        dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            if installed:raise ValueError('Retained pre-install baseline required: '+path)
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Menu baseline changed: '+path)
            shutil.copyfile(ROOT/path,dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=h:raise ValueError('Frozen menu baseline changed: '+path)
    (OUT/'alias-00.c').write_text(texts['source'][1]);(OUT/'baseline-guards.csv').write_text(texts['guards'][0]);(OUT/'private-guards.csv').write_text(texts['guards'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
    before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'alias-00')
    if bd!=ad:raise ValueError('Menu owner diagnostics changed')
    _,fa,_=pg.parse_object(before);_,fb,_=pg.parse_object(after)
    if fa.keys()!=fb.keys():raise ValueError('Menu owner function inventory changed')
    changed=[n for n in fa if n!=NAME and payload(before,n)!=payload(after,n)]
    if changed!=['func_151E2404']:raise ValueError(('Unexpected menu owner changes',changed))
    x,xr=payload(before,'func_151E2404');y,yr=payload(after,'func_151E2404')
    if sum(a!=b for a,b in zip(x,y))!=1 or xr!=yr:raise ValueError('Neighbor table offset changed unexpectedly')
    oldpool=sections(before)['.rodata'][1];newpool=sections(after)['.rodata'][1]
    delta=fb['func_151E2404']['value']-fa['func_151E2404']['value']
    oldtable=struct.unpack_from('>10I',oldpool);newtable=struct.unpack_from('>10I',newpool,40)
    if len(oldpool)!=48 or len(newpool)!=80 or any(b-a!=delta for a,b in zip(oldtable,newtable)) or oldpool[40:]!=b'\0'*8:
        raise ValueError('Menu jump-table owner layout changed')
    brokenneedle='value=record[6];D_800E0BE0[0x11]=1;D_800E0BE0[3]=2;D_800E0BE0[0x13]=value;'
    brokenreplacement='D_800E0BE0[0x11]=1;D_800E0BE0[3]=2;D_800E0BE0[0x13]=record[6];'
    if texts['source'][1].count(brokenneedle)!=1:raise ValueError('Menu alias control changed')
    broken,diag=compile_owner(ROOT,OUT,texts['source'][1].replace(brokenneedle,brokenreplacement),'broken')
    if diag!=ad:raise ValueError('Menu negative-control diagnostics changed')
    asm=(ROOT/'conker/asm/20AE20.s').read_text();start=asm.index('glabel '+NAME+'\n');end=asm.index('endlabel '+NAME,start)+len('endlabel '+NAME)
    original=asm[start:end].replace('jlabel .L151E23E0\n','.L151E23E0:\n')
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+original+'\n.size '+NAME+',.-'+NAME+'\n','retail')
    derived=runpy.run_module('tools.tests.game_menu_load_151e22bc_derive',run_name='__menu_derivation__')
    if derived['issues'] or len(derived['result'])!=82:raise ValueError('Menu instruction derivation changed')
    old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
    if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=55:raise ValueError('Menu guard history changed')
    emitted=pg.emit_padded_assembly(after,ROOT/'conker/asm/20AE20.s',filename=OWNER,
            word_patches_path=OUT/'private-guards.csv',rodata_symbol='jtbl_800AB994')
    guarded=assemble(emitted,'guarded-private')
    symbols={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
    linked=bound_blob(*payload(guarded,NAME),symbols);truth=(ROOT/'conker/conker.us.bin').read_bytes()[0x20f76c:0x20f8b4]
    if struct.pack('>82I',*linked)!=truth:raise ValueError('Menu guarded retail bytes differ')
    print('Menu loader: 82 retail words, 55 guards, adjacent retail tables; installed='+str(installed),flush=True)
    return texts,installed
if __name__=='__main__':prepare()
