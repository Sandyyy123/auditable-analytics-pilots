from datetime import datetime,timezone
import numpy as np
import pytest
from pilots import audit_feed,signal_quality,subject_split,report_metrics,examples

def test_quarantine_prevents_silent_publish():
    x=examples()['nhl']
    assert x['accepted']==1 and x['quarantined']==3 and not x['publish_allowed']
    assert not audit_feed([],datetime.now(timezone.utc))['publish_allowed']

def test_valid_feed_can_publish_and_nan_cannot():
    rows=[{'event_id':'1','observed_at':'2026-10-19T00:00:00Z','probability':0.5}]
    now=datetime(2026,10,19,1,tzinfo=timezone.utc)
    assert audit_feed(rows,now)['publish_allowed']
    rows[0]['probability']=float('nan')
    assert not audit_feed(rows,now)['publish_allowed']

def test_missing_timezone_and_future_data_quarantined():
    for timestamp in ['2026-10-19T00:00:00','2026-10-20T00:00:00Z']:
        result=audit_feed([{'event_id':'1','observed_at':timestamp,'probability':0.5}],datetime(2026,10,19,tzinfo=timezone.utc))
        assert not result['publish_allowed']

def test_quality_rejects_flatline_and_missing():
    assert not signal_quality(np.ones(1000),50)['usable_for_demo']
    x=np.ones(1000);x[10]=np.nan
    assert signal_quality(x,50)['reason']=='nonfinite_samples'

def test_synthetic_quality_contrast_is_not_clinical_validation():
    x=examples()['signals']
    assert x['clean_synthetic']['usable_for_demo']
    assert not x['noisy_synthetic']['usable_for_demo']
    assert x['subject_overlap']==0

def test_subject_split_rejects_unknown_identity_and_empty_holdout():
    with pytest.raises(ValueError):subject_split([{'window':1}],['a'])
    with pytest.raises(ValueError):subject_split([{'subject_id':'a'}],['b'])

def test_dashboard_unknown_status_never_counts_as_paid():
    x=examples()['dashboard']
    assert x['paid_total']==300 and x['paid_rows']==2 and x['unknown_status_rows']==1

def test_dashboard_rejects_duplicate_and_mixed_currency():
    a={'id':'1','amount':100,'currency':'USD','status':'paid'}
    with pytest.raises(ValueError):report_metrics([a,a])
    with pytest.raises(ValueError):report_metrics([a,dict(a,id='2',currency='EUR')])
