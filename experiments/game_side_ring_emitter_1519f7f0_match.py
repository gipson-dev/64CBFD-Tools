"""Complete emitter C, with proved phase relation and checked literal bindings."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
from unittest.mock import patch
from tools.experiments import game_side_ring_emitter_1519f7f0_recovery as history
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=history.ROOT
OUT=history.OUT/'proof-2484'
SOURCE,NAME,ENTRY,ROM,SIZE=history.SOURCE,history.NAME,history.ENTRY,history.ROM,history.SIZE
PIN=json.loads(Path(__file__).with_name('game_side_ring_emitter_1519f7f0_match_manifest.json').read_text())

def recover(before):
 stub='s32 func_1519F7F0() {\n    return 0;\n}'
 assert before.count(stub)==before.count('extern s32 D_800BE9E4;')==1
 return before.replace('extern s32 D_800BE9E4;',PIN['declarations']+'\nextern s32 D_800BE9E4;',1).replace(stub,PIN['source'])

def normalize(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!={int(k):[tuple(x) for x in v] for k,v in PIN['refs'].items()}:
  raise ValueError('Emitter instructions or bindings changed')
 words=list(struct.unpack('>415I',raw));nrefs={k:v[:] for k,v in refs.items()}
 for row in PIN['changes']:
  at=int(row['offset'],16);assert words[at//4]==int(row['expected'],16)
  assert nrefs.get(at,[])==[tuple(x) for x in row['expected_relocations']]
  words[at//4]=int(row['replacement'],16)
  if row['replacement_relocations']:nrefs[at]=[tuple(x) for x in row['replacement_relocations']]
  else:nrefs.pop(at,None)
 normal=struct.pack('>415I',*words)
 assert hashlib.sha256(normal).hexdigest()==PIN['normal_sha256']
 assert nrefs=={int(k):[tuple(x) for x in v] for k,v in PIN['normal_refs'].items()}
 return normal,nrefs

def programs():
 raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs);syms=g.symbols()
 return dict(retail=list(struct.unpack_from('>415I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)),candidate=bound_blob(raw,refs,{**syms,'.rodata':syms['D_800A8CF4']}),guarded=bound_blob(normal,nrefs,syms))

def assemble(label,text):
 path=OUT/(label+'.s');obj=path.with_suffix('.o');path.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True)
 assert p.returncode==0 and not p.stderr,p.stderr
 return obj

def main():
 frozen=history.OUT/'production-baseline';before=(frozen/SOURCE).read_text();proposed=recover(before)
 live=(ROOT/SOURCE).read_text();installed=live==proposed;assert live in (before,proposed)
 if not installed:history.immutable()
 baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,proposed,'qualified');assert bd==ad=='',bd+ad
 assert same_functions(baseline,obj,(NAME,))==38
 assert sections(obj)['.rodata'][1]==bytes.fromhex(PIN['literal_pool'])
 assert normalized_pools(baseline)['.data']==normalized_pools(obj)['.data']
 assert normalized_pools(baseline)['.rodata'] in (None,(b'',()))
 text,functions,allrefs=pg.parse_object(obj);start=functions[NAME]['value']
 pool_refs={at:rs for at,rs in allrefs.items() if any(n=='.rodata' for k,n in rs)}
 assert len(pool_refs)==6 and all(start<=at<start+SIZE for at in pool_refs)
 storage=history.local_storage(obj);raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);p=programs();assert p['guarded']==p['retail']
 syms=g.symbols();assert [syms[n]-syms['D_800A8CF4'] for n in ('D_800A8CF4','D_800A8CF8','D_800A8CFC')]==[0,4,8]
 elf=(ROOT/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,syms['D_800A8CF4'],12)
 assert elf[at:at+12]==bytes.fromhex(PIN['literal_pool'])[:12]
 from tools.tests import game_side_ring_emitter_1519f7f0_proof as proof
 relation=proof.prove(p['candidate'],p['retail']);relation['controls']=proof.qualify(p['candidate'],p['retail'])
 corruption=0
 for i in range(415):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:normalize(bytes(wrong),refs)
  except ValueError:corruption+=1
  else:raise AssertionError('Changed emitter word accepted')
 for at,values in refs.items():
  try:normalize(raw,{**refs,at:[(k,n+'_bad') for k,n in values]})
  except ValueError:corruption+=1
  else:raise AssertionError('Changed emitter binding accepted')
 original=(frozen/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())))
 assert not any(row['function']==NAME for row in csv.DictReader(io.StringIO(original.decode())))
 rel=lambda values:';'.join(k+':'+n for k,n in values) or '-'
 rows=[dict(filename='generated_1CC440',function=NAME,offset=row['offset'],expected=row['expected'],replacement=row['replacement'],expected_relocations=rel(row['expected_relocations']),replacement_relocations=rel(row['replacement_relocations']),note='Preserve proved emitter register roles, private spills and ordinary field scheduling; bind recovered literal pool',insert_after='',insert_after_relocations='',omit='false') for row in PIN['changes']]
 assert len(rows)==126
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in original else '\n').writerows(rows)
 guards=original+stream.getvalue().encode();(OUT/'proposed-guards.csv').write_bytes(guards)
 assert (ROOT/'conker/retail_word_patches.us.csv').read_bytes()==(guards if installed else original)
 padded=[]
 for label,assembly in (('guarded',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=OUT/'proposed-guards.csv')),
                        ('strict',pg.emit_padded_assembly(obj,ROOT/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=OUT/'proposed-guards.csv'))):
  result=assemble(label,assembly);assert bound_blob(*payload(result,NAME),syms)==p['retail']
  assert same_functions(frozen/'conker/build/src/game/generated_1CC440.c.o',result,(NAME,))==38
  assert normalized_pools(result)==normalized_pools(frozen/'conker/build/src/game/generated_1CC440.c.o')
  assert not any(n=='.rodata' for values in payload(result,NAME)[1].values() for k,n in values)
  padded.append(result)
 used=sorted({n for values in nrefs.values() for k,n in values});rebases=[]
 for ordinal,base in enumerate((syms['D_800A8CF4'],0x800AFFFC,0x80117FFC)):
  moved={**syms,**{n:syms[n]+((i+1)*(ordinal+1)*0x10000) for i,n in enumerate(used)}}
  for i,n in enumerate(('D_800A8CF4','D_800A8CF8','D_800A8CFC')):moved[n]=base+4*i
  left=bound_blob(raw,refs,{**moved,'.rodata':base});right=bound_blob(normal,nrefs,moved)
  for result in padded:assert bound_blob(*payload(result,NAME),moved)==right
  constants={n:moved[target] for n,target in (('SIDE','func_1519EF90'),('CLEAN','func_1519F48C'),('FACTORY','func_151491F4'),('COPY','memcpy'),('RNG','func_150ADA20'),('FLOOR','func_15045800'))}
  with patch.object(g,'symbols',lambda:moved),patch.multiple(g,**constants):rebases.append(proof.prove(left,right))
 (OUT/'proposed-owner.c').write_text(proposed)
 report=dict(raw_words=415,retail_words=415,raw_frame=280,retail_frame=280,raw_word_differences=122,guards=126,inserted_words=0,omissions=0,neighbors=38,padders=2,independent_rebases=3,literal_group_offsets=[0,4,8],literal_HI16_carry_controls=2,literal_bindings=6,unchanged_padded_pools=True,corruption_controls=corruption,local_storage=storage,proof=relation,installed=installed,c_match_credit=int(installed))
 (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('proof','local_storage')}),flush=True)
if __name__=='__main__':main()
