"""Private register-allocation closure after complete native/caller gates."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_render_list_parent_151674f8_match as packet
r,o=packet.ROOT,packet.OUT
from tools.experiments import game_render_list_parent_151674f8_roles as roles
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
NAME='func_151674F8';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def normalize(raw,refs):
 plan=json.loads((packet.TOOLROOT/'experiments/game_render_list_parent_151674f8_role_plan.json').read_text());assert hashlib.sha256(raw).hexdigest()==plan['raw_sha256']
 order=plan['order'];assert len(order)==len(set(order))==348 and order[:43]==list(range(43))and order[43:47]==[45,46,43,44]and order[47:]==list(range(47,348))
 source=list(struct.unpack('>348I',raw));result=[];newrefs={}
 for j,i in enumerate(order):
  w=source[i];spec=roles.info(w)
  for edit in plan['register_fields'][str(i)]:
   s=edit['shift'];v=edit['value'];assert s in spec['fields']and 0<=v<32;w=(w&~(31<<s))|v<<s
  assert roles.info(w)['signature']==spec['signature'];result.append(w)
  if 4*i in refs:newrefs[4*j]=refs[4*i]
 # The independent relational proof checks all live reads, including delay
 # slots, call targets/arguments and return/saved-register roles.
 assert roles.prove([source[i]for i in order],result)['register_operand_pairs']==497
 return struct.pack('>348I',*result),newrefs
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
def main():
 native=json.loads((o/'native.json').read_text());assert len(native['profiles'])==3 and all(v['cases']==1352 and v['SDK32']and v['UBSan']and v['strict_aliasing']for v in native['profiles'].values());assert native['recursive_parent_cases']==36 and len(native['effective_source_controls'])==20
 caller=json.loads((o/'callers.json').read_text());assert caller['complete_caller_functions']==6 and caller['all_14_actual_JAL_sites_executed']and not caller['range_helper_unexecuted']
 raw,refs=payload(o/'selected/candidate.o',NAME);fixed,nrefs=normalize(raw,refs);assert(fixed,nrefs)==payload(o/'original-target.o',NAME)
 original=(o/'baseline/conker/retail_word_patches.us.csv').read_bytes();columns=next(csv.reader(io.StringIO(original.decode())));rows=[]
 spec=lambda values:';'.join(k+':'+n for k,n in values)or'-'
 assert not any(v.startswith(('game_1944C0,'+NAME+',').encode())for v in original.splitlines())
 for i,((a,),(b,))in enumerate(zip(struct.iter_unpack('>I',raw),struct.iter_unpack('>I',fixed))):
  if a==b and refs.get(4*i,[])==nrefs.get(4*i,[]):continue
  rows.append(dict(filename='game_1944C0',function=NAME,offset='0x%03X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(nrefs.get(4*i,[])),note='Normalize render-list parent closed GPR roles and four independent setup words',insert_after='',insert_after_relocations='',omit='false'))
 assert len(rows)==91
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=columns).writerows(rows);guard=o/'private-word-patches.csv';guard.write_bytes(original+buf.getvalue().encode());where=o/'qualified-owner';where.mkdir(exist_ok=True);obj=where/'game_1944C0.c.o'
 assemble(pc.emit_padded_assembly(o/'selected/candidate.o',r/'conker/retail_layout.us.txt','game_1944C0',word_patches_path=guard),obj)
 assert payload(obj,NAME)==payload(o/'original-target.o',NAME)and same_functions(o/'baseline/conker/build/src/game_1944C0.c.o',obj,(NAME,))==41
 report=dict(raw_words=348,retail_words=348,frame=144,guards=91,omissions=0,insertions=0,all_348_origins_once=True,opcode_literal_named_binding_control_edges_and_memory_order_preserved=True,register_operand_pairs=497,neighbors=41,all_words_and_named_relocations_equal=True,qualified_object_sha256=sha(obj),source_installed=packet.installed(),matching_credit=0)
 (o/'normalization.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
