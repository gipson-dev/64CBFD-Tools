"""Fail-closed owner and relocation-aware line record qualification."""
import csv,hashlib,io,json,os,shutil,struct,subprocess
from pathlib import Path
from tools import pad_generated_object as pg
import sys
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-line-record-1512dd50-durable';NAME='func_1512DD50';OWNER='game_15B200'
MANIFEST=json.loads(Path(__file__).with_name('game_line_record_1512dd50_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()

def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('Line record source context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)

def sources():
 s=MANIFEST['source'];g=MANIFEST['guards'];current=(ROOT/s['path']).read_text();h=sha(current)
 if h==s['before_sha256']:before,installed=current,False
 elif h==s['after_sha256']:before,installed=apply(current,s['changes'],True),True
 else:raise ValueError('Unknown line record source state')
 after=apply(before,s['changes']);assert sha(before)==s['before_sha256'] and sha(after)==s['after_sha256']
 current=(ROOT/g['path']).read_text();suffix=g['append']
 if installed:
  if not current.endswith(suffix):raise ValueError('Line record guard suffix missing')
  old=current[:-len(suffix)];new=current
 else:old=current;new=current+suffix
 if sha(old)!=g['before_sha256'] or sha(new)!=g['after_sha256']:raise ValueError('Line record guard state changed')
 return {'source':(before,after),'guards':(old,new)},installed

def assemble(text,label):
 asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
 args=['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(ROOT/'conker')),str(asm.relative_to(ROOT/'conker'))]
 p=subprocess.run(args,cwd=ROOT/'conker',capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 return obj

def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for path,h in MANIFEST['inputs'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Line record input changed: '+path)
 texts,installed=sources()
 for path,h in MANIFEST['baseline'].items():
  dest=OUT/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():
   if installed:raise ValueError('Retained pre-install baseline required: '+path)
   if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise ValueError('Baseline changed: '+path)
   shutil.copyfile(ROOT/path,dest)
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=h:raise ValueError('Frozen baseline changed: '+path)
 (OUT/'pointer-reuse-00.c').write_text(texts['source'][1]);(OUT/'proposed-guards.csv').write_text(texts['guards'][1])
 before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'pointer-reuse-00')
 if same_functions(before,after,(NAME,))!=1 or normalized_pools(before)!=normalized_pools(after) or bd!=ad:raise ValueError('Line record owner or diagnostics changed')
 asm=(ROOT/'conker/asm/nonmatchings/game_15B200/func_1512DD50.s').read_text()
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after,NAME);truth,trefs=payload(retail,NAME)
 if len(raw)!=336 or len(truth)!=340:raise ValueError('Line record extent changed')
 w=list(struct.unpack('>84I',raw));retail_words=list(struct.unpack('>85I',truth))
 origins=list(range(14))+[18,20,16,17,14,19,21,15,23,None,27,22,28,25,29,30,34,32,33,31,35,36,37,38,39,40,41,42,43,44,45,49,47,66,None,46,50,51,52,53,54,56,58,59,60,62,48,55,61,57,63,64,65,67,68,69,70,71,72,73,74,75,76,79,77,78,80,81,83,82,24]
 assert len(origins)==85 and len(set(x for x in origins if x is not None))==83 and set(range(84))-set(x for x in origins if x is not None)=={26}
 edits={11:{6:16},18:{16:8},20:{16:10},16:{11:4},17:{6:18},14:{16:6},19:{11:4,6:2},21:{11:6,16:2,6:0},15:{16:6},23:{11:8,16:2},27:{11:10,16:0,6:0},22:{6:4},28:{11:18,6:10},25:{11:4,16:6,6:14},29:{16:10},30:{11:16,16:0,6:8},34:{6:10},32:{16:8},33:{16:4},31:{11:0,16:0,6:8},35:{11:4,16:14,6:6},36:{11:14,16:14,6:4},37:{16:6},38:{16:8},39:{16:10},40:{16:4},44:{11:6},49:{11:12},47:{11:6},51:{16:8},52:{11:2,16:8,6:10},53:{16:10},48:{16:8},55:{16:8,11:4},61:{21:8},57:{11:4,6:6},63:{11:8},65:{11:6,16:8,6:6},67:{16:6},68:{16:9},70:{16:9,11:10},71:{21:9},72:{11:10,6:4},75:{11:4,6:4},76:{16:4},79:{16:10},77:{16:12},78:{16:12},80:{16:10}}
 memory={50:(2,0x1c),53:(2,0x10),58:(2,0x14),62:(2,0x18),48:(3,0x20),68:(3,0x08),79:(3,0x1c)}
 inserted={23:0x46000086,48:0x24a306fc};result=[];newrefs={}
 for j,i in enumerate(origins):
  if i is None:value=inserted[j]
  else:
   value=w[i]
   for shift,reg in edits.get(i,{}).items():value=(value&~(31<<shift))|(reg<<shift)
   if i in memory:
    base,offset=memory[i];assert (value>>21)&31==5;value=(value&~((31<<21)|65535))|(base<<21)|offset
   if i*4 in refs:newrefs[j*4]=refs[i*4]
  result.append(value)
 if result!=retail_words or newrefs!=trefs:raise ValueError('Line record derivation or bindings changed')
 old=list(csv.DictReader(io.StringIO(texts['guards'][0])));new=list(csv.DictReader(io.StringIO(texts['guards'][1])))
 if new[:len(old)]!=old or new[len(old):]!=MANIFEST['guard_rows'] or len(new)-len(old)!=69:raise ValueError('Line record guard history changed')
 emitted=pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv');padded=assemble(emitted,'explicit-padded')
 if payload(padded,NAME)!=(truth,trefs) or same_functions(ROOT/'conker/build/src/game_15B200.c.o',padded,(NAME,))!=1:raise ValueError('Line record padded owner differs')
 addresses={r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};linked=bound_blob(truth,trefs,addresses)
 if struct.pack('>85I',*linked)!=(ROOT/'conker/conker.us.bin').read_bytes()[0x15b200:0x15b354]:raise ValueError('Line record retail bytes differ')
 print('Line record: 85 retail words, 69 checked guards, one unchanged neighbor; installed='+str(installed),flush=True)
 return texts,installed
if __name__=='__main__':prepare()
