from django.db import models

class FakeAdminAccessLog(models.Model):
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} - {self.attempted_at}"
