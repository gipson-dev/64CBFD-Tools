"""Both complete-owner padders, original data owner and GNU code/data rebases."""
from pathlib import Path
import json,os,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_record_payload_tables_15017114_match as source
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;conker=root/'conker'
    symbols={r[1]:r[2][1]for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())}
    texts={'generated':pg.emit_padded_assembly(out/'selected.o',conker/'asm/43D00.s',filename='generated_43D00',word_patches_path=out/'proposed-guards.csv'),'c':pc.emit_padded_assembly(out/'selected.o',conker/'retail_layout.us.txt','generated_43D00',word_patches_path=out/'proposed-guards.csv')}
    for name,text in texts.items():
        (out/(name+'-padded.s')).write_text(text)
        q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(name+'-padded.o')),str(out/(name+'-padded.s'))],cwd=conker,capture_output=True,text=True)
        assert q.returncode==0,q.stderr
        assert same_functions(out/'guarded.o',out/(name+'-padded.o'))==3
        assert normalized_pools(out/'guarded.o')==normalized_pools(out/(name+'-padded.o'))
    def link(obj,code_delta,data_delta,label):
        _,functions,_=pg.parse_object(obj);offset=functions[source.NAME]['value']
        script,elf,binary=(out/(label+suffix)for suffix in('.ld','.elf','.bin'))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+code_delta-offset))
        undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines();defs={}
        for line in undefined:
            name=line.split()[-1]
            value=int(name.split('_')[1],16)if name.startswith(('func_','D_'))else symbols[name]
            defs[name]=(value+(code_delta if name.startswith('func_')or name in source.SDK else data_delta))&0xffffffff
        q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.NAME,*['--defsym=%s=0x%X'%v for v in defs.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
        assert q.returncode==0,q.stderr
        subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
        return binary.read_bytes()[offset:offset+source.SLOT_SIZE]
    for i,(code_delta,data_delta)in enumerate(((0,0),(0x10000000,0x12348000),(0x50000000,0x23457ffc),(0x80000000,0x34567ffe))):
        retail=link(out/'retail.o',code_delta,data_delta,f'rebase-{i}-retail')
        if i==0:assert retail==(conker/'conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SLOT_SIZE]
        for name in texts:assert link(out/(name+'-padded.o'),code_delta,data_delta,f'rebase-{i}-{name}')==retail
    report=dict(padders=2,full_owner=True,layouts=4,gnu_links=12,words=121,slot_words=123,alignment_words=2,owner_functions=3,guards=json.loads((out/'match-report.json').read_text())['guards'],data_owner_unchanged=True,carry_and_independent_code_data=True)
    (out/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
