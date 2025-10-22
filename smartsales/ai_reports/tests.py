from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

class AiReportsSmokeTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_run_basic(self):
        url = reverse('ai_reports_run')
        r = self.client.post(url, {'prompt': 'ventas por marca en 2025', 'formato': 'json'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('rows', r.data)
