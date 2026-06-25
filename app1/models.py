from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone


def candidate_profile_file_path(instance, filename):
    user_id = getattr(instance, "user_id", None)
    if user_id is None and hasattr(instance, "profile_id"):
        user_id = instance.profile.user_id
    return f"candidate_profiles/user_{user_id}/{filename}"


def candidate_application_file_path(instance, filename):
    return f"candidate_applications/user_{instance.candidate_id}/job_{instance.job_offer_id}/{filename}"


class CandidateProfile(models.Model):
    EDUCATION_CHOICES = [
        ("high_school", "High School"),
        ("bachelor", "Bachelor"),
        ("master", "Master"),
        ("phd", "PhD"),
        ("bootcamp", "Bootcamp / Certification"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
    )
    phone_number = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    education_level = models.CharField(max_length=120, blank=True, choices=EDUCATION_CHOICES)
    skills = models.TextField(blank=True)
    experience_summary = models.TextField(blank=True)
    headline = models.CharField(max_length=180, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.FileField(upload_to=candidate_profile_file_path, blank=True)
    cv_file = models.FileField(upload_to=candidate_profile_file_path, blank=True)
    cover_letter_file = models.FileField(upload_to=candidate_profile_file_path, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name", "user__username"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username

    @property
    def completion_percent(self):
        profile_fields = [
            bool(self.user.first_name.strip() or self.user.last_name.strip()),
            bool(self.phone_number.strip()),
            bool(self.address.strip()),
            bool(self.city.strip() or self.country.strip()),
            bool(self.education_level.strip()),
            bool(self.skills.strip()),
            bool(self.experience_summary.strip()),
            bool(self.cv_file),
            bool(self.cover_letter_file),
            self.certifications.exists(),
        ]
        return int((sum(profile_fields) / len(profile_fields)) * 100)


class CandidateCertification(models.Model):
    profile = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="certifications",
    )
    file = models.FileField(upload_to=candidate_profile_file_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return self.file.name.rsplit("/", 1)[-1]


def company_profile_file_path(instance, filename):
    return f"company_profiles/user_{instance.user_id}/{filename}"


class CompanyProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_profile",
    )
    company_name = models.CharField(max_length=180, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    company_size = models.CharField(max_length=60, blank=True)
    phone_number = models.CharField(max_length=40, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    website = models.URLField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=company_profile_file_path, blank=True)
    background_image = models.ImageField(upload_to=company_profile_file_path, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moroccan Legal Verification Fields
    ice = models.CharField(max_length=15, blank=True, null=True, verbose_name="ICE (15 digits)")
    rc_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Registre du Commerce (RC)")
    legal_document = models.FileField(upload_to=company_profile_file_path, blank=True, null=True)

    class Meta:
        ordering = ["company_name", "user__username"]

    def __str__(self):
        return self.company_name or self.user.get_full_name().strip() or self.user.username

    @property
    def display_name(self):
        return self.company_name or self.user.get_full_name().strip() or self.user.username

    @property
    def completion_percent(self):
        fields = [
            bool(self.company_name.strip()),
            bool(self.industry.strip()),
            bool(self.company_size.strip()),
            bool(self.phone_number.strip()),
            bool(self.city.strip() or self.country.strip()),
            bool(self.website),
            bool(self.description.strip()),
            bool(self.logo),
            bool(self.ice and len(self.ice.strip()) == 15),
            bool(self.legal_document),
        ]
        return int((sum(fields) / len(fields)) * 100)



class JobOffer(models.Model):
    JOB_TYPE_CHOICES = [
        ("full_time", "Full-time"),
        ("part_time", "Part-time"),
        ("internship", "Internship / Stage"),
        ("alternance", "Alternance / Apprentissage"),
        ("freelance", "Freelance / Mission"),
        ("shift", "Shift Work"),
    ]
    CONTRACT_TYPE_CHOICES = [
        ("cdi", "CDI (Permanent)"),
        ("cdd", "CDD (Fixed-term)"),
        ("anapec", "ANAPEC (Insertion)"),
        ("stage_pre", "Stage Pré-embauche"),
        ("stage_obs", "Stage d'observation"),
        ("freelance", "Freelance / Auto-entrepreneur"),
        ("ctt", "CTT (Interim)"),
    ]
    EXPERIENCE_LEVEL_CHOICES = [
        ("junior", "Junior"),
        ("mid", "Mid-Level"),
        ("senior", "Senior"),
        ("lead", "Lead"),
    ]

    title = models.CharField(max_length=180)
    company_name = models.CharField(max_length=180)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120, default="Morocco")
    job_type = models.CharField(max_length=40, choices=JOB_TYPE_CHOICES)
    contract_type = models.CharField(max_length=40, choices=CONTRACT_TYPE_CHOICES)
    experience_level = models.CharField(max_length=40, choices=EXPERIENCE_LEVEL_CHOICES)
    summary = models.TextField()
    responsibilities = models.TextField()
    requirements = models.TextField()
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_job_offers",
    )
    salary_range = models.CharField(max_length=120, blank=True)
    is_remote = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    posted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-posted_at", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.company_name}"


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("under_review", "Under review"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("interview_scheduled", "Interview scheduled"),
    ]

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications",
    )
    job_offer = models.ForeignKey(
        JobOffer,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    full_name = models.CharField(max_length=180)
    email = models.EmailField()
    phone_number = models.CharField(max_length=40, blank=True)
    application_text = models.TextField(blank=True)
    cv_file = models.FileField(upload_to=candidate_application_file_path, blank=True)
    cover_letter_file = models.FileField(upload_to=candidate_application_file_path, blank=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="sent")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job_offer"],
                name="unique_candidate_job_application",
            )
        ]

    def __str__(self):
        return f"{self.full_name} -> {self.job_offer.title}"

    @property
    def progress_steps(self):
        status_map = {
            "sent": 1,
            "under_review": 2,
            "interview_scheduled": 3,
            "accepted": 4,
            "rejected": 4,
        }
        current_step_num = status_map.get(self.status, 1)
        
        steps = [
            {
                "key": "sent",
                "label": "Candidature Envoyée",
                "desc": "Votre dossier a été soumis avec succès.",
                "state": "completed" if current_step_num >= 1 else "upcoming"
            },
            {
                "key": "under_review",
                "label": "En cours d'examen",
                "desc": "L'équipe de recrutement étudie votre profil.",
                "state": "completed" if current_step_num > 2 else ("current" if current_step_num == 2 else "upcoming")
            },
            {
                "key": "interview",
                "label": "Entretien Planifié",
                "desc": "Un entretien a été organisé par l'entreprise.",
                "state": "completed" if current_step_num > 3 else ("current" if current_step_num == 3 else "upcoming")
            },
            {
                "key": "decision",
                "label": "Décision Finale",
                "desc": "Félicitations ! Candidature acceptée." if self.status == "accepted" else ("Désolé, candidature non retenue." if self.status == "rejected" else "Décision finale en attente."),
                "state": "rejected" if self.status == "rejected" else ("current" if self.status == "accepted" else ("current" if current_step_num == 4 else "upcoming"))
            }
        ]
        
        return steps

    @property
    def live_activity_logs(self):
        logs = []
        base_time = self.submitted_at
        
        logs.append({
            "time": base_time.strftime("%d %b, %H:%M"),
            "title": "Candidature reçue",
            "desc": "Votre dossier a été enregistré avec succès dans notre système."
        })
        
        status_map = {
            "sent": 1,
            "under_review": 2,
            "interview_scheduled": 3,
            "accepted": 4,
            "rejected": 4,
        }
        current_step_num = status_map.get(self.status, 1)
        
        if current_step_num >= 2:
            review_time = self.updated_at if current_step_num == 2 else base_time
            logs.append({
                "time": review_time.strftime("%d %b, %H:%M"),
                "title": "Profil en cours d'examen",
                "desc": "Le département des ressources humaines étudie votre parcours."
            })
            
        if current_step_num >= 3:
            interview_time = self.updated_at if current_step_num == 3 else base_time
            logs.append({
                "time": interview_time.strftime("%d %b, %H:%M"),
                "title": "Planification d'entretien",
                "desc": "Un entretien a été planifié. Vérifiez votre boîte mail."
            })
            
        if current_step_num == 4:
            decision_title = "Candidature Acceptée 🎉" if self.status == "accepted" else "Candidature Refusée"
            decision_desc = "Offre d'emploi émise. Félicitations !" if self.status == "accepted" else "Votre profil n'a pas été retenu pour ce poste."
            logs.append({
                "time": self.updated_at.strftime("%d %b, %H:%M"),
                "title": decision_title,
                "desc": decision_desc
            })
            
        logs.reverse()
        return logs


def social_post_file_path(instance, filename):
    return f"social_posts/user_{instance.author_id}/{filename}"


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_posts",
    )
    content = models.TextField()
    image = models.FileField(upload_to=social_post_file_path, blank=True, null=True)
    video = models.FileField(upload_to=social_post_file_path, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    tagged_company = models.ForeignKey(
        "CompanyProfile",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tagged_posts",
    )
    tagged_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="tagged_in_posts_list",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"

    @property
    def total_likes(self):
        return self.likes.count()


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on post {self.post_id}"


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_relations",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follower_relations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_follower_following",
            )
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class QuizResult(models.Model):
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_results",
    )
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    taken_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_at"]

    def __str__(self):
        return f"{self.candidate} — {self.score}/{self.total}"

    @property
    def percent(self):
        return int(round((self.score / self.total) * 100)) if self.total else 0


# ── File cleanup: delete old file from disk when a new one is uploaded ──────

def _replace_file(old_field, new_field):
    """Delete the old stored file if it was replaced with a different one."""
    if old_field and str(old_field) != str(new_field):
        old_field.delete(save=False)


@receiver(pre_save, sender=CandidateProfile)
def cleanup_candidate_profile_files(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = CandidateProfile.objects.get(pk=instance.pk)
    except CandidateProfile.DoesNotExist:
        return
    _replace_file(old.cv_file, instance.cv_file)
    _replace_file(old.cover_letter_file, instance.cover_letter_file)
    _replace_file(old.profile_picture, instance.profile_picture)


@receiver(post_delete, sender=CandidateProfile)
def delete_candidate_profile_files(sender, instance, **kwargs):
    for field in (instance.cv_file, instance.cover_letter_file, instance.profile_picture):
        if field:
            field.delete(save=False)


@receiver(post_delete, sender=CandidateCertification)
def delete_certification_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(post_delete, sender=JobApplication)
def delete_application_files(sender, instance, **kwargs):
    for field in (instance.cv_file, instance.cover_letter_file):
        if field:
            field.delete(save=False)


@receiver(post_delete, sender=Post)
def delete_post_files(sender, instance, **kwargs):
    for field in (instance.image, instance.video):
        if field:
            field.delete(save=False)

