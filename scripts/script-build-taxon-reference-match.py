"""Build taxon_reference_match: match every taxon outside the reference tree
(e.g. HAST-legacy tree 1) into the reference tree (TaiCOL tree 2), with
synonym resolution from the reference tree's source_data->>'synonyms'.

Re-runnable: rows are upserted, rows with is_manual (curator decisions) are
never touched. Re-run after every TaiCOL load and after bulk taxon imports.

usage (flask container):
    docker compose exec flask bash -c "cd /code && PYTHONPATH=/code \
        python scripts/script-build-taxon-reference-match.py --site hast [--dry-run]"
"""
import argparse
from collections import Counter

from sqlalchemy import select, text

from app import create_app

BATCH = 2000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', default='hast', help='site whose frontend.taxon.reference is used')
    ap.add_argument('--tree-id', type=int, help='source tree (default: every tree except the reference)')
    ap.add_argument('--dry-run', action='store_true', help='print coverage, write nothing')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        from app.database import session
        from app.models.site import Site
        from app.models.taxon import Taxon, TaxonReferenceMatch as M

        site = Site.query.filter(Site.name == args.site).one()
        conf = site.get_settings('frontend.taxon.reference') or {}
        ref_tree, kingdoms = conf.get('tree_id'), conf.get('prefer_kingdoms')
        if not ref_tree:
            raise SystemExit(f'{args.site}: no frontend.taxon.reference.tree_id')

        synonyms = Taxon.build_synonym_index(ref_tree, kingdoms)
        print(f'reference tree {ref_tree}: {len(synonyms)} unambiguous synonym names')

        q = select(Taxon).where(Taxon.tree_id != ref_tree).order_by(Taxon.id)
        if args.tree_id:
            q = q.where(Taxon.tree_id == args.tree_id)
        manual = set(session.execute(select(M.taxon_id).where(
            M.tree_id == ref_tree, M.is_manual.is_(True))).scalars())

        counts, written, offset = Counter(), 0, 0
        type_by_taxon = {}
        while taxa := session.execute(q.offset(offset).limit(BATCH)).scalars().all():
            offset += len(taxa)
            matches = Taxon.find_reference_matches(taxa, ref_tree, kingdoms, synonyms=synonyms)
            rows = []
            for t in taxa:
                ref, mt = matches.get(t.id, (None, ''))
                type_by_taxon[t.id] = mt or 'none'
                counts[mt or 'none'] += 1
                if t.id in manual:
                    continue
                rows.append({'taxon_id': t.id, 'tree_id': ref_tree,
                             'ref_taxon_id': ref.id if ref else None,
                             'match_type': mt or 'none'})
            if rows and not args.dry_run:
                M.upsert(rows)
                written += len(rows)
            # keep memory flat over ~40k taxa; no commit inside the loop, so the
            # synonym index's (detached) refs keep their loaded attributes
            session.expunge_all()
        if not args.dry_run:
            session.commit()  # one transaction: a failed run leaves the old rows

        # coverage by specimens: units whose record points at the taxon
        units = Counter()
        for tid, n in session.execute(text(
                'SELECT r.proxy_taxon_id, count(*) FROM unit u JOIN record r ON r.id = u.record_id '
                'WHERE r.proxy_taxon_id IS NOT NULL GROUP BY 1')):
            if tid in type_by_taxon:
                units[type_by_taxon[tid]] += n
        total = sum(units.values()) or 1
        print(f'{"match_type":<10} {"taxa":>7} {"units":>8}')
        for mt, n in counts.most_common():
            print(f'{mt:<10} {n:>7} {units[mt]:>8} ({units[mt] * 100 / total:.1f}%)')
        print(f'manual rows kept: {len(manual)}; '
              + ('dry run, nothing written' if args.dry_run else f'upserted: {written}'))


if __name__ == '__main__':
    main()
