from django.db import models, IntegrityError
from django.contrib.auth.models import User
from django.utils.text import slugify


class Contest(models.Model):
    title = models.CharField(max_length=255, blank=False, null=False)
    slug = models.SlugField(unique=True, blank=True)
    # audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    # created_by = models.ForeignKey
    modified_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            if Contest.objects.filter(slug=self.slug).exists():
                self.slug = slugify(self.title + '-' + str(Contest.objects.latest('id').id))
        super(Contest, self).save(*args, **kwargs)

    def __str__(self):
        return self.title
