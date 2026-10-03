"""Hypothesis profiles (TRD TR-TST-03): 500 examples in CI, 5,000 nightly.

Select the nightly profile with HYPOTHESIS_PROFILE=nightly.
"""

import os

from hypothesis import HealthCheck, settings

from tests.coreenv import TEMPLATE_DIR

_COMMON = {"deadline": None, "database": None, "suppress_health_check": [HealthCheck.too_slow]}
settings.register_profile("ci", max_examples=500, **_COMMON)
settings.register_profile("nightly", max_examples=5000, **_COMMON)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

# The API loads templates at startup (TR-OPS-02); point it at the repo's templates/ in tests.
os.environ.setdefault("TEMPLATE_DIR", str(TEMPLATE_DIR))
