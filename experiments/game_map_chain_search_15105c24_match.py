"""Qualified two-column chain search, header dependencies and exact linked image."""
import hashlib,json,os,re,shlex,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_map_chain_search_15105c24_normalizer import normalize
from tools.tests.game_map_chain_search_15105c24_proof import prove
from tools.tests import game_map_chain_search_15105c24_debugger as debugger
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
SPEC=json.loads(Path(__file__).with_name('game_map_chain_search_15105c24_match_manifest.json').read_text())
PACKET=ROOT/'conker/build/game-map-chain-search-15105c24-private';OUT=PACKET/'qualified';BASE=PACKET/'baseline'
FUNCTION,SOURCE,OBJECT,ENTRY,ROM=SPEC['function'],SPEC['source'],SPEC['object'],SPEC['entry'],SPEC['rom']
GUARDS,ELF,PROGRESS='conker/retail_word_patches.us.csv','conker/build/conker.us.elf','conker/progress.csv'
sha=lambda b:hashlib.sha256(b).hexdigest()
def diagnostics(text):return re.sub(r'[\w./-]+\.c, line \d+:','<owner>:',text)
def headers(new):
 for name in('variables.h','functions.h'):
  source='conker/include/'+name;(OUT/name).write_text(SPEC['new_files'][source]if new else SPEC['old_files'][source])
def pair(old,new,label):
 headers(False);before,bd=compile_owner(ROOT,OUT,old,label+'-before')
 headers(True);after,ad=compile_owner(ROOT,OUT,new,label+'-after')
 return before,after,bd,ad
def assemble(label,text):
 folder=OUT/label;folder.mkdir(parents=True,exist_ok=True);s=folder/'game_131F30.c.s';obj=s.with_suffix('.o');s.write_text(text)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(s)],check=True,capture_output=True);return obj
def layout_assembly(rom):
 text=[]
 for row in pc.load_layout(ROOT/'conker/retail_layout.us.txt',SPEC['owner']):
  text.append('glabel '+row['name'])
  for address in range(row['address'],row['end'],4):
   at=ROM+address-ENTRY;word=struct.unpack_from('>I',rom,at)[0];text.append(f'/* {at:X} {address:08X} {word:08X} */ .word 0x{word:08X}')
 p=OUT/'independent-layout.s';p.write_text('\n'.join(text)+'\n');return p
def actual_Make(source,object_path,text,compact,guards,label,plain=False,expected=None):
 conker=ROOT/'conker';shadow=OUT/('make-'+label);target=shadow/Path(object_path).relative_to('conker/build');target.parent.mkdir(parents=True,exist_ok=True)
 proposal=OUT/(label+'-proposed.c')
 for name in('functions.h','variables.h'):
  text=text.replace('#include "'+name+'"','#include "'+(OUT/name).relative_to(conker).as_posix()+'"')
 proposal.write_text(text)
 command=['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix()]
 if plain:command+=['GLOBAL_ASM_C_FILES=']
 elif source==SOURCE:command+=['GLOBAL_ASM_C_FILES='+source.removeprefix('conker/')]
 plan=subprocess.run(command+[target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
 (OUT/(label+'-Make-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
 for line in plan.stdout.replace('\\\n','').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
  args=[proposal.relative_to(conker).as_posix()if a==source.removeprefix('conker/')else guards.relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
  redirect=None
  if '>'in args:
   assert args.count('>')==1 and args[-2]=='>';redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  q=subprocess.run(args,cwd=conker,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
  if args[0]=='../ido/ido5.3_recomp/cc':assert args.count('-O2')==args.count('-g3')==1
  else:assert not q.stderr and(not q.stdout or redirect is not None),q.stdout+q.stderr
  if redirect:redirect.write_text(q.stdout)
  commands.append(args)
 assert len(commands)in(3,5)and same_functions(compact,Path(str(target)+'.compact'))>0
 assert normalized_pools(compact)==normalized_pools(Path(str(target)+'.compact'))
 if expected is not None:assert target.read_bytes()==expected.read_bytes(),('actual Make object differs',label)
 (OUT/(label+'-Make-commands.json')).write_text(json.dumps(commands,indent=2)+'\n')
 return target,dict(commands=len(commands),padded_object_equal=expected is not None,plain_recipe=plain,profile='existing O2/g3')
def link_image(objects,label):
 directory=OUT/label;directory.mkdir(exist_ok=True);script=directory/'conker.ld';text=(ROOT/'conker/build/conker.ld').read_text()
 for old,new in objects.items():
  old=old.removeprefix('conker/');assert text.count(old)==1;text=text.replace(old,new.relative_to(ROOT/'conker').as_posix())
 script.write_text(text);elf=directory/'conker.us.elf'
 subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(ROOT/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(ROOT/'conker'))],cwd=ROOT/'conker',check=True,capture_output=True)
 return elf
def predicted_image():
 before=(BASE/ELF).read_bytes();assert sha(before)==SPEC['predecessor']['inputs'][ELF]
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION];assert len(rows)==1 and rows[0][2][1:3]==(ENTRY,188)
 expected=bytearray(before);struct.pack_into('>I',expected,rows[0][0]+8,184)
 assert sum(a!=b for a,b in zip(before,expected))==1
 return bytes(expected)
def strict_image(actual):
 if actual!=predicted_image():raise ValueError('Chain-search full image differs from one-field size prediction')
 return 1
def prepare():
 OUT.mkdir(exist_ok=True)
 live=(ROOT/SOURCE).read_text();assert live in(SPEC['old_source'],SPEC['selected']);installed=live==SPEC['selected']
 debug_audit=debugger.verify(ROOT,BASE)if installed else None
 mutable={*SPEC['new_files'],GUARDS,PROGRESS,OBJECT,ELF,'README.md'}
 for n,h in SPEC['predecessor']['inputs'].items():
  if installed and n==debugger.OBJECT:
   assert h==debugger.OLD and sha((ROOT/n).read_bytes())==debug_audit['after_sha256'];continue
  q=BASE/n if n in mutable or n.startswith('DOCS/')else ROOT/n
  assert sha(q.read_bytes())==h,('frozen input changed',n)
 for n,new in SPEC['new_files'].items():assert(ROOT/n).read_text()==(new if installed else SPEC['old_files'][n]),n
 oldguards=(BASE/GUARDS).read_bytes();eol='\r\n'if b'\r\n'in oldguards else'\n';newguards=oldguards+SPEC['append_guards'].replace('\n',eol).encode()
 assert sha(newguards)==SPEC['new_guards_sha256']and(ROOT/GUARDS).read_bytes()==(newguards if installed else oldguards)
 csvold=(BASE/PROGRESS).read_bytes();oldrow=b',func_15105C24,353393700,188,asm';assert csvold.count(oldrow)==1;csvnew=csvold.replace(oldrow,oldrow[:-3]+b'c')
 assert(ROOT/PROGRESS).read_bytes()==(csvnew if installed else csvold)
 guards=OUT/'proposed-guards.csv';guards.write_bytes(newguards);(OUT/'proposed-progress.csv').write_bytes(csvnew)
 before,after,bd,ad=pair(SPEC['old_source'],SPEC['selected'],'owner')
 assert diagnostics(bd)==diagnostics(SPEC['diagnostics_before'])and diagnostics(ad)==diagnostics(SPEC['diagnostics_after'])
 raw,refs=payload(after,FUNCTION);normal,nrefs=normalize(raw,refs)
 assert len(raw)==188 and len(normal)==184 and sha(normal)==SPEC['original_raw_sha256']and json.loads(json.dumps(nrefs))==SPEC['original_refs']
 assert payload(before,FUNCTION)==(normal+b'\0'*4,nrefs)and same_functions(before,after,(FUNCTION,))==10 and normalized_pools(before)==normalized_pools(after)
 asm=(ROOT/'conker/asm/nonmatchings/game_131F30/func_15105C24.s').read_text().split('endlabel '+FUNCTION)[0]+'endlabel '+FUNCTION+'\n'
 original=assemble('original','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm+'.size '+FUNCTION+',.-'+FUNCTION+'\n')
 assert payload(original,FUNCTION)==(normal,nrefs)
 rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=rom[ROM:ROM+188];assert sha(truth)==SPEC['retail_sha256']and truth[-4:]==b'\0'*4
 retail=bound_blob(normal,nrefs);words=bound_blob(raw,refs);assert struct.pack('>46I',*retail)==truth[:184]
 proof=prove(words,retail);(OUT/'relation.json').write_text(json.dumps(proof,indent=2)+'\n')
 a=assemble('before-pad',pc.emit_padded_assembly(before,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=BASE/GUARDS))
 b=assemble('after-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=guards))
 assert same_functions(a,b,(FUNCTION,))==10 and normalized_pools(a)==normalized_pools(b)
 assert payload(a,FUNCTION)==(normal+b'\0'*4,nrefs)and payload(b,FUNCTION)==(normal,nrefs)
 assert(ROOT/OBJECT).read_bytes()==(b if installed else a).read_bytes()
 fullasm=layout_assembly(rom);independent=assemble('independent-pad',pg.emit_padded_assembly(after,fullasm,filename=SPEC['owner'],word_patches_path=guards))
 assert same_functions(b,independent)==11 and normalized_pools(b)==normalized_pools(independent)
 headers(True);mixed,mixed_report=actual_Make(SOURCE,OBJECT,SPEC['selected'],after,guards,'owner-mixed',expected=b)
 plain,plain_report=actual_Make(SOURCE,OBJECT,SPEC['selected'],after,guards,'owner-plain',plain=True,expected=b)
 assert mixed_report['commands']==5 and plain_report['commands']==3
 objects={OBJECT:plain};dependencies={}
 for dep in SPEC['dependencies']:
  x,y,xd,yd=pair(dep['old'],dep['new'],dep['owner']);count=same_functions(x,y);assert normalized_pools(x)==normalized_pools(y)
  xs,ys=sections(x),sections(y);assert {n:v for n,v in xs.items()if n.startswith(('.text','.rodata','.data','.reginfo'))}=={n:v for n,v in ys.items()if n.startswith(('.text','.rodata','.data','.reginfo'))}
  actual,receipt=actual_Make(dep['source'],dep['object'],dep['new'],y,guards,dep['owner'],expected=ROOT/dep['object'])
  objects[dep['object']]=actual;dependencies[dep['source']]=dict(functions=count,normalized_pools_equal=True,loaded_sections_and_reginfo_equal=True,Make=receipt)
 oldelf=link_image({OBJECT:a},'before-image');elf=link_image(objects,'after-image');assert oldelf.read_bytes()==(BASE/ELF).read_bytes();strict_image(elf.read_bytes())
 af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
 assert af==bf and aa==ba and bf[FUNCTION]==retail+[0]
 data=audit_layout(elf,ROOT/'conker');assert data['exact']and not data['different_bytes']
 calls=[at for at in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,at)[0]==0x0C000000|((ENTRY>>2)&0x3FFFFFF)];assert calls==[0x18D084]
 report=dict(body_words=46,slot_words=47,raw_words=47,frame=0,guards=len(SPEC['guard_rows']),insertions=0,omissions=1,unchanged_owner_neighbors=10,dependencies=dependencies,debugger_metadata=debug_audit,mixed_Make=mixed_report,plain_Make=plain_report,source_installed=installed,matching_credit=int(installed),ELF_identical=False,strict_changed_bytes=1,symbol_size_before=188,symbol_size_after=184,exclusions=0,functions=len(af),all_addresses_fixed=True,conversion_rows=1,protected_data=data,ELF_sha256=sha(elf.read_bytes()),direct_call_sites=calls)
 (OUT/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
 return dict(report=report,out=OUT,raw=raw,refs=refs,truth=retail,words=words,after=b,compact=after,retail=original,elf=elf,oldelf=oldelf,fullasm=fullasm,normal=normal,normal_refs=nrefs)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
