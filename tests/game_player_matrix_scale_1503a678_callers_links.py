from pathlib import Path
import csv,io,itertools,json,struct,subprocess,sys
from tools.experiments import game_player_matrix_scale_1503a678_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_player_matrix_scale_1503a678_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools import pad_generated_object as pg
from tools.experiments.alternative_source_draft_word_screen import emit_function
ENTRY=g.ENTRY
WINDOW,CONTINUATION,PARENT,INITIAL,TABLE=0x150A9750,0x150A96DC,0x1503A7F0,0x15036F34,0x8008857C

def caller_checks():
    census=json.loads((out/'caller-census.json').read_text())
    assert census['direct_original_calls']==[dict(entry=0x1503A818,ROM=0x67CC8,kind='JAL')]
    assert census['aligned_loaded_pointer_literals']==[dict(section='.game_data',address=0x8008859C)]
    rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
    window=list(struct.unpack_from('>139I',rom,0xD6C00));parent=list(struct.unpack_from('>16I',rom,0x67CA0))
    for start,words in((WINDOW,window),(PARENT,parent)):
        at=elf_slot_offset(elf,start,4*len(words));assert elf[at:at+4*len(words)]==struct.pack('>%dI'%len(words),*words)
    streams=g.programs();coverage=set();count=0

    class Connected(g.Machine):
        def __init__(self,words,c,memory,selected,opening=window):
            self.c=c;self.observations=[];self.selected=selected;self.target_entries=[];self.initial_calls=[]
            code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code.update(zip(range(PARENT,PARENT+64,4),parent))
            FactoryOracle.__init__(self,opening,memory,c,entry=WINDOW,s=g.SYMS,arguments=(),connected=code)
            self.r[19]=0x20 if selected==ENTRY else 0x28
            self.before=list(self.r);self.before_f=list(self.f)
            owned=dict(self.code);owned[CONTINUATION]=0
            self.code=WindowCode(owned,self);self.code.ends={CONTINUATION}
        def record_call(self,t):
            if t in(ENTRY,PARENT):self.target_entries.append(t);self.events.append(('CONNECTED',t))
            elif t==INITIAL:
                self.initial_calls.append(self.memory[g.PHASE]);self.calls.append((t,()));self.events.append(('CALL',t,()))
            else:super().record_call(t)
        def hook(self,t):
            if t!=INITIAL:return super().hook(t)
            assert self.memory[g.PHASE]==0;self.memory[g.PHASE]=127
            for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
            for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

    for selected,kind,scale,counter,page,mutation,phase in itertools.product((ENTRY,PARENT),(0,0x22,255),(0,64,255),(0,1,255),(0,1),(0,3),(0,8)):
        c=g.Case(kind=kind,scale=scale,counter=counter,page=page,mutation=mutation,phase=phase)
        initial=g.fixture(c)
        for at,value in((TABLE+0x20,ENTRY),(TABLE+0x24,1),(TABLE+0x28,PARENT),(TABLE+0x2C,1)):g.put(initial,at,value)
        expected=list(g.reference(initial,c,home=g.STACK+c.phase-0x108-(32 if selected==PARENT else 0)))
        if selected==PARENT:expected[1]=[(INITIAL,())]+expected[1]
        states=[]
        for words in streams:
            machine=Connected(words,c,dict(initial),selected)
            try:machine.run();raise AssertionError('Missing callback continuation boundary')
            except WindowBoundary:pass
            actual=(g.public(machine.memory),machine.calls,machine.observations)
            if actual!=tuple(expected):
                differences=[(hex(at),value,actual[0].get(at))for at,value in expected[0].items()if actual[0].get(at)!=value]
                raise AssertionError((c,hex(selected),machine.calls,expected[1],differences[:8],machine.observations==expected[2]))
            assert machine.target_entries==([ENTRY]if selected==ENTRY else[PARENT,ENTRY])
            assert machine.initial_calls==([]if selected==ENTRY else[0])
            assert machine.r[29]==g.STACK+c.phase and machine.f==machine.before_f
            for reg in range(32):
                if reg not in(17,19):assert machine.r[reg]==machine.before[reg],(c,reg)
            assert machine.r[17]==selected and machine.r[19]==1
            states.append(g.state(machine));coverage.update(machine.visits)
        assert states[0]==states[1]==states[2],c
        count+=1
    assert set(range(WINDOW,WINDOW+139*4,4))<=coverage
    assert set(range(PARENT,PARENT+64,4))<=coverage
    controls=[]
    for label,index,replacement in(('lost-V0-restore',(0x150A9904-WINDOW)//4,0),('lost-F0-restore',(0x150A9878-WINDOW)//4,0),('wrong-table-offset',2,0x26310028)):
        changed=list(window);changed[index]=replacement;c=g.Case(kind=0x22 if label=='lost-F0-restore'else 0);initial=g.fixture(c)
        for at,value in((TABLE+0x20,ENTRY),(TABLE+0x24,1),(TABLE+0x28,PARENT),(TABLE+0x2C,1)):g.put(initial,at,value)
        try:
            machine=Connected(streams[1],c,initial,ENTRY,changed)
            try:machine.run()
            except WindowBoundary:pass
            rejected=machine.r[2]!=machine.before[2]or machine.f!=machine.before_f or machine.target_entries!=[ENTRY]
        except(AssertionError,KeyError):rejected=True
        assert rejected,label;controls.append(label)
    actual_helpers={}
    for va,n in((g.IDENT,20),(g.SCALE,20),(g.MULT,78)):
        at=va-0x15000000+0x2D4B0;words=struct.unpack_from('>%dI'%n,rom,at)
        actual_helpers.update(zip(range(va,va+4*n,4),words))
    helpercoverage=set();helpercases=0
    for scale,counter in itertools.product(range(256),(0,1)):
        c=g.Case(scale=scale,counter=counter,page=scale&1);initial=g.fixture(c);expected=g.reference(initial,c)
        for words in streams:
            machine=g.Machine(words,c,dict(initial),connected=actual_helpers).run()
            assert(g.public(machine.memory),machine.calls,machine.observations)==expected,('original matrix helpers',c)
            helpercoverage.update(machine.visits)
        helpercases+=1
    helperwords={hex(va):sum(va+4*i in helpercoverage for i in range(n))for va,n in((g.IDENT,20),(g.SCALE,20),(g.MULT,78))}
    assert list(helperwords.values())==[19,19,76],helperwords
    padding={g.IDENT:[19],g.SCALE:[19],g.MULT:[76,77]}
    for va,n in((g.IDENT,20),(g.SCALE,20),(g.MULT,78)):
        assert[i for i in range(n)if va+4*i not in helpercoverage]==padding[va]
        assert all(actual_helpers[va+4*i]==0 for i in padding[va])
    report=dict(full_save_callback_window_words=139,callback_entry=hex(WINDOW),actual_JALR='0x150A986C',continuation=hex(CONTINUATION),direct_parent='func_1503A7F0',parent_words=16,cases_per_stream=count,streams=3,all_callback_and_parent_words_covered=True,raw_and_normalized_complete_boundary_states_equal=True,callback_restores_volatile_V0_and_all_FPRs=True,loaded_entry_flag=1,effective_controls=controls,original_matrix_helper_cases_per_stream=helpercases,original_matrix_helper_coverage=helperwords,original_matrix_helper_unreachable_alignment_words={hex(k):v for k,v in padding.items()},limits='Exact callback window and direct parent execute with target. Parent initializer and bcopy use bounded contracts; all three original matrix helpers also execute in the separate connected group. No full renderer/hardware claim.',source_installed=packet.installed(),matching_credit=0)
    (out/'caller-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report

def guard_checks():
    baseline=(out/'baseline/conker/retail_word_patches.us.csv').read_bytes()
    selected=(out/'private-guards.csv').read_bytes();assert selected.startswith(baseline)
    rows=list(csv.DictReader(io.StringIO(selected.decode())));target=[r for r in rows if r['function']=='func_1503A678']
    assert len(target)==16 and all(r['filename']=='generated_64120'and r['omit']=='false'and not r['insert_after']for r in target)
    fields=list(rows[0]);where=out/'guard-controls';where.mkdir(exist_ok=True)
    a,ar=payload(out/'qualified-source/candidate.o','func_1503A678')
    b,br=payload(out/'image-qualification/retail.o','func_1503A678')
    assert len(a)==len(b)==376 and ar==br
    left,right=struct.unpack('>94I',a),struct.unpack('>94I',b)
    maps={16:{11:3},17:{21:3},22:{21:3},34:{16:2},35:{21:2,16:2},37:{16:2},38:{21:2},49:{21:3},36:{6:0},39:{11:0},50:{11:0},53:{16:10},55:{16:0},56:{16:0},57:{16:0},58:{16:10}}
    assert{i for i,(x,y)in enumerate(zip(left,right))if x!=y}==set(maps)
    for i,w in enumerate(left):
        for shift,value in maps.get(i,{}).items():w=(w&~(31<<shift))|(value<<shift)
        assert w==right[i]
    controls=[]
    for label in('wrong-word','wrong-relocation','wrong-function','wrong-owner','duplicate-offset'):
        changed=[dict(r)for r in rows];first=next(r for r in changed if r['function']=='func_1503A678')
        if label=='wrong-word':first['expected']='0xFFFFFFFF'
        elif label=='wrong-relocation':first['expected_relocations']='R_MIPS_HI16:D_8008FD90'
        elif label=='wrong-function':first['function']='func_1503A678_invalid'
        elif label=='wrong-owner':
            for r in changed:
                if r['function']=='func_1503A678':r['filename']='wrong_owner'
        else:changed.append(dict(first))
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(changed)
        file=where/(label+'.csv');file.write_text(stream.getvalue())
        try:
            text=pg.emit_padded_assembly(out/'qualified-source/candidate.o',root/'conker/asm/1E73B0.s',filename='generated_64120',word_patches_path=file)
            # A different owner legitimately selects no rows, which must fail exact output.
            rejected=label=='wrong-owner'and text!=(out/'image-qualification/padded.s').read_text()
        except ValueError:rejected=True
        assert rejected,label;controls.append(label)
    report=dict(guards=16,original_CSV_prefix_preserved=True,register_operand_changes_only=True,all_opcodes_immediates_offsets_targets_and_relocations_preserved=True,effective_controls=controls,insertions=0,omissions=0)
    (out/'guard-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report

def links():
    where=out/'links';where.mkdir(exist_ok=True)
    paths={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_64120.c.o'}
    parsed=parse_object(paths['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_1503A678'],parsed[2],'func_1503A678',g.SYMS);assert not missing
    file=where/'raw-target.s';file.write_text(assembly);isolated=file.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(file)],capture_output=True,check=True)
    assert payload(isolated,'func_1503A678')==payload(paths['raw'],'func_1503A678');paths['raw']=isolated
    anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'))
    anchored.update({name:row[1]for _,name,row,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if name})
    reports=[]
    for code_delta,data_delta in((0,0),(0x10010,0x18020)):
        bindings={name:value+(data_delta if value&0x80000000 else code_delta)for name,value in g.SYMS.items()}
        for label,obj in paths.items():
            expected=bound_blob(*payload(obj,'func_1503A678'),bindings)
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%((0x15036C70 if label=='padded'else ENTRY)+code_delta))
            definitions={}
            for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
                name=line.split()[-1];address=bindings.get(name)
                if address is None:
                    assert name in anchored,('unqualified binding',name);address=anchored[name]+(data_delta if anchored[name]&0x80000000 else code_delta)
                definitions[name]=address
            result=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1503A678',*['--defsym=%s=0x%X'%item for item in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert result.returncode==0,result.stderr
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');addresses={name:row[1]for _,name,row,_ in symbol_rows(elf.read_bytes())if name}
            assert addresses['func_1503A678']==ENTRY+code_delta
            assert tuple(functions['func_1503A678'][:94])==tuple(expected)
            reports.append(dict(stream=label,code_delta=code_delta,data_delta=data_delta,words=94,GNU_equals_independent_binding=True))
    guard_checks()
    report=dict(links=reports,target_relocation_kinds=['R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'],HI16_LO16_carry_exercised=True,source_installed=packet.installed(),matching_credit=0)
    (out/'GNU-links.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report


if __name__=='__main__':caller_checks();links()
