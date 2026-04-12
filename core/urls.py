from django.urls import path
from . import views
from .views import delete_conference, delete_attendee, generate_qr

urlpatterns = [
    path('', views.home, name='home'), 
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_conference),
    path('event/<int:pk>/', views.event_page),
    path('attendees/<int:pk>/', views.attendee_list, name='attendee_list'),
    path('send-email/<int:pk>/<int:template_id>/', views.send_bulk_email),
    path('export/<int:pk>/', views.export_excel),
    path('logout/', views.user_logout, name='logout'),
    path('login/', views.user_login, name='login'), 

    path('delete-conference/<int:pk>/', delete_conference),
    path('delete-attendee/<int:pk>/', delete_attendee),

    path('qr/<int:pk>/', generate_qr),
]