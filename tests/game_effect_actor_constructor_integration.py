from pathlib import Path
import csv, json, struct
from tools.tests import game_oriented_effect_factory_integration as helpers

TARGET=0x15154884; ROM_BASE=0x2D4B0; VA_BASE=0x15000000
JAL_WORD=0x0D455221; J_WORD=0x09552221
CALL=0x150D64D0; START=0x150D6434; END=0x150D64E8
PROOFS=(
 (0x150D64A0,0x44058000,'A1 = randomized positive lifetime'),
 (0x150D64B8,0x8FA40030,'A0 = forwarded position pointer'),
 (0x150D64BC,0xAFAE0010,'stack arg4 = zero-extended caller byte'),
 (0x150D64C0,0xAFAF0014,'stack arg5 = forwarded caller context'),
 (0x150D64C4,0x44065000,'A2 = randomized amplitude'),
 (0x150D64CC,0x44073000,'A3 = randomized height'),
 (0x150D64D4,0x00000000,'call delay slot is nop'),
)

def word(rom,va):return struct.unpack_from('>I',rom,ROM_BASE+va-VA_BASE)[0]

def qualify(root,out):
 rom=(root/'conker/conker.us.bin').read_bytes();ws=struct.unpack(f'>{len(rom)//4}I',rom[:len(rom)&~3])
 jals=[i*4 for i,w in enumerate(ws)if w==JAL_WORD];jumps=[i*4 for i,w in enumerate(ws)if w==J_WORD];ptrs=[i*4 for i,w in enumerate(ws)if w==TARGET]
 assert jals==[0x103980]and not jumps and not ptrs
 rows=[]
 with (root/'conker/progress.csv').open(newline='')as f:
  for r in csv.DictReader(f):
   try:s,n=int(r['offset']),int(r['length'])
   except ValueError:continue
   if s<=CALL<s+n:rows.append(r)
 assert len(rows)==1 and rows[0]['function']=='func_150D6434'and int(rows[0]['offset'])==START and int(rows[0]['length'])==END-START
 proof=[]
 for va,wanted,meaning in PROOFS:
  actual=word(rom,va);assert actual==wanted,(hex(va),hex(actual),hex(wanted));proof.append(dict(va=hex(va),word=f'0x{actual:08X}',meaning=meaning))
 site=helpers.Callsite(CALL,'func_150D6434',START,END,0,())
 taint=helpers.return_value_is_unconsumed(rom,site)
 report=dict(success=True,private_only=True,matching_credit=0,target='func_15154884',target_va=hex(TARGET),
  original_callers=1,unique_parents=1,aligned_ROM_JALs=[hex(x)for x in jals],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[],
  argument_contract=dict(arg0='forwarded pointer to three-float position',arg1='random float * 3.0 + 8.0, therefore positive',
   arg2='random float * D_800A0AB0 + D_800A0AB4',arg3='random float * 50.0 + 100.0',
   arg4='zero-extended low byte of caller argument 1',arg5='full caller argument 2 context',return_value='discarded by the sole caller'),
  caller_site=dict(call_va=hex(CALL),parent='func_150D6434',parent_range=[hex(START),hex(END)],parent_words=(END-START)//4,
   parent_language=rows[0]['language'],owner=rows[0]['filename'],argument_proofs=proof,return_taint=taint),
  complete_position_input_bytes=12,full_parent_execution_claimed=False,alternate_source_used_for_ABI_proof=False)
 (out/'private-caller-v1.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
 root=Path.cwd();print(json.dumps(qualify(root,root/'conker/build/game-effect-actor-constructor-15154884-match'),indent=2))


