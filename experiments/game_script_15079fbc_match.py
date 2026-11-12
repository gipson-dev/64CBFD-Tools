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
OUT=ROOT/'conker/build/game-script-15079fbc-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_script_15079fbc_manifest.json').read_text());NAME=MANIFEST['function'];OWNER=MANIFEST['owner']
COMMENT='/* Select the actor script or update the movement command from its speed. */'
FLAGS=('-O2','-g3');RODATA='jtbl_8009A1E8_game'
def proposal(source):
 current=body(source,NAME)
 if current==MANIFEST['body']:
  if COMMENT not in source or source.count('void func_15079FBC();')!=1:raise ValueError('Installed handler comment or declaration changed')
  return source
 if current!='s32 func_15079FBC() {\n    return 0;\n}' or source.count('s32 func_15079FBC();')!=1:raise ValueError('Unknown predecessor')
 source=source.replace('s32 func_15079FBC();','void func_15079FBC();',1).replace('/* Non-matching C placeholders for asm/nonmatchings/game_A28B0/func_15079FBC.s. */\n'+current,COMMENT+'\n'+MANIFEST['body'],1)
 start=source.index('// NON-MATCHING: JUSTREG\n// void func_15079FBC(void) {');end=source.index('void func_1507A100(void) {',start);source=source[:start]+source[end:]
 return source

def payload(path):
 data,fs,rs=parse_object(path);at,n=fs[NAME]['value'],fs[NAME]['size'];return data[at:at+n],{k-at:v for k,v in rs.items() if at<=k<at+n}

def assemble(text,tag):
 path=OUT/(tag+'.s');path.write_text(text);out=path.with_suffix('.o');cmd=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out),str(path)];z=subprocess.run(cmd,cwd=ROOT/'conker',capture_output=True,text=True)
 if z.returncode:raise ValueError(z.stderr)
 return out

def guards():
 base=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();rows=[r for r in csv.DictReader(io.StringIO(base.decode())) if r['function']==NAME]
 if rows:raise ValueError('Unexpected target guards')
 path=OUT/'proposed-guards.csv';path.write_bytes(base);return path

def prepare():
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/MANIFEST['source']).read_text();source=proposal(original);before,bd=compile_owner(ROOT,OUT,original,'baseline',FLAGS);after,ad=compile_owner(ROOT,OUT,source,'candidate',FLAGS)
 if same_functions(before,after,(NAME,))!=210 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors or diagnostics changed')
 if normalized_pools(before)!=normalized_pools(after) or sections(before)['.reginfo'][1]!=sections(after)['.reginfo'][1]:raise ValueError('Owner pools or register metadata changed')
 text=(ROOT/MANIFEST['assembly']).read_text();retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+text+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after);truth,trefs=payload(retail)
 if len(raw)!=324 or (raw,refs)!=(truth,trefs):raise ValueError('Retail words or relocation bindings differ')
 syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};raw_words=tuple(bound_blob(raw,refs,syms));retail_words=tuple(bound_blob(truth,trefs,syms));rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if retail_words!=struct.unpack_from('>81I',rom,MANIFEST['rom_offset']):raise ValueError('Retail image mismatch')
 return dict(source=source,before=before,after=after,retail=retail,raw_words=raw_words,retail_words=retail_words,symbols=syms,rom=rom,guards=guards(),installed=body(original,NAME)==MANIFEST['body'])

def pad_both(state):
 raw,refs=payload(state['after']);source='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
  for typ,name in refs.get(4*i,[]):source+='.reloc ., '+typ+', '+name+'\n'
  source+='.word 0x%08X\n'%word
 isolated=assemble(source+'.size '+NAME+',.-'+NAME+'\n','isolated');assert payload(isolated)==(raw,refs)
 layout=OUT/'isolated-layout.csv';layout.write_text('section,filename,function,address,end\ngame,game_A28B0,func_15079FBC,0x15079FBC,0x1507A100\n')
 x=assemble(pad_generated_object.emit_padded_assembly(isolated,ROOT/MANIFEST['assembly'],filename=OWNER),'isolated-generated')
 y=assemble(pad_c_object.emit_padded_assembly(isolated,layout,OWNER),'isolated-generic')
 full=assemble(pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',OWNER,rodata_symbol=RODATA,word_patches_path=state['guards']),'full-generic')
 if not payload(x)==payload(y)==payload(full)==payload(state['retail']):raise ValueError('Independent padders disagree')
 if same_functions(ROOT/'conker/build/src/game_A28B0.c.o',full,(NAME,))!=210:raise ValueError('Padded owner neighbors changed')
 return x,full
