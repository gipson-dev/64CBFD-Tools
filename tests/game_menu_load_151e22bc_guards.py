"""Check each target guard rejects stale words and relocation bindings."""
from pathlib import Path
import csv,io,json,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable';conker=root/'conker'
allrows=list(csv.DictReader(io.StringIO((out/'private-guards.csv').read_text())))
rows=[r for r in allrows if r['function']=='func_151E22BC'];assert len(rows)==55
fields=list(rows[0]);bad=out/'invalid-guards.csv';obj=out/'alias-00.o'
def emit(rows):
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);bad.write_text(stream.getvalue())
def run(padder):
    if padder=='c':return pc.emit_padded_assembly(obj,conker/'retail_layout.us.txt','generated_20AE20',rodata_symbol='jtbl_800AB994',word_patches_path=bad)
    return pg.emit_padded_assembly(obj,conker/'asm/20AE20.s',filename='generated_20AE20',rodata_symbol='jtbl_800AB994',word_patches_path=bad)
emit(rows)
for padder in ('c','generated'):run(padder)
count=0;reasons={}
for i in range(len(rows)):
    for field in ('expected','expected_relocations'):
        copy=[dict(r) for r in rows];value=copy[i][field]
        copy[i][field]='0x%08X'%(int(value,0)^1) if field=='expected' else 'R_MIPS_LO16:incorrect_symbol'
        emit(copy)
        for padder in ('c','generated'):
            try:run(padder)
            except ValueError as e:
                message=str(e);assert 'stale' in message.lower() or 'mismatch' in message.lower(),message
                reasons.setdefault(field,message[:180]);count+=1
            else:raise AssertionError((rows[i]['offset'],field,padder))
assert count==55*2*2
report={'rows':len(rows),'padders':2,'stale_word_or_relocation_rejections':count,'sample_reasons':reasons,'uncredited':True}
(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
