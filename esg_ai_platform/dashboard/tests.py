from django.test import TestCase
from django.urls import reverse


class IntroPageTests(TestCase):
    def test_intro_page_is_public_and_distinct_from_dashboard(self):
        response = self.client.get(reverse("dashboard:intro"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carbon Disclosure Intelligence Platform")
        self.assertContains(response, "讓永續報告")
        self.assertContains(response, "founder-portrait.png")
