# Chunk 4 evidence: review → consent → national code (5 Oct 2026)

SYNTHETIC DATA. Live stack, driven through the API and photographed with headless Chrome
(1440 wide) as each person:

1. meera (MAKER, CPSE-A) starts a cross-CPSE run on the three seed-7 files: 689 groups, each with
   an OPEN review task.
2. A 3-CPSE group (`GLOBE VALVE, 20 INCH, CLASS 600 …`): meera proposes APPROVE → `MADE`.
3. arjun (CHECKER, CPSE-B) confirms → `AWAITING_CONSENT`, waiting for CPSE-C.
4. kavya (CHECKER, CPSE-C) sees it in her consent queue and consents → `DONE`,
   **NMC-00000000018** issued, three legacy codes in its crosswalk, a change notice per CPSE.

| Step | Screenshot |
|---|---|
| Review queue (maker) | [review-queue.png](screens/review-queue.png) |
| Cluster review, maker view | [cluster-maker.png](screens/cluster-maker.png) |
| Cluster review, checker view | [cluster-checker.png](screens/cluster-checker.png) |
| Consent queue (CPSE-C steward) | [consents.png](screens/consents.png) |
| Cluster review, steward view (own records highlighted) | [cluster-steward.png](screens/cluster-steward.png) |
| Registry | [registry.png](screens/registry.png) |
| National code detail with crosswalk and history | [cnmc-detail.png](screens/cnmc-detail.png) |
| Pair evidence | [pair.png](screens/pair.png) |
| Change notices (CPSE-A) | [notices.png](screens/notices.png) |

`sh backend/scripts/ci_local.sh all`: backend 818 tests (governance: `tests/api/test_governance.py`),
frontend 135 tests, lint clean, build OK.
