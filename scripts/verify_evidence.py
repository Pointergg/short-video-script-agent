"""Verify persisted evidence offline; optionally regenerate reports from saved JSON."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from script_agent.cli import render_markdown
from script_agent.tools import fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render-reports', action='store_true')
    args = parser.parse_args()
    count = 0
    for provider in ('mock', 'live'):
        folder = ROOT / 'examples' / provider
        summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
        assert summary['passed'] == summary['total'], f'{provider}: not all acceptance rows passed'
        for row in summary['cases']:
            file = folder / row['evidence']
            result = json.loads(file.read_text(encoding='utf-8'))
            assert result['status'] == row['actual']
            assert result['provider'] == provider
            assert result['steps_used'] == len(result['trace']) <= result['max_steps']
            if result['status'] == 'completed':
                script, timing, rules = result['script'], result['checks']['duration'], result['checks']['rules']
                assert timing['draft_id'] == rules['draft_id'] == fingerprint(script)
                assert timing['within_limit'] and rules['passed']
                assert len(script['scenes']) == len(timing['scenes']) == len(rules['scenes'])
                assert round(sum(s['seconds'] for s in timing['scenes']), 1) == result['estimated_total_seconds']
                sources = {s['id']: s for s in result['sources']}
                for scene, time, rule in zip(script['scenes'], timing['scenes'], rules['scenes']):
                    assert time['source_ids'] == rule['source_ids']
                    for segment in scene['segments']:
                        if segment['kind'] == 'fact':
                            assert segment['text'] in sources[segment['source_id']]['facts']
            else:
                assert result['script'] is None
            if args.render_reports:
                (file.parent / 'report.md').write_text(render_markdown(result), encoding='utf-8')
            count += 1
    print(f'Verified {count} saved scenarios: states, step budgets, draft hashes, timelines and fact citations.')


if __name__ == '__main__':
    main()
