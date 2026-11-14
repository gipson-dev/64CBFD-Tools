"""Check the peeled packet loop and its constant-folding derivation."""
from pathlib import Path
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable';name='func_150F1B48'
raw,refs=payload(out/'formatted.o',name);orig,trefs=payload(out/'retail.o',name)
w=list(struct.unpack('>87I',raw));truth=list(struct.unpack('>90I',orig));bound=bound_blob(raw,refs)
rom=struct.unpack('>90I',Path('conker/conker.us.bin').read_bytes()[0x11eff8:0x11f160])
assert [i for i,(a,b) in enumerate(zip(bound[:62],rom[:62])) if a!=b]==[21]
assert truth[63]==0x24020002 and truth[65]==0x00021880 and truth[68]==0x00621823 and truth[69]==0x00031840
assert [w[i]&65535 for i in (67,71,75,79)]==[190,196,202,208]
assert [0xb2+12,0xb8+12,0xbe+12,0xc4+12]==[190,196,202,208]
rows=json.loads((out/'guard-rows.json').read_text());inserted=[r for r in rows if r['insert_after']]
assert len(rows)==23 and [(r['offset'],r['insert_after']) for r in inserted]==[
    ('0xF8','0x24020002'),('0xFC','0x00021880'),('0x108','0x00031840')]
report={'compiled_words':87,'retail_words':90,'first_62_word_differences':[21],
        'inserted_instructions':3,'folded_x_values':[190,196,202,208],
        'finite_guest_semantics_only':True,'uncredited':True}
(out/'derive-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
