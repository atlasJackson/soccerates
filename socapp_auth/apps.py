from django.apps import AppConfig

class SocappAuthConfig(AppConfig):
    name = 'socapp_auth'

    def ready(self):
        from socapp_auth import signals