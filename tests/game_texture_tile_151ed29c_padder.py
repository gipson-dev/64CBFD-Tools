"""Compare both supported padders and reject stale guard preimages."""
from pathlib import Path
import csv,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable';conker=root/'conker';name='func_151ED29C';obj=out/'coords-02.o'
rows=json.loads((out/'guard-rows.json').read_text());assert len(rows)==88
def run(kind,guards):
    if kind=='c':return pc.emit_padded_assembly(obj,conker/'retail_layout.us.txt','generated_215960',word_patches_path=guards)
    return pg.emit_padded_assembly(obj,conker/'asm/215960.s',filename='generated_215960',word_patches_path=guards)
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
for kind in ('c','generated'):
    asm=out/(kind+'-guarded.s');padded=out/(kind+'-guarded.o');asm.write_text(run(kind,out/'private-guards.csv'))
    p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(padded.relative_to(conker)),str(asm.relative_to(conker))],cwd=conker,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert struct.pack('>101I',*bound_blob(*payload(padded,name),symbols))==(conker/'conker.us.bin').read_bytes()[0x21a74c:0x21a8e0]
    assert same_functions(conker/'build/src/game/generated_215960.c.o',padded,(name,))==26
bad=out/'invalid-guards.csv';fields=list(rows[0]);rejected=0
def emit(items):
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(items);bad.write_text(stream.getvalue())
for i in range(len(rows)):
    for field in ('expected','expected_relocations'):
        copy=[dict(r) for r in rows];value=copy[i][field]
        copy[i][field]='0x%08X'%(int(value,0)^1) if field=='expected' else 'R_MIPS_LO16:incorrect_symbol'
        emit(copy)
        for kind in ('c','generated'):
            try:run(kind,bad)
            except ValueError as e:
                assert 'stale' in str(e).lower() or 'mismatch' in str(e).lower(),str(e)
                rejected+=1
            else:raise AssertionError((i,field,kind))
assert rejected==len(rows)*4
report={'guards':len(rows),'padders':2,'stale_preimage_rejections':rejected,'uncredited':True}
(out/'padder-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
