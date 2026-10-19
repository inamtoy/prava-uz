from django.db import models


class Topic(models.Model):
    name = models.CharField("nomi", max_length=200)
    slug = models.SlugField("slug", max_length=200, unique=True)
    description = models.TextField("tavsif", blank=True)
    order = models.PositiveIntegerField("tartib", default=0)

    class Meta:
        db_table = "mavzular"
        ordering = ["order", "name"]
        verbose_name = "mavzu"
        verbose_name_plural = "mavzular"

    def __str__(self):
        return self.name


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions", verbose_name="mavzu")
    text = models.TextField("savol matni")
    image = models.ImageField("rasm", upload_to="questions/", blank=True, null=True)
    explanation = models.TextField("izoh", blank=True)
    is_active = models.BooleanField("faol", default=True)
    created_at = models.DateTimeField("yaratilgan", auto_now_add=True)

    class Meta:
        db_table = "savollar"
        ordering = ["topic__order", "id"]
        verbose_name = "savol"
        verbose_name_plural = "savollar"

    def __str__(self):
        return self.text[:80]


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers", verbose_name="savol")
    text = models.CharField("javob matni", max_length=500)
    is_correct = models.BooleanField("toʻgʻri mi", default=False)

    class Meta:
        db_table = "javoblar"
        ordering = ["id"]
        verbose_name = "javob"
        verbose_name_plural = "javoblar"

    def __str__(self):
        return self.text
