from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.create_prod_database import resolve_admin_socket


class ResolveAdminSocketTests(TestCase):
    def test_configured_admin_socket_must_exist(self):
        with self.assertRaisesRegex(SystemExit, "MYSQL_ADMIN_SOCKET does not exist"):
            resolve_admin_socket("/missing/mysql.sock", "127.0.0.1", "root", True)

    def test_local_root_automatically_uses_mysql_socket(self):
        socket_path = Path("/var/lib/mysql/mysql.sock")
        with patch.object(Path, "exists", return_value=True):
            self.assertEqual(
                resolve_admin_socket(None, "127.0.0.1", "root", True), str(socket_path)
            )

    def test_non_root_admin_uses_tcp(self):
        self.assertIsNone(resolve_admin_socket(None, "127.0.0.1", "dbadmin", True))
