import unittest
from tools.experiments import game_contact_effect_1516a3f4_match as packet
from tools.tests import game_contact_effect_1516a3f4_oracle as oracle
from tools.tests import game_contact_effect_1516a3f4_faults as faults
from tools.tests import game_contact_effect_1516a3f4_native as native
from tools.tests import game_contact_effect_1516a3f4_rebase as rebase
class ContactEffectPrivateScreen(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.state=packet.prepare()
 def test_guest_model(self):oracle.run()
 def test_fault_prefix(self):faults.run()
 def test_native_and_controls(self):native.run()
 def test_rebase(self):rebase.run()
