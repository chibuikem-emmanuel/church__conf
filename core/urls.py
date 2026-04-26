from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Auth
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Conference
    path('create/', views.create_conference, name='create_conference'),
    path('event/<int:pk>/', views.event_page, name='event_page'),
    path('delete-conference/<int:pk>/', views.delete_conference, name='delete_conference'),

    # Attendees
    path('attendees/<int:pk>/', views.attendee_list, name='attendee_list'),
    path('delete-attendee/<int:pk>/', views.delete_attendee, name='delete_attendee'),

    # Features
    path('export/<int:pk>/', views.export_attendees, name='export_attendees'),
    path('qr/<int:pk>/', views.generate_qr, name='generate_qr'),

    # Broadcast (ONLY ONE ROUTE)
    path('conference/<int:conf_id>/broadcast/', views.send_conference_broadcast, name='send_broadcast'),
]
