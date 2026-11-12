"""Prepare three sequenced alternate point callbacks without installing them."""
import csv,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-alternate-point-effect-triple-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_alternate_point_effect_triple_manifest.json').read_text())
NAMES=tuple(MANIFEST['functions']);OWNER=MANIFEST['owner'];RODATA=MANIFEST['rodata_symbol']
COMMENTS=('/* Submit the optional point effect before choosing the main effect. */','/* Submit the optional slot-6 point effect after the main effect. */','/* Submit the optional slot-11 point effect after the main effect. */')
def proposal(source):
 current=[body(source,n) for n in NAMES]
 if all(current[i]==MANIFEST['bodies'][n] for i,n in enumerate(NAMES)):
  if MANIFEST['declarations'] not in source or not all(c in source for c in COMMENTS):raise ValueError('Installed declarations or comments changed')
  return source
 if any(current[i]!='s32 '+n+'() {\n    return 0;\n}' for i,n in enumerate(NAMES)):raise ValueError('Unknown target source')
 marker='void func_15141F78(u8, u8 *, f32, u8, f32 *, u8);'
 if source.count(marker)!=1 or MANIFEST['declarations'] in source:raise ValueError('Unexpected owner declarations')
 source=source.replace(marker,marker+'\n'+MANIFEST['declarations'],1)
 for n,old,comment in zip(NAMES,current,COMMENTS):source=source.replace(old,comment+'\n'+MANIFEST['bodies'][n],1)
 return source
def payload(path,name):
 data,fs,rs=parse_object(path);at,n=fs[name]['value'],fs[name]['size'];return data[at:at+n],{k-at:v for k,v in rs.items() if at<=k<at+n}
def assemble(text,tag):
 path=OUT/(tag+'.s');path.write_text(text);out=path.with_suffix('.o');cmd=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out),str(path)];z=subprocess.run(cmd,cwd=ROOT/'conker',capture_output=True,text=True)
 if z.returncode:raise ValueError(z.stderr)
 return out
def guards():
 base=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(base.decode()));fields=reader.fieldnames;existing=[r for r in reader if r['function'] in NAMES];rows=MANIFEST['guard_rows']
 if existing and existing!=rows:raise ValueError('Existing guard rows changed')
 if not existing:
  output=io.StringIO(newline='');w=csv.DictWriter(output,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in base else '\n');w.writerows(rows);base+=output.getvalue().encode()
 path=OUT/'proposed-guards.csv';path.write_bytes(base);return path
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/MANIFEST['source']).read_text();source=proposal(original)
 before,bd=compile_owner(ROOT,OUT,original,'baseline');after,ad=compile_owner(ROOT,OUT,source,'candidate')
 if same_functions(before,after,NAMES)!=10 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors or diagnostics changed')
 if normalized_pools(before)!=normalized_pools(after):raise ValueError('Owner constant pools changed')
 text=(ROOT/MANIFEST['assembly']).read_text();rom=(ROOT/'conker/conker.us.bin').read_bytes();syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};retail={};raw_words={};retail_words={}
 for name,offset in zip(NAMES,MANIFEST['rom_offsets']):
  start='glabel '+name+'\n';end='endlabel '+name;snippet=start+text.split(start,1)[1].split(end,1)[0]+end
  target=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+snippet+'\n.size '+name+',.-'+name+'\n','retail-'+name);retail[name]=target
  raw,refs=payload(after,name);truth,trefs=payload(target,name)
  if len(raw)!=352 or len(truth)!=352 or refs!=trefs:raise ValueError('Target span or relocations changed: '+name)
  actual=struct.unpack('>88I',raw);expected=struct.unpack('>88I',truth);changes=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b];rows=[r for r in MANIFEST['guard_rows'] if r['function']==name]
  if len(rows)!=19 or changes!=[int(r['offset'],0)//4 for r in rows]:raise ValueError('Guard positions changed: '+name)
  for row in rows:
   i=int(row['offset'],0)//4
   if refs.get(i*4) or actual[i]!=int(row['expected'],0) or expected[i]!=int(row['replacement'],0):raise ValueError('Guard inputs changed')
  raw_words[name]=tuple(bound_blob(raw,refs,syms));retail_words[name]=tuple(bound_blob(truth,trefs,syms))
  if retail_words[name]!=struct.unpack_from('>88I',rom,offset):raise ValueError('Retail image mismatch')
 return dict(source=source,before=before,after=after,retail=retail,raw_words=raw_words,retail_words=retail_words,symbols=syms,rom=rom,guards=guards(),installed=all(body(original,n)==MANIFEST['bodies'][n] for n in NAMES))
def pad_both(state,path=None):
 patches=state['guards'] if path is None else path
 a=pad_generated_object.emit_padded_assembly(state['after'],ROOT/MANIFEST['assembly'],filename=OWNER,rodata_symbol=RODATA,word_patches_path=patches)
 b=pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',OWNER,rodata_symbol=RODATA,word_patches_path=patches)
 one,two=assemble(a,'generated'),assemble(b,'generic')
 if same_functions(one,two)!=13:raise ValueError('Padders differ')
 for n in NAMES:
  if payload(one,n)!=payload(two,n) or payload(one,n)!=payload(state['retail'][n],n):raise ValueError('Padders disagree on '+n)
 return one,two
