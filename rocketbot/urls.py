from django.urls import path

from rocketbot.views import IndexView, OauthCallbackView, CommandView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('oauth-callback/', OauthCallbackView.as_view(), name='oauth_callback'),
    path('command/', CommandView.as_view(), name='command'),

]
