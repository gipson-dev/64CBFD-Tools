from pathlib import Path
import itertools,json,struct,subprocess,sys
from tools.experiments import game_camera_mode_gates_1512317c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_mode_gates_1512317c_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
ENTRY=g.ENTRY

def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert len(census['direct_original_calls'])==1 and not census['aligned_loaded_pointer_literals']
 start=0x15122F10;end=start+16;assert census['direct_original_calls'][0]['entry']==start
 rom=(root/'conker/conker.us.bin').read_bytes();offset=start-0x15000000+0x2D4B0;window=list(struct.unpack_from('>4I',rom,offset))
 assert window==[0x0D448C5F,0x02002025,0x0D4494E5,0x02002025]
 elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,start,16);current_equal=elf[at:at+16]==struct.pack('>4I',*window)
 streams=g.programs()
 class Connected(g.Machine):
  def __init__(self,words,c,m,opening=window):
   self.c=c;code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code[end]=0
   FactoryOracle.__init__(self,opening,m,c,entry=start,s=g.SYMS,arguments=(g.OTHER,),connected=code)
   self.r[16]=g.CAMERA;self.r[17]=g.OTHER;self.before=self.r[:]
   self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:
    a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
   else:super().record_call(t)
  def hook(self,t):
   if t==g.INDEX and self.calls[-1][1][0]!=g.CAMERA:
    a=self.calls[-1][1][0];v=g.read(self.memory,a+0x2C);assert v
    g.put(self.memory,a,(v&-v).bit_length()-1,2)
    for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
   else:super().hook(t)
 cases=[g.Case(mode=mode,input=inp,edge=edge,slot=slot,substate=substate,mutation=mutation,pattern=pattern)for mode,inp,edge,slot,substate,mutation,pattern in itertools.product((1,0x100),(0,16),(0,16),(0,1),(0,3),(0,1,2,4),(0,1))]
 for c in cases:
  initial=g.fixture(c);expected,calls=g.reference(initial,c);g.index_effect(expected);expected_calls=[(ENTRY,(g.CAMERA,))]+calls+[(g.INDEX,(g.CAMERA,))];states=[]
  for w in streams:
   m=Connected(w,c,dict(initial))
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert(g.public(m.memory),m.calls)==(expected,expected_calls),c
   assert m.r[29]==g.STACK+c.phase and m.r[16]==g.CAMERA and m.r[17]==g.OTHER
   states.append(g.state(m))
  assert states[0]==states[1]==states[2]
 rejected=[];c=g.Case(mode=1);initial=g.fixture(c);expected,calls=g.reference(initial,c);g.index_effect(expected);expected_calls=[(ENTRY,(g.CAMERA,))]+calls+[(g.INDEX,(g.CAMERA,))]
 for label,index,value in(('skipped-target',0,0),('wrong-next-delay-argument',3,0x02202025)):
  changed=list(window);changed[index]=value
  m=Connected(streams[0],c,dict(initial),changed)
  try:m.run();raise AssertionError('missing caller boundary')
  except WindowBoundary:pass
  assert(g.public(m.memory),m.calls)!=(expected,expected_calls),label;rejected.append(label)
 r={'parent':'func_15122C5C','window':hex(start),'words':4,'cases_per_stream':len(cases),'streams':3,'current_window_equals_original':current_equal,'effective_controls':rejected,
  'S0_camera_argument_and_following_call_delays_verified':True,'whole_caller_claim':False,'scope':'Original ROM caller window; current parent remains a placeholder. Valid alternate next-call argument in the negative control.',
  'source_installed':packet.installed(),'matching_credit':0}
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
    parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_1512317C'],parsed[2],'func_1512317C',g.SYMS)
    assert not missing,missing
    isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
    assert payload(isolated,'func_1512317C')==payload(files['raw'],'func_1512317C')
    files['raw']=isolated
    for code_delta,data_delta in((0,0),(0x10010,0x18020)):
        bind={name:address+(data_delta if address&0x80000000 else code_delta)for name,address in g.SYMS.items()}
        expected=bound_blob(*payload(files['retail'],'func_1512317C'),bind)
        for label,obj in files.items():
            prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
            # The padded owner defines func_15123934 internally. Preserve its
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
            q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1512317C',
                *['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
            assert q.returncode==0,q.stderr
            linked_symbols={n:row[1]for _,n,row,_ in symbol_rows(elf.read_bytes())if n}
            assert linked_symbols['func_1512317C']==ENTRY+code_delta
            if label=='padded':assert linked_symbols['func_15123934']==g.SYMS['func_15123934']+code_delta
            functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump')
            assert tuple(functions['func_1512317C'][:227])==tuple(expected),(label,code_delta)
            reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':227,'GNU_equals_independent_binding':True})
    kinds={kind for entries in payload(files['raw'],'func_1512317C')[1].values()for kind,name in entries}
    assert kinds=={'R_MIPS_26'},kinds
    r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':False,'target_has_data_relocations':False,'raw_scope':'Exact isolated target payload and code bindings; unused raw-owner data is outside this link scope.',
       'source_installed':packet.installed(),'matching_credit':0}
    (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))




if __name__=='__main__':
 if len(sys.argv)==1:caller_checks()
 links()
