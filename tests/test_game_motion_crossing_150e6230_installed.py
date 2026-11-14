"""Fail-closed installed source, production object and native semantics check."""
from pathlib import Path
import csv,hashlib,os,struct,subprocess,sys,unittest
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-motion-crossing-150e6230-durable'
source=root/'conker/src/game/generated_113480.c';rom=root/'conker/conker.us.bin';elf=root/'conker/build/conker.us.elf'
sha=lambda b:hashlib.sha256(b).hexdigest()

class InstalledMotionCrossingTests(unittest.TestCase):
 def test_source_and_guards(self):
  text=source.read_bytes().replace(b'\r\n',b'\n')
  self.assertEqual(sha(text),'2724a42be1a8af7637bb71c477ae93a47b702d7468de8c659be22cc6efcff79e')
  self.assertIn(b'func_15144A74(delta, (f32 *)(state + 4))',text)
  with (root/'conker/retail_word_patches.us.csv').open(newline='') as stream:
   rows=[r for r in csv.DictReader(stream) if r['filename']=='generated_113480' and r['function']=='func_150E6230']
  indexes=[3,4,7,8,11,14,18,21,24,26,28,31,44,45,49,60,62,63,64,65,66,67,68,69,70,71,72,73,74]
  self.assertEqual([int(r['offset'],16)//4 for r in rows],indexes)
  self.assertEqual(sum(bool(r['insert_after']) for r in rows),2)
 def test_production_body(self):
  self.assertEqual(sha(rom.read_bytes()),'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382')
  image=elf.read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows(image)}
  body=rom.read_bytes()[0x1136e0:0x113850];self.assertEqual(len(body),368)
  self.assertEqual(image[elf_slot_offset(image,0x150e6230,368):][:368],body)
  obj=root/'conker/build/src/game/generated_113480.c.o'
  words=bound_blob(*payload(obj,'func_150E6230'),symbols)
  self.assertEqual(struct.pack('>92I',*words),body)
 def test_native_semantics(self):
  out.mkdir(parents=True,exist_ok=True);(out/'formatted.c').write_text(source.read_text())
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
  p=subprocess.run([sys.executable,'-m','tools.tests.game_motion_crossing_150e6230_native'],cwd=root,env=env,capture_output=True,text=True,timeout=300)
  self.assertEqual(p.returncode,0,(p.stdout,p.stderr));self.assertIn('"cases_per_configuration": 192',p.stdout)

if __name__=='__main__':unittest.main()
