"""API router package for Scan2Target."""

# Keep the public /api/v1/scan/batch URL while placing the persistent Phase 2
# implementation before the legacy route in Starlette's first-match route list.
from api import scan as scan
from api import batch_scan as batch_scan

scan.router.routes[0:0] = batch_scan.router.routes
