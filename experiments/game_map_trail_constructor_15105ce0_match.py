"""Complete constructor qualification, actual Make and literal whole-image gate."""
import csv,hashlib,json,os,re,shlex,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_map_trail_constructor_15105ce0_normalizer import normalize
from tools.tests.game_map_trail_constructor_15105ce0_proof import prove
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-map-trail-constructor-15105ce0-fit';BASE=PACKET/'baseline';OUT=PACKET/'qualified'
SPEC=json.loads(Path(__file__).with_name('game_map_trail_constructor_15105ce0_match_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object']
ENTRY,ROM,SIZE=SPEC['entry'],SPEC['rom'],940
GUARDS,ELF,PROGRESS='conker/retail_word_patches.us.csv','conker/build/conker.us.elf','conker/progress.csv'
sha=lambda b:hashlib.sha256(b).hexdigest()
diagnostics=lambda text:re.sub(r'\S+\.c, line \d+:','<owner>:',text)

def assemble(label,text,owner='generated_133190'):
 folder=OUT/label;folder.mkdir(parents=True,exist_ok=True)
 source=folder/(owner+'.c.s');obj=source.with_suffix('.o');source.write_text(text)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)],check=True,capture_output=True)
 return obj

def layout_assembly(rom):
 text=[]
 for row in pc.load_layout(ROOT/'conker/retail_layout.us.txt',SPEC['owner']):
  text.append('glabel '+row['name'])
  for address in range(row['address'],row['end'],4):
   at=ROM+address-ENTRY;word=struct.unpack_from('>I',rom,at)[0]
   text.append(f'/* {at:X} {address:08X} {word:08X} */ .word 0x{word:08X}')
 path=OUT/'independent-layout.s';path.write_text('\n'.join(text)+'\n');return path

def actual_Make(wanted,compact,guards,source=SOURCE,object_path=OBJECT,selected=None,label='target',functions=37):
 conker=ROOT/'conker';proposal=OUT/(label+'-proposed-source.c');proposal.write_text(SPEC['selected']if selected is None else selected)
 shadow=OUT/('make-'+label);target=shadow/Path(object_path).relative_to('conker/build');target.parent.mkdir(parents=True,exist_ok=True)
 command=['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()]
 plan=subprocess.run(command,cwd=conker,capture_output=True,text=True,check=True)
 (OUT/(label+'-Make-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[proposal.relative_to(conker).as_posix()if a==source.removeprefix('conker/')else guards.relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  redirect=None
  if '>'in args:
   assert args.count('>')==1 and args[-2]=='>'
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  q=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  assert q.returncode==0,q.stdout+q.stderr
  if args[0]=='../ido/ido5.3_recomp/cc':
   assert args.count('-O2')==args.count('-g3')==1
   assert diagnostics(q.stdout+q.stderr)==diagnostics((OUT/('after-diagnostics.txt'if source==SOURCE else label+'-after-diagnostics.txt')).read_text())
  else:assert not q.stderr and(not q.stdout or redirect is not None),q.stdout+q.stderr
  if redirect:redirect.write_text(q.stdout)
  commands.append(args)
 assert len(commands)==(5 if source==SOURCE else 3)
 assert target.read_bytes()==wanted.read_bytes(),'Actual Make object differs'
 assert same_functions(compact,Path(str(target)+'.compact'))==functions
 assert normalized_pools(compact)==normalized_pools(Path(str(target)+'.compact'))
 (OUT/(label+'-Make-commands.json')).write_text(json.dumps(commands,indent=2)+'\n')
 return dict(commands=len(commands),padded_object_equal=True,profile='existing O2/g3',mixed_GLOBAL_ASM_recipe=source==SOURCE)

def strict_image(actual):
 expected=(BASE/ELF).read_bytes()
 if sha(expected)!=SPEC['predecessor']['inputs'][ELF]or actual!=expected:raise ValueError('Constructor full image differs from literal frozen prediction')
 return 0

def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 mutable={SOURCE,OBJECT,ELF,GUARDS,PROGRESS,'README.md',*SPEC['dependencies'],*SPEC['new_files']}
 for name,text in SPEC['new_files'].items():assert(ROOT/name).read_text()==text,name
 for name,digest in SPEC['predecessor']['inputs'].items():
  path=BASE/name if(name in mutable or name.startswith('DOCS/'))and(BASE/name).is_file()else ROOT/name
  if sha(path.read_bytes())!=digest:raise ValueError('Frozen constructor input changed: '+name)
 live=(ROOT/SOURCE).read_text();assert live in(SPEC['old_source'],SPEC['selected']);installed=live==SPEC['selected']
 for name,dep in SPEC['dependencies'].items():assert(ROOT/name).read_text()==dep['new'if installed else'old']
 oldguards=(BASE/GUARDS).read_bytes();eol='\r\n'if b'\r\n'in oldguards else'\n'
 newguards=oldguards+SPEC['append_guards'].replace('\n',eol).encode()
 assert sha(newguards)==SPEC['new_guards_sha256']
 assert(ROOT/GUARDS).read_bytes()==(newguards if installed else oldguards)
 oldcsv=(BASE/PROGRESS).read_bytes();oldrow=b',func_15105CE0,353393888,940,asm'
 assert oldcsv.count(oldrow)==1
 newcsv=oldcsv.replace(oldrow,oldrow[:-3]+b'c')
 assert(ROOT/PROGRESS).read_bytes()==(newcsv if installed else oldcsv)
 guards=OUT/'proposed-guards.csv';guards.write_bytes(newguards);(OUT/'proposed-progress.csv').write_bytes(newcsv)
 before,bd=compile_owner(ROOT,OUT,SPEC['old_source'],'before')
 after,ad=compile_owner(ROOT,OUT,SPEC['selected'],'after')
 assert diagnostics(bd)==diagnostics(ad)and bd.count('cfe: Warning')==2
 raw,refs=payload(after,FUNCTION);normal,nrefs=normalize(raw,refs)
 assert sha(normal)==SPEC['original_raw_sha256']and json.loads(json.dumps(nrefs))==SPEC['original_refs']
 assert same_functions(before,after,(FUNCTION,))==36
 assert normalized_pools(before)==normalized_pools(after)
 original=assemble('original','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(ROOT/'conker/asm/nonmatchings/generated_133190/func_15105CE0.s').read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
 assert payload(original,FUNCTION)==payload(before,FUNCTION)==(normal,nrefs)
 syms={'memcpy':0x10022EC0,'bzero':0x100226F0}
 for rows in refs.values():
  for _,name in rows:
   if name not in syms:syms[name]=int(name.split('_')[1],16)
 words,truth=bound_blob(raw,refs,syms),bound_blob(normal,nrefs,syms)
 rom=(ROOT/'conker/conker.us.bin').read_bytes();assert struct.pack('>235I',*truth)==rom[ROM:ROM+SIZE]
 relation=prove(words,truth);(OUT/'CFG-relation.json').write_text(json.dumps(relation,indent=2)+'\n')
 options=dict(rodata_symbol='D_800A2420')
 old=assemble('before-pad',pc.emit_padded_assembly(before,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=BASE/GUARDS,**options))
 primary=assemble('after-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=guards,**options))
 assert old.read_bytes()==primary.read_bytes()
 assert(ROOT/OBJECT).read_bytes()==(primary if installed else old).read_bytes()
 assert payload(primary,FUNCTION)==(normal,nrefs)
 fullasm=layout_assembly(rom)
 independent=assemble('independent-pad',pg.emit_padded_assembly(after,fullasm,filename=SPEC['owner'],word_patches_path=guards,**options))
 assert same_functions(primary,independent)==37 and normalized_pools(primary)==normalized_pools(independent)
 make=actual_Make(primary,after,guards)
 dependencies={}
 for name,dep in SPEC['dependencies'].items():
  label=dep['owner'];db,bd=compile_owner(ROOT,OUT,dep['old'],label+'-before');da,ad=compile_owner(ROOT,OUT,dep['new'],label+'-after')
  assert diagnostics(bd)==diagnostics(ad)
  assert same_functions(db,da)==dep['functions']and normalized_pools(db)==normalized_pools(da)
  olddep=assemble(label+'-before-pad',pc.emit_padded_assembly(db,ROOT/'conker/retail_layout.us.txt',label,word_patches_path=BASE/GUARDS),label)
  newdep=assemble(label+'-after-pad',pc.emit_padded_assembly(da,ROOT/'conker/retail_layout.us.txt',label,word_patches_path=guards),label)
  assert olddep.read_bytes()==newdep.read_bytes()==(ROOT/dep['object']).read_bytes()
  dm=actual_Make(newdep,da,guards,source=name,object_path=dep['object'],selected=dep['new'],label=label,functions=dep['functions'])
  dependencies[name]=dict(functions=dep['functions'],pools_unchanged=True,complete_padded_object_equal=True,Make=dm)
 with patch.multiple(linker,FILENAME=SPEC['owner'],OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
  oldelf=linker.link_image(ROOT,OUT,old,'before-image');newelf=linker.link_image(ROOT,OUT,primary,'after-image')
 strict_image(oldelf.read_bytes());strict_image(newelf.read_bytes())
 assert(ROOT/ELF).read_bytes()==newelf.read_bytes()
 af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump')
 assert af==bf and aa==ba and bf[FUNCTION]==truth
 data=audit_layout(newelf,ROOT/'conker');assert data['exact']and not data['different_bytes']
 report=dict(body_words=235,raw_words=233,frame=216,raw_frame=216,guards=len(SPEC['guard_rows']),insertions=2,omissions=0,
             unchanged_owner_neighbors=36,pools_unchanged=True,Make=make,dependencies=dependencies,source_installed=installed,matching_credit=int(installed),
             strict_changed_bytes=0,exclusions=0,functions=len(af),all_addresses_fixed=True,protected_data=data,ELF_sha256=sha(newelf.read_bytes()))
 (OUT/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
 return dict(report=report,out=OUT,raw=raw,refs=refs,normal=normal,nrefs=nrefs,words=words,truth=truth,
             before=old,after=primary,original=original,elf=newelf,oldelf=oldelf,fullasm=fullasm,syms=syms)

if __name__=='__main__':print(json.dumps(prepare()['report']))
