"""Prepare and qualify the actor script handler without installing it."""
import csv,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-script-150793d8-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_script_150793d8_manifest.json').read_text());NAME=MANIFEST['function'];OWNER=MANIFEST['owner']
COMMENT='/* Choose a bounded randomized path node near the player. */'
FLAGS=('-O2','-g3');RODATA='jtbl_8009A1E8_game'
def proposal(source):
 current=body(source,NAME)
 if current==MANIFEST['body']:
  if COMMENT not in source or source.count('void func_150793D8();')!=1:raise ValueError('Installed handler comment or declaration changed')
  return source
 if current!='s32 func_150793D8() {\n    return 0;\n}' or source.count('s32 func_150793D8();')!=1:raise ValueError('Unknown predecessor')
 source=source.replace('s32 func_150793D8();','void func_150793D8();',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_A28B0/func_150793D8.s. */\n'+current,COMMENT+'\n'+MANIFEST['body'],1)
 return source

def payload(path):
 data,fs,rs=parse_object(path);at,n=fs[NAME]['value'],fs[NAME]['size'];return data[at:at+n],{k-at:v for k,v in rs.items() if at<=k<at+n}

def assemble(text,tag):
 path=OUT/(tag+'.s');path.write_text(text);out=path.with_suffix('.o');cmd=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out),str(path)];z=subprocess.run(cmd,cwd=ROOT/'conker',capture_output=True,text=True)
 if z.returncode:raise ValueError(z.stderr)
 return out

def guards():
 base=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(base.decode()));fields=reader.fieldnames;existing=[r for r in reader if r['function']==NAME];rows=MANIFEST['guard_rows']
 if existing and existing!=rows:raise ValueError('Existing guard rows changed')
 if not existing:
  output=io.StringIO(newline='');w=csv.DictWriter(output,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in base else '\n');w.writerows(rows);base+=output.getvalue().encode()
 path=OUT/'proposed-guards.csv';path.write_bytes(base);return path
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/MANIFEST['source']).read_text();source=proposal(original);before,bd=compile_owner(ROOT,OUT,original,'baseline',FLAGS);after,ad=compile_owner(ROOT,OUT,source,'candidate',FLAGS)
 if same_functions(before,after,(NAME,))!=210 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors or diagnostics changed')
 if normalized_pools(before)!=normalized_pools(after) or sections(before)['.reginfo'][1]!=sections(after)['.reginfo'][1]:raise ValueError('Owner pools or register metadata changed')
 text=(ROOT/MANIFEST['assembly']).read_text();retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+text+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after);truth,trefs=payload(retail)
 if len(raw)!=408 or len(truth)!=408:raise ValueError('Wrong executable span')
 actual=struct.unpack('>102I',raw);expected=struct.unpack('>102I',truth)
 changes=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b or refs.get(4*i)!=trefs.get(4*i)]
 rows=MANIFEST['guard_rows'];fmt=lambda es:';'.join(t+':'+n for t,n in es) if es else '-'
 if len(rows)!=5 or changes!=[int(r['offset'],0)//4 for r in rows]:raise ValueError('Guard positions changed')
 for row in rows:
  i=int(row['offset'],0)//4
  if actual[i]!=int(row['expected'],0) or expected[i]!=int(row['replacement'],0) or fmt(refs.get(i*4))!=row['expected_relocations'] or fmt(trefs.get(i*4))!=row['replacement_relocations']:raise ValueError('Guard inputs changed')
 syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};raw_words=tuple(bound_blob(raw,refs,syms));retail_words=tuple(bound_blob(truth,trefs,syms));rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if retail_words!=struct.unpack_from('>102I',rom,MANIFEST['rom_offset']):raise ValueError('Retail image mismatch')
 return dict(source=source,before=before,after=after,retail=retail,raw_words=raw_words,retail_words=retail_words,symbols=syms,rom=rom,guards=guards(),installed=body(original,NAME)==MANIFEST['body'])

def pad_both(state,path=None):
 patches=state['guards'] if path is None else path;raw,refs=payload(state['after'])
 source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
  for typ,name in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+name+'\n'
  source+='.word 0x%08X\n'%word
 isolated=assemble(source+'.size '+NAME+',.-'+NAME+'\n','isolated');assert payload(isolated)==(raw,refs)
 layout=OUT/'isolated-layout.csv';layout.write_text('section,filename,function,address,end\ngame,game_A28B0,func_150793D8,0x150793D8,0x15079570\n')
 with patches.open(newline='') as f:
  reader=csv.DictReader(f);fields=reader.fieldnames;rows=[r for r in reader if r['function']==NAME and r['filename']==OWNER]
 isolated_patches=OUT/'isolated-guards.csv'
 with isolated_patches.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
 one=assemble(pad_generated_object.emit_padded_assembly(isolated,ROOT/MANIFEST['assembly'],filename=OWNER,word_patches_path=isolated_patches),'isolated-generated')
 two=assemble(pad_c_object.emit_padded_assembly(isolated,layout,OWNER,word_patches_path=isolated_patches),'isolated-generic')
 full=assemble(pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',OWNER,rodata_symbol='jtbl_8009A1E8_game',word_patches_path=patches),'full-generic')
 if not payload(one)==payload(two)==payload(full)==payload(state['retail']):raise ValueError('Padders disagree')
 if same_functions(ROOT/'conker/build/src/game_A28B0.c.o',full,(NAME,))!=210:raise ValueError('Padded owner neighbors changed')
 return one,full
