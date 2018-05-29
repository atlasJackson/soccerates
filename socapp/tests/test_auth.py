from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
import socapp.tests.test_helpers as helpers

from socapp.models import *


class TestApplicationRoutes(TestCase):
    """
    Tests authorization rights for all routes in the application.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="password")
    
    #Assert that index page can be accessed by all.
    # def test_index_page(self):
    #     response = self.client.get(reverse('index'))
    #     print(response)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, "Sign In")
    #     self.assertNotContains(response, "Logout")
    
    # # Assert that the index template's navbar changes after logging in.
    # def test_index_page_after_login(self):
    #     self.client.login(username=self.user.username, password='password')
    #     response = self.client.get(reverse('index'))
    #     self.assertContains(response, "Logout")
    #     self.assertIsInstance(response.context['user'], User)

    # Ensure the login page is accessible to all
    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    # Tests POST request to login endpoint successfully logs user in.
    def test_user_can_login(self):
        data = {'username': self.user.username, 'password': 'password'}
        response = self.client.post(reverse('login'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logout")
        self.assertIsInstance(response.context['user'], User)
    
    # Tests POST request to login endpoint, with invalid credentials, does not login a user.
    def test_user_login_with_invalid_credentials(self):
        data = {'username': 'wrong', 'password': 'wrong'}
        response = self.client.post(reverse('login'), data, follow=True)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "Sign In")
        ###### MORE HERE ONCE ERROR MESSAGES ARE SHOWN ON PAGE ###

    
    # Tests that user can register and that the user is automatically logged in following registration
    def test_registering(self):
        data = {
            'username': 'test1',
            'password': 'randstr',
            'email': 'test@x.com',
            'password_confirm': 'randstr'
        }
        response = self.client.post(reverse('register'), data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Now, test that user is logged in
        # response2 = self.client.get(reverse("index"))
        # self.assertContains(response2, "Logout")
        # self.assertIsInstance(response.context['user'], User)
