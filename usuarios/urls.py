from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    # Usamos la vista de logout de Django, pero le decimos a dónde ir después
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

]