"""Completed compiled counterexamples for the angular update semantics."""
import json
from tools.experiments import game_angle_phase_150c4d20_match as p
from tools.tests import game_angle_phase_150c4d20_oracle as g
def main():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');s=(p.out/'selected-body.c').read_text(encoding='utf-8')
 variants={'no-initial-wrap':s.replace('angle -= 360.0f;','angle -= 180.0f;',1),'threshold':s.replace('>= 256.0f','> 256.0f'),'period':s.replace('(f32)phase - 256.0f','(f32)phase - 255.0f'),'wrong-sound':s.replace('0x55F0','0x55F1'),'wrong-coordinates':s.replace('state->x, state->y, state->z','state->y, state->x, state->z'),'wrong-flag':s.replace('flags & 4) == 4','flags & 2) == 2'),'wrong-sign':s.replace('velocity -= angle','velocity += angle'),'missing-bias':s.replace('velocity += scale;','velocity -= scale;'),'wrong-damping':s.replace('velocity *= D_800A03F8','velocity *= D_800A03F4'),'lost-local-velocity':s.replace('velocity += oscillation * scale','velocity = state->angular_velocity + oscillation * scale'),'lost-captured-phase':s.replace('state->phase = phase;','phase = state->phase;\n    state->phase = phase;'),'cached-angle':s.replace('state->angle += velocity','state->angle = angle + velocity'),'wrong-lower-wrap':s.replace('state->angle += 360.0f','state->angle += 180.0f'),'wrong-upper-wrap':s.replace('state->angle -= 360.0f','state->angle -= 180.0f')}
 cs=[g.Case(angle=g.bits(a),timer=t,mutation=mu,flags=f)for a in(-720.,-1.,0.,180.,181.,360.,720.)for t in(0,255,256)for mu in(0,3)for f in(0,4)]
 result={}
 for label,body in variants.items():
  assert body!=s;obj,diag=p.compile_owner(p.root,p.out,p.proposal(old,body),'control-'+label);assert not diag,diag;ws=g.words(obj);errors=0
  for c in cs:
   m=g.Oracle(ws,g.fixture(c),c)
   try:m.run()
   except(AssertionError,KeyError,ValueError):errors+=1;continue
   try:g.check(m,c)
   except AssertionError:result[label]=dict(case=c.__dict__,normal_completion=True,execution_errors_before_witness=errors);break
  assert label in result,(label,'no completed witness')
 report=dict(controls=len(result),effective_compiled_controls=result,execution_errors_counted_as_witnesses=False);(p.out/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(controls=len(result),all_normal=True)),flush=True);return report
if __name__=='__main__':main()
