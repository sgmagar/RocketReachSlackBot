import logging
import os
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from slackclient import SlackClient

from rocketbot.mixins import SlackMixin


class IndexView(SlackMixin, TemplateView):
    template_name = 'rocketbot/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'title': 'Home',
            'authorization_url': self.get_authorization_url()
        })
        return ctx

    def get_authorization_url(self):
        state = os.urandom(8).hex()
        self.request.session["slack_oauth_state"] = state
        query = urlencode({
            "client_id": self.client_id,
            "scope": self.scopes,
            "redirect_uri": self.get_redirect_url(),
            "state": state
        })

        return "https://slack.com/oauth/authorize?" + query


class OauthCallbackView(SlackMixin, TemplateView):
    template_name = 'rocketbot/auth_result.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx['error'] = kwargs.get('error') or None
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        response = self.exchange_code_for_token()
        return self.render_to_response(response)

    def exchange_code_for_token(self):
        code = self.request.GET.get("code")
        state = self.request.GET.get("state")
        error = self.request.GET.get("error")

        if error or not state or state != self.request.session.get('slack_oauth_state'):
            return {
                'error': "Error while installing rocket app in your workspace."
            }
        sc = SlackClient("")

        # Request the auth tokens from Slack
        response = sc.api_call(
            "oauth.access",
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.get_redirect_url(),
            code=code
        )

        if not response.get("ok"):
            return {
                'error': "Error while installing rocket app in your workspace."
            }
        return response


class CommandView(SlackMixin, View):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        token = request.POST.get("token")
        if token != self.verification_token:
            logging.warning("Incorrect token received.")
            return HttpResponse(status=403, content=b"Token does not match.")
        self.data = request.POST
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        command = self.data['command'].strip('/')
        try:
            method = getattr(self, f'{command}_command')
        except AttributeError:
            logging.info(f'Unhandled command {command}')
            return HttpResponse(status=200)
        return method()

    def linkedin_command(self):
        text = self.data['text'].strip()
        params = {'li_url': text}
        response = rocketreach_api_call('/lookupProfile', params)
        if not isinstance(response, list):
            return JsonResponse({'text': "No Profile on `RocketReach`" })
        profile = response[0]
        attachments = get_attachments(profile)
        message = {
            'text': f"This is the profile of `{profile['name']}`",
            'attachments': attachments
        }
        return JsonResponse(message)


def rocketreach_api_call(url, params={}):
    base_url = 'https://api.rocketreach.co/v1/api'
    query_json = {
        'api_key': settings.ROCKETREACH_API_KEY
    }
    query_json.update(params)
    query = urlencode(query_json)
    url = f'{base_url}{url}?{query}'
    response = requests.get(url)
    logging.info(response)
    return response.json()


def get_attachments(profile):
    attachment = {
        "color": "#aaefab",
        "title": f"{profile['name']}",
        "title_link": f"{profile['links'].get('linkedin')}",
        "thumb_url": f"{profile['profile_pic']}",
        "fields": [
            {
                "title": "Current Work Email",
                "value": f"{profile['current_work_email']}",
                "short": False
            },
            {
                "title": "Facebook Profile",
                "value": f"{profile['links'].get('facebook') or 'No Facebook Account'}",
                "short": False
            },
            {
                "title": "Twitter Profile",
                "value": f"{profile['links'].get('twitter') or 'No Twitter Account'}",
                "short": False
            }
        ],
    }
    return [attachment]
