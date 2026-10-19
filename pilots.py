"""Synthetic, deterministic examples. No client data or clinical claims."""
from datetime import datetime, timezone
import math
import numpy as np


def audit_feed(rows, as_of, max_age_hours=24):
    """Quarantine ambiguous rows rather than silently selecting a duplicate."""
    if as_of.tzinfo is None:
        raise ValueError('as_of must have a timezone')
    if not rows:
        return {'accepted':0,'quarantined':0,'publish_allowed':False,'records':[], 'issue':'empty_feed'}
    counts = {}
    for row in rows:
        key = row.get('event_id'); counts[key] = counts.get(key, 0) + 1
    accepted, rejected = [], []
    for row in rows:
        errors = []
        if not row.get('event_id'): errors.append('missing_event_id')
        if counts.get(row.get('event_id'), 0) > 1: errors.append('duplicate_event_id')
        try:
            when = datetime.fromisoformat(row['observed_at'].replace('Z','+00:00'))
            if when.tzinfo is None: raise ValueError('timezone missing')
            age = (as_of-when).total_seconds()/3600
            if age < 0: errors.append('future_timestamp')
            elif age > max_age_hours: errors.append('stale_source')
        except (ValueError, KeyError, TypeError): errors.append('invalid_timestamp')
        try:
            probability = float(row['probability'])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                errors.append('invalid_probability')
        except (ValueError, KeyError, TypeError): errors.append('invalid_probability')
        (rejected if errors else accepted).append({'record':row, 'issues':errors})
    return {'accepted':len(accepted), 'quarantined':len(rejected),
            'publish_allowed':not rejected, 'records':accepted+rejected}


def signal_quality(samples, sample_rate):
    """Technical window checks, not a clinical SQI or biomarker estimator."""
    x = np.asarray(samples, dtype=float)
    if not math.isfinite(sample_rate) or sample_rate <= 0: raise ValueError('Invalid sample rate')
    if x.ndim != 1 or len(x) < sample_rate*5: raise ValueError('Need a one-dimensional window of at least five seconds')
    missing = float(np.mean(~np.isfinite(x)))
    if missing: return {'usable_for_demo':False,'reason':'nonfinite_samples','missing_fraction':missing}
    span = float(np.ptp(x))
    if span < 1e-8: return {'usable_for_demo':False,'reason':'flatline','range':span}
    centered = x - np.mean(x)
    frequencies = np.fft.rfftfreq(len(x),1/sample_rate)
    power = abs(np.fft.rfft(centered*np.hanning(len(x))))**2
    total = float(power[1:].sum())
    # Illustrative band only: not a universal filter prescription for PPG/BCG.
    in_band = (frequencies>=0.5)&(frequencies<=4)
    ratio = float(power[in_band].sum()/total) if total else 0
    jump_fraction = float(np.mean(abs(np.diff(x)) > 0.25*span))
    return {'usable_for_demo':ratio >= 0.8 and jump_fraction <= 0.05,
            'illustrative_band_power_fraction':round(ratio,4),
            'abrupt_step_fraction':round(jump_fraction,4),
            'reason':'heuristic_only_requires_labelled_validation'}


def subject_split(records, test_subjects):
    """Split at subject level before fitting transforms or window augmentation."""
    if any(not r.get('subject_id') for r in records): raise ValueError('Missing subject ID')
    test_subjects = set(test_subjects)
    train = [r for r in records if r['subject_id'] not in test_subjects]
    test = [r for r in records if r['subject_id'] in test_subjects]
    if not train or not test: raise ValueError('Both partitions must contain subjects')
    return train,test


def report_metrics(rows):
    ids = [r['id'] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate transaction ID')
    if len({r['currency'] for r in rows}) != 1: raise ValueError('Mixed or missing currency')
    if any(not math.isfinite(float(r['amount'])) for r in rows): raise ValueError('Nonfinite amount')
    missing = sum(r.get('status') not in {'paid','pending','cancelled'} for r in rows)
    paid = [r for r in rows if r.get('status')=='paid']
    total = round(sum(float(r['amount']) for r in paid),2)
    return {'rows':len(rows),'paid_rows':len(paid),'paid_total':total,
            'currency':rows[0]['currency'],'unknown_status_rows':missing,
            'summary':f"Paid total: {total:.2f} {rows[0]['currency']} from {len(paid)} records. {missing} records need status review.",
            'summary_method':'deterministic; no LLM or unsupported AI claim'}


def examples():
    now = datetime(2026,10,19,0,0,tzinfo=timezone.utc)
    rows = [{'event_id':'NHL-001','observed_at':'2026-10-18T23:00:00Z','probability':0.62},
            {'event_id':'NHL-002','observed_at':'2026-10-18T23:00:00Z','probability':0.48},
            {'event_id':'NHL-002','observed_at':'2026-10-18T23:00:00Z','probability':0.51},
            {'event_id':'NHL-003','observed_at':'2026-10-16T23:00:00Z','probability':1.2}]
    fs=50; t=np.arange(1000)/fs; clean=np.sin(2*np.pi*1.2*t)
    noisy=clean+2*np.sin(2*np.pi*10*t)
    records=[{'subject_id':s,'window':i} for s in ['P01','P02','P03'] for i in range(3)]
    train,test=subject_split(records,['P03'])
    return {'nhl':audit_feed(rows,now),
            'signals':{'clean_synthetic':signal_quality(clean,fs),'noisy_synthetic':signal_quality(noisy,fs),
                       'flatline':signal_quality(np.ones(1000),fs),'train_windows':len(train),'test_windows':len(test),
                       'subject_overlap':len({r['subject_id'] for r in train}&{r['subject_id'] for r in test})},
            'dashboard':report_metrics([{'id':str(i),'currency':'USD','amount':amount,'status':status}
              for i,(amount,status) in enumerate([(120,'paid'),(180,'paid'),(90,'pending'),(150,None)])])}
