"""Verify both padders reject stale word and relocation preimages."""
from pathlib import Path
import csv,io,json,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable';conker=root/'conker'
allrows=list(csv.DictReader(io.StringIO((out/'private-guards.csv').read_text())))
rows=[r for r in allrows if r['function']=='func_151D2C40'];assert len(rows)==2
fields=list(rows[0]);bad=out/'invalid-guards.csv';obj=out/'portable-03.o'
layout=[r.split(',') for r in (conker/'retail_layout.us.txt').read_text().splitlines() if ',game_1FFF60,' in r]
assert len(layout)==19
retail=out/'synthetic-retail-layout.s';lines=[]
for _,_,name,start,end in layout:lines+=['glabel '+name,'/* 000000 %08X 00000000 */ nop'%int(start,0)]
lines+=['/* 000000 %08X 00000000 */ nop'%(int(layout[-1][-1],0)-4)]
retail.write_text('\n'.join(lines)+'\n')
def emit(rows):
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);bad.write_text(stream.getvalue())
def run(which):
    if which=='c':return pc.emit_padded_assembly(obj,conker/'retail_layout.us.txt','game_1FFF60',word_patches_path=bad)
    return pg.emit_padded_assembly(obj,retail,filename='game_1FFF60',word_patches_path=bad)
emit(rows)
for which in ('c','generated'):run(which)
rejected=0
for i in range(len(rows)):
    for field in ('expected','expected_relocations'):
        copy=[dict(r) for r in rows];value=copy[i][field]
        copy[i][field]='0x%08X'%(int(value,0)^1) if field=='expected' else 'R_MIPS_LO16:incorrect_symbol'
        emit(copy)
        for which in ('c','generated'):
            try:run(which)
            except ValueError as e:
                assert 'stale' in str(e).lower() or 'mismatch' in str(e).lower(),str(e);rejected+=1
            else:raise AssertionError((i,field,which))
assert rejected==8
report={'guards':len(rows),'padders':2,'stale_preimage_rejections':rejected,
        'generated_layout':'synthetic from retail boundaries','uncredited':True}
(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
