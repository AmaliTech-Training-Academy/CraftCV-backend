import ssl

from django.core.mail.backends.smtp import EmailBackend


class ResendEmailBackend(EmailBackend):
    """SMTP backend that relaxes Python 3.13+ strict X.509 verification.

    Python 3.13+ enables VERIFY_X509_STRICT by default, which rejects
    certificates that don't mark Basic Constraints as critical. Resend's
    SMTP certificate chain triggers this. We clear only the strict flag,
    keeping certificate verification and hostname checking intact.
    """

    def open(self):
        if self.connection:
            return False

        context = ssl.create_default_context()
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT

        self.connection = self.connection_class(
            self.host,
            self.port,
            local_hostname=None,
            timeout=self.timeout,
        )
        self.connection.ehlo()
        self.connection.starttls(context=context)
        self.connection.ehlo()
        if self.username and self.password:
            self.connection.login(self.username, self.password)
        return True
