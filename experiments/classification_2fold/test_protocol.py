#!/usr/bin/env python3

import unittest

import numpy as np

from run import metric_values, select_threshold


class MetricsTest(unittest.TestCase):
    def test_threshold_is_deterministic(self):
        labels = np.asarray([0, 0, 1, 1])
        probabilities = np.asarray([0.1, 0.4, 0.6, 0.9])
        self.assertEqual(select_threshold(labels, probabilities), 0.6)

    def test_metrics(self):
        labels = np.asarray([0, 0, 1, 1])
        probabilities = np.asarray([0.1, 0.2, 0.8, 0.9])
        result = metric_values(labels, probabilities, 0.5)
        self.assertEqual(result["auc"], 1.0)
        self.assertEqual(result["balanced_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
