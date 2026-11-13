def run():
 import sys
 from pathlib import Path
 from types import SimpleNamespace
 from intervaltree import IntervalTree
 from tools.experiments import game_hud_state_15178eb0_match as packet
 root=packet.ROOT;out=packet.OUT
 import tools
 sys.path.insert(0,str(Path(next(iter(tools.__path__)))/'n64splat/src'))
 from splat.util import symbols,options
 from splat.scripts import split
 source=out/'private-symbols.txt';text=source.read_text()
 line='func_15178EFC = 0x15178EFC; // type:func defined:true'
 assert text.count(line)==1
 for defined in (True,False):
  symbols.all_symbols=[];symbols.all_symbols_dict={};symbols.all_symbols_ranges=IntervalTree()
  lines=text.splitlines() if defined else text.replace(line,line.replace('defined:true','defined:false')).splitlines()
  symbols.handle_sym_addrs(source,lines,[])
  matches=[s for s in symbols.all_symbols if s.name=='func_15178EFC'];assert len(matches)==1
  target=matches[0];target.referenced=True
  assert (target.vram_start,target.type,target.defined)==(0x15178EFC,'func',defined)
  symbols.add_symbol(symbols.Symbol(0x15500000,given_name='unresolved_canary',type='func',referenced=True))
  dest=out/('splat-defined-%s.txt'%defined)
  options.opts=SimpleNamespace(create_undefined_funcs_auto=True,undefined_funcs_auto_path=dest)
  split.write_undefined_funcs_auto()
  expected=('' if defined else 'func_15178EFC = 0x15178EFC;\n')+'unresolved_canary = 0x15500000;\n'
  assert dest.read_text()==expected
 print('actual Splat parser/writer, unresolved canary, and missing-defined negative passed')
