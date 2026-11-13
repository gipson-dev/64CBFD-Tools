"""Recreate the script-query and camera-condition private qualification packet."""
import csv,hashlib,inspect,io,json,os,shutil,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-camera-condition-150be850-screen'
MANIFEST=json.loads(Path(__file__).with_name('game_camera_query_150be850_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
FIXTURES={'guest.py':'camera_guest','query-guest.py':'helper_guest','camera-connected.py':'connected','camera-dispatcher.py':'dispatcher','faults.py':'faults','query-native.py':'helper_native','camera-native.py':'camera_native'}
STUBS={'game/generated_C4DC0':'func_15099C14','game/generated_CBDB0':'func_1509ED74','game/generated_CD860':'func_150A04D8','game/generated_CCD00':'func_1509FE0C','game/generated_C3E20':'func_1509759C','game/generated_C9EC0':'func_1509DBBC','game/generated_CB3D0':'func_1509E3DC'}
RODATA={'generated_C9EC0':'jtbl_8009F1AC_game','generated_CD860':'jtbl_8009F550'}
def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  before,after=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];needle=item[before].splitlines(keepends=True)
  if lines[at:at+len(needle)]!=needle:raise ValueError('source patch context changed')
  lines[at:at+len(needle)]=item[after].splitlines(keepends=True)
 return ''.join(lines)
def assemble(text,label):
 src=OUT/(label+'.s');obj=OUT/(label+'.o');src.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
 if p.returncode:raise ValueError(p.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);proposals={}
 rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if hashlib.sha256(rom).hexdigest()!=MANIFEST['rom_sha256'] or hashlib.sha256((ROOT/'conker/retail_layout.us.txt').read_bytes()).hexdigest()!=MANIFEST['layout_sha256']:raise ValueError('retail image or layout changed')
 for owner,spec in MANIFEST['sources'].items():
  current=(ROOT/spec['path']).read_text()
  if owner=='game/generated_C9EC0' and sha(current) not in (spec['before_sha256'],spec['after_sha256']):
   from tools.experiments import game_query_list_1509dbbc_match as successor
   current=successor.historical_source(current)
  if sha(current)==spec['before_sha256']:old=current;new=apply(old,spec['changes'])
  elif sha(current)==spec['after_sha256']:new=current;old=apply(new,spec['changes'],True)
  else:raise ValueError('owner source changed: '+owner)
  if sha(old)!=spec['before_sha256'] or sha(new)!=spec['after_sha256']:raise ValueError('owner patch fingerprint mismatch: '+owner)
  proposals[owner]=(old,new)
 current=(ROOT/'conker/retail_word_patches.us.csv').read_text()
 fields=next(csv.reader(io.StringIO(current)));fp=io.StringIO(newline='');csv.DictWriter(fp,fieldnames=fields,lineterminator='\n').writerows(MANIFEST['guards']);suffix=fp.getvalue()
 if not current.endswith(suffix) and sha(current)!=MANIFEST['guards_sha256']:
  from tools.experiments import game_query_list_1509dbbc_match as successor
  current=successor.historical_guards(current)
 if current.endswith(suffix):base=current[:-len(suffix)];guardtext=current
 else:base=current;guardtext=current+suffix
 if sha(base)!=MANIFEST['guards_sha256']:raise ValueError('guard baseline changed')
 guards=OUT/'query-private-guards.csv';guards.write_text(guardtext)
 baseguards=OUT/'baseline-query-guards.csv';baseguards.write_text(base)
 oldobjects={}
 import tools.experiments.game_remaining_donor_candidates as source_module
 code=inspect.getsource(compile_owner);old="str(root / 'tools/asm-processor/asm_processor.py'), *flags,";new="str(root / 'tools/asm-processor/asm_processor.py'), *flags[:2],"
 if old not in code:raise ValueError('unexpected compiler helper')
 scope=dict(source_module.compile_owner.__globals__);exec(code.replace(old,new),scope);compile_profile=scope['compile_owner']
 compiled={}
 for i,(owner,(old,new)) in enumerate(proposals.items()):
  flags=('-O2','-g3','-Wo,-loopunroll,0') if owner=='game/generated_C9EC0' else ('-O2','-g3')
  oldobj,od=compile_profile(ROOT,OUT,old,'packet-%d-before'%i,flags)
  name='query-shape08' if owner=='game_C8950' else 'abi' if owner=='game/generated_EBD00' else 'packet-%d-after'%i
  newobj,nd=compile_profile(ROOT,OUT,new,name,flags)
  excluded=('func_1509BE40',) if owner=='game_C8950' else ('func_150BE850',) if owner=='game/generated_EBD00' else (STUBS[owner],) if owner in STUBS else ()
  same_functions(oldobj,newobj,excluded)
  if normalized_pools(oldobj)!=normalized_pools(newobj) or diagnostic_rows(od)!=diagnostic_rows(nd):raise ValueError('owner diagnostics or pools changed: '+owner)
  compiled[owner]=newobj;oldobjects[owner]=oldobj
 (OUT/'query-shape08.c').write_text(proposals['game_C8950'][1]);(OUT/'camera-abi-shape1.c').write_text(proposals['game/generated_EBD00'][1])
 camera='func_150BE850';assembly=(ROOT/'conker/asm/EBD00.s').read_text();a=assembly.index('glabel '+camera);b=assembly.index('endlabel '+camera,a)+len('endlabel '+camera)
 prefix='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
 retail=assemble(prefix+assembly[a:b]+'\n.size '+camera+',.-'+camera+'\n','retail');camera_obj=compiled['game/generated_EBD00']
 gen=assemble(pg.emit_padded_assembly(camera_obj,ROOT/'conker/asm/EBD00.s',word_patches_path=guards,filename='generated_EBD00'),'generated')
 generic=assemble(pc.emit_padded_assembly(camera_obj,ROOT/'conker/retail_layout.us.txt','generated_EBD00',word_patches_path=guards),'generic')
 if payload(gen,camera)!=payload(retail,camera) or payload(generic,camera)!=payload(retail,camera):raise ValueError('camera padding mismatch')
 helper='func_1509BE40';assembly=(ROOT/'conker/asm/nonmatchings/game_C8950/func_1509BE40.s').read_text();retail=assemble(prefix+assembly+'\n.size '+helper+',.-'+helper+'\n','query-retail');helper_obj=compiled['game_C8950']
 generic=assemble(pc.emit_padded_assembly(helper_obj,ROOT/'conker/retail_layout.us.txt','game_C8950',word_patches_path=guards),'query-generic')
 funcs=parse_object(helper_obj)[1];rows=[r for r in csv.DictReader(io.StringIO((ROOT/'conker/retail_layout.us.txt').read_text())) if r['filename']=='game_C8950' and r['function'] in funcs]
 if set(funcs)!={r['function'] for r in rows}:raise ValueError('synthetic layout function set changed')
 lines=[]
 for r in rows:lines.extend(['glabel '+r['function'],'/* 000000 %08X 00000000 */ nop'%int(r['address'],16)])
 lines.append('/* 000000 %08X 00000000 */ nop'%(int(rows[-1]['end'],16)-4));synthetic=OUT/'query-synthetic-retail.s';synthetic.write_text('\n'.join(lines)+'\n')
 generated=assemble(pg.emit_padded_assembly(helper_obj,synthetic,filename='game_C8950',word_patches_path=guards),'query-generated')
 if payload(generic,helper)!=payload(retail,helper) or payload(generated,helper)!=payload(retail,helper):raise ValueError('query padding mismatch')
 for i,(owner,name) in enumerate(STUBS.items()):
  filename=owner.rsplit('/',1)[1];asm=ROOT/('conker/asm/'+filename.removeprefix('generated_')+'.s');rodata=RODATA.get(filename)
  before=assemble(pg.emit_padded_assembly(oldobjects[owner],asm,filename=filename,word_patches_path=baseguards,rodata_symbol=rodata),'packet-stub-%d-before'%i)
  gen=assemble(pg.emit_padded_assembly(compiled[owner],asm,filename=filename,word_patches_path=guards,rodata_symbol=rodata),'packet-stub-%d-generated'%i)
  generic=assemble(pc.emit_padded_assembly(compiled[owner],ROOT/'conker/retail_layout.us.txt',filename,word_patches_path=guards,rodata_symbol=rodata),'packet-stub-%d-generic'%i)
  same_functions(before,gen);same_functions(before,generic)
 lookup={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 for obj,name,offset,size in ((OUT/'retail.o',camera,0xebd00,348),(OUT/'query-retail.o',helper,0xc92f0,368)):
  data,refs=payload(obj,name);words=bound_blob(data,refs,{n:lookup[n] for rows in refs.values() for _,n in rows})
  if struct.pack('>%dI'%len(words),*words)!=rom[offset:offset+size]:raise ValueError('assembled retail differs from input image: '+name)
 for target,suffix in FIXTURES.items():shutil.copyfile(Path(__file__).resolve().parents[1]/'tests'/('game_camera_query_150be850_'+suffix+'.py'),OUT/target)
 print('21 owners checked; both padders reproduce both retail functions and preserve seven placeholders')
 return proposals
