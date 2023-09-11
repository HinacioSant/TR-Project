from django.urls import path

from . import views
# App Urls:
urlpatterns = [
    path("tr", views.Index.as_view()),
    path("score/<region>/<summoner>", views.Get_Score.as_view()),

]
