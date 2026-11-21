from pathlib import Path
import csv,itertools,json,struct,sys,subprocess
from tools.experiments import game_camera_state_flags_151236d0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_state_flags_151236d0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=g.ENTRY
def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert len(census['direct_original_calls'])==8 and not census['aligned_loaded_pointer_literals']
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();reports=[];streams=g.programs()
 layout=[row for row in csv.reader((root/'conker/retail_layout.us.txt').read_text().splitlines())if len(row)>=5 and row[0]=='game']
 for call in census['direct_original_calls']:
  start=call['entry'];n=4 if start in(0x151285B8,0x151285E0,0x15128608,0x15128630)else 2;end=start+4*n
  window=list(struct.unpack_from('>%dI'%n,rom,call['ROM']));assert window[0]==0x0D448DB4 and window[1]in(0x02002025,0x02202025)
  if n==4:assert window[2:]==[0x0D44A131,0x02002025]
  parent=next(row[2]for row in layout if int(row[3],16)<=start<int(row[4],16));register=17 if window[1]==0x02202025 else 16
  current_equal=elf[elf_slot_offset(elf,start,4*n):elf_slot_offset(elf,start,4*n)+4*n]==struct.pack('>%dI'%n,*window)
  class Connected(g.Machine):
   def __init__(self,words,c,m,opening=window):
    self.c=c;code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code[end]=0
    FactoryOracle.__init__(self,opening,m,c,entry=start,s=g.SYMS,arguments=(0xDEADC0DE,),connected=code)
    self.r[register]=g.CAMERA;self.before[register]=g.CAMERA;self.code=WindowCode(self.code,self);self.code.ends=(end,)
   def record_call(self,t):
    if t in(ENTRY,0x151284C4):
     args=tuple(self.arguments(1));assert args==(g.CAMERA,),(hex(t),args);self.calls.append((t,args));self.events.append(('CALL',t,args))
    else:super().record_call(t)
   def hook(self,t):
    if t==0x151284C4:
     for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xBA000000+reg
    else:super().hook(t)
  cases=[g.Case(phase=phase,flags=flags,mode=mode,y=g.bits(height),counter=counter,slot=255,mutation=mutation)for phase,flags,mode,height,counter,mutation in itertools.product((0,8),(0,1,4,5),(0,0x100,0x40000),(-1.,0.,1.),(0,1),(0,3))]
  for c in cases:
   initial=g.fixture(c);expected,calls=g.reference(initial,c);states=[];want=[(ENTRY,(g.CAMERA,))]+calls+([(0x151284C4,(g.CAMERA,))]if n==4 else[])
   for words in streams:
    m=Connected(words,c,dict(initial))
    try:m.run();raise AssertionError('missing caller boundary')
    except WindowBoundary:pass
    assert(g.public(m.memory),m.calls)==(expected,want),c
    assert m.r[register]==g.CAMERA and m.r[29]==g.STACK+c.phase;states.append(g.state(m))
   assert states[0]==states[1]==states[2]
  bad=list(window);bad[1]=0;c=g.Case();failed=False
  try:m=Connected(streams[0],c,g.fixture(c),bad);m.run()
  except AssertionError:failed=True
  except WindowBoundary:failed=not m.calls or m.calls[0]!=(ENTRY,(g.CAMERA,))
  assert failed
  reports.append({'parent':parent,'window':hex(start),'words':n,'camera_register':register,'cases_per_stream':len(cases),'current_window_equals_original':current_equal,'effective_controls':['lost-delay-camera']})
 r={'callers':reports,'streams':3,'whole_caller_claim':False,'current_transition_caller_preserved_in_44_neighbor_gate':True,'bounded_scope':'Original call/delay windows; four also include the following call. Unfinished whole parents remain separate.','source_installed':packet.installed(),'matching_credit':0}
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
    parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_151236D0'],parsed[2],'func_151236D0',g.SYMS)
    assert not missing,missing
    isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
    assert payload(isolated,'func_151236D0')==payload(files['raw'],'func_151236D0')
    files['raw']=isolated
    for code_delta,data_delta in((0,0),(0x10010,0x18020)):
        bind={name:address+(data_delta if address&0x80000000 else code_delta)for name,address in g.SYMS.items()}
        expected=bound_blob(*payload(files['retail'],'func_151236D0'),bind)
        for label,obj in files.items():
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            # The padded owner defines func_15124B18 internally. Preserve its
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
            q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_151236D0',
                *['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert q.returncode==0,q.stderr
            linked_symbols={n:row[1]for _,n,row,_ in symbol_rows(elf.read_bytes())if n}
            assert linked_symbols['func_151236D0']==ENTRY+code_delta
            if label=='padded':assert linked_symbols['func_15124B18']==g.SYMS['func_15124B18']+code_delta
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump')
            assert tuple(functions['func_151236D0'][:153])==tuple(expected),(label,code_delta)
            reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':153,'GNU_equals_independent_binding':True})
    kinds={kind for entries in payload(files['raw'],'func_151236D0')[1].values()for kind,name in entries}
    assert kinds=={'R_MIPS_26'},kinds
    r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':False,'target_has_data_relocations':False,'raw_scope':'Exact isolated target payload and code bindings; unused raw-owner data is outside this link scope.',
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':
 if len(sys.argv)==1:caller_checks()
 links()
