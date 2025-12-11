"""Bridges are components which handle supplementary tasks in the IPS Framework. Applications should not need to import these classes directly, these are automatically initialized by the framework.

There are two bridges available:
- `LocalLoggingBridge`, which provides simple system logging (always created)
- `PortalBridge`, which allows interfacing with a remote IPS Portal (created if user provides a PORTAL_URL and does not disable the portal)
"""
