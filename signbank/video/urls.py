from django.conf.urls import url

urlpatterns = [
    url(r'^(?P<videoid>\d+)$',
     'signbank.video.views.video'),
    url(r'^upload/', 'signbank.video.views.addvideo'),
    url(r'^poster/(?P<videoid>\d+)$',
     'signbank.video.views.poster'),
]
