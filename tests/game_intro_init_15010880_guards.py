from pathlib import Path
import csv,io,json,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-intro-init-15010880-durable';conker=root/'conker';text=(out/'proposed-guards.csv').read_text();rows=list(csv.DictReader(io.StringIO(text)));fields=list(rows[0]);selected=[i for i,r in enumerate(rows) if r['function']=='func_15010880'];assert len(selected)==11
retail=out/'synthetic-retail-layout.s';retail.write_text('''glabel func_15010780\n/* 000000 15010780 00000000 */ nop\nglabel func_15010880\n/* 000000 15010880 00000000 */ nop\nglabel func_150109D0\n/* 000000 150109D0 00000000 */ nop\n/* 000000 15010A5C 00000000 */ nop\n''')
obj=out/'typed.o';bad=out/'invalid-guards.csv';reject=0
for i in selected:
 for field in ('expected','expected_relocations'):
  copy=[dict(r) for r in rows];value=copy[i][field];copy[i][field]='0x%08X'%(int(value,0)^1) if field=='expected' else 'R_MIPS_LO16:incorrect_symbol'
  stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(copy);bad.write_text(stream.getvalue())
  for padder in ('c','generated'):
   try:
    if padder=='c':pc.emit_padded_assembly(obj,conker/'retail_layout.us.txt','game_3DC30',word_patches_path=bad)
    else:pg.emit_padded_assembly(obj,retail,filename='game_3DC30',word_patches_path=bad)
   except ValueError:reject+=1
   else:raise AssertionError((rows[i]['offset'],field,padder))
assert reject==44
report={'rows':11,'stale_word_or_relocation_rejections':reject,'padders':2,'generated_padder_layout':'synthetic from retail slot boundaries'};(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
