"""Prepare and check the guarded actor point effect proposal without installing it."""
import csv,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-actor-point-emit-150bed4c-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_actor_point_emit_150bed4c_manifest.json').read_text())
NAME,OWNER=MANIFEST['function'],MANIFEST['owner'];COMMENT='/* Emit the alternate point effect and its additional high-intensity effect. */'
FLAGS=('-O2','-g3')
def proposal(source):
 current=body(source,NAME)
 if current==MANIFEST['body']:
  if MANIFEST['declarations'] not in source or COMMENT not in source:raise ValueError('Installed declarations or comment changed')
  return source
 if current!='s32 func_150BED4C() {\n    return 0;\n}':raise ValueError('Unknown source body')
 marker='extern f32 D_800A00C0,D_800A00C4,D_800A00C8,D_800A00CC;'
 if source.count(marker)!=1 or MANIFEST['declarations'] in source:raise ValueError('Unexpected owner declarations')
 return source.replace(marker,marker+'\n'+MANIFEST['declarations'],1).replace(current,COMMENT+'\n'+MANIFEST['body'],1)
def payload(path):
 data,fs,rs=parse_object(path);at,n=fs[NAME]['value'],fs[NAME]['size']
 return data[at:at+n],{k-at:v for k,v in rs.items() if at<=k<at+n}
def assemble(text,tag):
 path=OUT/(tag+'.s');path.write_text(text);out=path.with_suffix('.o')
 cmd=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out),str(path)]
 z=subprocess.run(cmd,cwd=ROOT/'conker',capture_output=True,text=True)
 if z.returncode:raise ValueError(z.stderr)
 return out
def guards():
 base=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(base.decode()));fields=reader.fieldnames;existing=[r for r in reader if r['function']==NAME];rows=MANIFEST['guard_rows']
 if existing and existing!=rows:raise ValueError('Existing guard rows changed')
 if not existing:
  output=io.StringIO(newline='');w=csv.DictWriter(output,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in base else '\n');w.writerows(rows);base+=output.getvalue().encode()
 path=OUT/'proposed-guards.csv';path.write_bytes(base);return path
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/MANIFEST['source']).read_text();source=proposal(original)
 before,bd=compile_owner(ROOT,OUT,original,'baseline',FLAGS);after,ad=compile_owner(ROOT,OUT,source,'candidate',FLAGS)
 if same_functions(before,after,(NAME,))!=6 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors or diagnostics changed')
 text=(ROOT/MANIFEST['assembly']).read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;snippet=start+text.split(start,1)[1].split(end,1)[0]+end
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+snippet+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after);truth,trefs=payload(retail)
 if len(raw)!=356 or len(truth)!=356:raise ValueError('Wrong executable span')
 actual=struct.unpack('>89I',raw);expected=struct.unpack('>89I',truth);changes=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b or refs.get(4*i)!=trefs.get(4*i)]
 rows=MANIFEST['guard_rows'];fmt=lambda es:';'.join(t+':'+n for t,n in es) if es else '-'
 if len(rows)!=17 or changes!=[int(r['offset'],0)//4 for r in rows]:raise ValueError('Guard positions changed')
 for row in rows:
  i=int(row['offset'],0)//4
  if actual[i]!=int(row['expected'],0) or expected[i]!=int(row['replacement'],0) or fmt(refs.get(i*4))!=row['expected_relocations'] or fmt(trefs.get(i*4))!=row['replacement_relocations']:raise ValueError('Guard inputs changed')
 syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};raw_words=tuple(bound_blob(raw,refs,syms));retail_words=tuple(bound_blob(truth,trefs,syms));rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if retail_words!=struct.unpack_from('>89I',rom,MANIFEST['rom_offset']):raise ValueError('Retail image mismatch')
 return dict(source=source,before=before,after=after,retail=retail,raw_words=raw_words,retail_words=retail_words,symbols=syms,rom=rom,guards=guards(),installed=body(original,NAME)==MANIFEST['body'])
def pad_both(state,path=None):
 patches=state['guards'] if path is None else path
 a=pad_generated_object.emit_padded_assembly(state['after'],ROOT/MANIFEST['assembly'],filename=OWNER,word_patches_path=patches)
 b=pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=patches)
 one,two=assemble(a,'generated'),assemble(b,'generic')
 if payload(one)!=payload(two) or payload(one)!=payload(state['retail']) or same_functions(one,two)!=7:raise ValueError('Padders disagree')
 return one,two
