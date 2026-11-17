"""Private strip-update recovery; immutable source, data, ABI and owner checks."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import load_section
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
PACKET=ROOT/'conker/build/game-next-151ad174-private';QUALIFICATION=PACKET/'qualification'
FROZEN=PACKET/'qualification-baseline';OUT=Path(os.environ.get('CBFD_STRIP_UPDATE_WORK',str(QUALIFICATION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
PIN=json.loads(Path(__file__).with_name('game_strip_update_151ad174_private_manifest.json').read_text())
NAME,SOURCE,ENTRY,ROM,SIZE=PIN['name'],PIN['source'],PIN['entry'],PIN['rom'],PIN['size']
STUB='/* Placeholder: the registered callback receives a byte-addressed record. */\nvoid func_151AD174(u8 *record) {\n}'
def check_inputs():
 inputs=json.loads((FROZEN/'fingerprints.json').read_text())['inputs'];assert len(inputs)==PIN['frozen_input_count']
 for name,h in inputs.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 assert STUB in(ROOT/SOURCE).read_text();return len(inputs)
def recover(before,body=None):
 assert before.count(STUB)==1
 return before.replace(STUB,PIN['declarations']+'\n'+(PIN['body']if body is None else body))
def compile_and_check():
 check_inputs();OUT.mkdir(exist_ok=False);before=(FROZEN/SOURCE).read_text()
 a,diagnostics=compile_owner(ROOT,OUT,before,'baseline');assert not diagnostics
 b,diagnostics=compile_owner(ROOT,OUT,recover(before),'owner');assert not diagnostics
 raw,refs=payload(b,NAME);assert len(raw)==1948 and hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in PIN['refs'].items()}
 assert same_functions(a,b,(NAME,))==32 and normalized_pools(a)==normalized_pools(b)
 truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert hashlib.sha256(truth).hexdigest()==PIN['retail_sha256']
 original=(FROZEN/'conker/asm/1D92F0.s').read_text().split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0]
 import re
 assert bytes.fromhex(''.join(re.findall(r'/\* [0-9A-F]{6} [0-9A-F]{8} ([0-9A-F]{8}) \*/',original)))==truth
 (OUT/'retail.bin').write_bytes(truth);(OUT/'raw.bin').write_bytes(raw);(OUT/'body.txt').write_text(PIN['body']);(OUT/'declarations.txt').write_text(PIN['declarations'])
 syms={v[1]:v[2][1]for v in symbol_rows((FROZEN/'conker/build/conker.us.elf').read_bytes())};base,data=load_section(FROZEN/'conker/build/conker.us.elf','.game_data');table=syms['D_8008B4A8'];registrations=[]
 for i in range(101):
  values=struct.unpack_from('>13I',data,table-base+i*52)
  if ENTRY in values:registrations.append(dict(category=i,address=table+i*52,words=[hex(v)for v in values],callback_offsets=[j*4 for j,v in enumerate(values)if v==ENTRY]))
 assert registrations==PIN['registrations']
 for name,item in PIN['constants'].items():assert data[syms[name]-base:syms[name]-base+len(bytes.fromhex(item['bytes']))].hex()==item['bytes']
 report=dict(raw_words=487,retail_words=494,frame=776,neighbors=32,pools_unchanged=True,registered_secondary_categories=[47,78],source_installed=False,c_match_credit=0)
 (OUT/'source-report.json').write_text(json.dumps(report,indent=2)+'\n');check_inputs();return report
if __name__=='__main__':print(json.dumps(compile_and_check()),flush=True)
