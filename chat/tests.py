import uuid

from django.test import Client, TestCase

from chat.models import ChatMessage, ChatSession


class DeleteSessionApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.session = ChatSession.objects.create(title="Test oturumu")

    def test_delete_returns_204(self):
        url = f"/api/session/{self.session.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(ChatSession.objects.filter(pk=self.session.pk).exists())

    def test_delete_unknown_returns_404(self):
        url = f"/api/session/{uuid.uuid4()}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_delete_method_not_allowed_for_get(self):
        url = f"/api/session/{self.session.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class HistoryApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.session = ChatSession.objects.create(title="Gecmis test")
        ChatMessage.objects.create(
            session=self.session,
            user_message="Soru",
            ai_response="Cevap",
        )

    def test_history_returns_messages(self):
        url = f"/api/history/{self.session.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["messages"]), 1)
        self.assertEqual(data["messages"][0]["user_message"], "Soru")
        self.assertEqual(data["messages"][0]["ai_response"], "Cevap")

    def test_history_unknown_session_404(self):
        url = f"/api/history/{uuid.uuid4()}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ChatPageTests(TestCase):
    def test_home_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acıbadem", html=False)
