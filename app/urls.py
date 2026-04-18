from django.urls import path
from app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.ssh_login, name='ssh_login'),
    path('execute/', views.execute_action, name='execute_action'),
    path('logout/', views.ssh_logout, name='ssh_logout'),
    path('groups/', views.list_groups, name='list_groups'),
]
