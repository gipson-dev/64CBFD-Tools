"""Qualify view scaling against retail and its existing jump table."""
import csv,hashlib,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-view-scale-1500e738-durable'
MANIFEST=json.loads(Path(__file__).with_name('game_view_scale_1500e738_manifest.json').read_text())
NAME,OWNER='func_1500E738','game_3BA70'
ASM='conker/asm/nonmatchings/game_3BA70/func_1500E738.s'
sha=lambda text:hashlib.sha256(text.encode()).hexdigest()

def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('View scaling candidate context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)

def sources():
 result,states={},set()
 for name,spec in MANIFEST['paths'].items():
  current=(ROOT/spec['path']).read_text()
  if sha(current)==spec['before_sha256']:before,installed=current,False
  elif sha(current)==spec['after_sha256']:before,installed=apply(current,spec['changes'],True),True
  else:raise ValueError('Unknown view scaling input: '+spec['path'])
  after=apply(before,spec['changes'])
  if sha(before)!=spec['before_sha256'] or sha(after)!=spec['after_sha256']:raise ValueError('View scaling reconstruction failed')
  result[name]=(before,after);states.add(installed)
 if len(states)!=1:raise ValueError('Partial view scaling installation')
 return result,states.pop()

def assemble(text,label):
 asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
 result=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(asm)],cwd=ROOT/'conker',capture_output=True,text=True)
 if result.returncode:raise ValueError(result.stderr)
 return obj

def reset_object():
 reset=OUT/'reset.o';includes=['.','include','include/2.0L','include/2.0L/PR','include/libc','src/libultra/os','src/libultra/audio','src/libultra/io']
 cmd=[str(ROOT/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838',*[flag for path in includes for flag in ('-I',path)],'-O2','-g3','-Wo,-loopunroll,0','-mips2','-o32','-o',str(reset.relative_to(ROOT/'conker')),str((OUT/'variant-case1_default-processed.c').relative_to(ROOT/'conker'))]
 result=subprocess.run(cmd,cwd=ROOT/'conker',capture_output=True,text=True)
 if result.returncode:raise ValueError(result.stdout+result.stderr)
 return reset

def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for key,path in (('rom','conker/conker.us.bin'),('layout','conker/retail_layout.us.txt'),('assembly',ASM),('makefile','conker/Makefile')):
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=MANIFEST[key+'_sha256']:raise ValueError('View scaling input changed: '+path)
 texts,installed=sources();before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'variant-case1_default')
 if same_functions(before,after,(NAME,))!=5 or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('View scaling neighbor or diagnostics changed')
 if normalized_pools(before)==normalized_pools(after):raise ValueError('Expected compiler jump table missing')
 compact_sections=sections(after);old_sections=sections(before)
 if '.rodata' in old_sections or len(compact_sections['.rodata'][1])!=64:raise ValueError('Unexpected compact owner pool')
 _,fs,_=parse_object(after);values=struct.unpack('>16I',compact_sections['.rodata'][1]);mapped=[0x1500E738+(value-fs[NAME]['value']) for value in values]
 listing=subprocess.run(['mips-linux-gnu-readelf','-r',str(after)],capture_output=True,text=True,check=True).stdout.split("Relocation section '.rel.rodata'",1)[1]
 if sum('R_MIPS_32' in line and '.text' in line for line in listing.splitlines())!=16:raise ValueError('Jump-table relocations changed')
 game_addr,game=sections(ROOT/'conker/build/conker.us.elf')['.game_data'];retail_table=game[0x800961D0-game_addr:0x800961D0-game_addr+64]
 if mapped!=list(struct.unpack('>16I',retail_table)):raise ValueError('Compiler and retail jump tables differ')
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(ROOT/ASM).read_text()+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after,NAME);truth,truth_refs=payload(retail,NAME)
 if len(raw)!=344 or raw!=truth or {o for o in refs.keys()|truth_refs.keys() if refs.get(o)!=truth_refs.get(o)}!={0xA4,0xAC}:raise ValueError('View scaling body or table bindings changed')
 guards=OUT/'proposed-guards.csv';guards.write_text(texts['guards'][1]);rows=[r for r in csv.DictReader(io.StringIO(texts['guards'][1])) if r['function']==NAME]
 if rows!=MANIFEST['guard_rows'] or len(rows)!=2:raise ValueError('View scaling guard rows changed')
 reset=reset_object();emitted=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards,function_objects={'func_1500E5C0':reset})
 padded=assemble(emitted,'padded')
 if payload(padded,NAME)!=(truth,truth_refs) or same_functions(ROOT/'conker/build/src/game_3BA70.c.o',padded,(NAME,))!=5:raise ValueError('View scaling padded body or neighbors changed')
 if '.rodata' in sections(padded):raise ValueError('Compiler jump table leaked into production owner')
 addresses={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(truth,truth_refs,{s:addresses[s] for v in truth_refs.values() for _,s in v})
 if struct.pack('>86I',*words)!=(ROOT/'conker/conker.us.bin').read_bytes()[0x3BBE8:0x3BD40]:raise ValueError('View scaling retail ROM changed')
 link_owner(ROOT,OUT,after,OWNER)
 print('View scaling: 86 direct words, two checked table bindings, five unchanged neighbors',flush=True)
 return texts,installed

if __name__=='__main__':prepare()
