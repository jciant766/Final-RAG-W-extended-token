#!/usr/bin/env python3
from vector_store import VectorStore

def print_results(title, results):
    print(f"\n=== {title} ===")
    if not results:
        print("No results")
        return
    for r in results[:5]:
        citation = r.get('citation') or r.get('metadata', {}).get('citation')
        score = r.get('score', 0)
        print(f"- {citation}  [score={score:.2f}]")
        snippet = (r.get('content') or '')[:160].replace('\n', ' ')
        print(f"  {snippet}...")


def main():
    vs = VectorStore()

    # Direct article lookups
    res1 = vs.get_article('1')
    print_results('Article 1', res1)

    # Subsidiary regulation lookup (if present)
    res2 = vs.search('Regulation 5 of S.L. 386.02', n_results=5)
    print_results('Regulation 5 (S.L. 386.02)', res2)

    # General semantic queries
    res3 = vs.search('company registration requirements', n_results=5)
    print_results('company registration requirements', res3)

    res4 = vs.search('penalties for late filing of accounts', n_results=5)
    print_results('penalties for late filing of accounts', res4)

if __name__ == '__main__':
    main()

