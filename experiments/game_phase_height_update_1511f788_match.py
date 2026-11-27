"""Phase/fall callback with closed GPR roles and stable-divisor MFLO scheduling."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_phase_height_update_1511f788_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x1511F788;ROM=0x14CC38;WORDS=105
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
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==(MANIFEST['guards_sha256'] if live else MANIFEST['inputs']['conker/retail_word_patches.us.csv']);_CHECKED=True;return live



fn=FUNCTION;owner=MANIFEST['filename']

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
def assemble(text,p):
 s=p.with_suffix('.s');s.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p),str(s)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def derive(raw,refs,truth,tr):
 a=list(struct.unpack('>105I',raw));z=list(struct.unpack('>105I',truth));assert refs==tr and len(refs)==6 and a[0]==z[0]==0x27BDFFD0
 early={5:2,2:8,8:5};temp=[8,9,10,11,12,13,14,15,24,25];late={reg:temp[(i+2)%10]for i,reg in enumerate(temp)};v=[]
 for i,w in enumerate(a):
  off=i*4;new=w;roles=early if off<=0x78 else late if off<=0x194 else{}
  op=w>>26;fields=(21,16,11)if op==0 else(16,)if op==15 else(21,16)if op in(4,5,9,10,11,12,13,20,21,32,33,35,36,40,41,43)else(16,)if op==17 and w>>21&31 in(0,4)else(21,)if op in(49,57)else()
  for shift in fields:
   reg=w>>shift&31
   if reg in roles:new=(new&~(31<<shift))|(roles[reg]<<shift)
  # The raw product and quotient reuseV1. Split the product live range toT9,
  # allowing the quotient MFLO to precede the constant-divisor guard block.
  if 0x40<=off<=0x70:
   for shift in fields:
    if w>>shift&31==3:new=(new&~(31<<shift))|(25<<shift)
  v.append(new)
 assert a[8//4]==0x2405003C and a[0x40//4]==0x00001812 and a[0x4C//4]==0x0065001A and a[0x74//4]==0x00001812
 # No instruction changes the divisor between its60 definition and DIV/
 # checks. Zero and signed-overflow guard BREAKs are therefore unreachable.
 def writes_gpr(w):
  op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;f=w&63
  if op==0:return {rd}if f in(0,2,3,16,18,33,35,36,37,42,43)else set()
  if op in(9,10,11,12,13,14,15,32,33,35,36):return {rt}
  if op==17 and rs in(0,2):return {rt}
  return set()
 assert all(5 not in writes_gpr(w)for w in a[3:0x74//4+1])
 assert [i*4 for i,w in enumerate(a)if w>>26==0 and w&63==13]==[0x58,0x70]
 normal=v[:];normal[0x50//4]=v[0x74//4]
 for off in range(0x50,0x74,4):normal[(off+4)//4]=v[off//4]
 assert normal==z,[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(normal,z))if x!=y]
 assert[w for w in a if w>>26==17 and w>>21&31 not in(0,4)]==[w for w in z if w>>26==17 and w>>21&31 not in(0,4)]
 # Stack addresses, widths and order are literal. The final previous-height
 # LH destination changes only through the proved transient GPR cycle.
 assert [(i,w&~(31<<16))for i,w in enumerate(a)if w>>21&31==29 and w>>26 in(9,32,33,35,36,40,41,43,49,57)]==[(i,w&~(31<<16))for i,w in enumerate(z)if w>>21&31==29 and w>>26 in(9,32,33,35,36,40,41,43,49,57)]
 rows=[dict(offset=i*4,expected=x,replacement=y)for i,(x,y)in enumerate(zip(a,normal))if x!=y];assert len(rows)==52
 return rows,dict(early_GPR_cycle=early,product_live_range=[0x40,0x70],product_raw_GPR=3,product_retail_GPR=25,late_GPR_cycle=late,late_region=[0x7C,0x194],MFLO_raw_offset=0x74,MFLO_retail_offset=0x50,checks_shifted_four_bytes=True,divisor_60_proved_stable=True,divide_zero_and_MIN_overflow_checks_unreachable=True,all_FP_arithmetic_FPR_roles_and_order_literal=True,all_stack_addresses_widths_and_order_literal=True,source_signed_product_requires_pinned_N64_low_word_contract_and_native_fwrapv=True,raw_full_dead_GPR_fault_identity_not_claimed=True)

def objects():
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original);assemble(original,o/'original-target.o')
 prepare();source=MANIFEST['selected_source'];(o/'semantic-source.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes())
 before,diag=compile_owner(r,o,(b/'conker/src/game/generated_142560.c').read_text(),'before-owner');assert not diag;selected,diag=compile_owner(r,o,source,'selected-owner');assert not diag;assert same_functions(before,selected,(fn,))==83 and normalized_pools(before)==normalized_pools(selected)
 raw,refs=payload(selected,fn);truth,tr=payload(o/'original-target.o',fn);rows,proof=derive(raw,refs,truth,tr);prefix=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in prefix.decode();fields=next(csv.reader(io.StringIO(prefix.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in prefix[:300]else'\n');spec=lambda refs:';'.join(k+':'+n for k,n in refs)or'-'
 for row in rows:
  off=row['offset'];out=dict.fromkeys(fields,'');out.update(filename=owner,function=fn,offset=hex(off),expected=hex(row['expected']),replacement=hex(row['replacement']),expected_relocations=spec(refs.get(off,[])),replacement_relocations=spec(tr.get(off,[])),note='Derived phase-height GPR roles and MFLO/check scheduling under stable divisor60; stack and FP arithmetic literal',omit='false');writer.writerow(out)
 (o/'guard-additions.csv').write_bytes(buf.getvalue().encode());(o/'selected-guards.csv').write_bytes(prefix+buf.getvalue().encode());assemble(assembly(truth,tr,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode,obj in [('before',before),('selected',selected)]:
  guards=b/'conker/retail_word_patches.us.csv'if mode=='before'else o/'selected-guards.csv'
  for kind in('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',owner,word_patches_path=guards),b/'conker/asm/142560.s')if kind=='generic'else pg.emit_padded_assembly(obj,b/'conker/asm/142560.s',filename=owner,word_patches_path=guards);path=where/(mode+'-'+kind+'.o');assemble(text,path)
   if mode=='before':assert path.read_bytes()==(b/'conker/build/src/game/generated_142560.c.o').read_bytes()
   else:assert payload(path,fn)==(truth,tr)and same_functions(where/('before-'+kind+'.o'),path,(fn,))==83;outputs.append(path)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();q=dict(words=105,normalized_words=105,retail_slot_words=105,frame=48,guards=52,insertions=0,omissions=0,raw_binding_positions=6,normalized_byte_exact=True,raw_byte_exact=False,raw_neighbors=83,both_complete_padders_equal=True,both_before_objects_equal_frozen=True,source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outputs[0]),structural_derivation=proof,semantic_qualification_complete=False,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
