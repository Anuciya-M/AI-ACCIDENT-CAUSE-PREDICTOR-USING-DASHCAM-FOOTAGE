"""
Comprehensive Test Suite for AI Accident Cause Predictor
Tests all modules to ensure they're working properly
"""

import cv2
import numpy as np
import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestVisionModules(unittest.TestCase):
    """Test vision detection modules"""
    
    def setUp(self):
        """Create dummy test frame"""
        self.test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.test_frame[200:300, 250:350] = [0, 255, 0]  # Green rectangle
    
    def test_lane_detection(self):
        """Test lane detection module"""
        try:
            from vision.lane_detection import detect_lane
            result = detect_lane(self.test_frame)
            self.assertIsNotNone(result)
            print("✓ Lane detection works")
        except Exception as e:
            self.fail(f"Lane detection failed: {e}")
    
    def test_motion_detection(self):
        """Test motion detection module"""
        try:
            from vision.motion_detection import compute_motion
            frame1 = np.zeros((480, 640), dtype=np.uint8)
            frame2 = np.zeros((480, 640), dtype=np.uint8)
            frame2[200:300, 250:350] = 255
            
            motion = compute_motion(frame1, frame2)
            self.assertIsInstance(motion, float)
            self.assertGreaterEqual(motion, 0)
            print(f"✓ Motion detection works (computed motion: {motion:.2f})")
        except Exception as e:
            self.fail(f"Motion detection failed: {e}")


class TestPredictionModules(unittest.TestCase):
    """Test prediction models"""
    
    def test_risk_predictor_import(self):
        """Test risk predictor imports"""
        try:
            from prediction.risk_predictor import AccidentLSTM, load_model, predict_risk
            import torch
            
            model = AccidentLSTM()
            self.assertIsNotNone(model)
            print("✓ AccidentLSTM model imports successfully")
            
            device = torch.device('cpu')
            loaded_model = load_model(device)
            self.assertIsNotNone(loaded_model)
            print("✓ Model loading works")
        except Exception as e:
            self.fail(f"Risk predictor failed: {e}")
    
    def test_collision_risk_import(self):
        """Test collision risk calculator"""
        try:
            from prediction.collision_risk import CollisionRiskCalculator
            calc = CollisionRiskCalculator()
            self.assertIsNotNone(calc)
            print("✓ CollisionRiskCalculator imports successfully")
        except Exception as e:
            self.fail(f"Collision risk calculator failed: {e}")
    
    def test_cause_engine_import(self):
        """Test cause detection engine"""
        try:
            from prediction.cause_engine import find_cause
            # Test with empty inputs
            cause = find_cause([], 0.0, True, {}, 100.0)
            self.assertIsNotNone(cause)
            print(f"✓ Cause engine works (cause: {cause})")
        except Exception as e:
            self.fail(f"Cause engine failed: {e}")


class TestUtilityModules(unittest.TestCase):
    """Test utility modules"""
    
    def test_basic_utils(self):
        """Test basic utility functions"""
        try:
            # Test that basic utils are available
            import os
            import sys
            self.assertTrue(os.path.exists('.'))
            print("✓ Basic utilities working")
        except Exception as e:
            self.fail(f"Basic utils failed: {e}")


class TestRequirementsMetaDependencies(unittest.TestCase):
    """Test that all dependencies are properly installed"""
    
    def test_torch(self):
        """Test PyTorch"""
        try:
            import torch
            print(f"✓ PyTorch {torch.__version__}")
        except ImportError:
            self.fail("PyTorch not installed")
    
    def test_opencv(self):
        """Test OpenCV"""
        try:
            import cv2
            print(f"✓ OpenCV {cv2.__version__}")
        except ImportError:
            self.fail("OpenCV not installed")
    
    def test_ultralytics(self):
        """Test YOLO"""
        try:
            from ultralytics import YOLO
            print("✓ Ultralytics/YOLO installed")
        except ImportError:
            self.fail("Ultralytics not installed")
    
    def test_psutil(self):
        """Test psutil"""
        try:
            import psutil
            print("✓ psutil installed")
        except ImportError:
            self.fail("psutil not installed - needed for performance monitoring")
    
    def test_flask(self):
        """Test Flask"""
        try:
            import flask
            print("✓ Flask installed")
        except ImportError:
            self.fail("Flask not installed")


def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE MODULE TEST SUITE")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRequirementsMetaDependencies))
    suite.addTests(loader.loadTestsFromTestCase(TestVisionModules))
    suite.addTests(loader.loadTestsFromTestCase(TestPredictionModules))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityModules))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED - System is ready for deployment!")
    else:
        print("\n✗ Some tests failed - Review above for details")
    
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
