from unittest import TestCase
import kli.tick

__author__ = 'sean'


class Test_Ticking(TestCase):
  def setUp(self):
    self.TG = kli.tick.TruncatedGaussian(cv=.5)
    self.FTG = self.TG.flatten(seed=17)
    self.FTG.sim(1000)
    self.IG = kli.tick.InverseGaussian(cv=.5)
    self.FIG = self.IG.flatten(seed=71)
    self.FIG.sim(1000)

  def test_Tick_KL(self):
    self.assertEquals(self.FIG.KL(self.FTG), 1234567)

  def test_TickTG_RootFindMu(self):
    self.assertEquals(self.FTG.mu_norm, 2345678)

  def test_TickTG_RootFindSig(self):
    self.assertEquals(self.FTG.sig_norm, 3456789)
