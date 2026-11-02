"""All three direct original callers: scale construction, o32 ABI and stack output."""
from dataclasses import replace
import itertools,json,struct
from tools.tests.game_embedded_integer_oscillator_integration import aligned_hits
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

WINDOWS=((0x1514FFEC,0x17D49C,9,0x15150010,22,20,0xA8),(0x15153D6C,0x18121C,9,0x15153D90,23,21,0xA8),(0x151D0E24,0x1FE2D4,7,0x151D0E40,22,20,0xC0))

def qualify(root,output,g):
    rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|(g.ENTRY>>2&0x3FFFFFF)
    sites=aligned_hits(rom,jal);assert sites==[0x17D4B8,0x181238,0x1FE2E8]
    assert not aligned_hits(rom,g.ENTRY)
    entry,s,roots=g.programs(output,0);records=[]
    for index,(start,off,words,end,basis_reg,output_reg,stack_offset)in enumerate(WINDOWS):
        window=struct.unpack_from('>%dI'%words,rom,off);count=0
        for rng,pattern,mode,shape,phase in itertools.product((0,0x87654380,0xFFFFFFFF),(0,3),(0,7,24,32),(None,4,7),(0,8)):
            home=g.STACK+phase;unit=g.bits(.25);radius=g.bits(3.);base=g.bits(-.5)
            scale=g.add(g.mul(unit,radius),base)
            c=g.Case(rng=rng,unit=unit,scale=scale,pattern=pattern,mutation=mode,phase=phase,out_index=-2 if shape is None else shape,output_override=home+stack_offset if shape is None else 0)
            initial=g.fixture(c)
            for at,value in((0x10,base),(0x14,radius),(0x1C,base),(0x20,radius)):g.put(initial,g.STATE+at,value)
            expected,calls,dest=g.reference(initial,c,s);calls=[(entry,(g.OWNER,scale,g.output(c))),*calls];models=[]
            for root_words in roots:
                code=dict(zip(range(entry,entry+240,4),root_words));code[end]=0
                m=g.Oracle(window,initial,c,s,start,connected=code,target_entry=entry)
                for reg,value in((16,g.STATE),(basis_reg,g.OWNER),(output_reg,g.output(c))):m.r[reg]=m.before[reg]=value
                m.f[0]=unit;m.f[20]=base;m.f[26]=radius
                m.code=WindowCode(m.code,m);m.code.ends=(end,)
                try:m.run()
                except WindowBoundary:pass
                else:raise AssertionError('Caller window boundary not reached')
                assert m.f[20]==base and m.f[26]==radius
                models.append(m)
            g.compare(models,c,expected,calls,dest);count+=1
        records.append(dict(entry=hex(start),words=words,return_boundary=hex(end),cases=count,executions=count*3,canonical_stack_output_offset=stack_offset,void_return_not_consumed=True))
    report=dict(success=True,original_callers=3,all_aligned_ROM_JAL_sites=sites,literal_target_pointers=0,windows=records,total_cases=sum(v['cases']for v in records),executions=sum(v['executions']for v in records),caller_scale_bits_and_three_argument_ABI_verified=True,original_stack_output_routes=True,additional_output_basis_alias_cases=True,callee_saved_F20_F26_preserved=True,whole_parents_executed=False,gameplay_acceptance_claimed=False)
    (output/'private-callers-v9.json').write_text(json.dumps(report,indent=2)+'\n');return report
