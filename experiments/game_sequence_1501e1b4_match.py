"""Prepare and qualify the actor script handler without installing it."""
import csv,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_sequence_direction_1501fe68_match import compile_selected
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-script-1501e1b4-tests'
MANIFEST=json.loads(Path(__file__).with_name('game_sequence_1501e1b4_manifest.json').read_text());NAME=MANIFEST['function'];OWNER=MANIFEST['owner']
COMMENT='/* Advance the sequence transition and initiate its timed fade. */'
FLAGS=('-O2','-g3');RODATA='jtbl_8009A1E8_game'
def proposal(source):
 current=body(source,NAME)
 if current==MANIFEST['body']:
  if COMMENT not in source or MANIFEST['declarations'] not in source:raise ValueError('Installed declarations or comment changed')
  return source
 if current!='s32 func_1501E1B4() {\n    return 0;\n}':raise ValueError('Unknown predecessor')
 return source.replace(current,MANIFEST['declarations']+COMMENT+'\n'+MANIFEST['body'],1)

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
 OUT.mkdir(parents=True,exist_ok=True);original=(ROOT/MANIFEST['source']).read_text();source=proposal(original);before,bd=compile_selected(ROOT,OUT,original,'baseline');after,ad=compile_selected(ROOT,OUT,source,'candidate')
 if same_functions(before,after,(NAME,))!=56 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner neighbors or diagnostics changed')
 if normalized_pools(before)!=normalized_pools(after) or sections(before)['.reginfo'][1]!=sections(after)['.reginfo'][1]:raise ValueError('Owner pools or register metadata changed')
 text=(ROOT/MANIFEST['assembly']).read_text();text='glabel '+NAME+'\n'+text.split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME;retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+text+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after);truth,trefs=payload(retail)
 if len(raw)!=324 or (raw,refs)!=(truth,trefs):raise ValueError('Retail words or relocation bindings differ')
 syms={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};raw_words=tuple(bound_blob(raw,refs,syms));retail_words=tuple(bound_blob(truth,trefs,syms));rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if retail_words!=struct.unpack_from('>81I',rom,MANIFEST['rom_offset']):raise ValueError('Retail image mismatch')
 return dict(source=source,before=before,after=after,retail=retail,raw_words=raw_words,retail_words=retail_words,symbols=syms,rom=rom,guards=guards(),installed=body(original,NAME)==MANIFEST['body'])

def pad_both(state):
 x=assemble(pad_generated_object.emit_padded_assembly(state['after'],ROOT/MANIFEST['assembly'],filename=OWNER,word_patches_path=state['guards']),'generated')
 y=assemble(pad_c_object.emit_padded_assembly(state['after'],ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=state['guards']),'generic')
 if not payload(x)==payload(y)==payload(state['retail']):raise ValueError('Independent padders disagree')
 if same_functions(ROOT/'conker/build/src/game/generated_49D30.c.o',y,(NAME,))!=56:raise ValueError('Padded owner neighbors changed')
 return x,y
