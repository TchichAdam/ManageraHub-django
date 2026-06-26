import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_html_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Utility function to send modern HTML emails with an automatic plain-text fallback.
    Automatically injects settings.SITE_URL into the context.
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    # Inject site_url for the buttons
    context['site_url'] = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')

    try:
        # Render the HTML template
        html_content = render_to_string(template_name, context)
        
        # Automatically generate a plain-text fallback by stripping HTML tags
        text_content = strip_tags(html_content)
        
        # Create email message with multi-alternatives
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Failed to send HTML email '{subject}' to {recipient_list}: {e}")
        return False
