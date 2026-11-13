"""Qualify the direct owner-mode callback and its preserved retail table."""
import csv,hashlib,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-owner-mode-1514ea1c-qualified'
MANIFEST=json.loads(Path(__file__).with_name('game_owner_mode_1514ea1c_direct_manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')

def assemble(text,label):
    src=OUT/(label+'.s');obj=OUT/(label+'.o');src.write_text(text)
    r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
    if r.returncode:raise ValueError(r.stderr)
    return obj

def prepare():
    OUT.mkdir(parents=True,exist_ok=True);spec=MANIFEST;name=spec['name'];jtbl=spec['table']
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    if sha(rom)!=spec['rom_sha256']:raise ValueError('Retail input changed')
    guards=ROOT/'conker/retail_word_patches.us.csv';gb=guards.read_bytes()
    if sha(norm(gb))!=spec['guard_sha256_normalized'] or any(r['function']==name for r in csv.DictReader(io.StringIO(gb.decode()))):raise ValueError('Guard baseline changed')
    source=norm((ROOT/spec['source']).read_bytes());old=spec['old_source'].encode();selected=spec['selected_source'].encode()
    makefile=norm((ROOT/'conker/Makefile').read_bytes());oldmake=spec['old_makefile'].encode();selectedmake=spec['selected_makefile'].encode()
    if source not in (old,selected) or sha(old)!=spec['baseline_sha256']:raise ValueError('Owner source changed')
    if makefile not in (oldmake,selectedmake) or sha(oldmake)!=spec['makefile_sha256']:raise ValueError('Makefile baseline changed')
    before,bd=compile_owner(ROOT,OUT,spec['old_source'],'before');after,ad=compile_owner(ROOT,OUT,spec['selected_source'],'after')
    if same_functions(before,after,(name,))!=77 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors or diagnostics changed')
    bp,ap=normalized_pools(before),normalized_pools(after)
    if bp['.data']!=ap['.data'] or bp['.rodata'] is not None:raise ValueError('Owner pool baseline changed')
    table=struct.unpack_from('>10I',rom,0x24a8e0);expected=tuple((i*4,name,v-0x1514ea1c) for i,v in enumerate(table))
    if ap['.rodata']!=(bytes(48),expected):raise ValueError('Compiled jump table differs from retail entries')
    asm=(ROOT/spec['assembly']).read_text();fragment='glabel '+name+'\n'+asm.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]+'endlabel '+name
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+name+',.-'+name+'\n','retail')
    raw,refs=payload(after,name);truth,trefs=payload(retail,name);mapped={off:[(kind,jtbl if sym=='.rodata' else sym)for kind,sym in rows]for off,rows in refs.items()}
    if len(raw)!=336 or sha(raw)!=spec['raw_sha256'] or (raw,mapped)!=(truth,trefs):raise ValueError('Raw body or bindings differ')
    generated=assemble(pg.emit_padded_assembly(after,ROOT/spec['assembly'],filename=spec['owner'],word_patches_path=guards,rodata_symbol=jtbl),'generated')
    generic=assemble(pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',spec['owner'],word_patches_path=guards,rodata_symbol=jtbl),'generic')
    oldp=assemble(pg.emit_padded_assembly(before,ROOT/spec['assembly'],filename=spec['owner'],word_patches_path=guards),'padded-before')
    if payload(generated,name)!=(truth,trefs) or payload(generic,name)!=(truth,trefs) or same_functions(oldp,generated,(name,))!=77:raise ValueError('Padding or owner neighbors differ')
    return dict(before=before,after=after,retail=retail,generated=generated,generic=generic,installed=source==selected)
