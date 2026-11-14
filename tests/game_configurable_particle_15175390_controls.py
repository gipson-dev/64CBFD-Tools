"""Effective source negatives for signed sampling, query gating and sound retention."""
import json
from tools.tests import game_configurable_particle_15175390_oracle as g
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
def main():
    source=(g.source.OUT/'selected.c').read_text();cases=[]
    controls=(('unsigned-samples','func_150ADA20() % sampleZ','(u32)func_150ADA20() % (u32)sampleZ',2,g.Case(count=1,flags=0,state=1,ground_flags=0,model_mask=0,seed=0)),('wrong-query-gate','state == 0 || grounded != 0','state == 0 || grounded == 0',1,g.Case(count=1,flags=0,state=1,ground_flags=0,model_mask=0,seed=0)),('wrong-first-sound','if (baseType == 10)','if (baseType != 10)',1,g.Case(count=1,base_type=77,flags=0,seed=0)))
    for label,old,new,count,case in controls:
        assert source.count(old)==count;changed=source.replace(old,new);obj,diag=compile_owner(g.source.ROOT,g.source.OUT,changed,label);assert not diag
        words=bound_blob(*payload(obj,g.source.NAME))
        try:g.run_case(case,(words,))
        except AssertionError as e:assert isinstance(e.args[0],tuple) and e.args[0][0]==case,(label,e.args)
        else:raise AssertionError('Ineffective semantic control: '+label)
        cases.append(label)
    report=dict(effective_controls=cases,comparison='observable memory calls and dispatched guest boundary',unsupported_instruction_failures_accepted=False)
    (g.source.OUT/'semantic-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
