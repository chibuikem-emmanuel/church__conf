from django.urls import path
from . import views
from .views import delete_conference, delete_attendee, export_attendees, generate_qr

urlpatterns = [
    path('', views.home, name='home'), 
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_conference),
    path('event/<int:pk>/', views.event_page),
    path('attendees/<int:pk>/', views.attendee_list, name='attendee_list'),
    path('attendees/<int:conf_id>/', views.attendee_list, name='attendee_list'),
    path('send-email/<int:pk>/<int:template_id>/', views.send_bulk_email),
    path('export/<int:pk>/', export_attendees, name='export_attendees'),
    path('logout/', views.user_logout, name='logout'),
    path('login/', views.user_login, name='login'), 

    path('delete-conference/<int:pk>/', delete_conference),
    path('delete-attendee/<int:pk>/', delete_attendee),

    path('qr/<int:pk>/', generate_qr),
    path('conference/<int:conf_id>/broadcast/', views.send_conference_broadcast, name='send_broadcast'),
    path('conference/<int:conf_id>/broadcast/', views.send_conference_broadcast, name='broadcast_email'),
]
