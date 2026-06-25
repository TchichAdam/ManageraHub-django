from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase

from .models import CandidateCertification, CandidateProfile, JobApplication, JobOffer, Post, Comment, Follow


class SigninRoutesTests(TestCase):
    def test_candidate_signin_route_renders(self):
        response = self.client.get("/candidate/signin")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate")

    def test_company_signin_route_renders(self):
        response = self.client.get("/company/signin")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Company")

    def test_candidate_login_redirects_to_candidate_dashboard_url(self):
        User.objects.create_user(
            username="candidate@example.com",
            email="candidate@example.com",
            password="secret123",
        )

        response = self.client.post(
            "/candidate/signin",
            {
                "role": "candidate",
                "email": "candidate@example.com",
                "password": "secret123",
            },
        )

        self.assertRedirects(response, "/candidate/dashboard/", fetch_redirect_response=False)

    def test_company_login_redirects_to_company_dashboard_url(self):
        User.objects.create_user(
            username="company@example.com",
            email="company@example.com",
            password="secret123",
        )

        response = self.client.post(
            "/company/signin",
            {
                "role": "company",
                "email": "company@example.com",
                "password": "secret123",
            },
        )

        self.assertRedirects(response, "/company/dashboard", fetch_redirect_response=False)

    def test_candidate_registration_creates_profile_and_redirects_to_dashboard(self):
        response = self.client.post(
            "/candidate/register",
            {
                "first_name": "Aya",
                "last_name": "Raji",
                "email": "aya@example.com",
                "phone": "+212600000000",
                "country": "Morocco",
                "city": "Casablanca",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "terms": "on",
            },
        )

        self.assertRedirects(response, "/candidate/dashboard/", fetch_redirect_response=False)
        user = User.objects.get(email="aya@example.com")
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())

    def test_candidate_dashboard_requires_candidate_account(self):
        response = self.client.get("/candidate/dashboard")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/candidate/signin", response.url)

    def test_candidate_dashboard_renders_for_candidate_user(self):
        user = User.objects.create_user(
            username="candidate2@example.com",
            email="candidate2@example.com",
            password="secret123",
        )
        CandidateProfile.objects.create(user=user, city="Rabat", country="Morocco")
        self.client.force_login(user)

        response = self.client.get("/candidate/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate Dashboard")
        self.assertContains(response, "Home")
        self.assertContains(response, "Search jobs, companies, or keywords")

    def test_job_offers_page_shows_all_active_jobs_by_default(self):
        user = User.objects.create_user(
            username="jobs@example.com",
            email="jobs@example.com",
            password="secret123",
        )
        CandidateProfile.objects.create(user=user, city="Rabat", country="Morocco")
        JobOffer.objects.create(
            title="Product Designer",
            company_name="Atlas Studio",
            city="Rabat",
            country="Morocco",
            job_type="design",
            contract_type="full_time",
            experience_level="mid",
            summary="Shape elegant interfaces for hiring teams.",
            responsibilities="Design flows",
            requirements="Figma",
        )
        JobOffer.objects.create(
            title="Marketing Analyst",
            company_name="North Metrics",
            city="Casablanca",
            country="Morocco",
            job_type="marketing",
            contract_type="contract",
            experience_level="junior",
            summary="Support campaign reporting and analysis.",
            responsibilities="Analyze reports",
            requirements="Excel",
        )
        self.client.force_login(user)

        response = self.client.get("/candidate/jobs/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product Designer")
        self.assertContains(response, "Marketing Analyst")
        self.assertContains(response, "Search jobs")

    def test_profile_update_saves_candidate_data(self):
        user = User.objects.create_user(
            username="profile@example.com",
            email="profile@example.com",
            password="secret123",
            first_name="Aya",
            last_name="Before",
        )
        CandidateProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            "/candidate/profile/",
            {
                "first_name": "Aya",
                "last_name": "After",
                "phone_number": "+212600000123",
                "address": "Casablanca-Settat",
                "city": "Casablanca",
                "country": "Morocco",
                "education_level": "master",
                "headline": "Junior software engineer",
                "skills": "Python, Django",
                "experience_summary": "Internship",
                "bio": "Looking for opportunities",
                "is_public": "on",
            },
        )

        self.assertRedirects(response, "/candidate/profile/?saved=1", fetch_redirect_response=False)
        user.refresh_from_db()
        profile = user.candidate_profile
        self.assertEqual(user.last_name, "After")
        self.assertEqual(profile.phone_number, "+212600000123")
        self.assertEqual(profile.address, "Casablanca-Settat")
        self.assertEqual(profile.education_level, "master")

    def test_candidate_can_apply_to_job_using_profile_documents(self):
        user = User.objects.create_user(
            username="apply@example.com",
            email="apply@example.com",
            password="secret123",
        )
        profile = CandidateProfile.objects.create(
            user=user,
            cv_file=SimpleUploadedFile("cv.txt", b"cv"),
            cover_letter_file=SimpleUploadedFile("cover.txt", b"cover"),
        )
        job = JobOffer.objects.create(
            title="Junior Frontend Developer",
            company_name="Atlas Digital",
            city="Casablanca",
            country="Morocco",
            job_type="engineering",
            contract_type="full_time",
            experience_level="junior",
            summary="Summary",
            responsibilities="Responsibilities",
            requirements="Requirements",
        )
        self.client.force_login(user)

        response = self.client.post(
            f"/candidate/jobs/{job.id}/apply/",
            {
                "full_name": "Aya Candidate",
                "email": "apply@example.com",
                "phone_number": "+212600000888",
                "application_text": "Ready to contribute.",
                "use_profile_cv": "on",
                "use_profile_cover_letter": "on",
            },
        )

        self.assertRedirects(response, f"/candidate/jobs/{job.id}/?applied=1", fetch_redirect_response=False)
        application = JobApplication.objects.get(candidate=user, job_offer=job)
        self.assertEqual(application.status, "sent")
        self.assertTrue(bool(application.cv_file))

    def test_profile_update_can_save_multiple_certifications(self):
        user = User.objects.create_user(
            username="certs@example.com",
            email="certs@example.com",
            password="secret123",
            first_name="Aya",
            last_name="Raji",
        )
        CandidateProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            "/candidate/profile/",
            {
                "first_name": "Aya",
                "last_name": "Raji",
                "phone_number": "+212600000123",
                "address": "Casablanca-Settat",
                "city": "Casablanca",
                "country": "Morocco",
                "education_level": "master",
                "headline": "Junior software engineer",
                "skills": "Python, Django",
                "experience_summary": "Internship",
                "bio": "Looking for opportunities",
                "is_public": "on",
                "certification_files": [
                    SimpleUploadedFile("cert1.txt", b"candidate certification 1"),
                    SimpleUploadedFile("cert2.txt", b"candidate certification 2"),
                ],
            },
        )

        self.assertRedirects(response, "/candidate/profile/?saved=1", fetch_redirect_response=False)
        self.assertEqual(CandidateCertification.objects.filter(profile=user.candidate_profile).count(), 2)


class SocialFeedAndNetworkTests(TestCase):
    def setUp(self):
        self.candidate_user = User.objects.create_user(
            username="test_candidate@example.com",
            email="test_candidate@example.com",
            password="secret123",
        )
        CandidateProfile.objects.create(user=self.candidate_user, city="Rabat", country="Morocco")
        
        self.other_user = User.objects.create_user(
            username="other_candidate@example.com",
            email="other_candidate@example.com",
            password="secret123",
        )
        CandidateProfile.objects.create(user=self.other_user, city="Casablanca", country="Morocco")

    def test_feed_page_requires_auth(self):
        response = self.client.get("/candidate/feed")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/candidate/signin", response.url)

    def test_feed_page_renders_for_logged_in_candidate(self):
        self.client.force_login(self.candidate_user)
        response = self.client.get("/candidate/feed")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Réseau Professionnel")
        self.assertContains(response, "Quoi de neuf ?")

    def test_candidate_can_create_post(self):
        self.client.force_login(self.candidate_user)
        response = self.client.post(
            "/candidate/feed",
            {"content": "Hello world from tests! #testtag"}
        )
        self.assertRedirects(response, "/candidate/feed")
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().content, "Hello world from tests! #testtag")

    def test_candidate_can_like_post(self):
        self.client.force_login(self.candidate_user)
        post = Post.objects.create(author=self.other_user, content="Some post content")
        response = self.client.get(f"/candidate/posts/{post.id}/like/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(post.likes.filter(id=self.candidate_user.id).exists())

    def test_candidate_can_comment_post(self):
        self.client.force_login(self.candidate_user)
        post = Post.objects.create(author=self.other_user, content="Some post content")
        response = self.client.post(
            f"/candidate/posts/{post.id}/comment/",
            {"content": "This is a great comment!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().content, "This is a great comment!")

    def test_candidate_can_follow_user(self):
        self.client.force_login(self.candidate_user)
        response = self.client.get(f"/candidate/users/{self.other_user.id}/follow/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Follow.objects.filter(follower=self.candidate_user, following=self.other_user).exists())

    def test_feed_search_filters_by_post_content(self):
        self.client.force_login(self.candidate_user)
        Post.objects.create(author=self.other_user, content="This is an OFPPT certified course post!")
        Post.objects.create(author=self.other_user, content="Django framework overview and details")
        
        response = self.client.get("/candidate/feed?q=OFPPT")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OFPPT")
        self.assertNotContains(response, "Django framework")

    def test_feed_search_filters_by_comment_content(self):
        self.client.force_login(self.candidate_user)
        post_ok = Post.objects.create(author=self.other_user, content="First original post content")
        post_fail = Post.objects.create(author=self.other_user, content="Second original post content")
        
        Comment.objects.create(post=post_ok, author=self.candidate_user, content="This is excellent feedback indeed!")
        
        response = self.client.get("/candidate/feed?q=feedback")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First original post content")
        self.assertNotContains(response, "Second original post content")

    def test_create_post_with_metadata(self):
        from .models import CompanyProfile
        self.client.force_login(self.candidate_user)
        company_user = User.objects.create_user(
            username="company_user_test@example.com",
            email="company_user_test@example.com",
            password="secret123",
        )
        company = CompanyProfile.objects.create(user=company_user, company_name="Test Corp", industry="IT")
        
        response = self.client.post(
            "/candidate/feed",
            {
                "content": "A high-end professional update!",
                "location": "Casablanca, Morocco",
                "tagged_company": company.id,
                "tagged_users": [self.other_user.id]
            }
        )
        self.assertRedirects(response, "/candidate/feed")
        
        post = Post.objects.latest("id")
        self.assertEqual(post.content, "A high-end professional update!")
        self.assertEqual(post.location, "Casablanca, Morocco")
        self.assertEqual(post.tagged_company, company)
        self.assertIn(self.other_user, post.tagged_users.all())

    def test_feed_renders_post_metadata(self):
        from .models import CompanyProfile
        self.client.force_login(self.candidate_user)
        company_user = User.objects.create_user(
            username="company_user_test2@example.com",
            email="company_user_test2@example.com",
            password="secret123",
        )
        company = CompanyProfile.objects.create(user=company_user, company_name="Test Corp", industry="IT")
        post = Post.objects.create(
            author=self.candidate_user,
            content="This is content with location and tags",
            location="Marrakech",
            tagged_company=company
        )
        post.tagged_users.add(self.other_user)
        
        response = self.client.get("/candidate/feed")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marrakech")
        self.assertContains(response, "Test Corp")



