"""Independent scalar-Kalman reference for the pricing posterior update."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
from loop import ElasticityLearner
class Posterior(unittest.TestCase):
 def test_matches_rank_one_update(self):
  m=ElasticityLearner(-2.,1.,3.,2.,noise_sd=.6);mu=m.mu.copy();cov=m.Sigma.copy();x=np.array([1.,np.log(10.)]);y=np.log(20.5);gain=cov@x/(.36+x@cov@x)
  expected_mu=mu+gain*(y-x@mu);expected_cov=cov-np.outer(gain,x@cov)
  m.update(10,20);np.testing.assert_allclose(m.mu,expected_mu,atol=1e-12);np.testing.assert_allclose(m.Sigma,expected_cov,atol=1e-12);self.assertGreaterEqual(np.linalg.eigvalsh(m.Sigma).min(),0)
 def test_invalid_observation(self):
  m=ElasticityLearner(-2.,1.,3.,2.)
  for price,units in [(0,1),(-1,1),(1,-1),(float('nan'),1)]:
   with self.subTest(price=price,units=units),self.assertRaises(ValueError):m.update(price,units)
if __name__=='__main__':unittest.main()
