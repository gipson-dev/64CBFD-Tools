"""Direct-source objects, both padders, carry links, full faults and mode-zero control."""
from pathlib import Path
import hashlib,json,re,struct,subprocess,sys
from tools.experiments import game_indexed_matrix_renderer_15168c4c_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_indexed_matrix_renderer_15168c4c_guest as q
g=q.g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
NAME='func_15168C4C';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 p=path.with_suffix('.s');p.write_text(text);result=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(p)],capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,name in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {name}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def objects():
 data,refs=g.payload(o/'selected-final/candidate.o',NAME);truth=g.payload(o/'original-target.o',NAME);assert(data,refs)==truth and len(data)==488
 guard=o/'baseline/conker/retail_word_patches.us.csv';assert guard.read_bytes()==(r/'conker/retail_word_patches.us.csv').read_bytes();assert not any(line.startswith(b'game_1944C0,func_15168C4C,')for line in guard.read_bytes().splitlines())
 where=o/'qualified-owner';where.mkdir(exist_ok=True);obj=where/'game_1944C0.c.o';assemble(pc.emit_padded_assembly(o/'selected-final/candidate.o',o/'baseline/conker/retail_layout.us.txt','game_1944C0',word_patches_path=guard),obj)
 assert g.payload(obj,NAME)==truth and same_functions(o/'baseline/conker/build/src/game_1944C0.c.o',obj,(NAME,))==41
 report=dict(raw_words=122,retail_words=122,frame=104,guards=0,omissions=0,insertions=0,raw_direct_byte_exact=True,named_relocations_equal=True,neighbors=41,guard_CSV_unchanged=True,qualified_object_sha256=sha(obj),source_installed=packet.installed(),matching_credit=0)
 (o/'objects.json').write_text(json.dumps(report,indent=2)+'\n');return report
def boundaries():
 data,refs=g.payload(o/'selected-final/candidate.o',NAME);truth=g.payload(o/'original-target.o',NAME);where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 header,*lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();line=[v for v in lines if v.split(',')[1:3]==['game_1944C0',NAME]];assert len(line)==1;layout=where/'layout.csv';layout.write_text(header+'\n'+line[0]+'\n');guard=o/'baseline/conker/retail_word_patches.us.csv';original=o/'baseline/conker/asm/nonmatchings/game_1944C0/func_15168C4C.s'
 # The isolated target has zero guard rows. Neighbor guards are exercised by
 # the complete-owner build above, not applied to this single-function object.
 emitters=[lambda obj:pc.emit_padded_assembly(obj,layout,'game_1944C0',word_patches_path=None),lambda obj:pg.emit_padded_assembly(obj,original,filename='game_1944C0',word_patches_path=None)]
 outputs=[]
 for index,emit in enumerate(emitters):
  obj=where/f'padded-{index}.o';assemble(emit(target),obj);assert g.payload(obj,NAME)==truth;outputs.append(obj)
 controls=0
 for kind in('wrong-word','wrong-named-binding'):
  bad=bytearray(data);brefs={i:list(v)for i,v in refs.items()}
  if kind=='wrong-word':struct.pack_into('>I',bad,0,struct.unpack_from('>I',bad)[0]^1)
  else:
   at=next(i for i,v in brefs.items()if('R_MIPS_26','func_15043D90')in v);brefs[at]=[('R_MIPS_26','func_15142FBC')]
  obj=where/(kind+'.o');assemble(assembly(bad,brefs),obj)
  for index,emit in enumerate(emitters):
   output=where/f'{kind}-{index}.o';assemble(emit(obj),output);assert g.payload(output,NAME)!=truth;controls+=1
 names=sorted({n for pairs in refs.values()for _,n in pairs});links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  symbols={n:(0x15300000+i*0x100 if n.startswith('func_')else 0x80300000+i*0x10000+low)for i,n in enumerate(names)};blobs=[]
  for index,obj in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{low:X}-{index}.ld';script.write_text('SECTIONS { .text 0x15168C4C : SUBALIGN(4) { *(.text) } }\n');image=script.with_suffix('.elf')
   result=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(image),str(obj)],capture_output=True,text=True);assert result.returncode==0,result.stderr
   text=sections(image)['.text'][1];assert not any(text[488:]);blob=text[:488];assert list(struct.unpack('>122I',blob))==g.bound_blob(*g.payload(obj,NAME),symbols)
   defs=[v for _,n,v,_ in symbol_rows(image.read_bytes())if n==NAME];assert len(defs)==1 and defs[0][1:3]==(q.ENTRY,488);blobs.append(blob);links+=1
  assert len(set(blobs))==1
 return dict(both_padders_direct_exact=True,target_guards=0,omissions=0,insertions=0,GNU_links=links,HI16_carry_boundaries=4,effective_wrong_word_and_binding_output_controls=controls)
def faults():
 data,refs=g.payload(o/'selected-final/candidate.o',NAME);streams={label:g.bound_blob(*g.payload(o/path,NAME),g.SYMS)for label,path in dict(raw='selected-final/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o').items()}
 count=0;rows=[q.Case(),q.Case(mode=2,combine=1,effect=15,pattern=8,phase=8),q.Case(mode=0,home_word=0xA1B2C3D4),q.Case(mode=0,home_word=0),q.Case(mode=255,home_word=0x504A50,combine=1),q.Case(cache_match=True,alpha=0,tile=255,buffer=1)]
 for c in rows:
  memory=q.fixture(c);complete=q.Oracle(streams['retail'],memory,c).run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in streams.values():
    m=q.Oracle(ws,memory,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('No actual fault boundary')
    states.append((m.memory,m.trace,m.calls,m.log,m.r,m.f,m.hi,m.lo))
   assert states[0]==states[1]==states[2],(c,cut);count+=1
 return dict(full_raw_padded_retail_access_prefix_triples=count,discriminating_cases=len(rows),full_memory_GPR_FPR_HI_LO_trace_and_calls_equal=True)
def rebases():
 old=dict(g.SYMS);runs=0
 try:
  for low in(0,0x7FFC,0x8000,0xFFFC):
   g.SYMS['D_800BE9C0']=0x80310000+low
   for name in('D_800DD1C0','D_800DD1C2','D_800DD1C4','D_800DD1C6','D_800DD218','D_800DD21C'):g.SYMS[name]=0x80320000+low+(old[name]-old['D_800DD1C0'])
   for mode,buffer,effect in itertools.product((1,2),(0,1),(0,15)):
    c=q.Case(mode=mode,buffer=buffer,effect=effect,combine=1,pattern=8);memory=q.fixture(c);expected,log,value=q.reference(memory,c)
    for path in('selected-final/candidate.o','qualified-owner/game_1944C0.c.o','original-target.o'):
     ws=g.bound_blob(*g.payload(o/path,NAME),g.SYMS);m=q.Oracle(ws,memory,c).run();assert(g.public(m.memory),m.log,m.r[2])==(g.public(expected),log,value);runs+=1
 finally:g.SYMS.clear();g.SYMS.update(old)
 return dict(guest_rebase_runs=runs,independent_carry_boundaries=4,cache_field_alias_offsets_preserved=True)
def mode_control():
 body=(o/'selected-final/body.c').read_text();marker='''            renderMode = 0x00504A50;
            break;
    }''';assert body.count(marker)==1
 bad=body.replace(marker,marker[:-5]+'        default:\n            renderMode = 0;\n            break;\n    }')
 source=(o/'selected-final/selected-owner.c').read_text();assert source.count(body.rstrip())==1;source=source.replace(body.rstrip(),bad.rstrip())
 where=o/'controls';where.mkdir(exist_ok=True);obj,_=compile_owner(r,where,source,'invented-mode-zero-default',('-O2','-g3'));ws=g.bound_blob(*g.payload(obj,NAME),g.SYMS)
 c=q.Case(mode=0,home_word=0xA1B2C3D4);memory=q.fixture(c);expected,log,value=q.reference(memory,c);m=q.Oracle(ws,memory,c).run()
 assert(g.public(m.memory),m.log,m.r[2])!=(g.public(expected),log,value),'Invented default control survived'
 return dict(effective_source_control='invented-mode-zero-default',guest_seeded_word=hex(c.home_word),failure_is_public_output_or_helper_arguments=True)
def upstream():
 source=(o/'additional-baseline/conker/src/game/generated_19E040.c').read_text();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();result={}
 for name,expected in(('func_15170B90',0),('func_15170F4C',2),('func_15171200',1)):
  lo,hi=function_span(source,name);body=source[lo:hi];assignments=re.findall(r'packet\.control5C\s*=\s*(\d+)\s*;',body);assert assignments==[str(expected)]
  rows=[v for _,n,v,_ in symbol_rows(elf)if n==name];assert len(rows)==1;_,va,size,*_=rows[0];at=g.elf_slot_offset(elf,va,size);offset=va-0x15000000+0x2D4B0;assert elf[at:at+size]==rom[offset:offset+size]
  result[name]=dict(complete_current_slot_equals_ROM=True,words=size//4,render_mode=expected)
 return dict(three_constructor_callers=result,mode_zero_is_real_upstream_input=True)
def main():
 report=dict(objects=objects(),boundaries=boundaries(),faults=faults(),rebases=rebases(),mode_control=mode_control(),upstream=upstream(),source_installed=packet.installed(),matching_credit=0)
 (o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
import itertools
if __name__=='__main__':main()
