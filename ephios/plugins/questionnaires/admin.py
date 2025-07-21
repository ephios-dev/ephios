from django.contrib import admin

from ephios.plugins.questionnaires.models import Answer, Question, Questionnaire, SavedAnswer

admin.site.register(Answer)
admin.site.register(Question)
admin.site.register(Questionnaire)
admin.site.register(SavedAnswer)
