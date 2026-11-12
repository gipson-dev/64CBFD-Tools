from pathlib import Path
import sys,os,hashlib,json,struct,csv,io,inspect,shutil
from types import SimpleNamespace
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-interpolation-screen'
MANIFEST=json.loads(Path(__file__).with_name('game_position_interpolation_manifest.json').read_text())
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

def _prepare():
 name='func_150BE2E8';owner='game/generated_EB340';source='conker/src/game/generated_EB340.c';hashes={}
 paths=[source,'conker/Makefile','conker/retail_word_patches.us.csv','conker/asm/EB340.s','conker/asm/13D350.s','conker/asm/CBDB0.s','conker/asm/data/22D710.rodata.s','conker/build/src/game/generated_EB340.c.o','conker/build/conker.us.elf','conker/build/conker.ld','conker/build/conker.us.bin','conker/conker.us.bin','conker/retail_layout.us.txt','conker/progress.csv']
 source_hash=hashlib.sha256((root/source).read_bytes()).hexdigest()
 old_hash=MANIFEST['frozen'][source];new_hash=MANIFEST['installed'][source]
 assert source_hash in (old_hash,new_hash),'Unknown source state'
 installed=source_hash==new_hash
 for n in paths:
  data=(root/n).read_bytes();f=out/'frozen'/n;f.parent.mkdir(parents=True,exist_ok=True);expected=MANIFEST['frozen'][n]
  if f.exists():assert hashlib.sha256(f.read_bytes()).hexdigest()==expected,('frozen',n)
  else:
   assert hashlib.sha256(data).hexdigest()==expected,('missing frozen baseline',n)
   f.write_bytes(data)
  live=hashlib.sha256(data).hexdigest()
  if installed and n=='conker/progress.csv':pass
  else:assert live==(MANIFEST['installed'].get(n,expected) if installed else expected),('live',n)
  hashes[n]=live
 old=(out/'frozen'/source).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';s=old.decode();candidate=MANIFEST['body'];s=s.replace('#include <ultra64.h>','#include <ultra64.h>\nextern f32 D_800A0068;\nextern s32 D_800BE9E4;'.replace('\n',nl));s=s.replace(body(s,name),'/* Advance actor position interpolation and fixed-point progress. */\n'.replace('\n',nl)+candidate.replace('\n',nl));proposal=out/'proposal.c';proposal.write_bytes(s.encode())
 make=(out/'frozen/conker/Makefile').read_bytes();needle=b'\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_12DAB0.c.o\nISOLATED_WRAPPER_GENERATED_SLICE_O_FILES';replacement=b'\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_12DAB0.c.o \\\n\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_EB340.c.o\nISOLATED_WRAPPER_GENERATED_SLICE_O_FILES';assert make.count(needle)==1;make=make.replace(needle,replacement)
 recipe='''\nifeq ($(VERSION),us)\n# Select the interpolation callback's retail floating-constant profile only.\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_EB340.c.o: $(SRC_DIR)/game/generated_EB340.c $$(call generated_slice_asm,EB340) ../tools/pad_generated_object.py retail_word_patches.us.csv Makefile\n\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) $(MIPSBIT) -o $@.compact $<\n\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) -Wo,-no_const_in_reg $(MIPSBIT) -o $@.float.compact $<\n\t$(PYTHON) ../tools/pad_generated_object.py $@.compact $(call generated_slice_asm,EB340) $@.padded.s --function-object func_150BE2E8=$@.float.compact --word-patches retail_word_patches.us.csv --filename generated_EB340 $(if $(RETAIL_RODATA_SYMBOL),--rodata-symbol $(RETAIL_RODATA_SYMBOL))\n\t$(AS) $(ASFLAGS) -o $@ $@.padded.s\n\trm -f $@.compact $@.float.compact $@.padded.s\nendif\n''';(out/'proposal.Makefile').write_bytes(make+recipe.encode())
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 compile_scope=dict(compile_owner.__globals__);exec(inspect.getsource(compile_owner).replace('*flags,','*[f for f in flags if not f.startswith("-Wo,")],',1),compile_scope)
 rawobj,diagnostics=compile_scope['compile_owner'](root,out,s,'base_no_const',('-O2','-g3','-Wo,-no_const_in_reg'));assert not diagnostics
 raw,fs,rs=parse_object(out/'base_no_const.o');a=fs[name]['value'];n=fs[name]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};words=list(struct.unpack('>84I',raw[a:a+n]));ret=list(struct.unpack('>84I',(root/'conker/conker.us.bin').read_bytes()[0xeb798:0xeb8e8]));addresses={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};bound=bound_blob(raw[a:a+n],refs,{nm:addresses[nm] for es in refs.values() for _,nm in es});diff=[i for i,(x,y) in enumerate(zip(bound,ret)) if x!=y];assert diff==[43,44,69,70,71,73,74,75,76,77] and all(i*4 not in refs for i in diff)
 oldcsv=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(oldcsv.decode())));assert not any(r['function']==name for r in csv.DictReader(io.StringIO(oldcsv.decode())));buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in oldcsv else '\n')
 for i in diff:writer.writerow(dict(filename='generated_EB340',function=name,offset='0x%X'%(4*i),expected='0x%08X'%words[i],replacement='0x%08X'%ret[i],expected_relocations='-',replacement_relocations='-',note='Normalize interpolation float register schedule and operand order',insert_after='',insert_after_relocations='',omit='false'))
 (out/'proposed-guards.csv').write_bytes(oldcsv+buf.getvalue().encode())
 q.p=SimpleNamespace(root=root,out=out)
 code=inspect.getsource(q.actual_make).replace("args=['make','-n'","args=['make','-f','build/game-motion-interpolation-screen/proposal.Makefile','-n'").replace("==1\n return targets,commands","==2\n return targets,commands");assert '==2\n return targets,commands' in code;scope=dict(q.actual_make.__globals__);exec(code,scope);targets,commands=scope['actual_make']({owner:proposal});obj=targets[owner];assert same_functions(out/'frozen/conker/build/src/game/generated_EB340.c.o',obj,(name,))==7

 def payload(path):
  d,f,r=parse_object(path);a=f[name]['value'];n=f[name]['size'];return d[a:a+n],{i-a:v for i,v in r.items() if a<=i<a+n}
 selected=Path(str(obj)+'.float.compact');assert payload(selected)==payload(out/'base_no_const.o');normalized,nrefs=payload(obj);nw=bound_blob(normalized,nrefs,{nm:addresses[nm] for es in nrefs.values() for _,nm in es});assert nw==ret
 elf=q.link(targets);before=(out/'frozen/conker/build/conker.us.elf').read_bytes();after=elf.read_bytes();code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150BE2E8':336}");scope=dict(q.strict_image.__globals__);exec(code,scope);image=scope['strict_image'](before,after,{name:struct.pack('>84I',*ret)})
 oldf,_,oldaddr=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newf,_,newaddr=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldf.keys()==newf.keys() and oldaddr==newaddr and {n for n in oldf if oldf[n]!=newf[n]}=={name};data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
 for n,h in hashes.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
 report=dict(target=name,words=84,guards=len(diff),neighbors=7,actual_make_commands=len(commands),addresses_fixed=True,image=image,protected_data=data,proposed_source_sha=hashlib.sha256(proposal.read_bytes()).hexdigest(),object_sha=hashlib.sha256(obj.read_bytes()).hexdigest(),elf_sha=hashlib.sha256(after).hexdigest());assert report==MANIFEST['expected'],(report,MANIFEST['expected']);(out/'shadow-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);return report


def prepare():
 prior=q.p
 try:return _prepare()
 finally:q.p=prior

if __name__=='__main__':prepare()
