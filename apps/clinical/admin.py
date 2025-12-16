from django.contrib import admin
from .models import Patient, Clinician, Department

admin.site.register(Patient)
admin.site.register(Clinician)
admin.site.register(Department)
