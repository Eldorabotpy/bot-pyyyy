import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'modules/combat/criticals.py'
spec=importlib.util.spec_from_file_location('crit_test',p);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class DamageTests(unittest.TestCase):
 def roll(self,a,t,options=None,rolls=None):
  with patch.object(c.random,'random',side_effect=rolls or [0.99]*8):return c.roll_damage(a,t,options)
 def test_attack_and_defense(self):self.assertEqual(self.roll({'attack':100},{'defense':20})[0],80)
 def test_magic_uses_magic_attack(self):self.assertEqual(self.roll({'attack':100,'magic_attack':40},{'defense':500},{'is_magic':True})[0],40)
 def test_dodge_and_accuracy(self):
  self.assertEqual(self.roll({'attack':100},{'dodge_chance_flat':0.5},rolls=[0.1])[0],0)
  self.assertEqual(self.roll({'attack':100,'accuracy_flat':0.5},{'dodge_chance_flat':0.5},rolls=[0.1,0.99])[0],100)
 def test_undodgeable_stat(self):self.assertEqual(self.roll({'attack':100,'cannot_be_dodged':True},{'dodge_chance_flat':0.75},rolls=[0.99])[0],100)
 def test_critical_immunity(self):self.assertFalse(self.roll({'attack':100,'crit_chance_flat':100},{'crit_immune':True},rolls=[0.99,0.0])[1])
 def test_critical_resistance(self):self.assertFalse(self.roll({'attack':100,'crit_chance_flat':20},{'crit_resistance_flat':1},rolls=[0.99,0.0])[1])
 def test_resistance_damage_type(self):
  self.assertEqual(self.roll({'attack':100},{'resistance':{'physical':0.25}})[0],75)
  self.assertEqual(self.roll({'magic_attack':100},{'resistance':{'magic':0.5}},{'is_magic':True})[0],50)
 def test_luck_increases_critical_damage(self):self.assertGreater(c.get_crit_params({'luck':200})['mult'],c.get_crit_params({'luck':5})['mult'])
if __name__=='__main__':unittest.main(verbosity=2)
