"""Link isolated raw and padded functions at three code/table layouts."""
import subprocess
from tools.experiments import game_owner_mode_1514ea1c_direct as packet
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_mode_1514ea1c_direct_oracle import SYMS

def run():
    name='func_1514EA1C'
    for k,base in enumerate((0x15001000,0x1f008000,0x1000fff0)):
        symbols={key:((base&0xf0000000)|(value&0x0fffffff))+0x1000*k for key,value in SYMS.items() if key.startswith('func_')}
        symbols['jtbl_800A5E20']=(0x80007ff0,0x80008000,0x8001fff0)[k]
        truth=bound_blob(*payload(packet.OUT/'retail.o',name),symbols)
        for kind in ('after','retail','generated','generic'):
            obj=packet.OUT/(kind+'.o');text,functions,refs=parse_object(obj)
            refs={off:[(typ,'jtbl_800A5E20' if sym=='.rodata' else sym)for typ,sym in rows]for off,rows in refs.items()}
            assembly,unknown=emit_function(text,functions[name],refs,name,symbols)
            assert not unknown,unknown
            isolated=packet.assemble(assembly,'rebase-%s-%d'%(kind,k));ld=packet.OUT/('rebase-%s-%d.ld'%(kind,k));elf=ld.with_suffix('.elf')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%base)
            command=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',name,*['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(isolated)]
            result=subprocess.run(command,cwd=packet.ROOT/'conker',capture_output=True,text=True);assert result.returncode==0,result.stderr
            functions,_,_=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
            assert tuple(functions[name][:len(truth)])==tuple(truth),(k,kind)
