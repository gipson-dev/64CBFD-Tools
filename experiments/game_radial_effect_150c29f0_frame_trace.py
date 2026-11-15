"""Observe owned CFE/UOPT/UGEN frame evidence for two retained radial forms."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from tools.experiments import game_radial_effect_150c29f0_recovery as s
from tools.experiments import game_actor_callback_frame_trace as observer
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob

def compile_input(root,out,name,source):
 src=out/(name+'.c');obj=out/(name+'.o');src.write_text(source)
 relative=lambda p:os.path.relpath(root/p,out)
 command=[relative('ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-mips2','-o32']
 for inc in ('conker/include','conker/include/2.0L','conker/include/2.0L/PR','conker/include/libc'):command+=['-I',relative(inc)]
 command+=['-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-O2','-g3','-o',obj.name,src.name]
 q=subprocess.run(command,cwd=out,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr)
 raw,refs=payload(obj,s.NAME);words=bound_blob(raw,refs,s.symbols());truth=s.programs()[0]
 return dict(body_words=len(words),frame=(-words[0])&65535,differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-len(truth)),raw_sha256=hashlib.sha256(raw).hexdigest()),None

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--variant',choices=('canonical','frame88','self','homes'),default='canonical');args=parser.parse_args()
 hashes=json.loads((s.OUT/'production-baseline/fingerprints.json').read_text())['inputs'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 for name,want in hashes.items():assert sha(s.ROOT/name)==want,name
 name={'canonical':'plain-O2.c','frame88':'volatile-typed-no-position.c','self':'volatile-self.c','homes':'position-first.c'}[args.variant]
 manifest=json.loads((s.OUT/'screen-artifact-sha256.json').read_text())
 manifest.update({'volatile-self.c':'5d6924754c2e5cec2b2547f38bb37ac2ab3a3793b06be204f9956fd16c59d5d7','position-first.c':'7e1c44f7563bbdd869ee0565e5f874fd3d6b2b20b4f0b1a310c0b7729fd2a403'})
 source=s.OUT/name;assert sha(source)==manifest[name]
 original=observer.screen.compile_candidate
 try:
  observer.screen.compile_candidate=compile_input
  record=observer.trace(s.ROOT,s.OUT/'frame-observation',args.variant,source.read_text())
 finally:observer.screen.compile_candidate=original
 work=s.OUT/'frame-observation'/args.variant;log=(work/'debugger.txt').read_text();controls=[]
 for label,bad in (('unfired_frame_gate',log.replace('FRAME_TRACE ','IGNORED ')),('missing_producer_exit',log.replace('TRACE_EXIT inferior=%d code=0'%record['inputs'][0]['inferior'],'IGNORED_PRODUCER_EXIT'))):
  try:observer.validate_observations(work,bad)
  except ValueError:controls.append(label)
  else:raise AssertionError('Ineffective trace control: '+label)
 for name,want in hashes.items():assert sha(s.ROOT/name)==want,name
 result=dict(variant=args.variant,baseline=record['baseline'],events=record['events'],inputs=record['inputs'],memory_definitions={kind:[r for r in rows if r['name']=='mst' or (r['name']=='def' and r['storage']=='M')] for kind,rows in record['records'].items()},record_counts={k:len(v) for k,v in record['records'].items()},code_unchanged=record['code_unchanged'],frozen_inputs_unchanged=len(hashes),controls=controls,installable=False)
 (work/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(variant=args.variant,baseline=result['baseline'],events=result['events'],record_counts=result['record_counts'],code_unchanged=result['code_unchanged'],controls=controls)),flush=True)
if __name__=='__main__':main()
