"""Synthetic point-in-time join audit; no client data or production connectors."""
from datetime import datetime, timezone
import json


def instant(value):
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timezone required')
    return d.astimezone(timezone.utc)


def as_of(rows, entity, observed_cutoff, knowledge_cutoff):
    """Latest observation available at cutoff. Equal-time conflicts abstain."""
    observed, known = instant(observed_cutoff), instant(knowledge_cutoff)
    eligible = [r for r in rows if r['entity'] == entity
                and instant(r['observed_at']) <= observed
                and instant(r['available_at']) <= known]
    if not eligible:
        return {'status': 'no_match', 'value': None, 'evidence': []}
    newest = max((instant(r['observed_at']), instant(r['available_at'])) for r in eligible)
    chosen = [r for r in eligible if (instant(r['observed_at']), instant(r['available_at'])) == newest]
    if len({json.dumps(r['value'], sort_keys=True) for r in chosen}) != 1:
        return {'status': 'conflict', 'value': None, 'evidence': sorted(r['id'] for r in chosen)}
    return {'status': 'matched', 'value': chosen[0]['value'], 'evidence': sorted(r['id'] for r in chosen)}


def entity_at(links, url, at):
    """Exact, time-valid identity map; overlapping contradictory links abstain."""
    when = instant(at)
    active = [r for r in links if r['url'] == url and instant(r['valid_from']) <= when
              and (not r.get('valid_to') or when < instant(r['valid_to']))]
    entities = {r['entity'] for r in active}
    return next(iter(entities)) if len(entities) == 1 else None


def demonstration():
    rows = [
        {'id': 'crawl-original', 'entity': 'page-A', 'observed_at': '2026-01-01T00:00:00Z', 'available_at': '2026-01-02T00:00:00Z', 'value': 7},
        {'id': 'crawl-correction', 'entity': 'page-A', 'observed_at': '2026-01-01T00:00:00Z', 'available_at': '2026-01-10T00:00:00Z', 'value': 9},
        {'id': 'future-crawl', 'entity': 'page-A', 'observed_at': '2026-01-06T00:00:00Z', 'available_at': '2026-01-06T00:00:00Z', 'value': 12},
    ]
    return {
        'label': 'Synthetic illustration; not SYSTEM35 data or past client results',
        'prediction_cutoff': '2026-01-05T00:00:00Z',
        'naive_latest_record_value': rows[-1]['value'],
        'point_in_time_value': as_of(rows, 'page-A', '2026-01-05T00:00:00Z', '2026-01-05T00:00:00Z'),
        'retrospective_corrected_value': as_of(rows, 'page-A', '2026-01-05T00:00:00Z', '2026-01-11T00:00:00Z'),
        'unknown_entity': as_of(rows, 'page-B', '2026-01-05T00:00:00Z', '2026-01-05T00:00:00Z'),
        'records': rows,
        'limits': ['No causal identification or performance estimates.', 'No source connectors or BigQuery execution.',
                   'No delete/retraction event semantics; explicit records and timezone-aware timestamps required.',
                   'Matching is exact; ambiguous identities require review.'],
    }


if __name__ == '__main__':
    print(json.dumps(demonstration(), indent=2))
