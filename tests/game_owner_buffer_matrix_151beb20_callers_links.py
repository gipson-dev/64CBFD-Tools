from pathlib import Path
from dataclasses import replace
import itertools
import json
import struct
import subprocess
import sys

from tools.experiments import game_owner_buffer_matrix_151beb20_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_owner_buffer_matrix_151beb20_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function

ENTRY=g.ENTRY
CALLER,PREDICATE,DISPATCH=0x150C52CC,0x150C5280,0x8008ADA8
GATE,MODE=0x800C35EA,0x800C35E8

def caller_checks():
    census=json.loads((out/'caller-census.json').read_text())
    assert not census['direct_original_calls']
    assert census['aligned_loaded_pointer_literals']==[dict(section='.game_data',address=DISPATCH)]
    rom=(root/'conker/conker.us.bin').read_bytes()
    elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
    caller=list(struct.unpack_from('>17I',rom,0xF277C))
    predicate=list(struct.unpack_from('>19I',rom,0xF2730))
    streams=g.programs()

    class Connected(g.Machine):
        def __init__(self,words,case,memory,opening=caller):
            self.c=case
            self.target_entries=[]
            code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words))
            code.update(zip(range(PREDICATE,PREDICATE+76,4),predicate))
            FactoryOracle.__init__(self,opening,memory,case,entry=CALLER,s=g.SYMS,arguments=(g.owner(case),),connected=code)

        def record_call(self,target):
            if target in (ENTRY,PREDICATE):
                if target==ENTRY:
                    self.target_entries.append(tuple(self.arguments(1)))
                    assert self.target_entries[-1]==(g.owner(self.c),)
                self.events.append(('CONNECTED',target))
            else:
                super().record_call(target)

    cases=[]
    for byte in range(256):
        cases.append((1,byte,g.Case(page=byte,pattern=byte%4)))
        cases.append((byte,11,g.Case(page=1,mutation=byte%8)))
    for gate,mode,page,mutation,phase in itertools.product((0,1,255),(0,11,12,13,255),(0,1),range(8),(0,8)):
        cases.append((gate,mode,g.Case(page=page,mutation=mutation,phase=phase)))
    coverage=set()
    for gate,mode,case in cases:
        initial=g.fixture(case)
        g.put(initial,DISPATCH,ENTRY)
        initial[GATE]=gate;initial[MODE]=mode
        skipped=gate==1 and mode in (11,12,13)
        expected=(g.public(initial),[],0) if skipped else g.reference(initial,case)
        states=[]
        for words in streams:
            machine=Connected(words,case,dict(initial)).run()
            assert (g.public(machine.memory),machine.calls,machine.r[2])==expected,(gate,mode,case)
            assert machine.target_entries==([] if skipped else [(g.owner(case),)])
            assert machine.r[29]==g.STACK+case.phase
            for register in (*range(16,24),30):
                assert machine.r[register]==machine.before[register]
            coverage.update(machine.visits)
            states.append(g.state(machine))
        assert states[0]==states[1]==states[2]
    assert set(range(CALLER,CALLER+68,4))<=coverage
    controls=[]
    case=g.Case()
    for label,index,value,gate,mode in (('skipped-callback',11,0,0,0),('wrong-owner-home',10,0x8FA4001C,0,0),('reversed-gate',5,0x14400003,1,11)):
        changed=list(caller);changed[index]=value
        initial=g.fixture(case);g.put(initial,DISPATCH,ENTRY);initial[GATE]=gate;initial[MODE]=mode
        expected=(g.public(initial),[],0) if gate==1 and mode in(11,12,13) else g.reference(initial,case)
        try:
            machine=Connected(streams[0],case,initial,changed).run()
            rejected=(g.public(machine.memory),machine.calls,machine.r[2])!=expected
        except (AssertionError,KeyError):
            rejected=True
        assert rejected,label
        controls.append(label)
    report=dict(caller='func_150C52CC',caller_words=17,predicate_words=19,cases_per_stream=len(cases),streams=3,covered_caller_words=17,covered_predicate_words=sum(PREDICATE+4*i in coverage for i in range(19)),dispatch_word=hex(DISPATCH),actual_JALR=hex(CALLER+44),current_caller_equals_original=elf[elf_slot_offset(elf,CALLER,68):elf_slot_offset(elf,CALLER,68)+68]==struct.pack('>17I',*caller),current_predicate_equals_original=elf[elf_slot_offset(elf,PREDICATE,76):elf_slot_offset(elf,PREDICATE,76)+76]==struct.pack('>19I',*predicate),effective_controls=controls,source_installed=packet.installed(),matching_credit=0)
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report

def links():
    where=out/'links';where.mkdir(exist_ok=True)
    paths={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_1E73B0.c.o'}
    parsed=parse_object(paths['raw'])
    assembly,missing=emit_function(parsed[0],parsed[1]['func_151BEB20'],parsed[2],'func_151BEB20',g.SYMS)
    assert not missing,missing
    file=where/'raw-target.s';file.write_text(assembly)
    isolated=file.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(file)],capture_output=True,check=True)
    assert payload(isolated,'func_151BEB20')==payload(paths['raw'],'func_151BEB20')
    paths['raw']=isolated
    anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'))
    anchored.update({name:row[1] for _,name,row,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes()) if name})
    reports=[]
    for code_delta,data_delta in ((0,0),(0x10010,0x18020)):
        bindings={name:value+(data_delta if value&0x80000000 else code_delta) for name,value in g.SYMS.items()}
        expected=bound_blob(*payload(paths['retail'],'func_151BEB20'),bindings)
        for label,obj in paths.items():
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            base=(0x151B9F00 if label=='padded' else ENTRY)+code_delta
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%base)
            definitions={}
            for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
                name=line.split()[-1]
                address=bindings.get(name)
                if address is None:
                    assert name in anchored,('unqualified binding',name)
                    address=anchored[name]+(data_delta if anchored[name]&0x80000000 else code_delta)
                definitions[name]=address
            result=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_151BEB20',*['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump')
            addresses={name:row[1]for _,name,row,_ in symbol_rows(elf.read_bytes())if name}
            assert addresses['func_151BEB20']==ENTRY+code_delta
            assert tuple(functions['func_151BEB20'][:93])==tuple(expected)
            reports.append(dict(stream=label,code_delta=code_delta,data_delta=data_delta,words=93,GNU_equals_independent_binding=True))
    report=dict(links=reports,target_relocation_kinds=['R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'],HI16_LO16_carry_exercised=True,source_installed=packet.installed(),matching_credit=0)
    (out/'GNU-links.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report

if __name__=='__main__':
    caller_checks()
    links()
