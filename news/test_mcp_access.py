from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from .mcp_access import authenticate_mcp_key, issue_mcp_key
from .models import MCPAccessKey


class MCPKeyIssuanceTests(TestCase):
    def test_issue_retries_database_uniqueness_collision(self):
        real_create = MCPAccessKey.objects.create
        attempts = 0

        def flaky_create(**kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise IntegrityError("simulated uniqueness collision")
            return real_create(**kwargs)

        with patch.object(MCPAccessKey.objects, "create", side_effect=flaky_create):
            access_key, raw_key = issue_mcp_key(label="Race test")

        self.assertEqual(attempts, 2)
        authenticated = authenticate_mcp_key(raw_key)
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.pk, access_key.pk)
