"""Fail-closed installed source, production object and native ordering check."""
from pathlib import Path
import csv,hashlib,json,os,struct,subprocess,sys,unittest
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-height-emitter-150e971c-durable'
source=root/'conker/src/game/generated_113D60.c';rom=root/'conker/conker.us.bin';elf=root/'conker/build/conker.us.elf'
sha=lambda b:hashlib.sha256(b).hexdigest()

class InstalledHeightEmitterTests(unittest.TestCase):
 def test_source_and_guards(self):
  text=source.read_bytes().replace(b'\r\n',b'\n')
  self.assertEqual(sha(text),'8a2205e97b2b063ab9d7f497e5e9e948b348ab876c236b65098d5f3bac2bbb16')
  self.assertIn(b'random = func_150ADA20();\n            func_1513C73C',text)
  with (root/'conker/retail_word_patches.us.csv').open(newline='') as stream:
   rows=[r for r in csv.DictReader(stream) if r['filename']=='generated_113D60' and r['function']=='func_150E971C']
  indexes=[0,20,27,28,29,*range(42,56),57,59,64,67,88]
  self.assertEqual([int(r['offset'],16)//4 for r in rows],indexes)
 def test_production_body(self):
  self.assertEqual(sha(rom.read_bytes()),'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382')
  image=elf.read_bytes();symbols={r[1]:r[2][1] for r in symbol_rows(image)}
  body=rom.read_bytes()[0x116bcc:0x116d38];self.assertEqual(len(body),364)
  self.assertEqual(image[elf_slot_offset(image,0x150e971c,364):][:364],body)
  obj=root/'conker/build/src/game/generated_113D60.c.o'
  words=bound_blob(*payload(obj,'func_150E971C'),symbols)
  self.assertEqual(struct.pack('>91I',*words),body)
 def test_native_ordering(self):
  out.mkdir(parents=True,exist_ok=True)
  text=source.read_text();direct=text.replace('    s32 random;\n','').replace('            random = func_150ADA20();\n','').replace('(random & 255)','(func_150ADA20() & 255)')
  self.assertNotEqual(direct,text)
  (out/'padded.c').write_text(direct);(out/'snapshot.c').write_text(text)
  env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
  p=subprocess.run([sys.executable,'-m','tools.tests.game_height_emitter_150e971c_native_screen'],cwd=root,env=env,capture_output=True,text=True,timeout=300)
  self.assertEqual(p.returncode,0,(p.stdout,p.stderr));self.assertIn('"snapshot_passed": true',p.stdout)

if __name__=='__main__':unittest.main()
