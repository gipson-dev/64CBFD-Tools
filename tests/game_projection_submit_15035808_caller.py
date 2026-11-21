"""Execute all three actual ten-argument caller windows with explicit scaffolds.

The original JAL, FP/GPR forwarding, final delay store and following index
increment are executed. This is a connected window test, not full callers.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
from dataclasses import replace
import json,struct
from tools.tests import game_projection_submit_15035808_oracle as g
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK
OUT=recovery.OUT;CANARY=0x110100;RECORD=0x110000
CONFIG=[dict(name='actor-height',rom=0x63744,entry=0x15036294,words=10,mode=1,increment_reg=17,continuation=0x150362bc),
    dict(name='record-plane',rom=0xce400,entry=0x150a0f50,words=21,mode=2,increment_reg=18,continuation=0x150a0fdc),
    dict(name='actor-floor',rom=0xce45c,entry=0x150a0fac,words=11,mode=1,increment_reg=18,continuation=0x150a0fd8)]

def prepared(c,config):
    c=replace(c,mode=config['mode']);memory=g.fixture(c);actor=g.ACTORS+c.index*0x32c
    memory.update({RECORD+i:0xa5 for i in range(0x104)})
    alpha=g.inputs(c)[-1];zero=g.bits(0.0);height=g.bits(-7.5)
    if config['name']=='record-plane':
        for off,v in zip((0,2,4),(13,-7,31)):g.write(memory,RECORD+off,v,2)
        g.write(memory,RECORD+0x10,g.bits(0.25))
        params=(g.bits(13.0),g.bits(-7.0),g.bits(31.0),zero,g.bits(0.25),g.bits(100.0),g.bits(200.0),alpha)
    else:
        g.write(memory,actor+0x180,height)
        params=(g.read(memory,actor+0x14),height,g.read(memory,actor+0x1c),zero,zero,g.bits(100.0),g.bits(150.0),alpha)
    g.write(memory,CANARY,0x12345678)
    return replace(c,argument_words=params),memory

class Connected(g.Oracle):
    def __init__(self,window,callee,memory,c,config,drop_delay=False):
        g.Providers.initialize(self,c,memory);self.boundaries=[];self.config=config;self.entry_arguments=[]
        prefix=(0x27bdffc0,0xafbf003c,0xafb00030,0xafb10034,0xafb20038)
        index=config['increment_reg'];increment=(9<<26)|(index<<21)|(index<<16)|1
        # The first CDE80 path has an original unconditional branch whose delay
        # increments S2. The explicit continuation begins at its real target.
        actual_after=(0x1000000d,increment)if config['name']=='record-plane'else(increment,)
        suffix=(0x3c080011,0x35080100,(43<<26)|(8<<21)|(index<<16),
            0x8fb00030,0x8fb10034,0x8fb20038,0x8fbf003c,0x03e00008,0x27bd0040)
        if drop_delay:window=window[:-1]+(0,)
        entry=config['entry']-4*len(prefix)
        extra={g.ENTRY+4*i:w for i,w in enumerate(callee)}
        # For straight-line continuations the actual increment occupies the
        # first word; the synthetic stores start immediately after it.
        suffix_entry=config['continuation']+(4 if config['name']!='record-plane'else 0)
        extra.update({suffix_entry+4*i:w for i,w in enumerate(suffix)})
        TimingOracle.__init__(self,prefix+window+actual_after,memory,phase=c.phase,entry=entry,arguments=(),connected=extra)
        actor=g.ACTORS+c.index*0x32c
        self.r[4:6]=[config['mode'],c.index]
        if config['name']=='actor-height':
            self.r[16]=actor;self.r[17]=c.index;self.f[0]=g.bits(-7.5)
            for r,v in((20,0.0),(26,100.0),(28,150.0)):self.f[r]=g.bits(v)
            self.f[30]=c.argument_words[-1]
        else:
            self.r[16]=RECORD;self.r[17]=actor;self.r[18]=c.index
            self.f[22]=g.bits(0.0);self.f[24]=c.argument_words[-1];self.f[28]=g.bits(150.0)
            self.f[20]=g.bits(100.0)
            if config['name']=='record-plane':self.r[25]=31;self.f[0]=g.bits(100.0);self.f[2]=g.bits(200.0)
        self.before=self.r.copy();self.saved_f=self.f[20:].copy()
    def record_call(self,target):
        if target==g.ENTRY:
            values=tuple(self.arguments(10));expected=(self.c.mode,self.c.index,*g.inputs(self.c))
            assert values==expected,('caller argument packet',self.config['name'],values,expected)
            self.entry_arguments.append(values);return
        return super().record_call(target)

def run():
    rom=(ROOT/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>345I',rom,0x62cb8)
    normalized=struct.unpack('>344I',(OUT/'matrix-normal-form.bin').read_bytes())
    reports=[];corpus=list(g.cases())
    for config in CONFIG:
        window=struct.unpack_from('>%dI'%config['words'],rom,config['rom'])
        assert window[-2]==0x0d40d602 and window[-1]>>26==57
        cases=corpus[768:1024]+[c for c in corpus[1030:]if c.mode==config['mode']]
        count=calls=0
        for c in cases:
            c,memory=prepared(c,config);expected=g.Reference(memory,c).run();g.write(expected.memory,CANARY,c.index+1)
            models=[]
            for stream in(normalized,retail):
                model=Connected(window,stream,memory,c,config).run()
                assert len(model.entry_arguments)==1 and model.trace==expected.trace,(config['name'],c,'connected calls')
                assert g.public(model.memory)==g.public(expected.memory),(config['name'],c,'complete public state and continuation')
                models.append(model)
            assert models[0].memory==models[1].memory,(config['name'],c,'complete connected RAM')
            count+=1;calls+=len(expected.trace)
        c,memory=prepared(cases[0],config)
        try:Connected(window,normalized,memory,c,config,drop_delay=True).run()
        except AssertionError as error:assert 'caller argument packet'in str(error),str(error)
        else:raise AssertionError(('Ineffective delay store control',config['name']))
        reports.append(dict(name=config['name'],cases=count,logical_helper_calls=calls,actual_window_words=config['words'],
            original_JAL_and_delay_store=True,all_10_arguments=True,original_following_increment=True,
            original_unconditional_continuation_branch=config['name']=='record-plane',effective_missing_delay_control=True,
            synthetic_prefix_words=5,synthetic_suffix_words=9,complete_connected_RAM_equal=True,full_caller_claim=False))
    report=dict(callers=reports,cases=sum(r['cases']for r in reports),all_three_actual_call_sites=True,matching_credit=0)
    (OUT/'caller-windows.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
