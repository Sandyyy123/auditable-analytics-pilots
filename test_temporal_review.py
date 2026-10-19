import pytest
from temporal_review import as_of, entity_at, demonstration


def test_late_correction_and_future_observation_cannot_leak_into_prediction():
    out = demonstration()
    assert out['point_in_time_value'] == {'status':'matched','value':7,'evidence':['crawl-original']}
    assert out['retrospective_corrected_value']['value'] == 9
    assert out['unknown_entity']['status'] == 'no_match'


def test_equal_time_conflicts_abstain():
    r = demonstration()['records'][0]
    result = as_of([r,dict(r,id='conflicting-copy',value=11)],'page-A','2026-01-05T00:00:00Z','2026-01-05T00:00:00Z')
    assert result['status'] == 'conflict' and result['value'] is None


def test_duplicate_identical_records_do_not_multiply_output():
    r = demonstration()['records'][0]
    assert as_of([r,dict(r,id='copy')],'page-A','2026-01-05T00:00:00Z','2026-01-05T00:00:00Z')['value'] == 7


def test_knowledge_boundary_is_inclusive_and_timezones_normalized():
    r = demonstration()['records'][0]
    assert as_of([r],'page-A','2026-01-02T01:00:00+01:00','2026-01-02T01:00:00+01:00')['value'] == 7
    assert as_of([r],'page-A','2026-01-02T00:00:00Z','2026-01-01T23:59:59Z')['status'] == 'no_match'
    with pytest.raises(ValueError):
        as_of([r],'page-A','2026-01-02','2026-01-02T00:00:00Z')


def test_redirect_boundary_and_ambiguous_identity():
    links = [{'url':'/old','entity':'A','valid_from':'2025-01-01T00:00:00Z','valid_to':'2026-01-01T00:00:00Z'},
             {'url':'/old','entity':'B','valid_from':'2026-01-01T00:00:00Z'}]
    assert entity_at(links,'/old','2025-12-31T23:59:59Z') == 'A'
    assert entity_at(links,'/old','2026-01-01T00:00:00Z') == 'B'
    assert entity_at(links+[dict(links[1],entity='C')],'/old','2026-01-01T00:00:00Z') is None
    assert entity_at(links,'/unknown','2026-01-01T00:00:00Z') is None
