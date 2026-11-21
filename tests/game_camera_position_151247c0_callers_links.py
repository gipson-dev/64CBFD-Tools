from pathlib import Path
import itertools,json,struct,subprocess,sys
from tools.experiments import game_camera_position_151247c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_position_151247c0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=g.ENTRY
def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert len(census['direct_original_calls'])==1 and not census['aligned_loaded_pointer_literals']
 start=0x15126138;end=start+24;assert census['direct_original_calls'][0]['entry']==start+8
 rom=(root/'conker/conker.us.bin').read_bytes();offset=start-0x15000000+0x2D4B0;window=list(struct.unpack_from('>6I',rom,offset))
 assert window==[0x27BDFFE8,0xAFBF0014,0x0D4491F0,0xAFA40018,0x8FA40018,0x8C8203D0]
 elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,start,24);current_equal=elf[at:at+24]==struct.pack('>6I',*window)
 streams=g.programs()
 class Connected(g.Machine):
  def __init__(self,words,c,m,opening=window):
   self.c=c;code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code[end]=0
   FactoryOracle.__init__(self,opening,m,c,entry=start,s=g.SYMS,arguments=(g.CAMERA,),connected=code)
   self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:
    a=tuple(self.arguments(1));assert a==(g.CAMERA,);self.calls.append((t,a));self.events.append(('CALL',t,a))
   else:super().record_call(t)
 cases=[g.Case(phase=phase,disabled=disabled,counter=counter,paired=paired,pattern=pattern,offset=offset,target=g.bits(-1.),mutation=mutation)for phase,disabled,counter,paired,pattern,offset,mutation in itertools.product((0,8),(0,1),(0,255),(0,1),(0,2),(0,g.bits(2.)),(0,2))]
 for c in cases:
  initial=g.fixture(c);expected,calls=g.reference(initial,c);states=[]
  for w in streams:
   m=Connected(w,c,dict(initial))
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert(g.public(m.memory),m.calls)==(expected,[(ENTRY,(g.CAMERA,))]+calls),c
   assert m.r[29]==g.STACK+c.phase-24 and m.r[4]==g.CAMERA and m.r[2]==g.read(m.memory,g.CAMERA+0x3D0)
   assert g.read(m.memory,g.STACK+c.phase)==g.CAMERA
   states.append(g.state(m))
  assert states[0]==states[1]==states[2]
 rejected=[];c=g.Case(offset=g.bits(2.));initial=g.fixture(c);expected,calls=g.reference(initial,c)
 for label,index,value in(('lost-camera-home-delay',3,0),('skipped-target-call',2,0)):
  changed=list(window);changed[index]=value;failed=False;probe=dict(initial)
  # A valid alternate pointer makes the lost-home control observable without
  # counting an oracle failure or unmapped-memory exception as a rejection.
  g.put(probe,g.STACK+c.phase,g.CAMERA+4)
  try:m=Connected(streams[0],c,probe,changed);m.run()
  except WindowBoundary:
   failed=(g.public(m.memory),m.calls)!=(expected,[(ENTRY,(g.CAMERA,))]+calls)or m.r[4]!=g.CAMERA or m.r[2]!=g.read(m.memory,g.CAMERA+0x3D0)
  assert failed,label;rejected.append(label)
 r={'parent':'func_15126138','window':hex(start),'words':6,'cases_per_stream':len(cases),'streams':3,'current_window_equals_original':current_equal,'effective_controls':rejected,
 'camera_saved_in_caller_incoming_home':True,'camera_reloaded_after_target':True,'whole_caller_claim':False,'source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)

from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function

def links():
    where=out/'links';where.mkdir(exist_ok=True);reports=[]
    files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/game_14FF90.c.o'}
    parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_151247C0'],parsed[2],'func_151247C0',g.SYMS)
    assert not missing,missing
    isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
    assert payload(isolated,'func_151247C0')==payload(files['raw'],'func_151247C0')
    files['raw']=isolated
    for code_delta,data_delta in((0,0),(0x10010,0x18020)):
        bind={name:address+(data_delta if address&0x80000000 else code_delta)for name,address in g.SYMS.items()}
        expected=bound_blob(*payload(files['retail'],'func_151247C0'),bind)
        for label,obj in files.items():
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            # The padded owner defines func_15125594 internally. Preserve its
            # real owner base instead of treating that definition as external.
            link_base=(0x15122AE0 if label=='padded' else ENTRY)+code_delta
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%link_base)
            undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines();definitions={}
            anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'))
            anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
            for line in undefined:
                n=line.split()[-1]
                if n in bind:definitions[n]=bind[n]
                elif n in anchored:definitions[n]=anchored[n]+(data_delta if anchored[n]&0x80000000 else code_delta)
                elif n.startswith(('D_','func_')):
                    value=int(n.split('_')[1],16);definitions[n]=value+(data_delta if value&0x80000000 else code_delta)
                else:raise AssertionError(('unqualified undefined symbol',n))
            q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_151247C0',
                *['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert q.returncode==0,q.stderr
            linked_symbols={n:row[1]for _,n,row,_ in symbol_rows(elf.read_bytes())if n}
            assert linked_symbols['func_151247C0']==ENTRY+code_delta
            if label=='padded':assert linked_symbols['func_15125594']==g.SYMS['func_15125594']+code_delta
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump')
            assert tuple(functions['func_151247C0'][:189])==tuple(expected),(label,code_delta)
            reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':189,'GNU_equals_independent_binding':True})
    kinds={kind for entries in payload(files['raw'],'func_151247C0')[1].values()for kind,name in entries}
    assert kinds=={'R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'},kinds
    r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':True,'target_has_data_relocations':True,'raw_scope':'Exact isolated target payload and code/data bindings; unused raw-owner data is outside this link scope.',
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))



if __name__=='__main__':
 if len(sys.argv)==1:caller_checks()
 links()
