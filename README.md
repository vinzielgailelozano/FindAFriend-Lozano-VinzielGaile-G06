# FindAFriend — Find New Friends and Connections Around Campus

IM2 project · **LOZANO, Vinziel Gaile S.** · Section G06

FindAFriend helps students — especially irregular, transferee, shiftee and exchange students — meet classmates,
study buddies and friends with similar interests, subjects and schedules, within their own school.
- **Project Development 1:** Account Feature (registration, login/logout, role-based dashboards, profile)
- **Project Development 2:– Core Feature (Vertical Slice)** Core feature, **Friend Connections** (find students, friend requests, friends list)

The system is made with Django (backend + templates) and uses Supabase (PostgreSQL) as the database.

## Features

### Project Development 1 – Account Feature
- Register, log in and log out
- Two roles: **Admin** and **Student**
- Each role has its own dashboard, and you can't open the other role's dashboard by typing the URL
- Profile page where you can edit your name, email, contact number, course, year level, status, interests, bio and profile photo

### Project Development 2 – Core Feature: Friend Connections
This is the main feature of the app. Students can look for other students and send them friend requests.

How it works:
1. Go to **Find Friends** and search by name or interest (example: "badminton"). You can also filter by course, year level and status.
2. Open a student's page and send a friend request. You can add a short message.
3. The other student sees it in **Friend Requests** and can accept or decline it.
4. While the request is still pending, the sender can edit the message or cancel it.
5. Once accepted, both students show up in each other's **My Friends** list. Friends can see each other's email and contact number. You can also unfriend someone.
6. The admin has a **Connections** page where they can see all requests and friendships and remove spam ones.

**CRUD in this feature:**
- Create – send a friend request
- Read – search students, view a student's page, view requests and friends
- Update – accept/decline a request, edit the request message
- Delete – cancel a request, unfriend, admin removes a connection

**Rules I added:**
- You can't send a request to yourself or to an admin
- You can't send another request if one is already pending (either way) or if you're already friends
- If someone declined you, you can send again later
- Max of 20 pending requests at a time so people can't spam
- Message is optional, up to 200 characters, and links are not allowed
- Only the person who received the request can accept/decline it, and only the sender can edit/cancel it
- Contact info is only shown to friends

**Database:**
I added a `FriendRequest` model with two foreign keys to the User model (`from_user` and `to_user`), a `message`, a `status` (Pending, Accepted or Declined) and the dates. An accepted request counts as a friendship.

## Branches
- `main` – stable version
- `develop` – where features get merged first
- `feature/find-students` – the Find Friends search and student page
- `feature/friend-requests` – friend requests, friends list and the admin Connections page

Each feature branch was merged into `develop` with a pull request, then `develop` was merged into `main`.

## How to run the project

1. Clone the repo and go inside the folder
   ```
   git clone https://github.com/vinzielgailelozano/FindAFriend-Lozano-VinzielGaile-G06.git
   cd FindAFriend-Lozano-VinzielGaile-G06
   ```
2. Make a virtual environment and install the requirements
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Make a `.env` file (copy `.env.example`) and put your own Supabase or PostgreSQL details and a secret key. The `.env` file is not uploaded to GitHub.
4. Run the migrations and make an admin account
   ```
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. Run the server
   ```
   python manage.py runserver
   ```
   Then open http://127.0.0.1:8000/ (on the school lab PC I use port 8080 instead: `python manage.py runserver 8080`)

To run the tests:
```
python manage.py test accounts friends
```

## Pages
- `/accounts/register/` – register
- `/accounts/login/` – log in
- `/dashboard/` – goes to your dashboard depending on your role
- `/accounts/profile/` – your profile
- `/friends/students/` – Find Friends (students only)
- `/friends/requests/` – Friend Requests (students only)
- `/friends/` – My Friends (students only)
- `/friends/connections/` – all connections (admin only)

## Next plans
- Messaging between friends
- Activity/study groups
- Notifications
- Blocking and reporting students