from django.core.mail import send_mail
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import JobApplication

_STATUS_LABELS = {
    "sent": "Sent",
    "under_review": "Under review",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "interview_scheduled": "Interview scheduled",
}

_STATUS_MESSAGES = {
    "accepted": (
        "Congratulations! Your application has been accepted.",
        "Great news — the company has accepted your application for {job}. "
        "They will be in touch with you soon.",
    ),
    "rejected": (
        "Update on your application for {job}",
        "Thank you for applying to {job}. Unfortunately the company has decided "
        "not to move forward with your application at this time. Keep applying!",
    ),
    "under_review": (
        "Your application for {job} is under review",
        "Good news — your application for {job} is now being reviewed by the hiring team.",
    ),
    "interview_scheduled": (
        "Interview scheduled for {job}",
        "Your application for {job} has progressed to the interview stage. "
        "The company will contact you with scheduling details.",
    ),
}


@receiver(pre_save, sender=JobApplication)
def notify_candidate_on_status_change(sender, instance, **kwargs):
    """Send an email to the candidate when their application status changes."""
    if not instance.pk:
        return
    try:
        previous = JobApplication.objects.get(pk=instance.pk)
    except JobApplication.DoesNotExist:
        return

    if previous.status == instance.status:
        return

    template = _STATUS_MESSAGES.get(instance.status)
    if not template:
        return

    job_title = instance.job_offer.title
    subject = template[0].format(job=job_title)
    body = template[1].format(job=job_title)
    candidate_email = instance.candidate.email

    if candidate_email:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[candidate_email],
            fail_silently=True,
        )


from django.db.models.signals import post_save
from .models import CandidateProfile, CompanyProfile

@receiver(post_save, sender=CandidateProfile)
def notify_candidate_on_welcome(sender, instance, created, **kwargs):
    """Send a welcome email to the candidate when their profile is created."""
    if created:
        user = instance.user
        subject = "Welcome to ManageraHub!"
        body = (
            f"Hello {user.get_full_name() or user.username},\n\n"
            "Thank you for registering as a Candidate on ManageraHub! "
            "Your profile has been created. You can now browse job offers, "
            "apply online, track your status, and pass quizzes.\n\n"
            "Best regards,\n"
            "The ManageraHub Team"
        )
        if user.email:
            send_mail(
                subject=subject,
                message=body,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )

@receiver(post_save, sender=CompanyProfile)
def notify_company_on_welcome(sender, instance, created, **kwargs):
    """Send a welcome email to the company when their profile is created."""
    if created:
        user = instance.user
        subject = "Welcome to ManageraHub!"
        body = (
            f"Hello {user.get_full_name() or user.username},\n\n"
            "Thank you for registering as a Company on ManageraHub! "
            "Your registration has been received and is currently pending administrator approval. "
            "Once approved, you will be able to post jobs, manage applications, and hire candidates.\n\n"
            "Best regards,\n"
            "The ManageraHub Team"
        )
        if user.email:
            send_mail(
                subject=subject,
                message=body,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
