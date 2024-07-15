import json
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.models import SocialApp, SocialAccount
from allauth.socialaccount.helpers import complete_social_login
from django.views.decorators.csrf import csrf_exempt

from .EmailBackend import EmailBackend
from .models import Attendance, Session, Subject

# Create your views here.


def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("staff_home"))
        else:
            return redirect(reverse("student_home"))
    return render(request, 'main_app/login.html')


@csrf_exempt
def doLogin(request, **kwargs):
    if request.method == 'GET':
        return HttpResponse("<h4>Denied</h4>")

    if 'g-recaptcha-response' in request.POST:
        # Google reCAPTCHA verification
        captcha_token = request.POST.get('g-recaptcha-response')
        captcha_url = "https://www.google.com/recaptcha/api/siteverify"
        captcha_key = settings.RECAPTCHA_SECRET_KEY
        data = {
            'secret': captcha_key,
            'response': captcha_token
        }
        try:
            captcha_server = requests.post(url=captcha_url, data=data)
            response = json.loads(captcha_server.text)
            if not response.get('success'):
                messages.error(request, 'Invalid Captcha. Try Again')
                return redirect('/')
        except:
            messages.error(request, 'Captcha could not be verified. Try Again')
            return redirect('/')

    # Check if the request is for Google Sign-In
    if 'google_login' in request.POST:
        try:
            # Get the social app
            social_app = SocialApp.objects.get(provider='google')

            # Adapter setup
            adapter = GoogleOAuth2Adapter()
            client = OAuth2Client(social_app.client_id, social_app.secret)
            token = request.POST.get('google_token')

            # Complete the social login
            login_response = complete_social_login(request, token, adapter, client)
            if isinstance(login_response, HttpResponse):
                return login_response

            if login_response.user:
                user = login_response.user
                backend = 'allauth.account.auth_backends.AuthenticationBackend'
                login(request, user, backend=backend)
                if user.user_type == '1':
                    return redirect(reverse("admin_home"))
                elif user.user_type == '2':
                    return redirect(reverse("staff_home"))
                else:
                    return redirect(reverse("student_home"))
        except SocialApp.DoesNotExist:
            messages.error(request, 'Google login not configured properly.')
            return redirect('/')

    # Traditional email/password authentication
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = EmailBackend.authenticate(request, username=email, password=password)
    if user is not None:
        backend = 'main_app.EmailBackend.EmailBackend'
        login(request, user, backend=backend)
        if user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif user.user_type == '2':
            return redirect(reverse("staff_home"))
        else:
            return redirect(reverse("student_home"))
    else:
        messages.error(request, "Invalid details")
        return redirect("/")

def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


@csrf_exempt
def get_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = Attendance.objects.filter(subject=subject, session=session)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date),
                    "session": attd.session.id
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None


def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
    """
    return HttpResponse(data, content_type='application/javascript')
