"""Detector boundary tests; no real process mutation or experiment fixtures."""
import unittest
from check_health import classify

class HealthTests(unittest.TestCase):
    def test_active_prediction(self):
        self.assertEqual(classify('running',True,'prediction',4,4)[0],'healthy')
    def test_initial_prefill_is_not_stalled(self):
        self.assertEqual(classify('running',True,'prediction',143,0)[0],'healthy')
    def test_stalled_preparation(self):
        self.assertEqual(classify('running',True,'preparing',301,0)[0],'suspected_stall')
    def test_optimizer_uses_longer_threshold(self):
        self.assertEqual(classify('running',True,'optimization',600,20)[0],'healthy')
        self.assertEqual(classify('running',True,'optimization',901,20)[0],'suspected_stall')
    def test_dead_and_failed(self):
        self.assertEqual(classify('running',False,'prediction',0)[0],'missing_process')
        self.assertEqual(classify('failed',True,'prediction',0)[0],'failed')
    def test_intentional_pause_and_completion(self):
        self.assertEqual(classify('paused',False,'prediction',99999)[0],'paused')
        self.assertEqual(classify('complete',False,'prediction',99999)[0],'complete')
    def test_progressing_slowdown(self):
        self.assertEqual(classify('running',True,'prediction',10,20,8,True,True)[0],'slowdown')

if __name__=='__main__':unittest.main()
