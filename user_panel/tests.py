from django.test import TestCase, Client
from accounts.models import User

class Custom404RoutingTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create an admin user
        self.admin_user = User.objects.create_user(
            email="admin@zitarra.com",
            password="adminpassword123",
            fullname="Master Admin",
            mobile_number="9876543211",
            is_verified=True,
            is_staff=True,
            is_superuser=True
        )

    def test_user_side_nonexistent_url_returns_404_template(self):
        response = self.client.get("/nonexistent-page-random-123/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Discordant Path", status_code=404)

    def test_admin_side_nonexistent_url_unauthenticated_returns_admin_404_card(self):
        response = self.client.get("/admin-panel/nonexistent-admin-page-random-123/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "admin_panel/404.html")
        # Should show the standalone card indicating "ADMIN ROUTE NOT FOUND"
        self.assertContains(response, "ADMIN ROUTE NOT FOUND", status_code=404)
        self.assertContains(response, "ADMIN SIGN IN", status_code=404)

    def test_admin_side_nonexistent_url_authenticated_returns_admin_404_layout(self):
        # Log in the admin user
        self.client.login(email="admin@zitarra.com", password="adminpassword123")
        response = self.client.get("/admin-panel/nonexistent-admin-page-random-123/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "admin_panel/404.html")
        # Should show admin full dashboard shell with admin_name
        self.assertContains(response, "Master Admin", status_code=404)
        self.assertContains(response, "ADMIN ENDPOINT UNRESOLVED", status_code=404)
        self.assertContains(response, "DASHBOARD", status_code=404)
        self.assertContains(response, "USERS", status_code=404)

    def test_admin_unimplemented_url_returns_404(self):
        self.client.login(email="admin@zitarra.com", password="adminpassword123")
        response = self.client.get("/admin-panel/unimplemented/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "admin_panel/404.html")
        self.assertContains(response, "Master Admin", status_code=404)
        self.assertContains(response, "ADMIN ENDPOINT UNRESOLVED", status_code=404)
