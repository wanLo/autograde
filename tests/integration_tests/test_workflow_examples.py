import os
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from zipfile import ZipFile

import pandas as pd

from autograde.cli.__main__ import cli
from autograde.cli.util import find_archives
from autograde.helpers import assert_isclose
from autograde.util import project_root, cd

PROJECT_ROOT = project_root()
EXAMPLES = PROJECT_ROOT.joinpath('tests', 'examples')


class TestWorkflow(TestCase):
    def test_test_report_patch_summary(self):
        with TemporaryDirectory() as temp, cd(temp), warnings.catch_warnings():
            warnings.simplefilter('ignore')

            os.mkdir('results_1')
            os.mkdir('results_2')

            # run tests
            cli(['test', str(EXAMPLES.joinpath('test_1.py')), str(EXAMPLES), '-t', 'results_1'])
            cli(['test', str(EXAMPLES.joinpath('test_2.py')), str(EXAMPLES), '-t', 'results_2'])

            for path in find_archives():
                with ZipFile(path, mode='r') as zipf:
                    self.assertListEqual(sorted(zipf.namelist()), [
                        'code.py',
                        'notebook.ipynb',
                        'results.json'
                    ])

            # create reports for test 2 results
            cli(['report', 'results_2'])

            for path in find_archives('results_2'):
                with ZipFile(path, mode='r') as zipf:
                    self.assertTrue('report.html' in zipf.namelist())

            # create test summaries
            cli(['summary', 'results_1'])
            cli(['summary', 'results_2'])

            summary_1 = pd.read_csv(Path('results_1', 'summary.csv'))
            summary_2 = pd.read_csv(Path('results_2', 'summary.csv'))

            assert_isclose(10., summary_1['score'].sum())
            assert_isclose(8., summary_2['score'].sum())
            assert_isclose(12., summary_1['max_score'].sum())
            assert_isclose(12., summary_2['max_score'].sum())
            self.assertEqual(2, sum(summary_1['duplicate']))
            self.assertEqual(2, sum(summary_2['duplicate']))

            # patch test 1 results and re-compute report + summary
            cli(['patch', 'results_1', 'results_2'])
            cli(['report', 'results_1'])
            cli(['summary', 'results_1'])

            for path in find_archives('results_1'):
                with ZipFile(path, mode='r') as zipf:
                    self.assertTrue('report.html' in zipf.namelist())

            summary_1 = pd.read_csv(Path('results_1', 'summary.csv'))

            assert_isclose(8., summary_1['score'].sum())
            assert_isclose(12., summary_1['max_score'].sum())
            self.assertEqual(2, sum(summary_1['duplicate']))

            # fails since multiple scores per task and student are not allowed!
            with self.assertRaises(AssertionError):
                cli(['summary', '.'])
