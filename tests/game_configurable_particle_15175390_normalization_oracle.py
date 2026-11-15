"""Replay the independent model against raw, normalized and retail streams."""
import itertools,json,struct
from tools.experiments import game_configurable_particle_15175390_normalization as source
from tools.tests import game_configurable_particle_15175390_oracle as g
from tools.tests.game_configurable_particle_15175390_oracle import Case,run_case,bits,ENTRY,SURFACES,SOUND,GROUND
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_remaining_donor_candidates import compile_owner

def controls():
    text=(source.OUT/'selected.c').read_text();cases=[]
    negatives=(('unsigned-samples','func_150ADA20() % sampleZ','(u32)func_150ADA20() % (u32)sampleZ',2,Case(count=1,flags=0,state=1,ground_flags=0,model_mask=0,seed=0)),('wrong-query-gate','state == 0 || grounded != 0','state == 0 || grounded == 0',1,Case(count=1,flags=0,state=1,ground_flags=0,model_mask=0,seed=0)),('wrong-first-sound','if (baseType == 10)','if (baseType != 10)',1,Case(count=1,base_type=77,flags=0,seed=0)))
    for label,old,new,count,case in negatives:
        assert text.count(old)==count
        obj,diag=compile_owner(source.ROOT,source.OUT,text.replace(old,new),label);assert not diag
        words=bound_blob(*payload(obj,source.NAME))
        try:run_case(case,(words,))
        except AssertionError as e:assert isinstance(e.args[0],tuple) and e.args[0][0]==case,(label,e.args)
        else:raise AssertionError('Ineffective observable semantic control: '+label)
        cases.append(label)
    return cases

def main():
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack_from('>370I',rom,source.ROM));raw=bound_blob(*payload(source.OUT/'selected.o',source.NAME));nr,refs=source.normalize(*payload(source.OUT/'selected.o',source.NAME));normal=bound_blob(nr,refs);assert len(raw)==370 and raw!=retail and normal==retail
    count=0;coverage=set();sound=ground=0
    for n,flags,state,ground_flags,mutation,alias in itertools.product((-1,0,1,3),(0,0x10000,0x20000,0x30000,0x40,0x30040),(0,1,2),(0,1),(0,1,2,3),(False,True)):
        c=Case(count=n,flags=flags,state=state,ground_flags=ground_flags,mutation=mutation,alias=alias,fail=(0,1,3)[count//2%3],type_range=(0,3)[count//3%2],model_mask=(-1,0,3)[count//5%3],base_type=(10,77,125)[count//7%3],vertical=(-1,0,1,30)[count//11%4],seed=count%7,phase=8*(count&1))
        used,calls,b=run_case(c,(retail,raw,normal));assert b is None;coverage.update(used);sound+=sum(t==SOUND for t,a in calls);ground+=sum(t==GROUND for t,a in calls);count+=1
    assert sound and ground
    directed=0
    for heading,base,spread in itertools.product((-400.,-15.,0.,360.,720.,2147483520.,-2147483648.),(-3.25,-0.,.8),(0.,-.5,2.)):
        c=Case(count=1,flags=0x30003,heading=bits(heading),base=bits(base),spread=bits(spread),seed=directed%7,phase=8*(directed&1))
        used,calls,b=run_case(c,(retail,raw,normal));assert b is None;coverage.update(used);directed+=1
    boundaries=[]
    for c in (Case(trap='type-zero',type_range=3),Case(trap='vertical-zero',state=1,ground_flags=0,vertical=1,type_range=0,flags=0),Case(outer=5,inner=5,type_range=0,flags=0),Case(outer=1,inner=2,trap='overflow-first',type_range=0,flags=0),Case(outer=1,inner=2,trap='overflow-second',type_range=0,flags=0),Case(flags=0x10000,heading=0x7fc01234),Case(flags=0x10000,heading=0x4f000000),Case(state=0,ground_height=2147483647)):
        used,calls,b=run_case(c,(retail,raw,normal));assert b;coverage.update(used);boundaries.append(b)
    unwritten=0
    for old,state,alias,phase in itertools.product((0,SURFACES-12,SURFACES+12),(0,1),(False,True),(0,8)):
        c=Case(write_surface=False,untouched_surface=old,state=state,ground_flags=1,alias=alias,phase=phase,count=2,flags=0);used,calls,b=run_case(c,(retail,normal));assert b is None;coverage.update(used);unwritten+=1
    missing=sorted(set(range(ENTRY,ENTRY+1480,4))-coverage)
    report=dict(semantic_cases=count,directed_source_cases=directed,source_streams=3,source_guest_boundaries=boundaries,retail_and_normalized_unwritten_cases=unwritten,sound_calls=sound,ground_calls=ground,retail_words_visited=370-len(missing),retail_unvisited_offsets=[hex(a-ENTRY) for a in missing],raw_words=370,frame=184,word_differences=219,normalized_differences=0,c_match_credit=0,installed=False,native_or_caller_execution_claimed=False)
    report['effective_source_controls']=controls()
    (source.OUT/'semantic-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
