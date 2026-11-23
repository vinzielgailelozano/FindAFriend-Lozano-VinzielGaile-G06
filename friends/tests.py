from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import FriendRequest

PASSWORD = "Pickle!Ball2026"


def make_user(username, role=User.Role.STUDENT, **extra):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        role=role,
        first_name=username.title(),
        last_name="Tester",
        course=extra.pop("course", "BSIT"),
        **extra,
    )


class FriendTestCase(TestCase):
    def setUp(self):
        self.ana = make_user("ana", interests="badminton, coding")
        self.ben = make_user("ben", course="BSCS")
        self.cara = make_user("cara")
        self.admin = make_user("boss", role=User.Role.ADMIN)

    def login(self, user):
        self.client.login(username=user.username, password=PASSWORD)

    def send(self, to, message=""):
        return self.client.post(reverse("friends:send_request", args=[to.pk]), {"message": message}, follow=True)


class SearchTests(FriendTestCase):
    def test_search_by_interest_and_course(self):
        self.login(self.ben)
        response = self.client.get(reverse("friends:student_list"), {"q": "badminton"})
        self.assertContains(response, "Ana Tester")
        self.assertNotContains(response, "Cara Tester")
        response = self.client.get(reverse("friends:student_list"), {"course": "BSIT"})
        self.assertContains(response, "Ana Tester")
        self.assertContains(response, "Cara Tester")

    def test_search_hides_self_and_admins(self):
        self.login(self.ana)
        response = self.client.get(reverse("friends:student_list"))
        self.assertNotContains(response, "Ana Tester")
        self.assertNotContains(response, "Boss Tester")

    def test_contact_hidden_until_friends(self):
        self.ben.contact_number = "09171234567"
        self.ben.save()
        self.login(self.ana)
        url = reverse("friends:student_detail", args=[self.ben.pk])
        self.assertNotContains(self.client.get(url), "09171234567")
        FriendRequest.objects.create(from_user=self.ana, to_user=self.ben, status=FriendRequest.Status.ACCEPTED)
        self.assertContains(self.client.get(url), "09171234567")


class RequestFlowTests(FriendTestCase):
    def test_full_flow_send_accept_unfriend(self):
        self.login(self.ana)
        response = self.send(self.ben, "Hi Ben!")
        self.assertContains(response, "Friend request sent")
        fr = FriendRequest.objects.get(from_user=self.ana, to_user=self.ben)
        self.assertEqual(fr.status, FriendRequest.Status.PENDING)

        self.client.logout()
        self.login(self.ben)
        response = self.client.post(reverse("friends:respond_request", args=[fr.pk, "accept"]), follow=True)
        self.assertContains(response, "are now friends")
        fr.refresh_from_db()
        self.assertEqual(fr.status, FriendRequest.Status.ACCEPTED)
        self.assertContains(self.client.get(reverse("friends:friend_list")), "Ana Tester")

        self.client.post(reverse("friends:unfriend", args=[self.ana.pk]))
        self.assertFalse(FriendRequest.objects.filter(pk=fr.pk).exists())

    def test_decline_then_resend(self):
        self.login(self.ana)
        self.send(self.ben)
        fr = FriendRequest.objects.get()
        self.client.logout()
        self.login(self.ben)
        self.client.post(reverse("friends:respond_request", args=[fr.pk, "decline"]))
        fr.refresh_from_db()
        self.assertEqual(fr.status, FriendRequest.Status.DECLINED)
        self.client.logout()
        self.login(self.ana)
        self.send(self.ben, "Second try")
        fr.refresh_from_db()
        self.assertEqual(fr.status, FriendRequest.Status.PENDING)
        self.assertEqual(FriendRequest.objects.count(), 1)

    def test_edit_and_cancel_own_request(self):
        self.login(self.ana)
        self.send(self.ben, "old")
        fr = FriendRequest.objects.get()
        self.client.post(reverse("friends:request_edit", args=[fr.pk]), {"message": "new message"})
        fr.refresh_from_db()
        self.assertEqual(fr.message, "new message")
        self.client.post(reverse("friends:request_cancel", args=[fr.pk]))
        self.assertFalse(FriendRequest.objects.exists())


class BusinessRuleTests(FriendTestCase):
    def test_no_duplicate_or_reverse_request(self):
        self.login(self.ana)
        self.send(self.ben)
        response = self.send(self.ben)
        self.assertContains(response, "already sent")
        self.client.logout()
        self.login(self.ben)
        response = self.send(self.ana)
        self.assertContains(response, "already sent you a request")
        self.assertEqual(FriendRequest.objects.count(), 1)

    def test_cannot_add_self_or_admin(self):
        self.login(self.ana)
        response = self.client.post(reverse("friends:send_request", args=[self.ana.pk]), {"message": ""})
        self.assertFalse(FriendRequest.objects.exists())
        response = self.client.post(reverse("friends:send_request", args=[self.admin.pk]), {"message": ""})
        self.assertEqual(response.status_code, 404)

    def test_message_validation(self):
        self.login(self.ana)
        response = self.send(self.ben, "add me at https://spam.example")
        self.assertContains(response, "links aren", status_code=400)
        response = self.send(self.ben, "x" * 201)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FriendRequest.objects.exists())


class OwnershipAndRoleTests(FriendTestCase):
    def setUp(self):
        super().setUp()
        self.fr = FriendRequest.objects.create(from_user=self.ana, to_user=self.ben, message="hi")

    def test_others_cannot_touch_request(self):
        self.login(self.cara)
        for name in ("friends:request_edit", "friends:request_cancel"):
            self.assertEqual(self.client.post(reverse(name, args=[self.fr.pk]), {"message": "x"}).status_code, 404)
        url = reverse("friends:respond_request", args=[self.fr.pk, "accept"])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.fr.refresh_from_db()
        self.assertEqual(self.fr.status, FriendRequest.Status.PENDING)

    def test_sender_cannot_accept_own_request(self):
        self.login(self.ana)
        url = reverse("friends:respond_request", args=[self.fr.pk, "accept"])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_admin_sees_connections_but_cannot_use_student_pages(self):
        self.login(self.admin)
        self.assertContains(self.client.get(reverse("friends:admin_connections")), "@ana")
        response = self.client.get(reverse("friends:student_list"))
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)
        self.client.post(reverse("friends:admin_connection_delete", args=[self.fr.pk]))
        self.assertFalse(FriendRequest.objects.exists())

    def test_student_cannot_open_admin_connections(self):
        self.login(self.ana)
        response = self.client.get(reverse("friends:admin_connections"))
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_logged_out_redirected_to_login(self):
        url = reverse("friends:student_list")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}", fetch_redirect_response=False)

    def test_dashboards_show_friend_data(self):
        self.login(self.ben)
        response = self.client.get(reverse("dashboard:student"))
        self.assertContains(response, "Requests waiting for you")
        self.client.logout()
        self.login(self.admin)
        self.assertContains(self.client.get(reverse("dashboard:admin")), "Pending friend requests")
