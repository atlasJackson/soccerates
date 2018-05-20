from django.apps import AppConfig


class SocappConfig(AppConfig):
    name = 'socapp'

    def ready(self):
        from socapp import signals