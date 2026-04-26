from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_conference, name='create_conference'),

    path('event/<int:pk>/', views.event_page, name='event_page'),
    path('attendees/<int:pk>/', views.attendee_list, name='attendee_list'),

    path('delete-conference/<int:pk>/', views.delete_conference),
    path('delete-attendee/<int:pk>/', views.delete_attendee),

    path('export/<int:pk>/', views.export_attendees, name='export_attendees'),

    path('qr/<int:pk>/', views.generate_qr),

    path('conference/<int:conf_id>/broadcast/', views.send_conference_broadcast, name='broadcast_email'),
]
