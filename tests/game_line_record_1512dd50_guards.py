"""Exercise both padders against stale preimages and relocation bindings."""
from pathlib import Path
import csv, io, json, sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable'
conker = root/'conker'
allrows = list(csv.DictReader(io.StringIO((out/'proposed-guards.csv').read_text())))
rows = [r for r in allrows if r['filename']=='game_15B200']
assert len(rows)==69 and all(r['function']=='func_1512DD50' for r in rows)
fields=list(rows[0])
retail=out/'synthetic-retail-layout.s'
retail.write_text('glabel func_1512DD50\n/* 000000 1512DD50 00000000 */ nop\n'
                  'glabel func_1512DEA4\n/* 000000 1512DEA4 00000000 */ nop\n'
                  '/* 000000 1512E13C 00000000 */ nop\n')
obj=out/'pointer-reuse-00.o'
bad=out/'invalid-guards.csv'
def emit(rows):
    stream=io.StringIO(newline='')
    w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    w.writeheader(); w.writerows(rows); bad.write_text(stream.getvalue())
def run(padder):
    if padder=='c':return pc.emit_padded_assembly(obj,conker/'retail_layout.us.txt','game_15B200',word_patches_path=bad)
    return pg.emit_padded_assembly(obj,retail,filename='game_15B200',word_patches_path=bad)
emit(rows)
for padder in ('c','generated'):run(padder)
rejections=0
reasons={}
for i in range(len(rows)):
    for field in ('expected','expected_relocations'):
        copy=[dict(r) for r in rows]
        value=copy[i][field]
        copy[i][field]='0x%08X'%(int(value,0)^1) if field=='expected' else 'R_MIPS_LO16:incorrect_symbol'
        emit(copy)
        for padder in ('c','generated'):
            try:run(padder)
            except ValueError as exc:
                message=str(exc)
                assert 'mismatch' in message.lower() or 'expected' in message.lower(),message
                reasons.setdefault(field,message[:180]);rejections+=1
            else:raise AssertionError((rows[i]['offset'],field,padder))
assert rejections==69*2*2
report={'rows':len(rows),'stale_word_or_relocation_rejections':rejections,
        'padders':2,'generated_padder_layout':'synthetic from retail slot boundaries','sample_reasons':reasons}
(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
