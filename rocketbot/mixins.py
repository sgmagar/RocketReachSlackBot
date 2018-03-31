from django.conf import settings
from django.urls import reverse


class SlackMixin:

    def dispatch(self, request, *args, **kwargs):
        self.load_slack_credentials()
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url(self):
        proto = "https" if self.request.is_secure() else "http"
        return f"{proto}://{self.request.get_host()}{reverse('oauth_callback')}"

    def load_slack_credentials(self):
        self.client_id = settings.ROCKET_APP['client_id']
        self.client_secret = settings.ROCKET_APP['client_secret']
        self.verification_token = settings.ROCKET_APP['verification_token']
        self.scopes = settings.ROCKET_APP['scopes']
