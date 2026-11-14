"""Run the recovered constructor followed by the unchanged retail callback."""
from dataclasses import replace
import itertools,json,struct
from tools.tests import game_motion_piece_15179fe0_oracle as b
from tools.tests import game_piece_update_1517a1ec_oracle as callback
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
def main():
    root,out,value,programs=b.load();rom=(root/'conker/conker.us.bin').read_bytes();code=bound_blob(*payload(out/'guarded.o','func_1517A1EC'));assert code==list(struct.unpack_from('>106I',rom,0x1a769c))
    cases=updates=retired=0
    for lifetime,mode,outcome,pattern,ticks,phase in itertools.product((0,2,1200),(0,5,37),(0,1),(0,2),(1,65),(0,8)):
        c=b.Case(lifetime=lifetime,mode=mode,outcome=outcome,pattern=pattern,phase=phase,seed=19,mutation=0,damping=3);initial=b.fixture(c,value);expected,_,_,zero=b.reference(initial,c);assert zero is None;memories=[]
        for words in programs:
            machine=b.Oracle(words,initial,c);machine.run();b.verify(machine,initial,c);memories.append(machine.memory)
        if outcome:
            consumed=6
            for step in range(3):
                child=callback.Case(seed=c.seed+consumed,pattern=pattern,phase=phase,mutation=0)
                b.put(expected,callback.TICKS,b.u32(ticks));prediction,calls,_,zero=callback.reference(expected,child);assert not zero
                for memory in memories:
                    b.put(memory,callback.TICKS,b.u32(ticks));machine=callback.Oracle(code,memory,child);machine.run();callback.verify(machine,memory,child);assert callback.public(machine.memory)==callback.public(prediction);memory.clear();memory.update(machine.memory)
                consumed+=sum(target==callback.RANDOM for target,_ in calls);expected=prediction;updates+=1
                if any(target==callback.FREE for target,_ in calls):retired+=1;break
        cases+=1
    report=dict(cases=cases,callback_steps=updates,retirements=retired,constructor_words=131,callback_words=106,callback_bytes_reverified=True,providers_modeled=True,three_step_sequences=True)
    (out/'lifecycle-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
