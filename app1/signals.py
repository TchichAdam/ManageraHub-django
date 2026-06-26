from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import JobApplication, CandidateProfile, CompanyProfile
from .emails import send_html_email

_STATUS_LABELS = {
    "sent": "Sent",
    "under_review": "Under review",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "interview_scheduled": "Interview scheduled",
}

_STATUS_SUBJECTS = {
    "accepted": "Félicitations! Votre candidature a été acceptée - ManageraHub",
    "rejected": "Mise à jour concernant votre candidature - ManageraHub",
    "under_review": "Votre candidature est en cours d'examen - ManageraHub",
    "interview_scheduled": "Entretien planifié pour votre candidature - ManageraHub",
}


@receiver(pre_save, sender=JobApplication)
def notify_candidate_on_status_change(sender, instance, **kwargs):
    """Send an HTML email to the candidate when their application status changes."""
    if not instance.pk:
        return
    try:
        previous = JobApplication.objects.get(pk=instance.pk)
    except JobApplication.DoesNotExist:
        return

    if previous.status == instance.status:
        return

    subject = _STATUS_SUBJECTS.get(instance.status)
    if not subject:
        return

    candidate = instance.candidate
    candidate_email = candidate.email

    if candidate_email:
        context = {
            "candidate_name": candidate.get_full_name() or candidate.username,
            "job_title": instance.job_offer.title,
            "company_name": instance.job_offer.company.company_name,
            "status": instance.status,
        }
        send_html_email(
            subject=subject,
            template_name="emails/status_change.html",
            context=context,
            recipient_list=[candidate_email],
        )


@receiver(post_save, sender=CandidateProfile)
def notify_candidate_on_welcome(sender, instance, created, **kwargs):
    """Send a welcome HTML email to the candidate when their profile is created."""
    if created:
        user = instance.user
        if user.email:
            context = {
                "display_name": user.get_full_name() or user.username,
            }
            send_html_email(
                subject="Bienvenue sur ManageraHub !",
                template_name="emails/welcome_candidate.html",
                context=context,
                recipient_list=[user.email],
            )


@receiver(post_save, sender=CompanyProfile)
def notify_company_on_welcome(sender, instance, created, **kwargs):
    """Send a welcome HTML email to the company when their profile is created."""
    if created:
        user = instance.user
        if user.email:
            context = {
                "display_name": user.get_full_name() or user.username,
                "company_name": instance.company_name,
            }
            send_html_email(
                subject="Bienvenue sur ManageraHub !",
                template_name="emails/welcome_company.html",
                context=context,
                recipient_list=[user.email],
            )
