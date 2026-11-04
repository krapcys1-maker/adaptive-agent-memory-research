"""Safety/provenance checks for the additive development-only runner."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from reviews import lifesim_development_diagnosis as D


@pytest.mark.parametrize('seeds', ([5000], [5099], [1000], [-1], [5, 5]))
def test_invalid_seed_selection_never_builds_a_world_or_creates_output(tmp_path, seeds):
    out = tmp_path / 'new'
    with patch.object(D.G, 'make_bundle') as build:
        with pytest.raises(ValueError):
            D.main(['--output', str(out), '--seeds', *map(str, seeds)])
    build.assert_not_called()
    assert not out.exists()


def test_existing_output_is_preserved_before_any_execution(tmp_path):
    marker = tmp_path / 'canonical.json'
    marker.write_bytes(b'original result\n')
    with patch.object(D.G, 'make_bundle') as build:
        with pytest.raises(FileExistsError):
            D.main(['--output', str(tmp_path)])
    build.assert_not_called()
    assert marker.read_bytes() == b'original result\n'


def test_concentration_uses_each_world_family_and_slot_as_its_denominator():
    def query(family, ask, value, prior=False):
        return NS(family=family, ask=ask, gold=NS(value=value), tags=NS(prior_answerable=prior))
    bundles = [NS(seed=5, queries=[query('SE4','job','A'), query('SE4','job','A'),
                                  query('IN4','time','B'), query('ME1','job','UNKNOWN')]),
               NS(seed=6, queries=[query('SE4','job','B'), query('SE4','job','C'),
                                  query('SE4','job','C', prior=True)])]
    rows = D.gold_concentration(bundles)
    assert [(r['seed'],r['family'],r['n'],r['modal_gold_share']) for r in rows] == [
        (5,'IN4',1,1.0), (5,'SE4',2,1.0), (6,'SE4',2,.5)]
