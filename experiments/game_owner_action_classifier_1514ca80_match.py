"""Complete 439-word owner/level action classifier and table binding audit."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_owner_action_classifier_1514ca80_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x1514CA80;ROM=0x179F30;WORDS=439
r=ROOT;o=OUT;b=o/'baseline';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly as _assembly
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
def assembly(data,refs,name=FUNCTION):return _assembly(data,refs,name)
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_CHECKED=False
def prepare():
 global _CHECKED
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
 allowed.update(MANIFEST.get('tool_task_overrides',{}))
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==MANIFEST.get('tool_task_overrides',{}).get(n,allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==(MANIFEST['guards_sha256'] if live else MANIFEST['inputs']['conker/retail_word_patches.us.csv']);_CHECKED=True;return live



import re
from tools.match_progress import load_symbol_addrs
from tools.tests.game_owner_action_dispatch_1514d15c_classifier_abi import at
fn=FUNCTION;owner=MANIFEST['filename'];neighbor='func_1514EA1C'
def compile_owner(root, out, source, name, flags=('-O2', '-g3')):
    raw, processed, obj = (out / (name + suffix) for suffix in ('.c', '-processed.c', '.o'))
    raw.write_text(source)
    processor = [sys.executable, str(TOOLROOT / 'asm-processor/asm_processor.py'), *flags,
        str(raw.relative_to(root / 'conker'))]
    preprocess = subprocess.run(processor, cwd=root / 'conker', capture_output=True, text=True, check=True)
    if preprocess.stderr:
        raise ValueError(preprocess.stderr)
    processed.write_text(preprocess.stdout)
    includes = ['.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
        'src/libultra/os', 'src/libultra/audio', 'src/libultra/io']
    command = [str(root / 'ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-D_LANGUAGE_C', '-D_FINALROM',
        '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', '-woff', '649,838',
        *[flag for path in includes for flag in ('-I', path)], *flags, '-mips2', '-o32',
        '-o', str(obj.relative_to(root / 'conker')), str(processed.relative_to(root / 'conker'))]
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    (out / (name + '-diagnostics.txt')).write_text(diagnostics)
    if result.returncode:
        raise ValueError(diagnostics)
    subprocess.run([*processor, '--post-process', str(obj.relative_to(root / 'conker')),
        '--assembler', 'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
        '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=root / 'conker',
        capture_output=True, text=True, check=True)
    return obj, diagnostics
def assemble(text,path):
 f=path.with_suffix('.s');f.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def objects():
 prepare()
 full=(b/MANIFEST['asm']).read_text();body=full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0];original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+body+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';original=re.sub(r'^([ \t]*)jlabel[ \t]+([^ \t\r\n]+)[ \t]*$',r'\1\2:',original,flags=re.M);assemble(original,o/'original-target.o')
 selected=MANIFEST['selected_source'];(o/'selected-source.c').write_text(selected);assert hashlib.sha256(selected.encode()).hexdigest()=='f658184ee0ac81673b7f80c165897e72d32ff1a94c420ada11048b26d8400c11'
 before,bd=compile_owner(r,o,(b/'conker/src/game/generated_179F30.c').read_text(),'before-owner');new,ad=compile_owner(r,o,selected,'selected-owner');assert diagnostic_rows(bd)==diagnostic_rows(ad) and sum(diagnostic_rows(ad).values())==4
 assert same_functions(before,new,(fn,neighbor))==76
 raw,refs=payload(new,fn);truth,tr=payload(o/'original-target.o',fn);assert len(raw)==len(truth)==1756 and len(refs)==len(tr)==10
 syms=load_symbol_addrs(str(r/'conker/symbol_addrs.us.txt'));syms['.rodata']=0x800A59AC
 for n in {n for rows in tr.values()for _,n in rows}:syms[n]=int(n.split('_',1)[1],16)
 assert bound_blob(raw,refs,syms)==bound_blob(truth,tr,syms)
 assert struct.pack('>439I',*bound_blob(truth,tr,syms))==(r/'conker/conker.us.bin').read_bytes()[0x179F30:0x17A60C]
 oldpool=normalized_pools(before);newpool=normalized_pools(new);assert oldpool['.data']==newpool['.data']==None
 oldbytes,oldids=oldpool['.rodata'];newbytes,newids=newpool['.rodata'];assert oldbytes==bytes(48) and newbytes==bytes(1120) and len(oldids)==10 and len(newids)==280
 assert tuple((offset+1080,name,rel)for offset,name,rel in oldids)==tuple(v for v in newids if v[0]>=1080)
 elf=(b/'conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();expected=[];tables=[];offset=0
 for start,end in [(0x800A59AC,0x800A5C98),(0x800A5C98,0x800A5D70),(0x800A5D70,0x800A5DBC),(0x800A5DBC,0x800A5DE4)]:
  table=at(elf,start,end-start);where=0x24A400+start-0x800A5940;assert table==rom[where:where+len(table)]
  values=struct.unpack('>'+str(len(table)//4)+'I',table);assert all(0x1514CA80<=v<0x1514D15C and v%4==0 for v in values)
  expected.extend((offset+4*i,fn,v-0x1514CA80)for i,v in enumerate(values));tables.append(dict(retail_VA=hex(start),entries=len(values),raw_offset=offset,ELF_ROM_equal=True,sha256=hashlib.sha256(table).hexdigest()));offset+=len(table)
 assert offset==1080 and tuple(expected)==tuple(v for v in newids if v[0]<1080)
 # The complete neighbor is independently unchanged after removing exactly
 # the new 1,080-byte local-pool displacement from its one LO16 addend.
 old,nrefs=payload(before,neighbor);nbody,newrefs=payload(new,neighbor);assert len(old)==len(nbody)==336 and nrefs==newrefs
 delta=[i for i in range(0,len(old),4)if old[i:i+4]!=nbody[i:i+4]];assert delta==[0x20] and int.from_bytes(nbody[0x20:0x24],'big')-int.from_bytes(old[0x20:0x24],'big')==1080 and newrefs[0x20]==[('R_MIPS_LO16','.rodata')]
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(guards.decode())));stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');rows=[];normalized=bytearray(raw);normalized_refs={k:list(v)for k,v in refs.items()}
 for where,bindings in sorted(refs.items()):
  if bindings[0][1]!='.rodata':continue
  assert len(bindings)==len(tr[where])==1;oldword=int.from_bytes(raw[where:where+4],'big');newword=int.from_bytes(truth[where:where+4],'big');kind,symbol=bindings[0];target_kind,target_symbol=tr[where][0];assert kind==target_kind and target_symbol.startswith('jtbl_')
  row=[owner,fn,f'0x{where:03X}',f'0x{oldword:08X}',f'0x{newword:08X}',kind+':'+symbol,target_kind+':'+target_symbol,'Bind the recovered classifier switch to its original retail jump table','','','false'];rows.append(row);writer.writerow(row);normalized[where:where+4]=newword.to_bytes(4,'big');normalized_refs[where]=tr[where]
 assert len(rows)==8 and (bytes(normalized),normalized_refs)==(truth,tr)
 row=[owner,neighbor,'0x020',f'0x{int.from_bytes(nbody[0x20:0x24],"big"):08X}',f'0x{int.from_bytes(old[0x20:0x24],"big"):08X}','R_MIPS_LO16:.rodata','R_MIPS_LO16:.rodata','Preserve the existing owner switch binding after the classifier adds four local tables','','','false'];rows.append(row);writer.writerow(row)
 assert all(len(row)==len(fields)for row in rows);suffix=stream.getvalue().encode();(o/'guard-additions.csv').write_bytes(suffix);(o/'selected-guards.csv').write_bytes(guards+suffix);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());assemble(assembly(truth,tr,fn),o/'normalized-target.o')
 where=o/'qualified-owner';where.mkdir(exist_ok=True);outs=[]
 for mode,obj in [('before',before),('selected',new)]:
  guard=b/'conker/retail_word_patches.us.csv'if mode=='before'else o/'selected-guards.csv'
  for kind in ('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',owner,word_patches_path=guard,rodata_symbol='jtbl_800A5E20'),b/'conker/asm/179F30.s')if kind=='generic'else pg.emit_padded_assembly(obj,b/'conker/asm/179F30.s',filename=owner,word_patches_path=guard,rodata_symbol='jtbl_800A5E20');path=where/(mode+'-'+kind+'.o');assemble(text,path)
   if mode=='before':assert path.read_bytes()==(b/'conker/build/src/game/generated_179F30.c.o').read_bytes()
   else:
    assert payload(path,fn)==(truth,tr) and same_functions(where/('before-'+kind+'.o'),path,(fn,))==77 and normalized_pools(path)==normalized_pools(where/('before-'+kind+'.o'));outs.append(path)
 assert outs[0].read_bytes()==outs[1].read_bytes()
 q=dict(words=439,frame=0,raw_bound_words_exact=True,raw_binding_positions=10,guards=9,target_table_binding_guards=8,neighbor_pool_addend_guard=1,insertions=0,omissions=0,new_tables=tables,new_table_entries=270,existing_table_entries=10,all_raw_pool_bytes_and_ownership_accounted=True,raw_neighbors_unchanged=76,normalized_neighbors_unchanged=77,both_before_objects_equal_frozen=True,both_complete_padders_equal=True,normalized_target_exact=True,normalized_pools_unchanged=True,profile_unchanged=True,new_diagnostics=0,existing_diagnostics=4,source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outs[0]),selected_guards_sha256=sha(o/'selected-guards.csv'),source_installed=installed(),matching_credit=0,goal_status='active');(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
