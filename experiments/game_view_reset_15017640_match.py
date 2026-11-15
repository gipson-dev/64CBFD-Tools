"""Thirteen checked register/address schedule guards for the complete C reset."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
from tools.experiments import game_view_reset_15017640_candidates as draft
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/draft.BUILD
NAME,ENTRY,ROM,SIZE,SLOT_SIZE,SOURCE,BUILD=draft.NAME,draft.ENTRY,draft.ROM,draft.SIZE,draft.SLOT,draft.SOURCE,draft.BUILD
OWNER='game_44A90';SDK={'bzero','guPerspective'}
PIN=json.loads(Path(__file__).with_name('game_view_reset_15017640_manifest.json').read_text())
RAW_REFS={int(k):[tuple(x) for x in v] for k,v in PIN['raw_refs'].items()}

def normalize(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=RAW_REFS or len(raw)!=328:raise ValueError('View reset raw words or bindings changed')
 words=list(struct.unpack('>82I',raw));order=list(range(82))
 for a,b in {1:2,2:3,3:1,5:7,6:5,7:6,26:27,27:26,31:32,32:31}.items():order[a]=b
 assert sorted(order)==list(range(82));result=[];bindings={}
 for i,old in enumerate(order):
  w=words[old]
  if i==3:assert w==0x3c030000;w=0x3c060000
  elif i==5:assert w==0x24630000;w=0x24c60000
  elif i in (20,21,22):assert w==0xe4600000+(i-20)*4;w=(w&~(31<<21))|(6<<21)
  result.append(w)
  if old*4 in refs:bindings[i*4]=refs[old*4]
 return struct.pack('>82I',*result),bindings

def programs():
 syms=draft.symbols(ROOT);truth=list(struct.unpack_from('>82I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
 return [(truth,ENTRY)]+[(bound_blob(*payload(OUT/(label+'.o'),NAME),syms),ENTRY) for label in ('qualified','guarded')]

def main():
 before=(OUT/'production-baseline'/SOURCE).read_text();candidate=draft.recover(before,draft.pointer_body());live=(ROOT/SOURCE).read_text();installed=live==candidate
 assert live==(candidate if installed else before)
 baseline,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'qualified');assert d1==d2==''
 assert same_functions(baseline,obj,(NAME,))==1 and normalized_pools(baseline)==normalized_pools(obj)
 raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);syms=draft.symbols(ROOT)
 from tools.tests.game_view_reset_15017640_prefix_proof import certify
 proof=certify(bound_blob(normal,nrefs,syms),bound_blob(raw,refs,syms));truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
 assert struct.pack('>82I',*bound_blob(normal,nrefs,syms))==truth
 corruptions=0
 for i in range(82):
  bad=bytearray(raw);bad[i*4+3]^=1
  try:normalize(bytes(bad),refs)
  except ValueError:corruptions+=1
  else:raise AssertionError('Changed instruction was accepted')
 for at,rows in refs.items():
  try:normalize(raw,{**refs,at:[(k,n+'_changed') for k,n in rows]})
  except ValueError:corruptions+=1
  else:raise AssertionError('Changed binding was accepted')
 original=(OUT/'production-baseline/conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));patches=[]
 rel=lambda xs:';'.join(k+':'+n for k,n in xs) or '-'
 for i,(a,b) in enumerate(zip(struct.unpack('>82I',raw),struct.unpack('>82I',normal))):
  er,rr=refs.get(i*4,[]),nrefs.get(i*4,[])
  if a!=b or er!=rr:patches.append(dict(filename=OWNER,function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(er),replacement_relocations=rel(rr),note='Preserve proved motion-vector register and independent address schedule',insert_after='',insert_after_relocations='',omit='false'))
 assert len(patches)==13 and not [r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
 stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(patches);guards=original+stream.getvalue().encode()
 assert (ROOT/'conker/retail_word_patches.us.csv').read_bytes()==(guards if installed else original)
 (OUT/'proposed-guards.csv').write_bytes(guards)
 fragment=(ROOT/'conker/asm/nonmatchings/game_44A90/func_15017640.s').read_text();fragment=fragment[:fragment.index('endlabel '+NAME)+len('endlabel '+NAME)]
 (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+NAME+',.-'+NAME+'\n')
 (OUT/'guarded.s').write_text(pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv'))
 for label in ('retail','guarded'):
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0,q.stderr
  assert struct.pack('>82I',*bound_blob(*payload(OUT/(label+'.o'),NAME),syms))==truth
 assert same_functions(OUT/'production-baseline/conker/build/src/game_44A90.c.o',OUT/'guarded.o',(NAME,))==1
 report=dict(body_words=82,slot_words=84,alignment_words=2,frame=40,guards=13,neighbors=1,corruption_controls=corruptions,prefix_proof=proof,installed=installed,c_match_credit=int(installed))
 (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
