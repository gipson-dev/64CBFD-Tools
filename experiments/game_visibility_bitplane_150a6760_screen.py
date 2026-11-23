"""Private visibility bit-plane decoder recovery; no production match credit."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_visibility_bitplane_150a6760_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
 for n,d in MANIFEST['inputs'].items():assert sha(ROOT/n)==d,('Private screen input changed',n)
 assert (ROOT/MANIFEST['source']).read_text().count('s32 func_150A6760() {\n    return 0;\n}')==1
 assert sha(ROOT/'conker/build/conker.us.elf')==MANIFEST['production_ELF_sha256']
 OUT.mkdir(parents=True,exist_ok=True)
 for name,text in [('declarations.c',MANIFEST['declarations']),('initialized.c',MANIFEST['bodies']['initialized'])]:(OUT/name).write_text(text)
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
 from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.experiments.game_path_heading_turn_roles import bound_blob
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 prepare();beforeSource=(ROOT/MANIFEST['source']).read_text();where=OUT/'screen-baseline';where.mkdir(exist_ok=True)
 before,bd=compile_owner(ROOT,where,beforeSource,'before',('-O2','-g3'));rows={}
 symbols={n:v[1]for _,n,v,_ in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())if n}
 truth=struct.unpack_from('>64I',(ROOT/'conker/conker.us.bin').read_bytes(),0xD3C10)
 lo,hi=function_span(beforeSource,FUNCTION)
 for label,body in MANIFEST['bodies'].items():
  selected=beforeSource[:lo]+MANIFEST['declarations']+body.rstrip()+beforeSource[hi:];where=OUT/label;where.mkdir(exist_ok=True)
  after,ad=compile_owner(ROOT,where,selected,'candidate',('-O2','-g3'));raw,refs=payload(after,FUNCTION);words=bound_blob(raw,refs,symbols)
  q=dict(raw_words=len(words),retail_words=64,frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,overlap_word_differences=sum(a!=b for a,b in zip(words,truth)),size_difference=len(words)-64,neighbors=same_functions(before,after,(FUNCTION,)),pools_equal=normalized_pools(before)==normalized_pools(after),diagnostics_equal=diagnostic_rows(bd)==diagnostic_rows(ad),raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=False,matching_credit=0)
  assert q==MANIFEST['shapes'][label],(label,q,MANIFEST['shapes'][label]);rows[label]=q
 (OUT/'source-screen.json').write_text(json.dumps(rows,indent=2)+'\n');prepare();return rows
def census():
 from tools.experiments.game_actor_state_tick_integration import symbol_rows
 prepare();targets={0x150A6760,0x150A67D0};edges=[];pointers={hex(t):[]for t in targets}
 rom=(ROOT/'conker/conker.us.bin').read_bytes()
 for at,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  t=((w&0x3ffffff)<<2)|0x10000000
  if w>>26 in(2,3)and t in targets:edges.append((at*4,w,t))
  if w in targets:pointers[hex(w)].append(at*4)
 assert edges==[(0xD3CB4,0x094299F4,0x150A67D0),(0x13D198,0x0D4299D8,0x150A6760)]and not any(pointers.values())
 symbols={n:v for _,n,v,_ in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())if n}
 alias=symbols['func_150A67D0'];assert alias[1]==0x150A67D0 and alias[5]==0xFFF1,alias
 assert len([x for x in(ROOT/'conker/retail_layout.us.txt').read_text().splitlines()if ',func_150A6760,'in x])==1
 assert ',func_150A67D0,'not in(ROOT/'conker/retail_layout.us.txt').read_text()
 q=dict(direct_edges=edges,exact_word_pointers=pointers,interior_label_is_absolute_symbol=True,source_installed=False,matching_credit=0,limits='Literal direct-edge and exact-word pointer census only; computed or separately materialized pointers are not excluded. Full caller execution and legal plane domain remain open.')
 (OUT/'caller-census-qualified.json').write_text(json.dumps(q,indent=2)+'\n');return q
