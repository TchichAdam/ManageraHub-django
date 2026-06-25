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
