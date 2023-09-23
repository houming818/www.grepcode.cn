"""squant URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

import squant.views as views


urlpatterns = [
    path("api/v1/sync_instrument/", views.sync_instrument),
    path("api/v1/get_instrument/", views.get_instrument),
    path("api/v1/get_history/", views.get_history),
    path("api/v1/au/get_instruments/", views.au_get_instruments),
    path("api/v1/au/save_instruments/", views.au_save_instruments),
    path("api/v1/au/save_histories/", views.au_save_histories),
    # path("api/v1/bs/save_instruments/", views.bs_save_instruments),
    path("api/v1/save_history/", views.save_history),
]
