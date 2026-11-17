"""Raw semantic and full normalized RAM/provider-frame execution checks."""
import json,struct
from tools.experiments import game_strip_update_151ad174_recovery as source
from tools.tests import game_strip_update_151ad174_private_oracle as o
from tools.tests.game_strip_update_151ad174_ordered_trace import Trace
from tools.tests import game_strip_update_151ad174_normalization as normalization
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
class BoundaryTrace(Trace):
    def __init__(self, *args):
        self.boundaries = []
        super().__init__(*args)

    def hook(self, target):
        assert self.r[29] == self.target_home - 776
        # hook is provider entry after the call delay instruction; observation
        # precedes the opaque provider's mutation or ABI clobbers.
        self.boundaries.append((self.pending, tuple(self.memory[self.target_home + i]
            for i in range(-776, 16)), tuple(self.fp)))
        return super().hook(target)


def programs():
    raw,refs=o.payload(source.OUT/'v82.o',source.NAME)
    raw=o.bound_blob(raw,refs,o.SYMS)
    intermediate,_=normalization.derive(raw)
    result={'retail':list(struct.unpack('>494I',(source.OUT/'retail.bin').read_bytes())),'raw':raw,'intermediate':intermediate}
    for label in ('strict','layout'):
        data,refs=o.payload(source.OUT/('strip-update-padded-'+label+'.o'),source.NAME)
        result[label]=o.bound_blob(data,refs,o.SYMS)
    if source.installed():
        data=(source.ROOT/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(data,source.ENTRY,source.SIZE)
        result['production']=list(struct.unpack_from('>494I',data,at))
    return result


def main():
    codes=programs();coverage={name:set()for name in codes};count=operations=boundaries=0
    for case in o.cases():
        initial=o.fixture(case);expected,calls=o.reference(initial,case)
        executions={name:BoundaryTrace(words,initial,case).run()for name,words in codes.items()}
        retail=executions['retail']
        for name,execution in executions.items():
            assert o.public(execution.memory)==o.public(expected),(name,'public',o.asdict(case))
            assert execution.service.calls==calls,(name,'calls',o.asdict(case))
            assert execution.fp==retail.fp,(name,'ordered FP',o.asdict(case))
            assert execution.loads==retail.loads,(name,'coefficient reads')
            assert tuple(execution.r[16:24])+(execution.r[28],execution.r[29],execution.r[30])==execution.saved_g
            assert tuple(execution.f[20:])==execution.saved_fp
            if name!='raw':
                assert execution.memory==retail.memory,(name,'all mapped RAM',o.asdict(case))
                assert execution.boundaries==retail.boundaries,(name,'provider frames',o.asdict(case))
            coverage[name].update(execution.visits)
        count+=1;operations+=len(retail.fp);boundaries+=len(retail.boundaries)
    assert count==544 and operations==648522 and boundaries==1976
    report=dict(cases_per_stream=count,streams=list(codes),words_visited={k:len(v)for k,v in coverage.items()},
        ordered_FP_operations=operations,provider_boundaries=boundaries,
        all_normalized_mapped_RAM_and_792_private_bytes_equal=True,raw_public_and_ordered_FP_equal=True,
        source_installed=source.installed(),c_match_credit=0)
    (source.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
