"""Effective missing argument/save delay controls for both original callers."""
from pathlib import Path
import json
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
from tools.tests import game_audio_command_dispatch_1509e730_callers as callers
def run():
    report={}
    for name in('varargs-missing-home-delay','varargs-missing-command-load','interpreter-missing-packet-delay','interpreter-missing-handle-delay'):
        reason='effects'if name=='varargs-missing-home-delay'else'original caller argument transfer'
        try:callers.run(control=name)
        except AssertionError as error:
            assert reason in str(error),(name,error)
            report[name]=dict(rejected=True,reason=reason)
        else:raise AssertionError('Caller defect was not detected: '+name)
    r=dict(passes=True,controls=report,source_installed=recovery.installed(),matching_credit=0)
    (recovery.OUT/'caller-controls.json').write_text(json.dumps(r,indent=2)+'\n');return r
