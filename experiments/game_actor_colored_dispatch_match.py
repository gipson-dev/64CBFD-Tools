import os,sys,subprocess,hashlib,inspect,json,struct
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();root=ROOT;out=root/'conker/build/game-actor-colored-dispatch-match'
MANIFEST=json.loads(Path(__file__).with_name('game_actor_colored_dispatch_manifest.json').read_text());FROZEN=MANIFEST['frozen']
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
sha=lambda b:hashlib.sha256(b).hexdigest();
MUTABLE=('conker/src/game/generated_12DAB0.c','conker/src/game/generated_5D2C0.c','conker/Makefile','conker/build/src/game/generated_12DAB0.c.o','conker/build/src/game/generated_5D2C0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt','conker/retail_word_patches.us.csv','conker/asm/12DAB0.s'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen input: '+n)
 current=sha((root/MUTABLE[0]).read_bytes());old=FROZEN[MUTABLE[0]];new=MANIFEST['qualification']['installed_hashes'][MUTABLE[0]]
 if current==old:installed=False
 elif current==new:installed=True
 else:raise ValueError('Unknown source state')
 allowed=dict(MANIFEST['qualification']['installed_hashes']);allowed[MUTABLE[-1]]=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed result incomplete: '+n)
 return FROZEN,installed

def main():
 q.p=SimpleNamespace(root=root,out=out)
 frozen,installed=freeze()
 name='conker/src/game/generated_12DAB0.c';text=MANIFEST['selected'];text=text.replace('s32 func_151026BC(actor, arg1, arg2, arg3, arg4, arg5)\n','/* Select the actor color pair and forward the effect setup. */\ns32 func_151026BC(actor, arg1, arg2, arg3, arg4, arg5)\n',1);old=(out/'frozen'/name).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'proposal.c';proposal.write_bytes(text.replace('\n',nl).encode())
 caller_name='conker/src/game/generated_5D2C0.c';caller_old=(out/'frozen'/caller_name).read_bytes();caller=caller_old.decode();before='void func_151026BC(u8 *, s32, s32, s32, s32, s32);';after='s32 func_151026BC(u8 *, int, int, int, int, s32);';assert caller.count(before)==1;caller=caller.replace(before,after);caller_path=out/'caller.c';caller_path.write_bytes(caller.encode())
 recipe='\nifeq ($(VERSION),us)\n# Use the retail float-constant profile only for the colored effect dispatcher.\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_12DAB0.c.o: $(SRC_DIR)/game/generated_12DAB0.c $$(call generated_slice_asm,12DAB0) ../tools/pad_generated_object.py retail_word_patches.us.csv Makefile\n\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) -DCBFD_COLORED_PRIMARY $(MIPSBIT) -o $@.compact $<\n\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) -Wo,-no_const_in_reg $(MIPSBIT) -o $@.float.compact $<\n\t$(PYTHON) ../tools/pad_generated_object.py $@.compact $(call generated_slice_asm,12DAB0) $@.padded.s --function-object func_151026BC=$@.float.compact --word-patches retail_word_patches.us.csv --filename generated_12DAB0 --rodata-symbol jtbl_800A2298_game\n\t$(AS) $(ASFLAGS) -o $@ $@.padded.s\n\trm -f $@.compact $@.float.compact $@.padded.s\nendif\n'
 make=(out/'frozen/conker/Makefile').read_bytes();assert b'CBFD_COLORED_PRIMARY' not in make;makepath=out/'proposal.Makefile';makepath.write_bytes(make+recipe.encode());(out/'proposed-guards.csv').write_bytes((out/'frozen/conker/retail_word_patches.us.csv').read_bytes())
 code=inspect.getsource(q.actual_make).replace("args=['make','-n'","args=['make','-f','build/game-actor-colored-dispatch-match/proposal.Makefile','-n'").replace("==1\n return targets,commands","==3\n return targets,commands");assert "==3\n return targets,commands" in code;scope=dict(q.actual_make.__globals__);exec(code,scope);targets,commands=scope['actual_make']({'game/generated_12DAB0':proposal,'game/generated_5D2C0':caller_path});obj=targets['game/generated_12DAB0'];caller_obj=targets['game/generated_5D2C0']
 assert same_functions(out/'frozen/conker/build/src/game/generated_12DAB0.c.o',obj,('func_151026BC',))==22
 assert same_functions(out/'frozen/conker/build/src/game/generated_5D2C0.c.o',caller_obj)==40
 def payload(path):
  data,fs,rs=parse_object(path);a,n=fs['func_151026BC']['value'],fs['func_151026BC']['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 body,refs=payload(obj);assert payload(out/'mixed-generated.o')==(body,refs)==payload(out/'mixed-generic.o')
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(body,refs,{nm:lookup[nm]for es in refs.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x12fb6c:0x12fc98];assert struct.pack('>75I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_151026BC':300}");scope=dict(q.strict_image.__globals__);exec(code,scope);image=scope['strict_image'](baseline,actual,{'func_151026BC':truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {n for n in oldfunc if oldfunc[n]!=newfunc[n]}=={'func_151026BC'}
 data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
 assert freeze()[1]==installed
 report=dict(source_installed=installed,frozen_inputs=len(frozen),target='func_151026BC',raw_words=75,guards=0,actual_Make_commands=len(commands),owner_neighbors=22,caller_functions=40,functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes={'conker/src/game/generated_12DAB0.c':sha(proposal.read_bytes()),caller_name:sha(caller_path.read_bytes()),'conker/Makefile':sha(makepath.read_bytes()),'conker/build/src/game/generated_12DAB0.c.o':sha(obj.read_bytes()),'conker/build/src/game/generated_5D2C0.c.o':sha(caller_obj.read_bytes()),'conker/build/conker.us.elf':sha(elf.read_bytes())})
 assert report['installed_hashes']==MANIFEST['qualification']['installed_hashes'] and image==MANIFEST['qualification']['image']
 (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);return report

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
