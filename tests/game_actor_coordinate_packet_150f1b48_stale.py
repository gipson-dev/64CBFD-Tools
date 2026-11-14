"""Require both padders to reject stale expected words and relocations."""
from pathlib import Path
import csv,io,json,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable';conker=root/'conker';obj=out/'formatted.o'
rows=json.loads((out/'guard-rows.json').read_text());assert len(rows)==23
fields=list(rows[0]);bad=out/'invalid-guards.csv'
def emit(items):
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(items);bad.write_text(stream.getvalue())
def run(kind):
    if kind=='c':return pc.emit_padded_assembly(obj,conker/'retail_layout.us.txt','generated_11C2B0',word_patches_path=bad)
    return pg.emit_padded_assembly(obj,conker/'asm/11C2B0.s',filename='generated_11C2B0',word_patches_path=bad)
emit(rows)
for kind in ('c','generated'):run(kind)
rejected=0
for i in range(len(rows)):
    for field in ('expected','expected_relocations'):
        copy=[dict(r) for r in rows];value=copy[i][field]
        copy[i][field]='0x%08X'%(int(value,0)^1) if field=='expected' else 'R_MIPS_LO16:incorrect_symbol'
        emit(copy)
        for kind in ('c','generated'):
            try:run(kind)
            except ValueError as e:
                assert 'stale' in str(e).lower() or 'mismatch' in str(e).lower(),str(e)
                rejected+=1
            else:raise AssertionError((i,field,kind))
report={'guards':len(rows),'padders':2,'stale_preimage_rejections':rejected,'uncredited':True};assert rejected==92
(out/'stale-guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
