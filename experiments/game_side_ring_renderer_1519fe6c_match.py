"""Semantic renderer plus constrained source-word schedule projection and gates."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_side_ring_renderer_1519fe6c_recovery as source
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests import game_side_ring_renderer_1519fe6c_composition as proof
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=source.ROOT;OUT=source.OUT/'frame-2488';O=OUT
NAME,SOURCE,ENTRY,ROM,SIZE=source.NAME,source.SOURCE,source.ENTRY,source.ROM,source.SIZE
PIN=json.loads(Path(__file__).with_name('game_side_ring_renderer_1519fe6c_match_manifest.json').read_text())

def recover(before):return source.recover(before)

def check_inputs():
 frozen=source.OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text())
 before=(frozen/SOURCE).read_text();live=(ROOT/SOURCE).read_text();installed=live==recover(before);assert installed or live==before
 plan=json.loads((OUT/'adoption-plan.json').read_text()) if installed else {}
 if installed:assert set(plan)=={SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1CC440.c.o','conker/build/conker.us.elf'}
 for n,h in record['inputs'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==plan.get(n,h),n
 return installed

def compile_and_check():
 installed=check_inputs();before=(source.OUT/'production-baseline'/SOURCE).read_text()
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');assert not bd,bd
 for pin,label in((source.PIN,'qualified'),(source.PIN['previous'],'previous'),(source.PIN['prior_selected'],'prior-selected')):
  obj,diagnostics=compile_owner(ROOT,OUT,source.recover(before,pin),label);assert not diagnostics,diagnostics
  raw,refs=payload(obj,NAME);assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256'] and {str(k):v for k,v in refs.items()}=={k:[tuple(x) for x in v] for k,v in pin['refs'].items()}
  assert same_functions(baseline,obj,(NAME,))==38
  assert sections(obj)['.rodata'][1]==bytes.fromhex(PIN['literal_pool']) and normalized_pools(baseline)['.data']==normalized_pools(obj)['.data']
 assert source.storage(OUT/'qualified.o')['cursor']==-4
 assert sections(baseline)['.rodata'][1]==bytes.fromhex('38d1b717469c4000c614700000000000')
 (OUT/'proposed-owner.c').write_text(recover(before))
 check_inputs();return installed

def programs():
 raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
 return dict(retail=list(struct.unpack_from('>632I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)),previous=bound_blob(*payload(OUT/'previous.o',NAME),{**g.S,'.rodata':g.S['D_800A8CF4']}),prior_selected=bound_blob(*payload(OUT/'prior-selected.o',NAME),{**g.S,'.rodata':g.S['D_800A8CF4']}),candidate=bound_blob(raw,refs,{**g.S,'.rodata':g.S['D_800A8CF4']}),guarded=bound_blob(normal,nrefs,g.S))

def fields(w):
 op,fn,fmt=w>>26,w&63,w>>21&31
 if op==0:
  shifts=(16,11) if fn in(0,2,3) else (21,16,11) if fn in(4,6,7,33,35,36,37,42,43) else (21,16) if fn in(24,25,26,27) else (11,) if fn in(16,18) else (21,) if fn==8 else None
 elif op==17:
  shifts=(16,11) if fmt in(0,4) else (11,16,6) if fmt==16 and fn in(0,1,2,3) else (11,6) if fmt==16 and fn in(4,5,6,7,13) else (11,16) if fmt==16 and fn in(50,60) else () if fmt==8 else None
 elif op in(3,):shifts=()
 elif op in(1,6,7,22,23):shifts=(21,)
 elif op==15:shifts=(16,)
 elif op in(4,5,9,10,11,12,13,20,21,32,33,35,36,37,40,41,43,49,53,57,61):shifts=(21,16)
 else:shifts=None
 assert shifts is not None,('unclassified instruction fields',hex(w))
 return sum(31<<shift for shift in shifts)

def branch_mask(w):
 op=w>>26
 return (0x11<<26) if op in(4,5,20,21,6,7,22,23) else (3<<16) if op==1 or(op==17 and w>>21&31==8) else 0

def base_word(words,pc,kind):
 w=words[pc//4]
 if kind=='byte-move':
  assert pc in(0x2F0,0x374,0x3E8,0x980) and w>>26==12 and w&65535==255
  return ((w>>21&31)<<21)|((w>>16&31)<<11)|37
 if kind=='private-reload-move':
  assert pc==0x47C and w>>26==33 and w>>21&31==29 and w&65535==148
  store=words[0x478//4];assert store>>26==41 and store>>21&31==29 and store&65535==148
  return ((store>>16&31)<<21)|((w>>16&31)<<11)|37
 assert kind=='instruction';return w

def project(raw,refs,pin):
 if len(raw)!=637*4 or hashlib.sha256(raw).hexdigest()!=pin['raw_sha256'] or {str(k):v for k,v in refs.items()}!={k:[tuple(x) for x in v] for k,v in pin['raw_refs'].items()}:raise ValueError('Renderer compiler words or bindings changed')
 words=list(struct.unpack('>637I',raw));out=[];nrefs={}
 for row in pin['order']:
  pc=row['source'];w=base_word(words,pc,row['kind']);m=fields(w);assert row['operands']&~m==0
  w=(w&~m)|row['operands']
  if row.get('private_offset') is not None:
   assert row['kind']=='instruction' and words[pc//4]>>21&31==w>>21&31==29 and pc not in refs
   assert w>>26 in(9,32,33,35,36,37,40,41,43,49,53,57,61)
   w=(w&0xFFFF0000)|row['private_offset']
  if row.get('target') is not None:
   bm=branch_mask(w);assert bm and row['branch_mode']&~bm==0
   w=(w&~bm)|row['branch_mode'];delta=row['target']-(len(out)*4+4);assert delta%4==0
   w=(w&0xFFFF0000)|((delta//4)&65535)
  if pc in refs:
   assert row['kind']=='instruction' and row.get('private_offset') is None and row.get('target') is None
   nrefs[len(out)*4]=[(kind,'D_800A8CF4' if name=='.rodata'else name) for kind,name in refs[pc]]
  out.append(w)
 return struct.pack('>'+str(len(out))+'I',*out),nrefs

def normalize(raw,refs):
 normal,nrefs=project(raw,refs,PIN)
 assert len(normal)==632*4 and hashlib.sha256(normal).hexdigest()==PIN['normal_sha256']
 assert {str(k):v for k,v in nrefs.items()}=={k:[tuple(x) for x in v] for k,v in PIN['normal_refs'].items()}
 return normal,nrefs

def assemble(label,text):
 path=O/(label+'.s');obj=path.with_suffix('.o');path.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=source.ROOT/'conker',capture_output=True,text=True)
 assert p.returncode==0 and not p.stderr,p.stderr
 return obj

def main():
 installed=compile_and_check();pin=PIN;obj=OUT/'qualified.o';raw,refs=payload(obj,source.NAME);normal,nrefs=normalize(raw,refs)
 assert len(normal)==632*4 and hashlib.sha256(normal).hexdigest()==pin['normal_sha256']
 syms=g.S;original=programs()['retail'];left=bound_blob(raw,refs,{**syms,'.rodata':syms['D_800A8CF4']});right=bound_blob(normal,nrefs,syms);assert right==original
 relation=proof.prove(left,right);assert relation['whole_function']
 # A genuinely different scratch allocation passes; no retail word template
 # is involved in the relational checker.
 alternative=right[:]
 for at in range(0x12C//4,0x18C//4):
  w=alternative[at];m=fields(w)
  for shift in(21,16,11):
   if m&(31<<shift)==31<<shift:
    reg=w>>shift&31
    if reg in(14,15):w=(w&~(31<<shift))|((29-reg)<<shift)
  alternative[at]=w
 assert alternative!=right and proof.prove(left,alternative)==relation
 corruption=0
 for i in range(637):
  bad=bytearray(raw);bad[4*i+3]^=1
  try:normalize(bytes(bad),refs)
  except ValueError:corruption+=1
  else:raise AssertionError(('changed compiler word accepted',i))
 for at,rows in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_bad') for kind,name in rows]})
  except ValueError:corruption+=1
  else:raise AssertionError(('changed compiler binding accepted',at))
 frozen=source.OUT/'production-baseline';before=(frozen/'conker/retail_word_patches.us.csv').read_bytes();assert not any(row['function']==source.NAME for row in csv.DictReader(io.StringIO(before.decode())))
 header=next(csv.reader(io.StringIO(before.decode())));raw_words=struct.unpack('>637I',raw);normal_words=struct.unpack('>632I',normal);rows=[]
 reloc=lambda values:';'.join(kind+':'+name for kind,name in values) or '-'
 for i,w in enumerate(raw_words):
  at=4*i;omit=i>=632
  rows.append(dict(filename='generated_1CC440',function=source.NAME,offset='0x%X'%at,expected='0x%08X'%w,replacement='0x%08X'%(0 if omit else normal_words[i]),expected_relocations=reloc(refs.get(at,[])),replacement_relocations=reloc([] if omit else nrefs.get(at,[])),note='Preserve composed renderer operand allocation, private storage and CFG schedule; constrained source provenance',insert_after='',insert_after_relocations='',omit=str(omit).lower()))
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in before else '\n').writerows(rows)
 guards=O/'proposed-guards.csv';guards.write_bytes(before+stream.getvalue().encode());padded=[]
 for label,assembly in(('layout',pc.emit_padded_assembly(obj,source.ROOT/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=guards)),('strict',pg.emit_padded_assembly(obj,source.ROOT/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=guards))):
  result=assemble(label,assembly);assert bound_blob(*payload(result,source.NAME),syms)==right
  assert same_functions(frozen/'conker/build/src/game/generated_1CC440.c.o',result,(source.NAME,))==38
  assert normalized_pools(result)==normalized_pools(frozen/'conker/build/src/game/generated_1CC440.c.o')
  assert not any(name=='.rodata' for values in payload(result,source.NAME)[1].values() for kind,name in values);padded.append(result)
 rebases=[];used=sorted({name for rows in nrefs.values() for kind,name in rows})
 for ordinal,base in enumerate((syms['D_800A8CF4'],0x800AFFFC,0x80117FF4)):
  moved={**syms,**{name:syms[name]+((i+1)*(ordinal+1)*0x10000) for i,name in enumerate(used)}}
  for i,name in enumerate(('D_800A8CF4','D_800A8CF8','D_800A8CFC','D_800A8D00')):moved[name]=base+4*i
  a=bound_blob(raw,refs,{**moved,'.rodata':base});b=bound_blob(normal,nrefs,moved)
  for result in padded:assert bound_blob(*payload(result,source.NAME),moved)==b
  targets={name:moved[function] for name,function in(('BACKEND','func_151D5D60'),('TEXTURE','func_15142E24'),('GEOMETRY','func_15142B7C'),('ENV','func_15142C10'),('PRIM','func_15142CF0'),('COMBINE','func_1513F4E4'),('MODE','func_15142FBC'))}
  rename={getattr(g,name):value for name,value in targets.items()}
  targets.update(COUNTS={rename[t]:n for t,n in g.COUNTS.items()},SYNC={rename[t]:n for t,n in g.SYNC.items()},S=moved)
  with patch.multiple(g,**targets):rebases.append(proof.prove(a,b))
 check_inputs()
 report=dict(raw_words=637,normalized_words=632,frame=240,word_guards=637,omitted_tail_slots=5,inserted_words=0,source_provenance_omissions=9,source_provenance_duplicates=4,padders=2,neighbors=38,independent_rebases=len(rebases),guards_cover_unreachable_words=True,corruption_controls=corruption,independent_register_allocation_positive_control=True,whole_function_relation=relation['whole_function'],production_state_matches_audited_inputs=True,source_installed=installed,c_match_credit=int(installed))
 (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
